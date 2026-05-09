import flet as ft
from datetime import date
from pathlib import Path
from calendar import monthrange
from src.core.constants import COLORS
from src.db.repository import Repository
from src.core.settings_store import SettingsStore
from src.ui.components.checklist_modal import show_checklist_modal


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
        self.status_text = ft.Text("Pilih konten dan format export.", size=13, opacity=0.7)

    @property
    def start(self) -> date:
        return date(self.year, self.month, 1)

    @property
    def end(self) -> date:
        return date(self.year, self.month, monthrange(self.year, self.month)[1])

    def build(self) -> ft.Control:
        return ft.Container(
            padding=28, expand=True,
            content=ft.Column(spacing=18, controls=[
                ft.Text("Monthly Report", size=28, weight=ft.FontWeight.W_800),
                ft.Text(f"Period: {self.start} -> {self.end}", size=13, opacity=0.7),
                ft.ElevatedButton(
                    "Export Monthly Report",
                    icon=ft.Icons.CALENDAR_MONTH,
                    on_click=lambda e: self._open_modal(e.page),
                    bgcolor=COLORS["accent"], color="white",
                ),
                self.status_text,
                ft.Container(height=12),
                ft.Text(
                    "Note: Excel '1:1 with Google Sheets' uses a default column layout. "
                    "HR will share the live Sheets format during integration to align exactly.",
                    size=11, italic=True, opacity=0.6,
                ),
            ]),
        )

    def _open_modal(self, page: ft.Page):
        show_checklist_modal(
            page, "Export Monthly Report", self._generate,
            include_monthly_extras=True,
        )

    def _generate(self, selected: dict, fmt: str):
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
        ranking_full = hall_of_late(self.repo, self.start.isoformat(), self.end.isoformat())
        top_n = selected.get("hall_top_n", "5")
        ranking = ranking_full if top_n == "All" else ranking_full[:int(top_n)]

        try:
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
            self.status_text.value = f"Generated: {output}"
        except Exception as exc:  # noqa: BLE001
            self.status_text.value = f"Failed to generate report: {exc}"
        self.status_text.update()

    def _build_pdf(self, output, selected, summary, coaching, repeat_set, ranking,
                   coaching_thr, repeat_count):
        from src.reports.pdf_builder import PdfReportBuilder
        from src.reports.sections.vital_section import render_vital
        from src.reports.sections.coaching_section import render_coaching
        from src.reports.sections.hall_of_late_section import render_hall_of_late

        # ASCII-only strings (Helvetica WinAnsi cannot render em-dash / arrows reliably)
        builder = PdfReportBuilder(
            title=f"Monthly Attendance Report - {self.start.strftime('%B %Y')}",
            subtitle=f"Period: {self.start} - {self.end}",
            version="1.0",
        )

        if any(selected.get(k) for k in
               ("vital_pending", "vital_coaching", "vital_repeat", "vital_attendance")):
            builder.add_section("vital", render_vital({
                "pending_issues": summary["pending_issues"] if selected.get("vital_pending") else 0,
                "resolved_issues": summary["resolved_issues"],
                "total_issues": summary["total_issues"],
                "need_coaching": len(coaching) if selected.get("vital_coaching") else 0,
                "coaching_threshold": coaching_thr,
                "repeat_offenders": repeat_count if selected.get("vital_repeat") else 0,
                "attendance_rate": summary["attendance_rate"] if selected.get("vital_attendance") else 0,
                "trend_text": "Monthly summary",
            }))

        if selected.get("section_coaching"):
            cards = [{
                "name": c["name"],
                "total_late": c["total_late"],
                "days_late": c["days_late"],
                "avg_per_day": c["total_late"] // c["days_late"] if c["days_late"] else 0,
                "streak": 4 if c["staff_no"] in repeat_set else 0,
            } for c in coaching]
            builder.add_section("coaching", render_coaching(cards))

        if selected.get("section_hall"):
            builder.add_section(
                "hall",
                render_hall_of_late(ranking, coaching_thr, repeat_set),
            )

        builder.save(output)

    def _build_sheets_format_excel(self, output):
        from src.reports.excel_builder import build_monthly_sheets_format

        rows = self.repo.list_attendance_with_resolutions(
            self.start.isoformat(), self.end.isoformat(), search="",
        )
        normalized = [{
            "date": r["date"],
            "name": r["employee_name"],
            "staff_no": r["staff_no"],
            "actual_in": r["actual_in"],
            "actual_out": r["actual_out"],
            "late_minutes": r["late_minutes"],
            "early_leave_minutes": r["early_leave_minutes"],
            "reason_code": r["reason_code"],
            "location": r["location"],
            "reason_detail": r["reason_detail"],
        } for r in rows]
        build_monthly_sheets_format(output, normalized)

    def _build_raw_excel(self, output, summary, ranking, coaching):
        from src.reports.excel_builder import build_raw_excel

        sections = {
            "Summary": [summary],
            "Hall of Late": [{
                "Rank": i + 1,
                "Staff No": r["staff_no"],
                "Name": r["name"],
                "Total Late (min)": r["total_late"],
                "Days Late": r["days_late"],
                "Max Late (min)": r["max_late"],
                "Max Late Date": r["max_late_date"],
            } for i, r in enumerate(ranking)],
            "Coaching": [{
                "Name": c["name"],
                "Total Late": c["total_late"],
                "Days Late": c["days_late"],
            } for c in coaching],
        }
        build_raw_excel(output, sections)
