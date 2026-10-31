import csv, io, json, os, requests

NSE_LIST_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv"
SCRIP_URL    = "https://images.dhan.co/api-data/api-scrip-master.csv"
SYMBOLS_CACHE = "nifty50_symbols.json"   # fallback list
IDMAP_CACHE   = "nifty50_ids.json"       # symbol -> security_id

def fetch_nifty50_symbols():
    """Official NSE Nifty 50 symbols. Falls back to cached JSON if the download fails."""
    try:
        r = requests.get(NSE_LIST_URL, timeout=30,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        rows = list(csv.DictReader(io.StringIO(r.text)))
        syms = [row["Symbol"].strip() for row in rows if row.get("Symbol")]
        if len(syms) >= 45:                     # sanity check
            json.dump(syms, open(SYMBOLS_CACHE, "w"), indent=2)
            return syms
    except Exception as e:
        print("NSE list download failed, using cache:", e)
    if os.path.exists(SYMBOLS_CACHE):
        return json.load(open(SYMBOLS_CACHE))
    raise RuntimeError("No Nifty 50 symbol list available (download failed, no cache).")

def build_id_map(symbols):
    """Map each Nifty 50 symbol -> Dhan NSE equity security id, from the scrip master."""
    if os.path.exists(IDMAP_CACHE):
        cached = json.load(open(IDMAP_CACHE))
        if all(s in cached for s in symbols):
            return cached
    rows = list(csv.DictReader(io.StringIO(
        requests.get(SCRIP_URL, timeout=60).text)))
    # [CONFIRM ON 1ST CALL] print(rows[0].keys()) once to verify these column names:
    out = {}
    wanted = set(symbols)
    for r in rows:
        if (r.get("SEM_EXM_EXCH_ID") == "NSE"
                and r.get("SEM_SEGMENT") == "E"
                and r.get("SEM_SERIES") == "EQ"):
            sym = (r.get("SEM_TRADING_SYMBOL") or "").strip()
            if sym in wanted:
                out[sym] = int(r["SEM_SMST_SECURITY_ID"])
    json.dump(out, open(IDMAP_CACHE, "w"), indent=2)
    missing = wanted - set(out)
    if missing:
        print("WARNING: no security id found for:", missing)
    return out
