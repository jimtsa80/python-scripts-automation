import pandas as pd
import sys

def filter_last_entries_and_update_sequence(input_file, check_file):
    # Load the initial Excel file
    df = pd.read_excel(input_file)
    
    # Extract the base sequence ID (up to the last underscore) to create groups
    df['Base Sequence'] = df['Sequence Frame Number'].str.rsplit(pat='_', n=1).str[0]
    
    # Sort by 'Sequence Frame Number' to ensure the latest entries are last
    df_sorted = df.sort_values(by='Sequence Frame Number')
    
    # Keep only the last entry in each 'Base Sequence' group
    df_last_entries = df_sorted.drop_duplicates(subset='Base Sequence', keep='last').copy()
    
    # Update the Sequence Frame Number by adding the Duration to the last part
    def update_sequence(row):
        base_sequence = row['Base Sequence']
        sequence_number = int(row['Sequence Frame Number'].rsplit('_', 1)[-1])
        new_sequence_number = sequence_number + row['Duration']
        return f"{base_sequence}_{new_sequence_number:06d}"
    
    # Safely set the updated sequence using .loc[]
    df_last_entries['Updated Sequence Frame Number'] = df_last_entries.apply(update_sequence, axis=1)
    
    # Drop the temporary 'Base Sequence' column
    df_last_entries = df_last_entries.drop(columns=['Base Sequence'])
    
    # Save the filtered data to a new Excel file
    output_file = 'filtered_last_entries_updated.xlsx'
    df_last_entries.to_excel(output_file, index=False)
    print(f"Filtered and updated data saved to {output_file}")
    
    # Load the second Excel file for validation
    df_check = pd.read_excel(check_file)
    
    # Extract the base sequences from 'Subfolder Name' and convert Updated Sequence Frame Number to integer for comparison
    df_last_entries['Base Sequence'] = df_last_entries['Updated Sequence Frame Number'].str.rsplit(pat='_', n=1).str[0]
    df_last_entries['Updated Sequence Numeric'] = df_last_entries['Updated Sequence Frame Number'].str.rsplit(pat='_', n=1).str[-1].astype(int)
    
    warnings = []

    # Check each entry in the second file against the filtered DataFrame
    for _, row in df_check.iterrows():
        subfolder_name = row['Subfolder Name']
        last_modified_file = row['Last Modified File']
        
        # Extract the numeric part of the Last Modified File
        last_modified_number = int(last_modified_file.rsplit('_', 1)[-1].replace('.jpg', '').replace('.heic', '').replace('.jpeg', ''))
        
        # Check if there's a matching base sequence in the filtered data
        match = df_last_entries[df_last_entries['Base Sequence'] == subfolder_name]
        
        if not match.empty:
            # Compare numbers
            updated_sequence_numeric = match['Updated Sequence Numeric'].values[0]
            if last_modified_number > updated_sequence_numeric:
                warnings.append(f"Warning: For Subfolder '{subfolder_name}', "
                                f"Last Modified File number ({last_modified_number}) exceeds "
                                f"Updated Sequence Frame Number ({updated_sequence_numeric}).")

    # Print warnings if any
    if warnings:
        print("\n".join(warnings))
    else:
        print("All Last Modified File numbers are within the limits of Updated Sequence Frame Numbers.")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        input_file = sys.argv[1]
        check_file = sys.argv[2]
        filter_last_entries_and_update_sequence(input_file, check_file)
    else:
        print("Please provide the paths to the initial Excel file and the second file to check as arguments.")