import os
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
from orchestrator.key_manager import key_manager

load_dotenv()

CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db")
COLLECTION_NAME = "veritrace_docs"

def retrieve(query: str, k: int = 4) -> list[dict]:
    """Embeds the query, returns top-k chunks (text + source filename)."""
    if not os.path.exists(CHROMA_DIR):
        print(f"Warning: {CHROMA_DIR} not found. Returning empty results.")
        return []

    def _do_search(active_key):
        embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-2", google_api_key=active_key)
        vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR
        )
        return vectorstore.similarity_search(query, k=k)

    try:
        docs = key_manager.execute_with_rotation(_do_search)
    except Exception as e:
        print(f"Error during document retrieval: {e}")
        return []
    
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
