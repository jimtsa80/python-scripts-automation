import zipfile
import os
import shutil
import sys
import pandas as pd
from tqdm import tqdm  # for progress bar

def flatten_folder(folder_path, root_folder):
    print(f"Flattening folder: {folder_path}")

    # Walk through the folder and move files to the root_folder
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            destination_path = os.path.join(root_folder, file)

            try:
                shutil.move(file_path, destination_path)
            except PermissionError as e:
                print(f"PermissionError: Unable to move file {file_path}. Error: {e}")
                continue
            except shutil.Error as e:
                print(f"File conflict detected: {file_path}. Attempting to resolve.")
                base, ext = os.path.splitext(file)
                counter = 1
                new_file_name = f"{base}_{counter}{ext}"
                new_file_path = os.path.join(root_folder, new_file_name)

                while os.path.exists(new_file_path):
                    counter += 1
                    new_file_name = f"{base}_{counter}{ext}"
                    new_file_path = os.path.join(root_folder, new_file_name)

                try:
                    shutil.move(file_path, new_file_path)
                except Exception as final_e:
                    print(f"Error moving file {file_path} to {new_file_path}. Error: {final_e}")
                    continue

    # Attempt to remove the empty directory after moving all contents
    try:
        shutil.rmtree(folder_path)
        print(f"Successfully flattened folder: {folder_path}\n")
    except PermissionError as e:
        print(f"PermissionError: Unable to remove folder {folder_path}. Error: {e}")
    except Exception as e:
        print(f"Error removing folder {folder_path}. Error: {e}")


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
            zip_ref.extractall(temp_dir)
            pbar.update(num_files)

    # Flatten the extracted folder
    flatten_folder(temp_dir, root_folder)

    # Optionally, remove the zip file after extraction if needed
    # os.remove(zip_path)

    print(f"Successfully flattened zip: {zip_path}\n")

def record_last_modified_file_in_subfolders(folder_path, folder_last_file_data):
    # Walk through subfolders and track the last modified file in each
    for root, dirs, files in os.walk(folder_path):
        if root == folder_path:
            continue  # Skip the main folder level

        last_file = None
        last_file_time = None

        for file in files:
            file_path = os.path.join(root, file)
            file_time = os.path.getmtime(file_path)
            if last_file is None or file_time > last_file_time:
                last_file = file
                last_file_time = file_time

        # Save the last modified file information if found
        if last_file:
            subfolder_name = os.path.basename(root)
            folder_last_file_data.append([subfolder_name, last_file])

def process_zips_and_folders_in_folder(folder_path):
    # Prepare a list to track subfolder names and last modified files
    folder_last_file_data = []

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
            # If it's a folder, flatten it and record last modified files in subfolders
            flatten_folder(item_path, folder_path)
            record_last_modified_file_in_subfolders(folder_path, folder_last_file_data)
        elif item.endswith('.zip'):
            # If it's a zip file, extract and flatten it, then record last modified files in subfolders
            extract_and_flatten_zip(item_path, folder_path)
            record_last_modified_file_in_subfolders(folder_path, folder_last_file_data)

    # Save the subfolder and last modified file data to an Excel file
    df = pd.DataFrame(folder_last_file_data, columns=["Subfolder Name", "Last Modified File"])
    excel_path = os.path.join(folder_path, f"{os.path.basename(folder_path)}_last_files.xlsx")
    df.to_excel(excel_path, index=False)
    print(f"Excel file saved as: {excel_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <folder_with_zips_and_folders>")
        sys.exit(1)

    folder_with_zips_and_folders = sys.argv[1]
    if not os.path.isdir(folder_with_zips_and_folders):
        print(f"Error: {folder_with_zips_and_folders} is not a valid folder")
        sys.exit(1)

    process_zips_and_folders_in_folder(folder_with_zips_and_folders)
