from datetime import datetime, timedelta
from src.db.repository import Repository


def _hari_kerja_records(repo: Repository, start: str, end: str) -> list[dict]:
    cursor = repo.conn.execute(
        """SELECT ar.*, e.name AS name, e.staff_no FROM attendance_records ar
           JOIN employees e ON ar.employee_id=e.id
           WHERE ar.date>=? AND ar.date<=? AND ar.day_type='Hari Kerja'""",
        (start, end),
    )
    return [dict(row) for row in cursor.fetchall()]


def _resolved_records(repo: Repository, start: str, end: str) -> list[dict]:
    cursor = repo.conn.execute(
        """SELECT ar.id, r.reason_code FROM attendance_records ar
           JOIN resolutions r ON r.record_id=ar.id
           WHERE ar.date>=? AND ar.date<=?""",
        (start, end),
    )
    return [dict(row) for row in cursor.fetchall()]


def weekly_summary(repo: Repository, start: str, end: str) -> dict:
    records = _hari_kerja_records(repo, start, end)
    issues_records = [r for r in records if r["issue_case"] in ("A", "B", "C", "F")]
    resolved = _resolved_records(repo, start, end)
    resolved_ids = {r["id"] for r in resolved}
    pending = [r for r in issues_records if r["id"] not in resolved_ids]

    total_late = sum(r["late_minutes"] or 0 for r in records)
    attended = len([r for r in records if r["actual_in"] and r["actual_out"]])
    rate = (attended / len(records) * 100) if records else 0

    return {
        "total_issues": len(issues_records),
        "pending_issues": len(pending),
        "resolved_issues": len(issues_records) - len(pending),
        "total_late_minutes": total_late,
        "attendance_rate": round(rate, 1),
        "total_records": len(records),
    }


def hall_of_late(repo: Repository, start: str, end: str) -> list[dict]:
    records = _hari_kerja_records(repo, start, end)
    by_employee: dict[str, dict] = {}
    for r in records:
        if not r["late_minutes"]:
            continue
        key = r["staff_no"]
        if key not in by_employee:
            by_employee[key] = {
                "staff_no": r["staff_no"], "name": r["name"],
                "total_late": 0, "days_late": 0, "max_late": 0,
                "max_late_date": None,
            }
        d = by_employee[key]
        d["total_late"] += r["late_minutes"]
        d["days_late"] += 1
        if r["late_minutes"] > d["max_late"]:
            d["max_late"] = r["late_minutes"]
            d["max_late_date"] = r["date"]
    return sorted(by_employee.values(), key=lambda x: x["total_late"], reverse=True)


def coaching_candidates(repo: Repository, start: str, end: str, threshold: int = 75) -> list[dict]:
    return [e for e in hall_of_late(repo, start, end) if e["total_late"] > threshold]


def repeat_offenders(repo: Repository, week_end: str, min_weeks: int = 3) -> list[dict]:
    """Employees with late_minutes > 0 in min_weeks consecutive weeks ending at week_end."""
    end_date = datetime.fromisoformat(week_end).date()
    weeks = []
    for i in range(min_weeks):
        week_end_d = end_date - timedelta(weeks=i)
        week_start_d = week_end_d - timedelta(days=6)
        cursor = repo.conn.execute(
            """SELECT DISTINCT e.staff_no, e.name FROM attendance_records ar
               JOIN employees e ON ar.employee_id=e.id
               WHERE ar.date>=? AND ar.date<=? AND ar.late_minutes>0""",
            (week_start_d.isoformat(), week_end_d.isoformat()),
        )
        weeks.append({(row["staff_no"], row["name"]) for row in cursor.fetchall()})
    repeat = set.intersection(*weeks) if weeks else set()
    return [{"staff_no": s, "name": n} for s, n in repeat]


def distribusi_alasan(repo: Repository, start: str, end: str) -> list[dict]:
    cursor = repo.conn.execute(
        """SELECT r.reason_code, COUNT(*) AS cnt
           FROM resolutions r
           JOIN attendance_records ar ON r.record_id=ar.id
           WHERE ar.date>=? AND ar.date<=?
           GROUP BY r.reason_code ORDER BY cnt DESC""",
        (start, end),
    )
    return [dict(row) for row in cursor.fetchall()]


def hari_paling_telat(repo: Repository, start: str, end: str) -> dict | None:
    records = _hari_kerja_records(repo, start, end)
    by_day: dict[str, dict] = {}
    for r in records:
        d = r["day_name"].strip()
        if d not in by_day:
            by_day[d] = {"day_name": d, "total_late": 0, "count_late": 0}
        if r["late_minutes"]:
            by_day[d]["total_late"] += r["late_minutes"]
            by_day[d]["count_late"] += 1
    if not by_day:
        return None
    return max(by_day.values(), key=lambda x: x["total_late"])


def best_performer(repo: Repository, start: str, end: str) -> dict | None:
    records = _hari_kerja_records(repo, start, end)
    by_employee: dict[str, dict] = {}
    for r in records:
        key = r["staff_no"]
        if key not in by_employee:
            by_employee[key] = {
                "staff_no": r["staff_no"], "name": r["name"],
                "total_late": 0, "days": 0, "complete_days": 0,
                "issues": 0,
            }
        d = by_employee[key]
        d["days"] += 1
        d["total_late"] += r["late_minutes"] or 0
        if r["actual_in"] and r["actual_out"]:
            d["complete_days"] += 1
        if r["issue_case"] in ("A", "B", "C", "F"):
            d["issues"] += 1
    candidates = [e for e in by_employee.values()
                  if e["total_late"] == 0 and e["issues"] == 0 and e["days"] > 0]
    if not candidates:
        return None
    return max(candidates, key=lambda x: x["complete_days"])


def late_trend(repo: Repository, current_start: str, current_end: str) -> dict:
    """% change in total_late_minutes vs previous week."""
    cur = weekly_summary(repo, current_start, current_end)
    prev_end = (datetime.fromisoformat(current_start).date() - timedelta(days=1)).isoformat()
    prev_start = (datetime.fromisoformat(prev_end).date() - timedelta(days=6)).isoformat()
    prev = weekly_summary(repo, prev_start, prev_end)
    if prev["total_late_minutes"] == 0:
        return {"change_pct": None, "current": cur["total_late_minutes"],
                "previous": prev["total_late_minutes"]}
    change = ((cur["total_late_minutes"] - prev["total_late_minutes"])
              / prev["total_late_minutes"] * 100)
    return {"change_pct": round(change, 1),
            "current": cur["total_late_minutes"],
            "previous": prev["total_late_minutes"]}
