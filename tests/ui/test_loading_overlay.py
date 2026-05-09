"""Tests for the LoadingOverlay component (top progress strip + dim).

We mock the Flet page so tests run without a Flet runtime; the overlay's
behavior is observable through the property values it sets on its widgets.
"""
from unittest.mock import MagicMock
from src.ui.components.loading_overlay import LoadingOverlay


def _make_overlay():
    page = MagicMock()
    page.overlay = []
    return LoadingOverlay(page), page


def test_init_appends_two_overlay_items_hidden():
    overlay, page = _make_overlay()
    # The dim layer + the strip — two separate page.overlay entries
    assert len(page.overlay) == 2
    assert overlay.dim.visible is False
    assert overlay.strip.visible is False


def test_show_sets_visible_and_label():
    overlay, _ = _make_overlay()
    overlay.show("Sedang import...")
    assert overlay.dim.visible is True
    assert overlay.strip.visible is True
    assert overlay.label.value == "Sedang import..."


def test_hide_restores_invisible():
    overlay, _ = _make_overlay()
    overlay.show("Anything")
    overlay.hide()
    assert overlay.dim.visible is False
    assert overlay.strip.visible is False


def test_repeat_show_updates_label():
    overlay, _ = _make_overlay()
    overlay.show("First op")
    overlay.show("Second op")
    assert overlay.label.value == "Second op"
    assert overlay.strip.visible is True


def test_dim_layer_absorbs_clicks():
    overlay, _ = _make_overlay()
    # The dim Container must have an on_click handler so Flet absorbs the
    # pointer event instead of letting it pass through to the sidebar.
    assert overlay.dim.on_click is not None
