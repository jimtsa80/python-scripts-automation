import os
import numpy as np
import argparse
from PIL import UnidentifiedImageError
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.resnet50 import preprocess_input
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm
import shutil
import re

# Load pre-trained ResNet50 model
model = ResNet50(weights='imagenet', include_top=False, pooling='max')

# Function to convert image to feature vector
def image_to_feature_vector(img_path, model):
    try:
        img = image.load_img(img_path, target_size=(224, 224))
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)

        features = model.predict(img_array, verbose=0)
        return features.flatten()
    except UnidentifiedImageError:
        print(f"Skipping unreadable image: {img_path}")
        return None
    except FileNotFoundError:
        print(f"Skipping missing image: {img_path}")
        return None

# Function to sanitize folder names
def sanitize_filename(name):
    """Remove invalid characters from folder names."""
    return re.sub(r'[<>:"/\\|?*]', '_', name)

# Function to normalize path for long paths
def normalize_path(path):
    """Adds the long path prefix for Windows if necessary."""
    if os.name == 'nt':
        if len(path) > 259:
            # Add the \\?\ prefix for long paths
            # Note: The prefix must be applied to the absolute path with a drive letter.
            if path.startswith('\\\\?\\'):
                return path  # Already normalized

            # If the path starts with a drive letter (e.g., C:), add the prefix.
            if path[1] == ':' and path[0].isalpha():
                # Ensure there are no extra backslashes at the beginning
                return r'\\?\\' + path.lstrip('\\')

            # If the path is a UNC path (e.g., \\server\share), add the UNC prefix.
            if path.startswith(r'\\'):
                return r'\\?\UNC\\' + path[2:]
    return path

# Main function to process images
def process_images(image_folder, num_clusters):
    # Normalize the input folder path immediately
    image_folder = normalize_path(image_folder)
    
    if not os.path.isdir(image_folder):
        print(f"Error: The specified folder '{image_folder}' does not exist or is not a directory.")
        return

    image_paths = [normalize_path(os.path.join(image_folder, f)) for f in os.listdir(image_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]
    folder_name = sanitize_filename(os.path.basename(os.path.normpath(image_folder)))

    print("Extracting features from images...")
    feature_vectors = []
    valid_image_paths = []

    for img in tqdm(image_paths, desc="Processing images"):
        features = image_to_feature_vector(img, model)
        if features is not None:
            feature_vectors.append(features)
            valid_image_paths.append(img)

    if not feature_vectors:
        print("No valid images found to cluster. Exiting.")
        return

    feature_vectors = np.array(feature_vectors)

    print("Clustering images...")
    kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init='auto')
    labels = kmeans.fit_predict(feature_vectors)

    print("Organizing clusters...")
    for cluster in tqdm(range(num_clusters), desc="Organizing clusters"):
        cluster_indices = np.where(labels == cluster)[0]
        cluster_features = feature_vectors[cluster_indices]
        
        similarity_matrix = cosine_similarity(cluster_features)
        
        sorted_indices = np.argsort(similarity_matrix.sum(axis=1))[::-1]
        
        cluster_folder = os.path.join(image_folder, f'{folder_name}-cluster_{cluster}')
        cluster_folder = normalize_path(cluster_folder) # Normalize the new cluster folder path
        
        os.makedirs(cluster_folder, exist_ok=True)
        
        for idx in tqdm(sorted_indices, desc=f"Moving images for cluster {cluster}", leave=False):
            original_img_path = valid_image_paths[cluster_indices[idx]]
            new_img_name = os.path.basename(original_img_path)
            
            new_path = normalize_path(os.path.join(cluster_folder, new_img_name))
            
            try:
                shutil.move(original_img_path, new_path)
            except Exception as e:
                print(f"Could not move {original_img_path} to {new_path}: {e}")
                
    print("\nClustering and sorting complete. ✨")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sort images based on similarity.')
    parser.add_argument('folder', type=str, help='Path to the folder containing images')
    parser.add_argument('clusters', type=int, help='Number of clusters for KMeans')
    
    args = parser.parse_args()
    
    process_images(args.folder, args.clusters)