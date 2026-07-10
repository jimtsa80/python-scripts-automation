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

def process_images(json_path, images_folder):
    """Process images based on JSON annotations."""
    data = load_json(json_path)

    # Define output folder
    output_folder = f"{images_folder}_annos"
    os.makedirs(output_folder, exist_ok=True)

    for image_name, details in data.get("images", {}).items():
        image_path = find_image(image_name, images_folder)
        if not image_path:
            print(f"Image not found: {image_name}")
            continue

        json_width, json_height = details["width"], details["height"]
        output_path = os.path.join(output_folder, os.path.basename(image_path))

        draw_annotations(image_path, details.get("annotations", []), json_width, json_height, output_path)
        print(f"Annotated: {image_name} -> {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Annotate images based on JSON annotations.")
    parser.add_argument("json_path", type=str, help="Path to JSON annotation file")
    parser.add_argument("images_folder", type=str, help="Folder containing images")

    args = parser.parse_args()
    process_images(args.json_path, args.images_folder)
