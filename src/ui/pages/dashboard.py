import flet as ft
from datetime import date, timedelta
from src.core.constants import COLORS, REASON_CODES
from src.core.metrics import (
    weekly_summary, hall_of_late, coaching_candidates,
    repeat_offenders, distribusi_alasan, hari_paling_telat,
    best_performer, late_trend
)
from src.ui.components.vital_card import vital_card
from src.ui.components.trivia_card import trivia_card
from src.ui.components.coaching_card import coaching_card
from src.ui.components.ranking_row import ranking_row
from src.db.repository import Repository
from src.core.settings_store import SettingsStore


class DashboardPage:
    def __init__(self, repo: Repository, settings: SettingsStore, mode: str = "dark",
                 nav_callback=None):
        self.repo = repo
        self.settings = settings
        self.mode = mode
        self.nav_callback = nav_callback
        today = date.today()
        self.start = today - timedelta(days=today.weekday())
        self.end = self.start + timedelta(days=6)

    def _show_snack(self, page, msg):
        page.snack_bar = ft.SnackBar(ft.Text(msg), open=True)
        page.update()

    def build(self) -> ft.Control:
        coaching_thr = self.settings.get("coaching_threshold_minutes", 75)
        repeat_weeks = self.settings.get("repeat_offender_weeks", 3)

        summary = weekly_summary(self.repo, self.start.isoformat(), self.end.isoformat())
        coaching = coaching_candidates(self.repo, self.start.isoformat(), self.end.isoformat(), coaching_thr)
        repeat = repeat_offenders(self.repo, self.end.isoformat(), repeat_weeks)
        ranking = hall_of_late(self.repo, self.start.isoformat(), self.end.isoformat())[:5]
        trend = late_trend(self.repo, self.start.isoformat(), self.end.isoformat())
        distribusi = distribusi_alasan(self.repo, self.start.isoformat(), self.end.isoformat())
        hari_telat = hari_paling_telat(self.repo, self.start.isoformat(), self.end.isoformat())
        best = best_performer(self.repo, self.start.isoformat(), self.end.isoformat())

        repeat_set = {r["staff_no"] for r in repeat}
        max_total_late = ranking[0]["total_late"] if ranking else 0

        return ft.Container(
            padding=28, expand=True,
            content=ft.Column(scroll=ft.ScrollMode.AUTO, spacing=20, controls=[
                self._page_header(summary),
                self._tier_label("⭐ Vital Metrics"),
                ft.Row(spacing=12, controls=[
                    vital_card("⚠️", "Pending Issues", str(summary["pending_issues"]),
                               f"{summary['resolved_issues']} of {summary['total_issues']} resolved", "urgent", self.mode),
                    vital_card("🚨", "Need Coaching", str(len(coaching)),
                               f"Threshold >{coaching_thr} mnt/minggu", "coaching", self.mode),
                    vital_card("🔥", "Repeat Offenders", str(len(repeat)),
                               f"Telat {repeat_weeks}+ minggu berturut", "warning", self.mode),
                    vital_card("✅", "Attendance Rate", f"{summary['attendance_rate']}%",
                               self._fmt_trend(trend), "positive", self.mode),
                ]),
                self._tier_label("📌 Trivia & Insights"),
                ft.Row(spacing=10, controls=[
                    trivia_card("🏷️", "Most Common Reason",
                                self._top_reason_label(distribusi),
                                self._top_reason_meta(distribusi, summary), self.mode),
                    trivia_card("📅", "Hari Paling Telat",
                                hari_telat["day_name"] if hari_telat else "—",
                                f"total {hari_telat['total_late']} mnt" if hari_telat else "", self.mode),
                    trivia_card("📈", "Late Trend", self._fmt_trend(trend),
                                "vs minggu lalu", self.mode),
                    trivia_card("🌟", "Best Performer",
                                best["name"] if best else "—",
                                "0 telat · 0 issue" if best else "—", self.mode),
                ]),
                self._coaching_section(coaching, repeat_set),
                self._hall_of_late_section(ranking, repeat_set, max_total_late),
            ]),
        )

    def _page_header(self, summary) -> ft.Control:
        return ft.Container(
            padding=ft.padding.only(bottom=16),
            border=ft.border.only(bottom=ft.BorderSide(1, f"{COLORS['primary']}33")),
            content=ft.Row(controls=[
                ft.Column(spacing=4, controls=[
                    ft.Text("Weekly Dashboard", size=28, weight=ft.FontWeight.W_800),
                    ft.Text(f"Periode: {self.start} → {self.end} · {summary['total_records']} records",
                            size=13, opacity=0.7),
                ]),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    "📤 Export Weekly",
                    on_click=lambda e: self.nav_callback("weekly_report") if self.nav_callback else None,
                    bgcolor=COLORS["primary"], color="white"),
                ft.ElevatedButton(
                    "📆 Export Monthly",
                    on_click=lambda e: self.nav_callback("monthly_report") if self.nav_callback else None,
                    bgcolor=COLORS["accent"], color="white"),
            ]),
        )

    def _tier_label(self, text: str) -> ft.Control:
        return ft.Row(spacing=8, controls=[
            ft.Text(text, size=11, weight=ft.FontWeight.W_800, color=COLORS["accent"]),
            ft.Container(expand=True, height=1,
                         gradient=ft.LinearGradient(
                             begin=ft.alignment.center_left, end=ft.alignment.center_right,
                             colors=[f"{COLORS['primary']}55", "transparent"])),
        ])

    def _coaching_section(self, candidates, repeat_set) -> ft.Control:
        if not candidates:
            return ft.Container(
                padding=20, border_radius=12,
                bgcolor=f"{COLORS['resolved']}11",
                border=ft.border.all(1, COLORS["resolved"]),
                content=ft.Row(controls=[
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=COLORS["resolved"]),
                    ft.Text("Tidak ada karyawan yang melebihi threshold coaching minggu ini ✨"),
                ]),
            )

        # Limit to top 4 in the UI
        cards = []
        medals = ["🥇", "🥈", "🥉", "🏅"]
        for i, c in enumerate(candidates[:4]):
            avg = c["total_late"] // c["days_late"] if c["days_late"] else 0
            streak = 4 if c["staff_no"] in repeat_set else 0
            cards.append(coaching_card(medals[i], c["name"], c["total_late"],
                                        c["days_late"], 5, avg, streak=streak))

        return ft.Container(
            padding=24, border_radius=16,
            bgcolor=f"{COLORS['accent']}10",
            border=ft.border.all(2, COLORS["accent"]),
            content=ft.Column(spacing=14, controls=[
                ft.Row(controls=[
                    ft.Text("🚨 COACHING REQUIRED", size=22, weight=ft.FontWeight.W_900,
                            color=COLORS["accent"]),
                    ft.Container(expand=True),
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=14, vertical=6),
                        bgcolor=COLORS["late_severe"], border_radius=999,
                        content=ft.Text("⚡ ACTION NEEDED", color="white", size=11,
                                        weight=ft.FontWeight.W_800),
                    ),
                ]),
                ft.Text("Karyawan dengan akumulasi keterlambatan > threshold · jadwalkan coaching minggu depan",
                        size=12, opacity=0.8),
                ft.GridView(runs_count=2, max_extent=500, spacing=12, run_spacing=12,
                            child_aspect_ratio=2.2, controls=cards),
            ]),
        )

    def _hall_of_late_section(self, ranking, repeat_set, max_value) -> ft.Control:
        coaching_thr = self.settings.get("coaching_threshold_minutes", 75)
        rows = [ranking_row(
            i + 1, r["name"], r["total_late"], r["days_late"],
            r["max_late"], r["max_late_date"], max_value,
            r["staff_no"] in repeat_set, coaching_thr,
        ) for i, r in enumerate(ranking)]

        if not rows:
            rows = [ft.Container(padding=20, alignment=ft.alignment.center,
                                  content=ft.Text("Tidak ada keterlambatan minggu ini ✨"))]

        return ft.Container(
            padding=22, border_radius=16,
            bgcolor=COLORS["surface_dark"] if self.mode == "dark" else COLORS["surface_light"],
            border=ft.border.all(1, f"{COLORS['primary']}33"),
            content=ft.Column(spacing=16, controls=[
                ft.Row(controls=[
                    ft.Column(spacing=2, controls=[
                        ft.Text("⏰ HALL OF LATE — Top 5 Minggu Ini",
                                size=20, weight=ft.FontWeight.W_900),
                        ft.Text("Total menit keterlambatan · 🔥 = repeat offender",
                                size=11, opacity=0.7),
                    ]),
                    ft.Container(expand=True),
                    ft.IconButton(
                        ft.Icons.OPEN_IN_FULL, tooltip="Show All Employees",
                        on_click=lambda e: self._show_snack(
                            e.page,
                            "Open Weekly Report page from sidebar to access Hall of Late exports")),
                    ft.IconButton(
                        ft.Icons.PICTURE_AS_PDF, tooltip="Export PDF",
                        on_click=lambda e: self._show_snack(
                            e.page,
                            "Use the Weekly/Monthly Report page to export.")),
                    ft.IconButton(
                        ft.Icons.TABLE_CHART, tooltip="Export Excel",
                        on_click=lambda e: self._show_snack(
                            e.page,
                            "Use the Weekly/Monthly Report page to export.")),
                ]),
                ft.Column(spacing=8, controls=rows),
            ]),
        )

    def _fmt_trend(self, t: dict) -> str:
        if t["change_pct"] is None:
            return "—"
        arrow = "↓" if t["change_pct"] < 0 else "↑"
        return f"{arrow} {abs(t['change_pct'])}% vs minggu lalu"

    def _top_reason_label(self, dist) -> str:
        if not dist:
            return "—"
        code = dist[0]["reason_code"]
        return REASON_CODES.get(code, {}).get("label", code)

    def _top_reason_meta(self, dist, summary) -> str:
        if not dist or not summary["resolved_issues"]:
            return ""
        cnt = dist[0]["cnt"]
        pct = round(cnt / summary["resolved_issues"] * 100)
        return f"{cnt} of {summary['resolved_issues']} ({pct}%)"
