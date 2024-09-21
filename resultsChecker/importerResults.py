import os
import pandas as pd
import gspread
import argparse
import time
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import APIError

# Step 1: Set up Google Sheets API using the sheet URL and the specified sheet/tab name
def setup_google_sheets(sheet_name):
    print("Setting up Google Sheets...")
    sheet_url = "https://docs.google.com/spreadsheets/d/1MA5KmcDq4ZsxXH5dWlIz7Tp3r0A9ajcI8VyJkBFtyrU/edit?gid=0#gid=0"
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
    client = gspread.authorize(creds)
    
    # Open the specified tab/sheet for results
    sheet = client.open_by_url(sheet_url).worksheet(sheet_name)
    
    # Open the tab for filenames (sheet_name + '_files')
    file_sheet = client.open_by_url(sheet_url).worksheet(f"{sheet_name}_files")
    
    return sheet, file_sheet

# Step 2: Get processed filenames from the file_sheet
def get_processed_filenames(file_sheet):
    """Retrieve the list of already processed filenames from the '_files' tab."""
    print("Retrieving list of already processed filenames from the '_files' tab...")
    filenames = file_sheet.col_values(1)  # Assuming filenames are in the first column
    processed_filenames = [filename.strip() for filename in filenames if filename]  # Strip any extra spaces
    return set(processed_filenames)  # Return a set for faster lookup
# Step 3: Process the XLSX files and filter out already processed ones

def process_xlsx_files(folder_path, processed_filenames):
    """Process XLSX files, skipping those that have already been processed."""
    print("Processing new XLSX files in folder:", folder_path)
    file_data = {}
    new_filenames = []

    for file_name in os.listdir(folder_path):
        if file_name.endswith('.xlsx'):
            cleaned_file_name = file_name.strip()  # Clean any extra spaces
            if cleaned_file_name in processed_filenames:
                print(f"Skipping already processed file: {cleaned_file_name}")
                continue  # Skip this file if it was already processed
            else:
                file_path = os.path.join(folder_path, file_name)
                print(f"Processing file: {cleaned_file_name}")
                new_filenames.append([cleaned_file_name])

                df = pd.read_excel(file_path)
                grouped = df.groupby(['Brand', 'Location'])['Duration'].sum().reset_index()

                file_data[cleaned_file_name] = {}
                for _, row in grouped.iterrows():
                    combo = (row['Brand'], row['Location'])
                    duration = row['Duration']

                    if combo in file_data[cleaned_file_name]:
                        file_data[cleaned_file_name][combo]['total_duration'] += duration
                    else:
                        file_data[cleaned_file_name][combo] = {'total_duration': duration, 'file_count': 1}
    
    return file_data, new_filenames


# Step 4: Retrieve existing data from Google Sheets
def get_existing_data(sheet):
    print("Retrieving existing data from Google Sheets...")
    records = sheet.get_all_records()
    existing_data = {}
    existing_brands = set()

    for record in records:
        combo = (record['Brand'], record['Location'])
        existing_data[combo] = {
            'total_duration': record['Total Duration'],
            'average_duration': record['Average Duration'],
            'cumulative_file_count': record['Cumulative File Count']
        }
        existing_brands.add(record['Brand'])  # Collect existing brands

    return existing_data, existing_brands

# Step 5: Compare new data with existing data
def compare_data(new_file_data, existing_data):
    if not existing_data:
        return  # Skip comparison if there's no existing data

    differences = []
    
    for file_name, new_data in new_file_data.items():
        print(f"\nComparing data for file: {file_name}")
        for combo, new_values in new_data.items():
            new_avg_duration = new_values['total_duration'] / new_values['file_count']
            
            if combo in existing_data:
                existing_avg_duration = existing_data[combo]['average_duration']
                
                # Calculate percentage difference
                if existing_avg_duration > 0:
                    percentage_difference = abs(new_avg_duration - existing_avg_duration) / existing_avg_duration * 100

                    if percentage_difference > 25:
                        differences.append({
                            'combo': combo,
                            'new_avg_duration': new_avg_duration,
                            'existing_avg_duration': existing_avg_duration,
                            'percentage_difference': percentage_difference
                        })

    # Sort differences in descending order by percentage_difference
    differences.sort(key=lambda x: x['percentage_difference'], reverse=True)

    # Print the differences
    for diff in differences:
        print(f"Combination {diff['combo']}: New total ({diff['new_avg_duration']:.2f}) has {diff['percentage_difference']:.2f}% difference from existing average ({diff['existing_avg_duration']:.2f})")

# Step 6: Merge new data with existing data
def merge_data(new_file_data, existing_data, file_count):
    print("Merging new data with existing data...")
    
    for _, new_data in new_file_data.items():
        for combo, new_values in new_data.items():
            new_total_duration = new_values['total_duration']
            new_file_count = new_values['file_count']
            
            if combo in existing_data:
                existing_total_duration = existing_data[combo]['total_duration']
                existing_file_count = existing_data[combo]['cumulative_file_count']
                
                updated_total_duration = existing_total_duration + new_total_duration
                updated_file_count = existing_file_count + new_file_count
                updated_average_duration = updated_total_duration / updated_file_count
                
                existing_data[combo] = {
                    'total_duration': updated_total_duration,
                    'average_duration': updated_average_duration,
                    'cumulative_file_count': updated_file_count
                }
            else:
                existing_data[combo] = {
                    'total_duration': new_total_duration,
                    'average_duration': new_total_duration / new_file_count,
                    'cumulative_file_count': new_file_count
                }
    
    return existing_data

# Step 7: Write updated results and filenames to Google Sheets
def write_to_google_sheets(merged_data, new_filenames, sheet, file_sheet):
    """
    Write the merged data to the Google Sheet, sorted by the biggest averages.
    Also, append new filenames to the _files tab to track all processed files.
    """
    print("Writing results to the Google Sheet...")

    # Convert merged data into a list of lists for writing to Google Sheets
    rows = [["Brand", "Location", "Total Duration", "Average Duration", "Cumulative File Count"]]
    for combo, data in merged_data.items():
        brand, location = combo
        rows.append([brand, location, data['total_duration'], data['average_duration'], data['cumulative_file_count']])
    
    # Step 1: Sort rows by "Average Duration" (index 3) in descending order
    sorted_rows = sorted(rows[1:], key=lambda x: x[3], reverse=True)

    # Step 2: Write the header and sorted data to the Google Sheet
    sheet.clear()  # Clear existing data
    sheet.append_row(rows[0])  # Write header
    sheet.append_rows(sorted_rows)  # Write sorted rows
    
    print(f"Successfully wrote {len(sorted_rows)} rows to the Google Sheet.")

    # Step 3: Append new filenames to the _files tab
    print("Updating the _files tab with new filenames...")

    # Read existing filenames from the _files tab
    existing_filenames = file_sheet.col_values(1)  # Assuming filenames are in the first column

    # Combine new filenames with existing ones, ensuring no duplicates
    combined_filenames = set(existing_filenames + [filename[0] for filename in new_filenames])

    # Clear the _files tab and write the updated list of filenames
    file_sheet.clear()  # Clear existing data in the _files tab
    for filename in combined_filenames:
        file_sheet.append_row([filename])
    
    print(f"Successfully updated the _files tab with {len(combined_filenames)} filenames.")



# Step 8: Identify brands missing in the new XLSX files
def identify_missing_brands(new_file_data, existing_brands):
    new_brands = set()

    for file_name, new_data in new_file_data.items():
        for combo in new_data:
            brand, location = combo
            new_brands.add(brand)  # Collect brands from new files

    # Find brands in existing data but not in new files
    missing_brands = existing_brands - new_brands

    if missing_brands:
        print("\nBrands found in existing data but missing in new files:")
        for brand in missing_brands:
            print(f"Brand: {brand}")

# Main script process
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process XLSX files to calculate Brand-Location total and average durations.")
    parser.add_argument("folder", help="The folder path containing the XLSX files.")
    parser.add_argument("sheet_name", help="The name of the Google Sheet tab to write results.")
    args = parser.parse_args()

    sheet, file_sheet = setup_google_sheets(args.sheet_name)
    processed_filenames = get_processed_filenames(file_sheet)

    new_file_data, new_filenames = process_xlsx_files(args.folder, processed_filenames)
    
    if new_filenames:
        existing_data, existing_brands = get_existing_data(sheet)

        if existing_data:
            compare_data(new_file_data, existing_data)

        # Step 8: Identify and print brands that are missing in new files
        identify_missing_brands(new_file_data, existing_brands)

        merged_data = merge_data(new_file_data, existing_data, len(new_file_data))
        write_to_google_sheets(merged_data, new_filenames, sheet, file_sheet)
    else:
        print("No new files to process.")

    print("Process completed successfully.")
