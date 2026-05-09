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
                 exports_dir: str, mode: str = "dark",
                 on_data_changed=None,
                 show_loading=None, hide_loading=None, notify=None):
        self.repo = repo
        self.settings = settings
        self.exports_dir = Path(exports_dir)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.mode = mode
        self.on_data_changed = on_data_changed
        self.show_loading = show_loading
        self.hide_loading = hide_loading
        self.notify = notify
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
