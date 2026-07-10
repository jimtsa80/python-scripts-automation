#!/usr/bin/env python3
"""
ERC Template Matcher - Specialized template matching for ERC logo detection

Focuses on broadcast overlay regions where ERC logos appear.
Uses multi-scale template matching for better accuracy.

Usage:
    python erc_template_matcher.py <image_folder>
    python erc_template_matcher.py <image_folder> --threshold 0.6
    python erc_template_matcher.py <image_folder> --region-only
"""

import argparse
import sys
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import time

# Default template matching threshold
# Increased to reduce false positives
DEFAULT_THRESHOLD = 0.70
# bottom_left ERC strip on temporal_median batches (--ERConly)
DEFAULT_THRESHOLD_ERC_ONLY = 0.55

# Minimum confidence for detections (stricter filtering)
DEFAULT_MIN_CONFIDENCE = 0.60

# Non-Maximum Suppression (NMS) IoU threshold
# Higher = more aggressive overlap removal (0.4 = remove if 40% overlap)
# Increased to 0.4 for better leaderboard logo detection (allows multiple instances in different rows)
DEFAULT_NMS_IOU_THRESHOLD = 0.4

# Minimum detection size (in pixels) - ERC uses stricter defaults than WRC
DEFAULT_MIN_DETECTION_SIZE = 14

# Zone-specific minimum detection sizes (in pixels)
# These override DEFAULT_MIN_DETECTION_SIZE for specific zones
# Calculated from actual detection: width=27.76px, height=14.45px -> min=14.45px
# Using 12px to allow slightly smaller detections for safety margin
# Standard TVGI zones share one minimum; bottom_left is the ERC-only strip (--ERConly)
STANDARD_ZONE_MIN_DETECTION_SIZE = 12
ZONE_MIN_DETECTION_SIZES = {
    "bottom_right": STANDARD_ZONE_MIN_DETECTION_SIZE,
    "bottom_left_driver": STANDARD_ZONE_MIN_DETECTION_SIZE,
    "bottom_right_up_ad": STANDARD_ZONE_MIN_DETECTION_SIZE,
    "bottom_left": 8,
}

# Brand-specific minimum detection sizes (in pixels)
# These can override zone-specific or default minimum sizes for specific brands
BRAND_MIN_DETECTION_SIZES = {
    "lancia": 5,
    "citroen": 5,
    "toyota": 5,  # small car logo in TVGI driver strip
    "renault": 8,
    "pirelli": 8,
    "michelin": 8,
    "hankook": 8,
    "mrf tyres": 8,
}

# Brand-specific minimum confidence thresholds
# These override DEFAULT_MIN_CONFIDENCE for specific brands
BRAND_MIN_CONFIDENCE = {
    "lancia": 0.45,
    "citroen": 0.52,
    "pirelli": 0.52,
    "michelin": 0.52,
    "toyota": 0.45,  # align with wrc_template_matcher (was 0.62 — too strict)
    "hyundai": 0.45,
    "renault": 0.45,
    "skoda": 0.48,
    "hankook": 0.58,  # reduce false positives on nearby tire logos
    "erc": 0.50,
}

# Maximum detection size ratio (relative to image) - filter out huge detections
# Increased to allow large center logos (like title cards)
MAX_DETECTION_SIZE_RATIO = 0.6  # 60% of image size (was 0.3)

# ERC output: zone-focused, one best hit per template file, light overlap rules.
ERC_BEST_MATCH_PER_TEMPLATE = True
ERC_DETECTION_MIN_ZONE_OVERLAP = 0.55
# Small / faint TVGI logos (Lancia, Toyota, …)
ERC_DETECTION_MIN_ZONE_OVERLAP_SMALL = 0.40
ERC_JSON_MIN_BOX_PX_DEFAULT = 12
ERC_JSON_MIN_BOX_DISPLAY_PX_DEFAULT = 6
ERC_JSON_MIN_BOX_PX_BY_BRAND = {
    "lancia": 6,
    "citroen": 8,
    "toyota": 6,
    "pirelli": 8,
    "michelin": 8,
    "hankook": 8,
    "mrf tyres": 8,
    "ford": 10,
    "hyundai": 10,
    "skoda": 10,
    "renault": 8,
}
ERC_JSON_MIN_BOX_DISPLAY_BY_BRAND = {
    "lancia": 5,
    "citroen": 5,
    "toyota": 5,
    "renault": 6,
    "pirelli": 8,
    "michelin": 8,
    "hankook": 8,
    "mrf tyres": 8,
}
ERC_JSON_MIN_ZONE_OVERLAP = 0.55
ERC_JSON_MIN_ZONE_OVERLAP_SMALL = 0.40

# Reject only extremely wide false matches (zone crop is ~47px tall — do not filter by height)
MAX_BOX_ZONE_WIDTH_RATIO = 0.62
# bottom_left TVGI strip: logo often fills nearly the whole zone crop
MAX_BOX_ZONE_WIDTH_RATIO_BY_ZONE = {
    "bottom_left": 1.0,
}

# bottom_right TVGI panel: tire logo left, car logo right (fraction of zone width)
BOTTOM_RIGHT_TIRE_X_SPLIT = 0.50

# Car slot: tie-break when confidences are close (Toyota still wins if clearly best)
BOTTOM_RIGHT_CAR_PREFERRED = frozenset({"skoda", "lancia", "citroen", "hyundai", "renault"})
BOTTOM_RIGHT_CAR_DEPRIORITIZE = frozenset({"ford"})  # Ford only — Toyota must not be suppressed globally
# If Toyota beats best preferred car by this margin, keep Toyota
BOTTOM_RIGHT_DEPRIORITIZE_MARGIN = 0.06

# Annotool photos.csv "Percentage" = box_area / (json_w * json_h) * 100 — drop tiny junk (e.g. 0.100)
ERC_MIN_CSV_PERCENT = 0.10
# Small driver-strip logos (Lancia ~30×10px) land near 0.02–0.03% on 960×540 canvas — 0.04 was too strict
ERC_MIN_CSV_PERCENT_DIFFICULT = 0.015
ERC_MIN_CSV_PERCENT_BY_BRAND = {
    "lancia": 0.012,
    "citroen": 0.015,
    "toyota": 0.02,
    "renault": 0.02,
    "hyundai": 0.02,
    "skoda": 0.02,
    "pirelli": 0.025,
    "erc": 0.012,
}

# Drop JSON annotations below this template-match confidence
ERC_MIN_ANNOTATION_CONFIDENCE = 0.10

# Brands / zones actually loaded from erc_templates/ (set in main)
LOADED_TEMPLATE_BRANDS: Optional[frozenset] = None
LOADED_TEMPLATE_ZONES: Optional[frozenset] = None

# Small / difficult brands — extra scales + lower match threshold (all images)
DIFFICULT_MATCH_BRANDS = frozenset({
    "lancia", "citroen", "pirelli", "erc", "toyota", "renault", "hyundai", "skoda",
})
SMALL_MATCH_BRANDS = frozenset({"lancia", "citroen", "toyota", "renault", "hyundai", "skoda"})
# Extra template-match threshold reduction (on top of DIFFICULT -0.15)
BRAND_MATCH_THRESHOLD_ADJUST = {
    "lancia": -0.25,
    "citroen": -0.18,
    "renault": -0.14,
    "hyundai": -0.12,
    "skoda": -0.12,
    "ford": 0.18,
}
# Primary marque logos in TVGI strips — keep when clearly best (before Lancia tie-break)
PRIMARY_CAR_BRANDS = frozenset({"toyota", "renault", "hyundai", "skoda"})
PRIMARY_CAR_MIN_CONFIDENCE = 0.48
PRIMARY_CAR_BEAT_LANCIA_MARGIN = 0.05
# Second-pass floor when Lancia finds nothing at the normal threshold
LANCIA_RETRY_THRESHOLD = 0.38
# bottom_left: ERC TVGI strip only (--ERConly). All other zones share STANDARD_* rules.
ERC_ONLY_ZONE = "bottom_left"
STANDARD_LOGO_ZONES = frozenset({
    "bottom_right",
    "bottom_left_driver",
    "bottom_right_up_ad",
})
# Prefer Lancia/Citroen over weak false positives only in single-slot driver/ad zones
STANDARD_ZONE_PREFER_MARGIN = 0.12
SINGLE_SLOT_CAR_ZONES = frozenset({"bottom_left_driver", "bottom_right_up_ad"})
# bottom_right TVGI panel: Toyota is a real car logo — never auto-drop it for Lancia
SINGLE_SLOT_DEPRIORITIZE_BRANDS = frozenset({"ford"})
# Slightly larger search crop for tiny logos (fraction of zone size)
SMALL_BRAND_ZONE_PAD_RATIO = 0.08

# Tire brands side-by-side: suppress cross-brand overlap (keep best confidence)
TIRE_BRANDS = frozenset({"pirelli", "hankook", "michelin", "mrf tyres"})
TIRE_CROSS_BRAND_IOU = 0.35

# Screen Zones - coordinates from zone_picker.py (relative 0.0-1.0)
SCREEN_ZONES = {
    "bottom_right": {
        "x_start": 0.7177,
        "x_end": 0.8240,
        "y_start": 0.8630,
        "y_end": 0.9074,
        "description": "Bottom Right Corner - TVGI-Driver"
    },
    "bottom_right_up_ad": {
        "x_start": 0.7802,
        "x_end": 0.8609,
        "y_start": 0.6963,
        "y_end": 0.7315,
        "description": "Bottom Right Corner - TVGI-Driver"
    },
    "bottom_left_driver": {
        "x_start": 0.3167,
        "x_end": 0.4245,
        "y_start": 0.8648,
        "y_end": 0.9102,
        "description": "bottom_left_driver"
    },
    "bottom_left": {
        "x_start": 0.0896,
        "x_end": 0.1406,
        "y_start": 0.8657,
        "y_end": 0.9056,
        "description": "ERC TVGI bottom-left strip",
    },
}

# All overlay zones (folder name must match SCREEN_ZONES key exactly).
ERC_ALL_ZONES = (
    "bottom_right",
    "bottom_right_up_ad",
    "bottom_left_driver",
    "bottom_left",
)

# Zones to search this run: set in main() — bottom_left only with --ERConly, else ERC_ALL_ZONES.
ERC_ACTIVE_ZONES: Tuple[str, ...] = ERC_ALL_ZONES

# Legacy --region-only: restrict to bottom_left_driver zone
BOTTOM_LEFT_REGION = SCREEN_ZONES["bottom_left_driver"]


def _preprocess_grayscale(image: np.ndarray) -> np.ndarray:
    """Contrast + sharpen (must match between frame and template, or match neither)."""
    out = cv2.convertScaleAbs(image, alpha=1.2, beta=10)
    gaussian = cv2.GaussianBlur(out, (0, 0), 2.0)
    return cv2.addWeighted(out, 1.5, gaussian, -0.5, 0)


def _should_preprocess_template(brand: Optional[str], zone_name: Optional[str]) -> bool:
    if brand and brand.lower() == "toyota":
        return False
    return True


def _max_box_zone_width_ratio(zone_name: Optional[str]) -> float:
    if zone_name:
        return MAX_BOX_ZONE_WIDTH_RATIO_BY_ZONE.get(zone_name, MAX_BOX_ZONE_WIDTH_RATIO)
    return MAX_BOX_ZONE_WIDTH_RATIO


def _zone_match_scales(region: np.ndarray, template: np.ndarray) -> Optional[List[float]]:
    """When template is larger than the zone crop, only try scales that fit."""
    tw, th = template.shape[1], template.shape[0]
    rw, rh = region.shape[1], region.shape[0]
    if tw > rw or th > rh:
        return _scales_fitting_region(region, template)
    return None


def _scales_for_small_brand_match(
    region: np.ndarray, template: np.ndarray, brand: Optional[str]
) -> Optional[List[float]]:
    """Fine-grained scales for tiny TVGI logos (Lancia/Citroen/Toyota).

    Always searches many scales in the zone — not only 1.0 when the template fits.
    """
    if not brand or brand.lower() not in SMALL_MATCH_BRANDS:
        return _zone_match_scales(region, template)
    rh, rw = region.shape[:2]
    th, tw = template.shape[:2]
    if tw < 1 or th < 1:
        return [1.0]
    max_scale = min(rw / tw, rh / th) * 0.98
    candidates = [
        0.12, 0.15, 0.18, 0.2, 0.22, 0.25, 0.28, 0.3, 0.32, 0.35, 0.38, 0.4,
        0.42, 0.45, 0.48, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9,
        0.95, 1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.35, 1.4, 1.5, 1.6, 1.75, 2.0,
    ]
    scales = [
        s for s in candidates
        if s <= max_scale and int(tw * s) >= 6 and int(th * s) >= 6
    ]
    return scales or [min(1.0, max_scale)]


def _brand_match_threshold_adjust(brand: Optional[str]) -> float:
    if not brand:
        return 0.0
    b = brand.lower()
    if b in BRAND_MATCH_THRESHOLD_ADJUST:
        return BRAND_MATCH_THRESHOLD_ADJUST[b]
    if b in DIFFICULT_MATCH_BRANDS:
        return -0.15
    return 0.0


def _apply_template_preprocess(
    template: np.ndarray, brand: Optional[str], zone_name: Optional[str]
) -> np.ndarray:
    if _should_preprocess_template(brand, zone_name):
        return _preprocess_grayscale(template)
    return template


def _scales_fitting_region(region: np.ndarray, template: np.ndarray) -> List[float]:
    """Scales where template fits inside a small zone crop (e.g. bottom_left ~98×43)."""
    rh, rw = region.shape[:2]
    th, tw = template.shape[:2]
    if tw < 1 or th < 1 or rw < 10 or rh < 10:
        return [1.0]
    max_scale = min(rw / tw, rh / th) * 0.98
    candidates = [
        0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9,
        0.95, 1.0, 1.05, 1.1, 1.15, 1.2, 1.3, 1.4, 1.5,
    ]
    return [
        s for s in candidates
        if s <= max_scale
        and int(tw * s) >= 8
        and int(th * s) >= 8
    ] or [min(1.0, max_scale)]


def _expand_zone_pixel_bounds(
    x_start: int, x_end: int, y_start: int, y_end: int, width: int, height: int,
    pad_ratio: float = SMALL_BRAND_ZONE_PAD_RATIO,
) -> Tuple[int, int, int, int]:
    """Pad zone crop so small logos near edges are not clipped."""
    zw, zh = x_end - x_start, y_end - y_start
    px = max(2, int(zw * pad_ratio))
    py = max(2, int(zh * pad_ratio))
    return (
        max(0, x_start - px),
        min(width, x_end + px),
        max(0, y_start - py),
        min(height, y_end + py),
    )


def _fallback_minmax_match(
    region: np.ndarray,
    template: np.ndarray,
    scales: List[float],
    brand: Optional[str],
    threshold: float,
) -> List[Tuple[int, int, int, int, float]]:
    """Single best correlation box when multi-match NMS returns nothing (common for Lancia)."""
    eff = threshold + _brand_match_threshold_adjust(brand)
    best_box = None
    best_conf = 0.0
    for scale in scales:
        if scale != 1.0:
            w = max(1, int(template.shape[1] * scale))
            h = max(1, int(template.shape[0] * scale))
            if w > region.shape[1] or h > region.shape[0]:
                continue
            interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
            scaled = cv2.resize(template, (w, h), interpolation=interp)
        else:
            scaled = template
        if scaled.shape[0] > region.shape[0] or scaled.shape[1] > region.shape[1]:
            continue
        result = cv2.matchTemplate(region, scaled, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        max_val = float(max_val)
        if max_val > best_conf:
            x, y = max_loc
            best_conf = max_val
            best_box = (x, y, x + scaled.shape[1], y + scaled.shape[0], max_val)
    if best_box and best_conf >= eff:
        return [best_box]
    return []


def _peak_template_score(
    region: np.ndarray, template: np.ndarray, scales: List[float]
) -> float:
    """Best TM_CCOEFF_NORMED score across scales (for --debug-match)."""
    best = 0.0
    for scale in scales:
        if scale != 1.0:
            w = max(1, int(template.shape[1] * scale))
            h = max(1, int(template.shape[0] * scale))
            if w > region.shape[1] or h > region.shape[0]:
                continue
            interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
            scaled = cv2.resize(template, (w, h), interpolation=interp)
        else:
            scaled = template
        if scaled.shape[0] > region.shape[0] or scaled.shape[1] > region.shape[1]:
            continue
        result = cv2.matchTemplate(region, scaled, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        best = max(best, float(max_val))
    return best


def detection_center_zone(
    x1: int, y1: int, x2: int, y2: int, width: int, height: int
) -> Optional[str]:
    """Return active zone name if detection center lies inside it, else None."""
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    for zone_name in ERC_ACTIVE_ZONES:
        zone = SCREEN_ZONES[zone_name]
        if (
            zone["x_start"] * width <= cx <= zone["x_end"] * width
            and zone["y_start"] * height <= cy <= zone["y_end"] * height
        ):
            return zone_name
    return None


def box_overlap_fraction_in_zone(
    x1: int, y1: int, x2: int, y2: int, zone_name: str, width: int, height: int
) -> float:
    """Fraction of box area that lies inside the given zone (0.0–1.0)."""
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    box_area = (x2 - x1) * (y2 - y1)
    if box_area <= 0:
        return 0.0
    zone = SCREEN_ZONES[zone_name]
    zx1 = zone["x_start"] * width
    zx2 = zone["x_end"] * width
    zy1 = zone["y_start"] * height
    zy2 = zone["y_end"] * height
    ix1 = max(x1, zx1)
    iy1 = max(y1, zy1)
    ix2 = min(x2, zx2)
    iy2 = min(y2, zy2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    return ((ix2 - ix1) * (iy2 - iy1)) / box_area


def _detection_zone(det: tuple) -> Optional[str]:
    return det[8] if len(det) > 8 else None


def _json_min_box_px(brand: Optional[str]) -> int:
    if brand:
        return ERC_JSON_MIN_BOX_PX_BY_BRAND.get(brand.lower(), ERC_JSON_MIN_BOX_PX_DEFAULT)
    return ERC_JSON_MIN_BOX_PX_DEFAULT


def _json_min_box_display_px(brand: Optional[str]) -> int:
    if brand:
        return ERC_JSON_MIN_BOX_DISPLAY_BY_BRAND.get(
            brand.lower(), ERC_JSON_MIN_BOX_DISPLAY_PX_DEFAULT
        )
    return ERC_JSON_MIN_BOX_DISPLAY_PX_DEFAULT


def get_annotool_canvas_size(orig_width: int, orig_height: int) -> Tuple[int, int]:
    """Match annotool-desktop_v2/js/webannotool.js loadImg() display dimensions.

    JSON startPoint/diagPoint must use this space — annotool draws them on the
    canvas without rescaling from per-image width/height metadata.
    """
    max_width, max_height = 960, 720
    if orig_height <= 0:
        return 960, 540
    aspect_ratio = orig_width / orig_height
    if orig_width > max_width or orig_height > max_height:
        if orig_width > orig_height:
            im_width = max_width
            im_height = int(round(im_width / aspect_ratio))
        else:
            im_height = max_height
            im_width = int(round(im_height * aspect_ratio))
    else:
        im_width = orig_width
        im_height = orig_height
    if im_width < 700:
        im_width = 700
    if im_height < 500:
        im_height = 500
    return int(im_width), int(im_height)


def _detection_iou(
    x1: int, y1: int, x2: int, y2: int,
    ex1: int, ey1: int, ex2: int, ey2: int,
) -> float:
    ix1 = max(x1, ex1)
    iy1 = max(y1, ey1)
    ix2 = min(x2, ex2)
    iy2 = min(y2, ey2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    a1 = (x2 - x1) * (y2 - y1)
    a2 = (ex2 - ex1) * (ey2 - ey1)
    union = a1 + a2 - inter
    return inter / union if union > 0 else 0.0


def resolve_tire_brand_overlaps(
    detections: List[Tuple[int, int, int, int, float, str, str, str]],
    iou_threshold: float = TIRE_CROSS_BRAND_IOU,
) -> List[Tuple[int, int, int, int, float, str, str, str]]:
    """If Hankook/Pirelli/etc. overlap, keep only the highest-confidence hit."""
    tire: List[Tuple] = []
    other: List[Tuple] = []
    for det in detections:
        brand = (det[6] or "").lower()
        if brand in TIRE_BRANDS:
            tire.append(det)
        else:
            other.append(det)
    if len(tire) < 2:
        return detections
    kept: List[Tuple] = []
    for det in sorted(tire, key=lambda d: d[4], reverse=True):
        x1, y1, x2, y2 = det[0], det[1], det[2], det[3]
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        if any(
            _detection_iou(x1, y1, x2, y2, k[0], k[1], k[2], k[3]) > iou_threshold
            for k in kept
        ):
            continue
        kept.append(det)
    return other + kept


def is_valid_erc_json_detection(
    x1: int, y1: int, x2: int, y2: int, width: int, height: int,
    brand: Optional[str] = None,
    template_zone: Optional[str] = None,
) -> bool:
    """Keep boxes with enough overlap inside the ERC zone that was searched."""
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    box_w = x2 - x1
    box_h = y2 - y1
    min_px = _json_min_box_px(brand)
    if box_w < min_px or box_h < min_px:
        return False
    canvas_w, canvas_h = get_annotool_canvas_size(width, height)
    scale_x = canvas_w / width if width else 1.0
    scale_y = canvas_h / height if height else 1.0
    min_disp = _json_min_box_display_px(brand)
    if box_w * scale_x < min_disp or box_h * scale_y < min_disp:
        return False
    check_zone = template_zone if template_zone in ERC_ACTIVE_ZONES else detection_center_zone(
        x1, y1, x2, y2, width, height
    )
    if check_zone is None:
        return False
    overlap = box_overlap_fraction_in_zone(x1, y1, x2, y2, check_zone, width, height)
    min_json_overlap = ERC_JSON_MIN_ZONE_OVERLAP
    if brand and brand.lower() in SMALL_MATCH_BRANDS:
        min_json_overlap = ERC_JSON_MIN_ZONE_OVERLAP_SMALL
    if overlap < min_json_overlap:
        return False
    zone = SCREEN_ZONES[check_zone]
    zone_w = (zone["x_end"] - zone["x_start"]) * width
    zone_h = (zone["y_end"] - zone["y_start"]) * height
    max_w_ratio = _max_box_zone_width_ratio(check_zone)
    if zone_w > 0 and box_w > zone_w * max_w_ratio:
        return False
    return True


def _erc_detection_reject_reason(
    x1: int, y1: int, x2: int, y2: int,
    width: int, height: int,
    zone_name: str,
    zone_min_size: int,
    brand: Optional[str] = None,
) -> Optional[str]:
    """Why a raw match was dropped; None if it would be kept."""
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    det_size = max(x2 - x1, y2 - y1)
    if det_size < zone_min_size:
        return f"too small ({det_size}px < {zone_min_size}px)"
    if box_overlap_fraction_in_zone(x1, y1, x2, y2, zone_name, width, height) < ERC_DETECTION_MIN_ZONE_OVERLAP:
        return "low zone overlap"
    if not is_valid_erc_json_detection(
        x1, y1, x2, y2, width, height, brand=brand, template_zone=zone_name
    ):
        zone = SCREEN_ZONES[zone_name]
        zone_w = (zone["x_end"] - zone["x_start"]) * width
        box_w = x2 - x1
        if zone_w > 0 and box_w > zone_w * _max_box_zone_width_ratio(zone_name):
            return f"box too wide ({box_w:.0f}px > {zone_w * _max_box_zone_width_ratio(zone_name):.0f}px)"
        return "json/annotool size filter"
    return None


def _brand_allowed(brand: Optional[str]) -> bool:
    if not brand or LOADED_TEMPLATE_BRANDS is None:
        return bool(brand)
    return brand.lower() in LOADED_TEMPLATE_BRANDS


def _consolidate_bottom_right_panel(
    dets: List[Tuple], width: int, height: int
) -> List[Tuple]:
    """Tire logo left, car logo right in the TVGI driver strip."""
    zone = SCREEN_ZONES["bottom_right"]
    zx1 = zone["x_start"] * width
    zx2 = zone["x_end"] * width
    split_x = zx1 + (zx2 - zx1) * BOTTOM_RIGHT_TIRE_X_SPLIT

    tire_candidates: List[Tuple] = []
    car_candidates: List[Tuple] = []
    for d in dets:
        cx = (d[0] + d[2]) / 2
        brand = (d[6] or "").lower()
        if brand in TIRE_BRANDS:
            tire_candidates.append(d)
        elif cx >= split_x:
            car_candidates.append(d)

    out: List[Tuple] = []
    if tire_candidates:
        out.append(max(tire_candidates, key=lambda d: d[4]))
    if car_candidates:
        picked = _pick_car_for_bottom_right(car_candidates)
        if picked is not None:
            out.append(picked)
    return out


def _best_per_brand(car_candidates: List[Tuple]) -> Dict[str, Tuple]:
    by_brand: Dict[str, Tuple] = {}
    for d in car_candidates:
        b = (d[6] or "").lower()
        if b not in by_brand or d[4] > by_brand[b][4]:
            by_brand[b] = d
    return by_brand


def _pick_car_for_bottom_right(car_candidates: List[Tuple]) -> Optional[Tuple]:
    """bottom_right car slot: highest confidence wins; Toyota is never dropped for Lancia."""
    if not car_candidates:
        return None
    by_brand = _best_per_brand(car_candidates)
    best = max(by_brand.values(), key=lambda d: d[4])
    brand = (best[6] or "").lower()
    if brand not in BOTTOM_RIGHT_CAR_DEPRIORITIZE:
        preferred = [
            d for d in by_brand.values()
            if (d[6] or "").lower() in BOTTOM_RIGHT_CAR_PREFERRED
        ]
        if preferred:
            best_pref = max(preferred, key=lambda d: d[4])
            if best_pref[4] > best[4] + BOTTOM_RIGHT_DEPRIORITIZE_MARGIN:
                return best_pref
        return best
    preferred = [
        d for d in by_brand.values()
        if (d[6] or "").lower() in BOTTOM_RIGHT_CAR_PREFERRED
    ]
    if preferred:
        best_pref = max(preferred, key=lambda d: d[4])
        if best[4] >= best_pref[4] + BOTTOM_RIGHT_DEPRIORITIZE_MARGIN:
            return best
        return best_pref
    return best


def _pick_car_for_single_slot(car_candidates: List[Tuple]) -> Optional[Tuple]:
    """Driver/ad strip: keep real Toyota/Renault/etc. when best; Lancia only if competitive."""
    if not car_candidates:
        return None
    by_brand = _best_per_brand(car_candidates)
    best_any = max(by_brand.values(), key=lambda d: d[4])
    best_brand = (best_any[6] or "").lower()
    lancia = by_brand.get("lancia")
    lmin = BRAND_MIN_CONFIDENCE.get("lancia", 0.45)

    if best_brand in PRIMARY_CAR_BRANDS and best_any[4] >= PRIMARY_CAR_MIN_CONFIDENCE:
        if lancia is None or lancia[4] < lmin:
            return best_any
        if best_any[4] > lancia[4] + PRIMARY_CAR_BEAT_LANCIA_MARGIN:
            return best_any

    pool = {
        b: d for b, d in by_brand.items() if b not in SINGLE_SLOT_DEPRIORITIZE_BRANDS
    }
    if not pool:
        pool = by_brand
    best = max(pool.values(), key=lambda d: d[4])
    # Lancia/Citroen only when within margin of the actual best score (not a weaker false positive)
    for pref in ("lancia", "citroen"):
        if pref not in pool:
            continue
        pref_det = pool[pref]
        if pref == "lancia" and pref_det[4] < lmin:
            continue
        if pref_det[4] >= best[4] - STANDARD_ZONE_PREFER_MARGIN:
            return pref_det
    for pref in ("skoda", "hyundai", "renault"):
        if pref in pool and pool[pref][4] >= best[4] - 0.06:
            return pool[pref]
    return best


def _annotation_csv_percent(
    start_point: List[float],
    diag_point: List[float],
    canvas_w: int,
    canvas_h: int,
) -> float:
    """Same metric as annotool generatePhotoCSV (Percentage column)."""
    if canvas_w <= 0 or canvas_h <= 0:
        return 0.0
    box_w = abs(diag_point[0] - start_point[0])
    box_h = abs(diag_point[1] - start_point[1])
    return round(box_w * box_h / (canvas_w * canvas_h) * 1e5) / 1000


def _output_filter_reject_reason(
    conf: float,
    brand: Optional[str],
    start_point: List[float],
    diag_point: List[float],
    canvas_w: int,
    canvas_h: int,
) -> Optional[str]:
    """Why a detection was dropped before JSON export; None if OK."""
    if conf < ERC_MIN_ANNOTATION_CONFIDENCE:
        return f"low conf ({conf:.3f} < {ERC_MIN_ANNOTATION_CONFIDENCE})"
    pct = _annotation_csv_percent(start_point, diag_point, canvas_w, canvas_h)
    b = (brand or "").lower()
    min_pct = ERC_MIN_CSV_PERCENT_BY_BRAND.get(b, ERC_MIN_CSV_PERCENT)
    if b in (DIFFICULT_MATCH_BRANDS | SMALL_MATCH_BRANDS):
        min_pct = min(min_pct, ERC_MIN_CSV_PERCENT_DIFFICULT)
    if pct < min_pct:
        return f"csv% too small ({pct:.3f}% < {min_pct}%)"
    return None


def _passes_output_filters(
    conf: float,
    brand: Optional[str],
    start_point: List[float],
    diag_point: List[float],
    canvas_w: int,
    canvas_h: int,
) -> bool:
    return _output_filter_reject_reason(
        conf, brand, start_point, diag_point, canvas_w, canvas_h
    ) is None


def finalize_image_detections(detections: List[Tuple]) -> List[Tuple]:
    """Keep bottom_right pair when complete; still allow bottom_left / up_ad zones."""
    br = [d for d in detections if _detection_zone(d) == "bottom_right"]
    rest = [d for d in detections if _detection_zone(d) != "bottom_right"]
    if len(br) >= 2:
        return br + rest
    return detections


def _consolidate_erc_zone(dets: List[Tuple]) -> List[Tuple]:
    """bottom_left: ERC strip only — best ERC hit."""
    erc = [d for d in dets if (d[6] or "").lower() == "erc"]
    if not erc:
        return []
    return [max(erc, key=lambda d: d[4])]


def _consolidate_standard_single_slot(dets: List[Tuple]) -> List[Tuple]:
    """One car (or tire if no car) per zone — Lancia-friendly pick in driver/ad strips."""
    car_dets = [d for d in dets if (d[6] or "").lower() not in TIRE_BRANDS]
    tires = [d for d in dets if (d[6] or "").lower() in TIRE_BRANDS]
    out: List[Tuple] = []
    if car_dets:
        picked = _pick_car_for_single_slot(car_dets)
        if picked is not None:
            out.append(picked)
    elif tires:
        out.append(max(tires, key=lambda d: d[4]))
    return out


def _consolidate_standard_zone(
    zone_name: str, dets: List[Tuple], width: int, height: int
) -> List[Tuple]:
    """Unified consolidate for bottom_right / bottom_left_driver / bottom_right_up_ad."""
    if zone_name == "bottom_right" and width > 0 and height > 0:
        return _consolidate_bottom_right_panel(dets, width, height)
    return _consolidate_standard_single_slot(dets)


def consolidate_zone_detections(
    detections: List[Tuple], width: int = 0, height: int = 0
) -> List[Tuple]:
    """bottom_left → ERC only; all other active zones → STANDARD_LOGO_ZONES rules."""
    by_zone: Dict[str, List[Tuple]] = {}
    for det in detections:
        zone = _detection_zone(det)
        if zone not in ERC_ACTIVE_ZONES:
            continue
        by_zone.setdefault(zone, []).append(det)

    out: List[Tuple] = []
    for zone_name, dets in by_zone.items():
        if zone_name == ERC_ONLY_ZONE:
            out.extend(_consolidate_erc_zone(dets))
        elif zone_name in STANDARD_LOGO_ZONES:
            out.extend(_consolidate_standard_zone(zone_name, dets, width, height))
        else:
            out.extend(_consolidate_standard_single_slot(dets))
    return out


def load_templates(templates_dir: Path) -> List[Tuple[Path, np.ndarray, str, str, Optional[str]]]:
    """Load all template images from templates directory and subfolders.
    
    Supports zone-based folder structure with location:
        templates/
        ├── ERC Logos/
        │   └── bottom_left/          <- Zone folder
        │       └── TVGI/              <- Location folder
        │           └── erc_logo.png
        ├── Ford Logos/
        │   └── left_column/          <- Zone folder
        │       └── TVGI/              <- Location folder
        │           └── ford_leaderboard.png
    
    Also supports old structures:
        templates/
        ├── Ford Logos/
        │   └── TVGI/                <- Location folder (searches everywhere, no zone)
        │       └── ford_colored_leaderboard.png
        └── ERC Logos/
            └── bottom_left/         <- Zone folder (no location subfolder)
                └── erc_logo.png
    
    Returns:
        List of (template_path, template_image, brand, location, zone) tuples
        zone is None if not in a zone folder, otherwise the zone name (e.g., "bottom_left")
    """
    templates = []
    if not templates_dir.exists():
        print(f"⚠️  Templates directory not found: {templates_dir}")
        return templates
    
    # Check for subfolder structure: {Brand} Logos/{Zone or Location}/
    brand_folders = [d for d in templates_dir.iterdir() if d.is_dir() and "logos" in d.name.lower()]
    
    if brand_folders:
        # New structure: subfolders by brand and location/zone
        print(f"📁 Found brand folders structure")
        for brand_folder in brand_folders:
            # Extract brand from folder name (e.g., "Ford Logos" -> "Ford")
            brand_name = brand_folder.name.replace(" Logos", "").replace(" logos", "").strip()
            
            # Look for zone or location subfolders
            subfolders = [d for d in brand_folder.iterdir() if d.is_dir()]
            
            if subfolders:
                for subfolder in subfolders:
                    folder_name = subfolder.name
                    
                    # Check if this folder name is a valid zone
                    zone_name = None
                    location_name = None
                    
                    if folder_name in SCREEN_ZONES:
                        # Zone folder (bottom_right, bottom_left, …) — active filter applied in main()
                        zone_name = folder_name
                        print(f"   🎯 Zone detected: {brand_name}/{zone_name}")
                        
                        # Check for location subfolders inside zone folder
                        location_folders = [d for d in subfolder.iterdir() if d.is_dir()]
                        
                        if location_folders:
                            # Zone/Location structure: Brand/Zone/Location/templates
                            for location_folder in location_folders:
                                location_name = location_folder.name
                                print(f"      📍 Location: {location_name}")
                                
                                # Load templates from location folder
                                for ext in ["*.png", "*.jpg", "*.jpeg"]:
                                    for template_path in location_folder.glob(ext):
                                        try:
                                            template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
                                            if template is not None:
                                                template = _apply_template_preprocess(
                                                    template, brand_name, zone_name
                                                )
                                                templates.append((template_path, template, brand_name, location_name, zone_name))
                                                print(f"✅ Loaded: {brand_name}/{zone_name}/{location_name}/{template_path.name} ({template.shape[1]}x{template.shape[0]})")
                                        except Exception as e:
                                            print(f"⚠️  Failed to load {template_path.name}: {e}")
                        else:
                            # Zone folder but no location subfolder - templates directly in zone folder
                            location_name = zone_name  # Use zone name as location
                            print(f"      📍 No location subfolder, using zone name as location")
                            
                            # Load templates directly from zone folder
                            for ext in ["*.png", "*.jpg", "*.jpeg"]:
                                for template_path in subfolder.glob(ext):
                                    try:
                                        template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
                                        if template is not None:
                                            template = _apply_template_preprocess(
                                                template, brand_name, zone_name
                                            )
                                            templates.append((template_path, template, brand_name, location_name, zone_name))
                                            print(f"✅ Loaded: {brand_name}/{zone_name}/{template_path.name} ({template.shape[1]}x{template.shape[0]})")
                                    except Exception as e:
                                        print(f"⚠️  Failed to load {template_path.name}: {e}")
                    else:
                        # Not a zone folder, treat as location (old structure: Brand/Location/templates)
                        location_name = folder_name
                        zone_name = None
                        print(f"   📍 Location: {brand_name}/{location_name} (no zone restriction)")
                        
                        # Load templates from this location folder
                        for ext in ["*.png", "*.jpg", "*.jpeg"]:
                            for template_path in subfolder.glob(ext):
                                try:
                                    template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
                                    if template is not None:
                                        template = _apply_template_preprocess(
                                            template, brand_name, zone_name
                                        )
                                        templates.append((template_path, template, brand_name, location_name, zone_name))
                                        print(f"✅ Loaded: {brand_name}/{location_name}/{template_path.name} ({template.shape[1]}x{template.shape[0]})")
                                except Exception as e:
                                    print(f"⚠️  Failed to load {template_path.name}: {e}")
            else:
                # No location/zone subfolders, check directly in brand folder
                for ext in ["*.png", "*.jpg", "*.jpeg"]:
                    for template_path in brand_folder.glob(ext):
                        try:
                            template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
                            if template is not None:
                                template = _apply_template_preprocess(
                                    template, brand_name, zone_name
                                )
                                # Default location if not in subfolder, no zone restriction
                                location_name = "Unknown"
                                zone_name = None
                                templates.append((template_path, template, brand_name, location_name, zone_name))
                                print(f"✅ Loaded: {brand_name}/{template_path.name} ({template.shape[1]}x{template.shape[0]})")
                        except Exception as e:
                            print(f"⚠️  Failed to load {template_path.name}: {e}")
    else:
        # Old structure: templates directly in templates/ folder
        print(f"📁 Using flat structure (templates directly in templates/)")
        for ext in ["*.png", "*.jpg", "*.jpeg"]:
            for template_path in templates_dir.glob(ext):
                try:
                    template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
                    if template is not None:
                        # Extract brand from filename
                        brand_name = extract_brand_from_filename(template_path.name)
                        template = _apply_template_preprocess(template, brand_name, None)
                        # Default location, no zone restriction
                        location_name = "Unknown"
                        zone_name = None
                        templates.append((template_path, template, brand_name, location_name, zone_name))
                        print(f"✅ Loaded template: {template_path.name} ({template.shape[1]}x{template.shape[0]})")
                except Exception as e:
                    print(f"⚠️  Failed to load {template_path.name}: {e}")
    
    return templates


def match_template_multi_scale(
    image: np.ndarray,
    template: np.ndarray,
    threshold: float = DEFAULT_THRESHOLD,
    scales: List[float] = None
) -> Optional[Tuple[int, int, int, int, float]]:
    """Match template with multi-scale approach.
    
    Optimized version with early exit and efficient scaling.
    
    Args:
        image: Grayscale image to search in
        template: Grayscale template to find
        threshold: Minimum match confidence (0-1)
        scales: List of scales to try (default: adaptive based on template size)
    
    Returns:
        (x1, y1, x2, y2, confidence) if match found, None otherwise
    """
    if scales is None:
        # Adaptive scales based on template size
        # For small templates (leaderboard logos), use wider range of downscales
        template_size = min(template.shape[0], template.shape[1])
        if template_size > 200:
            # Very large templates (title cards, center logos) - allow upscaling
            scales = [0.5, 0.7, 1.0, 1.5, 2.0, 2.5, 3.0]
        elif template_size > 100:
            # Large templates (car body, driver panel) - normal scales
            scales = [0.6, 0.8, 1.0, 1.2, 1.5, 2.0]
        elif template_size > 50:
            # Medium templates - wider range
            scales = [0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5]
        else:
            # Small templates (leaderboard) - very wide range to catch tiny logos
            scales = [0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5, 2.0]
    
    best_match = None
    best_confidence = 0.0
    
    # Pre-calculate adaptive thresholds for different sizes
    threshold_small = max(0.4, threshold - 0.15)
    threshold_medium = max(0.45, threshold - 0.1)
    
    for scale in scales:
        # Resize template
        if scale != 1.0:
            width = int(template.shape[1] * scale)
            height = int(template.shape[0] * scale)
            if width < 10 or height < 10:
                continue
            # Use INTER_AREA for downscaling (better quality), INTER_LINEAR for upscaling
            interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
            scaled_template = cv2.resize(template, (width, height), interpolation=interpolation)
        else:
            scaled_template = template
        
        # Validate that template is not larger than image
        if scaled_template.shape[0] > image.shape[0] or scaled_template.shape[1] > image.shape[1]:
            # Template is too large, skip this scale
            continue
        
        # Template matching
        result = cv2.matchTemplate(image, scaled_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        # Adaptive threshold: lower threshold for very small scaled templates
        # (small logos are harder to match due to compression/blur)
        scaled_size = min(scaled_template.shape[0], scaled_template.shape[1])
        if scaled_size < 30:
            effective_threshold = threshold_small
        elif scaled_size < 50:
            effective_threshold = threshold_medium
        else:
            effective_threshold = threshold
        
        # Early exit if we found a very high confidence match
        if max_val >= 0.95 and max_val >= effective_threshold:
            x1 = max_loc[0]
            y1 = max_loc[1]
            x2 = x1 + scaled_template.shape[1]
            y2 = y1 + scaled_template.shape[0]
            return (x1, y1, x2, y2, max_val)
        
        if max_val > best_confidence and max_val >= effective_threshold:
            best_confidence = max_val
            x1 = max_loc[0]
            y1 = max_loc[1]
            x2 = x1 + scaled_template.shape[1]
            y2 = y1 + scaled_template.shape[0]
            best_match = (x1, y1, x2, y2, max_val)
    
    return best_match


def match_template_multi_scale_all_matches(
    image: np.ndarray,
    template: np.ndarray,
    threshold: float = DEFAULT_THRESHOLD,
    scales: List[float] = None,
    min_distance: int = 10,
    zone_name: Optional[str] = None,
    brand: Optional[str] = None
) -> List[Tuple[int, int, int, int, float]]:
    """Match template with multi-scale approach and return ALL matches above threshold.
    
    This is useful when the same logo appears multiple times (e.g., in a leaderboard).
    
    Args:
        image: Grayscale image to search in
        template: Grayscale template to find
        threshold: Minimum match confidence (0-1)
        scales: List of scales to try (default: adaptive based on template size)
        min_distance: Minimum distance between matches in pixels (to avoid duplicates)
    
    Returns:
        List of (x1, y1, x2, y2, confidence) matches, sorted by confidence (highest first)
    """
    if scales is None:
        # Adaptive scales based on template size
        template_size = min(template.shape[0], template.shape[1])
        # For Lancia and Citroen, use more scales to catch smaller variations
        is_difficult_brand = brand and brand.lower() in DIFFICULT_MATCH_BRANDS
        
        if template_size > 200:
            scales = [0.5, 0.7, 1.0, 1.5, 2.0, 2.5, 3.0]
        elif template_size > 100:
            scales = [0.6, 0.8, 1.0, 1.2, 1.5, 2.0]
        elif template_size > 50:
            if is_difficult_brand:
                scales = [0.25, 0.3, 0.4, 0.5, 0.6, 0.75, 0.8, 1.0, 1.2, 1.5]  # More scales for Lancia/Citroen
            else:
                scales = [0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5]
        else:
            if is_difficult_brand:
                scales = [0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.75, 0.8, 1.0, 1.2, 1.5, 2.0]  # More scales for Lancia/Citroen
            else:
                scales = [0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5, 2.0]
    
    all_matches = []
    
    # Brand-specific threshold adjustments
    # Ford tends to have more false positives, so use higher threshold
    # Lancia and Citroen can be harder to detect, so use lower threshold
    # Toyota logos in TV graphics can be slightly harder to match reliably,
    # so we allow a mildly lower threshold for them as well.
    brand_threshold_adjustment = _brand_match_threshold_adjust(brand)
    adjusted_threshold = threshold + brand_threshold_adjustment
    # Lancia / Citroen / Toyota: lower bar on small scaled templates
    if brand and brand.lower() == "lancia":
        threshold_small = max(0.28, adjusted_threshold - 0.28)
        threshold_medium = max(0.34, adjusted_threshold - 0.22)
    elif brand and brand.lower() in SMALL_MATCH_BRANDS:
        threshold_small = max(0.32, adjusted_threshold - 0.22)
        threshold_medium = max(0.38, adjusted_threshold - 0.18)
    elif brand and brand.lower() in DIFFICULT_MATCH_BRANDS:
        threshold_small = max(0.35, adjusted_threshold - 0.2)
        threshold_medium = max(0.40, adjusted_threshold - 0.15)
    else:
        threshold_small = max(0.4, adjusted_threshold - 0.15)
        threshold_medium = max(0.45, adjusted_threshold - 0.1)
    
    for scale in scales:
        # Resize template
        if scale != 1.0:
            width = int(template.shape[1] * scale)
            height = int(template.shape[0] * scale)
            if width < 10 or height < 10:
                continue
            interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
            scaled_template = cv2.resize(template, (width, height), interpolation=interpolation)
        else:
            scaled_template = template
        
        # Validate that template is not larger than image
        if scaled_template.shape[0] > image.shape[0] or scaled_template.shape[1] > image.shape[1]:
            continue
        
        # Template matching
        result = cv2.matchTemplate(image, scaled_template, cv2.TM_CCOEFF_NORMED)
        
        # Adaptive threshold - but be more conservative to avoid too many false positives
        scaled_size = min(scaled_template.shape[0], scaled_template.shape[1])
        # Use adaptive threshold only for very small templates, otherwise use the main threshold
        # This makes behavior more consistent across different brand templates
        if scaled_size < 20:  # Very small templates only
            effective_threshold = threshold_small
        elif scaled_size < 35:  # Small templates
            effective_threshold = threshold_medium
        else:
            effective_threshold = adjusted_threshold  # Use brand-adjusted threshold
        
        # Find matches above threshold - use a smarter approach
        # For leaderboard zones, use vertical distance; for others, use euclidean distance
        is_leaderboard_zone = zone_name in ["left_column", "right_column"]
        
        # Find all pixels above threshold
        locations = np.where(result >= effective_threshold)
        
        # Store matches with non-maximum suppression per scale
        scale_matches = []
        # Sort by confidence (highest first) to process best matches first
        candidates = []
        for y, x in zip(locations[0], locations[1]):
            conf = result[y, x]
            candidates.append((conf, x, y))
        
        candidates.sort(reverse=True)  # Highest confidence first
        
        # Keep only matches that are far enough from existing ones
        for conf, x, y in candidates:
            x1 = x
            y1 = y
            x2 = x1 + scaled_template.shape[1]
            y2 = y1 + scaled_template.shape[0]
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            box_height = y2 - y1
            
            # Check if too close to existing match
            too_close = False
            for existing in scale_matches:
                ex1, ey1, ex2, ey2, econf = existing
                ecenter_x = (ex1 + ex2) / 2
                ecenter_y = (ey1 + ey2) / 2
                ebox_height = ey2 - ey1
                
                if is_leaderboard_zone:
                    # For leaderboard: use vertical distance only
                    vertical_distance = abs(center_y - ecenter_y)
                    # If in different rows (vertical distance > box height), keep both
                    # For Ford, be more strict - require larger vertical distance
                    min_vertical_distance = max(box_height, ebox_height) * (1.5 if brand and brand.lower() == "ford" else 1.2)
                    if vertical_distance > min_vertical_distance:
                        continue  # Different rows, keep both
                    # If in same row and overlapping horizontally, it's a duplicate
                    horizontal_overlap = not (x2 < ex1 or x1 > ex2)
                    if horizontal_overlap:
                        too_close = True
                        break
                else:
                    # For other zones: use euclidean distance
                    distance = np.sqrt((center_x - ecenter_x)**2 + (center_y - ecenter_y)**2)
                    # For Ford, require larger minimum distance
                    base_min_dist = max(5, min(scaled_template.shape[0], scaled_template.shape[1]) // 2)
                    if brand and brand.lower() in SMALL_MATCH_BRANDS:
                        base_min_dist = max(3, base_min_dist * 2 // 3)
                    min_dist = base_min_dist * (1.5 if brand and brand.lower() == "ford" else 1.0)
                    if distance < min_dist:
                        too_close = True
                        break
            
            if not too_close:
                scale_matches.append((x1, y1, x2, y2, float(conf)))
        
        # For each scale, keep only non-overlapping matches (IoU < 0.5)
        # This prevents finding the same logo multiple times at the same scale
        scale_filtered = []
        for match in scale_matches:
            x1, y1, x2, y2, conf = match
            overlap = False
            for existing in scale_filtered:
                ex1, ey1, ex2, ey2, econf = existing
                # Calculate IoU
                inter_x1 = max(x1, ex1)
                inter_y1 = max(y1, ey1)
                inter_x2 = min(x2, ex2)
                inter_y2 = min(y2, ey2)
                if inter_x2 > inter_x1 and inter_y2 > inter_y1:
                    inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
                    box1_area = (x2 - x1) * (y2 - y1)
                    box2_area = (ex2 - ex1) * (ey2 - ey1)
                    union_area = box1_area + box2_area - inter_area
                    if union_area > 0:
                        iou = inter_area / union_area
                        if iou > 0.5:  # Same detection at this scale
                            overlap = True
                            if conf > econf:
                                scale_filtered.remove(existing)
                                scale_filtered.append(match)
                            break
            if not overlap:
                scale_filtered.append(match)
        
        all_matches.extend(scale_filtered)
    
    if not all_matches:
        return []
    
    # Sort by confidence (highest first)
    all_matches.sort(key=lambda x: x[4], reverse=True)
    
    # Remove duplicates that are too close (same detection at different scales)
    # Use IoU-based deduplication for better accuracy
    filtered_matches = []
    for match in all_matches:
        x1, y1, x2, y2, conf = match
        
        # Check if this match overlaps significantly with an existing one
        too_close = False
        for existing in filtered_matches:
            ex1, ey1, ex2, ey2, econf = existing
            
            # Calculate IoU (Intersection over Union)
            inter_x1 = max(x1, ex1)
            inter_y1 = max(y1, ey1)
            inter_x2 = min(x2, ex2)
            inter_y2 = min(y2, ey2)
            
            if inter_x2 > inter_x1 and inter_y2 > inter_y1:
                inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
                box1_area = (x2 - x1) * (y2 - y1)
                box2_area = (ex2 - ex1) * (ey2 - ey1)
                union_area = box1_area + box2_area - inter_area
                
                if union_area > 0:
                    iou = inter_area / union_area
                    # If IoU > 0.5, they're the same detection (from different scales)
                    # Use 0.5 threshold to catch duplicates from different scales but allow nearby logos
                    # Keep the one with higher confidence
                    if iou > 0.5:
                        too_close = True
                        # Replace if current has higher confidence
                        if conf > econf:
                            filtered_matches.remove(existing)
                            filtered_matches.append(match)
                        break
        
        if not too_close:
            filtered_matches.append(match)
    
    return filtered_matches


def detect_erc_in_region(
    image_path: Path,
    templates: List[Tuple[Path, np.ndarray, str, str, Optional[str]]],
    threshold: float = DEFAULT_THRESHOLD,
    region_only: bool = False,
    brand_mapping: Dict[str, str] = None,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    nms_iou_threshold: float = DEFAULT_NMS_IOU_THRESHOLD,
    min_detection_size: int = DEFAULT_MIN_DETECTION_SIZE,
    debug_match: bool = False,
) -> List[Tuple[int, int, int, int, float, str, str, str]]:
    """Detect logos in image using template matching with zone-based search.
    
    If a template has a zone assigned (via folder structure), it will only be searched
    in that specific zone. Otherwise, it searches the full image.
    
    Args:
        image_path: Path to image file
        templates: List of (template_path, template_image, brand, location, zone) tuples
        threshold: Minimum match confidence
        region_only: If True, only search in bottom-left region (legacy mode)
        brand_mapping: Optional brand to location mapping (for fallback)
    
    Returns:
        List of (x1, y1, x2, y2, confidence, template_name, brand, location) detections
    """
    # Load image in grayscale (faster than color)
    # Use IMREAD_GRAYSCALE for better performance
    image_raw = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image_raw is None:
        return []  # Don't print in parallel mode to avoid output conflicts

    image = _preprocess_grayscale(image_raw)
    height, width = image_raw.shape
    detections = []
    
    # ERC: only templates in ERC_ACTIVE_ZONES (ignore other folders / no-zone templates)
    templates_with_zones = [
        (tp, t, b, l, z) for tp, t, b, l, z in templates
        if z is not None and z in ERC_ACTIVE_ZONES
    ]
    templates_without_zones = [
        (tp, t, b, l, z) for tp, t, b, l, z in templates
        if z is None or z not in ERC_ACTIVE_ZONES
    ]
    
    def _process_template_in_zone(
        template_path: Path,
        template: np.ndarray,
        brand: str,
        location: str,
        zone_name: str
    ) -> None:
        """Process a single template restricted to a screen zone (adds to outer `detections`)."""
        if zone_name not in SCREEN_ZONES:
            return
        if zone_name == ERC_ONLY_ZONE and (not brand or brand.lower() != "erc"):
            return

        zone = SCREEN_ZONES[zone_name]
        x_start = int(zone['x_start'] * width)
        x_end = int(zone['x_end'] * width)
        y_start = int(zone['y_start'] * height)
        y_end = int(zone['y_end'] * height)
        if (
            zone_name in STANDARD_LOGO_ZONES
            and brand
            and brand.lower() in SMALL_MATCH_BRANDS
        ):
            x_start, x_end, y_start, y_end = _expand_zone_pixel_bounds(
                x_start, x_end, y_start, y_end, width, height
            )

        # temporal_median frames + templates: both use same contrast/sharpen preprocessing
        region = image[y_start:y_end, x_start:x_end]
        if region.size == 0:
            return

        zone_scales = _scales_for_small_brand_match(region, template, brand)
        matches = match_template_multi_scale_all_matches(
            region,
            template,
            threshold,
            scales=zone_scales,
            zone_name=zone_name,
            brand=brand,
        )
        if (
            not matches
            and brand
            and brand.lower() == "lancia"
        ):
            retry_thresh = max(
                LANCIA_RETRY_THRESHOLD,
                threshold + _brand_match_threshold_adjust(brand) - 0.12,
            )
            matches = match_template_multi_scale_all_matches(
                region,
                template,
                retry_thresh,
                scales=zone_scales,
                zone_name=zone_name,
                brand=brand,
            )
        if not matches and brand and brand.lower() in SMALL_MATCH_BRANDS:
            matches = _fallback_minmax_match(
                region, template, zone_scales or [1.0], brand, threshold
            )
        if ERC_BEST_MATCH_PER_TEMPLATE and matches:
            matches = [max(matches, key=lambda m: m[4])]

        zone_min_size = ZONE_MIN_DETECTION_SIZES.get(zone_name, min_detection_size)
        if brand:
            brand_min_size = BRAND_MIN_DETECTION_SIZES.get(brand.lower())
            if brand_min_size is not None:
                zone_min_size = min(zone_min_size, brand_min_size)

        if debug_match:
            debug_scales = zone_scales or [1.0]
            peak = _peak_template_score(region, template, debug_scales)
            eff = threshold + _brand_match_threshold_adjust(brand)
            print(
                f"   🔬 {image_path.name} {brand}/{template_path.name}: "
                f"peak={peak:.3f} (match≥{eff:.2f} @ {len(debug_scales)} scales) "
                f"region={region.shape[1]}×{region.shape[0]} "
                f"template={template.shape[1]}×{template.shape[0]}"
            )
            if matches:
                bx1, by1, bx2, by2, bconf = max(matches, key=lambda m: m[4])
                gx1, gy1 = bx1 + x_start, by1 + y_start
                gx2, gy2 = bx2 + x_start, by2 + y_start
                reason = _erc_detection_reject_reason(
                    gx1, gy1, gx2, gy2, width, height, zone_name, zone_min_size, brand
                )
                if reason:
                    print(f"      ↳ match conf={bconf:.3f} but rejected: {reason}")
                else:
                    print(f"      ↳ match conf={bconf:.3f} → kept")
            elif peak >= threshold:
                print("      ↳ peak OK but matchTemplate returned nothing (check scales)")

        # Debug: detailed info for Toyota in bottom_right to understand misses
        if brand and brand.lower() == "toyota" and zone_name == "bottom_right":
            if matches:
                best_match = max(matches, key=lambda m: m[4])
                bx1, by1, bx2, by2, bconf = best_match
                bwidth = bx2 - bx1
                bheight = by2 - by1
                print(
                    f"   🔍 Toyota raw matches in bottom_right: {len(matches)} "
                    f"(best_conf={bconf:.3f}, size={bwidth}x{bheight}, "
                    f"threshold={threshold:.2f})"
                )
            else:
                print(
                    f"   ⚠️ Toyota: no raw matches in bottom_right zone "
                    f"(threshold={threshold:.2f})"
                )
        
        # Debug: small brands with no raw matches
        if brand and brand.lower() in SMALL_MATCH_BRANDS and not matches:
            print(f"   ⚠️ {brand}: No matches in {zone_name} zone (threshold={threshold:.2f})")
        
        # Use the same simple logic for all zones (including bottom_right):
        # Just check minimum size, same as leaderboard zones (left_column/right_column)
        for match in matches:
            x1, y1, x2, y2, conf = match
            x1 += x_start
            y1 += y_start
            x2 += x_start
            y2 += y_start
            
            det_width = x2 - x1
            det_height = y2 - y1
            det_size = max(det_width, det_height)
            
            if det_size < zone_min_size:
                continue
            min_zone_overlap = ERC_DETECTION_MIN_ZONE_OVERLAP
            if brand and brand.lower() in SMALL_MATCH_BRANDS:
                min_zone_overlap = ERC_DETECTION_MIN_ZONE_OVERLAP_SMALL
            if box_overlap_fraction_in_zone(
                x1, y1, x2, y2, zone_name, width, height
            ) < min_zone_overlap:
                continue
            if not is_valid_erc_json_detection(
                x1, y1, x2, y2, width, height, brand=brand, template_zone=zone_name
            ):
                continue
            detections.append((x1, y1, x2, y2, conf, template_path.name, brand, location, zone_name))
    
    # Group templates by zone; process only ERC_ACTIVE_ZONES in fixed order.
    templates_by_zone: Dict[str, List[Tuple[Path, np.ndarray, str, str, Optional[str]]]] = {}
    for tp, t, b, l, z in templates_with_zones:
        templates_by_zone.setdefault(z, []).append((tp, t, b, l, z))

    def _erc_brand_pass_order(brand: Optional[str]) -> Tuple[int, str]:
        b = (brand or "").lower()
        if b in DIFFICULT_MATCH_BRANDS:
            return (0, b)
        if b in TIRE_BRANDS:
            tire_order = ["pirelli", "michelin", "mrf tyres", "hankook"]
            return (1, str(tire_order.index(b) if b in tire_order else 99))
        return (2, b)

    for zone_name in ERC_ACTIVE_ZONES:
        zone_templates = templates_by_zone.get(zone_name, [])
        if not zone_templates:
            continue
        if zone_name == ERC_ONLY_ZONE:
            zone_templates = [
                t for t in zone_templates if t[2] and t[2].lower() == "erc"
            ]
        else:
            zone_templates = sorted(zone_templates, key=lambda t: _erc_brand_pass_order(t[2]))
        for template_path, template, brand, location, _ in zone_templates:
            if zone_name == ERC_ONLY_ZONE and (not brand or brand.lower() != "erc"):
                continue
            _process_template_in_zone(template_path, template, brand, location, zone_name)
    
    # Legacy region_only: keep only bottom_left_driver zone
    if region_only:
        detections = [
            det for det in detections
            if detection_center_zone(det[0], det[1], det[2], det[3], width, height) == "bottom_left_driver"
        ]
    
    # Filter by minimum confidence (use brand-specific minimum if available)
    filtered_by_confidence = []
    height, width = image.shape
    for det in detections:
        x1, y1, x2, y2, conf, name, brand, location = det[:8]
        brand_min_conf = BRAND_MIN_CONFIDENCE.get(brand.lower() if brand else None, min_confidence)
        if conf < brand_min_conf:
            continue
        if not is_valid_erc_json_detection(
            x1, y1, x2, y2, width, height,
            brand=brand, template_zone=_detection_zone(det),
        ):
            continue
        filtered_by_confidence.append(det)
    
    detections = filtered_by_confidence
    
    if not detections:
        return []
    
    max_size = max(width, height) * MAX_DETECTION_SIZE_RATIO
    filtered_by_size = []
    for det in detections:
        x1, y1, x2, y2, conf, name, brand, location = det[:8]
        det_size = max(x2 - x1, y2 - y1)
        if det_size <= max_size:
            filtered_by_size.append(det)
    
    detections = filtered_by_size
    
    if not detections:
        return []

    detections = [d for d in detections if _brand_allowed(d[6])]
    detections = consolidate_zone_detections(detections, width, height)
    detections = finalize_image_detections(detections)
    
    # Sort by confidence (highest first)
    detections.sort(key=lambda x: x[4], reverse=True)
    
    # Non-Maximum Suppression (NMS) - remove overlapping detections
    # But keep detections that are in different rows (for leaderboard logos)
    if len(detections) > 1:
        filtered = []
        for det in detections:
            x1, y1, x2, y2, conf, name, brand, location = det[:8]
            det_height = y2 - y1
            det_center_y = (y1 + y2) / 2
            
            # Check overlap with existing detections
            overlap = False
            for existing in filtered:
                ex1, ey1, ex2, ey2, econf, _, ebrand, _ = existing[:8]
                
                # Car + tire logos side-by-side: only suppress same brand
                if brand != ebrand:
                    continue
                
                # Check if detections are in different rows (vertical distance > box height)
                # This is important for leaderboard logos that appear multiple times
                existing_center_y = (ey1 + ey2) / 2
                existing_height = ey2 - ey1
                vertical_distance = abs(det_center_y - existing_center_y)
                
                # If vertical distance is large enough, they're in different rows - ALWAYS keep both
                # Use the larger of the two heights for comparison
                max_height = max(det_height, existing_height)
                if vertical_distance > max_height * 1.2:  # 20% margin for safety
                    continue  # Different rows, keep both
                
                # Calculate IoU (Intersection over Union) only if in similar row
                inter_x1 = max(x1, ex1)
                inter_y1 = max(y1, ey1)
                inter_x2 = min(x2, ex2)
                inter_y2 = min(y2, ey2)
                
                if inter_x2 > inter_x1 and inter_y2 > inter_y1:
                    inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
                    box1_area = (x2 - x1) * (y2 - y1)
                    box2_area = (ex2 - ex1) * (ey2 - ey1)
                    union_area = box1_area + box2_area - inter_area
                    
                    if union_area > 0:
                        iou = inter_area / union_area
                        
                        # Only suppress if significant overlap AND in similar row
                        # For leaderboard, logos in different rows should never be suppressed
                        if iou > nms_iou_threshold:
                            overlap = True
                            # If current detection has higher confidence, replace existing
                            if conf > econf:
                                filtered.remove(existing)
                                filtered.append(det)
                            break
            
            if not overlap:
                filtered.append(det)
        
        detections = filtered
    
    return detections


def visualize_zones(
    image_path: Path,
    output_path: Path,
    zones_to_show: List[str] = None
) -> None:
    """Draw zone rectangles on image to visualize search areas."""
    # Load image
    image = cv2.imread(str(image_path))
    if image is None:
        return
    
    height, width = image.shape[:2]
    
    # Convert to PIL for easier drawing
    pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_image)
    
    zone_colors = {
        "bottom_right": "blue",
        "bottom_right_up_ad": "cyan",
        "bottom_left_driver": "green",
    }
    
    if zones_to_show is None:
        zones_to_show = list(ERC_ACTIVE_ZONES)
    
    # Draw each zone
    for zone_name in zones_to_show:
        if zone_name not in SCREEN_ZONES:
            continue
        
        zone = SCREEN_ZONES[zone_name]
        x_start = int(zone['x_start'] * width)
        x_end = int(zone['x_end'] * width)
        y_start = int(zone['y_start'] * height)
        y_end = int(zone['y_end'] * height)
        
        color = zone_colors.get(zone_name, "white")
        
        # Draw rectangle
        draw.rectangle(
            [(x_start, y_start), (x_end, y_end)],
            outline=color,
            width=3
        )
        
        # Draw label
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        draw.text(
            (x_start + 5, y_start + 5),
            f"{zone_name}",
            fill=color,
            font=font
        )
    
    # Save
    pil_image.save(output_path)
    print(f"   📊 Zone visualization saved: {output_path}")


def annotate_image(
    image_path: Path,
    detections: List[Tuple[int, int, int, int, float, str, str, str]],
    output_path: Path
) -> None:
    """Draw bounding boxes on image and save annotated version."""
    # Load image in color
    image = cv2.imread(str(image_path))
    if image is None:
        return
    
    # Draw bounding boxes
    for det in detections:
        x1, y1, x2, y2, conf, template_name, brand, location = det[:8]
        # Draw rectangle
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 3)
        
        # Draw label
        label = f"{brand or '?'} {conf:.2f}"
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        label_y = max(y1, label_size[1] + 10)
        cv2.rectangle(image, (x1, label_y - label_size[1] - 10), 
                     (x1 + label_size[0], label_y + 5), (0, 255, 0), -1)
        cv2.putText(image, label, (x1, label_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    
    # Save annotated image
    cv2.imwrite(str(output_path), image)


def load_brand_mapping(mapping_file: Path) -> Dict[str, str]:
    """Load brand to location mapping from config file.
    
    Format: Brand:Location or Brand:Location:Hits (one per line)
    Example:
        ERC:TVGI
        Ford:TVGI
        Ford:TVGI:3
    
    Args:
        mapping_file: Path to mapping file
    
    Returns:
        Dict mapping brand_name -> location_name
    """
    mapping = {}
    if not mapping_file.exists():
        return mapping
    
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Parse Brand:Location or Brand:Location:Hits format
                if ':' in line:
                    parts = line.split(':')
                    brand = parts[0].strip()
                    location = parts[1].strip() if len(parts) > 1 else None
                    # Ignore hits part (parts[2]) if present - it's just for documentation
                    if brand and location:
                        mapping[brand] = location
    except Exception as e:
        print(f"⚠️  Warning: Failed to load brand mapping from {mapping_file}: {e}")
    
    return mapping


def extract_brand_from_filename(filename: str) -> str:
    """Extract brand name from template filename.
    
    Examples:
        Ford_colored_leaderboard.png -> Ford
        Ford_white_leaderboard.png -> Ford
        Ford_driver.png -> Ford
        erc_logo_basic.png -> ERC
        toyota_leaderboard.png -> Toyota
    
    Args:
        filename: Template filename
    
    Returns:
        Brand name (capitalized)
    """
    # Remove extension
    name = Path(filename).stem
    
    # Common patterns:
    # - {brand}_{variant}.png -> {brand}
    # - {brand}_{location}.png -> {brand}
    
    # Split by underscore and take first part
    parts = name.split('_')
    if parts:
        brand = parts[0]
        # Capitalize first letter
        return brand.capitalize()
    
    # Fallback: return filename without extension
    return name


def create_json_output(
    images_data: Dict[str, Dict[str, Any]],
    folder_name: str = "template_matching",
    group_name: str = "template_match",
    target_brands: List[str] = None
) -> Dict[str, Any]:
    """Create JSON output in the same format as detect_brands_v2.py
    
    Args:
        images_data: Dict mapping image_name -> {
            'image_path': Path,
            'width': int,
            'height': int,
            'annotations': List[Dict with startPoint, diagPoint, brand, tpoint, etc]
        }
        folder_name: Name for project/folder
        group_name: Group name for annotations
        target_brands: List of brand names detected
    
    Returns:
        JSON structure matching detect_brands_v2.py format
    """
    if target_brands is None:
        target_brands = []
    
    # Collect all unique brands from annotations
    all_brands = set(target_brands)
    for img_data in images_data.values():
        for ann in img_data.get('annotations', []):
            all_brands.add(ann.get('brand', 'ERC'))
    all_brands = sorted(list(all_brands))
    
    # Build images dict (format: imageName, imageIndex, width, height, annotations)
    images_dict = {}
    for image_name, img_data in images_data.items():
        orig_w = int(img_data.get("width", 1920))
        orig_h = int(img_data.get("height", 1080))
        json_width, json_height = get_annotool_canvas_size(orig_w, orig_h)
        try:
            numbers = re.findall(r'\d+', image_name)
            if numbers:
                image_index = int(max(numbers, key=len))
            else:
                image_index = 1
        except Exception:
            image_index = 1

        annotations = img_data.get("annotations", [])
        for ann in annotations:
            sp = ann["startPoint"]
            dp = ann["diagPoint"]
            sp[0] = max(0.0, min(float(json_width) - 0.01, float(sp[0])))
            sp[1] = max(0.0, min(float(json_height) - 0.01, float(sp[1])))
            dp[0] = max(0.0, min(float(json_width), float(dp[0])))
            dp[1] = max(0.0, min(float(json_height), float(dp[1])))
            if dp[0] <= sp[0]:
                dp[0] = min(float(json_width), sp[0] + 1.0)
            if dp[1] <= sp[1]:
                dp[1] = min(float(json_height), sp[1] + 1.0)

        images_dict[image_name] = {
            "imageName": image_name,
            "imageIndex": image_index,
            "width": json_width,
            "height": json_height,
            "annotations": annotations,
            "exifdata": {}
        }
    
    # Create JSON structure
    json_output = {
        "project": folder_name,
        "imageNum": 0,  # Will be set based on images
        "prefs": {
            "projectName": folder_name,
            "AnnotatorName": "Template Matching",
            "groups": [group_name],
            "brands": all_brands,
            "tpoints": ["Bottom Left Corner", "Top Left Graphic", "Middle Right Banner"],
            "prefsFilename": "erc_templates.txt",
            "imgFoldername": folder_name,
            "userAdds": {},
            "conns": {
                f"{group_name}__{brand}": {
                    "brand": brand,
                    "tpoints": ["Bottom Left Corner", "Top Left Graphic", "Middle Right Banner"],
                    "group": group_name
                }
                for brand in all_brands
            },
            "seelater": []
        },
        "images": images_dict,
        "end": [],
        "Annotator": "Template Matching"
    }
    
    return json_output


def scale_coordinates(
    x1: int, y1: int, x2: int, y2: int,
    orig_width: int, orig_height: int,
    target_width: Optional[float] = None,
    target_height: Optional[float] = None,
) -> Tuple[float, float, float, float]:
    """Scale coordinates from original image pixels to annotool canvas space."""
    if target_width is None or target_height is None:
        target_width, target_height = get_annotool_canvas_size(orig_width, orig_height)
    scale_x = target_width / orig_width
    scale_y = target_height / orig_height

    scaled_x1 = x1 * scale_x
    scaled_y1 = y1 * scale_y
    scaled_x2 = x2 * scale_x
    scaled_y2 = y2 * scale_y

    scaled_x1 = max(0.0, min(target_width, scaled_x1))
    scaled_y1 = max(0.0, min(target_height, scaled_y1))
    scaled_x2 = max(0.0, min(target_width, scaled_x2))
    scaled_y2 = max(0.0, min(target_height, scaled_y2))

    if scaled_x2 <= scaled_x1:
        scaled_x2 = scaled_x1 + 1.0
    if scaled_y2 <= scaled_y1:
        scaled_y2 = scaled_y1 + 1.0

    return scaled_x1, scaled_y1, scaled_x2, scaled_y2


def find_temporal_median_folders(root_dir: Path) -> list[Path]:
    """Find all subfolders ending with '_temporal_median' recursively."""
    temporal_median_folders = []
    for path in root_dir.rglob("*"):
        if path.is_dir() and path.name.endswith("_temporal_median"):
            temporal_median_folders.append(path)
    return sorted(temporal_median_folders)


def find_non_median_reduced_folders(root_dir: Path) -> list[Path]:
    """Find all 'reduced_*' subfolders that do NOT end with '_temporal_median' recursively."""
    reduced_folders = []
    for path in root_dir.rglob("*"):
        if path.is_dir() and path.name.startswith("reduced_") and not path.name.endswith("_temporal_median"):
            reduced_folders.append(path)
    return sorted(reduced_folders)


def process_single_folder(image_folder: Path, args, templates, brand_mapping, script_dir, output_dir) -> int:
    """Process a single image folder and return exit code."""
    if not image_folder.exists():
        print(f"❌ Image folder not found: {image_folder}")
        return 1
    
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
    images = [f for f in image_folder.iterdir() 
              if f.suffix.lower() in image_extensions and f.is_file()]
    
    if not images:
        print(f"❌ No images found in: {image_folder}")
        return 1
    
    # Determine number of workers
    if args.workers is None:
        import os
        num_workers = min(len(images), os.cpu_count() or 4, 8)  # Cap at 8 to avoid too many threads
    else:
        num_workers = max(1, min(args.workers, len(images)))
    
    print(f"\n🔍 Processing {len(images)} image(s) in {image_folder.name}...")
    print(f"   Threshold: {args.threshold}")
    print(f"   Min Confidence: {args.min_confidence}")
    print(f"   NMS IoU: {args.nms_iou}")
    print(f"   Min Size: {args.min_size}px")
    print(f"   Region-only: {args.region_only}")
    print(f"   Workers: {num_workers}")
    print()
    
    # Process images and collect data for JSON
    images_data = {}
    total_detections = 0
    
    # Process images in parallel
    start_time = time.time()
    
    def process_single_image(image_path: Path, visualize_zones_flag: bool = False) -> Tuple[Path, Dict[str, Any], List, int]:
        """Process a single image and return results."""
        try:
            # Get image dimensions
            image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
            if image is None:
                return image_path, None, [], 0
            
            orig_height, orig_width = image.shape[:2]
            
            detections = detect_erc_in_region(
                image_path, templates, args.threshold, args.region_only, brand_mapping,
                args.min_confidence, args.nms_iou, args.min_size,
                debug_match=getattr(args, "debug_match", False),
            )
            
            image_name = image_path.stem
            annotations = []
            detection_count = 0
            
            if detections:
                filtered_detections = []
                canvas_w, canvas_h = get_annotool_canvas_size(orig_width, orig_height)
                for det in detections:
                    x1, y1, x2, y2, conf, template_name, brand, location = det[:8]
                    if not is_valid_erc_json_detection(
                        x1, y1, x2, y2, orig_width, orig_height,
                        brand=brand, template_zone=_detection_zone(det),
                    ):
                        continue
                    scaled_x1, scaled_y1, scaled_x2, scaled_y2 = scale_coordinates(
                        x1, y1, x2, y2, orig_width, orig_height,
                        target_width=canvas_w, target_height=canvas_h,
                    )
                    start_pt = [float(scaled_x1), float(scaled_y1)]
                    diag_pt = [float(scaled_x2), float(scaled_y2)]
                    out_reject = _output_filter_reject_reason(
                        conf, brand, start_pt, diag_pt, canvas_w, canvas_h
                    )
                    if out_reject:
                        if getattr(args, "debug_match", False):
                            print(
                                f"      ↳ JSON drop {brand} conf={conf:.3f}: {out_reject}"
                            )
                        continue
                    annotation = {
                        "startPoint": start_pt,
                        "diagPoint": diag_pt,
                        "group": "template_match",
                        "brand": brand,
                        "tpoint": location,
                        "hits": 1,
                        "confidence": round(float(conf), 4),
                    }
                    annotations.append(annotation)
                    filtered_detections.append(det)
                    detection_count += 1

                if detection_count == 0:
                    zones = sorted(LOADED_TEMPLATE_ZONES or ERC_ACTIVE_ZONES)
                    print(
                        f"❌ {image_path.name}: Matches filtered out "
                        f"(try --threshold 0.55; zones: {zones})"
                    )
                else:
                    brands_found = {}
                    for ann in annotations:
                        b = ann.get("brand", "Unknown")
                        brands_found[b] = brands_found.get(b, 0) + 1
                    brand_summary = ", ".join(
                        f"{b}({n})" for b, n in sorted(brands_found.items())
                    )
                    print(
                        f"✅ {image_path.name}: {detection_count} annotation(s) → {brand_summary}"
                    )
                
                # Annotate image if requested
                if args.annotate:
                    annotate_image(image_path, filtered_detections, output_dir / f"annotated_{image_path.name}")
                    print(f"   💾 Annotated image saved: {output_dir / f'annotated_{image_path.name}'}")
            else:
                zones = sorted(LOADED_TEMPLATE_ZONES or ERC_ACTIVE_ZONES)
                print(
                    f"❌ {image_path.name}: No match in zone(s) {zones} "
                    f"(threshold={args.threshold}; try --threshold 0.55 --visualize-zones)"
                )

            if visualize_zones_flag:
                zone_viz_path = output_dir / f"zones_{image_path.name}"
                visualize_zones(
                    image_path, zone_viz_path, zones_to_show=list(ERC_ACTIVE_ZONES)
                )
                print(f"   💾 Zone visualization saved: {zone_viz_path}")
            
            if not annotations:
                return image_path, None, [], 0

            image_data = {
                'image_path': image_path,
                'width': orig_width,
                'height': orig_height,
                'annotations': annotations
            }
            
            return image_path, image_data, detections, detection_count
            
        except Exception as e:
            print(f"⚠️  Error processing {image_path.name}: {e}")
            return image_path, None, [], 0
    
    # Process images in parallel
    if num_workers > 1 and len(images) > 1:
        print(f"🚀 Using {num_workers} parallel workers...\n")
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Submit all tasks
            future_to_image = {executor.submit(process_single_image, img, args.visualize_zones): img for img in images}
            
            # Collect results as they complete
            for future in as_completed(future_to_image):
                image_path, image_data, detections, detection_count = future.result()
                if image_data:
                    image_name = image_path.stem
                    images_data[image_name] = image_data
                    total_detections += detection_count
    else:
        # Sequential processing (for debugging or single image)
        for image_path in images:
            image_path, image_data, detections, detection_count = process_single_image(image_path, args.visualize_zones)
            if image_data:
                image_name = image_path.stem
                images_data[image_name] = image_data
                total_detections += detection_count
    
    # Collect all unique brands from annotations
    all_brands = set()
    for img_data in images_data.values():
        for ann in img_data.get('annotations', []):
            all_brands.add(ann.get('brand', 'ERC'))
    all_brands = sorted(list(all_brands))
    
    # Create JSON output
    folder_name = image_folder.name if hasattr(image_folder, 'name') else "template_matching"
    json_output = create_json_output(
        images_data,
        folder_name=folder_name,
        group_name="template_match",
        target_brands=all_brands
    )
    
    # Save JSON file
    timestamp = datetime.now().strftime("%H%M%S")
    json_filename = f"{folder_name}_ANNOTATIONS__{timestamp}.json"
    json_path = output_dir / json_filename
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)
    
    print(f"📊 Summary: {total_detections} ERC detection(s) in {len(images)} image(s)")
    print(f"📝 JSON output saved to: {json_path}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(description="ERC Template Matcher")
    parser.add_argument("image_folder", type=Path, help="Folder containing images")
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help=(
            f"Template matching threshold (default: {DEFAULT_THRESHOLD}; "
            f"{DEFAULT_THRESHOLD_ERC_ONLY} with --ERConly)"
        ),
    )
    parser.add_argument("--region-only", action="store_true",
                       help="Only search in bottom-left region")
    parser.add_argument("--templates-dir", type=Path, default=None,
                       help="Path to templates directory (default: ./erc_templates)")
    parser.add_argument("--output-dir", type=Path, default=None,
                       help="Path to output directory (default: ./erc_output)")
    parser.add_argument("--annotate", action="store_true",
                       help="Save annotated images with bounding boxes")
    parser.add_argument("--visualize-zones", action="store_true",
                       help="Save zone visualization images showing search areas")
    parser.add_argument("--workers", type=int, default=None,
                       help="Parallel workers: with --ERConly = folders in parallel (default 4); else = images per folder (default: auto)")
    parser.add_argument("--min-confidence", type=float, default=DEFAULT_MIN_CONFIDENCE,
                       help=f"Minimum confidence for detections (default: {DEFAULT_MIN_CONFIDENCE})")
    parser.add_argument("--nms-iou", type=float, default=DEFAULT_NMS_IOU_THRESHOLD,
                       help=f"NMS IoU threshold for overlap removal (default: {DEFAULT_NMS_IOU_THRESHOLD})")
    parser.add_argument("--min-size", type=int, default=DEFAULT_MIN_DETECTION_SIZE,
                       help=f"Minimum detection size in pixels (default: {DEFAULT_MIN_DETECTION_SIZE})")
    parser.add_argument(
        "--debug-match",
        action="store_true",
        help="Print peak template-match score per template in raw zones (e.g. bottom_left)",
    )
    parser.add_argument(
        "--ERConly", "--ERCOnly", action="store_true", dest="ERConly",
        help="Batch mode: process all subfolders ending with '_temporal_median' (same as WRC --WRConly)",
    )
    
    args = parser.parse_args()

    if args.threshold is None:
        args.threshold = (
            DEFAULT_THRESHOLD_ERC_ONLY if args.ERConly else DEFAULT_THRESHOLD
        )

    global ERC_ACTIVE_ZONES
    if args.ERConly:
        ERC_ACTIVE_ZONES = ("bottom_left",)
    else:
        ERC_ACTIVE_ZONES = ERC_ALL_ZONES

    # Setup paths
    script_dir = Path(__file__).parent
    templates_dir = args.templates_dir or (script_dir / "erc_templates")
    output_dir = args.output_dir or (script_dir / "erc_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load templates
    print(f"📁 Loading templates from: {templates_dir}")
    templates = load_templates(templates_dir)
    erc_templates = [t for t in templates if t[4] in ERC_ACTIVE_ZONES]
    ignored = len(templates) - len(erc_templates)
    if ignored:
        print(f"⚠️  Ignored {ignored} template(s) not under zones: {', '.join(ERC_ACTIVE_ZONES)}")
    templates = erc_templates

    global LOADED_TEMPLATE_BRANDS, LOADED_TEMPLATE_ZONES
    LOADED_TEMPLATE_BRANDS = frozenset(
        (t[2] or "").lower() for t in templates if t[2]
    )
    LOADED_TEMPLATE_ZONES = frozenset(
        z for z in (t[4] for t in templates) if z in ERC_ACTIVE_ZONES
    )
    
    if not templates:
        print(
            "❌ No templates found for active zone(s): "
            f"{', '.join(ERC_ACTIVE_ZONES)}."
        )
        if args.ERConly:
            print(
                "   --ERConly uses only bottom_left (ERC TVGI strip). "
                "Put templates under e.g. ERC Logos/bottom_left/TVGI/"
            )
        else:
            print(
                "   Without --ERConly, use zone folders that match SCREEN_ZONES, e.g. "
                "Ford Logos/bottom_right/TVGI-Driver/ (not a flat Location path)."
            )
        return 1
    
    cw, ch = get_annotool_canvas_size(1920, 1080)
    zones_searched = sorted(LOADED_TEMPLATE_ZONES or ERC_ACTIVE_ZONES)
    print(
        f"🎯 ERC zones (with templates): {', '.join(zones_searched)} "
        f"| active config: {', '.join(ERC_ACTIVE_ZONES)} "
        f"| match = preprocessed frames (temporal_median) "
        f"| JSON = annotool canvas (~{cw}×{ch} for 1080p)"
    )
    if "bottom_right" in ERC_ACTIVE_ZONES:
        print(
            f"   bottom_right: tire left / car right | conf≥{ERC_MIN_ANNOTATION_CONFIDENCE} "
            f"| csv%≥{ERC_MIN_CSV_PERCENT} (small brands≥{ERC_MIN_CSV_PERCENT_DIFFICULT})"
        )
    print(f"   brands: {', '.join(sorted(LOADED_TEMPLATE_BRANDS))}")
    print(f"   {len(templates)} template file(s) loaded\n")
    
    # Load brand mapping (optional - now mainly used as fallback)
    mapping_file = script_dir / "erc_brand_mapping.txt"
    brand_mapping = load_brand_mapping(mapping_file)
    if brand_mapping:
        print(f"📋 Loaded brand mapping (fallback): {brand_mapping}")
    else:
        print(f"ℹ️  No erc_brand_mapping.txt found - using folder structure for brand/location detection")
    
    # Check for batch processing mode (--ERConly)
    if args.ERConly:
        root_folder = args.image_folder
        if not root_folder.exists():
            print(f"❌ Root folder not found: {root_folder}")
            return 1
        
        print(f"\n🔍 Batch mode: Searching for folders ending with '_temporal_median' in {root_folder}")
        temporal_median_folders = find_temporal_median_folders(root_folder)
        
        if not temporal_median_folders:
            print(f"❌ No folders ending with '_temporal_median' found in {root_folder}")
            return 1
        
        print(f"📁 Found {len(temporal_median_folders)} folder(s) to process:\n")
        for i, folder in enumerate(temporal_median_folders, 1):
            print(f"   {i}. {folder}")
        print()
        
        # Number of folders to process in parallel (--workers applies to folder-level when ERConly)
        import os
        folder_workers = args.workers if args.workers is not None else min(4, len(temporal_median_folders), os.cpu_count() or 4)
        folder_workers = max(1, min(folder_workers, len(temporal_median_folders)))
        print(f"🚀 Using {folder_workers} parallel worker(s) for folders.\n")
        
        total_folders = len(temporal_median_folders)
        failed_folders = []
        
        with ThreadPoolExecutor(max_workers=folder_workers) as executor:
            future_to_folder = {
                executor.submit(process_single_folder, folder, args, templates, brand_mapping, script_dir, output_dir): folder
                for folder in temporal_median_folders
            }
            for future in as_completed(future_to_folder):
                folder = future_to_folder[future]
                try:
                    exit_code = future.result()
                    if exit_code != 0:
                        failed_folders.append((folder.name, exit_code))
                except Exception as e:
                    failed_folders.append((folder.name, str(e)))
        
        if failed_folders:
            print(f"\n⚠️  {len(failed_folders)} folder(s) had issues:")
            for name, err in failed_folders:
                print(f"   - {name}: {err}")
        
        print(f"\n{'='*80}")
        print(f"✅ Batch processing complete! Processed {total_folders} folder(s).")
        print(f"{'='*80}\n")
        return 0
    
    # Single folder processing - check if root directory, then find non-median reduced folders
    image_folder = args.image_folder
    if not image_folder.exists():
        print(f"❌ Image folder not found: {image_folder}")
        return 1
    
    # Check if it's a root directory (contains subfolders with "reduced_" that don't end in "_temporal_median")
    non_median_folders = find_non_median_reduced_folders(image_folder)
    
    if non_median_folders:
        # Batch mode: process all non-median reduced folders
        print(f"\n🔍 Batch mode: Searching for 'reduced_*' folders (excluding '_temporal_median') in {image_folder}")
        print(f"📁 Found {len(non_median_folders)} folder(s) to process:\n")
        for i, folder in enumerate(non_median_folders, 1):
            print(f"   {i}. {folder}")
        print()
        
        # Number of folders to process in parallel
        import os
        folder_workers = args.workers if args.workers is not None else min(4, len(non_median_folders), os.cpu_count() or 4)
        folder_workers = max(1, min(folder_workers, len(non_median_folders)))
        print(f"🚀 Using {folder_workers} parallel worker(s) for folders.\n")
        
        total_folders = len(non_median_folders)
        failed_folders = []
        
        with ThreadPoolExecutor(max_workers=folder_workers) as executor:
            future_to_folder = {
                executor.submit(process_single_folder, folder, args, templates, brand_mapping, script_dir, output_dir): folder
                for folder in non_median_folders
            }
            for future in as_completed(future_to_folder):
                folder = future_to_folder[future]
                try:
                    exit_code = future.result()
                    if exit_code != 0:
                        failed_folders.append((folder.name, exit_code))
                except Exception as e:
                    failed_folders.append((folder.name, str(e)))
        
        if failed_folders:
            print(f"\n⚠️  {len(failed_folders)} folder(s) had issues:")
            for name, err in failed_folders:
                print(f"   - {name}: {err}")
        
        print(f"\n{'='*80}")
        print(f"✅ Batch processing complete! Processed {total_folders} folder(s).")
        print(f"{'='*80}\n")
        return 0
    
    # Without --ERConly, do not process folders ending with _temporal_median (use --ERConly for those)
    if image_folder.is_dir() and image_folder.name.endswith("_temporal_median"):
        print(f"❌ Without --ERConly, folders ending with '_temporal_median' are not processed. Use --ERConly to process median folders.")
        return 1
    
    # Original behavior: single folder processing
    return process_single_folder(image_folder, args, templates, brand_mapping, script_dir, output_dir)


if __name__ == "__main__":
    sys.exit(main())
