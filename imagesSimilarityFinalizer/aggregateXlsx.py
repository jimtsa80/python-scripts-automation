import os
import sys
import pandas as pd
from tqdm import tqdm  # Import tqdm for progress bar

def process_files_in_folder(folder_path):
    # Filter the directory for Excel files beginning with 'final_'
    files = [f for f in os.listdir(folder_path) if f.startswith('final_') and f.endswith('.xlsx')]

    # Initialize tqdm progress bar for file processing
    for file in tqdm(files, desc="Processing Files", unit="file"):
        file_path = os.path.join(folder_path, file)
        
        # Read the Excel file into a DataFrame
        original_data = pd.read_excel(file_path)

        # Get the total number of lines before processing (can be reduced)
        total_lines_before = len(original_data)

        # Rename columns to match the example provided
        original_data.columns = ['Brand', 'Location', 'Time the brand is at screen', 'Duration', 'Screen Location', 'Screen Size %', 'Total Hits', 'Average Hits', 'Sequence Frame Number']

        # Convert necessary columns to integers
        original_data['Duration'] = original_data['Duration'].astype(int)
        original_data['Total Hits'] = original_data['Total Hits'].astype(int)

        # Sort the DataFrame to group and aggregate data effectively
        sorted_data = original_data.sort_values(by=['Brand', 'Location', 'Sequence Frame Number']).reset_index(drop=True)

        # Create a new list to store the aggregated data rows
        aggregated_rows = []
        original_row_count = len(sorted_data)
        aggregated_row_count = 0

        # Initialize tqdm progress bar for row processing
        for i in tqdm(range(len(sorted_data)), desc=f"Processing rows in {file}", unit="row"):
            sequence_frame_number = sorted_data.loc[i, 'Sequence Frame Number']
            
            # Check if there is a '_' in 'Sequence Frame Number'
            if '_' in str(sequence_frame_number):
                # If there is '_', extract the numeric part after the last '_'
                current_sequence_number = int(sequence_frame_number.split('_')[-1])
                
                # If the sequence continues, check if the difference between the numbers is 1
                if i == 0 or not (
                    sorted_data.loc[i, 'Brand'] == sorted_data.loc[i - 1, 'Brand'] and
                    sorted_data.loc[i, 'Location'] == sorted_data.loc[i - 1, 'Location'] and
                    current_sequence_number == (int(sorted_data.loc[i - 1, 'Sequence Frame Number'].split('_')[-1]) + 1)
                ):
                    # Start a new aggregation sequence
                    aggregated_rows.append(sorted_data.loc[i].copy())
                    aggregated_row_count += 1
                else:
                    # If the sequence continues, aggregate the data
                    last_row = aggregated_rows[-1]
                    last_row['Duration'] += sorted_data.loc[i, 'Duration']
                    # last_row['Total Hits'] += sorted_data.loc[i, 'Total Hits']  # You can include this if needed
            else:
                # If there is no '_', compare as before (numerical sequence)
                if i == 0 or not (
                    sorted_data.loc[i, 'Brand'] == sorted_data.loc[i - 1, 'Brand'] and
                    sorted_data.loc[i, 'Location'] == sorted_data.loc[i - 1, 'Location'] and
                    sorted_data.loc[i, 'Sequence Frame Number'] == (sorted_data.loc[i - 1, 'Sequence Frame Number'] + 1)
                ):
                    # Start a new aggregation sequence
                    aggregated_rows.append(sorted_data.loc[i].copy())
                    aggregated_row_count += 1
                else:
                    # If the sequence continues, aggregate the data
                    last_row = aggregated_rows[-1]
                    last_row['Duration'] += sorted_data.loc[i, 'Duration']
                    # last_row['Total Hits'] += sorted_data.loc[i, 'Total Hits']  # You can include this if needed

        # Convert the list of aggregated rows back to a DataFrame
        aggregated_data = pd.DataFrame(aggregated_rows)

        # Sort the aggregated data by 'Sequence Frame Number' from smaller to bigger
        aggregated_data = aggregated_data.sort_values(by='Sequence Frame Number')

        # Write the aggregated and sorted data back to the same file, overwriting the original content
        aggregated_data.to_excel(file_path, index=False)

        # Calculate how many lines were affected by the change
        total_lines_after = len(aggregated_data)
        lines_affected = total_lines_before - total_lines_after

        #Print total lines after processing and lines affected (can be reduced for performance)
        print(f"File {file} has been updated.")
        print(f"Total lines after processing: {total_lines_after}")
        print(f"{lines_affected} lines were aggregated into {aggregated_row_count} lines.\n")

if __name__ == "__main__":
    # Check if the correct number of command-line arguments is provided
    if len(sys.argv) != 2:
        print("Usage: python script.py <folder_path>")
        sys.exit(1)

    # Get the folder path from command line argument
    folder_path = sys.argv[1]
    process_files_in_folder(folder_path)
