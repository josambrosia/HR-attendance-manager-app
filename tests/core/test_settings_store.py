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

    with open(config_path) as f:
        data = json.load(f)
    assert data["theme"] == "light"

def test_threshold_can_be_set_to_none(tmp_path):
    config_path = tmp_path / "config.json"
    store = SettingsStore(str(config_path))
    store.load()
    store.update({"late_threshold_minutes": None})

    settings = store.load()
    assert settings["late_threshold_minutes"] is None
