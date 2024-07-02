import sys
import pandas as pd

def process_files(file1, file2):
    # Read the first Excel file
    print(f"Reading the first Excel file: {file1}")
    df1 = pd.read_excel(file1)
    
    # Read the second Excel file
    print(f"Reading the second Excel file: {file2}")
    df2 = pd.read_excel(file2)

    # Process each row in df1
    for index, row in df1.iterrows():
        # Extract the first column value, removing leading zeros and the ".jpg" suffix
        first_image_number = int(row['First Image'].split('.')[0])
        print(f"Processing First Image: {row['First Image']} (Converted to {first_image_number})")

        # Check if there is a matching Sequence Frame Number in df2
        match = df2[df2['Sequence Frame Number'] == first_image_number]
        
        if not match.empty:
            print(f"Match found for Sequence Frame Number: {first_image_number}")
            original_duration = df2.loc[df2['Sequence Frame Number'] == first_image_number, 'Duration'].values[0]
            print(f"Original Duration: {original_duration}")
            df2.loc[df2['Sequence Frame Number'] == first_image_number, 'Duration'] += row['Number of Images']
            updated_duration = df2.loc[df2['Sequence Frame Number'] == first_image_number, 'Duration'].values[0]
            print(f"Updated Duration: {updated_duration}")
        else:
            print(f"No match found for Sequence Frame Number: {first_image_number}")

    # Save the updated df2 back to the second Excel file
    print(f"Saving the updated second Excel file: {file2}")
    df2.to_excel(file2, index=False)
    print("Process completed successfully.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: script.py <first_excel_file> <second_excel_file>")
    else:
        file1 = sys.argv[1]
        file2 = sys.argv[2]
        process_files(file1, file2)
