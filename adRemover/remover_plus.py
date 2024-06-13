import cv2
import os
import shutil
import sys
from tqdm import tqdm

def detect_logo(image_path, logo_templates, threshold=0.8, search_region=None):
    image = cv2.imread(image_path, 0)  # Read the image in grayscale
    if search_region:
        x, y, w, h = search_region
        image = image[y:y+h, x:x+w]
    
    # Iterate through each logo template to check for a match
    for logo_template in logo_templates:
        # Check if the region is smaller than the template
        if image.shape[0] < logo_template.shape[0] or image.shape[1] < logo_template.shape[1]:
            continue
        
        result = cv2.matchTemplate(image, logo_template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        if max_val >= threshold:
            return True
    
    return False

def load_logo_templates(logo_folder):
    logo_templates = []
    for filename in os.listdir(logo_folder):
        logo_path = os.path.join(logo_folder, filename)
        if os.path.isfile(logo_path):
            logo_template = cv2.imread(logo_path, 0)
            if logo_template is not None:
                logo_templates.append(logo_template)
    return logo_templates

def process_images(input_folder, logo_folder, output_folder, threshold=0.8, search_region=None):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    print(f"Loading logo templates from folder: {logo_folder}")
    logo_templates = load_logo_templates(logo_folder)

    if not logo_templates:
        print("No valid logo templates found. Exiting.")
        return

    print(f"Loaded {len(logo_templates)} logo templates.")

    print(f"Loading images from folder: {input_folder}")
    filenames = [f for f in os.listdir(input_folder) if os.path.isfile(os.path.join(input_folder, f))]

    print(f"Processing {len(filenames)} images...")
    for filename in tqdm(filenames, desc="Processing images"):
        image_path = os.path.join(input_folder, filename)
        if not detect_logo(image_path, logo_templates, threshold, search_region):
            print(f"Moving image {filename} to {output_folder} (logo not detected)")
            shutil.move(image_path, os.path.join(output_folder, filename))
        else:
            print(f"Logo detected in image {filename}")

    print("Processing completed.")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python script.py <input_folder> <logo_folder> <output_folder>")
        sys.exit(1)

    input_folder = sys.argv[1]
    logo_folder = sys.argv[2]
    output_folder = sys.argv[3]

    print(f"Input folder: {input_folder}")
    print(f"Logo folder: {logo_folder}")
    print(f"Output folder: {output_folder}")

    # Define the search region (x, y, width, height) for the logo detection
    search_region = (1707, 54, 159, 105)  # Replace these values with the actual coordinates
    print(f"Search region: {search_region}")

    # Process the images
    process_images(input_folder, logo_folder, output_folder, threshold=0.8, search_region=search_region)
