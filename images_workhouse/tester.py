import cv2
import numpy as np
import os
import shutil

def find_and_copy_images(template_path, folder_path, output_file, dest_folder, threshold=0.8):
    # Load the template image
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        print(f"Failed to load template image: {template_path}")
        return

    template_height, template_width = template.shape

    # Create destination folder if it doesn't exist
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)

    # Open the output file to write the results
    with open(output_file, 'w') as f:
        # Iterate over images in the folder
        for image_name in os.listdir(folder_path):
            image_path = os.path.join(folder_path, image_name)
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                print(f"Failed to load image: {image_path}")
                continue

            # Perform template matching
            result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)

            # Get the locations of matches
            locations = np.where(result >= threshold)
            if len(locations[0]) > 0:
                print(f"Template found in image: {image_path}")
                f.write(f"{image_name}\n")
                
                # Copy the matched image to the destination folder
                shutil.copy(image_path, os.path.join(dest_folder, image_name))
            else:
                print(f"Template not found in image: {image_path}")

# Example usage:
template_path = 'geico.jpg'
folder_path = 'test-images'
output_file = 'output.txt'
dest_folder = 'results-images'
find_and_copy_images(template_path, folder_path, output_file, dest_folder)
