import os
import uuid
import chromadb
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Import our tools
from . import memory_tool, general_tool, system_tool

# --- 1. Get the API Key ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("BRAIN: GOOGLE_API_KEY not found. Make sure server.py loads it.")

# --- 2. Initialize LLMs ---
print("Brain: Initializing...")

# LLMs
rag_llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0, google_api_key=GOOGLE_API_KEY)
router_llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0, google_api_key=GOOGLE_API_KEY)
general_llm = ChatGoogleGenerativeAI(model="gemini-pro-latest", temperature=0.7, google_api_key=GOOGLE_API_KEY)

# --- 3. Define All Chains ---

# General Knowledge Chain
general_prompt_template = "{user_input}"
general_prompt = PromptTemplate.from_template(general_prompt_template)
general_chain = general_prompt | general_llm | StrOutputParser()

# RAG chain (for personal memory)
retriever = memory_tool.retriever # Get the retriever from the tool
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

# Router chain (4 intents)
router_prompt_template = """
Classify the user's intent into one of four categories:
1. 'INGEST': User is stating a new fact or note to be saved (e.g., "Remember that...", "My new idea is...").
2. 'PERSONAL_QUERY': User is asking a question about themselves, their plans, or their saved notes (e.g., "What's my project idea?", "What's on my shopping list?").
3. 'GENERAL_KNOWLEDGE': User is asking a general fact-based question about the world (e.g., "What is the capital of India?", "How does a car engine work?").
4. 'SYSTEM_COMMAND': User is asking to perform an action on the computer (e.g., "Open Chrome", "Set a timer for 20 seconds", "Close this app").
Respond with ONLY the category name (e.g., "INGEST", "PERSONAL_QUERY", "GENERAL_KNOWLEDGE", "SYSTEM_COMMAND").
User's statement: "{user_input}"
Classification:
"""
router_prompt = PromptTemplate.from_template(router_prompt_template)
router_chain = router_prompt | router_llm | StrOutputParser()


# --- NEW: SUMMARIZER CHAIN ---
summarizer_prompt_template = """
You are a summarization assistant. Take the following text and create a concise, one-sentence summary.
If the text is already short (like an 'OK' message), just return the original text.

Original Text: "{full_text}"
Summary:
"""
summarizer_prompt = PromptTemplate.from_template(summarizer_prompt_template)
# We use the fast 'flash' model for this simple task
summarizer_chain = summarizer_prompt | ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0, google_api_key=GOOGLE_API_KEY) | StrOutputParser()
# --- END NEW CHAIN ---

print("--- Brain Initialized ---")


# --- 4. Define Main Logic Function ---

def get_ai_response(user_input):
    """
    This is the main function the server will call.
    It routes the intent, gets a full answer, summarizes it,
    and returns both.
    """
    
    # 1. Use the LLM Router
    intent = router_chain.invoke({"user_input": user_input})
    print(f"[Intent: {intent}]")

    full_answer = ""
    needs_summary = False

    # 2. Call the correct tool based on the intent
    if "PERSONAL_QUERY" in intent:
        full_answer = memory_tool.ask_personal_memory(user_input)
        needs_summary = True
    
    elif "INGEST" in intent:
        full_answer = memory_tool.add_to_memory(user_input)
        needs_summary = False # Answer is already short

    elif "GENERAL_KNOWLEDGE" in intent:
        full_answer = general_tool.ask_general_knowledge(user_input)
        needs_summary = True

    elif "SYSTEM_COMMAND" in intent:
        full_answer = system_tool.execute_system_command(user_input)
        needs_summary = False # Answer is already short
    
    else:
        # Fallback for any unknown intent
        print("[Intent: Fallback to General]")
        full_answer = general_tool.ask_general_knowledge(user_input)
        needs_summary = True

    # 3. Create the final response object
    response = {
        "full_text": full_answer,
        "summary_text": full_answer # Default
    }

    # 4. Summarize if needed
    if needs_summary:
        print("Summarizing full answer...")
        summary = summarizer_chain.invoke({"full_text": full_answer})
        response["summary_text"] = summary
        
    return response