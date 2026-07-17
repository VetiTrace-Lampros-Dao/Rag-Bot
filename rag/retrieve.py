import os
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()
if not os.environ.get("GOOGLE_API_KEY") and os.environ.get("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "veritrace_docs"

def retrieve(query: str, k: int = 4) -> list[dict]:
    """Embeds the query, returns top-k chunks (text + source filename)."""
    embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-2")
    
    # We must construct Chroma cautiously in case the DB doesn't exist yet
    if not os.path.exists(CHROMA_DIR):
        print(f"Warning: {CHROMA_DIR} not found. Returning empty results.")
        return []

    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR
    )
    
    docs = vectorstore.similarity_search(query, k=k)
    
    results = []
    for doc in docs:
        results.append({
            "text": doc.page_content,
            "source": doc.metadata.get("source", "unknown")
        })
        
    return results

if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "what is the pHash threshold"
    results = retrieve(query)
    for i, r in enumerate(results):
        print(f"--- Result {i+1} [{r['source']}] ---")
        print(r['text'])
        print()
