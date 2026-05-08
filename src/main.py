import flet as ft
from pathlib import Path
from src.core.settings_store import SettingsStore
from src.ui.shell import Shell

DATA_DIR = Path(__file__).parent.parent / "data"
CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def main(page: ft.Page):
    page.title = "Josaphat Tech Solution — HR Attendance Manager"
    page.window.width = 1280
    page.window.height = 800
    page.padding = 0

    DATA_DIR.mkdir(exist_ok=True)
    settings = SettingsStore(str(CONFIG_PATH))
    settings.load()

    shell = Shell(page, settings)
    page.add(shell.build())


if __name__ == "__main__":
    ft.app(target=main)
