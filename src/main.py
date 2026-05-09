"""Compatibility shim — the entry point moved to project root `main.py`.

PyInstaller / flet pack treats `src/main.py` as a top-level script, which
broke `from src.X import Y` imports in the .exe build. The real entry is
now `main.py` at the project root.

This shim keeps `python -m src.main` working for anyone who memorized that
command (Tasks 4 onward used it during development).
"""
import sys
from pathlib import Path

# Add project root to sys.path so `import main` resolves
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import flet as ft  # noqa: E402
from main import main  # noqa: E402

if __name__ == "__main__":
    ft.app(target=main)
