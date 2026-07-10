#!/usr/bin/env python3
"""
Script to concatenate multiple JSON files by merging their 'images' entries
while keeping other fields from the first file.
Groups files by base name extracted from 'reduced_' until '-'.
"""

import json
import os
import glob
import re
import argparse
from collections import defaultdict

def extract_base_name_from_filename(filename):
    """
    Extract base name from filename pattern: reduced_<base_name>-<rest>
    Returns the part between 'reduced_' and the first '-'
    """
    # Remove file extension
    name_without_ext = os.path.splitext(filename)[0]
    
    # Look for pattern: reduced_<base_name>-<rest>
    match = re.search(r'reduced_(.+?)-', name_without_ext)
    
    if match:
        return match.group(1)  # Returns the base name
    else:
        # Fallback: return the filename without extension
        return name_without_ext

def group_files_by_base_name(json_files):
    """
    Group JSON files by their base name extracted from filename.
    Returns a dictionary with base_name as key and list of files as value.
    """
    grouped_files = defaultdict(list)
    
    for file_path in json_files:
        filename = os.path.basename(file_path)
        base_name = extract_base_name_from_filename(filename)
        grouped_files[base_name].append(file_path)
    
    return grouped_files

def main():
    """Main function to run the script with CLI argument for input folder."""
    parser = argparse.ArgumentParser(
        description="Concatenate JSON files by merging 'images' entries, grouped by base name."
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "Results"),
        help="Directory containing the JSON files (default: ./Results)",
    )
    args = parser.parse_args()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.abspath(args.input_dir)

    print("JSON File Concatenator (Grouped by Base Name)")
    print("=" * 60)
    print(f"Working directory: {current_dir}")
    print(f"Results directory: {results_dir}")

    # Check if Results directory exists
    if not os.path.exists(results_dir):
        print(f"Error: Results directory not found at {results_dir}")
        return
    
    # Find all JSON files in the Results directory
    json_files = glob.glob(os.path.join(results_dir, "*.json"))
    
    if not json_files:
        print("No JSON files found in the Results directory!")
        return
    
    print(f"\nFound {len(json_files)} JSON files in Results directory")
    
    # Group files by base name
    grouped_files = group_files_by_base_name(json_files)
    
    print(f"\nGrouped into {len(grouped_files)} base name groups:")
    print("-" * 60)
    for base_name, files in grouped_files.items():
        print(f"\n📁 GROUP: '{base_name}'")
        print(f"   Files ({len(files)}):")
        for i, file in enumerate(files, 1):
            filename = os.path.basename(file)
            print(f"   {i:2d}. {filename}")
        print(f"   → Will create: {base_name}.json")
    
    # Show grouping summary
    print(f"\n{'='*60}")
    print("GROUPING SUMMARY:")
    print(f"Total groups: {len(grouped_files)}")
    print(f"Total files: {len(json_files)}")
    print(f"{'='*60}")
    
    print("\nStarting concatenation process...")
    
    # Process each group
    successful_groups = 0
    for base_name, files in grouped_files.items():
        print(f"\n{'='*60}")
        print(f"Processing group: {base_name}")
        print(f"{'='*60}")
        
        # Create output filename for this group
        output_filename = f"{base_name}.json"
        output_path = os.path.join(current_dir, output_filename)
        
        # Sort files to ensure consistent ordering
        files.sort()
        
        # Load the first file as the base
        print(f"Loading base file: {os.path.basename(files[0])}")
        with open(files[0], 'r', encoding='utf-8') as f:
            base_data = json.load(f)
        
        # Initialize the merged images dictionary with the first file's images
        merged_images = base_data.get('images', {}).copy()
        total_images = len(merged_images)
        
        print(f"Base file contains {total_images} images")
        
        # Process remaining files
        for i, file_path in enumerate(files[1:], 1):
            print(f"Processing file {i+1}/{len(files)}: {os.path.basename(file_path)}")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                
                # Get images from this file
                file_images = file_data.get('images', {})
                file_image_count = len(file_images)
                
                print(f"  - Contains {file_image_count} images")
                
                # Merge images (this will overwrite if there are duplicate keys)
                merged_images.update(file_images)
                
                # Count how many new images were added
                new_total = len(merged_images)
                new_images_added = new_total - total_images
                total_images = new_total
                
                if new_images_added > 0:
                    print(f"  - Added {new_images_added} new images (total: {total_images})")
                else:
                    print(f"  - No new images added (all were duplicates)")
                    
            except Exception as e:
                print(f"  - Error processing file: {e}")
                continue
        
        # Update the base data with merged images
        base_data['images'] = merged_images
        
        # Update imageNum to reflect the total number of images
        base_data['imageNum'] = total_images
        
        # Save the concatenated data
        print(f"\nSaving concatenated data to: {output_filename}")
        print(f"Total images in output: {total_images}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(base_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Successfully created {output_filename}")
        print(f"  - Project: {base_data.get('project', 'N/A')}")
        print(f"  - Total images: {base_data.get('imageNum', 0)}")
        print(f"  - Annotator: {base_data.get('prefs', {}).get('AnnotatorName', 'N/A')}")
        
        successful_groups += 1
    
    print(f"\n{'='*60}")
    print(f"CONCATENATION SUMMARY")
    print(f"{'='*60}")
    print(f"Successfully processed {successful_groups}/{len(grouped_files)} groups")
    print(f"Created {successful_groups} concatenated JSON files in the main directory")

if __name__ == "__main__":
    main()
