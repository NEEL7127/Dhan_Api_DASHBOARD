# Non-secret constants only. No credentials here.
BASE_URL = "https://api.dhan.co/v2"
AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"

# NIFTY 50 index underlying (CONFIRMED via official DhanHQ-py README)
NIFTY_SCRIP = 13
NIFTY_SEG = "IDX_I"

SECRETS_FILE = "dhan_secrets.json"

# Credential keys the app manages (name -> is_secret, for masking in the UI)
CRED_FIELDS = {
    "client_id": False,
    "access_token": True,
    "api_key": True,
    "api_secret": True,
    "totp_secret": True,
    "pin": True,
}

