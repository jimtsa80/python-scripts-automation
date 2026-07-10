import os
import shutil
import argparse

def move_files(txt_file, image_folder):
    # Create 'done' folder if it doesn't exist
    done_folder = os.path.join(image_folder, 'done')
    if not os.path.exists(done_folder):
        os.makedirs(done_folder)
    
    # Read filenames from the text file
    with open(txt_file, 'r') as f:
        filenames = [line.strip() for line in f.readlines()]
    
    # Iterate through filenames and move matching files
    for filename in filenames:
        # Check for possible file extensions
        for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:  # You can add more extensions if needed
            source_file = os.path.join(image_folder, filename + ext)
            if os.path.exists(source_file):
                dest_file = os.path.join(done_folder, filename + ext)
                shutil.move(source_file, dest_file)
                print(f"Moved: {source_file} -> {dest_file}")
                break

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Move files listed in a text file to a 'done' folder.")
    parser.add_argument('txt_file', type=str, help="Path to the text file containing filenames (without extensions).")
    parser.add_argument('image_folder', type=str, help="Path to the folder containing the images.")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Call the function to move files
    move_files(args.txt_file, args.image_folder)

if __name__ == "__main__":
    main()