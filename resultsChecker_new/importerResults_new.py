import os
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import argparse
import numpy as np

def setup_google_sheets(sheet_name):
    print("Setting up Google Sheets...")
    sheet_url = "https://docs.google.com/spreadsheets/d/1MA5KmcDq4ZsxXH5dWlIz7Tp3r0A9ajcI8VyJkBFtyrU/edit?gid=0#gid=0"
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
    client = gspread.authorize(creds)

    print(f"Opened sheet: {sheet_name}")
    sheet = client.open_by_url(sheet_url).worksheet(sheet_name)

    return sheet

def log_transform(value):
    """Apply logarithmic transformation to handle small values and ensure positive output."""
    transformed_value = np.log(abs(value) + 1e-10)  # Apply log to absolute value and add a small constant
    return abs(transformed_value)  # Ensure the final value is positive

def process_xlsx_files(folder_path, sheet_name):
    sheet = setup_google_sheets(sheet_name)

    print(f"Processing files in folder: {folder_path}")
    all_results = []
    
    existing_files = [row[0] for row in sheet.get_all_values()[1:]]  # Skip header

    for filename in os.listdir(folder_path):
        if filename.endswith('.xlsx'):
            file_without_extension = filename.replace('.xlsx', '')
            if file_without_extension in existing_files:
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

                safe_total_frames = 0 if pd.isna(total_frames) else int(total_frames)
                safe_total_duration = 0 if pd.isna(total_duration) else int(total_duration)

                all_results.append([
                    file_without_extension,
                    brand,
                    location,
                    safe_total_frames,
                    safe_total_duration,
                    avg_total_duration_log_rounded
                ])

    if all_results and len(all_results[0]) == 6:
        # Append rows at the end (after existing data, no empty rows)
        sheet.append_rows(all_results)
        print(f"Results appended to the main tab ({len(all_results)} rows added).")
    else:
        print("No valid results found with 'Avg Total / Duration'. Skipping append.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process XLSX files and write to Google Sheets.')
    parser.add_argument('folder', type=str, help='Path to the folder containing XLSX files.')
    parser.add_argument('sheet_name', type=str, help='Name of the Google Sheet tab to write data to.')

    args = parser.parse_args()
    process_xlsx_files(args.folder, args.sheet_name)

