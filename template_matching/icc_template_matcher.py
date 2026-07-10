#!/usr/bin/env python3
"""
ICC Template Matcher - Template matching for ICC broadcast brand detection

Focuses on bottom-right corner region where sponsor logos appear (e.g. Emirates).
Uses the same multi-scale template matching as WRC; templates are loaded from
icc_templates/ with the same folder structure (Brand Logos / zone / location).

Usage:
    python icc_template_matcher.py <image_folder>
    python icc_template_matcher.py <image_folder> --threshold 0.6
    python icc_template_matcher.py <image_folder> --region-only
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
import threading
import time

# Default template matching threshold
# Increased to reduce false positives
DEFAULT_THRESHOLD = 0.70

# Minimum confidence for detections (stricter filtering)
DEFAULT_MIN_CONFIDENCE = 0.60

# Non-Maximum Suppression (NMS) IoU threshold
# Higher = more aggressive overlap removal (0.4 = remove if 40% overlap)
# Increased to 0.4 for better leaderboard logo detection (allows multiple instances in different rows)
DEFAULT_NMS_IOU_THRESHOLD = 0.4

# Minimum detection size (in pixels) - filter out tiny detections
DEFAULT_MIN_DETECTION_SIZE = 15

# ICC project: every detection is exactly 1 hit (no aggregation/counting)
ICC_ANNOTATION_HITS = 1

# Zone-specific minimum detection sizes (in pixels)
ZONE_MIN_DETECTION_SIZES = {
    "bottom_right": 12,  # Bottom-right sponsor logos (e.g. Emirates)
}

# Brand-specific minimum detection sizes (in pixels)
BRAND_MIN_DETECTION_SIZES = {}

# Brand-specific minimum confidence thresholds (lower = catch more, risk false positives)
# Add brands that need lower than default 0.70; also load from icc_brand_thresholds.txt in main()
BRAND_MIN_CONFIDENCE = {
    "aramco": 0.52,
    "emirates": 0.60,
    "dp world": 0.60,
}

# Maximum detection size ratio (relative to image) - filter out huge detections
# Increased to allow large center logos (like title cards)
MAX_DETECTION_SIZE_RATIO = 0.6  # 60% of image size (was 0.3)

# Screen Zones - Define regions where different logos appear
# Coordinates are relative (0.0-1.0) for flexibility across different image sizes
SCREEN_ZONES = {
    # Corner zones
    "bottom_left": {
        "x_start": 0.0854,
        "x_end": 0.1786,
        "y_start": 0.7741,
        "y_end": 0.8250,
        "description": "Bottom left corner"
    },
    "top_left": {
        "x_start": 0.0,
        "x_end": 0.3,
        "y_start": 0.0,
        "y_end": 0.3,
        "description": "Top left corner - Channel logos, small overlays"
    },
    "top_right": {
        "x_start": 0.7,
        "x_end": 1.0,
        "y_start": 0.0,
        "y_end": 0.3,
        "description": "Top right corner - Channel info, live indicators"
    },
    "bottom_right": {
        "x_start": 0.75,   # Bottom-right: sponsor logos (Emirates etc.)
        "x_end": 0.90,
        "y_start": 0.86,
        "y_end": 0.95,
        "description": "Bottom right corner - Sponsor logos (Emirates)"
    },
        "bottom_right_custom": {
        "x_start": 0.6309,
        "x_end": 0.7824,
        "y_start": 0.71,
        "y_end": 0.77,
        "description": "Custom picked zone"
    },
        "info": {
        "x_start": 0.6849,
        "x_end": 0.7714,
        "y_start": 0.7889,
        "y_end": 0.8278,
        "description": "Custom picked zone"
    },
    # Vertical column zones
    "left_column": {
        "x_start": 0.0,
        "x_end": 0.2,      # First 20% of width (narrow column)
        "y_start": 0.0,
        "y_end": 0.85,     # Stops before bottom-left corner (85% of height)
        "description": "Left vertical column - Leaderboard with driver names, car logos"
    },
    "scorecard": {
        "x_start": 0.4589,
        "x_end": 0.5437,
        "y_start": 0.9046,
        "y_end": 0.9546,
        "description": "scorecard"
    },
    # Middle regions
    "middle_left": {
        "x_start": 0.0,
        "x_end": 0.4,
        "y_start": 0.3,
        "y_end": 0.7,
        "description": "Middle left area"
    },
    "middle_right": {
        "x_start": 0.6,
        "x_end": 1.0,
        "y_start": 0.3,
        "y_end": 0.7,
        "description": "Middle right area - Rally info panel, split times"
    },
    "center": {
        "x_start": 0.3,
        "x_end": 0.7,
        "y_start": 0.3,
        "y_end": 0.7,
        "description": "Center area - Main action, sponsor banners"
    },
    # Full screen (fallback)
    "full_screen": {
        "x_start": 0.0,
        "x_end": 1.0,
        "y_start": 0.0,
        "y_end": 1.0,
        "description": "Full screen - Search everywhere (use as fallback)"
    }
}

# Legacy compatibility - keep old constants pointing to new zones
BOTTOM_LEFT_REGION = SCREEN_ZONES["bottom_left"]
TOP_LEFT_LEADERBOARD_REGION = SCREEN_ZONES["left_column"]


def load_templates(templates_dir: Path) -> List[Tuple[Path, np.ndarray, str, str, Optional[str]]]:
    """Load all template images from templates directory and subfolders.
    
    Supports zone-based folder structure (same as WRC):
        icc_templates/
        ├── Emirates Logos/
        │   └── bottom_right/         <- Zone folder
        │       └── Banner/           <- Location folder
        │           └── emirates.png
        └── ...
    
    Also supports flat Brand/Location or Brand/Zone without location subfolder.
    
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
                        # This is a zone folder - look for location subfolders inside
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
                                                template = cv2.convertScaleAbs(template, alpha=1.2, beta=10)
                                                gaussian = cv2.GaussianBlur(template, (0, 0), 2.0)
                                                template = cv2.addWeighted(template, 1.5, gaussian, -0.5, 0)
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
                                            template = cv2.convertScaleAbs(template, alpha=1.2, beta=10)
                                            gaussian = cv2.GaussianBlur(template, (0, 0), 2.0)
                                            template = cv2.addWeighted(template, 1.5, gaussian, -0.5, 0)
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
                                        template = cv2.convertScaleAbs(template, alpha=1.2, beta=10)
                                        gaussian = cv2.GaussianBlur(template, (0, 0), 2.0)
                                        template = cv2.addWeighted(template, 1.5, gaussian, -0.5, 0)
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
                                template = cv2.convertScaleAbs(template, alpha=1.2, beta=10)
                                gaussian = cv2.GaussianBlur(template, (0, 0), 2.0)
                                template = cv2.addWeighted(template, 1.5, gaussian, -0.5, 0)
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
                        brand_name = extract_brand_from_filename(template_path.name)
                        template = cv2.convertScaleAbs(template, alpha=1.2, beta=10)
                        gaussian = cv2.GaussianBlur(template, (0, 0), 2.0)
                        template = cv2.addWeighted(template, 1.5, gaussian, -0.5, 0)
                        location_name = "Unknown"
                        zone_name = None
                        templates.append((template_path, template, brand_name, location_name, zone_name))
                        print(f"✅ Loaded template: {template_path.name} ({template.shape[1]}x{template.shape[0]})")
                except Exception as e:
                    print(f"⚠️  Failed to load {template_path.name}: {e}")
    
    if templates:
        brands_loaded = sorted(set(t[2] for t in templates))
        print(f"   📋 Brands loaded: {', '.join(brands_loaded)}")
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
        # ICC: More conservative scales (less noise, fewer false positives)
        template_size = min(template.shape[0], template.shape[1])
        if template_size > 100:
            scales = [0.7, 0.85, 1.0, 1.15, 1.3]
        elif template_size > 50:
            scales = [0.6, 0.75, 0.9, 1.0, 1.1, 1.25]
        else:
            scales = [0.5, 0.7, 0.85, 1.0, 1.15, 1.3]
    
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
        # ICC: Conservative scales (less noise)
        template_size = min(template.shape[0], template.shape[1])
        if template_size > 100:
            scales = [0.7, 0.85, 1.0, 1.15, 1.3]
        elif template_size > 50:
            scales = [0.6, 0.75, 0.9, 1.0, 1.1, 1.25]
        else:
            scales = [0.5, 0.7, 0.85, 1.0, 1.15, 1.3]
    
    all_matches = []
    
    # Use brand-specific min confidence if set, else main threshold (keeps default strict, less noise)
    effective_min = BRAND_MIN_CONFIDENCE.get((brand or "").lower())
    adjusted_threshold = min(threshold, effective_min) if effective_min is not None else threshold
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
                    vertical_distance = abs(center_y - ecenter_y)
                    min_vertical_distance = max(box_height, ebox_height) * 1.2
                    if vertical_distance > min_vertical_distance:
                        continue  # Different rows, keep both
                    # If in same row and overlapping horizontally, it's a duplicate
                    horizontal_overlap = not (x2 < ex1 or x1 > ex2)
                    if horizontal_overlap:
                        too_close = True
                        break
                else:
                    distance = np.sqrt((center_x - ecenter_x)**2 + (center_y - ecenter_y)**2)
                    base_min_dist = max(5, min(scaled_template.shape[0], scaled_template.shape[1]) // 2)
                    min_dist = base_min_dist
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


def detect_icc_in_region(
    image_path: Path,
    templates: List[Tuple[Path, np.ndarray, str, str, Optional[str]]],
    threshold: float = DEFAULT_THRESHOLD,
    region_only: bool = False,
    brand_mapping: Dict[str, str] = None,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    nms_iou_threshold: float = DEFAULT_NMS_IOU_THRESHOLD,
    min_detection_size: int = DEFAULT_MIN_DETECTION_SIZE
) -> List[Tuple[int, int, int, int, float, str, str, str]]:
    """Detect sponsor logos in image using template matching (zone-based).
    
    Focuses on bottom-right corner; templates with a zone are searched only in that zone.
    
    Args:
        image_path: Path to image file
        templates: List of (template_path, template_image, brand, location, zone) tuples
        threshold: Minimum match confidence
        region_only: If True, only search in bottom-right region
        brand_mapping: Optional brand to location mapping (fallback)
    
    Returns:
        List of (x1, y1, x2, y2, confidence, template_name, brand, location) detections
    """
    # Load image in grayscale (faster than color)
    # Use IMREAD_GRAYSCALE for better performance
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        return []  # Don't print in parallel mode to avoid output conflicts
    
    # Image preprocessing for better template matching
    # Apply contrast enhancement and sharpening
    # This helps with difficult brands like Lancia/Citroen
    image = cv2.convertScaleAbs(image, alpha=1.2, beta=10)  # Increase contrast
    # Apply unsharp masking for sharpening
    gaussian = cv2.GaussianBlur(image, (0, 0), 2.0)
    image = cv2.addWeighted(image, 1.5, gaussian, -0.5, 0)
    
    height, width = image.shape
    detections = []
    
    # Separate templates by zone assignment
    templates_with_zones = [(tp, t, b, l, z) for tp, t, b, l, z in templates if z is not None]
    templates_without_zones = [(tp, t, b, l, z) for tp, t, b, l, z in templates if z is None]
    
    # Process templates with zone assignments.
    #
    # Special case for bottom_right:
    # To avoid confusing the main brands (Skoda/Toyota/Hyundai/Ford) with Lancia/Citroen,
    # we search the main brands first, and if any of them produces detections we stop
    # searching further brands for bottom_right.
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
        
        zone = SCREEN_ZONES[zone_name]
        x_start = int(zone['x_start'] * width)
        x_end = int(zone['x_end'] * width)
        y_start = int(zone['y_start'] * height)
        y_end = int(zone['y_end'] * height)
        
        region = image[y_start:y_end, x_start:x_end]
        
        matches = match_template_multi_scale_all_matches(
            region,
            template,
            threshold,
            zone_name=zone_name,
            brand=brand
        )
        
        # Get zone-specific minimum size if available
        zone_min_size = ZONE_MIN_DETECTION_SIZES.get(zone_name, min_detection_size)
        # Override with brand-specific minimum if available
        if brand:
            brand_min_size = BRAND_MIN_DETECTION_SIZES.get(brand.lower())
            if brand_min_size is not None:
                zone_min_size = min(zone_min_size, brand_min_size)  # Use the smaller of the two
        
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
            
            # Simple check: just minimum size (same as leaderboard zones)
            if det_size >= zone_min_size:
                detections.append((x1, y1, x2, y2, conf, template_path.name, brand, location))
    
    # Group templates by zone for ordering/early-exit logic.
    templates_by_zone: Dict[str, List[Tuple[Path, np.ndarray, str, str, Optional[str]]]] = {}
    for tp, t, b, l, z in templates_with_zones:
        templates_by_zone.setdefault(z, []).append((tp, t, b, l, z))
    
    for zone_name, zone_templates in templates_by_zone.items():
        for template_path, template, brand, location, _ in zone_templates:
            _process_template_in_zone(template_path, template, brand, location, zone_name)
    
    # Process templates without zone assignments (search full image)
    for template_path, template, brand, location, zone_name in templates_without_zones:
        # Find ALL matches in full image
        matches = match_template_multi_scale_all_matches(image, template, threshold, brand=brand)
        
        for match in matches:
            x1, y1, x2, y2, conf = match
            detections.append((x1, y1, x2, y2, conf, template_path.name, brand, location))
    
    # region_only: keep only detections in bottom-right zone
    if region_only:
        br = SCREEN_ZONES["bottom_right"]
        x_start = int(br['x_start'] * width)
        x_end = int(br['x_end'] * width)
        y_start = int(br['y_start'] * height)
        y_end = int(br['y_end'] * height)
        filtered_detections = []
        for det in detections:
            x1, y1, x2, y2 = det[0], det[1], det[2], det[3]
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            if x_start <= center_x <= x_end and y_start <= center_y <= y_end:
                filtered_detections.append(det)
        detections = filtered_detections
    
    # Filter by minimum confidence (use brand-specific if set, else main min_confidence)
    filtered_by_confidence = []
    for det in detections:
        x1, y1, x2, y2, conf, name, brand, location = det
        brand_min_conf = BRAND_MIN_CONFIDENCE.get(brand.lower() if brand else None, min_confidence)
        if conf >= brand_min_conf:
            filtered_by_confidence.append(det)
    
    detections = filtered_by_confidence
    
    if not detections:
        return []
    
    # Filter by size (too small or too large detections are likely false positives)
    height, width = image.shape
    max_size = max(width, height) * MAX_DETECTION_SIZE_RATIO
    filtered_by_size = []
    for det in detections:
        x1, y1, x2, y2, conf, name, brand, location = det
        det_width = x2 - x1
        det_height = y2 - y1
        det_size = max(det_width, det_height)
        
        # Get brand-specific minimum size if available
        brand_min_size = BRAND_MIN_DETECTION_SIZES.get(brand.lower() if brand else None, min_detection_size)
        effective_min_size = min(brand_min_size, min_detection_size)  # Use the smaller of the two
        
        # Keep if size is reasonable
        if det_size >= effective_min_size and det_size <= max_size:
            filtered_by_size.append(det)
    
    detections = filtered_by_size
    
    if not detections:
        return []
    
    # Sort by confidence (highest first)
    detections.sort(key=lambda x: x[4], reverse=True)
    
    # Non-Maximum Suppression (NMS) - remove overlapping detections
    # But keep detections that are in different rows (for leaderboard logos)
    if len(detections) > 1:
        filtered = []
        for det in detections:
            x1, y1, x2, y2, conf, name, brand, location = det
            det_height = y2 - y1
            det_center_y = (y1 + y2) / 2
            
            # Check overlap with existing detections
            overlap = False
            for existing in filtered:
                ex1, ey1, ex2, ey2, econf, _, ebrand, _ = existing
                
                # Only suppress if same brand (different brands can overlap)
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
    
    # Colors for different zones
    zone_colors = {
        "bottom_left": "red",
        "bottom_right": "blue",
        "left_column": "green",
        "right_column": "yellow",
        "top_left": "orange",
        "top_right": "purple",
    }
    
    # Show all zones if none specified
    if zones_to_show is None:
        zones_to_show = list(SCREEN_ZONES.keys())
    
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
    for x1, y1, x2, y2, conf, template_name, brand, location in detections:
        # Draw rectangle
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Draw label (use brand name, e.g. Emirates)
        label = f"{brand or 'ICC'} {conf:.2f}"
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
        Emirates:Banner
        Emirates:BottomRight:3
    
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


def load_brand_thresholds(thresholds_file: Path) -> Dict[str, float]:
    """Load brand -> min confidence threshold from file (overrides/adds to BRAND_MIN_CONFIDENCE).
    
    Format: Brand:threshold (one per line). Example:
        Emirates:0.60
        Aramco:0.52
        DP World:0.58
    """
    out = {}
    if not thresholds_file.exists():
        return out
    try:
        with open(thresholds_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if ':' in line:
                    parts = line.split(':', 1)
                    brand = parts[0].strip().lower()
                    try:
                        val = float(parts[1].strip())
                        if 0.3 <= val <= 1.0 and brand:
                            out[brand] = val
                    except ValueError:
                        continue
    except Exception as e:
        print(f"⚠️  Warning: Failed to load brand thresholds from {thresholds_file}: {e}")
    return out


def extract_brand_from_filename(filename: str) -> str:
    """Extract brand name from template filename.
    
    Examples:
        emirates_banner.png -> Emirates
        emirates_logo.png -> Emirates
    
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
        target_brands = ["Emirates"]
    
    all_brands = set(target_brands)
    for img_data in images_data.values():
        for ann in img_data.get('annotations', []):
            all_brands.add(ann.get('brand', 'Emirates'))
    all_brands = sorted(list(all_brands))
    
    # Target dimensions for coordinate space (startPoint/diagPoint are in this space)
    target_width = 730
    target_height = 410
    
    # Build images dict (format: imageName, imageIndex, width, height, annotations)
    images_dict = {}
    for image_name, img_data in images_data.items():
        # Extract imageIndex from filename (e.g. "000010" -> 10)
        try:
            numbers = re.findall(r'\d+', image_name)
            if numbers:
                image_index = int(max(numbers, key=len))
            else:
                image_index = 1
        except Exception:
            image_index = 1
        
        images_dict[image_name] = {
            "imageName": image_name,
            "imageIndex": image_index,
            "width": target_width,
            "height": target_height,
            "annotations": img_data.get('annotations', []),
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
            "prefsFilename": "icc_templates.txt",
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
    target_width: float = 730.0, target_height: float = 410.6
) -> Tuple[float, float, float, float]:
    """Scale coordinates from original image size to target size.
    
    Args:
        x1, y1, x2, y2: Bounding box coordinates in original image
        orig_width, orig_height: Original image dimensions
        target_width, target_height: Target dimensions (default from detect_brands_v2.py)
    
    Returns:
        (scaled_x1, scaled_y1, scaled_x2, scaled_y2)
    """
    scale_x = target_width / orig_width
    scale_y = target_height / orig_height
    
    scaled_x1 = x1 * scale_x
    scaled_y1 = y1 * scale_y
    scaled_x2 = x2 * scale_x
    scaled_y2 = y2 * scale_y
    
    # Clamp to target dimensions
    scaled_x1 = max(0.0, min(target_width, scaled_x1))
    scaled_y1 = max(0.0, min(target_height, scaled_y1))
    scaled_x2 = max(0.0, min(target_width, scaled_x2))
    scaled_y2 = max(0.0, min(target_height, scaled_y2))
    
    # Ensure x2 > x1 and y2 > y1
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
    
    # When --debug, append all [debug] lines to debug.log (next to script)
    debug_log_path = script_dir / "debug.log"
    debug_log_file = open(debug_log_path, "w", encoding="utf-8") if getattr(args, "debug", False) else None
    debug_log_lock = threading.Lock() if debug_log_file else None
    if debug_log_file:
        debug_log_file.write(f"# ICC template matcher debug log - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        debug_log_file.write(f"# Folder: {image_folder}\n\n")
        debug_log_file.flush()
        print(f"   📝 Debug log: {debug_log_path}\n")
    
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
            
            detections = detect_icc_in_region(
                image_path, templates, args.threshold, args.region_only, brand_mapping,
                args.min_confidence, args.nms_iou, args.min_size
            )
            
            # ICC RULE: Only ONE logo per image - keep the largest one (by pixel area)
            if len(detections) > 1:
                largest_detection = max(detections, key=lambda d: (d[2] - d[0]) * (d[3] - d[1]))
                detections = [largest_detection]
            
            image_name = image_path.stem
            annotations = []
            detection_count = 0
            
            if detections:
                detection_count = len(detections)
                # Group by brand for summary
                brands_found = {}
                for det in detections:
                    brand = det[6] if len(det) > 6 else "Unknown"
                    if brand not in brands_found:
                        brands_found[brand] = []
                    brands_found[brand].append(det)
                
                # Print summary header
                brand_summary = ", ".join([f"{brand}({len(dets)})" for brand, dets in sorted(brands_found.items())])
                print(f"✅ {image_path.name}: Found {detection_count} detection(s) - Brands: {brand_summary}")
                
                # Convert detections to annotations format (startPoint, diagPoint, group, brand, tpoint, hits)
                for det in detections:
                    x1, y1, x2, y2, conf, template_name, brand, location = det
                    scaled_x1, scaled_y1, scaled_x2, scaled_y2 = scale_coordinates(
                        x1, y1, x2, y2, orig_width, orig_height
                    )
                    annotation = {
                        "startPoint": [float(scaled_x1), float(scaled_y1)],
                        "diagPoint": [float(scaled_x2), float(scaled_y2)],
                        "group": "template_match",
                        "brand": brand,
                        "tpoint": location,
                        "hits": ICC_ANNOTATION_HITS,
                    }
                    annotations.append(annotation)
                
                # Annotate image if requested
                if args.annotate:
                    annotate_image(image_path, detections, output_dir / f"annotated_{image_path.name}")
                    print(f"   💾 Annotated image saved: {output_dir / f'annotated_{image_path.name}'}")
            else:
                print(f"❌ {image_path.name}: No logos found (searched bottom-right and other zones)")
            
            # Create zone visualization if requested (always, even when no detections)
            if visualize_zones_flag:
                zone_viz_path = output_dir / f"zones_{image_path.name}"
                # Show all zones used by templates
                zones_used = set(t[4] for t in templates if t[4] is not None)
                if not zones_used:
                    zones_used = ["bottom_right"]  # fallback
                visualize_zones(image_path, zone_viz_path, zones_to_show=sorted(zones_used))
            
            # Debug: print best correlation per brand (multi-scale, in their assigned zone) when no detection
            if getattr(args, 'debug', False):
                all_brands_in_templates = {t[2] for t in templates}
                brands_found_this_image = {det[6] for det in detections} if detections else set()
                missing_brands = all_brands_in_templates - brands_found_this_image
                if missing_brands:
                    image_gray = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
                    if image_gray is not None:
                        image_gray = cv2.convertScaleAbs(image_gray, alpha=1.2, beta=10)
                        gaussian = cv2.GaussianBlur(image_gray, (0, 0), 2.0)
                        image_gray = cv2.addWeighted(image_gray, 1.5, gaussian, -0.5, 0)
                        h, w = image_gray.shape
                        debug_scales = [0.6, 0.75, 0.9, 1.0, 1.1, 1.25]
                        for brand in sorted(missing_brands):
                            best_val = -1.0
                            zone_searched = "bottom_right"  # default
                            for (_tp, template_img, b, _loc, z) in templates:
                                if b != brand:
                                    continue
                                # Use template's zone if assigned, else bottom_right
                                zone_name = z if z is not None else "bottom_right"
                                if zone_name not in SCREEN_ZONES:
                                    continue
                                zone_searched = zone_name
                                zone = SCREEN_ZONES[zone_name]
                                x1, x2 = int(zone['x_start'] * w), int(zone['x_end'] * w)
                                y1, y2 = int(zone['y_start'] * h), int(zone['y_end'] * h)
                                region = image_gray[y1:y2, x1:x2]
                                for scale in debug_scales:
                                    tw = int(template_img.shape[1] * scale)
                                    th_h = int(template_img.shape[0] * scale)
                                    if tw < 10 or th_h < 10 or th_h > region.shape[0] or tw > region.shape[1]:
                                        continue
                                    interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
                                    scaled_t = cv2.resize(template_img, (tw, th_h), interpolation=interp)
                                    res = cv2.matchTemplate(region, scaled_t, cv2.TM_CCOEFF_NORMED)
                                    _, max_val, _, _ = cv2.minMaxLoc(res)
                                    best_val = max(best_val, max_val)
                            if best_val >= 0:
                                th = BRAND_MIN_CONFIDENCE.get(brand.lower(), args.threshold)
                                gap = th - best_val
                                line = f"   [debug] {image_path.name} {brand} [{zone_searched}] best: {best_val:.3f} (threshold {th}, gap {gap:+.2f})"
                                print(line)
                                if debug_log_file and debug_log_lock:
                                    with debug_log_lock:
                                        debug_log_file.write(line + "\n")
                                        debug_log_file.flush()
            
            # Store image data
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
    
    if debug_log_file:
        debug_log_file.close()
    
    all_brands = set()
    for img_data in images_data.values():
        for ann in img_data.get('annotations', []):
            all_brands.add(ann.get('brand', 'Emirates'))
    all_brands = sorted(list(all_brands)) if all_brands else ["Emirates"]
    
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
    
    print(f"📊 Summary: {total_detections} ICC brand detection(s) in {len(images)} image(s)")
    print(f"📝 JSON output saved to: {json_path}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(description="ICC Template Matcher (bottom-right sponsor logos, e.g. Emirates)")
    parser.add_argument("image_folder", type=Path, help="Folder containing images")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                       help=f"Template matching threshold (default: {DEFAULT_THRESHOLD})")
    parser.add_argument("--region-only", action="store_true",
                       help="Only search in bottom-right region")
    parser.add_argument("--templates-dir", type=Path, default=None,
                       help="Path to templates directory (default: ./icc_templates)")
    parser.add_argument("--output-dir", type=Path, default=None,
                       help="Path to output directory (default: ./icc_output)")
    parser.add_argument("--annotate", action="store_true",
                       help="Save annotated images with bounding boxes")
    parser.add_argument("--visualize-zones", action="store_true",
                       help="Save zone visualization images showing search areas")
    parser.add_argument("--workers", type=int, default=None,
                       help="Parallel workers: with --ICConly = folders in parallel (default 4); else = images per folder (default: auto)")
    parser.add_argument("--min-confidence", type=float, default=DEFAULT_MIN_CONFIDENCE,
                       help=f"Minimum confidence for detections (default: {DEFAULT_MIN_CONFIDENCE})")
    parser.add_argument("--nms-iou", type=float, default=DEFAULT_NMS_IOU_THRESHOLD,
                       help=f"NMS IoU threshold for overlap removal (default: {DEFAULT_NMS_IOU_THRESHOLD})")
    parser.add_argument("--min-size", type=int, default=DEFAULT_MIN_DETECTION_SIZE,
                       help=f"Minimum detection size in pixels (default: {DEFAULT_MIN_DETECTION_SIZE})")
    parser.add_argument("--ICConly", action="store_true",
                       help="Batch mode: process all subfolders ending with '_temporal_median' in the given root folder")
    parser.add_argument("--debug", action="store_true",
                       help="Print best correlation per brand when no detection (to tune threshold/templates)")
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    # ICC: templates are read from icc_templates/ (hardcoded default)
    templates_dir = args.templates_dir or (script_dir / "icc_templates")
    output_dir = args.output_dir or (script_dir / "icc_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Loading templates from: {templates_dir}")
    templates = load_templates(templates_dir)
    
    if not templates:
        print("❌ No templates found! Add template images under icc_templates/ (e.g. Emirates Logos/bottom_right/...).")
        print("   Same folder structure as WRC: Brand Logos / zone / location / images.")
        return 1
    
    mapping_file = script_dir / "icc_brand_mapping.txt"
    brand_mapping = load_brand_mapping(mapping_file)
    if brand_mapping:
        print(f"📋 Loaded brand mapping (fallback): {brand_mapping}")
    else:
        print(f"ℹ️  No icc_brand_mapping.txt found - using folder structure for brand/location")
    
    # Load per-brand thresholds (so you can add brands without editing code)
    thresholds_file = script_dir / "icc_brand_thresholds.txt"
    loaded_thresholds = load_brand_thresholds(thresholds_file)
    if loaded_thresholds:
        BRAND_MIN_CONFIDENCE.update(loaded_thresholds)
        print(f"📋 Loaded brand thresholds from icc_brand_thresholds.txt: {loaded_thresholds}")
    
    if args.ICConly:
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
        
        # Number of folders to process in parallel (--workers applies to folder-level when ICConly)
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
    
    # Original behavior: single folder processing
    return process_single_folder(image_folder, args, templates, brand_mapping, script_dir, output_dir)


if __name__ == "__main__":
    sys.exit(main())
