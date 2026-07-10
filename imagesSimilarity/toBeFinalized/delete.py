import os
import sys
import shutil

def delete_specific_files_in_deepest_folders(directory):
    # Check if the directory exists
    if not os.path.exists(directory):
        print(f"The directory {directory} does not exist.")
        return

    print(f"Starting cleanup in directory: {directory}\n")

    # Walk through the directory structure to find the deepest level
    deepest_folders = []
    max_depth = -1

    for root, dirs, files in os.walk(directory):
        # Calculate the depth of the current folder
        depth = root.count(os.sep)

        if depth > max_depth:
            max_depth = depth
            deepest_folders = [root]  # Reset to only this folder
        elif depth == max_depth:
            deepest_folders.append(root)  # Add folder of the same depth

    # Process only the deepest folders
    for folder in deepest_folders:
        print(f"Processing folder: {folder}")

        for item in os.listdir(folder):
            item_path = os.path.join(folder, item)

            # Delete .jpg, .jpeg, and .zip files
            if os.path.isfile(item_path) and item.lower().endswith(('.jpg', '.jpeg', '.zip')):
                os.remove(item_path)
                print(f"Deleted file: {item_path}")

            # Print a message for .xlsx files to indicate they are retained
            elif os.path.isfile(item_path) and item.lower().endswith('.xlsx'):
                print(f"Retained .xlsx file: {item_path}")

    print("\nCleanup complete.")

if __name__ == "__main__":
    # Check if a directory was provided as an argument
    if len(sys.argv) != 2:
        print("Usage: python script.py <directory_path>")
    else:
        directory = sys.argv[1]
        delete_specific_files_in_deepest_folders(directory)
