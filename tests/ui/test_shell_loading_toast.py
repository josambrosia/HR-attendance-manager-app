"""Tests for Shell wiring of LoadingOverlay + ToastNotifier into pages."""
import pytest
from unittest.mock import MagicMock

from src.core.settings_store import SettingsStore
from src.db.repository import Repository
from src.ui.shell import Shell


@pytest.fixture
def shell(tmp_path):
    settings = SettingsStore(str(tmp_path / "config.json"))
    settings.load()
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    page = MagicMock()
    page.overlay = []
    s = Shell(page, settings, repo, str(snapshot_dir))
    s.build()
    yield s
    repo.close()


def test_shell_creates_loading_and_toast(shell):
    assert shell._loading is not None
    assert shell._toast is not None


def test_show_loading_delegates(shell):
    shell.show_loading("Test op...")
    assert shell._loading.label.value == "Test op..."
    assert shell._loading.strip.visible is True


def test_hide_loading_delegates(shell):
    shell.show_loading("Test")
    shell.hide_loading()
    assert shell._loading.strip.visible is False


def test_notify_default_kind_is_success(shell, monkeypatch):
    captured = []
    monkeypatch.setattr("src.ui.components.toast.threading.Timer",
                        lambda *a, **kw: type("T", (), {"start": lambda s: None,
                                                         "daemon": True})())
    shell.notify("Done", "Yay")
    assert len(shell._toast.stack.controls) == 1


def test_notify_error_kind(shell, monkeypatch):
    monkeypatch.setattr("src.ui.components.toast.threading.Timer",
                        lambda *a, **kw: type("T", (), {"start": lambda s: None,
                                                         "daemon": True})())
    shell.notify("Boom", "broke", kind="error")
    toast = shell._toast.stack.controls[0]
    from src.core.constants import COLORS
    assert toast.border.left.color == COLORS["late_severe"]
