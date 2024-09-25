import os
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import argparse
import time
import numpy as np

def setup_google_sheets(sheet_name):
    print("Setting up Google Sheets...")
    sheet_url = "https://docs.google.com/spreadsheets/d/1MA5KmcDq4ZsxXH5dWlIz7Tp3r0A9ajcI8VyJkBFtyrU/edit?gid=0#gid=0"
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
    client = gspread.authorize(creds)

    print(f"Opened sheet: {sheet_name}")
    sheet = client.open_by_url(sheet_url).worksheet(sheet_name)
    file_sheet = client.open_by_url(sheet_url).worksheet(f"{sheet_name}")

    return sheet, file_sheet

def log_transform(value):
    """Apply logarithmic transformation to handle small values and ensure positive output."""
    transformed_value = np.log(abs(value) + 1e-10)  # Apply log to absolute value and add a small constant
    return abs(transformed_value)  # Ensure the final value is positive

def check_differences_and_print(avg_df, total_df):
    significant_diffs = []
    
    # Loop through each row in avg_df and compare with total_df
    for index, new_row in avg_df.iterrows():
        try:
            brand, location, avg_duration = new_row['Brand'], new_row['Location'], new_row['Accumulative Avg']
            
            # Try to find the corresponding row in total_df
            matching_row = total_df[(total_df['Brand'] == brand) & (total_df['Location'] == location)]
            if not matching_row.empty:
                old_avg = matching_row.iloc[0]['Accumulative Avg']
                diff_percent = abs((avg_duration - old_avg) / old_avg) * 100

                # If difference is greater than 25%, store it
                if diff_percent > 25:
                    significant_diffs.append((brand, location, old_avg, avg_duration, diff_percent))
            else:
                print(f"New combination found for Brand: {brand}, Location: {location}.")
        
        # Catch KeyError for missing 'Avg Total / Duration' column
        except KeyError as e:
            print(f"KeyError: {e}. Please ensure that the 'Accumulative Avg' column exists in the provided dataframes.")
            return

    # Print significant differences
    if significant_diffs:
        print("\nSignificant differences (over 25%):")
        significant_diffs = sorted(significant_diffs, key=lambda x: x[4], reverse=True)  # Sort by difference percentage
        for brand, location, old_avg, new_avg, diff_percent in significant_diffs:
            print(f"Brand: {brand}, Location: {location} - Old Avg: {old_avg:.3f}, New Avg: {new_avg:.3f}, Diff: {diff_percent:.2f}%")
    else:
        print("No significant differences found.")


def update_total_avg(main_tab_df, total_sheet):

    # Get the list of existing brands from the total sheet
    total_data = total_sheet.get_all_records()
    total_brands = set(row['Brand'] for row in total_data if 'Brand' in row)

    new_brands = set(main_tab_df['Brand'].unique())

    # Check for missing brands in the total sheet
    missing_brands = new_brands - total_brands
    if missing_brands:
        print(f"Warning: The following brands from the new file do not exist in the Total tab: {', '.join(missing_brands)}")

    # Verify if the 'Avg Total / Duration' column exists in main_tab_df
    if 'Avg Total / Duration' in main_tab_df.columns:
        avg_df = main_tab_df.groupby(['Brand', 'Location'], as_index=False)['Avg Total / Duration'].mean()
        avg_df = avg_df.rename(columns={'Avg Total / Duration': 'Accumulative Avg'})

        # Debugging: Check if the column exists in avg_df
        print("Columns in avg_df:", avg_df.columns)

        # Check differences with existing totals before updating
        total_data = total_sheet.get_all_records()
        total_df = pd.DataFrame(total_data)

        # Check if 'Accumulative Avg' column exists in total_df
        if 'Accumulative Avg' in total_df.columns:
            check_differences_and_print(avg_df, total_df)
        else:
            print("No 'Accumulative Avg' column found in Total_ tab.")

        # Sort by Accumulative Avg in ascending order
        avg_df = avg_df.sort_values(by='Accumulative Avg').reset_index(drop=True)

        # Clear the existing entries in the Total_ tab
        total_sheet.clear()

        # Write the header
        total_sheet.append_row(['Brand', 'Location', 'Accumulative Avg'])

        # Write the sorted averages to the Total_ tab
        for _, row in avg_df.iterrows():
            total_sheet.append_row([row['Brand'], row['Location'], round(row['Accumulative Avg'], 3)])

        print("Accumulative Avg updated with sorted values.")
    else:
        print("'Avg Total / Duration' column not found in main tab. Ensure the data was processed correctly.")

def process_xlsx_files(folder_path, sheet_name):
    sheet, file_sheet = setup_google_sheets(sheet_name)
    total_sheet_name = f"Total_{sheet_name}"

    # Try to get existing data from Total_ tab
    try:
        total_sheet = sheet.spreadsheet.worksheet(total_sheet_name)
        total_data = total_sheet.get_all_records()
        total_df = pd.DataFrame(total_data)
    except gspread.exceptions.WorksheetNotFound:
        total_sheet = sheet.spreadsheet.add_worksheet(title=total_sheet_name, rows="100", cols="5")
        total_df = pd.DataFrame()

    print(f"Processing files in folder: {folder_path}")
    all_results = []
    
    # Processing files and gathering data
    existing_files = [row[0] for row in sheet.get_all_values()[1:]]  # Skip header

    for filename in os.listdir(folder_path):
        if filename.endswith('.xlsx'):
            file_without_extension = filename.replace('.xlsx', '')
            if file_without_extension in existing_files:
                # print(f"File '{filename}' already processed. Skipping...")
                continue

            file_path = os.path.join(folder_path, filename)
            print(f"Reading file: {filename}")
            df = pd.read_excel(file_path)

            total_frames = df['Sequence Frame Number'].iloc[-1] - df['Sequence Frame Number'].iloc[0] + df['Duration'].iloc[-1]

            grouped = df.groupby(['Brand', 'Location'])

            for (brand, location), group in grouped:
                total_duration = group['Duration'].sum()
                avg_total_duration = total_duration / total_frames if total_frames > 0 else 0
                avg_total_duration_log = log_transform(avg_total_duration)
                avg_total_duration_log_rounded = round(avg_total_duration_log, 3)

                all_results.append([
                    file_without_extension,
                    brand,
                    location,
                    int(total_frames),
                    int(total_duration),
                    avg_total_duration_log_rounded
                ])

    # Check if the results contain "Avg Total / Duration" before inserting
    if all_results and len(all_results[0]) == 6:
        sheet.insert_rows(all_results, 2)
        print("Results appended to the main tab.")
    else:
        print("No valid results found with 'Avg Total / Duration'. Skipping append.")

    # Fetch the updated main tab data after appending
    main_tab_data = sheet.get_all_records()
    main_tab_df = pd.DataFrame(main_tab_data)

    # Call the function to update the Total_ tab with sorted Accumulative Avg values
    update_total_avg(main_tab_df, total_sheet)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process XLSX files and write to Google Sheets.')
    parser.add_argument('folder', type=str, help='Path to the folder containing XLSX files.')
    parser.add_argument('sheet_name', type=str, help='Name of the Google Sheet tab to write data to.')

    args = parser.parse_args()
    process_xlsx_files(args.folder, args.sheet_name)
