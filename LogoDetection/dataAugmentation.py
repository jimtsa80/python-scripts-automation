import cv2
import numpy as np
import os
import random
from PIL import Image, ImageEnhance, ImageFilter
import argparse

def augment_logo_image(input_image_path, output_folder, num_variations=100):
    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Load the original image
    image = cv2.imread(input_image_path)
    if image is None:
        print(f"Error: Could not load image {input_image_path}")
        return

    # Get image dimensions
    h, w, _ = image.shape

    for i in range(1, num_variations + 1):
        augmented_image = image.copy()

        # 1. Slight rotation (up to 10 degrees)
        angle = random.uniform(-10, 10)
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        augmented_image = cv2.warpAffine(augmented_image, matrix, (w, h), borderMode=cv2.BORDER_REFLECT)

        # 2. Perspective adjustment (subtle)
        if random.random() > 0.5:
            pts1 = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
            shift = random.randint(-10, 10)  # Mild shift
            pts2 = np.float32([[shift, shift], [w - shift, shift], [shift, h - shift], [w - shift, h + shift]])
            matrix = cv2.getPerspectiveTransform(pts1, pts2)
            augmented_image = cv2.warpPerspective(augmented_image, matrix, (w, h), borderMode=cv2.BORDER_REFLECT)

        # 3. Lighting and shadow adjustments (subtle)
        pil_img = Image.fromarray(cv2.cvtColor(augmented_image, cv2.COLOR_BGR2RGB))
        enhancer = ImageEnhance.Brightness(pil_img)
        pil_img = enhancer.enhance(random.uniform(0.9, 1.1))  # Mild brightness variation
        enhancer = ImageEnhance.Contrast(pil_img)
        pil_img = enhancer.enhance(random.uniform(0.95, 1.05))  # Mild contrast variation
        augmented_image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        # # 4. Random Background Change (if you have a collection of backgrounds)
        # if random.random() > 0.7:  # 30% chance to change background
        #     background_image_path = "backgrounds/random_background.jpg"  # Change path to background images

        #     # Ensure the background image exists and is readable
        #     background_image = cv2.imread(background_image_path)
        #     if background_image is None:
        #         print(f"Warning: Background image '{background_image_path}' not found. Skipping background change.")
        #     else:
        #         background_image = cv2.resize(background_image, (w, h))
        #         mask = np.zeros(augmented_image.shape[:2], dtype=np.uint8)
        #         mask[augmented_image[:, :, 0] > 0] = 255  # Simple mask based on image's content
        #         background = cv2.inpaint(background_image, mask, 3, cv2.INPAINT_TELEA)
        #         augmented_image = cv2.addWeighted(augmented_image, 0.7, background, 0.3, 0)

        # 5. Apply subtle shadow effect (simulating different lighting)
        shadow = np.random.uniform(0.5, 1.0)
        augmented_image = np.clip(augmented_image * shadow, 0, 255).astype(np.uint8)

        # 6. Save augmented image
        output_path = os.path.join(output_folder, f"augmented_image_{i:04d}.jpg")
        cv2.imwrite(output_path, augmented_image)

    print(f"Generated {num_variations} augmented images in '{output_folder}'.")

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Generate augmented images for training.")
    parser.add_argument("input_image_path", type=str, help="Path to the input image")
    parser.add_argument("output_folder", type=str, help="Folder to save augmented images")
    parser.add_argument("--num_variations", type=int, default=100, help="Number of augmented images to generate")

    args = parser.parse_args()

    # Run the augmentation function with the provided arguments
    augment_logo_image(args.input_image_path, args.output_folder, args.num_variations)
