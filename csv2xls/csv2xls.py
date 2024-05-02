import os
import pandas as pd
from fuzzywuzzy import fuzz

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
    unique_filenames = set()

    for file in files:
        if file.endswith('.csv'):
            filename_parts = file.split('-')
            base_filename = filename_parts[0]
            unique_filenames.add(base_filename)

    for filename in unique_filenames:
        dfs = []
        csv_filename = None  
        for file in files:
            if file.startswith(filename) and file.endswith('.csv'):
                csv_filename = file  
                file_path = os.path.join(input_folder, file)
                df = pd.read_csv(file_path, delimiter='\t')
                dfs.append(df)

        if dfs:
            combined_df = pd.concat(dfs, ignore_index=True)
            combined_df.sort_values(by=combined_df.columns[-1], inplace=True)
            misspellings = find_misspellings(combined_df, csv_filename)
            if misspellings:
                print("Misspellings found in:", csv_filename)
                for misspelling in misspellings:
                    print("Misspelling:", misspelling)
                print()

            output_file = os.path.join(output_folder, f"{filename}.xlsx")
            combined_df.to_excel(output_file, index=False)

if __name__ == "__main__":

    csv_to_xlsx("csv", ".")

