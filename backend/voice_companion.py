import os
import time
import sounddevice as sd
import scipy.io.wavfile as wavfile
import google.generativeai as genai
from dotenv import load_dotenv, find_dotenv
import uuid
import pyttsx3  # Using the offline TTS library

# --- LangChain & DB Imports ---
import chromadb
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- 1. Load API Key & Configure ---
load_dotenv(find_dotenv())
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY not found. Please set it in your .env file.")
    exit()
genai.configure(api_key=GOOGLE_API_KEY)

# --- 2. Initialize RAG Brain & Ingest Tools ---
print("Initializing Cognitive Companion...")

print("Loading local embedding model (all-MiniLM-L6-v2)...")
embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
print("Embedding model loaded.")

client = chromadb.PersistentClient(path="../chroma_db")
vector_store = Chroma(
    client=client,
    collection_name="cognitive_companion_memory",
    embedding_function=embedding_function,
)
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)


rag_llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0)
router_llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0)
transcription_model = genai.GenerativeModel('gemini-flash-latest')

# RAG chain
retriever = vector_store.as_retriever(search_kwargs={"k": 2})
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

# Router chain
router_prompt_template = """
Classify the user's intent. Is the user asking a question (QUERY) or
stating a new piece of information to be saved (INGEST)?
Respond with only the word "QUERY" or "INGEST".

User's statement: "{user_input}"
Classification:
"""
router_prompt = PromptTemplate.from_template(router_prompt_template)
router_chain = router_prompt | router_llm | StrOutputParser()

# --- TTS Engine is no longer initialized here ---

print("--- Companion Initialized ---")

# --- 3. Define Audio Functions ---

def speak(text_to_speak):
    """
    Converts text to speech and plays it.
    Initializes the engine *every time* to fix the loop bug.
    """
    print(f"Companion: {text_to_speak}")
    try:
        # --- TTS FIX: Initialize engine inside the function ---
        tts_engine = pyttsx3.init(driverName='nsss')
        tts_engine.setProperty('rate', 180)
        # --- END OF FIX ---
        
        tts_engine.say(text_to_speak)
        tts_engine.runAndWait()
        tts_engine.stop() # Ensure it stops
    except Exception as e:
        print(f"Error in pyttsx3 playback: {e}")

def record_audio(filename="temp_audio.wav", duration=5, fs=44100):
    print("Recording...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    wavfile.write(filename, fs, recording)
    print("Recording finished.")
    return filename

def transcribe_audio(audio_filename):
    print("Transcribing audio...")
    try:
        audio_file = genai.upload_file(path=audio_filename)
        while audio_file.state.name == "PROCESSING":
            time.sleep(1)
            audio_file = genai.get_file(audio_file.name)
        
        response = transcription_model.generate_content([
            "Transcribe this audio clip.",
            audio_file
        ])
        genai.delete_file(audio_file.name)
        
        if response.text:
            print(f"You: {response.text}")
            return response.text
        else:
            return None
    except Exception as e:
        print(f"Error during transcription: {e}")
        return None

def add_note_to_memory(note_text, source="voice_journal"):
    print(f"\nAdding new note: '{note_text[:50]}...'")
    chunks = text_splitter.split_text(note_text)
    vector_store.add_texts(
        texts=chunks,
        metadatas=[{"source": source} for _ in chunks]
    )
    print(f"Successfully added {len(chunks)} chunks to memory.")

# --- 4. Main Application Loop ---

if __name__ == "__main__":
    speak("Cognitive Companion is online and ready.")
        
    while True:
        try:
            input("Press Enter to speak...")
            
            audio_file = record_audio()
            user_input = transcribe_audio(audio_file)
            if os.path.exists(audio_file):
                os.remove(audio_file)
            
            if user_input:
                intent = router_chain.invoke({"user_input": user_input})
                print(f"[Intent: {intent}]")

                if "QUERY" in intent:
                    answer = rag_chain.invoke(user_input)
                    speak(answer)
                elif "INGEST" in intent:
                    add_note_to_memory(user_input)
                    speak("Got it. I've saved that to my memory.")
                else:
                    speak("I'm not sure what you mean by that.")
            else:
                speak("Sorry, I didn't catch that.")

        except KeyboardInterrupt:
            print("\nShutting down...")
            speak("Goodbye.")
            break
        except Exception as e:
            print(f"An error occurred in the main loop: {e}")
            speak("I've hit an API limit. Please wait a moment and try again.")