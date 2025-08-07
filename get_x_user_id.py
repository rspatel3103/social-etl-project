import requests
import os
from dotenv import load_dotenv

load_dotenv()  # ensure .env is loaded

BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")
USERNAME = "simpkinstem_"

headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}

url = f"https://api.twitter.com/2/users/by/username/{USERNAME}"
params = {"user.fields": "id"}

response = requests.get(url, headers=headers, params=params)
print(response.status_code)
print(response.json())
