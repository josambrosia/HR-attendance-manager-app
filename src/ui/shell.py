import flet as ft
from src.core.constants import COLORS
from src.core.settings_store import SettingsStore
from src.db.repository import Repository
from src.ui.components.logo import hexagon_j
from src.ui.pages import _placeholder

NAV_GROUPS = [
    ("Workflow", [
        ("import_data", "Import Data", ft.Icons.UPLOAD_FILE),
        ("issues", "Issues", ft.Icons.WARNING_AMBER),
        ("dashboard", "Dashboard", ft.Icons.DASHBOARD),
    ]),
    ("Reports", [
        ("weekly_report", "Weekly Report", ft.Icons.CALENDAR_VIEW_WEEK),
        ("monthly_report", "Monthly Report", ft.Icons.CALENDAR_MONTH),
    ]),
    ("Tools", [
        ("edit_records", "Edit Records", ft.Icons.EDIT),
        ("backup_restore", "Backup / Restore", ft.Icons.BACKUP),
        ("settings", "Settings", ft.Icons.SETTINGS),
    ]),
]


class Shell:
    def __init__(self, page: ft.Page, settings: SettingsStore, repo: Repository, snapshot_dir: str):
        self.page = page
        self.settings = settings
        self.repo = repo
        self.snapshot_dir = snapshot_dir
        self.mode = settings.get("theme", "dark")
        self.current_route = "dashboard"
        self.content_area = ft.Container(expand=True)
        self._route_builders = self._init_route_builders()

    def _init_route_builders(self) -> dict:
        """Map route name -> builder callable. Builders take no args (use self.mode etc).

        Future tasks will replace placeholder entries with real page builders.
        Each builder returns the ft.Control to mount in content_area.
        """
        builders = {}
        for _, items in NAV_GROUPS:
            for route, label, _ in items:
                if route == "import_data":
                    builders[route] = self._build_import_data_page
                elif route == "issues":
                    builders[route] = self._build_issues_page
                else:
                    # Capture per-iteration via default args
                    builders[route] = (lambda r=route, t=label: _placeholder.build(t, self.mode))
        return builders

    def _build_import_data_page(self) -> ft.Control:
        from src.ui.pages.import_data import ImportDataPage
        page_obj = ImportDataPage(self.repo, self.settings, self.snapshot_dir, self.mode)
        return page_obj.build()

    def _build_issues_page(self) -> ft.Control:
        from src.ui.pages.issues import IssuesPage
        page_obj = IssuesPage(self.repo, self.settings, self.mode)
        return page_obj.build()

    def build(self) -> ft.Control:
        self._apply_theme()
        sidebar = self._build_sidebar()
        self._render_page(self.current_route)
        return ft.Row(
            expand=True, spacing=0,
            controls=[sidebar, self.content_area],
        )

    def _build_sidebar(self) -> ft.Control:
        nav_items = []
        for section_label, items in NAV_GROUPS:
            nav_items.append(
                ft.Text(section_label.upper(), size=10, weight=ft.FontWeight.W_700,
                        color=COLORS["accent"], opacity=0.8)
            )
            for route, label, icon in items:
                nav_items.append(self._make_nav_button(route, label, icon))
            nav_items.append(ft.Container(height=8))

        return ft.Container(
            width=240,
            bgcolor=COLORS["surface_dark"] if self.mode == "dark" else COLORS["surface_light"],
            padding=16,
            content=ft.Column(
                expand=True,
                controls=[
                    hexagon_j(size=40, with_wordmark=True, mode=self.mode),
                    ft.Container(height=20),
                    ft.Column(controls=nav_items, spacing=2),
                    ft.Container(expand=True),  # spacer
                    self._build_theme_toggle(),
                ],
            ),
        )

    def _make_nav_button(self, route: str, label: str, icon) -> ft.Control:
        is_active = route == self.current_route
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border_radius=8,
            bgcolor=f"{COLORS['primary']}33" if is_active else None,
            content=ft.Row(spacing=10, controls=[
                ft.Icon(icon, size=18,
                        color=COLORS["text_dark"] if self.mode == "dark" else COLORS["text_light"]),
                ft.Text(label, size=14,
                        weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.W_500),
            ]),
            on_click=lambda e, r=route: self._navigate(r),
            ink=True,
        )

    def _build_theme_toggle(self) -> ft.Control:
        is_dark = self.mode == "dark"
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=8,
            bgcolor=f"{COLORS['accent']}22",
            content=ft.Row(spacing=8, controls=[
                ft.Icon(ft.Icons.DARK_MODE if is_dark else ft.Icons.LIGHT_MODE, size=16),
                ft.Text("Dark Mode" if is_dark else "Light Mode", size=12),
            ]),
            on_click=lambda e: self._toggle_theme(),
            ink=True,
        )

    def _navigate(self, route: str):
        self.current_route = route
        # Rebuild sidebar so active state updates
        self.page.controls.clear()
        self.page.add(self.build())
        self.page.update()

    def _toggle_theme(self):
        self.mode = "light" if self.mode == "dark" else "dark"
        self.settings.update({"theme": self.mode})
        self._apply_theme()
        self.page.controls.clear()
        self.page.add(self.build())
        self.page.update()

    def _apply_theme(self):
        self.page.bgcolor = COLORS["bg_dark"] if self.mode == "dark" else COLORS["bg_light"]
        self.page.theme_mode = ft.ThemeMode.DARK if self.mode == "dark" else ft.ThemeMode.LIGHT

    def _render_page(self, route: str):
        builder = self._route_builders.get(route)
        if builder is None:
            # Fallback for unknown route
            self.content_area.content = _placeholder.build(route, self.mode)
            return
        self.content_area.content = builder()
