import os
import json
import argparse

# Initialize the argument parser
parser = argparse.ArgumentParser(description="Generate JSON from YOLO results in nested folders")
parser.add_argument('root_folder', type=str, help='Root folder containing subfolders with Processed_Images')
args = parser.parse_args()

# Map class IDs to brands (adjust based on your classes)
class_mapping = {
    0: "WorldRX-TVGI_Text",
    1: "WorldRX-TVGI_#worldrx"
}

# Fixed image width and height
width = 730
height = 410.625

# Traverse the root folder
for subfolder in os.listdir(args.root_folder):
    subfolder_path = os.path.join(args.root_folder, subfolder)
    
    # Check if this subfolder contains a Processed_Images folder
    processed_images_path = os.path.join(subfolder_path, "Processed_Images")
    if os.path.isdir(processed_images_path):
        print(f"Processing folder: {processed_images_path}")

        # Initialize JSON structure
        json_output = {"images": {}}

        # Process each .txt file in the Processed_Images folder
        for txt_file in os.listdir(processed_images_path):
            if txt_file.endswith(".txt"):
                image_name = os.path.splitext(txt_file)[0]

                # Initialize the image entry in the JSON
                json_output["images"][image_name] = {
                    "imageName": image_name,
                    "imageIndex": 0,
                    "width": width,
                    "height": height,
                    "annotations": []
                }

                # Open the corresponding .txt file
                with open(os.path.join(processed_images_path, txt_file), 'r') as f:
                    last_annotation = None  # Keep track of the last annotation
                    hit_counts = {}
                    for line in f:
                        values = line.split()
                        if len(values) == 5:
                            class_id, x_center, y_center, box_width, box_height = map(float, values)
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

                        # Count hits for each brand
                        hit_counts[brand] = hit_counts.get(brand, 0) + 1

                        # Create the annotation entry
                        last_annotation = {
                            "startPoint": [x1, y1],
                            "diagPoint": [x2, y2],
                            "group": "WorldRX",
                            "brand": brand,
                            "tpoint": touchpoint,
                            "hits": hit_counts[brand]
                        }

                    # Add the last annotation (if any) to the image's annotation list
                    if last_annotation:
                        json_output["images"][image_name]["annotations"].append(last_annotation)

                    print(f"Added the last annotation for image: {image_name}")

        # Save the JSON output inside the current subfolder
        output_json_path = os.path.join(subfolder_path, f"{subfolder}_results.json")
        with open(output_json_path, 'w') as json_file:
            json.dump(json_output, json_file, indent=4)

        print(f"JSON results saved to {output_json_path}")
