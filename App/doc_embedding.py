from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# ---------------- LOAD ENV ----------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env")

CHROMA_PATH = os.getenv("CHROMA_DB_PATH", "Chroma")

# ---------------- FASTAPI SETUP ----------------
app = FastAPI()

origins = [
    "http://localhost:8501",
    "http://127.0.0.1:8501",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




# Main Function
def process_documents(file_path):
    retrived_docs = load_documents(file_path)
    retrived_chunks = split_text(retrived_docs)
    result = save_to_database(retrived_chunks)
    return result

    
# Read files in format .txt, .pdf, .md, .csv and convert to Langchain Document Objects
# Load Documents
def load_documents(file_path):
    loader = DirectoryLoader(file_path)
    documents = loader.load()
    return documents


# Separate to chunks
def split_text(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=250,
        length_function=len,
        add_start_index=True,
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split {len(documents)} documents into {len(chunks)} chunks.")

    return chunks


def save_to_database(chunks: list[Document]):
    if os.path.exists(CHROMA_PATH):
        db = Chroma(
            embedding_function=OpenAIEmbeddings(),
            persist_directory=CHROMA_PATH
        )
        print("Loaded existing database.")
    else:
        db = Chroma(
            embedding_function=OpenAIEmbeddings(),
            persist_directory=CHROMA_PATH
        )
        print("Created new database.")

    # ---------- Get Existing Metadata ----------
    existing_docs = db.get(include=["metadatas"])
    existing_sources = set()

    if existing_docs and "metadatas" in existing_docs:
        for metadata in existing_docs["metadatas"]:
            # Each metadata is already a dict in Chroma
            if isinstance(metadata, dict):
                filename = os.path.basename(metadata.get("source", ""))
                if filename:
                    existing_sources.add(filename)
            elif isinstance(metadata, str):
                filename = os.path.basename(metadata)
                if filename:
                    existing_sources.add(filename)

    print("Existing filenames in DB:", existing_sources)

    # ---------- Detect Duplicates ----------
    duplicate_files = set()
    new_chunks = []

    for chunk in chunks:
        chunk_source_name = os.path.basename(
            chunk.metadata.get("source", "")
        )

        if chunk_source_name in existing_sources:
            duplicate_files.add(chunk_source_name)
        else:
            new_chunks.append(chunk)

    # ---------- If duplicates found ----------
    if duplicate_files:
        print("\n\n\Duplicate documents found:", duplicate_files)
        return {
            "status": "duplicate",
            "duplicates": list(duplicate_files)
        }

    # ---------- Save New Documents ----------
    db.add_documents(new_chunks)
    db.persist()

    print(f"Saved {len(new_chunks)} chunks to {CHROMA_PATH}.")

    return {
        "status": "success",
        "duplicates": []
    }