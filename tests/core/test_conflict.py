import json
from pathlib import Path
from src.db.repository import Repository
from src.core.conflict import resolve_import, ConflictPolicy


def setup_repo(tmp_path):
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    return repo


def make_record(staff_no="1002", date="2026-04-01", actual_in="08:00", actual_out="16:00"):
    return {
        "staff_no": staff_no, "name": "ANDIKA", "department": "ARGA DIRGA",
        "date": date, "day_name": "Rabu", "day_type": "Hari Kerja",
        "schedule_in": "08:00", "schedule_out": "16:00",
        "actual_in": actual_in, "actual_out": actual_out,
        "late_minutes": 0, "early_leave_minutes": 0, "work_hours": 8.0,
        "overtime_hours": 0, "absent_flag": 0, "forgot_punch_flag": 0,
    }


def test_first_import_inserts_all(tmp_path):
    repo = setup_repo(tmp_path)
    parsed = [make_record(date="2026-04-01"), make_record(date="2026-04-02")]
    summary = resolve_import(repo, parsed, "test.xls",
                              snapshot_dir=str(tmp_path / "backups"),
                              policy=ConflictPolicy.KEEP_EXISTING)
    assert summary["inserted"] == 2
    assert summary["kept"] == 0
    assert summary["overwritten"] == 0


def test_second_import_keep_existing(tmp_path):
    repo = setup_repo(tmp_path)
    resolve_import(repo, [make_record(actual_in="08:00")], "first.xls",
                   snapshot_dir=str(tmp_path / "backups"),
                   policy=ConflictPolicy.KEEP_EXISTING)
    summary = resolve_import(repo, [make_record(actual_in="08:30")], "second.xls",
                              snapshot_dir=str(tmp_path / "backups"),
                              policy=ConflictPolicy.KEEP_EXISTING)
    assert summary["inserted"] == 0
    assert summary["kept"] == 1
    assert summary["overwritten"] == 0
    # Original value preserved
    emp = repo.get_employee_by_staff_no("1002")
    rec = repo.get_attendance(emp["id"], "2026-04-01")
    assert rec["actual_in"] == "08:00"


def test_second_import_overwrite_creates_history(tmp_path):
    repo = setup_repo(tmp_path)
    resolve_import(repo, [make_record(actual_in="08:00")], "first.xls",
                   snapshot_dir=str(tmp_path / "backups"),
                   policy=ConflictPolicy.KEEP_EXISTING)
    summary = resolve_import(repo, [make_record(actual_in="08:30")], "second.xls",
                              snapshot_dir=str(tmp_path / "backups"),
                              policy=ConflictPolicy.OVERWRITE)
    assert summary["overwritten"] == 1
    # New value applied
    emp = repo.get_employee_by_staff_no("1002")
    rec = repo.get_attendance(emp["id"], "2026-04-01")
    assert rec["actual_in"] == "08:30"
    # History entry created
    cursor = repo.conn.execute("SELECT * FROM record_history WHERE changed_by='import'")
    history = cursor.fetchall()
    assert len(history) >= 1


def test_snapshot_file_written_on_conflict(tmp_path):
    repo = setup_repo(tmp_path)
    snapshot_dir = tmp_path / "backups"
    resolve_import(repo, [make_record()], "first.xls",
                   snapshot_dir=str(snapshot_dir), policy=ConflictPolicy.KEEP_EXISTING)
    resolve_import(repo, [make_record(actual_in="09:00")], "second.xls",
                   snapshot_dir=str(snapshot_dir), policy=ConflictPolicy.OVERWRITE)
    snapshots = list(snapshot_dir.glob("snapshot_*.json"))
    assert len(snapshots) >= 1
    data = json.loads(snapshots[0].read_text())
    assert "records" in data


from src.core.conflict import rollback_batch

def test_rollback_batch_restores_overwritten_values(tmp_path):
    repo = setup_repo(tmp_path)
    snapshot_dir = tmp_path / "backups"

    # First import: original value 08:00
    resolve_import(repo, [make_record(actual_in="08:00")], "first.xls",
                   snapshot_dir=str(snapshot_dir),
                   policy=ConflictPolicy.KEEP_EXISTING)

    # Second import OVERWRITE: changed to 09:00 — snapshot captured
    summary = resolve_import(repo, [make_record(actual_in="09:00")], "second.xls",
                              snapshot_dir=str(snapshot_dir),
                              policy=ConflictPolicy.OVERWRITE)
    overwrite_batch_id = summary["batch_id"]

    # Verify it was actually overwritten
    emp = repo.get_employee_by_staff_no("1002")
    rec = repo.get_attendance(emp["id"], "2026-04-01")
    assert rec["actual_in"] == "09:00"

    # Rollback the OVERWRITE batch
    restored = rollback_batch(repo, overwrite_batch_id)
    assert restored == 1

    # Verify original value restored
    rec = repo.get_attendance(emp["id"], "2026-04-01")
    assert rec["actual_in"] == "08:00"

    # Verify rollback history entry
    cursor = repo.conn.execute(
        "SELECT * FROM record_history WHERE changed_by='rollback'"
    )
    rollback_history = cursor.fetchall()
    assert len(rollback_history) == 1

def test_rollback_batch_returns_zero_for_batch_without_snapshot(tmp_path):
    repo = setup_repo(tmp_path)
    snapshot_dir = tmp_path / "backups"

    # First import has no conflicts → no snapshot file
    summary = resolve_import(repo, [make_record()], "first.xls",
                              snapshot_dir=str(snapshot_dir),
                              policy=ConflictPolicy.KEEP_EXISTING)
    first_batch_id = summary["batch_id"]
    assert summary["snapshot_path"] is None

    # Trying to rollback should return 0 (nothing to restore)
    restored = rollback_batch(repo, first_batch_id)
    assert restored == 0

def test_rollback_batch_returns_zero_for_unknown_batch(tmp_path):
    repo = setup_repo(tmp_path)
    restored = rollback_batch(repo, batch_id=99999)
    assert restored == 0
