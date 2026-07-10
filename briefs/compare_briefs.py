"""
Compare two brief files (AO2026.txt format) and show differences.
Shows extra brands and extra locations per brand.
"""
import os
import sys
from collections import defaultdict

def parse_brief_file(file_path):
    """
    Parse a brief file in AO2026.txt format.
    Returns: dict {brand: [locations]}
    """
    brands_dict = defaultdict(list)
    
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
                        brands_dict[current_brand] = []
                # Location line (under a brand)
                elif current_brand:
                    brands_dict[current_brand].append(line)
        
        return dict(brands_dict)
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def compare_briefs(file1_path, file2_path):
    """
    Compare two brief files and show differences.
    """
    print("=" * 70)
    print("Comparing Brief Files")
    print("=" * 70)
    print(f"File 1: {file1_path}")
    print(f"File 2: {file2_path}")
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
    print()
    
    # Find brands only in file1
    brands_only_in_1 = set(brands1.keys()) - set(brands2.keys())
    # Find brands only in file2
    brands_only_in_2 = set(brands2.keys()) - set(brands1.keys())
    # Common brands
    common_brands = set(brands1.keys()) & set(brands2.keys())
    
    # Print extra brands in file1
    if brands_only_in_1:
        print("=" * 70)
        print(f"EXTRA BRANDS in File 1 ({len(brands_only_in_1)}):")
        print("=" * 70)
        for brand in sorted(brands_only_in_1):
            locations_count = len(brands1[brand])
            print(f"  #{brand} ({locations_count} location(s))")
            for loc in brands1[brand]:
                print(f"    - {loc}")
        print()
    else:
        print("No extra brands in File 1")
        print()
    
    # Print extra brands in file2
    if brands_only_in_2:
        print("=" * 70)
        print(f"EXTRA BRANDS in File 2 ({len(brands_only_in_2)}):")
        print("=" * 70)
        for brand in sorted(brands_only_in_2):
            locations_count = len(brands2[brand])
            print(f"  #{brand} ({locations_count} location(s))")
            for loc in brands2[brand]:
                print(f"    - {loc}")
        print()
    else:
        print("No extra brands in File 2")
        print()
    
    # Find extra locations in common brands
    extra_locations_in_1 = defaultdict(list)
    extra_locations_in_2 = defaultdict(list)
    
    for brand in common_brands:
        locations1 = set(brands1[brand])
        locations2 = set(brands2[brand])
        
        # Locations only in file1
        only_in_1 = locations1 - locations2
        if only_in_1:
            extra_locations_in_1[brand] = sorted(only_in_1)
        
        # Locations only in file2
        only_in_2 = locations2 - locations1
        if only_in_2:
            extra_locations_in_2[brand] = sorted(only_in_2)
    
    # Print extra locations in file1
    if extra_locations_in_1:
        print("=" * 70)
        print(f"EXTRA LOCATIONS in File 1 ({sum(len(locs) for locs in extra_locations_in_1.values())} total):")
        print("=" * 70)
        for brand in sorted(extra_locations_in_1.keys()):
            print(f"  #{brand}:")
            for loc in extra_locations_in_1[brand]:
                print(f"    - {loc}")
        print()
    else:
        print("No extra locations in File 1 (common brands)")
        print()
    
    # Print extra locations in file2
    if extra_locations_in_2:
        print("=" * 70)
        print(f"EXTRA LOCATIONS in File 2 ({sum(len(locs) for locs in extra_locations_in_2.values())} total):")
        print("=" * 70)
        for brand in sorted(extra_locations_in_2.keys()):
            print(f"  #{brand}:")
            for loc in extra_locations_in_2[brand]:
                print(f"    - {loc}")
        print()
    else:
        print("No extra locations in File 2 (common brands)")
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Extra brands in File 1: {len(brands_only_in_1)}")
    print(f"Extra brands in File 2: {len(brands_only_in_2)}")
    print(f"Common brands: {len(common_brands)}")
    print(f"Extra locations in File 1: {sum(len(locs) for locs in extra_locations_in_1.values())}")
    print(f"Extra locations in File 2: {sum(len(locs) for locs in extra_locations_in_2.values())}")
    print("=" * 70)

def main():
    if len(sys.argv) < 3:
        print("Usage: python compare_briefs.py <file1.txt> <file2.txt>")
        print()
        print("Example:")
        print("  python compare_briefs.py A02026.txt AO_OnePoint2026.txt")
        sys.exit(1)
    
    file1 = sys.argv[1]
    file2 = sys.argv[2]
    
    # If files are relative, look in script directory
    if not os.path.isabs(file1):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file1 = os.path.join(script_dir, file1)
    
    if not os.path.isabs(file2):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file2 = os.path.join(script_dir, file2)
    
    compare_briefs(file1, file2)

if __name__ == "__main__":
    main()



