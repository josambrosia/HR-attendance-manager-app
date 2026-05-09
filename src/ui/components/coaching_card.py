import flet as ft
from src.core.constants import COLORS

def coaching_card(rank_emoji: str, name: str, total_late: int,
                  days_late: int, total_days: int, avg_per_day: int,
                  streak: int = 0) -> ft.Control:
    streak_text = f"🔥 {streak} mgg" if streak >= 2 else "—"
    return ft.Container(
        padding=18, border_radius=12,
        bgcolor=f"{COLORS['surface_dark']}cc",
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left, end=ft.alignment.bottom_right,
            colors=[f"{COLORS['surface_dark']}cc", f"{COLORS['late_severe']}22"],
        ),
        border=ft.border.all(1.5, f"{COLORS['late_severe']}88"),
        content=ft.Column(spacing=10, controls=[
            ft.Row(spacing=10, controls=[
                ft.Text(rank_emoji, size=22),
                ft.Text(name, size=20, weight=ft.FontWeight.W_900),
            ]),
            ft.Row(spacing=6, controls=[
                ft.Text("Akumulasi telat:", size=14, color=COLORS["late_severe"]),
                ft.Text(f"{total_late} menit", size=22, weight=ft.FontWeight.W_900,
                        color=COLORS["late_severe"]),
            ]),
            ft.Divider(height=1, opacity=0.2),
            ft.Row(spacing=20, controls=[
                _stat("Hari Telat", f"{days_late}/{total_days}"),
                _stat("Avg/Hari", f"{avg_per_day} mnt"),
                _stat("Streak", streak_text),
            ]),
        ]),
    )

def _stat(label: str, value: str) -> ft.Control:
    return ft.Column(spacing=2, controls=[
        ft.Text(label.upper(), size=9, weight=ft.FontWeight.W_600,
                color=COLORS["accent"], opacity=0.8),
        ft.Text(value, size=14, weight=ft.FontWeight.W_800),
    ])
