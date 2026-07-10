import os
import sys
import re
import ctypes

def enable_long_paths():
    try:
        ctypes.windll.kernel32.SetFileApisToOEM()
    except AttributeError:
        pass  # This function is not available on non-Windows systems

def rename_items(folder_path):
    if not os.path.exists(folder_path):
        print("Error: Folder does not exist.")
        return
    
    for item in os.listdir(folder_path):
        full_old_path = os.path.join(folder_path, item)
        
        game_match = re.search(r'Game.*', item)
        
        if game_match:
            new_name = game_match.group()
            full_new_path = os.path.join(folder_path, new_name)
            
            try:
                os.rename("\\\\?\\" + full_old_path, "\\\\?\\" + full_new_path)
                print(f'Renamed: "{full_old_path}" -> "{full_new_path}"')
            except Exception as e:
                print(f'Error renaming "{full_old_path}": {e}')
        else:
            print(f'Skipped: "{full_old_path}" (No match found)')

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python rename_files.py \"<folder_path>\"")
    else:
        enable_long_paths()
        rename_items(sys.argv[1])