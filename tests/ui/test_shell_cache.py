"""Tests for Shell's page cache and data-change invalidation.

The Shell now caches built page Controls by route to avoid rebuilding the
widget tree on every navigation (the previous behavior was a full
page.controls.clear() + rebuild on every nav, which was the dominant cause
of 5-10s navigation freezes).
"""
import pytest
from unittest.mock import MagicMock

from src.core.constants import COLORS
from src.core.settings_store import SettingsStore
from src.db.repository import Repository
from src.ui.shell import Shell, _DATA_CONSUMING_ROUTES


@pytest.fixture
def shell(tmp_path, monkeypatch):
    settings = SettingsStore(str(tmp_path / "config.json"))
    settings.load()
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()

    # Run threading.Thread synchronously in tests so the Main DB async-load
    # path completes before assertions. The real app uses a real thread.
    class _SyncThread:
        def __init__(self, target, daemon=False, **_):
            self._target = target
        def start(self):
            self._target()
    monkeypatch.setattr("src.ui.shell.threading.Thread", _SyncThread)

    page = MagicMock()  # Flet page stub — not exercised by cache logic
    s = Shell(page, settings, repo, str(snapshot_dir))
    s.build()  # registers nav buttons + pre-caches default route
    yield s
    repo.close()


def test_initial_build_caches_default_route(shell):
    # Default route is dashboard — should be pre-cached after build()
    assert "dashboard" in shell._page_cache
    assert shell.current_route == "dashboard"


def test_nav_buttons_registered_for_all_routes(shell):
    # All 9 routes from NAV_GROUPS must have a button reference
    expected = {
        "import_data", "issues", "dashboard", "main_database",
        "weekly_report", "monthly_report", "edit_records",
        "backup_restore", "settings",
    }
    assert set(shell._nav_buttons.keys()) == expected


def test_navigate_caches_built_page(shell):
    shell._navigate("issues")
    assert "issues" in shell._page_cache
    cached = shell._page_cache["issues"]

    # Navigate away then back — same instance reused (no rebuild)
    shell._navigate("dashboard")
    shell._navigate("issues")
    assert shell._page_cache["issues"] is cached


def test_same_route_navigate_drops_cache(shell):
    # Same-route nav is a "refresh" signal (e.g. Dashboard period change calls
    # nav_callback("dashboard") to repaint with new start/end). Must rebuild.
    cached = shell._page_cache["dashboard"]
    shell._navigate("dashboard")
    assert shell._page_cache["dashboard"] is not cached


def test_navigate_updates_active_button_state(shell):
    # Initial: dashboard active
    expected_active_bg = f"{COLORS['primary']}33"
    assert shell._nav_buttons["dashboard"].bgcolor == expected_active_bg

    shell._navigate("issues")
    assert shell._nav_buttons["issues"].bgcolor == expected_active_bg
    assert shell._nav_buttons["dashboard"].bgcolor is None


def test_invalidate_data_caches_clears_all_data_routes(shell):
    # Pre-populate caches for several data-consuming routes
    for r in ("issues", "main_database", "edit_records"):
        shell._navigate(r)
    for r in ("dashboard", "issues", "main_database", "edit_records"):
        assert r in shell._page_cache

    shell.invalidate_data_caches()
    for r in _DATA_CONSUMING_ROUTES:
        assert r not in shell._page_cache


def test_invalidate_data_caches_specific_routes(shell):
    shell._navigate("issues")
    assert "dashboard" in shell._page_cache
    assert "issues" in shell._page_cache

    shell.invalidate_data_caches("dashboard")
    assert "dashboard" not in shell._page_cache
    assert "issues" in shell._page_cache


def test_invalidate_does_not_touch_non_data_routes(shell):
    # settings + import_data + backup_restore are NOT data-consuming —
    # they don't display attendance metrics, so invalidate shouldn't drop them
    shell._navigate("settings")
    shell._navigate("import_data")
    shell._navigate("backup_restore")
    assert "settings" in shell._page_cache
    assert "import_data" in shell._page_cache
    assert "backup_restore" in shell._page_cache

    shell.invalidate_data_caches()
    # Non-data routes untouched
    assert "settings" in shell._page_cache
    assert "import_data" in shell._page_cache
    assert "backup_restore" in shell._page_cache


def test_data_consuming_routes_constant_matches_expectation():
    # Catch accidental changes to the invalidation set — these are the
    # routes that display attendance/resolution data and must rebuild
    # when the underlying data changes.
    assert set(_DATA_CONSUMING_ROUTES) == {
        "dashboard", "issues", "main_database",
        "weekly_report", "monthly_report", "edit_records",
    }
