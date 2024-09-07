import zipfile
import os
import sys
import tqdm
import shutil

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
            folder_name = os.path.splitext(file_name)[0]
            folder_path = os.path.join(target_directory, folder_name)
            
            # Temporary extraction path
            temp_extract_path = os.path.join(target_directory, f"temp_{folder_name}")
            os.makedirs(temp_extract_path, exist_ok=True)

            # Open the zip file
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                # Use tqdm to create a progress bar
                for file in tqdm.tqdm(zip_ref.namelist(), desc=f'Extracting {file_name}', unit='file'):
                    # Extract files into the temporary directory
                    zip_ref.extract(file, temp_extract_path)

            # Check if the files are already in a single folder
            extracted_items = os.listdir(temp_extract_path)
            if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_extract_path, extracted_items[0])):
                # Move the single folder to the target directory with the correct name
                shutil.move(os.path.join(temp_extract_path, extracted_items[0]), folder_path)
            else:
                # Create a folder named after the zip file and move the files there
                os.makedirs(folder_path, exist_ok=True)
                for item in extracted_items:
                    shutil.move(os.path.join(temp_extract_path, item), folder_path)

            # Clean up the temporary extraction directory
            shutil.rmtree(temp_extract_path)
            
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

