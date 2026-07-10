import os
import sys
import shutil
from PIL import Image, UnidentifiedImageError
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration
import pytesseract
import re
import csv
import multiprocessing
from concurrent.futures import ProcessPoolExecutor

pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"  # Use your installation path

def sanitize_text(text):
    text = text.replace("\n", " ").replace("\r", "").replace("\t", " ")
    text = re.sub(r'\s+', ' ', text).strip()
    return text.lower()

def load_keywords(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return set(line.strip().lower() for line in f if line.strip())
    except Exception as e:
        print(f"Error loading keywords file {file_path}: {e}")
        sys.exit(1)

def initialize_blip_model():
    try:
        checkpoint = "Salesforce/blip-image-captioning-base"
        processor = BlipProcessor.from_pretrained(checkpoint)
        model = BlipForConditionalGeneration.from_pretrained(checkpoint)
        return processor, model
    except Exception as e:
        print(f"Error initializing BLIP model: {e}")
        sys.exit(1)

def generate_caption(processor, model, image_path):
    try:
        image = Image.open(image_path).convert("RGB")
        inputs = processor(image, return_tensors="pt")
        with torch.no_grad():
            output = model.generate(**inputs)
        return processor.decode(output[0], skip_special_tokens=True)
    except UnidentifiedImageError:
        print(f"Invalid image format: {image_path}")
        return None
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None

def extract_ocr_text(image_path):
    try:
        image = Image.open(image_path).convert("RGB")
        return pytesseract.image_to_string(image)
    except Exception as e:
        print(f"Error extracting OCR from {image_path}: {e}")
        return ""

def save_to_csv(image_name, caption, ocr_text, csv_file):
    try:
        with open(csv_file, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([image_name, caption, ocr_text])
    except Exception as e:
        print(f"Error writing to CSV: {e}")

def classify_and_move_image(image_path, processor, model, keywords, ads_folder):
    try:
        filename = os.path.basename(image_path)
        caption = generate_caption(processor, model, image_path)
        ocr_text = extract_ocr_text(image_path)
        ocr_text_sanitized = sanitize_text(ocr_text)

        if caption:
            print(f"Processing {filename}...")
            print(f"Caption: {caption}")
            print(f"OCR Text: {ocr_text_sanitized}")

            if is_useful_image(caption, ocr_text, keywords):
                print(f"{filename} classified as useful frame.")
                return filename, caption, ocr_text_sanitized, True
            else:
                print(f"Moving {filename} to ads folder (not classified as useful).")
                return filename, caption, ocr_text_sanitized, False
        else:
            print(f"Could not generate a caption for {filename}.")
            return filename, None, ocr_text_sanitized, False
    except Exception as e:
        print(f"Error processing file {image_path}: {e}")
        return filename, None, None, False

def is_useful_image(caption, ocr_text, keywords):
    try:
        caption = caption.lower()
        ocr_text = sanitize_text(ocr_text)
        matched_keywords = [kw for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', caption + " " + ocr_text)]
        if matched_keywords:
            print("Useful image found:")
            print(f"  Keywords: {', '.join(matched_keywords)}")
            return True
        return False
    except Exception as e:
        print(f"Error checking useful criteria: {e}")
        return False

def main(input_folder, csv_file, keywords_file):
    ads_folder = os.path.join(input_folder, "ads")
    os.makedirs(ads_folder, exist_ok=True)

    processor, model = initialize_blip_model()
    print("Model initialized successfully.")

    keywords = load_keywords(keywords_file)

    with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Image", "Caption", "OCR Text"])

    all_images = [os.path.join(input_folder, f) for f in os.listdir(input_folder) if os.path.isfile(os.path.join(input_folder, f))]

    with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        results = list(executor.map(classify_and_move_image, all_images, [processor]*len(all_images), [model]*len(all_images), [keywords]*len(all_images), [ads_folder]*len(all_images)))

    for filename, caption, ocr_text, useful in results:
        save_to_csv(filename, caption, ocr_text, csv_file)
        if not useful:
            shutil.move(os.path.join(input_folder, filename), os.path.join(ads_folder, filename))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script_name.py <path_to_images_folder> <keywords_file>")
        sys.exit(1)

    input_folder = sys.argv[1]
    keywords_file = sys.argv[2]

    if not os.path.exists(input_folder) or not os.path.isdir(input_folder):
        print(f"Error: The folder '{input_folder}' does not exist or is not a directory.")
        sys.exit(1)

    if not os.path.exists(keywords_file):
        print(f"Error: The file '{keywords_file}' does not exist.")
        sys.exit(1)

    csv_file = os.path.splitext(keywords_file)[0] + "_image_data.csv"
    main(input_folder, csv_file, keywords_file)