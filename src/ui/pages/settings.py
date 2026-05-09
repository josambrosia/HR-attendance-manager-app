import flet as ft
from src.core.constants import COLORS
from src.core.settings_store import SettingsStore


class SettingsPage:
    def __init__(self, settings: SettingsStore, mode: str = "dark", on_data_changed=None,
                 show_loading=None, hide_loading=None, notify=None):
        self.settings = settings
        self.mode = mode
        self.on_data_changed = on_data_changed
        self.show_loading = show_loading
        self.hide_loading = hide_loading
        self.notify = notify
        self.cfg = settings.load()
        # key -> (TextField, Switch or None)
        self.fields = {}

    def build(self) -> ft.Control:
        self.status_text = ft.Text("", size=12, opacity=0.85)

        sections = [
            self._numeric_off_section(
                "Coaching Threshold (menit/minggu)",
                "coaching_threshold_minutes",
                off_allowed=False,
                hint="Karyawan yang melebihi total ini per minggu akan masuk Coaching Required.",
            ),
            self._numeric_off_section(
                "Late Threshold (menit)",
                "late_threshold_minutes",
                off_allowed=True,
                hint="Telat >= nilai ini -> cell merah; di bawah -> cell kuning. Off = no coloring.",
            ),
            self._numeric_off_section(
                "Lupa Absen Penalty (menit)",
                "lupa_absen_penalty_minutes",
                off_allowed=True,
                hint="Otomatis ditambahkan ke late_minutes saat resolusi 'Lupa Absen' dipilih. Off = no auto-add.",
            ),
            self._numeric_off_section(
                "Pulang Cepat Threshold (menit)",
                "pulang_cepat_threshold_minutes",
                off_allowed=True,
                hint="Pulang cepat > nilai ini -> flag case F. Off = no flagging.",
            ),
            self._numeric_off_section(
                "Repeat Offender (minggu berturut)",
                "repeat_offender_weeks",
                off_allowed=False,
                hint="Karyawan dianggap repeat offender bila telat di sejumlah minggu berturut ini.",
            ),
            self._time_section("Working Hours Start", "working_hours_start"),
            self._time_section("Working Hours End", "working_hours_end"),
        ]

        save_btn = ft.ElevatedButton(
            "Save Settings",
            icon=ft.Icons.SAVE,
            on_click=lambda e: self._save(),
            bgcolor=COLORS["primary"], color="white",
        )

        return ft.Container(
            padding=28, expand=True,
            content=ft.Column(scroll=ft.ScrollMode.AUTO, spacing=14, controls=[
                ft.Text("Settings", size=28, weight=ft.FontWeight.W_800),
                ft.Text(
                    "Configurable thresholds. Perubahan langsung tersimpan setelah klik Save.",
                    size=13, opacity=0.7,
                ),
                ft.Container(height=8),
                *sections,
                ft.Container(height=12),
                ft.Row(controls=[save_btn, ft.Container(width=12), self.status_text]),
            ]),
        )

    def _numeric_off_section(
        self, label: str, key: str, off_allowed: bool, hint: str,
    ) -> ft.Control:
        current = self.cfg.get(key)
        is_off = current is None
        off_switch = ft.Switch(
            label="Off (no policy)",
            value=is_off,
            visible=off_allowed,
            on_change=lambda e, k=key: self._toggle_off(k, e.control.value),
        )
        num_field = ft.TextField(
            label=label,
            value="" if is_off else str(current),
            width=220,
            disabled=is_off and off_allowed,
        )
        self.fields[key] = (num_field, off_switch if off_allowed else None)
        row_controls = [num_field, off_switch] if off_allowed else [num_field]
        return ft.Container(
            padding=14, border_radius=10,
            bgcolor=f"{COLORS['primary']}08",
            content=ft.Column(spacing=8, controls=[
                ft.Row(spacing=14, controls=row_controls),
                ft.Text(hint, size=11, opacity=0.65),
            ]),
        )

    def _time_section(self, label: str, key: str) -> ft.Control:
        current = self.cfg.get(key, "08:00")
        field = ft.TextField(
            label=label, value=current, width=180, hint_text="HH:MM",
        )
        self.fields[key] = (field, None)
        return ft.Container(
            padding=14, border_radius=10,
            bgcolor=f"{COLORS['primary']}08",
            content=field,
        )

    def _toggle_off(self, key: str, is_off: bool):
        field, _ = self.fields[key]
        field.disabled = is_off
        if is_off:
            field.value = ""
        field.update()

    def _save(self):
        update = {}
        for key, (field, off_switch) in self.fields.items():
            if off_switch is not None and off_switch.value:
                update[key] = None
                continue
            val = (field.value or "").strip()
            if not val:
                self._set_status(f"Error: {key} kosong", ok=False)
                return
            if ":" in val:
                # Time field: keep HH:MM format, basic shape check
                parts = val.split(":")
                if len(parts) != 2 or not (parts[0].isdigit() and parts[1].isdigit()):
                    self._set_status(f"Error: {key} harus format HH:MM", ok=False)
                    return
                update[key] = val
            else:
                try:
                    update[key] = int(val)
                except ValueError:
                    self._set_status(f"Error: {key} harus angka", ok=False)
                    return
        self.settings.update(update)
        self.cfg = self.settings.load()
        self._set_status("Settings saved", ok=True)
        if self.on_data_changed:
            self.on_data_changed()

    def _set_status(self, message: str, ok: bool):
        self.status_text.value = message
        self.status_text.color = COLORS["resolved"] if ok else COLORS["late_severe"]
        self.status_text.update()
