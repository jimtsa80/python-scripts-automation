import os
import json
import csv
import argparse
import glob
from collections import defaultdict, Counter
from datetime import timedelta

def get_screen_location(startPoint, diagPoint, width, height):
    """Determine screen location of the annotation."""
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
    elif width / 3 < center_x < 2 * height / 3 and center_y > 2 * height / 3:
        return 'D'

    return 'A'

def time_from_seconds(seconds):
    """Convert seconds to HH:MM:SS format."""
    return str(timedelta(seconds=seconds))

def main():
    parser = argparse.ArgumentParser(description="Process JSON files and export each to CSV with consistency checks.")
    parser.add_argument("input_folder", help="Path to the folder containing JSON files")
    args = parser.parse_args()

    input_folder = args.input_folder
    if not os.path.isdir(input_folder):
        print(f"Error: {input_folder} is not a valid directory.")
        return

    # Collect all JSON files in the folder
    json_files = glob.glob(os.path.join(input_folder, "*.json"))
    if not json_files:
        print("No JSON files found in the specified folder.")
        return

    # Store all annotations across frames to check for duplicates
    annotation_counter = Counter()
    processed_entries = []

    # Process each JSON file
    for json_file_path in json_files:
        try:    
            with open(json_file_path, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                print(f"JSON loaded successfully: {json_file_path}")
        except UnicodeDecodeError as e:
            print(f"Encoding error: {e}")
            continue
        except json.JSONDecodeError as e:
            print(f"JSON format error: {e}")
            continue
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            continue

        # Process images and annotations
        for image_data in data['images'].values():
            image_name = image_data['imageName']
            width, height = image_data['width'], image_data['height']

            for annotation in image_data['annotations']:
                start_x, start_y = annotation['startPoint']
                end_x, end_y = annotation['diagPoint']
                group, brand, tpoint = annotation['group'], annotation['brand'], annotation['tpoint']
                hits = annotation['hits']

                location = get_screen_location(annotation['startPoint'], annotation['diagPoint'], width, height)
                size_percentage = abs((end_x - start_x) * (end_y - start_y)) / (width * height) * 100

                # Create a unique key for duplicate tracking
                annotation_key = (brand, tpoint, start_x, start_y, end_x, end_y)
                annotation_counter[annotation_key] += 1

                processed_entries.append({
                    'group': group,
                    'brand': brand,
                    'tpoint': tpoint,
                    'time': "00:00:00",
                    'duration': 1,
                    'location': location,
                    'size': size_percentage,
                    'hits': hits,
                    'avgHits': hits,
                    'frameNum': image_name
                })

        # Derive output CSV filename
        json_filename = os.path.basename(json_file_path)
        csv_filename = os.path.splitext(json_filename)[0] + ".csv"
        output_csv_path = os.path.join(input_folder, csv_filename)

        # Write to CSV
        with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter='\t')

            # Write header
            csvwriter.writerow([
                'Brand', 'Location', 'Time the brand is at screen',
                'Duration', 'Screen Location', 'Screen Size %',
                'Total Hits', 'Average Hits', 'Sequence Frame Number'
            ])

            # Write rows
            for entry in processed_entries:
                csvwriter.writerow([
                    entry['brand'],
                    entry['tpoint'],
                    entry['time'],
                    entry['duration'],
                    entry['location'],
                    f"{entry['size']:.3f}",
                    entry['hits'],
                    int(entry['avgHits']),
                    entry['frameNum']
                ])

        print(f"CSV file '{output_csv_path}' has been created.")

    # Print warnings if there are repeated annotations
    total_annotations = sum(annotation_counter.values())  # Total annotations in all frames
    repeated_annotations = [(k, v) for k, v in annotation_counter.items() if v > 1]

    if repeated_annotations:
        print("\n⚠️  Warning: Some annotations appear multiple times across frames!")
        for i, ((brand, tpoint, x1, y1, x2, y2), count) in enumerate(sorted(repeated_annotations, key=lambda x: x[1], reverse=True)[:3]):
            percentage = (count / total_annotations) * 100  # Corrected percentage
            print(f"🔹 Top {i+1}: {brand} ({tpoint}) appears {count} times ({percentage:.2f}% of all annotations)")
    else:
        print("\n✅ No duplicate annotations detected.")

if __name__ == "__main__":
    main()
