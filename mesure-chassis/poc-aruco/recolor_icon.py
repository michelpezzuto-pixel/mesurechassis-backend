"""
Swap the orange (#FF5500) background of the user's reference icon
with green (#22C55E) — without touching the black arrow.

Output: 1024x1024 PNG ready for the Emergent iOS build form.
"""
from PIL import Image
import numpy as np

SRC = "/tmp/orig_orange.png"
DST_PRIMARY = "/app/mesure-chassis/poc-aruco/icon_green_1024.png"
DST_COPY = "/app/frontend/assets/icon_green_1024.png"

GREEN = (34, 197, 94)  # #22C55E


def main() -> None:
    img = Image.open(SRC).convert("RGB")
    arr = np.array(img)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    # Identify orange pixels (anything that's "warm orange-ish")
    orange = (r > 200) & (g > 30) & (g < 180) & (b < 80)
    arr[orange] = GREEN

    # Crop tight around the icon (non-black region) to maximise resolution
    non_black = (r > 30) | (g > 30) | (b > 30)
    ys, xs = np.where(non_black)
    y0, y1 = ys.min(), ys.max()
    x0, x1 = xs.min(), xs.max()

    # Square crop centered on the icon, with a tiny black margin (matches
    # the look of the original screenshot the user provided).
    cy = (y0 + y1) // 2
    cx = (x0 + x1) // 2
    side = int(max(y1 - y0, x1 - x0) * 1.04)  # ~4% padding
    h, w = arr.shape[:2]
    cx0 = max(0, cx - side // 2)
    cy0 = max(0, cy - side // 2)
    cx1 = min(w, cx0 + side)
    cy1 = min(h, cy0 + side)
    # re-snap if we hit a border
    cx0 = max(0, cx1 - side)
    cy0 = max(0, cy1 - side)

    cropped = Image.fromarray(arr).crop((cx0, cy0, cx1, cy1))
    icon = cropped.resize((1024, 1024), Image.LANCZOS)

    for p in (DST_PRIMARY, DST_COPY):
        icon.save(p, "PNG", optimize=True)
        print(f"Wrote {p}")

    # Quick verification
    out = Image.open(DST_PRIMARY)
    print(f"Final size: {out.size}, mode: {out.mode}")
    print(f"  center px (512,512) = {out.getpixel((512, 512))}")
    print(f"  corner px (50,50)   = {out.getpixel((50, 50))}")
    print(f"  bg sample (300,300) = {out.getpixel((300, 300))}")


if __name__ == "__main__":
    main()
