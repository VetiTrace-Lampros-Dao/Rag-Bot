"""VeriTrace RAG — Grounded Answering Module

Takes a user question, retrieves relevant document chunks, and uses Gemini
to generate an answer grounded in the retrieved context.

Usage:
    from rag.answer import answer
    result = answer("how does the dedup pipeline work")
    print(result["answer"])
    print(result["sources"])
"""

import os
import sys
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from rag.retrieve import retrieve
from orchestrator.key_manager import key_manager

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

SYSTEM_INSTRUCTION = """You are the VeriTrace Help Bot, a knowledgeable assistant for the VeriTrace content provenance platform.

Use ONLY the following context documents to answer the user's question. Follow these rules strictly:
1. If the context covers the question, answer it clearly and accurately based on the provided information.
2. If the context does NOT cover the question, say so clearly: "I don't have information about that in my knowledge base." Do NOT guess or make up an answer.
3. When referencing specific technical details (thresholds, endpoints, etc.), cite them accurately from the context.
4. Keep answers concise but thorough. Use bullet points or numbered lists for multi-part explanations.
5. Never claim capabilities that aren't described in the context (e.g., don't say VeriTrace can detect AI-generated images unless the docs say so).

Context documents:
{context}
"""


def format_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a context string."""
    parts = []
    for i, chunk in enumerate(chunks):
        parts.append(f"[Source: {chunk['source']}]\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


def answer(question: str, k: int = 4, model: str = None) -> dict:
    """Answer a question using RAG-grounded generation.

    Args:
        question: The user's question.
        k: Number of context chunks to retrieve.
        model: Gemini model to use (defaults to GEMINI_MODEL env var or gemini-2.5-flash-lite).

    Returns:
        A dict with 'answer' (str) and 'sources' (list of source filenames).
    """
    model_name = model or DEFAULT_MODEL

    # Retrieve relevant context
    chunks = retrieve(question, k=k)
    if not chunks:
        return {
            "answer": "I don't have any information in my knowledge base to answer that question. "
                      "The document store may be empty — try running `python rag/ingest.py` first.",
            "sources": [],
        }

    # Format context and build prompt
    context = format_context(chunks)
    system_prompt = SYSTEM_INSTRUCTION.format(context=context)

    # Call Gemini with rotation and retry logic
    max_retries = max(10, len(key_manager.keys) * 2)
    backoff = 1
    response = None

    for attempt in range(max_retries):
        current_key = key_manager.get_api_key()
        client = genai.Client(api_key=current_key)
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=question,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3,
                ),
            )
            break
        except Exception as e:
            err_msg = str(e)
            if any(x in err_msg.upper() for x in ["429", "RESOURCE_EXHAUSTED", "401", "UNAUTHENTICATED", "403", "PERMISSION_DENIED", "503", "UNAVAILABLE", "500", "INTERNAL"]):
                print(f"\n[RAG_ANSWER] Quota/Auth/API error ({err_msg[:60]}...). Rotating API key away from index {key_manager.current_index}...", file=sys.stderr)
                key_manager.rotate_key(current_key)
                time.sleep(backoff)
                backoff = min(8, backoff * 1.5)
            else:
                raise e
    else:
        # Fallback
        client = genai.Client(api_key=key_manager.get_api_key())
        response = client.models.generate_content(
            model=model_name,
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
            ),
        )

    answer_text = response.text if response.text else "I was unable to generate an answer."

    # Deduplicate source filenames
    sources = list(dict.fromkeys(c["source"] for c in chunks))

    return {
        "answer": answer_text,
        "sources": sources,
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = "how does the dedup pipeline work"

    print(f"Question: {question}")
    print("=" * 40)
    result = answer(question)
    print(f"Answer:\n{result['answer']}")
    print(f"Sources: {result['sources']}")
