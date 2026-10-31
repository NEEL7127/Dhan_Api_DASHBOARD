import streamlit as st
import pandas as pd
import secrets_store, dhan_client, transform, excel_export
from config import CRED_FIELDS

st.set_page_config(page_title="NIFTY Data Tracker", layout="wide")
page = st.sidebar.radio("Page", ["Dashboard", "Settings"])

@st.cache_data(ttl=3600)   # expiries change rarely; don't spend a call every rerun
def cached_expiries():
    return dhan_client.get_expiries()

# ---------------- SETTINGS PAGE ----------------
if page == "Settings":
    st.title("⚙️ Settings — Dhan Credentials")
    st.caption("Stored locally in dhan_secrets.json (never committed). "
               "Anyone using this machine can see these — keep it private.")
    creds = secrets_store.load()
    show = st.checkbox("Show secrets", value=False)
    new = {}
    for field, is_secret in CRED_FIELDS.items():
        label = field.replace("_", " ").title()
        current = creds.get(field, "")
        if show or not is_secret:
            new[field] = st.text_input(label, value=current)
        else:
            st.text(f"{label}: {secrets_store.mask(current)}")
            new[field] = st.text_input(label, value=current, type="password",
                                       key=f"pw_{field}")
    col1, col2 = st.columns(2)
    if col1.button("💾 Save"):
        merged = {**creds, **{k: v for k, v in new.items() if v != ""}}
        secrets_store.save(merged)
        st.success("Saved.")
    if col2.button("🔌 Test connection"):
        try:
            exp = dhan_client.get_expiries()
            st.success(f"OK — {len(exp)} expiries. First: {exp[0] if exp else 'n/a'}")
        except Exception as e:
            st.error(f"Failed: {e}")
    st.stop()

# ---------------- DASHBOARD PAGE ----------------
st.title("📈 NIFTY 50 Option Chain")
source = st.sidebar.selectbox("Data Source", ["Option Chain (NIFTY)", "Nifty 50 Stocks"])

if source == "Option Chain (NIFTY)":
    try:
        expiries = cached_expiries()
    except Exception as e:
        st.error(f"Can't load expiries — check Settings. ({e})"); st.stop()
    expiry = st.sidebar.selectbox("Expiry", expiries)
    n = st.sidebar.slider("Strikes around ATM", 3, 25, 10)

    all_cols = ["CE Buildup","CE Delta","CE Theta","CE IV","CE Volume","CE OI",
                "CE Chg%","CE LTP","Strike","PCR","PE LTP","PE Chg%","PE OI",
                "PE Volume","PE IV","PE Delta","PE Theta","PE Buildup"]
    chosen = st.sidebar.multiselect("Fields", all_cols, default=all_cols)
    refresh = st.sidebar.checkbox("Auto-refresh (5s)", value=False)

    @st.fragment(run_every=("5s" if refresh else None))
    def render():
        try:
            chain = dhan_client.get_option_chain(expiry)
            df, m = transform.build_chain_table(chain, n)
        except Exception as e:
            st.error(f"Fetch failed: {e}"); return
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("NIFTY LTP", f"{m['underlying']:.2f}")
        c2.metric("ATM", f"{m['atm']:.0f}")
        c3.metric("PCR", f"{m['pcr_overall']:.2f}")
        c4.metric("CE / PE OI (lakh)",
                  f"{m['total_ce_oi']/1e5:,.0f} / {m['total_pe_oi']/1e5:,.0f}")
        view = df[[c for c in chosen if c in df.columns]]
        pct_cols = [c for c in view.columns if "Chg%" in c]
        fmt = {c: "{:.2%}" for c in pct_cols}
        st.dataframe(view.style.format(fmt, precision=2), use_container_width=True, height=600)
        st.download_button("⬇ Download Excel",
            data=excel_export.to_excel_bytes(view, m),
            file_name=f"nifty_chain_{expiry}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    render()

else:
    st.info("Nifty 50 Stocks tab — Phase 7. Build instruments.py (symbol→id) first, "
            "then call dhan_client.get_quotes(ids) and transform.build_stock_table(...).")

