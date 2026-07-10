import json
import sys
import os

# Function to load brand-tpoint pairs from a text file
def load_brand_tpoint_pairs(filename):
    brand_tpoint_pairs = []
    with open(filename, 'r') as file:
        for line in file:
            line = line.strip()  # Remove any extra spaces or newlines
            if '-' in line:
                brand, tpoint = line.split('-')  # Split by hyphen
                brand_tpoint_pairs.append((brand.strip(), tpoint.strip()))
    return brand_tpoint_pairs

# Function to filter the images based on brand and tpoint
def filter_images_by_brand_and_tpoint(data, brand_tpoint_pairs):
    filtered_data = {'images': {}}

    # Loop through the images and filter annotations
    for image_id, image_data in data['images'].items():
        # Filter the annotations based on brand and tpoint
        filtered_annotations = [
            ann for ann in image_data['annotations']
            if (ann['brand'], ann['tpoint']) in brand_tpoint_pairs
        ]
        
        # If there are any remaining annotations, add the image to the filtered data
        if filtered_annotations:
            filtered_data['images'][image_id] = image_data
            filtered_data['images'][image_id]['annotations'] = filtered_annotations

    return filtered_data

# Main function to handle arguments and processing
def main():
    # Check if the correct number of arguments is provided
    if len(sys.argv) != 3:
        print("Usage: python filter_json.py <json_folder> <brand_tpoint_file>")
        sys.exit(1)

    # Get the folder and brand-tpoint file from the arguments
    json_folder = sys.argv[1]
    brand_tpoint_file = sys.argv[2]

    # Load the brand-tpoint pairs from the provided text file
    brand_tpoint_pairs = load_brand_tpoint_pairs(brand_tpoint_file)

    # Process each JSON file in the folder
    for json_file in os.listdir(json_folder):
        # Ensure the file has a .json extension
        if json_file.endswith('.json'):
            json_path = os.path.join(json_folder, json_file)
            filename = os.path.splitext(json_file)[0]

            # Load the input JSON file
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Filter the data based on the brand and tpoint combinations
            filtered_data = filter_images_by_brand_and_tpoint(data, brand_tpoint_pairs)

            # Save the filtered data to a new JSON file in the same folder
            output_file = os.path.join(json_folder, filename + '_filtered.json')
            with open(output_file, 'w') as f:
                json.dump(filtered_data, f, indent=4)

            print(f"Filtered JSON saved to {output_file}")

if __name__ == "__main__":
    main()
