import json
from pathlib import Path
from src.core.constants import DEFAULT_SETTINGS

class SettingsStore:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self._cache = None

    def load(self) -> dict:
        if not self.config_path.exists():
            self._cache = DEFAULT_SETTINGS.copy()
            self._write()
            return self._cache
        with open(self.config_path, "r", encoding="utf-8") as f:
            self._cache = json.load(f)
        # Backfill missing keys with defaults (for forward compat)
        for k, v in DEFAULT_SETTINGS.items():
            self._cache.setdefault(k, v)
        return self._cache

    def update(self, partial: dict):
        if self._cache is None:
            self.load()
        self._cache.update(partial)
        self._write()

    def _write(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default=None):
        if self._cache is None:
            self.load()
        return self._cache.get(key, default)
