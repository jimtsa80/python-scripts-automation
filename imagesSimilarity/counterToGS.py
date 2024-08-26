import os
import zipfile
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sys

def count_files_in_zip(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        file_list = zip_ref.namelist()
        file_count = len(file_list)
    return file_count

def write_file_count_to_google_sheet(file_name, file_count):
    # Define the Google Sheet URL
    sheet_url = "https://docs.google.com/spreadsheets/d/1tZ469trAOzQfthGqaT6fszwyy7N33fZcO-8iZmZ0r0k/edit?gid=0#gid=0"
    
    # Define the scope and authenticate with the service account
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("client_secret.json", scope)
    client = gspread.authorize(creds)

    # Open the Google Sheet
    sheet = client.open_by_url(sheet_url).sheet1
    
    # Append the file count to the sheet
    rows = sheet.get_all_values()
    row_idx = len(rows) + 1

    sheet.update_cell(row_idx, 1, file_name)  # File name or folder name
    sheet.update_cell(row_idx, 2, file_count)  # File count

def process_zip_files_in_directory(directory_path):
    for file_name in os.listdir(directory_path):
        file_path = os.path.join(directory_path, file_name)
        if zipfile.is_zipfile(file_path):
            file_count = count_files_in_zip(file_path)
            print(f"Total number of files in {file_name}: {file_count}")
            write_file_count_to_google_sheet(file_name, file_count)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <path_to_directory>")
        sys.exit(1)

    directory_path = sys.argv[1]
    
    if not os.path.isdir(directory_path):
        print(f"The provided path '{directory_path}' is not a valid directory.")
        sys.exit(1)

    process_zip_files_in_directory(directory_path)
    
    print("File counts written to Google Sheet")
