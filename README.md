# Josaphat Tech Solution — HR Attendance Manager

Single-user Windows desktop app for automating fingerprint attendance reporting.

## Run from source
```
pip install -r requirements.txt
python -m src.main
```

> Run with `-m` from the project root so Python resolves the `src.*` package imports correctly.

## Build .exe
See Phase 6 in `docs/superpowers/plans/2026-05-09-josaphat-tech-attendance.md`.

## Spec
See `docs/superpowers/specs/2026-05-09-josaphat-tech-attendance-design.md`.

## Build Standalone .exe

After completing development setup (`pip install -r requirements.txt`):

```
flet pack src/main.py --name "JosaphatTechHR" --icon assets/icon.ico --product-name "Josaphat Tech Solution HR Attendance Manager" --product-version "1.0.0"
```

> Requires `pyinstaller` (install with `pip install pyinstaller` if not already present — `flet pack` invokes it under the hood).

Output: `dist/JosaphatTechHR.exe` (~80-120 MB).

Copy this single file to any Windows machine — no Python install needed. The app will create `data/`, `config.json`, and `backups/` next to the .exe on first run.

## Backup for Laptop Migration

In-app: Backup/Restore page → Export ZIP → save to USB / cloud drive. On the new laptop, run the .exe once (creates empty data folder), then Backup/Restore → Import ZIP → restart app.
