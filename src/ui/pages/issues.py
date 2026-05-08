import flet as ft
from datetime import date, timedelta
from src.core.constants import COLORS
from src.core.resolver import (
    apply_resolution, list_all_reason_options, requires_extra_input
)
from src.db.repository import Repository
from src.core.settings_store import SettingsStore

CASE_LABELS = {
    "A": ("Tidak Hadir", COLORS["late_severe"]),
    "B": ("Lupa Absen Masuk", COLORS["late_mild"]),
    "C": ("Lupa Absen Pulang", COLORS["late_mild"]),
    "F": ("Pulang Cepat", COLORS["pulang_cepat"]),
}


class IssuesPage:
    def __init__(self, repo: Repository, settings: SettingsStore, mode: str = "dark"):
        self.repo = repo
        self.settings = settings
        self.mode = mode
        # Default: current week (Mon-Sun)
        today = date.today()
        self.start = today - timedelta(days=today.weekday())
        self.end = self.start + timedelta(days=6)
        self.selected_record_id = None
        self.selected_reason = None

    def build(self) -> ft.Control:
        self.list_view = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=6, expand=True)
        self.resolve_panel = ft.Container(
            width=360, padding=20, visible=False,
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

    def _build_period_selector(self) -> ft.Control:
        return ft.Row(spacing=8, controls=[
            ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda e: self._shift_week(-1)),
            ft.Text(f"{self.start.strftime('%d %b')} – {self.end.strftime('%d %b %Y')}", size=13),
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda e: self._shift_week(1)),
        ])

    def _shift_week(self, weeks: int):
        self.start += timedelta(weeks=weeks)
        self.end += timedelta(weeks=weeks)
        self._refresh_list()
        self.list_view.update()

    def _refresh_list(self):
        self.list_view.controls.clear()
        issues = self.repo.list_pending_issues(self.start.isoformat(), self.end.isoformat())
        if not issues:
            self.list_view.controls.append(
                ft.Container(padding=40, alignment=ft.alignment.center,
                             content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                 controls=[
                                     ft.Icon(ft.Icons.CHECK_CIRCLE, size=48, color=COLORS["resolved"]),
                                     ft.Text("Tidak ada issue pending minggu ini ✨", size=14),
                                 ])),
            )
            return

        for issue in issues:
            self.list_view.controls.append(self._build_issue_row(issue))

    def _build_issue_row(self, issue: dict) -> ft.Control:
        case_label, case_color = CASE_LABELS.get(issue["issue_case"], (issue["issue_case"], "#999"))
        return ft.Container(
            padding=12, border_radius=8,
            bgcolor=f"{case_color}15", border=ft.border.all(1, f"{case_color}66"),
            on_click=lambda e, rid=issue["id"]: self._select_issue(rid, issue),
            ink=True,
            content=ft.Row(spacing=12, controls=[
                ft.Container(width=4, height=40, bgcolor=case_color, border_radius=2),
                ft.Column(spacing=2, expand=True, controls=[
                    ft.Text(f"{issue['employee_name']}", weight=ft.FontWeight.W_700, size=14),
                    ft.Text(f"{issue['date']} · {issue['day_name']}", size=12, opacity=0.7),
                ]),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    border_radius=12, bgcolor=case_color,
                    content=ft.Text(case_label, color="white", size=11, weight=ft.FontWeight.W_600),
                ),
            ]),
        )

    def _select_issue(self, record_id: int, issue: dict):
        self.selected_record_id = record_id
        self.selected_reason = None
        self.resolve_panel.visible = True
        self.resolve_panel.content = self._build_resolve_panel(issue)
        self.resolve_panel.update()

    def _build_resolve_panel(self, issue: dict) -> ft.Control:
        self.extra_input_field = ft.TextField(label="Lokasi / Alasan", visible=False)

        def make_option(code: str, label: str):
            return ft.Container(
                padding=10, border_radius=6,
                bgcolor=f"{COLORS['primary']}22" if self.selected_reason == code else None,
                on_click=lambda e, c=code: self._select_reason(c),
                ink=True,
                content=ft.Text(label, size=13),
            )

        options_col = ft.Column(spacing=4, controls=[
            make_option(code, label) for code, label, _ in list_all_reason_options()
        ])

        return ft.Column(spacing=14, controls=[
            ft.Text("Resolve Issue", size=18, weight=ft.FontWeight.W_700),
            ft.Text(f"{issue['employee_name']} · {issue['date']}", size=12, opacity=0.7),
            ft.Divider(height=1),
            ft.Text("Pilih alasan:", size=12, weight=ft.FontWeight.W_600),
            options_col,
            self.extra_input_field,
            ft.Row(spacing=8, controls=[
                ft.ElevatedButton("Save", on_click=lambda e: self._save_resolution(),
                                  bgcolor=COLORS["resolved"], color="white"),
                ft.TextButton("Cancel", on_click=lambda e: self._close_panel()),
            ]),
        ])

    def _select_reason(self, code: str):
        self.selected_reason = code
        extra = requires_extra_input(code)
        self.extra_input_field.visible = extra is not None
        self.extra_input_field.label = "Lokasi" if extra == "location" else "Alasan"
        self.extra_input_field.value = ""
        # Rebuild panel to re-highlight option
        cursor = self.repo.conn.execute(
            """SELECT ar.*, e.name AS employee_name FROM attendance_records ar
               JOIN employees e ON ar.employee_id=e.id WHERE ar.id=?""",
            (self.selected_record_id,),
        ).fetchone()
        self.resolve_panel.content = self._build_resolve_panel(dict(cursor))
        self.resolve_panel.update()

    def _save_resolution(self):
        if not self.selected_reason:
            return
        extra_type = requires_extra_input(self.selected_reason)
        kwargs = {}
        if extra_type == "location":
            kwargs["location"] = self.extra_input_field.value
        elif extra_type == "reason_detail":
            kwargs["reason_detail"] = self.extra_input_field.value
        kwargs["penalty_minutes"] = self.settings.get("lupa_absen_penalty_minutes")
        apply_resolution(self.repo, self.selected_record_id, self.selected_reason, **kwargs)
        self._close_panel()
        self._refresh_list()
        self.list_view.update()

    def _close_panel(self):
        self.resolve_panel.visible = False
        self.resolve_panel.update()
