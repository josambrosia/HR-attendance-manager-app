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
    def __init__(self, repo: Repository, settings: SettingsStore, mode: str = "dark",
                 on_data_changed=None):
        self.repo = repo
        self.settings = settings
        self.mode = mode
        self.on_data_changed = on_data_changed
        # Default: current week (Mon-Sun)
        today = date.today()
        self.start = today - timedelta(days=today.weekday())
        self.end = self.start + timedelta(days=6)
        self.selected_record_id = None
        self.selected_reason = None
        self._refresh_timer = None

    def build(self) -> ft.Control:
        self.list_view = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=6, expand=True)
        self.resolve_panel = ft.Container(
            width=420, padding=20, visible=False,
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

    def _period_label(self) -> str:
        return f"{self.start.strftime('%d %b')} – {self.end.strftime('%d %b %Y')}"

    def _build_period_selector(self) -> ft.Control:
        self.period_text = ft.Text(self._period_label(), size=13, weight=ft.FontWeight.W_600)
        return ft.Row(spacing=8, controls=[
            ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda e: self._shift_week(-1)),
            self.period_text,
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda e: self._shift_week(1)),
        ])

    def _shift_week(self, weeks: int):
        self.start += timedelta(weeks=weeks)
        self.end += timedelta(weeks=weeks)
        self.period_text.value = self._period_label()
        self.period_text.update()
        self._schedule_refresh()

    def _schedule_refresh(self, delay_ms: int = 200):
        """Coalesce rapid ◀▶ clicks into a single DB query after delay."""
        import threading
        if hasattr(self, "_refresh_timer") and self._refresh_timer is not None:
            self._refresh_timer.cancel()
        def _do():
            self._refresh_list()
            try:
                self.list_view.update()
            except Exception:
                pass  # may be unmounted by now — safe to ignore
        self._refresh_timer = threading.Timer(delay_ms / 1000.0, _do)
        self._refresh_timer.start()

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
        from src.core.issue_detector import recommend
        case_label, case_color = CASE_LABELS.get(
            issue["issue_case"], (issue["issue_case"], "#999"),
        )
        ai_hint = recommend(issue["issue_case"])

        # Build detail text (Masuk/Keluar values)
        in_val = issue.get("actual_in") or "kosong"
        out_val = issue.get("actual_out") or "kosong"
        in_color = COLORS["resolved"] if issue.get("actual_in") else COLORS["late_severe"]
        out_color = COLORS["resolved"] if issue.get("actual_out") else COLORS["late_severe"]

        return ft.Container(
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=6,
            bgcolor=f"{case_color}15",
            border=ft.border.only(left=ft.BorderSide(3, case_color)),
            on_click=lambda e, rid=issue["id"]: self._select_issue(rid, issue),
            ink=True,
            content=ft.Row(spacing=12, controls=[
                # Col 1: Name + date
                ft.Container(width=140, content=ft.Column(spacing=2, controls=[
                    ft.Text(issue["employee_name"], weight=ft.FontWeight.W_700, size=13),
                    ft.Text(f"{issue['date']} · {issue.get('day_name','')}",
                            size=10, opacity=0.65),
                ])),
                # Col 2: Detail
                ft.Container(expand=True, content=ft.Column(spacing=1, controls=[
                    ft.Row(spacing=4, controls=[
                        ft.Text("In:", size=11, opacity=0.7),
                        ft.Text(in_val, size=11, color=in_color,
                                font_family="Courier New", weight=ft.FontWeight.W_600),
                    ]),
                    ft.Row(spacing=4, controls=[
                        ft.Text("Out:", size=11, opacity=0.7),
                        ft.Text(out_val, size=11, color=out_color,
                                font_family="Courier New", weight=ft.FontWeight.W_600),
                    ]),
                ])),
                # Col 3: AI recommendation (if any)
                ft.Container(width=240, content=ft.Row(spacing=6, controls=[
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        border_radius=4, bgcolor="#1E40AF55",
                        content=ft.Text("AI", size=9, weight=ft.FontWeight.W_700,
                                        color="#93C5FD"),
                    ) if ai_hint else ft.Container(),
                    ft.Text(ai_hint or "", size=10, opacity=0.8, expand=True),
                ])),
                # Col 4: Case badge
                ft.Container(
                    width=110,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=10, bgcolor=case_color,
                    content=ft.Text(case_label, color="white", size=10,
                                    weight=ft.FontWeight.W_700,
                                    text_align=ft.TextAlign.CENTER),
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
        from src.core.issue_detector import recommend
        from src.core.alasan_format import format_alasan

        self.extra_input_field = ft.TextField(
            label="Lokasi / Alasan", visible=False,
            on_change=lambda e: self._update_preview(),
        )
        self.preview_text = ft.Text("", size=10, italic=True, opacity=0.65)

        ai_hint = recommend(issue["issue_case"])

        def make_option(code: str, label: str):
            is_active = self.selected_reason == code
            return ft.Container(
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                border_radius=5,
                bgcolor=f"{COLORS['accent']}33" if is_active else f"{COLORS['primary']}11",
                border=ft.border.all(1,
                    COLORS["accent"] if is_active else "transparent"),
                on_click=lambda e, c=code: self._select_reason(c),
                ink=True,
                content=ft.Text(label, size=11,
                                weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.W_500),
            )

        options_grid = ft.GridView(
            runs_count=2, spacing=4, run_spacing=4, max_extent=180,
            child_aspect_ratio=4.5, height=240,
            controls=[make_option(code, label)
                      for code, label, _ in list_all_reason_options()],
        )

        rec_block = ft.Container(visible=ai_hint is not None,
            padding=10, border_radius=6,
            bgcolor="#1E40AF22",
            border=ft.border.all(1, "#3B82F688"),
            content=ft.Row(spacing=8, controls=[
                ft.Text("🤖", size=16),
                ft.Column(spacing=2, expand=True, controls=[
                    ft.Text("Recommendation", size=10, weight=ft.FontWeight.W_700,
                            color="#93C5FD"),
                    ft.Text(ai_hint or "", size=11, opacity=0.85),
                ]),
            ]),
        )

        return ft.Column(spacing=10, controls=[
            ft.Text("Resolve Issue", size=16, weight=ft.FontWeight.W_700),
            ft.Text(f"{issue['employee_name']} · {issue['date']}",
                    size=11, opacity=0.7),
            ft.Divider(height=1),
            rec_block,
            ft.Text("Pilih alasan:", size=11, weight=ft.FontWeight.W_600,
                    color=COLORS["accent"]),
            options_grid,
            self.extra_input_field,
            self.preview_text,
            ft.Row(spacing=8, controls=[
                ft.ElevatedButton("Save",
                    on_click=lambda e: self._save_resolution(),
                    bgcolor=COLORS["resolved"], color="white"),
                ft.TextButton("Cancel",
                    on_click=lambda e: self._close_panel()),
            ]),
        ])

    def _update_preview(self):
        """Live preview: show what 'Alasan Ijin' text will look like."""
        from src.core.alasan_format import format_alasan
        if not self.selected_reason:
            self.preview_text.value = ""
        else:
            extra = requires_extra_input(self.selected_reason)
            loc = self.extra_input_field.value if extra == "location" else None
            det = self.extra_input_field.value if extra == "reason_detail" else None
            rendered = format_alasan(self.selected_reason, loc, det)
            if rendered:
                self.preview_text.value = f'→ Akan tertulis: "{rendered}"'
            else:
                self.preview_text.value = ""
        try:
            self.preview_text.update()
        except Exception:
            pass  # may not be mounted

    def _select_reason(self, code: str):
        self.selected_reason = code
        extra = requires_extra_input(code)
        self.extra_input_field.visible = extra is not None
        self.extra_input_field.label = "Lokasi" if extra == "location" else "Alasan"
        self.extra_input_field.value = ""
        cursor = self.repo.conn.execute(
            """SELECT ar.*, e.name AS employee_name FROM attendance_records ar
               JOIN employees e ON ar.employee_id=e.id WHERE ar.id=?""",
            (self.selected_record_id,),
        ).fetchone()
        self.resolve_panel.content = self._build_resolve_panel(dict(cursor))
        self.resolve_panel.update()
        self._update_preview()

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
        if self.on_data_changed:
            self.on_data_changed()

    def _close_panel(self):
        self.resolve_panel.visible = False
        self.resolve_panel.update()
