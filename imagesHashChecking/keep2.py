import sys
import pandas as pd

def find_and_remove_duplicates(input_file):
    # Read the Excel file
    df = pd.read_excel(input_file)
    
    # Check if the required columns are present
    if df.shape[1] < 2:
        print("The input file must have at least two columns.")
        return
    
    # Get the first two columns
    first_col = df.columns[0]
    second_col = df.columns[1]

    # Find duplicate hashes in the second column
    duplicates = df[df.duplicated([second_col], keep=False)]

    # Create a new DataFrame with the entries from both columns
    result_df = duplicates[[first_col, second_col]]

    # Remove the duplicate rows from the original DataFrame
    df_cleaned = df.drop(duplicates.index)

    # Load the workbook to check for existing sheets
    with pd.ExcelWriter(input_file, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        # Write the duplicates DataFrame to a new sheet named 'Duplicates'
        result_df.to_excel(writer, sheet_name='Duplicates', index=False)
        # Overwrite the original sheet with cleaned data
        df_cleaned.to_excel(writer, sheet_name=writer.book.sheetnames[0], index=False)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <input_file.xlsx>")
    else:
        input_file = sys.argv[1]
        find_and_remove_duplicates(input_file)
