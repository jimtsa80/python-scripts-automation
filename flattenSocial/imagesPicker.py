import os
import shutil
import re
import sys
from PIL import Image

def move_matching_files(folder_path):
    # Get the base folder name
    base_folder_name = os.path.basename(os.path.normpath(folder_path))
    # Create the new folder for matching images
    new_folder = f"{base_folder_name}_imagesOnly"
    new_folder_path = os.path.join(os.path.dirname(folder_path), new_folder)
    
    if not os.path.exists(new_folder_path):
        os.makedirs(new_folder_path)

    # Define patterns
    dot_pattern = re.compile(r".*DOT.*")  # Files containing 'DOT'
    dd_pattern = re.compile(r".*_\d{2}_\d{2}$")  # Files ending with _dd_dd
    single_digit_pattern = re.compile(r".*_\d{4}_\d{2}_\d{2}(__\d{2}_\d{2}_\d{2}_\d)$")  
    exclude_more_than_three_digits = re.compile(r".*_\d{4,}$")  # exclude digit count > 3
    instagram_pattern = re.compile(r"Instagram_\d+_\d{1}$")


    # Iterate through the files in the folder
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        
        # Split filename and extension
        name, ext = os.path.splitext(filename)
        
        # Check if the filename matches any pattern, excluding those with more than 3 digits after 'DOT'
        if os.path.isfile(file_path):
            if (dot_pattern.match(name) or dd_pattern.match(name) or single_digit_pattern.match(name) or instagram_pattern.match(name)) and not exclude_more_than_three_digits.match(name):
                # Convert non-JPEG files to JPEG
                if ext.lower() not in ['.jpg', '.jpeg']:
                    try:
                        with Image.open(file_path) as img:
                            jpg_filename = f"{name}.jpg"
                            jpg_path = os.path.join(folder_path, jpg_filename)
                            img.convert("RGB").save(jpg_path, "JPEG")
                            print(f"Converted {filename} to JPEG format as {jpg_filename}")
                        os.remove(file_path)
                        file_path = jpg_path
                    except Exception as e:
                        print(f"Error converting {filename}: {e}")
                        continue

                # Move the file to the new folder
                print(f"Moving file: {os.path.basename(file_path)}")
                shutil.move(file_path, new_folder_path)

if __name__ == "__main__":
    # Accept folder path as argument
    if len(sys.argv) != 2:
        print("Usage: python script.py <folder_path>")
        sys.exit(1)

    folder_path = sys.argv[1]

    if not os.path.isdir(folder_path):
        print(f"The folder path {folder_path} does not exist or is not a directory.")
        sys.exit(1)

    # Process the folder
    move_matching_files(folder_path)
