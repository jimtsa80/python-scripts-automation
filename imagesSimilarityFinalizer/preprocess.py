import sys
import os
import pandas as pd

def process_excel_file(input_file):
    # Read the input Excel file
    print(f"Reading input file: {input_file}")
    df = pd.read_excel(input_file)
    
    # Create an empty list to store the processed rows
    processed_rows = []
    
    # Iterate over each row in the DataFrame
    for index, row in df.iterrows():
        duration = row['Duration']
        print(f"Processing row {index + 1} with duration {duration}")
        for i in range(duration):
            new_row = row.copy()
            new_row['Duration'] = 1
            new_row['Sequence Frame Number'] += i
            processed_rows.append(new_row)
            print(f"Added new row with Sequence Frame Number {new_row['Sequence Frame Number']}")
    
    # Create a new DataFrame from the processed rows
    processed_df = pd.DataFrame(processed_rows)
    
    # Generate the output file name
    output_file = os.path.join(os.path.dirname(input_file), f"final_{os.path.basename(input_file)}")
    print(f"Saving processed file as: {output_file}")
    
    # Write the processed DataFrame to a new Excel file
    processed_df.to_excel(output_file, index=False)
    print("File saved successfully")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <input_file.xlsx>")
    else:
        input_file = sys.argv[1]
        process_excel_file(input_file)
