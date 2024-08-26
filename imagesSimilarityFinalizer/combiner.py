import sys
import pandas as pd

def process_files(file1, file2):
    # Read the first Excel file
    df1 = pd.read_excel(file1)
    
    # Read the second Excel file
    df2 = pd.read_excel(file2)

    # List to store the updated line numbers
    updated_lines = []

    # Process each row in df1
    for index, row in df1.iterrows():
        # Extract the first column value, removing leading zeros and the ".jpg" suffix
        first_image_number = int(row['First Image'].split('.')[0])

        # Check if there is a matching Sequence Frame Number in df2
        match = df2[df2['Sequence Frame Number'] == first_image_number]
        
        if not match.empty:
            # Update the Duration column
            df2.loc[df2['Sequence Frame Number'] == first_image_number, 'Duration'] += row['Number of Images']
            
            # Update the Total Hits column
            df2.loc[df2['Sequence Frame Number'] == first_image_number, 'Total Hits'] += row['Number of Images']
            
            # Record the line number
            updated_lines.append(index + 1)

    # Save the updated df2 back to the second Excel file
    df2.to_excel(file2, index=False)

    # Print the updated line numbers
    print(f"Updated lines: {len(updated_lines)}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: script.py <first_excel_file> <second_excel_file>")
    else:
        file1 = sys.argv[1]
        file2 = sys.argv[2]
        process_files(file1, file2)
