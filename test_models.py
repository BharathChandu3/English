import requests
import os
from dotenv import load_dotenv

load_dotenv()

key = os.environ.get("GEMINI_API_KEY", "")
models = [
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
]
base = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
payload = {
    "contents": [{"role": "user", "parts": [{"text": "Reply with just the word: OK"}]}],
    "generationConfig": {"maxOutputTokens": 10}
}

print("=" * 50)
print("  SPEAKMATE AI - Model Availability Test")
print("=" * 50)

first_working = None
for m in models:
    url = f"{base.format(model=m)}?key={key}"
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 200:
            reply = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            print(f"[PASS] {m:35s} -> '{reply}'")
            if not first_working:
                first_working = m
        elif r.status_code == 429:
            print(f"[RATE] {m:35s} -> 429 Rate Limited (quota exhausted)")
        elif r.status_code == 404:
            print(f"[MISS] {m:35s} -> 404 Not found / unavailable")
        else:
            print(f"[FAIL] {m:35s} -> HTTP {r.status_code}")
    except Exception as e:
        print(f"[ERR ] {m:35s} -> {e}")

print("=" * 50)
if first_working:
    print(f"  Best model to use: {first_working}")
else:
    print("  No models available right now. Check your API key or try later.")
print("=" * 50)
