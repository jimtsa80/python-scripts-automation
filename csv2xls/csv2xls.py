import os
import pandas as pd
from fuzzywuzzy import fuzz
from collections import defaultdict
import sys
import json
from datetime import datetime

class SkipRemaining(Exception):
    """Exception to skip remaining typos and continue"""
    pass

def get_skipped_typos_file():
    """Get path to skipped typos file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "skipped_typos.json")

def load_skipped_typos():
    """Load skipped typos from file"""
    skipped_file = get_skipped_typos_file()
    if os.path.exists(skipped_file):
        try:
            with open(skipped_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load skipped typos: {e}")
            return {}
    return {}

def save_skipped_typo(column_name, val1, val2):
    """Save a skipped typo to file"""
    skipped_file = get_skipped_typos_file()
    skipped_typos = load_skipped_typos()
    
    # Create normalized pair (always same order)
    pair = tuple(sorted([val1, val2]))
    key = f"{column_name}:{pair[0]}:{pair[1]}"
    
    if key not in skipped_typos:
        skipped_typos[key] = {
            'column': column_name,
            'value1': pair[0],
            'value2': pair[1],
            'skipped_at': datetime.now().isoformat()
        }
        
        try:
            with open(skipped_file, 'w', encoding='utf-8') as f:
                json.dump(skipped_typos, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save skipped typo: {e}")

def is_skipped(column_name, val1, val2):
    """Check if a typo pair has been skipped before"""
    skipped_typos = load_skipped_typos()
    pair = tuple(sorted([val1, val2]))
    key = f"{column_name}:{pair[0]}:{pair[1]}"
    return key in skipped_typos

def find_and_fix_misspellings(df, csv_filename, column_name):
    """Find and interactively fix misspellings in a column"""
    if column_name not in df.columns:
        return df, []
    
    values = df[column_name].astype(str).unique()
    corrections = []
    processed_pairs = set()
    
    try:
        # Check for typos
        for val1 in values:
            for val2 in values:
                if val1 != val2:
                    # Use multiple similarity checks
                    similarity_scores = {
                        'ratio': fuzz.ratio(val1, val2),
                        'partial_ratio': fuzz.partial_ratio(val1, val2),
                        'token_sort_ratio': fuzz.token_sort_ratio(val1, val2),
                        'token_set_ratio': fuzz.token_set_ratio(val1, val2),
                        'partial_token_sort_ratio': fuzz.partial_token_sort_ratio(val1, val2)
                    }
                    max_similarity = max(similarity_scores.values())
                    
                    # Only report typos with 90% <= similarity < 99.9% (exclude perfect matches)
                    if 90 <= max_similarity < 99.9:
                        pair = (val1, val2) if val1 < val2 else (val2, val1)
                        if pair not in processed_pairs:
                            processed_pairs.add(pair)
                            
                            # Check if this typo was skipped before
                            if is_skipped(column_name, val1, val2):
                                print(f"\n  ⊘ Skipping (previously skipped): '{val1}' vs '{val2}' (similarity: {max_similarity:.1f}%)")
                                continue
                            
                            print(f"\n  Detected typo in {column_name}: '{val1}' vs '{val2}' (similarity: {max_similarity:.1f}%)")
                            
                            # Ask user which one to keep
                            while True:
                                choice = input(f"  Which one to keep? [1] '{val1}' [2] '{val2}' [s]kip [e]scape (skip remaining): ").strip().lower()
                                if choice == '1':
                                    # Replace val2 with val1 - use exact match with boolean indexing
                                    mask = df[column_name].astype(str).str.strip() == str(val2).strip()
                                    count = mask.sum()
                                    df.loc[mask, column_name] = val1
                                    corrections.append((val2, val1, max_similarity))
                                    print(f"  ✓ Replaced '{val2}' with '{val1}' ({count} occurrences)")
                                    break
                                elif choice == '2':
                                    # Replace val1 with val2 - use exact match with boolean indexing
                                    mask = df[column_name].astype(str).str.strip() == str(val1).strip()
                                    count = mask.sum()
                                    df.loc[mask, column_name] = val2
                                    corrections.append((val1, val2, max_similarity))
                                    print(f"  ✓ Replaced '{val1}' with '{val2}' ({count} occurrences)")
                                    break
                                elif choice == 's' or choice == 'skip':
                                    # Save skipped typo
                                    save_skipped_typo(column_name, val1, val2)
                                    print(f"  ⊘ Skipped (will remember this)")
                                    break
                                elif choice == 'e' or choice == 'escape':
                                    print(f"  ⊘ Escaping - skipping remaining typos in {column_name}")
                                    raise SkipRemaining
                                else:
                                    print("  Invalid choice. Please enter 1, 2, s, or e")
    except SkipRemaining:
        pass
    
    return df, corrections

def find_misspellings(df, csv_filename):
    """Find and interactively fix misspellings in Brand and Location columns"""
    if 'Brand' not in df.columns or 'Location' not in df.columns:
        return df, []
    
    corrections = []
    
    # Fix brands
    if 'Brand' in df.columns:
        print(f"\nChecking Brands in {csv_filename}:")
        df, brand_corrections = find_and_fix_misspellings(df, csv_filename, 'Brand')
        corrections.extend(brand_corrections)
    
    # Fix locations
    if 'Location' in df.columns:
        print(f"\nChecking Locations in {csv_filename}:")
        df, location_corrections = find_and_fix_misspellings(df, csv_filename, 'Location')
        corrections.extend(location_corrections)
    
    return df, corrections

def csv_to_xlsx(input_folder, output_folder):
    files = os.listdir(input_folder)
    part_files_dict = defaultdict(list)
    other_files = []

    # Group "part" files by base filename and separate others
    for file in files:
        if file.endswith('.csv'):
            if file.startswith("part"):
                base_filename = file.replace("reduced_", "").split('-')[0].replace("part", "").split("_", 1)[1]
                part_files_dict[base_filename].append(file)
            else:
                other_files.append(file)

    # Process "part" files
    for base_filename, part_files in part_files_dict.items():
        # Sort part files to ensure correct order (part1, part2, part3, etc.)
        part_files.sort()
        
        dfs = []
        csv_filenames = []

        for file in part_files:
            file_path = os.path.join(input_folder, file)
            try:
                df = pd.read_csv(file_path, delimiter='\t')
            except pd.errors.ParserError as e:
                print(f"Error reading {file_path}: {e}")
                continue

            # Sanitize all string columns: strip whitespace (spaces, tabs, newlines)
            str_cols = df.select_dtypes(include=["object"]).columns
            if len(str_cols) > 0:
                df[str_cols] = df[str_cols].apply(lambda col: col.astype(str).str.strip())

            required_columns = {'Brand', 'Location'}
            missing_columns = required_columns - set(df.columns)
            if missing_columns:
                raise ValueError(f"Missing columns {missing_columns} in file: {file_path}")

            empty_rows = df[df['Brand'].isnull() | df['Location'].isnull()]
            if not empty_rows.empty:
                print(f"Empty rows found in {file}:")
                print(empty_rows)
                df = df.drop(empty_rows.index)

            dfs.append(df)
            csv_filenames.append(file)

        if dfs:
            # Check if all DataFrames have the same columns before concatenation
            if len(dfs) > 1:
                first_columns = set(dfs[0].columns)
                for i, df in enumerate(dfs[1:], 1):
                    if set(df.columns) != first_columns:
                        print(f"Warning: DataFrame {csv_filenames[i]} has different columns than {csv_filenames[0]}")
                        print(f"  Expected: {sorted(first_columns)}")
                        print(f"  Found: {sorted(df.columns)}")
            
            combined_df = pd.concat(dfs, ignore_index=True)
            
            # Safe sorting with error handling
            # Use Sequence Frame Number as primary sort key if available, otherwise use last column
            # IMPORTANT: Do NOT use Brand/Location as secondary keys as they can change the order
            # of rows with the same frame number (e.g., "Luzhou Laojiao" vs "Rolex")
            try:
                if 'Sequence Frame Number' in combined_df.columns:
                    # Use Sequence Frame Number as primary sort key
                    sort_by = ['Sequence Frame Number']
                    # Add the last column as secondary only if it's different from Sequence Frame Number
                    last_column = combined_df.columns[-1]
                    if last_column != 'Sequence Frame Number':
                        sort_by.append(last_column)
                else:
                    # Fallback to last column if Sequence Frame Number doesn't exist
                    sort_column = combined_df.columns[-1]
                    sort_by = [sort_column]
                
                # Use kind='stable' to preserve order of rows with equal values
                combined_df.sort_values(by=sort_by, inplace=True, kind='stable')
            except (TypeError, KeyError) as e:
                print(f"Warning: Could not sort {base_filename} by columns {sort_by} due to error: {e}")
                # Fallback: try sorting by just Sequence Frame Number or last column
                try:
                    if 'Sequence Frame Number' in combined_df.columns:
                        combined_df.sort_values(by='Sequence Frame Number', inplace=True, kind='stable')
                    else:
                        sort_column = combined_df.columns[-1]
                        combined_df.sort_values(by=sort_column, inplace=True, kind='stable')
                except Exception as e2:
                    print(f"Warning: Could not sort {base_filename}: {e2}")

            combined_df, corrections = find_misspellings(combined_df, f"{base_filename} (concatenated)")
            if corrections:
                print(f"\n✓ Applied {len(corrections)} corrections to concatenated file {base_filename}")

            output_file = os.path.join(output_folder, f"{base_filename}.xlsx")
            combined_df.to_excel(output_file, index=False)
            print(f"Processed and concatenated part files into: {base_filename}.xlsx")

    # Process individual files
    for file in other_files:
        file_path = os.path.join(input_folder, file)
        try:
            df = pd.read_csv(file_path, delimiter='\t')
        except pd.errors.ParserError as e:
            print(f"Error reading {file_path}: {e}")
            continue

        # Sanitize all string columns: strip whitespace (spaces, tabs, newlines)
        str_cols = df.select_dtypes(include=["object"]).columns
        if len(str_cols) > 0:
            df[str_cols] = df[str_cols].apply(lambda col: col.astype(str).str.strip())

        required_columns = {'Brand', 'Location'}
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing columns {missing_columns} in file: {file_path}")

        empty_rows = df[df['Brand'].isnull() | df['Location'].isnull()]
        if not empty_rows.empty:
            print(f"Empty rows found in {file}:")
            print(empty_rows)
            df = df.drop(empty_rows.index)

        df, corrections = find_misspellings(df, file)
        if corrections:
            print(f"\n✓ Applied {len(corrections)} corrections to file {file}")

        cleaned_filename = file.replace("reduced_", "").split('-')[0]
        output_file = os.path.join(output_folder, f"{cleaned_filename}.xlsx")
        df.to_excel(output_file, index=False)
        print(f"Processed individual file: {cleaned_filename}.xlsx")

if __name__ == "__main__":
    csv_to_xlsx("csvs", ".")
