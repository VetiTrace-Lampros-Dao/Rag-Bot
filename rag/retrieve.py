"""VeriTrace RAG — Retrieval Module

Provides a retrieve() function that embeds a query using Gemini and
returns the top-k matching document chunks from ChromaDB.

Usage:
    from rag.retrieve import retrieve
    results = retrieve("what is the pHash threshold", k=4)
"""

import os
import sys
import time

from dotenv import load_dotenv
from google import genai
import chromadb

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from orchestrator.key_manager import key_manager

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
COLLECTION_NAME = "veritrace_docs"
EMBEDDING_MODEL = "gemini-embedding-001"


def _get_collection():
    """Get the ChromaDB collection."""
    chroma_client = chromadb.PersistentClient(path=os.path.abspath(CHROMA_DIR))
    return chroma_client.get_collection(name=COLLECTION_NAME)


def retrieve(query: str, k: int = 4) -> list[dict]:
    """Embed a query and return the top-k matching document chunks.

    Args:
        query: The search query string.
        k: Number of results to return (default 4).

    Returns:
        A list of dicts, each with 'text', 'source', and 'distance' keys,
        sorted by relevance (most relevant first).
    """
    collection = _get_collection()

    # Embed the query with key rotation and retry logic
    max_retries = max(10, len(key_manager.keys) * 2)
    backoff = 1
    query_embedding = None

    for attempt in range(max_retries):
        current_key = key_manager.get_api_key()
        client = genai.Client(api_key=current_key)
        try:
            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=[query],
            )
            query_embedding = result.embeddings[0].values
            break
        except Exception as e:
            err_msg = str(e)
            if any(x in err_msg.upper() for x in ["429", "RESOURCE_EXHAUSTED", "401", "UNAUTHENTICATED", "403", "PERMISSION_DENIED", "503", "UNAVAILABLE", "500", "INTERNAL"]):
                print(f"\n[RAG_RETRIEVE] Quota/Auth/API error ({err_msg[:60]}...). Rotating API key away from index {key_manager.current_index}...", file=sys.stderr)
                key_manager.rotate_key(current_key)
                time.sleep(backoff)
                backoff = min(8, backoff * 1.5)
            else:
                raise e
    else:
        # Final fallback attempt
        client = genai.Client(api_key=key_manager.get_api_key())
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=[query],
        )
        query_embedding = result.embeddings[0].values

    # Search ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    # Format results
    chunks = []
    if results and results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            chunks.append(
                {
                    "text": doc,
                    "source": results["metadatas"][0][i]["source"],
                    "distance": results["distances"][0][i],
                }
            )

    return chunks


if __name__ == "__main__":
    # Quick test
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "what is the pHash threshold"

    print(f"Query: {query}")
    print("=" * 40)
    results = retrieve(query)
    for i, r in enumerate(results):
        print(f"\n--- Result {i + 1} (distance: {r['distance']:.4f}) ---")
        print(f"Source: {r['source']}")
        print(f"Text: {r['text'][:200]}...")
