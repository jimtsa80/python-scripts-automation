import os
import sys
import shutil
import zipfile
import re
from pathlib import Path
from tqdm import tqdm

def flatten_folder(folder_path):
    """Flatten a folder by moving all files from subfolders to the main folder"""
    print(f"Flattening folder: {folder_path}")
    
    # Collect all files to move
    files_to_move = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            # Skip files already in the root folder
            if root != folder_path:
                files_to_move.append((file_path, file))
    
    print(f"Found {len(files_to_move)} files to move")
    
    # Move files with progress bar
    with tqdm(files_to_move, desc="Moving files", unit="file") as pbar:
        for file_path, filename in pbar:
            destination_path = os.path.join(folder_path, filename)
            
            try:
                # Handle file conflicts
                if os.path.exists(destination_path):
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    new_filename = f"{base}_{counter}{ext}"
                    destination_path = os.path.join(folder_path, new_filename)
                    
                    while os.path.exists(destination_path):
                        counter += 1
                        new_filename = f"{base}_{counter}{ext}"
                        destination_path = os.path.join(folder_path, new_filename)
                
                shutil.move(file_path, destination_path)
                pbar.set_postfix({"Moved": filename})
                
            except Exception as e:
                print(f"Error moving file {file_path}: {e}")
                continue
    
    # Remove empty subdirectories
    for root, dirs, files in os.walk(folder_path, topdown=False):
        if root != folder_path and not os.listdir(root):
            try:
                os.rmdir(root)
            except Exception as e:
                print(f"Could not remove empty directory {root}: {e}")
    
    print(f"Successfully flattened folder: {folder_path}\n")

def rename_files_in_folders(root_folder):
    """Rename files by keeping only the part after the last underscore"""
    print(f"Renaming files in folder: {root_folder}")
    
    # Supported file extensions
    valid_extensions = ('.jpg', '.jpeg')
    
    # Collect all files to rename
    files_to_rename = []
    for dirpath, dirnames, filenames in os.walk(root_folder):
        for filename in filenames:
            # Check if the file is a jpg or jpeg
            if filename.lower().endswith(valid_extensions):
                # Check if the filename contains an underscore
                if "_" in filename:
                    # Extract the part after the last underscore
                    new_name = filename.split("_")[-1]
                    # Construct full paths
                    old_file_path = os.path.join(dirpath, filename)
                    new_file_path = os.path.join(dirpath, new_name)
                    files_to_rename.append((old_file_path, new_file_path, filename, new_name))
    
    print(f"Found {len(files_to_rename)} files to rename")
    
    # Rename files with progress bar
    with tqdm(files_to_rename, desc="Renaming files", unit="file") as pbar:
        for old_file_path, new_file_path, old_name, new_name in pbar:
            try:
                os.rename(old_file_path, new_file_path)
                pbar.set_postfix({"Renamed": f"{old_name} -> {new_name}"})
            except Exception as e:
                print(f'Error renaming "{old_file_path}": {e}')
                continue

def rename_folder_to_hp(folder_path):
    """Rename folder to HP_[original_name_without_part_prefix_and_cluster_suffix]"""
    folder_name = os.path.basename(folder_path)
    parent_dir = os.path.dirname(folder_path)
    
    # Remove "part" prefix if it exists
    if folder_name.startswith("part"):
        # Find the first underscore after "part"
        if "_" in folder_name:
            # Get everything after the first underscore
            name_after_part = folder_name.split("_", 1)[1]
        else:
            name_after_part = folder_name
    else:
        name_after_part = folder_name
    
    # Remove part after last dash if it exists (like -cluster_2)
    if "-" in name_after_part:
        new_name = name_after_part.rsplit("-", 1)[0]
    else:
        new_name = name_after_part
    
    # Create new folder name as "HP_[original_name]"
    new_folder_name = f"HP_{new_name}"
    new_folder_path = os.path.join(parent_dir, new_folder_name)
    
    # Rename the folder
    try:
        os.rename(folder_path, new_folder_path)
        print(f"Renamed folder: '{folder_name}' -> '{new_folder_name}'")
        return new_folder_path
    except Exception as e:
        print(f"Error renaming folder '{folder_name}': {e}")
        return folder_path

def create_zip_archive(folder_path, zip_name):
    """Create a zip archive of the folder"""
    zip_path = f"{folder_path}.zip"
    
    try:
        # Count total files for progress bar
        total_files = 0
        for root, dirs, files in os.walk(folder_path):
            total_files += len(files)
        
        print(f"Creating zip archive with {total_files} files...")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            with tqdm(total=total_files, desc="Zipping files", unit="file") as pbar:
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, folder_path)
                        zipf.write(file_path, arcname)
                        pbar.update(1)
                        pbar.set_postfix({"Current": file})
        
        print(f"Created zip archive: {zip_path}")
        return zip_path
    except Exception as e:
        print(f"Error creating zip archive for '{folder_path}': {e}")
        return None

def process_folders(parent_folder):
    """Main function to process both folders according to the requirements"""
    print(f"Processing folders in: {parent_folder}")
    
    # Get all folders in the parent directory
    folders = [f for f in os.listdir(parent_folder) if os.path.isdir(os.path.join(parent_folder, f))]
    
    if len(folders) != 2:
        print(f"Expected 2 folders, found {len(folders)}. Please check the folder structure.")
        return
    
    print(f"Found folders: {folders}")
    
    # Process first folder (should be the one without "part" prefix)
    first_folder = None
    second_folder = None
    
    for folder in folders:
        if folder.startswith("part"):
            second_folder = os.path.join(parent_folder, folder)
        else:
            first_folder = os.path.join(parent_folder, folder)
    
    if not first_folder or not second_folder:
        print("Could not identify the correct folders. Please check folder names.")
        return
    
    print(f"\n=== Processing First Folder: {os.path.basename(first_folder)} ===")
    
    # Step 1: Flatten the first folder
    print("Step 1: Flattening folder...")
    flatten_folder(first_folder)
    
    # Step 2: Rename files in the first folder
    print("Step 2: Renaming files...")
    rename_files_in_folders(first_folder)
    
    print(f"\n=== Processing Second Folder: {os.path.basename(second_folder)} ===")
    
    # Step 1: Rename the second folder to "HP_[original_name]"
    print("Step 1: Renaming folder to HP_[original_name]...")
    renamed_second_folder = rename_folder_to_hp(second_folder)
    
    # Step 2: Rename files in the second folder
    print("Step 2: Renaming files...")
    rename_files_in_folders(renamed_second_folder)
    
    print(f"\n=== Creating Zip Archives ===")
    
    # Step 3: Create zip archives for both folders
    print("Creating zip for first folder...")
    create_zip_archive(first_folder, os.path.basename(first_folder))
    
    print("Creating zip for second folder...")
    create_zip_archive(renamed_second_folder, os.path.basename(renamed_second_folder))
    
    print("\n=== Processing Complete ===")
    print(f"First folder processed: {first_folder}")
    print(f"Second folder processed and renamed to: {renamed_second_folder}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python automate_folder_processing.py <parent_folder_path>")
        print("Example: python automate_folder_processing.py C:\\path\\to\\parent\\folder")
        sys.exit(1)
    
    parent_folder = sys.argv[1]
    
    if not os.path.isdir(parent_folder):
        print(f"Error: '{parent_folder}' is not a valid directory.")
        sys.exit(1)
    
    try:
        process_folders(parent_folder)
    except Exception as e:
        print(f"An error occurred during processing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
