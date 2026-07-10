import os
import shutil
import sys
from tqdm import tqdm

def move_matching_images(image_folder, txt_file):
    # Read strings from txt file
    with open(txt_file, "r", encoding="utf-8") as f:
        keywords = [line.strip() for line in f if line.strip()]
    
    # Ensure folder exists
    if not os.path.isdir(image_folder):
        print(f"Error: Folder '{image_folder}' not found.")
        return
    
    # Create destination folder
    parent_dir = os.path.dirname(image_folder)
    folder_name = os.path.basename(image_folder)
    dest_folder = os.path.join(parent_dir, f"sample_{folder_name}")
    os.makedirs(dest_folder, exist_ok=True)
    
    # Process images
    images_moved = 0
    images = [f for f in os.listdir(image_folder) if os.path.isfile(os.path.join(image_folder, f))]
    
    for image in tqdm(images, desc="Processing images", unit="file"):
        if any(keyword in image for keyword in keywords):
            shutil.move(os.path.join(image_folder, image), os.path.join(dest_folder, image))
            images_moved += 1
    
    print(f"Total images moved: {images_moved}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <image_folder> <txt_file>")
    else:
        move_matching_images(sys.argv[1], sys.argv[2])