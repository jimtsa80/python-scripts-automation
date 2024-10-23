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
        print("Usage: python filter_json.py <json_file> <brand_tpoint_file>")
        sys.exit(1)

    # Get the filenames from the arguments
    json_file = sys.argv[1]
    filename = os.path.splitext(os.path.basename(json_file))[0]
    brand_tpoint_file = sys.argv[2]

    # Load the brand-tpoint pairs from the provided text file
    brand_tpoint_pairs = load_brand_tpoint_pairs(brand_tpoint_file)

    # Load the input JSON file
    with open(json_file, 'r') as f:
        data = json.load(f)

    # Filter the data based on the brand and tpoint combinations
    filtered_data = filter_images_by_brand_and_tpoint(data, brand_tpoint_pairs)

    # Save the filtered data to a new JSON file
    output_file = filename+'_filtered.json'
    with open(output_file, 'w') as f:
        json.dump(filtered_data, f, indent=4)

    print(f"Filtered JSON saved to {output_file}")

if __name__ == "__main__":
    main()