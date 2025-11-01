import os
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from .database import vector_store, text_splitter

# Get API key
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Create the RAG chain
retriever = vector_store.as_retriever(search_kwargs={"k": 2})
rag_llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0, google_api_key=GOOGLE_API_KEY)

rag_prompt_template = """
You are a helpful assistant. Answer the user's question based *only* on the
following context (pieces of their memory):
{context}
Question: {question}
Answer:
"""
rag_prompt = PromptTemplate.from_template(rag_prompt_template)
rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | rag_prompt
    | rag_llm
    | StrOutputParser()
)

# --- Define the tool functions ---

def ask_personal_memory(user_input: str) -> str:
    """Answers questions based *only* on the user's saved memory."""
    print("Tool: Calling Personal Memory (RAG)")
    return rag_chain.invoke(user_input)

def add_to_memory(user_input: str) -> str:
    """Adds a new note to the user's memory."""
    print(f"Tool: Adding to memory: '{user_input[:30]}...'")
    chunks = text_splitter.split_text(user_input)
    vector_store.add_texts(
        texts=chunks,
        metadatas=[{"source": "voice_journal"} for _ in chunks]
    )
    return "Got it. I've saved that to my memory."