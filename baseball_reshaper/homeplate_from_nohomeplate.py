"""
For workbooks with NoHomeplate + Homeplate tabs:
- Move rows from NoHomeplate where Location is 'Home Plate' to Homeplate tab
- Sort Homeplate tab by the last column ascending (smallest to largest)
"""
import sys
import pandas as pd

def move_homeplate_and_sort(file_path):
    xls = pd.ExcelFile(file_path)
    sheet_names = xls.sheet_names

    if 'NoHomeplate' not in sheet_names or 'Homeplate' not in sheet_names:
        # Not a 2-tab file (NoHomeplate + Homeplate), skip
        return

    df_nohomeplate = xls.parse('NoHomeplate')
    df_homeplate = xls.parse('Homeplate')

    if 'Location' not in df_nohomeplate.columns:
        return

    # Rows with "Home Plate" in Location (case-insensitive, strip whitespace)
    loc_series = df_nohomeplate['Location'].astype(str).str.strip()
    mask_home_plate = loc_series.str.contains('Home Plate', case=False, na=False)
    rows_to_move = df_nohomeplate[mask_home_plate]
    rows_remain_nohomeplate = df_nohomeplate[~mask_home_plate]

    # Append moved rows to Homeplate
    df_homeplate = pd.concat([df_homeplate, rows_to_move], ignore_index=True)

    # Sort Homeplate by last column ascending (smallest to largest)
    last_col = df_homeplate.columns[-1]
    df_homeplate = df_homeplate.sort_values(by=last_col, ascending=True).reset_index(drop=True)

    # Write back: preserve all other sheets, replace NoHomeplate and Homeplate
    with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        rows_remain_nohomeplate.to_excel(writer, sheet_name='NoHomeplate', index=False)
        df_homeplate.to_excel(writer, sheet_name='Homeplate', index=False)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python homeplate_from_nohomeplate.py <path_to_excel_file>")
        sys.exit(1)
    file_path = sys.argv[1]
    move_homeplate_and_sort(file_path)
