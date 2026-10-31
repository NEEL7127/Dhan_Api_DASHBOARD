# NIFTY 50 Option Chain & Stocks Tracker (DhanHQ)

Live NIFTY 50 option chain and stock data from the DhanHQ v2 API, shown in a
Streamlit dashboard with selectable fields and one-click Excel export. Read-only
market data — it never places orders.

## Requirements
- Windows, Python 3.12 (python.org — tick "Add python.exe to PATH")
- A DhanHQ account with an ACTIVE Data API plan (Rs.499 + tax / month)
- Your Dhan Client ID and Access Token

## Run (Windows)
1. Install Python 3.12 (tick "Add python.exe to PATH").
2. Double-click **start.bat**. The first run installs everything (~1 min).
3. When the browser opens:
   - Go to **Settings**, enter your **Client ID** and **Access Token**
     (API Key / Secret optional), click **Save**, then **Test connection**
     (should say OK).
4. Go to **Dashboard** → choose Data Source (Option Chain or Nifty 50 Stocks),
   pick expiry / fields → view → **Download Excel**.

## Notes
- Each user needs their OWN Dhan credentials — none are stored in this repo.
- The access token expires every 24 hours; paste a fresh one in Settings
  (web.dhan.co → My Profile → Access DhanHQ APIs).
- Credentials are saved locally in `dhan_secrets.json` (git-ignored). Keep it private.
- "Test connection" failing with valid keys usually means the Data API plan isn't active.
