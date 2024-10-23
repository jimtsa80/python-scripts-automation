import zipfile
import os
import shutil
import sys
from tqdm import tqdm  # for progress bar

def flatten_folder(folder_path, root_folder):
    print(f"Flattening folder: {folder_path}")

    # Walk through the folder and move files to the root_folder
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            destination_path = os.path.join(root_folder, file)

            try:
                shutil.move(file_path, destination_path)  # Move file to the top level
            except shutil.Error:
                # Handle file name conflicts by renaming the file
                base, ext = os.path.splitext(file)
                counter = 1
                new_file_name = f"{base}_{counter}{ext}"
                new_file_path = os.path.join(root_folder, new_file_name)

                while os.path.exists(new_file_path):
                    counter += 1
                    new_file_name = f"{base}_{counter}{ext}"
                    new_file_path = os.path.join(root_folder, new_file_name)

                shutil.move(file_path, new_file_path)

    # Remove the empty directory after moving all contents
    shutil.rmtree(folder_path)
    print(f"Successfully flattened folder: {folder_path}\n")

def extract_and_flatten_zip(zip_path, root_folder):
    print(f"Processing zip file: {zip_path}")

    # Create a temporary directory for extraction
    temp_dir = os.path.join(root_folder, 'temp_extracted')
    os.makedirs(temp_dir, exist_ok=True)

    # Extract all contents of the zip file to the temporary directory
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        num_files = len(zip_ref.infolist())
        print("Extracting files...")
        with tqdm(total=num_files, desc="Extracting", unit="file") as pbar:
            for file in zip_ref.infolist():
                zip_ref.extract(file, temp_dir)
                pbar.update(1)

    # Move all extracted files to the root folder
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            file_path = os.path.join(root, file)
            destination_path = os.path.join(root_folder, file)

            try:
                shutil.move(file_path, destination_path)  # Move file to the root folder
            except shutil.Error:
                # Handle file name conflicts by renaming the file
                base, ext = os.path.splitext(file)
                counter = 1
                new_file_name = f"{base}_{counter}{ext}"
                new_file_path = os.path.join(root_folder, new_file_name)

                while os.path.exists(new_file_path):
                    counter += 1
                    new_file_name = f"{base}_{counter}{ext}"
                    new_file_path = os.path.join(root_folder, new_file_name)

                shutil.move(file_path, new_file_path)

    # Clean up temporary directory
    shutil.rmtree(temp_dir)

    # Optionally, remove the zip file after extraction if needed
    # os.remove(zip_path)

    print(f"Successfully flattened zip: {zip_path}\n")

def process_zips_and_folders_in_folder(folder_path):
    # Get all zip files and folders in the folder
    items = [f for f in os.listdir(folder_path)]
    
    if not items:
        print("No files or folders found in the directory.")
        return
    
    print(f"Found {len(items)} items to process.")

    # Process each item
    for item in items:
        item_path = os.path.join(folder_path, item)
        
        if os.path.isdir(item_path):
            # If it's a folder, flatten it
            flatten_folder(item_path, folder_path)
        elif item.endswith('.zip'):
            # If it's a zip file, extract and flatten it
            extract_and_flatten_zip(item_path, folder_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <folder_with_zips_and_folders>")
        sys.exit(1)

    folder_with_zips_and_folders = sys.argv[1]
    if not os.path.isdir(folder_with_zips_and_folders):
        print(f"Error: {folder_with_zips_and_folders} is not a valid folder")
        sys.exit(1)

    process_zips_and_folders_in_folder(folder_with_zips_and_folders)
