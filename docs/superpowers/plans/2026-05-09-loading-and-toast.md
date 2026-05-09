# Loading Indicators & Toast Notifications Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a top-of-screen loading strip (with click-blocking dim) for long operations, and a top-right toast notifier for success/error feedback on every operation in the HR Attendance Manager.

**Architecture:** Two singleton UI components (`LoadingOverlay`, `ToastNotifier`) are mounted into `page.overlay` from `Shell.__init__`. Shell exposes three delegate methods (`show_loading`, `hide_loading`, `notify`) and threads them as keyword callbacks into every page builder. Long-running operations wrap their work in a `threading.Thread` so the UI thread can repaint the loading overlay before the work begins.

**Tech Stack:** Flet 0.25.2 (overlay/Container/Stack/AnimatedSwitcher), Python `threading` (Thread + Timer), pytest 8.3.3 + pytest's `monkeypatch` for timer mocking.

**Spec:** [docs/superpowers/specs/2026-05-09-loading-and-toast.md](../specs/2026-05-09-loading-and-toast.md)
**Mockup:** [mockups/08-loading-and-toast.html](../../../mockups/08-loading-and-toast.html)

---

## File Structure

**New files (5):**
- `src/ui/components/loading_overlay.py` — `LoadingOverlay` class (~50 lines)
- `src/ui/components/toast.py` — `ToastNotifier` class (~80 lines)
- `tests/ui/test_loading_overlay.py` — show/hide/label tests
- `tests/ui/test_toast.py` — success/error/dismiss/stack-overflow tests
- `tests/ui/test_shell_loading_toast.py` — Shell wiring tests

**Modified files (8):**
- `src/ui/shell.py` — instantiate components + add delegates + thread callbacks into all builders
- `src/ui/pages/issues.py` — toast on `_save_resolution`
- `src/ui/pages/settings.py` — toast on `_save_all`
- `src/ui/pages/edit_records.py` — toast on save dialog
- `src/ui/pages/main_database.py` — loading on `_export_xlsx` (threaded) + toast on `_copy_tsv`
- `src/ui/pages/import_data.py` — loading + toast + threading on `_do_import`
- `src/ui/pages/weekly_report.py` — loading + toast + threading on PDF + Excel exports
- `src/ui/pages/monthly_report.py` — same as weekly
- `src/ui/pages/backup_restore.py` — loading + toast + threading on export + import
- `tests/ui/test_shell_cache.py` — small update so existing tests pass alongside new wiring

Each file has one focused responsibility; the components are isolated from page-specific logic, and the Shell is the only place that knows about both.

---

## Task 1: LoadingOverlay component

**Files:**
- Create: `src/ui/components/loading_overlay.py`
- Test: `tests/ui/test_loading_overlay.py`

- [ ] **Step 1: Write failing tests**

Create `tests/ui/test_loading_overlay.py`:

```python
"""Tests for the LoadingOverlay component (top progress strip + dim).

We mock the Flet page so tests run without a Flet runtime; the overlay's
behavior is observable through the property values it sets on its widgets.
"""
from unittest.mock import MagicMock
from src.ui.components.loading_overlay import LoadingOverlay


def _make_overlay():
    page = MagicMock()
    page.overlay = []
    return LoadingOverlay(page), page


def test_init_appends_two_overlay_items_hidden():
    overlay, page = _make_overlay()
    # The dim layer + the strip — two separate page.overlay entries
    assert len(page.overlay) == 2
    assert overlay.dim.visible is False
    assert overlay.strip.visible is False


def test_show_sets_visible_and_label():
    overlay, _ = _make_overlay()
    overlay.show("Sedang import...")
    assert overlay.dim.visible is True
    assert overlay.strip.visible is True
    assert overlay.label.value == "Sedang import..."


def test_hide_restores_invisible():
    overlay, _ = _make_overlay()
    overlay.show("Anything")
    overlay.hide()
    assert overlay.dim.visible is False
    assert overlay.strip.visible is False


def test_repeat_show_updates_label():
    overlay, _ = _make_overlay()
    overlay.show("First op")
    overlay.show("Second op")
    assert overlay.label.value == "Second op"
    assert overlay.strip.visible is True


def test_dim_layer_absorbs_clicks():
    overlay, _ = _make_overlay()
    # The dim Container must have an on_click handler so Flet absorbs the
    # pointer event instead of letting it pass through to the sidebar.
    assert overlay.dim.on_click is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/ui/test_loading_overlay.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.ui.components.loading_overlay'`

- [ ] **Step 3: Write minimal implementation**

Create `src/ui/components/loading_overlay.py`:

```python
"""Top progress strip + dim layer that blocks clicks during long operations.

Mounted as two separate items in `page.overlay` (dim layer + top strip).
Both are toggled together via `show(label)` / `hide()`.
"""
import flet as ft

from src.core.constants import COLORS


class LoadingOverlay:
    def __init__(self, page: ft.Page):
        self.page = page
        self.label = ft.Text("", size=12, weight=ft.FontWeight.W_600,
                             color=COLORS["text_dark"])
        self.bar = ft.ProgressBar(expand=True, height=4,
                                   color=COLORS["accent"],
                                   bgcolor=f"{COLORS['primary']}33")

        # Dim layer fills the entire page so clicks (including sidebar nav) are absorbed.
        self.dim = ft.Container(
            top=0, left=0, right=0, bottom=0,
            bgcolor=f"{COLORS['bg_dark']}73",  # ~45% alpha
            on_click=lambda e: None,            # absorb clicks
            visible=False,
        )

        # Top strip with label + indeterminate progress bar.
        self.strip = ft.Container(
            top=0, left=0, right=0,
            bgcolor=f"{COLORS['surface_dark']}F2",  # ~95% alpha
            border=ft.border.only(bottom=ft.BorderSide(1, COLORS["primary"])),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            content=ft.Row(spacing=12, controls=[self.label, self.bar]),
            visible=False,
        )

        page.overlay.append(self.dim)
        page.overlay.append(self.strip)

    def show(self, label_text: str) -> None:
        self.label.value = label_text
        self.dim.visible = True
        self.strip.visible = True
        try:
            self.page.update()
        except (AssertionError, AttributeError):
            pass  # page not yet mounted (first paint) — safe to ignore

    def hide(self) -> None:
        self.dim.visible = False
        self.strip.visible = False
        try:
            self.page.update()
        except (AssertionError, AttributeError):
            pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/ui/test_loading_overlay.py -v`
Expected: PASS — 5 tests

- [ ] **Step 5: Commit**

```bash
git add src/ui/components/loading_overlay.py tests/ui/test_loading_overlay.py
git commit -m "feat(ui): LoadingOverlay component (top strip + click-blocking dim)"
```

---

## Task 2: ToastNotifier component

**Files:**
- Create: `src/ui/components/toast.py`
- Test: `tests/ui/test_toast.py`

- [ ] **Step 1: Write failing tests**

Create `tests/ui/test_toast.py`:

```python
"""Tests for the ToastNotifier component (top-right stacked toasts).

threading.Timer is monkey-patched per-test so dismiss timers don't sleep
during the test run; the test invokes the captured timer function directly
to simulate timer firing.
"""
from unittest.mock import MagicMock

import pytest

from src.core.constants import COLORS
from src.ui.components.toast import ToastNotifier


@pytest.fixture
def captured_timers(monkeypatch):
    """Capture every threading.Timer; tests can fire them on demand."""
    fired = []
    class FakeTimer:
        def __init__(self, interval, fn):
            self.interval = interval
            self.fn = fn
        def start(self):
            fired.append(self)
        @property
        def daemon(self):
            return True
        @daemon.setter
        def daemon(self, _v):
            pass
    monkeypatch.setattr("src.ui.components.toast.threading.Timer", FakeTimer)
    return fired


@pytest.fixture
def notifier():
    page = MagicMock()
    page.overlay = []
    return ToastNotifier(page)


def test_init_mounts_one_container_in_overlay(notifier):
    assert notifier.container in notifier.page.overlay
    assert notifier.container.top == 80
    assert notifier.container.right == 20
    assert notifier.container.width == 280


def test_success_appends_toast_with_green_border(notifier, captured_timers):
    notifier.success("Done", "All good")
    assert len(notifier.stack.controls) == 1
    toast = notifier.stack.controls[0]
    assert toast.border.left.color == COLORS["resolved"]


def test_error_appends_toast_with_red_border(notifier, captured_timers):
    notifier.error("Boom", "It broke")
    toast = notifier.stack.controls[0]
    assert toast.border.left.color == COLORS["late_severe"]


def test_success_dismisses_after_1500ms(notifier, captured_timers):
    notifier.success("Done")
    assert captured_timers[0].interval == 1.5


def test_error_dismisses_after_3000ms(notifier, captured_timers):
    notifier.error("Boom")
    assert captured_timers[0].interval == 3.0


def test_dismiss_removes_toast_from_stack(notifier, captured_timers):
    notifier.success("Done")
    assert len(notifier.stack.controls) == 1
    captured_timers[0].fn()  # fire the dismiss timer
    assert len(notifier.stack.controls) == 0


def test_max_3_toasts_evicts_oldest(notifier, captured_timers):
    notifier.success("First")
    notifier.success("Second")
    notifier.success("Third")
    notifier.success("Fourth")  # should evict First
    assert len(notifier.stack.controls) == 3
    # Surviving toasts: Second, Third, Fourth
    titles = [_first_text(c) for c in notifier.stack.controls]
    assert titles == ["Second", "Third", "Fourth"]


def test_toast_without_desc_omits_second_text_line(notifier, captured_timers):
    notifier.success("OnlyTitle")  # no desc
    toast = notifier.stack.controls[0]
    column = toast.content.controls[1]  # Row -> [Icon, Column]
    assert len(column.controls) == 1  # title only, no desc line


def _first_text(toast_container):
    """Helper: extract the title text from a built toast Container."""
    column = toast_container.content.controls[1]  # Row -> [Icon, Column]
    return column.controls[0].value
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/ui/test_toast.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.ui.components.toast'`

- [ ] **Step 3: Write minimal implementation**

Create `src/ui/components/toast.py`:

```python
"""Top-right stacked toast notifier (success / error).

Mounted as a single positioned Container in `page.overlay`; the Container
holds a Column whose children are individual toast Containers. Each toast
self-dismisses via threading.Timer (1.5s for success, 3.0s for error).
"""
import threading

import flet as ft

from src.core.constants import COLORS

_MAX_VISIBLE = 3
_DISMISS_SUCCESS_S = 1.5
_DISMISS_ERROR_S = 3.0


class ToastNotifier:
    def __init__(self, page: ft.Page):
        self.page = page
        self.stack = ft.Column(spacing=8)
        self.container = ft.Container(
            top=80, right=20, width=280,
            content=self.stack,
        )
        page.overlay.append(self.container)

    def success(self, title: str, desc: str = "") -> None:
        self._add_toast(title, desc, COLORS["resolved"], "✅",
                        duration=_DISMISS_SUCCESS_S)

    def error(self, title: str, desc: str = "") -> None:
        self._add_toast(title, desc, COLORS["late_severe"], "❌",
                        duration=_DISMISS_ERROR_S)

    def _add_toast(self, title: str, desc: str, color: str,
                   icon: str, duration: float) -> None:
        # Evict oldest if we're already at the visible cap
        while len(self.stack.controls) >= _MAX_VISIBLE:
            self.stack.controls.pop(0)

        toast = self._build_toast(title, desc, color, icon)
        self.stack.controls.append(toast)
        self._safe_update()

        timer = threading.Timer(duration, lambda: self._dismiss(toast))
        timer.daemon = True
        timer.start()

    def _build_toast(self, title: str, desc: str,
                     color: str, icon: str) -> ft.Container:
        body_controls = [ft.Text(title, size=13, weight=ft.FontWeight.W_700,
                                  color=COLORS["text_dark"])]
        if desc:
            body_controls.append(ft.Text(desc, size=11, opacity=0.8,
                                          color=COLORS["text_dark"]))

        return ft.Container(
            bgcolor=f"{COLORS['surface_dark']}D1",  # ~82% alpha
            border=ft.border.only(left=ft.BorderSide(3, color)),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            content=ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(icon, size=16),
                    ft.Column(spacing=2, controls=body_controls),
                ],
            ),
        )

    def _dismiss(self, toast: ft.Container) -> None:
        if toast in self.stack.controls:
            self.stack.controls.remove(toast)
            self._safe_update()

    def _safe_update(self) -> None:
        try:
            self.stack.update()
        except (AssertionError, AttributeError):
            pass  # not mounted yet (initial paint) or already disposed
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/ui/test_toast.py -v`
Expected: PASS — 8 tests

- [ ] **Step 5: Commit**

```bash
git add src/ui/components/toast.py tests/ui/test_toast.py
git commit -m "feat(ui): ToastNotifier component (top-right, stacked, kind-aware duration)"
```

---

## Task 3: Wire components into Shell + delegate methods

**Files:**
- Modify: `src/ui/shell.py`
- Test: `tests/ui/test_shell_loading_toast.py`
- Modify: `tests/ui/test_shell_cache.py` (add overlay attr to MagicMock)

- [ ] **Step 1: Update existing test_shell_cache.py fixture so MagicMock supports `.overlay.append`**

Open `tests/ui/test_shell_cache.py`. The fixture's `MagicMock()` already supports attribute access (returns child MagicMocks), so `.overlay.append(...)` is a no-op MagicMock call. **No change required** if the existing tests still pass after Task 3 step 5. Re-run them at step 5 to confirm.

(This bullet is a verification step, not a code change. Move to Step 2.)

- [ ] **Step 2: Write failing tests**

Create `tests/ui/test_shell_loading_toast.py`:

```python
"""Tests for Shell wiring of LoadingOverlay + ToastNotifier into pages."""
import pytest
from unittest.mock import MagicMock

from src.core.settings_store import SettingsStore
from src.db.repository import Repository
from src.ui.shell import Shell


@pytest.fixture
def shell(tmp_path):
    settings = SettingsStore(str(tmp_path / "config.json"))
    settings.load()
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    page = MagicMock()
    page.overlay = []
    s = Shell(page, settings, repo, str(snapshot_dir))
    s.build()
    yield s
    repo.close()


def test_shell_creates_loading_and_toast(shell):
    assert shell._loading is not None
    assert shell._toast is not None


def test_show_loading_delegates(shell):
    shell.show_loading("Test op...")
    assert shell._loading.label.value == "Test op..."
    assert shell._loading.strip.visible is True


def test_hide_loading_delegates(shell):
    shell.show_loading("Test")
    shell.hide_loading()
    assert shell._loading.strip.visible is False


def test_notify_default_kind_is_success(shell, monkeypatch):
    captured = []
    monkeypatch.setattr("src.ui.components.toast.threading.Timer",
                        lambda *a, **kw: type("T", (), {"start": lambda s: None,
                                                         "daemon": True})())
    shell.notify("Done", "Yay")
    assert len(shell._toast.stack.controls) == 1


def test_notify_error_kind(shell, monkeypatch):
    monkeypatch.setattr("src.ui.components.toast.threading.Timer",
                        lambda *a, **kw: type("T", (), {"start": lambda s: None,
                                                         "daemon": True})())
    shell.notify("Boom", "broke", kind="error")
    toast = shell._toast.stack.controls[0]
    from src.core.constants import COLORS
    assert toast.border.left.color == COLORS["late_severe"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/ui/test_shell_loading_toast.py -v`
Expected: FAIL — `AttributeError: 'Shell' object has no attribute '_loading'`

- [ ] **Step 4: Modify Shell to instantiate components + add delegates**

Open `src/ui/shell.py`. Add imports near the top (after existing imports):

```python
from src.ui.components.loading_overlay import LoadingOverlay
from src.ui.components.toast import ToastNotifier
```

In `Shell.__init__` (after `self._page_cache: dict[str, ft.Control] = {}`), add:

```python
        # Singleton overlays mounted onto page.overlay; reusable across all pages
        self._loading = LoadingOverlay(page)
        self._toast = ToastNotifier(page)
```

After `_render_page` (anywhere reasonable in the class), add the three delegate methods:

```python
    def show_loading(self, label: str) -> None:
        self._loading.show(label)

    def hide_loading(self) -> None:
        self._loading.hide()

    def notify(self, title: str, desc: str = "", kind: str = "success") -> None:
        if kind == "error":
            self._toast.error(title, desc)
        else:
            self._toast.success(title, desc)
```

- [ ] **Step 5: Run new + existing Shell tests**

Run: `python -m pytest tests/ui/ -v`
Expected: PASS — all of test_shell_cache.py (9), test_shell_loading_toast.py (5), test_loading_overlay.py (5), test_toast.py (8) = 27 passing

- [ ] **Step 6: Commit**

```bash
git add src/ui/shell.py tests/ui/test_shell_loading_toast.py
git commit -m "feat(shell): mount LoadingOverlay + ToastNotifier + delegate methods"
```

---

## Task 4: Pass loading + notify callbacks into all page builders

**Files:**
- Modify: `src/ui/shell.py` (only the `_build_*` methods, plus matching ctor params on each page)

This task threads the new callbacks through Shell's existing builder methods. We only modify the **builder calls** here; the page constructors are updated in subsequent tasks (5–12) when each page actually starts using them.

But pages must accept the kwargs without crashing in the meantime. So every page constructor gets the kwargs added with default `None` in this task — even if the page doesn't use them yet. This lets us land Shell wiring in one safe step.

- [ ] **Step 1: Add ctor params (default None) to all 8 page constructors**

For each of the following, find the `def __init__` line and add the three kwargs immediately after the existing `on_data_changed=None`. No other change yet.

`src/ui/pages/import_data.py`: change

```python
    def __init__(self, repo: Repository, settings: SettingsStore, snapshot_dir: str,
                 mode: str = "dark", on_data_changed=None):
```

to

```python
    def __init__(self, repo: Repository, settings: SettingsStore, snapshot_dir: str,
                 mode: str = "dark", on_data_changed=None,
                 show_loading=None, hide_loading=None, notify=None):
```

and after `self.on_data_changed = on_data_changed`, add:

```python
        self.show_loading = show_loading
        self.hide_loading = hide_loading
        self.notify = notify
```

Repeat the **exact same pattern** for these files (each already has `on_data_changed`):
- `src/ui/pages/issues.py`
- `src/ui/pages/edit_records.py`
- `src/ui/pages/settings.py`
- `src/ui/pages/backup_restore.py`

For these two files (no `on_data_changed` yet — add as new):
- `src/ui/pages/main_database.py` — change ctor signature + body to add all four kwargs (`on_data_changed`, `show_loading`, `hide_loading`, `notify`) and store them; the page also needs `notify` for `_copy_tsv` and `_export_xlsx`.

  Find:
  ```python
      def __init__(self, repo: Repository, settings: SettingsStore,
                   exports_dir: str, mode: str = "dark"):
  ```
  Replace with:
  ```python
      def __init__(self, repo: Repository, settings: SettingsStore,
                   exports_dir: str, mode: str = "dark",
                   on_data_changed=None,
                   show_loading=None, hide_loading=None, notify=None):
  ```
  After `self.mode = mode`, add:
  ```python
          self.on_data_changed = on_data_changed
          self.show_loading = show_loading
          self.hide_loading = hide_loading
          self.notify = notify
  ```

- `src/ui/pages/weekly_report.py` — change

  ```python
      def __init__(self, repo: Repository, settings: SettingsStore, exports_dir: str, mode: str = "dark"):
  ```

  to

  ```python
      def __init__(self, repo: Repository, settings: SettingsStore, exports_dir: str,
                   mode: str = "dark",
                   on_data_changed=None,
                   show_loading=None, hide_loading=None, notify=None):
  ```

  and after `self.exports_dir.mkdir(parents=True, exist_ok=True)`, add:

  ```python
          self.on_data_changed = on_data_changed
          self.show_loading = show_loading
          self.hide_loading = hide_loading
          self.notify = notify
  ```

- `src/ui/pages/monthly_report.py` — apply the identical change as `weekly_report.py` above (the constructor signature is the same shape).

- [ ] **Step 2: Update `_build_*` methods in `src/ui/shell.py` to pass the callbacks**

Find each `_build_*_page` method and pass `show_loading=self.show_loading, hide_loading=self.hide_loading, notify=self.notify` to its page constructor. For example, change

```python
    def _build_import_data_page(self) -> ft.Control:
        from src.ui.pages.import_data import ImportDataPage
        page_obj = ImportDataPage(self.repo, self.settings, self.snapshot_dir, self.mode,
                                  on_data_changed=self.invalidate_data_caches)
        return page_obj.build()
```

to

```python
    def _build_import_data_page(self) -> ft.Control:
        from src.ui.pages.import_data import ImportDataPage
        page_obj = ImportDataPage(
            self.repo, self.settings, self.snapshot_dir, self.mode,
            on_data_changed=self.invalidate_data_caches,
            show_loading=self.show_loading,
            hide_loading=self.hide_loading,
            notify=self.notify,
        )
        return page_obj.build()
```

Repeat the same trailing-three-kwargs pattern for:
- `_build_issues_page`
- `_build_edit_records_page`
- `_build_main_database_page`
- `_build_weekly_report_page`
- `_build_monthly_report_page`
- `_build_backup_restore_page`
- `_build_settings_page`

(Skip Shell's _placeholder fallback — it doesn't accept kwargs.)

- [ ] **Step 3: Run full pytest suite**

Run: `python -m pytest -q`
Expected: PASS — 109 passed (existing 91 + 18 new across Tasks 1–3); 6 skipped (PII fixtures unchanged)

- [ ] **Step 4: Commit**

```bash
git add src/ui/shell.py src/ui/pages/import_data.py src/ui/pages/issues.py src/ui/pages/edit_records.py src/ui/pages/settings.py src/ui/pages/backup_restore.py src/ui/pages/main_database.py src/ui/pages/weekly_report.py src/ui/pages/monthly_report.py
git commit -m "feat(shell): thread show_loading/hide_loading/notify into all page builders"
```

---

## Task 5: Issues page — toast on resolution

**Files:**
- Modify: `src/ui/pages/issues.py:_save_resolution`

- [ ] **Step 1: Locate `_save_resolution` (around line 273) and add the toast call**

Find:

```python
        apply_resolution(self.repo, self.selected_record_id, self.selected_reason, **kwargs)
        self._close_panel()
        self._refresh_list()
        self.list_view.update()
        if self.on_data_changed:
            self.on_data_changed()
```

Above the existing code, capture the employee name BEFORE the resolution closes the panel (the issue dict is no longer accessible after `_close_panel`). Around line 270, when `_save_resolution` first reads the selected record, find or add a `self.selected_employee_name` field. Inspect lines 268–272 first:

```bash
sed -n '260,290p' src/ui/pages/issues.py
```

Look for where `self.selected_record_id` is set in `_select_issue`. Add `self.selected_employee_name = issue.get("employee_name", "")` right next to it.

Then in `_save_resolution`, change

```python
        apply_resolution(self.repo, self.selected_record_id, self.selected_reason, **kwargs)
        self._close_panel()
        self._refresh_list()
        self.list_view.update()
        if self.on_data_changed:
            self.on_data_changed()
```

to:

```python
        apply_resolution(self.repo, self.selected_record_id, self.selected_reason, **kwargs)
        emp_name = self.selected_employee_name
        self._close_panel()
        self._refresh_list()
        self.list_view.update()
        if self.on_data_changed:
            self.on_data_changed()
        if self.notify:
            self.notify("Issue resolved", emp_name)
```

- [ ] **Step 2: Run pytest to confirm no regression**

Run: `python -m pytest tests/ -q`
Expected: PASS — 109 passed, 6 skipped

- [ ] **Step 3: Commit**

```bash
git add src/ui/pages/issues.py
git commit -m "feat(issues): show success toast on resolution"
```

---

## Task 6: Settings page — toast on save

**Files:**
- Modify: `src/ui/pages/settings.py:_save_all` (around line 144)

- [ ] **Step 1: Add toast call after settings save**

Find:

```python
        self.settings.update(update)
        self.cfg = self.settings.load()
        self._set_status("Settings saved", ok=True)
        if self.on_data_changed:
            self.on_data_changed()
```

Replace with:

```python
        self.settings.update(update)
        self.cfg = self.settings.load()
        self._set_status("Settings saved", ok=True)
        if self.on_data_changed:
            self.on_data_changed()
        if self.notify:
            self.notify("Settings disimpan")
```

- [ ] **Step 2: Run pytest**

Run: `python -m pytest tests/ -q`
Expected: PASS — 109 passed, 6 skipped

- [ ] **Step 3: Commit**

```bash
git add src/ui/pages/settings.py
git commit -m "feat(settings): show success toast on save"
```

---

## Task 7: Edit Records page — toast on save dialog

**Files:**
- Modify: `src/ui/pages/edit_records.py` (the nested `save` function inside `_open_edit_dialog`, around line 89)

- [ ] **Step 1: Add toast call after the existing on_data_changed**

Find:

```python
            apply_resolution(self.repo, rec["id"], reason_dropdown.value, **kwargs)
            self._close_dialog(dialog)
            self._refresh()
            self.records_list.update()
            if self.on_data_changed:
                self.on_data_changed()
```

Replace with:

```python
            apply_resolution(self.repo, rec["id"], reason_dropdown.value, **kwargs)
            self._close_dialog(dialog)
            self._refresh()
            self.records_list.update()
            if self.on_data_changed:
                self.on_data_changed()
            if self.notify:
                self.notify("Record diperbarui", rec.get("employee_name", ""))
```

- [ ] **Step 2: Run pytest**

Run: `python -m pytest tests/ -q`
Expected: PASS — 109 passed, 6 skipped

- [ ] **Step 3: Commit**

```bash
git add src/ui/pages/edit_records.py
git commit -m "feat(edit-records): show success toast on save"
```

---

## Task 8: Main DB page — loading on Excel export + toast on TSV copy

**Files:**
- Modify: `src/ui/pages/main_database.py:_export_xlsx` (around line 200) and `_copy_tsv` (around line 231)

- [ ] **Step 1: Wrap `_export_xlsx` in a worker thread + show loading + toast**

At the top of `main_database.py`, ensure `import threading` is present (add if missing).

Find:

```python
    def _export_xlsx(self):
        from src.reports.excel_builder import build_monthly_sheets_format

        rows = self.repo.list_monthly_grid(self.year, self.month, self.employee_filter)
        normalized = [{ ... } for r in rows]  # full dict comprehension
        out = self.exports_dir / f"main-db_{self.year}-{self.month:02d}.xlsx"
        build_monthly_sheets_format(str(out), normalized)
        self.status_text.value = f"✅ Exported: {out}"
        self.status_text.update()
```

Replace the body (keep the `def` signature) with:

```python
    def _export_xlsx(self):
        if self.show_loading:
            self.show_loading("📊 Generating Excel...")

        def work():
            try:
                from src.reports.excel_builder import build_monthly_sheets_format
                rows = self.repo.list_monthly_grid(
                    self.year, self.month, self.employee_filter,
                )
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
                    "alasan_ijin": format_alasan(
                        r.get("reason_code"), r.get("location"), r.get("reason_detail"),
                    ),
                } for r in rows]
                out = self.exports_dir / f"main-db_{self.year}-{self.month:02d}.xlsx"
                build_monthly_sheets_format(str(out), normalized)

                if self.hide_loading:
                    self.hide_loading()
                self.status_text.value = f"✅ Exported: {out.name}"
                try:
                    self.status_text.update()
                except (AssertionError, AttributeError):
                    pass
                if self.notify:
                    self.notify("Excel tersimpan", out.name)
            except Exception as ex:
                if self.hide_loading:
                    self.hide_loading()
                if self.notify:
                    self.notify("Export gagal", str(ex)[:80], kind="error")

        threading.Thread(target=work, daemon=True).start()
```

- [ ] **Step 2: Add toast to `_copy_tsv` (no loading needed — instant op)**

Find the end of `_copy_tsv`:

```python
        try:
            self.status_text.page.set_clipboard(text)
            self.status_text.value = f"✅ Copied {len(rows)} rows as TSV — paste into Sheets"
        except Exception as ex:
            self.status_text.value = f"❌ Clipboard failed: {ex}"
        self.status_text.update()
```

Replace with:

```python
        try:
            self.status_text.page.set_clipboard(text)
            self.status_text.value = f"✅ Copied {len(rows)} rows as TSV — paste into Sheets"
            if self.notify:
                self.notify(f"{len(rows)} rows copied", "paste ke Sheets")
        except Exception as ex:
            self.status_text.value = f"❌ Clipboard failed: {ex}"
            if self.notify:
                self.notify("Copy gagal", str(ex)[:80], kind="error")
        self.status_text.update()
```

- [ ] **Step 3: Run pytest**

Run: `python -m pytest tests/ -q`
Expected: PASS — 109 passed, 6 skipped

- [ ] **Step 4: Commit**

```bash
git add src/ui/pages/main_database.py
git commit -m "feat(main-db): loading on Excel export, toast on TSV copy"
```

---

## Task 9: Import Data page — loading + toast + threading

**Files:**
- Modify: `src/ui/pages/import_data.py:_do_import` (around line 123)

- [ ] **Step 1: Add `import threading` at top of file if not present**

Open `src/ui/pages/import_data.py`. Verify the imports include `import threading` near the top (alongside `from pathlib import Path`). Add it if missing.

- [ ] **Step 2: Replace `_do_import` body**

Find:

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
        if self.on_data_changed:
            self.on_data_changed()
```

Replace with:

```python
    def _do_import(self, policy: ConflictPolicy):
        filename = Path(self.selected_file).name
        records = list(self.parsed_records)  # snapshot — _reset_after_success will clear
        if self.show_loading:
            self.show_loading(f"📥 Sedang import {filename}...")

        def work():
            try:
                summary = resolve_import(
                    self.repo, records, filename,
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

                if self.hide_loading:
                    self.hide_loading()
                self.status_text.value = msg
                try:
                    self.status_text.update()
                except (AssertionError, AttributeError):
                    pass
                self._reset_after_success()
                if self.on_data_changed:
                    self.on_data_changed()
                if self.notify:
                    self.notify("Import berhasil", " · ".join(parts))
            except Exception as ex:
                if self.hide_loading:
                    self.hide_loading()
                if self.notify:
                    self.notify("Import gagal", str(ex)[:80], kind="error")

        threading.Thread(target=work, daemon=True).start()
```

- [ ] **Step 3: Run pytest**

Run: `python -m pytest tests/ -q`
Expected: PASS — 109 passed, 6 skipped

- [ ] **Step 4: Commit**

```bash
git add src/ui/pages/import_data.py
git commit -m "feat(import): threaded import with loading overlay + success/error toast"
```

---

## Task 10: Weekly Report page — loading + toast + threading

**Files:**
- Modify: `src/ui/pages/weekly_report.py:_generate` (single dispatch point for both PDF + Excel)

The slow work in this page funnels through one method: `_generate(selected, fmt)`. Wrapping that one method covers both export formats.

- [ ] **Step 1: Add `import threading` to top of file**

Open `src/ui/pages/weekly_report.py`. Add `import threading` to the imports at the top of the file (alongside `from datetime import ...`).

- [ ] **Step 2: Replace `_generate` with threaded version**

Find the existing `_generate` method (lines 41–75). Replace its full body with:

```python
    def _generate(self, selected: dict, fmt: str):
        loading_label = "📄 Generating PDF..." if fmt == "pdf" else "📊 Generating Excel..."
        toast_title = "PDF tersimpan" if fmt == "pdf" else "Excel tersimpan"
        if self.show_loading:
            self.show_loading(loading_label)

        def work():
            try:
                # Lazy imports keep page-load cheap and avoid eager pulls of reportlab/openpyxl
                from src.core.metrics import (
                    weekly_summary, hall_of_late, coaching_candidates, repeat_offenders,
                    distribusi_alasan, hari_paling_telat, best_performer, late_trend,
                )

                coaching_thr = self.settings.get("coaching_threshold_minutes", 75)
                repeat_weeks = self.settings.get("repeat_offender_weeks", 3)

                s = weekly_summary(self.repo, self.start.isoformat(), self.end.isoformat())
                coaching = coaching_candidates(self.repo, self.start.isoformat(),
                                                self.end.isoformat(), coaching_thr)
                repeat = repeat_offenders(self.repo, self.end.isoformat(), repeat_weeks)
                repeat_set = {r["staff_no"] for r in repeat}
                ranking_full = hall_of_late(self.repo, self.start.isoformat(),
                                             self.end.isoformat())
                top_n = selected.get("hall_top_n", "5")
                ranking = ranking_full if top_n == "All" else ranking_full[:int(top_n)]
                trend = late_trend(self.repo, self.start.isoformat(), self.end.isoformat())

                if fmt == "pdf":
                    output = self.exports_dir / f"weekly-report_{self.start}_{self.end}.pdf"
                    self._build_pdf(
                        str(output), selected, s, coaching, repeat_set, ranking, trend,
                        coaching_thr, len(repeat),
                        distribusi_alasan, hari_paling_telat, best_performer,
                    )
                else:
                    output = self.exports_dir / f"weekly-report_{self.start}_{self.end}.xlsx"
                    self._build_excel(str(output), selected, s, ranking, coaching)

                if self.hide_loading:
                    self.hide_loading()
                self.status_text.value = f"Generated: {output.name}"
                try:
                    self.status_text.update()
                except (AssertionError, AttributeError):
                    pass
                if self.notify:
                    self.notify(toast_title, output.name)
            except Exception as exc:  # noqa: BLE001
                if self.hide_loading:
                    self.hide_loading()
                self.status_text.value = f"Failed to generate report: {exc}"
                try:
                    self.status_text.update()
                except (AssertionError, AttributeError):
                    pass
                if self.notify:
                    error_title = "Export PDF gagal" if fmt == "pdf" else "Export Excel gagal"
                    self.notify(error_title, str(exc)[:80], kind="error")

        threading.Thread(target=work, daemon=True).start()
```

The `_build_pdf` and `_build_excel` methods stay untouched — only `_generate` changes.

- [ ] **Step 3: Run pytest**

Run: `python -m pytest tests/ -q`
Expected: PASS — 109 passed, 6 skipped

- [ ] **Step 4: Commit**

```bash
git add src/ui/pages/weekly_report.py
git commit -m "feat(weekly-report): threaded exports with loading overlay + toast"
```

---

## Task 11: Monthly Report page — loading + toast + threading

**Files:**
- Modify: `src/ui/pages/monthly_report.py:_generate`

Same shape as Task 10 — `_generate(selected, fmt)` is the single dispatch point.

- [ ] **Step 1: Add `import threading` to top of file**

Open `src/ui/pages/monthly_report.py`. Add `import threading` to the imports at the top.

- [ ] **Step 2: Replace `_generate` with threaded version**

Find the existing `_generate` method (lines 60–96). Replace its full body with:

```python
    def _generate(self, selected: dict, fmt: str):
        loading_label = "📄 Generating PDF..." if fmt == "pdf" else "📊 Generating Excel..."
        toast_title = "PDF tersimpan" if fmt == "pdf" else "Excel tersimpan"
        if self.show_loading:
            self.show_loading(loading_label)

        def work():
            try:
                # Lazy imports keep page-load cheap and avoid eager pulls of reportlab/openpyxl
                from src.core.metrics import (
                    weekly_summary, hall_of_late, coaching_candidates, repeat_offenders,
                )

                coaching_thr = self.settings.get("coaching_threshold_minutes", 75)
                repeat_weeks = self.settings.get("repeat_offender_weeks", 3)

                s = weekly_summary(self.repo, self.start.isoformat(), self.end.isoformat())
                coaching = coaching_candidates(
                    self.repo, self.start.isoformat(), self.end.isoformat(), coaching_thr,
                )
                repeat = repeat_offenders(self.repo, self.end.isoformat(), repeat_weeks)
                repeat_set = {r["staff_no"] for r in repeat}
                ranking_full = hall_of_late(self.repo, self.start.isoformat(),
                                             self.end.isoformat())
                top_n = selected.get("hall_top_n", "5")
                ranking = ranking_full if top_n == "All" else ranking_full[:int(top_n)]

                if fmt == "pdf":
                    output = self.exports_dir / f"monthly-report_{self.year}-{self.month:02d}.pdf"
                    self._build_pdf(
                        str(output), selected, s, coaching, repeat_set, ranking,
                        coaching_thr, len(repeat),
                    )
                else:
                    if selected.get("monthly_excel_sheets_format"):
                        output = self.exports_dir / f"monthly-sheets-format_{self.year}-{self.month:02d}.xlsx"
                        self._build_sheets_format_excel(str(output))
                    else:
                        output = self.exports_dir / f"monthly-raw_{self.year}-{self.month:02d}.xlsx"
                        self._build_raw_excel(str(output), s, ranking, coaching)

                if self.hide_loading:
                    self.hide_loading()
                self.status_text.value = f"Generated: {output.name}"
                try:
                    self.status_text.update()
                except (AssertionError, AttributeError):
                    pass
                if self.notify:
                    self.notify(toast_title, output.name)
            except Exception as exc:  # noqa: BLE001
                if self.hide_loading:
                    self.hide_loading()
                self.status_text.value = f"Failed to generate report: {exc}"
                try:
                    self.status_text.update()
                except (AssertionError, AttributeError):
                    pass
                if self.notify:
                    error_title = "Export PDF gagal" if fmt == "pdf" else "Export Excel gagal"
                    self.notify(error_title, str(exc)[:80], kind="error")

        threading.Thread(target=work, daemon=True).start()
```

`_build_pdf`, `_build_raw_excel`, `_build_sheets_format_excel` stay untouched.

- [ ] **Step 3: Run pytest**

Run: `python -m pytest tests/ -q`
Expected: PASS — 109 passed, 6 skipped

- [ ] **Step 4: Commit**

```bash
git add src/ui/pages/monthly_report.py
git commit -m "feat(monthly-report): threaded exports with loading overlay + toast"
```

---

## Task 12: Backup/Restore page — loading + toast + threading

**Files:**
- Modify: `src/ui/pages/backup_restore.py:_do_export` (lines 94–104) and `:_on_zip_picked` (lines 106–130)

- [ ] **Step 1: Add `import threading` to top of file**

Open `src/ui/pages/backup_restore.py`. Add `import threading` to the top imports.

- [ ] **Step 2: Replace `_do_export`**

Find the existing `_do_export` method (lines 94–104). Replace its full body with:

```python
    def _do_export(self):
        if self.show_loading:
            self.show_loading("💾 Creating backup...")

        def work():
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output = str(Path(self.backup_dir) / f"hr_backup_{timestamp}.zip")
                written = export_backup(self.db_path, self.config_path,
                                         self.backup_dir, output)

                if self.hide_loading:
                    self.hide_loading()
                self.status_text.value = f"Export selesai: {written}"
                self.status_text.color = COLORS["resolved"]
                try:
                    self.status_text.update()
                except (AssertionError, AttributeError):
                    pass
                if self.notify:
                    self.notify("Backup tersimpan", Path(written).name)
            except Exception as ex:
                if self.hide_loading:
                    self.hide_loading()
                self.status_text.value = f"Export gagal: {ex}"
                self.status_text.color = COLORS["late_severe"]
                try:
                    self.status_text.update()
                except (AssertionError, AttributeError):
                    pass
                if self.notify:
                    self.notify("Backup gagal", str(ex)[:80], kind="error")

        threading.Thread(target=work, daemon=True).start()
```

- [ ] **Step 3: Replace `_on_zip_picked`**

Find the existing `_on_zip_picked` method (lines 106–130). Replace its full body with:

```python
    def _on_zip_picked(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return
        zip_path = e.files[0].path
        if self.show_loading:
            self.show_loading("📂 Restoring backup...")

        def work():
            try:
                summary = import_backup(
                    zip_path, self.db_path, self.config_path, self.pre_restore_dir,
                )
                parts = []
                if summary["db_restored"]:
                    parts.append("database")
                if summary["config_restored"]:
                    parts.append("settings")
                parts.append(f"{summary['snapshots_restored']} snapshots")

                if self.hide_loading:
                    self.hide_loading()
                self.status_text.value = (
                    f"Import selesai ({', '.join(parts)}). "
                    f"Restart aplikasi untuk memuat data baru."
                )
                self.status_text.color = COLORS["resolved"]
                try:
                    self.status_text.update()
                except (AssertionError, AttributeError):
                    pass
                if self.on_data_changed:
                    self.on_data_changed()
                if self.notify:
                    self.notify("Restore selesai", "restart aplikasi")
            except Exception as ex:
                if self.hide_loading:
                    self.hide_loading()
                self.status_text.value = f"Import gagal: {ex}"
                self.status_text.color = COLORS["late_severe"]
                try:
                    self.status_text.update()
                except (AssertionError, AttributeError):
                    pass
                if self.notify:
                    self.notify("Restore gagal", str(ex)[:80], kind="error")

        threading.Thread(target=work, daemon=True).start()
```

- [ ] **Step 4: Run pytest**

Run: `python -m pytest tests/ -q`
Expected: PASS — 109 passed, 6 skipped

- [ ] **Step 5: Commit**

```bash
git add src/ui/pages/backup_restore.py
git commit -m "feat(backup): threaded export+restore with loading overlay + toast"
```

---

## Task 13: Manual smoke test + version bump + rebuild .exe

**Files:**
- Modify: `scripts/build_exe.py` (PRODUCT_VERSION constant)
- Build artifact: `dist/JosaphatTechHR.exe`

- [ ] **Step 1: Run the full pytest suite once more**

Run: `python -m pytest -q`
Expected: PASS — 109 passed, 6 skipped, 1 deprecation warning (reportlab — pre-existing)

- [ ] **Step 2: Manual smoke test in dev mode**

Run: `python main.py`

Verify in the running app:
1. Click sidebar nav between Issues / Dashboard / Main DB → fast nav still works (regression check)
2. Resolve any issue → green toast appears top-right, dismisses in ~1.5s
3. Save settings (change a number, click save) → green toast appears
4. Trigger Import .xls → top progress strip + dim → click sidebar nav while loading → click is absorbed (no nav happens) → after ~2s, strip disappears, green toast "Import berhasil · N new"
5. Export Weekly PDF → strip + dim during gen, green toast on success with filename
6. Export Backup ZIP → strip during gen, green toast on success
7. Force an error (e.g., import an invalid file or rename one column header) → red toast appears for ~3s
8. Click many resolutions in quick succession → max 3 toasts visible at once

Note any visual regressions or layout glitches; fix inline by going back to the relevant task before proceeding.

- [ ] **Step 3: Bump PRODUCT_VERSION in `scripts/build_exe.py`**

Open `scripts/build_exe.py`. Find the line with `PRODUCT_VERSION` and change `2.0.0` to `2.1.0` (this is a feature addition).

```bash
grep -n "PRODUCT_VERSION" scripts/build_exe.py
```

- [ ] **Step 4: Rebuild .exe**

Run: `python scripts/build_exe.py`
Expected output ending in: `Build OK: ...\dist\JosaphatTechHR.exe (~98 MB)`

- [ ] **Step 5: Copy .exe to main repo dist (so the user's normal-launch path picks it up)**

Run: `cp ".claude/worktrees/nice-tesla-c616f6/dist/JosaphatTechHR.exe" "../../../dist/JosaphatTechHR.exe"`
(Adjust the destination if the worktree is rooted differently — verify the timestamp on `D:\Gawe\Project X\Human Resource App\dist\JosaphatTechHR.exe` updated.)

- [ ] **Step 6: Commit version bump**

```bash
git add scripts/build_exe.py
git commit -m "chore(build): bump PRODUCT_VERSION to 2.1.0 (loading + toast feature)"
```

- [ ] **Step 7: Optional — tag and push**

Discuss with the user before pushing. If approved:

```bash
git tag v2.1.0
git push origin claude/nice-tesla-c616f6
git push origin v2.1.0
```

---

## Self-Review Checklist (run before handoff)

After all tasks complete, run through these checks:

- [ ] **Spec coverage:** Every operation in spec Section 2 has a task that wires loading and/or toast?
  - Loading + Toast (slow ops): Import (Task 9), Weekly PDF/Excel (Task 10), Monthly PDF/Excel (Task 11), Main DB Excel (Task 8), Backup (Task 12), Restore (Task 12) ✓
  - Toast only (fast ops): Resolve (Task 5), Edit (Task 7), Settings (Task 6), TSV (Task 8) ✓
  - Error toast: covered by every threaded op's except branch ✓
- [ ] **Test count:** 109 passed, 6 skipped, 1 deprecation warning?
- [ ] **No placeholders:** Every step shows actual code, no "similar to" references?
- [ ] **Type consistency:** `show_loading`, `hide_loading`, `notify` callable signatures match across Shell + page ctors + invocations?
- [ ] **Threading correctness:** all slow-op `work()` closures have try/except wrapping all UI calls (so a Flet update on an unmounted page doesn't crash the worker thread)?

---

## Notes for Implementation

**Threading + Flet update safety**: every `try: control.update() except (AssertionError, AttributeError): pass` is intentional. If the user navigates away during a long op, the page's controls become unmounted and Flet's `update()` raises. The worker thread should swallow that quietly — the operation already completed at the data layer.

**Why `import threading` inside each page rather than a shared utility?** Existing precedent in `issues.py:_schedule_refresh` does the same. Each call site is tiny (one Thread + one daemon flag), and a shared utility would just rename the same boilerplate.

**Why `[:80]` truncation on error messages?** Long stack-trace-derived messages overflow the 280px-wide toast. 80 chars is roughly two lines at the 11px font size; longer error detail can still be inspected in dev mode by raising the exception.
