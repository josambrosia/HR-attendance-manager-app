from pathlib import Path
import pytest
from src.core.parser import (
    parse_xls,
    _to_int,
    _to_float,
    _normalize_time,
    _parse_date,
    _parse_schedule,
)

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_apr_1_10.xls"


def test_parse_returns_list_of_records():
    if not FIXTURE.exists():
        pytest.skip("Fixture not present (PII — kept local)")
    records = parse_xls(str(FIXTURE))
    assert isinstance(records, list)
    assert len(records) > 0


def test_parsed_record_has_expected_fields():
    if not FIXTURE.exists():
        pytest.skip("Fixture not present (PII — kept local)")
    records = parse_xls(str(FIXTURE))
    rec = records[0]
    expected_keys = {
        "staff_no", "name", "department", "date", "day_name",
        "day_type", "schedule_in", "schedule_out", "actual_in", "actual_out",
        "late_minutes", "early_leave_minutes", "work_hours", "overtime_hours",
        "absent_flag", "forgot_punch_flag",
    }
    assert expected_keys.issubset(set(rec.keys()))


def test_skips_total_personal_rows():
    if not FIXTURE.exists():
        pytest.skip("Fixture not present (PII — kept local)")
    records = parse_xls(str(FIXTURE))
    for rec in records:
        assert not rec["name"].startswith("Total Personal")


def test_andika_apr_1_parsed_correctly():
    if not FIXTURE.exists():
        pytest.skip("Fixture not present (PII — kept local)")
    records = parse_xls(str(FIXTURE))
    andika_apr_1 = next(
        r for r in records
        if r["name"] == "ANDIKA" and r["date"] == "2026-04-01"
    )
    assert andika_apr_1["staff_no"] == "1002"
    assert andika_apr_1["actual_in"] == "08:06"
    assert andika_apr_1["actual_out"] == "16:41"
    assert andika_apr_1["late_minutes"] == 6
    assert andika_apr_1["work_hours"] == 7.9
    assert andika_apr_1["day_type"] == "Hari Kerja"


def test_esa_apr_1_full_absent():
    if not FIXTURE.exists():
        pytest.skip("Fixture not present (PII — kept local)")
    records = parse_xls(str(FIXTURE))
    esa = next(
        r for r in records
        if r["name"] == "ESA" and r["date"] == "2026-04-01"
    )
    assert esa["actual_in"] is None
    assert esa["actual_out"] is None
    assert esa["absent_flag"] == 1


def test_istirahat_rows_included():
    if not FIXTURE.exists():
        pytest.skip("Fixture not present (PII — kept local)")
    records = parse_xls(str(FIXTURE))
    # Saturday/Sunday rows should reach Task 7/8 (not silently dropped)
    assert any(r["day_type"] == "Istirahat" for r in records)


# --- Helper unit tests (run without fixture) ---


def test_to_float_handles_indonesian_comma():
    assert _to_float("7,9") == 7.9
    assert _to_float("0") == 0.0
    assert _to_float("") == 0.0
    assert _to_float(None) == 0.0
    assert _to_float(7.9) == 7.9


def test_to_int_handles_strings_and_empty():
    assert _to_int("6") == 6
    assert _to_int(6) == 6
    assert _to_int("") == 0
    assert _to_int(None) == 0
    assert _to_int("6.5") == 6


def test_normalize_time_string_format():
    assert _normalize_time("08.06") == "08:06"
    assert _normalize_time("") is None
    assert _normalize_time(None) is None


def test_normalize_time_float_format():
    # xlrd day fraction: 0.3375 ~= 08:06
    result = _normalize_time(0.3375, datemode=0)
    assert result == "08:06"


def test_parse_date_indonesian_format():
    assert _parse_date("01/04/2026") == "2026-04-01"
    assert _parse_date("") is None
    assert _parse_date("not-a-date") is None


def test_parse_schedule_splits_correctly():
    assert _parse_schedule("08.00 - 16.00") == ("08:00", "16:00")
    assert _parse_schedule("") == (None, None)
    assert _parse_schedule(None) == (None, None)
