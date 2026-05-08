import flet as ft


def build(page_name: str, mode: str = "dark") -> ft.Control:
    return ft.Container(
        expand=True,
        alignment=ft.alignment.center,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(page_name, size=32, weight=ft.FontWeight.W_800),
                ft.Text("Page coming soon", size=14, opacity=0.6),
            ],
        ),
    )
