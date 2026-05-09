import flet as ft
from src.core.constants import COLORS

ACCENT_COLORS = {
    "urgent": COLORS["late_severe"],
    "coaching": COLORS["accent"],
    "warning": COLORS["pulang_cepat"],
    "positive": COLORS["resolved"],
}

def vital_card(icon: str, label: str, value: str, meta: str, accent: str = "urgent",
               mode: str = "dark") -> ft.Control:
    color = ACCENT_COLORS.get(accent, COLORS["primary"])
    bg = COLORS["surface_dark"] if mode == "dark" else COLORS["surface_light"]
    return ft.Container(
        padding=18, border_radius=12,
        bgcolor=bg,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left, end=ft.alignment.bottom_right,
            colors=[bg, f"{color}22"],
        ),
        border=ft.border.all(1, f"{color}55"),
        content=ft.Column(spacing=4, controls=[
            ft.Text(icon, size=22),
            ft.Text(label.upper(), size=10, weight=ft.FontWeight.W_700,
                    color=COLORS["accent"], opacity=0.85),
            ft.Text(value, size=32, weight=ft.FontWeight.W_900, color=color),
            ft.Text(meta, size=11, opacity=0.7),
        ]),
    )
