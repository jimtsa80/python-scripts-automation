import zipfile
import os
import sys
import tqdm
import shutil
import subprocess

def has_nested_folders(source_folder):
    """
    Check if the source folder contains any nested folders.
    """
    for root, dirs, files in os.walk(source_folder):
        if root != source_folder and dirs:
            return True
    return False

def move_files_to_top_level(source_folder):
    """
    Moves all files from nested folders into the top-level folder, skipping files if they already exist.
    """
    for root, dirs, files in os.walk(source_folder, topdown=False):
        # Skip if we are at the top level
        if root == source_folder:
            continue

        for file in files:
            file_path = os.path.join(root, file)
            # Destination path in the top-level folder
            dest_file_path = os.path.join(source_folder, file)

            # Skip the file if it already exists in the top-level folder
            if not os.path.exists(dest_file_path):
                shutil.move(file_path, dest_file_path)

        # Remove the now empty directories
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            if not os.listdir(dir_path):  # Check if the directory is empty
                os.rmdir(dir_path)

def unzip_files_in_directory(target_directory):
    # Check if the provided directory exists
    if not os.path.isdir(target_directory):
        print(f"The directory {target_directory} does not exist.")
        return

    # Iterate over all files in the target directory
    for file_name in os.listdir(target_directory):
        # Check if the file is a zip or 7z file
        if file_name.endswith('.zip') or file_name.endswith('.7z'):
            # Print the file being processed
            print(f'Processing {file_name}...')

            # Define the full path to the archive file
            archive_file_path = os.path.join(target_directory, file_name)
            folder_name = os.path.splitext(file_name)[0]
            folder_path = os.path.join(target_directory, folder_name)
            os.makedirs(folder_path, exist_ok=True)

            # Extract ZIP files
            if file_name.endswith('.zip'):
                with zipfile.ZipFile(archive_file_path, 'r') as zip_ref:
                    # Use tqdm to create a progress bar
                    for file in tqdm.tqdm(zip_ref.namelist(), desc=f'Extracting {file_name}', unit='file'):
                        # Extract files into the folder
                        zip_ref.extract(file, folder_path)

            # Extract 7z files using the 7z command-line tool
            elif file_name.endswith('.7z'):
                print(f'Extracting {file_name} using 7z...')
                subprocess.run(['7z', 'x', archive_file_path, f'-o{folder_path}', '-y'], check=True)

            # Check for nested folders
            if has_nested_folders(folder_path):
                print(f'Flattening folder structure for {file_name}...')
                move_files_to_top_level(folder_path)

            print(f'Processed {file_name} into {folder_path}\n')

    print("All files processed and flattened.")

if __name__ == "__main__":
    # Check if the user provided the target directory as a command-line argument
    if len(sys.argv) != 2:
        print("Usage: python unzip_script.py <target_directory>")
        sys.exit(1)

    # Get the target directory from the command-line argument
    target_directory = sys.argv[1]

    # Call the function to unzip files in the provided directory
    unzip_files_in_directory(target_directory)
