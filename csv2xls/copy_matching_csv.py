"""
Copy CSV files that match a partial filename into a 'results' folder.
Usage: python copy_matching_csv.py <search_path> <partial_filename> [--count]
Example: python copy_matching_csv.py "C:\data\exports" "20260102_UC_Nine_1255"
         python copy_matching_csv.py "C:\data\exports" "20260102_UC_Nine_1255" --count
"""
import argparse
import shutil
import re
from pathlib import Path
from collections import defaultdict


def check_duplicate_parts(files):
    """Check for files with same part number and same prefix until first dash.
    
    Example:
        part4_reduced_20260103_UC_Nine_1025-cluster_3-EG-260103-1718-Video
        part4_reduced_20260103_UC_Nine_1025-cluster_3-ER-260104-1313-Video
    Both have part4_ and same prefix 'reduced_20260103_UC_Nine_1025' until first '-'
    """
    # Group files by (part_number, prefix_until_first_dash)
    groups = defaultdict(list)
    
    for f in files:
        name = f.stem  # filename without extension
        
        # Extract part number (e.g., part4_)
        part_match = re.match(r'^(part\d+_)', name)
        if not part_match:
            continue
        
        part = part_match.group(1)
        
        # Extract prefix from after part until first dash
        rest = name[len(part):]  # Everything after part4_
        dash_idx = rest.find('-')
        if dash_idx == -1:
            prefix = rest  # No dash found, use entire rest
        else:
            prefix = rest[:dash_idx]  # From start until first dash
        
        key = (part, prefix)
        groups[key].append(f)
    
    # Check for duplicates (same part + prefix, multiple files)
    warnings = []
    for (part, prefix), file_list in groups.items():
        if len(file_list) > 1:
            warnings.append((part, prefix, file_list))
    
    return warnings


def main():
    parser = argparse.ArgumentParser(
        description="Copy CSV files that match a partial filename into a 'results' folder."
    )
    parser.add_argument("search_path", type=Path, help="Directory to search for CSV files")
    parser.add_argument("partial_filename", type=str, help="Partial string to match in filename")
    parser.add_argument(
        "--count",
        action="store_true",
        help="Print how many matching files exist and exit (no copy)",
    )
    args = parser.parse_args()

    search_path = args.search_path.resolve()
    partial = args.partial_filename.strip()

    if not search_path.is_dir():
        print(f"Error: Path is not a directory: {search_path}")
        raise SystemExit(1)

    # Collect all matching files first
    matching_files = []
    for f in search_path.rglob("*.csv"):
        if partial in f.name:
            matching_files.append(f)

    if args.count:
        print(f"Found {len(matching_files)} matching CSV file(s) in {search_path}")
        return

    # Τα αποτελέσματα αποθηκεύονται σε φάκελο 'csvs' δίπλα στο script,
    # ανεξάρτητα από το path που ψάχνουμε.
    results_dir = Path(__file__).parent / "csvs"
    results_dir.mkdir(exist_ok=True)
    
    # Check for duplicate parts before copying
    warnings = check_duplicate_parts(matching_files)
    if warnings:
        print("\n⚠️  WARNING: Found files with same part number and prefix:")
        for part, prefix, file_list in warnings:
            print(f"  Part: {part}, Prefix: {prefix}")
            for f in file_list:
                print(f"    - {f.name}")
        print()

    count = 0
    for f in matching_files:
        dest = results_dir / f.name
        if dest.resolve() == f.resolve():
            continue
        n = 1
        while dest.exists():
            dest = results_dir / f"{f.stem}_{n}{f.suffix}"
            n += 1
        shutil.copy2(f, dest)
        print(f"Copied: {f.name} -> csvs\\{dest.name}")
        count += 1

    print(f"\nDone. {count} CSV file(s) copied to {results_dir} (total matching: {len(matching_files)})")


if __name__ == "__main__":
    main()
