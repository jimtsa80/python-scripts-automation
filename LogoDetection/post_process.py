import os
import json
import argparse

# Initialize the argument parser
parser = argparse.ArgumentParser(description="Generate JSON from YOLO results")
parser.add_argument('output_json_path', type=str, help='Path where the output JSON will be saved')
parser.add_argument('exp_folder', type=str, help='Experiment folder name (e.g., exp9)')
args = parser.parse_args()

# Paths to the results and images directories
results_dir = os.path.join("C:\\Users\\jimtsa\\Desktop\\python-scripts-automation\\LogoDetection\\yolov5\\runs\\detect", args.exp_folder, "labels")  # Detection .txt files
images_dir = os.path.join("C:\\Users\\jimtsa\\Desktop\\python-scripts-automation\\LogoDetection\\yolov5\\runs\\detect", args.exp_folder)   # Images

print(f"Processing experiment folder: {args.exp_folder}")
print(f"Results directory: {results_dir}")
print(f"Images directory: {images_dir}")

# Map class IDs to brands (adjust based on your classes)
class_mapping = {
    0: "ERC-TVGI",
    1: "Rally.TV-TVGI",
    2: "Hyundai-TVGI",
    3: "Skoda-TVGI",
    4: "MRF Tyres-TVGI",
    5: "Citroen-TVGI",
    6: "Michelin-TVGI",
    7: "Pirelli-TVGI"
}

# Initialize JSON structure
json_output = {
    "images": {}
}

# Process each .txt file in the results directory
for txt_file in os.listdir(results_dir):
    if txt_file.endswith(".txt"):
        image_name = os.path.splitext(txt_file)[0]  # Get image name without extension
        image_path = os.path.join(images_dir, f"{image_name}.jpg")  # Path to image

        print(f"Processing file: {txt_file} for image: {image_name}")

        # Image dimensions
        image_width = 730  # Example width, replace with actual values
        image_height = 410.625  # Example height, replace with actual values

        # Initialize the image entry in the JSON
        json_output["images"][image_name] = {
            "imageName": image_name,
            "imageIndex": 0,  # Adjust the index based on your needs
            "width": image_width,
            "height": image_height,
            "annotations": [],
            "exifdata": {}  # Empty exifdata as per your request
        }

        # Open the corresponding .txt file for this image
        with open(os.path.join(results_dir, txt_file), 'r') as f:
            hit_counts = {}
            for line in f:
                # Handle cases with or without confidence score
                values = line.split()
                if len(values) == 5:
                    class_id, x_center, y_center, box_width, box_height = map(float, values)
                elif len(values) == 6:
                    class_id, x_center, y_center, box_width, box_height, conf = map(float, values)
                else:
                    raise ValueError(f"Unexpected number of values in {txt_file}: {len(values)}")

                print(f"Detected object - Class ID: {class_id}, Coordinates: ({x_center}, {y_center}), Box: ({box_width}, {box_height})")

                # Convert YOLO format back to bounding box coordinates
                x1 = (x_center - box_width / 2) * image_width
                y1 = (y_center - box_height / 2) * image_height
                x2 = (x_center + box_width / 2) * image_width
                y2 = (y_center + box_height / 2) * image_height

                brand = class_mapping[int(class_id)].split("-")[0]  # Map class ID to brand
                touchpoint = class_mapping[int(class_id)].split("-")[1]

                print(f"Class {class_id} mapped to brand: {brand}, touchpoint: {touchpoint}")

                # Count hits for each brand
                if brand not in hit_counts:
                    hit_counts[brand] = 1
                else:
                    hit_counts[brand] += 1

                # Create the annotation entry
                annotation = {
                    "startPoint": [x1, y1],
                    "diagPoint": [x2, y2],
                    "group": "detected_group",  # Example group
                    "brand": brand,
                    "tpoint": touchpoint,
                    "hits": hit_counts[brand]
                }

                # Add annotation to the image's annotation list
                json_output["images"][image_name]["annotations"].append(annotation)

            print(f"Added {len(json_output['images'][image_name]['annotations'])} annotations for image: {image_name}")

# Save the JSON output to the provided argument path
with open(args.output_json_path, 'w') as json_file:
    json.dump(json_output, json_file, indent=4)

print(f"JSON results saved to {args.output_json_path}")
