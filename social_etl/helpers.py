# helpers.py
import json

def get_access_token(platform: str, path="config/tokens.json") -> str:
    with open(path, "r") as f:
        tokens = json.load(f)
    return tokens[platform]["access_token"]
