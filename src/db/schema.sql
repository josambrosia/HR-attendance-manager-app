CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_no TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    department TEXT,
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attendance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    day_name TEXT,
    day_type TEXT,
    schedule_in TEXT,
    schedule_out TEXT,
    actual_in TEXT,
    actual_out TEXT,
    late_minutes INTEGER DEFAULT 0,
    early_leave_minutes INTEGER DEFAULT 0,
    work_hours REAL DEFAULT 0,
    overtime_hours REAL DEFAULT 0,
    absent_flag INTEGER DEFAULT 0,
    forgot_punch_flag INTEGER DEFAULT 0,
    issue_case TEXT,
    import_batch_id INTEGER,
    UNIQUE(employee_id, date),
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (import_batch_id) REFERENCES import_batches(id)
);

CREATE TABLE IF NOT EXISTS resolutions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER UNIQUE NOT NULL,
    reason_code TEXT NOT NULL,
    location TEXT,
    reason_detail TEXT,
    resolved_at TEXT NOT NULL,
    edited_at TEXT,
    edit_count INTEGER DEFAULT 0,
    FOREIGN KEY (record_id) REFERENCES attendance_records(id)
);

CREATE TABLE IF NOT EXISTS import_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    date_range_start TEXT,
    date_range_end TEXT,
    rows_inserted INTEGER DEFAULT 0,
    rows_kept INTEGER DEFAULT 0,
    rows_overwritten INTEGER DEFAULT 0,
    snapshot_path TEXT
);

CREATE TABLE IF NOT EXISTS record_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER NOT NULL,
    changed_field TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_at TEXT NOT NULL,
    changed_by TEXT NOT NULL,
    batch_id INTEGER,
    FOREIGN KEY (record_id) REFERENCES attendance_records(id),
    FOREIGN KEY (batch_id) REFERENCES import_batches(id)
);

CREATE INDEX IF NOT EXISTS idx_records_date ON attendance_records(date);
CREATE INDEX IF NOT EXISTS idx_records_employee ON attendance_records(employee_id);
CREATE INDEX IF NOT EXISTS idx_records_batch ON attendance_records(import_batch_id);
CREATE INDEX IF NOT EXISTS idx_history_record ON record_history(record_id);
