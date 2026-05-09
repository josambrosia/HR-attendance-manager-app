"""Build the standalone JosaphatTechHR.exe via flet pack.

Usage (from project root):
    python scripts/build_exe.py

Output:
    dist/JosaphatTechHR.exe  (~80-120 MB single-file Windows executable)

Requires:
    - flet (already in requirements.txt)
    - pyinstaller (install with `pip install pyinstaller` if missing —
      `flet pack` invokes it under the hood)
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Pack root main.py, NOT src/main.py — packing the latter produces a broken
# bundle that crashes at startup with "ModuleNotFoundError: No module named 'src'".
ENTRY_SCRIPT = PROJECT_ROOT / "main.py"
ICON = PROJECT_ROOT / "assets" / "icon.ico"
OUTPUT_NAME = "JosaphatTechHR"
PRODUCT_NAME = "Josaphat Tech Solution HR Attendance Manager"
PRODUCT_VERSION = "2.1.0"
COPYRIGHT = "Josaphat Tech Solution"


def main() -> int:
    if not ENTRY_SCRIPT.exists():
        print(f"ERROR: entry script not found: {ENTRY_SCRIPT}", file=sys.stderr)
        return 1
    if not ICON.exists():
        print(f"ERROR: icon not found: {ICON}", file=sys.stderr)
        return 1

    flet_exe = shutil.which("flet")
    if not flet_exe:
        print("ERROR: flet CLI not found on PATH. Install requirements first:", file=sys.stderr)
        print("    pip install -r requirements.txt", file=sys.stderr)
        return 1

    # Data files that must be inside the bundle (read-only, ship with app).
    # Format: "<src>;<dest_in_bundle>" on Windows.
    data_specs = [
        f"{PROJECT_ROOT / 'src' / 'db' / 'schema.sql'};src/db",
        f"{PROJECT_ROOT / 'assets' / 'logo.svg'};assets",
    ]

    cmd = [
        flet_exe,
        "pack",
        str(ENTRY_SCRIPT),
        "--name", OUTPUT_NAME,
        "--icon", str(ICON),
        "--product-name", PRODUCT_NAME,
        "--product-version", PRODUCT_VERSION,
        "--copyright", COPYRIGHT,
        "-y",
    ]
    for spec in data_specs:
        cmd.extend(["--add-data", spec])

    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(f"\nflet pack failed with exit code {result.returncode}", file=sys.stderr)
        return result.returncode

    out = PROJECT_ROOT / "dist" / f"{OUTPUT_NAME}.exe"
    if out.exists():
        size_mb = out.stat().st_size / (1024 * 1024)
        print(f"\nBuild OK: {out}  ({size_mb:.1f} MB)")
        return 0
    print(f"\nBuild reported success but {out} not found.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
