# Issues Page — Resolve Modal + Status-Aware List Redesign

**Date:** 2026-05-09
**Status:** Spec — pending implementation
**Mockup references:**
- `mockups/09-issues-resolve-redesign.html` — A1 modal vs A2 split (A1 picked)
- `mockups/10-issues-with-status.html` — final list + modal

---

## 1. Goal & Non-Goals

### Goal

Make the Issues page workflow significantly less painful:

1. **Bigger, dominant Resolve dialog.** Current right-side panel (420px wide) truncates reason labels and hides the extra-input field. User explicitly: *"jendela resolve kecil, padahal yang penting di situ."*
2. **Status-aware list.** Replace the AI hint column with a clear **Pending/Resolved** status badge. Sort Pending on top, Resolved below, so the user sees what still needs handling at a glance and can also trace history of past resolutions.
3. **Stat chips at top.** Permanent counters ("12 Pending", "9 Resolved", "21 total") so the user always knows how many they've handled, even when the Pending section is long enough to push the Resolved divider off-screen.
4. **AI recommendation moves into the modal.** Decluttering the list while keeping the suggestion contextual to where the user actually decides.

### Non-Goals

- Color palette change — Phase 2, separate spec.
- Pagination of issues if a period contains hundreds of rows (not a real workload at PT Tekno scale).
- Bulk-resolve (select multiple issues, apply same reason) — out of scope.
- Editing the `reason_code` set — the 11 codes from v2.0 stay as-is.
- Auto-applying AI suggestion — user still picks manually.

---

## 2. Scope

### In scope
- New issue list with Pending/Resolved sections, status badges, sorting.
- Stat chips above the list.
- New Resolve modal (720px, centered, dim backdrop, click-blocking).
- Reason-cards grouped into 4 categories.
- Extra-input area appears prominently below reasons when needed.
- Live-preview of how the resolution will render in Main DB.
- Edit-mode: clicking a Resolved row opens the modal pre-filled, with "Delete Resolution" button to un-resolve.
- New `Repository.list_issues_with_resolutions(start, end)` method that returns both resolved and unresolved issues sorted in display order.

### Repository-side
- Add `list_issues_with_resolutions(start, end)` — single query joining attendance + employees + resolutions, returning all rows where `issue_case IN ('A','B','C','F')` regardless of resolution status.
- Existing `list_pending_issues` stays (used by `weekly_summary` etc.) — unchanged.

---

## 3. Visual Design (Final)

### 3.1 Page header

```
Issues                                                    [◀] 30 Mar – 05 Apr 2026 [▶]
21 total · 12 pending · 9 resolved · period 30 Mar → 05 Apr 2026
─────────────────────────────────────────────────────────────────────────────────────
[⚠ 12 Pending]    [✓ 9 Resolved]    [📅 21 Total]
```

The three stat chips sit between the page title and the list, sized as visual chips:
- Padding: 8/16
- Border-radius: 999 (pill)
- Border: 1px in matching accent color
- "Pending" chip: red/orange palette (`COLORS["late_severe"]` border + `rgba(248,113,113,0.18)` bg)
- "Resolved" chip: green palette (`COLORS["resolved"]` border + matching tint)
- "Total" chip: neutral purple
- Each chip shows count number prominently (W_800, ~16px) + label W_600

### 3.2 Section dividers in list

Two horizontal divider rows, one before each section:

```
⚠️ Belum Ditangani  [12]                          ──────────────────
[ rows ]
✅ Sudah Ditangani  [9]                            ──────────────────
[ rows ]
```

Sections expanded by default. Indonesian labels because they read more natural here than English ("Pending"/"Resolved" stays on the badge for compactness).

### 3.3 Issue row layouts

**Pending row:**
- `border-left: 3px solid COLORS["late_severe"]`
- `bgcolor: rgba(248,113,113,0.10)`
- Hover: bg deepens to `rgba(248,113,113,0.18)`
- Columns (left to right):
  - Name (W_700, 13px) + date "2026-04-01 · Rabu" (subtitle)
  - In/Out times in monospace, red "kosong" or green "08:58"
  - Resolution slot: italic placeholder "— belum ditangani —" (low opacity)
  - Case badge: e.g. `Tidak Hadir` (red), `Pulang Cepat` (lavender), `Lupa Pulang` (yellow-mild)
  - Status badge: "⚠ Pending" (red pill, 95px)

**Resolved row:**
- `border-left: 3px solid COLORS["resolved"]`
- `bgcolor: rgba(52,211,153,0.06)`
- `opacity: 0.78` (dimmed) — un-dim to 1.0 on hover
- Same column layout, but resolution slot now shows the formatted `alasan_ijin` text (e.g., `✓ Lapangan ke PT XYZ Surabaya` or `✓ Cuti`)
- Status badge: "✓ Resolved" (green pill, 95px)
- Click → opens modal in **edit mode** (pre-filled)

### 3.4 Resolve modal

**Structure (top to bottom):**

1. **Header** (18/24 padding, bottom-border):
   - Title: "Resolve Issue" (W_800, 20px)
   - Meta: "ESA · 2026-04-01 (Rabu) · Tidak Hadir"
   - Close button (✕) at right

2. **Issue summary strip** (red-tinted bg, bottom-border):
   - Monospace In/Out: `In: kosong   Out: kosong`

3. **AI recommendation banner** (blue-tinted bg, bottom-border):
   - 32×32 icon box with 🤖
   - Label "AI MENYARANKAN" (W_800, uppercase, 11px)
   - Suggestion text e.g. "Kemungkinan: **Tidak Hadir**, **Cuti**, atau **Izin Sakit**?"
   - Static text — clicking it does not auto-select; user still picks a reason card.

4. **Reason categories** (16/24 padding):
   - Label "PILIH ALASAN"
   - 4 category panels stacked vertically, each with header + 3-col grid of reason cards

   **Category 1 — Tugas (di luar kantor):**
   - Tugas Lapangan ✏️ (needs location)
   - Tugas Paparan ✏️ (needs location)

   **Category 2 — Cuti / Sakit / Izin:**
   - Izin Sakit
   - Cuti
   - Izin Pagi ✏️ (needs reason_detail)
   - Pulang Lebih Awal ✏️ (needs reason_detail)

   **Category 3 — Telat / Lupa Absen:**
   - Masuk Terlambat (Pekerjaan) ✏️ (needs reason_detail)
   - Terlambat (personal)
   - Lupa Absen — hint "+16 mnt penalty"

   **Category 4 — Lain:**
   - Belum Ada Kabar
   - Tidak Hadir

   **Reason card style:**
   - Default: `rgba(124,58,237,0.10)` bg, 1px purple border
   - Hover: deeper purple
   - Selected: gradient purple→pink, 2px pink border, glow shadow
   - Each card: label (W_700, 13px) + optional hint (11px, muted)
   - ✏️ marker on cards that require extra input

5. **Extra input area** (only visible when selected reason requires input, slides in below reason categories):
   - Pink/accent-bordered container
   - Label like "📍 LOKASI *" or "✏️ ALASAN DETAIL *" with required asterisk
   - TextField full-width (~672px effective)
   - Hint text below: "Field wajib diisi sebelum Save"

6. **Live preview** (green-tinted strip below extra input area, always visible once a reason is selected):
   - "Preview di Main DB: *Lapangan ke ____*"
   - Updates live as user types in the extra input.

7. **Footer** (top-border, padding 14/24):
   - **Edit-mode only:** "🗑 Delete Resolution" button at far left (red-tinted ghost)
   - Cancel button (gray, secondary)
   - Save button (green primary, gradient): "Save Resolution" (new) or "Update Resolution" (edit)
   - Save is **disabled** until: (a) a reason is selected AND (b) extra input is non-empty (if required by that reason)

### 3.5 Sizing summary

| Element | Spec |
|---------|------|
| Modal width | 720px |
| Modal max-height | 92% of viewport, internal scroll if longer |
| Reason card grid | 3 cols × variable rows per category |
| Reason card padding | 9/11 |
| Extra input field | full-width inside its container, min-height 40px |

---

## 4. Data Layer

### 4.1 New Repository method

```python
def list_issues_with_resolutions(self, start_date: str, end_date: str) -> list[dict]:
    """Both pending and resolved issues in date range.

    Returns dicts ordered by:
    1. resolution status (NULL first = Pending on top)
    2. date asc
    3. employee name asc
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

The `(r.id IS NULL) DESC` trick puts unresolved (NULL) first — SQLite returns 1 for NULL match, 0 for non-NULL match, sorting DESC.

### 4.2 Computing stat counts

In page logic (no extra query needed — derived from the list):

```python
issues = self.repo.list_issues_with_resolutions(start, end)
total = len(issues)
resolved = sum(1 for i in issues if i.get("reason_code"))
pending = total - resolved
```

### 4.3 Existing `list_pending_issues` behavior

Unchanged — still used by `weekly_summary` and dashboard metrics. Backwards compatible.

---

## 5. UX Flows

### 5.1 Pending issue → resolve

1. User clicks a Pending row.
2. Modal opens centered with dim backdrop. Click outside or ✕ closes.
3. AI banner shows; reason cards visible; no card selected; extra input hidden.
4. User clicks a reason card → card highlights; if `requires_extra_input(code)`, the extra input area slides in below; live preview shows.
5. User fills extra input (if needed). Save button transitions from disabled to enabled.
6. User clicks Save → DB write → modal closes → toast appears → row updates to Resolved status, moves to bottom section.

### 5.2 Resolved issue → re-edit

1. User clicks a Resolved row (dimmed visual cue).
2. Modal opens with the same layout, but **pre-filled**:
   - Reason card matching `reason_code` is selected
   - Extra input pre-populated with `location` or `reason_detail`
   - Save button is enabled and labeled "Update Resolution"
   - Footer shows "🗑 Delete Resolution" at far left
3. User can:
   - Change reason → live preview updates → click Update Resolution
   - Click Delete Resolution → confirms ("Hapus resolution untuk {employee_name}?") → if yes, delete via existing `delete_resolution` → row moves back to Pending
   - Cancel → modal closes, no change

### 5.3 No-issues state

- If period has no issues at all: empty-state card "Tidak ada issue minggu ini ✨" (existing pattern).
- If period has only Resolved issues: Pending divider shows count 0 with collapsed empty area, Resolved section visible.
- If period has only Pending: Resolved divider count 0 with empty area, Pending section visible.

---

## 6. Files Changed

### New / heavily modified

- `src/ui/pages/issues.py` — major rewrite (current file ~310 lines, will grow to ~450)
- `src/db/repository.py` — add `list_issues_with_resolutions`
- `tests/db/test_repository.py` — add 2 tests for the new method
- `tests/ui/test_issues_page.py` — NEW file with tests for sort order, status badge, stat counts derivation

### Lightly touched
- `src/core/resolver.py` — no changes; `apply_resolution`, `delete_resolution`, `requires_extra_input` already cover what we need
- `src/core/alasan_format.py` — no changes; used for live preview

---

## 7. Component Breakdown

### 7.1 IssuesPage class structure (post-refactor)

```python
class IssuesPage:
    def __init__(self, repo, settings, mode, on_data_changed=None,
                 show_loading=None, hide_loading=None, notify=None):
        ...
        self._modal: ResolveModal | None = None
        self._stat_chips: dict[str, ft.Container] = {}

    # public
    def build(self) -> ft.Control: ...

    # list
    def _build_header_with_stats(self) -> ft.Control: ...
    def _build_stat_chip(self, label, count, kind) -> ft.Container: ...
    def _refresh_list(self) -> None:
        # 1. fetch from list_issues_with_resolutions
        # 2. update stat chips
        # 3. populate two sections (pending + resolved)
    def _build_pending_row(self, issue: dict) -> ft.Control: ...
    def _build_resolved_row(self, issue: dict) -> ft.Control: ...

    # modal
    def _open_resolve_modal(self, issue: dict) -> None: ...
    def _close_resolve_modal(self) -> None: ...
    def _save_resolution_from_modal(self) -> None: ...
    def _delete_resolution_from_modal(self) -> None: ...
```

### 7.2 ResolveModal helper class (new, in same file)

A small class encapsulating the modal widget tree. Lives in `issues.py` for now (single consumer); can be promoted to its own component if a second use-case emerges.

```python
class ResolveModal:
    def __init__(self, page, on_save, on_delete=None, on_cancel=None): ...
    def open_for(self, issue: dict, edit_mode: bool = False) -> None: ...
    def close(self) -> None: ...

    # internal
    def _select_reason(self, code: str) -> None: ...
    def _update_extra_input_visibility(self, code) -> None: ...
    def _update_live_preview(self) -> None: ...
    def _update_save_button_state(self) -> None: ...
```

The modal is mounted to `page.overlay` once at construction; toggling `visible` shows/hides it.

---

## 8. Tests

### 8.1 Repository tests (`tests/db/test_repository.py`)

```python
def test_list_issues_with_resolutions_pending_first(tmp_path):
    repo = ...
    # insert 2 attendance records with issue_case='A'
    # resolve one
    rows = repo.list_issues_with_resolutions("2026-04-01", "2026-04-07")
    assert len(rows) == 2
    assert rows[0]["reason_code"] is None  # pending first
    assert rows[1]["reason_code"] is not None  # resolved second

def test_list_issues_with_resolutions_includes_all_relevant_cases():
    # cover A, B, C, F (not D, E, G)
    ...
```

### 8.2 Page tests (`tests/ui/test_issues_page.py` — NEW)

```python
def test_stat_chip_counts_match_data(shell, fixture_issues):
    page = IssuesPage(...)
    page.build()
    assert page._stat_chips["pending"].content.controls[0].value == "12"
    assert page._stat_chips["resolved"].content.controls[0].value == "9"

def test_pending_rows_render_above_resolved(...):
    ...

def test_resolved_row_shows_alasan_text(...):
    ...

def test_clicking_resolved_opens_modal_pre_filled(...):
    ...
```

Page tests use the same `MagicMock` page pattern as existing UI tests.

### 8.3 Existing tests
- All existing `test_issue_detector.py`, `test_resolver.py`, `test_repository.py` stay green.
- Existing `test_shell_cache.py` and `test_shell_loading_toast.py` unaffected (Issues page constructor signature stays compatible).

Expected: 109 passed → ~115 passed after this spec lands.

---

## 9. Out of Scope / Deferred

- Stat chip click-through (clicking "Pending" filters list to only show pending) — possible follow-up.
- Keyboard navigation in the modal (Tab through reason cards, Enter to save) — Flet limitations make this awkward.
- Search/filter within the issue list — current period nav + scroll suffices.
- Animations on row move from Pending → Resolved (just re-render; no fancy slide).

---

## 10. Implementation Order (hint for writing-plans)

Suggested task ordering:

1. **Repository:** add `list_issues_with_resolutions` + 2 tests (foundation, can be built in isolation)
2. **Stat chips component:** small reusable widget (or inline helper inside issues.py) + tests
3. **List section refactor:** swap `_refresh_list` to use new repo method, add Pending/Resolved sections, status badges, sort. Visual smoke test in dev mode.
4. **Modal extraction:** pull current resolve panel logic into `ResolveModal` class + new layout (centered, 720px, AI banner moved in, reason categories grouped, extra input area, live preview)
5. **Edit mode:** wire pre-fill + Delete Resolution button + Update Resolution copy
6. **Wire `_open_resolve_modal` from row click** (replaces existing `_select_issue` flow)
7. **Page tests** (`tests/ui/test_issues_page.py`) covering stats, sort, modal open
8. **Manual verification** in dev mode + .exe rebuild
9. **Bump version v2.1.0 → v2.2.0** (significant feature change)

Each task: TDD for logic, manual verify for UI. One commit per task.
