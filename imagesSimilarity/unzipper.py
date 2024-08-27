import zipfile
import os
import sys
import tqdm

def unzip_files_in_directory(target_directory):
    # Check if the provided directory exists
    if not os.path.isdir(target_directory):
        print(f"The directory {target_directory} does not exist.")
        return

    # Iterate over all files in the target directory
    for file_name in os.listdir(target_directory):
        # Check if the file is a zip file
        if file_name.endswith('.zip'):
            # Print the file being processed
            print(f'Processing {file_name}...')

            # Define the full path to the zip file
            zip_file_path = os.path.join(target_directory, file_name)

            # Open the zip file
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                # Use tqdm to create a progress bar
                for file in tqdm.tqdm(zip_ref.namelist(), desc=f'Extracting {file_name}', unit='file'):
                    # Extract files directly into the target directory without creating subfolders
                    zip_ref.extract(file, target_directory)
            
            print(f'Extracted {file_name} to {target_directory}\n')

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
