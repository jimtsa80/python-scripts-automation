import sys
import pandas as pd
import re

def process_files_numeric(file1, file2):
    # Read the first Excel file
    df1 = pd.read_excel(file1)
    
    # Read the second Excel file
    df2 = pd.read_excel(file2)

    # List to store the updated line numbers
    updated_lines = []

    # Ensure that 'Sequence Frame Number' in df2 is treated as a string and strip leading zeros
    df2['Sequence Frame Number'] = df2['Sequence Frame Number'].astype(str).str.lstrip('0')

    # Process each row in df1
    for index, row in df1.iterrows():
        try:
            # Extract the numeric part from 'First Image' column and strip leading zeros
            first_image_number = re.search(r"(\d+)", row['First Image']).group(1).lstrip('0')
        except AttributeError:
            print(f"Error processing {row['First Image']}. Skipping.")
            continue

        # Find matching Sequence Frame Number in df2
        match = df2[df2['Sequence Frame Number'] == first_image_number]
        
        if not match.empty:
            # Update Duration and Total Hits
            df2.loc[df2['Sequence Frame Number'] == first_image_number, 'Duration'] += row['Number of Images']
            df2.loc[df2['Sequence Frame Number'] == first_image_number, 'Total Hits'] += row['Number of Images']
            
            # Record the line number
            updated_lines.append(index + 1)
        # else:
        #     print(f"No match found for First Image: {row['First Image']}")

    # Save the updated df2 back to the second Excel file
    df2.to_excel(file2, index=False)

    # Print the updated line numbers
    print(f"Updated lines (Numeric): {len(updated_lines)}")


def process_files_prefix(file1, file2):
    # Read the first Excel file
    df1 = pd.read_excel(file1)
    
    # Read the second Excel file
    df2 = pd.read_excel(file2)

    # List to store the updated line numbers
    updated_lines = []

    # Regular expression pattern to extract the identifier and number
    pattern_full = r"(.+_\d+)\.jpg$"

    # Function to update Duration and Total Hits for matched rows
    def update_matching_rows(df2, match_indices, num_images):
        df2.loc[match_indices, 'Duration'] += num_images
        df2.loc[match_indices, 'Total Hits'] += num_images

    # Process each row in df1
    for index, row in df1.iterrows():
        match_full = re.search(pattern_full, row['First Image'])
        if match_full:
            full_identifier = match_full.group(1)
            
            # Match Sequence Frame Number in df2 using the full identifier
            full_matches = df2[df2['Sequence Frame Number'].str.contains(f"^{full_identifier}$")]
            if not full_matches.empty:
                print(f"Match found in df2 for Full Identifier: {full_identifier}")
                
                # Update Duration and Total Hits
                update_matching_rows(df2, full_matches.index, row['Number of Images'])
                updated_lines.append(index + 1)
            else:
                print(f"No match found in df2 for Full Identifier: {full_identifier}")

    # Save the updated df2 back to the second Excel file
    df2.to_excel(file2, index=False)

    # Print the updated line numbers
    print(f"\nUpdated lines (Prefix): {len(updated_lines)}")

def determine_and_process(file1, file2):
    # Check the format of the filenames in the first row of df1 to determine the script to use
    df1 = pd.read_excel(file1)
    first_image = df1.iloc[0]['First Image']
    
    # Determine if the filename is purely numeric or has a prefix
    if re.match(r"^\d+\.jpg$", first_image):
        print("Numeric filenames detected. Using numeric matching.")
        process_files_numeric(file1, file2)
    else:
        print("Prefix-based filenames detected. Using prefix matching.")
        process_files_prefix(file1, file2)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: script.py <first_excel_file> <second_excel_file>")
    else:
        file1 = sys.argv[1]
        file2 = sys.argv[2]
        determine_and_process(file1, file2)
