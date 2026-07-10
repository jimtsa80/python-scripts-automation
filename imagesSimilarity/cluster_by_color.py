import argparse
import csv
import os
import shutil

import cv2
import numpy as np
from sklearn.cluster import KMeans


VALID_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def list_images(folder):
    return [
        os.path.join(folder, name)
        for name in os.listdir(folder)
        if name.lower().endswith(VALID_EXTENSIONS)
    ]


def extract_hsv_histogram(img_bgr, h_bins=24, s_bins=6, v_bins=6):
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist(
        [hsv],
        [0, 1, 2],
        None,
        [h_bins, s_bins, v_bins],
        [0, 180, 0, 256, 0, 256],
    )
    hist = cv2.normalize(hist, None).flatten()
    return hist


def orange_ratio(img_bgr):
    """
    Returns the percentage of orange pixels in image using HSV thresholds.
    Hue in OpenCV HSV is [0..179].
    """
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    lower_orange = np.array([8, 70, 50], dtype=np.uint8)
    upper_orange = np.array([25, 255, 255], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower_orange, upper_orange)
    return float(np.count_nonzero(mask)) / float(mask.size)


def ensure_clean_dir(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(
        description="Cluster images by color distribution and report orange-heavy groups."
    )
    parser.add_argument("input_folder", help="Folder with images")
    parser.add_argument(
        "--clusters",
        type=int,
        default=8,
        help="Number of KMeans clusters (default: 8)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output folder for clustered images (default: <input_folder>/color_clusters)",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy files instead of moving them",
    )
    args = parser.parse_args()

    input_folder = os.path.abspath(args.input_folder)
    if not os.path.isdir(input_folder):
        raise FileNotFoundError(f"Input folder does not exist: {input_folder}")

    image_paths = list_images(input_folder)
    if not image_paths:
        raise RuntimeError(f"No images found in: {input_folder}")

    output_dir = args.output or os.path.join(input_folder, "color_clusters")
    output_dir = os.path.abspath(output_dir)
    ensure_clean_dir(output_dir)

    features = []
    orange_scores = []
    valid_paths = []

    print(f"Reading {len(image_paths)} images...")
    for path in image_paths:
        img = cv2.imread(path)
        if img is None:
            continue
        features.append(extract_hsv_histogram(img))
        orange_scores.append(orange_ratio(img))
        valid_paths.append(path)

    if not features:
        raise RuntimeError("No readable images were found.")

    X = np.array(features, dtype=np.float32)
    n_clusters = min(args.clusters, len(valid_paths))
    if n_clusters < 2:
        n_clusters = 1

    print(f"Clustering {len(valid_paths)} images into {n_clusters} clusters...")
    labels = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(X)

    rows = []
    cluster_orange = {}
    cluster_counts = {}
    for idx, path in enumerate(valid_paths):
        cluster_id = int(labels[idx])
        score = float(orange_scores[idx])
        cluster_orange[cluster_id] = cluster_orange.get(cluster_id, 0.0) + score
        cluster_counts[cluster_id] = cluster_counts.get(cluster_id, 0) + 1
        rows.append((os.path.basename(path), path, cluster_id, score))

    # Create cluster folders and place files
    for file_name, src_path, cluster_id, _ in rows:
        cluster_path = os.path.join(output_dir, f"cluster_{cluster_id:02d}")
        os.makedirs(cluster_path, exist_ok=True)
        dst = os.path.join(cluster_path, file_name)
        if args.copy:
            shutil.copy2(src_path, dst)
        else:
            shutil.move(src_path, dst)

    # Save a report CSV
    report_path = os.path.join(output_dir, "color_cluster_report.csv")
    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["file_name", "original_path", "cluster_id", "orange_ratio"])
        writer.writerows(rows)

    print("\nCluster orange intensity (average orange_ratio):")
    ranking = []
    for cluster_id, total_score in cluster_orange.items():
        avg_orange = total_score / cluster_counts[cluster_id]
        ranking.append((cluster_id, avg_orange, cluster_counts[cluster_id]))
    ranking.sort(key=lambda x: x[1], reverse=True)

    for cluster_id, avg_orange, count in ranking:
        print(
            f"cluster_{cluster_id:02d}: avg_orange={avg_orange:.4f} | images={count}"
        )

    if ranking:
        best_cluster = ranking[0][0]
        print(
            f"\nMost orange cluster: cluster_{best_cluster:02d} "
            f"({os.path.join(output_dir, f'cluster_{best_cluster:02d}')})"
        )
    print(f"\nDone. Report saved: {report_path}")


if __name__ == "__main__":
    main()
