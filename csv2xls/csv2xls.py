import os
import pandas as pd
from fuzzywuzzy import fuzz
from collections import defaultdict

def find_misspellings(df, csv_filename):
    brand_names = df['Brand'].astype(str).unique()
    location_names = df['Location'].astype(str).unique()
    misspellings = set()

    for brand1 in brand_names:
        for brand2 in brand_names:
            if brand1 != brand2 and fuzz.partial_token_sort_ratio(brand1, brand2) > 99:
                pair = (brand1, brand2) if brand1 < brand2 else (brand2, brand1)
                misspellings.add((csv_filename, pair))

    for location1 in location_names:
        for location2 in location_names:
            if location1 != location2 and fuzz.partial_token_sort_ratio(location1, location2) > 99:
                pair = (location1, location2) if location1 < location2 else (location2, location1)
                misspellings.add((csv_filename, pair))

    return misspellings

def csv_to_xlsx(input_folder, output_folder):
    files = os.listdir(input_folder)
    part_files_dict = defaultdict(list)
    other_files = []

    # Group "part" files by their base filename and separate other files
    for file in files:
        if file.endswith('.csv'):
            if file.startswith("part"):
                # Extract the base filename (ignoring "part", the number, and "reduced")
                base_filename = file.replace("reduced_", "").split('-')[0].replace("part", "").split("_", 1)[1]
                part_files_dict[base_filename].append(file)
            else:
                other_files.append(file)

    # Process "part" files: concatenate files with the same base filename
    for base_filename, part_files in part_files_dict.items():
        dfs = []
        csv_filenames = []  # For tracking files used for misspellings check

        for file in part_files:
            file_path = os.path.join(input_folder, file)
            df = pd.read_csv(file_path, delimiter='\t')
            
            # Check for empty values and remove rows with missing "Brand" or "Location"
            empty_rows = df[df['Brand'].isnull() | df['Location'].isnull()]
            if not empty_rows.empty:
                print(f"Empty rows found in {file}:")
                print(empty_rows)
                df = df.drop(empty_rows.index)

            dfs.append(df)
            csv_filenames.append(file)  # Add file to the misspellings check list

        if dfs:
            # Concatenate all DataFrames for files with the same base filename
            combined_df = pd.concat(dfs, ignore_index=True)
            combined_df.sort_values(by=combined_df.columns[-1], inplace=True)

            # Run misspellings detection
            misspellings = find_misspellings(combined_df, tuple(csv_filenames))
            if misspellings:
                print(f"Misspellings found in concatenated file {base_filename}:")
                for misspelling in misspellings:
                    print("Misspelling:", misspelling)

            # Ensure the base_filename does not contain "reduced"
            base_filename = base_filename.replace("reduced_", "")

            # Save the combined DataFrame to a single XLSX file
            output_file = os.path.join(output_folder, f"{base_filename}.xlsx")
            combined_df.to_excel(output_file, index=False)
            print(f"Processed and concatenated part files into: {base_filename}.xlsx")

    # Process other files (non-part files) individually
    for file in other_files:
        file_path = os.path.join(input_folder, file)
        df = pd.read_csv(file_path, delimiter='\t')

        # Remove empty rows
        empty_rows = df[df['Brand'].isnull() | df['Location'].isnull()]
        if not empty_rows.empty:
            print(f"Empty rows found in {file}:")
            print(empty_rows)
            df = df.drop(empty_rows.index)

        # Run misspellings detection on individual files
        misspellings = find_misspellings(df, file)
        if misspellings:
            print(f"Misspellings found in file {file}:")
            for misspelling in misspellings:
                print("Misspelling:", misspelling)

        # Generate output filename (portion before the hyphen '-') and remove "reduced"
        cleaned_filename = file.replace("reduced_", "").split('-')[0]
        output_file = os.path.join(output_folder, f"{cleaned_filename}.xlsx")

        # Save individual DataFrame to XLSX
        df.to_excel(output_file, index=False)
        print(f"Processed individual file: {cleaned_filename}.xlsx")

if __name__ == "__main__":
    csv_to_xlsx("csvs", ".")
