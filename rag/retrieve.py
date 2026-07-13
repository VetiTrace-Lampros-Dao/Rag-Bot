"""VeriTrace RAG — Retrieval Module

Provides a retrieve() function that embeds a query using Gemini and
returns the top-k matching document chunks from ChromaDB.

Usage:
    from rag.retrieve import retrieve
    results = retrieve("what is the pHash threshold", k=4)
"""

import os
import sys

from dotenv import load_dotenv
from google import genai
import chromadb

load_dotenv()

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
COLLECTION_NAME = "veritrace_docs"
EMBEDDING_MODEL = "gemini-embedding-001"


def _get_client():
    """Initialize the Gemini client."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)
    return genai.Client(api_key=api_key)


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
    client = _get_client()

    # Embed the query
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=[query],
    )
    query_embedding = result.embeddings[0].values

    # Search ChromaDB
    collection = _get_collection()
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
