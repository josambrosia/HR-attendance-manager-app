import flet as ft
from src.core.constants import COLORS

def ranking_row(position: int, name: str, total_late: int, days_late: int,
                max_late: int, max_late_date: str, max_value: int,
                is_repeat_offender: bool, coaching_threshold: int = 75) -> ft.Control:
    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(position, f"#{position}")
    border_color = {
        1: COLORS["late_severe"], 2: COLORS["late_severe"], 3: COLORS["late_mild"],
    }.get(position)
    over_threshold = total_late > coaching_threshold
    bar_pct = (total_late / max_value * 100) if max_value else 0

    name_row = [ft.Text(name, size=18, weight=ft.FontWeight.W_900)]
    if is_repeat_offender:
        name_row.append(ft.Text("🔥", size=14))

    over_text = " · over coaching threshold" if over_threshold else ""

    return ft.Container(
        padding=ft.padding.symmetric(horizontal=14, vertical=12),
        border_radius=10,
        bgcolor=f"{COLORS['primary']}08",
        border=ft.border.only(left=ft.BorderSide(4, border_color)) if border_color else None,
        content=ft.Row(spacing=14, alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
            ft.Container(width=50,
                         content=ft.Text(medal, size=24, text_align=ft.TextAlign.CENTER)),
            ft.Container(expand=True, content=ft.Column(spacing=2, controls=[
                ft.Row(spacing=6, controls=name_row),
                ft.Text(f"{days_late} hari telat · max {max_late} mnt ({max_late_date}){over_text}",
                        size=11, opacity=0.7),
            ])),
            ft.Container(width=130, content=ft.Container(
                height=10, border_radius=6,
                bgcolor=f"{COLORS['primary']}11",
                content=ft.Container(
                    width=bar_pct * 1.3, height=10, border_radius=6,
                    gradient=ft.LinearGradient(
                        begin=ft.alignment.center_left, end=ft.alignment.center_right,
                        colors=[COLORS["late_severe"], COLORS["accent"]] if over_threshold
                                else [COLORS["pulang_cepat"], COLORS["primary"]],
                    ),
                ),
            )),
            ft.Container(width=80, content=ft.Text(
                f"{total_late} mnt", size=18, weight=ft.FontWeight.W_900,
                color=COLORS["late_severe"] if over_threshold else None,
                text_align=ft.TextAlign.RIGHT,
            )),
        ]),
    )
