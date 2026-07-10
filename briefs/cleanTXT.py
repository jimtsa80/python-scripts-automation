import re
import sys
import os

def clean_text(input_file):
    try:
        # Try reading with utf-8 encoding first
        with open(input_file, 'r', encoding='utf-8') as file:
            text = file.read()
    except UnicodeDecodeError:
        # If it fails, fallback to 'latin-1' which can decode anything (but may not be perfect)
        with open(input_file, 'r', encoding='latin-1') as file:
            text = file.read()
        print(f"Warning: UTF-8 decode failed. Loaded with 'latin-1' encoding instead.")

    # Remove 'nan' as a word (case insensitive)
    text = re.sub(r'\bnan\b', '', text, flags=re.IGNORECASE)
    
    # Remove entire lines that start with a number, underscore, or single quote
    text = re.sub(r'^[\d_\'].*', '', text, flags=re.MULTILINE)

    # Remove empty lines after cleaning
    text = '\n'.join([line for line in text.splitlines() if line.strip()])

    # Prepare output filename
    dirname, filename = os.path.split(input_file)
    cleaned_filename = os.path.join(dirname, 'cleaned_' + filename)

    # Write output in UTF-8 encoding
    with open(cleaned_filename, 'w', encoding='utf-8') as file:
        file.write(text)
    
    print(f"Cleaned text saved to '{cleaned_filename}'")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <input_file.txt>")
    else:
        input_file = sys.argv[1]
        clean_text(input_file)
