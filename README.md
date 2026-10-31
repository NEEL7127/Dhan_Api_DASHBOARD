# NIFTY Data Tracker — Dhan API

A Streamlit dashboard that fetches NIFTY 50 Option Chain data (and optionally
the 50 constituent stocks) from the Dhan API, displays it with filters and
metrics, and exports to Excel.

**Read-only. No orders, ever.**

## Prerequisites

- **Python 3.12** (add to PATH during install)
- **Dhan Data API plan (₹499 + tax/month)** must be active
- A valid **Dhan Access Token** (24-hr) or **TOTP secret + PIN** for auto-refresh

## Setup

```bash
# 1. Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install packages
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Set credentials (pick one):
#    Option A: Copy .env.example -> .env, fill in your values
#    Option B: Run the app and use the Settings page
```

## Run

```bash
streamlit run app.py
```

Opens `http://localhost:8501` in your browser.

## Usage

1. Open the app → **Settings** → enter Client ID + (TOTP secret + PIN) or Access Token → **Save** → **Test connection** (should say OK).
2. Go to **Dashboard** → pick expiry/fields → view the option chain → **Download Excel**.

## Daily Token

- **With TOTP secret + PIN:** token auto-refreshes, nothing to do.
- **Without:** paste a fresh 24-hr token in Settings each day (web.dhan.co → My Profile → Access DhanHQ APIs).

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI: Dashboard + Settings pages |
| `config.py` | Non-secret constants (NIFTY=13/IDX_I, URLs) |
| `secrets_store.py` | Read/write dhan_secrets.json |
| `auth.py` | Token: manual OR TOTP auto-mint |
| `dhan_client.py` | API calls: expiries, option chain, quotes + rate-limit |
| `transform.py` | Raw JSON → tidy table; compute %chg, PCR, Buildup, ATM |
| `excel_export.py` | Build .xlsx from selected columns |
| `instruments.py` | (Dataset A) scrip-master → symbol:id map |

