import json
import os
import sys

# Ensure correct usage
if len(sys.argv) != 2:
    print("Usage: python replace_images_key.py <json_folder_path>")
    sys.exit(1)

# Define paths
sample_json_path = "sample.json"  # Load sample.json from the same level as the script
json_folder_path = sys.argv[1]  # Folder containing subfolders with JSON files

# Load the sample JSON
try:
    with open(sample_json_path, 'r') as f:
        sample_data = json.load(f)
        print("Sample JSON loaded successfully.")
except json.JSONDecodeError as e:
    print(f"Error in sample JSON: {e}")
    sys.exit(1)

# Process each subfolder
for root, dirs, files in os.walk(json_folder_path):
    for filename in files:
        if filename.endswith(".json"):
            json_path = os.path.join(root, filename)

            # Load the JSON file to replace its "images" key
            try:
                with open(json_path, 'r') as f:
                    new_images_data = json.load(f)
                    print(f"Loaded JSON from {json_path}")
            except json.JSONDecodeError as e:
                print(f"Error in {json_path}: {e}")
                continue

            # Replace the "images" key if it exists
            if "images" in new_images_data:
                sample_data["images"] = new_images_data["images"]
            else:
                print(f"No 'images' key in {json_path}. Skipping.")
                continue

            # Define the output path one folder up from the current folder
            parent_folder = os.path.dirname(root)
            output_json_path = os.path.join(parent_folder, f"{filename.rsplit('.', 1)[0]}_automated.json")

            # Save the modified JSON
            with open(output_json_path, 'w') as f:
                json.dump(sample_data, f, indent=4)
                print(f"Updated JSON saved to {output_json_path}")
