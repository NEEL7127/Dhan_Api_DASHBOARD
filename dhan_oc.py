import os
import time
import requests
import pandas as pd
import openpyxl
import xlwings as xw
import secrets_store
import auth
import transform
from config import BASE_URL, NIFTY_SCRIP, NIFTY_SEG

# --- WORKBOOK & CONFIGURATION ---
WORKBOOK_NAME = "OptionChain.xlsx"
WORKBOOK_PATH = os.path.abspath(WORKBOOK_NAME)

UNDERLYING = NIFTY_SCRIP  # 13 for NIFTY
SEGMENT = NIFTY_SEG       # "IDX_I"

def ensure_workbook_file():
    """Ensure OptionChain.xlsx exists on disk with Option Chain and Raw Data sheets."""
    if not os.path.exists(WORKBOOK_PATH):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Option Chain"
        wb.create_sheet(title="Raw Data")
        wb.save(WORKBOOK_PATH)

def get_headers():
    creds = secrets_store.load()
    token = auth.get_token() if hasattr(auth, "get_token") else creds.get("access_token", "")
    return {
        "access-token": token,
        "client-id": creds.get("client_id", ""),
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

def post(path, body, retries=3):
    url = f"{BASE_URL}{path}"
    for attempt in range(retries + 1):
        r = requests.post(url, json=body, headers=get_headers(), timeout=15)
        if r.status_code == 429 or (r.status_code == 200 and "Too many requests" in r.text):
            if attempt < retries:
                time.sleep(3.5)
                continue
        r.raise_for_status()
        return r.json()

def nearest_expiry():
    j = post("/optionchain/expirylist", {"UnderlyingScrip": UNDERLYING, "UnderlyingSeg": SEGMENT})
    d = j.get("data", j)
    return sorted(d)[0]

def get_sheets(wb):
    """Safely resolve Option Chain and Raw Data sheets in the workbook."""
    sheet_names = [s.name for s in wb.sheets]
    if "Option Chain" in sheet_names:
        sh1 = wb.sheets["Option Chain"]
    elif "Live Chain" in sheet_names:
        sh1 = wb.sheets["Live Chain"]
    else:
        sh1 = wb.sheets[0]

    if "Raw Data" in sheet_names:
        sh2 = wb.sheets["Raw Data"]
    else:
        sh2 = wb.sheets.add("Raw Data", after=sh1)

    return sh1, sh2

def main():
    print("=" * 60)
    print("DhanHQ Live Option Chain -> Excel Streamer (xlwings)")
    print(f"Target Workbook: {WORKBOOK_PATH}")
    print("Sheets: Option Chain (Computed) + Raw Data (All 35 API Columns)")
    print("=" * 60)

    ensure_workbook_file()

    try:
        expiry = nearest_expiry()
        print(f"Nearest Expiry detected: {expiry}")
    except Exception as e:
        print(f"Error fetching expiry list: {e}")
        return

    print("\nStreaming live option chain (Computed + Raw Data) to Excel every 3s. Press Ctrl+C to stop.\n")

    wb = None
    app = None
    iteration = 0

    while True:
        try:
            # 1. Connect or attach to OptionChain.xlsx safely
            need_connect = True
            if wb is not None:
                try:
                    _ = wb.name
                    need_connect = False
                except Exception:
                    wb = None

            if need_connect:
                for a in xw.apps:
                    try:
                        for b in a.books:
                            if b.name.lower() == WORKBOOK_NAME.lower():
                                wb = b
                                app = a
                                need_connect = False
                                break
                    except Exception:
                        continue
                    if not need_connect:
                        break

            if need_connect:
                app = xw.App(visible=True, add_book=False)
                wb = app.books.open(WORKBOOK_PATH)

            sh_chain, sh_raw = get_sheets(wb)

            # 2. Fetch chain data
            full_json = post("/optionchain", {
                "UnderlyingScrip": UNDERLYING,
                "UnderlyingSeg": SEGMENT,
                "Expiry": expiry
            })

            # 3. Build both tables: computed and full 35-column raw table
            df_comp, m = transform.build_chain_table(full_json, strikes_around_atm=25)
            df_raw, _ = transform.build_raw_chain_table(full_json, strikes_around_atm=25)

            now = time.strftime("%H:%M:%S")
            spot = m.get("underlying", "")

            # --- Update Sheet 1: Option Chain ---
            sh_chain.range("A1").value = f"Expiry: {expiry}"
            sh_chain.range("A1").font.bold = True
            sh_chain.range("C1").value = f"Spot LTP: {spot}"
            sh_chain.range("C1").font.bold = True
            sh_chain.range("E1").value = f"Last Updated: {now}"
            sh_chain.range("E1").font.bold = True
            sh_chain.range("G1").value = f"PCR: {round(m.get('pcr_overall', 0), 2)}"

            comp_cols = [c for c in df_comp.columns if not c.startswith("_")]
            nrows_comp = len(df_comp)
            sh_chain.range((3, 1), (3, len(comp_cols))).value = comp_cols
            sh_chain.range((3, 1), (3, len(comp_cols))).font.bold = True
            sh_chain.range((3, 1), (3, len(comp_cols))).color = (220, 220, 220)
            sh_chain.range((4, 1), (3 + nrows_comp, len(comp_cols))).value = df_comp[comp_cols].values

            # --- Update Sheet 2: Raw Data (All 35 API columns) ---
            raw_cols = [c for c in df_raw.columns if not c.startswith("_")]
            nrows_raw = len(df_raw)
            sh_raw.range((1, 1), (1, len(raw_cols))).value = raw_cols
            sh_raw.range((1, 1), (1, len(raw_cols))).font.bold = True
            sh_raw.range((2, 1), (1 + nrows_raw, len(raw_cols))).value = df_raw[raw_cols].values

            iteration += 1
            print(f"[{now}] Tick #{iteration} | Spot: {spot} | Strikes: {nrows_comp} | Live Updated (Option Chain + Raw Data)")

        except Exception as e:
            now = time.strftime("%H:%M:%S")
            print(f"[{now}] Error updating Excel: {e}")
            # Reset handles on COM or detachment errors so next tick reconnects cleanly
            wb = None
            app = None

        time.sleep(3)

if __name__ == "__main__":
    main()
