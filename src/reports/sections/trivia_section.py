from reportlab.lib import colors
from reportlab.lib.units import mm
from src.core.constants import COLORS

PURPLE = colors.HexColor(COLORS["primary"])
TEXT = colors.HexColor("#1e1b4b")
GREY = colors.HexColor("#64748b")


def render_trivia(items: list[dict]):
    """items: [{'label': str, 'value': str, 'meta': str}, ...]"""
    def fn(c, x, y, w):
        c.setFillColor(PURPLE)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "Trivia & Insights")
        y -= 7 * mm

        n = len(items)
        if n == 0:
            return y
        col_w = (w - (n - 1) * 2 * mm) / n
        for i, item in enumerate(items):
            cx = x + i * (col_w + 2 * mm)
            c.setStrokeColor(colors.HexColor(COLORS["primary"] + "33"))
            c.setLineWidth(0.4)
            c.roundRect(cx, y - 16 * mm, col_w, 16 * mm, 2, stroke=1, fill=0)
            c.setFillColor(GREY)
            c.setFont("Helvetica-Bold", 7)
            c.drawString(cx + 2 * mm, y - 4 * mm, item["label"].upper())
            c.setFillColor(TEXT)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(cx + 2 * mm, y - 9 * mm, item["value"])
            c.setFillColor(GREY)
            c.setFont("Helvetica", 7)
            c.drawString(cx + 2 * mm, y - 13.5 * mm, item["meta"])
        return y - 18 * mm
    return fn
