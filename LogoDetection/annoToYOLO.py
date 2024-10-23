import json
import os
import shutil
import sys

# Ensure correct usage
if len(sys.argv) != 6:
    print("Usage: python script.py <json_file_path> <brand> <tpoint> <images_folder> <brand_mapping_file_or_none>")
    sys.exit(1)

# Get arguments from command-line
json_file_path = sys.argv[1]
json_filename = os.path.splitext(os.path.basename(json_file_path))[0]
brand_input = sys.argv[2]
tpoint_input = sys.argv[3]
images_folder = sys.argv[4]  # Path to folder containing images
brand_mapping_file = sys.argv[5]

print(f"JSON File: {json_file_path}")
print(f"Brand: {brand_input}, Touchpoint: {tpoint_input}")
print(f"Images Folder: {images_folder}")
print(f"Brand Mapping File: {brand_mapping_file}")

# Setup output directories
dataset_dir = f'./dataset_{json_filename}/train'
images_dir = os.path.join(dataset_dir, 'images')
labels_dir = os.path.join(dataset_dir, 'labels')

os.makedirs(images_dir, exist_ok=True)
os.makedirs(labels_dir, exist_ok=True)

print(f"Output directories created: \nImages: {images_dir}\nLabels: {labels_dir}")

# Dictionary to store unique class mappings for each brand-tpoint combination
class_mapping = {}
class_counter = 0  # Counter for assigning class IDs

# Load brand mapping from the file if provided
if brand_mapping_file.lower() != 'none':
    print(f"Loading brand mappings from {brand_mapping_file}...")
    with open(brand_mapping_file, 'r') as f:
        for line in f:
            if line.strip():
                # Parse the line format: "0: ERC-TVGI"
                class_id, combination = line.strip().split(": ")
                class_mapping[combination] = int(class_id)
    print("Brand mappings loaded successfully:")
    for combination, class_id in class_mapping.items():
        print(f"{class_id}: {combination}")
else:
    print("No brand mapping file provided. Using dynamic class ID assignment.")

# Load the JSON data
print(f"Loading JSON data from {json_file_path}...")
with open(json_file_path, 'r') as f:
    data = json.load(f)

# Iterate through images in the JSON
for image_id, image_data in data["images"].items():
    image_filename = f"{image_data['imageName']}.jpg" if os.path.exists(f"{image_data['imageName']}.jpg") else f"{image_data['imageName']}.jpeg"
    image_path = os.path.join(images_folder, image_filename)

    # Check if the image exists in the provided images folder
    if not os.path.exists(image_path):
        print(f"Image {image_filename} not found in {images_folder}. Skipping...")
        continue

    print(f"Processing image: {image_filename}")

    # Create a .txt file for each image, but only for the specified brand-tpoint combination
    for annotation in image_data["annotations"]:
        annotation_combination = f"{annotation['brand']}-{annotation['tpoint']}"
        
        # If brand_input or tpoint_input is 'all', skip combination filtering
        if not (brand_input == 'all' and tpoint_input == 'all'):
            if annotation['brand'] != brand_input and brand_input != 'all':
                print(f"Skipping annotation with brand: {annotation['brand']}")
                continue
            if annotation['tpoint'] != tpoint_input and tpoint_input != 'all':
                print(f"Skipping annotation with touchpoint: {annotation['tpoint']}")
                continue

        # Use class ID from the mapping if available, otherwise assign a new one
        if annotation_combination not in class_mapping:
            if brand_mapping_file.lower() == 'none':
                class_mapping[annotation_combination] = class_counter
                print(f"Assigning class ID {class_counter} to combination: {annotation_combination}")
                class_counter += 1
            else:
                print(f"Brand-tpoint combination {annotation_combination} not found in mapping file. Skipping...")
                continue
        
        class_id = class_mapping[annotation_combination]

        # Copy the image to the images directory
        shutil.copy(image_path, images_dir)
        print(f"Copied image {image_filename} to {images_dir}")

        # Create a YOLO-format annotation file
        annotation_file = os.path.join(labels_dir, f"{image_data['imageName']}.txt")
        with open(annotation_file, 'a') as f:
            # Extract annotation points and image dimensions
            x1, y1 = annotation["startPoint"]
            x2, y2 = annotation["diagPoint"]
            image_width = image_data["width"]
            image_height = image_data["height"]

            # Calculate YOLO format coordinates
            x_center = (x1 + x2) / 2 / image_width
            y_center = (y1 + y2) / 2 / image_height
            box_width = (x2 - x1) / image_width
            box_height = (y2 - y1) / image_height

            # Write YOLO annotation to the .txt file
            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {box_width:.6f} {box_height:.6f}\n")
            print(f"Annotation written to {annotation_file}")

# Print the final class mappings at the end
print("\nFinal Class ID mappings for brand-tpoint combinations:")
for combination, class_id in class_mapping.items():
    print(f"{class_id}: {combination}")

print("\nCopy the following mappings for future use:")
for combination, class_id in class_mapping.items():
    print(f"{class_id}: {combination}")
