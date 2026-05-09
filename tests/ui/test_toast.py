"""Tests for the ToastNotifier component (top-right stacked toasts).

threading.Timer is monkey-patched per-test so dismiss timers don't sleep
during the test run; the test invokes the captured timer function directly
to simulate timer firing.
"""
from unittest.mock import MagicMock

import pytest

from src.core.constants import COLORS
from src.ui.components.toast import ToastNotifier


@pytest.fixture
def captured_timers(monkeypatch):
    """Capture every threading.Timer; tests can fire them on demand."""
    fired = []
    class FakeTimer:
        def __init__(self, interval, fn):
            self.interval = interval
            self.fn = fn
        def start(self):
            fired.append(self)
        @property
        def daemon(self):
            return True
        @daemon.setter
        def daemon(self, _v):
            pass
    monkeypatch.setattr("src.ui.components.toast.threading.Timer", FakeTimer)
    return fired


@pytest.fixture
def notifier():
    page = MagicMock()
    page.overlay = []
    return ToastNotifier(page)


def test_init_mounts_one_container_in_overlay(notifier):
    assert notifier.container in notifier.page.overlay
    assert notifier.container.top == 20
    assert notifier.container.right == 20
    assert notifier.container.width == 360


def test_success_appends_toast_with_green_border(notifier, captured_timers):
    notifier.success("Done", "All good")
    assert len(notifier.stack.controls) == 1
    toast = notifier.stack.controls[0]
    assert toast.border.left.color == COLORS["resolved"]


def test_error_appends_toast_with_red_border(notifier, captured_timers):
    notifier.error("Boom", "It broke")
    toast = notifier.stack.controls[0]
    assert toast.border.left.color == COLORS["late_severe"]


def test_success_dismisses_after_1500ms(notifier, captured_timers):
    notifier.success("Done")
    assert captured_timers[0].interval == 1.5


def test_error_dismisses_after_3000ms(notifier, captured_timers):
    notifier.error("Boom")
    assert captured_timers[0].interval == 3.0


def test_dismiss_removes_toast_from_stack(notifier, captured_timers):
    notifier.success("Done")
    assert len(notifier.stack.controls) == 1
    captured_timers[0].fn()  # fire the dismiss timer
    assert len(notifier.stack.controls) == 0


def test_max_3_toasts_evicts_oldest(notifier, captured_timers):
    notifier.success("First")
    notifier.success("Second")
    notifier.success("Third")
    notifier.success("Fourth")  # should evict First
    assert len(notifier.stack.controls) == 3
    # Surviving toasts: Second, Third, Fourth
    titles = [_first_text(c) for c in notifier.stack.controls]
    assert titles == ["Second", "Third", "Fourth"]


def test_toast_without_desc_omits_second_text_line(notifier, captured_timers):
    notifier.success("OnlyTitle")  # no desc
    toast = notifier.stack.controls[0]
    column = toast.content.controls[1]  # Row -> [Icon, Column]
    assert len(column.controls) == 1  # title only, no desc line


def _first_text(toast_container):
    """Helper: extract the title text from a built toast Container."""
    column = toast_container.content.controls[1]  # Row -> [Icon, Column]
    return column.controls[0].value
