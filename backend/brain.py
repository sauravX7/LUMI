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

# --- UPDATED: Import all 4 tools ---
from backend import memory_tool, general_tool, system_tool, vision_tool
# ---

# --- 1. Get the API Key ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("BRAIN: GOOGLE_API_KEY not found. Make sure server.py loads it.")

# --- 2. Initialize LLMs (FIXED) ---
print("Brain: Initializing...")
# --- FIX: Added 'google_api_key=GOOGLE_API_KEY' back in ---
rag_llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0, google_api_key=GOOGLE_API_KEY)
router_llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0, google_api_key=GOOGLE_API_KEY)
general_llm = ChatGoogleGenerativeAI(model="gemini-pro-latest", temperature=0.7, google_api_key=GOOGLE_API_KEY)
# --- END OF FIX ---

# --- 3. Define All Chains ---
general_chain = general_tool.general_chain
rag_chain = memory_tool.rag_chain

# --- Router chain (UPDATED to 6 intents) ---
router_prompt_template = """
Classify the user's intent into one of six categories:

1. 'CONVERSATION': Simple greetings, small talk, or conversational questions (e.g., "Hello", "How are you?", "What's up?", "Who are you?").
2. 'VISION': User is asking to see, look at, or analyze the screen (e.g., "see my screen", "what is this", "what am I looking at").
3. 'INGEST': User is stating a new fact or note to be saved (e.g., "Remember that...", "My new idea is...").
4. 'PERSONAL_QUERY': User is asking a question about themselves, their plans, or their saved notes (e.g., "What's my project idea?", "What's on my shopping list?").
5. 'GENERAL_KNOWLEDGE': User is asking a general fact-based question about the world (e.g., "What is the capital of India?", "How does a car engine work?").
6. 'SYSTEM_COMMAND': User is asking to perform an action on the computer (e.g., "Open Chrome", "Set a timer for 20 seconds", "Close this app").

Respond with ONLY the category name (e.g., "CONVERSATION", "VISION", "INGEST", "PERSONAL_QUERY", "GENERAL_KNOWLEDGE", "SYSTEM_COMMAND").

User's statement: "{user_input}"
Classification:
"""
router_prompt = PromptTemplate.from_template(router_prompt_template)
router_chain = router_prompt | router_llm | StrOutputParser()

# Summarizer Chain
summarizer_prompt_template = """
You are a summarization assistant. Take the following text and create a concise, one-sentence summary.
If the text is already short (like an 'OK' message), just return the original text.
Original Text: "{full_text}"
Summary:
"""
summarizer_prompt = PromptTemplate.from_template(summarizer_prompt_template)
# --- FIX: Added 'google_api_key=GOOGLE_API_KEY' back in ---
summarizer_chain = summarizer_prompt | ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0, google_api_key=GOOGLE_API_KEY) | StrOutputParser()

# --- NEW: Define Greeting Keywords ---
GREETING_KEYWORDS = ['hello', 'hi', 'hey', 'greeting', 'greetings', 'yo']
# ---

print("--- Brain Initialized ---")


# --- 4. Define Main Logic Function (UPDATED) ---

def get_ai_response(user_input):
    """
    This is the main function the server will call.
    It routes the intent and calls the correct tool.
    """
    
    # --- NEW: Simple keyword check for greetings ---
    # We check this *before* calling the LLM router
    clean_input = user_input.lower().strip("?!., ")
    if any(clean_input.startswith(word) for word in GREETING_KEYWORDS):
        print("[Intent: GREETING] (Hard-coded)")
        full_answer = "Hi there! How can I help you?"
        return {
            "full_text": full_answer,
            "summary_text": full_answer
        }
    # --- END OF NEW CHECK ---

    # 1. Use the LLM Router
    intent = router_chain.invoke({"user_input": user_input})
    print(f"[Intent: {intent}]")

    full_answer = ""
    needs_summary = False

    # 2. Call the correct tool based on the intent
    if "VISION" in intent:
        full_answer = vision_tool.analyze_screen(user_input)
        needs_summary = True # Vision answers can be long

    elif "CONVERSATION" in intent: # This will now catch "How are you?"
        full_answer = general_tool.ask_general_knowledge(user_input)
        needs_summary = False 

    elif "PERSONAL_QUERY" in intent:
        full_answer = memory_tool.ask_personal_memory(user_input)
        needs_summary = True
    
    elif "INGEST" in intent:
        full_answer = memory_tool.add_to_memory(user_input)
        needs_summary = False

    elif "GENERAL_KNOWLEDGE" in intent:
        full_answer = general_tool.ask_general_knowledge(user_input)
        needs_summary = True

    elif "SYSTEM_COMMAND" in intent:
        full_answer = system_tool.execute_system_command(user_input)
        needs_summary = False
    
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
    if needs_summary and len(full_answer) > 70: # Only summarize long answers
        print("Summarizing full answer...")
        summary = summarizer_chain.invoke({"full_text": full_answer})
        response["summary_text"] = summary
        
    return response