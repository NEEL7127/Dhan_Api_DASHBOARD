import io, time
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

def to_excel_bytes(df, metrics, title="NIFTY Option Chain"):
    wb = Workbook(); ws = wb.active; ws.title = "Data"
    ws["A1"] = title; ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f"Underlying LTP: {metrics.get('underlying','')}"
    ws["C2"] = f"Last Updated: {time.strftime('%H:%M:%S')}"
    ws["C2"].font = Font(bold=True)
    ws["A3"] = f"ATM: {metrics.get('atm','')}   PCR: {round(metrics.get('pcr_overall',0),2)}"
    start = 5
    cols = [c for c in df.columns if not c.startswith("_")]
    for j, c in enumerate(cols, start=1):
        cell = ws.cell(row=start, column=j, value=c)
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="DDDDDD")
    for i, (_, row) in enumerate(df.iterrows(), start=start + 1):
        for j, c in enumerate(cols, start=1):
            v = row[c]
            if hasattr(v, "item"):          # numpy int64/float64 -> native python
                v = v.item()                # (openpyxl rejects numpy ints on Windows)
            ws.cell(row=i, column=j, value=v)
    for j, c in enumerate(cols, start=1):
        if "Chg%" in c:
            for r in range(start + 1, start + 1 + len(df)):
                ws.cell(row=r, column=j).number_format = "0.00%"
    ws.freeze_panes = ws.cell(row=start + 1, column=1)
    for col in ws.columns:
        width = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(width + 2, 22)
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return buf.getvalue()


def to_excel_raw_bytes(df, sheet_name="RawData"):
    """Faithful dump: header row + values only. No title block, no number formats."""
    wb = Workbook(); ws = wb.active; ws.title = sheet_name
    cols = [c for c in df.columns if not c.startswith("_")]
    for j, c in enumerate(cols, start=1):
        ws.cell(row=1, column=j, value=c)
    for i, (_, row) in enumerate(df.iterrows(), start=2):
        for j, c in enumerate(cols, start=1):
            v = row[c]
            if hasattr(v, "item"):   # numpy -> native python
                v = v.item()
            ws.cell(row=i, column=j, value=v)
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return buf.getvalue()


def _write_sheet_computed(ws, df, metrics, title):
    """Write a computed option-chain sheet with title, headers, formatting."""
    ws["A1"] = title; ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f"Underlying LTP: {metrics.get('underlying','')}"
    ws["C2"] = f"Last Updated: {time.strftime('%H:%M:%S')}"
    ws["C2"].font = Font(bold=True)
    ws["A3"] = f"ATM: {metrics.get('atm','')}   PCR: {round(metrics.get('pcr_overall',0),2)}"
    start = 5
    cols = [c for c in df.columns if not c.startswith("_")]
    for j, c in enumerate(cols, start=1):
        cell = ws.cell(row=start, column=j, value=c)
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="DDDDDD")
    for i, (_, row) in enumerate(df.iterrows(), start=start + 1):
        for j, c in enumerate(cols, start=1):
            v = row[c]
            if hasattr(v, "item"): v = v.item()
            ws.cell(row=i, column=j, value=v)
    for j, c in enumerate(cols, start=1):
        if "Chg%" in c:
            for r in range(start + 1, start + 1 + len(df)):
                ws.cell(row=r, column=j).number_format = "0.00%"
    ws.freeze_panes = ws.cell(row=start + 1, column=1)
    for col in ws.columns:
        width = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(width + 2, 22)


def _write_sheet_raw(ws, df):
    """Write a raw API data sheet: plain header + values, no formatting."""
    cols = [c for c in df.columns if not c.startswith("_")]
    for j, c in enumerate(cols, start=1):
        cell = ws.cell(row=1, column=j, value=c)
        cell.font = Font(bold=True)
    for i, (_, row) in enumerate(df.iterrows(), start=2):
        for j, c in enumerate(cols, start=1):
            v = row[c]
            if hasattr(v, "item"): v = v.item()
            ws.cell(row=i, column=j, value=v)


def to_excel_combined_bytes(computed_df, raw_df, metrics, title="NIFTY Option Chain"):
    """Single workbook with two sheets: Option Chain (computed) + Raw Data (all API fields)."""
    wb = Workbook()
    # Sheet 1 — Computed Option Chain
    ws1 = wb.active; ws1.title = "Option Chain"
    _write_sheet_computed(ws1, computed_df, metrics, title)
    # Sheet 2 — Raw API Data
    ws2 = wb.create_sheet("Raw Data")
    _write_sheet_raw(ws2, raw_df)
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return buf.getvalue()

