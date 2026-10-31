import os
import time
import requests
import pandas as pd
import openpyxl
import xlwings as xw
import secrets_store
from config import BASE_URL, NIFTY_SCRIP, NIFTY_SEG

# --- WORKBOOK & CONFIGURATION ---
WORKBOOK_NAME = "OptionChain.xlsx"
WORKBOOK_PATH = os.path.abspath(WORKBOOK_NAME)

UNDERLYING = NIFTY_SCRIP  # 13 for NIFTY
SEGMENT = NIFTY_SEG       # "IDX_I"

def ensure_workbook_file():
    """Ensure OptionChain.xlsx exists on disk so Excel opens it cleanly."""
    if not os.path.exists(WORKBOOK_PATH):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Live Chain"
        wb.save(WORKBOOK_PATH)

def get_headers():
    creds = secrets_store.load()
    return {
        "access-token": creds.get("access_token", ""),
        "client-id": creds.get("client_id", ""),
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

def post(path, body):
    url = f"{BASE_URL}{path}"
    r = requests.post(url, json=body, headers=get_headers(), timeout=15)
    r.raise_for_status()
    j = r.json()
    return j.get("data", j)

def nearest_expiry():
    d = post("/optionchain/expirylist", {"UnderlyingScrip": UNDERLYING, "UnderlyingSeg": SEGMENT})
    return sorted(d)[0]

def chain_df(expiry):
    d = post("/optionchain", {"UnderlyingScrip": UNDERLYING, "UnderlyingSeg": SEGMENT, "Expiry": expiry})
    rows = []
    for strike, leg in d["oc"].items():
        row = {"Strike": float(strike)}
        for side in ("ce", "pe"):
            x = leg.get(side) or {}
            g = x.get("greeks", {}) or {}
            p = side.upper()
            row.update({
                f"{p} LTP": x.get("last_price", 0.0),
                f"{p} OI": x.get("oi", 0),
                f"{p} PrevOI": x.get("previous_oi", 0),
                f"{p} Vol": x.get("volume", 0),
                f"{p} IV": x.get("implied_volatility", 0.0),
                f"{p} Delta": g.get("delta", 0.0),
                f"{p} Theta": g.get("theta", 0.0),
                f"{p} Gamma": g.get("gamma", 0.0),
                f"{p} Vega": g.get("vega", 0.0),
                f"{p} Bid": x.get("top_bid_price", 0.0),
                f"{p} Ask": x.get("top_ask_price", 0.0),
            })
        rows.append(row)

    df = pd.DataFrame(rows).sort_values("Strike").reset_index(drop=True)
    ce_cols = [c for c in df.columns if c.startswith("CE")]
    pe_cols = [c for c in df.columns if c.startswith("PE")]
    cols = ce_cols + ["Strike"] + pe_cols
    return df[cols], d.get("last_price")

def main():
    print("=" * 60)
    print("DhanHQ Live Option Chain -> Excel Streamer (xlwings)")
    print(f"Target Workbook: {WORKBOOK_PATH}")
    print("=" * 60)

    ensure_workbook_file()

    # Launch Excel and attach/open OptionChain.xlsx
    app = xw.App(visible=True, add_book=False)
    try:
        wb = xw.Book(WORKBOOK_PATH)
    except Exception:
        wb = app.books.open(WORKBOOK_PATH)

    sh = wb.sheets[0]
    sh.name = "Live Chain"

    try:
        expiry = nearest_expiry()
        print(f"Nearest Expiry detected: {expiry}")
    except Exception as e:
        print(f"Error fetching expiry list: {e}")
        return

    print("\nStreaming live option chain to Excel every 3-5 seconds. Press Ctrl+C to stop.\n")

    iteration = 0
    while True:
        try:
            df, spot = chain_df(expiry)
            now = time.strftime("%H:%M:%S")

            # Header info
            sh.range("A1").value = f"Expiry: {expiry}"
            sh.range("A1").font.bold = True
            sh.range("C1").value = f"Spot LTP: {spot}"
            sh.range("C1").font.bold = True
            sh.range("E1").value = f"Last Updated: {now}"
            sh.range("G1").value = ""  # Clear previous errors

            # Write DataFrame table directly into Excel
            sh.range("A3").options(index=False).value = df
            
            # Format header row
            sh.range((3, 1), (3, len(df.columns))).font.bold = True
            sh.range((3, 1), (3, len(df.columns))).color = (220, 220, 220)

            iteration += 1
            print(f"[{now}] Tick #{iteration} | Spot: {spot} | Strikes: {len(df)} pushed to Excel")

        except Exception as e:
            now = time.strftime("%H:%M:%S")
            print(f"[{now}] Error updating Excel: {e}")
            try:
                sh.range("G1").value = f"Error: {e}"
            except Exception:
                pass

        time.sleep(3)  # Respect Dhan 3-second option chain rate limit

if __name__ == "__main__":
    main()

