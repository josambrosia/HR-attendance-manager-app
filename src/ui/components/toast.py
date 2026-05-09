"""Top-right stacked toast notifier (success / error).

Mounted as a single positioned Container in `page.overlay`; the Container
holds a Column whose children are individual toast Containers. Each toast
self-dismisses via threading.Timer (1.5s for success, 3.0s for error).
"""
import threading

import flet as ft

from src.core.constants import COLORS

_MAX_VISIBLE = 3
_DISMISS_SUCCESS_S = 1.5
_DISMISS_ERROR_S = 3.0


class ToastNotifier:
    def __init__(self, page: ft.Page):
        self.page = page
        self.stack = ft.Column(spacing=8)
        self.container = ft.Container(
            top=20, right=20, width=360,
            content=self.stack,
        )
        page.overlay.append(self.container)

    def success(self, title: str, desc: str = "") -> None:
        self._add_toast(title, desc, COLORS["resolved"], "✅",
                        duration=_DISMISS_SUCCESS_S)

    def error(self, title: str, desc: str = "") -> None:
        self._add_toast(title, desc, COLORS["late_severe"], "❌",
                        duration=_DISMISS_ERROR_S)

    def _add_toast(self, title: str, desc: str, color: str,
                   icon: str, duration: float) -> None:
        # Evict oldest if we're already at the visible cap
        while len(self.stack.controls) >= _MAX_VISIBLE:
            self.stack.controls.pop(0)

        toast = self._build_toast(title, desc, color, icon)
        self.stack.controls.append(toast)
        self._safe_update()

        timer = threading.Timer(duration, lambda: self._dismiss(toast))
        timer.daemon = True
        timer.start()

    def _build_toast(self, title: str, desc: str,
                     color: str, icon: str) -> ft.Container:
        # max_lines=None + selectable=False allows multi-line wrap so long error
        # messages don't get clipped. expand=True on the inner Column lets text
        # consume the remaining width inside the 360px container.
        body_controls = [ft.Text(title, size=13, weight=ft.FontWeight.W_700,
                                  color=COLORS["text_dark"], max_lines=2)]
        if desc:
            body_controls.append(ft.Text(desc, size=11, opacity=0.8,
                                          color=COLORS["text_dark"], max_lines=4))

        return ft.Container(
            bgcolor=f"{COLORS['surface_dark']}D1",  # ~82% alpha
            border=ft.border.only(left=ft.BorderSide(3, color)),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            content=ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Text(icon, size=16),
                    ft.Column(spacing=2, controls=body_controls, expand=True),
                ],
            ),
        )

    def _dismiss(self, toast: ft.Container) -> None:
        if toast in self.stack.controls:
            self.stack.controls.remove(toast)
            self._safe_update()

    def _safe_update(self) -> None:
        try:
            self.stack.update()
        except (AssertionError, AttributeError):
            pass  # not mounted yet (initial paint) or already disposed
