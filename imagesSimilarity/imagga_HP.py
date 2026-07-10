import os
import requests
import shutil

# Imagga API credentials
API_KEY = "acc_1a5f7cb6ae4b548"
API_SECRET = "421365c891f09acb28b1d6125824c356"  # Imagga requires key + secret

API_URL = "https://api.imagga.com/v2/tags"  # Tagging endpoint

def classify_image(image_path):
    """Classify an image using Imagga API."""
    with open(image_path, "rb") as img_file:
        response = requests.post(
            API_URL,
            files={"image": img_file},
            auth=(API_KEY, API_SECRET)
        )
        response.raise_for_status()
        data = response.json()

    # Imagga returns a list of tags with confidence
    tags = data.get("result", {}).get("tags", [])
    top_tags = [t["tag"]["en"] for t in tags[:5]]  # top 5 tags

    # Determine Yes / No / Maybe
    if "baseball" in top_tags or "home plate" in top_tags:
        return "Yes"
    elif any(tag in ["sport", "field", "ball"] for tag in top_tags):
        return "Maybe"
    else:
        return "No"

def process_folder(folder_path):
    """Process all images in the folder and move them based on classification."""
    # Create destination folders
    yes_folder = os.path.join(folder_path, "Yes")
    no_folder = os.path.join(folder_path, "No")
    maybe_folder = os.path.join(folder_path, "Maybe")
    for f in [yes_folder, no_folder, maybe_folder]:
        os.makedirs(f, exist_ok=True)

    # Process images
    for fname in os.listdir(folder_path):
        if fname.lower().endswith((".jpg", ".jpeg", ".png")):
            fullpath = os.path.join(folder_path, fname)
            try:
                result = classify_image(fullpath)
                print(f"{fname}: {result}")

                # Move image to the corresponding folder
                if result == "Yes":
                    shutil.move(fullpath, os.path.join(yes_folder, fname))
                elif result == "No":
                    shutil.move(fullpath, os.path.join(no_folder, fname))
                else:
                    shutil.move(fullpath, os.path.join(maybe_folder, fname))

            except Exception as e:
                print(f"Error processing {fname}: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python classify_images_imagga.py <folder_path>")
    else:
        folder = sys.argv[1]
        process_folder(folder)
