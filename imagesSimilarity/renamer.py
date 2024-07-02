import os
import sys

def rename_files_in_folder(folder_path, start_number):
    try:
        # Convert start_number to an integer
        start_number = int(start_number)
        
        # List all files in the directory
        files = os.listdir(folder_path)
        
        # Sort files to ensure consistent renaming order
        files.sort()

        # Rename each file with increasing number
        for i, filename in enumerate(files):
            # Construct the new filename with leading zeros
            new_number = str(start_number + i).zfill(6)
            new_filename = f"{new_number}{os.path.splitext(filename)[1]}"
            
            # Get full file paths
            src = os.path.join(folder_path, filename)
            dst = os.path.join(folder_path, new_filename)
            
            # Rename the file
            os.rename(src, dst)
            print(f"Renamed '{src}' to '{dst}'")
    
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python rename_files.py <folder_path> <start_number>")
    else:
        folder_path = sys.argv[1]
        start_number = sys.argv[2]
        rename_files_in_folder(folder_path, start_number)