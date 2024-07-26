import sys
import re
import os
import pandas as pd

def extract_brands_from_txt(file_path):
    brands = set()
    with open(file_path, 'r') as file:
        content = file.read()
        # Find all words starting with #
        brands = set(re.findall(r'#(\w+)', content))
    return brands

def filter_brands_by_duration(brands, folder_path, threshold):
    # Initialize an empty DataFrame to hold the combined data
    combined_df = pd.DataFrame()

    # Read all Excel files in the specified folder
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.xlsx'):
            file_path = os.path.join(folder_path, file_name)
            df = pd.read_excel(file_path)
            combined_df = pd.concat([combined_df, df], ignore_index=True)

    # Ensure the necessary columns exist
    if 'Brand' not in combined_df.columns or 'Duration' not in combined_df.columns:
        raise ValueError("Excel files must contain 'Brand' and 'Duration' columns")
    
    # Filter the dataframe for rows where brand is in the list of brands
    filtered_df = combined_df[combined_df['Brand'].isin(brands)]
    
    # Sum the durations for each brand
    brand_durations = filtered_df.groupby('Brand')['Duration'].sum()
    
    # Filter the brands by the given threshold
    brands_below_threshold = brand_durations[brand_durations < threshold]
    
    return brands_below_threshold, set(brand_durations.index)

def main():
    if len(sys.argv) != 4:
        print("Usage: python script.py <txt_file_path> <folder_path> <threshold>")
        sys.exit(1)
    
    txt_file_path = sys.argv[1]
    folder_path = sys.argv[2]
    threshold = float(sys.argv[3])

    # Extract brands from the text file
    brands = extract_brands_from_txt(txt_file_path)
    
    # Filter brands by duration from the Excel files in the folder
    brands_below_threshold, brands_in_excel = filter_brands_by_duration(brands, folder_path, threshold)
    
    # Brands in txt but not in results below threshold
    brands_not_in_result = brands - brands_in_excel
    
    # Output the result
    if not brands_below_threshold.empty:
        print("Brands with total duration less than {}:".format(threshold))
        print(brands_below_threshold)
    else:
        print("No brands found with total duration less than {}".format(threshold))

    if brands_not_in_result:
        print("\nBrands found in txt file but not present in the Excel files:")
        for brand in brands_not_in_result:
            print(brand)

if __name__ == "__main__":
    main()

