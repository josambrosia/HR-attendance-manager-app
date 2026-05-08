import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


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
