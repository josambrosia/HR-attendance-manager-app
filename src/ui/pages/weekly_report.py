import flet as ft
from datetime import date, timedelta
from pathlib import Path
from src.core.constants import COLORS
from src.db.repository import Repository
from src.core.settings_store import SettingsStore
from src.ui.components.checklist_modal import show_checklist_modal


class WeeklyReportPage:
    def __init__(self, repo: Repository, settings: SettingsStore, exports_dir: str,
                 mode: str = "dark",
                 on_data_changed=None,
                 show_loading=None, hide_loading=None, notify=None):
        self.repo = repo
        self.settings = settings
        self.exports_dir = Path(exports_dir)
        self.mode = mode
        today = date.today()
        self.start = today - timedelta(days=today.weekday())
        self.end = self.start + timedelta(days=6)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.on_data_changed = on_data_changed
        self.show_loading = show_loading
        self.hide_loading = hide_loading
        self.notify = notify
        self.status_text = ft.Text("Pilih konten untuk di-export.", size=13, opacity=0.7)

    def build(self) -> ft.Control:
        return ft.Container(
            padding=28, expand=True,
            content=ft.Column(spacing=18, controls=[
                ft.Text("Weekly Report", size=28, weight=ft.FontWeight.W_800),
                ft.Text(f"Period: {self.start} -> {self.end}", size=13, opacity=0.7),
                ft.ElevatedButton(
                    "Export Weekly Report",
                    icon=ft.Icons.UPLOAD_FILE,
                    on_click=lambda e: self._open_modal(e.page),
                    bgcolor=COLORS["primary"], color="white",
                ),
                self.status_text,
            ]),
        )

    def _open_modal(self, page: ft.Page):
        show_checklist_modal(page, "Export Weekly Report", self._generate)

    def _generate(self, selected: dict, fmt: str):
        # Lazy imports keep page-load cheap and avoid eager pulls of reportlab/openpyxl
        from src.core.metrics import (
            weekly_summary, hall_of_late, coaching_candidates, repeat_offenders,
            distribusi_alasan, hari_paling_telat, best_performer, late_trend,
        )

        coaching_thr = self.settings.get("coaching_threshold_minutes", 75)
        repeat_weeks = self.settings.get("repeat_offender_weeks", 3)

        s = weekly_summary(self.repo, self.start.isoformat(), self.end.isoformat())
        coaching = coaching_candidates(self.repo, self.start.isoformat(), self.end.isoformat(),
                                       coaching_thr)
        repeat = repeat_offenders(self.repo, self.end.isoformat(), repeat_weeks)
        repeat_set = {r["staff_no"] for r in repeat}
        ranking_full = hall_of_late(self.repo, self.start.isoformat(), self.end.isoformat())
        top_n = selected.get("hall_top_n", "5")
        ranking = ranking_full if top_n == "All" else ranking_full[:int(top_n)]
        trend = late_trend(self.repo, self.start.isoformat(), self.end.isoformat())

        try:
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
            self.status_text.value = f"Generated: {output}"
        except Exception as exc:  # noqa: BLE001
            self.status_text.value = f"Failed to generate report: {exc}"
        self.status_text.update()

    def _build_pdf(self, output, selected, summary, coaching, repeat_set, ranking, trend,
                   coaching_thr, repeat_count,
                   distribusi_alasan, hari_paling_telat, best_performer):
        from src.reports.pdf_builder import PdfReportBuilder
        from src.reports.sections.vital_section import render_vital
        from src.reports.sections.trivia_section import render_trivia
        from src.reports.sections.coaching_section import render_coaching
        from src.reports.sections.hall_of_late_section import render_hall_of_late

        builder = PdfReportBuilder(
            title="Weekly Attendance Report",
            subtitle=f"Period: {self.start} - {self.end}",
            version="1.0",
        )

        if any(selected.get(k) for k in
               ("vital_pending", "vital_coaching", "vital_repeat", "vital_attendance")):
            metrics = {
                "pending_issues": summary["pending_issues"] if selected.get("vital_pending") else 0,
                "resolved_issues": summary["resolved_issues"],
                "total_issues": summary["total_issues"],
                "need_coaching": len(coaching) if selected.get("vital_coaching") else 0,
                "coaching_threshold": coaching_thr,
                "repeat_offenders": repeat_count if selected.get("vital_repeat") else 0,
                "attendance_rate": summary["attendance_rate"] if selected.get("vital_attendance") else 0,
                "trend_text": _ascii_trend_text(trend),
            }
            builder.add_section("vital", render_vital(metrics))

        trivia_items = []
        if selected.get("trivia_reason"):
            dist = distribusi_alasan(self.repo, self.start.isoformat(), self.end.isoformat())
            top = dist[0] if dist else None
            trivia_items.append({
                "label": "Most Common Reason",
                "value": top["reason_code"] if top else "-",
                "meta": f"{top['cnt']} resolutions" if top else "",
            })
        if selected.get("trivia_day"):
            day = hari_paling_telat(self.repo, self.start.isoformat(), self.end.isoformat())
            trivia_items.append({
                "label": "Hari Paling Telat",
                "value": day["day_name"] if day else "-",
                "meta": f"{day['total_late']} mnt total" if day else "",
            })
        if selected.get("trivia_trend"):
            trivia_items.append({
                "label": "Late Trend",
                "value": _ascii_trend_text(trend) or "-",
                "meta": "vs last week",
            })
        if selected.get("trivia_best"):
            best = best_performer(self.repo, self.start.isoformat(), self.end.isoformat())
            trivia_items.append({
                "label": "Best Performer",
                "value": best["name"] if best else "-",
                "meta": "0 late · 0 issue" if best else "",
            })
        if trivia_items:
            builder.add_section("trivia", render_trivia(trivia_items))

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

    def _build_excel(self, output, selected, summary, ranking, coaching):
        from src.reports.excel_builder import build_raw_excel

        sections: dict = {}
        if selected.get("vital_pending") or selected.get("vital_coaching"):
            sections["Summary"] = [summary]
        if selected.get("section_hall"):
            sections["Hall of Late"] = [{
                "Rank": i + 1,
                "Staff No": r["staff_no"],
                "Name": r["name"],
                "Total Late (min)": r["total_late"],
                "Days Late": r["days_late"],
                "Max Late (min)": r["max_late"],
                "Max Late Date": r["max_late_date"],
            } for i, r in enumerate(ranking)]
        if selected.get("section_coaching"):
            sections["Coaching"] = [{
                "Name": c["name"],
                "Total Late": c["total_late"],
                "Days Late": c["days_late"],
            } for c in coaching]
        if not sections:
            sections["Empty"] = [{"note": "No content selected"}]
        build_raw_excel(output, sections)


def _ascii_trend_text(trend: dict) -> str:
    """ASCII-safe trend label for PDF (Helvetica WinAnsi cannot render unicode arrows)."""
    pct = trend.get("change_pct") if trend else None
    if pct is None:
        return ""
    if pct < 0:
        return f"down {abs(pct)}%"
    if pct > 0:
        return f"up {pct}%"
    return "0%"
