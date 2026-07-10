import os
import shutil
import sys

def move_files(file_list_path, source_folder):
    # Ensure the provided folder exists
    if not os.path.isdir(source_folder):
        print(f"Error: The folder '{source_folder}' does not exist.")
        return
    
    # Read filenames from the text file
    try:
        with open(file_list_path, 'r', encoding='utf-8') as f:
            filenames = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: The file '{file_list_path}' was not found.")
        return
    
    # Create temp folder inside the source folder
    temp_folder = os.path.join(source_folder, "temp_removed_files")
    os.makedirs(temp_folder, exist_ok=True)
    
    moved_files = 0
    for filename in filenames:
        src_path = os.path.join(source_folder, filename)
        dest_path = os.path.join(temp_folder, filename)
        
        if os.path.exists(src_path):
            shutil.move(src_path, dest_path)
            moved_files += 1
            print(f"Moved: {filename}")
        else:
            print(f"Warning: File '{filename}' not found in '{source_folder}'.")
    
    print(f"Done. Moved {moved_files} files to '{temp_folder}'.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python move_files.py <file_list.txt> <source_folder>")
    else:
        move_files(sys.argv[1], sys.argv[2])