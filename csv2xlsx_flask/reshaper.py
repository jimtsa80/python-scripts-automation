import pandas as pd
import sys
import warnings

def process_excel(input_file):
    warnings.simplefilter(action='ignore', category=FutureWarning)
    # Read the Excel file
    xl = pd.ExcelFile(input_file)
    try:
        df = xl.parse('Homeplate')
    except KeyError:
        try:
            df = xl.parse('Homeplate')
        except KeyError:
            print("Neither 'HomePlate' nor 'Homeplate' sheet found in the Excel file.")

    # Create a new DataFrame to store the modified data
    new_df = pd.DataFrame(columns=df.columns)

    # Iterate over each row in the original DataFrame
    for index, row in df.iterrows():
        # Extract relevant information
        duration = row['Duration']
        total_hits = row['Total Hits']
        
        # Create new rows with duration and total hits as 1, and incrementing the sequence number
        for i in range(duration):
            new_row = row.copy()
            new_row['Duration'] = 1
            new_row['Total Hits'] = 1
            new_row['Sequence Frame Number'] += i
            new_df = new_df.append(new_row, ignore_index=True)

    # Add the modified data to a new tab in the existing Excel file
    with pd.ExcelWriter(input_file, mode='a', engine='openpyxl') as writer:
        new_df.to_excel(writer, sheet_name='new', index=False)

    print("Modified data added to a new tab in the existing Excel file.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script_name.py input_file.xlsx")
        sys.exit(1)

    input_file = sys.argv[1]
    process_excel(input_file)





