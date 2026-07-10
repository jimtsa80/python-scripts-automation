import zipfile
import os
import sys
import tqdm
import shutil
import subprocess
import tempfile

def move_files_to_top_level(source_folder, target_folder):
    """
    Moves all files from nested folders into the target folder, skipping files if they already exist.
    """
    for root, dirs, files in os.walk(source_folder):
        for file in files:
            file_path = os.path.join(root, file)
            # Destination path in the target folder
            dest_file_path = os.path.join(target_folder, file)

            # Skip the file if it already exists in the target folder
            if not os.path.exists(dest_file_path):
                shutil.move(file_path, dest_file_path)

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
            target_folder_path = os.path.join(target_directory, folder_name)
            os.makedirs(target_folder_path, exist_ok=True)

            # Temporary directory for extraction
            with tempfile.TemporaryDirectory() as tmpdirname:
                try:
                    # Extract ZIP files
                    if file_name.endswith('.zip'):
                        with zipfile.ZipFile(archive_file_path, 'r') as zip_ref:
                            # Use tqdm to create a progress bar
                            for file in tqdm.tqdm(zip_ref.namelist(), desc=f'Extracting {file_name}', unit='file'):
                                try:
                                    # Extract files into the temporary folder
                                    zip_ref.extract(file, tmpdirname)
                                except Exception as file_error:
                                    print(f"Failed to extract {file} from {file_name}: {file_error}")

                    # Extract 7z files using the 7z command-line tool
                    elif file_name.endswith('.7z'):
                        print(f'Extracting {file_name} using 7z...')
                        subprocess.run(['7z', 'x', archive_file_path, f'-o{tmpdirname}', '-y'], check=True)

                    # Move files from temporary folder to target folder
                    move_files_to_top_level(tmpdirname, target_folder_path)

                    print(f'Processed {file_name} into {target_folder_path}\n')

                except zipfile.BadZipFile:
                    print(f"Error: {file_name} is not a valid ZIP file and will be skipped.")
                except Exception as e:
                    print(f"Unexpected error while processing {file_name}: {e}")

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
