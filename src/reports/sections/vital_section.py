from reportlab.lib import colors
from reportlab.lib.units import mm
from src.core.constants import COLORS

PURPLE = colors.HexColor(COLORS["primary"])
PINK = colors.HexColor(COLORS["accent"])
TEXT = colors.HexColor("#1e1b4b")


def render_vital(metrics: dict):
    """Returns a render_fn for use with PdfReportBuilder.add_section."""
    def fn(c, x, y, w):
        c.setFillColor(PURPLE)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(x, y, "Vital Metrics")
        y -= 8 * mm

        cards = [
            ("Pending Issues", str(metrics["pending_issues"]),
             f"{metrics['resolved_issues']} of {metrics['total_issues']} resolved"),
            ("Need Coaching", str(metrics.get("need_coaching", 0)),
             f"Threshold >{metrics.get('coaching_threshold', 75)} min"),
            ("Repeat Offenders", str(metrics.get("repeat_offenders", 0)),
             "Late 3+ weeks in a row"),
            ("Attendance Rate", f"{metrics['attendance_rate']}%",
             metrics.get("trend_text", "")),
        ]
        col_w = (w - 6 * mm) / 4
        for i, (label, value, meta) in enumerate(cards):
            cx = x + i * (col_w + 2 * mm)
            c.setStrokeColor(PINK)
            c.setLineWidth(0.5)
            c.roundRect(cx, y - 22 * mm, col_w, 22 * mm, 3, stroke=1, fill=0)
            c.setFillColor(PINK)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(cx + 3 * mm, y - 5 * mm, label.upper())
            c.setFillColor(TEXT)
            c.setFont("Helvetica-Bold", 18)
            c.drawString(cx + 3 * mm, y - 13 * mm, value)
            c.setFillColor(colors.HexColor("#64748b"))
            c.setFont("Helvetica", 7)
            c.drawString(cx + 3 * mm, y - 19 * mm, meta)
        return y - 24 * mm
    return fn
