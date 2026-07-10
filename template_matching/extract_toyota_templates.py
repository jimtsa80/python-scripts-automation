#!/usr/bin/env python3
"""
Extract Toyota logo templates from frames by finding good matches
in the bottom_right zone and saving them as new template candidates.

Usage:
    python extract_toyota_templates.py F:\path\to\frames --templates-dir ./templates --output-dir ./toyota_candidates --min-confidence 0.55 --top-n 20
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

# Import zone definitions from wrc_template_matcher
SCREEN_ZONES = {
    "bottom_right": {
        "x_start": 0.78,
        "x_end": 0.85,
        "y_start": 0.86,
        "y_end": 0.90,
        "description": "Bottom right corner - Driver info overlay (TVGI-Driver)",
    },
}


def load_toyota_templates(templates_dir: Path) -> List[Tuple[Path, np.ndarray]]:
    """Load all Toyota templates from the templates directory."""
    templates = []
    
    # Look for Toyota templates in various folder structures
    toyota_folders = []
    for folder in templates_dir.rglob("*"):
        if folder.is_dir() and "toyota" in folder.name.lower():
            toyota_folders.append(folder)
    
    # Also check for "Toyota Logos" folder
    brand_folders = [d for d in templates_dir.iterdir() if d.is_dir() and "toyota" in d.name.lower()]
    toyota_folders.extend(brand_folders)
    
    # Load templates from found folders
    for folder in toyota_folders:
        for ext in ["*.png", "*.jpg", "*.jpeg"]:
            for template_path in folder.rglob(ext):
                try:
                    template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
                    if template is not None:
                        templates.append((template_path, template))
                        print(f"✅ Loaded Toyota template: {template_path.name} ({template.shape[1]}x{template.shape[0]})")
                except Exception as e:
                    print(f"⚠️  Failed to load {template_path.name}: {e}")
    
    if not templates:
        print(f"⚠️  No Toyota templates found in {templates_dir}")
        print(f"   Looking for folders containing 'toyota' or 'Toyota Logos'")
    
    return templates


def crop_to_zone(img: np.ndarray, zone_name: str) -> np.ndarray:
    """Crop an image to a predefined screen zone."""
    h, w = img.shape[:2]
    zone = SCREEN_ZONES[zone_name]
    x_start = int(zone["x_start"] * w)
    x_end = int(zone["x_end"] * w)
    y_start = int(zone["y_start"] * h)
    y_end = int(zone["y_end"] * h)
    
    x_start = max(0, min(x_start, w - 1))
    x_end = max(x_start + 1, min(x_end, w))
    y_start = max(0, min(y_start, h - 1))
    y_end = max(y_start + 1, min(y_end, h))
    
    return img[y_start:y_end, x_start:x_end]


def match_template_simple(image: np.ndarray, template: np.ndarray, threshold: float) -> List[Tuple[int, int, int, int, float]]:
    """Simple template matching - find best match above threshold."""
    if template.shape[0] > image.shape[0] or template.shape[1] > image.shape[1]:
        return []
    
    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    
    if max_val >= threshold:
        x1 = max_loc[0]
        y1 = max_loc[1]
        x2 = x1 + template.shape[1]
        y2 = y1 + template.shape[0]
        return [(x1, y1, x2, y2, max_val)]
    
    return []


def extract_toyota_from_frame(
    frame_path: Path,
    toyota_templates: List[Tuple[Path, np.ndarray]],
    min_confidence: float,
    threshold: float = 0.6
) -> List[Tuple[int, int, int, int, float, np.ndarray]]:
    """Extract Toyota logo from a frame if found with good confidence."""
    img = cv2.imread(str(frame_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return []
    
    # Crop to bottom_right zone
    zone_crop = crop_to_zone(img, "bottom_right")
    
    # Try matching with each Toyota template
    best_match = None
    best_conf = 0.0
    
    for template_path, template in toyota_templates:
        # Try a few scales
        for scale in [0.8, 0.9, 1.0, 1.1, 1.2]:
            if scale != 1.0:
                w = int(template.shape[1] * scale)
                h = int(template.shape[0] * scale)
                if w < 10 or h < 10 or w > zone_crop.shape[1] or h > zone_crop.shape[0]:
                    continue
                scaled_template = cv2.resize(template, (w, h), interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR)
            else:
                scaled_template = template
            
            matches = match_template_simple(zone_crop, scaled_template, threshold)
            if matches:
                for x1, y1, x2, y2, conf in matches:
                    if conf > best_conf:
                        best_conf = conf
                        # Convert back to full image coordinates
                        zone = SCREEN_ZONES["bottom_right"]
                        img_h, img_w = img.shape[:2]
                        full_x1 = int(zone["x_start"] * img_w) + x1
                        full_y1 = int(zone["y_start"] * img_h) + y1
                        full_x2 = int(zone["x_start"] * img_w) + x2
                        full_y2 = int(zone["y_start"] * img_h) + y2
                        
                        # Extract the logo region (with some padding)
                        pad = 2
                        crop_x1 = max(0, full_x1 - pad)
                        crop_y1 = max(0, full_y1 - pad)
                        crop_x2 = min(img_w, full_x2 + pad)
                        crop_y2 = min(img_h, full_y2 + pad)
                        
                        logo_crop = img[crop_y1:crop_y2, crop_x1:crop_x2]
                        best_match = (crop_x1, crop_y1, crop_x2, crop_y2, conf, logo_crop)
    
    if best_match and best_conf >= min_confidence:
        return [best_match]
    
    return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract Toyota logo templates from frames by finding good matches."
    )
    parser.add_argument(
        "frames_dir",
        type=Path,
        help="Directory containing frames to search for Toyota logos",
    )
    parser.add_argument(
        "--templates-dir",
        type=Path,
        default=Path("./templates"),
        help="Directory containing existing Toyota templates (default: ./templates)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./toyota_candidates"),
        help="Directory to save extracted template candidates (default: ./toyota_candidates)",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.55,
        help="Minimum confidence to save a template candidate (default: 0.55)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="Template matching threshold for initial detection (default: 0.6)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Save only top N candidates by confidence (default: save all above min-confidence)",
    )
    parser.add_argument(
        "--ext",
        type=str,
        default=".png",
        help="Output file extension (default: .png)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    
    if not args.frames_dir.exists():
        print(f"❌ Frames directory not found: {args.frames_dir}")
        return 1
    
    if not args.templates_dir.exists():
        print(f"❌ Templates directory not found: {args.templates_dir}")
        return 1
    
    # Load Toyota templates
    print(f"🔍 Loading Toyota templates from {args.templates_dir}...")
    toyota_templates = load_toyota_templates(args.templates_dir)
    
    if not toyota_templates:
        print(f"❌ No Toyota templates found. Cannot proceed.")
        return 1
    
    print(f"✅ Loaded {len(toyota_templates)} Toyota template(s)\n")
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all image files
    image_files = []
    for ext in ["*.png", "*.jpg", "*.jpeg"]:
        image_files.extend(args.frames_dir.glob(ext))
        image_files.extend(args.frames_dir.rglob(ext))
    
    image_files = sorted(set(image_files))
    
    if not image_files:
        print(f"❌ No image files found in {args.frames_dir}")
        return 1
    
    print(f"🔍 Processing {len(image_files)} frame(s)...")
    print(f"   Min confidence: {args.min_confidence}")
    print(f"   Matching threshold: {args.threshold}")
    print(f"   Output directory: {args.output_dir}\n")
    
    # Extract candidates
    candidates = []
    
    for i, frame_path in enumerate(image_files, 1):
        matches = extract_toyota_from_frame(
            frame_path,
            toyota_templates,
            args.min_confidence,
            args.threshold
        )
        
        for x1, y1, x2, y2, conf, logo_crop in matches:
            candidates.append((conf, frame_path, logo_crop, x1, y1, x2, y2))
        
        if i % 50 == 0:
            print(f"   Processed {i}/{len(image_files)} frames... (found {len(candidates)} candidates so far)")
    
    # Sort by confidence (highest first)
    candidates.sort(key=lambda x: x[0], reverse=True)
    
    # Keep top N if specified
    if args.top_n:
        candidates = candidates[:args.top_n]
    
    print(f"\n✅ Found {len(candidates)} Toyota template candidate(s) above confidence {args.min_confidence}")
    
    if not candidates:
        print("   No candidates to save.")
        return 0
    
    # Save candidates
    print(f"\n💾 Saving template candidates to {args.output_dir}...")
    
    for idx, (conf, frame_path, logo_crop, x1, y1, x2, y2) in enumerate(candidates, 1):
        # Create filename with confidence and frame name
        frame_stem = frame_path.stem
        filename = f"toyota_candidate_{idx:03d}_conf{conf:.3f}_{frame_stem}{args.ext}"
        output_path = args.output_dir / filename
        
        cv2.imwrite(str(output_path), logo_crop)
        print(f"   [{idx:3d}] Saved: {filename} (conf={conf:.3f}, size={logo_crop.shape[1]}x{logo_crop.shape[0]}, from {frame_path.name})")
    
    print(f"\n✅ Done! Saved {len(candidates)} template candidate(s).")
    print(f"   Review them and add the best ones to your templates/Toyota Logos/bottom_right/TVGI/ folder")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
