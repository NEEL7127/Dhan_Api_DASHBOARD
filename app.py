import streamlit as st
import pandas as pd
import secrets_store, dhan_client, transform, excel_export, live_excel
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
    refresh = st.sidebar.checkbox("Auto-refresh (3s)", value=False)
    live_stream = st.sidebar.checkbox("🔴 Live Stream to Excel (3s)", value=False)

    @st.fragment(run_every=("3s" if refresh or live_stream else None))
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

        # Stream to open Excel if checked
        if live_stream:
            try:
                live_excel.stream_to_excel(view, m, title=f"NIFTY Option Chain ({expiry})", sheet_name="Option Chain")
                st.sidebar.success("🟢 Excel Live Linked")
            except Exception as ex:
                st.sidebar.warning(f"Excel Live Link note: {ex}")

        st.download_button("⬇ Download Excel",
            data=excel_export.to_excel_bytes(view, m),
            file_name=f"nifty_chain_{expiry}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    render()

else:  # source == "Nifty 50 Stocks"
    import instruments
    try:
        symbols = instruments.fetch_nifty50_symbols()
        sym_to_id = instruments.build_id_map(symbols)
        id_to_sym = {v: k for k, v in sym_to_id.items()}
    except Exception as e:
        st.error(f"Could not load Nifty 50 list / ids: {e}"); st.stop()

    all_cols = ["Symbol", "LTP", "Chg%", "Open", "High", "Low", "Volume"]
    chosen = st.sidebar.multiselect("Fields", all_cols, default=all_cols)
    refresh = st.sidebar.checkbox("Auto-refresh (3s)", value=False)
    live_stream = st.sidebar.checkbox("🔴 Live Stream to Excel (3s)", value=False)

    @st.fragment(run_every=("3s" if refresh or live_stream else None))
    def render_stocks():
        try:
            q = dhan_client.get_quotes(list(sym_to_id.values()))
            df = transform.build_stock_table(q, id_to_sym)
        except Exception as e:
            st.error(f"Quote fetch failed: {e}"); return
        up = int((df["Chg%"] > 0).sum()); down = int((df["Chg%"] < 0).sum())
        c1, c2, c3 = st.columns(3)
        c1.metric("Stocks", len(df)); c2.metric("Advancing", up); c3.metric("Declining", down)
        view = df[[c for c in chosen if c in df.columns]]
        pct = {c: "{:.2%}" for c in view.columns if c == "Chg%"}
        st.dataframe(view.style.format(pct, precision=2),
                     use_container_width=True, height=600)

        # Stream to open Excel if checked
        if live_stream:
            try:
                live_excel.stream_to_excel(view, {"underlying": "Nifty 50 Stocks"}, title="Nifty 50 Live Stocks", sheet_name="Nifty 50 Stocks")
                st.sidebar.success("🟢 Excel Live Linked")
            except Exception as ex:
                st.sidebar.warning(f"Excel Live Link note: {ex}")

        st.download_button("⬇ Download Excel",
            data=excel_export.to_excel_bytes(view, {"underlying": "Nifty 50 Stocks"},
                                             title="Nifty 50 Stocks"),
            file_name="nifty50_stocks.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    render_stocks()

