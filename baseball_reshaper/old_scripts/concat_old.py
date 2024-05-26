import pandas as pd
import sys
import warnings

def process_concat_data(input_file):
    warnings.simplefilter(action='ignore', category=FutureWarning)
    print("Reading the Excel file...")
    # Read the Excel file
    batters_df = pd.read_excel(input_file, sheet_name='Batters')
    new_df = pd.read_excel(input_file, sheet_name='new')

    print("Processing data and writing to 'concat_data' tab...")
    # Create a new DataFrame to store the concatenated data
    concat_df = pd.DataFrame(columns=['Brand', 'Location', 'Time the brand is at screen', 'Duration',
                                      'Screen Location', 'Screen Size %', 'Total Hits', 'Average Hits',
                                      'Sequence Frame Number', 'Inning', 'Player'])

    # Iterate over each row in the 'new' DataFrame
    for index, row in new_df.iterrows():
        
        brand = row['Brand']
        location = row['Location']
        seq_frame_number = row['Sequence Frame Number']
        print(f"Processing Sequence Frame Number: {seq_frame_number}")

        # Find matching row in 'Batters' DataFrame
        match_row = batters_df[batters_df['Sequence Frame Number'] == seq_frame_number]

        if not match_row.empty:
            # Extract necessary information from 'Batters' DataFrame
            location_batters = match_row['Location'].iloc[0]
            time_at_screen = match_row['Time the brand is at screen'].iloc[0]
            duration = match_row['Duration'].iloc[0]
            screen_location = match_row['Screen Location'].iloc[0]
            screen_size = match_row['Screen Size %'].iloc[0]
            total_hits = match_row['Total Hits'].iloc[0]
            avg_hits = match_row['Average Hits'].iloc[0]
            inning = match_row['Inning'].iloc[0]
            

            # Create new rows for each sequence frame number based on duration
            for i in range(duration):
                new_row = {'Brand': brand, 'Location': location, 'Time the brand is at screen': time_at_screen,
                           'Duration': 1, 'Screen Location': screen_location, 'Screen Size %': screen_size,
                           'Total Hits': total_hits, 'Average Hits': avg_hits,
                           'Sequence Frame Number': seq_frame_number + i, 'Inning': inning,'Player': location_batters}
                concat_df = concat_df.append(new_row, ignore_index=True)
        else:
            # If no match is found, copy the row from the 'new' DataFrame to 'concat_data' DataFrame
            new_row = {'Brand': brand, 'Location': location, 'Time the brand is at screen': row['Time the brand is at screen'],
                       'Duration': row['Duration'], 'Screen Location': row['Screen Location'],
                       'Screen Size %': row['Screen Size %'], 'Total Hits': row['Total Hits'],
                       'Average Hits': row['Average Hits'], 'Sequence Frame Number': seq_frame_number
                       }
            concat_df = concat_df.append(new_row, ignore_index=True)

    # Write the concatenated data to the 'concat_data' tab in the Excel file
    with pd.ExcelWriter(input_file, mode='a', engine='openpyxl') as writer:
        concat_df.to_excel(writer, sheet_name='concat_data', index=False)

    print("Data written to the 'concat_data' tab in the Excel file.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script_name.py input_file.xlsx")
        sys.exit(1)

    input_file = sys.argv[1]
    process_concat_data(input_file)
