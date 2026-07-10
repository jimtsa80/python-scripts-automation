import os
import re
import sys

def rename_files_in_folder(folder_path):
    # Ensure the folder path exists
    if not os.path.isdir(folder_path):
        print(f"Error: The specified folder '{folder_path}' does not exist.")
        return
    
    # List all files in the folder
    files = os.listdir(folder_path)
    
    # Sort files to ensure consistent ordering
    files.sort()
    
    # Regular expression to match "partX_" at the start of filenames
    part_regex = re.compile(r"^part\d+_")

    count = 1
    for file_name in files:
        old_file_path = os.path.join(folder_path, file_name)
        
        # Skip if it's not a file
        if not os.path.isfile(old_file_path):
            continue

        # Remove existing "partX_" from the filename
        new_name = re.sub(part_regex, "", file_name)
        
        # Add new "part_X_" prefix
        new_name = f"part{count}_{new_name}"
        new_file_path = os.path.join(folder_path, new_name)
        
        # Rename the file
        os.rename(old_file_path, new_file_path)
        print(f"Renamed: {file_name} -> {new_name}")
        count += 1

if __name__ == "__main__":
    # Check if folder path is provided as an argument
    if len(sys.argv) < 2:
        print("Usage: python script.py <folder_path>")
        sys.exit(1)

    folder_path = sys.argv[1]
    rename_files_in_folder(folder_path)
