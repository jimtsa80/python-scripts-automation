import os
import shutil
import pandas as pd
import sys

def filter_and_move_images(csv_file, image_folder, row_limits={1: 600, 2: 1800, 3: 600, 4: 1800, 5: 600}):
    df = pd.read_csv(csv_file, delimiter=',', header=None)
    output_folder = f"sample_{os.path.basename(image_folder)}"
    os.makedirs(output_folder, exist_ok=True)
    
    selected_intervals = [(row[0], row[1]) for _, row in df.iterrows()]
    print("Selected intervals:", selected_intervals)
    
    image_files = [f for f in os.listdir(image_folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    image_numbers = sorted([int(os.path.splitext(f)[0]) for f in image_files if os.path.splitext(f)[0].isdigit()])
    
    total_images_in_ranges = 0
    images_to_move = []
    
    for i, (start, end) in enumerate(selected_intervals):
        interval_limit = row_limits.get(i + 1, float('inf'))  # Defaults to no limit
        
        # Select images within the interval
        images_in_range = [f for f in image_files if start <= int(os.path.splitext(f)[0]) <= end]
        
        # For rows 2 and 4 (1800 images)
        if i + 1 == 2 or i + 1 == 4:
            # Take a range of exactly 1800 numbers, but we don't care about the images count
            start_number = start
            end_number = start_number + 1799  # 1800 total
            selected_images = [f for f in image_files if start_number <= int(os.path.splitext(f)[0]) <= end_number]
            
            print(f"Selected interval ({start_number}-{end_number}) with {len(selected_images)} images")
            
            images_to_move.extend(selected_images)
        
        # For rows 1, 3, and 5 (600 images)
        elif i + 1 == 1 or i + 1 == 3 or i + 1 == 5:
            # Take a range of exactly 600 numbers, but we don't care about the images count
            start_number = start
            end_number = start_number + 599  # 600 total
            selected_images = [f for f in image_files if start_number <= int(os.path.splitext(f)[0]) <= end_number]
            
            print(f"Selected interval ({start_number}-{end_number}) with {len(selected_images)} images")
            
            images_to_move.extend(selected_images)
        
        total_images_in_ranges += len(images_in_range)
    
    print(f"Total images across all selected intervals: {total_images_in_ranges}")
    
    moved_count = 0
    for img in images_to_move:
        shutil.copy(os.path.join(image_folder, img), os.path.join(output_folder, img))
        moved_count += 1
    
    print(f"Moved {moved_count} images to {output_folder}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <csv_file> <image_folder>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    image_folder = sys.argv[2]
    filter_and_move_images(csv_file, image_folder)
