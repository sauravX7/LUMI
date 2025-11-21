import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

# Load the keys we just added to .env
load_dotenv()

# This scope is what allows LUMI to control playback
SCOPE = "user-modify-playback-state user-read-playback-state"

print("--- Starting Spotify Authorization ---")

try:
    sp_oauth = SpotifyOAuth(
        scope=SCOPE,
        client_id=os.environ.get("SPOTIPY_CLIENT_ID"),
        client_secret=os.environ.get("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.environ.get("SPOTIPY_REDIRECT_URI")
    )

    # This will get a cached token or prompt you to log in
    token_info = sp_oauth.get_access_token()

    if token_info:
        print("\n--- SUCCESS! ---")
        print("Authorization successful.")
        print("A new file named '.cache' has been created.")
        print("You can now close this script and restart the main server.")
    else:
        print("Error: Could not get token.")

except Exception as e:
    print(f"\n--- ERROR ---")
    print(f"An error occurred: {e}")
    print("\nPlease check your SPOTIPY variables in the .env file and ensure your Redirect URI matches the Spotify Dashboard.")