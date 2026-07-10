import pandas as pd
import sys
import os
from pathlib import Path

def calculate_brand_durations(file_or_folder_path):
    """
    Reads xlsx file(s) and calculates the total duration for each brand.
    Can accept either a single xlsx file or a folder containing xlsx files.
    """
    path = Path(file_or_folder_path)
    
    if not path.exists():
        print(f"❌ Path not found: {file_or_folder_path}")
        return
    
    # Determine if it's a file or folder
    xlsx_files = []
    
    if path.is_file():
        if path.suffix.lower() == '.xlsx':
            xlsx_files = [path]
            print(f"📄 Processing single file: {path.name}")
        else:
            print(f"❌ File is not an xlsx file: {file_or_folder_path}")
            return
    elif path.is_dir():
        # Find all xlsx files in the folder (recursively)
        xlsx_files = list(path.rglob("*.xlsx"))
        if not xlsx_files:
            print(f"❌ No xlsx files found in folder: {file_or_folder_path}")
            return
        print(f"📁 Found {len(xlsx_files)} xlsx file(s) in folder:")
        for f in xlsx_files:
            print(f"   - {f.name}")
    else:
        print(f"❌ Path is neither a file nor a directory: {file_or_folder_path}")
        return
    
    # Read all Excel files and combine them
    all_dataframes = []
    
    for xlsx_file in xlsx_files:
        try:
            print(f"📖 Reading: {xlsx_file.name}")
            df = pd.read_excel(xlsx_file)
            
            # Check if required columns exist
            if 'Brand' not in df.columns:
                print(f"⚠️  Warning: Column 'Brand' not found in {xlsx_file.name}, skipping...")
                print(f"   Available columns: {list(df.columns)}")
                continue
            
            if 'Duration' not in df.columns:
                print(f"⚠️  Warning: Column 'Duration' not found in {xlsx_file.name}, skipping...")
                print(f"   Available columns: {list(df.columns)}")
                continue
            
            all_dataframes.append(df)
        except Exception as e:
            print(f"⚠️  Error reading {xlsx_file.name}: {e}")
            continue
    
    if not all_dataframes:
        print("❌ No valid data found in any xlsx files")
        return
    
    # Combine all dataframes
    combined_df = pd.concat(all_dataframes, ignore_index=True)
    
    # Convert Duration to numeric (in case it's a string)
    combined_df['Duration'] = pd.to_numeric(combined_df['Duration'], errors='coerce')
    
    # Group by Brand and sum Duration
    summary = combined_df.groupby('Brand')['Duration'].sum().reset_index()
    summary = summary.sort_values('Duration', ascending=False)
    
    # Print results
    print("\n" + "="*60)
    print("📊 TOTAL DURATION BY BRAND (COMBINED)")
    print("="*60)
    
    grand_total = summary['Duration'].sum()
    
    for _, row in summary.iterrows():
        brand = str(row['Brand'])
        duration = int(row['Duration']) if pd.notna(row['Duration']) else 0
        print(f"Brand: {brand:40} Duration: {duration:>10}")
    
    print("="*60)
    print(f"TOTAL DURATION (all brands): {int(grand_total):>10}")
    print("="*60 + "\n")

def main():
    if len(sys.argv) < 2:
        # If no path provided, search for xlsx files in the current folder
        folder = Path(__file__).parent
        xlsx_files = list(folder.glob("*.xlsx"))
        
        if not xlsx_files:
            print("❌ No xlsx file found in current folder")
            print("\nUsage: python brand_duration_summary.py <path_to_xlsx_file_or_folder>")
            print("       Can accept either a single xlsx file or a folder containing xlsx files")
            sys.exit(1)
        
        if len(xlsx_files) == 1:
            file_path = xlsx_files[0]
            print(f"📁 Found one xlsx file: {file_path.name}")
            calculate_brand_durations(file_path)
        else:
            # Multiple files found - process the folder
            print(f"📁 Found {len(xlsx_files)} xlsx files in current folder, processing all...")
            calculate_brand_durations(folder)
    else:
        path = sys.argv[1]
        calculate_brand_durations(path)

if __name__ == "__main__":
    main()
