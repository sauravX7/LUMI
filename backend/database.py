import chromadb
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Initialize components
print("DB: Loading local embedding model...")
embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path="../chroma_db")

vector_store = Chroma(
    client=client,
    collection_name="cognitive_companion_memory",
    embedding_function=embedding_function,
)

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

print("DB: Embedding model and database loaded.")