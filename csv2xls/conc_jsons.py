import os
import json
import sys

def concatenate_images_from_jsons(folder_path):
    # Dictionary to store concatenated images
    concatenated_images = {}

    # Get all JSON files in the folder
    json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]

    if not json_files:
        print("No JSON files found in the folder.")
        return

    # Use the first file's name (without extension) as the output file name
    first_file_name = os.path.splitext(json_files[0])[0]
    output_file = os.path.join(folder_path, f"{first_file_name}_concatenated.json")

    # Process each JSON file
    for json_file in json_files:
        file_path = os.path.join(folder_path, json_file)
        with open(file_path, 'r',encoding='utf-8') as f:
            data = json.load(f)
            if "images" in data and isinstance(data["images"], dict):
                concatenated_images.update(data["images"])

    # Create the output JSON structure
    output_data = {
        "project": "",
        "imageNum": 0,
        "prefs": {
            "projectName": "",
            "AnnotatorName": "",
            "prefsFilename": "",
            "imgFoldername": "",
            "userAdds": {},
            "groups": [""],
            "brands": [""],
            "tpoints": [""],
            "conns": {
                "ERC__ERC": {
                    "brand": "",
                    "tpoints": [""],
                    "group": ""
                }
            },
            "seelater": []
        },
        "images": concatenated_images,  # Add concatenated images here
        "currentImage": "000000",
        "presets": {
            "0": [], "1": [], "2": [], "3": [], "4": [], "5": [], "6": [], "7": [], "8": [], "9": [],
            "f1": [], "f2": [], "f3": [], "f4": [], "f5": [], "f6": [], "f7": [], "f8": [], "f9": [], "f10": [], "f11": [], "f12": [],
            "alt+f1": [], "alt+f2": [], "alt+f3": [], "alt+f4": [], "alt+f5": [], "alt+f6": [], "alt+f7": [], "alt+f8": [], "alt+f9": [], "alt+f10": [], "alt+f11": [], "alt+f12": [],
            "alt+1": [], "alt+2": [], "alt+3": [], "alt+4": [], "alt+5": [], "alt+6": [], "alt+7": [], "alt+8": [], "alt+9": [], "alt+0": [],
            "q": [], "w": [], "e": [], "r": [], "t": [], "y": [], "u": [], "i": [], "o": [], "p": [],
            "alt+q": [], "alt+w": [], "alt+e": [], "alt+r": [], "alt+t": [], "alt+y": [], "alt+u": [], "alt+i": [], "alt+o": [], "alt+p": [],
            "g": [], "h": [], "j": [], "k": [], "l": [], "b": [], "n": [], "m": [],
            "alt+g": [], "alt+h": [], "alt+j": [], "alt+k": [], "alt+l": [], "alt+b": [], "alt+n": [], "alt+m": [],
            "end": []
        },
        "Annotator": ""
    }

    # Save the output JSON files
    with open(output_file, 'w',encoding='utf-8') as f:
        json.dump(output_data, f, indent=4)

    print(f"Concatenated JSON saved to: {output_file}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <folder_path>")
        return

    folder_path = sys.argv[1]
    if not os.path.isdir(folder_path):
        print(f"The provided path '{folder_path}' is not a valid directory.")
        return

    concatenate_images_from_jsons(folder_path)

if __name__ == "__main__":
    main()