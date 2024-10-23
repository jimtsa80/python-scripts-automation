import os
import numpy as np
import argparse
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.resnet50 import preprocess_input
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import shutil

# Load pre-trained ResNet50 model
model = ResNet50(weights='imagenet', include_top=False, pooling='max')

# Function to convert image to feature vector
def image_to_feature_vector(img_path, model):
    img = image.load_img(img_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = preprocess_input(img_array)
    
    features = model.predict(img_array)
    return features.flatten()

# Main function to process images
def process_images(image_folder):
    # Load and process all images
    image_paths = [os.path.join(image_folder, f) for f in os.listdir(image_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]
    feature_vectors = [image_to_feature_vector(img, model) for img in image_paths]

    # Convert list to numpy array
    feature_vectors = np.array(feature_vectors)

    # Cluster images using KMeans
    kmeans = KMeans(n_clusters=5)  # Adjust the number of clusters as needed
    labels = kmeans.fit_predict(feature_vectors)

    # Sort images within each cluster by similarity using cosine similarity
    for cluster in range(5):
        cluster_indices = np.where(labels == cluster)[0]
        cluster_features = feature_vectors[cluster_indices]
        
        # Calculate similarity matrix within the cluster
        similarity_matrix = cosine_similarity(cluster_features)
        
        # Sort images based on similarity
        sorted_indices = np.argsort(similarity_matrix.sum(axis=1))[::-1]
        
        # Create folder for each cluster and move sorted images
        cluster_folder = os.path.join(image_folder, f'cluster_{cluster}')
        os.makedirs(cluster_folder, exist_ok=True)
        
        for i, idx in enumerate(sorted_indices):
            img_path = image_paths[cluster_indices[idx]]
            new_path = os.path.join(cluster_folder, f'{os.path.basename(img_path)}')
            shutil.move(img_path, new_path)

if __name__ == '__main__':
    # Set up argument parsing
    parser = argparse.ArgumentParser(description='Sort images based on similarity.')
    parser.add_argument('folder', type=str, help='Path to the folder containing images')
    
    # Parse the command-line arguments
    args = parser.parse_args()
    
    # Call the function with the provided folder
    process_images(args.folder)
