"""VeriTrace RAG — Document Ingestion Pipeline

Reads markdown files from docs/, chunks them by ## heading boundaries,
embeds each chunk via Gemini text-embedding-004, and stores them in a
local ChromaDB collection.

Usage:
    python rag/ingest.py             # incremental (only if collection is empty)
    python rag/ingest.py --rebuild   # wipe and re-embed everything
"""

import os
import sys
import re
import argparse
import hashlib

from dotenv import load_dotenv
from google import genai
import chromadb

load_dotenv()

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
COLLECTION_NAME = "veritrace_docs"
EMBEDDING_MODEL = "gemini-embedding-001"

# Rough token estimate: ~4 chars per token
MAX_CHUNK_CHARS = 2000  # ~500 tokens


def get_gemini_client():
    """Initialize the Gemini client."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)
    return genai.Client(api_key=api_key)


def read_markdown_files(docs_dir: str) -> list[dict]:
    """Read all .md files from the docs directory."""
    files = []
    for fname in sorted(os.listdir(docs_dir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(docs_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        files.append({"filename": fname, "content": content})
    return files


def chunk_by_headings(text: str, source: str) -> list[dict]:
    """Split markdown text by ## headings, then further split large chunks."""
    # Split on ## headings, keeping the heading with its section
    sections = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    chunks = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        if len(section) <= MAX_CHUNK_CHARS:
            chunks.append({"text": section, "source": source})
        else:
            # Further split large sections by paragraphs
            paragraphs = section.split("\n\n")
            current_chunk = ""
            for para in paragraphs:
                if len(current_chunk) + len(para) + 2 > MAX_CHUNK_CHARS and current_chunk:
                    chunks.append({"text": current_chunk.strip(), "source": source})
                    current_chunk = para
                else:
                    current_chunk = current_chunk + "\n\n" + para if current_chunk else para
            if current_chunk.strip():
                chunks.append({"text": current_chunk.strip(), "source": source})

    return chunks


def embed_texts(client, texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using Gemini text-embedding-004."""
    embeddings = []
    # Process in batches of 100 (API limit)
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=batch,
        )
        for embedding in result.embeddings:
            embeddings.append(embedding.values)
    return embeddings


def get_chroma_collection(rebuild: bool = False):
    """Get or create the ChromaDB collection."""
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

    if rebuild:
        try:
            chroma_client.delete_collection(COLLECTION_NAME)
            print(f"  Deleted existing collection '{COLLECTION_NAME}'")
        except Exception:
            pass  # Collection didn't exist

    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def make_chunk_id(source: str, text: str) -> str:
    """Generate a deterministic ID for a chunk."""
    h = hashlib.sha256(f"{source}::{text[:200]}".encode()).hexdigest()[:16]
    return f"{source}_{h}"


def main():
    parser = argparse.ArgumentParser(description="VeriTrace RAG ingestion pipeline")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Wipe the collection and re-embed everything from scratch",
    )
    args = parser.parse_args()

    print("VeriTrace RAG Ingestion Pipeline")
    print("=" * 40)

    # 1. Read docs
    docs_path = os.path.abspath(DOCS_DIR)
    print(f"\n1. Reading docs from: {docs_path}")
    files = read_markdown_files(docs_path)
    if not files:
        print("   ERROR: No .md files found in docs/", file=sys.stderr)
        sys.exit(1)
    print(f"   Found {len(files)} files: {[f['filename'] for f in files]}")

    # 2. Chunk documents
    print("\n2. Chunking documents...")
    all_chunks = []
    for doc in files:
        chunks = chunk_by_headings(doc["content"], doc["filename"])
        all_chunks.extend(chunks)
        print(f"   {doc['filename']} -> {len(chunks)} chunks")
    print(f"   Total chunks: {len(all_chunks)}")

    # 3. Initialize Gemini client and embed
    print("\n3. Embedding chunks via Gemini text-embedding-004...")
    client = get_gemini_client()
    texts = [c["text"] for c in all_chunks]
    embeddings = embed_texts(client, texts)
    print(f"   Embedded {len(embeddings)} chunks")

    # 4. Store in ChromaDB
    print(f"\n4. Storing in ChromaDB (rebuild={args.rebuild})...")
    collection = get_chroma_collection(rebuild=args.rebuild)

    ids = [make_chunk_id(c["source"], c["text"]) for c in all_chunks]
    documents = [c["text"] for c in all_chunks]
    metadatas = [{"source": c["source"]} for c in all_chunks]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    final_count = collection.count()
    print(f"   Collection '{COLLECTION_NAME}' now has {final_count} chunks")
    print("\nIngestion complete!")


if __name__ == "__main__":
    main()
