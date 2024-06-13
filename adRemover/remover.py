import cv2
import os
import shutil
import sys
from tqdm import tqdm

def detect_logo(image_path, logo_template, threshold=0.8, search_region=None):
    image = cv2.imread(image_path, 0)  # Read the image in grayscale
    if search_region:
        x, y, w, h = search_region
        image = image[y:y+h, x:x+w]
    
    # Check if the region is smaller than the template
    if image.shape[0] < logo_template.shape[0] or image.shape[1] < logo_template.shape[1]:
        return False

    result = cv2.matchTemplate(image, logo_template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    return max_val >= threshold

def process_images(input_folder, logo_path, output_folder, threshold=0.8, search_region=None):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    print(f"Loading logo template from: {logo_path}")
    logo_template = cv2.imread(logo_path, 0)

    print(f"Loading images from folder: {input_folder}")
    filenames = [f for f in os.listdir(input_folder) if os.path.isfile(os.path.join(input_folder, f))]

    print(f"Processing {len(filenames)} images...")
    for filename in tqdm(filenames, desc="Processing images"):
        image_path = os.path.join(input_folder, filename)
        if not detect_logo(image_path, logo_template, threshold, search_region):
            print(f"Moving image {filename} to {output_folder} (logo not detected)")
            shutil.move(image_path, os.path.join(output_folder, filename))
        else:
            print(f"Logo detected in image {filename}")

    print("Processing completed.")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python script.py <input_folder> <logo_path> <output_folder>")
        sys.exit(1)

    input_folder = sys.argv[1]
    logo_path = sys.argv[2]
    output_folder = sys.argv[3]

    print(f"Input folder: {input_folder}")
    print(f"Logo path: {logo_path}")
    print(f"Output folder: {output_folder}")

    # Define the search region (x, y, width, height) for the logo detection
    search_region = (1707, 54, 159, 105)  # Replace these values with the actual coordinates
    print(f"Search region: {search_region}")

    # Process the images
    process_images(input_folder, logo_path, output_folder, threshold=0.8, search_region=search_region)
