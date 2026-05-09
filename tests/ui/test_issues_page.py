"""Tests for IssuesPage list/modal redesign.

Strategy: instantiate IssuesPage with a real in-memory Repository (so SQL
behaviour is exercised) and a MagicMock Flet page (so modal can append to
page.overlay without crashing). Inspect widget property values to verify
expected state.
"""
from unittest.mock import MagicMock

import pytest

from src.core.constants import COLORS
from src.core.settings_store import SettingsStore
from src.db.repository import Repository
from src.ui.pages.issues import IssuesPage


@pytest.fixture
def page_with_data(tmp_path):
    """Build a Repository with 2 pending + 1 resolved issue in the test week."""
    settings = SettingsStore(str(tmp_path / "config.json"))
    settings.load()
    repo = Repository(str(tmp_path / "test.db"))
    repo.init_schema()

    emp = repo.upsert_employee(staff_no="1001", name="ALICE")
    pending_a = repo.insert_attendance({
        "employee_id": emp, "date": "2026-04-01", "day_name": "Rabu",
        "day_type": "Hari Kerja", "issue_case": "A",
    })
    pending_b = repo.insert_attendance({
        "employee_id": emp, "date": "2026-04-02", "day_name": "Kamis",
        "day_type": "Hari Kerja", "issue_case": "A",
    })
    resolved = repo.insert_attendance({
        "employee_id": emp, "date": "2026-04-03", "day_name": "Jumat",
        "day_type": "Hari Kerja", "issue_case": "A",
    })
    repo.upsert_resolution(resolved, reason_code="cuti")

    page = MagicMock()
    page.overlay = []

    issues_page = IssuesPage(page, repo, settings, mode="dark")
    issues_page.start = type(issues_page.start).fromisoformat("2026-03-30")
    issues_page.end = type(issues_page.end).fromisoformat("2026-04-05")
    issues_page.build()
    yield issues_page, repo
    repo.close()


def test_stat_chips_show_correct_counts(page_with_data):
    p, _ = page_with_data
    pending_count = p._stat_pending.content.controls[0].value
    resolved_count = p._stat_resolved.content.controls[0].value
    total_count = p._stat_total.content.controls[0].value
    assert pending_count == "2"
    assert resolved_count == "1"
    assert total_count == "3"


def test_stat_pending_chip_uses_late_severe_color(page_with_data):
    p, _ = page_with_data
    border = p._stat_pending.border
    assert border is not None
    assert border.left.color == COLORS["late_severe"]


def test_stat_resolved_chip_uses_resolved_color(page_with_data):
    p, _ = page_with_data
    border = p._stat_resolved.border
    assert border.left.color == COLORS["resolved"]


def test_list_has_pending_divider_first(page_with_data):
    p, _ = page_with_data
    controls = p.list_view.controls
    pending_div = controls[0]
    label_text = pending_div.controls[0].value
    assert "Belum Ditangani" in label_text


def test_pending_row_has_pending_status_badge(page_with_data):
    p, _ = page_with_data
    row = p.list_view.controls[1]
    children = row.content.controls
    status_badge = children[-1]
    status_text = status_badge.content.controls[-1].value
    assert "Pending" in status_text


def test_resolved_row_shows_alasan(page_with_data):
    p, _ = page_with_data
    controls = p.list_view.controls
    resolved_idx = None
    for i, c in enumerate(controls):
        try:
            if "Sudah Ditangani" in c.controls[0].value:
                resolved_idx = i
                break
        except (AttributeError, IndexError, TypeError):
            continue
    assert resolved_idx is not None
    resolved_row = controls[resolved_idx + 1]
    children = resolved_row.content.controls
    resolution_text = children[2].value
    assert "Cuti" in resolution_text or "✓" in resolution_text


def test_resolved_row_has_resolved_status_badge(page_with_data):
    p, _ = page_with_data
    controls = p.list_view.controls
    resolved_idx = None
    for i, c in enumerate(controls):
        try:
            if "Sudah Ditangani" in c.controls[0].value:
                resolved_idx = i
                break
        except (AttributeError, IndexError, TypeError):
            continue
    resolved_row = controls[resolved_idx + 1]
    status_badge = resolved_row.content.controls[-1]
    status_text = status_badge.content.controls[-1].value
    assert "Resolved" in status_text


def test_subtitle_shows_breakdown(page_with_data):
    p, _ = page_with_data
    assert "3 total" in p.subtitle_text.value
    assert "2 pending" in p.subtitle_text.value
    assert "1 resolved" in p.subtitle_text.value


def test_modal_starts_hidden(page_with_data):
    p, _ = page_with_data
    assert p._modal is not None
    assert p._modal._dialog.visible is False


def test_modal_open_for_pending_issue_sets_state(page_with_data):
    p, _ = page_with_data
    issue = {
        "id": 1, "employee_name": "ALICE", "date": "2026-04-01",
        "day_name": "Rabu", "issue_case": "A", "actual_in": None, "actual_out": None,
        "reason_code": None,
    }
    p._modal.open_for(issue, edit_mode=False)
    assert p._modal._issue == issue
    assert p._modal._edit_mode is False
    assert p._modal._dialog.visible is True
    assert "ALICE" in p._modal._header_meta.value


def test_modal_close_hides_dialog(page_with_data):
    p, _ = page_with_data
    issue = {"id": 1, "employee_name": "X", "date": "2026-04-01",
             "day_name": "Rabu", "issue_case": "A",
             "actual_in": None, "actual_out": None, "reason_code": None}
    p._modal.open_for(issue)
    p._modal.close()
    assert p._modal._dialog.visible is False


def test_modal_body_has_ai_banner_text_after_open(page_with_data):
    p, _ = page_with_data
    issue = {"id": 1, "employee_name": "ALICE", "date": "2026-04-01",
             "day_name": "Rabu", "issue_case": "A",
             "actual_in": None, "actual_out": None, "reason_code": None}
    p._modal.open_for(issue, edit_mode=False)
    # AI banner suggestion text should mention something for case A
    assert p._modal._ai_suggestion_text.value != ""
    # Case A → suggestions include "Tidak Hadir" / "Cuti" / "Izin Sakit"
    assert any(word in p._modal._ai_suggestion_text.value
               for word in ("Tidak Hadir", "Cuti", "Izin Sakit"))


def test_modal_has_11_reason_cards(page_with_data):
    p, _ = page_with_data
    assert len(p._modal._reason_cards) == 11


def test_select_reason_marks_card_selected(page_with_data):
    p, _ = page_with_data
    issue = {"id": 1, "employee_name": "ALICE", "date": "2026-04-01",
             "day_name": "Rabu", "issue_case": "A",
             "actual_in": None, "actual_out": None, "reason_code": None}
    p._modal.open_for(issue, edit_mode=False)
    p._modal._select_reason("cuti")
    assert p._modal._selected_reason == "cuti"
    assert p._modal._reason_cards["cuti"].border.left.color == COLORS["accent"]


def test_select_reason_with_location_shows_extra_input(page_with_data):
    p, _ = page_with_data
    issue = {"id": 1, "employee_name": "ALICE", "date": "2026-04-01",
             "day_name": "Rabu", "issue_case": "A",
             "actual_in": None, "actual_out": None, "reason_code": None}
    p._modal.open_for(issue)
    p._modal._select_reason("tugas_lapangan")
    assert p._modal._extra_input_area.visible is True
    assert "LOKASI" in p._modal._extra_input_label.value


def test_select_reason_without_input_hides_extra_input(page_with_data):
    p, _ = page_with_data
    issue = {"id": 1, "employee_name": "ALICE", "date": "2026-04-01",
             "day_name": "Rabu", "issue_case": "A",
             "actual_in": None, "actual_out": None, "reason_code": None}
    p._modal.open_for(issue)
    p._modal._select_reason("cuti")
    assert p._modal._extra_input_area.visible is False


def test_save_button_disabled_until_input_filled(page_with_data):
    p, _ = page_with_data
    issue = {"id": 1, "employee_name": "ALICE", "date": "2026-04-01",
             "day_name": "Rabu", "issue_case": "A",
             "actual_in": None, "actual_out": None, "reason_code": None}
    p._modal.open_for(issue)
    p._modal._select_reason("tugas_lapangan")
    assert p._modal._save_btn.disabled is True
    p._modal._extra_input_field.value = "Surabaya"
    p._modal._update_save_btn_state()
    assert p._modal._save_btn.disabled is False


def test_save_button_enabled_for_no_input_reason(page_with_data):
    p, _ = page_with_data
    issue = {"id": 1, "employee_name": "ALICE", "date": "2026-04-01",
             "day_name": "Rabu", "issue_case": "A",
             "actual_in": None, "actual_out": None, "reason_code": None}
    p._modal.open_for(issue)
    p._modal._select_reason("cuti")
    assert p._modal._save_btn.disabled is False


def test_live_preview_updates_on_extra_input(page_with_data):
    p, _ = page_with_data
    issue = {"id": 1, "employee_name": "ALICE", "date": "2026-04-01",
             "day_name": "Rabu", "issue_case": "A",
             "actual_in": None, "actual_out": None, "reason_code": None}
    p._modal.open_for(issue)
    p._modal._select_reason("tugas_lapangan")
    p._modal._extra_input_field.value = "Surabaya"
    p._modal._update_live_preview()
    assert "Lapangan ke Surabaya" in p._modal._live_preview_text.value


def test_save_calls_apply_resolution_and_callback(page_with_data):
    p, repo = page_with_data
    # Find an existing pending record
    rows = repo.list_issues_with_resolutions("2026-03-30", "2026-04-05")
    pending = next(r for r in rows if r["reason_code"] is None)

    callback_fired = []
    p._modal.on_resolved = lambda: callback_fired.append(True)

    p._modal.open_for(pending, edit_mode=False)
    p._modal._select_reason("cuti")
    p._modal._save()

    # Resolution row was created in DB
    after = repo.get_resolution(pending["id"])
    assert after is not None
    assert after["reason_code"] == "cuti"
    # on_resolved callback fired
    assert callback_fired == [True]
    # Modal closed
    assert p._modal._dialog.visible is False


def test_edit_mode_prefills_reason_and_extra(page_with_data):
    p, repo = page_with_data
    rows = repo.list_issues_with_resolutions("2026-03-30", "2026-04-05")
    resolved = next(r for r in rows if r["reason_code"] is not None)
    # Update with location to test pre-fill
    repo.upsert_resolution(resolved["id"], reason_code="tugas_lapangan",
                           location="Surabaya")
    refreshed = repo.list_issues_with_resolutions("2026-03-30", "2026-04-05")
    issue = next(r for r in refreshed if r["id"] == resolved["id"])

    p._modal.open_for(issue, edit_mode=True)
    assert p._modal._selected_reason == "tugas_lapangan"
    assert p._modal._extra_input_field.value == "Surabaya"
    assert p._modal._extra_input_area.visible is True
    assert p._modal._delete_btn.visible is True
    assert p._modal._save_btn.text == "Update Resolution"


def test_delete_calls_delete_resolution_and_callback(page_with_data):
    p, repo = page_with_data
    rows = repo.list_issues_with_resolutions("2026-03-30", "2026-04-05")
    resolved = next(r for r in rows if r["reason_code"] is not None)

    deleted_callback = []
    p._modal.on_deleted = lambda: deleted_callback.append(True)

    # Bypass confirmation by directly calling the delete worker
    p._modal.open_for(resolved, edit_mode=True)
    p._modal._do_delete()  # internal method, skips dialog

    assert repo.get_resolution(resolved["id"]) is None
    assert deleted_callback == [True]
