import csv, io, json, os, requests
SCRIP_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"
CACHE = "nifty50_symbols.json"

def build_map(nifty_symbols):
    """Map the 50 Nifty symbols -> Dhan security ids from the scrip master."""
    rows = list(csv.DictReader(io.StringIO(requests.get(SCRIP_URL, timeout=30).text)))
    # [CONFIRM ON 1ST CALL] exact column names by printing rows[0].keys()
    out = {}
    for r in rows:
        if r.get("SEM_EXM_EXCH_ID") == "NSE" and r.get("SEM_SEGMENT") == "E":
            sym = r.get("SEM_TRADING_SYMBOL", "")
            if sym in nifty_symbols:
                out[sym] = int(r["SEM_SMST_SECURITY_ID"])
    json.dump(out, open(CACHE, "w"), indent=2)
    return out

