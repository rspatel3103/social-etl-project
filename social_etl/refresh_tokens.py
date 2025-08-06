import requests
import json
from datetime import datetime

APP_CREDENTIALS = {
    'instagram': {
        'app_id': '1374937216940994',
        'app_secret': 'aab85f9c90d65b82209067a5f3c2c9eb'
    },
    'facebook': {
        'app_id': '1374937216940994',
        'app_secret': 'aab85f9c90d65b82209067a5f3c2c9eb'
    }
}

TOKENS_PATH = 'config/tokens.json'

def refresh_token(platform: str):
    with open(TOKENS_PATH, 'r') as f:
        tokens = json.load(f)

    current_token = tokens[platform]['access_token']
    creds = APP_CREDENTIALS[platform]

    url = (
        "https://graph.facebook.com/v18.0/oauth/access_token"
        f"?grant_type=fb_exchange_token"
        f"&client_id={creds['app_id']}"
        f"&client_secret={creds['app_secret']}"
        f"&fb_exchange_token={current_token}"
    )

    response = requests.get(url)
    data = response.json()

    if 'access_token' in data:
        tokens[platform]['access_token'] = data['access_token']
        tokens[platform]['refreshed_at'] = datetime.utcnow().isoformat()

        with open(TOKENS_PATH, 'w') as f:
            json.dump(tokens, f, indent=2)

        print(f"✅ {platform} token refreshed.")
    else:
        print(f"❌ Failed to refresh {platform} token: {data}")

if __name__ == "__main__":
    for platform in ['instagram', 'facebook']:
        refresh_token(platform)
