import zipfile
import os
import sys
import tqdm
import shutil
import subprocess

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
                        # Extract files into the target folder
                        zip_ref.extract(file, folder_path)

            # Extract 7z files using the 7z command-line tool
            elif file_name.endswith('.7z'):
                print(f'Extracting {file_name} using 7z...')
                subprocess.run(['7z', 'x', archive_file_path, f'-o{folder_path}', '-y'], check=True)

            print(f'Extracted {file_name} to {folder_path}\n')

    print("All files processed.")

if __name__ == "__main__":
    # Check if the user provided the target directory as a command-line argument
    if len(sys.argv) != 2:
        print("Usage: python unzip_script.py <target_directory>")
        sys.exit(1)

    # Get the target directory from the command-line argument
    target_directory = sys.argv[1]

    # Call the function to unzip files in the provided directory
    unzip_files_in_directory(target_directory)
