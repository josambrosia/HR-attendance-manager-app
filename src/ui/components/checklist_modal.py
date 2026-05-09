import flet as ft
from src.core.constants import COLORS

GROUPS = [
    ("Vital Metrics", [
        ("vital_pending", "Pending Issues", True),
        ("vital_coaching", "Need Coaching", True),
        ("vital_repeat", "Repeat Offenders", True),
        ("vital_attendance", "Attendance Rate", True),
    ]),
    ("Trivia & Insights", [
        ("trivia_reason", "Most Common Reason", False),
        ("trivia_day", "Hari Paling Telat", False),
        ("trivia_trend", "Late Trend", False),
        ("trivia_best", "Best Performer", False),
    ]),
    ("Sections", [
        ("section_coaching", "Coaching Required (detail cards)", True),
        ("section_hall", "Hall of Late ranking", True),
        ("section_per_employee", "Per-employee breakdown", False),
    ]),
]


def show_checklist_modal(page: ft.Page, title: str, on_generate, include_monthly_extras: bool = False):
    """Open an AlertDialog with grouped checkboxes + format radio.

    on_generate(selected_dict, format_str) is invoked when the user clicks Generate.
    Uses the Flet 0.25 overlay dialog pattern (page.overlay.append) which is the
    pattern established by Task 12 (edit_records.py).
    """
    checkboxes: dict = {}
    sections_ui: list = []

    for group_label, items in GROUPS:
        sections_ui.append(
            ft.Text(group_label.upper(), size=11, weight=ft.FontWeight.W_700,
                    color=COLORS["accent"])
        )
        for key, label, default in items:
            cb = ft.Checkbox(label=label, value=default)
            checkboxes[key] = cb
            sections_ui.append(cb)
        sections_ui.append(ft.Container(height=4))

    if include_monthly_extras:
        sections_ui.append(
            ft.Text("MONTHLY EXTRAS", size=11, weight=ft.FontWeight.W_700,
                    color=COLORS["accent"])
        )
        for key, label, default in [
            ("monthly_excel_sheets_format", "Excel format 1:1 with Google Sheets", True),
            ("monthly_dept_breakdown", "Department breakdown", False),
        ]:
            cb = ft.Checkbox(label=label, value=default)
            checkboxes[key] = cb
            sections_ui.append(cb)
        sections_ui.append(ft.Container(height=4))

    hall_top_n = ft.Dropdown(
        label="Hall of Late: Top",
        value="5",
        options=[
            ft.dropdown.Option("5"),
            ft.dropdown.Option("10"),
            ft.dropdown.Option("All"),
        ],
        width=160,
    )
    sections_ui.append(hall_top_n)

    fmt = ft.RadioGroup(
        value="pdf",
        content=ft.Row(spacing=20, controls=[
            ft.Radio(value="pdf", label="PDF (designed)"),
            ft.Radio(value="excel", label="Excel (raw)"),
        ]),
    )
    sections_ui.append(fmt)

    def _close():
        dialog.open = False
        page.update()

    def on_click_generate(e):
        selected = {k: cb.value for k, cb in checkboxes.items()}
        selected["hall_top_n"] = hall_top_n.value
        _close()
        on_generate(selected, fmt.value)

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(title),
        content=ft.Container(
            width=440, height=480,
            content=ft.Column(scroll=ft.ScrollMode.AUTO, spacing=4, controls=sections_ui),
        ),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: _close()),
            ft.ElevatedButton(
                "Generate Report", on_click=on_click_generate,
                bgcolor=COLORS["primary"], color="white",
            ),
        ],
    )

    # Flet 0.25 overlay pattern (Task 12 established)
    if dialog not in page.overlay:
        page.overlay.append(dialog)
    dialog.open = True
    page.update()
