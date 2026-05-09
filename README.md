# Josaphat Tech Solution — HR Attendance Manager

Single-user Windows desktop app for automating fingerprint attendance reporting.

## Run from source
```
pip install -r requirements.txt
python main.py
```

> The legacy `python -m src.main` invocation also still works (`src/main.py` is a thin shim that defers to root `main.py`).

## Build .exe
See Phase 6 in `docs/superpowers/plans/2026-05-09-josaphat-tech-attendance.md`.

## Spec
See `docs/superpowers/specs/2026-05-09-josaphat-tech-attendance-design.md`.

## Build Standalone .exe

After completing development setup (`pip install -r requirements.txt`):

Easy way — use the helper script:
```
python scripts/build_exe.py
```

Or invoke `flet pack` directly:
```
flet pack main.py --name "JosaphatTechHR" --icon assets/icon.ico --product-name "Josaphat Tech Solution HR Attendance Manager" --product-version "1.0.2" --add-data "src/db/schema.sql;src/db" --add-data "assets/logo.svg;assets"
```

> Requires `pyinstaller` (install with `pip install pyinstaller` if not already present — `flet pack` invokes it under the hood).
>
> **Important:** Pack `main.py` from the project root, not `src/main.py`. The earlier path produced a broken bundle that crashed at startup with `ModuleNotFoundError: No module named 'src'`.
>
> **`--add-data` is required** so the SQLite schema and built-in logo SVG are bundled inside the .exe. Without these the app starts but errors at first DB init or PDF render.

Output: `dist/JosaphatTechHR.exe` (~80-120 MB).

Copy this single file to any Windows machine — no Python install needed. The app will create `data/`, `config.json`, and `backups/` next to the .exe on first run.

## Backup for Laptop Migration

In-app: Backup/Restore page → Export ZIP → save to USB / cloud drive. On the new laptop, run the .exe once (creates empty data folder), then Backup/Restore → Import ZIP → restart app.

## Custom Logo

To replace the placeholder Hex J logo with your real brand:
- Save your SVG as `assets/logo-custom.svg` (in the same folder as the .exe).
- Restart the app — the new logo will appear in the PDF report footer.
- The built-in placeholder remains as fallback if `logo-custom.svg` is missing.
