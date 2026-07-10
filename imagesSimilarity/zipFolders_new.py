import os
import shutil
import sys

# Check if the user provided an argument
if len(sys.argv) < 2:
    print("Usage: python zip_folders.py <path_to_directory>")
    sys.exit(1)

# Get the folder path from the argument
source_path = sys.argv[1]

# Validate the path
if not os.path.isdir(source_path):
    print("Error: Provided path is not a valid directory.")
    sys.exit(1)

# Get all folders inside the given directory
for folder in os.listdir(source_path):
    folder_path = os.path.join(source_path, folder)

    if os.path.isdir(folder_path):  # Only process directories
        zip_file = os.path.join(source_path, folder)  # Zip filename (same location)
        shutil.make_archive(zip_file, 'zip', folder_path)
        print(f"Zipped: {zip_file}.zip")

print("All folders have been zipped successfully.")
