import subprocess
import shlex

def speak(text_to_speak: str):
    """
    Uses the Mac's 'say' command to speak text.
    This is robust and blocks until speech is done.
    """
    print(f"Companion: {text_to_speak}")
    try:
        # Sanitize text for the command line
        sanitized_text = text_to_speak.replace('\n', ' ')
        
        # Use subprocess.run() to wait for the command to complete
        subprocess.run(["say", sanitized_text], check=True)
    except Exception as e:
        print(f"Error in 'say' command playback: {e}")