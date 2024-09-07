import sys
import os
import pandas as pd

def process_excel_file(input_file):
    # Read the input Excel file
    print(f"Reading input file: {input_file}")
    df = pd.read_excel(input_file)
    
    # Calculate the total duration
    total_duration = df['Duration'].sum()
    print(f"Total Duration: {total_duration}")
    
    # Create an empty list to store the processed rows
    processed_rows = []
    
    # Iterate over each row in the DataFrame
    for index, row in df.iterrows():
        duration = row['Duration']
        sequence_frame = str(row['Sequence Frame Number'])
        
        if '_' in sequence_frame:
            # Split the Sequence Frame Number to handle the prefix
            prefix, frame_number = sequence_frame.rsplit('_', 1)
        else:
            # No prefix, treat the whole Sequence Frame Number as a number
            prefix = ''
            frame_number = sequence_frame
        
        # Determine the length of the numeric part to preserve leading zeros
        frame_number_length = len(frame_number)
        frame_number = int(frame_number)  # Convert frame number to an integer
        
        for i in range(duration):
            new_row = row.copy()
            new_row['Duration'] = 1
            
            # Format the new sequence frame number with leading zeros
            new_frame_number = str(frame_number + i).zfill(frame_number_length)
            
            if prefix:
                new_row['Sequence Frame Number'] = f"{prefix}_{new_frame_number}"
            else:
                new_row['Sequence Frame Number'] = new_frame_number
            
            processed_rows.append(new_row)
            #print(f"Added new row with Sequence Frame Number {new_row['Sequence Frame Number']}")
    
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
