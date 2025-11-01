import os       # <-- ADDED
import sys
import subprocess
import threading
import json
import shlex    # <-- ADDED
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

# Get API key
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# This LLM is *only* for parsing commands
parser_llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0, google_api_key=GOOGLE_API_KEY)


# --- THIS IS THE FIX ---
# A dictionary to map common aliases to their exact macOS app names
APP_MAP = {
    "chrome": "Google Chrome",
    "vscode": "Visual Studio Code",
    "spotify": "Spotify",
    "textedit": "TextEdit",
    "notes": "Notes",
    "terminal": "Terminal"
    # Add more apps here as you like
}
# --- END OF FIX ---


# --- Define the tool function ---

def execute_system_command(user_input: str) -> str:
    """Parses and executes a safe system command."""
    print(f"Tool: Received system command: '{user_input}'")

    # 1. Use an LLM to parse the command into structured JSON
    parser_prompt = f"""
    Parse the user's command into a JSON object.
    The only valid commands are 'open_app' and 'set_timer'.
    The 'open_app' command requires an 'app_name' (e.g., "Chrome", "Spotify", "TextEdit").
    The 'set_timer' command requires a 'duration' in seconds.
    
    If the command is not one of these, return {{"command": "unknown"}}.

    Examples:
    User: "Open Chrome" -> {{"command": "open_app", "app_name": "Chrome"}}
    User: "Hey, can you open Spotify" -> {{"command": "open_app", "app_name": "Spotify"}}
    User: "Set a timer for 20 seconds" -> {{"command": "timer", "duration": 20}}
    User: "Delete all my files" -> {{"command": "unknown"}}
    User: "Set a 1 minute timer" -> {{"command": "timer", "duration": 60}}
    
    User: "{user_input}" ->
    """
    
    try:
        response = parser_llm.invoke(parser_prompt)
        print(f"LLM Parser output: {response.content}")
        # Clean the response to be valid JSON
        json_str = response.content.strip().replace("`", "").replace("json", "")
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
            # --- THIS IS THE FIX ---
            # Use the 'say' command to give a voice alert
            sanitized_text = shlex.quote(text)
            os.system(f"say {sanitized_text}")
            # --- END OF FIX ---
        
        threading.Timer(duration, timer_finished, args=[duration]).start()
        print(f"Executing: Timer for {duration} seconds")
        return f"OK, timer set for {duration} seconds."

    else:
        return "I can't perform that system command. I can only open apps and set timers."