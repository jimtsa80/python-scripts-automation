import json
import os
import shutil
import sys

# Ensure correct usage
if len(sys.argv) != 6:
    print("Usage: python script.py <json_folder_path> <brand> <tpoint> <images_folder> <brand_mapping_file_or_none>")
    sys.exit(1)

# Get arguments from command-line
json_folder_path = sys.argv[1]
brand_input = sys.argv[2]
tpoint_input = sys.argv[3]
images_folder = sys.argv[4]  # Path to folder containing images
brand_mapping_file = sys.argv[5]
filter_string = "filter"  # Define the string filter to match JSON filenames


print(f"Brand: {brand_input}, Touchpoint: {tpoint_input}")
print(f"Images Folder: {images_folder}")
print(f"Brand Mapping File: {brand_mapping_file}")

# Setup base output directories
dataset_dir = './dataset/train'
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

# Process each JSON file in the folder that contains the filter string
for json_filename in os.listdir(json_folder_path):
    if json_filename.endswith(".json") and filter_string in json_filename:
        json_file_path = os.path.join(json_folder_path, json_filename)
        
        print(f"\nProcessing JSON file: {json_file_path}")

        # Strip the "_filtered" postfix from the filename to match the folder name (without .json)
        json_image_name = json_filename.replace('_filtered', '').replace('.json', '')

        # Load the JSON data
        with open(json_file_path, 'r') as f:
            data = json.load(f)

        # Find the corresponding subfolder in the images folder
        image_folder_path = os.path.join(images_folder, json_image_name)
    
        # Check if the folder exists inside the images folder
        if not os.path.isdir(image_folder_path):
            print(f"Folder {json_image_name} not found in {images_folder}. Skipping...")
            continue

        print(f"Checking JSON folder path: {json_folder_path} -> Exists: {os.path.isdir(json_folder_path)}")
        print(f"Checking Images folder path: {images_folder} -> Exists: {os.path.isdir(images_folder)}")
        print(f"Checking Brand Mapping file path: {brand_mapping_file} -> Exists: {os.path.isfile(brand_mapping_file)}")

        # Iterate through images in the JSON
        for image_id, image_data in data["images"].items():
            # Check if the image exists in the correct subfolder
            image_filename = None
            for ext in ['.jpg', '.jpeg']:
                possible_image_path = os.path.join(image_folder_path, f"{image_data['imageName']}{ext}")
                if os.path.exists(possible_image_path):
                    image_filename = f"{image_data['imageName']}{ext}"
                    break

            # If no image is found, skip to the next
            if image_filename is None:
                print(f"Image {image_data['imageName']} not found in folder {json_image_name}. Skipping...")
                continue

            # Proceed with processing the image
            image_path = os.path.join(image_folder_path, image_filename)
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

                # Add the folder name (subfolder name) as a prefix to avoid filename conflicts
                new_image_filename = f"{json_image_name}_{image_filename}"

                # Copy the image to the images directory with a new name to avoid conflicts
                new_image_path = os.path.join(images_dir, new_image_filename)
                shutil.copy(image_path, new_image_path)
                print(f"Copied image {image_filename} to {new_image_path}")

                # Create a YOLO-format annotation file
                new_annotation_filename = f"{json_image_name}_{image_data['imageName']}.txt"
                annotation_file = os.path.join(labels_dir, new_annotation_filename)
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
