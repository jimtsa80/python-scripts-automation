#!/usr/bin/env python3
"""
Improved JSON to CSV converter for concatenated annotation data.
Processes the concatenated.json file and creates a comprehensive CSV output.
"""

import os
import json
import csv
import argparse
from collections import defaultdict, Counter
from datetime import datetime

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    print("Warning: openpyxl not available. Install with: pip install openpyxl")

def get_screen_location(startPoint, diagPoint, width, height):
    """Determine screen location of the annotation using letter codes (A, B, C, D, E)."""
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

def calculate_annotation_area(startPoint, diagPoint):
    """Calculate the area of the annotation bounding box."""
    x1, y1 = startPoint
    x2, y2 = diagPoint
    return abs((x2 - x1) * (y2 - y1))

def extract_time_from_filename(image_name):
    """Extract time from filename based on the last part with exactly 6 digits."""
    import re
    
    # Look for the last part of the filename that has exactly 6 digits
    # Pattern to match exactly 6 digits at the end of the filename (after underscore)
    match = re.search(r'_(\d{6})$', image_name)
    
    if match:
        # Found exactly 6 digits at the end, convert to seconds
        frame_number = int(match.group(1))
        # Convert to HH:MM:SS format
        hours = frame_number // 3600
        minutes = (frame_number % 3600) // 60
        seconds = frame_number % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        # No 6-digit sequence found at the end, return default time
        return "00:00:00"

def extract_filename_prefix(image_name):
    """Extract the first part of filename before the frame number."""
    import re
    
    # Remove the last part that contains digits (frame number)
    # This will keep everything before the last sequence of digits
    prefix = re.sub(r'_\d+$', '', image_name)
    return prefix

def is_single_digit_filename(image_name):
    """Check if filename ends with a single digit (like _6)."""
    import re
    return bool(re.search(r'_\d$', image_name))

def extract_base_name_from_json(input_file):
    """Extract base name from original JSON files in the directory (e.g., 20250814_ERC_Rome_IG_e547ad)."""
    import re
    import glob
    
    # Look for original JSON files in the same directory as the input file
    input_dir = os.path.dirname(input_file)
    if not input_dir:
        input_dir = "."
    
    # Find all JSON files that match the pattern part*_*.json
    json_files = glob.glob(os.path.join(input_dir, "part*_*.json"))
    
    if json_files:
        # Use the first JSON file to extract the base name
        first_json = json_files[0]
        filename = os.path.basename(first_json)
        name_without_ext = os.path.splitext(filename)[0]
        
        # Look for the pattern: part followed by underscore, then date and project info until dash
        # Example: part1_20250814_ERC_Rome_IG_e547ad-XV-250909-1724
        match = re.search(r'part\d+_(.+?)-', name_without_ext)
        
        if match:
            return match.group(1)  # Returns: 20250814_ERC_Rome_IG_e547ad
    
    # Fallback: use the input filename without extension
    filename = os.path.basename(input_file)
    name_without_ext = os.path.splitext(filename)[0]
    return name_without_ext

def extract_frame_number(filename):
    """Extract the frame number from filename (e.g., 1 from Facebook_xxx_1_000001)."""
    import re
    # Look for the last sequence of digits in the filename
    match = re.search(r'_(\d+)$', filename)
    if match:
        return int(match.group(1))
    return 0

def merge_duplicate_entries(processed_entries):
    """Merge entries with same Brand, Location, Screen Location, and consecutive frame numbers."""
    from collections import defaultdict
    
    # Group entries by the key: (brand, tpoint, location, filename_prefix)
    grouped_entries = defaultdict(list)
    
    for entry in processed_entries:
        # Extract filename prefix (everything before the frame number)
        filename_prefix = extract_filename_prefix(entry['frame_number'])
        key = (entry['brand'], entry['tpoint'], entry['location'], filename_prefix)
        grouped_entries[key].append(entry)
    
    merged_entries = []
    
    for key, entries in grouped_entries.items():
        if len(entries) == 1:
            # No merging needed
            merged_entries.append(entries[0])
        else:
            # Sort entries by frame number
            entries.sort(key=lambda x: extract_frame_number(x['frame_number']))
            
            # Group consecutive frame numbers
            consecutive_groups = []
            current_group = [entries[0]]
            
            for i in range(1, len(entries)):
                current_frame = extract_frame_number(entries[i]['frame_number'])
                previous_frame = extract_frame_number(entries[i-1]['frame_number'])
                
                if current_frame == previous_frame + 1:
                    # Consecutive frame, add to current group
                    current_group.append(entries[i])
                else:
                    # Non-consecutive frame, start new group
                    consecutive_groups.append(current_group)
                    current_group = [entries[i]]
            
            # Add the last group
            consecutive_groups.append(current_group)
            
            # Merge each consecutive group
            for group in consecutive_groups:
                if len(group) == 1:
                    # Single entry, no merging needed
                    merged_entries.append(group[0])
                else:
                    # Merge multiple consecutive entries
                    first_entry = group[0]  # Keep the first entry as base
                    
                    # Sum up duration and hits
                    total_duration = sum((entry.get('duration') or 0) for entry in group)
                    total_hits = sum((entry.get('hits') or 1) for entry in group)
                    
                    # Calculate average hits with 2 decimal places
                    avg_hits = round(total_hits / total_duration, 2) if total_duration > 0 else 0
                    
                    # Update the first entry with merged values
                    first_entry['duration'] = total_duration
                    first_entry['hits'] = total_hits
                    first_entry['avgHits'] = avg_hits
                    
                    merged_entries.append(first_entry)
    
    return merged_entries

def write_to_excel(merged_entries, output_file):
    """Write merged entries to Excel file."""
    if not EXCEL_AVAILABLE:
        raise ImportError("openpyxl is required for Excel output. Install with: pip install openpyxl")
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Annotations"
    
    # Define headers
    headers = [
        'Brand', 'Location', 'Time the brand is at screen',
        'Duration', 'Screen Location', 'Screen Size %',
        'Total Hits', 'Average Hits', 'Sequence Frame Number'
    ]
    
    # Write headers with styling
    header_font = Font(bold=True)
    header_fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
    
    # Write data rows
    for row, entry in enumerate(merged_entries, 2):
        ws.cell(row=row, column=1, value=entry['brand'])
        ws.cell(row=row, column=2, value=entry['tpoint'])
        ws.cell(row=row, column=3, value=entry['time'])
        ws.cell(row=row, column=4, value=entry['duration'])
        ws.cell(row=row, column=5, value=entry['location'])
        ws.cell(row=row, column=6, value=round(entry['size_percentage'], 3))
        ws.cell(row=row, column=7, value=entry['hits'])
        ws.cell(row=row, column=8, value=entry['avgHits'])
        ws.cell(row=row, column=9, value=entry['frame_number'])
    
    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Save the workbook
    wb.save(output_file)

def write_to_csv(entries, output_file):
    """Write entries to CSV file."""
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter='\t')
        
        # Write header (matching original format)
        csvwriter.writerow([
            'Brand', 'Location', 'Time the brand is at screen',
            'Duration', 'Screen Location', 'Screen Size %',
            'Total Hits', 'Average Hits', 'Sequence Frame Number'
        ])
        
        # Write rows (matching original format)
        for entry in entries:
            csvwriter.writerow([
                entry['brand'],
                entry['tpoint'],
                entry['time'],
                entry['duration'],
                entry['location'],
                f"{entry['size_percentage']:.3f}",
                entry['hits'],
                entry['avgHits'],  # Keep as float with 2 decimal places
                entry['frame_number']
            ])

def process_concatenated_json(input_file, output_file=None, output_format='csv'):
    """
    Process the concatenated JSON file and convert to CSV.
    
    Args:
        input_file (str): Path to the concatenated JSON file
        output_file (str): Path for the output CSV file (optional)
    
    Returns:
        dict: Statistics about the processing
    """
    
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found!")
        return None
    
    # Set default output filename if not provided
    if output_file is None:
        base_name = os.path.splitext(input_file)[0]
        extension = 'xlsx' if output_format == 'excel' else 'csv'
        output_file = f"{base_name}_annotations.{extension}"
    
    print(f"Processing: {input_file}")
    print(f"Output: {output_file}")
    
    try:
        # Load the JSON data
        print("Loading JSON data...")
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✓ JSON loaded successfully")
        print(f"  - Project: {data.get('project', 'Unknown')}")
        print(f"  - Total images: {data.get('imageNum', 0)}")
        
        # Initialize counters and data storage
        annotation_counter = Counter()
        processed_entries = []
        single_digit_entries = []  # For filenames ending in single digit
        six_digit_entries = []     # For filenames ending in 6 digits
        brand_stats = defaultdict(int)
        tpoint_stats = defaultdict(int)
        location_stats = defaultdict(int)
        
        images_data = data.get('images', {})
        total_images = len(images_data)
        
        print(f"Processing {total_images} images...")
        
        # Process each image and its annotations
        for idx, (image_key, image_data) in enumerate(images_data.items()):
            if idx % 500 == 0:  # Progress indicator
                print(f"  Progress: {idx}/{total_images} images processed...")
            
            image_name = image_data.get('imageName', image_key)
            width = image_data.get('width', 0)
            height = image_data.get('height', 0)
            annotations = image_data.get('annotations', [])
            
            for annotation in annotations:
                # Extract annotation data
                start_point = annotation.get('startPoint', [0, 0])
                diag_point = annotation.get('diagPoint', [0, 0])
                group = annotation.get('group', '')
                brand = annotation.get('brand', '')
                tpoint = annotation.get('tpoint', '')
                hits = annotation.get('hits')
                if hits is None:
                    hits = 1
                
                # Calculate derived metrics
                location = get_screen_location(start_point, diag_point, width, height)
                area = calculate_annotation_area(start_point, diag_point)
                total_area = width * height if width > 0 and height > 0 else 1
                size_percentage = (area / total_area) * 100
                
                # Create unique key for duplicate detection
                annotation_key = (brand, tpoint, tuple(start_point), tuple(diag_point))
                annotation_counter[annotation_key] += 1
                
                # Update statistics
                brand_stats[brand] += 1
                tpoint_stats[tpoint] += 1
                location_stats[location] += 1
                
                # Extract time from filename
                time_from_filename = extract_time_from_filename(image_name)
                
                # Create entry for CSV (matching original format)
                entry = {
                    'brand': brand,
                    'tpoint': tpoint,
                    'time': time_from_filename,
                    'duration': 1,
                    'location': location,
                    'size_percentage': size_percentage,
                    'hits': hits,
                    'avgHits': hits,
                    'frame_number': image_name
                }
                
                # Separate entries based on filename ending
                if is_single_digit_filename(image_name):
                    single_digit_entries.append(entry)
                else:
                    six_digit_entries.append(entry)
                
                # Keep all entries in processed_entries for statistics
                processed_entries.append(entry)
        
        print(f"✓ Processed {len(processed_entries)} annotations from {total_images} images")
        print(f"  - Single digit filenames: {len(single_digit_entries)} entries")
        print(f"  - 6-digit filenames: {len(six_digit_entries)} entries")
        
        # Process single digit entries (no merging)
        print("Processing single digit filename entries...")
        single_digit_entries.sort(key=lambda x: x['frame_number'])
        
        # Process 6-digit entries (with merging)
        print("Merging duplicate entries for 6-digit filenames...")
        merged_six_digit_entries = merge_duplicate_entries(six_digit_entries)
        print(f"✓ Merged from {len(six_digit_entries)} to {len(merged_six_digit_entries)} entries")
        merged_six_digit_entries.sort(key=lambda x: x['frame_number'])
        
        # Extract base name from JSON file
        base_name = extract_base_name_from_json(input_file)
        extension = 'xlsx' if output_format == 'excel' else 'csv'
        
        # Create output filenames with proper naming
        single_digit_file = f"{base_name}_images.{extension}"
        six_digit_file = f"{base_name}_videos.{extension}"
        
        # Write single digit entries file (images)
        if output_format == 'excel':
            print(f"Writing images Excel file: {single_digit_file}")
            write_to_excel(single_digit_entries, single_digit_file)
            print(f"✓ Images Excel file created: {single_digit_file}")
            
            print(f"Writing videos Excel file: {six_digit_file}")
            write_to_excel(merged_six_digit_entries, six_digit_file)
            print(f"✓ Videos Excel file created: {six_digit_file}")
        else:
            print(f"Writing images CSV file: {single_digit_file}")
            write_to_csv(single_digit_entries, single_digit_file)
            print(f"✓ Images CSV file created: {single_digit_file}")
            
            print(f"Writing videos CSV file: {six_digit_file}")
            write_to_csv(merged_six_digit_entries, six_digit_file)
            print(f"✓ Videos CSV file created: {six_digit_file}")
        
        # Generate statistics
        stats = {
            'total_annotations': len(processed_entries),
            'single_digit_annotations': len(single_digit_entries),
            'six_digit_annotations': len(six_digit_entries),
            'merged_six_digit_annotations': len(merged_six_digit_entries),
            'total_images': total_images,
            'unique_brands': len(brand_stats),
            'unique_tpoints': len(tpoint_stats),
            'duplicate_annotations': sum(1 for count in annotation_counter.values() if count > 1),
            'brand_stats': dict(brand_stats),
            'tpoint_stats': dict(tpoint_stats),
            'location_stats': dict(location_stats)
        }
        
        return stats
        
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format - {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def print_statistics(stats):
    """Print processing statistics."""
    if not stats:
        return
    
    print("\n" + "="*60)
    print("PROCESSING STATISTICS")
    print("="*60)
    print(f"Total annotations: {stats['total_annotations']:,}")
    print(f"Single digit filenames: {stats['single_digit_annotations']:,}")
    print(f"6-digit filenames: {stats['six_digit_annotations']:,}")
    print(f"Merged 6-digit annotations: {stats['merged_six_digit_annotations']:,}")
    print(f"Total images: {stats['total_images']:,}")
    print(f"Unique brands: {stats['unique_brands']}")
    print(f"Unique touchpoints: {stats['unique_tpoints']}")
    print(f"Duplicate annotations: {stats['duplicate_annotations']}")
    
    print(f"\nTop 10 Brands:")
    for brand, count in sorted(stats['brand_stats'].items(), key=lambda x: x[1], reverse=True)[:10]:
        percentage = (count / stats['total_annotations']) * 100
        print(f"  {brand}: {count:,} ({percentage:.1f}%)")
    
    print(f"\nTop 10 Touchpoints:")
    for tpoint, count in sorted(stats['tpoint_stats'].items(), key=lambda x: x[1], reverse=True)[:10]:
        percentage = (count / stats['total_annotations']) * 100
        print(f"  {tpoint}: {count:,} ({percentage:.1f}%)")
    
    print(f"\nScreen Locations:")
    for location, count in sorted(stats['location_stats'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / stats['total_annotations']) * 100
        print(f"  {location}: {count:,} ({percentage:.1f}%)")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Convert concatenated JSON annotation data to CSV or Excel format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python jsonToCsv_improved.py concatenated.json
  python jsonToCsv_improved.py concatenated.json -f excel -o my_annotations.xlsx
  python jsonToCsv_improved.py concatenated.json -f csv -o my_annotations.csv
        """
    )
    
    parser.add_argument("input_file", help="Path to the concatenated JSON file")
    parser.add_argument("-o", "--output", help="Output file path (optional)")
    parser.add_argument("-f", "--format", choices=['csv', 'excel'], default='excel',
                       help="Output format: csv or excel (default: excel)")
    parser.add_argument("--stats-only", action="store_true", 
                       help="Only show statistics, don't create output file")
    
    args = parser.parse_args()
    
    print("JSON to CSV Converter (Improved)")
    print("="*50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Process the file
    stats = process_concatenated_json(args.input_file, args.output, args.format)
    
    if stats:
        print_statistics(stats)
        print(f"\n✓ Processing completed successfully!")
    else:
        print(f"\n✗ Processing failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
