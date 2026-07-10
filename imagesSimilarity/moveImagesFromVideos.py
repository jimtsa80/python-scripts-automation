import os
import shutil
import sys

def move_images(source_folder):
    # Define the destination folder for Type 1 images
    dest_folder_type1 = source_folder + "_imagesOnly"
    
    # Create the destination folder if it doesn't exist
    os.makedirs(dest_folder_type1, exist_ok=True)

    # Iterate through the files in the source folder
    for filename in os.listdir(source_folder):
        # Ignore files that are not images (skip if the file has an extension)
        name_without_extension, ext = os.path.splitext(filename)
        
        if ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:  # Add other image extensions if needed
            # Split the filename by underscores and focus on the part before the file extension
            parts = name_without_extension.rsplit('_', 1)  # Split only on the last underscore
            print(parts)
            
            # Check if the last part has 1 to 3 characters
            if len(parts[-1]) >= 1 and len(parts[-1]) <= 3:
                # Move the image to the destination folder
                shutil.move(os.path.join(source_folder, filename), os.path.join(dest_folder_type1, filename))

    print(f"Moved Type 1 images to {dest_folder_type1}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <source_folder>")
    else:
        move_images(sys.argv[1])
