import pandas as pd
import sys

def brands_to_numbers(lst):
    numbered_list = []
    count = 1

    for i in range(len(lst)):
        if i == 0 or lst[i] != lst[i - 1]:
            count = 1
        numbered_list.append(str(count))
        count += 1

    return numbered_list

def normalize_numbers(lst):
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

def finalize_innings(lst):
    bottom_count = 7  # Start Bottom innings count from 7
    top_count = 7  # Start Top innings count from 7
    last_type = 'Top'  # Set initial last_type to 'Top' so the first item starts from 'Bottom'

    # Iterate through the input list and modify it accordingly
    for i, item in enumerate(lst):
        if int(item) % 2 == 0:
            if last_type != 'Bottom':
                bottom_count += 1
            lst[i] = f'Bottom {bottom_count}'
            last_type = 'Bottom'
        else:
            if last_type != 'Top':
                top_count += 1
            lst[i] = f'Top {top_count}'
            last_type = 'Top'

    return lst

def add_inning_column(input_file):
    # Read the Excel file
    df = pd.read_excel(input_file, sheet_name='Batters')

    brands = []

    for _, row in df.iterrows():
        brand = row['Brand']
        brands.append(brand)
 
    numbers = brands_to_numbers(brands)

    normalized_numbers = normalize_numbers(numbers)

    innings = finalize_innings(normalized_numbers)

    # Add the "Inning" column to the DataFrame
    df['Inning'] = innings

    # Save the modified DataFrame back to the same Excel file and same tab
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
