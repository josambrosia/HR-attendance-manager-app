from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from src.core.constants import COLORS, REASON_CODES

PRIMARY_FILL = PatternFill("solid", fgColor=COLORS["primary"].lstrip("#"))
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
THIN_BORDER = Border(
    left=Side(style="thin", color="CCCCCC"),
    right=Side(style="thin", color="CCCCCC"),
    top=Side(style="thin", color="CCCCCC"),
    bottom=Side(style="thin", color="CCCCCC"),
)


def build_raw_excel(output_path: str, sections: dict):
    """sections: {sheet_name: list_of_dicts}. Each sheet gets its own worksheet."""
    wb = Workbook()
    wb.remove(wb.active)
    for sheet_name, rows in sections.items():
        ws = wb.create_sheet(title=sheet_name[:31])  # Excel sheet name limit
        if not rows:
            ws.append(["(no data)"])
            continue
        headers = list(rows[0].keys())
        ws.append(headers)
        for cell in ws[1]:
            cell.font = HEADER_FONT
            cell.fill = PRIMARY_FILL
            cell.alignment = Alignment(horizontal="center")
            cell.border = THIN_BORDER
        for row in rows:
            ws.append([row.get(h, "") for h in headers])
        for col_idx, h in enumerate(headers, 1):
            max_len = max([len(str(h))] + [len(str(r.get(h, ""))) for r in rows])
            ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, 40)
    wb.save(output_path)


def build_hall_of_late_excel(output_path: str, ranking: list[dict]):
    """Convenience wrapper: ranking -> single-sheet excel."""
    rows = [{
        "Rank": i + 1,
        "Staff No": r["staff_no"],
        "Name": r["name"],
        "Total Late (min)": r["total_late"],
        "Days Late": r["days_late"],
        "Max Late (min)": r["max_late"],
        "Max Late Date": r["max_late_date"],
    } for i, r in enumerate(ranking)]
    build_raw_excel(output_path, {"Hall of Late": rows})


def build_monthly_sheets_format(output_path: str, monthly_summary: list[dict]):
    """Output structured to be copy-pasteable into the shared Google Sheets.

    NOTE: The exact column layout matching the user's Google Sheets cannot be
    finalized until the user shares a screenshot or .xlsx export of the live
    Sheets (see spec section 17, Open Item #1). This implementation produces a
    sensible default layout that can be adjusted in a later iteration.
    """
    rows = [{
        "Tanggal": s["date"],
        "Nama": s["name"],
        "No Staff": s["staff_no"],
        "Masuk": s.get("actual_in", "") or "",
        "Keluar": s.get("actual_out", "") or "",
        "Terlambat (mnt)": s.get("late_minutes", 0),
        "Pulang Cepat (mnt)": s.get("early_leave_minutes", 0),
        "Alasan Ijin": REASON_CODES.get(s.get("reason_code"), {}).get("label", "") if s.get("reason_code") else "",
        "Lokasi/Detail": s.get("location") or s.get("reason_detail") or "",
    } for s in monthly_summary]
    build_raw_excel(output_path, {"Monthly Report": rows})
