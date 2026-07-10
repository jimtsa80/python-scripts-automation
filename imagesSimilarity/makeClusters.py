import os
import numpy as np
import argparse
from PIL import UnidentifiedImageError
import tensorflow as tf
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.resnet50 import preprocess_input
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm
import shutil
import re
import cv2
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure GPU (if available)
try:
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        try:
            # Enable memory growth to avoid allocating all GPU memory
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
            print(f"TensorFlow GPU enabled: {len(gpus)} device(s) detected")
        except Exception:
            pass
except Exception:
    pass

# Load pre-trained ResNet50 model
model = ResNet50(weights='imagenet', include_top=False, pooling='max')
# Compile model for faster inference (creates optimized computation graph)
model.compile()

# Function to convert image to feature vector
def image_to_feature_vector(img_path, model):
    try:
        img = image.load_img(img_path, target_size=(224, 224))
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)

        features = model.predict(img_array)
        return features.flatten()
    except UnidentifiedImageError:
        print(f"Skipping unreadable image: {img_path}")
        return None  # Return None for problematic images

def load_and_preprocess(img_path):
    try:
        img = image.load_img(img_path, target_size=(224, 224))
        arr = image.img_to_array(img)
        return arr
    except UnidentifiedImageError:
        return None
    except Exception:
        return None

def load_and_preprocess_batch(paths, num_workers=4):
    """Load and preprocess multiple images in parallel."""
    results = []
    with ThreadPoolExecutor(max_workers=min(len(paths), num_workers * 2)) as executor:
        future_to_path = {executor.submit(load_and_preprocess, p): p for p in paths}
        for future in as_completed(future_to_path):
            path = future_to_path[future]
            try:
                arr = future.result()
                if arr is not None:
                    results.append((arr, path))
            except Exception:
                pass
    return results

def extract_features_batched(paths, batch_size, num_workers=4, progress_bar=None):
    feature_vectors = []
    valid_paths = []
    # Process in larger chunks for parallel loading
    chunk_size = batch_size * 2  # Load more images in parallel than batch size
    for start in range(0, len(paths), chunk_size):
        chunk_paths = paths[start:start + chunk_size]
        # Load images in parallel
        loaded_results = load_and_preprocess_batch(chunk_paths, num_workers=num_workers)
        
        # Update progress bar for all images in chunk (including failed ones)
        if progress_bar:
            progress_bar.update(len(chunk_paths))
        
        if not loaded_results:
            continue
        
        # Process loaded images in batches for GPU inference
        loaded_arrays = [arr for arr, _ in loaded_results]
        loaded_paths = [path for _, path in loaded_results]
        
        for batch_start in range(0, len(loaded_arrays), batch_size):
            batch_arrays = loaded_arrays[batch_start:batch_start + batch_size]
            batch_paths_subset = loaded_paths[batch_start:batch_start + batch_size]
            
            if not batch_arrays:
                continue
                
            batch = np.stack(batch_arrays, axis=0)
            batch = preprocess_input(batch)
            # Use larger batch size for GPU if available
            feats = model.predict(batch, verbose=0, batch_size=len(batch_arrays))
            for j in range(len(batch_arrays)):
                feature_vectors.append(feats[j].flatten())
                valid_paths.append(batch_paths_subset[j])
    
    return feature_vectors, valid_paths

# Function to sanitize folder names
def sanitize_filename(name):
    """Remove invalid characters from folder names."""
    return re.sub(r'[<>:"/\\|?*]', '_', name)

# --- Ads pre-filter helpers ---
def parse_region(region_str):
    """Parse region string 'x,y,w,h' into tuple of ints, or None."""
    if not region_str:
        return None
    try:
        parts = [int(p.strip()) for p in region_str.split(',')]
        if len(parts) != 4:
            return None
        return tuple(parts)
    except Exception:
        return None

def load_ad_templates(folder):
    """Load grayscale templates from a folder (png/jpg/jpeg)."""
    if not folder or not os.path.isdir(folder):
        return []
    exts = ('.png', '.jpg', '.jpeg')
    paths = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(exts)]
    templates = []
    for p in paths:
        t = cv2.imread(p, 0)
        if t is not None:
            templates.append(t)
    return templates

def detect_ad_by_templates(image_path, templates, threshold=0.8, search_region=None):
    """Return True if any template matches above threshold in optional region."""
    if not templates:
        return False
    img = cv2.imread(image_path, 0)
    if img is None:
        return False
    region_img = img
    if search_region:
        x, y, w, h = search_region
        region_img = img[y:y+h, x:x+w]
    for tpl in templates:
        if region_img.shape[0] < tpl.shape[0] or region_img.shape[1] < tpl.shape[1]:
            continue
        res = cv2.matchTemplate(region_img, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        if max_val >= threshold:
            return True
    return False

# Main function to process images
def choose_best_k(X, k_min=2, k_max=12):
    """Choose the best k using silhouette score on preprocessed features X."""
    best_k, best_score = None, -1.0
    for k in range(max(2, k_min), max(2, k_max) + 1):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)
        # Ensure at least 2 clusters present
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(X, labels, metric='euclidean')
        if score > best_score:
            best_score, best_k = score, k
    return best_k, best_score


# Main function to process images
def process_images(image_folder, num_clusters, auto=False, k_min=2, k_max=12, use_pca=True, pca_dims=128,
                   ad_templates_folder=None, ads_folder=None, ad_threshold=0.8, ad_region=None, num_workers=4):
    folder_name = sanitize_filename(os.path.basename(os.path.normpath(image_folder)))
    # If path would exceed Windows MAX_PATH (260), rename folder to "temp" so cluster subfolders fit
    sample_cluster_path = os.path.join(image_folder, f'part1_{folder_name}-cluster_0')
    if len(sample_cluster_path) >= 260:
        parent = os.path.dirname(image_folder)
        temp_path = os.path.join(parent, 'temp')
        if os.path.abspath(image_folder) != os.path.abspath(temp_path):
            os.rename(image_folder, temp_path)
            image_folder = temp_path
    image_paths = [os.path.join(image_folder, f) for f in os.listdir(image_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]

    # Optional ads pre-filter
    templates = load_ad_templates(ad_templates_folder) if ad_templates_folder else []
    ad_region_tuple = parse_region(ad_region) if isinstance(ad_region, str) else ad_region
    if templates:
        ads_out = ads_folder or os.path.join(image_folder, f"{folder_name}-ads")
        os.makedirs(ads_out, exist_ok=True)
        kept_paths = []
        ads_to_move = []
        print("Filtering ads using templates...")
        
        # Parallel ad detection
        def check_ad(img_path):
            try:
                is_ad = detect_ad_by_templates(img_path, templates, threshold=ad_threshold, search_region=ad_region_tuple)
                return img_path, is_ad
            except Exception:
                return img_path, False
        
        with ThreadPoolExecutor(max_workers=num_workers * 2) as executor:
            futures = [executor.submit(check_ad, img) for img in image_paths]
            for future in tqdm(as_completed(futures), total=len(futures), desc="Ad filtering"):
                img_path, is_ad = future.result()
                if is_ad:
                    ads_to_move.append(img_path)
                else:
                    kept_paths.append(img_path)
        
        # Move ads in parallel
        def move_ad(img_path):
            try:
                new_path = os.path.join(ads_out, os.path.basename(img_path))
                shutil.move(img_path, new_path)
            except Exception:
                pass
        
        if ads_to_move:
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                list(tqdm(executor.map(move_ad, ads_to_move), total=len(ads_to_move), desc="Moving ads"))
        
        image_paths = kept_paths

    print("Extracting features from images...")
    total_images = len(image_paths)
    feature_vectors = []
    valid_image_paths = []
    bar = tqdm(total=total_images, desc="Processing images")
    batch_size = getattr(process_images, "_batch_size", 32)
    feats, vpaths = extract_features_batched(image_paths, batch_size, num_workers=num_workers, progress_bar=bar)
    feature_vectors.extend(feats)
    valid_image_paths.extend(vpaths)
    bar.close()

    # Convert list to numpy array
    feature_vectors = np.array(feature_vectors)

    if feature_vectors.size == 0:
        print("No valid images found to process.")
        return

    # Normalize features to align Euclidean with cosine
    X_norm = normalize(feature_vectors, norm='l2')

    # Optional PCA for stability/speed (n_components must be <= min(n_samples, n_features))
    if use_pca:
        max_components = min(X_norm.shape[0], X_norm.shape[1])
        n_components = int(min(pca_dims, max_components))
        if n_components >= 2:
            pca = PCA(n_components=n_components, random_state=42)
            X_clust = pca.fit_transform(X_norm)
        else:
            X_clust = X_norm
    else:
        X_clust = X_norm

    # Determine number of clusters
    inferred_k = None
    if auto or (isinstance(num_clusters, str) and num_clusters.lower() == 'auto'):
        print(f"Selecting number of clusters automatically (k in [{k_min}, {k_max}]) using silhouette score...")
        # Verbose per-k reporting
        best_k, best_score = None, -1.0
        for k in range(max(2, k_min), max(2, k_max) + 1):
            kmeans_tmp = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels_tmp = kmeans_tmp.fit_predict(X_clust)
            if len(set(labels_tmp)) < 2:
                tqdm.write(f"k={k}: skipped (degenerate clusters)")
                continue
            score_tmp = silhouette_score(X_clust, labels_tmp, metric='euclidean')
            tqdm.write(f"k={k}: silhouette={score_tmp:.4f}")
            if score_tmp > best_score:
                best_score, best_k = score_tmp, k
        inferred_k = best_k
        if inferred_k is None:
            print("Failed to determine k automatically; defaulting to k=2.")
            inferred_k = 2
        else:
            print(f"Selected k={inferred_k} with silhouette={best_score:.4f}")
        n_clusters = inferred_k
    else:
        # Allow str or int input
        n_clusters = int(num_clusters)

    # Cluster images using KMeans
    print("Clustering images...")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_clust)

    # Sort images within each cluster by similarity using cosine similarity
    def process_cluster(cluster):
        cluster_indices = np.where(labels == cluster)[0]
        # Use normalized original features for cosine similarity ordering
        cluster_features = X_norm[cluster_indices]
        
        # Calculate similarity matrix within the cluster
        similarity_matrix = cosine_similarity(cluster_features)
        
        # Sort images based on similarity
        sorted_indices = np.argsort(similarity_matrix.sum(axis=1))[::-1]
        
        # Create folder for each cluster with part prefix (path already shortened by renaming to temp if needed)
        part_num = cluster + 1  # 1-indexed part number
        cluster_folder = os.path.join(image_folder, f'part{part_num}_{folder_name}-cluster_{cluster}')
        os.makedirs(cluster_folder, exist_ok=True)
        
        # Prepare move operations
        move_ops = []
        for idx in sorted_indices:
            img_path = valid_image_paths[cluster_indices[idx]]
            new_path = os.path.join(cluster_folder, f'{os.path.basename(img_path)}')
            move_ops.append((img_path, new_path))
        
        return move_ops
    
    # Process clusters and collect move operations
    all_move_ops = []
    for cluster in tqdm(range(n_clusters), desc="Organizing clusters"):
        move_ops = process_cluster(cluster)
        all_move_ops.extend(move_ops)
    
    # Move files in parallel
    def move_file(op):
        img_path, new_path = op
        try:
            shutil.move(img_path, new_path)
        except Exception:
            pass
    
    if all_move_ops:
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            list(tqdm(executor.map(move_file, all_move_ops), total=len(all_move_ops), desc="Moving images"))

if __name__ == '__main__':
    # Set up argument parsing
    parser = argparse.ArgumentParser(description='Sort images based on similarity.')
    parser.add_argument('folder', type=str, help='Path to the folder containing images')
    parser.add_argument('clusters', type=str, help='Number of clusters for KMeans (e.g., 5) or "auto"')
    parser.add_argument('--k-min', type=int, default=2, help='Minimum k when using auto mode')
    parser.add_argument('--k-max', type=int, default=12, help='Maximum k when using auto mode')
    parser.add_argument('--pca-dims', type=int, default=128, help='PCA components for clustering (auto disabled if <2)')
    parser.add_argument('--no-pca', action='store_true', help='Disable PCA before clustering')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size for feature extraction (GPU-friendly)')
    parser.add_argument('--num-workers', type=int, default=4, help='Number of parallel workers for I/O operations')
    # Ads pre-filter options
    parser.add_argument('--ad-templates', type=str, default=None, help='Folder with ad/logo templates (png/jpg)')
    parser.add_argument('--ads-folder', type=str, default=None, help='Destination folder for detected ads')
    parser.add_argument('--ad-threshold', type=float, default=0.8, help='Template match threshold (0-1)')
    parser.add_argument('--ad-region', type=str, default=None, help='Region x,y,w,h to search for ads')
    
    # Parse the command-line arguments
    args = parser.parse_args()

    use_pca = not args.no_pca
    auto_flag = isinstance(args.clusters, str) and args.clusters.lower() == 'auto'

    # Propagate batch size to processing function via attribute to avoid changing signature elsewhere
    process_images._batch_size = max(1, args.batch_size)

    # Call the function with the provided folder and number of clusters
    process_images(
        args.folder,
        args.clusters,
        auto=auto_flag,
        k_min=args.k_min,
        k_max=args.k_max,
        use_pca=use_pca,
        pca_dims=args.pca_dims,
        ad_templates_folder=args.ad_templates,
        ads_folder=args.ads_folder,
        ad_threshold=args.ad_threshold,
        ad_region=args.ad_region,
        num_workers=args.num_workers,
    )