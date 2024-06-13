import pandas as pd
import sys

def remove_leading_zeros_and_extension(filename):
    stripped = filename.lstrip('0').replace('.jpg', '')
    return int(stripped) if stripped else 0

def main(file1, file2, output_file):
    # Load the data from the Excel files
    df1 = pd.read_excel(file1)
    df2 = pd.read_excel(file2)

    # Process the 'First Image' column
    df1['Processed Image'] = df1['First Image'].apply(remove_leading_zeros_and_extension)

    # Ensure 'Sequence Frame Number' is of integer type
    df2['Sequence Frame Number'] = df2['Sequence Frame Number'].astype(int)

    # Merge the dataframes on the processed image number and the 'Sequence Frame Number' column
    merged_df = pd.merge(df1, df2, how='inner', left_on='Processed Image', right_on='Sequence Frame Number')

    # Create a new dataframe with the required columns
    result_df = merged_df[['Number of Images', 'Brand', 'Location', 'Duration', 'Sequence Frame Number']]

    # Save the result to a new Excel file
    result_df.to_excel(output_file, index=False)
    print(f"New Excel file created: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python script.py <file1> <file2> <output_file>")
    else:
        file1 = sys.argv[1]
        file2 = sys.argv[2]
        output_file = sys.argv[3]
        main(file1, file2, output_file)
