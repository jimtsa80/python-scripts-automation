import pandas as pd
import sys
import warnings

def process_excel(input_file):
    warnings.simplefilter(action='ignore', category=FutureWarning)
    
    # Attempt to load the Excel file
    try:
        xl = pd.ExcelFile(input_file)
        print("Excel file loaded successfully.")
    except Exception as e:
        print(f"Error loading Excel file: {e}")
        sys.exit(1)

    # Attempt to parse the 'Homeplate' sheet
    try:
        df = xl.parse('Homeplate')
        print("'Homeplate' sheet found and loaded successfully.")
    except KeyError:
        print("'Homeplate' sheet not found. Trying 'HomePlate' (capital P).")
        try:
            df = xl.parse('HomePlate')
            print("'HomePlate' sheet found and loaded successfully.")
        except KeyError:
            print("Neither 'HomePlate' nor 'Homeplate' sheet found in the Excel file.")
            sys.exit(1)
    except Exception as e:
        print(f"Error parsing sheet: {e}")
        sys.exit(1)

    # Check if the DataFrame is loaded correctly
    if df.empty:
        print("The DataFrame is empty. Please check the sheet for data.")
        sys.exit(1)
    else:
        print("DataFrame loaded with data:")
        print(df.head())  # Display the first few rows for verification

    # Create a list to store the modified rows
    new_rows = []

    # Iterate over each row in the original DataFrame
    for index, row in df.iterrows():
        try:
            # Extract relevant information
            duration = row['Duration']
            total_hits = row['Total Hits']
            
            # Create new rows with duration and total hits as 1, and incrementing the sequence number
            for i in range(duration):
                new_row = row.copy()
                new_row['Duration'] = 1
                new_row['Total Hits'] = 1
                new_row['Sequence Frame Number'] += i
                new_rows.append(new_row)  # Add the new row to the list
        except KeyError as e:
            print(f"KeyError: {e} - Possible missing column in the DataFrame.")
        except Exception as e:
            print(f"Error processing row {index}: {e}")

    # Convert the list of new rows back into a DataFrame
    new_df = pd.DataFrame(new_rows)

    # Check if new_df has been populated
    if new_df.empty:
        print("No data processed. The new DataFrame is empty.")
        sys.exit(1)
    else:
        print("Data processed successfully. Here's a preview of the new DataFrame:")
        print(new_df.head())

    # Add the modified data to a new tab in the existing Excel file
    try:
        with pd.ExcelWriter(input_file, mode='a', engine='openpyxl') as writer:
            new_df.to_excel(writer, sheet_name='new', index=False)
        print("Modified data added to a new tab in the existing Excel file.")
    except Exception as e:
        print(f"Error saving the new sheet to Excel file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script_name.py input_file.xlsx")
        sys.exit(1)

    input_file = sys.argv[1]
    process_excel(input_file)
