import flet as ft
from src.core.constants import COLORS

def trivia_card(icon: str, label: str, value: str, meta: str, mode: str = "dark") -> ft.Control:
    return ft.Container(
        padding=12, border_radius=8,
        bgcolor=f"{COLORS['surface_dark']}88" if mode == "dark" else f"{COLORS['surface_light']}88",
        border=ft.border.all(1, f"{COLORS['primary']}22"),
        content=ft.Column(spacing=3, controls=[
            ft.Text(icon, size=15, opacity=0.8),
            ft.Text(label.upper(), size=9, weight=ft.FontWeight.W_600,
                    color=COLORS["accent"], opacity=0.85),
            ft.Text(value, size=14, weight=ft.FontWeight.W_700),
            ft.Text(meta, size=10, opacity=0.65),
        ]),
    )
