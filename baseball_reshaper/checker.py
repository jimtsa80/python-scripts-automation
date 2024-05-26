import pandas as pd
import sys

def check_occasion(file_path):
    # Read the Excel file
    try:
        df = pd.read_excel(file_path, sheet_name='Homeplate')
    except Exception as e:
        print("Error:", e)
        return
    
    # Check for the sequence of frame number and different player names
    for i in range(len(df) - 1):
        if df.at[i, 'First Sequence Frame Number'] == df.at[i + 1, 'First Sequence Frame Number'] and \
           df.at[i, 'Player'] != df.at[i + 1, 'Player']:
            print("Occasion found at frame number:", df.at[i, 'First Sequence Frame Number'])
            print("Players involved:", df.at[i, 'Player'], "and", df.at[i + 1, 'Player'])
            print("--------------")
    
    print("Check completed.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <excel_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    check_occasion(file_path)
