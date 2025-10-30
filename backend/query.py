import chromadb
from dotenv import load_dotenv, find_dotenv
import os

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# --- NEW/UPDATED IMPORTS ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
# --- END OF UPDATES ---


# --- 1. Load API Key ---
load_dotenv(find_dotenv())
if "GOOGLE_API_KEY" not in os.environ:
    print("Error: GOOGLE_API_KEY not found. Please set it in your .env file.")
    exit()

# --- 2. Initialize ---
print("Initializing...")

# --- NEW: Use the same local embedding model ---
print("Loading local embedding model (all-MiniLM-L6-v2)...")
embedding_function = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)
print("Embedding model loaded.")

# Note: path is now ../ to find DB in the root LUMI folder
client = chromadb.PersistentClient(path="../chroma_db") 

# --- THIS FIXES THE 'AttributeError' ---
vector_store = Chroma(
    client=client,
    collection_name="cognitive_companion_memory",
    embedding_function=embedding_function,
)
# --- END OF FIX ---

llm = ChatGoogleGenerativeAI(model="gemini-pro-latest", temperature=0)

# --- 3. Create the RAG Chain ---
retriever = vector_store.as_retriever(search_kwargs={"k": 2})

template = """
You are a helpful assistant. Answer the user's question based *only* on the
following context (pieces of their memory):

{context}

Question: {question}

Answer:
"""
prompt = PromptTemplate.from_template(template)

rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# --- 4. Main part to run the script ---
if __name__ == "__main__":
    print("--- Cognitive Companion (Local Embeddings) is ready. Ask a question (or type 'exit'). ---")
    
    while True:
        question = input("\nYou: ")
        if question.lower() == 'exit':
            break
            
        print("[Companion is thinking...]")
        
        answer = rag_chain.invoke(question)
        
        print(f"\nCompanion: {answer}")