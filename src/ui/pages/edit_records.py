import flet as ft
from datetime import date, timedelta
from src.core.constants import COLORS, REASON_CODES
from src.core.resolver import apply_resolution, requires_extra_input
from src.db.repository import Repository
from src.core.settings_store import SettingsStore


class EditRecordsPage:
    def __init__(self, repo: Repository, settings: SettingsStore, mode: str = "dark",
                 on_data_changed=None):
        self.repo = repo
        self.settings = settings
        self.mode = mode
        self.on_data_changed = on_data_changed
        today = date.today()
        # Show last 30 days by default
        self.end = today
        self.start = today - timedelta(days=30)
        self.search_query = ""

    def build(self) -> ft.Control:
        self.search_field = ft.TextField(
            label="Cari nama / no. staff",
            on_change=lambda e: self._on_search(e.control.value),
            width=300,
        )
        self.records_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=4, expand=True)
        self._refresh()
        return ft.Container(
            padding=24, expand=True,
            content=ft.Column(spacing=16, controls=[
                ft.Row(controls=[
                    ft.Text("Edit Records", size=28, weight=ft.FontWeight.W_800),
                    ft.Container(expand=True),
                    self.search_field,
                ]),
                ft.Text(f"Showing {self.start} → {self.end}", size=12, opacity=0.7),
                ft.Container(expand=True, content=self.records_list),
            ]),
        )

    def _on_search(self, query: str):
        self.search_query = query
        self._refresh()
        self.records_list.update()

    def _refresh(self):
        self.records_list.controls.clear()
        records = self.repo.list_attendance_with_resolutions(
            self.start.isoformat(), self.end.isoformat(), self.search_query
        )
        for rec in records[:200]:  # cap to keep UI responsive
            self.records_list.controls.append(self._build_row(rec))

    def _build_row(self, rec: dict) -> ft.Control:
        reason_label = (
            REASON_CODES.get(rec["reason_code"], {}).get("label", "—")
            if rec["reason_code"] else "—"
        )
        return ft.Container(
            padding=10, border_radius=6,
            bgcolor=f"{COLORS['primary']}08",
            content=ft.Row(spacing=12, controls=[
                ft.Container(width=80, content=ft.Text(rec["date"], size=12, weight=ft.FontWeight.W_600)),
                ft.Container(width=120, content=ft.Text(rec["employee_name"], size=12)),
                ft.Container(width=80, content=ft.Text(f"In: {rec['actual_in'] or '—'}", size=11)),
                ft.Container(width=80, content=ft.Text(f"Out: {rec['actual_out'] or '—'}", size=11)),
                ft.Container(expand=True, content=ft.Text(reason_label, size=11, opacity=0.85)),
                ft.IconButton(ft.Icons.EDIT, icon_size=16,
                              on_click=lambda e, r=rec: self._open_edit_dialog(r)),
                ft.IconButton(ft.Icons.HISTORY, icon_size=16,
                              on_click=lambda e, r=rec: self._open_history_dialog(r)),
            ]),
        )

    def _open_edit_dialog(self, rec: dict):
        actual_in_field = ft.TextField(label="Actual In (HH:MM)", value=rec["actual_in"] or "")
        actual_out_field = ft.TextField(label="Actual Out (HH:MM)", value=rec["actual_out"] or "")
        reason_dropdown = ft.Dropdown(
            label="Reason",
            value=rec["reason_code"] or "belum_kabar",
            options=[ft.dropdown.Option(code, info["label"])
                     for code, info in REASON_CODES.items()],
        )
        extra_field = ft.TextField(
            label="Lokasi / Alasan",
            value=rec["location"] or rec["reason_detail"] or "",
        )

        def save(_):
            self.repo.update_attendance(rec["id"], {
                "actual_in": actual_in_field.value or None,
                "actual_out": actual_out_field.value or None,
            })
            extra_type = requires_extra_input(reason_dropdown.value)
            kwargs = {}
            if extra_type == "location":
                kwargs["location"] = extra_field.value
            elif extra_type == "reason_detail":
                kwargs["reason_detail"] = extra_field.value
            kwargs["penalty_minutes"] = self.settings.get("lupa_absen_penalty_minutes")
            apply_resolution(self.repo, rec["id"], reason_dropdown.value, **kwargs)
            self._close_dialog(dialog)
            self._refresh()
            self.records_list.update()
            if self.on_data_changed:
                self.on_data_changed()

        dialog = ft.AlertDialog(
            modal=True, title=ft.Text(f"Edit · {rec['employee_name']} · {rec['date']}"),
            content=ft.Column(width=400, spacing=10, tight=True, controls=[
                actual_in_field, actual_out_field, reason_dropdown, extra_field,
            ]),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self._close_dialog(dialog)),
                ft.ElevatedButton("Save", on_click=save, bgcolor=COLORS["resolved"], color="white"),
            ],
        )
        self._open_dialog(dialog)

    def _open_history_dialog(self, rec: dict):
        history = self.repo.list_history_for_record(rec["id"])
        rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(h["changed_at"][:19], size=11)),
                ft.DataCell(ft.Text(h["changed_field"], size=11)),
                ft.DataCell(ft.Text(str(h["old_value"]), size=11)),
                ft.DataCell(ft.Text(str(h["new_value"]), size=11)),
                ft.DataCell(ft.Text(h["changed_by"], size=11)),
            ]) for h in history
        ]
        dialog = ft.AlertDialog(
            modal=True, title=ft.Text(f"History · {rec['employee_name']} · {rec['date']}"),
            content=ft.Container(width=700, height=400, content=ft.Column(scroll=ft.ScrollMode.AUTO, controls=[
                ft.DataTable(columns=[
                    ft.DataColumn(ft.Text("When")),
                    ft.DataColumn(ft.Text("Field")),
                    ft.DataColumn(ft.Text("Old")),
                    ft.DataColumn(ft.Text("New")),
                    ft.DataColumn(ft.Text("By")),
                ], rows=rows or [ft.DataRow(cells=[ft.DataCell(ft.Text("—"))] * 5)]),
            ])),
            actions=[ft.TextButton("Close", on_click=lambda e: self._close_dialog(dialog))],
        )
        self._open_dialog(dialog)

    def _open_dialog(self, dialog: ft.AlertDialog):
        page = self.search_field.page
        # Flet 0.25: use overlay for reliable dialog rendering
        if dialog not in page.overlay:
            page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _close_dialog(self, dialog: ft.AlertDialog):
        dialog.open = False
        self.search_field.page.update()
