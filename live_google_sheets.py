import os
import json
import gspread

CREDENTIALS_FILE = "google_creds.json"
DEFAULT_SHEET_TITLE = "Dhan Live Nifty Tracker"

_client = None

def is_configured():
    """Check if google_creds.json exists."""
    return os.path.exists(CREDENTIALS_FILE)

def get_client():
    """Authenticate and return the gspread client."""
    global _client
    if _client is not None:
        return _client
    if not is_configured():
        raise FileNotFoundError(
            f"Google Sheets credentials file '{CREDENTIALS_FILE}' not found. "
            "Place your Google Service Account JSON in the project folder as google_creds.json."
        )
    _client = gspread.service_account(filename=CREDENTIALS_FILE)
    return _client

def get_or_create_sheet(sheet_title=DEFAULT_SHEET_TITLE, worksheet_name="Option Chain"):
    """
    Open the Google Spreadsheet by title (or create it if it doesn't exist).
    Returns the specific worksheet.
    """
    client = get_client()
    try:
        sh = client.open(sheet_title)
    except gspread.exceptions.SpreadsheetNotFound:
        sh = client.create(sheet_title)
        # Note: If newly created, the user can also share this spreadsheet with their own personal Google email

    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=worksheet_name, rows="300", cols="30")
        
    return ws

def stream_to_google_sheet(df, metrics, title="NIFTY Live Option Chain", worksheet_name="Option Chain", sheet_title=DEFAULT_SHEET_TITLE):
    """
    Push data to the designated Google Sheet worksheet in a single API call (batch update).
    """
    ws = get_or_create_sheet(sheet_title=sheet_title, worksheet_name=worksheet_name)

    underlying = metrics.get("underlying", "")
    atm = metrics.get("atm", "")
    pcr = round(metrics.get("pcr_overall", 0), 2)

    # Build the full 2D grid to update all at once
    header_rows = [
        [title, "", "", f"Underlying LTP: {underlying}"],
        ["", "", "", f"ATM: {atm} | PCR: {pcr}"],
        []
    ]

    cols = [c for c in df.columns if not c.startswith("_")]
    header_rows.append(cols)

    # Prepare data rows
    data_rows = []
    for _, row in df[cols].iterrows():
        row_vals = []
        for val in row:
            if hasattr(val, "item"):
                val = val.item()
            row_vals.append(val)
        data_rows.append(row_vals)

    full_grid = header_rows + data_rows

    # Batch update from cell A1
    ws.update(range_name=f"A1", values=full_grid)
    return True
