import os
import sys
import shutil
import numpy as np
from PIL import Image, ImageOps
from keras.models import load_model

# Disable scientific notation
np.set_printoptions(suppress=True)

# Check for folder argument
if len(sys.argv) < 2:
    print("Usage: python classify_and_sort_images.py <images_folder_path>")
    sys.exit(1)

input_folder = sys.argv[1]

# Load model and class labels
model = load_model("keras_Model.h5", compile=False)
class_names = [line.strip() for line in open("labels.txt", "r").readlines()]

# Prepare image shape
IMG_SIZE = (224, 224)
data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)

# Process each image
for filename in os.listdir(input_folder):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
        image_path = os.path.join(input_folder, filename)
        try:
            image = Image.open(image_path).convert("RGB")
            image = ImageOps.fit(image, IMG_SIZE, Image.Resampling.LANCZOS)
            image_array = np.asarray(image)
            normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1
            data[0] = normalized_image_array

            prediction = model.predict(data, verbose=0)
            index = np.argmax(prediction)
            class_name = class_names[index].strip()
            confidence_score = prediction[0][index]

            print(f"{filename} => {class_name} ({confidence_score:.2f})")

            # Create destination folder
            dest_folder = os.path.join(input_folder, class_name)
            os.makedirs(dest_folder, exist_ok=True)

            # Move image
            shutil.move(image_path, os.path.join(dest_folder, filename))

        except Exception as e:
            print(f"Failed to process {filename}: {e}")
