import json
from enum import Enum
from pathlib import Path
from datetime import datetime
from src.db.repository import Repository
from src.core.issue_detector import classify_issue


class ConflictPolicy(Enum):
    KEEP_EXISTING = "keep"
    OVERWRITE = "overwrite"


# Fields the parser produces that map to attendance_records columns
RECORD_FIELDS = [
    "date", "day_name", "day_type", "schedule_in", "schedule_out",
    "actual_in", "actual_out", "late_minutes", "early_leave_minutes",
    "work_hours", "overtime_hours", "absent_flag", "forgot_punch_flag",
]


def resolve_import(
    repo: Repository,
    parsed_records: list[dict],
    filename: str,
    snapshot_dir: str,
    policy: ConflictPolicy = ConflictPolicy.KEEP_EXISTING,
    settings: dict | None = None,
) -> dict:
    """
    Apply a parsed batch to the DB, resolving (employee, date) conflicts per policy.
    Snapshots affected records BEFORE any change. Returns counts summary.
    """
    if not parsed_records:
        return {"inserted": 0, "kept": 0, "overwritten": 0, "batch_id": None}

    settings = settings or {}
    late_thr = settings.get("late_threshold_minutes", 15)
    pc_thr = settings.get("pulang_cepat_threshold_minutes", 0)

    dates = [r["date"] for r in parsed_records]
    batch_id = repo.create_import_batch(filename, min(dates), max(dates))

    inserted = kept = overwritten = 0
    conflicting_old_records = []

    for rec in parsed_records:
        emp_id = repo.upsert_employee(
            staff_no=rec["staff_no"],
            name=rec["name"],
            department=rec.get("department"),
        )
        existing = repo.get_attendance(emp_id, rec["date"])

        # Detect issue case for the new record
        new_case = classify_issue(rec, late_threshold=late_thr,
                                   pulang_cepat_threshold=pc_thr)

        record_data = {k: rec.get(k) for k in RECORD_FIELDS}
        record_data["employee_id"] = emp_id
        record_data["issue_case"] = new_case
        record_data["import_batch_id"] = batch_id

        if existing is None:
            repo.insert_attendance(record_data)
            inserted += 1
        elif policy == ConflictPolicy.KEEP_EXISTING:
            kept += 1
        else:  # OVERWRITE
            conflicting_old_records.append(dict(existing))
            for field in RECORD_FIELDS + ["issue_case"]:
                old_val = existing.get(field)
                new_val = record_data.get(field)
                if str(old_val) != str(new_val):
                    repo.insert_history(existing["id"], field, old_val, new_val,
                                        changed_by="import", batch_id=batch_id)
            update_fields = {k: record_data[k] for k in RECORD_FIELDS + ["issue_case"]}
            repo.update_attendance(existing["id"], update_fields)
            overwritten += 1

    # Write snapshot if there were conflicts
    snapshot_path = None
    if conflicting_old_records:
        snapshot_dir_p = Path(snapshot_dir)
        snapshot_dir_p.mkdir(parents=True, exist_ok=True)
        snapshot_path = str(snapshot_dir_p / f"snapshot_{batch_id}.json")
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump({
                "batch_id": batch_id, "filename": filename,
                "snapshotted_at": datetime.now().isoformat(),
                "records": conflicting_old_records,
            }, f, indent=2, default=str)

    repo.update_batch_counts(batch_id, inserted, kept, overwritten, snapshot_path)
    return {
        "inserted": inserted, "kept": kept, "overwritten": overwritten,
        "batch_id": batch_id, "snapshot_path": snapshot_path,
    }


def detect_conflicts(repo: Repository, parsed_records: list[dict]) -> list[dict]:
    """Return list of (parsed_record, existing_record) pairs that overlap.
    Used by UI to show conflict dialog before commit."""
    conflicts = []
    for rec in parsed_records:
        emp = repo.get_employee_by_staff_no(rec["staff_no"])
        if not emp:
            continue
        existing = repo.get_attendance(emp["id"], rec["date"])
        if existing:
            conflicts.append({"new": rec, "existing": dict(existing)})
    return conflicts


def rollback_batch(repo: Repository, batch_id: int) -> int:
    """Restore records from a batch's snapshot. Returns count restored."""
    cursor = repo.conn.execute(
        "SELECT snapshot_path FROM import_batches WHERE id=?", (batch_id,)
    )
    row = cursor.fetchone()
    if not row or not row["snapshot_path"]:
        return 0
    snap_path = Path(row["snapshot_path"])
    if not snap_path.exists():
        return 0
    data = json.loads(snap_path.read_text())
    restored = 0
    for old_rec in data["records"]:
        rec_id = old_rec["id"]
        update_fields = {k: old_rec[k] for k in RECORD_FIELDS + ["issue_case"]
                          if k in old_rec}
        repo.update_attendance(rec_id, update_fields)
        repo.insert_history(rec_id, "rollback", None, f"batch {batch_id}",
                            changed_by="rollback", batch_id=batch_id)
        restored += 1
    return restored
