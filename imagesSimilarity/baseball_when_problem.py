import os
import sys

def get_image_filenames(folder, extensions):
    """Return a set of image filenames in the given folder."""
    return set(
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f)) and f.lower().endswith(extensions)
    )

def delete_common_images(folder1, folder2):
    # Image file extensions to consider
    extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp')
    
    # Get filenames (not paths) of images in both folders
    images1 = get_image_filenames(folder1, extensions)
    images2 = get_image_filenames(folder2, extensions)
    
    # Find common filenames
    common_images = images1 & images2
    
    # Delete those images from folder2
    for filename in common_images:
        file_to_delete = os.path.join(folder2, filename)
        try:
            os.remove(file_to_delete)
            print(f"Deleted: {file_to_delete}")
        except Exception as e:
            print(f"Could not delete {file_to_delete}: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <folder1> <folder2>")
        sys.exit(1)
    
    folder1 = sys.argv[1]
    folder2 = sys.argv[2]
    
    if not (os.path.isdir(folder1) and os.path.isdir(folder2)):
        print("Both arguments must be existing directories.")
        sys.exit(1)
    
    delete_common_images(folder1, folder2)