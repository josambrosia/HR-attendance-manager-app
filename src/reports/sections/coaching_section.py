from reportlab.lib import colors
from reportlab.lib.units import mm
from src.core.constants import COLORS

PINK = colors.HexColor(COLORS["accent"])
RED = colors.HexColor(COLORS["late_severe"])
TEXT = colors.HexColor("#1e1b4b")


def render_coaching(candidates: list[dict]):
    """candidates: [{'name', 'total_late', 'days_late', 'avg_per_day', 'streak'}, ...]"""
    def fn(c, x, y, w):
        c.setFillColor(PINK)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(x, y, "COACHING REQUIRED")
        y -= 7 * mm
        if not candidates:
            c.setFillColor(colors.HexColor("#10B981"))
            c.setFont("Helvetica", 10)
            c.drawString(x, y, "No employees over coaching threshold this period.")
            return y - 6 * mm

        medals = ["#1", "#2", "#3", "#4"]
        for i, cand in enumerate(candidates[:4]):
            row_h = 16 * mm
            c.setStrokeColor(PINK)
            c.setLineWidth(0.6)
            c.roundRect(x, y - row_h, w, row_h, 3, stroke=1, fill=0)
            c.setFillColor(TEXT)
            c.setFont("Helvetica-Bold", 14)
            c.drawString(x + 4 * mm, y - 6 * mm,
                         f"{medals[i] if i < len(medals) else f'#{i+1}'}  {cand['name']}")
            c.setFillColor(RED)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(x + 4 * mm, y - 11 * mm,
                         f"Akumulasi telat: {cand['total_late']} menit")
            c.setFillColor(colors.HexColor("#64748b"))
            c.setFont("Helvetica", 8)
            c.drawString(x + 4 * mm, y - 14.5 * mm,
                         f"Hari telat: {cand['days_late']}  ·  "
                         f"Avg/hari: {cand.get('avg_per_day', 0)} mnt  ·  "
                         f"Streak: {cand.get('streak', 0)} mgg")
            y -= row_h + 3 * mm
        return y
    return fn
