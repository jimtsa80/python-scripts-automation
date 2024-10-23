import json
import sys

# Ensure correct usage
if len(sys.argv) != 4:
    print("Usage: python replace_images_key.py <original_json> <new_images_json> <output_json>")
    sys.exit(1)

# Get file paths from command-line arguments
original_json_path = sys.argv[1]
new_images_json_path = sys.argv[2]
output_json_path = sys.argv[3]

# Load the original JSON
with open(original_json_path, 'r') as f:
    try:
        original_data = json.load(f)
        print("Original JSON loaded successfully")
    except json.JSONDecodeError as e:
        print(f"Error in original JSON: {e}")

# Load the JSON containing the new "images" key
with open(new_images_json_path, 'r') as f:
    try:
        new_images_data = json.load(f)
        print("New images JSON loaded successfully")
    except json.JSONDecodeError as e:
        print(f"Error in new images JSON: {e}")

# Replace the "images" key in the original data with the "images" key from the new data
if "images" in new_images_data:
    original_data["images"] = new_images_data["images"]
else:
    print("The new JSON file does not contain an 'images' key.")
    sys.exit(1)

# Save the modified JSON to the output file
with open(output_json_path, 'w') as f:
    json.dump(original_data, f, indent=4)

print(f"Updated JSON saved to {output_json_path}")
