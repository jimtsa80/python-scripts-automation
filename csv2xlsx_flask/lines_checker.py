import sys
import pandas as pd

def check_sequence_frame_number(file_path):
    # Read the Excel file
    xls = pd.ExcelFile(file_path)
    
    # Load the specified sheets
    batters_df = pd.read_excel(xls, 'Batters')
    homeplate_df = pd.read_excel(xls, 'Homeplate')
    
    # Get the last entry in the 'Sequence Frame Number' column for both sheets
    last_batters_value = batters_df['Sequence Frame Number'].iloc[-1]
    last_homeplate_value = homeplate_df['Sequence Frame Number'].iloc[-1]
    
    # Check if the last entry in Batters is smaller than the last entry in Homeplate
    if last_batters_value < last_homeplate_value:
        print("true")
    else:
        print("false")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <path_to_excel_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    check_sequence_frame_number(file_path)
