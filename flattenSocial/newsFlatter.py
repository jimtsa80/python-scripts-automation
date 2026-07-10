import os
import shutil
import sys
import time
import stat

def make_writable(func, path, _):
    """Change file permissions to writable and retry deletion."""
    os.chmod(path, stat.S_IWUSR)
    func(path)

def flatten_folders(initial_folder):
    for root, dirs, files in os.walk(initial_folder):
        for dir_name in dirs:
            folder_path = os.path.join(root, dir_name)

            # Move all files from the subfolder to the main folder
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)

                if os.path.isfile(file_path):
                    base_name, extension = os.path.splitext(file_name)
                    new_folder_name = dir_name.replace(" ", "").replace(".", "_")
                    new_base_name = base_name.replace(" ", "").replace(".", "_")
                    new_name = f"{new_folder_name}_{new_base_name}{extension}"
                    new_file_path = os.path.join(initial_folder, new_name)

                    # Ensure unique filenames
                    counter = 1
                    while os.path.exists(new_file_path):
                        new_name = f"{new_folder_name}_{new_base_name}_{counter}{extension}"
                        new_file_path = os.path.join(initial_folder, new_name)
                        counter += 1

                    shutil.move(file_path, new_file_path)

            # Attempt to remove the folder with retries
            for _ in range(5):  # Retry up to 5 times
                try:
                    shutil.rmtree(folder_path, onerror=make_writable)
                    break  # If successful, exit loop
                except PermissionError:
                    print(f"Warning: Could not delete {folder_path}, retrying...")
                    time.sleep(1)  # Wait 1 second before retrying

    print(f"Flattening complete for folder: {initial_folder}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python flatten_folders.py <initial_folder>")
        sys.exit(1)

    initial_folder = sys.argv[1]
    if not os.path.isdir(initial_folder):
        print(f"Error: {initial_folder} is not a valid directory.")
        sys.exit(1)

    flatten_folders(initial_folder)
