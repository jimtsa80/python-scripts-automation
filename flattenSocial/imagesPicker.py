import os
import shutil
import re
import sys

def move_matching_files(folder_path):
    # Create the new folder for matching images
    new_folder = f"{folder_path}_imagesOnly"
    if not os.path.exists(new_folder):
        os.makedirs(new_folder)

    # Define patterns: one to match filenames containing 'DOT' and another for filenames ending with _dd_dd
    dot_pattern = re.compile(r".*DOT.*")
    dd_pattern = re.compile(r".*_\d{2}_\d{2}$")

    # Pattern to exclude files with more than 3 digits at the end after 'DOT'
    exclude_more_than_three_digits = re.compile(r".*DOT.*_\d{4,}$")

    # Iterate through the files in the folder
    for filename in os.listdir(folder_path):
        # Full path to the current file
        file_path = os.path.join(folder_path, filename)
        
        # Split filename and extension
        name, ext = os.path.splitext(filename)
        
        # Check if the filename matches either pattern, but exclude those with more than 3 digits after 'DOT'
        if os.path.isfile(file_path):
            if (dot_pattern.match(name) or dd_pattern.match(name)) and not exclude_more_than_three_digits.match(name):
                print(f"Moving file: {filename}")
                shutil.move(file_path, new_folder)

if __name__ == "__main__":
    # Accept folder path as argument
    if len(sys.argv) != 2:
        print("Usage: python script.py <folder_path>")
        sys.exit(1)

    folder_path = sys.argv[1]

    if not os.path.isdir(folder_path):
        print(f"The folder path {folder_path} does not exist or is not a directory.")
        sys.exit(1)

    # Process the folder
    move_matching_files(folder_path)
