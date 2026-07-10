import os
import json
import argparse
from PIL import Image

# Initialize the argument parser
parser = argparse.ArgumentParser(description="Generate JSON from YOLO results")
parser.add_argument('output_names_txt', type=str, help='Path to the .txt file containing output JSON names')
parser.add_argument('exp_base_folder', type=str, help='Base folder containing experiment folders')
args = parser.parse_args()

# Load JSON filenames from the text file
with open(args.output_names_txt, 'r') as f:
    json_names = [line.strip() for line in f.readlines()]

# Load class mappings from a fixed file: brands_tpoints_mappings.txt
class_mapping_file = "brands_tpoints_mappings.txt"
class_mapping = {}
with open(class_mapping_file, 'r') as f:
    for line in f:
        class_id, mapping = line.strip().split(':', 1)
        class_mapping[int(class_id.strip())] = mapping.strip()

print(f"Loaded class mappings: {class_mapping}")

# Iterate over each experiment folder and JSON filename
for exp_folder, json_name in zip(sorted(os.listdir(args.exp_base_folder)), json_names):
    exp_folder_path = os.path.join(args.exp_base_folder, exp_folder)
    results_dir = os.path.join(exp_folder_path, "labels")  # Detection .txt files
    images_dir = exp_folder_path  # Images
    output_json_path = os.path.join(exp_folder_path, f"{json_name}.json")

    print(f"Processing experiment folder: {exp_folder}")
    print(f"Results directory: {results_dir}")
    print(f"Images directory: {images_dir}")
    print(f"Output JSON path: {output_json_path}")

    # Initialize JSON structure
    json_output = {"images": {}}

    # Process each .txt file in the results directory
    for txt_file in os.listdir(results_dir):
        if txt_file.endswith(".txt"):
            image_name = os.path.splitext(txt_file)[0]
            image_path = next((p for p in [os.path.join(images_dir, f"{image_name}.{ext}") for ext in ("jpg", "jpeg")] if os.path.exists(p)), None)

            # Get image dimensions
            try:
                with Image.open(image_path) as img:
                    image_width, image_height = img.size
                    if image_width < 730:
                        width, height = image_width, image_height
                    else:
                        width, height = 730, 410.625
                    print(f"Image: {image_name}, Width: {width}, Height: {height}")
            except FileNotFoundError:
                print(f"Image file not found for {image_name}. Skipping...")
                continue

            # Initialize the image entry in the JSON
            json_output["images"][image_name] = {
                "imageName": image_name,
                "imageIndex": 0,
                "width": width,
                "height": height,
                "annotations": [],
                "exifdata": {}
            }

            # Open the corresponding .txt file for this image
            touchpoint_hits = {}  # To count hits for each touchpoint
            annotations_by_touchpoint = {}  # To store the last annotation per touchpoint

            with open(os.path.join(results_dir, txt_file), 'r') as f:
                for line in f:
                    values = line.split()
                    if len(values) == 5:
                        class_id, x_center, y_center, box_width, box_height = map(float, values)
                        conf = None  # Confidence not provided
                    elif len(values) == 6:
                        class_id, x_center, y_center, box_width, box_height, conf = map(float, values)
                    else:
                        print(f"Unexpected line format in {txt_file}: {line.strip()}")
                        continue

                    # Convert YOLO format to bounding box coordinates
                    x1 = (x_center - box_width / 2) * width
                    y1 = (y_center - box_height / 2) * height
                    x2 = (x_center + box_width / 2) * width
                    y2 = (y_center + box_height / 2) * height

                    brand = class_mapping[int(class_id)].split("-")[0]
                    touchpoint = class_mapping[int(class_id)].split("-")[1]

                    print(f"Class {class_id} mapped to brand: {brand}, touchpoint: {touchpoint}")

                    # Increment the hit count for the touchpoint
                    touchpoint_hits[touchpoint] = touchpoint_hits.get(touchpoint, 0) + 1

                    # Create or update the annotation entry for this touchpoint
                    annotations_by_touchpoint[touchpoint] = {
                        "startPoint": [x1, y1],
                        "diagPoint": [x2, y2],
                        "group": "NZCricket",
                        "brand": brand,
                        "tpoint": touchpoint,
                        "hits": touchpoint_hits[touchpoint]
                    }

            # Add the final annotations for each touchpoint to the image's annotation list
            json_output["images"][image_name]["annotations"].extend(annotations_by_touchpoint.values())
            print(f"Final annotations for image {image_name}: {annotations_by_touchpoint.values()}")

    # Save the JSON output
    with open(output_json_path, 'w') as json_file:
        json.dump(json_output, json_file, indent=4)

    print(f"JSON results saved to {output_json_path}")
