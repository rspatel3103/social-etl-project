import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

APP_CREDENTIALS = {
    'instagram': {
        'app_id': os.getenv("INSTAGRAM_APP_ID"),
        'app_secret': os.getenv("INSTAGRAM_APP_SECRET")
    },
    'facebook': {
        'app_id': os.getenv("FACEBOOK_APP_ID"),
        'app_secret': os.getenv("FACEBOOK_APP_SECRET")
    }
}

# Resolve paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TOKENS_PATH = os.path.join(BASE_DIR, 'config', 'tokens.json')

def get_access_token(platform: str, path=TOKENS_PATH) -> str:
    with open(path, "r") as f:
        tokens = json.load(f)
    return tokens[platform]["access_token"]

def should_refresh(refreshed_at_str):
    try:
        last_refresh = datetime.fromisoformat(refreshed_at_str.replace("Z", ""))
        return datetime.utcnow() - last_refresh > timedelta(days=0)
    except Exception:
        return True

def refresh_if_needed():
    with open(TOKENS_PATH, 'r') as f:
        tokens = json.load(f)

    for platform in ['instagram', 'facebook']:
        refreshed_at = tokens[platform].get('refreshed_at', '1970-01-01T00:00:00Z')

        if should_refresh(refreshed_at):
            creds = APP_CREDENTIALS[platform]
            current_token = tokens[platform]['access_token']

            response = requests.get(
                "https://graph.facebook.com/v18.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": creds['app_id'],
                    "client_secret": creds['app_secret'],
                    "fb_exchange_token": current_token,
                }
            )

            data = response.json()
            if 'access_token' in data:
                tokens[platform]['access_token'] = data['access_token']
                tokens[platform]['refreshed_at'] = datetime.utcnow().isoformat() + "Z"
                print(f"[OK] Refreshed {platform} token.")
            else:
                print(f"[ERROR] Failed to refresh {platform}: {data}")
        else:
            print(f"[SKIP] {platform} token still fresh.")

    with open(TOKENS_PATH, 'w') as f:
        json.dump(tokens, f, indent=2)
