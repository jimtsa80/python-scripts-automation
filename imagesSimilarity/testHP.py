import os
import sys
import requests
import shutil

# Check if input folder was provided
if len(sys.argv) < 2:
    print("Usage: python classify_images.py <input_folder>")
    sys.exit(1)

input_folder = sys.argv[1]

# Output folders
output_folders = {
    'home_plate': os.path.join(input_folder, 'Home_Plate'),
    'not_home_plate': os.path.join(input_folder, 'Not_Home_Plate'),
    'maybe': os.path.join(input_folder, 'Maybe')
}

# Create output folders if they don't exist
for folder in output_folders.values():
    os.makedirs(folder, exist_ok=True)

# Puter.js API endpoint (or another free API)
api_url = 'https://api.puter.com/v1/classify'

# Process images
for filename in os.listdir(input_folder):
    file_path = os.path.join(input_folder, filename)
    if os.path.isfile(file_path) and filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        with open(file_path, 'rb') as img_file:
            files = {'image': img_file}
            try:
                response = requests.post(api_url, files=files)
                response.raise_for_status()
                label = response.json().get('label', '').lower()

                if 'home plate' in label:
                    shutil.move(file_path, os.path.join(output_folders['home_plate'], filename))
                elif 'not home plate' in label:
                    shutil.move(file_path, os.path.join(output_folders['not_home_plate'], filename))
                else:
                    shutil.move(file_path, os.path.join(output_folders['maybe'], filename))

            except Exception as e:
                print(f"Error processing {filename}: {e}")

