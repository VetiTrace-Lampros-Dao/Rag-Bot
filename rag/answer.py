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

from dotenv import load_dotenv
from google import genai
from google.genai import types

from rag.retrieve import retrieve

load_dotenv()

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

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

    # Call Gemini
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

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
    print("=" * 50)
    result = answer(question)
    print(f"\nAnswer:\n{result['answer']}")
    print(f"\nSources: {result['sources']}")
