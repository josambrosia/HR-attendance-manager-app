# Josaphat Tech Solution — HR Attendance Manager

> **For new Claude sessions:** Read this entire file first. It contains all the context, conventions, and pitfalls discovered across previous brainstorming + implementation sessions. The user (HR at PT Tekno) communicates in Indonesian/English mix and has basic Python knowledge — explain trade-offs in plain language when needed.

**Current shipped version:** **v2.2.0** (commit `c35666f`, tag `v2.2.0` PUSHED to remote).

**Latest local-only commits (v2.3.0 territory, not yet pushed):** none — branch `claude/nice-tesla-c616f6` is at HEAD `c35666f` matching `origin/master`.

**Repo:** `https://github.com/josambrosia/HR-attendance-manager-app.git` (HTTPS auth via Git Credential Manager).

**Working directory:** `D:\Gawe\Project X\Human Resource App` (Windows, paths have spaces — quote carefully).

**Test count:** 134 passing, 6 skipped (PII fixtures), 1 deprecation warning (third-party reportlab).

---

## What This App Does

A single-user **Windows desktop app** that automates the user's weekly + monthly fingerprint attendance reporting workflow at PT Tekno (Indonesia).

**Workflow it replaces:**
1. HR exports weekly fingerprint data as `.xls` from the office system
2. Used to scan it manually for missing clock-ins / lateness
3. Chase employees via WhatsApp for explanation
4. Type the explanation back into a Google Sheets monthly recap
5. Repeat at end-of-month for management report

**What this app does:**
1. Import `.xls` → auto-detect 7 issue cases (A=full absent, B=no Masuk, C=no Keluar, D=late <15min, E=late ≥15min, F=Pulang Cepat, G=Istirahat skip)
2. **Issues page**: list pending follow-ups with AI recommendation, click to resolve with 1 of 11 reason codes
3. **Dashboard**: vital + trivia metrics, Coaching Required (>75 mnt/week), Hall of Late ranking, Maximum Bold tone with medals/streaks
4. **Main Database** (NEW in v2.0): monthly grid matching the user's Google Sheets format byte-for-byte (17 cols), inline editable, Export `.xlsx` + Copy as TSV (paste-ready for Sheets)
5. **Reports**: Weekly + Monthly PDF (branded "Powered by Josaphat Tech Solution") + Excel export with checklist modal
6. **Backup/Restore**: ZIP DB+config for laptop migration

**Out of scope (don't propose):**
- Multi-user, cloud sync, mobile app
- Real-time fingerprint device integration
- Automated WhatsApp messaging (HR keeps that human/personal)

---

## User Context (Critical to Remember)

- **Role:** HR at PT Tekno, Indonesia. Not a developer.
- **Python:** Has *basic* Python from past learning — can read code, can't deeply maintain it.
- **Language:** Mix Bahasa Indonesia + English; prefers Indonesian. Use Indonesian by default in your replies.
- **Communication style:** Direct, prefers multiple-choice questions over open-ended. Suka penjelasan ringkas dengan tabel.
- **Decision pattern:** Often **flips initial preferences after seeing visual mockups**. She said "Wall of Shame se subtle mungkin" then later said "actually make it bold dan menantang". Always show 1-2 alternatives even when she gave a directional hint.
- **Issue resolution UX preference:**
  - **Passive issues** (lateness with timing recorded) → cell color only, NO follow-up
  - **Follow-up issues** (data missing — full absent, lupa absen) → goes into list to chase via WA
  - **Dual** (Pulang Cepat — has timing but unusual) → both color + follow-up

---

## Tech Stack (LOCKED — Don't Re-Propose)

| Layer | Choice | Why |
|---|---|---|
| Language | **Python 3.13.5** | User has basic Python familiarity; pre-installed |
| GUI | **Flet 0.25.2** | Material Design 3, dark/light theme built-in, modern look (user picked over CustomTkinter/PyQt6) |
| Excel input | `xlrd==2.0.1` (.xls) + `openpyxl==3.1.5` (.xlsx) | Industry standard |
| PDF | `reportlab==4.2.5` | Mature, embeddable images for branding |
| DB | **SQLite** (single file at `data/app.db`) | Zero setup, easy backup |
| Charts | `matplotlib` (PDF) + Flet's built-in (UI) | Already bundled |
| Packaging | `flet pack` (wraps PyInstaller) | Single .exe portable |
| Tests | `pytest==8.3.3` | 88 tests across `tests/core/`, `tests/db/`, `tests/reports/` |

**No new dependencies in v2.0.** Don't add unless absolutely necessary — installer surface area matters.

---

## Visual Design (Sunset Coral Palette — LOCKED)

| Token | Hex | Use |
|---|---|---|
| Primary | `#7C3AED` (purple) | Main brand, sidebar accent |
| Accent | `#F472B6` (pink) | Secondary, gradients with primary |
| Highlight | `#FBBF24` (yellow) | Late mild |
| Resolved | `#34D399` (green) | Success, has-resolution |
| Late mild | `#FCD34D` | Late <15min cell |
| Late severe | `#F87171` (red) | Late ≥15min cell, full absent |
| Pulang cepat | `#C084FC` (lavender) | Pulang Cepat cell |
| BG dark | `#1a0b2e` | Dark mode background |
| BG light | `#faf5ff` | Light mode background |

**Logo:** Hexagon "J" with purple→pink gradient. Brand: "Josaphat Tech Solution". Tagline: "HR Attendance Manager".

**Logo asset files** (all bundled into .exe via `--add-data`):
- `assets/logo.svg` — built-in placeholder (vector, used in PDF footer + UI)
- `assets/icon.ico` — multi-res Windows icon (16/32/48/64/128/256) for .exe + taskbar
- `assets/logo-256.png` — splash screen + app icon
- `assets/logo-custom.svg` — **user override slot** (if exists, replaces built-in everywhere). Generator: `scripts/generate_logo.py`.

**Dashboard tone: Maximum Bold.** Use medals (🥇🥈🥉) for top latecomers, big red numbers, "🚨 COACHING REQUIRED" headers, pulsing animations for over-threshold cards. Subtle is wrong — user explicitly rejected that.

---

## File Structure

```
main.py                        # Flet app entry — RUN THIS, not src/main.py
config.json                    # User settings (runtime-generated, gitignored)
requirements.txt
README.md
.gitignore                     # Excludes data/, backups/, *.db, *.xls, .superpowers/, .claude/
src/
  main.py                      # Compatibility SHIM — defers to root main.py
  core/
    constants.py               # COLORS, REASON_CODES (11 codes), DEFAULT_SETTINGS
    settings_store.py          # SettingsStore class — atomic write, JSON, "Off" thresholds
    parser.py                  # parse_xls() — fingerprint .xls → record dicts
    issue_detector.py          # classify_issue() (7 cases) + recommend() (AI hints)
    resolver.py                # apply_resolution() — handles 11 codes + lupa_absen penalty
    conflict.py                # resolve_import() — KEEP_EXISTING/OVERWRITE + preserved_resolved rule
    metrics.py                 # 8 dashboard aggregations
    backup.py                  # export_backup / import_backup (ZIP)
    alasan_format.py           # NEW v2.0: format_alasan() renders 11 codes → free-form text matching Sheets
  db/
    schema.sql                 # 5 tables: employees, attendance_records, resolutions, import_batches, record_history
    repository.py              # ALL SQLite access. Frozen-aware SCHEMA_PATH resolver.
  ui/
    shell.py                   # Sidebar nav (4 groups: Workflow/Database/Reports/Tools), routing, theme toggle.
                               # v2.1: page-Control cache + invalidate; v2.1: mounts LoadingOverlay + ToastNotifier
                               # singletons; v2.1: Main DB async first-load (cache miss → background thread builds widget)
    theme.py                   # build_theme() + getters
    pages/
      _placeholder.py          # "Page coming soon" placeholder
      import_data.py           # File picker + parse + conflict preview. v2.1: threaded import + loading + toast
      issues.py                # v2.2 redesign: stat chips at top + Pending/Resolved sections + ResolveModal class.
                               # ResolveModal lives at bottom of this file — 720px centered with AI banner,
                               # 4 reason categories, extra input area, live preview, save state machine,
                               # edit mode pre-fill + Delete Resolution with confirm.
      dashboard.py             # Vital/trivia + Coaching + Hall of Late + Weekly/Monthly toggle (v2.0)
      main_database.py         # v2.0: monthly grid 17 cols, skeleton rows, Export+TSV. v2.1: threaded Excel
                               # export + loading + toast. NOTE: Phase C todo list adds Filter dropdown +
                               # Delete bulan button.
      weekly_report.py         # Checklist modal → PDF or Excel. v2.1: threaded exports
      monthly_report.py        # Same as weekly. v2.1: threaded exports
      edit_records.py          # Searchable inline edit + history dialog. v2.1: notify + on_data_changed
      backup_restore.py        # Export/Import ZIP buttons. v2.1: threaded export+import
      settings.py              # Threshold editors with "Off" toggles. v2.1: notify + on_data_changed
    components/
      logo.py                  # hexagon_j() widget (rounded square fallback — true hexagon only in .ico/.svg)
      vital_card.py            # Big colored metric card. NOTE: Phase C todo — make Pending Issues clickable.
      trivia_card.py           # Smaller secondary metric card
      coaching_card.py         # Coaching Required card with medals + streak
      ranking_row.py           # Hall of Late row with medal + bar viz
      checklist_modal.py       # Generic checklist for export selection
      loading_overlay.py       # NEW v2.1: top progress strip + click-blocking dim. Singleton mounted by Shell.
      toast.py                 # NEW v2.1: top-right (top=20, right=20, width=360) translucent solid toast,
                               # max-3 stack, success 1.5s / error 3s auto-dismiss. Singleton mounted by Shell.
  reports/
    pdf_builder.py             # reportlab-based PDF + branded footer (frozen-aware logo path)
    excel_builder.py           # build_raw_excel + build_hall_of_late_excel + build_monthly_sheets_format (17-col v2.0)
    sections/
      vital_section.py
      trivia_section.py
      coaching_section.py
      hall_of_late_section.py
assets/                        # Logo + icons (committed)
data/                          # SQLite + exports (gitignored, runtime-only)
backups/                       # Snapshot JSONs + zip backups (gitignored, runtime-only)
mockups/                       # HTML design references — committed: 01, 03, 05, 06, 07, 08, 09, 10
                               # untracked: 02, 04 (superseded)
                               # NEW v2.1: 08-loading-and-toast.html (3 loading variants × 3 toast variants)
                               # NEW v2.2: 09-issues-resolve-redesign.html (modal vs split panel)
                               #          10-issues-with-status.html (final list + modal — picked design)
docs/
  superpowers/
    specs/                     # Design specs (read these for deep dives)
      2026-05-09-josaphat-tech-attendance-design.md   # v1.0 spec (17 sections)
      2026-05-09-main-db-and-issues-redesign.md       # v2.0 spec (Main DB + bug fixes)
      2026-05-09-loading-and-toast.md                 # v2.1 spec (LoadingOverlay + ToastNotifier)
      2026-05-09-issues-resolve-redesign.md           # v2.2 spec (modal + status list + stats)
    plans/                     # Implementation plans
      2026-05-09-josaphat-tech-attendance.md          # v1.0 plan (23 tasks)
      2026-05-09-main-db-and-issues-redesign.md       # v2.0 plan (12 tasks)
      2026-05-09-loading-and-toast.md                 # v2.1 plan (13 tasks)
      2026-05-09-issues-resolve-redesign.md           # v2.2 plan (10 tasks)
scripts/
  generate_logo.py             # Pillow-based hex J generator (replaces broken svglib approach)
  build_exe.py                 # Helper that calls flet pack with correct flags
tests/
  core/
    test_parser.py             # 12 tests
    test_issue_detector.py     # 15 tests (10 cases + 5 recommend)
    test_resolver.py           # 7 tests
    test_conflict.py           # 8 tests
    test_metrics.py            # 5 tests
    test_settings_store.py     # 6 tests
    test_alasan_format.py      # 20 parametric tests (NEW v2.0)
    test_backup.py             # 2 tests
  db/
    test_repository.py         # 10 tests (was 8 in v2.0; +2 in v2.2 for list_issues_with_resolutions)
  reports/
    test_pdf_builder.py        # 2 tests
    test_excel_builder.py      # 3 tests
  ui/                          # NEW v2.1+; uses MagicMock page + page.overlay = []
    test_shell_cache.py        # 9 tests (v2.1 nav perf cache + invalidate)
    test_loading_overlay.py    # 5 tests (v2.1)
    test_toast.py              # 8 tests (v2.1)
    test_shell_loading_toast.py# 5 tests (v2.1 — Shell delegate methods)
    test_issues_page.py        # 23 tests (v2.2 — list, stat chips, modal, save/edit/delete)
  fixtures/
    sample_apr_1_10.xls        # PII — gitignored, kept LOCAL only
```

---

## Critical Pitfalls (Don't Repeat These Mistakes)

### 1. Run from source: `python main.py`, NOT `python src/main.py` or `python -m src.main`

The entry point is at PROJECT ROOT (not in `src/`). `src/main.py` exists but is a thin compatibility shim. PyInstaller bundles whatever you pass it as the top-level module — packing `src/main.py` produces a broken .exe with `ModuleNotFoundError: No module named 'src'`. **Fix in v1.0.1: moved to root.**

### 2. PyInstaller `--onefile` doesn't bundle data files — use `--add-data`

`schema.sql` and `assets/logo.svg` MUST be passed via `--add-data` flags or the .exe crashes at first DB init / first PDF render with `[Errno 2] No such file or directory`. **Fix in v1.0.2: added flags + frozen-aware path resolvers using `sys._MEIPASS`.**

`scripts/build_exe.py` already handles this correctly. Use it instead of calling `flet pack` manually:

```bash
python scripts/build_exe.py
```

If you ever add NEW data files, add them to the `data_specs` list in `scripts/build_exe.py`.

### 3. `Path` resolution differs in frozen vs source mode

When packaged, `__file__` lives inside the temp `_MEIPASS` extraction dir, not the user's filesystem. **Two helpers exist:**

- `_resolve_schema_path()` in `src/db/repository.py` — uses `sys._MEIPASS / "src/db/schema.sql"` when frozen
- `_user_dir()` and `_bundled_dir()` in `src/reports/pdf_builder.py` — split user-replaceable files (next to .exe) from bundled assets (in temp extract)
- `_resolve_root()` in `main.py` — uses `Path(sys.executable).parent` so `data/`, `config.json`, `backups/` land next to the .exe

If you add a new data file or a new "user override" slot, follow these patterns. Don't use `Path(__file__).parent / "thing"` for any file that needs to be readable in the frozen .exe.

### 4. Flet 0.25.2 dialog API: use overlay, not deprecated `page.dialog`

```python
# ❌ Deprecated (silently does nothing)
page.dialog = my_dialog

# ✅ Correct
page.overlay.append(my_dialog)
my_dialog.open = True
page.update()

# To close: my_dialog.open = False; page.update()
```

Pages that use this pattern: `edit_records.py`, `checklist_modal.py`. Follow the same when adding new dialogs.

### 5. ASCII-only in PDF text strings

ReportLab's default Helvetica font uses WinAnsi encoding which doesn't include emojis or em-dashes. Stick to ASCII + the WinAnsi-safe `·` middle dot for separators. **Don't use:** `→ ↑ ↓ — 🥇 🚨` in PDF strings. (UI text in Flet handles Unicode/emojis fine — only PDF is restricted.)

For trend arrows in PDF, use ASCII text: `"down 12% vs last week"` not `"↓ 12%"`.

### 6. Git env header lies, repo IS git-initialized

Some tool environments report `Is directory a git repo: No` for this directory. **Ignore that header** — `git status`, `git commit`, `git push` all work. Multiple subagents have been confused by this; remind them in the prompt to ignore it.

### 7. Untracked files to leave alone

These three files are untracked intentionally — DO NOT commit them:
- `config.json` — runtime-generated user settings
- `mockups/02-logo-direction.html` — superseded design iteration
- `mockups/04-dashboard-layout.html` — superseded design iteration

Use specific `git add <files>` not `git add .` to avoid grabbing them.

### 8. Test fixtures contain PII — never commit

`tests/fixtures/*.xls` is in `.gitignore`. The fixture file (`sample_apr_1_10.xls`) is a copy of the user's actual fingerprint export with employee names. Tests skip gracefully via `pytest.skip("Fixture not present (PII — kept local)")` when fixture is missing.

### 9. Build artifacts are gitignored

`dist/`, `build/`, `*.spec` are ignored. The .exe is distributed via local file or USB, not git.

### 10. Don't pre-emptively refactor

Lessons from 1.0 and 2.0 reviews repeatedly flagged "good observations but defer". User cares about features that affect HER daily workflow, not code-quality polish. When in doubt, ask before refactoring.

---

## Resolution Codes (11 Options — LOCKED)

| Code | Label | Extra input | Renders as in Sheets |
|---|---|---|---|
| `tugas_lapangan` | Tugas Lapangan | location | "Lapangan ke {loc}" |
| `tugas_paparan` | Tugas Paparan | location | "Tugas Paparan di {loc}" |
| `sakit` | Izin Sakit | — | "Izin Sakit" |
| `cuti` | Cuti | — | "Cuti" or "Cuti, {detail}" |
| `izin_pagi` | Izin Pagi | reason_detail | "Izin Pagi - {detail}" |
| `pulang_awal` | Pulang Lebih Awal | reason_detail | "Pulang Lebih Awal - {detail}" |
| `telat_kerja` | Masuk Terlambat dengan Alasan Pekerjaan | reason_detail | "Masuk Terlambat - {detail}" |
| `telat_personal` | Terlambat | — | "Terlambat" |
| `lupa_absen` | Lupa Absen (terhitung telat 16 menit) | — | "Lupa absen" (lowercase, matches Sheets) |
| `belum_kabar` | Belum Ada Kabar | — | "" (or `reason_detail` text if Main DB inline-edited) |
| `tidak_hadir` (NEW v2.0) | Tidak Hadir | — | "Tidak Hadir" |

The `lupa_absen` code auto-adds `lupa_absen_penalty_minutes` (default 16) to `late_minutes` when applied. Configurable in Settings — can be disabled via "Off" toggle.

`format_alasan(code, location, reason_detail) -> str` in `src/core/alasan_format.py` is the single source of truth for rendering. Used by Main DB cell render, Excel export, Issues live preview.

---

## Issue Cases (7 — LOCKED)

| Case | Condition | Treatment |
|---|---|---|
| **A** | Masuk empty AND Keluar empty | Follow-up list |
| **B** | Masuk empty, Keluar present | Follow-up list |
| **C** | Masuk present, Keluar empty | Follow-up list |
| **D** | `late_minutes > 0 AND < late_threshold` (default 15) | Cell yellow, NO follow-up |
| **E** | `late_minutes >= late_threshold` | Cell red, NO follow-up |
| **F** | `early_leave_minutes > pulang_cepat_threshold` (default 0) | Cell orange + follow-up |
| **G** | `day_type == "Istirahat"` (Sat/Sun) | Stored, excluded from displays |

**3 thresholds support "Off" (set to None):**
- `late_threshold_minutes` → disables D/E classification
- `lupa_absen_penalty_minutes` → disables auto-penalty
- `pulang_cepat_threshold_minutes` → disables F flagging

`coaching_threshold_minutes` (default 75/week) and other settings always required.

---

## Quick Commands

```bash
# Run from source (after pip install -r requirements.txt)
python main.py

# Run all tests (134 expected)
python -m pytest -q

# Rebuild .exe (uses flet pack with --add-data flags)
python scripts/build_exe.py
# → dist/JosaphatTechHR.exe (~98MB)

# Push to remote
git push origin master
git push origin <tag>
```

---

## Recent History (read newest-first)

### v2.2.0 (current) — Issues page modal + status redesign
- 9 tasks (atomic 10) across 1 phase
- +25 tests (134 total — 109 → 134)
- New: 720px centered Resolve modal (replaces 420px right-side panel) — grouped reason categories (Tugas / Cuti·Sakit·Izin / Telat·Lupa / Lain), AI banner inside modal, extra-input area + live preview + save-state machine, edit mode for resolved with Delete Resolution + confirm
- New: Status-aware list with Pending (top) / Resolved (bottom) sections, sort `(r.id IS NULL) DESC, ar.date, e.name`, status badges Pending/Resolved
- New: Stat chips at page top (12 Pending · 9 Resolved · 21 Total) — always visible
- New: Repository.list_issues_with_resolutions returns both sets in one query
- Spec: `docs/superpowers/specs/2026-05-09-issues-resolve-redesign.md`
- Plan: `docs/superpowers/plans/2026-05-09-issues-resolve-redesign.md`
- Mockups: `09-issues-resolve-redesign.html`, `10-issues-with-status.html`

### v2.1.0 — Loading indicators + Toast notifications + Main DB async loading
- 12 tasks across multiple sittings (some bug-fix follow-ups)
- +18 tests baseline + 18 → 109 tests
- New: `LoadingOverlay` (top progress strip + click-blocking dim) for slow ops
- New: `ToastNotifier` (top-right 360px translucent solid toast, max-3 stack, 1.5s success / 3s error auto-dismiss)
- Threading wrap on Import / Export PDF/Excel / Backup / Restore — UI thread shows loading immediately, work runs in worker thread
- Main DB async first-load (background thread builds widget tree, loading overlay visible)
- **CRITICAL FIX:** `sqlite3.connect(check_same_thread=False)` — prior cross-thread DB pattern (issues.py `_schedule_refresh`) had been silently failing since v2.0; surfaced now because v2.1.0 added error toasts. Fix in `src/db/repository.py:Repository.__init__`.
- Toast position adjusted multiple times: top-right 280px → bottom-left → finally **top=20, right=20, width=360** with `expand=True` on inner Column for text wrap (long error messages were getting clipped)
- Per-page perf fix: Shell `_navigate` swaps `content_area.content` only + caches built page Controls + invalidates on data mutation. Reduced nav from 5-10s freeze to sub-second.
- Spec: `docs/superpowers/specs/2026-05-09-loading-and-toast.md`
- Plan: `docs/superpowers/plans/2026-05-09-loading-and-toast.md`
- Mockup: `08-loading-and-toast.html`

### v2.0.0 — Main DB, Dashboard default, Issues redesign
- 12 tasks across 5 phases
- 30 new tests (88 total)
- New: Main Database page (17-col grid matching user's Sheets), AI recommendation in Issues, Tidak Hadir reason code (11th)
- Fixed: Issues navbar stale text bug, Dashboard always-empty default, conflict resolver clobbering resolved records
- Spec: `docs/superpowers/specs/2026-05-09-main-db-and-issues-redesign.md`
- Plan: `docs/superpowers/plans/2026-05-09-main-db-and-issues-redesign.md`

### v1.0.2 — Bundle data files
Fixed `[Errno 2] schema.sql` crash by adding `--add-data` flags + frozen-aware path resolvers.

### v1.0.1 — Move main.py to root
Fixed `ModuleNotFoundError: No module named 'src'` crash by relocating entry point.

### v1.0.0 — Initial release
23 tasks, ~3000 lines, 58 tests, .exe ~94MB. Full v1.0 design covered import → resolve → dashboard → reports → backup pipeline.

---

## Open Items (Deferred — Not Bugs)

### Outstanding work — user surfaced these on 2026-05-09 after v2.2.0 ship

**Decomposed into 4 phases** for separate spec/plan/release cycles:

#### Phase A — Bug fixes (URGENT, do first) — would be **v2.2.1**
- **A1: Issues Resolve modal content terpotong + tidak bisa di-scroll.** Mockup ke-10 pakai `_dialog` dengan `_body_placeholder` → ketika reason categories + extra input + live preview combined exceed viewport, content cut off. Fix: wrap modal body in `ft.Column(scroll=ft.ScrollMode.AUTO)` or set explicit `max_height` on outer card with internal scroll container.
- **A2: Issues sort priority salah.** Currently `ORDER BY (r.id IS NULL) DESC, ar.date, e.name` (status → date → name). User wants **status → name → date** so issues per employee group together. Fix: edit SQL in `Repository.list_issues_with_resolutions` to `ORDER BY (r.id IS NULL) DESC, e.name, ar.date`.

#### Phase B — General Design (palette migration) — would be **v2.3.0**
User-supplied palette to replace current "Sunset Coral":
- `#1E104E` (dark navy) → maps to `bg_dark` (was `#1a0b2e`)
- `#452E5A` (muted purple) → maps to `surface_dark` (was `#2d1b4e`)
- `#FF653F` (vivid orange) → replaces `primary` (was `#7C3AED` purple)
- `#FFC85C` (warm yellow) → replaces `accent` (was `#F472B6` pink) AND `highlight`

Semantic colors NOT in user-supplied palette — keep as-is:
- `resolved` `#34D399` (success green)
- `late_severe` `#F87171` (error red)
- `late_mild` `#FCD34D` (mild yellow — overlaps with new accent — may need disambiguation)
- `pulang_cepat` `#C084FC` (lavender — clashes with new primary orange? double-check visually)

Affected files: `src/core/constants.py:COLORS`, all UI pages (most just use COLORS dict), mockups for next phases should use new palette.

#### Phase C — Quick wins (3 small features) — would be **v2.4.0**
- **C1: Dashboard Pending Issue clickable → nav ke Issues di minggu terkait.** Currently clicking the vital_card does nothing. Add `on_click` that calls `nav_callback("issues")` AND passes the current Dashboard period (start/end) to Issues so it opens at the SAME week, not Issues' current default. Need to add a way to pass period — options: (a) IssuesPage accepts optional `start, end` ctor params; Shell stores last-set period and passes; (b) add a `set_period(start, end)` method on IssuesPage and Shell calls it before navigation.
- **C2: Main DB — Delete bulan dengan konfirmasi.** Add a button "🗑 Hapus data bulan {month_name}" to Main DB toolbar. Click → AlertDialog "Apakah anda yakin? Semua attendance + resolutions di bulan {month} akan dihapus dan tidak bisa di-undo." → Hapus → call new `Repository.delete_month(year, month)` that deletes from `attendance_records` (cascade FK should cascade to `resolutions`). Refresh main_db + invalidate caches + toast.
- **C3: Main DB — Filter by employee + Show All toggle.** Add `ft.Dropdown` on toolbar with options ["Semua karyawan"] + each active employee. On change, set `self.employee_filter = staff_no` and `_refresh_table()`. The dropdown default is "Semua karyawan". Existing `list_monthly_grid` already accepts `staff_no_filter` param — just wire UI to it.

#### Phase D — Import redesign (biggest UI work) — would be **v2.5.0**
User wants git-style conflict resolution:
- **D1: Detail compare** — show row-by-row diff between existing main DB rows for the period vs incoming .xls rows. Highlight which fields differ.
- **D2: Center the import button** — current Import Data page has empty space; reposition button + add visual hierarchy.
- **D3: Resolve conflict one-by-one** — instead of bulk KEEP_EXISTING / OVERWRITE policies, let user step through each conflicted row and pick.
- **D4: Side-by-side compare design** — left panel = existing row, right panel = incoming row, conflicting fields highlighted in yellow/red. User clicks "← keep existing" or "use new →" per field, or "keep both rows" (impossible with UNIQUE(employee_id, date) constraint — so per-field merge actually).

This is the largest scope. Will require its own brainstorm + mockups + spec + 8-12 task plan.

### Pre-existing deferred items (older)

From v2.0 final review, flagged but not fixed (waiting for user clarification):
1. **Main DB grid vs Monthly Report**: produce different row counts for "the same month" (Main DB = full 30-day skeleton, Monthly Report = only imported days). Probably intentional — user should confirm if she wants byte-for-byte equivalence.
2. **"Total Personal:" separator rows**: User's actual Sheets reference has them per-employee, but our 17-col exporter writes flat row sequence. Easy to add if requested.

From v1.0 final review (still pending):
3. Dead code in `src/ui/theme.py` (helpers never imported — could delete)
4. Hardcoded `streak=4` placeholder in coaching cards (should compute actual streak from `repeat_offender_weeks` setting)
5. Minimum window width not set (resizing too narrow breaks 4-card row)
6. Dialog memory leak (added to `page.overlay`, never removed in `_close_dialog`) — flagged again in v2.2.0 final review

### Pitfall notes added during v2.1/v2.2 work

- **`page.overlay.append(dialog)` from a method NOT in the Shell**: needs `ft.Page` reference. Pattern: pass `page` as ctor arg (see how Issues page accepts it in v2.2.0 — `IssuesPage.__init__(page, ...)`). Shell passes `self.page` from its `_build_*_page` builders.
- **Cross-thread DB access**: `check_same_thread=False` is now set in `Repository.__init__`. Existing `issues.py:_schedule_refresh` Timer pattern works correctly now. Don't try to "fix" by removing the flag — it'll re-introduce the v2.1 import-fails bug.
- **Test pattern for pages with modals on `page.overlay`**: use `MagicMock()` page with `page.overlay = []` so `.append()` works. See `tests/ui/test_issues_page.py` fixture.

---

## When User Asks for a New Feature

1. **Use brainstorming skill** (`superpowers:brainstorming`) — don't go straight to code
2. **Generate visual mockups** for UI questions (HTML files in `mockups/`, double-clickable)
3. Show 2-3 alternatives even when she gave a directional hint (she sometimes flips after seeing visuals)
4. **Write spec** to `docs/superpowers/specs/YYYY-MM-DD-<topic>.md`
5. **Get user approval** before invoking writing-plans
6. **Write plan** to `docs/superpowers/plans/YYYY-MM-DD-<topic>.md`
7. **Execute via subagent-driven-development** — fresh subagent per task
8. **Each task: TDD for logic** (failing test first), **manual verify for UI**
9. **Commit per task** with conventional-commit messages
10. **After all tasks: tag**, push to remote, rebuild .exe

User explicitly authorized direct-to-master commits early in v1.0 ("OK lanjut bisa dieksekusi sekarang"). No feature branches needed for solo work.

---

## When User Reports a Bug

1. Ask for screenshot if visual
2. Diagnose root cause before proposing fix (don't guess)
3. If bug is in v2.0 path-resolution / flet API / conflict logic: check existing pitfalls section above first
4. Fix → test → commit → optionally bump patch version (e.g. v2.0.1)
5. Push + rebuild .exe so user can test new version

---

## Useful Read-Targets for Deep Dives

| Want to know | Read |
|---|---|
| Why we picked Flet over CustomTkinter/PyQt6 | `docs/superpowers/specs/2026-05-09-josaphat-tech-attendance-design.md` §2 |
| Full v1.0 architecture | Same spec, all sections |
| 17-col Sheets format | `docs/superpowers/specs/2026-05-09-main-db-and-issues-redesign.md` §4 + actual ref at `D:\Gawe\Dani\PT Tekno\Laporan Bulanan April.xlsx` |
| User's design preferences (subtle vs bold flip) | `mockups/05-dashboard-bold.html` (final dashboard look) |
| Issue cases + treatments rationale | v1.0 spec §6 + this file's "Issue Cases" section |
| Why backup uses snapshots not git | v1.0 plan Task 21 |

---

**End of context file.** Use the brainstorming skill if user wants new features. Use systematic-debugging skill if user reports a bug. Always invoke superpowers (using-superpowers skill) at session start.
