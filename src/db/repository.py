import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def _resolve_schema_path() -> Path:
    """schema.sql ships with the app. PyInstaller --onefile extracts it
    to sys._MEIPASS; from source it sits next to repository.py."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "src" / "db" / "schema.sql"
    return Path(__file__).parent / "schema.sql"


SCHEMA_PATH = _resolve_schema_path()


class Repository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def init_schema(self):
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            self.conn.executescript(f.read())
        self.conn.commit()

    def list_tables(self) -> list[str]:
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        return [row["name"] for row in cursor.fetchall()]

    def close(self):
        self.conn.close()

    def upsert_employee(self, staff_no: str, name: str, department: str | None = None) -> int:
        existing = self.get_employee_by_staff_no(staff_no)
        if existing:
            self.conn.execute(
                "UPDATE employees SET name=?, department=COALESCE(?, department) WHERE id=?",
                (name, department, existing["id"]),
            )
            self.conn.commit()
            return existing["id"]
        cursor = self.conn.execute(
            "INSERT INTO employees (staff_no, name, department, created_at) VALUES (?, ?, ?, ?)",
            (staff_no, name, department, datetime.now().isoformat()),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_employee_by_staff_no(self, staff_no: str):
        cursor = self.conn.execute(
            "SELECT * FROM employees WHERE staff_no=?", (staff_no,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def insert_attendance(self, record: dict) -> int:
        fields = ",".join(record.keys())
        placeholders = ",".join("?" for _ in record)
        cursor = self.conn.execute(
            f"INSERT INTO attendance_records ({fields}) VALUES ({placeholders})",
            list(record.values()),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_attendance(self, employee_id: int, date: str):
        cursor = self.conn.execute(
            "SELECT * FROM attendance_records WHERE employee_id=? AND date=?",
            (employee_id, date),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def list_attendance_in_range(self, start_date: str, end_date: str) -> list[dict]:
        cursor = self.conn.execute(
            """SELECT ar.*, e.name AS employee_name, e.staff_no
               FROM attendance_records ar
               JOIN employees e ON ar.employee_id = e.id
               WHERE ar.date >= ? AND ar.date <= ?
               ORDER BY ar.date, e.name""",
            (start_date, end_date),
        )
        return [dict(row) for row in cursor.fetchall()]

    def create_import_batch(self, filename: str, date_start: str, date_end: str) -> int:
        cursor = self.conn.execute(
            """INSERT INTO import_batches
               (filename, imported_at, date_range_start, date_range_end)
               VALUES (?, ?, ?, ?)""",
            (filename, datetime.now().isoformat(), date_start, date_end),
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_batch_counts(self, batch_id: int, inserted: int, kept: int,
                            overwritten: int, snapshot_path: str | None = None):
        self.conn.execute(
            """UPDATE import_batches
               SET rows_inserted=?, rows_kept=?, rows_overwritten=?, snapshot_path=?
               WHERE id=?""",
            (inserted, kept, overwritten, snapshot_path, batch_id),
        )
        self.conn.commit()

    def update_attendance(self, record_id: int, fields: dict):
        set_clause = ", ".join(f"{k}=?" for k in fields.keys())
        values = list(fields.values()) + [record_id]
        self.conn.execute(
            f"UPDATE attendance_records SET {set_clause} WHERE id=?", values
        )
        self.conn.commit()

    def insert_history(self, record_id: int, field: str, old_val, new_val,
                       changed_by: str, batch_id: int | None = None):
        self.conn.execute(
            """INSERT INTO record_history
               (record_id, changed_field, old_value, new_value, changed_at, changed_by, batch_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (record_id, field,
             str(old_val) if old_val is not None else None,
             str(new_val) if new_val is not None else None,
             datetime.now().isoformat(), changed_by, batch_id),
        )
        self.conn.commit()

    def list_batches(self, limit: int = 50) -> list[dict]:
        cursor = self.conn.execute(
            "SELECT * FROM import_batches ORDER BY imported_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def upsert_resolution(self, record_id: int, reason_code: str,
                          location: str | None = None,
                          reason_detail: str | None = None) -> int:
        existing = self.get_resolution(record_id)
        now = datetime.now().isoformat()
        if existing:
            # Track edits in history
            for field, old_val, new_val in [
                ("resolution.reason_code", existing["reason_code"], reason_code),
                ("resolution.location", existing["location"], location),
                ("resolution.reason_detail", existing["reason_detail"], reason_detail),
            ]:
                if str(old_val) != str(new_val):
                    self.insert_history(record_id, field, old_val, new_val,
                                        changed_by="user-edit")
            self.conn.execute(
                """UPDATE resolutions SET reason_code=?, location=?, reason_detail=?,
                   edited_at=?, edit_count=edit_count+1 WHERE record_id=?""",
                (reason_code, location, reason_detail, now, record_id),
            )
            self.conn.commit()
            return existing["id"]
        cursor = self.conn.execute(
            """INSERT INTO resolutions
               (record_id, reason_code, location, reason_detail, resolved_at)
               VALUES (?, ?, ?, ?, ?)""",
            (record_id, reason_code, location, reason_detail, now),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_resolution(self, record_id: int):
        cursor = self.conn.execute(
            "SELECT * FROM resolutions WHERE record_id=?", (record_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def delete_resolution(self, record_id: int):
        existing = self.get_resolution(record_id)
        if existing:
            self.insert_history(record_id, "resolution.deleted",
                                existing["reason_code"], None, "user-edit")
            self.conn.execute("DELETE FROM resolutions WHERE record_id=?", (record_id,))
            self.conn.commit()

    def list_pending_issues(self, start_date: str, end_date: str) -> list[dict]:
        """Records with issue_case in (A,B,C,F) that lack a resolution."""
        cursor = self.conn.execute(
            """SELECT ar.*, e.name AS employee_name, e.staff_no
               FROM attendance_records ar
               JOIN employees e ON ar.employee_id = e.id
               LEFT JOIN resolutions r ON r.record_id = ar.id
               WHERE ar.date >= ? AND ar.date <= ?
                 AND ar.issue_case IN ('A','B','C','F')
                 AND r.id IS NULL
               ORDER BY ar.date, e.name""",
            (start_date, end_date),
        )
        return [dict(row) for row in cursor.fetchall()]

    def list_resolved_issues(self, start_date: str, end_date: str) -> list[dict]:
        cursor = self.conn.execute(
            """SELECT ar.*, e.name AS employee_name, e.staff_no,
                      r.reason_code, r.location, r.reason_detail, r.resolved_at
               FROM attendance_records ar
               JOIN employees e ON ar.employee_id = e.id
               JOIN resolutions r ON r.record_id = ar.id
               WHERE ar.date >= ? AND ar.date <= ?
               ORDER BY ar.date, e.name""",
            (start_date, end_date),
        )
        return [dict(row) for row in cursor.fetchall()]

    def list_history_for_record(self, record_id: int) -> list[dict]:
        cursor = self.conn.execute(
            """SELECT * FROM record_history
               WHERE record_id=? ORDER BY changed_at DESC""",
            (record_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def list_attendance_with_resolutions(self, start_date: str, end_date: str,
                                          search: str = "") -> list[dict]:
        pattern = f"%{search}%" if search else "%"
        cursor = self.conn.execute(
            """SELECT ar.*, e.name AS employee_name, e.staff_no,
                      r.reason_code, r.location, r.reason_detail
               FROM attendance_records ar
               JOIN employees e ON ar.employee_id = e.id
               LEFT JOIN resolutions r ON r.record_id = ar.id
               WHERE ar.date >= ? AND ar.date <= ?
                 AND (e.name LIKE ? OR e.staff_no LIKE ?)
                 AND ar.day_type = 'Hari Kerja'
               ORDER BY ar.date DESC, e.name""",
            (start_date, end_date, pattern, pattern),
        )
        return [dict(row) for row in cursor.fetchall()]

    def list_monthly_grid(self, year: int, month: int,
                          staff_no_filter: str | None = None) -> list[dict]:
        """Return one row per (active employee, day-of-month) for the given period.

        Rows where attendance_records doesn't exist are skeleton rows with
        actual_in/out=None but day_name and day_type populated. Used by Main
        Database page to show 'format ready, awaiting import' rows.
        """
        from calendar import monthrange
        from datetime import date as _date

        days_in_month = monthrange(year, month)[1]
        day_name_id = {0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis",
                       4: "Jumat", 5: "Sabtu", 6: "Minggu"}

        # Fetch employees
        if staff_no_filter:
            emp_cursor = self.conn.execute(
                "SELECT * FROM employees WHERE active=1 AND staff_no=? ORDER BY name",
                (staff_no_filter,),
            )
        else:
            emp_cursor = self.conn.execute(
                "SELECT * FROM employees WHERE active=1 ORDER BY name"
            )
        employees = [dict(row) for row in emp_cursor.fetchall()]

        # Fetch all attendance + resolution data for this month in one shot
        start_iso = f"{year:04d}-{month:02d}-01"
        end_iso = f"{year:04d}-{month:02d}-{days_in_month:02d}"
        data_cursor = self.conn.execute(
            """SELECT ar.*, r.reason_code, r.location, r.reason_detail
               FROM attendance_records ar
               LEFT JOIN resolutions r ON r.record_id = ar.id
               WHERE ar.date >= ? AND ar.date <= ?""",
            (start_iso, end_iso),
        )
        by_emp_date = {}
        for row in data_cursor.fetchall():
            by_emp_date[(row["employee_id"], row["date"])] = dict(row)

        # Build the grid
        grid = []
        for emp in employees:
            for day in range(1, days_in_month + 1):
                d = _date(year, month, day)
                iso = d.isoformat()
                weekday = d.weekday()
                day_type = "Istirahat" if weekday >= 5 else "Hari Kerja"

                existing = by_emp_date.get((emp["id"], iso))
                if existing:
                    row = existing
                    row["staff_no"] = emp["staff_no"]
                    row["name"] = emp["name"]
                    row["department"] = emp["department"]
                    # Make sure day_name/day_type are populated even if blank in DB
                    row["day_name"] = row.get("day_name") or day_name_id[weekday]
                    row["day_type"] = row.get("day_type") or day_type
                else:
                    row = {
                        "id": None,
                        "employee_id": emp["id"],
                        "staff_no": emp["staff_no"],
                        "name": emp["name"],
                        "department": emp["department"],
                        "date": iso,
                        "day_name": day_name_id[weekday],
                        "day_type": day_type,
                        "schedule_in": None, "schedule_out": None,
                        "actual_in": None, "actual_out": None,
                        "late_minutes": None, "early_leave_minutes": None,
                        "work_hours": None, "overtime_hours": None,
                        "absent_flag": None, "forgot_punch_flag": None,
                        "issue_case": None, "import_batch_id": None,
                        "reason_code": None, "location": None, "reason_detail": None,
                    }
                grid.append(row)
        return grid
