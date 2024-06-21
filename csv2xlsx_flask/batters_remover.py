import sys
import pandas as pd
import re

def remove_rows_with_digits(file_path):
    # Read the Excel file
    df = pd.read_excel(file_path, sheet_name='Homeplate')
    
    # Function to check if a string contains any digits
    def contains_digit(s):
        return bool(re.search(r'\d', str(s)))
    
    # Filter out rows where the 'Location' column contains any digits
    filtered_df = df[~df['Location'].apply(contains_digit)]
    
    # Swap the 'Player' and 'Inning' columns
    cols = list(filtered_df.columns)
    player_index = cols.index('Player')
    inning_index = cols.index('Inning')
    cols[player_index], cols[inning_index] = cols[inning_index], cols[player_index]
    filtered_df = filtered_df[cols]
    
    # Save the filtered DataFrame back to the Excel file
    with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        filtered_df.to_excel(writer, sheet_name='Homeplate', index=False)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    remove_rows_with_digits(file_path)
    print(f"Processed file saved at {file_path}")


