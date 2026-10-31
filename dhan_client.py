import time, requests
from config import BASE_URL, NIFTY_SCRIP, NIFTY_SEG
import secrets_store, auth

_last_call = {"t": 0.0}

def _throttle(min_gap=3.1):
    """Option-chain limit is 1 req / 3s. Sleep if we're too fast."""
    wait = min_gap - (time.time() - _last_call["t"])
    if wait > 0:
        time.sleep(wait)
    _last_call["t"] = time.time()

def _headers():
    creds = secrets_store.load()
    return {
        "access-token": auth.get_token(),
        "client-id": creds["client_id"],
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def _post(path, body, throttle=True):
    if throttle:
        _throttle()
    r = requests.post(f"{BASE_URL}{path}", json=body, headers=_headers(), timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"Dhan {path} HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    if data.get("status") not in (None, "success"):
        raise RuntimeError(f"Dhan {path} status={data.get('status')}: {str(data)[:300]}")
    return data

def get_expiries():
    body = {"UnderlyingScrip": NIFTY_SCRIP, "UnderlyingSeg": NIFTY_SEG}
    return _post("/optionchain/expirylist", body, throttle=True)["data"]

def get_option_chain(expiry):
    body = {"UnderlyingScrip": NIFTY_SCRIP, "UnderlyingSeg": NIFTY_SEG, "Expiry": expiry}
    return _post("/optionchain", body, throttle=True)

def get_quotes(security_ids):
    # Market Quote limit is 1 req/sec; use its own short throttle
    body = {"NSE_EQ": [int(s) for s in security_ids]}
    return _post("/marketfeed/quote", body, throttle=False)

