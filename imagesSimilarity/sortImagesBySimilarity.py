import os
import cv2
import numpy as np
from scipy.spatial.distance import euclidean
from tqdm import tqdm
import shutil

def safe_path(path):
    """Ensures compatibility with long file paths on Windows."""
    abs_path = os.path.abspath(path)
    return f"\\\\?\\{abs_path}" if os.name == 'nt' and not abs_path.startswith('\\\\?\\') else abs_path

def get_image_histogram(image_path, target_size=(256, 256)):
    try:
        image = cv2.imread(safe_path(image_path))
        if image is None:
            return None
        image = cv2.resize(image, target_size, interpolation=cv2.INTER_AREA)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        hist = cv2.calcHist([image], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        return cv2.normalize(hist, hist).flatten()
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")
        return None

def calculate_distances(histograms):
    num_images = len(histograms)
    distances = np.zeros((num_images, num_images))
    for i in range(num_images):
        for j in range(i + 1, num_images):
            distance = euclidean(histograms[i], histograms[j])
            distances[i, j] = distance
            distances[j, i] = distance
    return distances

def move_invalid_images(image_paths, folder):
    invalid_folder = os.path.join(folder, "invalid_images")
    os.makedirs(invalid_folder, exist_ok=True)
    for path in image_paths:
        shutil.move(safe_path(path), safe_path(os.path.join(invalid_folder, os.path.basename(path))))
    print(f"Moved {len(image_paths)} invalid images to: {invalid_folder}")

def sort_images_by_similarity(folder):
    folder = safe_path(folder)
    image_paths = [os.path.join(folder, f) for f in os.listdir(folder)
                   if f.lower().endswith(('png', 'jpg', 'jpeg', 'bmp'))]
    if not image_paths:
        print("No images found in the folder.")
        return

    valid_histograms = []
    valid_image_paths = []
    invalid_image_paths = []

    print("Processing images...")
    for path in tqdm(image_paths, desc="Processing"):
        hist = get_image_histogram(path)
        if hist is not None:
            valid_histograms.append(hist)
            valid_image_paths.append(path)
        else:
            invalid_image_paths.append(path)

    if invalid_image_paths:
        move_invalid_images(invalid_image_paths, folder)

    if not valid_image_paths:
        print("No valid images to process after filtering.")
        return

    print("Calculating distances between valid images...")
    distances = calculate_distances(valid_histograms)
    start_index = 0
    sorted_indices = [start_index]
    current_index = start_index

    while len(sorted_indices) < len(valid_image_paths):
        remaining_indices = [i for i in range(len(valid_image_paths)) if i not in sorted_indices]
        next_index = min(remaining_indices, key=lambda x: distances[current_index, x])
        sorted_indices.append(next_index)
        current_index = next_index

    print("Sorting images and renaming...")
    temp_names = []
    for i, index in enumerate(sorted_indices):
        original_path = valid_image_paths[index]
        temp_name = os.path.join(folder, f"temp_{i+1:03d}.tmp")
        os.rename(safe_path(original_path), safe_path(temp_name))
        temp_names.append((temp_name, os.path.basename(original_path)))

    for i, (temp_name, original_filename) in enumerate(temp_names):
        base_name, ext = os.path.splitext(original_filename)
        new_name = os.path.join(folder, f"sort_{i:05d}_{base_name}{ext}")
        os.rename(safe_path(temp_name), safe_path(new_name))

    print("Sorting complete. Images renamed sequentially in folder:", folder)

def process_all_subfolders(root_folder):
    root_folder = safe_path(root_folder)
    for subfolder in os.listdir(root_folder):
        subfolder_path = os.path.join(root_folder, subfolder)
        if os.path.isdir(subfolder_path):
            print(f"Processing subfolder: {subfolder}")
            sort_images_by_similarity(subfolder_path)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python sort_images_by_similarity.py <root_folder>")
        sys.exit(1)
    root_folder = sys.argv[1]
    process_all_subfolders(root_folder)
