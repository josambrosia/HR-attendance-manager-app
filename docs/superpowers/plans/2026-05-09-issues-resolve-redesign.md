# Issues Page — Resolve Modal + Status-Aware List Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the cramped 420px right-side resolve panel with a 720px centered modal that has grouped reason categories, AI recommendation banner, prominent extra-input field, live preview, and edit-mode for re-touching resolved issues. Add a status-aware list (Pending on top, Resolved below) with stat chips at the page header.

**Architecture:** New `Repository.list_issues_with_resolutions(start, end)` returns both pending and resolved rows in one query, sorted with NULL-resolution first. `IssuesPage` keeps its constructor signature mostly unchanged (one new `page` parameter so the modal can mount onto `page.overlay`). New nested `ResolveModal` class encapsulates the dialog widget tree and state. Existing `apply_resolution` / `delete_resolution` / `requires_extra_input` / `format_alasan` are reused unchanged.

**Tech Stack:** Flet 0.25.2, Python sqlite3, pytest 8.3.3 + `unittest.mock.MagicMock` for page stub.

**Spec:** [docs/superpowers/specs/2026-05-09-issues-resolve-redesign.md](../specs/2026-05-09-issues-resolve-redesign.md)
**Mockups:** [mockups/09-issues-resolve-redesign.html](../../../mockups/09-issues-resolve-redesign.html), [mockups/10-issues-with-status.html](../../../mockups/10-issues-with-status.html)

---

## File Structure

**New files:**
- `tests/ui/test_issues_page.py` — page + modal tests (~12 tests)

**Modified files:**
- `src/db/repository.py` — add `list_issues_with_resolutions` method
- `src/db/schema.sql` — no changes
- `src/ui/shell.py` — pass `self.page` into `IssuesPage` constructor
- `src/ui/pages/issues.py` — major refactor (~310 → ~550 lines):
  - `IssuesPage.__init__` adds `page` param
  - `IssuesPage.build` rebuilt — full-width list, no right-side panel
  - Stat chips builder
  - Sectioned list (Pending divider + rows / Resolved divider + rows)
  - New row builders `_build_pending_row` / `_build_resolved_row`
  - New nested `ResolveModal` class (~250 lines inside same file)
  - Old `_build_resolve_panel`, `_select_issue`, `_select_reason`, `_save_resolution`, `_close_panel`, `_build_reason_button`, `_update_preview` removed (replaced by ResolveModal)
- `tests/db/test_repository.py` — 2 new tests for the new method
- `scripts/build_exe.py` — bump PRODUCT_VERSION to 2.2.0 (Task 10 only)

---

## Task 1: Repository.list_issues_with_resolutions

**Files:**
- Modify: `src/db/repository.py` (append a new method on the Repository class)
- Test: `tests/db/test_repository.py` (append 2 tests)

- [ ] **Step 1: Write failing tests**

Append to `tests/db/test_repository.py`:

```python
def test_list_issues_with_resolutions_pending_first(tmp_path):
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    emp = repo.upsert_employee(staff_no="1001", name="ALICE")
    # Two attendance records on different dates, both case A (tidak hadir)
    rec_a = repo.insert_attendance({
        "employee_id": emp, "date": "2026-04-01", "day_name": "Rabu",
        "day_type": "Hari Kerja", "issue_case": "A",
    })
    rec_b = repo.insert_attendance({
        "employee_id": emp, "date": "2026-04-02", "day_name": "Kamis",
        "day_type": "Hari Kerja", "issue_case": "A",
    })
    # Resolve only rec_a
    repo.upsert_resolution(rec_a, reason_code="cuti")

    rows = repo.list_issues_with_resolutions("2026-04-01", "2026-04-07")
    assert len(rows) == 2
    # Pending (no reason_code) must come first
    assert rows[0]["reason_code"] is None
    assert rows[0]["id"] == rec_b
    assert rows[1]["reason_code"] == "cuti"
    assert rows[1]["id"] == rec_a


def test_list_issues_with_resolutions_excludes_non_issue_cases(tmp_path):
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    emp = repo.upsert_employee(staff_no="1001", name="ALICE")
    # Case D (mild late) is NOT in the issue set (A/B/C/F) — should be excluded
    repo.insert_attendance({
        "employee_id": emp, "date": "2026-04-01", "day_name": "Rabu",
        "day_type": "Hari Kerja", "issue_case": "D",
    })
    # Case G (Istirahat / weekend) is also out
    repo.insert_attendance({
        "employee_id": emp, "date": "2026-04-04", "day_name": "Sabtu",
        "day_type": "Istirahat", "issue_case": "G",
    })
    # Case A is in
    repo.insert_attendance({
        "employee_id": emp, "date": "2026-04-02", "day_name": "Kamis",
        "day_type": "Hari Kerja", "issue_case": "A",
    })

    rows = repo.list_issues_with_resolutions("2026-04-01", "2026-04-07")
    assert len(rows) == 1
    assert rows[0]["issue_case"] == "A"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/db/test_repository.py -v -k "issues_with_resolutions"`
Expected: FAIL — `AttributeError: 'Repository' object has no attribute 'list_issues_with_resolutions'`

- [ ] **Step 3: Add the method**

Open `src/db/repository.py`. Just before the existing `def list_history_for_record` method (around line 213), add:

```python
    def list_issues_with_resolutions(self, start_date: str, end_date: str) -> list[dict]:
        """Return all issues (case A/B/C/F) in date range, with resolution info if any.

        Ordered: pending first (resolution NULL), then resolved; within each group
        by date asc, then employee name asc. Used by the Issues page to render
        the Pending and Resolved sections.
        """
        cursor = self.conn.execute(
            """SELECT ar.*, e.name AS employee_name, e.staff_no,
                      r.reason_code, r.location, r.reason_detail, r.resolved_at
               FROM attendance_records ar
               JOIN employees e ON ar.employee_id = e.id
               LEFT JOIN resolutions r ON r.record_id = ar.id
               WHERE ar.date >= ? AND ar.date <= ?
                 AND ar.issue_case IN ('A','B','C','F')
               ORDER BY (r.id IS NULL) DESC, ar.date, e.name""",
            (start_date, end_date),
        )
        return [dict(row) for row in cursor.fetchall()]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/db/test_repository.py -v -k "issues_with_resolutions"`
Expected: PASS — 2 tests

- [ ] **Step 5: Run full suite for regression**

Run: `python -m pytest -q`
Expected: PASS — 111 passed (109 prior + 2 new), 6 skipped

- [ ] **Step 6: Commit**

```bash
git add src/db/repository.py tests/db/test_repository.py
git commit -m "feat(db): list_issues_with_resolutions returns pending + resolved sorted"
```

---

## Task 2: IssuesPage constructor accepts `page` + Shell passes it

**Files:**
- Modify: `src/ui/pages/issues.py:18-36` (constructor + new attribute)
- Modify: `src/ui/shell.py` (`_build_issues_page` method)

The modal mounts onto `page.overlay`, so `IssuesPage` needs a `page` reference. Shell already has `self.page`; pass it through.

- [ ] **Step 1: Modify the IssuesPage constructor**

Open `src/ui/pages/issues.py`. Find:

```python
class IssuesPage:
    def __init__(self, repo: Repository, settings: SettingsStore, mode: str = "dark",
                 on_data_changed=None,
                 show_loading=None, hide_loading=None, notify=None):
        self.repo = repo
        self.settings = settings
        self.mode = mode
        self.on_data_changed = on_data_changed
        self.show_loading = show_loading
        self.hide_loading = hide_loading
        self.notify = notify
        # Default: current week (Mon-Sun)
        today = date.today()
        self.start = today - timedelta(days=today.weekday())
        self.end = self.start + timedelta(days=6)
        self.selected_record_id = None
        self.selected_employee_name = ""
        self.selected_reason = None
        self._refresh_timer = None
```

Replace with:

```python
class IssuesPage:
    def __init__(self, page: ft.Page, repo: Repository, settings: SettingsStore,
                 mode: str = "dark",
                 on_data_changed=None,
                 show_loading=None, hide_loading=None, notify=None):
        self.page = page
        self.repo = repo
        self.settings = settings
        self.mode = mode
        self.on_data_changed = on_data_changed
        self.show_loading = show_loading
        self.hide_loading = hide_loading
        self.notify = notify
        # Default: current week (Mon-Sun)
        today = date.today()
        self.start = today - timedelta(days=today.weekday())
        self.end = self.start + timedelta(days=6)
        self._refresh_timer = None
        # Filled in build() — kept here so methods can reference safely before build
        self.list_view: ft.Column | None = None
        self._stat_pending: ft.Container | None = None
        self._stat_resolved: ft.Container | None = None
        self._stat_total: ft.Container | None = None
        self._modal: "ResolveModal | None" = None
```

(Removed `selected_record_id`, `selected_employee_name`, `selected_reason` — these are now state of the modal, not the page.)

- [ ] **Step 2: Update Shell builder**

Open `src/ui/shell.py`. Find `_build_issues_page`:

```python
    def _build_issues_page(self) -> ft.Control:
        from src.ui.pages.issues import IssuesPage
        page_obj = IssuesPage(self.repo, self.settings, self.mode,
                              on_data_changed=self.invalidate_data_caches,
                              show_loading=self.show_loading,
                              hide_loading=self.hide_loading,
                              notify=self.notify)
        return page_obj.build()
```

Replace with:

```python
    def _build_issues_page(self) -> ft.Control:
        from src.ui.pages.issues import IssuesPage
        page_obj = IssuesPage(self.page, self.repo, self.settings, self.mode,
                              on_data_changed=self.invalidate_data_caches,
                              show_loading=self.show_loading,
                              hide_loading=self.hide_loading,
                              notify=self.notify)
        return page_obj.build()
```

- [ ] **Step 3: Run full suite**

Run: `python -m pytest -q`
Expected: PASS — 111 passed (existing tests still pass; the IssuesPage constructor change is non-breaking for shell tests because they only test that `Shell.build()` populates the page cache and don't instantiate `IssuesPage` directly).

The `tests/ui/test_shell_cache.py` test `test_navigate_caches_built_page` calls `shell._navigate("issues")` which goes through `_build_issues_page` → IssuesPage → `.build()`. The mock page's `MagicMock` supports any attribute (including `.overlay.append`), so this passes.

- [ ] **Step 4: Commit**

```bash
git add src/ui/pages/issues.py src/ui/shell.py
git commit -m "refactor(issues): constructor accepts ft.Page for modal mounting"
```

---

## Task 3: Stat chips builder + page header rebuild

**Files:**
- Modify: `src/ui/pages/issues.py` — replace `build()` and add stat chip helper
- Test: `tests/ui/__init__.py` exists; create `tests/ui/test_issues_page.py`

- [ ] **Step 1: Write failing tests**

Create `tests/ui/test_issues_page.py`:

```python
"""Tests for IssuesPage list/modal redesign.

Strategy: instantiate IssuesPage with a real in-memory Repository (so SQL
behaviour is exercised) and a MagicMock Flet page (so modal can append to
page.overlay without crashing). Inspect widget property values to verify
expected state.
"""
from unittest.mock import MagicMock

import pytest

from src.core.constants import COLORS
from src.core.settings_store import SettingsStore
from src.db.repository import Repository
from src.ui.pages.issues import IssuesPage


@pytest.fixture
def page_with_data(tmp_path):
    """Build a Repository with 2 pending + 1 resolved issue in the test week."""
    settings = SettingsStore(str(tmp_path / "config.json"))
    settings.load()
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()

    emp = repo.upsert_employee(staff_no="1001", name="ALICE")
    pending_a = repo.insert_attendance({
        "employee_id": emp, "date": "2026-04-01", "day_name": "Rabu",
        "day_type": "Hari Kerja", "issue_case": "A",
    })
    pending_b = repo.insert_attendance({
        "employee_id": emp, "date": "2026-04-02", "day_name": "Kamis",
        "day_type": "Hari Kerja", "issue_case": "A",
    })
    resolved = repo.insert_attendance({
        "employee_id": emp, "date": "2026-04-03", "day_name": "Jumat",
        "day_type": "Hari Kerja", "issue_case": "A",
    })
    repo.upsert_resolution(resolved, reason_code="cuti")

    page = MagicMock()
    page.overlay = []

    issues_page = IssuesPage(page, repo, settings, mode="dark")
    issues_page.start = type(issues_page.start).fromisoformat("2026-03-30")
    issues_page.end = type(issues_page.end).fromisoformat("2026-04-05")
    issues_page.build()
    yield issues_page, repo
    repo.close()


def test_stat_chips_show_correct_counts(page_with_data):
    p, _ = page_with_data
    # Stat chips have a Column with [Text(count), Text(label)]
    pending_count = p._stat_pending.content.controls[0].value
    resolved_count = p._stat_resolved.content.controls[0].value
    total_count = p._stat_total.content.controls[0].value
    assert pending_count == "2"
    assert resolved_count == "1"
    assert total_count == "3"


def test_stat_pending_chip_uses_late_severe_color(page_with_data):
    p, _ = page_with_data
    # Pending chip border should match late_severe palette
    border = p._stat_pending.border
    assert border is not None
    assert border.left.color == COLORS["late_severe"]


def test_stat_resolved_chip_uses_resolved_color(page_with_data):
    p, _ = page_with_data
    border = p._stat_resolved.border
    assert border.left.color == COLORS["resolved"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/ui/test_issues_page.py -v`
Expected: FAIL — `AttributeError: 'IssuesPage' object has no attribute '_stat_pending'`

- [ ] **Step 3: Add stat-chip helper + rewrite build()**

Open `src/ui/pages/issues.py`. Find the existing `build` method (~line 38):

```python
    def build(self) -> ft.Control:
        self.list_view = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=6, expand=True)
        self.resolve_panel = ft.Container(
            width=420, padding=20, visible=False,
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
```

Replace with:

```python
    def build(self) -> ft.Control:
        self.list_view = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=4, expand=True)
        self._stat_pending = self._build_stat_chip("0", "Pending", "pending")
        self._stat_resolved = self._build_stat_chip("0", "Resolved", "resolved")
        self._stat_total = self._build_stat_chip("0", "Total", "total")
        self.subtitle_text = ft.Text("", size=12, opacity=0.7)

        # Modal mounts itself onto page.overlay during construction
        self._modal = ResolveModal(
            self.page, self.repo, self.settings,
            on_resolved=self._on_modal_resolved,
            on_deleted=self._on_modal_deleted,
        )

        self._refresh_list()
        return ft.Container(
            padding=24, expand=True,
            content=ft.Column(spacing=12, expand=True, controls=[
                ft.Row(controls=[
                    ft.Column(spacing=2, controls=[
                        ft.Text("Issues", size=28, weight=ft.FontWeight.W_800),
                        self.subtitle_text,
                    ]),
                    ft.Container(expand=True),
                    self._build_period_selector(),
                ]),
                ft.Row(spacing=10, controls=[
                    self._stat_pending, self._stat_resolved, self._stat_total,
                ]),
                ft.Container(expand=True, content=self.list_view),
            ]),
        )

    def _build_stat_chip(self, count: str, label: str, kind: str) -> ft.Container:
        """Pill-shaped chip showing a count + label, color-coded by kind.

        kind: "pending" | "resolved" | "total"
        """
        if kind == "pending":
            color = COLORS["late_severe"]
            bg = f"{COLORS['late_severe']}2E"  # ~18% alpha
        elif kind == "resolved":
            color = COLORS["resolved"]
            bg = f"{COLORS['resolved']}2E"
        else:
            color = COLORS["primary"]
            bg = f"{COLORS['primary']}2E"
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            border_radius=999,
            bgcolor=bg,
            border=ft.border.only(left=ft.BorderSide(2, color)),
            content=ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.Text(count, size=18, weight=ft.FontWeight.W_800, color=color),
                ft.Text(label, size=12, weight=ft.FontWeight.W_600, opacity=0.85),
            ]),
        )

    def _on_modal_resolved(self):
        """Called by ResolveModal after a successful save. Refresh list + stats."""
        self._refresh_list()
        if self.notify:
            self.notify("Issue resolved")
        if self.on_data_changed:
            self.on_data_changed()

    def _on_modal_deleted(self):
        """Called by ResolveModal after a successful delete. Refresh list + stats."""
        self._refresh_list()
        if self.notify:
            self.notify("Resolution dihapus")
        if self.on_data_changed:
            self.on_data_changed()
```

(Note: `ResolveModal` class is built in Tasks 6-9. For now this build code references it but the class is added later. To keep this task self-contained and tests passing, add a stub `ResolveModal` class at the bottom of `issues.py` for now.)

At the very bottom of `src/ui/pages/issues.py` (after the `IssuesPage` class), add:

```python
class ResolveModal:
    """Stub — fully built in Tasks 6-9. Just lets IssuesPage construct."""
    def __init__(self, page, repo, settings, on_resolved=None, on_deleted=None):
        self.page = page
        self.repo = repo
        self.settings = settings
        self.on_resolved = on_resolved
        self.on_deleted = on_deleted

    def open_for(self, issue: dict, edit_mode: bool = False) -> None:
        pass

    def close(self) -> None:
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/ui/test_issues_page.py -v`
Expected: PASS — 3 tests (stat counts come from `_refresh_list` which is built in Task 4. For now, `_refresh_list` will fail because it still references the old logic. **Skip this step — Task 4 will make tests pass.** Move to commit.)

Actually, `_refresh_list` was not yet replaced. So tests will fail with errors related to the OLD `_refresh_list`. Run instead:

Run: `python -m pytest tests/ui/test_issues_page.py::test_stat_chips_show_correct_counts -v`
Expected: FAIL — error from old `_refresh_list` (uses removed `selected_*` attributes or calls old method).

That's fine — Task 4 will fix `_refresh_list`. We commit Task 3 with the build method working but the tests pending.

Better approach: bundle Task 3 + Task 4 into one task to avoid this in-between state. **Continue to Task 4 first, THEN run tests, THEN commit both together.** See Task 4 for full integration.

For now, **don't commit Task 3 yet.** Move to Task 4.

---

## Task 4: List refactor with sections + new row builders

**Files:**
- Modify: `src/ui/pages/issues.py` — replace `_refresh_list`, add `_build_pending_row`, `_build_resolved_row`, helpers

This task lands together with Task 3's build() change, in a single commit.

- [ ] **Step 1: Add tests for sections + row content**

Append to `tests/ui/test_issues_page.py`:

```python
def test_list_has_pending_divider_first(page_with_data):
    p, _ = page_with_data
    # Filter to non-Container divider markers — find divider rows by their
    # cat-name child text content
    controls = p.list_view.controls
    # First control should be the "Belum Ditangani" divider
    pending_div = controls[0]
    # Drill into the divider to find the label text
    label_text = pending_div.content.controls[0].value
    assert "Belum Ditangani" in label_text


def test_pending_row_has_pending_status_badge(page_with_data):
    p, _ = page_with_data
    # Index 1 is first pending row (after divider at 0)
    row = p.list_view.controls[1]
    # Status badge is the last child in the row's Row content
    children = row.content.controls
    status_badge = children[-1]
    # Status text inside container
    status_text = status_badge.content.controls[-1].value
    assert "Pending" in status_text


def test_resolved_row_shows_alasan(page_with_data):
    p, _ = page_with_data
    # Find a resolved row by scanning controls for the resolved divider then next row
    controls = p.list_view.controls
    resolved_idx = None
    for i, c in enumerate(controls):
        try:
            if "Sudah Ditangani" in c.content.controls[0].value:
                resolved_idx = i
                break
        except (AttributeError, IndexError, TypeError):
            continue
    assert resolved_idx is not None
    resolved_row = controls[resolved_idx + 1]
    # Resolution text is in column index 2 of row's Row content (resolution slot)
    children = resolved_row.content.controls
    resolution_text = children[2].value
    assert "Cuti" in resolution_text or "✓" in resolution_text


def test_resolved_row_has_resolved_status_badge(page_with_data):
    p, _ = page_with_data
    controls = p.list_view.controls
    resolved_idx = None
    for i, c in enumerate(controls):
        try:
            if "Sudah Ditangani" in c.content.controls[0].value:
                resolved_idx = i
                break
        except (AttributeError, IndexError, TypeError):
            continue
    resolved_row = controls[resolved_idx + 1]
    status_badge = resolved_row.content.controls[-1]
    status_text = status_badge.content.controls[-1].value
    assert "Resolved" in status_text


def test_subtitle_shows_breakdown(page_with_data):
    p, _ = page_with_data
    assert "3 total" in p.subtitle_text.value
    assert "2 pending" in p.subtitle_text.value
    assert "1 resolved" in p.subtitle_text.value
```

- [ ] **Step 2: Replace `_refresh_list` and add row helpers**

In `src/ui/pages/issues.py`, find the existing `_refresh_list` (around line 86) and `_build_issue_row` (around line 103). Replace BOTH with the following block (delete the old `_build_issue_row` entirely, including its imports of `recommend`):

```python
    # Maps reason_code → friendly Indonesian label, used in resolution slot
    _RESOLUTION_LABELS = {
        "tugas_lapangan": "Lapangan",
        "tugas_paparan": "Paparan",
        "sakit": "Izin Sakit",
        "cuti": "Cuti",
        "izin_pagi": "Izin Pagi",
        "pulang_awal": "Pulang Lebih Awal",
        "telat_kerja": "Telat (kerja)",
        "telat_personal": "Terlambat",
        "lupa_absen": "Lupa Absen",
        "belum_kabar": "Belum Ada Kabar",
        "tidak_hadir": "Tidak Hadir",
    }

    def _refresh_list(self):
        from src.core.alasan_format import format_alasan
        self.list_view.controls.clear()
        issues = self.repo.list_issues_with_resolutions(
            self.start.isoformat(), self.end.isoformat(),
        )

        pending = [i for i in issues if i.get("reason_code") is None]
        resolved = [i for i in issues if i.get("reason_code") is not None]

        # Update stat chip counts (text inside count-text widget)
        self._set_chip_count(self._stat_pending, len(pending))
        self._set_chip_count(self._stat_resolved, len(resolved))
        self._set_chip_count(self._stat_total, len(issues))
        self.subtitle_text.value = (
            f"{len(issues)} total · {len(pending)} pending · "
            f"{len(resolved)} resolved · period {self.start} → {self.end}"
        )

        if not issues:
            self.list_view.controls.append(self._empty_state())
            return

        # Pending section
        self.list_view.controls.append(self._build_section_divider(
            "⚠️ Belum Ditangani", len(pending), "pending"))
        if pending:
            for issue in pending:
                self.list_view.controls.append(self._build_pending_row(issue))
        else:
            self.list_view.controls.append(self._section_empty(
                "Tidak ada issue pending minggu ini ✨"))

        # Resolved section
        self.list_view.controls.append(self._build_section_divider(
            "✅ Sudah Ditangani", len(resolved), "resolved"))
        if resolved:
            for issue in resolved:
                alasan = format_alasan(
                    issue.get("reason_code"), issue.get("location"),
                    issue.get("reason_detail"),
                )
                self.list_view.controls.append(self._build_resolved_row(issue, alasan))
        else:
            self.list_view.controls.append(self._section_empty(
                "Belum ada yang di-resolve di periode ini."))

    def _set_chip_count(self, chip: ft.Container, count: int) -> None:
        """Chip is Container > Row > [Text(count), Text(label)]."""
        chip.content.controls[0].value = str(count)

    def _build_section_divider(self, label: str, count: int, kind: str) -> ft.Control:
        if kind == "pending":
            chip_color = COLORS["late_severe"]
            chip_bg = f"{COLORS['late_severe']}2E"
        else:
            chip_color = COLORS["resolved"]
            chip_bg = f"{COLORS['resolved']}2E"
        return ft.Row(spacing=10, controls=[
            ft.Text(label, size=13, weight=ft.FontWeight.W_700,
                    color=COLORS["accent"]),
            ft.Container(
                padding=ft.padding.symmetric(horizontal=10, vertical=2),
                border_radius=999,
                bgcolor=chip_bg,
                content=ft.Text(str(count), size=11, weight=ft.FontWeight.W_800,
                                color=chip_color),
            ),
            ft.Container(expand=True, height=1,
                         gradient=ft.LinearGradient(
                             begin=ft.alignment.center_left,
                             end=ft.alignment.center_right,
                             colors=[f"{COLORS['accent']}55", "transparent"])),
        ])

    def _section_empty(self, msg: str) -> ft.Control:
        return ft.Container(
            padding=ft.padding.symmetric(vertical=14, horizontal=12),
            content=ft.Text(msg, size=12, italic=True, opacity=0.55),
        )

    def _empty_state(self) -> ft.Control:
        return ft.Container(
            padding=40, alignment=ft.alignment.center,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=48, color=COLORS["resolved"]),
                    ft.Text("Tidak ada issue di periode ini ✨", size=14),
                ]),
        )

    def _build_pending_row(self, issue: dict) -> ft.Control:
        case_label, case_color = CASE_LABELS.get(
            issue["issue_case"], (issue["issue_case"], "#999"))
        in_val = issue.get("actual_in") or "kosong"
        out_val = issue.get("actual_out") or "kosong"
        in_color = COLORS["resolved"] if issue.get("actual_in") else COLORS["late_severe"]
        out_color = COLORS["resolved"] if issue.get("actual_out") else COLORS["late_severe"]

        return ft.Container(
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border_radius=8,
            bgcolor=f"{COLORS['late_severe']}1A",
            border=ft.border.only(left=ft.BorderSide(3, COLORS["late_severe"])),
            on_click=lambda e, iss=issue: self._open_resolve_modal(iss, edit_mode=False),
            ink=True,
            content=ft.Row(spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                ft.Container(width=140, content=ft.Column(spacing=2, controls=[
                    ft.Text(issue["employee_name"], size=13, weight=ft.FontWeight.W_700),
                    ft.Text(f"{issue['date']} · {issue.get('day_name','')}",
                            size=10, opacity=0.7),
                ])),
                ft.Container(width=170, content=ft.Column(spacing=2, controls=[
                    ft.Row(spacing=4, controls=[
                        ft.Text("In:", size=11, opacity=0.55),
                        ft.Text(in_val, size=11, color=in_color,
                                font_family="Courier New", weight=ft.FontWeight.W_600),
                    ]),
                    ft.Row(spacing=4, controls=[
                        ft.Text("Out:", size=11, opacity=0.55),
                        ft.Text(out_val, size=11, color=out_color,
                                font_family="Courier New", weight=ft.FontWeight.W_600),
                    ]),
                ])),
                ft.Container(expand=True, content=ft.Text(
                    "— belum ditangani —",
                    size=11, italic=True, opacity=0.45,
                )),
                ft.Container(
                    width=110,
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    border_radius=8,
                    bgcolor=case_color,
                    content=ft.Text(case_label, color="white", size=10,
                                    weight=ft.FontWeight.W_700,
                                    text_align=ft.TextAlign.CENTER),
                ),
                ft.Container(
                    width=95,
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    border_radius=999,
                    bgcolor=f"{COLORS['late_severe']}2E",
                    border=ft.border.all(1, f"{COLORS['late_severe']}73"),
                    content=ft.Row(spacing=4,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    controls=[
                        ft.Text("⚠", size=10),
                        ft.Text("Pending", size=10, weight=ft.FontWeight.W_800,
                                color=COLORS["late_severe"]),
                    ]),
                ),
            ]),
        )

    def _build_resolved_row(self, issue: dict, alasan_text: str) -> ft.Control:
        case_label, case_color = CASE_LABELS.get(
            issue["issue_case"], (issue["issue_case"], "#999"))
        in_val = issue.get("actual_in") or "kosong"
        out_val = issue.get("actual_out") or "kosong"
        in_color = COLORS["resolved"] if issue.get("actual_in") else COLORS["late_severe"]
        out_color = COLORS["resolved"] if issue.get("actual_out") else COLORS["late_severe"]

        return ft.Container(
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border_radius=8,
            bgcolor=f"{COLORS['resolved']}10",
            border=ft.border.only(left=ft.BorderSide(3, COLORS["resolved"])),
            opacity=0.78,
            on_click=lambda e, iss=issue: self._open_resolve_modal(iss, edit_mode=True),
            ink=True,
            content=ft.Row(spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                ft.Container(width=140, content=ft.Column(spacing=2, controls=[
                    ft.Text(issue["employee_name"], size=13, weight=ft.FontWeight.W_700),
                    ft.Text(f"{issue['date']} · {issue.get('day_name','')}",
                            size=10, opacity=0.7),
                ])),
                ft.Container(width=170, content=ft.Column(spacing=2, controls=[
                    ft.Row(spacing=4, controls=[
                        ft.Text("In:", size=11, opacity=0.55),
                        ft.Text(in_val, size=11, color=in_color,
                                font_family="Courier New", weight=ft.FontWeight.W_600),
                    ]),
                    ft.Row(spacing=4, controls=[
                        ft.Text("Out:", size=11, opacity=0.55),
                        ft.Text(out_val, size=11, color=out_color,
                                font_family="Courier New", weight=ft.FontWeight.W_600),
                    ]),
                ])),
                ft.Text(f"✓ {alasan_text}", size=11, italic=True,
                        color=COLORS["resolved"], expand=True),
                ft.Container(
                    width=110,
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    border_radius=8,
                    bgcolor=case_color,
                    content=ft.Text(case_label, color="white", size=10,
                                    weight=ft.FontWeight.W_700,
                                    text_align=ft.TextAlign.CENTER),
                ),
                ft.Container(
                    width=95,
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    border_radius=999,
                    bgcolor=f"{COLORS['resolved']}2E",
                    border=ft.border.all(1, f"{COLORS['resolved']}73"),
                    content=ft.Row(spacing=4,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    controls=[
                        ft.Text("✓", size=10, color=COLORS["resolved"]),
                        ft.Text("Resolved", size=10, weight=ft.FontWeight.W_800,
                                color=COLORS["resolved"]),
                    ]),
                ),
            ]),
        )

    def _open_resolve_modal(self, issue: dict, edit_mode: bool) -> None:
        if self._modal:
            self._modal.open_for(issue, edit_mode=edit_mode)
```

Also DELETE the now-unused old methods (the existing `_build_issue_row`, `_build_resolve_panel`, `_select_issue`, `_select_reason`, `_save_resolution`, `_close_panel`, `_build_reason_button`, `_update_preview`). Find each in the file and remove. Also remove the now-unused `from src.core.resolver import (apply_resolution, list_all_reason_options, requires_extra_input)` import — those will be re-imported by ResolveModal in Task 6.

For now (until Task 6 builds the modal), import only what's still used:

```python
import flet as ft
from datetime import date, timedelta
from src.core.constants import COLORS
from src.db.repository import Repository
from src.core.settings_store import SettingsStore
```

Keep `CASE_LABELS` constant at module level.

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/ui/test_issues_page.py -v`
Expected: PASS — 8 tests (3 from Task 3 + 5 new from Task 4).

Run: `python -m pytest -q`
Expected: PASS — 119 passed (111 + 8), 6 skipped.

- [ ] **Step 4: Commit Tasks 3 + 4 together**

```bash
git add src/ui/pages/issues.py tests/ui/test_issues_page.py
git commit -m "feat(issues): list refactor — Pending/Resolved sections + stat chips"
```

---

## Task 5: ResolveModal — header + summary + footer skeleton

**Files:**
- Modify: `src/ui/pages/issues.py` — replace the stub `ResolveModal` with the real class

This task builds the modal's outer chrome (header, issue summary, footer) and basic open/close. Reason cards and edit logic come in Tasks 6-9.

- [ ] **Step 1: Add tests**

Append to `tests/ui/test_issues_page.py`:

```python
def test_modal_starts_hidden(page_with_data):
    p, _ = page_with_data
    assert p._modal is not None
    assert p._modal._dialog.visible is False


def test_modal_open_for_pending_issue_sets_state(page_with_data):
    p, _ = page_with_data
    issue = {
        "id": 1, "employee_name": "ALICE", "date": "2026-04-01",
        "day_name": "Rabu", "issue_case": "A", "actual_in": None, "actual_out": None,
        "reason_code": None,
    }
    p._modal.open_for(issue, edit_mode=False)
    assert p._modal._issue == issue
    assert p._modal._edit_mode is False
    assert p._modal._dialog.visible is True
    assert "ALICE" in p._modal._header_meta.value


def test_modal_close_hides_dialog(page_with_data):
    p, _ = page_with_data
    issue = {"id": 1, "employee_name": "X", "date": "2026-04-01",
             "day_name": "Rabu", "issue_case": "A",
             "actual_in": None, "actual_out": None, "reason_code": None}
    p._modal.open_for(issue)
    p._modal.close()
    assert p._modal._dialog.visible is False
```

- [ ] **Step 2: Replace stub ResolveModal**

In `src/ui/pages/issues.py`, find the stub `ResolveModal` class at the bottom and replace its full body with:

```python
class ResolveModal:
    """Centered 720px dialog for resolving / editing an Issue.

    Constructed once per IssuesPage; mounts itself onto page.overlay; toggles
    visibility via open_for() / close(). Keeps its widget tree alive across
    open/close cycles to avoid Flet's "control already added" issues.
    """

    def __init__(self, page: ft.Page, repo: Repository, settings: SettingsStore,
                 on_resolved=None, on_deleted=None):
        self.page = page
        self.repo = repo
        self.settings = settings
        self.on_resolved = on_resolved
        self.on_deleted = on_deleted

        # Per-open state
        self._issue: dict | None = None
        self._edit_mode = False
        self._selected_reason: str | None = None

        # Build widgets that we'll mutate later
        self._header_title = ft.Text("Resolve Issue", size=20,
                                      weight=ft.FontWeight.W_800)
        self._header_meta = ft.Text("", size=13, color=COLORS["accent"])
        self._summary_text = ft.Text("", size=14,
                                      font_family="Courier New")
        self._cancel_btn = ft.TextButton(
            "Cancel", on_click=lambda e: self.close(),
        )
        self._save_btn = ft.ElevatedButton(
            "Save Resolution", on_click=lambda e: self._save(),
            bgcolor=COLORS["resolved"], color="white", disabled=True,
        )
        self._delete_btn = ft.TextButton(
            "🗑 Delete Resolution",
            on_click=lambda e: self._confirm_delete(),
            visible=False,
            style=ft.ButtonStyle(color=COLORS["late_severe"]),
        )

        # Body placeholder (Tasks 6-7 will fill this)
        self._body_placeholder = ft.Column(spacing=12, controls=[])

        self._dialog = ft.Container(
            top=0, left=0, right=0, bottom=0,
            bgcolor=f"{COLORS['bg_dark']}C7",  # ~78% alpha dim
            visible=False,
            on_click=lambda e: None,  # absorb clicks on dim layer
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=720,
                        padding=0,
                        border_radius=16,
                        bgcolor=COLORS["surface_dark"],
                        border=ft.border.all(2, COLORS["primary"]),
                        content=ft.Column(spacing=0, controls=[
                            # Header
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=24,
                                                              vertical=18),
                                border=ft.border.only(bottom=ft.BorderSide(
                                    1, f"{COLORS['accent']}33")),
                                content=ft.Row(controls=[
                                    ft.Column(spacing=2, controls=[
                                        self._header_title,
                                        self._header_meta,
                                    ]),
                                    ft.Container(expand=True),
                                    ft.IconButton(
                                        ft.Icons.CLOSE,
                                        on_click=lambda e: self.close(),
                                    ),
                                ]),
                            ),
                            # Issue summary strip
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=24,
                                                              vertical=14),
                                bgcolor=f"{COLORS['late_severe']}14",
                                border=ft.border.only(bottom=ft.BorderSide(
                                    1, f"{COLORS['late_severe']}40")),
                                content=self._summary_text,
                            ),
                            # Body (reason cards, extra input, preview — Tasks 6-7)
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=24,
                                                              vertical=16),
                                content=self._body_placeholder,
                            ),
                            # Footer
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=24,
                                                              vertical=14),
                                border=ft.border.only(top=ft.BorderSide(
                                    1, f"{COLORS['accent']}33")),
                                content=ft.Row(controls=[
                                    self._delete_btn,
                                    ft.Container(expand=True),
                                    self._cancel_btn,
                                    self._save_btn,
                                ]),
                            ),
                        ]),
                    ),
                ],
            ),
        )
        page.overlay.append(self._dialog)

    def open_for(self, issue: dict, edit_mode: bool = False) -> None:
        self._issue = issue
        self._edit_mode = edit_mode
        self._selected_reason = issue.get("reason_code") if edit_mode else None

        case_label = CASE_LABELS.get(issue["issue_case"],
                                      (issue["issue_case"], "#999"))[0]
        self._header_meta.value = (
            f"{issue['employee_name']} · {issue['date']} "
            f"({issue.get('day_name','')}) · {case_label}"
        )
        in_val = issue.get("actual_in") or "kosong"
        out_val = issue.get("actual_out") or "kosong"
        self._summary_text.value = f"In: {in_val}     Out: {out_val}"

        self._delete_btn.visible = edit_mode
        self._save_btn.text = "Update Resolution" if edit_mode else "Save Resolution"
        self._save_btn.disabled = not edit_mode  # Tasks 7+ refine this

        self._dialog.visible = True
        try:
            self.page.update()
        except (AssertionError, AttributeError):
            pass

    def close(self) -> None:
        self._dialog.visible = False
        try:
            self.page.update()
        except (AssertionError, AttributeError):
            pass

    def _save(self) -> None:
        # Stub — Task 8 implements
        pass

    def _confirm_delete(self) -> None:
        # Stub — Task 8 implements
        pass
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/ui/test_issues_page.py -v`
Expected: PASS — 11 tests (8 prior + 3 new).

Run: `python -m pytest -q`
Expected: PASS — 122 passed, 6 skipped.

- [ ] **Step 4: Commit**

```bash
git add src/ui/pages/issues.py tests/ui/test_issues_page.py
git commit -m "feat(issues): ResolveModal skeleton (header, summary, open/close)"
```

---

## Task 6: ResolveModal — AI banner + reason cards in 4 categories

**Files:**
- Modify: `src/ui/pages/issues.py` — fill in `_body_placeholder` of `ResolveModal`

- [ ] **Step 1: Add tests**

Append to `tests/ui/test_issues_page.py`:

```python
def test_modal_body_has_ai_banner_text_after_open(page_with_data):
    p, _ = page_with_data
    issue = {"id": 1, "employee_name": "ALICE", "date": "2026-04-01",
             "day_name": "Rabu", "issue_case": "A",
             "actual_in": None, "actual_out": None, "reason_code": None}
    p._modal.open_for(issue, edit_mode=False)
    # AI banner suggestion text should mention something for case A
    assert p._modal._ai_suggestion_text.value != ""
    # Case A → suggestions include "Tidak Hadir" / "Cuti" / "Izin Sakit"
    assert any(word in p._modal._ai_suggestion_text.value
               for word in ("Tidak Hadir", "Cuti", "Izin Sakit"))


def test_modal_has_11_reason_cards(page_with_data):
    p, _ = page_with_data
    assert len(p._modal._reason_cards) == 11


def test_select_reason_marks_card_selected(page_with_data):
    p, _ = page_with_data
    issue = {"id": 1, "employee_name": "ALICE", "date": "2026-04-01",
             "day_name": "Rabu", "issue_case": "A",
             "actual_in": None, "actual_out": None, "reason_code": None}
    p._modal.open_for(issue, edit_mode=False)
    p._modal._select_reason("cuti")
    assert p._modal._selected_reason == "cuti"
    assert p._modal._reason_cards["cuti"].border.left.color == COLORS["accent"]
```

- [ ] **Step 2: Add AI hint mapping + reason categories + builder methods**

In `src/ui/pages/issues.py`, near the top after `CASE_LABELS`, add:

```python
# AI suggestion text for each issue case (was previously in src/core/issue_detector.recommend)
_AI_SUGGESTIONS = {
    "A": "Kemungkinan: Tidak Hadir, Cuti, atau Izin Sakit?",
    "B": "Kemungkinan: Lupa Absen Masuk, atau Izin Pagi?",
    "C": "Kemungkinan: Lupa Absen Pulang, atau Pulang Lebih Awal?",
    "F": "Kemungkinan: Pulang Lebih Awal dengan alasan?",
}

# Grouping of reason codes into 4 categories for the modal UI
_REASON_CATEGORIES = [
    ("Tugas (di luar kantor)", [
        ("tugas_lapangan", "Tugas Lapangan", "Field/site visit"),
        ("tugas_paparan", "Tugas Paparan", "Presentasi luar"),
    ]),
    ("Cuti / Sakit / Izin", [
        ("sakit", "Izin Sakit", "Sakit (tanpa input)"),
        ("cuti", "Cuti", "Cuti tahunan / besar"),
        ("izin_pagi", "Izin Pagi", "Datang siang, ada urusan"),
        ("pulang_awal", "Pulang Lebih Awal", "Keluar dini, ada urusan"),
    ]),
    ("Telat / Lupa Absen", [
        ("telat_kerja", "Masuk Terlambat (Pekerjaan)", "Krn meeting / urusan kerja"),
        ("telat_personal", "Terlambat (personal)", "Telat tanpa alasan kerja"),
        ("lupa_absen", "Lupa Absen", "+16 mnt penalty otomatis"),
    ]),
    ("Lain", [
        ("belum_kabar", "Belum Ada Kabar", "Sementara, blm tau alasan"),
        ("tidak_hadir", "Tidak Hadir", "Resmi tidak hadir"),
    ]),
]

# Codes that require extra input (mirror of resolver.requires_extra_input)
_REASON_NEEDS_INPUT = {
    "tugas_lapangan": "location",
    "tugas_paparan": "location",
    "izin_pagi": "reason_detail",
    "pulang_awal": "reason_detail",
    "telat_kerja": "reason_detail",
}
```

In the `ResolveModal.__init__`, after `self._body_placeholder = ft.Column(...)` line, add:

```python
        # AI banner widgets (mutable text)
        self._ai_label = ft.Text("AI MENYARANKAN", size=11,
                                  weight=ft.FontWeight.W_800,
                                  color=COLORS["primary"], opacity=0.85)
        self._ai_suggestion_text = ft.Text("", size=13)

        # Reason cards keyed by code (built once, mounted in body)
        self._reason_cards: dict[str, ft.Container] = {}
        self._build_reason_cards_into_body()
```

Then add the `_build_reason_cards_into_body` method (and `_build_reason_card` helper):

```python
    def _build_reason_cards_into_body(self) -> None:
        """Populate self._body_placeholder with AI banner + 4 categories."""
        # AI banner (top of body)
        ai_banner = ft.Container(
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border_radius=10,
            bgcolor=f"{COLORS['primary']}1A",
            border=ft.border.all(1, f"{COLORS['primary']}44"),
            content=ft.Row(spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                ft.Container(
                    width=32, height=32,
                    border_radius=8,
                    bgcolor=f"{COLORS['primary']}33",
                    alignment=ft.alignment.center,
                    content=ft.Text("🤖", size=16),
                ),
                ft.Column(spacing=2, controls=[
                    self._ai_label,
                    self._ai_suggestion_text,
                ]),
            ]),
        )

        body_label = ft.Text("PILIH ALASAN", size=11,
                              weight=ft.FontWeight.W_800,
                              color=COLORS["accent"],
                              opacity=0.85)

        category_widgets = []
        for cat_name, codes_in_cat in _REASON_CATEGORIES:
            cards_in_cat = []
            for code, label, hint in codes_in_cat:
                card = self._build_reason_card(code, label, hint)
                self._reason_cards[code] = card
                cards_in_cat.append(card)
            category_widgets.append(ft.Container(
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border_radius=10,
                bgcolor=f"{COLORS['surface_dark']}80",
                border=ft.border.all(1, f"{COLORS['accent']}33"),
                content=ft.Column(spacing=8, controls=[
                    ft.Text(cat_name.upper(), size=10,
                            weight=ft.FontWeight.W_800,
                            color=COLORS["accent"]),
                    ft.GridView(
                        runs_count=3,
                        max_extent=220,
                        spacing=8,
                        run_spacing=8,
                        child_aspect_ratio=2.4,
                        controls=cards_in_cat,
                    ),
                ]),
            ))

        self._body_placeholder.controls = [
            ai_banner,
            body_label,
            *category_widgets,
        ]

    def _build_reason_card(self, code: str, label: str, hint: str) -> ft.Container:
        needs_input = code in _REASON_NEEDS_INPUT
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=11, vertical=9),
            border_radius=8,
            bgcolor=f"{COLORS['primary']}1A",
            border=ft.border.only(left=ft.BorderSide(2, f"{COLORS['primary']}55")),
            on_click=lambda e, c=code: self._select_reason(c),
            ink=True,
            content=ft.Column(spacing=2, controls=[
                ft.Text(
                    f"{label}{' ✏️' if needs_input else ''}",
                    size=12, weight=ft.FontWeight.W_700,
                ),
                ft.Text(hint, size=10, color=COLORS["accent"], opacity=0.75),
            ]),
        )

    def _select_reason(self, code: str) -> None:
        self._selected_reason = code
        # Visual: highlight selected card, reset others
        for c, card in self._reason_cards.items():
            if c == code:
                card.bgcolor = f"{COLORS['accent']}33"
                card.border = ft.border.only(
                    left=ft.BorderSide(3, COLORS["accent"]))
            else:
                card.bgcolor = f"{COLORS['primary']}1A"
                card.border = ft.border.only(
                    left=ft.BorderSide(2, f"{COLORS['primary']}55"))
        # Tasks 7+: trigger extra-input visibility + save state + preview
        try:
            self._dialog.update()
        except (AssertionError, AttributeError):
            pass
```

In `open_for`, after `self._selected_reason = ...`, add:

```python
        # Update AI banner suggestion based on issue case
        self._ai_suggestion_text.value = _AI_SUGGESTIONS.get(
            issue["issue_case"], "")
        # Reset card highlight (clear previous open's selection state)
        for code, card in self._reason_cards.items():
            if code == self._selected_reason:
                card.bgcolor = f"{COLORS['accent']}33"
                card.border = ft.border.only(
                    left=ft.BorderSide(3, COLORS["accent"]))
            else:
                card.bgcolor = f"{COLORS['primary']}1A"
                card.border = ft.border.only(
                    left=ft.BorderSide(2, f"{COLORS['primary']}55"))
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/ui/test_issues_page.py -v`
Expected: PASS — 14 tests.

Run: `python -m pytest -q`
Expected: PASS — 125 passed, 6 skipped.

- [ ] **Step 4: Commit**

```bash
git add src/ui/pages/issues.py tests/ui/test_issues_page.py
git commit -m "feat(issues): ResolveModal AI banner + 4 reason categories"
```

---

## Task 7: ResolveModal — extra input + live preview + save-button state

**Files:**
- Modify: `src/ui/pages/issues.py`

- [ ] **Step 1: Add tests**

Append to `tests/ui/test_issues_page.py`:

```python
def test_select_reason_with_location_shows_extra_input(page_with_data):
    p, _ = page_with_data
    issue = {"id": 1, "employee_name": "ALICE", "date": "2026-04-01",
             "day_name": "Rabu", "issue_case": "A",
             "actual_in": None, "actual_out": None, "reason_code": None}
    p._modal.open_for(issue)
    p._modal._select_reason("tugas_lapangan")
    assert p._modal._extra_input_area.visible is True
    assert "Lokasi" in p._modal._extra_input_label.value


def test_select_reason_without_input_hides_extra_input(page_with_data):
    p, _ = page_with_data
    issue = {"id": 1, "employee_name": "ALICE", "date": "2026-04-01",
             "day_name": "Rabu", "issue_case": "A",
             "actual_in": None, "actual_out": None, "reason_code": None}
    p._modal.open_for(issue)
    p._modal._select_reason("cuti")
    assert p._modal._extra_input_area.visible is False


def test_save_button_disabled_until_input_filled(page_with_data):
    p, _ = page_with_data
    issue = {"id": 1, "employee_name": "ALICE", "date": "2026-04-01",
             "day_name": "Rabu", "issue_case": "A",
             "actual_in": None, "actual_out": None, "reason_code": None}
    p._modal.open_for(issue)
    p._modal._select_reason("tugas_lapangan")
    assert p._modal._save_btn.disabled is True
    p._modal._extra_input_field.value = "Surabaya"
    p._modal._update_save_btn_state()
    assert p._modal._save_btn.disabled is False


def test_save_button_enabled_for_no_input_reason(page_with_data):
    p, _ = page_with_data
    issue = {"id": 1, "employee_name": "ALICE", "date": "2026-04-01",
             "day_name": "Rabu", "issue_case": "A",
             "actual_in": None, "actual_out": None, "reason_code": None}
    p._modal.open_for(issue)
    p._modal._select_reason("cuti")
    assert p._modal._save_btn.disabled is False


def test_live_preview_updates_on_extra_input(page_with_data):
    p, _ = page_with_data
    issue = {"id": 1, "employee_name": "ALICE", "date": "2026-04-01",
             "day_name": "Rabu", "issue_case": "A",
             "actual_in": None, "actual_out": None, "reason_code": None}
    p._modal.open_for(issue)
    p._modal._select_reason("tugas_lapangan")
    p._modal._extra_input_field.value = "Surabaya"
    p._modal._update_live_preview()
    assert "Lapangan ke Surabaya" in p._modal._live_preview_text.value
```

- [ ] **Step 2: Add extra-input area + live-preview widgets + state-update methods**

In `ResolveModal.__init__`, after `self._build_reason_cards_into_body()`, add:

```python
        # Extra-input area (hidden by default; shown when reason needs input)
        self._extra_input_label = ft.Text("", size=11,
                                           weight=ft.FontWeight.W_800,
                                           color=COLORS["accent"])
        self._extra_input_field = ft.TextField(
            label="", hint_text="", expand=True,
            on_change=lambda e: self._on_extra_input_change(),
        )
        self._extra_input_hint = ft.Text(
            "Field wajib diisi sebelum Save.",
            size=10, color=COLORS["accent"], opacity=0.7,
        )
        self._extra_input_area = ft.Container(
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            border_radius=10,
            bgcolor=f"{COLORS['accent']}14",
            border=ft.border.all(1, f"{COLORS['accent']}55"),
            visible=False,
            content=ft.Column(spacing=6, controls=[
                self._extra_input_label,
                self._extra_input_field,
                self._extra_input_hint,
            ]),
        )

        # Live preview strip
        self._live_preview_text = ft.Text("", size=12, italic=True,
                                           color=COLORS["resolved"])
        self._live_preview_area = ft.Container(
            padding=ft.padding.symmetric(horizontal=12, vertical=9),
            border_radius=6,
            bgcolor=f"{COLORS['resolved']}14",
            border=ft.border.only(left=ft.BorderSide(3, COLORS["resolved"])),
            visible=False,
            content=ft.Row(spacing=6, controls=[
                ft.Text("Preview di Main DB:", size=11, weight=ft.FontWeight.W_700,
                        color=COLORS["resolved"], opacity=0.85),
                self._live_preview_text,
            ]),
        )

        # Append to body placeholder so they appear below reason categories
        self._body_placeholder.controls.append(self._extra_input_area)
        self._body_placeholder.controls.append(self._live_preview_area)
```

Update `_select_reason` to also handle extra-input visibility, save-button state, and live preview. Replace the existing `_select_reason` body with:

```python
    def _select_reason(self, code: str) -> None:
        self._selected_reason = code
        # Visual: highlight selected card, reset others
        for c, card in self._reason_cards.items():
            if c == code:
                card.bgcolor = f"{COLORS['accent']}33"
                card.border = ft.border.only(
                    left=ft.BorderSide(3, COLORS["accent"]))
            else:
                card.bgcolor = f"{COLORS['primary']}1A"
                card.border = ft.border.only(
                    left=ft.BorderSide(2, f"{COLORS['primary']}55"))

        # Extra-input area visibility + label
        extra_kind = _REASON_NEEDS_INPUT.get(code)
        if extra_kind == "location":
            self._extra_input_area.visible = True
            self._extra_input_label.value = "📍 LOKASI *"
            self._extra_input_field.label = "Lokasi"
            self._extra_input_field.hint_text = "Misal: Kantor Klien Surabaya, Site PT XYZ"
        elif extra_kind == "reason_detail":
            self._extra_input_area.visible = True
            self._extra_input_label.value = "✏️ ALASAN DETAIL *"
            self._extra_input_field.label = "Alasan detail"
            self._extra_input_field.hint_text = "Singkat alasan kenapa terjadi"
        else:
            self._extra_input_area.visible = False
            self._extra_input_field.value = ""

        # Live preview area visible whenever a reason is picked
        self._live_preview_area.visible = True
        self._update_live_preview()
        self._update_save_btn_state()
        try:
            self._dialog.update()
        except (AssertionError, AttributeError):
            pass

    def _on_extra_input_change(self) -> None:
        self._update_live_preview()
        self._update_save_btn_state()
        try:
            self._dialog.update()
        except (AssertionError, AttributeError):
            pass

    def _update_live_preview(self) -> None:
        from src.core.alasan_format import format_alasan
        if self._selected_reason is None:
            self._live_preview_text.value = ""
            return
        extra = _REASON_NEEDS_INPUT.get(self._selected_reason)
        location = self._extra_input_field.value if extra == "location" else None
        reason_detail = self._extra_input_field.value if extra == "reason_detail" else None
        self._live_preview_text.value = format_alasan(
            self._selected_reason, location, reason_detail,
        )

    def _update_save_btn_state(self) -> None:
        if self._selected_reason is None:
            self._save_btn.disabled = True
            return
        extra = _REASON_NEEDS_INPUT.get(self._selected_reason)
        if extra and not (self._extra_input_field.value or "").strip():
            self._save_btn.disabled = True
        else:
            self._save_btn.disabled = False
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/ui/test_issues_page.py -v`
Expected: PASS — 19 tests.

Run: `python -m pytest -q`
Expected: PASS — 130 passed, 6 skipped.

- [ ] **Step 4: Commit**

```bash
git add src/ui/pages/issues.py tests/ui/test_issues_page.py
git commit -m "feat(issues): ResolveModal extra input + live preview + save state"
```

---

## Task 8: ResolveModal — save + edit-mode pre-fill + delete

**Files:**
- Modify: `src/ui/pages/issues.py`

- [ ] **Step 1: Add tests**

Append to `tests/ui/test_issues_page.py`:

```python
def test_save_calls_apply_resolution_and_callback(page_with_data):
    p, repo = page_with_data
    # Find an existing pending record
    rows = repo.list_issues_with_resolutions("2026-03-30", "2026-04-05")
    pending = next(r for r in rows if r["reason_code"] is None)

    callback_fired = []
    p._modal.on_resolved = lambda: callback_fired.append(True)

    p._modal.open_for(pending, edit_mode=False)
    p._modal._select_reason("cuti")
    p._modal._save()

    # Resolution row was created in DB
    after = repo.get_resolution(pending["id"])
    assert after is not None
    assert after["reason_code"] == "cuti"
    # on_resolved callback fired
    assert callback_fired == [True]
    # Modal closed
    assert p._modal._dialog.visible is False


def test_edit_mode_prefills_reason_and_extra(page_with_data):
    p, repo = page_with_data
    rows = repo.list_issues_with_resolutions("2026-03-30", "2026-04-05")
    resolved = next(r for r in rows if r["reason_code"] is not None)
    # Update with location to test pre-fill
    repo.upsert_resolution(resolved["id"], reason_code="tugas_lapangan",
                           location="Surabaya")
    refreshed = repo.list_issues_with_resolutions("2026-03-30", "2026-04-05")
    issue = next(r for r in refreshed if r["id"] == resolved["id"])

    p._modal.open_for(issue, edit_mode=True)
    assert p._modal._selected_reason == "tugas_lapangan"
    assert p._modal._extra_input_field.value == "Surabaya"
    assert p._modal._extra_input_area.visible is True
    assert p._modal._delete_btn.visible is True
    assert p._modal._save_btn.text == "Update Resolution"


def test_delete_calls_delete_resolution_and_callback(page_with_data, monkeypatch):
    p, repo = page_with_data
    rows = repo.list_issues_with_resolutions("2026-03-30", "2026-04-05")
    resolved = next(r for r in rows if r["reason_code"] is not None)

    deleted_callback = []
    p._modal.on_deleted = lambda: deleted_callback.append(True)

    # Bypass confirmation by directly calling the delete worker
    p._modal.open_for(resolved, edit_mode=True)
    p._modal._do_delete()  # internal method, skips dialog

    assert repo.get_resolution(resolved["id"]) is None
    assert deleted_callback == [True]
```

- [ ] **Step 2: Implement save + edit-mode prefill + delete flow**

In `ResolveModal.open_for`, after the existing block, add a pre-fill step. Find the line `self._save_btn.disabled = not edit_mode  # Tasks 7+ refine this` and replace the surrounding block (from `self._delete_btn.visible = ...` through end of `open_for`) with:

```python
        self._delete_btn.visible = edit_mode
        self._save_btn.text = "Update Resolution" if edit_mode else "Save Resolution"

        # Pre-fill from existing resolution if edit mode
        if edit_mode and issue.get("reason_code"):
            self._extra_input_field.value = (
                issue.get("location") or issue.get("reason_detail") or ""
            )
            self._select_reason(issue["reason_code"])
        else:
            self._extra_input_field.value = ""
            # Hide extra/preview until user picks
            self._extra_input_area.visible = False
            self._live_preview_area.visible = False
            self._save_btn.disabled = True

        self._dialog.visible = True
        try:
            self.page.update()
        except (AssertionError, AttributeError):
            pass
```

(Remove the duplicate `self._dialog.visible = True` and `page.update()` block lower in `open_for` if any — should now appear only at the end.)

Replace the stub `_save` and `_confirm_delete`:

```python
    def _save(self) -> None:
        from src.core.resolver import apply_resolution
        if self._issue is None or self._selected_reason is None:
            return
        kwargs = {}
        extra = _REASON_NEEDS_INPUT.get(self._selected_reason)
        if extra == "location":
            kwargs["location"] = self._extra_input_field.value or ""
        elif extra == "reason_detail":
            kwargs["reason_detail"] = self._extra_input_field.value or ""
        kwargs["penalty_minutes"] = self.settings.get("lupa_absen_penalty_minutes")
        apply_resolution(self.repo, self._issue["id"],
                          self._selected_reason, **kwargs)
        self.close()
        if self.on_resolved:
            self.on_resolved()

    def _confirm_delete(self) -> None:
        # Build a small confirmation AlertDialog and show via page.overlay.
        # Bypass the dialog by calling _do_delete() directly in tests.
        if self._issue is None:
            return
        confirm = ft.AlertDialog(
            modal=True,
            title=ft.Text("Hapus resolution?"),
            content=ft.Text(
                f"Resolution untuk {self._issue['employee_name']} "
                f"({self._issue['date']}) akan dihapus dan kembali ke Pending."
            ),
            actions=[
                ft.TextButton("Batal", on_click=lambda e: self._dismiss_confirm(confirm)),
                ft.ElevatedButton(
                    "Hapus", on_click=lambda e: (self._dismiss_confirm(confirm),
                                                  self._do_delete()),
                    bgcolor=COLORS["late_severe"], color="white",
                ),
            ],
        )
        self.page.overlay.append(confirm)
        confirm.open = True
        try:
            self.page.update()
        except (AssertionError, AttributeError):
            pass

    def _dismiss_confirm(self, confirm: ft.AlertDialog) -> None:
        confirm.open = False
        try:
            self.page.update()
        except (AssertionError, AttributeError):
            pass

    def _do_delete(self) -> None:
        if self._issue is None:
            return
        self.repo.delete_resolution(self._issue["id"])
        self.close()
        if self.on_deleted:
            self.on_deleted()
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/ui/test_issues_page.py -v`
Expected: PASS — 22 tests.

Run: `python -m pytest -q`
Expected: PASS — 133 passed, 6 skipped.

- [ ] **Step 4: Commit**

```bash
git add src/ui/pages/issues.py tests/ui/test_issues_page.py
git commit -m "feat(issues): ResolveModal save + edit-mode + delete-with-confirm"
```

---

## Task 9: Period selector + week-shift refresh

**Files:**
- Modify: `src/ui/pages/issues.py` — keep existing `_build_period_selector` + `_shift_week` + `_schedule_refresh` working with the new `_refresh_list`

The existing methods still reference correct attributes (`self.start`, `self.end`, `self.list_view`, `self.period_text`). Just verify they still work after the rest of the refactor.

- [ ] **Step 1: Audit existing period methods**

Run a quick grep:

```bash
grep -n "def _build_period_selector\|def _shift_week\|def _schedule_refresh\|def _period_label" src/ui/pages/issues.py
```

If any of these were accidentally deleted in Tasks 3-8, restore them. Their logic doesn't change. Reference (current implementation in pre-refactor file):

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

- [ ] **Step 2: Add a smoke test for week shift**

Append to `tests/ui/test_issues_page.py`:

```python
def test_shift_week_updates_period(page_with_data):
    p, _ = page_with_data
    old_start = p.start
    p._shift_week(1)
    from datetime import timedelta
    assert p.start == old_start + timedelta(weeks=1)
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/ui/test_issues_page.py -v`
Expected: PASS — 23 tests.

Run: `python -m pytest -q`
Expected: PASS — 134 passed, 6 skipped.

- [ ] **Step 4: Commit**

```bash
git add src/ui/pages/issues.py tests/ui/test_issues_page.py
git commit -m "feat(issues): verify period nav + shift-week refresh hooks new list"
```

---

## Task 10: Manual smoke test + version bump + .exe rebuild + push

**Files:**
- Modify: `scripts/build_exe.py` (PRODUCT_VERSION)
- Build artifact: `dist/JosaphatTechHR.exe`

- [ ] **Step 1: Run full pytest one last time**

Run: `python -m pytest -q`
Expected: PASS — 134 passed, 6 skipped, 1 deprecation warning (reportlab — pre-existing).

- [ ] **Step 2: Manual smoke test in dev mode**

Run: `python main.py`

Verify in the running app:

1. **List rendering**
   - Import April .xls if needed (Import page)
   - Navigate to Issues → arrow ◀◀◀ until you reach the imported April week
   - Pending section appears at top with the right count chip
   - Resolved section below (or "Belum ada yang di-resolve di periode ini." if empty)
   - Stat chips at top show correct counts: e.g. "12 Pending · 0 Resolved · 12 Total"
2. **Resolve flow (pending → resolved)**
   - Click any Pending row → modal opens centered, dim layer behind
   - AI banner shows a suggestion like "Kemungkinan: Tidak Hadir, Cuti, atau Izin Sakit?"
   - Pick "Cuti" → live preview shows "Cuti", Save button enables
   - Pick "Tugas Lapangan" → extra input area appears with "📍 LOKASI *" label, Save disabled
   - Type "Surabaya" in the field → Save enables, live preview shows "Lapangan ke Surabaya"
   - Click Save → modal closes, success toast, row moves to Resolved section
3. **Edit flow (resolved → re-edit)**
   - Click the same row again (now in Resolved) → modal reopens, pre-filled with "Tugas Lapangan" + "Surabaya", Delete button visible at bottom-left, button label "Update Resolution"
   - Change to "Cuti" → extra-input area hides, Save still enabled, label still "Update Resolution"
   - Click Update Resolution → row updates with new alasan
4. **Delete flow**
   - Click another resolved row → modal opens
   - Click 🗑 Delete Resolution → confirmation dialog appears
   - Click "Hapus" → modal closes, row moves back to Pending
5. **Stats stay in sync** at all times: the chip counts update immediately after Save / Delete

- [ ] **Step 3: Bump PRODUCT_VERSION**

Open `scripts/build_exe.py`. Find the line:

```python
PRODUCT_VERSION = "2.1.0"
```

Replace with:

```python
PRODUCT_VERSION = "2.2.0"
```

- [ ] **Step 4: Rebuild .exe**

Run: `python scripts/build_exe.py`
Expected output ends with: `Build OK: ...\dist\JosaphatTechHR.exe (~98 MB)`

- [ ] **Step 5: Copy .exe to main repo dist**

Run: `cp ".claude/worktrees/nice-tesla-c616f6/dist/JosaphatTechHR.exe" "../../../dist/JosaphatTechHR.exe"`
Verify the timestamp on `D:\Gawe\Project X\Human Resource App\dist\JosaphatTechHR.exe` updates.

- [ ] **Step 6: Commit version bump**

```bash
git add scripts/build_exe.py
git commit -m "chore(build): bump PRODUCT_VERSION to 2.2.0 (Issues redesign)"
```

- [ ] **Step 7: Tag + push (only after user confirms manual smoke test passed)**

Wait for user confirmation, then:

```bash
git push origin claude/nice-tesla-c616f6:master
git tag v2.2.0
git push origin v2.2.0
```

---

## Self-Review Checklist (run before handoff)

- [ ] **Spec coverage:**
  - Section 2 list & sort → Tasks 3, 4 ✓
  - Section 3.1 stat chips → Task 3 ✓
  - Section 3.2 dividers → Task 4 ✓
  - Section 3.3 row layouts → Task 4 ✓
  - Section 3.4 modal structure → Tasks 5, 6, 7, 8 ✓
  - Section 4 repo method → Task 1 ✓
  - Section 5 UX flows (resolve, re-edit, delete) → Tasks 7, 8, 10 ✓
  - Section 6 file changes → all ✓
  - Section 8 tests → spread across tasks 1, 3-9 ✓

- [ ] **Placeholder scan:** No "TBD" / "TODO" / "similar to Task N" in step bodies. Each step has full code or full command + expected output.

- [ ] **Type consistency:**
  - `ResolveModal.__init__(self, page, repo, settings, on_resolved=None, on_deleted=None)` — same in Tasks 5, 6, 7, 8 ✓
  - `open_for(issue, edit_mode=False)` — same in Tasks 5, 8 ✓
  - `_select_reason(code)` — same signature in Tasks 6, 7 ✓
  - `_REASON_NEEDS_INPUT` keys ("location" / "reason_detail") — used consistently in Tasks 6, 7, 8 ✓
  - `_REASON_CATEGORIES` structure (cat_name, [(code, label, hint), ...]) — consistent in Tasks 6 ✓

- [ ] **Threading correctness:** No new threading introduced (Issues page already uses Timer for `_schedule_refresh`; new modal is fully synchronous because it just toggles widget state).

---

## Notes for Implementation

**Why ResolveModal lives inside `issues.py`?** It's a single-consumer component. Promoting to its own file (`src/ui/components/resolve_modal.py`) is fine if a second use-case ever emerges, but for now scope discipline says keep it where the consumer is.

**Why pre-fill via `_select_reason` in edit mode?** That single method handles all the cascade (visual highlight + extra-input visibility + live preview + save-button state). Calling it instead of duplicating the cascade keeps logic DRY and reduces bug surface.

**Why `_do_delete` separate from `_confirm_delete`?** Tests can call `_do_delete` directly to bypass the AlertDialog (which requires Flet runtime). Production code goes `_confirm_delete → AlertDialog → user clicks Hapus → _do_delete`.

**Why error handling on `page.update()`?** The page may be unmounted (user navigated away mid-modal) by the time the update fires from a non-UI thread (e.g., `_schedule_refresh` Timer). Existing pattern in v2.1.0 wraps these in try/except `(AssertionError, AttributeError)`.

**`format_alasan` import inside methods, not at module top:** Avoids a circular-import risk if `src/core/alasan_format.py` ever pulls in something from UI layer.
