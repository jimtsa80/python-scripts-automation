import sys
import pandas as pd

def parse_xlsx(input_file):
    print("Reading Excel file...")
    # Read the Excel file
    with pd.ExcelFile(input_file) as xls:
        df_concat_data = pd.read_excel(xls, sheet_name='concat_data')
        try:
            df_home_plate = pd.read_excel(xls, sheet_name='HomePlate')
        except:
            df_home_plate = pd.read_excel(xls, sheet_name='Homeplate')

    print("Updating 'Inning' and 'Name' columns...")
    # Merge data based on 'Sequence Frame Number' and update 'Inning' and 'Name' columns in 'HomePlate'
    df_home_plate = pd.merge(df_home_plate, df_concat_data[['Sequence Frame Number', 'Inning', 'Player']], how='left', on='Sequence Frame Number')

    print("Writing updated data to 'HomePlate' sheet...")
    # Write the updated data to a new 'HomePlate' sheet
    with pd.ExcelWriter(input_file, mode='a', engine='openpyxl') as writer:
        if 'HomePlate' in writer.book.sheetnames:
            writer.book.remove(writer.book['HomePlate'])  # Remove existing 'HomePlate' sheet
        df_home_plate.to_excel(writer, sheet_name='HomePlate', index=False)

        # Remove unnecessary tabs
        tabs_to_remove = ['Batters', 'new', 'concat_data']
        for tab in tabs_to_remove:
            if tab in writer.book.sheetnames:
                writer.book.remove(writer.book[tab])

    print("Data processing complete!")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <xlsx_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    parse_xlsx(input_file)



