"""Diagnostic script to verify Groq API connectivity, list accessible models,

and test completion with the candidate models.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import dotenv

# Load .env explicitly from finguide directory
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if not ENV_PATH.exists():
    print(f"[FAIL] .env file not found at: {ENV_PATH}")
    sys.exit(1)

dotenv.load_dotenv(dotenv_path=ENV_PATH)

api_key = os.getenv("GROQ_API_KEY", "")
configured_model = os.getenv("GROQ_MODEL", "")

print("=" * 60)
print("Finbot Groq API Diagnostic Check")
print("=" * 60)

# Check API key presence without printing the value
if not api_key or not api_key.strip() or api_key == "your_groq_api_key_here":
    print("[FAIL] GROQ_API_KEY is missing or contains placeholder in .env")
    sys.exit(1)

masked_key = f"{api_key[:4]}...{api_key[-4:]} (length: {len(api_key)})"
print(f"[OK] GROQ_API_KEY detected: {masked_key}")
print(f"[INFO] Currently configured GROQ_MODEL in .env: '{configured_model}'")

try:
    from groq import Groq
except ImportError:
    print("[FAIL] groq package is not installed. Run 'pip install groq'.")
    sys.exit(1)

try:
    client = Groq(api_key=api_key.strip())
    print("[INFO] Querying Groq API for available models (client.models.list())...")
    models_response = client.models.list()
    available_models = sorted([m.id for m in models_response.data])
    active_models = sorted([m.id for m in models_response.data if getattr(m, 'active', True)])

    print(f"\n[OK] Successfully retrieved {len(available_models)} models from Groq API.")
    print("Accessible Models:")
    for model_id in available_models:
        is_active = "(active)" if model_id in active_models else ""
        print(f"  - {model_id} {is_active}")

except Exception as exc:
    print(f"\n[FAIL] Failed to list models from Groq API: {exc}")
    sys.exit(1)

# Now test candidate models
candidates_to_test = []
if configured_model:
    candidates_to_test.append(configured_model)
if "openai/gpt-oss-120b" not in candidates_to_test:
    candidates_to_test.append("openai/gpt-oss-120b")

# Also add popular fallback models from available_models
fallbacks = ["llama-3.1-8b-instant", "llama3-8b-8192", "mixtral-8x7b-32768", "gemma2-9b-it"]
for f in fallbacks:
    if f in available_models and f not in candidates_to_test:
        candidates_to_test.append(f)

print("\n" + "=" * 60)
print("Testing Candidate Models for Chat Completion")
print("=" * 60)

working_model = None

for model in candidates_to_test:
    print(f"\nTesting model: '{model}'...")
    if model not in available_models:
        print(f"  -> Model '{model}' is NOT present in available models list.")
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Respond with the single word 'OK'."}],
            max_tokens=10,
            temperature=0.0,
        )
        reply = (completion.choices[0].message.content or "").strip()
        print(f"  [SUCCESS] Model '{model}' responded successfully: '{reply}'")
        if not working_model:
            working_model = model
    except Exception as exc:
        print(f"  [ERROR] Model '{model}' failed: {exc}")

print("\n" + "=" * 60)
print(f"Diagnostic Summary: Working Model: {working_model}")
print("=" * 60)
