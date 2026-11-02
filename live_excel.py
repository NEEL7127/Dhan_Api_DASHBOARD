import os
import time
import glob
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
        wb.create_sheet(title="Raw Data")
        wb.create_sheet(title="Nifty 50 Stocks")
        wb.save(WORKBOOK_PATH)

def _is_target_book_name(name):
    """Check if workbook name matches downloaded chain file, OptionChain.xlsx, or default live tracker."""
    n = name.lower()
    return n.startswith("nifty_chain") or n == "optionchain.xlsx" or n == WORKBOOK_NAME.lower()

def get_target_sheets(sheet_name="Option Chain"):
    """
    Finds or connects to all active target sheets across open Excel instances.
    Supports:
    - Any open workbook in Excel matching 'nifty_chain*.xlsx' (the user's downloaded file!)
    - Any open workbook named 'Live_Nifty_Tracker.xlsx'
    If no Excel workbook is open, launches/connects to Live_Nifty_Tracker.xlsx.
    """
    global _app_instance, _wb_instance
    _ensure_workbook_file()

    target_sheets = []
    seen_books = set()

    # 1. Search all running Excel apps for any open matching workbook
    try:
        for app in xw.apps:
            try:
                for b in app.books:
                    if _is_target_book_name(b.name) and b.name.lower() not in seen_books:
                        seen_books.add(b.name.lower())
                        try:
                            sh = b.sheets[sheet_name]
                        except Exception:
                            sh = b.sheets.add(sheet_name)
                        target_sheets.append(sh)
            except Exception:
                continue
    except Exception:
        pass

    # 2. If no open workbook was found in running Excel instances, open WORKBOOK_PATH
    if not target_sheets:
        need_open = True
        if _wb_instance is not None and _app_instance is not None:
            try:
                _ = _wb_instance.name
                need_open = False
            except Exception:
                _app_instance = None
                _wb_instance = None

        if need_open:
            try:
                _app_instance = xw.App(visible=True, add_book=False)
                _wb_instance = _app_instance.books.open(WORKBOOK_PATH)
            except Exception:
                pass

        if _wb_instance is not None:
            try:
                sh = _wb_instance.sheets[sheet_name]
            except Exception:
                sh = _wb_instance.sheets.add(sheet_name)
            target_sheets.append(sh)

    return target_sheets

# --- module state (persists across Streamlit reruns); keyed per book+sheet ---
_layout = {}          # f"{book_name}::{sheet_name}" -> {"cols": [...], "nrows": int}
_tick = {"n": 0}

def _write_sheet(sheet, df, metrics, live_cols, title, sheet_name, is_raw):
    """Write DataFrame values and headers to a single open Excel sheet."""
    cols = [c for c in df.columns if not c.startswith("_")]
    nrows = len(df)
    start_row = 1 if is_raw else 5
    book_sheet_key = f"{sheet.book.name}::{sheet_name}"
    st_ = _layout.setdefault(book_sheet_key, {"cols": None, "nrows": None})
    layout_changed = (st_["cols"] != cols or st_["nrows"] != nrows)

    now = time.strftime("%H:%M:%S")

    if not is_raw:
        # Live headline metrics + live clock updating every 3s
        sheet.range("A2").value = f"Underlying LTP: {metrics.get('underlying','')}"
        sheet.range("C2").value = f"Last Updated: {now}"
        sheet.range("C2").font.bold = True
        atm = metrics.get("atm", "")
        sheet.range("A3").value = (f"ATM: {atm}   PCR: {round(metrics.get('pcr_overall',0),2)}"
                                   if atm else "")

    if layout_changed:
        if not is_raw:
            sheet.range("A1").value = title
            sheet.range("A1").font.bold = True
            sheet.range("A1").font.size = 14
        sheet.range((start_row, 1), (start_row + 2000, len(cols) + 2)).clear_contents()
        hdr = sheet.range((start_row, 1), (start_row, len(cols)))
        hdr.value = cols
        hdr.font.bold = True
        if not is_raw:
            hdr.color = (220, 220, 220)
        sheet.range((start_row + 1, 1), (start_row + nrows, len(cols))).value = df[cols].values
        if not is_raw:
            for j, c in enumerate(cols, start=1):
                if "Chg%" in c:
                    sheet.range((start_row + 1, j), (start_row + nrows, j)).number_format = "0.00%"
        st_.update(cols=list(cols), nrows=nrows)
        try:
            sheet.book.save()
        except Exception:
            pass
    else:
        live = set(cols) if not live_cols else set(live_cols)
        for j, c in enumerate(cols, start=1):
            if c in live:
                rng = sheet.range((start_row + 1, j), (start_row + nrows, j))
                rng.value = [[v] for v in df[c].values]

    return True

def _sync_latest_download_file(df, metrics, sheet_name, is_raw):
    """
    Also sync the latest downloaded file on disk if it exists in Downloads folder
    and is not currently locked/open in Excel.
    """
    try:
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        files = glob.glob(os.path.join(downloads_dir, "nifty_chain_all_*.xlsx"))
        if not files:
            return
        latest_file = max(files, key=os.path.getmtime)
        wb = openpyxl.load_workbook(latest_file)
        if sheet_name not in wb.sheetnames:
            ws = wb.create_sheet(sheet_name)
        else:
            ws = wb[sheet_name]

        cols = [c for c in df.columns if not c.startswith("_")]
        start_row = 1 if is_raw else 5

        if not is_raw:
            ws["A2"] = f"Underlying LTP: {metrics.get('underlying','')}"
            ws["C2"] = f"Last Updated: {time.strftime('%H:%M:%S')}"
            ws["A3"] = f"ATM: {metrics.get('atm','')}   PCR: {round(metrics.get('pcr_overall',0),2)}"

        for j, c in enumerate(cols, start=1):
            ws.cell(row=start_row, column=j, value=c)
        for i, (_, row) in enumerate(df.iterrows(), start=start_row + 1):
            for j, c in enumerate(cols, start=1):
                v = row[c]
                if hasattr(v, "item"): v = v.item()
                ws.cell(row=i, column=j, value=v)

        wb.save(latest_file)
    except Exception:
        # If open in Excel or inaccessible, xlwings already handles it
        pass

def stream_to_excel(df, metrics, live_cols=None, title="NIFTY Live Tracker",
                    sheet_name="Option Chain", save_every=5, is_raw=False):
    """
    Streams data to all active target workbooks (both the downloaded file and Live_Nifty_Tracker).
    Updates in real time and saves periodically.
    """
    sheets = get_target_sheets(sheet_name)
    saved_books = set()

    for sheet in sheets:
        try:
            _write_sheet(sheet, df, metrics, live_cols, title, sheet_name, is_raw)
        except Exception:
            continue

    _tick["n"] += 1
    # Save open workbooks periodically (or on layout changes)
    if _tick["n"] % save_every == 0:
        for sheet in sheets:
            try:
                b_name = sheet.book.name
                if b_name not in saved_books:
                    saved_books.add(b_name)
                    sheet.book.save()
            except Exception:
                pass
        # Also sync to Downloads disk file if present
        _sync_latest_download_file(df, metrics, sheet_name, is_raw)

    return True
