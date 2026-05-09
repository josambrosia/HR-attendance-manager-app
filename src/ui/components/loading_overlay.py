"""Top progress strip + dim layer that blocks clicks during long operations.

Mounted as two separate items in `page.overlay` (dim layer + top strip).
Both are toggled together via `show(label)` / `hide()`.
"""
import flet as ft

from src.core.constants import COLORS


class LoadingOverlay:
    def __init__(self, page: ft.Page):
        self.page = page
        self.label = ft.Text("", size=12, weight=ft.FontWeight.W_600,
                             color=COLORS["text_dark"])
        self.bar = ft.ProgressBar(expand=True, height=4,
                                   color=COLORS["accent"],
                                   bgcolor=f"{COLORS['primary']}33")

        # Dim layer fills the entire page so clicks (including sidebar nav) are absorbed.
        self.dim = ft.Container(
            top=0, left=0, right=0, bottom=0,
            bgcolor=f"{COLORS['bg_dark']}73",  # ~45% alpha
            on_click=lambda e: None,            # absorb clicks
            visible=False,
        )

        # Top strip with label + indeterminate progress bar.
        self.strip = ft.Container(
            top=0, left=0, right=0,
            bgcolor=f"{COLORS['surface_dark']}F2",  # ~95% alpha
            border=ft.border.only(bottom=ft.BorderSide(1, COLORS["primary"])),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            content=ft.Row(spacing=12, controls=[self.label, self.bar]),
            visible=False,
        )

        page.overlay.append(self.dim)
        page.overlay.append(self.strip)

    def show(self, label_text: str) -> None:
        self.label.value = label_text
        self.dim.visible = True
        self.strip.visible = True
        try:
            self.page.update()
        except (AssertionError, AttributeError):
            pass  # page not yet mounted (first paint) — safe to ignore

    def hide(self) -> None:
        self.dim.visible = False
        self.strip.visible = False
        try:
            self.page.update()
        except (AssertionError, AttributeError):
            pass
