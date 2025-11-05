import os
import sys
from dotenv import load_dotenv, find_dotenv

# --- FIX: Load .env file *before* any other backend imports ---
load_dotenv(find_dotenv())
# --- END OF FIX ---

# --- Silence the Tokenizer Warning ---
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# ---

# --- Add root_dir to path ---
backend_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(backend_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)
# ---

# This line is no longer needed here
# load_dotenv(find_dotenv()) 

from flask import Flask, jsonify, request
import subprocess 
import time
import sounddevice as sd
import scipy.io.wavfile as wavfile
import google.generativeai as genai
import threading 
import shlex
import werkzeug.utils

# --- Now these imports will find the loaded environment variable ---
from backend import brain 
from backend import speak_tool
from backend import document_processor
# ---

# --- 1. Initialize Flask App ---
app = Flask(__name__)

# --- NEW: Upload Folder ---
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# ---

# --- 2. Load API Key & Configure ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file.")
genai.configure(api_key=GOOGLE_API_KEY)

# --- 3. Initialize AI Components ---
transcription_model = genai.GenerativeModel('gemini-flash-latest')

print("--- Server Initialized ---")

# --- 4. Define Core Functions ---

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

# --- NEW: Text Command Endpoint ---
@app.route('/text-command', methods=['POST'])
def handle_text_command():
    data = request.get_json()
    if not data or 'user_input' not in data:
        return jsonify({"status": "error", "message": "No input provided"})

    user_input = data['user_input']
    if not user_input:
        return jsonify({"status": "error", "message": "Empty input provided"})

    print(f"You (text): {user_input}")
    
    # We can reuse the exact same brain function
    response_object = brain.get_ai_response(user_input)
    response_object['user_text'] = user_input
    
    # Also speak the response
    threading.Thread(target=speak_tool.speak, args=(response_object["summary_text"],)).start()
    
    return jsonify(response_object)
# --- END OF NEW ENDPOINT ---

# --- NEW: Document Upload Endpoint ---
@app.route('/upload', methods=['POST'])
def handle_upload():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
    
    if file:
        filename = werkzeug.utils.secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        print(f"File saved to {filepath}")
        
        # Process the file and create the RAG chain
        message = document_processor.load_and_process_document(filepath)
        
        if "Error" in message:
            return jsonify({"status": "error", "message": message}), 500
        else:
            return jsonify({"status": "success", "filename": filename, "message": message})

# --- NEW: Document Q&A Endpoint ---
@app.route('/ask-document', methods=['POST'])
def handle_ask_document():
    data = request.get_json()
    if not data or 'user_input' not in data:
        return jsonify({"status": "error", "message": "No input provided"}), 400

    user_input = data['user_input']
    
    response_text = document_processor.ask_document_question(user_input)
    
    # Create a response object similar to the other endpoints
    response_object = {
        "full_text": response_text,
        "summary_text": response_text, # Doc answers are usually specific
        "user_text": user_input
    }
    
    # Also speak the response
    threading.Thread(target=speak_tool.speak, args=(response_object["summary_text"],)).start()
    
    return jsonify(response_object)


# --- 6. Run the Server ---
if __name__ == "__main__":
    print("Starting Flask server... (Speak 'online' message)")
    # Use the tool for the startup message
    threading.Thread(target=speak_tool.speak, args=("Lumi is online, here to help",)).start()
    app.run(port=5001, debug=False)