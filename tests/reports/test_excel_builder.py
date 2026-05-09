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


def test_monthly_format_has_17_sheets_columns(tmp_path):
    """Output must match user's actual Sheets format byte-for-byte (17 cols)."""
    out = tmp_path / "monthly.xlsx"
    rows = [{
        "name": "ANDIKA", "department": "ARGA DIRGA",
        "date": "2026-04-01", "day_name": "Rabu", "day_type": "Hari Kerja",
        "schedule_in": "08:00", "schedule_out": "16:00",
        "actual_in": "08:06", "actual_out": "16:41",
        "work_hours": 7.9, "overtime_hours": None,
        "kurang_hours": 0.1, "late_minutes": 6, "early_leave_minutes": None,
        "absent_flag": None, "forgot_punch_flag": None, "ijin_flag": None,
        "alasan_ijin": "",
    }]
    build_monthly_sheets_format(str(out), rows)
    wb = load_workbook(out)
    ws = wb["Monthly Report"]
    headers = [ws.cell(1, c).value for c in range(1, 18)]
    assert headers == [
        "Nama", "Dept.", "Tanggal", "Hari", "Tipe",
        "Jadwal", "Masuk", "Keluar",
        "Kerja", "Lembur", "Kurang", "Terlambat", "Pulang Cepat",
        "Absen", "Lupa in/out", "Ijin", "Alasan Ijin",
    ]
    # Spot-check first data row
    assert ws.cell(2, 1).value == "ANDIKA"
    assert ws.cell(2, 7).value == "08:06"
    assert ws.cell(2, 12).value == 6
