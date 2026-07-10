import os
import cv2
import numpy as np
from scipy.spatial.distance import euclidean
from tqdm import tqdm

def safe_path(path):
    """Ensures compatibility with long file paths on Windows."""
    abs_path = os.path.abspath(path)
    return f"\\\\?\\{abs_path}" if os.name == 'nt' and not abs_path.startswith('\\\\?\\') else abs_path

def get_image_histogram(image_path):
    image = cv2.imread(safe_path(image_path))
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    hist = cv2.calcHist([image], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    return cv2.normalize(hist, hist).flatten()

def calculate_distances(histograms):
    num_images = len(histograms)
    distances = np.zeros((num_images, num_images))
    for i in range(num_images):
        for j in range(i + 1, num_images):
            distance = euclidean(histograms[i], histograms[j])
            distances[i, j] = distance
            distances[j, i] = distance
    return distances

def sort_images_by_similarity(folder):
    folder = safe_path(folder)
    image_paths = [os.path.join(folder, f) for f in os.listdir(folder)
                   if f.lower().endswith(('png', 'jpg', 'jpeg', 'bmp'))]
    if not image_paths:
        print(f"No images found in folder: {folder}")
        return

    histograms = []
    for path in tqdm(image_paths, desc="Calculating Histograms"):
        try:
            histograms.append(get_image_histogram(path))
        except ValueError as e:
            print(e)

    distances = calculate_distances(histograms)
    sorted_indices = [0]
    current_index = 0
    while len(sorted_indices) < len(image_paths):
        remaining_indices = [i for i in range(len(image_paths)) if i not in sorted_indices]
        next_index = min(remaining_indices, key=lambda x: distances[current_index, x])
        sorted_indices.append(next_index)
        current_index = next_index

    temp_names = []
    for i, index in enumerate(tqdm(sorted_indices, desc="Renaming Images")):
        original_path = image_paths[index]
        temp_name = os.path.join(folder, f"temp_{i:03d}.tmp")
        os.rename(original_path, safe_path(temp_name))
        temp_names.append((temp_name, os.path.basename(original_path)))

    for i, (temp_name, original_filename) in enumerate(temp_names):
        new_filename = f"{i:05d}"
        base_filename, ext = os.path.splitext(original_filename)
        new_name = os.path.join(folder, f"sort_{new_filename}_{base_filename}{ext}")
        os.rename(safe_path(temp_name), safe_path(new_name))
    print(f"Sorting complete. Images renamed sequentially in folder: {folder}")

def process_all_subfolders(root_folder):
    root_folder = safe_path(root_folder)
    try:
        subfolders = os.listdir(root_folder)
    except FileNotFoundError:
        # Path may not exist if makeClusters renamed reduced_... to "temp"; try parent/temp (same level)
        parent = os.path.dirname(root_folder.rstrip(os.sep))
        fallback_same = os.path.join(parent, "temp")
        fallback_same = safe_path(fallback_same)
        # Or try grandparent/temp/<last_folder_name> e.g. .../batch12/temp/reduced_...
        grandparent = os.path.dirname(parent)
        fallback_proteleft = os.path.join(grandparent, "temp", os.path.basename(root_folder.rstrip(os.sep)))
        fallback_proteleft = safe_path(fallback_proteleft)
        for fallback in (fallback_same, fallback_proteleft):
            if os.path.isdir(fallback):
                root_folder = fallback
                subfolders = os.listdir(root_folder)
                break
        else:
            raise
    for subfolder in subfolders:
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