import zipfile
import os
import shutil
import sys
from tqdm import tqdm  # for progress bar

def extract_and_flatten_zip(zip_path):
    print(f"Processing: {zip_path}")

    # Create a temporary directory for extraction
    temp_dir = os.path.join(os.path.dirname(zip_path), 'temp_extracted')
    os.makedirs(temp_dir, exist_ok=True)

    # Extract all contents of the zip file to the temporary directory
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        num_files = len(zip_ref.infolist())
        print("Extracting files...")
        with tqdm(total=num_files, desc="Extracting", unit="file") as pbar:
            for file in zip_ref.infolist():
                zip_ref.extract(file, temp_dir)
                pbar.update(1)

    # Walk through the temp directory to flatten folder structure
    print("Flattening folder structure...")
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            file_path = os.path.join(root, file)
            destination_path = os.path.join(temp_dir, file)
            
            try:
                shutil.move(file_path, destination_path)  # Move the file to the top level of temp_dir
            except shutil.Error:
                # If the file already exists, rename it and then move
                base, ext = os.path.splitext(file)
                counter = 1
                new_file_name = f"{base}_{counter}{ext}"
                new_file_path = os.path.join(temp_dir, new_file_name)
                
                # Increment counter until a non-existent file name is found
                while os.path.exists(new_file_path):
                    counter += 1
                    new_file_name = f"{base}_{counter}{ext}"
                    new_file_path = os.path.join(temp_dir, new_file_name)

                shutil.move(file_path, new_file_path)

    # Remove any empty directories
    print("Removing empty directories...")
    for root, dirs, _ in os.walk(temp_dir, topdown=False):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            if not os.listdir(dir_path):  # Check if directory is empty
                os.rmdir(dir_path)

    # Recreate the zip file with the same name, but flattened
    new_zip_path = zip_path
    print(f"Repackaging zip: {new_zip_path}...")
    files_to_zip = os.listdir(temp_dir)
    with tqdm(total=len(files_to_zip), desc="Repackaging", unit="file") as pbar:
        with zipfile.ZipFile(new_zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            for file in files_to_zip:
                file_path = os.path.join(temp_dir, file)
                zip_ref.write(file_path, os.path.basename(file_path))
                pbar.update(1)

    # Clean up temporary directory
    shutil.rmtree(temp_dir)
    print(f"Successfully processed: {new_zip_path}\n")


def process_zips_in_folder(folder_path):
    # Get all zip files in the folder
    zip_files = [f for f in os.listdir(folder_path) if f.endswith('.zip')]
    
    if not zip_files:
        print("No zip files found in the folder.")
        return
    
    print(f"Found {len(zip_files)} zip files to process.")

    # Process each zip file
    for zip_file in zip_files:
        zip_file_path = os.path.join(folder_path, zip_file)
        extract_and_flatten_zip(zip_file_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <folder_with_zips>")
        sys.exit(1)

    folder_with_zips = sys.argv[1]
    if not os.path.isdir(folder_with_zips):
        print(f"Error: {folder_with_zips} is not a valid folder")
        sys.exit(1)

    process_zips_in_folder(folder_with_zips)
