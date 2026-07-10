import os
import numpy as np
import argparse
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.resnet50 import preprocess_input
from sklearn.cluster import KMeans

# Load pre-trained ResNet50 model
model = ResNet50(weights='imagenet', include_top=False, pooling='max')

# Function to convert an image to a feature vector
def image_to_feature_vector(img_path, model):
    img = image.load_img(img_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = preprocess_input(img_array)
    
    features = model.predict(img_array)
    return features.flatten()

# Calculate the mean feature vector for each clustered folder
def calculate_folder_feature(folder):
    image_paths = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    feature_vectors = [image_to_feature_vector(img, model) for img in image_paths]
    return np.mean(feature_vectors, axis=0)

# Label folders based on their mean feature vectors
def label_folders(parent_folder, num_clusters):
    folder_paths = []
    folder_features = []

    # Process each subfolder within the main folder
    for subfolder in os.listdir(parent_folder):
        subfolder_path = os.path.join(parent_folder, subfolder)
        if os.path.isdir(subfolder_path):
            # Calculate the mean feature vector for the folder
            folder_feature = calculate_folder_feature(subfolder_path)
            folder_paths.append(subfolder_path)
            folder_features.append(folder_feature)
    
    # Perform KMeans clustering on folder features
    folder_features = np.array(folder_features)
    kmeans = KMeans(n_clusters=num_clusters, random_state=42)
    cluster_labels = kmeans.fit_predict(folder_features)

    # Rename folders based on cluster labels
    for folder_path, cluster_label in zip(folder_paths, cluster_labels):
        new_folder_name = f"folder_cluster_{cluster_label}"
        new_folder_path = os.path.join(parent_folder, new_folder_name)
        os.rename(folder_path, new_folder_path)
        print(f"Renamed '{os.path.basename(folder_path)}' to '{new_folder_name}'")

if __name__ == '__main__':
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Label folders based on image similarity.")
    parser.add_argument('parent_folder', type=str, help='Path to the folder containing clustered subfolders')
    parser.add_argument('clusters', type=int, default=5, help='Number of clusters for labeling (default: 5)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Run the labeling process
    label_folders(args.parent_folder, args.clusters)