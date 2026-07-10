"""
New Brief Creator
Reads brands.txt and creates a formatted brief with brands and their locations.
"""
import os
import re
import sys
from collections import defaultdict

_CAR_NUMBER_RE = re.compile(r"Car\s+(\d+)\s*$", re.IGNORECASE)


def car_number_sort_key(location: str):
    """Sort locations by trailing car number, then alphabetically."""
    match = _CAR_NUMBER_RE.search(location.strip())
    if match:
        return (0, int(match.group(1)), location.lower())
    return (1, 0, location.lower())


def brand_car_sort_key(item):
    """Sort brands by their smallest car number, then alphabetically."""
    brand, locations = item
    car_numbers = [
        int(match.group(1))
        for location in locations
        if (match := _CAR_NUMBER_RE.search(location.strip()))
    ]
    min_car = min(car_numbers) if car_numbers else float("inf")
    return (min_car, brand.lower())

def detect_file_format(lines):
    """
    Detect which format the file uses:
    - Format 1: Each line has brand\tlocation (or brand  location)
    - Format 2: First line has brands (columns), subsequent lines have locations
    Returns: 'format1' or 'format2'
    """
    if not lines:
        return 'format1'
    
    # Check first non-empty line
    first_line = None
    for line in lines:
        if line.strip():
            first_line = line.strip()
            break
    
    if not first_line:
        return 'format1'
    
    # Split first line by tab
    parts = first_line.split('\t')
    
    # If first line has many columns (>= 3), it's likely format 2
    if len(parts) >= 3:
        # Check if second line also has many columns (confirms format 2)
        second_line = None
        for line in lines[1:]:
            if line.strip():
                second_line = line.strip()
                break
        
        if second_line and len(second_line.split('\t')) >= 3:
            return 'format2'
    
    return 'format1'

def parse_format1(lines):
    """
    Parse Format 1: Each line has brand\tlocation (or brand  location)
    Returns: dict {brand: [locations]}
    """
    brands_dict = defaultdict(list)
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Split by tab
        parts = line.split('\t')
        
        if len(parts) < 2:
            # Try splitting by multiple spaces if no tab
            parts = [p for p in line.split('  ') if p.strip()]
            if len(parts) < 2:
                print(f"Warning: Line {line_num} has invalid format: {line}")
                continue
        
        brand = parts[0].strip()
        location = parts[1].strip()
        
        if brand and location:
            brands_dict[brand].append(location)
    
    return brands_dict

def parse_format2(lines):
    """
    Parse Format 2: First line has brands (columns), subsequent lines have locations
    Returns: dict {brand: [locations]}
    """
    brands_dict = defaultdict(list)
    
    # Find first non-empty line (should be brands)
    brands_line = None
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip():
            brands_line = line.strip()
            start_idx = i
            break
    
    if not brands_line:
        return brands_dict
    
    # Split brands by tab
    brands = [b.strip() for b in brands_line.split('\t') if b.strip()]
    
    if not brands:
        return brands_dict
    
    # Process subsequent lines (locations)
    for line in lines[start_idx + 1:]:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Split locations by tab
        locations = [l.strip() for l in line.split('\t')]
        
        # Match each location with corresponding brand
        for i, location in enumerate(locations):
            if i < len(brands) and location:  # Make sure we have a brand for this column
                brand = brands[i]
                brands_dict[brand].append(location)
    
    return brands_dict

def dedupe_brand_locations(brands_dict):
    """
    Remove duplicate locations within the same brand (keeps first occurrence).
    Returns: (deduped_dict, removed_count)
    """
    deduped = {}
    removed_count = 0

    for brand, locations in brands_dict.items():
        seen = set()
        unique_locations = []

        for location in locations:
            loc = location.strip()
            if not loc:
                continue
            if loc in seen:
                removed_count += 1
                continue
            seen.add(loc)
            unique_locations.append(loc)

        if unique_locations:
            deduped[brand] = unique_locations

    return deduped, removed_count

def parse_brands_file(file_path):
    """
    Parse brands.txt file (supports both formats).
    Returns: dict {brand: [locations]}
    """
    brands_dict = defaultdict(list)
    
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found")
        sys.exit(1)
    
    try:
        # Read all lines first
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Detect format
        file_format = detect_file_format(lines)
        print(f"Detected format: {file_format}")
        
        # Parse according to format
        if file_format == 'format2':
            brands_dict = parse_format2(lines)
        else:
            brands_dict = parse_format1(lines)
    
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)
    
    return brands_dict

def create_brief(brands_dict, output_file=None):
    """
    Create formatted brief from brands dictionary.
    """
    output_lines = []
    
    # Sort brands by car number (ascending), then alphabetically
    sorted_brands = [brand for brand, _ in sorted(brands_dict.items(), key=brand_car_sort_key)]
    
    total_brands = len(sorted_brands)
    total_locations = 0
    
    for brand in sorted_brands:
        locations = brands_dict[brand]
        
        # Add brand header
        output_lines.append(f"#{brand}")
        
        # Add all locations for this brand
        for location in sorted(locations, key=car_number_sort_key):
            output_lines.append(location)
        
        # Add empty line between brands
        output_lines.append("")
        
        total_locations += len(locations)
    
    # Join all lines
    output_text = "\n".join(output_lines)
    
    # Print or save
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_text)
            print(f"Brief saved to: {output_file}")
        except Exception as e:
            print(f"Error saving file: {e}")
            # Still print to console
            print("\n" + "=" * 50)
            print(output_text)
    else:
        print("\n" + "=" * 50)
        print(output_text)
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"Total: {total_brands} brands x {total_locations} locations")
    print("=" * 50)

def main():
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    brands_file = os.path.join(script_dir, "brands.txt")
    
    # Parse brands file
    brands_dict = parse_brands_file(brands_file)

    if not brands_dict:
        print("No brands found in file")
        sys.exit(1)

    brands_dict, removed_duplicates = dedupe_brand_locations(brands_dict)
    print(f"Removed {removed_duplicates} duplicate location(s) under the same brand")
    
    # Create output file path (same directory, named "brief_output.txt")
    output_file = os.path.join(script_dir, "brief_output.txt")
    
    # Create brief
    create_brief(brands_dict, output_file)

if __name__ == "__main__":
    main()

