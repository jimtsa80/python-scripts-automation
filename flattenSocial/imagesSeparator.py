import os
import shutil
import sys
import chardet

def detect_encoding(file_path):
    with open(file_path, "rb") as f:
        raw_data = f.read(10000)
        result = chardet.detect(raw_data)
        return result["encoding"]

def move_files_by_substrings(target_folder, substrings_file):
    encoding = detect_encoding(substrings_file)
    
    with open(substrings_file, 'r', encoding=encoding) as f:
        substrings = [line.strip() for line in f if line.strip()]
    
    if not substrings:
        print("No substrings provided.")
        return
    
    temp_folder = os.path.join(target_folder, "temp")
    os.makedirs(temp_folder, exist_ok=True)
    
    for filename in os.listdir(target_folder):
        file_path = os.path.join(target_folder, filename)
        if os.path.isfile(file_path) and any(sub in filename for sub in substrings):
            shutil.move(file_path, os.path.join(temp_folder, filename))
            print(f"Moved: {filename}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <folder_path> <substrings_file>")
    else:
        move_files_by_substrings(sys.argv[1], sys.argv[2])