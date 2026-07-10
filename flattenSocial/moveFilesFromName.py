import os
import shutil
import sys
import re

def move_and_rename_files_to_temp_folder(source_folder):
    # Create the temp folder inside the source folder
    temp_folder = os.path.join(source_folder, 'temp')
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)
    
    # Initialize a counter for the number of files moved
    files_moved = 0
    
    # Iterate over all files in the source folder
    for filename in os.listdir(source_folder):
        # Check if the file has a pattern like .1, .2, .3 before the file extension
        match = re.search(r'(\.\d+)(\.[^.]+)$', filename)
        if match:
            # Extract the number and the file extension
            number_part = match.group(1)
            extension_part = match.group(2)
            
            # Replace the number part with an underscore
            new_filename = filename.replace(number_part, number_part.replace('.', '_'))
            
            # Construct the full file path
            source_path = os.path.join(source_folder, filename)
            
            # Construct the new file path in the temp folder
            destination_path = os.path.join(temp_folder, new_filename)
            
            # Move and rename the file
            shutil.move(source_path, destination_path)
            
            # Increment the counter
            files_moved += 1
    
    # Print the number of files moved
    print(f"Files have been moved and renamed successfully to the 'temp' folder. Total files moved: {files_moved}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <source_folder>")
        sys.exit(1)
    
    source_folder = sys.argv[1]
    
    move_and_rename_files_to_temp_folder(source_folder)