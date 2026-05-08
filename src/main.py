import flet as ft
from pathlib import Path
from src.core.settings_store import SettingsStore
from src.db.repository import Repository
from src.ui.shell import Shell

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
BACKUP_DIR = ROOT / "backups"
CONFIG_PATH = ROOT / "config.json"
DB_PATH = DATA_DIR / "app.db"


def main(page: ft.Page):
    page.title = "Josaphat Tech Solution — HR Attendance Manager"
    page.window.width = 1280
    page.window.height = 800
    page.padding = 0

    DATA_DIR.mkdir(exist_ok=True)
    BACKUP_DIR.mkdir(exist_ok=True)

    settings = SettingsStore(str(CONFIG_PATH))
    settings.load()

    repo = Repository(str(DB_PATH))
    repo.init_schema()

    shell = Shell(page, settings, repo, str(BACKUP_DIR))
    page.add(shell.build())


if __name__ == "__main__":
    ft.app(target=main)
