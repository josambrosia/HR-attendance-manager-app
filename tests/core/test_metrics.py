from datetime import date
from src.db.repository import Repository
from src.core.metrics import (
    weekly_summary, hall_of_late, coaching_candidates,
    repeat_offenders, distribusi_alasan, hari_paling_telat,
    best_performer, late_trend
)

def setup_repo(tmp_path):
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    return repo

def add_record(repo, staff_no, name, d, late=0, actual_in="08:00", actual_out="16:00",
               case=None, day_type="Hari Kerja"):
    emp_id = repo.upsert_employee(staff_no, name)
    return repo.insert_attendance({
        "employee_id": emp_id, "date": d, "day_name": "Senin",
        "day_type": day_type,
        "schedule_in": "08:00", "schedule_out": "16:00",
        "actual_in": actual_in, "actual_out": actual_out,
        "late_minutes": late, "early_leave_minutes": 0,
        "work_hours": 8.0, "overtime_hours": 0,
        "absent_flag": 0, "forgot_punch_flag": 0,
        "issue_case": case, "import_batch_id": None,
    })

def test_weekly_summary_counts(tmp_path):
    repo = setup_repo(tmp_path)
    add_record(repo, "1", "A", "2026-04-01", late=10)
    add_record(repo, "2", "B", "2026-04-01", late=0)
    add_record(repo, "3", "C", "2026-04-01", actual_in=None, actual_out=None, case="A")
    summary = weekly_summary(repo, "2026-04-01", "2026-04-07")
    assert summary["total_issues"] >= 1
    assert summary["pending_issues"] >= 1
    assert summary["total_late_minutes"] == 10
    assert summary["attendance_rate"] is not None

def test_hall_of_late_sorts_descending(tmp_path):
    repo = setup_repo(tmp_path)
    add_record(repo, "1", "A", "2026-04-01", late=10)
    add_record(repo, "2", "B", "2026-04-01", late=50)
    add_record(repo, "3", "C", "2026-04-01", late=30)
    ranking = hall_of_late(repo, "2026-04-01", "2026-04-07")
    assert [r["name"] for r in ranking] == ["B", "C", "A"]
    assert ranking[0]["total_late"] == 50

def test_coaching_candidates_above_threshold(tmp_path):
    repo = setup_repo(tmp_path)
    add_record(repo, "1", "TOMBAK", "2026-04-01", late=80)
    add_record(repo, "2", "ANDIKA", "2026-04-01", late=20)
    candidates = coaching_candidates(repo, "2026-04-01", "2026-04-07", threshold=75)
    assert len(candidates) == 1
    assert candidates[0]["name"] == "TOMBAK"

def test_repeat_offenders_three_weeks(tmp_path):
    repo = setup_repo(tmp_path)
    # TOMBAK late in 3 consecutive weeks
    for d in ["2026-03-16", "2026-03-23", "2026-03-30"]:
        add_record(repo, "1", "TOMBAK", d, late=10)
    # ANDIKA late only this week
    add_record(repo, "2", "ANDIKA", "2026-03-30", late=10)
    offenders = repeat_offenders(repo, "2026-03-30", min_weeks=3)
    names = [o["name"] for o in offenders]
    assert "TOMBAK" in names
    assert "ANDIKA" not in names

def test_best_performer_no_late_no_issues(tmp_path):
    repo = setup_repo(tmp_path)
    add_record(repo, "1", "A", "2026-04-01", late=0)
    add_record(repo, "2", "B", "2026-04-01", late=10)
    best = best_performer(repo, "2026-04-01", "2026-04-07")
    assert best is not None
    assert best["name"] == "A"
