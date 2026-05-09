import flet as ft
from datetime import date, timedelta
from src.core.constants import COLORS
from src.db.repository import Repository
from src.core.settings_store import SettingsStore

CASE_LABELS = {
    "A": ("Tidak Hadir", COLORS["late_severe"]),
    "B": ("Lupa Absen Masuk", COLORS["late_mild"]),
    "C": ("Lupa Absen Pulang", COLORS["late_mild"]),
    "F": ("Pulang Cepat", COLORS["pulang_cepat"]),
}

# AI suggestion text for each issue case
_AI_SUGGESTIONS = {
    "A": "Kemungkinan: Tidak Hadir, Cuti, atau Izin Sakit?",
    "B": "Kemungkinan: Lupa Absen Masuk, atau Izin Pagi?",
    "C": "Kemungkinan: Lupa Absen Pulang, atau Pulang Lebih Awal?",
    "F": "Kemungkinan: Pulang Lebih Awal dengan alasan?",
}

# Grouping of reason codes into 4 categories for the modal UI
_REASON_CATEGORIES = [
    ("Tugas (di luar kantor)", [
        ("tugas_lapangan", "Tugas Lapangan", "Field/site visit"),
        ("tugas_paparan", "Tugas Paparan", "Presentasi luar"),
    ]),
    ("Cuti / Sakit / Izin", [
        ("sakit", "Izin Sakit", "Sakit (tanpa input)"),
        ("cuti", "Cuti", "Cuti tahunan / besar"),
        ("izin_pagi", "Izin Pagi", "Datang siang, ada urusan"),
        ("pulang_awal", "Pulang Lebih Awal", "Keluar dini, ada urusan"),
    ]),
    ("Telat / Lupa Absen", [
        ("telat_kerja", "Masuk Terlambat (Pekerjaan)", "Krn meeting / urusan kerja"),
        ("telat_personal", "Terlambat (personal)", "Telat tanpa alasan kerja"),
        ("lupa_absen", "Lupa Absen", "+16 mnt penalty otomatis"),
    ]),
    ("Lain", [
        ("belum_kabar", "Belum Ada Kabar", "Sementara, blm tau alasan"),
        ("tidak_hadir", "Tidak Hadir", "Resmi tidak hadir"),
    ]),
]

# Codes that require extra input
_REASON_NEEDS_INPUT = {
    "tugas_lapangan": "location",
    "tugas_paparan": "location",
    "izin_pagi": "reason_detail",
    "pulang_awal": "reason_detail",
    "telat_kerja": "reason_detail",
}


class IssuesPage:
    # Maps reason_code → friendly Indonesian label, used in resolution slot
    _RESOLUTION_LABELS = {
        "tugas_lapangan": "Lapangan",
        "tugas_paparan": "Paparan",
        "sakit": "Izin Sakit",
        "cuti": "Cuti",
        "izin_pagi": "Izin Pagi",
        "pulang_awal": "Pulang Lebih Awal",
        "telat_kerja": "Telat (kerja)",
        "telat_personal": "Terlambat",
        "lupa_absen": "Lupa Absen",
        "belum_kabar": "Belum Ada Kabar",
        "tidak_hadir": "Tidak Hadir",
    }

    def __init__(self, page: ft.Page, repo: Repository, settings: SettingsStore,
                 mode: str = "dark",
                 on_data_changed=None,
                 show_loading=None, hide_loading=None, notify=None):
        self.page = page
        self.repo = repo
        self.settings = settings
        self.mode = mode
        self.on_data_changed = on_data_changed
        self.show_loading = show_loading
        self.hide_loading = hide_loading
        self.notify = notify
        # Default: current week (Mon-Sun)
        today = date.today()
        self.start = today - timedelta(days=today.weekday())
        self.end = self.start + timedelta(days=6)
        self._refresh_timer = None
        # Filled in build() — kept here so methods can reference safely before build
        self.list_view: ft.Column | None = None
        self._stat_pending: ft.Container | None = None
        self._stat_resolved: ft.Container | None = None
        self._stat_total: ft.Container | None = None
        self._modal: "ResolveModal | None" = None

    def build(self) -> ft.Control:
        self.list_view = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=4, expand=True)
        self._stat_pending = self._build_stat_chip("0", "Pending", "pending")
        self._stat_resolved = self._build_stat_chip("0", "Resolved", "resolved")
        self._stat_total = self._build_stat_chip("0", "Total", "total")
        self.subtitle_text = ft.Text("", size=12, opacity=0.7)

        self._modal = ResolveModal(
            self.page, self.repo, self.settings,
            on_resolved=self._on_modal_resolved,
            on_deleted=self._on_modal_deleted,
        )

        self._refresh_list()
        return ft.Container(
            padding=24, expand=True,
            content=ft.Column(spacing=12, expand=True, controls=[
                ft.Row(controls=[
                    ft.Column(spacing=2, controls=[
                        ft.Text("Issues", size=28, weight=ft.FontWeight.W_800),
                        self.subtitle_text,
                    ]),
                    ft.Container(expand=True),
                    self._build_period_selector(),
                ]),
                ft.Row(spacing=10, controls=[
                    self._stat_pending, self._stat_resolved, self._stat_total,
                ]),
                ft.Container(expand=True, content=self.list_view),
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

    def _build_stat_chip(self, count: str, label: str, kind: str) -> ft.Container:
        if kind == "pending":
            color = COLORS["late_severe"]
            bg = f"{COLORS['late_severe']}2E"
        elif kind == "resolved":
            color = COLORS["resolved"]
            bg = f"{COLORS['resolved']}2E"
        else:
            color = COLORS["primary"]
            bg = f"{COLORS['primary']}2E"
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            border_radius=999,
            bgcolor=bg,
            border=ft.border.only(left=ft.BorderSide(2, color)),
            content=ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.Text(count, size=18, weight=ft.FontWeight.W_800, color=color),
                ft.Text(label, size=12, weight=ft.FontWeight.W_600, opacity=0.85),
            ]),
        )

    def _on_modal_resolved(self):
        self._refresh_list()
        if self.notify:
            self.notify("Issue resolved")
        if self.on_data_changed:
            self.on_data_changed()

    def _on_modal_deleted(self):
        self._refresh_list()
        if self.notify:
            self.notify("Resolution dihapus")
        if self.on_data_changed:
            self.on_data_changed()

    def _refresh_list(self):
        from src.core.alasan_format import format_alasan
        self.list_view.controls.clear()
        issues = self.repo.list_issues_with_resolutions(
            self.start.isoformat(), self.end.isoformat(),
        )
        pending = [i for i in issues if i.get("reason_code") is None]
        resolved = [i for i in issues if i.get("reason_code") is not None]

        self._set_chip_count(self._stat_pending, len(pending))
        self._set_chip_count(self._stat_resolved, len(resolved))
        self._set_chip_count(self._stat_total, len(issues))
        self.subtitle_text.value = (
            f"{len(issues)} total · {len(pending)} pending · "
            f"{len(resolved)} resolved · period {self.start} → {self.end}"
        )

        if not issues:
            self.list_view.controls.append(self._empty_state())
            return

        self.list_view.controls.append(self._build_section_divider(
            "⚠️ Belum Ditangani", len(pending), "pending"))
        if pending:
            for issue in pending:
                self.list_view.controls.append(self._build_pending_row(issue))
        else:
            self.list_view.controls.append(self._section_empty(
                "Tidak ada issue pending minggu ini ✨"))

        self.list_view.controls.append(self._build_section_divider(
            "✅ Sudah Ditangani", len(resolved), "resolved"))
        if resolved:
            for issue in resolved:
                alasan = format_alasan(
                    issue.get("reason_code"), issue.get("location"),
                    issue.get("reason_detail"),
                )
                self.list_view.controls.append(self._build_resolved_row(issue, alasan))
        else:
            self.list_view.controls.append(self._section_empty(
                "Belum ada yang di-resolve di periode ini."))

    def _set_chip_count(self, chip: ft.Container, count: int) -> None:
        chip.content.controls[0].value = str(count)

    def _build_section_divider(self, label: str, count: int, kind: str) -> ft.Control:
        if kind == "pending":
            chip_color = COLORS["late_severe"]
            chip_bg = f"{COLORS['late_severe']}2E"
        else:
            chip_color = COLORS["resolved"]
            chip_bg = f"{COLORS['resolved']}2E"
        return ft.Row(spacing=10, controls=[
            ft.Text(label, size=13, weight=ft.FontWeight.W_700, color=COLORS["accent"]),
            ft.Container(
                padding=ft.padding.symmetric(horizontal=10, vertical=2),
                border_radius=999, bgcolor=chip_bg,
                content=ft.Text(str(count), size=11, weight=ft.FontWeight.W_800, color=chip_color),
            ),
            ft.Container(expand=True, height=1,
                         gradient=ft.LinearGradient(
                             begin=ft.alignment.center_left,
                             end=ft.alignment.center_right,
                             colors=[f"{COLORS['accent']}55", "transparent"])),
        ])

    def _section_empty(self, msg: str) -> ft.Control:
        return ft.Container(
            padding=ft.padding.symmetric(vertical=14, horizontal=12),
            content=ft.Text(msg, size=12, italic=True, opacity=0.55),
        )

    def _empty_state(self) -> ft.Control:
        return ft.Container(
            padding=40, alignment=ft.alignment.center,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=48, color=COLORS["resolved"]),
                    ft.Text("Tidak ada issue di periode ini ✨", size=14),
                ]),
        )

    def _build_pending_row(self, issue: dict) -> ft.Control:
        case_label, case_color = CASE_LABELS.get(
            issue["issue_case"], (issue["issue_case"], "#999"))
        in_val = issue.get("actual_in") or "kosong"
        out_val = issue.get("actual_out") or "kosong"
        in_color = COLORS["resolved"] if issue.get("actual_in") else COLORS["late_severe"]
        out_color = COLORS["resolved"] if issue.get("actual_out") else COLORS["late_severe"]
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border_radius=8,
            bgcolor=f"{COLORS['late_severe']}1A",
            border=ft.border.only(left=ft.BorderSide(3, COLORS["late_severe"])),
            on_click=lambda e, iss=issue: self._open_resolve_modal(iss, edit_mode=False),
            ink=True,
            content=ft.Row(spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                ft.Container(width=140, content=ft.Column(spacing=2, controls=[
                    ft.Text(issue["employee_name"], size=13, weight=ft.FontWeight.W_700),
                    ft.Text(f"{issue['date']} · {issue.get('day_name','')}",
                            size=10, opacity=0.7),
                ])),
                ft.Container(width=170, content=ft.Column(spacing=2, controls=[
                    ft.Row(spacing=4, controls=[
                        ft.Text("In:", size=11, opacity=0.55),
                        ft.Text(in_val, size=11, color=in_color,
                                font_family="Courier New", weight=ft.FontWeight.W_600),
                    ]),
                    ft.Row(spacing=4, controls=[
                        ft.Text("Out:", size=11, opacity=0.55),
                        ft.Text(out_val, size=11, color=out_color,
                                font_family="Courier New", weight=ft.FontWeight.W_600),
                    ]),
                ])),
                ft.Container(expand=True, content=ft.Text(
                    "— belum ditangani —", size=11, italic=True, opacity=0.45,
                )),
                ft.Container(
                    width=110,
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    border_radius=8, bgcolor=case_color,
                    content=ft.Text(case_label, color="white", size=10,
                                    weight=ft.FontWeight.W_700,
                                    text_align=ft.TextAlign.CENTER),
                ),
                ft.Container(
                    width=95,
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    border_radius=999,
                    bgcolor=f"{COLORS['late_severe']}2E",
                    border=ft.border.all(1, f"{COLORS['late_severe']}73"),
                    content=ft.Row(spacing=4, alignment=ft.MainAxisAlignment.CENTER,
                                    controls=[
                        ft.Text("⚠", size=10),
                        ft.Text("Pending", size=10, weight=ft.FontWeight.W_800,
                                color=COLORS["late_severe"]),
                    ]),
                ),
            ]),
        )

    def _build_resolved_row(self, issue: dict, alasan_text: str) -> ft.Control:
        case_label, case_color = CASE_LABELS.get(
            issue["issue_case"], (issue["issue_case"], "#999"))
        in_val = issue.get("actual_in") or "kosong"
        out_val = issue.get("actual_out") or "kosong"
        in_color = COLORS["resolved"] if issue.get("actual_in") else COLORS["late_severe"]
        out_color = COLORS["resolved"] if issue.get("actual_out") else COLORS["late_severe"]
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border_radius=8,
            bgcolor=f"{COLORS['resolved']}10",
            border=ft.border.only(left=ft.BorderSide(3, COLORS["resolved"])),
            opacity=0.78,
            on_click=lambda e, iss=issue: self._open_resolve_modal(iss, edit_mode=True),
            ink=True,
            content=ft.Row(spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                ft.Container(width=140, content=ft.Column(spacing=2, controls=[
                    ft.Text(issue["employee_name"], size=13, weight=ft.FontWeight.W_700),
                    ft.Text(f"{issue['date']} · {issue.get('day_name','')}",
                            size=10, opacity=0.7),
                ])),
                ft.Container(width=170, content=ft.Column(spacing=2, controls=[
                    ft.Row(spacing=4, controls=[
                        ft.Text("In:", size=11, opacity=0.55),
                        ft.Text(in_val, size=11, color=in_color,
                                font_family="Courier New", weight=ft.FontWeight.W_600),
                    ]),
                    ft.Row(spacing=4, controls=[
                        ft.Text("Out:", size=11, opacity=0.55),
                        ft.Text(out_val, size=11, color=out_color,
                                font_family="Courier New", weight=ft.FontWeight.W_600),
                    ]),
                ])),
                ft.Text(f"✓ {alasan_text}", size=11, italic=True,
                        color=COLORS["resolved"], expand=True),
                ft.Container(
                    width=110,
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    border_radius=8, bgcolor=case_color,
                    content=ft.Text(case_label, color="white", size=10,
                                    weight=ft.FontWeight.W_700,
                                    text_align=ft.TextAlign.CENTER),
                ),
                ft.Container(
                    width=95,
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    border_radius=999,
                    bgcolor=f"{COLORS['resolved']}2E",
                    border=ft.border.all(1, f"{COLORS['resolved']}73"),
                    content=ft.Row(spacing=4, alignment=ft.MainAxisAlignment.CENTER,
                                    controls=[
                        ft.Text("✓", size=10, color=COLORS["resolved"]),
                        ft.Text("Resolved", size=10, weight=ft.FontWeight.W_800,
                                color=COLORS["resolved"]),
                    ]),
                ),
            ]),
        )

    def _open_resolve_modal(self, issue: dict, edit_mode: bool) -> None:
        if self._modal:
            self._modal.open_for(issue, edit_mode=edit_mode)


class ResolveModal:
    """Centered 720px dialog for resolving / editing an Issue.

    Constructed once per IssuesPage; mounts itself onto page.overlay; toggles
    visibility via open_for() / close(). Keeps its widget tree alive across
    open/close cycles to avoid Flet's "control already added" issues.
    """

    def __init__(self, page: ft.Page, repo: Repository, settings: SettingsStore,
                 on_resolved=None, on_deleted=None):
        self.page = page
        self.repo = repo
        self.settings = settings
        self.on_resolved = on_resolved
        self.on_deleted = on_deleted

        # Per-open state
        self._issue: dict | None = None
        self._edit_mode = False
        self._selected_reason: str | None = None

        # Build widgets that we'll mutate later
        self._header_title = ft.Text("Resolve Issue", size=20,
                                      weight=ft.FontWeight.W_800)
        self._header_meta = ft.Text("", size=13, color=COLORS["accent"])
        self._summary_text = ft.Text("", size=14,
                                      font_family="Courier New")
        self._cancel_btn = ft.TextButton(
            "Cancel", on_click=lambda e: self.close(),
        )
        self._save_btn = ft.ElevatedButton(
            "Save Resolution", on_click=lambda e: self._save(),
            bgcolor=COLORS["resolved"], color="white", disabled=True,
        )
        self._delete_btn = ft.TextButton(
            "🗑 Delete Resolution",
            on_click=lambda e: self._confirm_delete(),
            visible=False,
            style=ft.ButtonStyle(color=COLORS["late_severe"]),
        )

        # AI banner widgets (mutable text)
        self._ai_label = ft.Text("AI MENYARANKAN", size=11,
                                  weight=ft.FontWeight.W_800,
                                  color=COLORS["primary"], opacity=0.85)
        self._ai_suggestion_text = ft.Text("", size=13)

        # Reason cards keyed by code (built once, mounted in body)
        self._reason_cards: dict[str, ft.Container] = {}

        # Body placeholder (Tasks 6-7 will fill this)
        self._body_placeholder = ft.Column(spacing=12, controls=[])
        self._build_reason_cards_into_body()

        # Extra-input area (hidden by default; shown when reason needs input)
        self._extra_input_label = ft.Text("", size=11,
                                           weight=ft.FontWeight.W_800,
                                           color=COLORS["accent"])
        self._extra_input_field = ft.TextField(
            label="", hint_text="", expand=True,
            on_change=lambda e: self._on_extra_input_change(),
        )
        self._extra_input_hint = ft.Text(
            "Field wajib diisi sebelum Save.",
            size=10, color=COLORS["accent"], opacity=0.7,
        )
        self._extra_input_area = ft.Container(
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            border_radius=10,
            bgcolor=f"{COLORS['accent']}14",
            border=ft.border.all(1, f"{COLORS['accent']}55"),
            visible=False,
            content=ft.Column(spacing=6, controls=[
                self._extra_input_label,
                self._extra_input_field,
                self._extra_input_hint,
            ]),
        )

        # Live preview strip
        self._live_preview_text = ft.Text("", size=12, italic=True,
                                           color=COLORS["resolved"])
        self._live_preview_area = ft.Container(
            padding=ft.padding.symmetric(horizontal=12, vertical=9),
            border_radius=6,
            bgcolor=f"{COLORS['resolved']}14",
            border=ft.border.only(left=ft.BorderSide(3, COLORS["resolved"])),
            visible=False,
            content=ft.Row(spacing=6, controls=[
                ft.Text("Preview di Main DB:", size=11, weight=ft.FontWeight.W_700,
                        color=COLORS["resolved"], opacity=0.85),
                self._live_preview_text,
            ]),
        )

        # Append to body placeholder so they appear below reason categories
        self._body_placeholder.controls.append(self._extra_input_area)
        self._body_placeholder.controls.append(self._live_preview_area)

        self._dialog = ft.Container(
            top=0, left=0, right=0, bottom=0,
            bgcolor=f"{COLORS['bg_dark']}C7",  # ~78% alpha dim
            visible=False,
            on_click=lambda e: None,  # absorb clicks on dim layer
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=720,
                        padding=0,
                        border_radius=16,
                        bgcolor=COLORS["surface_dark"],
                        border=ft.border.all(2, COLORS["primary"]),
                        content=ft.Column(spacing=0, controls=[
                            # Header
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=24,
                                                              vertical=18),
                                border=ft.border.only(bottom=ft.BorderSide(
                                    1, f"{COLORS['accent']}33")),
                                content=ft.Row(controls=[
                                    ft.Column(spacing=2, controls=[
                                        self._header_title,
                                        self._header_meta,
                                    ]),
                                    ft.Container(expand=True),
                                    ft.IconButton(
                                        ft.Icons.CLOSE,
                                        on_click=lambda e: self.close(),
                                    ),
                                ]),
                            ),
                            # Issue summary strip
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=24,
                                                              vertical=14),
                                bgcolor=f"{COLORS['late_severe']}14",
                                border=ft.border.only(bottom=ft.BorderSide(
                                    1, f"{COLORS['late_severe']}40")),
                                content=self._summary_text,
                            ),
                            # Body (reason cards, extra input, preview — Tasks 6-7)
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=24,
                                                              vertical=16),
                                content=self._body_placeholder,
                            ),
                            # Footer
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=24,
                                                              vertical=14),
                                border=ft.border.only(top=ft.BorderSide(
                                    1, f"{COLORS['accent']}33")),
                                content=ft.Row(controls=[
                                    self._delete_btn,
                                    ft.Container(expand=True),
                                    self._cancel_btn,
                                    self._save_btn,
                                ]),
                            ),
                        ]),
                    ),
                ],
            ),
        )
        page.overlay.append(self._dialog)

    def _build_reason_cards_into_body(self) -> None:
        """Populate self._body_placeholder with AI banner + 4 categories."""
        # AI banner (top of body)
        ai_banner = ft.Container(
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border_radius=10,
            bgcolor=f"{COLORS['primary']}1A",
            border=ft.border.all(1, f"{COLORS['primary']}44"),
            content=ft.Row(spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                ft.Container(
                    width=32, height=32,
                    border_radius=8,
                    bgcolor=f"{COLORS['primary']}33",
                    alignment=ft.alignment.center,
                    content=ft.Text("🤖", size=16),
                ),
                ft.Column(spacing=2, controls=[
                    self._ai_label,
                    self._ai_suggestion_text,
                ]),
            ]),
        )

        body_label = ft.Text("PILIH ALASAN", size=11,
                              weight=ft.FontWeight.W_800,
                              color=COLORS["accent"],
                              opacity=0.85)

        category_widgets = []
        for cat_name, codes_in_cat in _REASON_CATEGORIES:
            cards_in_cat = []
            for code, label, hint in codes_in_cat:
                card = self._build_reason_card(code, label, hint)
                self._reason_cards[code] = card
                cards_in_cat.append(card)
            category_widgets.append(ft.Container(
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border_radius=10,
                bgcolor=f"{COLORS['surface_dark']}80",
                border=ft.border.all(1, f"{COLORS['accent']}33"),
                content=ft.Column(spacing=8, controls=[
                    ft.Text(cat_name.upper(), size=10,
                            weight=ft.FontWeight.W_800,
                            color=COLORS["accent"]),
                    ft.GridView(
                        runs_count=3,
                        max_extent=220,
                        spacing=8,
                        run_spacing=8,
                        child_aspect_ratio=2.4,
                        controls=cards_in_cat,
                    ),
                ]),
            ))

        self._body_placeholder.controls = [
            ai_banner,
            body_label,
            *category_widgets,
        ]

    def _build_reason_card(self, code: str, label: str, hint: str) -> ft.Container:
        needs_input = code in _REASON_NEEDS_INPUT
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=11, vertical=9),
            border_radius=8,
            bgcolor=f"{COLORS['primary']}1A",
            border=ft.border.only(left=ft.BorderSide(2, f"{COLORS['primary']}55")),
            on_click=lambda e, c=code: self._select_reason(c),
            ink=True,
            content=ft.Column(spacing=2, controls=[
                ft.Text(
                    f"{label}{' ✏️' if needs_input else ''}",
                    size=12, weight=ft.FontWeight.W_700,
                ),
                ft.Text(hint, size=10, color=COLORS["accent"], opacity=0.75),
            ]),
        )

    def _select_reason(self, code: str) -> None:
        self._selected_reason = code
        # Visual: highlight selected card, reset others
        for c, card in self._reason_cards.items():
            if c == code:
                card.bgcolor = f"{COLORS['accent']}33"
                card.border = ft.border.only(
                    left=ft.BorderSide(3, COLORS["accent"]))
            else:
                card.bgcolor = f"{COLORS['primary']}1A"
                card.border = ft.border.only(
                    left=ft.BorderSide(2, f"{COLORS['primary']}55"))

        # Extra-input area visibility + label
        extra_kind = _REASON_NEEDS_INPUT.get(code)
        if extra_kind == "location":
            self._extra_input_area.visible = True
            self._extra_input_label.value = "📍 LOKASI *"
            self._extra_input_field.label = "Lokasi"
            self._extra_input_field.hint_text = "Misal: Kantor Klien Surabaya, Site PT XYZ"
        elif extra_kind == "reason_detail":
            self._extra_input_area.visible = True
            self._extra_input_label.value = "✏️ ALASAN DETAIL *"
            self._extra_input_field.label = "Alasan detail"
            self._extra_input_field.hint_text = "Singkat alasan kenapa terjadi"
        else:
            self._extra_input_area.visible = False
            self._extra_input_field.value = ""

        # Live preview area visible whenever a reason is picked
        self._live_preview_area.visible = True
        self._update_live_preview()
        self._update_save_btn_state()
        try:
            self._dialog.update()
        except (AssertionError, AttributeError):
            pass

    def _on_extra_input_change(self) -> None:
        self._update_live_preview()
        self._update_save_btn_state()
        try:
            self._dialog.update()
        except (AssertionError, AttributeError):
            pass

    def _update_live_preview(self) -> None:
        from src.core.alasan_format import format_alasan
        if self._selected_reason is None:
            self._live_preview_text.value = ""
            return
        extra = _REASON_NEEDS_INPUT.get(self._selected_reason)
        location = self._extra_input_field.value if extra == "location" else None
        reason_detail = self._extra_input_field.value if extra == "reason_detail" else None
        self._live_preview_text.value = format_alasan(
            self._selected_reason, location, reason_detail,
        )

    def _update_save_btn_state(self) -> None:
        if self._selected_reason is None:
            self._save_btn.disabled = True
            return
        extra = _REASON_NEEDS_INPUT.get(self._selected_reason)
        if extra and not (self._extra_input_field.value or "").strip():
            self._save_btn.disabled = True
        else:
            self._save_btn.disabled = False

    def open_for(self, issue: dict, edit_mode: bool = False) -> None:
        self._issue = issue
        self._edit_mode = edit_mode
        self._selected_reason = issue.get("reason_code") if edit_mode else None

        case_label = CASE_LABELS.get(issue["issue_case"],
                                      (issue["issue_case"], "#999"))[0]
        self._header_meta.value = (
            f"{issue['employee_name']} · {issue['date']} "
            f"({issue.get('day_name','')}) · {case_label}"
        )
        in_val = issue.get("actual_in") or "kosong"
        out_val = issue.get("actual_out") or "kosong"
        self._summary_text.value = f"In: {in_val}     Out: {out_val}"

        # Update AI banner suggestion based on issue case
        self._ai_suggestion_text.value = _AI_SUGGESTIONS.get(
            issue["issue_case"], "")
        # Reset card highlight (clear previous open's selection state)
        for code, card in self._reason_cards.items():
            if code == self._selected_reason:
                card.bgcolor = f"{COLORS['accent']}33"
                card.border = ft.border.only(
                    left=ft.BorderSide(3, COLORS["accent"]))
            else:
                card.bgcolor = f"{COLORS['primary']}1A"
                card.border = ft.border.only(
                    left=ft.BorderSide(2, f"{COLORS['primary']}55"))

        self._delete_btn.visible = edit_mode
        self._save_btn.text = "Update Resolution" if edit_mode else "Save Resolution"
        self._save_btn.disabled = not edit_mode  # Tasks 7+ refine this

        self._dialog.visible = True
        try:
            self.page.update()
        except (AssertionError, AttributeError):
            pass

    def close(self) -> None:
        self._dialog.visible = False
        try:
            self.page.update()
        except (AssertionError, AttributeError):
            pass

    def _save(self) -> None:
        # Stub — Task 8 implements
        pass

    def _confirm_delete(self) -> None:
        # Stub — Task 8 implements
        pass
