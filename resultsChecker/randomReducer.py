import pandas as pd
import sys
import random
from openpyxl import load_workbook

def reduce_duration(xlsx_path, brand, location, percentage):
    # Load the XLSX file
    df = pd.read_excel(xlsx_path)

    # Filter the data based on brand and location
    filtered_df = df[(df['Brand'] == brand) & (df['Location'] == location)]

    # Calculate the initial duration
    initial_duration = filtered_df['Duration'].sum()
    print(f"Initial Duration: {initial_duration}")

    # Determine the target duration after reduction
    target_duration = initial_duration * (1 - percentage / 100)

    # Randomly remove rows until target duration is achieved
    remaining_rows = filtered_df.index.tolist()
    random.shuffle(remaining_rows)  # Shuffle to ensure randomness

    while filtered_df['Duration'].sum() > target_duration:
        for idx in remaining_rows:
            if filtered_df['Duration'].sum() <= target_duration:
                break
            filtered_df = filtered_df.drop(idx)  # Drop rows randomly

    # Calculate the final duration
    final_duration = filtered_df['Duration'].sum()
    print(f"Final Duration: {final_duration}")

    # Load existing "Reduced Data" sheet if it exists
    try:
        existing_data = pd.read_excel(xlsx_path, sheet_name='Reduced Data')
        combined_df = pd.concat([existing_data, filtered_df], ignore_index=True)
    except ValueError:  # If "Reduced Data" sheet does not exist
        combined_df = filtered_df

    # Write combined data to the "Reduced Data" sheet
    with pd.ExcelWriter(xlsx_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        combined_df.to_excel(writer, sheet_name='Reduced Data', index=False)

    print(f"Reduced data appended to {xlsx_path}")

# Example usage
if __name__ == "__main__":
    # Arguments: file_path, brand, location, percentage
    reduce_duration(sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]))