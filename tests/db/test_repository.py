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
