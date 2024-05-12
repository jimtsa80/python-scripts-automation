import pandas as pd
import sys
from collections import Counter

def number_groups(lst):
    numbered_list = []
    count = 1

    for i in range(len(lst)):
        if i == 0 or lst[i] != lst[i - 1]:
            count = 1
        numbered_list.append(str(count))
        count += 1

    return numbered_list

def number_nums(lst):
    numbered_list = []
    count = 0
    top_count = 0

    for i in range(len(lst)):
        if lst[i] == '1':
            top_count += 1
            count = 1
        elif count > top_count:
            count = 1
        numbered_list.append(str(top_count))
        count += 1

    return numbered_list

def final(lst):

    top_count = 0  # Initialize counter for "top"
    bottom_count = 0  # Initialize counter for "bottom"
    last_type = None
    
    # Iterate through the input list and modify it accordingly
    for i, item in enumerate(lst):
        if int(item) % 2 == 0:
            if last_type != 'bottom':
                bottom_count += 1
            lst[i] = f'bottom {bottom_count}'
            last_type = 'bottom'
        else:
            if last_type != 'top':
                top_count += 1
            lst[i] = f'top {top_count}'
            last_type = 'top'

    return lst

def add_inning_column(input_file):
    # Read the Excel file
    df = pd.read_excel(input_file, sheet_name='Batters')

    brands = []
    last_results = []

    for _, row in df.iterrows():
        brand = row['Brand']
        brands.append(brand)

    numbers = number_groups(brands)

    results = number_nums(numbers)

    last_results = final(results)

    # Add the "Inning" column to the DataFrame
    df['Inning'] = last_results

    #Save the modified DataFrame back to the same Excel file and same tab
    with pd.ExcelWriter(input_file, engine='openpyxl', mode='a') as writer:
        if 'Batters' in writer.book.sheetnames:
            writer.book.remove(writer.book['Batters'])
        df.to_excel(writer, index=False, sheet_name='Batters')

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py input_file.xlsx")
        sys.exit(1)

    input_file = sys.argv[1]

    add_inning_column(input_file)