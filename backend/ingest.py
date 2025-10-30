import chromadb
from dotenv import load_dotenv, find_dotenv
import os
import uuid

# --- THIS IS THE NEW IMPORT ---
from langchain_huggingface import HuggingFaceEmbeddings
# --- THIS IS THE NEW IMPORT ---

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma


# --- 1. Load API Key ---
load_dotenv(find_dotenv()) 
if "GOOGLE_API_KEY" not in os.environ:
    print("Error: GOOGLE_API_KEY not found. Please set it in your .env file.")
    exit()

# --- 2. Initialize ---
print("Initializing...")

# --- THIS IS THE NEW EMBEDDING MODEL (100% FREE AND LOCAL) ---
print("Loading local embedding model (all-MiniLM-L6-v2)...")
embedding_function = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)
print("Embedding model loaded.")
# --- END NEW EMBEDDING MODEL ---

# Note: path is now ../ to save DB in the root LUMI folder
client = chromadb.PersistentClient(path="../chroma_db") 

collection = client.get_or_create_collection(
    name="cognitive_companion_memory"
)

vector_store = Chroma(
    client=client,
    collection_name="cognitive_companion_memory",
    embedding_function=embedding_function,
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, 
    chunk_overlap=200
)

print("--- Initialization Complete ---")

# --- 3. Create a function to add notes ---
def add_note_to_memory(note_text, source="voice_journal"):
    print(f"\nAdding new note: '{note_text[:50]}...'")
    chunks = text_splitter.split_text(note_text)
    
    vector_store.add_texts(
        texts=chunks,
        metadatas=[{"source": source} for _ in chunks]
    )
    
    print(f"Successfully added {len(chunks)} chunks to memory.")

# --- 4. Main part to run the script ---
if __name__ == "__main__":
    print("Running ingest script...")
    
    collection_count = collection.count()
    if collection_count > 0:
        print(f"Clearing {collection_count} old documents from memory...")
        collection.delete(ids=collection.get()['ids']) 
    
    add_note_to_memory(
        "Project Idea: 'Cognitive Companion'. A desktop AI that uses SST, TTS, LLMs, and RAG. It should also have an avatar and see the screen.",
        source="project_ideas"
    )
    
    add_note_to_memory(
        "My favorite programming language is Python because it's versatile and has great libraries for AI and web development.",
        source="personal_opinions"
    )

    add_note_to_memory(
        "I need to remember to buy milk, eggs, and bread on the way home today.",
        source="todo_list"
    )
    
    print("\n--- Ingestion complete. Memory is updated. ---")