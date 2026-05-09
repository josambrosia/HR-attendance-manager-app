from openpyxl import load_workbook
from src.reports.excel_builder import (
    build_raw_excel, build_hall_of_late_excel, build_monthly_sheets_format
)


def test_raw_excel_creates_sheets(tmp_path):
    out = tmp_path / "test.xlsx"
    build_raw_excel(str(out), {
        "Sheet1": [{"a": 1, "b": 2}, {"a": 3, "b": 4}],
        "Sheet2": [{"x": "y"}],
    })
    wb = load_workbook(out)
    assert "Sheet1" in wb.sheetnames
    assert "Sheet2" in wb.sheetnames
    assert wb["Sheet1"].cell(2, 1).value == 1


def test_hall_of_late_excel(tmp_path):
    out = tmp_path / "rank.xlsx"
    build_hall_of_late_excel(str(out), [
        {"staff_no": "1", "name": "A", "total_late": 100, "days_late": 3,
         "max_late": 50, "max_late_date": "2026-04-01"},
    ])
    wb = load_workbook(out)
    ws = wb["Hall of Late"]
    assert ws.cell(1, 1).value == "Rank"
    assert ws.cell(2, 3).value == "A"
    assert ws.cell(2, 4).value == 100


def test_monthly_format_has_required_columns(tmp_path):
    out = tmp_path / "monthly.xlsx"
    build_monthly_sheets_format(str(out), [
        {"date": "2026-04-01", "name": "ANDIKA", "staff_no": "1002",
         "actual_in": "08:06", "actual_out": "16:41",
         "late_minutes": 6, "early_leave_minutes": 0,
         "reason_code": None, "location": None, "reason_detail": None},
    ])
    wb = load_workbook(out)
    ws = wb["Monthly Report"]
    headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
    assert "Tanggal" in headers
    assert "Nama" in headers
    assert "Terlambat (mnt)" in headers
