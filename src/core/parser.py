import xlrd
from datetime import datetime

# Column indices in the fingerprint .xls (header at row 0, units at row 1)
COL_NAME = 0
COL_STAFF_NO = 1
COL_DEPT = 2
COL_DATE = 3
COL_DAY = 4
COL_TYPE = 5
COL_SCHEDULE = 6
COL_MASUK = 8
COL_KELUAR = 10
COL_KERJA = 13
COL_LEMBUR = 14
COL_TERLAMBAT = 16
COL_PULANG_CEPAT = 17
COL_ABSEN = 18
COL_LUPA = 19


def _to_int(value) -> int:
    """Convert cell to int. Empty -> 0."""
    if value == "" or value is None:
        return 0
    if isinstance(value, str):
        value = value.replace(",", ".").strip()
        if not value:
            return 0
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0


def _to_float(value) -> float:
    """Convert cell with Indonesian decimal comma to float. Empty -> 0.0."""
    if value == "" or value is None:
        return 0.0
    if isinstance(value, str):
        value = value.replace(",", ".").strip()
        if not value:
            return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _to_staff_no(value) -> str:
    """Normalize staff_no cell to string. xlrd may yield float for numeric IDs."""
    if value is None or value == "":
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _normalize_time(value, datemode: int = 0) -> str | None:
    """Convert '08.06' or 0.3375 -> '08:06'. Empty -> None.

    xlrd may return time-formatted Excel cells as either a string ('08.06')
    or a float representing day fraction (0.3375 ~= 08:06). The current
    fingerprint export emits strings, but other versions could emit floats,
    so handle both. ``datemode`` defaults to 0 (1900 epoch) which is the
    standard for Windows .xls files.
    """
    if value == "" or value is None:
        return None
    if isinstance(value, float):
        # xlrd returns time as a fraction of a day; convert via xldate.
        try:
            tup = xlrd.xldate.xldate_as_tuple(value, datemode)
            # tup = (year, month, day, hour, minute, second)
            return f"{tup[3]:02d}:{tup[4]:02d}"
        except Exception:
            return None
    s = str(value).strip()
    if not s:
        return None
    return s.replace(".", ":")


def _parse_date(value) -> str | None:
    """Convert '01/04/2026' -> '2026-04-01'."""
    if not value:
        return None
    s = str(value).strip()
    try:
        dt = datetime.strptime(s, "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def _parse_schedule(schedule_str) -> tuple[str | None, str | None]:
    """'08.00 - 16.00' -> ('08:00', '16:00')."""
    if not schedule_str or " - " not in str(schedule_str):
        return (None, None)
    parts = str(schedule_str).split(" - ")
    if len(parts) != 2:
        return (None, None)
    return (_normalize_time(parts[0]), _normalize_time(parts[1]))


def parse_xls(path: str) -> list[dict]:
    """Parse fingerprint export .xls into list of normalized record dicts."""
    # ignore_workbook_corruption: fingerprint .xls exports often have a benign
    # OLE2 inconsistency warning (SSCS/SSAT size mismatch) that doesn't affect
    # data integrity. Without this flag, xlrd raises on open.
    book = xlrd.open_workbook(path, ignore_workbook_corruption=True)
    sheet = book.sheet_by_index(0)
    records = []

    # Skip rows 0 (header) and 1 (units). Data starts at row 2.
    for row_idx in range(2, sheet.nrows):
        row = sheet.row_values(row_idx)
        name = str(row[COL_NAME]).strip() if row[COL_NAME] else ""

        # Skip blank rows and "Total Personal:" separator rows
        if not name or name.startswith("Total Personal"):
            continue

        date_str = _parse_date(row[COL_DATE])
        if not date_str:
            continue

        sched_in, sched_out = _parse_schedule(row[COL_SCHEDULE])

        records.append({
            "staff_no": _to_staff_no(row[COL_STAFF_NO]),
            "name": name,
            "department": str(row[COL_DEPT]).strip() if row[COL_DEPT] else None,
            "date": date_str,
            "day_name": str(row[COL_DAY]).strip(),
            "day_type": str(row[COL_TYPE]).strip(),
            "schedule_in": sched_in,
            "schedule_out": sched_out,
            "actual_in": _normalize_time(row[COL_MASUK], book.datemode),
            "actual_out": _normalize_time(row[COL_KELUAR], book.datemode),
            "late_minutes": _to_int(row[COL_TERLAMBAT]),
            "early_leave_minutes": _to_int(row[COL_PULANG_CEPAT]),
            "work_hours": _to_float(row[COL_KERJA]),
            "overtime_hours": _to_float(row[COL_LEMBUR]),
            "absent_flag": _to_int(row[COL_ABSEN]),
            "forgot_punch_flag": _to_int(row[COL_LUPA]),
        })

    return records
