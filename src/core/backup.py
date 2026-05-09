"""Backup / Restore helpers.

Bundles the SQLite database, settings file and recent import snapshots into
a single ZIP archive so HR can move data to a new laptop. Restore safely
copies any pre-existing target files into a pre_restore directory before
overwriting, so a bad import can be rolled back manually.
"""

import shutil
import zipfile
from datetime import datetime
from pathlib import Path

# Maximum number of recent snapshot_*.json files to bundle in an export.
MAX_SNAPSHOTS = 10


def _collect_recent_snapshots(backup_dir: Path) -> list[Path]:
    """Return the most-recent MAX_SNAPSHOTS snapshot_*.json files (newest first)."""
    if not backup_dir.exists():
        return []
    snapshots = sorted(
        backup_dir.glob("snapshot_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return snapshots[:MAX_SNAPSHOTS]


def export_backup(
    db_path: str,
    config_path: str,
    backup_dir: str,
    output_path: str | None = None,
) -> str:
    """Bundle db + config + last 10 snapshots into a ZIP.

    Missing source files are skipped silently so an export still produces a
    valid (possibly partial) archive on a fresh install. Returns the absolute
    path to the written archive.
    """
    db_p = Path(db_path)
    config_p = Path(config_path)
    backup_p = Path(backup_dir)

    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_p.mkdir(parents=True, exist_ok=True)
        output = backup_p / f"hr_backup_{timestamp}.zip"
    else:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        if db_p.exists():
            zf.write(db_p, arcname="app.db")
        if config_p.exists():
            zf.write(config_p, arcname="config.json")
        for snap in _collect_recent_snapshots(backup_p):
            zf.write(snap, arcname=f"snapshots/{snap.name}")

    return str(output.resolve())


def _safe_copy_aside(source: Path, pre_restore_dir: Path, label: str) -> Path | None:
    """Copy source into pre_restore_dir with a timestamp suffix. Returns dest or None."""
    if not source.exists():
        return None
    pre_restore_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = pre_restore_dir / f"{label}.{timestamp}"
    shutil.copy2(source, dest)
    return dest


def import_backup(
    zip_path: str,
    target_db_path: str,
    target_config_path: str,
    pre_restore_dir: str,
) -> dict:
    """Restore a backup ZIP, moving any existing target files aside first.

    Returns a summary dict describing what was restored. Existing files at
    target_db_path / target_config_path are copied into pre_restore_dir with
    a timestamp suffix before being overwritten.
    """
    zip_p = Path(zip_path)
    target_db = Path(target_db_path)
    target_config = Path(target_config_path)
    pre_restore = Path(pre_restore_dir)

    summary = {
        "db_restored": False,
        "config_restored": False,
        "snapshots_restored": 0,
        "pre_restore_dir": str(pre_restore),
    }

    if not zip_p.exists():
        raise FileNotFoundError(f"Backup ZIP not found: {zip_p}")

    # Safety: copy any existing files aside before overwrite.
    _safe_copy_aside(target_db, pre_restore, "app.db")
    _safe_copy_aside(target_config, pre_restore, "config.json")

    target_db.parent.mkdir(parents=True, exist_ok=True)
    target_config.parent.mkdir(parents=True, exist_ok=True)
    snapshot_dest_dir = target_db.parent.parent / "backups"

    with zipfile.ZipFile(zip_p, "r") as zf:
        names = zf.namelist()
        if "app.db" in names:
            with zf.open("app.db") as src, open(target_db, "wb") as dst:
                shutil.copyfileobj(src, dst)
            summary["db_restored"] = True
        if "config.json" in names:
            with zf.open("config.json") as src, open(target_config, "wb") as dst:
                shutil.copyfileobj(src, dst)
            summary["config_restored"] = True

        snapshot_names = [n for n in names if n.startswith("snapshots/snapshot_")]
        if snapshot_names:
            snapshot_dest_dir.mkdir(parents=True, exist_ok=True)
            for name in snapshot_names:
                target = snapshot_dest_dir / Path(name).name
                with zf.open(name) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                summary["snapshots_restored"] += 1

    return summary
