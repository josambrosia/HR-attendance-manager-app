import json
import zipfile
from pathlib import Path

from src.core.backup import export_backup, import_backup


def _make_source_tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create db, config, and a backup_dir with a few snapshot files."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "app.db"
    db_path.write_bytes(b"SQLITE-FAKE-BYTES-v1")

    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"theme": "dark", "marker": 42}), encoding="utf-8")

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    # Twelve snapshot files; export should keep the most recent 10.
    for i in range(12):
        (backup_dir / f"snapshot_{i:02d}.json").write_text(
            json.dumps({"records": [], "n": i}), encoding="utf-8"
        )

    return db_path, config_path, backup_dir


def test_export_creates_zip(tmp_path):
    db_path, config_path, backup_dir = _make_source_tree(tmp_path)
    output_path = tmp_path / "out" / "backup.zip"

    result = export_backup(str(db_path), str(config_path), str(backup_dir), str(output_path))

    assert Path(result).exists()
    assert Path(result) == output_path
    with zipfile.ZipFile(result, "r") as zf:
        names = set(zf.namelist())
        assert "app.db" in names
        assert "config.json" in names
        snap_names = [n for n in names if n.startswith("snapshots/snapshot_")]
        # Should bundle at most the 10 most recent snapshot files.
        assert len(snap_names) == 10
        # Config round-trips intact.
        with zf.open("config.json") as f:
            assert json.loads(f.read().decode("utf-8"))["marker"] == 42


def test_import_restores_data(tmp_path):
    # First, build a real backup ZIP via export.
    db_path, config_path, backup_dir = _make_source_tree(tmp_path)
    zip_path = tmp_path / "backup.zip"
    export_backup(str(db_path), str(config_path), str(backup_dir), str(zip_path))

    # Now set up a "new laptop": existing db + config with different content.
    target_root = tmp_path / "new_laptop"
    target_root.mkdir()
    target_db = target_root / "data" / "app.db"
    target_db.parent.mkdir()
    target_db.write_bytes(b"OLD-DB")

    target_config = target_root / "config.json"
    target_config.write_text(json.dumps({"theme": "light", "marker": 1}), encoding="utf-8")

    pre_restore = target_root / "backups" / "pre-restore"

    summary = import_backup(str(zip_path), str(target_db), str(target_config), str(pre_restore))

    # Restored content matches the source backup.
    assert target_db.read_bytes() == b"SQLITE-FAKE-BYTES-v1"
    assert json.loads(target_config.read_text(encoding="utf-8"))["marker"] == 42

    # Pre-restore safety copies exist for the previously present files.
    assert pre_restore.exists()
    saved_files = list(pre_restore.iterdir())
    saved_names = {p.name for p in saved_files}
    assert any(name.startswith("app.db") for name in saved_names)
    assert any(name.startswith("config.json") for name in saved_names)

    # Summary reports what was restored.
    assert summary["db_restored"] is True
    assert summary["config_restored"] is True
    assert summary["snapshots_restored"] >= 1
