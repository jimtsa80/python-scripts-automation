import os
import sys

def rename_files_in_folders(root_folder):
    # Supported file extensions
    valid_extensions = ('.jpg', '.jpeg')
    
    # Walk through all folders and subfolders
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
                    
                    # Rename the file
                    try:
                        os.rename(old_file_path, new_file_path)
                        print(f'Renamed: "{old_file_path}" -> "{new_file_path}"')
                    except Exception as e:
                        print(f'Error renaming "{old_file_path}": {e}')

if __name__ == "__main__":
    # Check for input arguments
    if len(sys.argv) != 2:
        print("Usage: python script.py <folder_path>")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    # Check if folder exists
    if not os.path.isdir(folder_path):
        print(f'Error: "{folder_path}" is not a valid directory.')
        sys.exit(1)
    
    # Start renaming process
    rename_files_in_folders(folder_path)
