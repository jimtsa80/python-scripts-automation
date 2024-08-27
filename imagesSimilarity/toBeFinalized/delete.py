import os
import sys
import shutil

def delete_folders_and_zip_files_in_subdirectories(directory):
    # Check if the directory exists
    if not os.path.exists(directory):
        print(f"The directory {directory} does not exist.")
        return
    
    # Iterate over all items in the specified directory
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        
        # Process only subdirectories
        if os.path.isdir(item_path):
            # Iterate over all items in the subdirectory
            for sub_item in os.listdir(item_path):
                sub_item_path = os.path.join(item_path, sub_item)
                
                # Delete folders inside the subdirectory
                if os.path.isdir(sub_item_path):
                    shutil.rmtree(sub_item_path)
                    print(f"Deleted folder: {sub_item_path}")
                
                # Delete .zip files inside the subdirectory
                elif os.path.isfile(sub_item_path) and sub_item.endswith('.zip'):
                    os.remove(sub_item_path)
                    print(f"Deleted zip file: {sub_item_path}")
    
    print("Deletion complete.")

if __name__ == "__main__":
    # Check if a directory was provided as an argument
    if len(sys.argv) != 2:
        print("Usage: python script.py <directory_path>")
    else:
        directory = sys.argv[1]
        delete_folders_and_zip_files_in_subdirectories(directory)
