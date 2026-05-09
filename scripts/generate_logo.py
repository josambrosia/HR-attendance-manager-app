"""Generate icon.ico (multi-resolution) and logo-256.png from logo.svg.

We render the logo natively with Pillow rather than rasterising the SVG —
svglib/reportlab does not handle linearGradient fills, and cairosvg requires
the native Cairo DLLs (not bundled with the Python wheel on Windows).

The geometry mirrors assets/logo.svg (a 256x280 viewBox with a regular hexagon
and a centred "J" glyph). Keep them in sync if the SVG changes.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).parent.parent
SVG_PATH = ROOT / "assets" / "logo.svg"
ICO_PATH = ROOT / "assets" / "icon.ico"
PNG_PATH = ROOT / "assets" / "logo-256.png"

ICO_SIZES = [16, 32, 48, 64, 128, 256]

# Logical viewBox dimensions matching assets/logo.svg
VB_W, VB_H = 256, 280
HEX_POINTS = [(128, 8), (248, 72), (248, 208), (128, 272), (8, 208), (8, 72)]
TEXT_BASELINE_Y = 190  # Matches the SVG <text y="190">
GRAD_START = (124, 58, 237)   # #7C3AED
GRAD_END = (244, 114, 182)    # #F472B6
SHADOW_COLOR = (124, 58, 237) # purple shadow tint
SHADOW_ALPHA = 100            # ~0.4 opacity


def _gradient_fill(width: int, height: int, start: tuple, end: tuple) -> Image.Image:
    """Diagonal linear gradient (top-left -> bottom-right) as RGBA image."""
    grad = Image.new("RGBA", (width, height), 0)
    px = grad.load()
    sr, sg, sb = start
    er, eg, eb = end
    # Diagonal interpolation: t = (x + y) / (width + height - 2)
    denom = max(1, (width - 1) + (height - 1))
    for y in range(height):
        for x in range(width):
            t = (x + y) / denom
            r = int(sr + (er - sr) * t)
            g = int(sg + (eg - sg) * t)
            b = int(sb + (eb - sb) * t)
            px[x, y] = (r, g, b, 255)
    return grad


def _load_font(font_size: int) -> ImageFont.FreeTypeFont:
    """Try Inter -> Helvetica -> Arial -> default. Pillow font fallback chain."""
    candidates = [
        "Inter-Black.ttf", "Inter-Bold.ttf", "Inter.ttf",
        "Helvetica-Bold.ttf", "Helvetica.ttf",
        "arialbd.ttf", "arial.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, font_size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def render_logo(size: int) -> Image.Image:
    """Render the Hex-J logo at the requested square size (RGBA)."""
    # Render at 4x then downscale for crisp anti-aliased edges.
    ss = 4
    big = size * ss
    scale_x = big / VB_W
    scale_y = big / VB_H

    # Use the larger viewBox dimension to keep aspect — square output canvas.
    canvas = Image.new("RGBA", (big, big), (0, 0, 0, 0))

    # Centre the logical 256x280 viewBox inside the square canvas.
    offset_x = (big - int(VB_W * scale_x)) // 2
    offset_y = (big - int(VB_H * scale_y)) // 2
    # When canvas is square and we use min scale, both offsets are 0 if 256/280
    # ratio < 1; pick uniform scale.
    uniform = min(big / VB_W, big / VB_H)
    offset_x = (big - int(VB_W * uniform)) // 2
    offset_y = (big - int(VB_H * uniform)) // 2

    poly = [
        (offset_x + int(x * uniform), offset_y + int(y * uniform))
        for (x, y) in HEX_POINTS
    ]

    # Drop shadow: draw mask, blur, composite tinted shadow first.
    shadow_layer = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow_layer)
    shadow_offset = max(2, int(4 * uniform))
    blur_radius = max(2, int(6 * uniform))
    shadow_poly = [(x, y + shadow_offset) for (x, y) in poly]
    sdraw.polygon(shadow_poly, fill=(*SHADOW_COLOR, SHADOW_ALPHA))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(blur_radius))
    canvas = Image.alpha_composite(canvas, shadow_layer)

    # Hexagon mask (white inside, transparent outside)
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).polygon(poly, fill=255)

    # Gradient fill clipped to hex
    gradient = _gradient_fill(big, big, GRAD_START, GRAD_END)
    hex_layer = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    hex_layer.paste(gradient, (0, 0), mask)
    canvas = Image.alpha_composite(canvas, hex_layer)

    # "J" glyph centred on hexagon (only at sizes large enough to read)
    if size >= 32:
        font_px = int(160 * uniform)
        font = _load_font(font_px)
        text_layer = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        tdraw = ImageDraw.Draw(text_layer)
        # anchor="ms" -> middle horizontally, baseline (matches SVG text-anchor)
        cx = offset_x + int(128 * uniform)
        by = offset_y + int(TEXT_BASELINE_Y * uniform)
        try:
            tdraw.text((cx, by), "J", fill=(255, 255, 255, 255),
                       font=font, anchor="ms")
        except (TypeError, ValueError):
            # Default font may not support anchor — fall back to xy approx.
            bbox = tdraw.textbbox((0, 0), "J", font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            tdraw.text((cx - tw // 2, by - th), "J",
                       fill=(255, 255, 255, 255), font=font)
        canvas = Image.alpha_composite(canvas, text_layer)

    # Downscale with high-quality resampling
    return canvas.resize((size, size), Image.LANCZOS)


def main():
    print(f"Reading {SVG_PATH}")  # SVG is the design source of truth
    if not SVG_PATH.exists():
        raise RuntimeError(f"SVG missing: {SVG_PATH}")

    # Generate the 256px PNG (used for splash screen + app icon)
    png_img = render_logo(256)
    png_img.save(PNG_PATH, format="PNG")
    print(f"Wrote {PNG_PATH}")

    # Generate one image per ICO size, combine into single multi-res .ico.
    # Pillow's ICO writer maps each entry in `sizes` to whichever source image
    # (base or appended) is closest to that size, so we must save the LARGEST
    # image as the base and append the rest in descending order.
    sizes_desc = sorted(ICO_SIZES, reverse=True)
    images = [render_logo(s) for s in sizes_desc]
    images[0].save(
        ICO_PATH,
        format="ICO",
        sizes=[(s, s) for s in sizes_desc],
        append_images=images[1:],
    )
    print(f"Wrote {ICO_PATH} ({len(ICO_SIZES)} resolutions)")


if __name__ == "__main__":
    main()
