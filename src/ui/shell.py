import flet as ft
from pathlib import Path
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
    ("Database", [
        ("main_database", "Main Database", ft.Icons.TABLE_VIEW),
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


# Routes that read attendance/resolution data — their cached widget tree
# must be dropped whenever data mutates (import, resolve, edit, restore,
# settings change that affects derived metrics).
_DATA_CONSUMING_ROUTES = (
    "dashboard", "issues", "main_database",
    "weekly_report", "monthly_report", "edit_records",
)


class Shell:
    def __init__(self, page: ft.Page, settings: SettingsStore, repo: Repository, snapshot_dir: str):
        self.page = page
        self.settings = settings
        self.repo = repo
        self.snapshot_dir = snapshot_dir
        self.mode = settings.get("theme", "dark")
        self.current_route = "dashboard"
        self.content_area = ft.Container(expand=True)
        # route -> nav button Container (for toggling active state without rebuilding sidebar)
        self._nav_buttons: dict[str, ft.Control] = {}
        # route -> built ft.Control (reuse on revisit; dropped on data change or theme toggle)
        self._page_cache: dict[str, ft.Control] = {}
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
                elif route == "edit_records":
                    builders[route] = self._build_edit_records_page
                elif route == "dashboard":
                    builders[route] = self._build_dashboard_page
                elif route == "main_database":
                    builders[route] = self._build_main_database_page
                elif route == "weekly_report":
                    builders[route] = self._build_weekly_report_page
                elif route == "monthly_report":
                    builders[route] = self._build_monthly_report_page
                elif route == "backup_restore":
                    builders[route] = self._build_backup_restore_page
                elif route == "settings":
                    builders[route] = self._build_settings_page
                else:
                    # Capture per-iteration via default args
                    builders[route] = (lambda r=route, t=label: _placeholder.build(t, self.mode))
        return builders

    def _build_import_data_page(self) -> ft.Control:
        from src.ui.pages.import_data import ImportDataPage
        page_obj = ImportDataPage(self.repo, self.settings, self.snapshot_dir, self.mode,
                                  on_data_changed=self.invalidate_data_caches)
        return page_obj.build()

    def _build_issues_page(self) -> ft.Control:
        from src.ui.pages.issues import IssuesPage
        page_obj = IssuesPage(self.repo, self.settings, self.mode,
                              on_data_changed=self.invalidate_data_caches)
        return page_obj.build()

    def _build_edit_records_page(self) -> ft.Control:
        from src.ui.pages.edit_records import EditRecordsPage
        page_obj = EditRecordsPage(self.repo, self.settings, self.mode,
                                   on_data_changed=self.invalidate_data_caches)
        return page_obj.build()

    def _build_dashboard_page(self) -> ft.Control:
        from src.ui.pages.dashboard import DashboardPage
        page_obj = DashboardPage(self.repo, self.settings, self.mode,
                                 nav_callback=self._navigate)
        return page_obj.build()

    def _build_main_database_page(self) -> ft.Control:
        from src.ui.pages.main_database import MainDatabasePage
        root = Path(self.snapshot_dir).parent
        page_obj = MainDatabasePage(
            self.repo, self.settings,
            str(root / "data" / "exports"),
            self.mode,
        )
        return page_obj.build()

    def _build_weekly_report_page(self) -> ft.Control:
        from src.ui.pages.weekly_report import WeeklyReportPage
        exports_dir = Path(self.snapshot_dir).parent / "data" / "exports"
        page_obj = WeeklyReportPage(self.repo, self.settings, str(exports_dir), self.mode)
        return page_obj.build()

    def _build_monthly_report_page(self) -> ft.Control:
        from src.ui.pages.monthly_report import MonthlyReportPage
        exports_dir = Path(self.snapshot_dir).parent / "data" / "exports"
        page_obj = MonthlyReportPage(self.repo, self.settings, str(exports_dir), self.mode)
        return page_obj.build()

    def _build_backup_restore_page(self) -> ft.Control:
        from src.ui.pages.backup_restore import BackupRestorePage
        root = Path(self.snapshot_dir).parent
        page_obj = BackupRestorePage(
            str(root / "data" / "app.db"),
            str(root / "config.json"),
            self.snapshot_dir,
            str(root / "backups" / "pre-restore"),
            self.mode,
            on_data_changed=self.invalidate_data_caches,
        )
        return page_obj.build()

    def _build_settings_page(self) -> ft.Control:
        from src.ui.pages.settings import SettingsPage
        page_obj = SettingsPage(self.settings, self.mode,
                                on_data_changed=self.invalidate_data_caches)
        return page_obj.build()

    def build(self) -> ft.Control:
        self._apply_theme()
        # Sidebar buttons are recreated; clear stale references so the new
        # buttons get registered into self._nav_buttons via _make_nav_button.
        self._nav_buttons.clear()
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
        container = ft.Container(
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
        # Track for cheap active-state toggling on _navigate (avoid full sidebar rebuild)
        self._nav_buttons[route] = container
        return container

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
        old = self.current_route
        self.current_route = route
        # Same-route click = explicit refresh signal (e.g. Dashboard period change
        # calls nav_callback("dashboard") to repaint with new start/end). Drop the
        # cached widget tree so it gets rebuilt with current state.
        if old == route:
            self._page_cache.pop(route, None)

        self._update_nav_active_state(old, route)
        self._render_page(route)
        # Update only the content_area instead of clearing & rebuilding the whole page.
        # The sidebar stays mounted; only the swapped widgets travel over the wire.
        try:
            self.content_area.update()
        except (AssertionError, AttributeError):
            # content_area not yet attached (unlikely from a click handler, but safe)
            self.page.update()

    def _update_nav_active_state(self, old_route: str, new_route: str):
        """Toggle bgcolor + font weight on affected nav buttons without rebuilding."""
        for route in (old_route, new_route):
            btn = self._nav_buttons.get(route)
            if btn is None:
                continue
            is_active = route == new_route
            btn.bgcolor = f"{COLORS['primary']}33" if is_active else None
            text = btn.content.controls[1]  # Row -> [Icon, Text]
            text.weight = ft.FontWeight.W_600 if is_active else ft.FontWeight.W_500
            try:
                btn.update()
            except (AssertionError, AttributeError):
                pass  # not yet mounted

    def invalidate_data_caches(self, *routes: str) -> None:
        """Drop cached page widget trees so they rebuild with fresh data on next visit.

        Called by pages that mutate the DB (Import, Issues resolve, Edit, Restore)
        or change settings that affect derived metrics. With no args, invalidates
        all data-consuming routes.
        """
        targets = routes if routes else _DATA_CONSUMING_ROUTES
        for r in targets:
            self._page_cache.pop(r, None)

    def _toggle_theme(self):
        self.mode = "light" if self.mode == "dark" else "dark"
        self.settings.update({"theme": self.mode})
        # Theme change repaints colors everywhere — drop all cached widget trees
        # so they rebuild with the new palette.
        self._page_cache.clear()
        self._apply_theme()
        self.page.controls.clear()
        self.page.add(self.build())
        self.page.update()

    def _apply_theme(self):
        self.page.bgcolor = COLORS["bg_dark"] if self.mode == "dark" else COLORS["bg_light"]
        self.page.theme_mode = ft.ThemeMode.DARK if self.mode == "dark" else ft.ThemeMode.LIGHT

    def _render_page(self, route: str):
        if route not in self._page_cache:
            builder = self._route_builders.get(route)
            if builder is None:
                # Fallback for unknown route — placeholder is cheap, cache it too
                self._page_cache[route] = _placeholder.build(route, self.mode)
            else:
                self._page_cache[route] = builder()
        self.content_area.content = self._page_cache[route]
