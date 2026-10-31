import time, requests, pyotp
from config import AUTH_URL
import secrets_store

_cache = {"token": None, "ts": 0}
_TTL = 23 * 3600  # refresh a bit before the 24h expiry

def get_token() -> str:
    """Return a valid access token. TOTP auto-mint if configured, else manual token."""
    creds = secrets_store.load()

    # Option 2: auto-mint with TOTP (fully headless)
    if creds.get("totp_secret") and creds.get("pin") and creds.get("client_id"):
        now = time.time()
        if _cache["token"] and (now - _cache["ts"] < _TTL):
            return _cache["token"]
        otp = pyotp.TOTP(creds["totp_secret"]).now()
        # [CONFIRM ON 1ST CALL] exact param + response field names
        r = requests.post(AUTH_URL, params={
            "dhanClientId": creds["client_id"],
            "pin": creds["pin"],
            "totp": otp,
        }, timeout=15)
        r.raise_for_status()
        payload = r.json()
        token = (payload.get("accessToken") or payload.get("access_token")
                 or (payload.get("data") or {}).get("accessToken"))
        if not token:
            raise RuntimeError(f"No token in auth response: {r.text[:200]}")
        _cache.update(token=token, ts=now)
        return token

    # Option 1: manual token from Settings/.env
    if creds.get("access_token"):
        return creds["access_token"]

    raise RuntimeError("No credentials. Open Settings and set a token (or TOTP + PIN).")

