import pandas as pd
import sys

def process_excel(file_path):
    # Load the Excel file
    print("Loading Excel file...")
    df = pd.read_excel(file_path)
    print("Initial data loaded:")
    print(df.head())

    # Group by the relevant columns and aggregate Duration and Sequence Frame Number
    print("Grouping and aggregating data...")
    grouped = df.groupby(
        ['Brand', 'Location', 'Time the brand is at screen', 'Screen Location', 'Screen Size %', 'Total Hits', 'Average Hits'],
        as_index=False
    ).agg({
        'Duration': 'sum',  # Sum the durations
        'Sequence Frame Number': 'min'  # Get the minimum Sequence Frame Number
    })

    print("Aggregated data:")
    print(grouped.head())

    # Merge with the original dataframe to retain other columns based on the minimum Sequence Frame Number
    result_df = pd.merge(
        grouped,
        df[['Brand', 'Location', 'Time the brand is at screen', 'Screen Location', 'Screen Size %', 'Total Hits', 'Average Hits', 'Sequence Frame Number']],
        on=['Brand', 'Location', 'Time the brand is at screen', 'Screen Location', 'Screen Size %', 'Total Hits', 'Average Hits', 'Sequence Frame Number'],
        how='left'
    ).drop_duplicates()

    print("Merged data:")
    print(result_df.head())

    # Sort by 'Sequence Frame Number'
    print("Sorting data by 'Sequence Frame Number'...")
    result_df = result_df.sort_values(by='Sequence Frame Number')

    # Ensure 'Duration' is in column D
    columns = result_df.columns.tolist()
    duration_index = columns.index('Duration')
    columns.insert(3, columns.pop(duration_index))
    result_df = result_df[columns]

    print("Final data to be saved:")
    print(result_df.head())

    # Save the result back to the same Excel file
    print("Saving the result back to the Excel file...")
    with pd.ExcelWriter(file_path, engine='openpyxl', mode='w') as writer:
        result_df.to_excel(writer, index=False)
    print("Process completed successfully.")

if __name__ == "__main__":
    # Ensure the correct number of arguments are provided
    if len(sys.argv) != 2:
        print("Usage: python script.py <excel_file_path>")
        sys.exit(1)
    
    excel_file_path = sys.argv[1]
    process_excel(excel_file_path)
