import os
import shutil
import sys

def multiply_files(folder_path, times, prefix):
    try:
        # Validate folder path
        if not os.path.isdir(folder_path):
            print(f"Error: '{folder_path}' is not a valid directory.")
            return
        
        # Ensure prefix ends with an underscore
        if not prefix.endswith("_"):
            prefix += "_"
        
        # Get the list of files in the folder
        files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        if not files:
            print(f"No files found in '{folder_path}'.")
            return
        
        # Duplicate each file in the folder
        for original_file in files:
            original_file_path = os.path.join(folder_path, original_file)
            print(f"Multiplicating file: {original_file}")
            
            for i in range(1, times + 1):
                new_filename = f"{prefix}{os.path.splitext(original_file)[0]}_{i:06d}{os.path.splitext(original_file)[1]}"
                new_file_path = os.path.join(folder_path, new_filename)
                shutil.copy2(original_file_path, new_file_path)
        
        print(f"Successfully multiplicated all files in '{folder_path}' {times} times with prefix '{prefix}'.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Check if script is called with arguments
    if len(sys.argv) != 4:
        print("Usage: python script.py <folder_path> <times> <prefix>")
    else:
        folder_path = sys.argv[1]
        times = int(sys.argv[2])
        prefix = sys.argv[3]
        multiply_files(folder_path, times, prefix)