import json
from src.core.settings_store import SettingsStore
from src.core.constants import DEFAULT_SETTINGS

def test_load_creates_defaults_if_missing(tmp_path):
    config_path = tmp_path / "config.json"
    store = SettingsStore(str(config_path))
    settings = store.load()
    assert settings == DEFAULT_SETTINGS
    assert config_path.exists()

def test_load_returns_existing_config(tmp_path):
    config_path = tmp_path / "config.json"
    custom = DEFAULT_SETTINGS.copy()
    custom["coaching_threshold_minutes"] = 100
    config_path.write_text(json.dumps(custom))

    store = SettingsStore(str(config_path))
    settings = store.load()
    assert settings["coaching_threshold_minutes"] == 100

def test_save_writes_to_disk(tmp_path):
    config_path = tmp_path / "config.json"
    store = SettingsStore(str(config_path))
    store.load()
    store.update({"theme": "light"})

    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["theme"] == "light"

def test_threshold_can_be_set_to_none(tmp_path):
    config_path = tmp_path / "config.json"
    store = SettingsStore(str(config_path))
    store.load()
    store.update({"late_threshold_minutes": None})

    settings = store.load()
    assert settings["late_threshold_minutes"] is None

def test_load_backfills_missing_keys(tmp_path):
    config_path = tmp_path / "config.json"
    # Simulate older config from a previous version that had only 'theme'
    config_path.write_text(json.dumps({"theme": "light"}), encoding="utf-8")

    store = SettingsStore(str(config_path))
    settings = store.load()

    # User's existing value preserved
    assert settings["theme"] == "light"
    # Missing keys filled with defaults
    assert settings["coaching_threshold_minutes"] == 75
    assert settings["workdays"] == ["Mon", "Tue", "Wed", "Thu", "Fri"]

    # And the on-disk file now contains the backfilled keys
    with open(config_path, encoding="utf-8") as f:
        on_disk = json.load(f)
    assert on_disk["coaching_threshold_minutes"] == 75
    assert on_disk["theme"] == "light"

def test_update_persists_across_instances(tmp_path):
    config_path = tmp_path / "config.json"

    store1 = SettingsStore(str(config_path))
    store1.update({"coaching_threshold_minutes": 90, "theme": "light"})

    # Fresh instance, no in-memory cache from store1
    store2 = SettingsStore(str(config_path))
    settings = store2.load()
    assert settings["coaching_threshold_minutes"] == 90
    assert settings["theme"] == "light"
