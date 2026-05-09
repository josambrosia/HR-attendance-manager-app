import flet as ft
from pathlib import Path
from src.core.parser import parse_xls
from src.core.conflict import resolve_import, detect_conflicts, ConflictPolicy
from src.db.repository import Repository
from src.core.settings_store import SettingsStore
from src.core.constants import COLORS


class ImportDataPage:
    def __init__(self, repo: Repository, settings: SettingsStore, snapshot_dir: str,
                 mode: str = "dark", on_data_changed=None):
        self.repo = repo
        self.settings = settings
        self.snapshot_dir = snapshot_dir
        self.mode = mode
        self.on_data_changed = on_data_changed
        self.parsed_records = []
        self.selected_file = None
        self.file_picker = None

    def build(self) -> ft.Control:
        self.file_picker = ft.FilePicker(on_result=self._on_file_picked)
        self.status_text = ft.Text("Belum ada file yang dipilih.", size=14, opacity=0.7)
        self.preview_container = ft.Container()
        self.action_row = ft.Row(visible=False, spacing=10)

        return ft.Container(
            padding=32, expand=True,
            content=ft.Column(
                spacing=20, controls=[
                    self.file_picker,
                    ft.Text("Import Data", size=28, weight=ft.FontWeight.W_800),
                    ft.Text("Tarik file fingerprint .xls ke sini, atau klik 'Pilih File'.",
                            size=13, opacity=0.7),
                    ft.Container(
                        padding=40, border_radius=12,
                        bgcolor=f"{COLORS['primary']}11",
                        border=ft.border.all(2, f"{COLORS['primary']}55"),
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=12, controls=[
                                ft.Icon(ft.Icons.UPLOAD_FILE, size=48, color=COLORS["primary"]),
                                ft.ElevatedButton(
                                    "\U0001F4C1 Pilih File .xls",
                                    on_click=lambda e: self.file_picker.pick_files(
                                        allowed_extensions=["xls", "xlsx"], allow_multiple=False
                                    ),
                                    bgcolor=COLORS["primary"], color="white",
                                ),
                                self.status_text,
                            ],
                        ),
                    ),
                    self.preview_container,
                    self.action_row,
                ],
            ),
        )

    def _on_file_picked(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return
        self.selected_file = e.files[0].path
        try:
            self.parsed_records = parse_xls(self.selected_file)
        except Exception as ex:
            self.status_text.value = f"❌ Gagal parse: {ex}"
            self.status_text.update()
            return

        n = len(self.parsed_records)
        if n == 0:
            self.status_text.value = (
                f"❌ File {Path(self.selected_file).name} kosong atau tidak bisa di-parse."
            )
            self.status_text.update()
            return

        dates = sorted({r["date"] for r in self.parsed_records})
        self.status_text.value = (
            f"✅ {n} baris ter-parse dari {Path(self.selected_file).name} "
            f"· periode {dates[0]} → {dates[-1]}"
        )
        self.status_text.update()

        self._show_preview_and_actions()

    def _show_preview_and_actions(self):
        # Detect conflicts before commit
        conflicts = detect_conflicts(self.repo, self.parsed_records)
        n_conflict = len(conflicts)
        n_new = len(self.parsed_records) - n_conflict

        info_box = ft.Container(
            padding=16, border_radius=8, bgcolor=f"{COLORS['accent']}22",
            content=ft.Column(spacing=4, controls=[
                ft.Text(f"\U0001F4E5 Baris baru: {n_new}", size=13, weight=ft.FontWeight.W_600),
                ft.Text(f"⚠️ Konflik (sudah ada di DB): {n_conflict}",
                        size=13, weight=ft.FontWeight.W_600,
                        color=COLORS["accent"] if n_conflict else None),
            ]),
        )
        self.preview_container.content = info_box
        self.preview_container.update()

        self.action_row.controls.clear()
        self.action_row.controls.append(
            ft.ElevatedButton("✅ Import (keep existing untuk konflik)",
                              on_click=lambda e: self._do_import(ConflictPolicy.KEEP_EXISTING),
                              bgcolor=COLORS["resolved"], color="white"),
        )
        if n_conflict > 0:
            self.action_row.controls.append(
                ft.ElevatedButton("⚡ Import + Overwrite konflik",
                                  on_click=lambda e: self._do_import(ConflictPolicy.OVERWRITE),
                                  bgcolor=COLORS["accent"], color="white"),
            )
        self.action_row.controls.append(
            ft.TextButton("Cancel", on_click=lambda e: self._reset()),
        )
        self.action_row.visible = True
        self.action_row.update()

    def _do_import(self, policy: ConflictPolicy):
        summary = resolve_import(
            self.repo, self.parsed_records, Path(self.selected_file).name,
            snapshot_dir=self.snapshot_dir, policy=policy,
            settings=self.settings.load(),
        )
        parts = [
            f"{summary['inserted']} new",
            f"{summary['kept']} kept",
            f"{summary['overwritten']} overwritten",
        ]
        if summary.get("preserved_resolved", 0) > 0:
            parts.append(f"{summary['preserved_resolved']} preserved (resolved)")
        msg = "✅ Import done · " + " · ".join(parts)
        self.status_text.value = msg
        self.status_text.update()
        self._reset_after_success()
        if self.on_data_changed:
            self.on_data_changed()

    def _reset(self):
        self.parsed_records = []
        self.selected_file = None
        self.status_text.value = "Belum ada file yang dipilih."
        self.preview_container.content = None
        self.action_row.visible = False
        self.status_text.update()
        self.preview_container.update()
        self.action_row.update()

    def _reset_after_success(self):
        self.parsed_records = []
        self.selected_file = None
        self.preview_container.content = None
        self.action_row.visible = False
        self.preview_container.update()
        self.action_row.update()
