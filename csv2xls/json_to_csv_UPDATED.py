#!/usr/bin/env python3
"""
json_to_csv.py - Convert annotation JSON to CSV format
Replicates the exact logic from annotool-desktop_v2/js/exports.js

Usage:
  python json_to_csv.py <path>
  python json_to_csv.py <folder_with_jsons>
  python json_to_csv.py <folder> -o <output_folder>

  path: single JSON file or folder containing JSON files (*.json, *_ANNOTATIONS__*.json)
"""

# Minimum Screen Size % to include in CSV (annotations below this are skipped)
MIN_SCREEN_SIZE_PCT = 0.08

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Any, Tuple, List


def check_image_part(width: float, height: float, center_x: float, center_y: float) -> str:
    """Determine screen location based on center point.
    
    Replicates: function checkImagePart(a, b, c, d)
    Returns: "A", "B", "C", "D", or "E"
    """
    if center_x < width / 4:
        return "B" if center_y < height / 2 else "E"
    elif width / 4 <= center_x < width / 2:
        if center_y < height / 4:
            return "B"
        elif center_y >= 3 * height / 4:
            return "E"
        else:
            return "A"
    elif width / 2 <= center_x < 3 * width / 4:
        if center_y < height / 4:
            return "C"
        elif center_y >= 3 * height / 4:
            return "D"
        else:
            return "A"
    else:  # center_x >= 3 * width / 4
        return "C" if center_y < height / 2 else "D"


def hour24_to_secs(time_str: str) -> int:
    """Convert time string (HHMM or HH:MM) to seconds.
    
    Replicates: function hour24ToSecs(a)
    """
    if isinstance(time_str, (int, float)):
        time_str = str(int(time_str))
    else:
        time_str = str(time_str).replace(":", "")
    
    if len(time_str) >= 4:
        hours = int(time_str[:2])
        minutes = int(time_str[2:4])
        seconds = 0
        if len(time_str) >= 6:
            seconds = int(time_str[4:6]) if len(time_str) == 6 else 0
        return 3600 * hours + 60 * minutes + seconds
    return 0


def secs_to_hour24(seconds: int) -> str:
    """Convert seconds to HH:MM:SS format.
    
    Replicates: function secsToHour24(a)
    """
    if isinstance(seconds, str):
        seconds = int(seconds)
    
    hours = seconds // 3600
    minutes = (seconds - 3600 * hours) // 60
    secs = seconds - 3600 * hours - 60 * minutes
    
    hours_str = f"0{hours}" if hours < 10 else str(hours)
    minutes_str = f"0{minutes}" if minutes < 10 else str(minutes)
    secs_str = f"0{secs}" if secs < 10 else str(secs)
    
    return f"{hours_str}:{minutes_str}:{secs_str}"


def alphanum_key(key: str) -> Tuple:
    """Natural sort key function for alphanumeric sorting.
    
    Replicates alphanumCase sorting behavior.
    """
    def convert(text):
        return int(text) if text.isdigit() else text.lower()
    
    return [convert(c) for c in re.split('([0-9]+)', key)]


def to_number(value: Any, default: float = 0.0) -> float:
    """Safely convert nullable values to number."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def common_export_data(all_annotations: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Process annotations and create row data.
    
    Replicates: function commonExportData()
    Returns: Dictionary with keys like "offset::group::brand::tpoint"
    """
    # Extract project start time
    project = all_annotations.get("project", "")
    proj_arr = project.split("_")
    proj_start = proj_arr[-1] if proj_arr else "0000"
    
    try:
        start_seconds = hour24_to_secs(proj_start)
    except (ValueError, TypeError):
        start_seconds = 0
    
    # Get and sort image keys
    anno_imgs = list(all_annotations.get("images", {}).keys())
    anno_imgs.sort(key=alphanum_key)
    
    annorows = {}
    
    for img in anno_imgs:
        each_data = all_annotations["images"][img]
        X = to_number(each_data.get("width", 0), default=0.0)
        Y = to_number(each_data.get("height", 0), default=0.0)
        img_area = X * Y
        
        imgannos = each_data.get("annotations", [])
        n = 0 if len(imgannos) > 1 else 1  # solus
        
        # Get offset (frame number)
        try:
            offset = int(img)
        except (ValueError, TypeError):
            offset = each_data.get("imageIndex", 0)
        
        time_format = secs_to_hour24(start_seconds + offset)
        
        for anno in imgannos:
            gr = anno.get("group", "")
            br = anno.get("brand", "")
            tp = anno.get("tpoint", "")
            hts = to_number(anno.get("hits", 1), default=0.0)
            
            start = anno.get("startPoint", [0, 0])
            end = anno.get("diagPoint", [0, 0])
            
            # Calculate center point
            center_x = start[0] + round((end[0] - start[0]) / 2)
            center_y = start[1] + round((end[1] - start[1]) / 2)
            
            loc = check_image_part(X, Y, center_x, center_y)
            
            # Calculate box dimensions
            box_w = abs(end[0] - start[0])
            box_h = abs(end[1] - start[1])
            
            # Calculate size percentage
            if img_area <= 0:
                continue
            size_perc = round(box_w * box_h / img_area * 1e5) / 1e3
            
            # Skip annotations below minimum screen size
            if size_perc < MIN_SCREEN_SIZE_PCT:
                continue
            
            # Create key: offset::group::brand::tpoint
            key = f"{offset}::{gr}::{br}::{tp}"
            
            annorows[key] = {
                "group": gr,
                "brand": br,
                "tpoint": tp,
                "time": time_format,
                "duration": 1,
                "solus": n,
                "location": loc,
                "size": size_perc,
                "hits": hts,
                "avgHits": hts / 1,
                "frameNum": img,
                "annoTimeOffset": offset
            }
    
    return annorows


def generate_video_csv(all_annotations: Dict[str, Any], output_path: Path) -> None:
    """Generate Video CSV from annotations.
    
    Replicates: function generateVideoCSV()
    This function merges consecutive frames with the same group/brand/tpoint
    """
    # CSV header
    output = "Brand\tLocation\tTime the brand is at screen\tDuration\tScreen Location\tScreen Size %\tTotal Hits\tAverage Hits\tSequence Frame Number\n"
    
    # Get annotation rows
    annorows = common_export_data(all_annotations)
    
    # Sort keys
    annokeys = sorted(annorows.keys(), key=alphanum_key)
    
    # Merge consecutive frames with same group/brand/tpoint
    # This replicates the exact logic from exports.js lines 110-140
    prev = ""
    for i in range(len(annokeys)):
        if prev:
            current = annokeys[i]
            current_parts = current.split("::")
            prev_parts = prev.split("::")
            
            # Check if consecutive offsets
            try:
                current_offset = int(current_parts[0])
                prev_offset = int(prev_parts[0])
                
                if current_offset == prev_offset + 1:
                    # Check subsequent frames
                    for j in range(len(annokeys) - i):
                        if i + j >= len(annokeys):
                            break
                        
                        check_key = annokeys[i + j]
                        check_parts = check_key.split("::")
                        
                        try:
                            check_offset = int(check_parts[0])
                            if check_offset > current_offset:
                                break
                        except (ValueError, IndexError):
                            break
                        
                        # Check if previous has same group/brand/tpoint
                        prev_key_base = f"{prev_parts[0]}::{check_parts[1]}::{check_parts[2]}::{check_parts[3]}"
                        
                        if prev_key_base in annorows:
                            # Merge: update current with previous data
                            current_key_base = f"{check_parts[0]}::{check_parts[1]}::{check_parts[2]}::{check_parts[3]}"
                            
                            if current_key_base in annorows:
                                annorows[current_key_base]["frameNum"] = annorows[prev_key_base]["frameNum"]
                                annorows[current_key_base]["time"] = annorows[prev_key_base]["time"]
                                annorows[current_key_base]["hits"] += annorows[prev_key_base]["hits"]
                                annorows[current_key_base]["duration"] += annorows[prev_key_base]["duration"]
                                
                                avg_val = annorows[current_key_base]["hits"] / annorows[current_key_base]["duration"]
                                if round(avg_val) != avg_val:
                                    annorows[current_key_base]["avgHits"] = round(avg_val * 1000) / 1000
                                else:
                                    annorows[current_key_base]["avgHits"] = avg_val
                                
                                annorows[current_key_base]["location"] = annorows[prev_key_base]["location"]
                                annorows[current_key_base]["solus"] = annorows[prev_key_base]["solus"]
                                
                                # Delete previous
                                del annorows[prev_key_base]
            except (ValueError, IndexError):
                pass
        
        prev = annokeys[i]
    
    # Get final rows and sort
    finalrows = annorows
    finalkeys = sorted(finalrows.keys(), key=alphanum_key)
    
    # Generate CSV output
    for key in finalkeys:
        row = finalrows[key]
        brand = row["brand"]
        tpoint = row["tpoint"]
        time = row["time"]
        duration = row["duration"]
        location = row["location"]
        size = row["size"]
        hits = row["hits"]
        avg_hits = row["avgHits"]
        frame_num = row["frameNum"]
        
        # Format size to 3 decimal places
        size_str = f"{size:.3f}"
        
        # Format avg_hits
        if isinstance(avg_hits, float) and round(avg_hits) != avg_hits:
            avg_hits_str = f"{avg_hits:.3f}"
        else:
            avg_hits_str = str(int(avg_hits)) if isinstance(avg_hits, float) else str(avg_hits)
        
        # Format frame number
        try:
            frame_num_str = str(int(frame_num))
        except (ValueError, TypeError):
            frame_num_str = str(frame_num)
        
        output += f"{brand}\t{tpoint}\t{time}\t{duration}\t{location}\t{size_str}\t{hits}\t{avg_hits_str}\t{frame_num_str}\n"
    
    # Write to file
    output_path.write_text(output, encoding="utf-8")
    print(f"Video CSV saved to: {output_path}")


def process_one_json(
    json_path: Path, output_dir: Path, prefix_index: int | None = None
) -> bool:
    """Convert one JSON file to CSV. Returns True on success.

    prefix_index: if set (e.g. 100, 101, ...), output filename is part{N}_{stem}.csv
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            all_annotations = json.load(f)
    except Exception as e:
        print(f"  Error reading {json_path.name}: {e}")
        return False

    if "images" not in all_annotations:
        print(f"  Error: {json_path.name} missing 'images' key")
        return False

    base_name = (
        json_path.stem.replace("_ANNOTATIONS", "-ANNOTATIONS").replace("_temporal", "-temporal")
    )
    if prefix_index is not None:
        csv_name = f"part{prefix_index}_{base_name}"
    else:
        csv_name = base_name
    csv_path = output_dir / f"{csv_name}.csv"
    try:
        generate_video_csv(all_annotations, csv_path)
        print(f"  OK: {json_path.name} -> {len(all_annotations.get('images', {}))} images -> {csv_path.name}")
        return True
    except Exception as e:
        print(f"  Error converting {json_path.name}: {e}")
        return False


def collect_json_files(folder: Path) -> List[Path]:
    """Find JSON files in folder (annotation-style and plain .json)."""
    files = list(folder.glob("*_ANNOTATIONS__*.json"))
    if not files:
        files = list(folder.glob("*.json"))
    return sorted(files, key=lambda p: p.name)


def main():
    parser = argparse.ArgumentParser(
        description="Convert annotation JSON(s) to Video CSV format (exports.js logic)."
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Single JSON file or folder containing JSON files",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("csvs"),
        help="Output folder for CSV files (default: csvs)",
    )
    args = parser.parse_args()

    path = args.path.resolve()
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if path.is_file():
        if path.suffix.lower() != ".json":
            print("Error: input must be a .json file or a folder")
            return
        print(f"Input: {path.name}")
        ok = process_one_json(path, output_dir, prefix_index=100)
        print("Done." if ok else "Failed.")
        return

    if not path.is_dir():
        print(f"Error: path not found or not a file/folder: {path}")
        return

    json_files = collect_json_files(path)
    if not json_files:
        print(f"No JSON files found in: {path}")
        return

    print(f"Folder: {path}")
    print(f"Output: {output_dir}")
    print(f"Found {len(json_files)} JSON file(s)\n")

    ok_count = 0
    for i, jf in enumerate(json_files):
        if process_one_json(jf, output_dir, prefix_index=100 + i):
            ok_count += 1

    print(f"\nDone. {ok_count}/{len(json_files)} converted.")


if __name__ == "__main__":
    main()
