"""
Generate the MesureEscalier iOS app icon.
Style: solid colored background + black diagonal double-arrow (expand icon).
Output: 1024x1024 PNG, opaque (App Store requirement).
"""
from PIL import Image, ImageDraw

SIZE = 1024
GREEN = "#22C55E"   # vibrant green, equivalent brightness to the orange reference
BLACK = "#000000"


def draw_expand_arrow(img: Image.Image) -> None:
    draw = ImageDraw.Draw(img)

    # Geometry, all in pixels in the 1024^2 canvas
    cx = cy = SIZE // 2

    # Diagonal shaft: from (x1, y2) to (x2, y1), bottom-left -> top-right
    margin = 260                 # distance from icon edge to arrow tip
    x1, y1 = margin, margin                     # top-left (used by TR tip)
    x2, y2 = SIZE - margin, SIZE - margin       # bottom-right (used by BL tip)

    # Tip coordinates
    tr = (x2, y1)   # top-right tip
    bl = (x1, y2)   # bottom-left tip

    stroke = 96      # shaft thickness (bold, matches reference)
    wing = 200       # length of each L-shaped wing at the arrow tips

    # --- Main diagonal shaft ---
    draw.line([bl, tr], fill=BLACK, width=stroke)

    # --- Top-right tip: L-shape (horizontal left + vertical down) ---
    # Horizontal segment of the wing (top edge)
    draw.line([(tr[0] - wing, tr[1]), tr], fill=BLACK, width=stroke)
    # Vertical segment of the wing (right edge)
    draw.line([tr, (tr[0], tr[1] + wing)], fill=BLACK, width=stroke)

    # --- Bottom-left tip: L-shape (horizontal right + vertical up) ---
    draw.line([bl, (bl[0] + wing, bl[1])], fill=BLACK, width=stroke)
    draw.line([(bl[0], bl[1] - wing), bl], fill=BLACK, width=stroke)

    # Square caps look slightly cleaner when we patch the inner corners
    # at the L-tips with small filled rectangles (avoids the tiny notch
    # that PIL produces at right angles with thick lines).
    half = stroke // 2
    # Top-right inner corner patch
    draw.rectangle(
        [tr[0] - half, tr[1] - half, tr[0] + half, tr[1] + half],
        fill=BLACK,
    )
    # Bottom-left inner corner patch
    draw.rectangle(
        [bl[0] - half, bl[1] - half, bl[0] + half, bl[1] + half],
        fill=BLACK,
    )


SUPERSAMPLE = 4   # render @ 4096 then downscale for smooth diagonals


def main() -> None:
    # Render at 4x then downscale with LANCZOS -> clean anti-aliased edges
    global SIZE
    target_size = SIZE
    SIZE = target_size * SUPERSAMPLE          # temporarily bump for drawing
    big = Image.new("RGB", (SIZE, SIZE), GREEN)
    draw_expand_arrow(big)
    SIZE = target_size                         # restore for any later use

    img = big.resize((target_size, target_size), Image.LANCZOS)

    out_paths = [
        "/app/mesure-chassis/poc-aruco/icon_green_1024.png",
        "/app/frontend/assets/icon_green_1024.png",
    ]
    for p in out_paths:
        img.save(p, "PNG", optimize=True)
        print(f"Wrote {p}")


if __name__ == "__main__":
    main()
