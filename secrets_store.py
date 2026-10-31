import json, os
from dotenv import load_dotenv
from config import SECRETS_FILE, CRED_FIELDS

load_dotenv()  # read .env if present

def _from_env():
    # map env var names to our keys
    env_map = {
        "client_id": "DHAN_CLIENT_ID",
        "access_token": "DHAN_ACCESS_TOKEN",
        "api_key": "DHAN_API_KEY",
        "api_secret": "DHAN_API_SECRET",
        "totp_secret": "DHAN_TOTP_SECRET",
        "pin": "DHAN_PIN",
    }
    return {k: (os.getenv(v) or "") for k, v in env_map.items()}

def load() -> dict:
    """Return the current credentials. Seeds from .env on first run."""
    if os.path.exists(SECRETS_FILE):
        with open(SECRETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = _from_env()
        save(data)
    # ensure every field exists
    for k in CRED_FIELDS:
        data.setdefault(k, "")
    return data

def save(data: dict) -> None:
    clean = {k: (data.get(k) or "").strip() for k in CRED_FIELDS}
    with open(SECRETS_FILE, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2)

def mask(value: str) -> str:
    if not value:
        return "(not set)"
    return "•" * max(0, len(value) - 4) + value[-4:]

