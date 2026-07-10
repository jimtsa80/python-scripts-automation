import os
import sys
import shutil
import re

def sanitize(name):
    # Replace all non-alphanumeric characters with '_'
    return re.sub(r'[^A-Za-z0-9_]', '_', name)

def flatten_folder(root_folder):
    root_folder = os.path.abspath(root_folder)
    parent_dir = os.path.dirname(root_folder)
    flatten_dir = os.path.join(parent_dir, 'flatten')

    if not os.path.isdir(root_folder):
        print(f'Error: {root_folder} is not a directory.')
        sys.exit(1)
    if not os.path.exists(flatten_dir):
        os.makedirs(flatten_dir)
    
    for dirpath, dirnames, filenames in os.walk(root_folder):
        if dirpath == root_folder:
            continue  # Skip the root itself
        relpath = os.path.relpath(dirpath, root_folder)
        sanitized_folders = sanitize(relpath.replace(os.sep, '_'))
        for filename in filenames:
            src_path = os.path.join(dirpath, filename)
            new_filename = f"{sanitized_folders}_{filename}"
            dest_path = os.path.join(flatten_dir, new_filename)
            print(f"Copying: {src_path} -> {dest_path}")
            shutil.copy2(src_path, dest_path)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <folder1>")
        sys.exit(1)
    flatten_folder(sys.argv[1])