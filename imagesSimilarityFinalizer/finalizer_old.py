import pandas as pd
import sys
import re
from datetime import datetime, timedelta

def extract_start_time(file_path):
    filename = file_path.split("_")[-1].replace(".xlsx", "")  # Extract filename from path
    match = re.search(r'(\d{4,6})$', filename)  # Find last 4 to 6 digits
    
    if match:
        base_time = match.group(1)
        if len(base_time) == 6:
            base_time = base_time[:4]  # Use only the first four digits
        start_time = datetime.strptime(base_time, "%H%M")
    else:
        start_time = datetime.strptime("000000", "%H%M%S")
    
    return start_time

def process_excel(file_path):
    # Load the Excel file
    print("Loading Excel file...")
    df = pd.read_excel(file_path)
    
    # Sort by 'Sequence Frame Number' before processing
    df = df.sort_values(by='Sequence Frame Number')
    
    # Group by relevant columns, keeping the original values for Total Hits
    print("Grouping and aggregating data...")
    grouped = df.groupby(
        ['Brand', 'Location', 'Time the brand is at screen','Screen Location', 'Screen Size %'],
        as_index=False
    ).agg({
        'Duration': 'sum',                # Sum the durations
        'Total Hits': 'first',            # Keep the initial 'Total Hits' for all rows in the group
        'Sequence Frame Number': 'min'    # Get the minimum Sequence Frame Number for grouping
    })

    # Extract start time from filename
    start_time = extract_start_time(file_path)
    
    # Convert 'Sequence Frame Number' to timedelta (assuming 1 frame per second)
    df['Time the brand is at screen'] = df['Sequence Frame Number'].apply(
        lambda x: start_time + timedelta(seconds=int(x)) if pd.notnull(x) else pd.NaT
    )
    df['Time the brand is at screen'] = df['Time the brand is at screen'].dt.strftime('%H:%M:%S')


    grouped['Total Hits'] = grouped.apply(lambda row: max(row['Total Hits'], row['Duration']), axis=1)

    # Calculate 'Average Hits' as 'Total Hits' / 'Duration' per row
    grouped['Average Hits'] = grouped['Total Hits'] / grouped['Duration']
    grouped['Average Hits'] = grouped['Average Hits'].round(2)  # Round to 2 decimal places

    # Format 'Screen Size %' and 'Total Hits'
    grouped['Screen Size %'] = grouped['Screen Size %'].round(2)
    #grouped['Total Hits'] = grouped['Total Hits'].round(0)

    # Sort alphabetically by 'Sequence Frame Number'
    print("Sorting data by 'Sequence Frame Number'...")
    result_df = grouped.sort_values(by='Sequence Frame Number')

    # Ensure 'Duration' is in column D
    columns = result_df.columns.tolist()
    duration_index = columns.index('Duration')
    columns.insert(3, columns.pop(duration_index))
    result_df = result_df[columns]

    # Move 'Sequence Frame Number' to the last column
    columns.remove('Sequence Frame Number')
    columns.append('Sequence Frame Number')
    result_df = result_df[columns]

    # Save the result back to the same Excel file
    print("Saving the result back to the Excel file...")
    with pd.ExcelWriter(file_path, engine='openpyxl', mode='w') as writer:
        result_df.to_excel(writer, index=False)
    print("Process completed successfully.")

    # Calculate and print the total duration
    total_duration = result_df['Duration'].sum()
    print(f"Total Duration: {total_duration}")

if __name__ == "__main__":
    # Ensure the correct number of arguments are provided
    if len(sys.argv) != 2:
        print("Usage: python script.py <excel_file_path>")
        sys.exit(1)
    
    excel_file_path = sys.argv[1]
    process_excel(excel_file_path)