import os
import pandas as pd
from openpyxl import Workbook

# Function to get the matching pairs of files
def get_matching_pairs(file_list):
    pairs = {}
    for file in file_list:
        if file.startswith('final_HP_'):
            identifier = file[9:]  # Get the string after 'final_HP_'
            if identifier in pairs:
                pairs[identifier]['HP'] = file
            else:
                pairs[identifier] = {'HP': file}
        elif file.startswith('final_'):
            identifier = file[6:]  # Get the string after 'final_'
            if identifier in pairs:
                pairs[identifier]['No_HP'] = file
            else:
                pairs[identifier] = {'No_HP': file}
        elif file.startswith('batters_'):
            identifier = file[8:]  # Get the string after 'batters_'
            if identifier in pairs:
                pairs[identifier]['Batters'] = file
            else:
                pairs[identifier] = {'Batters': file}
    return pairs

# Function to create a new file with the desired structure
def process_files(pair):
    hp_file = pair.get('HP')
    no_hp_file = pair.get('No_HP')
    batters_file = pair.get('Batters')

    # Determine if we should skip processing `no_hp_file` based on the filename
    skip_no_hp = any(keyword in (hp_file or '').upper() for keyword in ['MEXICO', 'CANADA'])
    
    # Load the final_HP_ file if it exists
    hp_df = pd.read_excel(hp_file) if hp_file else None

    # Load the final_ file if it exists and not skipping
    no_hp_df = pd.read_excel(no_hp_file) if no_hp_file and not skip_no_hp else None

    # Load the batters_ file if it exists
    batters_df = pd.read_excel(batters_file) if batters_file else None

    # Create a new workbook
    new_file = hp_file.replace('final_HP_', 'updated_final_') if hp_file else 'updated_final.xlsx'

    with pd.ExcelWriter(new_file, engine='openpyxl') as writer:
        # Create a workbook and add the NoHomeplate sheet
        if no_hp_df is not None:
            no_hp_df.to_excel(writer, sheet_name='NoHomeplate', index=False)
        else:
            # Add an empty NoHomeplate sheet if skipping no_hp_file
            wb = writer.book
            wb.create_sheet(title="NoHomeplate")

        # Add Homeplate sheet if it exists
        if hp_df is not None:
            hp_df.to_excel(writer, sheet_name='Homeplate', index=False)

        # Add Batters sheet if it exists
        if batters_df is not None:
            batters_df.to_excel(writer, sheet_name='Batters', index=False)

    print(f"Created new file {new_file} with the sheets: NoHomeplate, Homeplate, and Batters.")


# Main function to iterate through the files and process them
def main():
    # List all files in the current directory
    files = [f for f in os.listdir() if f.endswith('.xlsx') and (f.startswith('final') or f.startswith('batters'))]
    
    # Get the matching pairs of files
    pairs = get_matching_pairs(files)

    # Process each pair
    for identifier, pair in pairs.items():
        process_files(pair)

if __name__ == "__main__":
    main()
