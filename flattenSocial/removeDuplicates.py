import os
import argparse

def remove_duplicates(folder1, folder2):
    # Get all file names from both folders
    folder1_files = set(os.listdir(folder1))
    folder2_files = set(os.listdir(folder2))

    # Find common files
    common_files = folder1_files.intersection(folder2_files)

    # Remove common files from folder2
    for file_name in common_files:
        file_path = os.path.join(folder2, file_name)
        if os.path.isfile(file_path):  # Double-check it's a file before deleting
            os.remove(file_path)
            print(f"Removed: {file_path}")
        else:
            print(f"Skipped: {file_path} (not a file)")

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Remove duplicate files from Folder2 if they also exist in Folder1.")
    parser.add_argument("folder1", help="Path to the first folder (reference folder)")
    parser.add_argument("folder2", help="Path to the second folder (target folder from which duplicates will be removed)")

    # Parse arguments
    args = parser.parse_args()

    # Run the function with provided arguments
    remove_duplicates(args.folder1, args.folder2)