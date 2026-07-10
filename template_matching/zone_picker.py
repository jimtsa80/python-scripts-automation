#!/usr/bin/env python3
"""
Simple tool to pick screen zones by clicking on an image.

Usage:
    python zone_picker.py path/to/image.jpg

Instructions:
    - A window will open with the image.
    - Left-click once to set the first corner of the rectangle.
    - Left-click a second time to set the opposite corner.
    - Press 'r' to reset the selection and start again.
    - Press 'q' or ESC to quit.

After you click two points, the script prints:
    - Pixel coordinates (x1, y1, x2, y2)
    - Normalized coordinates (x_start, x_end, y_start, y_end) in [0,1]
    - A ready-to-paste SCREEN_ZONES snippet for template_matcher.
"""

import sys
from pathlib import Path
from typing import List, Tuple

import cv2


def pick_zone(image_path: Path) -> None:
    if not image_path.exists():
        print(f"❌ Image not found: {image_path}")
        return

    image = cv2.imread(str(image_path))
    if image is None:
        print(f"❌ Failed to load image: {image_path}")
        return

    clone = image.copy()
    h, w = image.shape[:2]

    points: List[Tuple[int, int]] = []
    window_name = "zone_picker - click two corners, 'r' reset, 'q' quit"

    def mouse_callback(event, x, y, flags, param):
        nonlocal image, points
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(points) == 0:
                points = [(x, y)]
            elif len(points) == 1:
                points.append((x, y))
            else:
                # Start over on third click
                points = [(x, y)]
            # Redraw
            image = clone.copy()
            for px, py in points:
                cv2.circle(image, (px, py), 4, (0, 0, 255), -1)
            if len(points) == 2:
                (x1, y1), (x2, y2) = points
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 2)

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window_name, mouse_callback)

    print(f"📷 Image: {image_path} ({w}x{h})")
    print("🖱️  Left-click two corners of the desired zone.")
    print("   Press 'r' to reset selection, 'q' or ESC to quit.\n")

    while True:
        cv2.imshow(window_name, image)
        key = cv2.waitKey(20) & 0xFF

        if key in (27, ord("q")):  # ESC or 'q'
            break
        if key == ord("r"):
            points = []
            image = clone.copy()
            continue

        if len(points) == 2:
            (x1, y1), (x2, y2) = points
            x_min, x_max = sorted([x1, x2])
            y_min, y_max = sorted([y1, y2])

            x_start = x_min / w
            x_end = x_max / w
            y_start = y_min / h
            y_end = y_max / h

            print("\n📌 Selected zone (pixels):")
            print(f"   x1={x_min}, y1={y_min}, x2={x_max}, y2={y_max}")
            print("📐 Normalized (0–1):")
            print(f"   x_start = {x_start:.4f}")
            print(f"   x_end   = {x_end:.4f}")
            print(f"   y_start = {y_start:.4f}")
            print(f"   y_end   = {y_end:.4f}")

            print("\n🔁 SCREEN_ZONES snippet (example name: 'bottom_right_custom'):\n")
            print("    \"bottom_right_custom\": {")
            print(f"        \"x_start\": {x_start:.4f},")
            print(f"        \"x_end\": {x_end:.4f},")
            print(f"        \"y_start\": {y_start:.4f},")
            print(f"        \"y_end\": {y_end:.4f},")
            print("        \"description\": \"Custom picked zone\"")
            print("    },\n")

            # Wait for next action (r to redo, q to quit)
            points = []

    cv2.destroyAllWindows()


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python zone_picker.py path/to/image.jpg")
        return 1
    image_path = Path(argv[1])
    pick_zone(image_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

