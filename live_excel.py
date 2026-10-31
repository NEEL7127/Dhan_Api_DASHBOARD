import xlwings as xw

_wb_cache = {}

def get_or_create_sheet(sheet_name="Live Data"):
    """
    Connect to an active Excel workbook or create a new one.
    Returns the target worksheet.
    """
    app = None
    wb = None
    try:
        # Check if Excel is already running
        if xw.apps.count > 0:
            app = xw.apps.active
            if len(app.books) > 0:
                wb = app.books.active
            else:
                wb = app.books.add()
        else:
            app = xw.App(visible=True)
            wb = app.books.add()
    except Exception:
        app = xw.App(visible=True)
        wb = app.books.add()

    # Find or add the target sheet
    try:
        sheet = wb.sheets[sheet_name]
    except Exception:
        sheet = wb.sheets.add(sheet_name)
    
    return sheet

def stream_to_excel(df, metrics, title="NIFTY Live Tracker", sheet_name="Live Data"):
    """
    Stream a pandas DataFrame and summary metrics into an open Excel worksheet in real time.
    """
    sheet = get_or_create_sheet(sheet_name)
    
    # 1. Update Header & Summary Metrics at the top
    sheet.range("A1").value = title
    sheet.range("A1").font.bold = True
    sheet.range("A1").font.size = 14
    
    underlying = metrics.get("underlying", "")
    atm = metrics.get("atm", "")
    pcr = round(metrics.get("pcr_overall", 0), 2)
    
    sheet.range("A2").value = f"Underlying LTP: {underlying}"
    if atm:
        sheet.range("A3").value = f"ATM: {atm}   PCR: {pcr}"
    else:
        sheet.range("A3").value = ""

    # 2. Filter out internal columns
    cols = [c for c in df.columns if not c.startswith("_")]
    export_df = df[cols].copy()

    # 3. Write Headers and Table values in one high-performance block
    start_row = 5
    headers_range = sheet.range((start_row, 1), (start_row, len(cols)))
    headers_range.value = cols
    headers_range.font.bold = True
    headers_range.color = (220, 220, 220)

    data_range = sheet.range((start_row + 1, 1), (start_row + len(export_df), len(cols)))
    data_range.value = export_df.values

    # 4. Apply Percentage format for Chg% columns
    for j, c in enumerate(cols, start=1):
        if "Chg%" in c:
            pct_range = sheet.range((start_row + 1, j), (start_row + len(export_df), j))
            pct_range.number_format = "0.00%"

    return True
