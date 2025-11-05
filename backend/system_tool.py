import os
import sys
import subprocess
import threading
import json
import shlex
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from backend import speak_tool 

# Get API key
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# This LLM is *only* for parsing commands
# --- FIX: Added 'google_api_key=GOOGLE_API_KEY' back in ---
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

# --- Define the tool function ---
def execute_system_command(user_input: str) -> str:
    """Parses and executes a safe system command."""
    print(f"Tool: Received system command: '{user_input}'")

    # 1. Parse the command (unchanged)
    parser_prompt = f"""
    Parse the user's command into a JSON object.
    The only valid commands are 'open_app' and 'set_timer'.
    ... (rest of prompt is the same) ...
    User: "{user_input}" ->
    """
    
    try:
        response = parser_llm.invoke(parser_prompt)
        # --- FIX: Use .content to get string from AI Message ---
        json_str = response.content.strip().replace("`", "").replace("json", "")
        # ---
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

    else:
        return "I can't perform that system command. I can only open apps and set timers."