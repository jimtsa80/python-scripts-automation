import pandas as pd
import sys

def compare_columns(file_path):
    try:
        # Load the Excel file
        excel_data = pd.ExcelFile(file_path)
        
        # Assuming the first sheet is the target
        sheet_name = excel_data.sheet_names[0]
        data = pd.read_excel(file_path, sheet_name=sheet_name)
        
        # Ensure the columns 'A' and 'C' exist
        if 'A' not in data.columns or 'C' not in data.columns:
            print("Error: Columns 'A' and 'C' must exist in the file.")
            return
        
        # Get unique values from columns A and C
        column_a_values = set(data['A'].dropna().astype(str))
        column_c_values = set(data['C'].dropna().astype(str))
        
        # Find differences
        a_not_in_c = column_a_values - column_c_values
        c_not_in_a = column_c_values - column_a_values
        
        # Output results
        print("Values in Column A but not in Column C:")
        if a_not_in_c:
            print("\n".join(a_not_in_c))
        else:
            print("None")
        
        print("\nValues in Column C but not in Column A:")
        if c_not_in_a:
            print("\n".join(c_not_in_a))
        else:
            print("None")
    
    except Exception as e:
        print(f"Error processing the file: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python compare_columns.py <file_path>")
    else:
        file_path = sys.argv[1]
        compare_columns(file_path)
