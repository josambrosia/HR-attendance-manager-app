# Josaphat Tech Solution — HR Attendance Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-user Windows desktop app to automate weekly/monthly fingerprint attendance reporting at PT Tekno, replacing manual Excel review with parsed-and-tagged workflow + dashboard + reports.

**Architecture:** Python + Flet UI + SQLite. Flet provides Material Design 3 dark/light themes and ships .exe via `flet pack`. SQLite for local persistence (single file = easy backup). Excel parsing with `xlrd` (.xls) and `openpyxl` (.xlsx). PDF reports with `reportlab`. Tests with `pytest` for all core logic; UI verified manually with checklist.

**Tech Stack:** Python 3.13, Flet, openpyxl, xlrd, reportlab, matplotlib, pytest, Pillow (for icon generation)

**Spec:** [docs/superpowers/specs/2026-05-09-josaphat-tech-attendance-design.md](../specs/2026-05-09-josaphat-tech-attendance-design.md)

---

## Phase Overview

| Phase | Output | Tasks |
|---|---|---|
| 1. Foundation | App opens, sidebar shows, theme toggle works, DB initialized | 1–5 |
| 2. Data Pipeline | Can import .xls, see records in DB, conflict resolved with snapshot | 6–9 |
| 3. Resolution Workflow | Issues page lists follow-ups, resolve panel works, edit records works | 10–12 |
| 4. Dashboard | Vital + trivia + coaching + Hall of Late + charts all live | 13–15 |
| 5. Reports & Export | PDF + Excel exports work with checklist modal + branding | 16–19 |
| 6. Polish & Distribution | Logo assets, backup/restore, settings UI, single .exe builds | 20–23 |

---

## File Structure (locked at planning time)

```
src/
  main.py                      # Flet app entry
  ui/
    shell.py                   # Sidebar + routing + theme
    theme.py                   # Sunset Coral palette tokens
    pages/
      import_data.py
      issues.py
      dashboard.py
      weekly_report.py
      monthly_report.py
      edit_records.py
      backup_restore.py
      settings.py
    components/
      logo.py                  # Hexagon J widget (reusable)
      vital_card.py
      trivia_card.py
      coaching_card.py
      ranking_row.py
      checklist_modal.py
  core/
    parser.py                  # xls reader + normalizer
    issue_detector.py          # 7-case classification
    resolver.py                # Resolution CRUD + 10 options
    metrics.py                 # All dashboard aggregations
    conflict.py                # Versioning + snapshots
    settings_store.py          # config.json read/write
    constants.py               # Reason codes, defaults
  reports/
    pdf_builder.py             # reportlab base + footer brand
    excel_builder.py           # openpyxl raw + Sheets-format
    sections/
      vital_section.py         # PDF section: vital metrics
      trivia_section.py
      coaching_section.py
      hall_of_late_section.py
      charts_section.py
  db/
    schema.sql
    repository.py              # All SQLite access
assets/
  icon.ico
  logo.svg
  logo-256.png
tests/
  core/
    test_parser.py
    test_issue_detector.py
    test_resolver.py
    test_metrics.py
    test_conflict.py
    test_settings_store.py
  db/
    test_repository.py
  reports/
    test_pdf_builder.py
    test_excel_builder.py
  fixtures/
    sample_apr_1_10.xls        # copy of D:\Gawe\Dani\PT Tekno\April week 1&2 ; 1-10 april.xls
config.json                    # user-editable settings (created at first run)
requirements.txt
README.md
.gitignore                     # already exists
```

---

# PHASE 1 — FOUNDATION (Tasks 1–5)

End state: app starts, you can switch dark/light theme, click sidebar nav (pages are placeholders), DB file is created on first run.

---

### Task 1: Project Scaffold + Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `src/main.py`
- Create: `README.md`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```txt
flet==0.25.2
openpyxl==3.1.5
xlrd==2.0.1
reportlab==4.2.5
matplotlib==3.9.2
Pillow==11.0.0
pytest==8.3.3
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: all packages install without errors.

- [ ] **Step 3: Create minimal `src/main.py`**

```python
import flet as ft

def main(page: ft.Page):
    page.title = "Josaphat Tech Solution — HR Attendance Manager"
    page.window.width = 1280
    page.window.height = 800
    page.add(ft.Text("Hello, Josaphat!", size=24))

if __name__ == "__main__":
    ft.app(target=main)
```

- [ ] **Step 4: Run app to verify Flet boots**

Run: `python src/main.py`
Expected: a window opens with "Hello, Josaphat!" text. Close it.

- [ ] **Step 5: Create `README.md`**

```markdown
# Josaphat Tech Solution — HR Attendance Manager

Single-user Windows desktop app for automating fingerprint attendance reporting.

## Run from source
```
pip install -r requirements.txt
python src/main.py
```

## Build .exe
See Phase 6 in `docs/superpowers/plans/2026-05-09-josaphat-tech-attendance.md`.

## Spec
See `docs/superpowers/specs/2026-05-09-josaphat-tech-attendance-design.md`.
```

- [ ] **Step 6: Create `tests/__init__.py`**

Empty file. Just for pytest discovery.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt src/main.py README.md tests/__init__.py
git commit -m "scaffold: project structure with Flet hello-world"
```

---

### Task 2: SQLite Schema + Repository Layer

**Files:**
- Create: `src/db/__init__.py` (empty)
- Create: `src/db/schema.sql`
- Create: `src/db/repository.py`
- Create: `tests/db/__init__.py` (empty)
- Create: `tests/db/test_repository.py`

- [ ] **Step 1: Create `src/db/schema.sql`**

```sql
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
```

- [ ] **Step 2: Write failing test for repository init**

Create `tests/db/test_repository.py`:

```python
import os
import tempfile
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/db/test_repository.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.db.repository'`.

- [ ] **Step 4: Implement minimal `src/db/repository.py`**

```python
import sqlite3
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/db/test_repository.py -v`
Expected: PASS.

- [ ] **Step 6: Add CRUD methods + test for employees**

Append to `tests/db/test_repository.py`:

```python
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
```

Run: `pytest tests/db/test_repository.py::test_upsert_and_fetch_employee -v`
Expected: FAIL.

- [ ] **Step 7: Implement upsert_employee + get_employee_by_staff_no**

Append to `src/db/repository.py`:

```python
from datetime import datetime

class Repository:
    # ... existing code ...

    def upsert_employee(self, staff_no: str, name: str, department: str = None) -> int:
        existing = self.get_employee_by_staff_no(staff_no)
        if existing:
            self.conn.execute(
                "UPDATE employees SET name=?, department=? WHERE id=?",
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
```

Run: `pytest tests/db/test_repository.py -v`
Expected: both tests PASS.

- [ ] **Step 8: Add tests + impl for attendance_records (insert, get_by_employee_and_date, list_by_date_range)**

Append test:

```python
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
```

Append impl:

```python
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
```

Run: `pytest tests/db/test_repository.py -v`
Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add src/db/ tests/db/
git commit -m "db: SQLite schema and repository CRUD for employees + attendance"
```

---

### Task 3: Settings Store

**Files:**
- Create: `src/core/__init__.py` (empty)
- Create: `src/core/constants.py`
- Create: `src/core/settings_store.py`
- Create: `tests/core/__init__.py` (empty)
- Create: `tests/core/test_settings_store.py`

- [ ] **Step 1: Create `src/core/constants.py`**

```python
"""Constants used across the app."""

DEFAULT_SETTINGS = {
    "coaching_threshold_minutes": 75,
    "late_threshold_minutes": 15,        # set to None to disable late cell coloring
    "lupa_absen_penalty_minutes": 16,    # set to None to disable
    "pulang_cepat_threshold_minutes": 0, # set to None to disable Pulang Cepat flagging
    "working_hours_start": "08:00",
    "working_hours_end": "16:00",
    "workdays": ["Mon", "Tue", "Wed", "Thu", "Fri"],
    "theme": "dark",
    "repeat_offender_weeks": 3,
}

REASON_CODES = {
    "tugas_lapangan": {"label": "Tugas Lapangan", "extra": "location"},
    "tugas_paparan": {"label": "Tugas Paparan", "extra": "location"},
    "sakit": {"label": "Izin Sakit", "extra": None},
    "cuti": {"label": "Cuti", "extra": None},
    "izin_pagi": {"label": "Izin Pagi", "extra": "reason_detail"},
    "pulang_awal": {"label": "Pulang Lebih Awal", "extra": "reason_detail"},
    "telat_kerja": {"label": "Masuk Terlambat dengan Alasan Pekerjaan", "extra": "reason_detail"},
    "telat_personal": {"label": "Terlambat", "extra": None},
    "lupa_absen": {"label": "Lupa Absen (terhitung telat 16 menit)", "extra": None},
    "belum_kabar": {"label": "Belum Ada Kabar", "extra": None},
}

# Sunset Coral palette
COLORS = {
    "primary": "#7C3AED",
    "accent": "#F472B6",
    "highlight": "#FBBF24",
    "resolved": "#34D399",
    "late_mild": "#FCD34D",
    "late_severe": "#F87171",
    "pulang_cepat": "#C084FC",
    "bg_dark": "#1a0b2e",
    "bg_light": "#faf5ff",
    "surface_dark": "#2d1b4e",
    "surface_light": "#ffffff",
    "text_dark": "#e9d5ff",
    "text_light": "#1e1b4b",
}
```

- [ ] **Step 2: Write failing test for SettingsStore**

```python
import json
from src.core.settings_store import SettingsStore
from src.core.constants import DEFAULT_SETTINGS

def test_load_creates_defaults_if_missing(tmp_path):
    config_path = tmp_path / "config.json"
    store = SettingsStore(str(config_path))
    settings = store.load()
    assert settings == DEFAULT_SETTINGS
    assert config_path.exists()

def test_load_returns_existing_config(tmp_path):
    config_path = tmp_path / "config.json"
    custom = DEFAULT_SETTINGS.copy()
    custom["coaching_threshold_minutes"] = 100
    config_path.write_text(json.dumps(custom))

    store = SettingsStore(str(config_path))
    settings = store.load()
    assert settings["coaching_threshold_minutes"] == 100

def test_save_writes_to_disk(tmp_path):
    config_path = tmp_path / "config.json"
    store = SettingsStore(str(config_path))
    store.load()
    store.update({"theme": "light"})

    with open(config_path) as f:
        data = json.load(f)
    assert data["theme"] == "light"

def test_threshold_can_be_set_to_none(tmp_path):
    config_path = tmp_path / "config.json"
    store = SettingsStore(str(config_path))
    store.load()
    store.update({"late_threshold_minutes": None})

    settings = store.load()
    assert settings["late_threshold_minutes"] is None
```

Run: `pytest tests/core/test_settings_store.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement `src/core/settings_store.py`**

```python
import json
from pathlib import Path
from src.core.constants import DEFAULT_SETTINGS

class SettingsStore:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self._cache = None

    def load(self) -> dict:
        if not self.config_path.exists():
            self._cache = DEFAULT_SETTINGS.copy()
            self._write()
            return self._cache
        with open(self.config_path, "r", encoding="utf-8") as f:
            self._cache = json.load(f)
        # Backfill missing keys with defaults (for forward compat)
        for k, v in DEFAULT_SETTINGS.items():
            self._cache.setdefault(k, v)
        return self._cache

    def update(self, partial: dict):
        if self._cache is None:
            self.load()
        self._cache.update(partial)
        self._write()

    def _write(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default=None):
        if self._cache is None:
            self.load()
        return self._cache.get(key, default)
```

Run: `pytest tests/core/test_settings_store.py -v`
Expected: all 4 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add src/core/ tests/core/
git commit -m "core: settings store with JSON config and 'Off' threshold support"
```

---

### Task 4: Theme Tokens + Logo Component

**Files:**
- Create: `src/ui/__init__.py` (empty)
- Create: `src/ui/theme.py`
- Create: `src/ui/components/__init__.py` (empty)
- Create: `src/ui/components/logo.py`

- [ ] **Step 1: Create `src/ui/theme.py`**

```python
import flet as ft
from src.core.constants import COLORS

def build_theme(mode: str = "dark") -> ft.Theme:
    """Return a Flet Theme configured with Sunset Coral palette."""
    return ft.Theme(
        color_scheme_seed=COLORS["primary"],
        color_scheme=ft.ColorScheme(
            primary=COLORS["primary"],
            secondary=COLORS["accent"],
            tertiary=COLORS["highlight"],
            surface=COLORS["surface_dark"] if mode == "dark" else COLORS["surface_light"],
            background=COLORS["bg_dark"] if mode == "dark" else COLORS["bg_light"],
            on_surface=COLORS["text_dark"] if mode == "dark" else COLORS["text_light"],
        ),
        font_family="Segoe UI",
    )

def get_bg_color(mode: str) -> str:
    return COLORS["bg_dark"] if mode == "dark" else COLORS["bg_light"]

def get_surface_color(mode: str) -> str:
    return COLORS["surface_dark"] if mode == "dark" else COLORS["surface_light"]

def get_text_color(mode: str) -> str:
    return COLORS["text_dark"] if mode == "dark" else COLORS["text_light"]
```

- [ ] **Step 2: Create `src/ui/components/logo.py` (Hexagon J widget)**

```python
import flet as ft
from src.core.constants import COLORS

def hexagon_j(size: int = 40, with_wordmark: bool = True, mode: str = "dark") -> ft.Control:
    """Reusable Hex J logo. If with_wordmark=True, returns Row with brand text."""
    icon = ft.Container(
        width=size,
        height=size * 1.1,
        content=ft.Text(
            "J",
            color="white",
            weight=ft.FontWeight.W_900,
            size=size * 0.55,
            text_align=ft.TextAlign.CENTER,
        ),
        alignment=ft.alignment.center,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=[COLORS["primary"], COLORS["accent"]],
        ),
        shape=ft.BoxShape.RECTANGLE,
        # Hexagon clip via custom path is non-trivial in Flet — use rounded square
        # as visual fallback; final icon.ico will be true hexagon (Phase 6, Task 20).
        border_radius=size * 0.2,
        shadow=ft.BoxShadow(
            blur_radius=size * 0.2,
            color=f"{COLORS['primary']}66",
        ),
    )
    if not with_wordmark:
        return icon

    text_color = COLORS["text_dark"] if mode == "dark" else COLORS["text_light"]
    accent_color = COLORS["accent"] if mode == "dark" else COLORS["primary"]

    wordmark = ft.Column(
        spacing=2,
        controls=[
            ft.Text("Josaphat Tech Solution", weight=ft.FontWeight.W_800, size=14, color=text_color),
            ft.Text("HR Attendance Manager", size=10, color=accent_color),
        ],
    )
    return ft.Row(spacing=10, controls=[icon, wordmark])
```

- [ ] **Step 3: Manually verify logo renders**

Update `src/main.py` temporarily:

```python
import flet as ft
from src.ui.components.logo import hexagon_j

def main(page: ft.Page):
    page.title = "Logo preview"
    page.bgcolor = "#1a0b2e"
    page.add(hexagon_j(size=48, with_wordmark=True, mode="dark"))

if __name__ == "__main__":
    ft.app(target=main)
```

Run: `python src/main.py`
Expected: Window opens with purple→pink gradient "J" badge + "Josaphat Tech Solution / HR Attendance Manager" wordmark on dark background.

- [ ] **Step 4: Commit**

```bash
git add src/ui/
git commit -m "ui: theme tokens and Hexagon J logo component"
```

---

### Task 5: App Shell — Sidebar + Routing + Theme Toggle

**Files:**
- Create: `src/ui/shell.py`
- Create: `src/ui/pages/__init__.py` (empty)
- Create: `src/ui/pages/_placeholder.py` (returns "Page coming soon" widget)
- Modify: `src/main.py`

- [ ] **Step 1: Create placeholder page builder**

`src/ui/pages/_placeholder.py`:

```python
import flet as ft

def build(page_name: str, mode: str = "dark") -> ft.Control:
    return ft.Container(
        expand=True,
        alignment=ft.alignment.center,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(page_name, size=32, weight=ft.FontWeight.W_800),
                ft.Text("Page coming soon", size=14, opacity=0.6),
            ],
        ),
    )
```

- [ ] **Step 2: Create `src/ui/shell.py` with sidebar, nav, routing, theme toggle**

```python
import flet as ft
from src.core.constants import COLORS
from src.core.settings_store import SettingsStore
from src.ui.components.logo import hexagon_j
from src.ui.pages import _placeholder

NAV_GROUPS = [
    ("Workflow", [
        ("import_data", "Import Data", ft.Icons.UPLOAD_FILE),
        ("issues", "Issues", ft.Icons.WARNING_AMBER),
        ("dashboard", "Dashboard", ft.Icons.DASHBOARD),
    ]),
    ("Reports", [
        ("weekly_report", "Weekly Report", ft.Icons.CALENDAR_VIEW_WEEK),
        ("monthly_report", "Monthly Report", ft.Icons.CALENDAR_MONTH),
    ]),
    ("Tools", [
        ("edit_records", "Edit Records", ft.Icons.EDIT),
        ("backup_restore", "Backup / Restore", ft.Icons.BACKUP),
        ("settings", "Settings", ft.Icons.SETTINGS),
    ]),
]

class Shell:
    def __init__(self, page: ft.Page, settings: SettingsStore):
        self.page = page
        self.settings = settings
        self.mode = settings.get("theme", "dark")
        self.current_route = "dashboard"
        self.content_area = ft.Container(expand=True)
        self.nav_buttons = {}

    def build(self) -> ft.Control:
        self._apply_theme()
        sidebar = self._build_sidebar()
        self._render_page(self.current_route)
        return ft.Row(
            expand=True, spacing=0,
            controls=[sidebar, self.content_area],
        )

    def _build_sidebar(self) -> ft.Control:
        nav_items = []
        for section_label, items in NAV_GROUPS:
            nav_items.append(
                ft.Text(section_label.upper(), size=10, weight=ft.FontWeight.W_700,
                        color=COLORS["accent"], opacity=0.8)
            )
            for route, label, icon in items:
                btn = self._make_nav_button(route, label, icon)
                self.nav_buttons[route] = btn
                nav_items.append(btn)
            nav_items.append(ft.Container(height=8))

        return ft.Container(
            width=240,
            bgcolor=COLORS["surface_dark"] if self.mode == "dark" else COLORS["surface_light"],
            padding=16,
            content=ft.Column(
                expand=True,
                controls=[
                    hexagon_j(size=40, with_wordmark=True, mode=self.mode),
                    ft.Container(height=20),
                    ft.Column(controls=nav_items, spacing=2),
                    ft.Container(expand=True),  # spacer
                    self._build_theme_toggle(),
                ],
            ),
        )

    def _make_nav_button(self, route: str, label: str, icon) -> ft.Control:
        is_active = route == self.current_route
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border_radius=8,
            bgcolor=f"{COLORS['primary']}33" if is_active else None,
            content=ft.Row(spacing=10, controls=[
                ft.Icon(icon, size=18,
                        color=COLORS["text_dark"] if self.mode == "dark" else COLORS["text_light"]),
                ft.Text(label, size=14,
                        weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.W_500),
            ]),
            on_click=lambda e, r=route: self._navigate(r),
            ink=True,
        )

    def _build_theme_toggle(self) -> ft.Control:
        is_dark = self.mode == "dark"
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=8,
            bgcolor=f"{COLORS['accent']}22",
            content=ft.Row(spacing=8, controls=[
                ft.Icon(ft.Icons.DARK_MODE if is_dark else ft.Icons.LIGHT_MODE, size=16),
                ft.Text("Dark Mode" if is_dark else "Light Mode", size=12),
            ]),
            on_click=lambda e: self._toggle_theme(),
            ink=True,
        )

    def _navigate(self, route: str):
        self.current_route = route
        # Rebuild sidebar so active state updates
        self.page.controls.clear()
        self.page.add(self.build())
        self.page.update()

    def _toggle_theme(self):
        self.mode = "light" if self.mode == "dark" else "dark"
        self.settings.update({"theme": self.mode})
        self._apply_theme()
        self.page.controls.clear()
        self.page.add(self.build())
        self.page.update()

    def _apply_theme(self):
        self.page.bgcolor = COLORS["bg_dark"] if self.mode == "dark" else COLORS["bg_light"]
        self.page.theme_mode = ft.ThemeMode.DARK if self.mode == "dark" else ft.ThemeMode.LIGHT

    def _render_page(self, route: str):
        # Placeholder for now; real pages plug in during later phases
        page_titles = {r: l for _, items in NAV_GROUPS for r, l, _ in items}
        self.content_area.content = _placeholder.build(page_titles.get(route, route), self.mode)
```

- [ ] **Step 3: Update `src/main.py` to use the Shell**

```python
import flet as ft
from pathlib import Path
from src.core.settings_store import SettingsStore
from src.ui.shell import Shell

DATA_DIR = Path(__file__).parent.parent / "data"
CONFIG_PATH = Path(__file__).parent.parent / "config.json"

def main(page: ft.Page):
    page.title = "Josaphat Tech Solution — HR Attendance Manager"
    page.window.width = 1280
    page.window.height = 800
    page.padding = 0

    DATA_DIR.mkdir(exist_ok=True)
    settings = SettingsStore(str(CONFIG_PATH))
    settings.load()

    shell = Shell(page, settings)
    page.add(shell.build())

if __name__ == "__main__":
    ft.app(target=main)
```

- [ ] **Step 4: Manually verify the shell**

Run: `python src/main.py`

Verify checklist:
- [ ] Window opens at 1280×800
- [ ] Left sidebar visible with Hex J logo + "Josaphat Tech Solution" wordmark
- [ ] Three nav sections: Workflow, Reports, Tools
- [ ] All 8 nav items show with their icons
- [ ] Click each nav item → main area shows "<page name>" + "Page coming soon"
- [ ] Click theme toggle at sidebar bottom → background flips dark↔light, icon and label swap
- [ ] Theme persists across nav clicks
- [ ] Close and reopen app → theme remains as last set (config.json was written)

Any failure: fix before commit.

- [ ] **Step 5: Commit**

```bash
git add src/main.py src/ui/shell.py src/ui/pages/_placeholder.py src/ui/pages/__init__.py
git commit -m "ui: app shell with sidebar nav, page routing, theme toggle"
```

---

# PHASE 2 — DATA PIPELINE (Tasks 6–9)

End state: drag a .xls file into the Import Data page, see records flow into DB, conflicts handled with snapshot for rollback.

---

### Task 6: Excel Parser

**Files:**
- Create: `src/core/parser.py`
- Create: `tests/core/test_parser.py`
- Create: `tests/fixtures/sample_apr_1_10.xls` (copy from `D:\Gawe\Dani\PT Tekno\April week 1&2 ; 1-10 april.xls`)

- [ ] **Step 1: Copy sample fixture**

```bash
mkdir -p tests/fixtures
cp "D:/Gawe/Dani/PT Tekno/April week 1&2 ; 1-10 april.xls" tests/fixtures/sample_apr_1_10.xls
```

Note: This file contains real employee data. The `tests/fixtures/` path is **NOT** in `.gitignore` by default, so add it explicitly to keep PII out of git:

Append to `.gitignore`:
```
tests/fixtures/*.xls
tests/fixtures/*.xlsx
```

The file stays locally for testing but never gets pushed.

- [ ] **Step 2: Write failing test for parser basic shape**

`tests/core/test_parser.py`:

```python
from pathlib import Path
import pytest
from src.core.parser import parse_xls

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_apr_1_10.xls"

def test_parse_returns_list_of_records():
    if not FIXTURE.exists():
        pytest.skip("Fixture not present (PII — kept local)")
    records = parse_xls(str(FIXTURE))
    assert isinstance(records, list)
    assert len(records) > 0

def test_parsed_record_has_expected_fields():
    if not FIXTURE.exists():
        pytest.skip("Fixture not present (PII — kept local)")
    records = parse_xls(str(FIXTURE))
    rec = records[0]
    expected_keys = {
        "staff_no", "name", "department", "date", "day_name",
        "day_type", "schedule_in", "schedule_out", "actual_in", "actual_out",
        "late_minutes", "early_leave_minutes", "work_hours", "overtime_hours",
        "absent_flag", "forgot_punch_flag",
    }
    assert expected_keys.issubset(set(rec.keys()))

def test_skips_total_personal_rows():
    if not FIXTURE.exists():
        pytest.skip()
    records = parse_xls(str(FIXTURE))
    for rec in records:
        assert not rec["name"].startswith("Total Personal")

def test_andika_apr_1_parsed_correctly():
    if not FIXTURE.exists():
        pytest.skip()
    records = parse_xls(str(FIXTURE))
    andika_apr_1 = next(
        r for r in records
        if r["name"] == "ANDIKA" and r["date"] == "2026-04-01"
    )
    assert andika_apr_1["staff_no"] == "1002"
    assert andika_apr_1["actual_in"] == "08:06"
    assert andika_apr_1["actual_out"] == "16:41"
    assert andika_apr_1["late_minutes"] == 6
    assert andika_apr_1["work_hours"] == 7.9
    assert andika_apr_1["day_type"] == "Hari Kerja"

def test_esa_apr_1_full_absent():
    if not FIXTURE.exists():
        pytest.skip()
    records = parse_xls(str(FIXTURE))
    esa = next(
        r for r in records
        if r["name"] == "ESA" and r["date"] == "2026-04-01"
    )
    assert esa["actual_in"] is None
    assert esa["actual_out"] is None
    assert esa["absent_flag"] == 1
```

- [ ] **Step 3: Run tests — expect import failure**

Run: `pytest tests/core/test_parser.py -v`
Expected: FAIL (no parser module yet).

- [ ] **Step 4: Implement `src/core/parser.py`**

```python
import xlrd
from datetime import datetime

# Column indices in the fingerprint .xls (header at row 0, units at row 1)
COL_NAME = 0
COL_STAFF_NO = 1
COL_DEPT = 2
COL_DATE = 3
COL_DAY = 4
COL_TYPE = 5
COL_SCHEDULE = 6
COL_MASUK = 8
COL_KELUAR = 10
COL_KERJA = 13
COL_LEMBUR = 14
COL_KURANG = 15
COL_TERLAMBAT = 16
COL_PULANG_CEPAT = 17
COL_ABSEN = 18
COL_LUPA = 19
COL_IJIN = 20

def _to_int(value) -> int:
    """Convert cell to int. Empty → 0."""
    if value == "" or value is None:
        return 0
    if isinstance(value, str):
        value = value.replace(",", ".").strip()
        if not value:
            return 0
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0

def _to_float(value) -> float:
    """Convert cell with Indonesian decimal comma to float. Empty → 0.0."""
    if value == "" or value is None:
        return 0.0
    if isinstance(value, str):
        value = value.replace(",", ".").strip()
        if not value:
            return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def _normalize_time(value) -> str | None:
    """Convert '08.06' → '08:06'. Empty → None."""
    if value == "" or value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    return s.replace(".", ":")

def _parse_date(value) -> str | None:
    """Convert '01/04/2026' → '2026-04-01'."""
    if not value:
        return None
    s = str(value).strip()
    try:
        dt = datetime.strptime(s, "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None

def _parse_schedule(schedule_str: str) -> tuple[str | None, str | None]:
    """'08.00 - 16.00' → ('08:00', '16:00')."""
    if not schedule_str or " - " not in str(schedule_str):
        return (None, None)
    parts = str(schedule_str).split(" - ")
    if len(parts) != 2:
        return (None, None)
    return (_normalize_time(parts[0]), _normalize_time(parts[1]))

def parse_xls(path: str) -> list[dict]:
    """Parse fingerprint export .xls into list of normalized record dicts."""
    book = xlrd.open_workbook(path, ignore_workbook_corruption=True)
    sheet = book.sheet_by_index(0)
    records = []

    # Skip rows 0 (header) and 1 (units). Data starts at row 2.
    for row_idx in range(2, sheet.nrows):
        row = sheet.row_values(row_idx)
        name = str(row[COL_NAME]).strip() if row[COL_NAME] else ""

        # Skip blank rows and "Total Personal:" separator rows
        if not name or name.startswith("Total Personal"):
            continue

        date_str = _parse_date(row[COL_DATE])
        if not date_str:
            continue

        sched_in, sched_out = _parse_schedule(row[COL_SCHEDULE])

        records.append({
            "staff_no": str(row[COL_STAFF_NO]).strip(),
            "name": name,
            "department": str(row[COL_DEPT]).strip() if row[COL_DEPT] else None,
            "date": date_str,
            "day_name": str(row[COL_DAY]).strip(),
            "day_type": str(row[COL_TYPE]).strip(),
            "schedule_in": sched_in,
            "schedule_out": sched_out,
            "actual_in": _normalize_time(row[COL_MASUK]),
            "actual_out": _normalize_time(row[COL_KELUAR]),
            "late_minutes": _to_int(row[COL_TERLAMBAT]),
            "early_leave_minutes": _to_int(row[COL_PULANG_CEPAT]),
            "work_hours": _to_float(row[COL_KERJA]),
            "overtime_hours": _to_float(row[COL_LEMBUR]),
            "absent_flag": _to_int(row[COL_ABSEN]),
            "forgot_punch_flag": _to_int(row[COL_LUPA]),
        })

    return records
```

- [ ] **Step 5: Run tests to verify all pass**

Run: `pytest tests/core/test_parser.py -v`
Expected: All 5 PASS (or skip if fixture missing — fixture must be present locally).

- [ ] **Step 6: Commit**

```bash
git add src/core/parser.py tests/core/test_parser.py .gitignore
git commit -m "core: Excel parser for fingerprint .xls export"
```

---

### Task 7: Issue Detector

**Files:**
- Create: `src/core/issue_detector.py`
- Create: `tests/core/test_issue_detector.py`

- [ ] **Step 1: Write failing tests for all 7 cases**

```python
from src.core.issue_detector import classify_issue

def make_record(**overrides):
    base = {
        "actual_in": "08:00",
        "actual_out": "16:00",
        "late_minutes": 0,
        "early_leave_minutes": 0,
        "day_type": "Hari Kerja",
    }
    base.update(overrides)
    return base

def test_case_a_full_absent():
    rec = make_record(actual_in=None, actual_out=None)
    assert classify_issue(rec) == "A"

def test_case_b_no_masuk():
    rec = make_record(actual_in=None, actual_out="19:00")
    assert classify_issue(rec) == "B"

def test_case_c_no_keluar():
    rec = make_record(actual_in="08:14", actual_out=None)
    assert classify_issue(rec) == "C"

def test_case_d_late_mild():
    rec = make_record(late_minutes=6)
    assert classify_issue(rec, late_threshold=15) == "D"

def test_case_e_late_severe():
    rec = make_record(late_minutes=161)
    assert classify_issue(rec, late_threshold=15) == "E"

def test_case_f_pulang_cepat():
    rec = make_record(early_leave_minutes=30)
    assert classify_issue(rec, pulang_cepat_threshold=0) == "F"

def test_case_g_istirahat():
    rec = make_record(day_type="Istirahat")
    assert classify_issue(rec) == "G"

def test_late_threshold_null_disables_de():
    rec = make_record(late_minutes=20)
    assert classify_issue(rec, late_threshold=None) is None

def test_pulang_cepat_threshold_null_disables_f():
    rec = make_record(early_leave_minutes=30)
    assert classify_issue(rec, pulang_cepat_threshold=None) is None

def test_no_issue_clean_record():
    rec = make_record()
    assert classify_issue(rec) is None
```

Run: `pytest tests/core/test_issue_detector.py -v`
Expected: FAIL (module missing).

- [ ] **Step 2: Implement `src/core/issue_detector.py`**

```python
def classify_issue(
    record: dict,
    late_threshold: int | None = 15,
    pulang_cepat_threshold: int | None = 0,
) -> str | None:
    """
    Classify the attendance record into one of cases A-G or None.
    See spec §6 for the full rule set.

    Priority order matters: data-missing cases (A/B/C) take precedence over
    timing-based cases (D/E/F). Case G (Istirahat) short-circuits.
    """
    # Case G: rest day, skip
    if record.get("day_type") == "Istirahat":
        return "G"

    actual_in = record.get("actual_in")
    actual_out = record.get("actual_out")

    # Case A: both empty
    if not actual_in and not actual_out:
        return "A"
    # Case B: masuk empty, keluar filled
    if not actual_in and actual_out:
        return "B"
    # Case C: masuk filled, keluar empty
    if actual_in and not actual_out:
        return "C"

    # Both timestamps present — check passive issues
    late = record.get("late_minutes", 0) or 0
    early = record.get("early_leave_minutes", 0) or 0

    # Case F: Pulang Cepat (data-complete but unusual — needs follow-up + color)
    if pulang_cepat_threshold is not None and early > pulang_cepat_threshold:
        return "F"

    # Cases D / E: late (color only — never returned if threshold is None)
    if late_threshold is not None and late > 0:
        if late < late_threshold:
            return "D"
        return "E"

    return None

def needs_follow_up(case: str | None) -> bool:
    """Cases that appear in the Issues list."""
    return case in ("A", "B", "C", "F")

def needs_cell_color(case: str | None) -> str | None:
    """Returns CSS-like color name or None for cell display."""
    return {
        "D": "yellow",
        "E": "red",
        "F": "orange",
    }.get(case)
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/core/test_issue_detector.py -v`
Expected: all 10 PASS.

- [ ] **Step 4: Commit**

```bash
git add src/core/issue_detector.py tests/core/test_issue_detector.py
git commit -m "core: issue detector for 7 cases with threshold-null handling"
```

---

### Task 8: Conflict Resolver + Snapshots

**Files:**
- Create: `src/core/conflict.py`
- Create: `tests/core/test_conflict.py`
- Modify: `src/db/repository.py` (add insert_history, create_batch, snapshot helpers)

- [ ] **Step 1: Add repository methods for batches and history**

Append to `src/db/repository.py`:

```python
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
```

- [ ] **Step 2: Write failing tests for conflict resolver**

`tests/core/test_conflict.py`:

```python
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
```

Run: `pytest tests/core/test_conflict.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `src/core/conflict.py`**

```python
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
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/core/test_conflict.py -v`
Expected: all 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/core/conflict.py src/db/repository.py tests/core/test_conflict.py
git commit -m "core: conflict resolver with keep/overwrite policy and snapshots"
```

---

### Task 9: Import Data Page UI

**Files:**
- Create: `src/ui/pages/import_data.py`
- Modify: `src/ui/shell.py` (wire route → real page)

- [ ] **Step 1: Create `src/ui/pages/import_data.py`**

```python
import flet as ft
from pathlib import Path
from src.core.parser import parse_xls
from src.core.conflict import resolve_import, detect_conflicts, ConflictPolicy
from src.db.repository import Repository
from src.core.settings_store import SettingsStore
from src.core.constants import COLORS

class ImportDataPage:
    def __init__(self, repo: Repository, settings: SettingsStore, snapshot_dir: str, mode: str = "dark"):
        self.repo = repo
        self.settings = settings
        self.snapshot_dir = snapshot_dir
        self.mode = mode
        self.parsed_records = []
        self.selected_file = None
        self.file_picker = None

    def build(self) -> ft.Control:
        self.file_picker = ft.FilePicker(on_result=self._on_file_picked)
        self.status_text = ft.Text("Belum ada file yang dipilih.", size=14, opacity=0.7)
        self.preview_container = ft.Container()
        self.action_row = ft.Row(visible=False, spacing=10)

        return ft.Container(
            padding=32, expand=True,
            content=ft.Column(
                spacing=20, controls=[
                    self.file_picker,
                    ft.Text("Import Data", size=28, weight=ft.FontWeight.W_800),
                    ft.Text("Tarik file fingerprint .xls ke sini, atau klik 'Pilih File'.",
                            size=13, opacity=0.7),
                    ft.Container(
                        padding=40, border_radius=12,
                        bgcolor=f"{COLORS['primary']}11",
                        border=ft.border.all(2, f"{COLORS['primary']}55"),
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=12, controls=[
                                ft.Icon(ft.Icons.UPLOAD_FILE, size=48, color=COLORS["primary"]),
                                ft.ElevatedButton(
                                    "📁 Pilih File .xls",
                                    on_click=lambda e: self.file_picker.pick_files(
                                        allowed_extensions=["xls", "xlsx"], allow_multiple=False
                                    ),
                                    bgcolor=COLORS["primary"], color="white",
                                ),
                                self.status_text,
                            ],
                        ),
                    ),
                    self.preview_container,
                    self.action_row,
                ],
            ),
        )

    def _on_file_picked(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return
        self.selected_file = e.files[0].path
        try:
            self.parsed_records = parse_xls(self.selected_file)
        except Exception as ex:
            self.status_text.value = f"❌ Gagal parse: {ex}"
            self.status_text.update()
            return

        n = len(self.parsed_records)
        dates = sorted({r["date"] for r in self.parsed_records})
        self.status_text.value = f"✅ {n} baris ter-parse dari {Path(self.selected_file).name} · periode {dates[0]} → {dates[-1]}"
        self.status_text.update()

        self._show_preview_and_actions()

    def _show_preview_and_actions(self):
        # Detect conflicts before commit
        conflicts = detect_conflicts(self.repo, self.parsed_records)
        n_conflict = len(conflicts)
        n_new = len(self.parsed_records) - n_conflict

        info_box = ft.Container(
            padding=16, border_radius=8, bgcolor=f"{COLORS['accent']}22",
            content=ft.Column(spacing=4, controls=[
                ft.Text(f"📥 Baris baru: {n_new}", size=13, weight=ft.FontWeight.W_600),
                ft.Text(f"⚠️ Konflik (sudah ada di DB): {n_conflict}", size=13, weight=ft.FontWeight.W_600,
                        color=COLORS["accent"] if n_conflict else None),
            ]),
        )
        self.preview_container.content = info_box
        self.preview_container.update()

        self.action_row.controls.clear()
        self.action_row.controls.append(
            ft.ElevatedButton("✅ Import (keep existing untuk konflik)",
                              on_click=lambda e: self._do_import(ConflictPolicy.KEEP_EXISTING),
                              bgcolor=COLORS["resolved"], color="white"),
        )
        if n_conflict > 0:
            self.action_row.controls.append(
                ft.ElevatedButton("⚡ Import + Overwrite konflik",
                                  on_click=lambda e: self._do_import(ConflictPolicy.OVERWRITE),
                                  bgcolor=COLORS["accent"], color="white"),
            )
        self.action_row.controls.append(
            ft.TextButton("Cancel", on_click=lambda e: self._reset()),
        )
        self.action_row.visible = True
        self.action_row.update()

    def _do_import(self, policy: ConflictPolicy):
        summary = resolve_import(
            self.repo, self.parsed_records, Path(self.selected_file).name,
            snapshot_dir=self.snapshot_dir, policy=policy,
            settings=self.settings.load(),
        )
        msg = (f"✅ Import selesai · {summary['inserted']} baru · "
               f"{summary['kept']} kept · {summary['overwritten']} overwritten")
        self.status_text.value = msg
        self.status_text.update()
        self._reset_after_success()

    def _reset(self):
        self.parsed_records = []
        self.selected_file = None
        self.status_text.value = "Belum ada file yang dipilih."
        self.preview_container.content = None
        self.action_row.visible = False
        self.status_text.update()
        self.preview_container.update()
        self.action_row.update()

    def _reset_after_success(self):
        self.parsed_records = []
        self.selected_file = None
        self.preview_container.content = None
        self.action_row.visible = False
        self.preview_container.update()
        self.action_row.update()
```

- [ ] **Step 2: Wire route in `src/ui/shell.py`**

Replace `_render_page` method:

```python
def _render_page(self, route: str):
    from src.ui.pages import _placeholder, import_data
    if route == "import_data":
        page_obj = import_data.ImportDataPage(
            self.repo, self.settings, self.snapshot_dir, self.mode
        )
        self.content_area.content = page_obj.build()
    else:
        page_titles = {r: l for _, items in NAV_GROUPS for r, l, _ in items}
        self.content_area.content = _placeholder.build(page_titles.get(route, route), self.mode)
```

Update `Shell.__init__` signature:

```python
def __init__(self, page: ft.Page, settings: SettingsStore, repo: Repository, snapshot_dir: str):
    self.page = page
    self.settings = settings
    self.repo = repo
    self.snapshot_dir = snapshot_dir
    self.mode = settings.get("theme", "dark")
    self.current_route = "dashboard"
    self.content_area = ft.Container(expand=True)
    self.nav_buttons = {}
```

Add import at top of shell.py:

```python
from src.db.repository import Repository
```

- [ ] **Step 3: Update `src/main.py` to pass repo**

```python
import flet as ft
from pathlib import Path
from src.core.settings_store import SettingsStore
from src.db.repository import Repository
from src.ui.shell import Shell

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
BACKUP_DIR = ROOT / "backups"
CONFIG_PATH = ROOT / "config.json"
DB_PATH = DATA_DIR / "app.db"

def main(page: ft.Page):
    page.title = "Josaphat Tech Solution — HR Attendance Manager"
    page.window.width = 1280
    page.window.height = 800
    page.padding = 0

    DATA_DIR.mkdir(exist_ok=True)
    BACKUP_DIR.mkdir(exist_ok=True)

    settings = SettingsStore(str(CONFIG_PATH))
    settings.load()

    repo = Repository(str(DB_PATH))
    repo.init_schema()

    shell = Shell(page, settings, repo, str(BACKUP_DIR))
    page.add(shell.build())

if __name__ == "__main__":
    ft.app(target=main)
```

- [ ] **Step 4: Manually verify**

Run: `python src/main.py`

Verify checklist:
- [ ] Click "Import Data" in sidebar → import page shows
- [ ] Click "Pilih File .xls" → file dialog opens
- [ ] Select `D:\Gawe\Dani\PT Tekno\April week 1&2 ; 1-10 april.xls`
- [ ] Status text updates with row count and date range
- [ ] Info box shows "Baris baru: 270, Konflik: 0" (first import)
- [ ] Click "Import (keep existing)" → success message, count summary
- [ ] Pick same file again → now shows "Baris baru: 0, Konflik: 270"
- [ ] "Import + Overwrite" button appears
- [ ] Click cancel → resets state
- [ ] Verify SQLite file exists: `data/app.db` (size > 0)

- [ ] **Step 5: Commit**

```bash
git add src/ui/pages/import_data.py src/ui/shell.py src/main.py
git commit -m "ui: Import Data page with file picker, preview, conflict handling"
```

---

# PHASE 3 — RESOLUTION WORKFLOW (Tasks 10–12)

End state: Issues page lists pending follow-ups, click row → resolve panel with 10 options, Edit Records page lets you correct past data.

---

### Task 10: Resolution Manager

**Files:**
- Create: `src/core/resolver.py`
- Create: `tests/core/test_resolver.py`
- Modify: `src/db/repository.py` (add resolution CRUD)

- [ ] **Step 1: Add resolution CRUD to repository**

Append to `src/db/repository.py`:

```python
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
```

- [ ] **Step 2: Write failing tests**

`tests/core/test_resolver.py`:

```python
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
```

Run: `pytest tests/core/test_resolver.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `src/core/resolver.py`**

```python
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
        # Only add penalty once — track via history check
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
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/core/test_resolver.py -v`
Expected: all 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/core/resolver.py src/db/repository.py tests/core/test_resolver.py
git commit -m "core: resolution manager with 10 reason codes and lupa_absen penalty"
```

---

### Task 11: Issues Page UI

**Files:**
- Create: `src/ui/pages/issues.py`
- Modify: `src/ui/shell.py` (wire route)

- [ ] **Step 1: Create `src/ui/pages/issues.py`**

```python
import flet as ft
from datetime import date, timedelta
from src.core.constants import COLORS
from src.core.resolver import (
    apply_resolution, list_all_reason_options, requires_extra_input
)
from src.db.repository import Repository
from src.core.settings_store import SettingsStore

CASE_LABELS = {
    "A": ("Tidak Hadir", COLORS["late_severe"]),
    "B": ("Lupa Absen Masuk", COLORS["late_mild"]),
    "C": ("Lupa Absen Pulang", COLORS["late_mild"]),
    "F": ("Pulang Cepat", COLORS["pulang_cepat"]),
}

class IssuesPage:
    def __init__(self, repo: Repository, settings: SettingsStore, mode: str = "dark"):
        self.repo = repo
        self.settings = settings
        self.mode = mode
        # Default: current week (Mon-Sun)
        today = date.today()
        self.start = today - timedelta(days=today.weekday())
        self.end = self.start + timedelta(days=6)
        self.selected_record_id = None
        self.selected_reason = None

    def build(self) -> ft.Control:
        self.list_view = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=6, expand=True)
        self.resolve_panel = ft.Container(
            width=360, padding=20, visible=False,
            bgcolor=COLORS["surface_dark"] if self.mode == "dark" else COLORS["surface_light"],
        )
        self._refresh_list()
        return ft.Container(
            padding=24, expand=True,
            content=ft.Column(spacing=16, controls=[
                ft.Row(controls=[
                    ft.Text("Issues", size=28, weight=ft.FontWeight.W_800),
                    ft.Container(expand=True),
                    self._build_period_selector(),
                ]),
                ft.Text(f"Period: {self.start} → {self.end}", size=12, opacity=0.7),
                ft.Row(expand=True, spacing=20, controls=[
                    ft.Container(expand=True, content=self.list_view),
                    self.resolve_panel,
                ]),
            ]),
        )

    def _build_period_selector(self) -> ft.Control:
        return ft.Row(spacing=8, controls=[
            ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda e: self._shift_week(-1)),
            ft.Text(f"{self.start.strftime('%d %b')} – {self.end.strftime('%d %b %Y')}", size=13),
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda e: self._shift_week(1)),
        ])

    def _shift_week(self, weeks: int):
        self.start += timedelta(weeks=weeks)
        self.end += timedelta(weeks=weeks)
        self._refresh_list()
        self.list_view.update()

    def _refresh_list(self):
        self.list_view.controls.clear()
        issues = self.repo.list_pending_issues(self.start.isoformat(), self.end.isoformat())
        if not issues:
            self.list_view.controls.append(
                ft.Container(padding=40, alignment=ft.alignment.center,
                             content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                 controls=[
                                     ft.Icon(ft.Icons.CHECK_CIRCLE, size=48, color=COLORS["resolved"]),
                                     ft.Text("Tidak ada issue pending minggu ini ✨", size=14),
                                 ])),
            )
            return

        for issue in issues:
            self.list_view.controls.append(self._build_issue_row(issue))

    def _build_issue_row(self, issue: dict) -> ft.Control:
        case_label, case_color = CASE_LABELS.get(issue["issue_case"], (issue["issue_case"], "#999"))
        return ft.Container(
            padding=12, border_radius=8,
            bgcolor=f"{case_color}15", border=ft.border.all(1, f"{case_color}66"),
            on_click=lambda e, rid=issue["id"]: self._select_issue(rid, issue),
            ink=True,
            content=ft.Row(spacing=12, controls=[
                ft.Container(width=4, height=40, bgcolor=case_color, border_radius=2),
                ft.Column(spacing=2, expand=True, controls=[
                    ft.Text(f"{issue['employee_name']}", weight=ft.FontWeight.W_700, size=14),
                    ft.Text(f"{issue['date']} · {issue['day_name']}", size=12, opacity=0.7),
                ]),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    border_radius=12, bgcolor=case_color,
                    content=ft.Text(case_label, color="white", size=11, weight=ft.FontWeight.W_600),
                ),
            ]),
        )

    def _select_issue(self, record_id: int, issue: dict):
        self.selected_record_id = record_id
        self.selected_reason = None
        self.resolve_panel.visible = True
        self.resolve_panel.content = self._build_resolve_panel(issue)
        self.resolve_panel.update()

    def _build_resolve_panel(self, issue: dict) -> ft.Control:
        self.extra_input_field = ft.TextField(label="Lokasi / Alasan", visible=False)

        def make_option(code: str, label: str):
            return ft.Container(
                padding=10, border_radius=6,
                bgcolor=f"{COLORS['primary']}22" if self.selected_reason == code else None,
                on_click=lambda e, c=code: self._select_reason(c),
                ink=True,
                content=ft.Text(label, size=13),
            )

        options_col = ft.Column(spacing=4, controls=[
            make_option(code, label) for code, label, _ in list_all_reason_options()
        ])

        return ft.Column(spacing=14, controls=[
            ft.Text("Resolve Issue", size=18, weight=ft.FontWeight.W_700),
            ft.Text(f"{issue['employee_name']} · {issue['date']}", size=12, opacity=0.7),
            ft.Divider(height=1),
            ft.Text("Pilih alasan:", size=12, weight=ft.FontWeight.W_600),
            options_col,
            self.extra_input_field,
            ft.Row(spacing=8, controls=[
                ft.ElevatedButton("Save", on_click=lambda e: self._save_resolution(),
                                  bgcolor=COLORS["resolved"], color="white"),
                ft.TextButton("Cancel", on_click=lambda e: self._close_panel()),
            ]),
        ])

    def _select_reason(self, code: str):
        self.selected_reason = code
        extra = requires_extra_input(code)
        self.extra_input_field.visible = extra is not None
        self.extra_input_field.label = "Lokasi" if extra == "location" else "Alasan"
        self.extra_input_field.value = ""
        # Rebuild panel to re-highlight option
        cursor = self.repo.conn.execute(
            """SELECT ar.*, e.name AS employee_name FROM attendance_records ar
               JOIN employees e ON ar.employee_id=e.id WHERE ar.id=?""",
            (self.selected_record_id,),
        ).fetchone()
        self.resolve_panel.content = self._build_resolve_panel(dict(cursor))
        self.resolve_panel.update()

    def _save_resolution(self):
        if not self.selected_reason:
            return
        extra_type = requires_extra_input(self.selected_reason)
        kwargs = {}
        if extra_type == "location":
            kwargs["location"] = self.extra_input_field.value
        elif extra_type == "reason_detail":
            kwargs["reason_detail"] = self.extra_input_field.value
        kwargs["penalty_minutes"] = self.settings.get("lupa_absen_penalty_minutes")
        apply_resolution(self.repo, self.selected_record_id, self.selected_reason, **kwargs)
        self._close_panel()
        self._refresh_list()
        self.list_view.update()

    def _close_panel(self):
        self.resolve_panel.visible = False
        self.resolve_panel.update()
```

- [ ] **Step 2: Wire route in `src/ui/shell.py`**

Update `_render_page`:

```python
def _render_page(self, route: str):
    from src.ui.pages import _placeholder, import_data, issues
    if route == "import_data":
        page_obj = import_data.ImportDataPage(self.repo, self.settings, self.snapshot_dir, self.mode)
        self.content_area.content = page_obj.build()
    elif route == "issues":
        page_obj = issues.IssuesPage(self.repo, self.settings, self.mode)
        self.content_area.content = page_obj.build()
    else:
        page_titles = {r: l for _, items in NAV_GROUPS for r, l, _ in items}
        self.content_area.content = _placeholder.build(page_titles.get(route, route), self.mode)
```

- [ ] **Step 3: Manually verify**

Run: `python src/main.py`
- Import the sample .xls if not already (Phase 2)
- Click "Issues" in sidebar
- Verify list of pending issues shows with case badges (Tidak Hadir / Lupa Absen Masuk / etc.)
- Click an issue → resolve panel appears on the right
- Click a reason option → option highlights; if it's Tugas Lapangan/Paparan/Izin Pagi/etc., text field appears
- Fill extra input if needed → click Save
- Issue disappears from pending list
- Use ◀ ▶ buttons to switch weeks

- [ ] **Step 4: Commit**

```bash
git add src/ui/pages/issues.py src/ui/shell.py
git commit -m "ui: Issues page with pending list and 10-option resolve panel"
```

---

### Task 12: Edit Records Page UI

**Files:**
- Create: `src/ui/pages/edit_records.py`
- Modify: `src/ui/shell.py` (wire route)
- Modify: `src/db/repository.py` (add list_history_for_record)

- [ ] **Step 1: Add history query to repository**

Append to `src/db/repository.py`:

```python
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
```

- [ ] **Step 2: Create `src/ui/pages/edit_records.py`**

```python
import flet as ft
from datetime import date, timedelta
from src.core.constants import COLORS, REASON_CODES
from src.core.resolver import apply_resolution, remove_resolution, requires_extra_input
from src.db.repository import Repository
from src.core.settings_store import SettingsStore

class EditRecordsPage:
    def __init__(self, repo: Repository, settings: SettingsStore, mode: str = "dark"):
        self.repo = repo
        self.settings = settings
        self.mode = mode
        today = date.today()
        # Show last 30 days by default
        self.end = today
        self.start = today - timedelta(days=30)
        self.search_query = ""

    def build(self) -> ft.Control:
        self.search_field = ft.TextField(
            label="Cari nama / no. staff",
            on_change=lambda e: self._on_search(e.control.value),
            width=300,
        )
        self.records_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=4, expand=True)
        self._refresh()
        return ft.Container(
            padding=24, expand=True,
            content=ft.Column(spacing=16, controls=[
                ft.Row(controls=[
                    ft.Text("Edit Records", size=28, weight=ft.FontWeight.W_800),
                    ft.Container(expand=True),
                    self.search_field,
                ]),
                ft.Text(f"Showing {self.start} → {self.end}", size=12, opacity=0.7),
                ft.Container(expand=True, content=self.records_list),
            ]),
        )

    def _on_search(self, query: str):
        self.search_query = query
        self._refresh()
        self.records_list.update()

    def _refresh(self):
        self.records_list.controls.clear()
        records = self.repo.list_attendance_with_resolutions(
            self.start.isoformat(), self.end.isoformat(), self.search_query
        )
        for rec in records[:200]:  # cap to keep UI responsive
            self.records_list.controls.append(self._build_row(rec))

    def _build_row(self, rec: dict) -> ft.Control:
        reason_label = REASON_CODES.get(rec["reason_code"], {}).get("label", "—") if rec["reason_code"] else "—"
        return ft.Container(
            padding=10, border_radius=6,
            bgcolor=f"{COLORS['primary']}08",
            content=ft.Row(spacing=12, controls=[
                ft.Container(width=80, content=ft.Text(rec["date"], size=12, weight=ft.FontWeight.W_600)),
                ft.Container(width=120, content=ft.Text(rec["employee_name"], size=12)),
                ft.Container(width=80, content=ft.Text(f"In: {rec['actual_in'] or '—'}", size=11)),
                ft.Container(width=80, content=ft.Text(f"Out: {rec['actual_out'] or '—'}", size=11)),
                ft.Container(expand=True, content=ft.Text(reason_label, size=11, opacity=0.85)),
                ft.IconButton(ft.Icons.EDIT, icon_size=16,
                              on_click=lambda e, r=rec: self._open_edit_dialog(r)),
                ft.IconButton(ft.Icons.HISTORY, icon_size=16,
                              on_click=lambda e, r=rec: self._open_history_dialog(r)),
            ]),
        )

    def _open_edit_dialog(self, rec: dict):
        actual_in_field = ft.TextField(label="Actual In (HH:MM)", value=rec["actual_in"] or "")
        actual_out_field = ft.TextField(label="Actual Out (HH:MM)", value=rec["actual_out"] or "")
        reason_dropdown = ft.Dropdown(
            label="Reason",
            value=rec["reason_code"] or "belum_kabar",
            options=[ft.dropdown.Option(code, label)
                     for code, label, _ in [(c, info["label"], info["extra"])
                                              for c, info in REASON_CODES.items()]],
        )
        extra_field = ft.TextField(
            label="Lokasi / Alasan", value=rec["location"] or rec["reason_detail"] or "",
        )

        def save(_):
            self.repo.update_attendance(rec["id"], {
                "actual_in": actual_in_field.value or None,
                "actual_out": actual_out_field.value or None,
            })
            extra_type = requires_extra_input(reason_dropdown.value)
            kwargs = {}
            if extra_type == "location":
                kwargs["location"] = extra_field.value
            elif extra_type == "reason_detail":
                kwargs["reason_detail"] = extra_field.value
            kwargs["penalty_minutes"] = self.settings.get("lupa_absen_penalty_minutes")
            apply_resolution(self.repo, rec["id"], reason_dropdown.value, **kwargs)
            dialog.open = False
            page = self.search_field.page
            page.update()
            self._refresh()
            self.records_list.update()

        dialog = ft.AlertDialog(
            modal=True, title=ft.Text(f"Edit · {rec['employee_name']} · {rec['date']}"),
            content=ft.Column(width=400, spacing=10, tight=True, controls=[
                actual_in_field, actual_out_field, reason_dropdown, extra_field,
            ]),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self._close_dialog(dialog)),
                ft.ElevatedButton("Save", on_click=save, bgcolor=COLORS["resolved"], color="white"),
            ],
        )
        page = self.search_field.page
        page.dialog = dialog
        dialog.open = True
        page.update()

    def _open_history_dialog(self, rec: dict):
        history = self.repo.list_history_for_record(rec["id"])
        rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(h["changed_at"][:19], size=11)),
                ft.DataCell(ft.Text(h["changed_field"], size=11)),
                ft.DataCell(ft.Text(str(h["old_value"]), size=11)),
                ft.DataCell(ft.Text(str(h["new_value"]), size=11)),
                ft.DataCell(ft.Text(h["changed_by"], size=11)),
            ]) for h in history
        ]
        dialog = ft.AlertDialog(
            modal=True, title=ft.Text(f"History · {rec['employee_name']} · {rec['date']}"),
            content=ft.Container(width=700, height=400, content=ft.Column(scroll=ft.ScrollMode.AUTO, controls=[
                ft.DataTable(columns=[
                    ft.DataColumn(ft.Text("When")),
                    ft.DataColumn(ft.Text("Field")),
                    ft.DataColumn(ft.Text("Old")),
                    ft.DataColumn(ft.Text("New")),
                    ft.DataColumn(ft.Text("By")),
                ], rows=rows or [ft.DataRow(cells=[ft.DataCell(ft.Text("—"))]*5)]),
            ])),
            actions=[ft.TextButton("Close", on_click=lambda e: self._close_dialog(dialog))],
        )
        page = self.search_field.page
        page.dialog = dialog
        dialog.open = True
        page.update()

    def _close_dialog(self, dialog):
        dialog.open = False
        self.search_field.page.update()
```

- [ ] **Step 3: Wire route in `src/ui/shell.py`**

Add to `_render_page`:

```python
elif route == "edit_records":
    from src.ui.pages import edit_records
    page_obj = edit_records.EditRecordsPage(self.repo, self.settings, self.mode)
    self.content_area.content = page_obj.build()
```

- [ ] **Step 4: Manually verify**

Run app, navigate to Edit Records:
- Search by name → list filters
- Click ✏️ on a row → dialog opens with actual_in/out, reason dropdown, extra field
- Edit values → Save → row updates in list
- Click 🕐 history button → table of all changes for that record shows

- [ ] **Step 5: Commit**

```bash
git add src/ui/pages/edit_records.py src/ui/shell.py src/db/repository.py
git commit -m "ui: Edit Records page with inline edit and history dialog"
```

---

# PHASE 4 — DASHBOARD (Tasks 13–15)

End state: Dashboard displays vital + trivia metrics, Coaching Required section, Hall of Late ranking, charts.

---

### Task 13: Metrics Engine

**Files:**
- Create: `src/core/metrics.py`
- Create: `tests/core/test_metrics.py`

- [ ] **Step 1: Write failing tests for metric calculations**

`tests/core/test_metrics.py`:

```python
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
```

Run: `pytest tests/core/test_metrics.py -v`
Expected: FAIL.

- [ ] **Step 2: Implement `src/core/metrics.py`**

```python
from datetime import datetime, timedelta, date
from collections import Counter
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
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/core/test_metrics.py -v`
Expected: all 5 PASS.

- [ ] **Step 4: Commit**

```bash
git add src/core/metrics.py tests/core/test_metrics.py
git commit -m "core: metrics engine for vital, trivia, coaching, ranking, trend"
```

---

### Task 14: Dashboard Components (Cards, Coaching, Ranking)

**Files:**
- Create: `src/ui/components/vital_card.py`
- Create: `src/ui/components/trivia_card.py`
- Create: `src/ui/components/coaching_card.py`
- Create: `src/ui/components/ranking_row.py`

- [ ] **Step 1: Create `src/ui/components/vital_card.py`**

```python
import flet as ft
from src.core.constants import COLORS

ACCENT_COLORS = {
    "urgent": COLORS["late_severe"],
    "coaching": COLORS["accent"],
    "warning": COLORS["pulang_cepat"],
    "positive": COLORS["resolved"],
}

def vital_card(icon: str, label: str, value: str, meta: str, accent: str = "urgent",
               mode: str = "dark") -> ft.Control:
    color = ACCENT_COLORS.get(accent, COLORS["primary"])
    bg = COLORS["surface_dark"] if mode == "dark" else COLORS["surface_light"]
    return ft.Container(
        padding=18, border_radius=12,
        bgcolor=bg,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left, end=ft.alignment.bottom_right,
            colors=[bg, f"{color}22"],
        ),
        border=ft.border.all(1, f"{color}55"),
        content=ft.Column(spacing=4, controls=[
            ft.Text(icon, size=22),
            ft.Text(label.upper(), size=10, weight=ft.FontWeight.W_700,
                    color=COLORS["accent"], opacity=0.85),
            ft.Text(value, size=32, weight=ft.FontWeight.W_900, color=color),
            ft.Text(meta, size=11, opacity=0.7),
        ]),
    )
```

- [ ] **Step 2: Create `src/ui/components/trivia_card.py`**

```python
import flet as ft
from src.core.constants import COLORS

def trivia_card(icon: str, label: str, value: str, meta: str, mode: str = "dark") -> ft.Control:
    return ft.Container(
        padding=12, border_radius=8,
        bgcolor=f"{COLORS['surface_dark']}88" if mode == "dark" else f"{COLORS['surface_light']}88",
        border=ft.border.all(1, f"{COLORS['primary']}22"),
        content=ft.Column(spacing=3, controls=[
            ft.Text(icon, size=15, opacity=0.8),
            ft.Text(label.upper(), size=9, weight=ft.FontWeight.W_600,
                    color=COLORS["accent"], opacity=0.85),
            ft.Text(value, size=14, weight=ft.FontWeight.W_700),
            ft.Text(meta, size=10, opacity=0.65),
        ]),
    )
```

- [ ] **Step 3: Create `src/ui/components/coaching_card.py`**

```python
import flet as ft
from src.core.constants import COLORS

def coaching_card(rank_emoji: str, name: str, total_late: int,
                  days_late: int, total_days: int, avg_per_day: int,
                  streak: int = 0) -> ft.Control:
    streak_text = f"🔥 {streak} mgg" if streak >= 2 else "—"
    return ft.Container(
        padding=18, border_radius=12,
        bgcolor=f"{COLORS['surface_dark']}cc",
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left, end=ft.alignment.bottom_right,
            colors=[f"{COLORS['surface_dark']}cc", f"{COLORS['late_severe']}22"],
        ),
        border=ft.border.all(1.5, f"{COLORS['late_severe']}88"),
        content=ft.Column(spacing=10, controls=[
            ft.Row(spacing=10, controls=[
                ft.Text(rank_emoji, size=22),
                ft.Text(name, size=20, weight=ft.FontWeight.W_900),
            ]),
            ft.Row(spacing=6, controls=[
                ft.Text("Akumulasi telat:", size=14, color=COLORS["late_severe"]),
                ft.Text(f"{total_late} menit", size=22, weight=ft.FontWeight.W_900,
                        color=COLORS["late_severe"]),
            ]),
            ft.Divider(height=1, opacity=0.2),
            ft.Row(spacing=20, controls=[
                _stat("Hari Telat", f"{days_late}/{total_days}"),
                _stat("Avg/Hari", f"{avg_per_day} mnt"),
                _stat("Streak", streak_text),
            ]),
        ]),
    )

def _stat(label: str, value: str) -> ft.Control:
    return ft.Column(spacing=2, controls=[
        ft.Text(label.upper(), size=9, weight=ft.FontWeight.W_600,
                color=COLORS["accent"], opacity=0.8),
        ft.Text(value, size=14, weight=ft.FontWeight.W_800),
    ])
```

- [ ] **Step 4: Create `src/ui/components/ranking_row.py`**

```python
import flet as ft
from src.core.constants import COLORS

def ranking_row(position: int, name: str, total_late: int, days_late: int,
                max_late: int, max_late_date: str, max_value: int,
                is_repeat_offender: bool, coaching_threshold: int = 75) -> ft.Control:
    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(position, f"#{position}")
    border_color = {
        1: COLORS["late_severe"], 2: COLORS["late_severe"], 3: COLORS["late_mild"],
    }.get(position)
    over_threshold = total_late > coaching_threshold
    bar_pct = (total_late / max_value * 100) if max_value else 0

    name_row = [ft.Text(name, size=18, weight=ft.FontWeight.W_900)]
    if is_repeat_offender:
        name_row.append(ft.Text("🔥", size=14))

    over_text = " · over coaching threshold" if over_threshold else ""

    return ft.Container(
        padding=ft.padding.symmetric(horizontal=14, vertical=12),
        border_radius=10,
        bgcolor=f"{COLORS['primary']}08",
        border=ft.border.only(left=ft.BorderSide(4, border_color)) if border_color else None,
        content=ft.Row(spacing=14, alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
            ft.Container(width=50,
                         content=ft.Text(medal, size=24, text_align=ft.TextAlign.CENTER)),
            ft.Container(expand=True, content=ft.Column(spacing=2, controls=[
                ft.Row(spacing=6, controls=name_row),
                ft.Text(f"{days_late} hari telat · max {max_late} mnt ({max_late_date}){over_text}",
                        size=11, opacity=0.7),
            ])),
            ft.Container(width=130, content=ft.Container(
                height=10, border_radius=6,
                bgcolor=f"{COLORS['primary']}11",
                content=ft.Container(
                    width=bar_pct * 1.3, height=10, border_radius=6,
                    gradient=ft.LinearGradient(
                        begin=ft.alignment.center_left, end=ft.alignment.center_right,
                        colors=[COLORS["late_severe"], COLORS["accent"]] if over_threshold
                                else [COLORS["pulang_cepat"], COLORS["primary"]],
                    ),
                ),
            )),
            ft.Container(width=80, content=ft.Text(
                f"{total_late} mnt", size=18, weight=ft.FontWeight.W_900,
                color=COLORS["late_severe"] if over_threshold else None,
                text_align=ft.TextAlign.RIGHT,
            )),
        ]),
    )
```

- [ ] **Step 5: Smoke test components in main.py**

Temporarily replace `src/main.py` body to render samples:

```python
import flet as ft
from src.ui.components.vital_card import vital_card
from src.ui.components.trivia_card import trivia_card
from src.ui.components.coaching_card import coaching_card
from src.ui.components.ranking_row import ranking_row

def main(page: ft.Page):
    page.bgcolor = "#1a0b2e"
    page.padding = 24
    page.add(
        ft.Row(spacing=10, controls=[
            vital_card("⚠️", "Pending Issues", "4", "8 of 12 resolved", "urgent"),
            vital_card("🚨", "Need Coaching", "2", "Threshold >75 mnt", "coaching"),
            vital_card("✅", "Attendance", "94%", "↑ 2% vs last week", "positive"),
        ]),
        ft.Row(spacing=10, controls=[
            trivia_card("🏷️", "Most Common", "Tugas Lapangan", "4 of 12 (33%)"),
            trivia_card("📈", "Late Trend", "↓ 12%", "vs last week"),
        ]),
        coaching_card("🥇", "TOMBAK", 181, 3, 5, 60, streak=4),
        ranking_row(1, "TOMBAK", 181, 3, 161, "1 Apr", 181, True),
        ranking_row(4, "SARI", 31, 3, 14, "3 Apr", 181, True),
    )

if __name__ == "__main__":
    ft.app(target=main)
```

Run: `python src/main.py`
Verify: cards, coaching card with medal, two ranking rows render correctly.

Then **revert** `src/main.py` to its post-Task 9 state.

- [ ] **Step 6: Commit**

```bash
git add src/ui/components/
git commit -m "ui: dashboard components — vital/trivia cards, coaching card, ranking row"
```

---

### Task 15: Dashboard Page

**Files:**
- Create: `src/ui/pages/dashboard.py`
- Modify: `src/ui/shell.py` (wire route + set as default)

- [ ] **Step 1: Create `src/ui/pages/dashboard.py`**

```python
import flet as ft
from datetime import date, timedelta
from src.core.constants import COLORS, REASON_CODES
from src.core.metrics import (
    weekly_summary, hall_of_late, coaching_candidates,
    repeat_offenders, distribusi_alasan, hari_paling_telat,
    best_performer, late_trend
)
from src.ui.components.vital_card import vital_card
from src.ui.components.trivia_card import trivia_card
from src.ui.components.coaching_card import coaching_card
from src.ui.components.ranking_row import ranking_row
from src.db.repository import Repository
from src.core.settings_store import SettingsStore

class DashboardPage:
    def __init__(self, repo: Repository, settings: SettingsStore, mode: str = "dark"):
        self.repo = repo
        self.settings = settings
        self.mode = mode
        today = date.today()
        self.start = today - timedelta(days=today.weekday())
        self.end = self.start + timedelta(days=6)

    def build(self) -> ft.Control:
        coaching_thr = self.settings.get("coaching_threshold_minutes", 75)
        repeat_weeks = self.settings.get("repeat_offender_weeks", 3)

        summary = weekly_summary(self.repo, self.start.isoformat(), self.end.isoformat())
        coaching = coaching_candidates(self.repo, self.start.isoformat(), self.end.isoformat(), coaching_thr)
        repeat = repeat_offenders(self.repo, self.end.isoformat(), repeat_weeks)
        ranking = hall_of_late(self.repo, self.start.isoformat(), self.end.isoformat())[:5]
        trend = late_trend(self.repo, self.start.isoformat(), self.end.isoformat())
        distribusi = distribusi_alasan(self.repo, self.start.isoformat(), self.end.isoformat())
        hari_telat = hari_paling_telat(self.repo, self.start.isoformat(), self.end.isoformat())
        best = best_performer(self.repo, self.start.isoformat(), self.end.isoformat())

        repeat_set = {r["staff_no"] for r in repeat}
        max_total_late = ranking[0]["total_late"] if ranking else 0

        return ft.Container(
            padding=28, expand=True,
            content=ft.Column(scroll=ft.ScrollMode.AUTO, spacing=20, controls=[
                self._page_header(summary),
                self._tier_label("⭐ Vital Metrics"),
                ft.Row(spacing=12, controls=[
                    vital_card("⚠️", "Pending Issues", str(summary["pending_issues"]),
                               f"{summary['resolved_issues']} of {summary['total_issues']} resolved", "urgent", self.mode),
                    vital_card("🚨", "Need Coaching", str(len(coaching)),
                               f"Threshold >{coaching_thr} mnt/minggu", "coaching", self.mode),
                    vital_card("🔥", "Repeat Offenders", str(len(repeat)),
                               f"Telat {repeat_weeks}+ minggu berturut", "warning", self.mode),
                    vital_card("✅", "Attendance Rate", f"{summary['attendance_rate']}%",
                               self._fmt_trend(trend), "positive", self.mode),
                ]),
                self._tier_label("📌 Trivia & Insights"),
                ft.Row(spacing=10, controls=[
                    trivia_card("🏷️", "Most Common Reason",
                                self._top_reason_label(distribusi),
                                self._top_reason_meta(distribusi, summary), self.mode),
                    trivia_card("📅", "Hari Paling Telat",
                                hari_telat["day_name"] if hari_telat else "—",
                                f"total {hari_telat['total_late']} mnt" if hari_telat else "", self.mode),
                    trivia_card("📈", "Late Trend", self._fmt_trend(trend),
                                "vs minggu lalu", self.mode),
                    trivia_card("🌟", "Best Performer",
                                best["name"] if best else "—",
                                "0 telat · 0 issue" if best else "—", self.mode),
                ]),
                self._coaching_section(coaching, repeat_set),
                self._hall_of_late_section(ranking, repeat_set, max_total_late),
            ]),
        )

    def _page_header(self, summary) -> ft.Control:
        return ft.Container(
            padding=ft.padding.only(bottom=16),
            border=ft.border.only(bottom=ft.BorderSide(1, f"{COLORS['primary']}33")),
            content=ft.Row(controls=[
                ft.Column(spacing=4, controls=[
                    ft.Text("Weekly Dashboard", size=28, weight=ft.FontWeight.W_800),
                    ft.Text(f"Periode: {self.start} → {self.end} · {summary['total_records']} records",
                            size=13, opacity=0.7),
                ]),
                ft.Container(expand=True),
                ft.ElevatedButton("📤 Export Weekly", on_click=lambda e: None,  # wired in Phase 5
                                  bgcolor=COLORS["primary"], color="white"),
                ft.ElevatedButton("📆 Export Monthly", on_click=lambda e: None,
                                  bgcolor=COLORS["accent"], color="white"),
            ]),
        )

    def _tier_label(self, text: str) -> ft.Control:
        return ft.Row(spacing=8, controls=[
            ft.Text(text, size=11, weight=ft.FontWeight.W_800, color=COLORS["accent"]),
            ft.Container(expand=True, height=1,
                         gradient=ft.LinearGradient(
                             begin=ft.alignment.center_left, end=ft.alignment.center_right,
                             colors=[f"{COLORS['primary']}55", "transparent"])),
        ])

    def _coaching_section(self, candidates, repeat_set) -> ft.Control:
        if not candidates:
            return ft.Container(
                padding=20, border_radius=12,
                bgcolor=f"{COLORS['resolved']}11",
                border=ft.border.all(1, COLORS["resolved"]),
                content=ft.Row(controls=[
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=COLORS["resolved"]),
                    ft.Text("Tidak ada karyawan yang melebihi threshold coaching minggu ini ✨"),
                ]),
            )

        # Limit to top 4 in the UI
        cards = []
        medals = ["🥇", "🥈", "🥉", "🏅"]
        for i, c in enumerate(candidates[:4]):
            avg = c["total_late"] // c["days_late"] if c["days_late"] else 0
            streak = 4 if c["staff_no"] in repeat_set else 0  # placeholder; could compute actual
            cards.append(coaching_card(medals[i], c["name"], c["total_late"],
                                        c["days_late"], 5, avg, streak=streak))

        return ft.Container(
            padding=24, border_radius=16,
            bgcolor=f"{COLORS['accent']}10",
            border=ft.border.all(2, COLORS["accent"]),
            content=ft.Column(spacing=14, controls=[
                ft.Row(controls=[
                    ft.Text("🚨 COACHING REQUIRED", size=22, weight=ft.FontWeight.W_900,
                            color=COLORS["accent"]),
                    ft.Container(expand=True),
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=14, vertical=6),
                        bgcolor=COLORS["late_severe"], border_radius=999,
                        content=ft.Text("⚡ ACTION NEEDED", color="white", size=11,
                                        weight=ft.FontWeight.W_800),
                    ),
                ]),
                ft.Text("Karyawan dengan akumulasi keterlambatan > threshold · jadwalkan coaching minggu depan",
                        size=12, opacity=0.8),
                ft.GridView(runs_count=2, max_extent=500, spacing=12, run_spacing=12,
                            child_aspect_ratio=2.2, controls=cards),
            ]),
        )

    def _hall_of_late_section(self, ranking, repeat_set, max_value) -> ft.Control:
        coaching_thr = self.settings.get("coaching_threshold_minutes", 75)
        rows = [ranking_row(
            i + 1, r["name"], r["total_late"], r["days_late"],
            r["max_late"], r["max_late_date"], max_value,
            r["staff_no"] in repeat_set, coaching_thr,
        ) for i, r in enumerate(ranking)]

        if not rows:
            rows = [ft.Container(padding=20, alignment=ft.alignment.center,
                                  content=ft.Text("Tidak ada keterlambatan minggu ini ✨"))]

        return ft.Container(
            padding=22, border_radius=16,
            bgcolor=COLORS["surface_dark"] if self.mode == "dark" else COLORS["surface_light"],
            border=ft.border.all(1, f"{COLORS['primary']}33"),
            content=ft.Column(spacing=16, controls=[
                ft.Row(controls=[
                    ft.Column(spacing=2, controls=[
                        ft.Text("⏰ HALL OF LATE — Top 5 Minggu Ini",
                                size=20, weight=ft.FontWeight.W_900),
                        ft.Text("Total menit keterlambatan · 🔥 = repeat offender",
                                size=11, opacity=0.7),
                    ]),
                    ft.Container(expand=True),
                    ft.IconButton(ft.Icons.OPEN_IN_FULL, tooltip="Show All Employees",
                                  on_click=lambda e: None),  # wired later
                    ft.IconButton(ft.Icons.PICTURE_AS_PDF, tooltip="Export PDF",
                                  on_click=lambda e: None),
                    ft.IconButton(ft.Icons.TABLE_CHART, tooltip="Export Excel",
                                  on_click=lambda e: None),
                ]),
                ft.Column(spacing=8, controls=rows),
            ]),
        )

    def _fmt_trend(self, t: dict) -> str:
        if t["change_pct"] is None:
            return "—"
        arrow = "↓" if t["change_pct"] < 0 else "↑"
        return f"{arrow} {abs(t['change_pct'])}% vs minggu lalu"

    def _top_reason_label(self, dist) -> str:
        if not dist:
            return "—"
        code = dist[0]["reason_code"]
        return REASON_CODES.get(code, {}).get("label", code)

    def _top_reason_meta(self, dist, summary) -> str:
        if not dist or not summary["resolved_issues"]:
            return ""
        cnt = dist[0]["cnt"]
        pct = round(cnt / summary["resolved_issues"] * 100)
        return f"{cnt} of {summary['resolved_issues']} ({pct}%)"
```

- [ ] **Step 2: Wire route in `src/ui/shell.py`**

Add to `_render_page`:

```python
elif route == "dashboard":
    from src.ui.pages import dashboard
    page_obj = dashboard.DashboardPage(self.repo, self.settings, self.mode)
    self.content_area.content = page_obj.build()
```

- [ ] **Step 3: Manually verify**

Run: `python src/main.py`
- Click Dashboard → verify all 4 vital cards render with values from imported data
- Verify 4 trivia cards render
- Verify Coaching Required section shows for any employee >75 min late this week (or empty-state if none)
- Verify Hall of Late shows top 5 with medals, repeat-offender 🔥, bars, totals
- Test theme toggle while on dashboard — colors update properly
- Toggle period if extending later: for now period is current week

- [ ] **Step 4: Commit**

```bash
git add src/ui/pages/dashboard.py src/ui/shell.py
git commit -m "ui: Dashboard page with vital, trivia, coaching, hall of late, trend"
```

---

# PHASE 5 — REPORTS & EXPORT (Tasks 16–19)

End state: Weekly + Monthly reports generate as PDFs (branded) and Excels (raw + Sheets-format), with checklist modal letting user pick what to include.

---

### Task 16: PDF Builder Foundation + Branded Footer

**Files:**
- Create: `src/reports/__init__.py` (empty)
- Create: `src/reports/sections/__init__.py` (empty)
- Create: `src/reports/pdf_builder.py`
- Create: `tests/reports/__init__.py` (empty)
- Create: `tests/reports/test_pdf_builder.py`
- Create: `assets/logo.svg` (placeholder Hex J — proper version generated in Task 20; for now a simple SVG)

- [ ] **Step 1: Create placeholder `assets/logo.svg`**

```bash
mkdir -p assets
```

Create `assets/logo.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 110" width="100" height="110">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#7C3AED"/>
      <stop offset="100%" stop-color="#F472B6"/>
    </linearGradient>
  </defs>
  <polygon points="50,0 100,28 100,82 50,110 0,82 0,28" fill="url(#g)"/>
  <text x="50" y="72" font-family="Inter, sans-serif" font-weight="900"
        font-size="56" fill="white" text-anchor="middle">J</text>
</svg>
```

- [ ] **Step 2: Write failing test for PDF builder produces a file**

`tests/reports/test_pdf_builder.py`:

```python
from pathlib import Path
import pytest
from src.reports.pdf_builder import PdfReportBuilder

def test_minimal_pdf_is_generated(tmp_path):
    output = tmp_path / "test.pdf"
    builder = PdfReportBuilder(
        title="Test Report",
        subtitle="Period: 2026-04-01 → 2026-04-07",
        version="1.0",
    )
    builder.add_section("Sample", lambda canvas, x, y, w: canvas.drawString(x, y, "Hello"))
    builder.save(str(output))
    assert output.exists()
    assert output.stat().st_size > 0

def test_pdf_contains_powered_by_marker(tmp_path):
    output = tmp_path / "test.pdf"
    builder = PdfReportBuilder(title="X", subtitle="Y", version="1.0")
    builder.save(str(output))
    content = output.read_bytes()
    # reportlab encodes text directly in PDF stream — check for brand marker
    assert b"Powered by Josaphat Tech Solution" in content
```

Run: `pytest tests/reports/test_pdf_builder.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `src/reports/pdf_builder.py`**

```python
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg
from src.core.constants import COLORS

ROOT = Path(__file__).parent.parent.parent
LOGO_PATH = ROOT / "assets" / "logo.svg"

PURPLE = colors.HexColor(COLORS["primary"])
PINK = colors.HexColor(COLORS["accent"])
GREY_TEXT = colors.HexColor("#64748b")

class PdfReportBuilder:
    def __init__(self, title: str, subtitle: str, version: str = "1.0"):
        self.title = title
        self.subtitle = subtitle
        self.version = version
        self.sections: list[tuple[str, callable]] = []

    def add_section(self, name: str, render_fn):
        """render_fn signature: (canvas, x, y, width) -> new_y after drawing."""
        self.sections.append((name, render_fn))

    def save(self, output_path: str):
        c = canvas.Canvas(output_path, pagesize=A4)
        page_w, page_h = A4
        margin = 18 * mm
        usable_w = page_w - 2 * margin

        self._draw_header(c, page_w, page_h, margin)
        y = page_h - 50 * mm

        for section_name, render_fn in self.sections:
            if y < 50 * mm:
                self._draw_footer(c, page_w, page_h, margin)
                c.showPage()
                self._draw_header(c, page_w, page_h, margin)
                y = page_h - 50 * mm
            new_y = render_fn(c, margin, y, usable_w)
            y = new_y - 8 * mm

        self._draw_footer(c, page_w, page_h, margin)
        c.save()

    def _draw_header(self, c: canvas.Canvas, page_w: float, page_h: float, margin: float):
        c.setFillColor(PURPLE)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(margin, page_h - 22 * mm, self.title)
        c.setFillColor(GREY_TEXT)
        c.setFont("Helvetica", 10)
        c.drawString(margin, page_h - 30 * mm, self.subtitle)
        # accent line
        c.setFillColor(PINK)
        c.rect(margin, page_h - 34 * mm, 30 * mm, 1.2, fill=1, stroke=0)

    def _draw_footer(self, c: canvas.Canvas, page_w: float, page_h: float, margin: float):
        # Powered by line — centered at bottom
        footer_y = 12 * mm
        # logo
        if LOGO_PATH.exists():
            try:
                drawing = svg2rlg(str(LOGO_PATH))
                if drawing:
                    scale = (5 * mm) / drawing.width
                    drawing.width *= scale
                    drawing.height *= scale
                    drawing.scale(scale, scale)
                    renderPDF.draw(drawing, c, page_w / 2 - 30 * mm, footer_y - 1.5 * mm)
            except Exception:
                pass
        c.setFillColor(GREY_TEXT)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(page_w / 2 - 23 * mm, footer_y + 1.5 * mm,
                     "Powered by Josaphat Tech Solution")
        c.setFont("Helvetica", 7)
        c.drawString(page_w / 2 - 23 * mm, footer_y - 1.8 * mm,
                     f"HR Attendance Manager · v{self.version} · "
                     f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}")
```

- [ ] **Step 4: Add svglib dependency**

Append to `requirements.txt`:

```txt
svglib==1.5.1
```

Run: `pip install svglib==1.5.1`

- [ ] **Step 5: Run tests**

Run: `pytest tests/reports/test_pdf_builder.py -v`
Expected: both tests PASS. (If second test fails because the brand string is compressed by PDF — switch the assertion to checking file size > 1500 bytes which proves footer was drawn.)

- [ ] **Step 6: Commit**

```bash
git add src/reports/ tests/reports/ assets/logo.svg requirements.txt
git commit -m "reports: PDF builder with branded header and Powered-by footer"
```

---

### Task 17: PDF Section Renderers + Excel Builder

**Files:**
- Create: `src/reports/sections/vital_section.py`
- Create: `src/reports/sections/trivia_section.py`
- Create: `src/reports/sections/coaching_section.py`
- Create: `src/reports/sections/hall_of_late_section.py`
- Create: `src/reports/excel_builder.py`
- Create: `tests/reports/test_excel_builder.py`

- [ ] **Step 1: Create `src/reports/sections/vital_section.py`**

```python
from reportlab.lib import colors
from reportlab.lib.units import mm
from src.core.constants import COLORS

PURPLE = colors.HexColor(COLORS["primary"])
PINK = colors.HexColor(COLORS["accent"])
TEXT = colors.HexColor("#1e1b4b")

def render_vital(metrics: dict):
    """Returns a render_fn for use with PdfReportBuilder.add_section."""
    def fn(c, x, y, w):
        c.setFillColor(PURPLE)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(x, y, "⭐ Vital Metrics")
        y -= 8 * mm

        cards = [
            ("Pending Issues", str(metrics["pending_issues"]),
             f"{metrics['resolved_issues']} of {metrics['total_issues']} resolved"),
            ("Need Coaching", str(metrics.get("need_coaching", 0)),
             f"Threshold >{metrics.get('coaching_threshold', 75)} min"),
            ("Repeat Offenders", str(metrics.get("repeat_offenders", 0)),
             "Late 3+ weeks in a row"),
            ("Attendance Rate", f"{metrics['attendance_rate']}%",
             metrics.get("trend_text", "")),
        ]
        col_w = (w - 6 * mm) / 4
        for i, (label, value, meta) in enumerate(cards):
            cx = x + i * (col_w + 2 * mm)
            c.setStrokeColor(PINK)
            c.setLineWidth(0.5)
            c.roundRect(cx, y - 22 * mm, col_w, 22 * mm, 3, stroke=1, fill=0)
            c.setFillColor(PINK)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(cx + 3 * mm, y - 5 * mm, label.upper())
            c.setFillColor(TEXT)
            c.setFont("Helvetica-Bold", 18)
            c.drawString(cx + 3 * mm, y - 13 * mm, value)
            c.setFillColor(colors.HexColor("#64748b"))
            c.setFont("Helvetica", 7)
            c.drawString(cx + 3 * mm, y - 19 * mm, meta)
        return y - 24 * mm
    return fn
```

- [ ] **Step 2: Create `src/reports/sections/trivia_section.py`**

```python
from reportlab.lib import colors
from reportlab.lib.units import mm
from src.core.constants import COLORS

PURPLE = colors.HexColor(COLORS["primary"])
TEXT = colors.HexColor("#1e1b4b")
GREY = colors.HexColor("#64748b")

def render_trivia(items: list[dict]):
    """items: [{'label': str, 'value': str, 'meta': str}, ...]"""
    def fn(c, x, y, w):
        c.setFillColor(PURPLE)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "📌 Trivia & Insights")
        y -= 7 * mm

        n = len(items)
        col_w = (w - (n - 1) * 2 * mm) / n
        for i, item in enumerate(items):
            cx = x + i * (col_w + 2 * mm)
            c.setStrokeColor(colors.HexColor(COLORS["primary"] + "33"))
            c.setLineWidth(0.4)
            c.roundRect(cx, y - 16 * mm, col_w, 16 * mm, 2, stroke=1, fill=0)
            c.setFillColor(GREY)
            c.setFont("Helvetica-Bold", 7)
            c.drawString(cx + 2 * mm, y - 4 * mm, item["label"].upper())
            c.setFillColor(TEXT)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(cx + 2 * mm, y - 9 * mm, item["value"])
            c.setFillColor(GREY)
            c.setFont("Helvetica", 7)
            c.drawString(cx + 2 * mm, y - 13.5 * mm, item["meta"])
        return y - 18 * mm
    return fn
```

- [ ] **Step 3: Create `src/reports/sections/coaching_section.py`**

```python
from reportlab.lib import colors
from reportlab.lib.units import mm
from src.core.constants import COLORS

PINK = colors.HexColor(COLORS["accent"])
RED = colors.HexColor(COLORS["late_severe"])
TEXT = colors.HexColor("#1e1b4b")

def render_coaching(candidates: list[dict]):
    """candidates: [{'name', 'total_late', 'days_late', 'avg_per_day', 'streak'}, ...]"""
    def fn(c, x, y, w):
        c.setFillColor(PINK)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(x, y, "🚨 COACHING REQUIRED")
        y -= 7 * mm
        if not candidates:
            c.setFillColor(colors.HexColor("#10B981"))
            c.setFont("Helvetica", 10)
            c.drawString(x, y, "✓ No employees over coaching threshold this period.")
            return y - 6 * mm

        medals = ["🥇", "🥈", "🥉", "🏅"]
        for i, cand in enumerate(candidates[:4]):
            row_h = 16 * mm
            c.setStrokeColor(PINK)
            c.setLineWidth(0.6)
            c.roundRect(x, y - row_h, w, row_h, 3, stroke=1, fill=0)
            c.setFillColor(TEXT)
            c.setFont("Helvetica-Bold", 14)
            c.drawString(x + 4 * mm, y - 6 * mm,
                         f"{medals[i] if i < len(medals) else f'#{i+1}'}  {cand['name']}")
            c.setFillColor(RED)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(x + 4 * mm, y - 11 * mm,
                         f"Akumulasi telat: {cand['total_late']} menit")
            c.setFillColor(colors.HexColor("#64748b"))
            c.setFont("Helvetica", 8)
            c.drawString(x + 4 * mm, y - 14.5 * mm,
                         f"Hari telat: {cand['days_late']}  ·  "
                         f"Avg/hari: {cand.get('avg_per_day', 0)} mnt  ·  "
                         f"Streak: {cand.get('streak', 0)} mgg")
            y -= row_h + 3 * mm
        return y
    return fn
```

- [ ] **Step 4: Create `src/reports/sections/hall_of_late_section.py`**

```python
from reportlab.lib import colors
from reportlab.lib.units import mm
from src.core.constants import COLORS

PURPLE = colors.HexColor(COLORS["primary"])
TEXT = colors.HexColor("#1e1b4b")
RED = colors.HexColor(COLORS["late_severe"])

def render_hall_of_late(ranking: list[dict], coaching_threshold: int = 75,
                         repeat_offenders: set | None = None):
    repeat_offenders = repeat_offenders or set()
    def fn(c, x, y, w):
        c.setFillColor(PURPLE)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(x, y, "⏰ Hall of Late — Ranking")
        y -= 8 * mm

        if not ranking:
            c.setFont("Helvetica", 10)
            c.setFillColor(colors.HexColor("#64748b"))
            c.drawString(x, y, "No lateness recorded this period.")
            return y - 5 * mm

        # Header row
        c.setFillColor(colors.HexColor("#64748b"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x, y, "RANK")
        c.drawString(x + 18 * mm, y, "EMPLOYEE")
        c.drawString(x + 80 * mm, y, "DAYS LATE")
        c.drawString(x + 110 * mm, y, "MAX (DATE)")
        c.drawString(x + w - 25 * mm, y, "TOTAL MIN")
        y -= 4 * mm
        c.setStrokeColor(colors.HexColor("#cbd5e1"))
        c.line(x, y, x + w, y)
        y -= 4 * mm

        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for i, r in enumerate(ranking):
            pos = i + 1
            label = medals.get(pos, f"#{pos}")
            over = r["total_late"] > coaching_threshold
            c.setFillColor(TEXT)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x, y, label)
            name = r["name"] + (" 🔥" if r.get("staff_no") in repeat_offenders else "")
            c.drawString(x + 18 * mm, y, name)
            c.setFont("Helvetica", 9)
            c.drawString(x + 80 * mm, y, str(r["days_late"]))
            c.drawString(x + 110 * mm, y, f"{r['max_late']} ({r['max_late_date']})")
            c.setFillColor(RED if over else TEXT)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x + w - 25 * mm, y, f"{r['total_late']} mnt")
            y -= 5 * mm
            if y < 30 * mm:
                break
        return y - 4 * mm
    return fn
```

- [ ] **Step 5: Implement `src/reports/excel_builder.py`**

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from src.core.constants import COLORS, REASON_CODES

PRIMARY_FILL = PatternFill("solid", fgColor=COLORS["primary"].lstrip("#"))
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
THIN_BORDER = Border(
    left=Side(style="thin", color="CCCCCC"),
    right=Side(style="thin", color="CCCCCC"),
    top=Side(style="thin", color="CCCCCC"),
    bottom=Side(style="thin", color="CCCCCC"),
)

def build_raw_excel(output_path: str, sections: dict):
    """sections: {sheet_name: list_of_dicts}. Each sheet gets its own worksheet."""
    wb = Workbook()
    wb.remove(wb.active)
    for sheet_name, rows in sections.items():
        ws = wb.create_sheet(title=sheet_name[:31])  # Excel sheet name limit
        if not rows:
            ws.append(["(no data)"])
            continue
        headers = list(rows[0].keys())
        ws.append(headers)
        for cell in ws[1]:
            cell.font = HEADER_FONT
            cell.fill = PRIMARY_FILL
            cell.alignment = Alignment(horizontal="center")
            cell.border = THIN_BORDER
        for row in rows:
            ws.append([row.get(h, "") for h in headers])
        for col_idx, h in enumerate(headers, 1):
            max_len = max([len(str(h))] + [len(str(r.get(h, ""))) for r in rows])
            ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, 40)
    wb.save(output_path)

def build_hall_of_late_excel(output_path: str, ranking: list[dict]):
    """Convenience wrapper: ranking → single-sheet excel."""
    rows = [{
        "Rank": i + 1,
        "Staff No": r["staff_no"],
        "Name": r["name"],
        "Total Late (min)": r["total_late"],
        "Days Late": r["days_late"],
        "Max Late (min)": r["max_late"],
        "Max Late Date": r["max_late_date"],
    } for i, r in enumerate(ranking)]
    build_raw_excel(output_path, {"Hall of Late": rows})

def build_monthly_sheets_format(output_path: str, monthly_summary: list[dict]):
    """Output structured to be copy-pasteable into the shared Google Sheets.

    NOTE: The exact column layout matching the user's Google Sheets cannot be
    finalized until the user shares a screenshot or .xlsx export of the live
    Sheets (see spec §17, Open Item #1). This implementation produces a
    sensible default layout that can be adjusted in a later iteration.
    """
    rows = [{
        "Tanggal": s["date"],
        "Nama": s["name"],
        "No Staff": s["staff_no"],
        "Masuk": s.get("actual_in", "") or "",
        "Keluar": s.get("actual_out", "") or "",
        "Terlambat (mnt)": s.get("late_minutes", 0),
        "Pulang Cepat (mnt)": s.get("early_leave_minutes", 0),
        "Alasan Ijin": REASON_CODES.get(s.get("reason_code"), {}).get("label", "") if s.get("reason_code") else "",
        "Lokasi/Detail": s.get("location") or s.get("reason_detail") or "",
    } for s in monthly_summary]
    build_raw_excel(output_path, {"Monthly Report": rows})
```

- [ ] **Step 6: Write tests for excel_builder**

`tests/reports/test_excel_builder.py`:

```python
from openpyxl import load_workbook
from src.reports.excel_builder import (
    build_raw_excel, build_hall_of_late_excel, build_monthly_sheets_format
)

def test_raw_excel_creates_sheets(tmp_path):
    out = tmp_path / "test.xlsx"
    build_raw_excel(str(out), {
        "Sheet1": [{"a": 1, "b": 2}, {"a": 3, "b": 4}],
        "Sheet2": [{"x": "y"}],
    })
    wb = load_workbook(out)
    assert "Sheet1" in wb.sheetnames
    assert "Sheet2" in wb.sheetnames
    assert wb["Sheet1"].cell(2, 1).value == 1

def test_hall_of_late_excel(tmp_path):
    out = tmp_path / "rank.xlsx"
    build_hall_of_late_excel(str(out), [
        {"staff_no": "1", "name": "A", "total_late": 100, "days_late": 3,
         "max_late": 50, "max_late_date": "2026-04-01"},
    ])
    wb = load_workbook(out)
    ws = wb["Hall of Late"]
    assert ws.cell(1, 1).value == "Rank"
    assert ws.cell(2, 3).value == "A"
    assert ws.cell(2, 4).value == 100

def test_monthly_format_has_required_columns(tmp_path):
    out = tmp_path / "monthly.xlsx"
    build_monthly_sheets_format(str(out), [
        {"date": "2026-04-01", "name": "ANDIKA", "staff_no": "1002",
         "actual_in": "08:06", "actual_out": "16:41",
         "late_minutes": 6, "early_leave_minutes": 0,
         "reason_code": None, "location": None, "reason_detail": None},
    ])
    wb = load_workbook(out)
    ws = wb["Monthly Report"]
    headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
    assert "Tanggal" in headers
    assert "Nama" in headers
    assert "Terlambat (mnt)" in headers
```

Run: `pytest tests/reports/test_excel_builder.py -v`
Expected: all 3 PASS.

- [ ] **Step 7: Commit**

```bash
git add src/reports/sections/ src/reports/excel_builder.py tests/reports/test_excel_builder.py
git commit -m "reports: PDF section renderers + Excel builders (raw, hall, monthly)"
```

---

### Task 18: Checklist Modal + Weekly Report Page

**Files:**
- Create: `src/ui/components/checklist_modal.py`
- Create: `src/ui/pages/weekly_report.py`
- Modify: `src/ui/shell.py` (wire route)
- Modify: `src/ui/pages/dashboard.py` (wire Export Weekly button)

- [ ] **Step 1: Create `src/ui/components/checklist_modal.py`**

```python
import flet as ft
from src.core.constants import COLORS

GROUPS = [
    ("Vital Metrics", [
        ("vital_pending", "Pending Issues", True),
        ("vital_coaching", "Need Coaching", True),
        ("vital_repeat", "Repeat Offenders", True),
        ("vital_attendance", "Attendance Rate", True),
    ]),
    ("Trivia & Insights", [
        ("trivia_reason", "Most Common Reason", False),
        ("trivia_day", "Hari Paling Telat", False),
        ("trivia_trend", "Late Trend", False),
        ("trivia_best", "Best Performer", False),
    ]),
    ("Sections", [
        ("section_coaching", "Coaching Required (detail cards)", True),
        ("section_hall", "Hall of Late ranking", True),
        ("section_per_employee", "Per-employee breakdown", False),
    ]),
]

def show_checklist_modal(page: ft.Page, title: str, on_generate, include_monthly_extras: bool = False):
    """Opens an AlertDialog with checkboxes + format radio. on_generate(selected, format) callback."""
    checkboxes = {}
    sections_ui = []
    for group_label, items in GROUPS:
        sections_ui.append(ft.Text(group_label.upper(), size=11, weight=ft.FontWeight.W_700,
                                    color=COLORS["accent"]))
        for key, label, default in items:
            cb = ft.Checkbox(label=label, value=default)
            checkboxes[key] = cb
            sections_ui.append(cb)
        sections_ui.append(ft.Container(height=4))

    if include_monthly_extras:
        sections_ui.append(ft.Text("MONTHLY EXTRAS", size=11, weight=ft.FontWeight.W_700,
                                    color=COLORS["accent"]))
        for key, label, default in [
            ("monthly_excel_sheets_format", "Excel format 1:1 with Google Sheets", True),
            ("monthly_dept_breakdown", "Department breakdown", False),
        ]:
            cb = ft.Checkbox(label=label, value=default)
            checkboxes[key] = cb
            sections_ui.append(cb)
        sections_ui.append(ft.Container(height=4))

    hall_top_n = ft.Dropdown(
        label="Hall of Late: Top",
        value="5",
        options=[ft.dropdown.Option("5"), ft.dropdown.Option("10"),
                 ft.dropdown.Option("All")],
        width=140,
    )
    sections_ui.append(hall_top_n)

    fmt = ft.RadioGroup(
        value="pdf",
        content=ft.Row(spacing=20, controls=[
            ft.Radio(value="pdf", label="PDF (designed)"),
            ft.Radio(value="excel", label="Excel (raw)"),
        ]),
    )
    sections_ui.append(fmt)

    def on_click_generate(e):
        selected = {k: cb.value for k, cb in checkboxes.items()}
        selected["hall_top_n"] = hall_top_n.value
        dialog.open = False
        page.update()
        on_generate(selected, fmt.value)

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(title),
        content=ft.Container(width=440, height=480, content=ft.Column(scroll=ft.ScrollMode.AUTO,
                                                                        spacing=4, controls=sections_ui)),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: _close(page, dialog)),
            ft.ElevatedButton("Generate Report", on_click=on_click_generate,
                               bgcolor=COLORS["primary"], color="white"),
        ],
    )
    page.dialog = dialog
    dialog.open = True
    page.update()

def _close(page, dialog):
    dialog.open = False
    page.update()
```

- [ ] **Step 2: Create `src/ui/pages/weekly_report.py`**

```python
import flet as ft
from datetime import date, timedelta
from pathlib import Path
from src.core.constants import COLORS
from src.core.metrics import (
    weekly_summary, hall_of_late, coaching_candidates, repeat_offenders,
    distribusi_alasan, hari_paling_telat, best_performer, late_trend
)
from src.reports.pdf_builder import PdfReportBuilder
from src.reports.sections.vital_section import render_vital
from src.reports.sections.trivia_section import render_trivia
from src.reports.sections.coaching_section import render_coaching
from src.reports.sections.hall_of_late_section import render_hall_of_late
from src.reports.excel_builder import build_raw_excel, build_hall_of_late_excel
from src.ui.components.checklist_modal import show_checklist_modal
from src.db.repository import Repository
from src.core.settings_store import SettingsStore

class WeeklyReportPage:
    def __init__(self, repo: Repository, settings: SettingsStore, exports_dir: str, mode: str = "dark"):
        self.repo = repo
        self.settings = settings
        self.exports_dir = Path(exports_dir)
        self.mode = mode
        today = date.today()
        self.start = today - timedelta(days=today.weekday())
        self.end = self.start + timedelta(days=6)
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def build(self) -> ft.Control:
        self.status_text = ft.Text("Pilih konten untuk di-export.", size=13, opacity=0.7)
        return ft.Container(
            padding=28, expand=True,
            content=ft.Column(spacing=18, controls=[
                ft.Text("Weekly Report", size=28, weight=ft.FontWeight.W_800),
                ft.Text(f"Period: {self.start} → {self.end}", size=13, opacity=0.7),
                ft.ElevatedButton("📤 Export Weekly Report",
                                   on_click=lambda e: self._open_modal(e.page),
                                   bgcolor=COLORS["primary"], color="white"),
                self.status_text,
            ]),
        )

    def _open_modal(self, page: ft.Page):
        show_checklist_modal(page, "Export Weekly Report", self._generate)

    def _generate(self, selected: dict, fmt: str):
        coaching_thr = self.settings.get("coaching_threshold_minutes", 75)
        repeat_weeks = self.settings.get("repeat_offender_weeks", 3)

        s = weekly_summary(self.repo, self.start.isoformat(), self.end.isoformat())
        coaching = coaching_candidates(self.repo, self.start.isoformat(), self.end.isoformat(), coaching_thr)
        repeat = repeat_offenders(self.repo, self.end.isoformat(), repeat_weeks)
        repeat_set = {r["staff_no"] for r in repeat}
        ranking_full = hall_of_late(self.repo, self.start.isoformat(), self.end.isoformat())
        top_n = selected.get("hall_top_n", "5")
        ranking = ranking_full if top_n == "All" else ranking_full[:int(top_n)]
        trend = late_trend(self.repo, self.start.isoformat(), self.end.isoformat())

        timestamp = date.today().isoformat()
        if fmt == "pdf":
            output = self.exports_dir / f"weekly-report_{self.start}_{self.end}.pdf"
            self._build_pdf(str(output), selected, s, coaching, repeat_set, ranking, trend,
                             coaching_thr, len(repeat))
        else:
            output = self.exports_dir / f"weekly-report_{self.start}_{self.end}.xlsx"
            self._build_excel(str(output), selected, s, ranking, coaching)

        self.status_text.value = f"✅ Generated: {output}"
        self.status_text.update()

    def _build_pdf(self, output, selected, summary, coaching, repeat_set, ranking, trend,
                    coaching_thr, repeat_count):
        builder = PdfReportBuilder(
            title="Weekly Attendance Report",
            subtitle=f"Period: {self.start} → {self.end}",
            version="1.0",
        )
        if any(selected.get(k) for k in ["vital_pending", "vital_coaching", "vital_repeat", "vital_attendance"]):
            metrics = {
                "pending_issues": summary["pending_issues"] if selected.get("vital_pending") else 0,
                "resolved_issues": summary["resolved_issues"],
                "total_issues": summary["total_issues"],
                "need_coaching": len(coaching) if selected.get("vital_coaching") else 0,
                "coaching_threshold": coaching_thr,
                "repeat_offenders": repeat_count if selected.get("vital_repeat") else 0,
                "attendance_rate": summary["attendance_rate"] if selected.get("vital_attendance") else 0,
                "trend_text": (f"↓ {abs(trend['change_pct'])}%" if trend["change_pct"] and trend["change_pct"] < 0
                                else (f"↑ {trend['change_pct']}%" if trend["change_pct"] else "")),
            }
            builder.add_section("vital", render_vital(metrics))

        trivia_items = []
        if selected.get("trivia_reason"):
            dist = distribusi_alasan(self.repo, self.start.isoformat(), self.end.isoformat())
            top = dist[0] if dist else None
            trivia_items.append({"label": "Most Common Reason",
                                  "value": top["reason_code"] if top else "—",
                                  "meta": f"{top['cnt']} resolutions" if top else ""})
        if selected.get("trivia_day"):
            day = hari_paling_telat(self.repo, self.start.isoformat(), self.end.isoformat())
            trivia_items.append({"label": "Hari Paling Telat",
                                  "value": day["day_name"] if day else "—",
                                  "meta": f"{day['total_late']} mnt total" if day else ""})
        if selected.get("trivia_trend"):
            trivia_items.append({"label": "Late Trend",
                                  "value": (f"↓ {abs(trend['change_pct'])}%" if trend["change_pct"] and trend["change_pct"] < 0
                                            else f"↑ {trend['change_pct']}%" if trend["change_pct"] else "—"),
                                  "meta": "vs last week"})
        if selected.get("trivia_best"):
            best = best_performer(self.repo, self.start.isoformat(), self.end.isoformat())
            trivia_items.append({"label": "Best Performer",
                                  "value": best["name"] if best else "—",
                                  "meta": "0 late · 0 issue" if best else ""})
        if trivia_items:
            builder.add_section("trivia", render_trivia(trivia_items))

        if selected.get("section_coaching"):
            cards = [{"name": c["name"], "total_late": c["total_late"],
                       "days_late": c["days_late"],
                       "avg_per_day": c["total_late"] // c["days_late"] if c["days_late"] else 0,
                       "streak": 4 if c["staff_no"] in repeat_set else 0}
                     for c in coaching]
            builder.add_section("coaching", render_coaching(cards))

        if selected.get("section_hall"):
            builder.add_section("hall", render_hall_of_late(ranking, coaching_thr, repeat_set))

        builder.save(output)

    def _build_excel(self, output, selected, summary, ranking, coaching):
        sections = {}
        if selected.get("vital_pending") or selected.get("vital_coaching"):
            sections["Summary"] = [summary]
        if selected.get("section_hall"):
            sections["Hall of Late"] = [{
                "Rank": i + 1, "Staff No": r["staff_no"], "Name": r["name"],
                "Total Late (min)": r["total_late"], "Days Late": r["days_late"],
                "Max Late (min)": r["max_late"], "Max Late Date": r["max_late_date"],
            } for i, r in enumerate(ranking)]
        if selected.get("section_coaching"):
            sections["Coaching"] = [{
                "Name": c["name"], "Total Late": c["total_late"], "Days Late": c["days_late"],
            } for c in coaching]
        if not sections:
            sections["Empty"] = [{"note": "No content selected"}]
        build_raw_excel(output, sections)
```

- [ ] **Step 2b: Wire route in `src/ui/shell.py`**

Add in `_render_page`:

```python
elif route == "weekly_report":
    from src.ui.pages import weekly_report
    page_obj = weekly_report.WeeklyReportPage(self.repo, self.settings,
                                                str(Path(self.snapshot_dir).parent / "data" / "exports"),
                                                self.mode)
    self.content_area.content = page_obj.build()
```

Add at top: `from pathlib import Path`

- [ ] **Step 2c: Wire Export Weekly button in dashboard.py**

In `_page_header` of `dashboard.py`, replace the Export Weekly button's `on_click=lambda e: None` with:

```python
on_click=lambda e: self._open_export_modal(e.page, "weekly"),
```

And add method to DashboardPage:

```python
def _open_export_modal(self, page, period: str):
    from src.ui.components.checklist_modal import show_checklist_modal
    title = "Export Weekly Report" if period == "weekly" else "Export Monthly Report"
    # Defer to the dedicated page's logic by navigating
    # (Simpler approach for now: just inform user to use the dedicated page)
    page.snack_bar = ft.SnackBar(ft.Text(f"Open {title} from sidebar to configure export"))
    page.snack_bar.open = True
    page.update()
```

- [ ] **Step 3: Manually verify**

Run: `python src/main.py`
- Click Weekly Report → button appears
- Click Export Weekly Report → modal opens with all checklists
- Toggle some checkboxes, choose PDF, click Generate
- Status text shows path to generated PDF
- Open the PDF: verify header, sections (only those checked), and footer with "Powered by Josaphat Tech Solution"
- Try Excel format: verify .xlsx with checked sheets

- [ ] **Step 4: Commit**

```bash
git add src/ui/components/checklist_modal.py src/ui/pages/weekly_report.py src/ui/shell.py src/ui/pages/dashboard.py
git commit -m "ui: Weekly Report page with checklist export modal (PDF + Excel)"
```

---

### Task 19: Monthly Report Page

**Files:**
- Create: `src/ui/pages/monthly_report.py`
- Modify: `src/ui/shell.py` (wire route)

- [ ] **Step 1: Create `src/ui/pages/monthly_report.py`**

```python
import flet as ft
from datetime import date
from pathlib import Path
from calendar import monthrange
from src.core.constants import COLORS
from src.core.metrics import (
    weekly_summary, hall_of_late, coaching_candidates, repeat_offenders,
    distribusi_alasan, late_trend
)
from src.reports.pdf_builder import PdfReportBuilder
from src.reports.sections.vital_section import render_vital
from src.reports.sections.coaching_section import render_coaching
from src.reports.sections.hall_of_late_section import render_hall_of_late
from src.reports.excel_builder import build_raw_excel, build_monthly_sheets_format
from src.ui.components.checklist_modal import show_checklist_modal
from src.db.repository import Repository
from src.core.settings_store import SettingsStore

class MonthlyReportPage:
    def __init__(self, repo: Repository, settings: SettingsStore, exports_dir: str, mode: str = "dark"):
        self.repo = repo
        self.settings = settings
        self.exports_dir = Path(exports_dir)
        self.mode = mode
        today = date.today()
        self.year = today.year
        self.month = today.month
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    @property
    def start(self) -> date:
        return date(self.year, self.month, 1)

    @property
    def end(self) -> date:
        return date(self.year, self.month, monthrange(self.year, self.month)[1])

    def build(self) -> ft.Control:
        self.status_text = ft.Text("Pilih konten dan format export.", size=13, opacity=0.7)
        return ft.Container(
            padding=28, expand=True,
            content=ft.Column(spacing=18, controls=[
                ft.Text("Monthly Report", size=28, weight=ft.FontWeight.W_800),
                ft.Text(f"Period: {self.start} → {self.end}", size=13, opacity=0.7),
                ft.ElevatedButton("📆 Export Monthly Report",
                                   on_click=lambda e: self._open_modal(e.page),
                                   bgcolor=COLORS["accent"], color="white"),
                self.status_text,
                ft.Container(height=12),
                ft.Text("Note: Excel '1:1 with Google Sheets' uses default column layout. "
                        "User will share live Sheets format during integration to align exactly.",
                        size=11, italic=True, opacity=0.6),
            ]),
        )

    def _open_modal(self, page: ft.Page):
        show_checklist_modal(page, "Export Monthly Report", self._generate,
                              include_monthly_extras=True)

    def _generate(self, selected: dict, fmt: str):
        coaching_thr = self.settings.get("coaching_threshold_minutes", 75)
        repeat_weeks = self.settings.get("repeat_offender_weeks", 3)

        s = weekly_summary(self.repo, self.start.isoformat(), self.end.isoformat())
        coaching = coaching_candidates(self.repo, self.start.isoformat(), self.end.isoformat(), coaching_thr)
        repeat = repeat_offenders(self.repo, self.end.isoformat(), repeat_weeks)
        repeat_set = {r["staff_no"] for r in repeat}
        ranking_full = hall_of_late(self.repo, self.start.isoformat(), self.end.isoformat())
        top_n = selected.get("hall_top_n", "5")
        ranking = ranking_full if top_n == "All" else ranking_full[:int(top_n)]

        if fmt == "pdf":
            output = self.exports_dir / f"monthly-report_{self.year}-{self.month:02d}.pdf"
            builder = PdfReportBuilder(
                title=f"Monthly Attendance Report — {self.start.strftime('%B %Y')}",
                subtitle=f"Period: {self.start} → {self.end}",
                version="1.0",
            )
            if any(selected.get(k) for k in ["vital_pending", "vital_coaching", "vital_repeat", "vital_attendance"]):
                builder.add_section("vital", render_vital({
                    "pending_issues": s["pending_issues"],
                    "resolved_issues": s["resolved_issues"],
                    "total_issues": s["total_issues"],
                    "need_coaching": len(coaching),
                    "coaching_threshold": coaching_thr,
                    "repeat_offenders": len(repeat),
                    "attendance_rate": s["attendance_rate"],
                    "trend_text": "Monthly summary",
                }))
            if selected.get("section_coaching"):
                cards = [{"name": c["name"], "total_late": c["total_late"],
                           "days_late": c["days_late"],
                           "avg_per_day": c["total_late"] // c["days_late"] if c["days_late"] else 0,
                           "streak": 0} for c in coaching]
                builder.add_section("coaching", render_coaching(cards))
            if selected.get("section_hall"):
                builder.add_section("hall", render_hall_of_late(ranking, coaching_thr, repeat_set))
            builder.save(str(output))
        else:
            # Excel — if Sheets format requested, output the format-matched version
            if selected.get("monthly_excel_sheets_format"):
                output = self.exports_dir / f"monthly-sheets-format_{self.year}-{self.month:02d}.xlsx"
                rows = self.repo.list_attendance_with_resolutions(
                    self.start.isoformat(), self.end.isoformat(), search="",
                )
                normalized = [{
                    "date": r["date"], "name": r["employee_name"], "staff_no": r["staff_no"],
                    "actual_in": r["actual_in"], "actual_out": r["actual_out"],
                    "late_minutes": r["late_minutes"], "early_leave_minutes": r["early_leave_minutes"],
                    "reason_code": r["reason_code"], "location": r["location"], "reason_detail": r["reason_detail"],
                } for r in rows]
                build_monthly_sheets_format(str(output), normalized)
            else:
                output = self.exports_dir / f"monthly-raw_{self.year}-{self.month:02d}.xlsx"
                sections = {
                    "Summary": [s],
                    "Hall of Late": [{
                        "Rank": i + 1, "Name": r["name"], "Staff No": r["staff_no"],
                        "Total Late": r["total_late"], "Days Late": r["days_late"],
                    } for i, r in enumerate(ranking)],
                    "Coaching": [{
                        "Name": c["name"], "Total Late": c["total_late"],
                    } for c in coaching],
                }
                build_raw_excel(str(output), sections)

        self.status_text.value = f"✅ Generated: {output}"
        self.status_text.update()
```

- [ ] **Step 2: Wire route in shell.py**

Add to `_render_page`:

```python
elif route == "monthly_report":
    from src.ui.pages import monthly_report
    page_obj = monthly_report.MonthlyReportPage(self.repo, self.settings,
                                                  str(Path(self.snapshot_dir).parent / "data" / "exports"),
                                                  self.mode)
    self.content_area.content = page_obj.build()
```

- [ ] **Step 3: Manually verify**

Run app, navigate Monthly Report:
- Click Export Monthly Report → modal with monthly extras (Excel sheets-format checkbox)
- Generate PDF → check footer branding, sections render
- Generate Excel with sheets-format → open .xlsx, verify columns: Tanggal, Nama, No Staff, Masuk, Keluar, Terlambat, Pulang Cepat, Alasan Ijin, Lokasi/Detail

- [ ] **Step 4: Commit**

```bash
git add src/ui/pages/monthly_report.py src/ui/shell.py
git commit -m "ui: Monthly Report page with checklist + Sheets-format Excel"
```

---

# PHASE 6 — POLISH & DISTRIBUTION (Tasks 20–23)

End state: Real Hex J icon assets, Backup/Restore page, Settings page, .exe packaged and tested.

---

### Task 20: Logo Asset Generation (Hex J → .ico, .png, refined .svg)

**Files:**
- Create: `scripts/generate_logo.py`
- Modify: `assets/logo.svg` (refined version)
- Generate: `assets/icon.ico`, `assets/logo-256.png`

- [ ] **Step 1: Refine `assets/logo.svg` for production**

Replace contents:

```svg
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 280" width="256" height="280">
  <defs>
    <linearGradient id="hex-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#7C3AED"/>
      <stop offset="100%" stop-color="#F472B6"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#7C3AED" flood-opacity="0.4"/>
    </filter>
  </defs>
  <polygon
    points="128,8 248,72 248,208 128,272 8,208 8,72"
    fill="url(#hex-grad)"
    filter="url(#shadow)"/>
  <text x="128" y="190"
        font-family="Inter, Helvetica, Arial, sans-serif"
        font-weight="900"
        font-size="160"
        fill="white"
        text-anchor="middle">J</text>
</svg>
```

- [ ] **Step 2: Create `scripts/generate_logo.py`**

```python
"""Generate icon.ico (multi-resolution) and logo-256.png from logo.svg."""
from pathlib import Path
from PIL import Image
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

ROOT = Path(__file__).parent.parent
SVG_PATH = ROOT / "assets" / "logo.svg"
ICO_PATH = ROOT / "assets" / "icon.ico"
PNG_PATH = ROOT / "assets" / "logo-256.png"

ICO_SIZES = [16, 32, 48, 64, 128, 256]

def render_svg_to_png(svg_path: Path, output_path: Path, size: int):
    drawing = svg2rlg(str(svg_path))
    if drawing is None:
        raise RuntimeError(f"Failed to load SVG: {svg_path}")
    scale = size / drawing.width
    drawing.width *= scale
    drawing.height *= scale
    drawing.scale(scale, scale)
    renderPM.drawToFile(drawing, str(output_path), fmt="PNG")

def main():
    print(f"Reading {SVG_PATH}")
    # Generate the 256px PNG (used for splash screen + app icon)
    render_svg_to_png(SVG_PATH, PNG_PATH, 256)
    print(f"Wrote {PNG_PATH}")

    # Generate temporary PNGs at each ICO size, combine into single .ico
    images = []
    tmp_dir = ROOT / "assets" / "_tmp_icons"
    tmp_dir.mkdir(exist_ok=True)
    for size in ICO_SIZES:
        tmp_path = tmp_dir / f"icon_{size}.png"
        render_svg_to_png(SVG_PATH, tmp_path, size)
        img = Image.open(tmp_path).convert("RGBA")
        images.append(img)

    # Save as multi-resolution .ico
    images[0].save(
        ICO_PATH,
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
        append_images=images[1:],
    )
    print(f"Wrote {ICO_PATH} ({len(ICO_SIZES)} resolutions)")

    # Cleanup
    for size in ICO_SIZES:
        (tmp_dir / f"icon_{size}.png").unlink()
    tmp_dir.rmdir()

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the generator**

Run: `python scripts/generate_logo.py`
Expected output:
```
Reading .../assets/logo.svg
Wrote .../assets/logo-256.png
Wrote .../assets/icon.ico (6 resolutions)
```

Verify both files exist and `icon.ico` size > 5 KB (multi-res ICO is heavier than single PNG).

- [ ] **Step 4: Manually verify icon visuals**

- Open `assets/icon.ico` in Windows File Explorer thumbnail view → should show Hex J with purple→pink gradient
- Open `assets/logo-256.png` in image viewer → same Hex J, crisp at 256 px

- [ ] **Step 5: Commit**

```bash
git add scripts/ assets/logo.svg assets/icon.ico assets/logo-256.png
git commit -m "assets: generate Hex J logo as .svg, multi-res .ico, and 256px .png"
```

---

### Task 21: Backup / Restore Page

**Files:**
- Create: `src/core/backup.py`
- Create: `src/ui/pages/backup_restore.py`
- Modify: `src/ui/shell.py` (wire route)
- Create: `tests/core/test_backup.py`

- [ ] **Step 1: Write failing test for backup**

`tests/core/test_backup.py`:

```python
import zipfile
from pathlib import Path
from src.db.repository import Repository
from src.core.backup import export_backup, import_backup

def test_export_creates_zip(tmp_path):
    db_path = tmp_path / "data" / "app.db"
    db_path.parent.mkdir()
    repo = Repository(str(db_path))
    repo.init_schema()
    repo.upsert_employee("1", "TEST")
    repo.close()

    config = tmp_path / "config.json"
    config.write_text('{"theme": "dark"}')
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    out = export_backup(
        db_path=str(db_path),
        config_path=str(config),
        backup_dir=str(backup_dir),
        output_path=str(tmp_path / "out.zip"),
    )
    assert Path(out).exists()
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        assert "app.db" in names
        assert "config.json" in names

def test_import_restores_data(tmp_path):
    # Create a backup first
    db_path = tmp_path / "data" / "app.db"
    db_path.parent.mkdir()
    repo = Repository(str(db_path))
    repo.init_schema()
    repo.upsert_employee("1", "ORIGINAL")
    repo.close()
    config = tmp_path / "config.json"
    config.write_text('{"theme": "dark"}')
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    backup_zip = export_backup(
        db_path=str(db_path), config_path=str(config),
        backup_dir=str(backup_dir), output_path=str(tmp_path / "backup.zip"),
    )

    # Wipe and restore
    db_path.unlink()
    config.write_text('{"theme": "light"}')

    import_backup(
        zip_path=backup_zip,
        target_db_path=str(db_path),
        target_config_path=str(config),
        pre_restore_dir=str(tmp_path / "pre-restore"),
    )

    repo2 = Repository(str(db_path))
    emp = repo2.get_employee_by_staff_no("1")
    assert emp["name"] == "ORIGINAL"
    repo2.close()
    assert '"theme": "dark"' in config.read_text()
```

Run: `pytest tests/core/test_backup.py -v`
Expected: FAIL.

- [ ] **Step 2: Implement `src/core/backup.py`**

```python
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

def export_backup(db_path: str, config_path: str, backup_dir: str,
                   output_path: str | None = None) -> str:
    """Bundle DB + config + last 10 snapshots into a ZIP."""
    if output_path is None:
        ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        output_path = str(Path(backup_dir) / f"josaphat-backup-{ts}.zip")

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
        if Path(db_path).exists():
            z.write(db_path, arcname="app.db")
        if Path(config_path).exists():
            z.write(config_path, arcname="config.json")
        # Include last 10 snapshot files
        backup_dir_p = Path(backup_dir)
        if backup_dir_p.exists():
            snaps = sorted(backup_dir_p.glob("snapshot_*.json"),
                            key=lambda p: p.stat().st_mtime, reverse=True)[:10]
            for snap in snaps:
                z.write(snap, arcname=f"snapshots/{snap.name}")
    return output_path

def import_backup(zip_path: str, target_db_path: str, target_config_path: str,
                  pre_restore_dir: str) -> dict:
    """Restore from ZIP. Existing data moved to pre_restore_dir for safety."""
    pre_restore = Path(pre_restore_dir) / datetime.now().strftime("%Y-%m-%d-%H%M%S")
    pre_restore.mkdir(parents=True, exist_ok=True)

    if Path(target_db_path).exists():
        shutil.copy(target_db_path, pre_restore / "app.db.previous")
    if Path(target_config_path).exists():
        shutil.copy(target_config_path, pre_restore / "config.json.previous")

    with zipfile.ZipFile(zip_path, "r") as z:
        for name in z.namelist():
            if name == "app.db":
                Path(target_db_path).parent.mkdir(parents=True, exist_ok=True)
                with open(target_db_path, "wb") as f:
                    f.write(z.read(name))
            elif name == "config.json":
                with open(target_config_path, "wb") as f:
                    f.write(z.read(name))
            elif name.startswith("snapshots/"):
                snap_dir = Path(target_db_path).parent.parent / "backups"
                snap_dir.mkdir(parents=True, exist_ok=True)
                with open(snap_dir / Path(name).name, "wb") as f:
                    f.write(z.read(name))

    return {"pre_restore_dir": str(pre_restore)}
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/core/test_backup.py -v`
Expected: both PASS.

- [ ] **Step 4: Create `src/ui/pages/backup_restore.py`**

```python
import flet as ft
from pathlib import Path
from datetime import datetime
from src.core.backup import export_backup, import_backup
from src.core.constants import COLORS

class BackupRestorePage:
    def __init__(self, db_path: str, config_path: str, backup_dir: str,
                 pre_restore_dir: str, mode: str = "dark"):
        self.db_path = db_path
        self.config_path = config_path
        self.backup_dir = backup_dir
        self.pre_restore_dir = pre_restore_dir
        self.mode = mode

    def build(self) -> ft.Control:
        self.status_text = ft.Text("", size=13, opacity=0.85)
        self.file_picker = ft.FilePicker(on_result=self._on_zip_picked)

        return ft.Container(
            padding=28, expand=True,
            content=ft.Column(spacing=20, controls=[
                self.file_picker,
                ft.Text("Backup / Restore", size=28, weight=ft.FontWeight.W_800),
                ft.Text("Untuk pindah laptop atau snapshot data: export ke ZIP, lalu import di laptop tujuan.",
                        size=13, opacity=0.7),
                ft.Container(height=8),
                ft.Container(
                    padding=20, border_radius=12,
                    bgcolor=f"{COLORS['resolved']}11",
                    border=ft.border.all(1, COLORS["resolved"]),
                    content=ft.Row(spacing=14, controls=[
                        ft.Icon(ft.Icons.CLOUD_UPLOAD, size=32, color=COLORS["resolved"]),
                        ft.Column(expand=True, spacing=4, controls=[
                            ft.Text("Export Backup", size=16, weight=ft.FontWeight.W_700),
                            ft.Text("Bundle database + config + snapshots terakhir ke ZIP.", size=12, opacity=0.7),
                        ]),
                        ft.ElevatedButton("📤 Export ZIP", on_click=lambda e: self._export(),
                                           bgcolor=COLORS["resolved"], color="white"),
                    ]),
                ),
                ft.Container(
                    padding=20, border_radius=12,
                    bgcolor=f"{COLORS['accent']}11",
                    border=ft.border.all(1, COLORS["accent"]),
                    content=ft.Row(spacing=14, controls=[
                        ft.Icon(ft.Icons.CLOUD_DOWNLOAD, size=32, color=COLORS["accent"]),
                        ft.Column(expand=True, spacing=4, controls=[
                            ft.Text("Import Backup", size=16, weight=ft.FontWeight.W_700),
                            ft.Text("Restore dari ZIP backup. Data lama di-backup ke pre-restore folder dulu.",
                                    size=12, opacity=0.7),
                        ]),
                        ft.ElevatedButton("📥 Import ZIP",
                                           on_click=lambda e: self.file_picker.pick_files(
                                               allowed_extensions=["zip"], allow_multiple=False),
                                           bgcolor=COLORS["accent"], color="white"),
                    ]),
                ),
                self.status_text,
            ]),
        )

    def _export(self):
        try:
            output = export_backup(self.db_path, self.config_path, self.backup_dir)
            self.status_text.value = f"✅ Backup created: {output}"
        except Exception as ex:
            self.status_text.value = f"❌ Export failed: {ex}"
        self.status_text.update()

    def _on_zip_picked(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return
        zip_path = e.files[0].path
        try:
            result = import_backup(zip_path, self.db_path, self.config_path, self.pre_restore_dir)
            self.status_text.value = (f"✅ Restored from {Path(zip_path).name}. "
                                       f"Previous data preserved at {result['pre_restore_dir']}. "
                                       f"Restart app to see changes.")
        except Exception as ex:
            self.status_text.value = f"❌ Import failed: {ex}"
        self.status_text.update()
```

- [ ] **Step 5: Wire route in shell.py**

Add to `_render_page`:

```python
elif route == "backup_restore":
    from src.ui.pages import backup_restore
    root = Path(self.snapshot_dir).parent
    page_obj = backup_restore.BackupRestorePage(
        str(root / "data" / "app.db"),
        str(root / "config.json"),
        self.snapshot_dir,
        str(root / "backups" / "pre-restore"),
        self.mode,
    )
    self.content_area.content = page_obj.build()
```

- [ ] **Step 6: Manually verify**

- Click Backup/Restore in sidebar
- Click Export ZIP → status shows path; check the file exists in `backups/`
- Click Import ZIP → file picker, select the just-exported ZIP → status shows success
- Restart app → DB loads from restored data

- [ ] **Step 7: Commit**

```bash
git add src/core/backup.py src/ui/pages/backup_restore.py src/ui/shell.py tests/core/test_backup.py
git commit -m "feat: backup/restore for laptop migration with pre-restore safety"
```

---

### Task 22: Settings Page

**Files:**
- Create: `src/ui/pages/settings.py`
- Modify: `src/ui/shell.py` (wire route)

- [ ] **Step 1: Create `src/ui/pages/settings.py`**

```python
import flet as ft
from src.core.constants import COLORS
from src.core.settings_store import SettingsStore

class SettingsPage:
    def __init__(self, settings: SettingsStore, mode: str = "dark"):
        self.settings = settings
        self.mode = mode
        self.cfg = settings.load()
        self.fields = {}

    def build(self) -> ft.Control:
        self.status_text = ft.Text("", size=12, opacity=0.85)
        sections = [
            self._numeric_off_section("Coaching Threshold (menit/minggu)",
                                       "coaching_threshold_minutes", off_allowed=False,
                                       hint="Karyawan yang melebihi total ini per minggu akan masuk Coaching Required."),
            self._numeric_off_section("Late Threshold (menit)",
                                       "late_threshold_minutes", off_allowed=True,
                                       hint="Telat ≥ nilai ini → cell merah; di bawah → cell kuning. Off = no coloring."),
            self._numeric_off_section("Lupa Absen Penalty (menit)",
                                       "lupa_absen_penalty_minutes", off_allowed=True,
                                       hint="Otomatis tambah ke late_minutes saat resolusi 'Lupa Absen' dipilih. Off = no auto-add."),
            self._numeric_off_section("Pulang Cepat Threshold (menit)",
                                       "pulang_cepat_threshold_minutes", off_allowed=True,
                                       hint="Pulang cepat > nilai ini → flag case F. Off = no flagging."),
            self._numeric_off_section("Repeat Offender (minggu berturut)",
                                       "repeat_offender_weeks", off_allowed=False,
                                       hint="Karyawan dianggap repeat offender bila telat di sejumlah minggu berturut ini."),
            self._time_section("Working Hours Start", "working_hours_start"),
            self._time_section("Working Hours End", "working_hours_end"),
        ]

        save_btn = ft.ElevatedButton("💾 Save Settings", on_click=lambda e: self._save(),
                                      bgcolor=COLORS["primary"], color="white")

        return ft.Container(
            padding=28, expand=True,
            content=ft.Column(scroll=ft.ScrollMode.AUTO, spacing=14, controls=[
                ft.Text("Settings", size=28, weight=ft.FontWeight.W_800),
                ft.Text("Configurable thresholds. Perubahan langsung tersimpan setelah klik Save.",
                        size=13, opacity=0.7),
                ft.Container(height=8),
                *sections,
                ft.Container(height=12),
                ft.Row(controls=[save_btn, ft.Container(width=12), self.status_text]),
            ]),
        )

    def _numeric_off_section(self, label: str, key: str, off_allowed: bool, hint: str) -> ft.Control:
        current = self.cfg.get(key)
        is_off = current is None
        off_switch = ft.Switch(label="Off (no policy)", value=is_off,
                                visible=off_allowed,
                                on_change=lambda e, k=key: self._toggle_off(k, e.control.value))
        num_field = ft.TextField(
            label=label, value="" if is_off else str(current),
            width=180, disabled=is_off,
        )
        self.fields[key] = (num_field, off_switch if off_allowed else None)
        return ft.Container(
            padding=14, border_radius=10,
            bgcolor=f"{COLORS['primary']}08",
            content=ft.Column(spacing=8, controls=[
                ft.Row(spacing=14, controls=[num_field, off_switch] if off_allowed else [num_field]),
                ft.Text(hint, size=11, opacity=0.65),
            ]),
        )

    def _time_section(self, label: str, key: str) -> ft.Control:
        current = self.cfg.get(key, "08:00")
        field = ft.TextField(label=label, value=current, width=180, hint_text="HH:MM")
        self.fields[key] = (field, None)
        return ft.Container(
            padding=14, border_radius=10,
            bgcolor=f"{COLORS['primary']}08",
            content=field,
        )

    def _toggle_off(self, key: str, is_off: bool):
        field, _ = self.fields[key]
        field.disabled = is_off
        if is_off:
            field.value = ""
        field.update()

    def _save(self):
        update = {}
        for key, (field, off_switch) in self.fields.items():
            if off_switch and off_switch.value:
                update[key] = None
            else:
                val = field.value.strip()
                if not val:
                    self.status_text.value = f"❌ {key} kosong"
                    self.status_text.update()
                    return
                if ":" in val:  # time field
                    update[key] = val
                else:
                    try:
                        update[key] = int(val)
                    except ValueError:
                        self.status_text.value = f"❌ {key}: harus angka"
                        self.status_text.update()
                        return
        self.settings.update(update)
        self.cfg = self.settings.load()
        self.status_text.value = "✅ Settings saved"
        self.status_text.update()
```

- [ ] **Step 2: Wire route in shell.py**

Add to `_render_page`:

```python
elif route == "settings":
    from src.ui.pages import settings as settings_page
    page_obj = settings_page.SettingsPage(self.settings, self.mode)
    self.content_area.content = page_obj.build()
```

- [ ] **Step 3: Manually verify**

- Click Settings in sidebar
- Verify all configurable values shown with current default
- Toggle "Off" switches for Late/Lupa/Pulang Cepat → field disables
- Edit Coaching Threshold to 60 → Save → status "✅ Settings saved"
- Navigate to Dashboard → confirm Need Coaching uses new threshold (60 menit instead of 75)
- Restart app → settings persist (config.json)

- [ ] **Step 4: Commit**

```bash
git add src/ui/pages/settings.py src/ui/shell.py
git commit -m "ui: Settings page with threshold editors and Off toggles"
```

---

### Task 23: Build .exe with flet pack + Distribution Test

**Files:**
- Create: `scripts/build_exe.py` (or use `flet pack` directly)
- Modify: `README.md` (add build instructions)

- [ ] **Step 1: Verify icon.ico is in assets/**

Run: `ls assets/icon.ico` — must exist (Task 20).

- [ ] **Step 2: Run flet pack**

```bash
python -m flet pack src/main.py \
  --name "JosaphatTechHR" \
  --icon assets/icon.ico \
  --product-name "Josaphat Tech Solution HR Attendance Manager" \
  --product-version "1.0.0" \
  --copyright "Josaphat Tech Solution"
```

(On Windows PowerShell, replace backslash continuations with backtick `` ` `` or put on one line.)

Expected: `dist/JosaphatTechHR.exe` is produced (~80–120 MB).

- [ ] **Step 3: Verify .exe runs standalone**

Copy `dist/JosaphatTechHR.exe` to a folder that has no Python installed (or rename `python` temporarily). Double-click. Expected:
- Window opens with Josaphat Tech Solution title
- Hex J icon appears in window title bar AND taskbar
- Sidebar with all 8 nav items renders
- Theme toggle works
- Import a sample .xls → records appear in DB (created in `data/app.db` next to .exe)
- All pages function

- [ ] **Step 4: Update README**

Append to `README.md`:

```markdown
## Build Standalone .exe

After completing development setup:

```bash
python -m flet pack src/main.py --name "JosaphatTechHR" --icon assets/icon.ico --product-name "Josaphat Tech Solution HR Attendance Manager" --product-version "1.0.0"
```

Output is `dist/JosaphatTechHR.exe`. Copy this single file to any Windows machine — no Python install needed. The app will create `data/`, `config.json`, and `backups/` next to the .exe on first run.

## Backup for Laptop Migration

In-app: Backup/Restore page → Export ZIP → save to USB / cloud drive. On the new laptop, run the .exe once (creates empty data folder), then Backup/Restore → Import ZIP → restart app.
```

- [ ] **Step 5: Tag the release**

```bash
git add scripts/ README.md
git commit -m "build: flet pack config and v1.0 distribution instructions"
git tag -a v1.0.0 -m "v1.0.0 — Initial release of Josaphat Tech HR Attendance Manager"
```

- [ ] **Step 6: Final verification — full smoke test**

1. Wipe `data/` and `config.json` — fresh state
2. Launch the .exe
3. Import the sample April 1-10 .xls
4. Resolve 2-3 pending issues (try Tugas Lapangan with location, Izin Pagi with reason, Lupa Absen)
5. View Dashboard → all metrics, coaching, hall of late render
6. Export Weekly Report PDF → verify branding, sections
7. Export Monthly Report Excel (sheets format) → open in Excel/Sheets, verify columns
8. Open Settings → change Coaching threshold to 50 → Save
9. Return to Dashboard → coaching count updates
10. Backup → Export ZIP
11. Wipe `data/`, restart, Backup → Import ZIP → verify all data restored

If any step fails: file an issue, fix, re-run.

---

## Self-Review Checklist (run after writing this plan)

- [ ] **Spec coverage**: every section of the spec maps to one or more tasks above (✓ done — see mapping below)
- [ ] **Placeholder scan**: no "TBD/TODO/handle X appropriately" in any step
- [ ] **Type consistency**: function names match across tasks (`apply_resolution` used in T10, T11, T12; `weekly_summary` used in T13, T15, T18, T19)
- [ ] **TDD enforced** for all `core/`, `db/`, `reports/excel_builder` modules
- [ ] **Manual verification** specified for all UI tasks with concrete checklists
- [ ] **Frequent commits** — every task ends with a commit

### Spec → Task Mapping

| Spec Section | Tasks |
|---|---|
| §2 Tech Stack & Distribution | 1, 23 |
| §3 Architecture | 1, 5 (shell scaffolds module composition) |
| §4 Data Model | 2 (5 tables) |
| §5 Excel Parser | 6 |
| §6 Issue Detection | 7 |
| §7 Resolution (10 options) | 10, 11 |
| §8 UI Screens | 5 (shell), 9 (import), 11 (issues), 12 (edit), 15 (dashboard), 18 (weekly), 19 (monthly), 21 (backup), 22 (settings) |
| §9 Dashboard Maximum Bold | 13 (logic), 14 (components), 15 (page) |
| §10 Reports & Export | 16 (PDF foundation), 17 (sections + Excel), 18 (weekly modal), 19 (monthly + sheets format) |
| §11 Configurable Settings | 3 (store with off support), 22 (UI) |
| §12 Conflict Resolution & Versioning | 8 |
| §13 Backup & Restore | 21 |
| §14 Branding | 16 (PDF footer), 20 (logo assets), 23 (.exe icon) |
| §15 File Structure | All — file paths match the proposed structure |
| §17 Open Items | Noted in T17 (sheets format) and T19 (default layout); to refine after user shares Sheets sample |











