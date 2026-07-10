import os
import sys
import shutil
import numpy as np
import csv
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
import pytesseract
import easyocr
from datetime import timedelta
import time

# Set the correct path for Tesseract
pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

# Initialize EasyOCR reader once (for efficiency)
easyocr_reader = easyocr.Reader(['en'], gpu=False)

# Preprocessing function to improve OCR results
def preprocess_image(image):
    print("Preprocessing image for OCR...")
    gray_image = image.convert('L')
    enhancer = ImageEnhance.Contrast(gray_image)
    enhanced_image = enhancer.enhance(2)
    print("Image preprocessing completed.")
    return enhanced_image

# OCR function with fallback to EasyOCR
def ocr_with_fallback(image):
    """
    Perform OCR using Tesseract first. If it fails, fallback to EasyOCR.
    Ensures coordinates are always retrieved.
    """
    print("Attempting OCR with Tesseract...")
    try:
        # Attempt OCR with Tesseract
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        if not any(data['text']):
            raise ValueError("Tesseract detected no text.")
        print("Tesseract OCR successful.")
        return data
    except Exception as e:
        print(f"Tesseract OCR failed: {e}")
        print("Falling back to EasyOCR...")
        
        # Convert PIL image to NumPy array
        image_np = np.array(image)
        
        # Fallback to EasyOCR
        easyocr_results = easyocr_reader.readtext(image_np, detail=1)
        
        # Convert EasyOCR results to a similar format as Tesseract's output
        data = {
            'text': [],
            'left': [],
            'top': [],
            'width': [],
            'height': []
        }
        
        for result in easyocr_results:
            bbox, text, _ = result  # Bounding box, text, and confidence
            (x_min, y_min), (x_max, y_max) = bbox[0], bbox[2]
            data['text'].append(text)
            data['left'].append(int(x_min))
            data['top'].append(int(y_min))
            data['width'].append(int(x_max - x_min))
            data['height'].append(int(y_max - y_min))
        
        print("EasyOCR fallback successful.")
        return data


# Function to calculate screen location based on bounding box center
def get_screen_location(startPoint, diagPoint, width, height):
    x1, y1 = startPoint
    x2, y2 = diagPoint
    center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2

    if width / 3 < center_x < 2 * width / 3 and height / 3 < center_y < 2 * height / 3:
        return 'A'  # Center
    elif center_x < width / 3 and center_y < height / 3:
        return 'B'  # Upper-left corner
    elif center_x > 2 * width / 3 and center_y < height / 3:
        return 'C'  # Upper-right corner
    elif center_x < width / 3 and center_y > 2 * height / 3:
        return 'D'  # Bottom-left corner
    elif center_x > 2 * width / 3 and center_y > 2 * height / 3:
        return 'E'  # Bottom-right corner
    elif center_x < width / 3 and height / 3 < center_y < 2 * height / 3:
        return 'B'
    elif center_x > 2 * width / 3 and height / 3 < center_y < 2 * height / 3:
        return 'C'
    elif width / 3 < center_x < 2 * width / 3 and center_y < height / 3:
        return 'B'
    elif width / 3 < center_x < 2 * width / 3 and center_y > 2 * height / 3:
        return 'D'

    return 'A'

# Function to calculate screen size percentage from bounding box
def calculate_screen_size_percentage(startPoint, diagPoint, width, height):
    x1, y1 = startPoint
    x2, y2 = diagPoint
    bbox_area = (x2 - x1) * (y2 - y1)
    total_area = width * height
    screen_size_percentage = (bbox_area / total_area) * 100
    return round(screen_size_percentage, 3)

# Function to load class mappings from a text file
def load_class_mapping(mapping_file):
    class_mapping = {}
    with open(mapping_file, 'r') as file:
        for line in file:
            parts = line.strip().split()
            class_id = int(parts[0])
            brand_touchpoint = ' '.join(parts[1:])
            class_mapping[class_id] = brand_touchpoint
    return class_mapping

# Function to process a single image and save YOLO annotations
def process_image(image_path, image_index, width, height, brands, main_folder, class_mapping_file):
    print(f"Processing image {image_index + 1}: {os.path.basename(image_path)}")
    image = Image.open(image_path)
    image = preprocess_image(image)

    # Attempt OCR with fallback
    data = ocr_with_fallback(image)
    time.sleep(0.5)
    annotations = {brand: [] for brand in brands}

    # Load class mapping from the provided file
    class_mapping = load_class_mapping(class_mapping_file)

    # YOLO annotations file path
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    yolo_annotations_path = os.path.join(main_folder, f"{base_name}.txt")

    yolo_lines = []

    # Print all detected text from the image
    print("\nDetected text in the image:")
    for i, text in enumerate(data['text']):
        if text.strip():  # Skip empty or whitespace-only text
            print(f"Text: {text}, Coordinates: (x={data['left'][i]}, y={data['top'][i]}, width={data['width'][i]}, height={data['height'][i]})")

    for i, text in enumerate(data['text']):
        for target_brand in brands:
            if target_brand.lower() in text.lower():
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                startPoint = [x, y]
                diagPoint = [(x + w), (y + h)]
                location = get_screen_location(startPoint, diagPoint, width, height)
                screen_size_percentage = calculate_screen_size_percentage(startPoint, diagPoint, width, height)

                annotations[target_brand].append({
                    "startPoint": startPoint,
                    "diagPoint": diagPoint,
                    "group": "WorldRX",
                    "brand": target_brand,
                    "tpoint": "TVGI Text",
                    "hits": 1,
                    "location": location,
                    "screen_size_percentage": screen_size_percentage
                })

                # Calculate YOLO normalized coordinates
                x_center = (x + w / 2) / width
                y_center = (y + h / 2) / height
                bbox_width = w / width
                bbox_height = h / height

                # Determine class ID based on brand's index in the class_mapping dictionary
                class_id = None
                for key, value in class_mapping.items():
                    if value.split("-")[0].lower() == target_brand.lower():
                        class_id = key
                        break

                # If class ID is not found, skip this annotation
                if class_id is None:
                    print(f"Warning: Class ID not found for brand: {target_brand}. Skipping annotation.")
                    continue

                # Create YOLO format line
                yolo_line = f"{class_id} {x_center:.6f} {y_center:.6f} {bbox_width:.6f} {bbox_height:.6f}"
                yolo_lines.append(yolo_line)

    # Save YOLO annotations to a text file
    if yolo_lines:
        with open(yolo_annotations_path, 'w') as yolo_file:
            yolo_file.write('\n'.join(yolo_lines))
        print(f"Saved YOLO annotations for {os.path.basename(image_path)}.")

    for target_brand in brands:
        if annotations[target_brand]:
            print(f"Found brand {target_brand} in image. Copying to folder...")
            brand_folder = os.path.join(main_folder, target_brand)
            if not os.path.exists(brand_folder):
                os.makedirs(brand_folder)

            # Save the original image and annotated image in the brand folder
            annotated_image_path = os.path.join(brand_folder, os.path.basename(image_path))
            shutil.copy(image_path, annotated_image_path)

            # Draw annotations on the copied image
            draw_annotations(annotated_image_path, annotations, annotated_image_path)

    return annotations

# Function to draw annotations on the image
def draw_annotations(image_path, annotations, output_path):
    print(f"Drawing annotations on: {output_path}")
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()  # Default font; use custom font if needed

    for brand, brand_annotations in annotations.items():
        for annotation in brand_annotations:
            try:
                x1, y1 = annotation["startPoint"]
                x2, y2 = annotation["diagPoint"]
                location = annotation["location"]

                # Validate coordinates
                if x1 >= x2 or y1 >= y2:
                    print(f"Skipping invalid bounding box for {brand}: {x1}, {y1}, {x2}, {y2}")
                    continue

                # Draw rectangle around detected brand
                draw.rectangle([x1, y1, x2, y2], outline="red", width=2)

                # Annotate brand name and location
                text = f"{brand} ({location})"

                # Calculate text dimensions using font.getbbox
                text_bbox = draw.textbbox((x1, y1), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]

                # Create a background rectangle for the text
                text_background = [x1, y1 - text_height - 4, x1 + text_width + 4, y1]
                draw.rectangle(text_background, fill="black")

                # Draw the text
                draw.text((x1 + 2, y1 - text_height - 2), text, fill="white", font=font)

            except Exception as e:
                print(f"Error while annotating brand {brand}: {e}")
                continue

    # Save the annotated image
    try:
        image.save(output_path)
        print(f"Annotations saved successfully: {output_path}")
    except Exception as e:
        print(f"Failed to save annotated image: {output_path}. Error: {e}")

# Function to calculate "Time the brand is at screen"
def calculate_time(frame_number):
    base_time = timedelta(seconds=frame_number)
    return str(base_time)

# Function to read brands from a text file
def read_brands_from_file(file_path):
    print(f"Reading brand list from file: {file_path}")
    with open(file_path, 'r') as f:
        brands = [line.strip() for line in f.readlines() if line.strip()]
    print(f"Loaded {len(brands)} brands.")
    return brands

# Function to process a folder and create CSV for multiple brands
def process_folder_and_create_csv(folder_path, width, height, brands):
    print(f"Processing folder: {folder_path}")
    folder_name = os.path.basename(folder_path.rstrip('/\\'))
    main_folder = os.path.join(folder_path, 'Processed_Images')
    if not os.path.exists(main_folder):
        os.makedirs(main_folder)

    image_index = 0
    last_annotation = None
    aggregated_annotations = []

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            image_path = os.path.join(folder_path, filename)
            annotations = process_image(image_path, image_index, width, height, brands, main_folder, class_mapping_file)

            for target_brand in brands:
                if annotations[target_brand]:
                    for anno in annotations[target_brand]:
                        brand = anno["brand"]
                        tpoint = anno["tpoint"]
                        time_at_screen = calculate_time(image_index)
                        duration = 1
                        screen_size_percentage = anno["screen_size_percentage"]
                        total_hits = anno["hits"]
                        location = anno["location"]
                        avg_hits = total_hits / duration if duration > 0 else 0

                        if last_annotation and last_annotation['brand'] == brand and last_annotation['location'] == location:
                            aggregated_annotations[-1]['duration'] += duration
                            aggregated_annotations[-1]['total_hits'] += total_hits
                            aggregated_annotations[-1]['avg_hits'] = aggregated_annotations[-1]['total_hits'] / aggregated_annotations[-1]['duration']
                        else:
                            aggregated_annotations.append({
                                'brand': brand,
                                'tpoint': tpoint,
                                'time_at_screen': time_at_screen,
                                'duration': duration,
                                'location': location,
                                'screen_size_percentage': screen_size_percentage,
                                'total_hits': total_hits,
                                'avg_hits': avg_hits,
                                'image_index': image_index
                            })

                        last_annotation = aggregated_annotations[-1]

            image_index += 1

    csv_filename = f"{folder_name}-brands.csv"
    print(f"Saving results to CSV: {csv_filename}")
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Brand", "Location", "Time the brand is at screen", "Duration", "Screen Location", "Screen Size %", "Total Hits", "Average Hits", "Sequence Frame Number"])
        for annotation in aggregated_annotations:
            writer.writerow([
                annotation['brand'],
                annotation['location'],
                annotation['time_at_screen'],
                annotation['duration'],
                annotation['location'],
                annotation['screen_size_percentage'],
                annotation['total_hits'],
                annotation['avg_hits'],
                annotation['image_index']
            ])

    print("All brand processing completed.")

# Function to process a main folder containing subfolders of images
def process_main_folder_and_create_csv(main_folder_path, width, height, brands):
    print(f"Processing main folder: {main_folder_path}")
    for subfolder_name in os.listdir(main_folder_path):
        subfolder_path = os.path.join(main_folder_path, subfolder_name)
        if os.path.isdir(subfolder_path):
            print(f"Processing subfolder: {subfolder_name}")
            process_folder_and_create_csv(subfolder_path, width, height, brands)

# Main script entry point
if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python script.py <folder_path> <image_width> <image_height> <brands_file>")
        sys.exit(1)

    folder_path = sys.argv[1]
    image_width = int(sys.argv[2])
    image_height = int(sys.argv[3])
    brands_file = sys.argv[4]

    brands = read_brands_from_file(brands_file)
    class_mapping_file = "ocr_brands_mapping.txt"
    process_main_folder_and_create_csv(folder_path, image_width, image_height, brands)