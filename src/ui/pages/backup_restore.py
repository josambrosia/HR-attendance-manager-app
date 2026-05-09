import flet as ft
from datetime import datetime
from pathlib import Path

from src.core.backup import export_backup, import_backup
from src.core.constants import COLORS


class BackupRestorePage:
    def __init__(
        self,
        db_path: str,
        config_path: str,
        backup_dir: str,
        pre_restore_dir: str,
        mode: str = "dark",
        on_data_changed=None,
    ):
        self.db_path = db_path
        self.config_path = config_path
        self.backup_dir = backup_dir
        self.pre_restore_dir = pre_restore_dir
        self.mode = mode
        self.on_data_changed = on_data_changed

    def build(self) -> ft.Control:
        self.status_text = ft.Text(
            "Pilih Export untuk membuat backup, atau Import untuk memulihkan dari ZIP.",
            size=13, opacity=0.75,
        )
        self.file_picker = ft.FilePicker(on_result=self._on_zip_picked)

        export_btn = ft.ElevatedButton(
            "Export Backup (.zip)",
            icon=ft.Icons.DOWNLOAD,
            on_click=lambda e: self._do_export(),
            bgcolor=COLORS["primary"], color="white",
        )
        import_btn = ft.ElevatedButton(
            "Import Backup (.zip)",
            icon=ft.Icons.UPLOAD,
            on_click=lambda e: self.file_picker.pick_files(
                allowed_extensions=["zip"], allow_multiple=False,
            ),
            bgcolor=COLORS["accent"], color="white",
        )

        info_card = ft.Container(
            padding=16, border_radius=10,
            bgcolor=f"{COLORS['primary']}11",
            border=ft.border.all(1, f"{COLORS['primary']}33"),
            content=ft.Column(spacing=6, controls=[
                ft.Text("Apa yang dibundel?", size=13, weight=ft.FontWeight.W_700),
                ft.Text("- Database absensi (app.db)", size=12, opacity=0.85),
                ft.Text("- File pengaturan (config.json)", size=12, opacity=0.85),
                ft.Text("- 10 snapshot import terakhir untuk rollback", size=12, opacity=0.85),
            ]),
        )

        warning_card = ft.Container(
            padding=16, border_radius=10,
            bgcolor=f"{COLORS['accent']}22",
            border=ft.border.all(1, f"{COLORS['accent']}55"),
            content=ft.Column(spacing=6, controls=[
                ft.Text("Catatan Import", size=13, weight=ft.FontWeight.W_700),
                ft.Text(
                    "Data lama akan disalin ke folder pre-restore sebelum di-overwrite.",
                    size=12, opacity=0.9,
                ),
                ft.Text(
                    "Restart aplikasi setelah import agar perubahan termuat penuh.",
                    size=12, opacity=0.9,
                ),
            ]),
        )

        return ft.Container(
            padding=32, expand=True,
            content=ft.Column(spacing=18, controls=[
                self.file_picker,
                ft.Text("Backup / Restore", size=28, weight=ft.FontWeight.W_800),
                ft.Text(
                    "Migrasi data ke laptop lain: Export di sini, Import di laptop baru.",
                    size=13, opacity=0.7,
                ),
                ft.Row(spacing=12, controls=[export_btn, import_btn]),
                self.status_text,
                ft.Container(height=4),
                info_card,
                warning_card,
            ]),
        )

    def _do_export(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = str(Path(self.backup_dir) / f"hr_backup_{timestamp}.zip")
            written = export_backup(self.db_path, self.config_path, self.backup_dir, output)
            self.status_text.value = f"Export selesai: {written}"
            self.status_text.color = COLORS["resolved"]
        except Exception as ex:
            self.status_text.value = f"Export gagal: {ex}"
            self.status_text.color = COLORS["late_severe"]
        self.status_text.update()

    def _on_zip_picked(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return
        zip_path = e.files[0].path
        try:
            summary = import_backup(
                zip_path, self.db_path, self.config_path, self.pre_restore_dir,
            )
            parts = []
            if summary["db_restored"]:
                parts.append("database")
            if summary["config_restored"]:
                parts.append("settings")
            parts.append(f"{summary['snapshots_restored']} snapshots")
            self.status_text.value = (
                f"Import selesai ({', '.join(parts)}). "
                f"Restart aplikasi untuk memuat data baru."
            )
            self.status_text.color = COLORS["resolved"]
            if self.on_data_changed:
                self.on_data_changed()
        except Exception as ex:
            self.status_text.value = f"Import gagal: {ex}"
            self.status_text.color = COLORS["late_severe"]
        self.status_text.update()
