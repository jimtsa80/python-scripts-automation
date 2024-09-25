import gspread
import argparse
from oauth2client.service_account import ServiceAccountCredentials

def setup_google_sheets(sheet_name):
    print("Setting up Google Sheets...")
    sheet_url = "https://docs.google.com/spreadsheets/d/1MA5KmcDq4ZsxXH5dWlIz7Tp3r0A9ajcI8VyJkBFtyrU/edit?gid=0#gid=0"
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
    client = gspread.authorize(creds)

    print(f"Opened sheet: {sheet_name}")
    sheet = client.open_by_url(sheet_url).worksheet(sheet_name)

    return sheet

def create_brand_location_txt(sheet_name):
    sheet = setup_google_sheets(sheet_name)

    # Get all the data from the Google Sheet
    data = sheet.get_all_records()

    # Dictionary to store Brand as key and associated Locations as values
    brand_location_dict = {}
    
    for row in data:
        brand = row['Brand']
        location = row['Location']
        if brand in brand_location_dict:
            brand_location_dict[brand].add(location)
        else:
            brand_location_dict[brand] = {location}
    
    # Sorting brands and locations alphabetically
    sorted_brands = sorted(brand_location_dict.keys())
    
    # Create the text file based on the sheet_name argument
    txt_file_name = f"{sheet_name}.txt"
    with open(txt_file_name, 'w', encoding='utf-8') as file:
        for brand in sorted_brands:
            file.write(f"#{brand}\n")
            sorted_locations = sorted(brand_location_dict[brand])
            for location in sorted_locations:
                file.write(f"{location}\n")
            file.write("\n")  # Empty line between brands

    print(f"Text file '{txt_file_name}' created successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Google Sheet to create Brand/Location text file.")
    parser.add_argument("sheet_tab_name", help="The name of the Google Sheet tab (prefixed with 'Total_')")

    args = parser.parse_args()

    # Ensure the prefix 'Total_' is added to the sheet tab name
    full_sheet_tab_name = f"Total_{args.sheet_tab_name}"

    # Calling the function with the modified tab name
    create_brand_location_txt(full_sheet_tab_name)
