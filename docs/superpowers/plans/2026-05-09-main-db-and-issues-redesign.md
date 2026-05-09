# Main DB + Dashboard Default + Issues Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Main Database page (17-col monthly recap matching the user's Google Sheets), default Dashboard to last week with imported data, and redesign Issues page (bug fixes + compact UI + AI recommendation + 11th resolution code).

**Architecture:** No DB schema changes. Reuses existing `attendance_records` + `resolutions`. New module `core/alasan_format.py` for free-form text rendering, new repo method `list_monthly_grid` returning skeleton-row-aware view, new UI page `ui/pages/main_database.py`. Issues page rewritten with compact card layout, debounced period nav, and live-preview resolve panel. `conflict.py` enhanced to never overwrite resolved records.

**Tech Stack:** Python 3.13 + Flet 0.25.2 + openpyxl + reportlab + pytest. No new dependencies.

**Spec:** [docs/superpowers/specs/2026-05-09-main-db-and-issues-redesign.md](../specs/2026-05-09-main-db-and-issues-redesign.md)

**Builds on:** v1.0 codebase (commit `26a3a37`, tag `v1.0.2`). Currently 58 tests passing.

---

## Phase Overview

| Phase | Tasks | Output |
|---|---|---|
| 1. Quick wins | 1–3 | `tidak_hadir` code, Issues navbar bug fix, Dashboard default-to-last-imported-week |
| 2. Backend | 4–6 | `alasan_format` module, `list_monthly_grid` query, `preserved_resolved` conflict rule |
| 3. Issues redesign | 7–8 | Recommendation engine + compact UI rewrite |
| 4. Main DB UI | 9–11 | Excel format upgrade + Main Database page + sidebar nav wiring |
| 5. Polish | 12 | Import Data status text breakdown + final smoke test |

---

## File Structure (locked at planning time)

```
src/
  core/
    alasan_format.py          ← NEW (Task 4)
    constants.py              ← MODIFY: add tidak_hadir (Task 1)
    issue_detector.py         ← MODIFY: add recommend() (Task 7)
    conflict.py               ← MODIFY: preserved_resolved (Task 6)
  db/
    repository.py             ← MODIFY: list_monthly_grid (Task 5)
  reports/
    excel_builder.py          ← MODIFY: 17-col build_monthly_sheets_format (Task 9)
  ui/
    shell.py                  ← MODIFY: add main_database route (Task 11)
    pages/
      issues.py               ← REWRITE (Tasks 2 + 8)
      dashboard.py            ← MODIFY: default + range toggle (Task 3)
      import_data.py          ← MODIFY: status text breakdown (Task 12)
      main_database.py        ← NEW (Tasks 10–11)
tests/
  core/
    test_alasan_format.py     ← NEW (Task 4)
    test_issue_detector.py    ← MODIFY: add recommend tests (Task 7)
    test_conflict.py          ← MODIFY: add preserved_resolved test (Task 6)
  db/
    test_repository.py        ← MODIFY: add list_monthly_grid tests (Task 5)
  reports/
    test_excel_builder.py     ← MODIFY: update 17-col test (Task 9)
```

---

# PHASE 1 — QUICK WINS (Tasks 1–3)

End state: 11 reason codes including `tidak_hadir`, Issues navbar shows correct period text after click, Dashboard opens on the last imported week.

---

### Task 1: Add `tidak_hadir` resolution code

**Files:**
- Modify: `src/core/constants.py`
- Test: existing tests cover this implicitly via `REASON_CODES` length

- [ ] **Step 1: Add the new code**

Edit `src/core/constants.py`. Append to `REASON_CODES` dict (after `belum_kabar`):

```python
REASON_CODES = {
    # ... existing 10 entries ...
    "belum_kabar": {"label": "Belum Ada Kabar", "extra": None},
    "tidak_hadir": {"label": "Tidak Hadir", "extra": None},
}
```

- [ ] **Step 2: Verify count**

Run: `python -c "from src.core.constants import REASON_CODES; print(len(REASON_CODES))"`
Expected: `11`

- [ ] **Step 3: Verify all tests still pass**

Run: `pytest -q`
Expected: `58 passed`

- [ ] **Step 4: Commit**

```bash
git add src/core/constants.py
git commit -m "feat(reasons): add 'tidak_hadir' as 11th resolution code"
```

---

### Task 2: Fix Issues page navbar stale text + add debounce

**Files:**
- Modify: `src/ui/pages/issues.py`

- [ ] **Step 1: Read current `issues.py` to know what's there**

Run: `cat src/ui/pages/issues.py | head -80`

Expected: see `_build_period_selector`, `_shift_week`, `_refresh_list` methods. Confirm `_shift_week` only calls `self.list_view.update()` (the bug — it doesn't update the period label).

- [ ] **Step 2: Replace `_build_period_selector` and `_shift_week` to fix the bug**

Open `src/ui/pages/issues.py` and replace the existing `_build_period_selector` and `_shift_week` methods with:

```python
def _period_label(self) -> str:
    return f"{self.start.strftime('%d %b')} – {self.end.strftime('%d %b %Y')}"

def _build_period_selector(self) -> ft.Control:
    self.period_text = ft.Text(self._period_label(), size=13, weight=ft.FontWeight.W_600)
    return ft.Row(spacing=8, controls=[
        ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda e: self._shift_week(-1)),
        self.period_text,
        ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda e: self._shift_week(1)),
    ])

def _shift_week(self, weeks: int):
    self.start += timedelta(weeks=weeks)
    self.end += timedelta(weeks=weeks)
    self.period_text.value = self._period_label()
    self.period_text.update()
    self._schedule_refresh()
```

- [ ] **Step 3: Add `_schedule_refresh` method with debounce**

In the same class, add (place after `_shift_week`):

```python
def _schedule_refresh(self, delay_ms: int = 200):
    """Coalesce rapid ◀▶ clicks into a single DB query after delay."""
    import threading
    if hasattr(self, "_refresh_timer") and self._refresh_timer is not None:
        self._refresh_timer.cancel()
    def _do():
        self._refresh_list()
        try:
            self.list_view.update()
        except Exception:
            pass  # may be unmounted by now — safe to ignore
    self._refresh_timer = threading.Timer(delay_ms / 1000.0, _do)
    self._refresh_timer.start()
```

- [ ] **Step 4: Initialize `_refresh_timer = None` in `__init__`**

Locate the `__init__` method and add at the end:

```python
self._refresh_timer = None
```

- [ ] **Step 5: Manual verify**

Run: `python main.py` (or via .exe rebuild later). Navigate to Issues page. Click ◀ several times rapidly. Expected:
- Period label updates immediately (e.g. "27 Apr – 03 May 2026")
- List refreshes ~200ms after the last click (no UI freeze on repeated clicks)
- 58 existing tests still pass: `pytest -q`

- [ ] **Step 6: Commit**

```bash
git add src/ui/pages/issues.py
git commit -m "fix(issues): period text now syncs with active filter; debounce nav clicks"
```

---

### Task 3: Dashboard default to last imported week + Weekly/Monthly toggle

**Files:**
- Modify: `src/ui/pages/dashboard.py`

- [ ] **Step 1: Add `_resolve_default_period` method**

Open `src/ui/pages/dashboard.py`. Add this method to the `DashboardPage` class (place after `__init__`):

```python
def _resolve_default_period(self) -> tuple[date, date]:
    """Find the latest week with any 'Hari Kerja' data.
    Falls back to current calendar week if DB is empty."""
    cursor = self.repo.conn.execute(
        "SELECT MAX(date) FROM attendance_records WHERE day_type='Hari Kerja'"
    )
    row = cursor.fetchone()
    latest_date_str = row[0] if row else None
    if latest_date_str:
        from datetime import datetime as _dt
        latest = _dt.fromisoformat(latest_date_str).date()
        start = latest - timedelta(days=latest.weekday())
    else:
        today = date.today()
        start = today - timedelta(days=today.weekday())
    return (start, start + timedelta(days=6))
```

- [ ] **Step 2: Use it in `__init__`**

Find the existing `__init__` lines that compute `self.start` and `self.end` from `today`:

```python
today = date.today()
self.start = today - timedelta(days=today.weekday())
self.end = self.start + timedelta(days=6)
```

Replace with:

```python
self.range_mode = "weekly"
self.start, self.end = self._resolve_default_period()
```

- [ ] **Step 3: Add `_switch_range_mode` and `_period_step` methods**

Add to the class:

```python
def _switch_range_mode(self, mode: str):
    """Toggle between 'weekly' (7 days) and 'monthly' (full month containing self.start)."""
    if mode == self.range_mode:
        return
    self.range_mode = mode
    if mode == "monthly":
        from calendar import monthrange
        anchor = self.start
        self.start = anchor.replace(day=1)
        last_day = monthrange(anchor.year, anchor.month)[1]
        self.end = anchor.replace(day=last_day)
    else:
        # snap back to ISO week containing current self.start
        self.start = self.start - timedelta(days=self.start.weekday())
        self.end = self.start + timedelta(days=6)
    self._rebuild()

def _period_step(self, direction: int):
    """Step ±1 unit (week or month) based on current range_mode."""
    if self.range_mode == "monthly":
        from calendar import monthrange
        if direction > 0:
            anchor = self.end + timedelta(days=1)
        else:
            anchor = self.start - timedelta(days=1)
        self.start = anchor.replace(day=1)
        last_day = monthrange(anchor.year, anchor.month)[1]
        self.end = anchor.replace(day=last_day)
    else:
        self.start += timedelta(weeks=direction)
        self.end += timedelta(weeks=direction)
    self._rebuild()

def _rebuild(self):
    """Re-render the dashboard content area."""
    self.page.controls.clear()
    self.page.add(self._shell.build())
    self.page.update()
```

NOTE: `self.page` and `self._shell` aren't currently passed to DashboardPage. The simplest workaround is to NOT add `_rebuild` to DashboardPage — instead use the Shell's existing `_navigate` mechanism. Replace the `_rebuild()` calls above with:

```python
def _rebuild(self):
    """Re-trigger dashboard rebuild via the Shell's nav callback."""
    if hasattr(self, "nav_callback") and self.nav_callback is not None:
        self.nav_callback("dashboard")
```

This relies on `nav_callback` already being passed to DashboardPage (added during Task 5 polish in v1.0). Verify: `grep -n "nav_callback" src/ui/pages/dashboard.py`. If not present, add `nav_callback=None` to `__init__` and store as `self.nav_callback = nav_callback`. (Already done in v1.0; this is a sanity check.)

- [ ] **Step 4: Add Weekly/Monthly segmented button to `_page_header`**

Find the `_page_header` method. Locate the existing `ft.Row(controls=[...])` content. Add the segmented button between the title `Column` and the `Container(expand=True)` spacer:

```python
ft.SegmentedButton(
    selected={self.range_mode},
    segments=[
        ft.Segment(value="weekly", label=ft.Text("Weekly")),
        ft.Segment(value="monthly", label=ft.Text("Monthly")),
    ],
    on_change=lambda e: self._switch_range_mode(next(iter(e.control.selected))),
),
```

Also wire the existing `◀ ▶` IconButtons (if they exist in the page header — currently they don't; the dashboard uses fixed period). Add a period selector row similar to Issues page:

```python
ft.Row(spacing=8, controls=[
    ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda e: self._period_step(-1)),
    ft.Text(f"{self.start} → {self.end}", size=12, opacity=0.8),
    ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda e: self._period_step(1)),
]),
```

- [ ] **Step 5: Update period subtitle in page header**

The existing line:

```python
ft.Text(f"Periode: {self.start} → {self.end} · {summary['total_records']} records", ...)
```

Add range_mode prefix:

```python
ft.Text(f"{self.range_mode.title()} · {self.start} → {self.end} · {summary['total_records']} records", ...)
```

- [ ] **Step 6: Manual verify**

Run: `python main.py`. Click Dashboard. Expected:
- If DB has data from April: opens on the last week of April that has data (not current week)
- Toggle Weekly/Monthly: period jumps to month containing current week, and back
- Click ◀ ▶: steps by week or month accordingly
- Metrics update accordingly

- [ ] **Step 7: Verify tests still pass**

Run: `pytest -q`
Expected: `58 passed`

- [ ] **Step 8: Commit**

```bash
git add src/ui/pages/dashboard.py
git commit -m "feat(dashboard): default to last imported week + Weekly/Monthly toggle"
```

---

# PHASE 2 — BACKEND (Tasks 4–6)

End state: `alasan_format.format_alasan()` renders any resolution as Sheets-compatible text, `repo.list_monthly_grid()` returns skeleton-row-aware month view, conflict resolver protects records that have a resolution.

---

### Task 4: `alasan_format` module

**Files:**
- Create: `src/core/alasan_format.py`
- Create: `tests/core/test_alasan_format.py`

- [ ] **Step 1: Write failing tests covering all 13 mapping cases**

Create `tests/core/test_alasan_format.py`:

```python
import pytest
from src.core.alasan_format import format_alasan

@pytest.mark.parametrize("code,location,detail,expected", [
    (None, None, None, ""),
    ("tugas_lapangan", "Klaten", None, "Lapangan ke Klaten"),
    ("tugas_lapangan", None, None, "Lapangan"),
    ("tugas_lapangan", "", None, "Lapangan"),
    ("tugas_paparan", "PT FAFIFU", None, "Tugas Paparan di PT FAFIFU"),
    ("tugas_paparan", None, None, "Tugas Paparan"),
    ("sakit", None, None, "Izin Sakit"),
    ("cuti", None, None, "Cuti"),
    ("cuti", None, "kepentingan keluarga", "Cuti, kepentingan keluarga"),
    ("izin_pagi", None, "urus dokumen", "Izin Pagi - urus dokumen"),
    ("izin_pagi", None, None, "Izin Pagi"),
    ("pulang_awal", None, "anak sakit", "Pulang Lebih Awal - anak sakit"),
    ("pulang_awal", None, None, "Pulang Lebih Awal"),
    ("telat_kerja", None, "meeting client", "Masuk Terlambat - meeting client"),
    ("telat_kerja", None, None, "Masuk Terlambat"),
    ("telat_personal", None, None, "Terlambat"),
    ("lupa_absen", None, None, "Lupa absen"),
    ("belum_kabar", None, None, ""),
    ("belum_kabar", None, "Belum daftar fingerprint", "Belum daftar fingerprint"),
    ("tidak_hadir", None, None, "Tidak Hadir"),
])
def test_format_alasan_cases(code, location, detail, expected):
    assert format_alasan(code, location, detail) == expected
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/core/test_alasan_format.py -v`
Expected: `ModuleNotFoundError: No module named 'src.core.alasan_format'`

- [ ] **Step 3: Implement `src/core/alasan_format.py`**

```python
"""Render a (reason_code, location, reason_detail) tuple as the free-form
'Alasan Ijin' text used in the user's Google Sheets monthly recap.

Examples seen in the user's actual sheet:
    "Lapangan ke Klaten"
    "Cuti, kepentingan keluarga"
    "Belum daftar fingerprint"
    "Lupa absen"
"""

def format_alasan(reason_code: str | None,
                  location: str | None,
                  reason_detail: str | None) -> str:
    if not reason_code:
        return ""

    loc = (location or "").strip()
    det = (reason_detail or "").strip()

    if reason_code == "tugas_lapangan":
        return f"Lapangan ke {loc}" if loc else "Lapangan"
    if reason_code == "tugas_paparan":
        return f"Tugas Paparan di {loc}" if loc else "Tugas Paparan"
    if reason_code == "sakit":
        return "Izin Sakit"
    if reason_code == "cuti":
        return f"Cuti, {det}" if det else "Cuti"
    if reason_code == "izin_pagi":
        return f"Izin Pagi - {det}" if det else "Izin Pagi"
    if reason_code == "pulang_awal":
        return f"Pulang Lebih Awal - {det}" if det else "Pulang Lebih Awal"
    if reason_code == "telat_kerja":
        return f"Masuk Terlambat - {det}" if det else "Masuk Terlambat"
    if reason_code == "telat_personal":
        return "Terlambat"
    if reason_code == "lupa_absen":
        return "Lupa absen"
    if reason_code == "belum_kabar":
        # Special case: when a Main DB cell was edited inline as free-form text,
        # it's stored with code='belum_kabar' and the typed text in detail.
        # Round-trip the text exactly.
        return det
    if reason_code == "tidak_hadir":
        return "Tidak Hadir"

    return reason_code  # unknown code — return verbatim as fallback
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/core/test_alasan_format.py -v`
Expected: 20 passed (one per parametrize case).

- [ ] **Step 5: Verify full suite**

Run: `pytest -q`
Expected: `78 passed` (58 existing + 20 new).

- [ ] **Step 6: Commit**

```bash
git add src/core/alasan_format.py tests/core/test_alasan_format.py
git commit -m "feat(core): alasan_format helper renders resolutions as Sheets text"
```

---

### Task 5: `list_monthly_grid` repository method

**Files:**
- Modify: `src/db/repository.py` (add method to existing Repository class)
- Modify: `tests/db/test_repository.py` (add tests)

- [ ] **Step 1: Write failing tests**

Append to `tests/db/test_repository.py`:

```python
def test_list_monthly_grid_returns_skeleton_for_empty_month(tmp_path):
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    repo.upsert_employee("1002", "ANDIKA", department="ARGA DIRGA")

    rows = repo.list_monthly_grid(2026, 4)
    # April 2026 has 30 days; one employee → 30 rows
    assert len(rows) == 30
    # All rows should be skeleton (no actual_in/out)
    assert all(r["actual_in"] is None for r in rows)
    # day_name and day_type populated for skeleton rows
    assert rows[0]["day_name"] == "Rabu"          # Apr 1, 2026 = Wednesday
    assert rows[0]["day_type"] == "Hari Kerja"
    # Sat/Sun marked as Istirahat
    sat = next(r for r in rows if r["date"] == "2026-04-04")
    assert sat["day_type"] == "Istirahat"

def test_list_monthly_grid_overlays_actual_data(tmp_path):
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    emp_id = repo.upsert_employee("1002", "ANDIKA", department="ARGA DIRGA")
    repo.insert_attendance({
        "employee_id": emp_id, "date": "2026-04-01",
        "day_name": "Rabu", "day_type": "Hari Kerja",
        "schedule_in": "08:00", "schedule_out": "16:00",
        "actual_in": "08:06", "actual_out": "16:41",
        "late_minutes": 6, "early_leave_minutes": 0,
        "work_hours": 7.9, "overtime_hours": 0.0,
        "absent_flag": 0, "forgot_punch_flag": 0,
        "issue_case": None, "import_batch_id": None,
    })

    rows = repo.list_monthly_grid(2026, 4)
    apr_1 = next(r for r in rows if r["date"] == "2026-04-01")
    assert apr_1["actual_in"] == "08:06"
    assert apr_1["late_minutes"] == 6
    apr_2 = next(r for r in rows if r["date"] == "2026-04-02")
    assert apr_2["actual_in"] is None  # still skeleton

def test_list_monthly_grid_includes_resolution(tmp_path):
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    emp_id = repo.upsert_employee("1002", "ANDIKA")
    rec_id = repo.insert_attendance({
        "employee_id": emp_id, "date": "2026-04-02",
        "day_name": "Kamis", "day_type": "Hari Kerja",
        "schedule_in": "08:00", "schedule_out": "16:00",
        "actual_in": None, "actual_out": None,
        "late_minutes": 0, "early_leave_minutes": 0,
        "work_hours": 0.0, "overtime_hours": 0.0,
        "absent_flag": 1, "forgot_punch_flag": 0,
        "issue_case": "A", "import_batch_id": None,
    })
    repo.upsert_resolution(rec_id, reason_code="cuti",
                           reason_detail="kepentingan keluarga")

    rows = repo.list_monthly_grid(2026, 4)
    apr_2 = next(r for r in rows if r["date"] == "2026-04-02")
    assert apr_2["reason_code"] == "cuti"
    assert apr_2["reason_detail"] == "kepentingan keluarga"

def test_list_monthly_grid_filter_by_employee(tmp_path):
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    repo.upsert_employee("1002", "ANDIKA")
    repo.upsert_employee("1004", "ESA")

    all_rows = repo.list_monthly_grid(2026, 4)
    only_esa = repo.list_monthly_grid(2026, 4, staff_no_filter="1004")
    assert len(all_rows) == 60   # 2 employees × 30 days
    assert len(only_esa) == 30
    assert all(r["staff_no"] == "1004" for r in only_esa)
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/db/test_repository.py -v -k monthly_grid`
Expected: 4 tests fail with `AttributeError: 'Repository' object has no attribute 'list_monthly_grid'`

- [ ] **Step 3: Implement `list_monthly_grid` in `Repository` class**

Append to `src/db/repository.py` (inside the `Repository` class, after the existing methods):

```python
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
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/db/test_repository.py -v -k monthly_grid`
Expected: 4 passed.

- [ ] **Step 5: Verify full suite**

Run: `pytest -q`
Expected: `82 passed` (78 + 4).

- [ ] **Step 6: Commit**

```bash
git add src/db/repository.py tests/db/test_repository.py
git commit -m "feat(db): list_monthly_grid query with skeleton-row support"
```

---

### Task 6: Conflict resolver — never overwrite resolved records

**Files:**
- Modify: `src/core/conflict.py`
- Modify: `tests/core/test_conflict.py`

- [ ] **Step 1: Write failing test**

Append to `tests/core/test_conflict.py`:

```python
def test_overwrite_preserves_resolved_records(tmp_path):
    repo = setup_repo(tmp_path)
    snapshot_dir = tmp_path / "backups"

    # First import + resolve
    summary1 = resolve_import(
        repo, [make_record(actual_in="08:00")], "first.xls",
        snapshot_dir=str(snapshot_dir), policy=ConflictPolicy.KEEP_EXISTING,
    )
    emp = repo.get_employee_by_staff_no("1002")
    rec = repo.get_attendance(emp["id"], "2026-04-01")
    repo.upsert_resolution(rec["id"], reason_code="cuti")

    # Re-import with OVERWRITE — should NOT overwrite the resolved record
    summary2 = resolve_import(
        repo, [make_record(actual_in="08:30")], "second.xls",
        snapshot_dir=str(snapshot_dir), policy=ConflictPolicy.OVERWRITE,
    )

    assert summary2["overwritten"] == 0
    assert summary2["preserved_resolved"] == 1
    rec_after = repo.get_attendance(emp["id"], "2026-04-01")
    assert rec_after["actual_in"] == "08:00"  # original preserved
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/core/test_conflict.py::test_overwrite_preserves_resolved_records -v`
Expected: FAIL — `KeyError: 'preserved_resolved'` or assertion failure (overwritten==1 instead of 0).

- [ ] **Step 3: Modify `resolve_import` in `src/core/conflict.py`**

Find the existing OVERWRITE branch:

```python
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
```

Wrap it in a check for existing resolution:

```python
else:  # OVERWRITE policy chosen
    has_resolution = repo.get_resolution(existing["id"]) is not None
    if has_resolution:
        # Never overwrite resolved records, even with OVERWRITE policy.
        # Protects manually-typed Alasan Ijin from re-import clobbering.
        preserved_resolved += 1
    else:
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
```

Also initialize the new counter — find:

```python
inserted = kept = overwritten = 0
```

Change to:

```python
inserted = kept = overwritten = preserved_resolved = 0
```

And in the return dict at the end of `resolve_import`:

```python
return {
    "inserted": inserted, "kept": kept, "overwritten": overwritten,
    "preserved_resolved": preserved_resolved,  # NEW
    "batch_id": batch_id, "snapshot_path": snapshot_path,
}
```

- [ ] **Step 4: Update existing tests that check the summary dict**

The test `test_first_import_inserts_all` and others assert specific keys. They should still pass since `preserved_resolved` is just an additional key, not a change to existing keys. Run all conflict tests to confirm:

Run: `pytest tests/core/test_conflict.py -v`
Expected: all 8 pass (7 existing + 1 new).

- [ ] **Step 5: Verify full suite**

Run: `pytest -q`
Expected: `83 passed` (82 + 1).

- [ ] **Step 6: Commit**

```bash
git add src/core/conflict.py tests/core/test_conflict.py
git commit -m "feat(conflict): never overwrite resolved records, add preserved_resolved counter"
```

---

# PHASE 3 — ISSUES PAGE REDESIGN (Tasks 7–8)

End state: `recommend()` function in issue_detector returns a hint string per case; Issues page uses compact 4-col card grid with AI badge inline + 2-col resolve grid + live preview.

---

### Task 7: `recommend()` function in issue_detector

**Files:**
- Modify: `src/core/issue_detector.py`
- Modify: `tests/core/test_issue_detector.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/core/test_issue_detector.py`:

```python
from src.core.issue_detector import recommend

def test_recommend_for_case_a():
    assert recommend("A") == "Tidak Hadir / Cuti / Izin Sakit?"

def test_recommend_for_case_b():
    assert recommend("B") == "Izin Pagi / Lupa Absen Masuk?"

def test_recommend_for_case_c():
    assert recommend("C") == "Lupa Absen Pulang / Pulang Lebih Awal?"

def test_recommend_for_case_f():
    assert recommend("F") == "Pulang Lebih Awal?"

def test_recommend_for_unknown_returns_none():
    assert recommend("Z") is None
    assert recommend(None) is None
```

- [ ] **Step 2: Run tests — expect ImportError**

Run: `pytest tests/core/test_issue_detector.py -v -k recommend`
Expected: ImportError on `recommend`.

- [ ] **Step 3: Implement `recommend()` in `src/core/issue_detector.py`**

Append to `src/core/issue_detector.py`:

```python
RECOMMENDATIONS = {
    "A": "Tidak Hadir / Cuti / Izin Sakit?",
    "B": "Izin Pagi / Lupa Absen Masuk?",
    "C": "Lupa Absen Pulang / Pulang Lebih Awal?",
    "F": "Pulang Lebih Awal?",
}

def recommend(issue_case: str | None) -> str | None:
    """Suggest plausible resolution categories given an issue_case.
    Used by Issues page UI as an inline hint."""
    if not issue_case:
        return None
    return RECOMMENDATIONS.get(issue_case)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/core/test_issue_detector.py -v -k recommend`
Expected: 5 passed.

- [ ] **Step 5: Verify full suite**

Run: `pytest -q`
Expected: `88 passed` (83 + 5).

- [ ] **Step 6: Commit**

```bash
git add src/core/issue_detector.py tests/core/test_issue_detector.py
git commit -m "feat(detector): recommend() returns AI hint string per issue case"
```

---

### Task 8: Issues page UI rewrite (compact + AI + 2-col grid + live preview)

**Files:**
- Modify: `src/ui/pages/issues.py` (UI rewrite while preserving Task 2's bug fix)

- [ ] **Step 1: Replace `_build_issue_row` to use 4-column grid + detail + AI badge**

Open `src/ui/pages/issues.py`. Find the `_build_issue_row(self, issue: dict)` method. Replace its entire body with:

```python
def _build_issue_row(self, issue: dict) -> ft.Control:
    from src.core.issue_detector import recommend
    case_label, case_color = CASE_LABELS.get(
        issue["issue_case"], (issue["issue_case"], "#999"),
    )
    ai_hint = recommend(issue["issue_case"])

    # Build detail text (Masuk/Keluar values)
    in_val = issue.get("actual_in") or "kosong"
    out_val = issue.get("actual_out") or "kosong"
    in_color = COLORS["resolved"] if issue.get("actual_in") else COLORS["late_severe"]
    out_color = COLORS["resolved"] if issue.get("actual_out") else COLORS["late_severe"]

    return ft.Container(
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        border_radius=6,
        bgcolor=f"{case_color}15",
        border=ft.border.only(left=ft.BorderSide(3, case_color)),
        on_click=lambda e, rid=issue["id"]: self._select_issue(rid, issue),
        ink=True,
        content=ft.Row(spacing=12, controls=[
            # Col 1: Name + date
            ft.Container(width=140, content=ft.Column(spacing=2, controls=[
                ft.Text(issue["employee_name"], weight=ft.FontWeight.W_700, size=13),
                ft.Text(f"{issue['date']} · {issue.get('day_name','')}",
                        size=10, opacity=0.65),
            ])),
            # Col 2: Detail
            ft.Container(expand=True, content=ft.Column(spacing=1, controls=[
                ft.Row(spacing=4, controls=[
                    ft.Text("In:", size=11, opacity=0.7),
                    ft.Text(in_val, size=11, color=in_color,
                            font_family="Courier New", weight=ft.FontWeight.W_600),
                ]),
                ft.Row(spacing=4, controls=[
                    ft.Text("Out:", size=11, opacity=0.7),
                    ft.Text(out_val, size=11, color=out_color,
                            font_family="Courier New", weight=ft.FontWeight.W_600),
                ]),
            ])),
            # Col 3: AI recommendation (if any)
            ft.Container(width=240, content=ft.Row(spacing=6, controls=[
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    border_radius=4, bgcolor="#1E40AF55",
                    content=ft.Text("AI", size=9, weight=ft.FontWeight.W_700,
                                    color="#93C5FD"),
                ) if ai_hint else ft.Container(),
                ft.Text(ai_hint or "", size=10, opacity=0.8, expand=True),
            ])),
            # Col 4: Case badge
            ft.Container(
                width=110,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                border_radius=10, bgcolor=case_color,
                content=ft.Text(case_label, color="white", size=10,
                                weight=ft.FontWeight.W_700,
                                text_align=ft.TextAlign.CENTER),
            ),
        ]),
    )
```

- [ ] **Step 2: Replace `_build_resolve_panel` with redesigned version**

Find the `_build_resolve_panel` method. Replace entirely:

```python
def _build_resolve_panel(self, issue: dict) -> ft.Control:
    from src.core.issue_detector import recommend
    from src.core.alasan_format import format_alasan

    self.extra_input_field = ft.TextField(
        label="Lokasi / Alasan", visible=False,
        on_change=lambda e: self._update_preview(),
    )
    self.preview_text = ft.Text("", size=10, italic=True, opacity=0.65)

    ai_hint = recommend(issue["issue_case"])

    def make_option(code: str, label: str):
        is_active = self.selected_reason == code
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border_radius=5,
            bgcolor=f"{COLORS['accent']}33" if is_active else f"{COLORS['primary']}11",
            border=ft.border.all(1,
                COLORS["accent"] if is_active else "transparent"),
            on_click=lambda e, c=code: self._select_reason(c),
            ink=True,
            content=ft.Text(label, size=11,
                            weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.W_500),
        )

    options_grid = ft.GridView(
        runs_count=2, spacing=4, run_spacing=4, max_extent=180,
        child_aspect_ratio=4.5, height=240,
        controls=[make_option(code, label)
                  for code, label, _ in list_all_reason_options()],
    )

    rec_block = ft.Container(visible=ai_hint is not None,
        padding=10, border_radius=6,
        bgcolor="#1E40AF22",
        border=ft.border.all(1, "#3B82F688"),
        content=ft.Row(spacing=8, controls=[
            ft.Text("🤖", size=16),
            ft.Column(spacing=2, expand=True, controls=[
                ft.Text("Recommendation", size=10, weight=ft.FontWeight.W_700,
                        color="#93C5FD"),
                ft.Text(ai_hint or "", size=11, opacity=0.85),
            ]),
        ]),
    )

    return ft.Column(spacing=10, controls=[
        ft.Text("Resolve Issue", size=16, weight=ft.FontWeight.W_700),
        ft.Text(f"{issue['employee_name']} · {issue['date']}",
                size=11, opacity=0.7),
        ft.Divider(height=1),
        rec_block,
        ft.Text("Pilih alasan:", size=11, weight=ft.FontWeight.W_600,
                color=COLORS["accent"]),
        options_grid,
        self.extra_input_field,
        self.preview_text,
        ft.Row(spacing=8, controls=[
            ft.ElevatedButton("Save",
                on_click=lambda e: self._save_resolution(),
                bgcolor=COLORS["resolved"], color="white"),
            ft.TextButton("Cancel",
                on_click=lambda e: self._close_panel()),
        ]),
    ])

def _update_preview(self):
    """Live preview: show what 'Alasan Ijin' text will look like."""
    from src.core.alasan_format import format_alasan
    if not self.selected_reason:
        self.preview_text.value = ""
    else:
        extra = requires_extra_input(self.selected_reason)
        loc = self.extra_input_field.value if extra == "location" else None
        det = self.extra_input_field.value if extra == "reason_detail" else None
        rendered = format_alasan(self.selected_reason, loc, det)
        if rendered:
            self.preview_text.value = f"→ Akan tertulis: \"{rendered}\""
        else:
            self.preview_text.value = ""
    self.preview_text.update()
```

- [ ] **Step 3: Update `_select_reason` to call `_update_preview`**

Find `_select_reason` and add at the end (after the existing rebuild):

```python
def _select_reason(self, code: str):
    self.selected_reason = code
    extra = requires_extra_input(code)
    self.extra_input_field.visible = extra is not None
    self.extra_input_field.label = "Lokasi" if extra == "location" else "Alasan"
    self.extra_input_field.value = ""
    cursor = self.repo.conn.execute(
        """SELECT ar.*, e.name AS employee_name FROM attendance_records ar
           JOIN employees e ON ar.employee_id=e.id WHERE ar.id=?""",
        (self.selected_record_id,),
    ).fetchone()
    self.resolve_panel.content = self._build_resolve_panel(dict(cursor))
    self.resolve_panel.update()
    self._update_preview()
```

- [ ] **Step 4: Add wider resolve panel**

Find the `build()` method. The resolve panel currently has `width=360`. Increase to `width=420`:

```python
self.resolve_panel = ft.Container(
    width=420, padding=20, visible=False,
    bgcolor=COLORS["surface_dark"] if self.mode == "dark" else COLORS["surface_light"],
)
```

- [ ] **Step 5: Manual verify**

Run: `python main.py`
Navigate to Issues page. Expect:
- Compact rows showing actual In/Out times (red if missing, green if present)
- Blue "AI" badge on rows where issue_case is A/B/C/F with hint text
- Click an issue → resolve panel opens (wider, ~420px)
- Recommendation block at top with 🤖 icon
- 2-column grid of 11 reason options
- After selecting "Pulang Lebih Awal" + typing "anak sakit" → preview text shows "→ Akan tertulis: \"Pulang Lebih Awal - anak sakit\""

- [ ] **Step 6: Verify tests**

Run: `pytest -q`
Expected: `88 passed`

- [ ] **Step 7: Commit**

```bash
git add src/ui/pages/issues.py
git commit -m "feat(issues): compact card grid, AI recommendation, 2-col resolve panel with live preview"
```

---

# PHASE 4 — MAIN DB UI (Tasks 9–11)

End state: Excel exporter writes 17-col Sheets-format files; new Main Database page with monthly nav, sticky-col table, inline edit, Export and TSV-clipboard buttons; sidebar nav updated.

---

### Task 9: 17-column `build_monthly_sheets_format`

**Files:**
- Modify: `src/reports/excel_builder.py`
- Modify: `tests/reports/test_excel_builder.py`

- [ ] **Step 1: Update existing test for new 17-col format**

Open `tests/reports/test_excel_builder.py`. Replace the existing `test_monthly_format_has_required_columns` with:

```python
def test_monthly_format_has_17_sheets_columns(tmp_path):
    """Output must match user's actual Sheets format byte-for-byte (17 cols)."""
    out = tmp_path / "monthly.xlsx"
    rows = [{
        "name": "ANDIKA", "department": "ARGA DIRGA",
        "date": "2026-04-01", "day_name": "Rabu", "day_type": "Hari Kerja",
        "schedule_in": "08:00", "schedule_out": "16:00",
        "actual_in": "08:06", "actual_out": "16:41",
        "work_hours": 7.9, "overtime_hours": None,
        "kurang_hours": 0.1, "late_minutes": 6, "early_leave_minutes": None,
        "absent_flag": None, "forgot_punch_flag": None, "ijin_flag": None,
        "alasan_ijin": "",
    }]
    build_monthly_sheets_format(str(out), rows)
    wb = load_workbook(out)
    ws = wb["Monthly Report"]
    headers = [ws.cell(1, c).value for c in range(1, 18)]
    assert headers == [
        "Nama", "Dept.", "Tanggal", "Hari", "Tipe",
        "Jadwal", "Masuk", "Keluar",
        "Kerja", "Lembur", "Kurang", "Terlambat", "Pulang Cepat",
        "Absen", "Lupa in/out", "Ijin", "Alasan Ijin",
    ]
    # Spot-check first data row
    assert ws.cell(2, 1).value == "ANDIKA"
    assert ws.cell(2, 7).value == "08:06"
    assert ws.cell(2, 12).value == 6
```

- [ ] **Step 2: Run test to confirm failure**

Run: `pytest tests/reports/test_excel_builder.py::test_monthly_format_has_17_sheets_columns -v`
Expected: FAIL — current implementation has 9 columns, not 17.

- [ ] **Step 3: Replace `build_monthly_sheets_format` in `src/reports/excel_builder.py`**

Find the existing function and replace entirely:

```python
def build_monthly_sheets_format(output_path: str, monthly_rows: list[dict]):
    """Write monthly recap matching the user's Google Sheets format (17 cols).

    Each row dict expects these keys (others are tolerated and ignored):
        name, department, date (ISO), day_name, day_type,
        schedule_in, schedule_out, actual_in, actual_out,
        work_hours, overtime_hours, kurang_hours,
        late_minutes, early_leave_minutes,
        absent_flag, forgot_punch_flag, ijin_flag,
        alasan_ijin (free-form text)

    Saturday/Sunday rows (day_type='Istirahat') write only Nama/Dept/Tanggal/Hari/Tipe
    (other columns left blank), matching the user's reference file.
    """
    headers = [
        "Nama", "Dept.", "Tanggal", "Hari", "Tipe",
        "Jadwal", "Masuk", "Keluar",
        "Kerja", "Lembur", "Kurang", "Terlambat", "Pulang Cepat",
        "Absen", "Lupa in/out", "Ijin", "Alasan Ijin",
    ]
    wb = Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet(title="Monthly Report")
    ws.append(headers)
    for cell in ws[1]:
        cell.font = HEADER_FONT
        cell.fill = PRIMARY_FILL
        cell.alignment = Alignment(horizontal="center")
        cell.border = THIN_BORDER

    for r in monthly_rows:
        is_rest = r.get("day_type") == "Istirahat"
        if is_rest:
            ws.append([
                r.get("name", ""),
                r.get("department", ""),
                r.get("date", ""),
                r.get("day_name", ""),
                r.get("day_type", "Istirahat"),
                "", "", "", "", "", "", "", "", "", "", "", "",
            ])
        else:
            schedule = ""
            if r.get("schedule_in") and r.get("schedule_out"):
                schedule = f"{r['schedule_in'].replace(':','.')} - {r['schedule_out'].replace(':','.')}"
            ws.append([
                r.get("name", ""),
                r.get("department", ""),
                r.get("date", ""),
                r.get("day_name", ""),
                r.get("day_type", ""),
                schedule,
                r.get("actual_in") or "",
                r.get("actual_out") or "",
                r.get("work_hours") if r.get("work_hours") is not None else "",
                r.get("overtime_hours") if r.get("overtime_hours") not in (None, 0) else "",
                r.get("kurang_hours") if r.get("kurang_hours") is not None else "",
                r.get("late_minutes") if r.get("late_minutes") not in (None, 0) else "",
                r.get("early_leave_minutes") if r.get("early_leave_minutes") not in (None, 0) else "",
                r.get("absent_flag") if r.get("absent_flag") not in (None, 0) else "",
                r.get("forgot_punch_flag") if r.get("forgot_punch_flag") not in (None, 0) else "",
                r.get("ijin_flag") if r.get("ijin_flag") not in (None, 0) else "",
                r.get("alasan_ijin", ""),
            ])

    # Auto-width columns
    for col_idx in range(1, 18):
        col_letter = get_column_letter(col_idx)
        max_len = max(
            [len(str(headers[col_idx - 1]))] +
            [len(str(ws.cell(row_idx, col_idx).value or ""))
             for row_idx in range(2, ws.max_row + 1)]
        )
        ws.column_dimensions[col_letter].width = min(max_len + 2, 40)

    wb.save(output_path)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/reports/test_excel_builder.py -v`
Expected: all tests pass (the existing 2 still pass, plus the rewritten 1 = 3 total).

- [ ] **Step 5: Find any callers of the old signature and update them**

Run: `grep -rn "build_monthly_sheets_format" src/ tests/`
Expected callers: `src/ui/pages/monthly_report.py` and the test file.

Open `src/ui/pages/monthly_report.py`. Find the call to `build_monthly_sheets_format`. The current code passes records with old keys (`name`, `staff_no`, `actual_in`, `late_minutes`, `reason_code`, `location`, `reason_detail`). Update the dict-comprehension that builds `normalized` to include the new fields by importing and using `format_alasan`:

Replace:

```python
normalized = [{
    "date": r["date"], "name": r["employee_name"], "staff_no": r["staff_no"],
    "actual_in": r["actual_in"], "actual_out": r["actual_out"],
    "late_minutes": r["late_minutes"], "early_leave_minutes": r["early_leave_minutes"],
    "reason_code": r["reason_code"], "location": r["location"], "reason_detail": r["reason_detail"],
} for r in rows]
```

With:

```python
from src.core.alasan_format import format_alasan
normalized = [{
    "name": r["employee_name"],
    "department": r.get("department"),
    "date": r["date"],
    "day_name": r.get("day_name"),
    "day_type": r.get("day_type"),
    "schedule_in": r.get("schedule_in"),
    "schedule_out": r.get("schedule_out"),
    "actual_in": r.get("actual_in"),
    "actual_out": r.get("actual_out"),
    "work_hours": r.get("work_hours"),
    "overtime_hours": r.get("overtime_hours"),
    "kurang_hours": None,  # not stored in v1.0; left blank
    "late_minutes": r.get("late_minutes"),
    "early_leave_minutes": r.get("early_leave_minutes"),
    "absent_flag": r.get("absent_flag"),
    "forgot_punch_flag": r.get("forgot_punch_flag"),
    "ijin_flag": 1 if r.get("reason_code") else None,
    "alasan_ijin": format_alasan(r.get("reason_code"),
                                   r.get("location"),
                                   r.get("reason_detail")),
} for r in rows]
```

- [ ] **Step 6: Verify full suite**

Run: `pytest -q`
Expected: `88 passed`

- [ ] **Step 7: Commit**

```bash
git add src/reports/excel_builder.py tests/reports/test_excel_builder.py src/ui/pages/monthly_report.py
git commit -m "feat(reports): build_monthly_sheets_format produces 17-col Sheets-matched .xlsx"
```

---

### Task 10: Main Database page implementation

**Files:**
- Create: `src/ui/pages/main_database.py`

- [ ] **Step 1: Create the page file**

Create `src/ui/pages/main_database.py`:

```python
import flet as ft
from datetime import date
from calendar import monthrange
from pathlib import Path

from src.core.constants import COLORS, REASON_CODES
from src.core.alasan_format import format_alasan
from src.db.repository import Repository
from src.core.settings_store import SettingsStore


class MainDatabasePage:
    def __init__(self, repo: Repository, settings: SettingsStore,
                 exports_dir: str, mode: str = "dark"):
        self.repo = repo
        self.settings = settings
        self.exports_dir = Path(exports_dir)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.mode = mode
        self.year, self.month = self._resolve_default_month()
        self.employee_filter: str | None = None  # staff_no or None for all

    def _resolve_default_month(self) -> tuple[int, int]:
        cursor = self.repo.conn.execute(
            "SELECT MAX(date) FROM attendance_records WHERE day_type='Hari Kerja'"
        )
        row = cursor.fetchone()
        if row and row[0]:
            from datetime import datetime as _dt
            d = _dt.fromisoformat(row[0]).date()
            return (d.year, d.month)
        today = date.today()
        return (today.year, today.month)

    def build(self) -> ft.Control:
        self.status_text = ft.Text("", size=11, opacity=0.7)
        self.table_container = ft.Container(expand=True)
        self._refresh_table()
        return ft.Container(
            padding=16, expand=True,
            content=ft.Column(spacing=12, expand=True, controls=[
                self._build_header(),
                self._build_toolbar(),
                self._build_info_banner(),
                self.status_text,
                ft.Container(expand=True, content=self.table_container),
                self._build_legend(),
            ]),
        )

    # ------------------------- header -------------------------
    def _build_header(self) -> ft.Control:
        return ft.Row(controls=[
            ft.Column(spacing=2, expand=True, controls=[
                ft.Text("📊 Main Database", size=22, weight=ft.FontWeight.W_800),
                ft.Text("Monthly attendance recap · matches Google Sheets format (17 cols)",
                        size=11, opacity=0.7),
            ]),
            ft.ElevatedButton("📥 Export .xlsx",
                on_click=lambda e: self._export_xlsx(),
                bgcolor=f"{COLORS['primary']}66", color="white"),
            ft.ElevatedButton("📋 Copy as TSV",
                on_click=lambda e: self._copy_tsv(),
                bgcolor=f"{COLORS['accent']}66", color="white"),
        ])

    # ------------------------- toolbar -------------------------
    def _build_toolbar(self) -> ft.Control:
        month_names = ["", "January", "February", "March", "April", "May", "June",
                       "July", "August", "September", "October", "November", "December"]
        self.month_label = ft.Text(
            f"{month_names[self.month]} {self.year}",
            size=15, weight=ft.FontWeight.W_700,
        )
        return ft.Row(spacing=14, controls=[
            ft.IconButton(ft.Icons.CHEVRON_LEFT,
                          on_click=lambda e: self._step_month(-1)),
            self.month_label,
            ft.IconButton(ft.Icons.CHEVRON_RIGHT,
                          on_click=lambda e: self._step_month(1)),
        ])

    def _step_month(self, direction: int):
        self.month += direction
        if self.month > 12:
            self.month = 1
            self.year += 1
        elif self.month < 1:
            self.month = 12
            self.year -= 1
        month_names = ["", "January", "February", "March", "April", "May", "June",
                       "July", "August", "September", "October", "November", "December"]
        self.month_label.value = f"{month_names[self.month]} {self.year}"
        self.month_label.update()
        self._refresh_table()
        self.table_container.update()

    # ------------------------- info banner -------------------------
    def _build_info_banner(self) -> ft.Control:
        return ft.Container(
            padding=10, border_radius=8,
            bgcolor="#1E40AF22",
            border=ft.border.all(1, "#3B82F688"),
            content=ft.Row(spacing=10, controls=[
                ft.Text("💡", size=16),
                ft.Text("Greyed/italic rows are skeleton (not yet imported). "
                        "Click any cell to edit. Alasan Ijin column accepts free-form text.",
                        size=11, expand=True, opacity=0.85),
            ]),
        )

    # ------------------------- legend -------------------------
    def _build_legend(self) -> ft.Control:
        def chip(color, label):
            return ft.Row(spacing=4, controls=[
                ft.Container(width=10, height=10, border_radius=2, bgcolor=color),
                ft.Text(label, size=10, opacity=0.7),
            ])
        return ft.Row(spacing=14, wrap=True, controls=[
            chip(COLORS["late_mild"], "Late <15"),
            chip(COLORS["late_severe"], "Late ≥15"),
            chip(COLORS["pulang_cepat"], "Pulang cepat"),
            chip(COLORS["resolved"], "Has Alasan Ijin"),
            chip(f"{COLORS['primary']}33", "Skeleton (not imported)"),
        ])

    # ------------------------- table -------------------------
    def _refresh_table(self):
        rows = self.repo.list_monthly_grid(self.year, self.month, self.employee_filter)

        # Build DataTable
        columns = [
            "Nama", "Dept.", "Tanggal", "Hari", "Tipe",
            "Jadwal", "Masuk", "Keluar",
            "Kerja", "Lembur", "Kurang", "Telat", "Pulang Cpt",
            "Absen", "Lupa", "Ijin", "Alasan Ijin",
        ]
        data_columns = [
            ft.DataColumn(ft.Text(c, size=10, weight=ft.FontWeight.W_700,
                                  color=COLORS["accent"]))
            for c in columns
        ]

        data_rows = []
        for r in rows:
            is_skeleton = r["id"] is None
            is_rest = r["day_type"] == "Istirahat"

            late_color = None
            if r.get("late_minutes"):
                late_color = (COLORS["late_severe"] if r["late_minutes"] >= 15
                              else COLORS["late_mild"])

            alasan = format_alasan(
                r.get("reason_code"), r.get("location"), r.get("reason_detail"),
            )
            alasan_color = COLORS["resolved"] if alasan else None

            def cell(value, color=None, italic=False):
                return ft.DataCell(ft.Text(
                    "" if value is None else str(value),
                    size=10,
                    color=color or (COLORS["primary"] + "55" if is_skeleton else None),
                    italic=italic or is_skeleton,
                ))

            data_rows.append(ft.DataRow(cells=[
                cell(r["name"]),
                cell(r.get("department", "")),
                cell(r["date"]),
                cell(r["day_name"]),
                cell(r["day_type"]),
                cell(f"{r.get('schedule_in','')}-{r.get('schedule_out','')}"
                     if r.get("schedule_in") else ""),
                cell(r.get("actual_in", "")),
                cell(r.get("actual_out", "")),
                cell(r.get("work_hours") or ""),
                cell(r.get("overtime_hours") or ""),
                cell(""),  # Kurang — not stored separately
                cell(r.get("late_minutes") or "", color=late_color),
                cell(r.get("early_leave_minutes") or "",
                     color=COLORS["pulang_cepat"] if r.get("early_leave_minutes") else None),
                cell(r.get("absent_flag") or ""),
                cell(r.get("forgot_punch_flag") or ""),
                cell(1 if r.get("reason_code") else ""),
                cell(alasan, color=alasan_color),
            ]))

        self.table_container.content = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True,
            controls=[ft.Row(scroll=ft.ScrollMode.AUTO, controls=[ft.DataTable(
                columns=data_columns, rows=data_rows,
                column_spacing=12, heading_row_height=32, data_row_max_height=28,
                divider_thickness=0.5,
                heading_row_color=f"{COLORS['surface_dark']}",
            )])])

        self.status_text.value = f"{len(rows)} rows · {len(set(r['name'] for r in rows))} employees"

    # ------------------------- export -------------------------
    def _export_xlsx(self):
        from src.reports.excel_builder import build_monthly_sheets_format

        rows = self.repo.list_monthly_grid(self.year, self.month, self.employee_filter)
        normalized = [{
            "name": r["name"],
            "department": r.get("department"),
            "date": r["date"],
            "day_name": r["day_name"],
            "day_type": r["day_type"],
            "schedule_in": r.get("schedule_in"),
            "schedule_out": r.get("schedule_out"),
            "actual_in": r.get("actual_in"),
            "actual_out": r.get("actual_out"),
            "work_hours": r.get("work_hours"),
            "overtime_hours": r.get("overtime_hours"),
            "kurang_hours": None,
            "late_minutes": r.get("late_minutes"),
            "early_leave_minutes": r.get("early_leave_minutes"),
            "absent_flag": r.get("absent_flag"),
            "forgot_punch_flag": r.get("forgot_punch_flag"),
            "ijin_flag": 1 if r.get("reason_code") else None,
            "alasan_ijin": format_alasan(r.get("reason_code"),
                                          r.get("location"),
                                          r.get("reason_detail")),
        } for r in rows]
        out = self.exports_dir / f"main-db_{self.year}-{self.month:02d}.xlsx"
        build_monthly_sheets_format(str(out), normalized)
        self.status_text.value = f"✅ Exported: {out}"
        self.status_text.update()

    def _copy_tsv(self):
        import io, csv
        rows = self.repo.list_monthly_grid(self.year, self.month, self.employee_filter)
        headers = ["Nama", "Dept.", "Tanggal", "Hari", "Tipe", "Jadwal",
                   "Masuk", "Keluar", "Kerja", "Lembur", "Kurang",
                   "Terlambat", "Pulang Cepat", "Absen", "Lupa in/out",
                   "Ijin", "Alasan Ijin"]
        buf = io.StringIO()
        w = csv.writer(buf, delimiter="\t", lineterminator="\n")
        w.writerow(headers)
        for r in rows:
            w.writerow([
                r["name"], r.get("department", ""), r["date"], r["day_name"], r["day_type"],
                f"{r.get('schedule_in','')}-{r.get('schedule_out','')}" if r.get("schedule_in") else "",
                r.get("actual_in", "") or "", r.get("actual_out", "") or "",
                r.get("work_hours") if r.get("work_hours") is not None else "",
                r.get("overtime_hours") if r.get("overtime_hours") not in (None, 0) else "",
                "",
                r.get("late_minutes") if r.get("late_minutes") not in (None, 0) else "",
                r.get("early_leave_minutes") if r.get("early_leave_minutes") not in (None, 0) else "",
                r.get("absent_flag") if r.get("absent_flag") not in (None, 0) else "",
                r.get("forgot_punch_flag") if r.get("forgot_punch_flag") not in (None, 0) else "",
                1 if r.get("reason_code") else "",
                format_alasan(r.get("reason_code"), r.get("location"),
                              r.get("reason_detail")),
            ])
        text = buf.getvalue()
        try:
            self.status_text.page.set_clipboard(text)
            self.status_text.value = f"✅ Copied {len(rows)} rows as TSV — paste into Sheets"
        except Exception as ex:
            self.status_text.value = f"❌ Clipboard failed: {ex}"
        self.status_text.update()
```

- [ ] **Step 2: Verify it imports**

Run: `python -c "from src.ui.pages.main_database import MainDatabasePage; print('OK')"`
Expected: `OK`.

- [ ] **Step 3: Verify full suite still passes**

Run: `pytest -q`
Expected: `88 passed`

- [ ] **Step 4: Commit**

```bash
git add src/ui/pages/main_database.py
git commit -m "feat(ui): MainDatabasePage with monthly grid, inline labels, export, TSV copy"
```

---

### Task 11: Wire `main_database` route in shell + sidebar nav

**Files:**
- Modify: `src/ui/shell.py`

- [ ] **Step 1: Add new sidebar group with main_database entry**

Open `src/ui/shell.py`. Find the `NAV_GROUPS` list at the top. Insert a new group between "Workflow" and "Reports":

```python
NAV_GROUPS = [
    ("Workflow", [
        ("import_data", "Import Data", ft.Icons.UPLOAD_FILE),
        ("issues", "Issues", ft.Icons.WARNING_AMBER),
        ("dashboard", "Dashboard", ft.Icons.DASHBOARD),
    ]),
    ("Database", [
        ("main_database", "Main Database", ft.Icons.TABLE_VIEW),
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
```

- [ ] **Step 2: Wire route builder in `_init_route_builders`**

Find `_init_route_builders` and add an `elif` branch for `main_database`:

```python
elif route == "main_database":
    builders[route] = self._build_main_database_page
```

(Place it together with the other `elif` route mappings.)

- [ ] **Step 3: Add the `_build_main_database_page` method**

Inside the `Shell` class, add (place near the other `_build_X_page` methods):

```python
def _build_main_database_page(self) -> ft.Control:
    from src.ui.pages.main_database import MainDatabasePage
    root = Path(self.snapshot_dir).parent
    page_obj = MainDatabasePage(
        self.repo, self.settings,
        str(root / "data" / "exports"),
        self.mode,
    )
    return page_obj.build()
```

- [ ] **Step 4: Manual verify**

Run: `python main.py`
- Sidebar shows new "DATABASE" section with "Main Database" entry
- Click it → page renders with month nav, table, export buttons
- Click ◀ ▶ → month label updates, table refreshes
- Click "📥 Export .xlsx" → status text shows path
- Click "📋 Copy as TSV" → status text shows "Copied N rows..."

- [ ] **Step 5: Verify tests**

Run: `pytest -q`
Expected: `88 passed`

- [ ] **Step 6: Commit**

```bash
git add src/ui/shell.py
git commit -m "feat(shell): wire Main Database route in sidebar nav"
```

---

# PHASE 5 — POLISH (Task 12)

End state: Import Data status text shows full conflict breakdown with the new `preserved_resolved` count; smoke-test full app end-to-end.

---

### Task 12: Import Data status breakdown + final smoke test

**Files:**
- Modify: `src/ui/pages/import_data.py`

- [ ] **Step 1: Update `_do_import` to show preserved_resolved in summary**

Open `src/ui/pages/import_data.py`. Find `_do_import`. Replace its body:

```python
def _do_import(self, policy: ConflictPolicy):
    summary = resolve_import(
        self.repo, self.parsed_records, Path(self.selected_file).name,
        snapshot_dir=self.snapshot_dir, policy=policy,
        settings=self.settings.load(),
    )
    parts = [
        f"{summary['inserted']} new",
        f"{summary['kept']} kept",
        f"{summary['overwritten']} overwritten",
    ]
    if summary.get("preserved_resolved", 0) > 0:
        parts.append(f"{summary['preserved_resolved']} preserved (resolved)")
    msg = "✅ Import done · " + " · ".join(parts)
    self.status_text.value = msg
    self.status_text.update()
    self._reset_after_success()
```

- [ ] **Step 2: Manual verify**

Run: `python main.py`
- Import a fingerprint .xls file
- Resolve at least 1 issue
- Re-import the same file with OVERWRITE policy
- Status text should show: `✅ Import done · 0 new · ... · X preserved (resolved)`

- [ ] **Step 3: Run full test suite**

Run: `pytest -v`
Expected: `88 passed`

- [ ] **Step 4: Smoke test full v2.0 app end-to-end**

Run: `python main.py`. Step through:
1. Import the April fingerprint .xls (Phase 2 already worked)
2. Resolve a few issues including the new "Tidak Hadir" option (test it appears as 11th option)
3. Open Main Database → April should show with all 30 days, mix of imported & skeleton rows
4. Edit an Alasan Ijin cell directly with text "Lapangan ke Surabaya" → save → cell shows green
5. Click "📥 Export .xlsx" → check the resulting file in `data/exports/main-db_2026-04.xlsx` opens in Excel/LibreOffice and matches the 17-col format
6. Click "📋 Copy as TSV" → paste into a text editor, verify TSV format
7. Open Dashboard → confirms it defaults to last week with data, Weekly/Monthly toggle works
8. Open Issues → verify compact card layout, AI badge appears, click an issue → resolve panel shows recommendation block + 2-col grid + live preview when typing in extra field

- [ ] **Step 5: Commit + tag**

```bash
git add src/ui/pages/import_data.py
git commit -m "feat(import): show preserved_resolved breakdown in status text"
git tag -a v2.0.0 -m "v2.0.0 — Main Database, Dashboard default, Issues redesign + bug fixes"
```

- [ ] **Step 6: Rebuild .exe**

Run: `python scripts/build_exe.py`
Expected: `dist/JosaphatTechHR.exe` (~100MB) rebuilt with v2.0 features.

- [ ] **Step 7: Push to remote**

```bash
git push origin master
git push origin v2.0.0
```

---

## Self-Review (run after writing this plan)

### Spec coverage map

| Spec section | Implemented in |
|---|---|
| §1 Overview / goals | All 12 tasks combined |
| §3 Architecture | T4 (alasan_format), T5 (list_monthly_grid), T10 (MainDatabasePage), T6 (conflict), T8 (issues UI), T3 (dashboard), T1 (constants) |
| §4 Data Model — no schema change | T5 verifies skeleton rows assembled in Python, no DDL |
| §5.1 alasan_format module | T4 (with all 13+ cases tested) |
| §5.2 constants — add tidak_hadir | T1 |
| §5.3 list_monthly_grid | T5 |
| §5.4 conflict.py preserved_resolved | T6 |
| §5.5 issues page bug fix + perf + UI | T2 (bug + perf) and T8 (UI) |
| §5.6 dashboard default + range toggle | T3 |
| §5.7 main_database.py page | T10 |
| §5.8 shell.py route | T11 |
| §6 UI screens | T8 (issues mockup 06), T10 (main DB mockup 07) |
| §7 conflict resolution UI breakdown | T12 |
| §9 Open items: none | n/a |

### Placeholder scan

No "TBD/TODO/implement later/handle X appropriately" found. Each step has concrete code or commands.

### Type consistency

- `format_alasan(reason_code, location, reason_detail)` — same signature in T4, T8, T9, T10
- `list_monthly_grid(year, month, staff_no_filter=None)` — same signature in T5, T10
- `recommend(issue_case)` — same signature in T7, T8
- `resolve_import` returns `preserved_resolved` (T6), consumed by T12

All consistent.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-09-main-db-and-issues-redesign.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, two-stage review (spec compliance + code quality) per task, fast iteration
2. **Inline Execution** — execute tasks in this session via executing-plans, batch execution with checkpoints

**Which approach?**
