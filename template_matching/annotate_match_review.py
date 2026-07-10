#!/usr/bin/env python3
"""Annotate all frames in a URC match reduced folder (hit=green box, miss=label)."""
import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).parent))
from urc_template_matcher import (
    load_templates,
    resolve_urc_templates_dir,
    detect_urc_in_region,
    load_brand_mapping,
    annotate_image,
    DEFAULT_THRESHOLD,
    BRAND_MIN_CONFIDENCE,
    find_cluster_folders,
    find_reduced_folder,
    is_match_folder,
)

NO_HIT_COLOR = (0, 0, 255)  # BGR red


def annotate_miss(image_path: Path, output_path: Path) -> None:
    image = cv2.imread(str(image_path))
    if image is None:
        return
    h, w = image.shape[:2]
    label = "NO URC HIT"
    cv2.putText(
        image, label, (12, h - 18),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, NO_HIT_COLOR, 2,
    )
    cv2.imwrite(str(output_path), image)


def process_match(reduced_folder: Path, output_dir: Path, workers: int = 1) -> None:
    script_dir = Path(__file__).parent
    templates = load_templates(resolve_urc_templates_dir(script_dir, None))
    brand_mapping = load_brand_mapping(script_dir / "urc_brand_mapping.txt")
    min_conf = BRAND_MIN_CONFIDENCE.get("urc", 0.26)

    clusters = find_cluster_folders(reduced_folder)
    if not clusters:
        print(f"No clusters in {reduced_folder}")
        return

    hits_file = output_dir / "marked_frames_HITS.txt"
    misses_file = output_dir / "marked_frames_MISSES.txt"
    summary_file = output_dir / "marked_frames_SUMMARY.txt"

    hits_lines: list[str] = []
    misses_lines: list[str] = []
    total = 0
    hit_count = 0

    for cluster in clusters:
        cluster_out = output_dir / "annotated" / cluster.name
        cluster_out.mkdir(parents=True, exist_ok=True)
        images = sorted(cluster.glob("*.jpg"))
        print(f"Cluster {cluster.name}: {len(images)} image(s)")

        for img_path in images:
            total += 1
            dets = detect_urc_in_region(
                img_path,
                templates,
                DEFAULT_THRESHOLD,
                False,
                brand_mapping,
                min_conf,
                0.4,
                10,
            )
            out_path = cluster_out / img_path.name
            rel = f"{cluster.name}/{img_path.name}"

            if dets:
                hit_count += 1
                conf = dets[0][4]
                hits_lines.append(f"{rel}\t{conf:.4f}")
                annotate_image(img_path, dets, out_path)
            else:
                misses_lines.append(rel)
                annotate_miss(img_path, out_path)

    hits_file.write_text("\n".join(hits_lines) + ("\n" if hits_lines else ""), encoding="utf-8")
    misses_file.write_text("\n".join(misses_lines) + ("\n" if misses_lines else ""), encoding="utf-8")
    summary = (
        f"Match reduced folder: {reduced_folder}\n"
        f"Threshold: {DEFAULT_THRESHOLD}\n"
        f"Min confidence: {min_conf}\n"
        f"Total images: {total}\n"
        f"Marked (green box): {hit_count}\n"
        f"No hit (red label): {total - hit_count}\n"
        f"Hit rate: {100 * hit_count / total:.1f}%\n"
        f"\nAnnotated images: {output_dir / 'annotated'}\n"
        f"Hits list: {hits_file.name}\n"
        f"Misses list: {misses_file.name}\n"
    )
    summary_file.write_text(summary, encoding="utf-8")
    print(summary)


def main() -> int:
    parser = argparse.ArgumentParser(description="Annotate all URC match frames for review")
    parser.add_argument("path", type=Path, help="Match folder or reduced_* folder")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: urc_output/<match>_review)",
    )
    args = parser.parse_args()

    path = args.path
    if path.is_dir() and path.name.startswith("reduced_"):
        reduced = path
        match_name = path.name.replace("reduced_", "", 1)
    elif is_match_folder(path):
        reduced = find_reduced_folder(path)
        match_name = path.name
    else:
        print(f"Not a match/reduced folder: {path}")
        return 1

    if reduced is None:
        print("No reduced_* folder found")
        return 1

    out = args.output_dir or (Path(__file__).parent / "urc_output" / f"{match_name}_review")
    out.mkdir(parents=True, exist_ok=True)
    process_match(reduced, out)
    print(f"Done. Output: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
