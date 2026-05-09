from reportlab.lib import colors
from reportlab.lib.units import mm
from src.core.constants import COLORS

PURPLE = colors.HexColor(COLORS["primary"])
TEXT = colors.HexColor("#1e1b4b")
RED = colors.HexColor(COLORS["late_severe"])


def render_hall_of_late(ranking: list[dict], coaching_threshold: int = 75,
                        repeat_offenders: set | None = None):
    repeat_offenders = repeat_offenders or set()

    def fn(c, x, y, w):
        c.setFillColor(PURPLE)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(x, y, "Hall of Late - Ranking")
        y -= 8 * mm

        if not ranking:
            c.setFont("Helvetica", 10)
            c.setFillColor(colors.HexColor("#64748b"))
            c.drawString(x, y, "No lateness recorded this period.")
            return y - 5 * mm

        # Header row
        c.setFillColor(colors.HexColor("#64748b"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x, y, "RANK")
        c.drawString(x + 18 * mm, y, "EMPLOYEE")
        c.drawString(x + 80 * mm, y, "DAYS LATE")
        c.drawString(x + 110 * mm, y, "MAX (DATE)")
        c.drawString(x + w - 25 * mm, y, "TOTAL MIN")
        y -= 4 * mm
        c.setStrokeColor(colors.HexColor("#cbd5e1"))
        c.line(x, y, x + w, y)
        y -= 4 * mm

        for i, r in enumerate(ranking):
            pos = i + 1
            label = f"#{pos}"
            over = r["total_late"] > coaching_threshold
            c.setFillColor(TEXT)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x, y, label)
            name = r["name"] + ("  *" if r.get("staff_no") in repeat_offenders else "")
            c.drawString(x + 18 * mm, y, name)
            c.setFont("Helvetica", 9)
            c.drawString(x + 80 * mm, y, str(r["days_late"]))
            c.drawString(x + 110 * mm, y, f"{r['max_late']} ({r['max_late_date']})")
            c.setFillColor(RED if over else TEXT)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x + w - 25 * mm, y, f"{r['total_late']} mnt")
            y -= 5 * mm
            if y < 30 * mm:
                break
        return y - 4 * mm
    return fn
