import zipfile
import os
import shutil
import sys
import pandas as pd

def flatten_folder(folder_path, root_folder):
    print("Flattening folder: {}".format(folder_path))

    # Walk through the folder and move files to the root_folder
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            destination_path = os.path.join(root_folder, file)

            try:
                shutil.move(file_path, destination_path)
            except shutil.Error:
                print("File conflict detected: {}. Attempting to resolve.".format(file_path))
                base, ext = os.path.splitext(file)
                counter = 1
                new_file_name = "{}_{}{}".format(base, counter, ext)
                new_file_path = os.path.join(root_folder, new_file_name)

                while os.path.exists(new_file_path):
                    counter += 1
                    new_file_name = "{}_{}{}".format(base, counter, ext)
                    new_file_path = os.path.join(root_folder, new_file_name)

                try:
                    shutil.move(file_path, new_file_path)
                except Exception as final_e:
                    print("Error moving file {} to {}. Error: {}".format(file_path, new_file_path, final_e))
                    continue

    # Remove the empty directory
    try:
        shutil.rmtree(folder_path)
        print("Successfully flattened folder: {}".format(folder_path))
    except Exception as e:
        print("Error removing folder {}. Error: {}".format(folder_path, e))


def extract_and_flatten_zip(zip_path, root_folder):
    print("Processing zip file: {}".format(zip_path))

    # Create a temporary directory for extraction
    temp_dir = os.path.join(root_folder, 'temp_extracted')
    try:
        os.makedirs(temp_dir)
    except OSError:
        pass  # Directory already exists

    # Extract all contents of the zip file to the temporary directory
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    # Flatten the extracted folder
    flatten_folder(temp_dir, root_folder)
    
    # Delete the zip file after extraction
    try:
        os.remove(zip_path)
        print("Deleted zip file: {}".format(zip_path))
    except Exception as e:
        print("Error deleting zip file {}. Error: {}".format(zip_path, e))

    print("Successfully flattened zip: {}".format(zip_path))


def process_zips_and_folders_in_folder(folder_path):
    items = os.listdir(folder_path)
    
    if not items:
        print("No files or folders found in the directory.")
        return
    
    print("Found {} items to process.".format(len(items)))

    for item in items:
        item_path = os.path.join(folder_path, item)
        
        if os.path.isdir(item_path):
            flatten_folder(item_path, folder_path)
        elif item.endswith('.zip'):
            extract_and_flatten_zip(item_path, folder_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <folder_with_zips_and_folders>")
        sys.exit(1)

    folder_with_zips_and_folders = sys.argv[1]
    if not os.path.isdir(folder_with_zips_and_folders):
        print("Error: {} is not a valid folder".format(folder_with_zips_and_folders))
        sys.exit(1)

    process_zips_and_folders_in_folder(folder_with_zips_and_folders)
