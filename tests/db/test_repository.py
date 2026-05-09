from src.db.repository import Repository


def test_repository_initializes_schema(tmp_path):
    db_path = tmp_path / "test.db"
    repo = Repository(str(db_path))
    repo.init_schema()

    # Verify all 5 tables exist
    tables = repo.list_tables()
    expected = {"employees", "attendance_records", "resolutions",
                "import_batches", "record_history"}
    assert expected.issubset(set(tables))


def test_upsert_and_fetch_employee(tmp_path):
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()

    emp_id = repo.upsert_employee(
        staff_no="1002", name="ANDIKA", department="ARGA DIRGA"
    )
    assert emp_id > 0

    fetched = repo.get_employee_by_staff_no("1002")
    assert fetched["name"] == "ANDIKA"
    assert fetched["department"] == "ARGA DIRGA"

    # Upsert idempotent: same staff_no returns same id
    emp_id2 = repo.upsert_employee(
        staff_no="1002", name="ANDIKA", department="ARGA DIRGA"
    )
    assert emp_id2 == emp_id


def test_upsert_employee_preserves_department_when_omitted(tmp_path):
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    # First insert with department
    repo.upsert_employee("1002", "ANDIKA", department="ARGA DIRGA")
    # Re-upsert without department (e.g., parser doesn't have dept info this time)
    repo.upsert_employee("1002", "ANDIKA")
    # Department should be preserved, not nulled
    fetched = repo.get_employee_by_staff_no("1002")
    assert fetched["department"] == "ARGA DIRGA"


def test_insert_and_fetch_attendance(tmp_path):
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    emp_id = repo.upsert_employee("1002", "ANDIKA")

    rec_id = repo.insert_attendance({
        "employee_id": emp_id,
        "date": "2026-04-01",
        "day_name": "Rabu",
        "day_type": "Hari Kerja",
        "schedule_in": "08:00",
        "schedule_out": "16:00",
        "actual_in": "08:06",
        "actual_out": "16:41",
        "late_minutes": 6,
        "early_leave_minutes": 0,
        "work_hours": 7.9,
        "overtime_hours": 0,
        "absent_flag": 0,
        "forgot_punch_flag": 0,
        "issue_case": None,
        "import_batch_id": None,
    })
    assert rec_id > 0

    fetched = repo.get_attendance(emp_id, "2026-04-01")
    assert fetched["actual_in"] == "08:06"
    assert fetched["late_minutes"] == 6


def test_list_monthly_grid_returns_skeleton_for_empty_month(tmp_path):
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    repo.upsert_employee("1002", "ANDIKA", department="ARGA DIRGA")

    rows = repo.list_monthly_grid(2026, 4)
    # April 2026 has 30 days; one employee → 30 rows
    assert len(rows) == 30
    # All rows should be skeleton (no actual_in/out)
    assert all(r["actual_in"] is None for r in rows)
    # day_name and day_type populated for skeleton rows
    assert rows[0]["day_name"] == "Rabu"          # Apr 1, 2026 = Wednesday
    assert rows[0]["day_type"] == "Hari Kerja"
    # Sat/Sun marked as Istirahat
    sat = next(r for r in rows if r["date"] == "2026-04-04")
    assert sat["day_type"] == "Istirahat"

def test_list_monthly_grid_overlays_actual_data(tmp_path):
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    emp_id = repo.upsert_employee("1002", "ANDIKA", department="ARGA DIRGA")
    repo.insert_attendance({
        "employee_id": emp_id, "date": "2026-04-01",
        "day_name": "Rabu", "day_type": "Hari Kerja",
        "schedule_in": "08:00", "schedule_out": "16:00",
        "actual_in": "08:06", "actual_out": "16:41",
        "late_minutes": 6, "early_leave_minutes": 0,
        "work_hours": 7.9, "overtime_hours": 0.0,
        "absent_flag": 0, "forgot_punch_flag": 0,
        "issue_case": None, "import_batch_id": None,
    })

    rows = repo.list_monthly_grid(2026, 4)
    apr_1 = next(r for r in rows if r["date"] == "2026-04-01")
    assert apr_1["actual_in"] == "08:06"
    assert apr_1["late_minutes"] == 6
    apr_2 = next(r for r in rows if r["date"] == "2026-04-02")
    assert apr_2["actual_in"] is None  # still skeleton

def test_list_monthly_grid_includes_resolution(tmp_path):
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    emp_id = repo.upsert_employee("1002", "ANDIKA")
    rec_id = repo.insert_attendance({
        "employee_id": emp_id, "date": "2026-04-02",
        "day_name": "Kamis", "day_type": "Hari Kerja",
        "schedule_in": "08:00", "schedule_out": "16:00",
        "actual_in": None, "actual_out": None,
        "late_minutes": 0, "early_leave_minutes": 0,
        "work_hours": 0.0, "overtime_hours": 0.0,
        "absent_flag": 1, "forgot_punch_flag": 0,
        "issue_case": "A", "import_batch_id": None,
    })
    repo.upsert_resolution(rec_id, reason_code="cuti",
                           reason_detail="kepentingan keluarga")

    rows = repo.list_monthly_grid(2026, 4)
    apr_2 = next(r for r in rows if r["date"] == "2026-04-02")
    assert apr_2["reason_code"] == "cuti"
    assert apr_2["reason_detail"] == "kepentingan keluarga"

def test_list_monthly_grid_filter_by_employee(tmp_path):
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    repo.upsert_employee("1002", "ANDIKA")
    repo.upsert_employee("1004", "ESA")

    all_rows = repo.list_monthly_grid(2026, 4)
    only_esa = repo.list_monthly_grid(2026, 4, staff_no_filter="1004")
    assert len(all_rows) == 60   # 2 employees × 30 days
    assert len(only_esa) == 30
    assert all(r["staff_no"] == "1004" for r in only_esa)


def test_list_issues_with_resolutions_pending_first(tmp_path):
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    emp = repo.upsert_employee(staff_no="1001", name="ALICE")
    # Two attendance records on different dates, both case A (tidak hadir)
    rec_a = repo.insert_attendance({
        "employee_id": emp, "date": "2026-04-01", "day_name": "Rabu",
        "day_type": "Hari Kerja", "issue_case": "A",
    })
    rec_b = repo.insert_attendance({
        "employee_id": emp, "date": "2026-04-02", "day_name": "Kamis",
        "day_type": "Hari Kerja", "issue_case": "A",
    })
    # Resolve only rec_a
    repo.upsert_resolution(rec_a, reason_code="cuti")

    rows = repo.list_issues_with_resolutions("2026-04-01", "2026-04-07")
    assert len(rows) == 2
    # Pending (no reason_code) must come first
    assert rows[0]["reason_code"] is None
    assert rows[0]["id"] == rec_b
    assert rows[1]["reason_code"] == "cuti"
    assert rows[1]["id"] == rec_a


def test_list_issues_with_resolutions_excludes_non_issue_cases(tmp_path):
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    emp = repo.upsert_employee(staff_no="1001", name="ALICE")
    # Case D (mild late) is NOT in the issue set (A/B/C/F) — should be excluded
    repo.insert_attendance({
        "employee_id": emp, "date": "2026-04-01", "day_name": "Rabu",
        "day_type": "Hari Kerja", "issue_case": "D",
    })
    # Case G (Istirahat / weekend) is also out
    repo.insert_attendance({
        "employee_id": emp, "date": "2026-04-04", "day_name": "Sabtu",
        "day_type": "Istirahat", "issue_case": "G",
    })
    # Case A is in
    repo.insert_attendance({
        "employee_id": emp, "date": "2026-04-02", "day_name": "Kamis",
        "day_type": "Hari Kerja", "issue_case": "A",
    })

    rows = repo.list_issues_with_resolutions("2026-04-01", "2026-04-07")
    assert len(rows) == 1
    assert rows[0]["issue_case"] == "A"
