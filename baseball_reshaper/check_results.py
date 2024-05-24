import pandas as pd
import sys

def compare_sheets(file1, file2):
    # Load the HomePlate sheets from both Excel files
    df1 = pd.read_excel(file1, sheet_name='HomePlate')
    df2 = pd.read_excel(file2, sheet_name='HomePlate')
    
    # Find rows that are in df1 but not in df2
    extra_in_file1 = pd.concat([df1, df2, df2]).drop_duplicates(keep=False)
    
    # Find rows that are in df2 but not in df1
    extra_in_file2 = pd.concat([df2, df1, df1]).drop_duplicates(keep=False)
    
    print("Rows in {} but not in {}:".format(file1, file2))
    print(extra_in_file1)
    
    print("\nRows in {} but not in {}:".format(file2, file1))
    print(extra_in_file2)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare_xlsx.py <file1.xlsx> <file2.xlsx>")
        sys.exit(1)

    file1 = sys.argv[1]
    file2 = sys.argv[2]

    compare_sheets(file1, file2)
