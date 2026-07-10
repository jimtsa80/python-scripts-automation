import os
import json
import sys
from collections import defaultdict

def merge_json_files(file1, file2):
    # Load both JSON files
    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        data1 = json.load(f1)
        data2 = json.load(f2)
    
    # Merge top-level fields
    merged_data = {key: data1.get(key, data2.get(key)) for key in set(data1) | set(data2)}

    # Handle merging of `images`
    merged_images = defaultdict(dict)

    # Combine images from both files
    for image_key, image_data in data1.get('images', {}).items():
        merged_images[image_key] = image_data
    for image_key, image_data in data2.get('images', {}).items():
        if image_key in merged_images:
            # Combine annotations if the same image exists in both
            merged_images[image_key]['annotations'].extend(image_data['annotations'])
        else:
            merged_images[image_key] = image_data

    # Replace the `images` field in the merged data
    merged_data['images'] = dict(merged_images)
    
    return merged_data

def normalize_filename(filename):
    # Remove "results_" from anywhere in the filename
    return filename.replace("results_", "")

def merge_json_folders(folder1, folder2):
    # Build a mapping of JSON files by their base key
    def build_file_mapping(folder):
        mapping = {}
        for filename in os.listdir(folder):
            if filename.endswith('.json'):
                normalized_name = normalize_filename(filename)
                base_key = "_".join(normalized_name.split('_')[:-1])  # Extract part before the last `_`
                mapping[base_key] = os.path.join(folder, filename)
        return mapping

    mapping1 = build_file_mapping(folder1)
    mapping2 = build_file_mapping(folder2)

    # Merge matching JSON files based on the normalized base key
    for base_key in mapping1.keys() & mapping2.keys():
        file1 = mapping1[base_key]
        file2 = mapping2[base_key]
        output_file = f"{base_key}_merged.json"  # Save in the current working directory

        merged_data = merge_json_files(file1, file2)

        # Write the merged JSON to the output file
        with open(output_file, 'w') as out_file:
            json.dump(merged_data, out_file, indent=4)
        print(f"Merged JSON saved to {output_file}")

    # Handle unmatched files
    unmatched_in_folder1 = mapping1.keys() - mapping2.keys()
    unmatched_in_folder2 = mapping2.keys() - mapping1.keys()

    if unmatched_in_folder1:
        print(f"Unmatched files in {folder1}: {unmatched_in_folder1}")
    if unmatched_in_folder2:
        print(f"Unmatched files in {folder2}: {unmatched_in_folder2}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python merge_json_folders.py <folder1> <folder2>")
        sys.exit(1)

    folder1 = sys.argv[1]
    folder2 = sys.argv[2]

    merge_json_folders(folder1, folder2)
