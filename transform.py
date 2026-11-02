import pandas as pd

def _buildup(last, prev_close, oi, prev_oi):
    price_up = (last - prev_close) >= 0
    oi_up = (oi - prev_oi) >= 0
    if price_up and oi_up:      return "Long Buildup"
    if not price_up and oi_up:  return "Short Buildup"
    if price_up and not oi_up:  return "Short Covering"
    return "Long Unwinding"

def _pct(last, prev_close):
    return (last - prev_close) / prev_close if prev_close else 0.0

def _side(d):
    g = d.get("greeks", {}) or {}
    return {
        "ltp": d.get("last_price", 0.0),
        "chg_pct": _pct(d.get("last_price", 0.0), d.get("previous_close_price", 0.0)),
        "oi": d.get("oi", 0),
        "volume": d.get("volume", 0),
        "iv": d.get("implied_volatility", 0.0),
        "delta": g.get("delta", 0.0),
        "theta": g.get("theta", 0.0),
        "gamma": g.get("gamma", 0.0),
        "vega": g.get("vega", 0.0),
        "buildup": _buildup(d.get("last_price", 0.0), d.get("previous_close_price", 0.0),
                            d.get("oi", 0), d.get("previous_oi", 0)),
    }

def build_chain_table(chain_json, strikes_around_atm=10):
    data = chain_json["data"]
    underlying = data["last_price"]
    oc = data["oc"]
    # keep the ORIGINAL key alongside the float so we never reconstruct it
    pairs = sorted(((float(k), k) for k in oc.keys()), key=lambda p: p[0])
    strikes = [p[0] for p in pairs]
    atm = min(strikes, key=lambda s: abs(s - underlying))
    atm_i = strikes.index(atm)
    lo = max(0, atm_i - strikes_around_atm)
    hi = min(len(pairs), atm_i + strikes_around_atm + 1)
    kept = pairs[lo:hi]

    rows, tot_ce_oi, tot_pe_oi = [], 0, 0
    for s, key in kept:
        ce = _side(oc[key].get("ce", {}) or {})
        pe = _side(oc[key].get("pe", {}) or {})
        tot_ce_oi += ce["oi"]; tot_pe_oi += pe["oi"]
        rows.append({
            "CE Buildup": ce["buildup"], "CE Delta": ce["delta"], "CE Theta": ce["theta"],
            "CE IV": ce["iv"], "CE Volume": ce["volume"], "CE OI": ce["oi"],
            "CE Chg%": ce["chg_pct"], "CE LTP": ce["ltp"],
            "Strike": s, "PCR": (pe["oi"] / ce["oi"] if ce["oi"] else 0.0),
            "PE LTP": pe["ltp"], "PE Chg%": pe["chg_pct"], "PE OI": pe["oi"],
            "PE Volume": pe["volume"], "PE IV": pe["iv"], "PE Delta": pe["delta"],
            "PE Theta": pe["theta"], "PE Buildup": pe["buildup"],
            "_is_atm": s == atm,
        })
    df = pd.DataFrame(rows)
    metrics = {
        "underlying": underlying, "atm": atm,
        "pcr_overall": (tot_pe_oi / tot_ce_oi if tot_ce_oi else 0.0),
        "total_ce_oi": tot_ce_oi, "total_pe_oi": tot_pe_oi,
    }
    return df, metrics

# ---- Raw builder (all API fields, no derived columns) ----
_RAW_FIELDS = [
    ("last_price", "LTP"), ("previous_close_price", "PrevClose"),
    ("oi", "OI"), ("previous_oi", "PrevOI"),
    ("volume", "Volume"), ("previous_volume", "PrevVolume"),
    ("average_price", "AvgPrice"), ("implied_volatility", "IV"),
    ("top_bid_price", "BidPrice"), ("top_bid_quantity", "BidQty"),
    ("top_ask_price", "AskPrice"), ("top_ask_quantity", "AskQty"),
    ("security_id", "SecurityId"),
]
_GREEKS = [("delta","Delta"), ("theta","Theta"), ("gamma","Gamma"), ("vega","Vega")]

def _raw_side(d, prefix):
    out = {}
    for api, name in _RAW_FIELDS:
        out[f"{prefix} {name}"] = d.get(api, 0)
    g = d.get("greeks", {}) or {}
    for api, name in _GREEKS:
        out[f"{prefix} {name}"] = g.get(api, 0.0)
    return out

def build_raw_chain_table(chain_json, strikes_around_atm=10):
    """ALL raw API fields per strike, no derived columns. Mirrors build_chain_table's
       ATM windowing so the two views line up."""
    data = chain_json["data"]
    underlying = data["last_price"]
    oc = data["oc"]
    pairs = sorted(((float(k), k) for k in oc.keys()), key=lambda p: p[0])
    strikes = [p[0] for p in pairs]
    atm = min(strikes, key=lambda s: abs(s - underlying))
    atm_i = strikes.index(atm)
    lo = max(0, atm_i - strikes_around_atm)
    hi = min(len(pairs), atm_i + strikes_around_atm + 1)
    rows, tot_ce_oi, tot_pe_oi = [], 0, 0
    for s, key in pairs[lo:hi]:
        ce = oc[key].get("ce", {}) or {}
        pe = oc[key].get("pe", {}) or {}
        tot_ce_oi += ce.get("oi", 0); tot_pe_oi += pe.get("oi", 0)
        row = {}
        row.update(_raw_side(ce, "CE"))
        row["Strike"] = s
        row.update(_raw_side(pe, "PE"))
        rows.append(row)
    df = pd.DataFrame(rows)
    ce_cols = [c for c in df.columns if c.startswith("CE")]
    pe_cols = [c for c in df.columns if c.startswith("PE")]
    df = df[ce_cols + ["Strike"] + pe_cols]
    metrics = {"underlying": underlying, "atm": atm,
               "pcr_overall": (tot_pe_oi/tot_ce_oi if tot_ce_oi else 0.0),
               "total_ce_oi": tot_ce_oi, "total_pe_oi": tot_pe_oi}
    return df, metrics

# --- static column lists so the Field/Live widgets can live OUTSIDE the fragment ---
COMPUTED_COLUMNS = ["CE Buildup","CE Delta","CE Theta","CE IV","CE Volume","CE OI",
                    "CE Chg%","CE LTP","Strike","PCR","PE LTP","PE Chg%","PE OI",
                    "PE Volume","PE IV","PE Delta","PE Theta","PE Buildup"]
_CE_NAMES = [f"CE {name}" for _, name in _RAW_FIELDS] + [f"CE {name}" for _, name in _GREEKS]
_PE_NAMES = [f"PE {name}" for _, name in _RAW_FIELDS] + [f"PE {name}" for _, name in _GREEKS]
RAW_COLUMNS = _CE_NAMES + ["Strike"] + _PE_NAMES   # the full 35-column raw layout


def build_stock_table(quote_json, id_to_symbol):
    out = []
    seg = quote_json["data"].get("NSE_EQ", {})
    for sid, q in seg.items():
        last = q.get("last_price", 0.0); net = q.get("net_change", 0.0)
        prev = last - net
        ohlc = q.get("ohlc", {}) or {}
        out.append({
            "Symbol": id_to_symbol.get(int(sid), sid), "LTP": last,
            "Chg%": (net / prev if prev else 0.0),
            "Open": ohlc.get("open", 0.0), "High": ohlc.get("high", 0.0),
            "Low": ohlc.get("low", 0.0), "Volume": q.get("volume", 0),
        })
    return pd.DataFrame(out).sort_values("Symbol").reset_index(drop=True)

