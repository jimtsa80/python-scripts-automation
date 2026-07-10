import os
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import argparse

def load_json(json_path):
    """Load annotation JSON file."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def find_image(image_name, images_folder):
    """Find the actual image file (handles different extensions)."""
    for ext in [".jpg", ".png", ".jpeg", ".bmp"]:
        img_path = os.path.join(images_folder, image_name + ext)
        if os.path.exists(img_path):
            return img_path
    return None

def scale_annotations(annotations, json_width, json_height, actual_width, actual_height):
    """Scale annotation coordinates to match the actual image size."""
    scale_x = actual_width / json_width
    scale_y = actual_height / json_height

    scaled_annotations = []
    for ann in annotations:
        start_x, start_y = ann["startPoint"]
        end_x, end_y = ann["diagPoint"]

        # Scale coordinates
        start_x *= scale_x
        start_y *= scale_y
        end_x *= scale_x
        end_y *= scale_y

        # Store updated annotation
        scaled_annotations.append({
            "startPoint": (start_x, start_y),
            "diagPoint": (end_x, end_y),
            "brand": ann["brand"],
            "tpoint": ann["tpoint"],
            "hits": ann["hits"]
        })

    return scaled_annotations

def draw_annotations(image_path, annotations, json_width, json_height, output_path):
    """Draw bounding boxes and labels on an image."""
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    actual_width, actual_height = image.size

    # Scale annotations to actual image size
    scaled_annotations = scale_annotations(annotations, json_width, json_height, actual_width, actual_height)

    # Try loading a default font, else use a basic one
    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except IOError:
        font = ImageFont.load_default()

    for ann in scaled_annotations:
        start_x, start_y = ann["startPoint"]
        end_x, end_y = ann["diagPoint"]

        # Ensure valid rectangle coordinates
        start_x, end_x = min(start_x, end_x), max(start_x, end_x)
        start_y, end_y = min(start_y, end_y), max(start_y, end_y)

        label = f"{ann['brand']} / {ann['tpoint']} ({ann['hits']} hits)"

        # Randomly generate a color based on brand name
        color = tuple(np.random.randint(0, 255, 3).tolist())

        # Draw bounding box
        draw.rectangle([start_x, start_y, end_x, end_y], outline=color, width=3)

        # Draw label background
        text_size = draw.textbbox((0, 0), label, font=font)
        text_width, text_height = text_size[2] - text_size[0], text_size[3] - text_size[1]
        draw.rectangle([start_x, start_y - text_height - 2, start_x + text_width + 4, start_y], fill=color)

        # Draw text
        draw.text((start_x + 2, start_y - text_height - 2), label, fill="white", font=font)

    # Save the modified image
    image.save(output_path)


def get_json_paths(input_path):
    """
    Return list of JSON file paths.
    If input_path is a .json file, return [input_path].
    If input_path is a folder, return all .json files inside it (one level).
    """
    input_path = os.path.abspath(input_path)
    if os.path.isfile(input_path):
        if input_path.lower().endswith(".json"):
            return [input_path]
        return []
    if os.path.isdir(input_path):
        return [
            os.path.join(input_path, f)
            for f in sorted(os.listdir(input_path))
            if f.lower().endswith(".json")
        ]
    return []


def cluster_suffix_from_json_path(json_path):
    """
    If the JSON filename contains the word 'cluster', return that part (e.g. 'cluster3').
    Otherwise return None.
    """
    base = os.path.splitext(os.path.basename(json_path))[0]
    lower = base.lower()
    if "cluster" not in lower:
        return None
    idx = lower.index("cluster")
    return base[idx:]  # e.g. cluster3, cluster_12


def process_images(json_path, images_folder, name_suffix=None):
    """
    Process images based on JSON annotations.
    If name_suffix is set (e.g. 'cluster3'), output image names become '5 - cluster3.png'.
    """
    data = load_json(json_path)

    output_folder = f"{images_folder}_annos"
    os.makedirs(output_folder, exist_ok=True)

    for image_name, details in data.get("images", {}).items():
        image_path = find_image(image_name, images_folder)
        if not image_path:
            print(f"Image not found: {image_name}")
            continue

        json_width, json_height = details["width"], details["height"]

        base = os.path.basename(image_path)
        name_no_ext, ext = os.path.splitext(base)
        if name_suffix:
            out_name = f"{name_no_ext} - {name_suffix}{ext}"
        else:
            out_name = base
        output_path = os.path.join(output_folder, out_name)

        draw_annotations(image_path, details.get("annotations", []), json_width, json_height, output_path)
        print(f"Annotated: {image_name} -> {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Annotate images based on JSON annotations. "
        "First argument: a .json file or a folder containing .json files."
    )
    parser.add_argument(
        "json_path",
        type=str,
        help="Path to a single JSON annotation file, or folder containing multiple .json files",
    )
    parser.add_argument("images_folder", type=str, help="Folder containing images")

    args = parser.parse_args()

    json_paths = get_json_paths(args.json_path)
    if not json_paths:
        print("No JSON file(s) found. First argument must be a .json file or a folder with .json files.")
        exit(1)

    print(f"Processing {len(json_paths)} JSON file(s)...")
    for jp in json_paths:
        suffix = cluster_suffix_from_json_path(jp)
        print(f"\n--- {os.path.basename(jp)} (output suffix: {suffix or 'none'}) ---")
        process_images(jp, args.images_folder, name_suffix=suffix)
