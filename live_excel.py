import os
import openpyxl
import xlwings as xw

WORKBOOK_NAME = "Live_Nifty_Tracker.xlsx"
WORKBOOK_PATH = os.path.abspath(WORKBOOK_NAME)

_app_instance = None
_wb_instance = None

def _ensure_workbook_file():
    """Ensure the physical workbook file exists with initial sheets."""
    if not os.path.exists(WORKBOOK_PATH):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Option Chain"
        wb.create_sheet(title="Nifty 50 Stocks")
        wb.save(WORKBOOK_PATH)

def get_or_create_sheet(sheet_name="Option Chain"):
    """
    Connect to Live_Nifty_Tracker.xlsx or launch Excel and open it.
    Reuses persistent app and workbook handles across Streamlit reruns.
    """
    global _app_instance, _wb_instance
    _ensure_workbook_file()

    need_connect = True
    if _wb_instance is not None and _app_instance is not None:
        try:
            _ = _wb_instance.name
            need_connect = False
        except Exception:
            _app_instance = None
            _wb_instance = None
            need_connect = True

    if need_connect:
        for app in xw.apps:
            for b in app.books:
                if b.name.lower() == WORKBOOK_NAME.lower():
                    _app_instance = app
                    _wb_instance = b
                    need_connect = False
                    break
            if not need_connect:
                break

    if need_connect:
        _app_instance = xw.App(visible=True, add_book=False)
        _wb_instance = _app_instance.books.open(WORKBOOK_PATH)

    try:
        sheet = _wb_instance.sheets[sheet_name]
    except Exception:
        sheet = _wb_instance.sheets.add(sheet_name)

    return sheet

# --- module state (persists across Streamlit reruns); keyed per sheet ---
_layout = {}          # sheet_name -> {"cols": [...], "nrows": int}
_tick = {"n": 0}

def stream_to_excel(df, metrics, live_cols=None, title="NIFTY Live Tracker",
                    sheet_name="Option Chain", save_every=20):
    sheet = get_or_create_sheet(sheet_name)
    cols = [c for c in df.columns if not c.startswith("_")]
    nrows = len(df)
    start_row = 5
    st_ = _layout.setdefault(sheet_name, {"cols": None, "nrows": None})
    layout_changed = (st_["cols"] != cols or st_["nrows"] != nrows)

    # live summary line — cheap, update every tick
    sheet.range("A2").value = f"Underlying LTP: {metrics.get('underlying','')}"
    atm = metrics.get("atm", "")
    sheet.range("A3").value = (f"ATM: {atm}   PCR: {round(metrics.get('pcr_overall',0),2)}"
                               if atm else "")

    if layout_changed:
        # title + header + ALL values + formats written ONCE (not every tick)
        sheet.range("A1").value = title
        sheet.range("A1").font.bold = True
        sheet.range((start_row, 1), (start_row + 2000, len(cols) + 2)).clear_contents()
        hdr = sheet.range((start_row, 1), (start_row, len(cols)))
        hdr.value = cols
        hdr.font.bold = True
        hdr.color = (220, 220, 220)
        sheet.range((start_row + 1, 1), (start_row + nrows, len(cols))).value = df[cols].values
        # apply % format ONCE to any Chg% column (setting a cell's value later keeps its format)
        for j, c in enumerate(cols, start=1):
            if "Chg%" in c:
                sheet.range((start_row + 1, j), (start_row + nrows, j)).number_format = "0.00%"
        st_.update(cols=list(cols), nrows=nrows)
    else:
        live = set(cols) if not live_cols else set(live_cols)
        for j, c in enumerate(cols, start=1):
            if c in live:        # write ONLY the live columns, values only
                rng = sheet.range((start_row + 1, j), (start_row + nrows, j))
                rng.value = [[v] for v in df[c].values]

    _tick["n"] += 1
    if _tick["n"] % save_every == 0:     # save to disk occasionally, not every tick
        try: sheet.book.save()
        except Exception: pass
    return True
