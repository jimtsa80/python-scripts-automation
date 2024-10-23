import os
import argparse
import tensorflow as tf
import shutil
from tensorflow.keras.preprocessing.image import img_to_array, load_img
import numpy as np

def classify_image(model, image_path, img_height, img_width):
    image = load_img(image_path, target_size=(img_height, img_width))
    image = img_to_array(image)
    image = np.expand_dims(image, axis=0) / 255.0  # Rescale
    prediction = model.predict(image)
    return prediction[0][0] > 0.5  # Returns True if classified as "match"

def move_ads_images(model_path, input_folder, img_height=224, img_width=224):
    # Load the trained model
    model = tf.keras.models.load_model(model_path)

    # Create the 'ads' folder
    ads_folder = os.path.join(input_folder, 'ads')
    os.makedirs(ads_folder, exist_ok=True)

    # Initialize counters for the images
    total_images = 0
    ads_images = 0

    # Iterate over images in the input folder
    for filename in os.listdir(input_folder):
        file_path = os.path.join(input_folder, filename)

        if filename.lower().endswith(('.jpg', '.png', '.jpeg')):
            total_images += 1  # Count total images
            # Classify the image
            if not classify_image(model, file_path, img_height, img_width):
                # Move the image to the 'ads' folder if classified as an advertisement
                shutil.move(file_path, os.path.join(ads_folder, filename))
                ads_images += 1  # Count images classified as ads
                print(f"Moved: {filename} to 'ads' folder")

    # Print statistics
    remaining_images = total_images - ads_images
    reduction_percentage = (ads_images / total_images) * 100
    print(f"Total images: {total_images}")
    print(f"Ads images: {ads_images}")
    print(f"Remaining images: {remaining_images}")
    print(f"Reduction percentage: {reduction_percentage:.2f}%")

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Classify images as ads or matches and move ads to a separate folder.")
    parser.add_argument('model_path', type=str, help='Path to the trained model (advertisement_classifier.h5).')
    parser.add_argument('image_folder', type=str, help='Path to the folder containing images to classify.')

    # Parse the arguments
    args = parser.parse_args()

    # Move the ads images using the provided model and image folder
    move_ads_images(model_path=args.model_path, input_folder=args.image_folder)
