import os
import re
import shutil
import sys

def move_files_with_number(source_folder):
    # Create the temp folder inside the source folder
    temp_folder = os.path.join(source_folder, "temp")
    os.makedirs(temp_folder, exist_ok=True)

    # Regex to find files ending with numbers >= 61 before the extension
    pattern = re.compile(r".*_(\d+)\.[a-zA-Z]+$")
    moved_files_count = 0  # Counter for the number of moved files

    # Iterate through files in the source folder
    for filename in os.listdir(source_folder):
        source_file_path = os.path.join(source_folder, filename)

        # Check if it's a file
        if os.path.isfile(source_file_path):
            # Check if the filename ends with a number >= 61
            match = pattern.match(filename)
            if match:
                number = int(match.group(1))  # Extract the trailing number
                if number >= 61:
                    # Move the file to the temp folder
                    shutil.move(source_file_path, os.path.join(temp_folder, filename))
                    print(f"Moved: {filename} -> {temp_folder}")
                    moved_files_count += 1

    # Print the total number of files moved
    print(f"\nTotal files moved: {moved_files_count}")

if __name__ == "__main__":
    # Ensure the user provides the source folder as an argument
    if len(sys.argv) != 2:
        print("Usage: python script.py <source_folder>")
        sys.exit(1)

    source_folder = sys.argv[1]

    # Validate the source folder
    if not os.path.isdir(source_folder):
        print(f"Error: {source_folder} is not a valid directory.")
        sys.exit(1)

    move_files_with_number(source_folder)
