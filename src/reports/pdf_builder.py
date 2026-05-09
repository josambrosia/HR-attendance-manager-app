from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg
from src.core.constants import COLORS

ROOT = Path(__file__).parent.parent.parent
LOGO_PATH = ROOT / "assets" / "logo.svg"

PURPLE = colors.HexColor(COLORS["primary"])
PINK = colors.HexColor(COLORS["accent"])
GREY_TEXT = colors.HexColor("#64748b")


class PdfReportBuilder:
    def __init__(self, title: str, subtitle: str, version: str = "1.0"):
        self.title = title
        self.subtitle = subtitle
        self.version = version
        self.sections: list[tuple[str, callable]] = []

    def add_section(self, name: str, render_fn):
        """render_fn signature: (canvas, x, y, width) -> new_y after drawing."""
        self.sections.append((name, render_fn))

    def save(self, output_path: str):
        c = canvas.Canvas(output_path, pagesize=A4)
        page_w, page_h = A4
        margin = 18 * mm
        usable_w = page_w - 2 * margin

        self._draw_header(c, page_w, page_h, margin)
        y = page_h - 50 * mm

        for section_name, render_fn in self.sections:
            if y < 50 * mm:
                self._draw_footer(c, page_w, page_h, margin)
                c.showPage()
                self._draw_header(c, page_w, page_h, margin)
                y = page_h - 50 * mm
            new_y = render_fn(c, margin, y, usable_w)
            if new_y is None:
                new_y = y
            y = new_y - 8 * mm

        self._draw_footer(c, page_w, page_h, margin)
        c.save()

    def _draw_header(self, c: canvas.Canvas, page_w: float, page_h: float, margin: float):
        c.setFillColor(PURPLE)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(margin, page_h - 22 * mm, self.title)
        c.setFillColor(GREY_TEXT)
        c.setFont("Helvetica", 10)
        c.drawString(margin, page_h - 30 * mm, self.subtitle)
        # accent line
        c.setFillColor(PINK)
        c.rect(margin, page_h - 34 * mm, 30 * mm, 1.2, fill=1, stroke=0)

    def _draw_footer(self, c: canvas.Canvas, page_w: float, page_h: float, margin: float):
        # Powered by line - centered at bottom
        footer_y = 12 * mm
        # logo
        if LOGO_PATH.exists():
            try:
                drawing = svg2rlg(str(LOGO_PATH))
                if drawing:
                    scale = (5 * mm) / drawing.width
                    drawing.width *= scale
                    drawing.height *= scale
                    drawing.scale(scale, scale)
                    renderPDF.draw(drawing, c, page_w / 2 - 30 * mm, footer_y - 1.5 * mm)
            except Exception:
                pass
        c.setFillColor(GREY_TEXT)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(page_w / 2 - 23 * mm, footer_y + 1.5 * mm,
                     "Powered by Josaphat Tech Solution")
        c.setFont("Helvetica", 7)
        c.drawString(page_w / 2 - 23 * mm, footer_y - 1.8 * mm,
                     f"HR Attendance Manager - v{self.version} - "
                     f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}")
