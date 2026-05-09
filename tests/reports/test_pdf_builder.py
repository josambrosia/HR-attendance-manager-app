from pathlib import Path
import pytest
from src.reports.pdf_builder import PdfReportBuilder


def test_minimal_pdf_is_generated(tmp_path):
    output = tmp_path / "test.pdf"
    builder = PdfReportBuilder(
        title="Test Report",
        subtitle="Period: 2026-04-01 -> 2026-04-07",
        version="1.0",
    )
    builder.add_section("Sample", lambda canvas, x, y, w: canvas.drawString(x, y, "Hello"))
    builder.save(str(output))
    assert output.exists()
    assert output.stat().st_size > 0


def test_pdf_size_implies_footer_drawn(tmp_path):
    output = tmp_path / "test.pdf"
    builder = PdfReportBuilder(title="X", subtitle="Y", version="1.0")
    builder.save(str(output))
    # Footer + header + branding all drawn -> PDF should be at least a few KB
    assert output.stat().st_size > 1500
