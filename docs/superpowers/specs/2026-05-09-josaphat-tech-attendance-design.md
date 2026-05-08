# Josaphat Tech Solution — HR Attendance Manager

**Design Specification**
Date: 2026-05-09 · Status: Draft for review · Version: 1.0-spec

---

## 1. Overview

A single-user Windows desktop application that automates the weekly and monthly attendance reporting workflow at PT Tekno. The fingerprint export (.xls) is parsed, attendance issues are detected and resolved through a guided UI, and reports are generated in formats that match the existing shared Google Sheets.

### Goals

- Cut weekly attendance review time from hours to minutes.
- Surface follow-up items (missing clock-ins, missing clock-outs, full absences) so HR can chase them via WhatsApp without combing the spreadsheet manually.
- Track resolutions (10 reason categories) so the monthly report writes itself.
- Show a dashboard that makes lateness patterns visible and actionable, including coaching candidates.

### Non-goals

- No multi-user support, no cloud sync, no authentication.
- No real-time integration with the fingerprint device — input is the existing .xls export.
- No mobile app.
- WhatsApp follow-up itself is **out of scope** — HR keeps that conversation manual to preserve the personal tone.

### Success criteria

- Weekly Friday review for ~30 employees finishes in under 30 minutes.
- All 10 resolution categories supported, including the 3 with extra inputs.
- Monthly report Excel output is byte-paste-able into the shared Google Sheets without reformatting.
- Coaching threshold and lateness thresholds editable in Settings (no code change).

---

## 2. Tech Stack & Distribution

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.13 | Already installed; user has basic Python familiarity |
| GUI | **Flet** | Material Design 3, dark/light theme built-in, modern look |
| Excel parsing (input) | `xlrd` (.xls), `openpyxl` (.xlsx) | Industry standard |
| Excel writing (output) | `openpyxl` | Required for styled Excel + cell coloring |
| PDF generation | `reportlab` | Mature, full layout control, embeddable images for branding |
| Charts | Flet's built-in chart components + `matplotlib` for PDF | Flet for live UI; matplotlib for static PDF embedding |
| Database | **SQLite** (single file) | Zero setup, easy backup (copy file), no server |
| Packaging | `flet pack` (wraps PyInstaller) | Single .exe portable |

**Distribution model:**
- Single-file portable `.exe` (~80–100 MB, includes Flutter runtime).
- All dependencies bundled — no Python install needed on target machine.
- Zero installer; user double-clicks the .exe to run.
- Settings + database stored next to the .exe in `data/` and `config.json` (so backup = copy folder).
- **.exe icon, taskbar icon, window title bar icon, and Alt-Tab icon all use the Hexagon J logo** for visual consistency with the in-app sidebar logo and PDF footer mark.

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Flet UI (single window)                  │
│  ┌──────────┬──────────────────────────────────────────┐    │
│  │ Sidebar  │  Routed pages:                           │    │
│  │ Nav      │  - Import Data                           │    │
│  │ + Theme  │  - Issues (follow-up list + resolve)     │    │
│  │ Toggle   │  - Dashboard (vital, trivia, coaching,   │    │
│  │ + Logo   │    Hall of Late, charts)                 │    │
│  │          │  - Weekly Report (export modal)          │    │
│  │          │  - Monthly Report (export modal)         │    │
│  │          │  - Edit Records                          │    │
│  │          │  - Backup / Restore                      │    │
│  │          │  - Settings                              │    │
│  └──────────┴──────────────────────────────────────────┘    │
└──────────────────┬──────────────────────────────────────────┘
                   │
       ┌───────────┴───────────┐
       │   Application core    │
       │  ┌─────────────────┐  │
       │  │ Excel Parser    │  │  Reads .xls, normalizes rows
       │  ├─────────────────┤  │
       │  │ Issue Detector  │  │  Classifies each workday row
       │  ├─────────────────┤  │
       │  │ Resolution Mgr  │  │  Stores reasons + edits
       │  ├─────────────────┤  │
       │  │ Metrics Engine  │  │  Aggregates for dashboard
       │  ├─────────────────┤  │
       │  │ Report Generator│  │  PDF (reportlab) + Excel (openpyxl)
       │  ├─────────────────┤  │
       │  │ Conflict / Ver. │  │  Versioning + rollback
       │  ├─────────────────┤  │
       │  │ Settings Store  │  │  Reads/writes config.json
       │  └─────────────────┘  │
       └──────────┬────────────┘
                  │
       ┌──────────┴────────────┐
       │  SQLite (data/app.db) │
       │  + config.json        │
       │  + backups/           │
       └───────────────────────┘
```

Each module sits behind a clean Python interface (a class or module with documented public functions). UI never queries SQLite directly — it goes through a service layer.

---

## 4. Data Model (SQLite)

### `employees`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PRIMARY KEY | |
| staff_no | TEXT UNIQUE | e.g. "1002" |
| name | TEXT NOT NULL | e.g. "ANDIKA" |
| department | TEXT | e.g. "ARGA DIRGA" |
| active | INTEGER DEFAULT 1 | Soft delete |
| created_at | TEXT | ISO timestamp |

### `attendance_records`
One row per (employee, date).

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PRIMARY KEY | |
| employee_id | INTEGER FK | |
| date | TEXT NOT NULL | ISO date `YYYY-MM-DD` |
| day_name | TEXT | "Senin", etc. |
| day_type | TEXT | "Hari Kerja" or "Istirahat" |
| schedule_in | TEXT | e.g. "08:00" |
| schedule_out | TEXT | e.g. "16:00" |
| actual_in | TEXT | e.g. "08:06" or NULL |
| actual_out | TEXT | e.g. "16:41" or NULL |
| late_minutes | INTEGER | from fingerprint "Terlambat" |
| early_leave_minutes | INTEGER | from fingerprint "Pulang Cepat" |
| work_hours | REAL | from "Kerja" |
| overtime_hours | REAL | from "Lembur" |
| absent_flag | INTEGER | from "Absen" |
| forgot_punch_flag | INTEGER | from "Lupa in/out" |
| issue_case | TEXT | A/B/C/D/E/F/G/null — see §6 |
| import_batch_id | INTEGER FK | which import batch produced this row |
| UNIQUE(employee_id, date) | | |

### `resolutions`
One row per resolved issue, linked 1:1 to `attendance_records`.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PRIMARY KEY | |
| record_id | INTEGER FK UNIQUE | |
| reason_code | TEXT | one of 10 options (see §7) |
| location | TEXT | for Tugas Lapangan / Tugas Paparan |
| reason_detail | TEXT | for Izin Pagi / Pulang Lebih Awal / Masuk Terlambat alasan kerja |
| resolved_at | TEXT | ISO timestamp |
| edited_at | TEXT | last edit timestamp |
| edit_count | INTEGER DEFAULT 0 | |

### `import_batches`
Tracks every .xls import for versioning and rollback.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PRIMARY KEY | |
| filename | TEXT | original .xls name |
| imported_at | TEXT | timestamp |
| date_range_start | TEXT | earliest date in batch |
| date_range_end | TEXT | latest date in batch |
| rows_inserted | INTEGER | new records |
| rows_kept | INTEGER | conflicts kept |
| rows_overwritten | INTEGER | conflicts overwritten |
| snapshot_path | TEXT | path to pre-import snapshot for rollback |

### `record_history` (versioning)
Every overwrite or resolution edit copies the previous state here.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PRIMARY KEY | |
| record_id | INTEGER FK | |
| changed_field | TEXT | "actual_in", "resolution.reason_code", etc. |
| old_value | TEXT | |
| new_value | TEXT | |
| changed_at | TEXT | |
| changed_by | TEXT | "import" / "user-edit" / "rollback" |
| batch_id | INTEGER FK NULL | if change came from an import |

---

## 5. Excel Parser

**Input format:** the fingerprint export (.xls) has 22 columns, header on row 0, units on row 1, data from row 2. Each employee block ends with a "Total Personal:" separator row (skip those). Sample reference: `D:\Gawe\Dani\PT Tekno\April week 1&2 ; 1-10 april.xls`.

**Format quirks:**
- Decimal separator is comma: `7,9` → 7.9
- Time format is `HH.MM` (period, not colon): `08.06`
- Date format is `DD/MM/YYYY`: `01/04/2026`
- Empty cells → `None`

**Parsing steps:**

1. Open with `xlrd`.
2. Skip rows where col[0] starts with "Total Personal" or is empty.
3. Normalize each row into a dict matching the `attendance_records` schema.
4. Convert dates, times, decimals.
5. Run Issue Detector (§6) to assign `issue_case`.
6. Hand off to Conflict Resolver (§10) before writing to DB.

**Edge cases:**
- Sabtu/Minggu rows where `day_type == "Istirahat"` → store with `issue_case = "G"` (skip in dashboards/reports).
- Holiday rows (no schedule) → same as Istirahat.
- Employees not in DB yet → auto-create entry in `employees`.

---

## 6. Issue Detection — 7 Cases, 3 Treatments

| Case | Condition | Treatment |
|---|---|---|
| **A** | `actual_in` empty AND `actual_out` empty (workday) | Follow-up list |
| **B** | `actual_in` empty, `actual_out` filled | Follow-up list |
| **C** | `actual_in` filled, `actual_out` empty | Follow-up list |
| **D** | `late_minutes > 0` AND `late_minutes < late_threshold` (default 15) | Cell color: **yellow** · NO follow-up |
| **E** | `late_minutes >= late_threshold` (default 15) | Cell color: **red** · NO follow-up |
| **F** | `early_leave_minutes > pulang_cepat_threshold` (default 0) | Cell color: **orange** · YES follow-up |
| **G** | `day_type == "Istirahat"` | Stored with `issue_case = "G"`; excluded from dashboards, Issues list, and reports |

**Threshold-null behavior:**
- If `late_threshold_minutes` is null in settings → cases D and E never trigger; late minutes still recorded but no cell color.
- If `pulang_cepat_threshold_minutes` is null → case F never triggers; `early_leave_minutes` still recorded but no flag.
- If `lupa_absen_penalty_minutes` is null → choosing the "Lupa Absen" resolution does not auto-add the penalty.

**Treatments:**

1. **Follow-up only** (A, B, C): appears in Issues list, no cell color.
2. **Cell color only** (D, E): displayed colored in tables, never enters Issues list.
3. **Both** (F): displayed colored AND enters Issues list.
4. **Skip** (G): excluded from displays/reports.

A single record can have multiple flags (e.g. case B + late). The Issues list shows whatever needs follow-up; cell coloring is independent.

---

## 7. Resolution — 10 Options

| # | Code | Label | Extra input |
|---|---|---|---|
| 1 | `tugas_lapangan` | Tugas Lapangan | Lokasi (text) |
| 2 | `tugas_paparan` | Tugas Paparan | Lokasi (text) |
| 3 | `sakit` | Izin Sakit | — |
| 4 | `cuti` | Cuti | — |
| 5 | `izin_pagi` | Izin Pagi | Alasan (text) |
| 6 | `pulang_awal` | Pulang Lebih Awal | Alasan (text) |
| 7 | `telat_kerja` | Masuk Terlambat dengan Alasan Pekerjaan | Alasan (text) |
| 8 | `telat_personal` | Terlambat | — |
| 9 | `lupa_absen` | Lupa Absen (terhitung telat 16 menit) | — |
| 10 | `belum_kabar` | Belum Ada Kabar | — (default for unresolved) |

**Resolution UI flow:**

1. From Issues page, click an issue row → side panel opens.
2. Choose reason from 10-option grid (with icons).
3. If reason needs extra input, a text field appears below.
4. Save → record marked resolved, vanishes from pending list. To see resolved items, switch the page filter to "All" or "Resolved".
5. Edit Records page lets user revisit + change any past resolution. Old values go to `record_history`.

**`lupa_absen` special behavior:**
When chosen, app auto-adds 16 minutes to `late_minutes` (configurable via settings; can be disabled, see §11).

---

## 8. UI Screens

### Layout shell
- **Left sidebar** (240px): logo (Hexagon J + "Josaphat Tech Solution" + tagline), nav grouped into Workflow / Reports / Tools, theme toggle at bottom.
- **Top bar of each page**: page title + page-level actions (e.g. Export buttons).
- **Main content** below.

### Pages

1. **Import Data** — drag-drop or browse for .xls; preview new records before commit; show conflict resolution dialog if overlap detected.
2. **Issues** — table of pending follow-ups (cases A/B/C/F unresolved). Filter by employee/date. Click row → resolve panel.
3. **Dashboard** — see §9.
4. **Weekly Report** — preview + export modal.
5. **Monthly Report** — preview + export modal (Excel matches Google Sheets format; PDF designed).
6. **Edit Records** — searchable table of all attendance records. Editable fields: `actual_in`, `actual_out`, and the linked resolution (reason + location/detail). Day type, schedule, and late/early minutes are read-only (computed from raw times). Every edit writes prior values to `record_history` with `changed_by = "user-edit"`. Per-row history button shows full change log with field-level rollback.
7. **Backup / Restore** — one-click "Export everything" (zips db + config + custom assets) and "Import backup" for laptop migration.
8. **Settings** — see §11.

---

## 9. Dashboard — Maximum Bold Tone

**Period selector** at top (default: current week).

### Vital Metrics (4 prominent cards, top row)

| Card | Color accent | Source |
|---|---|---|
| ⚠️ Pending Issues | red | Count of unresolved A/B/C/F this week |
| 🚨 Need Coaching | pink | Employees over coaching threshold this week |
| 🔥 Repeat Offenders | orange | Employees late ≥3 weeks in a row |
| ✅ Attendance Rate | green | (workdays attended / total workdays) × 100 |

### Trivia & Insights (4 smaller cards, second row)

| Card | Source |
|---|---|
| 🏷️ Most Common Reason | Top resolution code by count |
| 📅 Hari Paling Telat | Day-of-week with highest total `late_minutes` |
| 📈 Late Trend | % change vs previous week |
| 🌟 Best Performer | Employee with 0 late + 0 issues this week |

### 🚨 COACHING REQUIRED (Maximum Bold visual)

- Pink-bordered section with shimmer animation on top edge.
- "ACTION NEEDED" badge that pulses red.
- Cards per employee over threshold:
  - 🥇🥈 medal for #1 / #2 / #3
  - Big red number for total late minutes
  - Stats: hari telat, avg/hari, weekly streak (with 🔥 if multi-week)

### ⏰ HALL OF LATE — Top 5 (default)

- Ranked list with medal icons for top 3.
- Border-left color and bar gradient progressively bolder for higher ranks.
- 🔥 icon next to name for repeat offenders (≥3 weeks).
- "Show All Employees →" button at bottom → opens Full Ranking page (sortable, filterable, paginated).

### Charts (bottom row)

- 📈 Tren issue 4 minggu terakhir (bar chart).
- 🥧 Distribusi alasan issue minggu ini (legend list with colored dots).

---

## 10. Reports & Export

### Per-section export (inline buttons in section headers)

Only **Hall of Late** has its own inline export buttons:
- 📤 Export PDF (designed)
- 📊 Export Excel (raw)

Other sections (Vital Metrics, Trivia, Coaching Required, Charts) do not have inline buttons — they are exported through the page-level modal below.

### Page-level export (top-right of Dashboard)

Two buttons: **📤 Export Weekly** and **📆 Export Monthly**.

Click opens a modal with a checklist of content groups (vital metrics, trivia, coaching section, Hall of Late ranking with Top-N selector, trend chart, distribusi chart, per-employee breakdown). User picks PDF designed or Excel raw, then "Generate Report".

### Monthly Report

**Excel output:** column structure must match the shared Google Sheets exactly (1:1) so HR can copy-paste into the live sheet at end of month. **Open question:** the exact column layout of the Sheets is not yet captured — HR will share a screenshot or .xlsx export of the Sheets structure during implementation.

**PDF output:** branded design with:
- Cover page (month, period, summary stats)
- Per-employee monthly summary
- Coaching summary (who needed coaching this month)
- Trend chart over the month
- Department/team breakdown
- Same checklist-driven content selection

### Branding on every PDF

Footer on every page: small Hexagon J logo + "Powered by Josaphat Tech Solution · HR Attendance Manager · v[X.Y]" centered. Subtle muted text, ~9-10pt.

---

## 11. Configurable Settings

All read from `config.json`, editable via Settings page. Changes apply immediately.

| Setting | Default | Type | "Off" allowed? |
|---|---|---|---|
| `coaching_threshold_minutes` | 75 | int (per week) | No (always required) |
| `late_threshold_minutes` | 15 | int or `null` | **Yes — `null` disables late cell coloring** |
| `lupa_absen_penalty_minutes` | 16 | int or `null` | **Yes — `null` disables auto-penalty** |
| `pulang_cepat_threshold_minutes` | 0 | int or `null` | **Yes — `null` disables Pulang Cepat flagging** |
| `working_hours_start` | "08:00" | time | No |
| `working_hours_end` | "16:00" | time | No |
| `workdays` | ["Mon","Tue","Wed","Thu","Fri"] | array | No |
| `theme` | "dark" | "dark" or "light" | — |
| `repeat_offender_weeks` | 3 | int | No |

Settings page has tooltips explaining each value and shows the current effective threshold prominently.

---

## 12. Conflict Resolution & Versioning

### When new import overlaps existing data

For each (employee, date) already in DB:

- **Default action: keep existing.** New row is discarded for that record; user gets a count summary at end.
- **User can choose "Overwrite" per-row** in a conflict dialog: shows side-by-side comparison (existing vs new), check boxes per row.
- Every overwritten record's old values go to `record_history` with `changed_by = "import"` and `batch_id`.

### Pre-import snapshot

Before any import that has conflicts, a snapshot of affected records is saved (`backups/snapshot_<batch_id>.json`). The Backup/Restore page lists recent snapshots with "Rollback this batch" button.

### Resolution edits

Editing an existing resolution writes the old reason/location/detail to `record_history` with `changed_by = "user-edit"`. Edit count increments. Edit Records page can roll back individual fields.

---

## 13. Backup & Restore (laptop migration)

- **Export backup**: zips `data/app.db` + `config.json` + last N snapshots into `josaphat-backup-YYYY-MM-DD.zip`.
- **Import backup**: prompts user, validates zip structure, replaces current data folder after explicit confirmation. Existing data is moved to `backups/pre-restore-<timestamp>/` (not deleted).

User flow when moving to a new laptop:
1. On old laptop: Backup → Export → save zip to USB / cloud drive.
2. On new laptop: install .exe, open app, Backup → Import → pick zip.
3. Done. All resolutions, history, settings preserved.

---

## 14. Branding & Visual Design

- **Brand:** Josaphat Tech Solution
- **Tagline:** HR Attendance Manager (editable in `config.json`)
- **Logo:** Hexagon J with purple→pink gradient (matches palette primary→accent)
- **Palette: Sunset Coral**
  - Primary: `#7C3AED` · Accent: `#F472B6` · Highlight: `#FBBF24`
  - Resolved: `#34D399` · Late mild: `#FCD34D` · Late severe: `#F87171` · Pulang cepat: `#C084FC`
- **Light mode background:** `#faf5ff` (with `#1e1b4b` text)
- **Dark mode background:** `#1a0b2e` (with `#e9d5ff` text)
- **Logo on PDFs:** small hex J + wordmark in footer, "Powered by Josaphat Tech Solution"

**Logo asset deliverables** (all the same Hexagon J design, generated during implementation):
- `assets/icon.ico` — Windows icon, multi-resolution (16, 32, 48, 64, 128, 256 px). Used by `flet pack --icon`.
- `assets/logo.png` — PNG at multiple sizes (1×, 2×, 3×) for in-app use.
- `assets/logo.svg` — vector for crisp rendering at any size; embedded in PDF footer.
- `assets/logo-custom.svg` (optional) — if user drops a custom logo here, app prefers it over the built-in placeholder.

Reference mockups (kept in repo):
- `mockups/01-color-palette.html` — palette comparison
- `mockups/03-logo-josaphat-solution.html` — logo direction (variant 4 selected)
- `mockups/05-dashboard-bold.html` — final dashboard direction

---

## 15. File Structure (proposed)

```
Human Resource App/
├── src/
│   ├── main.py                    # Flet app entry
│   ├── ui/
│   │   ├── shell.py               # Sidebar + routing
│   │   ├── pages/
│   │   │   ├── import_data.py
│   │   │   ├── issues.py
│   │   │   ├── dashboard.py
│   │   │   ├── weekly_report.py
│   │   │   ├── monthly_report.py
│   │   │   ├── edit_records.py
│   │   │   ├── backup_restore.py
│   │   │   └── settings.py
│   │   └── components/            # Reusable: cards, buttons, modals
│   ├── core/
│   │   ├── parser.py              # Excel parser
│   │   ├── issue_detector.py      # Rules for cases A-G
│   │   ├── resolver.py            # Resolution CRUD
│   │   ├── metrics.py             # Aggregations for dashboard
│   │   ├── conflict.py            # Versioning + rollback
│   │   └── settings_store.py      # config.json read/write
│   ├── reports/
│   │   ├── pdf_builder.py         # reportlab-based PDF
│   │   ├── excel_builder.py       # openpyxl-based Excel
│   │   └── templates/             # Static layout pieces
│   └── db/
│       ├── schema.sql             # Initial DDL
│       └── repository.py          # SQLite access layer
├── assets/
│   ├── icon.ico                   # Hex J — Windows .exe + taskbar + title bar
│   ├── logo.svg                   # Hex J vector — PDF footer + in-app
│   ├── logo-256.png               # Hex J raster — splash screen
│   └── logo-custom.svg            # OPTIONAL — user-provided real logo (overrides built-in)
├── data/                          # gitignored — runtime data
│   ├── app.db
│   └── exports/
├── backups/                       # gitignored — snapshots
├── mockups/                       # design references (committed)
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-05-09-josaphat-tech-attendance-design.md
├── config.json                    # editable settings
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 16. Out of Scope (explicit)

- Multi-user / shared editing
- Cloud sync (Google Sheets API, Dropbox, etc.)
- Web or mobile interface
- Direct integration with the fingerprint device (USB/network)
- Automated WhatsApp messaging — HR keeps that human
- Payroll calculations
- Leave balance tracking (only records that leave was the reason)
- Authentication / login

---

## 17. Open Items (need user input during implementation)

1. **Google Sheets format**: HR will share a screenshot or .xlsx export of the existing shared Sheets so the Monthly Excel output matches column-for-column.
2. **Real logo asset**: HR will eventually provide the real Josaphat Tech Solution logo to replace the placeholder Hex J. The logo loading should look for `assets/logo-custom.svg` first; fallback to built-in placeholder.
3. **Remote git URL**: HR will share GitHub/GitLab repo URL when ready to push.
