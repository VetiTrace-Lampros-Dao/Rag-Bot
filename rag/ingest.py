import os
import argparse
import glob
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

print("Starting ingest script")
load_dotenv()
if not os.environ.get("GOOGLE_API_KEY") and os.environ.get("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
print("Loaded dotenv")

DOCS_DIR = "docs"
CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "veritrace_docs"

def ingest(rebuild: bool = False):
    print("Inside ingest function")
    if rebuild:
        import shutil
        if os.path.exists(CHROMA_DIR):
            shutil.rmtree(CHROMA_DIR)
            print(f"Removed existing Chroma DB at {CHROMA_DIR}")

    embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-2")
    
    # Init Chroma
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR
    )

    # If not rebuilding, we might just add to existing. For simplicity, if documents are many, we might duplicate.
    # The spec just says supports --rebuild to wipe and re-embed.

    # 1. Read all .md files
    md_files = glob.glob(os.path.join(DOCS_DIR, "*.md"))
    if not md_files:
        print("No .md files found in docs/ directory.")
        return

    # 2. Split by ## heading
    headers_to_split_on = [
        ("##", "Header 2")
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    # 3. Further split if over ~500 tokens (we approximate with chars, e.g. 2000 chars)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000, 
        chunk_overlap=200
    )

    all_splits = []
    for file_path in md_files:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        md_header_splits = markdown_splitter.split_text(text)
        
        # Add source filename to metadata
        filename = os.path.basename(file_path)
        for split in md_header_splits:
            split.metadata["source"] = filename
            
        # Further split
        splits = text_splitter.split_documents(md_header_splits)
        all_splits.extend(splits)

    if all_splits:
        vectorstore.add_documents(all_splits)
        print(f"Successfully ingested {len(all_splits)} chunks into {COLLECTION_NAME}.")
    else:
        print("No text chunks generated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest docs into Chroma.")
    parser.add_argument("--rebuild", action="store_true", help="Wipe existing DB and rebuild")
    args = parser.parse_args()
    
    ingest(rebuild=args.rebuild)
