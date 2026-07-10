#!/usr/bin/env python3
"""
Script to aggregate Excel files by merging rows with same Brand, Location, Screen Location,
and consecutive frame numbers.
"""

import os
import glob
import argparse
import re
from collections import defaultdict

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: pandas not available. Install with: pip install pandas")

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    print("Warning: openpyxl not available. Install with: pip install openpyxl")

def extract_frame_number(filename):
    """Extract the frame number from filename (e.g., 305 from Facebook_xxx_1_000305)."""
    # Look for the last sequence of digits in the filename
    match = re.search(r'_(\d+)$', filename)
    if match:
        return int(match.group(1))
    return 0

def extract_filename_prefix(filename):
    """Extract the first part of filename before the frame number."""
    # Remove the last part that contains digits (frame number)
    prefix = re.sub(r'_\d+$', '', filename)
    return prefix

def aggregate_excel_file(input_file, output_file=None):
    """
    Aggregate rows in an Excel file based on Brand, Location, Screen Location, and consecutive frame numbers.
    
    Args:
        input_file (str): Path to the input Excel file
        output_file (str): Path for the output Excel file (optional)
    
    Returns:
        bool: True if successful, False otherwise
    """
    
    if not PANDAS_AVAILABLE:
        print("Error: pandas is required. Install with: pip install pandas")
        return False
    
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found!")
        return False
    
    # Set default output filename if not provided
    if output_file is None:
        base_name = os.path.splitext(input_file)[0]
        # Remove _concatenated_ from filename if present
        base_name = base_name.replace('_concatenated_', '_')
        output_file = f"{base_name}.xlsx"
    
    print(f"Processing: {input_file}")
    print(f"Output: {output_file}")
    
    try:
        # Read the Excel file
        print("Loading Excel data...")
        df = pd.read_excel(input_file)
        
        print(f"✓ Excel loaded successfully")
        print(f"  - Total rows: {len(df)}")
        print(f"  - Columns: {list(df.columns)}")
        
        # Check if required columns exist
        required_columns = ['Brand', 'Location', 'Screen Location', 'Sequence Frame Number']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            print(f"Error: Missing required columns: {missing_columns}")
            return False
        
        # Group rows by Brand, Location, Screen Location, and filename prefix
        grouped_data = defaultdict(list)
        
        for index, row in df.iterrows():
            filename = str(row['Sequence Frame Number'])
            filename_prefix = extract_filename_prefix(filename)
            key = (row['Brand'], row['Location'], row['Screen Location'], filename_prefix)
            grouped_data[key].append((index, row))
        
        print(f"Grouped into {len(grouped_data)} groups")
        
        # Process each group
        aggregated_rows = []
        total_original_rows = len(df)
        total_aggregated_rows = 0
        
        for key, rows in grouped_data.items():
            brand, location, screen_location, filename_prefix = key
            
            if len(rows) == 1:
                # Single row, no aggregation needed
                aggregated_rows.append(rows[0][1])
                total_aggregated_rows += 1
            else:
                # Multiple rows, check for consecutive frame numbers
                # Sort by frame number
                rows.sort(key=lambda x: extract_frame_number(str(x[1]['Sequence Frame Number'])))
                
                # Group consecutive frame numbers
                consecutive_groups = []
                current_group = [rows[0]]
                
                for i in range(1, len(rows)):
                    current_frame = extract_frame_number(str(rows[i][1]['Sequence Frame Number']))
                    previous_frame = extract_frame_number(str(rows[i-1][1]['Sequence Frame Number']))
                    
                    if current_frame == previous_frame + 1:
                        # Consecutive frame, add to current group
                        current_group.append(rows[i])
                    else:
                        # Non-consecutive frame, start new group
                        consecutive_groups.append(current_group)
                        current_group = [rows[i]]
                
                # Add the last group
                consecutive_groups.append(current_group)
                
                # Aggregate each consecutive group
                for group in consecutive_groups:
                    if len(group) == 1:
                        # Single row, no aggregation needed
                        aggregated_rows.append(group[0][1])
                        total_aggregated_rows += 1
                    else:
                        # Aggregate multiple consecutive rows
                        first_row = group[0][1].copy()
                        
                        # Sum duration and total hits
                        total_duration = sum(row[1]['Duration'] for row in group)
                        total_hits = sum(row[1]['Total Hits'] for row in group)
                        
                        # Calculate average hits
                        avg_hits = round(total_hits / total_duration, 2) if total_duration > 0 else 0
                        
                        # Update the first row with aggregated values
                        first_row['Duration'] = total_duration
                        first_row['Total Hits'] = total_hits
                        first_row['Average Hits'] = avg_hits
                        
                        # Keep the first frame number as representative
                        first_row['Sequence Frame Number'] = group[0][1]['Sequence Frame Number']
                        
                        aggregated_rows.append(first_row)
                        total_aggregated_rows += 1
        
        # Create new DataFrame with aggregated data
        aggregated_df = pd.DataFrame(aggregated_rows)
        
        # Sort by the last column (Sequence Frame Number)
        if 'Sequence Frame Number' in aggregated_df.columns:
            # Extract frame numbers for sorting
            aggregated_df['_sort_key'] = aggregated_df['Sequence Frame Number'].apply(
                lambda x: extract_frame_number(str(x))
            )
            aggregated_df = aggregated_df.sort_values('_sort_key')
            aggregated_df = aggregated_df.drop('_sort_key', axis=1)
            print(f"✓ Sorted by Sequence Frame Number")
        
        # Save to Excel file
        print(f"Saving aggregated data...")
        aggregated_df.to_excel(output_file, index=False)
        
        print(f"✓ Successfully created {output_file}")
        print(f"  - Original rows: {total_original_rows}")
        print(f"  - Aggregated rows: {total_aggregated_rows}")
        print(f"  - Reduction: {total_original_rows - total_aggregated_rows} rows ({((total_original_rows - total_aggregated_rows) / total_original_rows * 100):.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"Error processing file: {e}")
        return False

def process_folder(input_folder, output_folder=None):
    """
    Process all Excel files in a folder.
    
    Args:
        input_folder (str): Path to the folder containing Excel files
        output_folder (str): Path to the output folder (optional, defaults to input folder)
    
    Returns:
        dict: Statistics about the processing
    """
    
    if not os.path.exists(input_folder):
        print(f"Error: Input folder '{input_folder}' not found!")
        return None
    
    if output_folder is None:
        output_folder = input_folder
    
    # Find all Excel files in the folder
    excel_files = glob.glob(os.path.join(input_folder, "*.xlsx"))
    
    if not excel_files:
        print(f"No Excel files found in folder: {input_folder}")
        return None
    
    print(f"Found {len(excel_files)} Excel files in folder")
    
    stats = {
        'total_files': len(excel_files),
        'successful_files': 0,
        'failed_files': 0,
        'total_original_rows': 0,
        'total_aggregated_rows': 0
    }
    
    # Process each Excel file
    for excel_file in excel_files:
        filename = os.path.basename(excel_file)
        print(f"\n{'='*60}")
        print(f"Processing: {filename}")
        print(f"{'='*60}")
        
        # Create output filename
        base_name = os.path.splitext(filename)[0]
        base_name = base_name.replace('_concatenated_', '_')
        output_file = os.path.join(output_folder, f"{base_name}.xlsx")
        
        # Process the file
        if aggregate_excel_file(excel_file, output_file):
            stats['successful_files'] += 1
        else:
            stats['failed_files'] += 1
    
    return stats

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Aggregate Excel files by merging rows with same Brand, Location, Screen Location, and consecutive frame numbers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 aggregate_xlsx.py Results
  python3 aggregate_xlsx.py Results --output-dir /path/to/output
  python3 aggregate_xlsx.py file.xlsx --output file_aggregated.xlsx
        """
    )
    
    parser.add_argument(
        'input_path',
        help='Path to Excel file or folder containing Excel files'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output file path (for single file) or output directory (for folder)'
    )
    
    args = parser.parse_args()
    
    print("Excel File Aggregator")
    print("=" * 50)
    
    # Check if input is a file or folder
    if os.path.isfile(args.input_path):
        # Process single file
        if aggregate_excel_file(args.input_path, args.output):
            print(f"\n✓ Processing completed successfully!")
        else:
            print(f"\n✗ Processing failed!")
            return 1
    elif os.path.isdir(args.input_path):
        # Process folder
        stats = process_folder(args.input_path, args.output)
        
        if stats:
            print(f"\n{'='*60}")
            print(f"AGGREGATION SUMMARY")
            print(f"{'='*60}")
            print(f"Total files: {stats['total_files']}")
            print(f"Successful: {stats['successful_files']}")
            print(f"Failed: {stats['failed_files']}")
            print(f"\n✓ Processing completed successfully!")
        else:
            print(f"\n✗ Processing failed!")
            return 1
    else:
        print(f"Error: '{args.input_path}' is neither a file nor a directory")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
