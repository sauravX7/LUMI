import os
import sys
import subprocess
import threading
import json
import shlex
import webbrowser  # For opening URLs
import urllib.parse 
import time
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from backend import speak_tool 

# --- Import Spotipy ---
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Get API key
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# This LLM is *only* for parsing commands
parser_llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0, google_api_key=GOOGLE_API_KEY)

# --- App Map (unchanged) ---
APP_MAP = {
    "chrome": "Google Chrome",
    "vscode": "Visual Studio Code",
    "spotify": "Spotify",
    "textedit": "TextEdit",
    "notes": "Notes",
    "terminal": "Terminal"
}

# --- Initialize Spotipy Client ---
try:
    SCOPE = "user-modify-playback-state user-read-playback-state"
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.environ.get("SPOTIPY_CLIENT_ID"),
        client_secret=os.environ.get("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.environ.get("SPOTIPY_REDIRECT_URI"),
        scope=SCOPE
    ))
    sp.devices()
    print("Tool: Spotipy client initialized successfully.")
except Exception as e:
    print(f"Tool: Spotipy client FAILED to initialize: {e}")
    sp = None

# --- Helper function for AppleScript (Kept for other functions) ---
def run_applescript(script: str):
    """
    Executes a given AppleScript command.
    Returns (True, "Success") on success.
    Returns (False, "Error message") on failure.
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", script], 
            check=True, 
            capture_output=True, 
            text=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"AppleScript Error: {e.stderr}")
        return False, e.stderr
    except FileNotFoundError:
        print("Error: 'osascript' command not found. This tool only works on macOS.")
        return False, "osascript command not found."

# --- NEW HELPER: Check if app is running via shell ---
def is_app_running_check(app_name: str) -> bool:
    """Checks if the given application name is currently running."""
    try:
        # 'pgrep' checks for process IDs by name
        subprocess.run(['pgrep', '-x', app_name], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False

# --- Main Tool Function ---
def execute_system_command(user_input: str) -> str:
    """Parses and executes a safe system command."""
    print(f"Tool: Received system command: '{user_input}'")

    # 1. Parse the command
    parser_prompt = f"""
    You are an AI assistant that parses a user's natural language command into a
    structured JSON object. You can only perform a few actions: 'open_app', 'timer',
    'open_website', and 'play_spotify'.

    - 'open_app': Opens a locally installed application.
      - Requires: 'app_name' (e.g., "chrome", "vscode", "spotify").
    - 'timer': Sets a timer.
      - Requires: 'duration' in seconds.
    - 'open_website': Opens a URL in the default browser.
      - Requires: 'url' (e.g., "https://google.com").
    - 'play_spotify': Plays music on Spotify.
      - Requires: 'song_name' (e.g., "Bohemian Rhapsody").
      - Optional: 'artist_name' (e.g., "Queen").

    If the command is not one of these, or if it's too complex (like 'close this app'),
    respond with {{"command": "unrecognized"}}.

    Examples:
    User: "Open Chrome" ->
    {{ "command": "open_app", "app_name": "chrome" }}
    
    User: "Set a timer for 5 minutes" ->
    {{ "command": "timer", "duration": 300 }}

    User: "Open google.com" ->
    {{ "command": "open_website", "url": "https://google.com" }}

    User: "Open Chrome and go to youtube.com" ->
    {{ "command": "open_website", "url": "https://youtube.com" }}
    
    User: "Play Bohemian Rhapsody on Spotify" ->
    {{ "command": "play_spotify", "song_name": "Bohemian Rhapsody" }}
    
    User: "Play smells like teen spirit by nirvana" ->
    {{ "command": "play_spotify", "song_name": "smells like teen spirit", "artist_name": "nirvana" }}

    User: "What's the weather?" ->
    {{ "command": "unrecognized", "reason": "Cannot get weather" }}

    User: "Close Chrome" ->
    {{ "command": "unrecognized", "reason": "Cannot close apps" }}

    User: "{user_input}" ->
    """
    
    try:
        response = parser_llm.invoke(parser_prompt)
        raw_content = response.content
        if isinstance(raw_content, list):
            raw_content = ' '.join(map(str, raw_content))
        
        json_str = str(raw_content).strip().replace("`", "").replace("json", "")
        print(f"LLM Parser output: {json_str}")
        command_data = json.loads(json_str)
        command = command_data.get("command")
    except Exception as e:
        print(f"Error parsing command: {e}")
        return "I had trouble understanding that command."

    # 2. Safely execute the parsed command
    if command == "open_app":
        app_name_alias = command_data.get("app_name")
        if not app_name_alias:
            return "You need to tell me which app to open."
        
        app_name_real = APP_MAP.get(app_name_alias.lower(), app_name_alias)
        
        print(f"Executing: open -a '{app_name_real}'")
        try:
            subprocess.run(["open", "-a", app_name_real], check=True)
            return f"Opening {app_name_real}."
        except Exception as e:
            print(e)
            return f"I couldn't find an app named {app_name_real}."

    elif command == "timer":
        duration = command_data.get("duration")
        if not duration or not isinstance(duration, int):
            return "You need to tell me how long the timer should be."
        
        def timer_finished(seconds):
            text = f"Timer complete. Your {seconds} seconds are up."
            print(f"TIMER: {text}")
            speak_tool.speak(text)
        
        threading.Timer(duration, timer_finished, args=[duration]).start()
        print(f"Executing: Timer for {duration} seconds")
        return f"OK, timer set for {duration} seconds."

    elif command == "open_website":
        url = command_data.get("url")
        if not url:
            return "You need to tell me what website to open."
        
        print(f"Executing: webbrowser.open('{url}')")
        webbrowser.open(url)
        return f"Opening {url}."

    # --- UPDATED: 'play_spotify' (Final Focus-Safe Hybrid) ---
    elif command == "play_spotify":
        if sp is None:
            return "Sorry, the Spotify service isn't connected. Please check the server."
            
        song = command_data.get("song_name")
        artist = command_data.get("artist_name")
        
        if not song:
            return "You need to tell me what song to play."
        
        # Build a search query for the API
        search_query = song
        if artist:
            search_query += f" artist:{artist}"
        
        try:
            # 1. Check if Spotify is running and launch silently if needed
            if not is_app_running_check("Spotify"):
                # If closed, use 'open -g' for a silent launch
                print("Executing: open -a Spotify -g (Silent Launch)")
                try:
                    subprocess.run(["open", "-a", "Spotify", "-g"], check=True)
                    time.sleep(7) # <-- FIX: EXTENDED DELAY
                except Exception as e:
                    print(f"Silent Launch Error: {e}")
                    # If launch fails, we let the API call fail below and return the original error.
                    pass 
            else:
                print("Spotify process already running. Proceeding to API play.")
                
            # 2. Use API to find the song URI
            results = sp.search(q=search_query, limit=1, type='track')
            tracks = results['tracks']['items']
            
            if not tracks:
                return f"Sorry, I couldn't find a song called {song}."
            
            # 3. Get the Track URI (its official ID)
            track_uri = tracks[0]['uri']
            
            # 4. Play the track URI using the API (Reliable Playback)
            print(f"Telling Spotify API to play URI: {track_uri}")
            sp.start_playback(uris=[track_uri])
            
            if artist:
                return f"Playing {song} by {artist} on Spotify."
            else:
                return f"Playing {song} on Spotify."

        except Exception as e:
            print(f"Spotify API Error: {e}")
            error_message = str(e).strip().splitlines()[-1]
            if "No active device found" in str(e):
                return "I played the song, but there was no active device. Please check your Spotify Connect settings."
            return f"I couldn't play that. The system reported: {error_message}"

    else:
        # This is the "unrecognized" or failed block
        return "I can't perform that system command. I'm limited to opening apps, opening websites, setting timers, and playing music on Spotify."