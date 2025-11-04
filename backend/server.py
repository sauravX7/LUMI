import os
import sys
from dotenv import load_dotenv, find_dotenv

# --- Silence the Tokenizer Warning ---
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# ---

# --- Add root_dir to path ---
backend_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(backend_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)
# ---

load_dotenv(find_dotenv())

from flask import Flask, jsonify, request
import subprocess 
import time
import sounddevice as sd
import scipy.io.wavfile as wavfile
import google.generativeai as genai
import threading 
import shlex

from backend import brain 
# --- NEW: Import the speak tool ---
from backend import speak_tool
# ---

# --- 1. Initialize Flask App ---
app = Flask(__name__)

# --- 2. Load API Key & Configure ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file.")
genai.configure(api_key=GOOGLE_API_KEY)

# --- 3. Initialize AI Components ---
transcription_model = genai.GenerativeModel('gemini-flash-latest')

print("--- Server Initialized ---")

# --- 4. Define Core Functions ---

# --- The 'speak' function is GONE from server.py ---

def record_and_transcribe(filename="temp_audio.wav", duration=5, fs=44100):
    print("Recording...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    wavfile.write(filename, fs, recording)
    print("Recording finished. Transcribing...")

    try:
        audio_file = genai.upload_file(path=filename)
        while audio_file.state.name == "PROCESSING":
            time.sleep(1)
            audio_file = genai.get_file(audio_file.name)
        
        response = transcription_model.generate_content([
            "Transcribe this audio clip.",
            audio_file
        ])
        genai.delete_file(audio_file.name)
        os.remove(filename)
        
        return response.text if response.text else None
    except Exception as e:
        print(f"Error during transcription: {e}")
        if os.path.exists(filename):
            os.remove(filename)
        return None

# --- 5. Create the API Endpoint (Updated) ---
@app.route('/listen', methods=['POST'])
def handle_listen():
    user_input = record_and_transcribe()
    if not user_input:
        speak_tool.speak("Sorry, I didn't catch that.")
        return jsonify({"status": "error", "message": "No input detected", "user_text": ""})

    print(f"You: {user_input}")
    
    response_object = brain.get_ai_response(user_input)
    response_object['user_text'] = user_input
    
    # --- NEW: Use the speak tool ---
    # We run this in a thread so the server can respond to the UI *while* speaking.
    threading.Thread(target=speak_tool.speak, args=(response_object["summary_text"],)).start()
    
    return jsonify(response_object)

# --- 6. Run the Server ---
if __name__ == "__main__":
    print("Starting Flask server... (Speak 'online' message)")
    # Use the tool for the startup message
    threading.Thread(target=speak_tool.speak, args=("Lumi is online, here to help",)).start()
    app.run(port=5001, debug=False)