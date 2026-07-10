#!/usr/bin/env python3
"""
OCR Brand Detector

This script uses OCR to detect brands in images and moves matching images
to a new folder named {parent_folder_name}_TVGIs.

The script automatically detects and processes folder structures with 1, 2, or 3 levels:
- 1 level: Images directly in the parent folder
- 2 levels: Parent folder -> subfolders with images
- 3 levels: Parent folder -> level1 folders -> level2 folders with images

For all folders with images, it collects all matched images into a single {parent_folder_name}_TVGIs folder.

Usage:
    python ocr_brands.py <parent_folder> <brands_file>

Example:
    python ocr_brands.py F:\downloads\Rugby OCR_brands.txt

Requires:
    pip install easyocr pillow
    OR
    pip install pytesseract pillow
    
Optional (for progress bars):
    pip install tqdm
    python ocr_brands.py F:\downloads\Rugby OCR_brands.txt --gpu --workers 4 --fuzzy-threshold 0.7 --min-confidence 0.4
"""

#python ocr_brands.py F:\downloads\toBeFinalized\ocr_icc  OCR_brands.txt --workers 2

import argparse
import re
import shutil
import time
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from difflib import SequenceMatcher
from multiprocessing import Pool, cpu_count
from functools import partial
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

# Suppress PyTorch RNN warnings from EasyOCR (known issue, doesn't affect functionality)
warnings.filterwarnings("ignore", message=".*RNN module weights are not part of single contiguous chunk.*")
warnings.filterwarnings("ignore", category=UserWarning, module="torch.nn.modules.rnn")

try:
    import easyocr
except ImportError:
    easyocr = None

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

try:
    import pytesseract
    from pytesseract import Output as TesseractOutput
except ImportError:
    pytesseract = None
    TesseractOutput = None

# Image suffixes we will consider
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff")


def sanitize_folder_name(name: str) -> str:
    """Make a filesystem-friendly folder name from a brand."""
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return sanitized or "brand"


def normalize_brand(name: str) -> str:
    """Normalize brand strings for comparison."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def load_brands_from_file(brands_file: Path) -> Tuple[Dict[str, str], Dict[str, Set[str]]]:
    """Load brands from txt file with alias support.
    
    Returns:
        Tuple of (brand_map: normalized -> canonical, alias_map: canonical -> set of normalized aliases)
    """
    brand_map: Dict[str, str] = {}
    alias_map: Dict[str, Set[str]] = {}

    def add_brand(raw_name: str, canonical_name: Optional[str] = None, register_alias: bool = True) -> None:
        canonical = canonical_name or raw_name
        normalized = normalize_brand(raw_name)
        if normalized and normalized not in brand_map:
            brand_map[normalized] = canonical
        alias_set = alias_map.setdefault(canonical, set())
        if register_alias and normalized:
            alias_set.add(normalized)

    def process_brand_entry(entry: str) -> bool:
        """Process a line that may contain alias mappings like 'Brand <= alias1, alias2'."""
        if not entry:
            return False
        canonical_part, sep, synonym_part = entry.partition("<=")
        canonical_name = canonical_part.strip()
        if not canonical_name:
            return False
        has_synonyms = bool(sep) and synonym_part.strip()
        add_brand(canonical_name, canonical_name, register_alias=not has_synonyms)
        if has_synonyms:
            synonyms = [
                syn.strip()
                for syn in re.split(r"[,\|]", synonym_part)
                if syn.strip()
            ]
            for synonym in synonyms:
                add_brand(synonym, canonical_name, register_alias=True)
        return True

    if not brands_file.exists():
        print(f"Warning: brands file not found: {brands_file}")
        return brand_map, alias_map

    try:
        for line in brands_file.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text or text.startswith("//"):
                continue
            if text.startswith("#"):
                body = text[1:].strip()
                if body:
                    processed = process_brand_entry(body)
                    if not processed:
                        add_brand(body, body, register_alias=True)
                continue
            if "<=" in text:
                processed = process_brand_entry(text)
                if processed:
                    continue
            else:
                # Treat plain lines as brands
                add_brand(text, text, register_alias=True)
    except Exception as exc:
        print(f"Error reading brands file: {exc}")

    return brand_map, alias_map


def check_brand_match(
    text: str, 
    brand_map: Dict[str, str], 
    alias_map: Dict[str, Set[str]],
    fuzzy_threshold: float = 0.92,
    min_length: int = 3
) -> Optional[str]:
    """Check if text matches any brand from the brand map.
    
    Args:
        text: Text to check
        brand_map: Map of normalized brand names to canonical names
        alias_map: Map of canonical names to sets of normalized aliases
        fuzzy_threshold: Minimum similarity ratio for fuzzy matching (default: 0.92)
        min_length: Minimum length for text to be considered (default: 3)
    
    Returns:
        Canonical brand name if match found, None otherwise
    """
    normalized_text = normalize_brand(text)
    if not normalized_text or len(normalized_text) < min_length:
        return None
    
    # Direct exact match
    if normalized_text in brand_map:
        return brand_map[normalized_text]
    
    # Check against all aliases with stricter matching
    for canonical, aliases in alias_map.items():
        for alias in aliases:
            if not alias or len(alias) < min_length:
                continue
                
            # Exact match
            if normalized_text == alias:
                return canonical
            
            # Fuzzy match with higher threshold (0.92 instead of 0.85)
            similarity = SequenceMatcher(None, normalized_text, alias).ratio()
            if similarity >= fuzzy_threshold:
                return canonical
            
            # Substring matching - only if one is significantly longer (at least 1.5x)
            # and the shorter one is at least 4 chars, and similarity is high
            len_ratio = max(len(normalized_text), len(alias)) / min(len(normalized_text), len(alias))
            if len_ratio >= 1.5 and min(len(normalized_text), len(alias)) >= 4:
                if alias in normalized_text or normalized_text in alias:
                    # Additional check: require high similarity even for substring matches
                    if similarity >= 0.88:
                        return canonical
    
    return None


def preprocess_image_for_ocr(image_path: Path, scale_factor: float = 2.5, verbose: bool = True) -> Optional[Any]:
    """Preprocess image to improve OCR accuracy for small text.
    
    Args:
        image_path: Path to image file
        scale_factor: Factor to upscale image (default: 2.5)
        verbose: Whether to print preprocessing steps (default: True)
    
    Returns:
        Preprocessed image array (numpy array) or None if preprocessing fails
    """
    if cv2 is None or np is None:
        if verbose:
            print(f"  [PREPRO] {image_path.name}: OpenCV not available, skipping preprocessing")
        return None
    
    try:
        if verbose:
            print(f"  [PREPRO] {image_path.name}: Starting preprocessing...")
        
        # Read image
        img = cv2.imread(str(image_path))
        if img is None:
            if verbose:
                print(f"  [PREPRO] {image_path.name}: Failed to read image")
            return None
        
        # Get original stats
        original_height, original_width = img.shape[:2]
        original_channels = img.shape[2] if len(img.shape) == 3 else 1
        if verbose:
            print(f"  [PREPRO] {image_path.name}: Original size: {original_width}x{original_height} ({original_channels} channels)")
        
        # 1. Upscale image (most important for small text)
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)
        img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        if verbose:
            print(f"  [PREPRO] {image_path.name}: ✓ Upscaled to {new_width}x{new_height} ({scale_factor}x)")
        
        # 2. Convert to grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            if verbose:
                print(f"  [PREPRO] {image_path.name}: ✓ Converted to grayscale")
        else:
            gray = img
        
        # Get stats before enhancement
        mean_before = np.mean(gray)
        std_before = np.std(gray)
        
        # 3. Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        mean_after_clahe = np.mean(gray)
        std_after_clahe = np.std(gray)
        if verbose:
            print(f"  [PREPRO] {image_path.name}: ✓ CLAHE contrast enhancement (brightness: {mean_before:.1f}→{mean_after_clahe:.1f}, contrast: {std_before:.1f}→{std_after_clahe:.1f})")
        
        # 4. Denoising
        gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
        if verbose:
            print(f"  [PREPRO] {image_path.name}: ✓ Denoising applied")
        
        # 5. Sharpening using unsharp mask
        gaussian = cv2.GaussianBlur(gray, (0, 0), 2.0)
        sharpened = cv2.addWeighted(gray, 1.5, gaussian, -0.5, 0)
        if verbose:
            print(f"  [PREPRO] {image_path.name}: ✓ Sharpening applied (unsharp mask)")
        
        # 6. Gamma correction to brighten dark text
        gamma = 1.3
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
        gamma_corrected = cv2.LUT(sharpened, table)
        mean_final = np.mean(gamma_corrected)
        std_final = np.std(gamma_corrected)
        if verbose:
            print(f"  [PREPRO] {image_path.name}: ✓ Gamma correction (γ=1.3) applied")
            print(f"  [PREPRO] {image_path.name}: Final stats - Brightness: {mean_final:.1f}, Contrast: {std_final:.1f}")
            print(f"  [PREPRO] {image_path.name}: ✓ Preprocessing complete!")
        
        return gamma_corrected
    except Exception as exc:
        if verbose:
            print(f"  [PREPRO] {image_path.name}: ✗ Preprocessing failed: {exc}")
        return None


def extract_text_with_ocr(
    image_path: Path, 
    ocr_reader: Optional[Any],
    min_confidence: float = 0.5,
    preprocess: bool = False
) -> List[str]:
    """Extract all text from image using OCR.
    
    Args:
        image_path: Path to image file
        ocr_reader: EasyOCR reader instance (if available)
        min_confidence: Minimum confidence threshold for OCR results (default: 0.5)
        preprocess: Whether to preprocess image before OCR (default: False)
    
    Returns:
        List of extracted text strings
    """
    texts = []
    
    # Preprocess image if requested
    preprocessed_img = None
    if preprocess:
        preprocessed_img = preprocess_image_for_ocr(image_path)
        if preprocessed_img is None:
            print(f"  [OCR] {image_path.name}: Preprocessing failed, using original image")
    
    # Try EasyOCR first
    if ocr_reader is not None:
        try:
            if preprocessed_img is not None:
                # Use preprocessed image with EasyOCR
                print(f"  [OCR] {image_path.name}: Running OCR on preprocessed image...")
                results = ocr_reader.readtext(preprocessed_img)
            else:
                # Use original image path
                if preprocess:
                    print(f"  [OCR] {image_path.name}: Running OCR on original image (preprocessing not applied)...")
                results = ocr_reader.readtext(str(image_path))
            
            for bbox, text, confidence in results:
                # Filter by confidence threshold
                if text and text.strip() and confidence >= min_confidence:
                    texts.append(text.strip())
        except Exception as exc:
            print(f"Warning: EasyOCR failed on {image_path.name}: {exc}")
    
    # Fallback to pytesseract
    if not texts and pytesseract is not None and TesseractOutput is not None:
        try:
            if preprocessed_img is not None:
                # Convert preprocessed numpy array to PIL Image
                pil_image = Image.fromarray(preprocessed_img)
            else:
                pil_image = Image.open(image_path)
            
            data = pytesseract.image_to_data(pil_image, output_type=TesseractOutput.DICT)
            n = len(data["text"])
            for i in range(n):
                text = data["text"][i].strip()
                conf = float(data["conf"][i]) if data["conf"][i] != "-1" else 0.0
                # pytesseract confidence is 0-100, convert to 0-1
                if text and conf / 100.0 >= min_confidence:
                    texts.append(text)
            
            # Close PIL image if we created it from preprocessed array
            if preprocessed_img is not None:
                pil_image.close()
        except Exception as exc:
            print(f"Warning: pytesseract failed on {image_path.name}: {exc}")
    
    return texts


def detect_brands_in_image(
    image_path: Path,
    brand_map: Dict[str, str],
    alias_map: Dict[str, Set[str]],
    ocr_reader: Optional[Any],
    fuzzy_threshold: float = 0.92,
    min_confidence: float = 0.5,
    min_word_length: int = 3,
    preprocess: bool = False
) -> List[str]:
    """Detect brands in an image using OCR.
    
    Args:
        image_path: Path to image file
        brand_map: Map of normalized brand names to canonical names
        alias_map: Map of canonical names to sets of normalized aliases
        ocr_reader: EasyOCR reader instance (if available)
        fuzzy_threshold: Minimum similarity ratio for fuzzy matching
        min_confidence: Minimum OCR confidence threshold
        min_word_length: Minimum word length to consider
        preprocess: Whether to preprocess image before OCR
    
    Returns:
        List of detected canonical brand names
    """
    detected_brands = set()
    
    # Extract all text from image
    texts = extract_text_with_ocr(image_path, ocr_reader, min_confidence, preprocess)
    
    # Check each text against brands
    for text in texts:
        # Check full text first (more reliable)
        brand = check_brand_match(text, brand_map, alias_map, fuzzy_threshold, min_word_length)
        if brand:
            detected_brands.add(brand)
            continue  # If full text matches, don't check words separately
        
        # Also check individual words (split by spaces and common separators)
        # Only if full text didn't match
        words = re.split(r'[\s\-_.,;:]+', text)
        for word in words:
            if len(word) >= min_word_length:
                brand = check_brand_match(word, brand_map, alias_map, fuzzy_threshold, min_word_length)
                if brand:
                    detected_brands.add(brand)
    
    return list(detected_brands)


def collect_images(folder: Path) -> List[Path]:
    """Collect all image files from folder."""
    if not folder.exists():
        raise FileNotFoundError(f"Image folder not found: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {folder}")
    
    images = sorted(
        [p for p in folder.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES]
    )
    return images


def collect_subfolders(parent_folder: Path) -> List[Path]:
    """Collect all subdirectories from parent folder."""
    if not parent_folder.exists():
        raise FileNotFoundError(f"Parent folder not found: {parent_folder}")
    if not parent_folder.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {parent_folder}")
    
    subfolders = sorted(
        [p for p in parent_folder.iterdir() if p.is_dir()]
    )
    return subfolders


def detect_folder_structure(parent_folder: Path) -> Tuple[int, List[Path]]:
    """Detect folder structure depth and return image folders to process.
    
    Returns:
        Tuple of (depth: int, image_folders: List[Path])
        depth: 1 = images in parent, 2 = images in subfolders, 3 = images in sub-subfolders
    """
    # Check if parent folder has images directly (1 level)
    images_in_parent = collect_images(parent_folder)
    if images_in_parent:
        return (1, [parent_folder])
    
    # Check level 1 subfolders
    level1_folders = collect_subfolders(parent_folder)
    if not level1_folders:
        return (0, [])  # No structure found
    
    # Check if level 1 folders have images directly (2 levels)
    level1_with_images = []
    level2_folders = []
    
    for level1_folder in level1_folders:
        images = collect_images(level1_folder)
        if images:
            level1_with_images.append(level1_folder)
        else:
            # Check for level 2 subfolders (3 levels)
            try:
                subfolders = collect_subfolders(level1_folder)
                for subfolder in subfolders:
                    sub_images = collect_images(subfolder)
                    if sub_images:
                        level2_folders.append((level1_folder, subfolder))
            except Exception:
                pass
    
    if level1_with_images:
        # 2 levels: parent -> level1 (with images)
        return (2, level1_with_images)
    elif level2_folders:
        # 3 levels: parent -> level1 -> level2 (with images)
        # Return tuples of (level1, level2) for processing
        return (3, level2_folders)
    else:
        return (0, [])


def format_time(seconds: float) -> str:
    """Format seconds into human-readable time string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"


def check_gpu_available() -> Tuple[bool, Optional[str]]:
    """Check if GPU is available for EasyOCR.
    
    Returns:
        Tuple of (gpu_available: bool, gpu_name: Optional[str])
    """
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            return True, gpu_name
        return False, None
    except ImportError:
        return False, None


def init_ocr_reader(use_gpu: Optional[bool] = None, force_cpu: bool = False) -> Optional[Any]:
    """Initialize EasyOCR reader with automatic GPU detection.
    
    Args:
        use_gpu: If True, use GPU; if False, use CPU; if None, auto-detect
        force_cpu: If True, force CPU even if GPU is available
    
    Returns:
        EasyOCR reader instance or None
    """
    if easyocr is None:
        return None
    
    # Check if GPU is available
    gpu_available, gpu_name = check_gpu_available()
    
    # Determine whether to use GPU
    if force_cpu:
        use_gpu_final = False
    elif use_gpu is None:
        # Auto-detect: use GPU if available
        use_gpu_final = gpu_available
    else:
        # User explicitly requested GPU or CPU
        use_gpu_final = use_gpu and gpu_available
        if use_gpu and not gpu_available:
            print("Warning: --gpu flag set but no GPU detected, falling back to CPU")
    
    try:
        reader = easyocr.Reader(["en"], gpu=use_gpu_final)
        if use_gpu_final:
            print(f"EasyOCR initialized with GPU acceleration ({gpu_name})")
        else:
            if gpu_available and not force_cpu:
                print(f"EasyOCR initialized with CPU (GPU available: {gpu_name}, use --gpu to enable)")
            else:
                print("EasyOCR initialized with CPU")
        return reader
    except Exception as exc:
        print(f"Warning: could not initialize EasyOCR reader: {exc}")
        if use_gpu_final:
            print("Attempting to initialize EasyOCR with CPU as fallback...")
            try:
                return easyocr.Reader(["en"], gpu=False)
            except Exception:
                pass
    return None


# Global variable for OCR reader (initialized per worker process)
_worker_ocr_reader = None
_worker_use_gpu = False

def _init_worker(use_gpu: bool, force_cpu: bool):
    """Initialize worker process with OCR reader."""
    global _worker_ocr_reader, _worker_use_gpu
    _worker_use_gpu = use_gpu
    if easyocr is not None:
        try:
            gpu_available = False
            if use_gpu and not force_cpu:
                gpu_available, _ = check_gpu_available()
            _worker_ocr_reader = easyocr.Reader(["en"], gpu=gpu_available)
        except Exception:
            _worker_ocr_reader = None
    else:
        _worker_ocr_reader = None


def process_single_image(
    args_tuple: Tuple[Path, Dict[str, str], Dict[str, Set[str]], float, float, int, Path, str, bool]
) -> Tuple[Path, List[str], bool]:
    """Process a single image (for multiprocessing).
    
    Returns:
        Tuple of (image_path, detected_brands, is_match)
    """
    global _worker_ocr_reader
    image_path, brand_map, alias_map, fuzzy_threshold, min_confidence, min_word_length, output_folder, subfolder_name, preprocess = args_tuple
    
    detected_brands = detect_brands_in_image(
        image_path, brand_map, alias_map, _worker_ocr_reader,
        fuzzy_threshold, min_confidence, min_word_length, preprocess
    )
    
    is_match = len(detected_brands) > 0
    if is_match:
        # Move image to single output folder with original filename
        dest_path = output_folder / image_path.name
        # Handle filename conflicts by adding subfolder prefix only if file exists
        if dest_path.exists():
            filename = f"{subfolder_name}_{image_path.name}"
            dest_path = output_folder / filename
        shutil.move(str(image_path), str(dest_path))
    
    return (image_path, detected_brands, is_match)


def process_single_image_threaded(
    image_path: Path,
    brand_map: Dict[str, str],
    alias_map: Dict[str, Set[str]],
    ocr_reader: Optional[Any],
    fuzzy_threshold: float,
    min_confidence: float,
    min_word_length: int,
    output_folder: Path,
    subfolder_name: str,
    preprocess: bool = False
) -> Tuple[Path, List[str], bool]:
    """Process a single image (for threading - shares OCR reader).
    
    Returns:
        Tuple of (image_path, detected_brands, is_match)
    """
    detected_brands = detect_brands_in_image(
        image_path, brand_map, alias_map, ocr_reader,
        fuzzy_threshold, min_confidence, min_word_length, preprocess
    )
    
    is_match = len(detected_brands) > 0
    if is_match:
        # Move image to single output folder with original filename
        dest_path = output_folder / image_path.name
        # Handle filename conflicts by adding subfolder prefix only if file exists
        if dest_path.exists():
            filename = f"{subfolder_name}_{image_path.name}"
            dest_path = output_folder / filename
        shutil.move(str(image_path), str(dest_path))
    
    return (image_path, detected_brands, is_match)


def process_folder(
    image_folder: Path,
    brand_map: Dict[str, str],
    alias_map: Dict[str, Set[str]],
    ocr_reader: Optional[Any],
    parent_folder: Path,
    fuzzy_threshold: float = 0.92,
    min_confidence: float = 0.5,
    min_word_length: int = 3,
    num_workers: int = 3,
    force_cpu: bool = False,
    use_multiprocessing: bool = False,
    preprocess: bool = False
) -> Tuple[int, int]:
    """Process a single folder of images (level 2 folder).
    
    Args:
        parent_folder: The parent folder Path (input folder) - output folder will be created relative to this
    
    Returns:
        Tuple of (matched_count, total_count)
    """
    try:
        images = collect_images(image_folder)
    except Exception as exc:
        print(f"Error loading images from {image_folder}: {exc}")
        return 0, 0
    
    if not images:
        print(f"    No images found in folder: {image_folder.name}")
        return 0, 0
    
    # Create output folder inside parent_folder
    # Single folder for all matched images from all subfolders: {parent_folder_name}-TVGIs
    # Output folder is created at the same level as the subfolders being analyzed
    folder_name = image_folder.name
    output_folder = parent_folder / f"{parent_folder.name}-TVGIs"
    output_folder.mkdir(parents=True, exist_ok=True)
    
    total_count = len(images)
    matched_count = 0
    
    # Start timing for this folder
    folder_start_time = time.time()
    
    # Setup progress bar
    if tqdm is not None:
        pbar = tqdm(total=total_count, desc=f"    {folder_name[:40]:<40}", 
                   unit="img", leave=True, ncols=100)
    else:
        pbar = None
        print(f"    Processing {total_count} images in '{folder_name}'...")
    
    if num_workers > 1 and len(images) > 1:
        # Use threading (shares OCR reader) or multiprocessing
        # Threading is better for I/O-bound tasks and when sharing GPU resources
        # Multiprocessing is better for CPU-bound tasks but requires per-process OCR initialization
        use_threading = not use_multiprocessing  # Use threading by default (more efficient for OCR with shared reader)
        
        process_start_time = time.time()
        
        if use_threading:
            # Threading: share the same OCR reader across threads
            # This is more efficient for EasyOCR as it can share GPU memory
            # Limit threading workers to prevent system overload
            # EasyOCR reader sharing may cause issues with too many threads
            safe_thread_workers = min(num_workers, 2)
            if num_workers > safe_thread_workers:
                print(f"        Note: Limiting threading workers to {safe_thread_workers} to prevent system overload")
            with ThreadPoolExecutor(max_workers=safe_thread_workers) as executor:
                # Submit all tasks
                future_to_image = {
                    executor.submit(
                        process_single_image_threaded,
                        img, brand_map, alias_map, ocr_reader,
                        fuzzy_threshold, min_confidence, min_word_length, output_folder, folder_name, preprocess
                    ): img
                    for img in images
                }
                
                # Process results as they complete
                if pbar is not None:
                    results = []
                    for future in as_completed(future_to_image):
                        try:
                            result = future.result()
                            results.append(result)
                            image_path, detected_brands, is_match = result
                            if is_match:
                                matched_count += 1
                                pbar.set_postfix({"Match": f"{matched_count}/{len(results)}", 
                                                "Brands": ', '.join(detected_brands[:2])})
                            pbar.update(1)
                        except Exception as exc:
                            image_path = future_to_image[future]
                            print(f"      Error processing {image_path.name}: {exc}")
                else:
                    results = []
                    for i, future in enumerate(as_completed(future_to_image), 1):
                        try:
                            image_path, detected_brands, is_match = future.result()
                            results.append((image_path, detected_brands, is_match))
                            if is_match:
                                matched_count += 1
                                print(f"      [{i}/{total_count}] {image_path.name} ✓ MATCH - Brands: {', '.join(detected_brands)}")
                            else:
                                print(f"      [{i}/{total_count}] {image_path.name} ✗ No match")
                        except Exception as exc:
                            image_path = future_to_image[future]
                            print(f"      [{i}/{total_count}] Error processing {image_path.name}: {exc}")
        else:
            # Multiprocessing: initialize OCR reader per worker process
            # For EasyOCR, we need to initialize per worker
            # Note: Each worker process can use GPU independently
            use_gpu_for_workers = False
            if ocr_reader is not None and not force_cpu:
                # Check if main process is using GPU
                gpu_available, _ = check_gpu_available()
                # Use GPU in workers if available (each process gets its own GPU context)
                use_gpu_for_workers = gpu_available
                # Note: With multiple workers, GPU memory might be limited, so we could limit workers
                # But for now, let each worker try to use GPU
            
            process_args = [
                (img, brand_map, alias_map, fuzzy_threshold, min_confidence, min_word_length, output_folder, folder_name, preprocess)
                for img in images
            ]
            
            # Initialize workers with OCR reader
            # Limit multiprocessing workers to prevent GPU memory issues
            safe_mp_workers = min(num_workers, 2)
            if num_workers > safe_mp_workers:
                print(f"        Note: Limiting multiprocessing workers to {safe_mp_workers} to prevent GPU memory issues")
            with Pool(processes=safe_mp_workers, initializer=_init_worker, initargs=(use_gpu_for_workers, force_cpu)) as pool:
                # Use imap for progress tracking
                if pbar is not None:
                    results = []
                    for result in pool.imap(process_single_image, process_args):
                        results.append(result)
                        image_path, detected_brands, is_match = result
                        if is_match:
                            matched_count += 1
                            pbar.set_postfix({"Match": f"{matched_count}/{pbar.n+1}", 
                                            "Brands": ', '.join(detected_brands[:2])})
                        pbar.update(1)
                else:
                    results = pool.map(process_single_image, process_args)
                    for i, (image_path, detected_brands, is_match) in enumerate(results, 1):
                        if is_match:
                            matched_count += 1
                            print(f"      [{i}/{total_count}] {image_path.name} ✓ MATCH - Brands: {', '.join(detected_brands)}")
                        else:
                            print(f"      [{i}/{total_count}] {image_path.name} ✗ No match")
        
        process_elapsed = time.time() - process_start_time
        
        # Calculate timing
        avg_time_per_image = process_elapsed / total_count if total_count > 0 else 0
        folder_elapsed = time.time() - folder_start_time
        if pbar is not None:
            pbar.set_postfix({"Time": format_time(process_elapsed), 
                            "Avg": format_time(avg_time_per_image)})
            pbar.close()
        else:
            method = "threading" if use_threading else "multiprocessing"
            print(f"        [Processed in {format_time(process_elapsed)}, "
                  f"avg: {format_time(avg_time_per_image)}/image with {num_workers} workers ({method})]")
    else:
        # Sequential processing with time tracking
        image_times = []
        for i, image_path in enumerate(images, 1):
            image_start_time = time.time()
            
            if pbar is not None:
                pbar.set_description(f"    {folder_name[:35]:<35} | {image_path.name[:20]}")
            else:
                print(f"      [{i}/{total_count}] {image_path.name}...", end=" ", flush=True)
            
            detected_brands = detect_brands_in_image(
                image_path, brand_map, alias_map, ocr_reader,
                fuzzy_threshold, min_confidence, min_word_length, preprocess
            )
            
            if detected_brands:
                # Move image to single output folder with original filename
                dest_path = output_folder / image_path.name
                # Handle filename conflicts by adding subfolder prefix only if file exists
                if dest_path.exists():
                    filename = f"{folder_name}_{image_path.name}"
                    dest_path = output_folder / filename
                shutil.move(str(image_path), str(dest_path))
                matched_count += 1
                if pbar is not None:
                    pbar.set_postfix({"Match": f"{matched_count}/{i}", 
                                    "Brands": ', '.join(detected_brands[:2])})
                else:
                    print(f"✓ MATCH - Brands: {', '.join(detected_brands)}")
            else:
                if pbar is not None:
                    pbar.set_postfix({"Match": f"{matched_count}/{i}"})
                else:
                    print("✗ No match")
            
            image_elapsed = time.time() - image_start_time
            image_times.append(image_elapsed)
            
            if pbar is not None:
                # Update progress bar with timing info
                avg_time = sum(image_times) / len(image_times)
                remaining = avg_time * (total_count - i)
                pbar.set_postfix({
                    "Match": f"{matched_count}/{i}",
                    "ETA": format_time(remaining) if remaining > 0 else "0s",
                    "Avg": format_time(avg_time)
                })
                pbar.update(1)
            else:
                # Calculate and display time estimates (old way)
                if i > 0:
                    avg_time_per_image = sum(image_times) / len(image_times)
                    remaining_images = total_count - i
                    estimated_remaining = avg_time_per_image * remaining_images
                    
                    if i % 5 == 0 or i == total_count:  # Update every 5 images or on last image
                        elapsed_so_far = time.time() - folder_start_time
                        print(f"        [Time: {format_time(elapsed_so_far)} elapsed, "
                              f"~{format_time(estimated_remaining)} remaining, "
                              f"avg: {format_time(avg_time_per_image)}/image]")
        
        folder_elapsed = time.time() - folder_start_time
        avg_time_per_image = sum(image_times) / len(image_times) if image_times else 0
        
        if pbar is not None:
            pbar.set_postfix({"Match": f"{matched_count}/{total_count}", 
                            "Time": format_time(folder_elapsed)})
            pbar.close()
    
    # Print folder summary with timing
    folder_elapsed = time.time() - folder_start_time
    print(f"    '{folder_name}': {matched_count}/{total_count} images matched "
          f"in {format_time(folder_elapsed)} "
          f"(avg: {format_time(avg_time_per_image)}/image)")
    return matched_count, total_count


def main():
    parser = argparse.ArgumentParser(
        description="Detect brands in images using OCR and move matching images to {folder_name}_TVGIs"
    )
    parser.add_argument(
        "parent_folder",
        help="Path to parent folder containing 2 levels of subfolders (level 1 -> level 2 with images)"
    )
    parser.add_argument(
        "brands_file",
        help="Path to brands txt file"
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="Force use GPU acceleration for EasyOCR (GPU is auto-detected by default)"
    )
    parser.add_argument(
        "--no-gpu",
        action="store_true",
        dest="force_cpu",
        help="Force CPU usage even if GPU is available"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help=f"Number of parallel workers for image processing (default: 1, recommended: 2-4, max: {cpu_count()})"
    )
    parser.add_argument(
        "--fuzzy-threshold",
        type=float,
        default=0.92,
        help="Fuzzy matching threshold (0.0-1.0, higher = stricter, default: 0.92)"
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.5,
        help="Minimum OCR confidence threshold (0.0-1.0, higher = stricter, default: 0.5)"
    )
    parser.add_argument(
        "--min-word-length",
        type=int,
        default=3,
        help="Minimum word length to consider for matching (default: 3)"
    )
    parser.add_argument(
        "--use-multiprocessing",
        action="store_true",
        help="Use multiprocessing instead of threading (default: uses threading for better OCR performance)"
    )
    parser.add_argument(
        "--prepro",
        action="store_true",
        help="Preprocess images before OCR (upscales, enhances contrast, sharpens) - improves accuracy for small text"
    )
    args = parser.parse_args()
    
    parent_folder = Path(args.parent_folder)
    brands_file = Path(args.brands_file)
    
    # Validate inputs
    if not brands_file.exists():
        print(f"Error: brands file not found: {brands_file}")
        return 1
    
    # Validate and adjust workers with safer limits to prevent system overload
    # Threading: max 2 workers (EasyOCR reader sharing may not be fully thread-safe)
    # Multiprocessing: max 2 workers (GPU memory limits)
    if args.use_multiprocessing:
        max_safe_workers = min(2, cpu_count())
    else:
        max_safe_workers = min(2, cpu_count())  # Conservative limit for threading
    
    num_workers = max(1, min(args.workers, max_safe_workers))
    if args.workers > max_safe_workers:
        method = "multiprocessing" if args.use_multiprocessing else "threading"
        print(f"Warning: Limited workers from {args.workers} to {num_workers} to prevent system overload ({method} mode)")
        print(f"         If your PC is still slow, use --workers 1 to disable parallel processing")
    
    # Validate thresholds
    fuzzy_threshold = max(0.0, min(1.0, args.fuzzy_threshold))
    min_confidence = max(0.0, min(1.0, args.min_confidence))
    min_word_length = max(2, args.min_word_length)
    
    # Detect folder structure
    try:
        depth, image_folders = detect_folder_structure(parent_folder)
    except Exception as exc:
        print(f"Error detecting folder structure: {exc}")
        return 1
    
    if depth == 0:
        print(f"Error: No images found in folder structure: {parent_folder}")
        return 1
    
    print(f"Detected {depth}-level folder structure")
    if depth == 1:
        print(f"Processing images directly in: {parent_folder}")
    elif depth == 2:
        print(f"Found {len(image_folders)} folders with images (2-level structure)")
    elif depth == 3:
        print(f"Found {len(image_folders)} folders with images (3-level structure)")
    
    # Load brands
    brand_map, alias_map = load_brands_from_file(brands_file)
    if not brand_map:
        print("Warning: No brands loaded from file. All images will be copied.")
    else:
        print(f"Loaded {len(set(brand_map.values()))} brands from {brands_file}")
    
    # Initialize OCR (auto-detect GPU by default)
    use_gpu_arg = args.gpu if args.gpu else None  # None = auto-detect
    ocr_reader = init_ocr_reader(use_gpu=use_gpu_arg, force_cpu=args.force_cpu)
    if ocr_reader is None and pytesseract is None:
        print("Error: Neither EasyOCR nor pytesseract is available.")
        print("Please install one of them:")
        print("  pip install easyocr")
        print("  OR")
        print("  pip install pytesseract")
        return 1
    
    if ocr_reader is None:
        print("EasyOCR not available, using pytesseract")
    else:
        print("Using EasyOCR for text extraction")
    
    # Check if preprocessing is requested but opencv is not available
    if args.prepro and (cv2 is None or np is None):
        print("Warning: --prepro flag set but OpenCV (cv2) is not available.")
        print("         Preprocessing will be skipped. Install OpenCV with: pip install opencv-python")
        args.prepro = False  # Disable preprocessing if not available
    
    print(f"\nSettings:")
    print(f"  Fuzzy threshold: {fuzzy_threshold}")
    print(f"  Min OCR confidence: {min_confidence}")
    print(f"  Min word length: {min_word_length}")
    print(f"  Workers: {num_workers}")
    print(f"  Preprocessing: {'Enabled' if args.prepro else 'Disabled'}")
    if args.prepro:
        print(f"\nPreprocessing steps (applied to each image):")
        print(f"  1. Upscale image by 2.5x (LANCZOS4 interpolation)")
        print(f"  2. Convert to grayscale")
        print(f"  3. Apply CLAHE contrast enhancement")
        print(f"  4. Apply denoising filter")
        print(f"  5. Apply sharpening (unsharp mask)")
        print(f"  6. Apply gamma correction (γ=1.3)")
        print(f"  Note: Detailed preprocessing info will be shown for each image\n")
    
    # Process folders based on detected structure
    total_matched = 0
    total_images = 0
    total_folders_processed = 0
    overall_start_time = time.time()
    
    print(f"\n{'='*60}")
    print(f"Processing {len(image_folders)} folder(s) with images...")
    print(f"{'='*60}")
    
    # Overall progress bar for folders
    if tqdm is not None:
        overall_pbar = tqdm(total=len(image_folders), desc="Overall Progress", 
                           unit="folder", position=0, leave=True, ncols=100)
    else:
        overall_pbar = None
    
    if depth == 1:
        # 1 level: process images directly in parent folder
        image_folder = image_folders[0]
        if overall_pbar is not None:
            overall_pbar.set_description(f"Processing: {image_folder.name[:50]}")
        else:
            print(f"\nProcessing folder: {image_folder.name}")
        
        matched, total = process_folder(
            image_folder, brand_map, alias_map, ocr_reader, parent_folder,
            fuzzy_threshold, min_confidence, min_word_length, num_workers, args.force_cpu, args.use_multiprocessing, args.prepro
        )
        total_matched += matched
        total_images += total
        if total > 0:
            total_folders_processed += 1
        
        if overall_pbar is not None:
            overall_pbar.set_postfix({"Matched": f"{total_matched}/{total_images}"})
            overall_pbar.update(1)
    
    elif depth == 2:
        # 2 levels: parent -> folders with images
        for i, image_folder in enumerate(image_folders, 1):
            if overall_pbar is not None:
                overall_pbar.set_description(f"Processing: {image_folder.name[:50]}")
            else:
                print(f"\n[{i}/{len(image_folders)}] Processing folder: {image_folder.name}")
            
            matched, total = process_folder(
                image_folder, brand_map, alias_map, ocr_reader, parent_folder,
                fuzzy_threshold, min_confidence, min_word_length, num_workers, args.force_cpu, args.use_multiprocessing, args.prepro
            )
            total_matched += matched
            total_images += total
            if total > 0:
                total_folders_processed += 1
            
            if overall_pbar is not None:
                overall_pbar.set_postfix({"Matched": f"{total_matched}/{total_images}", 
                                       "Folders": f"{total_folders_processed}"})
                overall_pbar.update(1)
    
    elif depth == 3:
        # 3 levels: parent -> level1 -> level2 (with images)
        for i, (level1_folder, level2_folder) in enumerate(image_folders, 1):
            if overall_pbar is not None:
                overall_pbar.set_description(f"L1: {level1_folder.name[:25]:<25} | L2: {level2_folder.name[:25]}")
            else:
                print(f"\n[{i}/{len(image_folders)}] L1: {level1_folder.name} | L2: {level2_folder.name}")
            
            matched, total = process_folder(
                level2_folder, brand_map, alias_map, ocr_reader, parent_folder.name,
                fuzzy_threshold, min_confidence, min_word_length, num_workers, args.force_cpu, args.use_multiprocessing, args.prepro
            )
            total_matched += matched
            total_images += total
            if total > 0:
                total_folders_processed += 1
            
            if overall_pbar is not None:
                overall_pbar.set_postfix({"Matched": f"{total_matched}/{total_images}", 
                                       "Folders": f"{total_folders_processed}"})
                overall_pbar.update(1)
    
    if overall_pbar is not None:
        overall_pbar.close()
    
    overall_elapsed = time.time() - overall_start_time
    
    print(f"\n{'='*60}")
    print(f"Processing complete!")
    print(f"Folder structure: {depth}-level")
    print(f"Folders processed: {total_folders_processed}")
    print(f"Total images: {total_images}")
    print(f"Images with brands: {total_matched}")
    print(f"Total time: {format_time(overall_elapsed)}")
    if total_images > 0:
        avg_time_per_image = overall_elapsed / total_images
        print(f"Average time per image: {format_time(avg_time_per_image)}")
    print(f"{'='*60}")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

