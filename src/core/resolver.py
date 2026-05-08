from src.db.repository import Repository
from src.core.constants import REASON_CODES


def apply_resolution(
    repo: Repository,
    record_id: int,
    reason_code: str,
    location: str | None = None,
    reason_detail: str | None = None,
    penalty_minutes: int | None = 16,
) -> int:
    """Save (or update) the resolution for a record. Auto-applies the
    Lupa Absen penalty if reason is 'lupa_absen' and penalty_minutes is set."""
    if reason_code not in REASON_CODES:
        raise ValueError(f"Unknown reason code: {reason_code}")

    res_id = repo.upsert_resolution(
        record_id, reason_code, location=location, reason_detail=reason_detail
    )

    # Special behavior: lupa_absen adds penalty to late_minutes
    if reason_code == "lupa_absen" and penalty_minutes:
        existing = repo.conn.execute(
            "SELECT late_minutes FROM attendance_records WHERE id=?", (record_id,)
        ).fetchone()
        old_late = existing["late_minutes"] if existing else 0
        # Only add penalty once - track via history check
        already_applied = repo.conn.execute(
            """SELECT 1 FROM record_history
               WHERE record_id=? AND changed_field='lupa_absen_penalty'""",
            (record_id,),
        ).fetchone()
        if not already_applied:
            new_late = old_late + penalty_minutes
            repo.update_attendance(record_id, {"late_minutes": new_late})
            repo.insert_history(record_id, "lupa_absen_penalty",
                                old_late, new_late, "user-edit")

    return res_id


def remove_resolution(repo: Repository, record_id: int):
    """Clear a resolution (record returns to pending)."""
    repo.delete_resolution(record_id)


def get_resolution_label(reason_code: str) -> str:
    return REASON_CODES.get(reason_code, {}).get("label", reason_code)


def requires_extra_input(reason_code: str) -> str | None:
    """Returns 'location', 'reason_detail', or None."""
    return REASON_CODES.get(reason_code, {}).get("extra")


def list_all_reason_options() -> list[tuple[str, str, str | None]]:
    """Returns list of (code, label, extra_input_type)."""
    return [(code, info["label"], info["extra"])
            for code, info in REASON_CODES.items()]
