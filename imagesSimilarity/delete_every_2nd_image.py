import os
import sys
from tqdm import tqdm

def delete_every_second_image(folder_path):
    # Check folder
    if not os.path.isdir(folder_path):
        print(f"❌ The provided path '{folder_path}' is not a folder.")
        return

    # Get all files (sorted)
    files = sorted([
        f for f in os.listdir(folder_path)
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'))
    ])

    total_files = len(files)
    print(f"📂 Found {total_files} image files in: {folder_path}")

    # If no files, exit
    if total_files == 0:
        print("⚠️ No image files found.")
        return

    # Iterate and delete every 2nd file (index 1, 3, 5, ...)
    print("🧹 Deleting every second file...")
    for i in tqdm(range(len(files)), desc="Processing"):
        if i % 2 == 1:  # delete 2nd, 4th, 6th, etc.
            file_to_delete = os.path.join(folder_path, files[i])
            try:
                os.remove(file_to_delete)
            except Exception as e:
                print(f"⚠️ Could not delete {file_to_delete}: {e}")

    # Final count
    remaining = len([
        f for f in os.listdir(folder_path)
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'))
    ])
    print(f"✅ Done! Remaining files: {remaining}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python delete_every_second_image.py <folder_path>")
        sys.exit(1)

    folder = sys.argv[1]
    delete_every_second_image(folder)
