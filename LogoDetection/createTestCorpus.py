import os
import zipfile
import pandas as pd
import argparse
from shutil import move

def process_frames(file_path, brand, location, image_folder):
    # Read the Excel file
    print(f"Reading Excel file: {file_path}")
    df = pd.read_excel(file_path)

    # Filter rows by brand and location
    print(f"Filtering data for Brand: {brand} and Location: {location}")
    filtered_df = df[(df['Brand'] == brand) & (df['Location'] == location)]

    # Initialize the final list of frames
    frame_list = []

    # Loop through filtered rows and generate frame sequences
    for _, row in filtered_df.iterrows():
        start_frame = row['Sequence Frame Number']
        duration = row['Duration']
        frame_list.extend(range(start_frame, start_frame + duration))

    # Convert frame numbers to 6-digit strings
    frame_list = [f"{frame:06d}" for frame in frame_list]
    print(f"Generated frame list: {frame_list}")

    # Process the image folder
    matched_images = []
    print(f"Searching for matching images in folder: {image_folder}")
    for root, _, files in os.walk(image_folder):
        for file in files:
            file_no_ext = os.path.splitext(file)[0]
            if file_no_ext in frame_list:
                matched_images.append(os.path.join(root, file))

    print(f"Matched {len(matched_images)} images.")

    # Create the output folder based on the combination
    output_combination_folder = os.path.join(os.getcwd(), f"{brand}_{location}")
    os.makedirs(output_combination_folder, exist_ok=True)
    print(f"Output folder created: {output_combination_folder}")

    # Move and rename images
    for image_path in matched_images:
        image_name = os.path.basename(image_path)
        new_image_name = f"{os.path.splitext(os.path.basename(file_path))[0]}_{image_name}"
        new_image_path = os.path.join(output_combination_folder, new_image_name)
        move(image_path, new_image_path)
        print(f"Moved and renamed: {image_path} -> {new_image_path}")

    print(f"Process completed. {len(matched_images)} images moved to {output_combination_folder}")


def find_matching_folder(input_folder, file_name):
    # Search for a folder or zip file with the same name as the Excel file
    base_name = os.path.splitext(os.path.basename(file_name))[0]
    print(f"Searching for folder or zip matching the Excel file name: {base_name}")
    for root, dirs, files in os.walk(input_folder):
        for folder in dirs:
            if folder == base_name:
                print(f"Matching folder found: {folder}")
                return os.path.join(root, folder)
        for file in files:
            if file == f"{base_name}.zip":
                zip_path = os.path.join(root, file)
                extract_path = os.path.join(root, base_name)
                print(f"Matching zip file found: {file}. Extracting to: {extract_path}")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                return extract_path
    raise FileNotFoundError(f"No matching folder or zip found for {file_name} in {input_folder}")


if __name__ == "__main__":
    # Set up command line arguments
    parser = argparse.ArgumentParser(description="Process frame sequences and match images.")
    parser.add_argument("file_path", help="Path to the input Excel file.")
    parser.add_argument("brand", help="Brand to filter.")
    parser.add_argument("location", help="Location to filter.")
    parser.add_argument("image_folder", help="Path to the folder containing images or zip file.")

    args = parser.parse_args()

    try:
        # Find the matching folder
        matching_folder = find_matching_folder(args.image_folder, args.file_path)
        print(f"Found matching folder: {matching_folder}")

        # Process the frames and move images
        process_frames(args.file_path, args.brand, args.location, matching_folder)
    except FileNotFoundError as e:
        print(f"Error: {e}")
