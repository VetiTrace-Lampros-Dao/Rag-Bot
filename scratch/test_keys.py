import os
import sys
from dotenv import load_dotenv
from google import genai

load_dotenv()

keys_str = os.getenv("GEMINI_API_KEYS", "")
keys = [k.strip() for k in keys_str.split(",") if k.strip()]

print(f"Testing {len(keys)} API keys...")

for i, key in enumerate(keys):
    client = genai.Client(api_key=key)
    try:
        # Simple list models call to verify authentication
        client.models.list()
        print(f"Key {i} (starts with {key[:15]}...): VALID (Authentication OK)")
    except Exception as e:
        print(f"Key {i} (starts with {key[:15]}...): INVALID - {e}")
