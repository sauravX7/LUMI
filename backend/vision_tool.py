import os
import mss
import mss.tools
from PIL import Image
import google.generativeai as genai
from io import BytesIO

# Get API key
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# --- Initialize the Gemini Vision Model ---
# We use 'gemini-pro-vision' which is the old name, 
# The new 'gemini-flash-latest' or 'gemini-pro-latest'
# can also handle images. We'll use flash for speed.
try:
    vision_model = genai.GenerativeModel('gemini-flash-latest')
    print("Tool: Vision model loaded.")
except Exception as e:
    print(f"Error loading vision model: {e}")
    vision_model = None

def analyze_screen(user_query: str) -> str:
    """Captures the screen and uses Gemini Vision to describe it or answer a question."""
    if not vision_model:
        return "Sorry, the vision model isn't working right now."
        
    print("Tool: Capturing screen...")
    try:
        # 1. Capture the screen
        with mss.mss() as sct:
            # Get the first monitor
            monitor = sct.monitors[1] # 0 is all monitors, 1 is the primary
            sct_img = sct.grab(monitor)
            
            # 2. Convert to PIL Image
            img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)

        # 3. Ask Gemini Vision
        # The new genai library can take PIL Images directly
        prompt_parts = [
            f"You are a screen analysis assistant. A user has sent you this screenshot from their computer. Answer their question about it. User's question: '{user_query}'",
            img
        ]
        
        response = vision_model.generate_content(prompt_parts)
        
        return response.text
            
    except Exception as e:
        print(f"Vision Error: {e}")
        return "I encountered an error trying to see your screen."