import sys
import pandas as pd
import re

def process_files_numeric(file1, file2):
    print("\nStarting numeric processing...")

    # Read the first Excel file
    print(f"Reading data from {file1}...")
    df1 = pd.read_excel(file1)

    # Read the second Excel file
    print(f"Reading data from {file2}...")
    df2 = pd.read_excel(file2)

    # List to store the updated line numbers
    updated_lines = []

    # Ensure that 'Sequence Frame Number' in df2 is treated as a string and strip leading zeros
    print("Cleaning up 'Sequence Frame Number' column in df2...")
    df2['Sequence Frame Number'] = df2['Sequence Frame Number'].astype(str).str.lstrip('0').str.strip()

    # Process each row in df1
    for index, row in df1.iterrows():
        try:
            # Extract the numeric part from 'First Image' column and strip leading zeros
            first_image_number = re.search(r"(\d+)", row['First Image']).group(1).lstrip('0')
        except AttributeError:
            print(f"Error processing 'First Image': {row['First Image']}. Skipping row.")
            continue

        # Find matching Sequence Frame Number in df2
        match = df2[df2['Sequence Frame Number'] == first_image_number]
        if not match.empty:
            #print(f"Match found in df2 for 'Sequence Frame Number': {first_image_number}")
            # Update Duration and Total Hits
            #df2.loc[df2['Sequence Frame Number'] == first_image_number, 'Duration'] += row['Number of Images'] - 2
            df2.loc[df2['Sequence Frame Number'] == first_image_number, 'Duration'] += row['Number of Images'] - 1
            updated_lines.append(index + 1)

    # Save the updated df2 back to the second Excel file
    print(f"\nSaving updated data to {file2}...")
    df2.to_excel(file2, index=False)
    print(f"Numeric processing complete. Updated lines: {updated_lines}")


def process_files_prefix(file1, file2):
    print("\nStarting prefix processing...")

    # Read the first Excel file
    print(f"Reading data from {file1}...")
    df1 = pd.read_excel(file1)

    # Read the second Excel file
    print(f"Reading data from {file2}...")
    df2 = pd.read_excel(file2)

    # List to store the updated line numbers
    updated_lines = []

    # Regular expression pattern to extract the identifier
    pattern_full = r"(.+_\d+)(?:\.jpg|\.jpeg)?$"
    #pattern_full = r"^(.+?_\d{2}-\d{2}-\d{4}_\d{2}_\d{2}_\d{2}_\d+)(?:\.jpg|\.jpeg)?$"


    # Ensure both columns are treated as strings and remove any leading/trailing spaces
    df1['First Image'] = df1['First Image'].astype(str).str.strip()
    df2['Sequence Frame Number'] = df2['Sequence Frame Number'].astype(str).str.strip()

    # Function to update Duration and Total Hits for matched rows
    def update_matching_rows(df2, match_indices, num_images):
        print(f"Updating rows in df2 for indices: {list(match_indices)} with Number of Images: {num_images}")
        df2.loc[match_indices, 'Duration'] += num_images - 1
        # df2.loc[match_indices, 'Total Hits'] += num_images - 1
        # df2.loc[match_indices, 'Average Hits'] = (
        #     df2.loc[match_indices, 'Total Hits'] / df2.loc[match_indices, 'Duration']
        # ).apply(lambda x: round(x, 3) if x % 1 != 0 else x)

    # Process each row in df1
    for index, row in df1.iterrows():
        #print(f"\nProcessing row {index + 1} in df1: {row}")
        #print(pattern_full)
        match_full = re.search(pattern_full, row['First Image'])
        if match_full:
            full_identifier = match_full.group(1)
            #print(f"Extracted full identifier from 'First Image': {full_identifier}")

            # DEBUG: Print unique values from df2['Sequence Frame Number']
            # print("\nDEBUG: Checking values in df2['Sequence Frame Number']")
            # for val in df2['Sequence Frame Number'].unique():
            #     print(f"df2 contains: [{val}] (length: {len(val)})")
            # print(f"Looking for: [{full_identifier}] (length: {len(full_identifier)})\n")

            # Match Sequence Frame Number in df2 using the full identifier
            full_matches = df2[df2['Sequence Frame Number'].astype(str).str.fullmatch(re.escape(full_identifier))]

            if not full_matches.empty:
                print(f"Match found in df2 for Full Identifier: {full_identifier}")
                update_matching_rows(df2, full_matches.index, row['Number of Images'])
                updated_lines.append(index + 1)
            #else:
                #print(f"No match found in df2 for Full Identifier: {full_identifier}")

    # Save the updated df2 back to the second Excel file
    print(f"\nSaving updated data to {file2}...")
    df2.to_excel(file2, index=False)
    print(f"Prefix processing complete. Updated lines: {updated_lines}")


def determine_and_process(file1, file2):
    print("\nDetermining filename format...")

    # Check the format of the filenames in the first row of df1 to determine the script to use
    df1 = pd.read_excel(file1)
    first_image = df1.iloc[0]['First Image']
    #print(f"First 'First Image' entry: {first_image}")

    # Determine if the filename is purely numeric or has a prefix
    if re.match(r"^\d+\.(jpg|jpeg)$", first_image):
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
        print(f"\nStarting script with files:\n  File1: {file1}\n  File2: {file2}")
        determine_and_process(file1, file2)
