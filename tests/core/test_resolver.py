from src.db.repository import Repository
from src.core.resolver import (
    apply_resolution, get_resolution_label, requires_extra_input
)


def setup_repo_with_record(tmp_path):
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    emp_id = repo.upsert_employee("1002", "ANDIKA")
    rec_id = repo.insert_attendance({
        "employee_id": emp_id, "date": "2026-04-02", "day_name": "Kamis",
        "day_type": "Hari Kerja", "schedule_in": "08:00", "schedule_out": "16:00",
        "actual_in": None, "actual_out": None,
        "late_minutes": 0, "early_leave_minutes": 0,
        "work_hours": 0, "overtime_hours": 0,
        "absent_flag": 1, "forgot_punch_flag": 0,
        "issue_case": "A", "import_batch_id": None,
    })
    return repo, rec_id


def test_apply_simple_resolution(tmp_path):
    repo, rec_id = setup_repo_with_record(tmp_path)
    apply_resolution(repo, rec_id, "sakit")
    res = repo.get_resolution(rec_id)
    assert res["reason_code"] == "sakit"
    assert res["location"] is None


def test_apply_resolution_with_location(tmp_path):
    repo, rec_id = setup_repo_with_record(tmp_path)
    apply_resolution(repo, rec_id, "tugas_lapangan", location="Sragen")
    res = repo.get_resolution(rec_id)
    assert res["location"] == "Sragen"


def test_apply_lupa_absen_adds_penalty(tmp_path):
    repo, rec_id = setup_repo_with_record(tmp_path)
    apply_resolution(repo, rec_id, "lupa_absen", penalty_minutes=16)
    rec = repo.conn.execute(
        "SELECT * FROM attendance_records WHERE id=?", (rec_id,)
    ).fetchone()
    assert rec["late_minutes"] == 16


def test_apply_lupa_absen_no_penalty_when_disabled(tmp_path):
    repo, rec_id = setup_repo_with_record(tmp_path)
    apply_resolution(repo, rec_id, "lupa_absen", penalty_minutes=None)
    rec = repo.conn.execute(
        "SELECT * FROM attendance_records WHERE id=?", (rec_id,)
    ).fetchone()
    assert rec["late_minutes"] == 0


def test_edit_resolution_creates_history(tmp_path):
    repo, rec_id = setup_repo_with_record(tmp_path)
    apply_resolution(repo, rec_id, "sakit")
    apply_resolution(repo, rec_id, "cuti")
    history = repo.conn.execute(
        "SELECT * FROM record_history WHERE record_id=?", (rec_id,)
    ).fetchall()
    assert any(h["changed_field"] == "resolution.reason_code" for h in history)


def test_get_resolution_label_returns_text():
    assert get_resolution_label("sakit") == "Izin Sakit"
    assert get_resolution_label("tugas_lapangan") == "Tugas Lapangan"


def test_requires_extra_input():
    assert requires_extra_input("tugas_lapangan") == "location"
    assert requires_extra_input("izin_pagi") == "reason_detail"
    assert requires_extra_input("sakit") is None
