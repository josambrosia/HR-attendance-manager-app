# Loading Indicators & Toast Notifications

**Date:** 2026-05-09
**Status:** Spec — pending implementation
**Mockup reference:** `mockups/08-loading-and-toast.html`

---

## 1. Goal & Non-Goals

### Goal

Add two pieces of visual feedback to the HR Attendance Manager so the user always knows what the app is doing:

1. **Loading indicator** on slow operations — so the user knows the app is busy and stops clicking other navigation while waiting.
2. **Toast notifications** on every completed operation (success and failure) — so the user gets confirmation that something actually happened.

### Non-Goals

- Determinate progress (% complete) — out of scope. Indeterminate animation is sufficient for now.
- Click-to-dismiss toasts — out of scope. Auto-dismiss only.
- Cancellation buttons on the loading overlay — out of scope.
- Replacing existing inline `status_text` displays on Import/Backup pages — those stay; toasts are additive.
- Touching the existing snackbar usages (`page.snack_bar = ...`) in Dashboard — out of scope.

---

## 2. Scope (User-Picked Variants)

| Element | Variant | Behavior |
|---------|---------|----------|
| **Loading** | **L2 — Top Progress Strip** | Indeterminate `ProgressBar` + label at the top of the content area, light dim layer underneath blocking clicks. Disappears when op finishes. |
| **Toast** | **T2 — Translucent Solid** | Top-right corner card. Semi-transparent dark fill (~82% opacity) with a left border (3px) — green for success, red for error. Auto-dismiss after 1500ms. Stacks vertically when multiple are queued. |

User-stated constraints:
- Loading: blocks clicks (modal feel)
- Toast: positioned so it does not cover important UI behind it
- Toast duration: 1-2 seconds (1500ms picked)

### Scope of operations

**Operations that get LOADING + TOAST (slow ops, >1s):**

| Operation | Source location | Loading label | Success toast |
|-----------|----------------|---------------|---------------|
| Import .xls | `src/ui/pages/import_data.py:_do_import` | `📥 Sedang import {filename}...` | `Import berhasil` · `{N} new · {C} conflict` |
| Export PDF (weekly) | `src/ui/pages/weekly_report.py` PDF export handler | `📄 Generating PDF...` | `PDF tersimpan` · `{filename}` |
| Export PDF (monthly) | `src/ui/pages/monthly_report.py` PDF export handler | (same) | (same) |
| Export Excel (weekly) | `src/ui/pages/weekly_report.py` Excel export handler | `📊 Generating Excel...` | `Excel tersimpan` · `{filename}` |
| Export Excel (monthly) | `src/ui/pages/monthly_report.py` Excel export handler | (same) | (same) |
| Export Main DB Excel | `src/ui/pages/main_database.py:_export_xlsx` | (same) | (same) |
| Backup ZIP | `src/ui/pages/backup_restore.py:_do_export` | `💾 Creating backup...` | `Backup tersimpan` · `{filename}` |
| Restore ZIP | `src/ui/pages/backup_restore.py:_on_zip_picked` | `📂 Restoring backup...` | `Restore selesai` · `restart aplikasi` |

**Note on Main DB first load:** intentionally NOT in scope. Showing a loading overlay during a synchronous page builder requires a Timer-deferred render trick that adds fragility for marginal benefit. User stated Main DB performance is acceptable as-is. Revisit if Tier C (Main DB pagination/virtualization) ever happens.

**Operations that get TOAST ONLY (fast ops, <1s — confirmation feedback):**

| Operation | Source location | Success toast |
|-----------|----------------|---------------|
| Resolve issue | `src/ui/pages/issues.py:_save_resolution` | `Issue resolved` · `{employee_name}` |
| Edit record | `src/ui/pages/edit_records.py:save` | `Record diperbarui` |
| Save settings | `src/ui/pages/settings.py:_save_all` | `Settings disimpan` |
| Copy TSV | `src/ui/pages/main_database.py:_copy_tsv` | `{N} rows copied` · `paste ke Sheets` |

**Error toast (operations from the slow-ops table that fail):**

If any operation in the first table raises during execution, the loading hides, then a red-bordered error toast shows:
- Title: `{operation} gagal` (e.g., `Import gagal`, `Backup gagal`)
- Description: the exception message (truncated to 80 chars)

Fast-op errors keep the existing inline `status_text` behavior — no error toast for those (out of scope to avoid disrupting current error UX).

---

## 3. Components

### 3.1 LoadingOverlay (`src/ui/components/loading_overlay.py`)

A singleton overlay that mounts itself onto `page.overlay` once. Exposes two public methods.

**Public API:**
```python
class LoadingOverlay:
    def __init__(self, page: ft.Page): ...
    def show(self, label: str) -> None: ...
    def hide(self) -> None: ...
```

**Internal structure (Flet widgets):**
```
ft.Stack (full-screen, mounted in page.overlay)
├── ft.Container (dim layer)
│   bgcolor=rgba(15, 7, 23, 0.45)
│   expand=True
│   on_click=lambda e: None  # absorb clicks (block-click behavior)
└── ft.Container (top strip)
    top=0, left=0, right=0
    padding=10/16
    bgcolor=COLORS["surface_dark"] with 0.95 alpha
    border-bottom: 1px solid COLORS["primary"]
    content=ft.Row([
        ft.Text(label, size=12, weight=W_600),
        ft.ProgressBar(expand=True, height=4),  # indeterminate
    ])
```

`visible` flag is toggled by `show`/`hide`. `show(label)` updates the label text and sets visible=True; `hide()` sets visible=False. Both call `self.update()` to push state.

**Sidebar exclusion:** the dim layer covers the entire page including the sidebar. This is intentional — user explicitly wanted nav clicks blocked during loading.

### 3.2 ToastNotifier (`src/ui/components/toast.py`)

A singleton stacked toast queue mounted in `page.overlay`.

**Public API:**
```python
class ToastNotifier:
    def __init__(self, page: ft.Page): ...
    def success(self, title: str, desc: str = "") -> None: ...
    def error(self, title: str, desc: str = "") -> None: ...
```

**Internal structure:**
```
ft.Container (positioned, mounted in page.overlay)
  top=80, right=20, width=280
  content=ft.Column(spacing=8)  # toast stack
```

**Per-toast widget:**
```
ft.Container
  bgcolor=rgba(45, 27, 78, 0.82)  # semi-transparent surface
  border=ft.border.only(left=BorderSide(3, color))
    color: COLORS["resolved"] (#34D399) for success
    color: COLORS["late_severe"] (#F87171) for error
  border_radius=8
  padding=10/14
  content=ft.Row([
    ft.Text(icon),  # ✅ for success, ❌ for error
    ft.Column([
      ft.Text(title, size=13, weight=W_700),
      ft.Text(desc, size=11, opacity=0.8),  # only if desc != ""
    ]),
  ])
```

**Auto-dismiss:** each toast spawns a `threading.Timer(1.5, dismiss)` on append. `dismiss` removes the toast from the stack and calls `update()`. Wrapped in try/except to handle race with manual unmount.

**Stacking:** `success`/`error` append to the stack column. Stack max-3 — if already 3 visible, the oldest is removed before appending.

**Positioning rationale:** `top=80` deliberately offsets below page headers (Dashboard's top has `Export Weekly`/`Export Monthly` buttons at right). `width=280` keeps the toast narrow so even at top=80 it does not cover central content. The user explicitly asked for "tidak terlalu menutupi UI di belakangnya".

### 3.3 Shell extensions (`src/ui/shell.py`)

Three new public methods on `Shell` that delegate to the singletons. Pages call these instead of importing the components directly.

```python
class Shell:
    def __init__(self, ...):
        ...
        self._loading = LoadingOverlay(page)
        self._toast = ToastNotifier(page)

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

**No auto-loading wrapper in `_render_page`:** the synchronous Flet builder pattern means showing a loading overlay around a synchronous build does not give the UI a chance to repaint; the overlay would only be visible to the user after the build finishes (i.e., useless). Main DB first load slowness is therefore not addressed here — see Section 2 note.

### 3.4 Page constructor extensions

Each page that performs a tracked operation gets new constructor parameters in addition to the existing `on_data_changed`:

```python
def __init__(
    self,
    repo, settings, ...,
    on_data_changed=None,
    show_loading=None,   # callable(label: str)
    hide_loading=None,   # callable()
    notify=None,         # callable(title, desc="", kind="success")
):
```

The Shell builders wire these from `self.show_loading`, `self.hide_loading`, `self.notify`.

Pages with internal mutators check for `None` callbacks before invoking, the same way existing `on_data_changed` is checked:
```python
if self.show_loading:
    self.show_loading(label)
```

---

## 4. Threading Pattern

Heavy operations must run in a background thread; otherwise the UI never repaints to show the loading overlay until the operation already finished.

The codebase already has precedent for this pattern in `issues.py:_schedule_refresh` (uses `threading.Timer`). New code uses plain `threading.Thread(daemon=True)`.

**Standard wrapper for slow ops:**

```python
def _do_import(self, policy: ConflictPolicy):
    filename = Path(self.selected_file).name
    if self.show_loading:
        self.show_loading(f"📥 Sedang import {filename}...")

    def work():
        try:
            summary = resolve_import(
                self.repo, self.parsed_records, filename,
                snapshot_dir=self.snapshot_dir, policy=policy,
                settings=self.settings.load(),
            )
            if self.hide_loading:
                self.hide_loading()
            if self.notify:
                desc_parts = [f"{summary['inserted']} new"]
                if summary['overwritten']:
                    desc_parts.append(f"{summary['overwritten']} overwritten")
                if summary.get('preserved_resolved', 0):
                    desc_parts.append(f"{summary['preserved_resolved']} preserved")
                self.notify("Import berhasil", " · ".join(desc_parts))
            if self.on_data_changed:
                self.on_data_changed()
            self._reset_after_success()
        except Exception as ex:
            if self.hide_loading:
                self.hide_loading()
            if self.notify:
                self.notify("Import gagal", str(ex)[:80], kind="error")

    threading.Thread(target=work, daemon=True).start()
```

**Cross-thread `update()` safety:** Flet 0.25.2 supports calling `control.update()` from non-main threads. Existing code in `issues.py:_schedule_refresh` confirms this works. Wrap each `update()` in try/except for the case where the page has been unmounted (e.g., user nav-ed away mid-op).

**Double-click protection:** loading overlay's dim layer absorbs all clicks (covers the entire page including the trigger button), so double-click on the trigger is implicitly prevented while loading is visible. No per-button disable logic required.

---

## 5. Visual Specification

Match existing Sunset Coral palette (`src/core/constants.py:COLORS`).

### Loading Overlay (L2)

| Element | Property | Value |
|---------|----------|-------|
| Dim layer | bgcolor | `rgba(15, 7, 23, 0.45)` (≈ COLORS["bg_dark"] @ 45% alpha) |
| Strip background | bgcolor | `COLORS["surface_dark"]` @ 95% alpha |
| Strip border-bottom | color | `COLORS["primary"]` (1px) |
| Label text | size, weight | 12px, W_600 |
| Progress bar | height | 4px |
| Progress bar fill | gradient | linear `COLORS["primary"]` → `COLORS["accent"]` |

### Toast (T2)

| Element | Property | Value |
|---------|----------|-------|
| Container position | top, right, width | 80px, 20px, 280px |
| Per-toast bgcolor | | `rgba(45, 27, 78, 0.82)` |
| Per-toast border-left | width, color (success) | 3px, `COLORS["resolved"]` (#34D399) |
| Per-toast border-left | width, color (error) | 3px, `COLORS["late_severe"]` (#F87171) |
| Border radius | | 8px |
| Padding | | 10px vertical, 14px horizontal |
| Title text | size, weight | 13px, W_700 |
| Desc text | size, opacity | 11px, 80% |
| Stack gap | | 8px |
| Auto-dismiss | | 1500ms |
| Max stack size | | 3 (oldest evicted on overflow) |

---

## 6. Files Changed

### New files
- `src/ui/components/loading_overlay.py` — `LoadingOverlay` class
- `src/ui/components/toast.py` — `ToastNotifier` class
- `tests/ui/test_toast.py` — unit tests for `ToastNotifier` queue + dismiss
- `tests/ui/test_loading_overlay.py` — unit tests for `LoadingOverlay` show/hide
- `tests/ui/test_shell_loading_toast.py` — integration test that Shell wires callbacks correctly

### Modified files
- `src/ui/shell.py` — instantiate components in `__init__`; add `show_loading` / `hide_loading` / `notify` methods; thread `Main DB first load` auto-loading into `_render_page`; pass new callbacks to all page builders
- `src/ui/pages/import_data.py` — add `show_loading` / `hide_loading` / `notify` ctor params; wrap `_do_import` in worker thread + show loading + show toast
- `src/ui/pages/issues.py` — add `notify` ctor param; toast on `_save_resolution` success
- `src/ui/pages/edit_records.py` — add `notify` ctor param; toast on save success
- `src/ui/pages/settings.py` — add `notify` ctor param; toast on save success
- `src/ui/pages/main_database.py` — add `show_loading` / `hide_loading` / `notify` ctor params; wrap `_export_xlsx` in worker thread; add toast to `_copy_tsv`
- `src/ui/pages/weekly_report.py` — add callbacks; wrap PDF + Excel exports in worker threads
- `src/ui/pages/monthly_report.py` — add callbacks; wrap PDF + Excel exports in worker threads
- `src/ui/pages/backup_restore.py` — add callbacks; wrap export + import in worker threads

---

## 7. Testing

### Unit tests (`tests/ui/`)

- **`test_toast.py`**:
  - `success()` appends a toast to the stack with green border
  - `error()` appends a toast with red border
  - Dismiss timer removes toast after 1500ms (use `freezegun` or mock `threading.Timer`)
  - Stack overflow at max-3 evicts oldest
  - Multiple toasts stack vertically (gap 8px)

- **`test_loading_overlay.py`**:
  - `show(label)` sets `visible=True` and updates label text
  - `hide()` sets `visible=False`
  - Successive `show` calls update label without re-mounting

- **`test_shell_loading_toast.py`**:
  - Shell wires `show_loading` / `hide_loading` / `notify` into page constructors that accept them
  - Pages without these params (e.g., `_placeholder`) are not affected

### Manual verification

After implementation, manual smoke test in the actual app:
1. Import a small `.xls` → loading strip appears at top, dims content, toast confirms after 1-2s
2. Click sidebar nav during loading → confirms click is blocked
3. Resolve an issue → toast appears top-right, dismisses in 1500ms
4. Export weekly PDF → loading visible during gen, toast on success with file path
5. Trigger an intentional error (e.g., import bad file) → red error toast appears with message
6. Resolve 5 issues quickly → max 3 toasts visible, oldest evicted, all dismiss eventually

Tests pass: 91 → ~100 expected (depending on exact count of new tests added).

---

## 8. Open Questions / Deferred

- **Per-operation icons:** spec uses emoji prefixes in labels (`📥`, `📄`, `📊`, `💾`, `📂`). If the user prefers icon widgets (`ft.Icon`) instead of emoji, this is a small follow-up.
- **Toast click-to-dismiss:** currently auto-dismiss only. Adding click-to-dismiss is trivial but out of scope.
- **Error toast duration:** errors might warrant longer duration (e.g., 3000ms) so the user can read them. Spec uses 1500ms uniformly to match user's "1-2 detik" — revisit after testing if errors get missed.
- **Toast for fast-op errors:** out of scope. Existing inline `status_text` for fast-op errors is preserved.

---

## 9. Implementation Order (Hint for writing-plans)

Suggested task ordering for the implementation plan:

1. Build `LoadingOverlay` component + tests
2. Build `ToastNotifier` component + tests
3. Wire into Shell (constructor + delegate methods + Main DB auto-loading) + tests
4. Wire into Issues page (toast only, simplest)
5. Wire into Settings page (toast only)
6. Wire into Edit Records page (toast only)
7. Wire into Main DB page (loading on Excel export + toast on TSV copy)
8. Wire into Import Data page (loading + toast + threading)
9. Wire into Weekly Report page (loading + toast + threading on both exports)
10. Wire into Monthly Report page (same pattern as Weekly)
11. Wire into Backup/Restore page (loading + toast + threading on both ops)
12. Manual verification + screenshot
13. Bump version (v2.0.0 → v2.1.0 since this is a feature addition) + rebuild .exe

Each task: TDD for component logic, manual verify for actual UI behavior. Commit per task.
