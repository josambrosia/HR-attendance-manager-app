import flet as ft
from src.core.constants import COLORS

def hexagon_j(size: int = 40, with_wordmark: bool = True, mode: str = "dark") -> ft.Control:
    """Reusable Hex J logo. If with_wordmark=True, returns Row with brand text."""
    icon = ft.Container(
        width=size,
        height=size * 1.1,
        content=ft.Text(
            "J",
            color="white",
            weight=ft.FontWeight.W_900,
            size=size * 0.55,
            text_align=ft.TextAlign.CENTER,
        ),
        alignment=ft.alignment.center,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=[COLORS["primary"], COLORS["accent"]],
        ),
        shape=ft.BoxShape.RECTANGLE,
        # Hexagon clip via custom path is non-trivial in Flet — use rounded square
        # as visual fallback; final icon.ico will be true hexagon (Phase 6, Task 20).
        border_radius=size * 0.2,
        shadow=ft.BoxShadow(
            blur_radius=size * 0.2,
            color=f"{COLORS['primary']}66",
        ),
    )
    if not with_wordmark:
        return icon

    text_color = COLORS["text_dark"] if mode == "dark" else COLORS["text_light"]
    accent_color = COLORS["accent"] if mode == "dark" else COLORS["primary"]

    wordmark = ft.Column(
        spacing=2,
        controls=[
            ft.Text("Josaphat Tech Solution", weight=ft.FontWeight.W_800, size=14, color=text_color),
            ft.Text("HR Attendance Manager", size=10, color=accent_color),
        ],
    )
    return ft.Row(spacing=10, controls=[icon, wordmark])
