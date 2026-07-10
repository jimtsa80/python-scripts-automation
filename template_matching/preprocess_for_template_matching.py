#!/usr/bin/env python3
"""
Simple image preprocessor to make frames or templates more suitable
for template matching (WRC logos, brands etc).

Usage examples:

    # Preprocess all images in a folder and write to _preprocessed
    python preprocess_for_template_matching.py F:\downloads\batch11\some_folder

    # Explicitly set output folder
    python preprocess_for_template_matching.py F:\input F:\input_preprocessed

What it does (per image):
    - Optional upscaling (--scale, e.g., 2.0 for 2x larger) - useful for small/compressed frames
    - Convert to grayscale
    - Optional crop to a screen zone (e.g. bottom_right) using the same
      relative coordinates as wrc_template_matcher.SCREEN_ZONES
    - Contrast boost (alpha / beta)
    - Slight sharpening (unsharp mask)
    - Optional histogram equalization (CLAHE) to fight compression / low contrast
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import cv2
import numpy as np


# Copy the relevant zones so we can reuse the same coordinates
SCREEN_ZONES = {
    "bottom_left": {
        "x_start": 0.0,
        "x_end": 0.22,
        "y_start": 0.8,
        "y_end": 1.0,
        "description": "Bottom left corner - WRC logo, broadcast info",
    },
    "bottom_right": {
        "x_start": 0.78,
        "x_end": 0.85,
        "y_start": 0.86,
        "y_end": 0.90,
        "description": "Bottom right corner - Driver info overlay (TVGI-Driver)",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preprocess images to improve template matching (contrast, sharpen, optional zone crop)."
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        help="Folder with input images (jpg/png). Processed images are written to a sibling *_preprocessed folder by default.",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        nargs="?",
        help="Optional output folder. If omitted, a '<input_dir>_preprocessed' folder is created next to input_dir.",
    )
    parser.add_argument(
        "--zone",
        type=str,
        choices=sorted(SCREEN_ZONES.keys()) + ["none"],
        default="none",
        help="Optionally crop to a known screen zone before preprocessing (e.g. 'bottom_right').",
    )
    parser.add_argument(
        "--clahe",
        action="store_true",
        help="Apply CLAHE (adaptive histogram equalization) after contrast/sharpen. Good for low-contrast/compressed frames.",
    )
    parser.add_argument(
        "--ext",
        type=str,
        default=".png",
        help="Output extension (default: .png).",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Upscale factor (e.g., 2.0 for 2x larger images). Useful for small/compressed frames. Default: 1.0 (no scaling).",
    )
    parser.add_argument(
        "--enhance-light-text",
        action="store_true",
        help="Apply special processing for light-colored text (inversion, adaptive thresholding, morphological ops). Automatically enabled for bottom_right zone.",
    )
    parser.add_argument(
        "--morph-gradient",
        action="store_true",
        help="Use morphological gradient instead of standard preprocessing. Better for template matching with low threshold.",
    )
    parser.add_argument(
        "--temporal-mode",
        action="store_true",
        help="Temporal consistency mode: Process multiple frames to find static overlays (watermarks, logos). Requires frames from same video.",
    )
    parser.add_argument(
        "--frames-dir",
        type=Path,
        help="Directory with multiple frames for temporal processing (used with --temporal-mode).",
    )
    parser.add_argument(
        "--temporal-output-median",
        action="store_true",
        help="When using --temporal-mode, also save individual preprocessed frames using the median frame as reference.",
    )
    parser.add_argument(
        "--temporal-median-all",
        action="store_true",
        help="Calculate temporal median for each image using neighboring frames. Creates median version of each image.",
    )
    parser.add_argument(
        "--temporal-window",
        type=int,
        default=15,
        help="Number of frames to use for temporal median (default: 15). Uses frames before and after current frame.",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="Number of threads for parallel processing (default: 4).",
    )
    return parser.parse_args()


def crop_to_zone(img: np.ndarray, zone_name: str) -> np.ndarray:
    """Crop an image to a predefined screen zone."""
    h, w = img.shape[:2]
    zone = SCREEN_ZONES[zone_name]
    x_start = int(zone["x_start"] * w)
    x_end = int(zone["x_end"] * w)
    y_start = int(zone["y_start"] * h)
    y_end = int(zone["y_end"] * h)

    # Safety clamps
    x_start = max(0, min(x_start, w - 1))
    x_end = max(x_start + 1, min(x_end, w))
    y_start = max(0, min(y_start, h - 1))
    y_end = max(y_start + 1, min(y_end, h))

    return img[y_start:y_end, x_start:x_end]


def preprocess_image(
    img: np.ndarray,
    zone_name: Optional[str] = None,
    use_clahe: bool = False,
    scale: float = 1.0,
    enhance_light_text: bool = False,
    morph_gradient: bool = False,
) -> np.ndarray:
    """Apply upscaling (optional), grayscale, optional zone crop, contrast, sharpen (+ optional CLAHE).
    
    Args:
        img: Input image (BGR)
        zone_name: Optional zone name to crop to
        use_clahe: Apply CLAHE histogram equalization
        scale: Upscaling factor
        enhance_light_text: Special processing for light-colored text (inverts and enhances contrast)
        morph_gradient: Use morphological gradient for template matching (better than Canny)
    """
    # Upscale first if requested (before grayscale for better quality)
    # Recommended: scale ×4 for better template matching
    if scale != 1.0:
        h, w = img.shape[:2]
        new_w = int(w * scale)
        new_h = int(h * scale)
        # Use INTER_LANCZOS4 for best upscaling quality (slower but better)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Optional zone crop in full-res coordinates
    if zone_name and zone_name in SCREEN_ZONES:
        gray = crop_to_zone(gray, zone_name)

    # Morphological gradient preprocessing for template matching
    # Better than Canny for low threshold template matching
    if morph_gradient:
        # Apply CLAHE first for better contrast
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        gray_clahe = clahe.apply(gray)
        
        # Unsharp mask for sharpening
        gaussian = cv2.GaussianBlur(gray_clahe, (0, 0), 1.5)
        sharp = cv2.addWeighted(gray_clahe, 1.6, gaussian, -0.6, 0)
        
        # Morphological gradient (dilation - erosion)
        # This is better than Canny for template matching
        kernel = np.ones((3, 3), np.uint8)
        gradient = cv2.morphologyEx(sharp, cv2.MORPH_GRADIENT, kernel)
        
        return gradient

    # Special handling for different zones
    if zone_name == "bottom_left":
        # EXTREME BINARY: Background = PURE BLACK (0), Text = PURE WHITE (255)
        # Step 1: Maximum contrast enhancement
        gray_contrast = cv2.convertScaleAbs(gray, alpha=3.0, beta=20)
        
        # Step 2: Apply CLAHE for local contrast
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4))
        gray_clahe = clahe.apply(gray_contrast)
        
        # Step 3: Use adaptive thresholding to find text regions
        adaptive = cv2.adaptiveThreshold(
            gray_clahe, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 10
        )
        
        # Step 4: Use Otsu thresholding
        _, otsu = cv2.threshold(gray_clahe, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Step 5: Find bright pixels (white/light text) - very aggressive
        bright_threshold = np.percentile(gray_clahe, 55)  # Top 45% brightest
        bright_mask = gray_clahe > bright_threshold
        
        # Step 6: Combine all methods
        text_mask = (adaptive > 0) | (otsu > 0) | bright_mask
        text_mask = text_mask.astype(np.uint8) * 255
        
        # Step 7: Use contours to refine and fill text regions
        contours, _ = cv2.findContours(text_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        refined_mask = np.zeros_like(gray, dtype=np.uint8)
        h, w = gray.shape
        
        for contour in contours:
            area = cv2.contourArea(contour)
            x, y, cw, ch = cv2.boundingRect(contour)
            
            # Very relaxed filters to catch all text
            if (area > 5 and area < (h * w * 0.2) and
                cw < w * 0.7 and ch < h * 0.7):
                cv2.drawContours(refined_mask, [contour], -1, 255, -1)
        
        # Step 8: Combine refined contours with original mask
        text_mask = refined_mask | text_mask
        
        # Step 9: Aggressive morphological operations to fill text and clean up
        kernel_small = np.ones((3, 3), np.uint8)
        kernel_medium = np.ones((5, 5), np.uint8)
        text_mask = cv2.morphologyEx(text_mask, cv2.MORPH_CLOSE, kernel_small, iterations=3)
        text_mask = cv2.morphologyEx(text_mask, cv2.MORPH_CLOSE, kernel_medium, iterations=2)
        text_mask = cv2.morphologyEx(text_mask, cv2.MORPH_OPEN, kernel_small)
        
        # Step 10: Create PURE BINARY result
        result = np.zeros_like(gray, dtype=np.uint8)  # Start with PURE BLACK (0)
        result[text_mask > 0] = 255  # Text pixels = PURE WHITE (255)
        
        gray = result
        # Skip unsharp mask and CLAHE for binary result
        return gray
        
    elif enhance_light_text:
        # SIMPLE DIRECT APPROACH: Find white/bright pixels (WRC text) and make them black
        # Background stays white, only text becomes black
        
        # Step 1: Enhance contrast to separate text from background
        gray_enhanced = cv2.convertScaleAbs(gray, alpha=2.5, beta=10)
        
        # Step 2: Apply CLAHE for local contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        gray_clahe = clahe.apply(gray_enhanced)
        
        # Step 3: Find bright/white pixels that are likely text
        # Use multiple thresholds to catch different shades of white text
        mean_intensity = np.mean(gray_clahe)
        
        # If image is generally bright, text might be slightly brighter
        if mean_intensity > 140:
            # Bright image: text is likely brighter than average
            text_threshold = np.percentile(gray_clahe, 75)  # Top 25% brightest pixels
        else:
            # Darker image: text is bright
            text_threshold = np.percentile(gray_clahe, 70)  # Top 30% brightest pixels
        
        # Step 4: Create mask for bright pixels (text)
        bright_mask = gray_clahe > text_threshold
        
        # Step 5: Use edge detection to find text boundaries
        edges = cv2.Canny(gray_clahe, 50, 150)
        
        # Step 6: Dilate edges to fill in text regions
        kernel = np.ones((3, 3), np.uint8)
        edges_dilated = cv2.dilate(edges, kernel, iterations=2)
        
        # Step 7: Combine bright pixels with edge-based detection
        text_mask = bright_mask | (edges_dilated > 0)
        
        # Step 8: Use contours to refine - keep only text-like regions
        text_mask_uint8 = text_mask.astype(np.uint8) * 255
        contours, _ = cv2.findContours(text_mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        refined_mask = np.zeros_like(gray, dtype=np.uint8)
        h, w = gray.shape
        
        for contour in contours:
            area = cv2.contourArea(contour)
            x, y, cw, ch = cv2.boundingRect(contour)
            aspect_ratio = cw / max(ch, 1)
            
            # Filter for text-like regions (small to medium, reasonable aspect ratio)
            if (area > 10 and area < (h * w * 0.15) and
                aspect_ratio > 0.2 and aspect_ratio < 8.0 and
                cw < w * 0.5 and ch < h * 0.5):
                cv2.drawContours(refined_mask, [contour], -1, 255, -1)
        
        # Step 9: Combine refined mask with bright pixels
        text_mask_final = (refined_mask > 0) | bright_mask
        
        # Step 10: Clean up with morphological operations
        text_mask_uint8 = text_mask_final.astype(np.uint8) * 255
        kernel_clean = np.ones((2, 2), np.uint8)
        text_mask_uint8 = cv2.morphologyEx(text_mask_uint8, cv2.MORPH_CLOSE, kernel_clean)
        text_mask_uint8 = cv2.morphologyEx(text_mask_uint8, cv2.MORPH_OPEN, kernel_clean)
        
        # Step 11: Make result: white background, black text
        result = np.full_like(gray, 255, dtype=np.uint8)  # White background
        result[text_mask_uint8 > 0] = 0  # Black text (WRC)
        
        gray = result
        # Skip unsharp mask and CLAHE for extreme extraction (already binary)
        return gray
        
    elif zone_name == "bottom_right":
        # Bottom right: Light/transparent text on white background
        # Simple approach: Darken white/light background to make light WRC text stand out
        bright_threshold = 180  # Pixels brighter than this are considered background
        dark_threshold = 150    # Pixels darker than this are likely text
        
        # Create masks
        bright_mask = gray > bright_threshold  # White/light background
        dark_mask = gray < dark_threshold     # Darker areas (text)
        
        # Darken bright background areas significantly
        gray_darkened = gray.copy().astype(np.float32)
        gray_darkened[bright_mask] = gray_darkened[bright_mask] * 0.25  # Darken white background by 75%
        gray_darkened[dark_mask] = gray_darkened[dark_mask] * 0.95      # Keep text almost unchanged
        gray = np.clip(gray_darkened, 0, 255).astype(np.uint8)
        
        # Increase contrast to make text stand out more
        gray = cv2.convertScaleAbs(gray, alpha=2.0, beta=-10)
    else:
        # Standard preprocessing for other zones
        # BUT: Apply adaptive brightness handling FIRST to prevent darkening bright areas
        pass  # Will apply adaptive enhancement below

    # Adaptive brightness handling: MORE AGGRESSIVE - darken bright areas more
    # Calculate local mean brightness BEFORE enhancement
    local_mean = cv2.blur(gray.astype(np.float32), (31, 31))
    
    # Normalize local mean to 0-1 range
    local_mean_norm = local_mean / 255.0
    
    # Create adaptive adjustment: VERY AGGRESSIVE thresholds
    # - Bright areas (> 0.5): DARKEN VERY significantly to make text stand out
    # - Dark areas (< 0.5): increase enhancement
    # - Medium areas: normal enhancement
    bright_mask = local_mean_norm > 0.5  # Even lower threshold to catch more bright areas
    dark_mask = local_mean_norm < 0.5   # Catch dark areas
    
    # Apply contrast enhancement adaptively pixel-by-pixel
    gray_float = gray.astype(np.float32)
    
    # Create enhancement factors based on local brightness
    alpha_map = np.ones_like(gray_float) * 1.3  # Default
    beta_map = np.ones_like(gray_float) * 8    # Default
    
    # Bright areas: DARKEN VERY aggressively (make background much darker)
    alpha_map[bright_mask] = 0.5  # Reduce brightness by 50%
    beta_map[bright_mask] = -40   # Darken significantly by subtracting
    
    # Dark areas: more enhancement
    alpha_map[dark_mask] = 1.6
    beta_map[dark_mask] = 15
    
    # Apply adaptive enhancement
    gray_enhanced = gray_float * alpha_map + beta_map
    gray_enhanced = np.clip(gray_enhanced, 0, 255)
    gray = gray_enhanced.astype(np.uint8)

    # MAXIMUM AGGRESSIVE text cleaning: Make text PERFECTLY bright, clean, uniform - remove ALL dark spots
    # Find bright pixels that are likely text (not background) - very inclusive
    text_threshold = np.percentile(gray, 55)  # Top 45% brightest pixels (very inclusive)
    text_mask = gray > text_threshold
    
    # Apply MAXIMUM aggressive smoothing - multiple passes with different techniques
    gray_smooth = cv2.bilateralFilter(gray, d=25, sigmaColor=150, sigmaSpace=150)  # Maximum smoothing
    gray_smooth = cv2.medianBlur(gray_smooth, 9)  # Very large median blur
    gray_smooth = cv2.GaussianBlur(gray_smooth, (9, 9), 0)  # Large Gaussian smoothing
    gray_smooth = cv2.bilateralFilter(gray_smooth, d=15, sigmaColor=100, sigmaSpace=100)  # Second pass
    
    # MAXIMUM aggressive morphological operations to fill in ALL dark spots
    kernel_small = np.ones((3, 3), np.uint8)
    kernel_medium = np.ones((5, 5), np.uint8)
    kernel_large = np.ones((7, 7), np.uint8)
    
    # Multiple close operations with increasing kernel sizes
    gray_smooth = cv2.morphologyEx(gray_smooth, cv2.MORPH_CLOSE, kernel_small, iterations=5)
    gray_smooth = cv2.morphologyEx(gray_smooth, cv2.MORPH_CLOSE, kernel_medium, iterations=4)
    gray_smooth = cv2.morphologyEx(gray_smooth, cv2.MORPH_CLOSE, kernel_large, iterations=3)
    
    # Dilate text slightly to ensure coverage
    gray_smooth = cv2.dilate(gray_smooth, kernel_small, iterations=1)
    
    # Brighten text regions MAXIMUM - make it PERFECTLY bright and uniform
    gray_float_smooth = gray_smooth.astype(np.float32)
    gray_float_orig = gray.astype(np.float32)
    
    # For text regions: MAXIMUM brightening
    # Brighten text by 60% and ensure VERY HIGH minimum brightness
    text_brightened = gray_float_smooth[text_mask] * 1.6
    text_brightened = np.clip(text_brightened, 220, 255)  # Ensure text is MAXIMUM bright (min 220)
    
    # Fill ANY remaining dark spots in text with maximum brightness
    dark_spots_in_text = text_brightened < 230
    text_brightened[dark_spots_in_text] = 240  # Fill dark spots with very bright value
    
    # Ensure all text pixels are uniformly bright
    text_brightened = np.clip(text_brightened, 230, 255)  # Force minimum 230
    
    gray_float_orig[text_mask] = text_brightened
    
    # For background: ensure it's MAXIMUM dark and uniform
    background_mask = ~text_mask
    
    # Darken background first
    gray_float_orig[background_mask] = np.clip(gray_float_orig[background_mask] * 0.25, 0, 50)  # MAXIMUM dark background (max 50)
    
    # Maximum smoothing for background to make it perfectly uniform
    # Apply smoothing to entire image, then extract background regions
    gray_temp = gray_float_orig.astype(np.uint8)
    gray_smooth_bg = cv2.GaussianBlur(gray_temp, (11, 11), 0)  # Very large blur
    gray_smooth_bg = cv2.medianBlur(gray_smooth_bg, 7)  # Additional median blur
    gray_smooth_bg_float = gray_smooth_bg.astype(np.float32)
    
    # Apply smoothed background only to background regions
    gray_float_orig[background_mask] = gray_smooth_bg_float[background_mask]
    
    gray = gray_float_orig.astype(np.uint8)

    # Unsharp mask for slightly crisper edges
    gaussian = cv2.GaussianBlur(gray, (0, 0), 1.5)
    sharp = cv2.addWeighted(gray, 1.6, gaussian, -0.6, 0)

    if use_clahe:
        # Adaptive CLAHE: Use lower clipLimit for bright areas to prevent over-enhancement
        # Create CLAHE with moderate clipLimit
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        
        # Apply CLAHE
        sharp_clahe = clahe.apply(sharp)
        
        # Blend: use less CLAHE in bright areas, more in dark areas
        bright_mask_uint8 = (local_mean_norm > 0.6).astype(np.float32)
        dark_mask_uint8 = (local_mean_norm < 0.4).astype(np.float32)
        
        # Blend original and CLAHE based on brightness
        sharp = sharp.astype(np.float32)
        sharp_clahe = sharp_clahe.astype(np.float32)
        
        # Bright areas: use less CLAHE (70% original, 30% CLAHE)
        sharp = sharp * (1 - bright_mask_uint8 * 0.3) + sharp_clahe * bright_mask_uint8 * 0.3
        
        # Dark areas: use more CLAHE (30% original, 70% CLAHE)
        sharp = sharp * (1 - dark_mask_uint8 * 0.7) + sharp_clahe * dark_mask_uint8 * 0.7
        
        # Medium areas: use balanced CLAHE (50% original, 50% CLAHE)
        medium_mask = 1 - bright_mask_uint8 - dark_mask_uint8
        sharp = sharp * (1 - medium_mask * 0.5) + sharp_clahe * medium_mask * 0.5
        
        sharp = np.clip(sharp, 0, 255).astype(np.uint8)

    return sharp


def iter_images(root: Path):
    exts = {".jpg", ".jpeg", ".png"}
    for path in root.rglob("*"):
        if path.suffix.lower() in exts:
            yield path


def process_single_image_median(
    img_path: Path,
    all_images: list,
    index: int,
    input_dir: Path,
    output_dir: Path,
    window_size: int,
    zone_name: Optional[str],
) -> tuple[str, bool]:
    """
    Process a single image to calculate its temporal median.
    Returns (filename, success).
    """
    filename = img_path.name
    
    try:
        # Determine frame range: window_size before and after current frame
        start_idx = max(0, index - window_size)
        end_idx = min(len(all_images), index + window_size + 1)
        
        # Get frame paths for this window
        frame_paths = all_images[start_idx:end_idx]
        
        # Load frames
        frames = []
        for frame_path in frame_paths:
            img = cv2.imread(str(frame_path), cv2.IMREAD_COLOR)
            if img is None:
                continue
            
            # Crop to zone if specified
            if zone_name and zone_name in SCREEN_ZONES:
                img = crop_to_zone(img, zone_name)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            frames.append(gray)
        
        if len(frames) < 3:
            return (filename, False)
        
        # Calculate temporal median for this image
        stack = np.stack(frames, axis=0)
        median_frame = np.median(stack, axis=0).astype(np.uint8)
        
        # Save median version
        output_path = output_dir / filename
        output_path = output_path.with_suffix('.png')
        
        # Skip if file already exists
        if output_path.exists():
            return (filename, False)
        
        cv2.imwrite(str(output_path), median_frame)
        return (filename, True)
    
    except Exception as e:
        print(f"   ⚠️  Error processing {filename}: {e}")
        return (filename, False)


def process_temporal_median_all(input_dir: Path, output_dir: Path, window_size: int = 15, zone_name: Optional[str] = None, num_threads: int = 4) -> int:
    """
    Calculate temporal median for each image using neighboring frames.
    
    For each image, takes window_size frames before and after, calculates median,
    and saves the median version of that image.
    
    This creates a "cleaned" version of each frame with moving objects removed.
    IMPORTANT: Creates 1:1 mapping - only processes images that exist in input.
    """
    # Get all images sorted by name (important for temporal order)
    # IMPORTANT: Only process files directly in input_dir (flat structure)
    exts = {".jpg", ".jpeg", ".png"}
    all_images = []
    
    # Only get files directly in the input directory (no subdirectories)
    for path in sorted(input_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in exts:
            all_images.append(path)
    
    # Remove duplicates by converting to set of absolute paths, then back to list
    seen = set()
    unique_images = []
    for img_path in all_images:
        abs_path = img_path.resolve()  # Get absolute path
        if abs_path not in seen:
            seen.add(abs_path)
            unique_images.append(img_path)
    all_images = sorted(unique_images)  # Keep sorted
    
    if len(all_images) == 0:
        print(f"⚠️  No images found in: {input_dir}")
        return 1
    
    # Remove duplicates by filename (in case same file appears multiple times)
    seen_filenames = set()
    unique_images = []
    for img_path in all_images:
        if img_path.name not in seen_filenames:
            seen_filenames.add(img_path.name)
            unique_images.append(img_path)
    all_images = sorted(unique_images)
    
    print(f"📹 Found {len(all_images)} unique images")
    print(f"   Input : {input_dir}")
    print(f"   Output: {output_dir}")
    print(f"   Zone  : {zone_name if zone_name else 'none'}")
    print(f"   Window: {window_size} frames")
    
    if len(all_images) < window_size * 2 + 1:
        print(f"⚠️  Warning: Only {len(all_images)} images found, but need at least {window_size * 2 + 1} for optimal temporal median")
        print(f"   Will use available frames (minimum 3 required)")
    print()
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"   Using {num_threads} threads for parallel processing...")
    print()
    
    # Process images in parallel using ThreadPoolExecutor
    processed_count = 0
    skipped_count = 0
    processed_files = set()  # Track processed filenames to avoid duplicates
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Submit all tasks
        future_to_image = {}
        for i, img_path in enumerate(all_images):
            filename = img_path.name
            
            # Skip if already processed
            if filename in processed_files:
                continue
            
            future = executor.submit(
                process_single_image_median,
                img_path,
                all_images,
                i,
                input_dir,
                output_dir,
                window_size,
                zone_name
            )
            future_to_image[future] = (i, img_path, filename)
        
        # Process completed tasks
        for future in as_completed(future_to_image):
            i, img_path, filename = future_to_image[future]
            
            # Skip if already processed
            if filename in processed_files:
                continue
            
            try:
                result_filename, success = future.result()
                if success:
                    processed_files.add(result_filename)
                    processed_count += 1
                    if processed_count % 10 == 0:
                        print(f"   Processed {processed_count}/{len(all_images)} images...")
                else:
                    skipped_count += 1
            except Exception as e:
                print(f"   ⚠️  Error processing {filename}: {e}")
                skipped_count += 1
    
    print(f"✅ Temporal median processing complete!")
    print(f"   Processed: {processed_count} images")
    if skipped_count > 0:
        print(f"   Skipped: {skipped_count} images (not enough frames)")
    print(f"   Output folder: {output_dir}")
    print(f"   ✅ 1:1 mapping - same number of images as input (where possible)")
    
    print(f"✅ Temporal median processing complete!")
    print(f"   Processed {processed_count} images")
    print(f"   Output folder: {output_dir}")
    
    return 0


def process_temporal_consistency(frames_dir: Path, output_dir: Path, zone_name: Optional[str] = None, output_median_frames: bool = False) -> int:
    """
    Temporal consistency method for finding static overlays (watermarks, logos).
    
    Strategy: Find regions that are stable across multiple frames (overlays)
    while removing moving content (people, camera movement).
    
    Steps:
    1. Load 20-30 consecutive frames
    2. Calculate temporal median (removes moving content)
    3. Find regions with low temporal variance (static overlays)
    4. Focus on bottom-right region where WRC watermark appears
    5. Extract connected components (logo regions)
    """
    # Get all images sorted by name
    exts = ["*.jpg", "*.jpeg", "*.png"]
    frame_paths = []
    for ext in exts:
        frame_paths.extend(sorted(frames_dir.glob(ext)))
        frame_paths.extend(sorted(frames_dir.glob(ext.upper())))
    
    if len(frame_paths) < 5:
        print(f"⚠️  Need at least 5 frames for temporal processing, found {len(frame_paths)}")
        return 1
    
    # Use 20-30 frames (or all available if less)
    num_frames = min(30, len(frame_paths))
    frame_paths = frame_paths[:num_frames]
    
    print(f"📹 Processing {num_frames} frames for temporal consistency...")
    
    # Load all frames
    frames = []
    for frame_path in frame_paths:
        img = cv2.imread(str(frame_path), cv2.IMREAD_COLOR)
        if img is None:
            continue
        
        # Crop to zone if specified
        if zone_name and zone_name in SCREEN_ZONES:
            img = crop_to_zone(img, zone_name)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        frames.append(gray)
    
    if len(frames) < 5:
        print(f"⚠️  Not enough valid frames: {len(frames)}")
        return 1
    
    # Stack frames: shape = (num_frames, height, width)
    stack = np.stack(frames, axis=0)
    print(f"   Stack shape: {stack.shape}")
    
    # Step 1: Calculate temporal median (removes moving content, keeps static overlays)
    print("   Calculating temporal median...")
    median_frame = np.median(stack, axis=0).astype(np.uint8)
    
    # Step 2: Calculate temporal standard deviation (low variance = static overlay)
    print("   Calculating temporal variance...")
    std_map = np.std(stack, axis=0)
    
    # Step 3: Find regions with low temporal variance (static overlays)
    # Low variance = pixels that don't change much across frames = overlays
    variance_threshold = np.percentile(std_map, 20)  # Bottom 20% variance
    static_mask = std_map < variance_threshold
    
    # Step 4: Focus on bottom-right region where WRC watermark appears
    h, w = static_mask.shape
    roi_mask = np.zeros_like(static_mask, dtype=bool)
    
    if zone_name == "bottom_right":
        # Use bottom_right zone coordinates
        zone = SCREEN_ZONES["bottom_right"]
        y_start = int(zone["y_start"] * h)
        y_end = int(zone["y_end"] * h)
        x_start = int(zone["x_start"] * w)
        x_end = int(zone["x_end"] * w)
    else:
        # Default: bottom-right quarter
        y_start = int(h * 0.55)
        y_end = h
        x_start = int(w * 0.55)
        x_end = w
    
    roi_mask[y_start:y_end, x_start:x_end] = True
    final_mask = static_mask & roi_mask
    
    # Step 5: Find connected components (logo regions)
    print("   Finding connected components...")
    final_mask_uint8 = final_mask.astype(np.uint8) * 255
    num_labels, labels = cv2.connectedComponents(final_mask_uint8)
    
    # Create output: median frame with overlay regions highlighted
    output = median_frame.copy()
    
    # Highlight static overlay regions
    overlay_regions = np.zeros_like(output)
    for label_id in range(1, num_labels):  # Skip background (0)
        component_mask = labels == label_id
        component_area = np.sum(component_mask)
        
        # Filter by size (logo should be reasonable size)
        if component_area > 50 and component_area < (h * w * 0.1):
            overlay_regions[component_mask] = 255
    
    # Save results
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save median frame (static overlay visible)
    cv2.imwrite(str(output_dir / "temporal_median.png"), median_frame)
    
    # Save variance map
    std_map_normalized = (std_map / std_map.max() * 255).astype(np.uint8)
    cv2.imwrite(str(output_dir / "temporal_variance.png"), std_map_normalized)
    
    # Save static overlay mask
    cv2.imwrite(str(output_dir / "static_overlay_mask.png"), final_mask_uint8)
    
    # Save overlay regions highlighted
    overlay_highlighted = cv2.cvtColor(median_frame, cv2.COLOR_GRAY2BGR)
    overlay_highlighted[overlay_regions > 0] = [0, 255, 0]  # Green highlight
    cv2.imwrite(str(output_dir / "overlay_regions.png"), overlay_highlighted)
    
    # Save binary result: overlay regions = white, rest = black
    binary_result = np.zeros_like(median_frame)
    binary_result[overlay_regions > 0] = 255
    cv2.imwrite(str(output_dir / "overlay_binary.png"), binary_result)
    
    # Optional: Preprocess individual frames using the median frame as reference
    if output_median_frames:
        print("   Preprocessing individual frames using median reference...")
        preprocessed_dir = output_dir / "preprocessed_frames"
        preprocessed_dir.mkdir(exist_ok=True)
        
        for i, frame_path in enumerate(frame_paths):
            img = cv2.imread(str(frame_path), cv2.IMREAD_COLOR)
            if img is None:
                continue
            
            # Crop to zone if specified
            if zone_name and zone_name in SCREEN_ZONES:
                img = crop_to_zone(img, zone_name)
            
            # Preprocess using standard method but with median frame as reference
            processed = preprocess_image(
                img,
                zone_name=None,  # Already cropped
                use_clahe=True,
                scale=1.0,
                enhance_light_text=False,
                morph_gradient=False
            )
            
            # Save preprocessed frame
            frame_name = frame_path.stem
            output_path = preprocessed_dir / f"{frame_name}_preprocessed.png"
            cv2.imwrite(str(output_path), processed)
        
        print(f"   Preprocessed {len(frame_paths)} frames saved to: {preprocessed_dir}")
    
    print(f"✅ Temporal processing complete!")
    print(f"   Found {num_labels - 1} static overlay regions")
    print(f"   Output saved to: {output_dir}")
    print()
    print("📌 HOW TO USE:")
    print("   1. Use 'temporal_median.png' for template matching (clean overlay visible)")
    print("   2. Use 'overlay_binary.png' as binary mask for WRC logo")
    print("   3. Use 'overlay_regions.png' to see detected overlay regions")
    print("   4. Feed 'temporal_median.png' to wrc_template_matcher.py")
    
    return 0


def find_reduced_folders(root_dir: Path) -> list[Path]:
    """Find all subfolders containing 'reduced_' in their name."""
    reduced_folders = []
    for path in root_dir.rglob("*"):
        if path.is_dir() and "reduced_" in path.name.lower():
            reduced_folders.append(path)
    return sorted(reduced_folders)


def main() -> int:
    args = parse_args()

    # Handle temporal median for all images
    if args.temporal_median_all:
        input_dir: Path = args.input_dir
        output_dir: Optional[Path] = args.output_dir
        
        if not input_dir.exists() or not input_dir.is_dir():
            print(f"❌ Input directory not found or not a folder: {input_dir}")
            return 1
        
        # Check if input_dir contains "reduced_" folders (batch processing mode)
        reduced_folders = find_reduced_folders(input_dir)
        
        if len(reduced_folders) > 0:
            # Batch processing mode: process each "reduced_" folder
            print(f"📁 Batch processing mode: Found {len(reduced_folders)} folders with 'reduced_'")
            print()
            
            zone_name = None if args.zone == "none" else args.zone
            total_processed = 0
            total_skipped = 0
            
            for i, reduced_folder in enumerate(reduced_folders, 1):
                print(f"{'='*60}")
                print(f"📂 Processing folder {i}/{len(reduced_folders)}: {reduced_folder.name}")
                print(f"{'='*60}")
                
                # Create output folder next to the reduced folder
                if output_dir:
                    # If output_dir specified, create subfolder with reduced folder name
                    folder_output_dir = output_dir / reduced_folder.name
                else:
                    # Default: create _temporal_median folder next to reduced folder
                    folder_output_dir = reduced_folder.parent / (reduced_folder.name + "_temporal_median")
                
                result = process_temporal_median_all(
                    reduced_folder,
                    folder_output_dir,
                    args.temporal_window,
                    zone_name,
                    args.threads
                )
                
                if result == 0:
                    total_processed += 1
                else:
                    total_skipped += 1
                
                print()
            
            print(f"{'='*60}")
            print(f"✅ Batch processing complete!")
            print(f"   Processed: {total_processed}/{len(reduced_folders)} folders")
            if total_skipped > 0:
                print(f"   Skipped: {total_skipped} folders")
            print(f"{'='*60}")
            return 0
        else:
            # Single folder mode: process input_dir directly
            if output_dir is None:
                output_dir = input_dir.with_name(input_dir.name + "_temporal_median")
            
            zone_name = None if args.zone == "none" else args.zone
            return process_temporal_median_all(input_dir, output_dir, args.temporal_window, zone_name, args.threads)

    # Handle temporal mode (different processing)
    if args.temporal_mode:
        frames_dir = args.frames_dir or args.input_dir
        output_dir = args.output_dir or frames_dir.with_name(frames_dir.name + "_temporal")
        
        zone_name = None if args.zone == "none" else args.zone
        return process_temporal_consistency(frames_dir, output_dir, zone_name, args.temporal_output_median)

    input_dir: Path = args.input_dir
    output_dir: Optional[Path] = args.output_dir

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"❌ Input directory not found or not a folder: {input_dir}")
        return 1

    if output_dir is None:
        output_dir = input_dir.with_name(input_dir.name + "_preprocessed")

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"🔧 Preprocessing images for template matching")
    print(f"   Input : {input_dir}")
    print(f"   Output: {output_dir}")
    print(f"   Zone  : {args.zone}")
    print(f"   Scale : {args.scale}x")
    print(f"   CLAHE : {'on' if args.clahe else 'off'}")
    print(f"   Light text enhancement : {'on' if (args.enhance_light_text or args.zone == 'bottom_right') else 'off'}")
    print(f"   Morphological gradient : {'on' if args.morph_gradient else 'off'}")
    print(f"   Temporal mode : {'on' if args.temporal_mode else 'off'}")
    print()

    zone_name = None if args.zone == "none" else args.zone
    count = 0

    for img_path in iter_images(input_dir):
        rel = img_path.relative_to(input_dir)
        out_path = output_dir / rel
        out_path = out_path.with_suffix(args.ext)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        img = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
        if img is None:
            print(f"⚠️  Failed to read image: {img_path}")
            continue

        processed = preprocess_image(
            img, 
            zone_name=zone_name, 
            use_clahe=args.clahe, 
            scale=args.scale,
            enhance_light_text=args.enhance_light_text
        )

        if not cv2.imwrite(str(out_path), processed):
            print(f"⚠️  Failed to write: {out_path}")
            continue

        count += 1
        if count % 50 == 0:
            print(f"   Processed {count} images...")

    print(f"✅ Done. Processed {count} image(s).")
    print(f"   Output folder: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

