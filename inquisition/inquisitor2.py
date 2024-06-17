import sys
import re
import pandas as pd

def extract_brands_from_txt(file_path):
    brands = set()
    with open(file_path, 'r') as file:
        content = file.read()
        # Find all words starting with #
        brands = set(re.findall(r'#(\w+)', content))
    return brands

def filter_brands_by_duration(brands, excel_file_path, threshold):
    # Read the Excel file
    df = pd.read_excel(excel_file_path)
    # Ensure the necessary columns exist
    if 'Brand' not in df.columns or 'Duration' not in df.columns:
        raise ValueError("Excel file must contain 'Brand' and 'Duration' columns")
    
    # Filter the dataframe for rows where brand is in the list of brands
    filtered_df = df[df['Brand'].isin(brands)]
    
    # Sum the durations for each brand
    brand_durations = filtered_df.groupby('Brand')['Duration'].sum()
    
    # Filter the brands by the given threshold
    brands_below_threshold = brand_durations[brand_durations < threshold]
    
    return brands_below_threshold

def main():
    if len(sys.argv) != 4:
        print("Usage: python script.py <txt_file_path> <excel_file_path> <threshold>")
        sys.exit(1)
    
    txt_file_path = sys.argv[1]
    excel_file_path = sys.argv[2]
    threshold = float(sys.argv[3])

    # Extract brands from the text file
    brands = extract_brands_from_txt(txt_file_path)
    
    # Filter brands by duration from the Excel file
    brands_below_threshold = filter_brands_by_duration(brands, excel_file_path, threshold)
    
    # Output the result
    if not brands_below_threshold.empty:
        print("Brands with total duration less than {}:".format(threshold))
        print(brands_below_threshold)
    else:
        print("No brands found with total duration less than {}".format(threshold))

if __name__ == "__main__":
    main()
