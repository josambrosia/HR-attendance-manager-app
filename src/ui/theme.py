import flet as ft
from src.core.constants import COLORS

def build_theme(mode: str = "dark") -> ft.Theme:
    """Return a Flet Theme configured with Sunset Coral palette."""
    return ft.Theme(
        color_scheme_seed=COLORS["primary"],
        color_scheme=ft.ColorScheme(
            primary=COLORS["primary"],
            secondary=COLORS["accent"],
            tertiary=COLORS["highlight"],
            surface=COLORS["surface_dark"] if mode == "dark" else COLORS["surface_light"],
            background=COLORS["bg_dark"] if mode == "dark" else COLORS["bg_light"],
            on_surface=COLORS["text_dark"] if mode == "dark" else COLORS["text_light"],
        ),
        font_family="Segoe UI",
    )

def get_bg_color(mode: str) -> str:
    return COLORS["bg_dark"] if mode == "dark" else COLORS["bg_light"]

def get_surface_color(mode: str) -> str:
    return COLORS["surface_dark"] if mode == "dark" else COLORS["surface_light"]

def get_text_color(mode: str) -> str:
    return COLORS["text_dark"] if mode == "dark" else COLORS["text_light"]
