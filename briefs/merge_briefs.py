"""
Merge two brief files (AO2026.txt format) into one.
Combines brands and locations - if brand exists in both, merges all locations.
Output: MERGED_<second_filename>
"""
import os
import sys
from collections import defaultdict

def parse_brief_file(file_path):
    """
    Parse a brief file in AO2026.txt format.
    Returns: dict {brand: set(locations)}
    """
    brands_dict = defaultdict(set)
    
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found")
        return None
    
    try:
        current_brand = None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('//') or line.startswith('--'):
                    continue
                
                # Brand line starts with #
                if line.startswith('#'):
                    current_brand = line[1:].strip()  # Remove # and whitespace
                    if current_brand:
                        brands_dict[current_brand] = set()
                # Location line (under a brand)
                elif current_brand:
                    brands_dict[current_brand].add(line)
        
        return dict(brands_dict)
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def merge_briefs(file1_path, file2_path, output_path):
    """
    Merge two brief files into one.
    """
    print("=" * 70)
    print("Merging Brief Files")
    print("=" * 70)
    print(f"File 1: {file1_path}")
    print(f"File 2: {file2_path}")
    print(f"Output: {output_path}")
    print()
    
    # Parse both files
    print("Parsing files...")
    brands1 = parse_brief_file(file1_path)
    brands2 = parse_brief_file(file2_path)
    
    if brands1 is None or brands2 is None:
        print("Error: Could not parse one or both files")
        sys.exit(1)
    
    print(f"File 1: {len(brands1)} brands")
    print(f"File 2: {len(brands2)} brands")
    
    # Merge brands
    merged_brands = defaultdict(set)
    
    # Add all brands from file1
    for brand, locations in brands1.items():
        merged_brands[brand].update(locations)
    
    # Add all brands from file2 (will merge if brand exists)
    for brand, locations in brands2.items():
        merged_brands[brand].update(locations)
    
    print(f"Merged: {len(merged_brands)} unique brands")
    print()
    
    # Write merged file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write header comments from file1 (if any)
            with open(file1_path, 'r', encoding='utf-8') as f1:
                for line in f1:
                    line_stripped = line.strip()
                    if line_stripped.startswith('//') or line_stripped.startswith('--'):
                        f.write(line)
                    elif not line_stripped:
                        continue
                    elif line_stripped.startswith('#'):
                        break  # Stop at first brand
            
            # Write merged brands (sorted alphabetically)
            for brand in sorted(merged_brands.keys()):
                f.write(f"#{brand}\n")
                # Write locations (sorted alphabetically)
                for location in sorted(merged_brands[brand]):
                    f.write(f"{location}\n")
                f.write("\n")  # Empty line between brands
        
        print(f"Successfully created merged file: {output_path}")
        print()
        
        # Print statistics
        print("=" * 70)
        print("MERGE STATISTICS")
        print("=" * 70)
        
        # Count brands only in file1
        brands_only_in_1 = set(brands1.keys()) - set(brands2.keys())
        # Count brands only in file2
        brands_only_in_2 = set(brands2.keys()) - set(brands1.keys())
        # Common brands
        common_brands = set(brands1.keys()) & set(brands2.keys())
        
        print(f"Brands only in File 1: {len(brands_only_in_1)}")
        print(f"Brands only in File 2: {len(brands_only_in_2)}")
        print(f"Common brands (merged): {len(common_brands)}")
        print(f"Total unique brands in merged file: {len(merged_brands)}")
        print()
        
        # Count locations
        total_locations = sum(len(locs) for locs in merged_brands.values())
        print(f"Total locations in merged file: {total_locations}")
        
        # Show examples of merged brands (if any)
        if common_brands:
            print()
            print("Examples of merged brands (with location counts):")
            for brand in sorted(list(common_brands))[:5]:  # Show first 5
                locs1 = len(brands1[brand])
                locs2 = len(brands2[brand])
                locs_merged = len(merged_brands[brand])
                print(f"  #{brand}: File1={locs1}, File2={locs2}, Merged={locs_merged}")
            if len(common_brands) > 5:
                print(f"  ... and {len(common_brands) - 5} more")
        
        print("=" * 70)
        
    except Exception as e:
        print(f"Error writing merged file: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) < 3:
        print("Usage: python merge_briefs.py <file1.txt> <file2.txt>")
        print()
        print("Merges two brief files into one:")
        print("  - Combines all brands from both files")
        print("  - If brand exists in both, merges all locations (no duplicates)")
        print("  - Output: MERGED_<file2_name>")
        print()
        print("Example:")
        print("  python merge_briefs.py A02026.txt UPDATE_AO2026.txt")
        print("  -> Creates: MERGED_UPDATE_AO2026.txt")
        sys.exit(1)
    
    file1 = sys.argv[1]
    file2 = sys.argv[2]
    
    # If files are relative, look in script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(file1):
        file1 = os.path.join(script_dir, file1)
    if not os.path.isabs(file2):
        file2 = os.path.join(script_dir, file2)
    
    # Create output filename: MERGED_<file2_name>
    file2_basename = os.path.basename(file2)
    output_filename = f"MERGED_{file2_basename}"
    output_path = os.path.join(script_dir, output_filename)
    
    merge_briefs(file1, file2, output_path)

if __name__ == "__main__":
    main()



