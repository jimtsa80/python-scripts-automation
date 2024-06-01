import sys
import pandas as pd
import random

def create_sets(input_file_path, output_file_path):
    # Read the Excel file
    df = pd.read_excel(input_file_path)

    # Check if the necessary columns are present
    if 'Hash' not in df.columns or 'Image Name' not in df.columns:
        print("The Excel file must contain 'hash' and 'entries' columns.")
        return

    # Group by the hash values
    grouped = df.groupby('Hash')['Image Name'].apply(list).reset_index()

    # Initialize lists for storing the sets
    sets = []

    for _, row in grouped.iterrows():
        hash_value = row['Hash']
        entries = row['Image Name']

        # Split entries into WRC and non-WRC lists
        wrc_entries = [entry for entry in entries if entry.startswith('WRC')]
        non_wrc_entries = [entry for entry in entries if not entry.startswith('WRC')]

        # Ensure there is at least one entry in both lists
        if not wrc_entries:
            wrc_entries = random.choices(entries, k=1)
        if not non_wrc_entries:
            non_wrc_entries = random.choices(entries, k=1)

        # Create sets
        max_len = max(len(wrc_entries), len(non_wrc_entries))
        for i in range(max_len):
            wrc_entry = wrc_entries[i % len(wrc_entries)]
            non_wrc_entry = non_wrc_entries[i % len(non_wrc_entries)]
            sets.append((hash_value, wrc_entry, non_wrc_entry))

    # Convert the result to a DataFrame
    result_df = pd.DataFrame(sets, columns=['Hash', 'WRC_entry', 'non_WRC_entry'])

    # Save the result to a new Excel file
    result_df.to_excel(output_file_path, index=False)
    print(f"Sets have been created and saved to {output_file_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <path_to_input_excel_file> <path_to_output_excel_file>")
    else:
        input_file_path = sys.argv[1]
        output_file_path = sys.argv[2]
        create_sets(input_file_path, output_file_path)
