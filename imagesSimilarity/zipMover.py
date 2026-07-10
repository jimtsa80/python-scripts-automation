import os
import shutil
import argparse

def move_zip_files(root_folder):
    """
    Move all .zip files from subfolders to the root folder.
    """
    for subdir, _, files in os.walk(root_folder):
        if subdir == root_folder:
            continue  # Skip the root folder itself
        
        for file in files:
            if file.endswith(".zip"):
                src_path = os.path.join(subdir, file)
                dest_path = os.path.join(root_folder, file)
                
                # Ensure unique filenames
                counter = 1
                while os.path.exists(dest_path):
                    name, ext = os.path.splitext(file)
                    dest_path = os.path.join(root_folder, f"{name}_{counter}{ext}")
                    counter += 1
                
                shutil.move(src_path, dest_path)
                print(f"Moved: {src_path} -> {dest_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Move all .zip files from subfolders to the root folder.")
    parser.add_argument("folder", type=str, help="Path to the root folder")
    args = parser.parse_args()
    
    move_zip_files(args.folder)