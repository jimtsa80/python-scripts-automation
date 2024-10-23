import os
import shutil
import sys

def flatten_folders(initial_folder):
    # Traverse through the folder and find all subfolders
    for root, dirs, files in os.walk(initial_folder):
        for dir_name in dirs:
            folder_path = os.path.join(root, dir_name)
            
            # Flatten each folder
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)
                
                if os.path.isfile(file_path):
                    # Split the file name into name and extension
                    base_name, extension = os.path.splitext(file_name)
                    
                    # Remove spaces and replace dots with underscores in the base name
                    new_folder_name = dir_name.replace(" ", "").replace(".", "_")
                    new_base_name = base_name.replace(" ", "").replace(".", "_")
                    
                    # Combine folder name and modified file name, keeping the original extension
                    new_name = f"{new_folder_name}_{new_base_name}{extension}"
                    
                    # Destination file path (moving to the initial folder)
                    new_file_path = os.path.join(initial_folder, new_name)
                    
                    # Move and rename the file
                    shutil.move(file_path, new_file_path)
                    
            # Remove the now empty folder
            os.rmdir(folder_path)

    print(f"Flattening complete for folder: {initial_folder}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python flatten_folders.py <initial_folder>")
        sys.exit(1)
    
    initial_folder = sys.argv[1]
    if not os.path.isdir(initial_folder):
        print(f"Error: {initial_folder} is not a valid directory.")
        sys.exit(1)

    flatten_folders(initial_folder)
