import pandas as pd
import sys

# Helper function to process keys and values
def process_item(item):
    """
    Process an item to extract the relevant part (removes spaces,
    leading zeros, and unnecessary parts).
    """
    item = item.strip().replace(" ", "_")  # Normalize spaces
    if '.' in item:  # Remove any file extension like .jpg
        item = item.split('.')[0]
    parts = item.split('_')
    return parts[-1].lstrip('0')  # Return the last part and remove leading zeros

# Load Excel file and create the dictionary
def create_dictionary_from_excel(excel_path):
    """
    Reads the Excel file and creates a dictionary.
    Key: Extracted from the first column, removing leading zeros and non-essential parts.
    Value: Extracted from the second column, processed similarly, and can contain multiple values.
    """
    try:
        # Read the Excel file
        df_excel = pd.read_excel(excel_path, header=None)
        print(f"Excel file loaded successfully. Shape: {df_excel.shape}")
        print("Excel content preview:")
        print(df_excel.head())  # Preview first few rows to check the content
        
        # Check if the Excel file has at least two columns
        if df_excel.shape[1] < 2:
            print("Error: Excel file does not contain at least two columns.")
            return None
        
        # Create the dictionary
        dictionary = {}
        for _, row in df_excel.iterrows():
            key = process_item(row[0])  # Process key
            values = [process_item(val) for val in str(row[1]).split(',')]  # Process values (comma-separated)
            dictionary[key] = values
        
        print("Dictionary created:")
        print(dictionary)  # Show the full dictionary for verification
        
        return dictionary
    
    except Exception as e:
        print(f"Error reading the Excel file: {e}")
        return None

# Extract the sequence frame number from the full key (last part)
def extract_frame_number(key):
    """
    Extracts the frame number from a key by splitting based on spaces and taking the last element.
    """
    parts = key.split()
    return parts[-1]  # Assuming the frame number is the last part of the key

# Step 1: Generate new rows based on the dictionary
def generate_new_rows(df_csv, dictionary):
    """
    Generates new rows based on matches from the CSV and the dictionary.
    This does NOT append them to the CSV yet, but stores them for later.
    """
    if dictionary is None:
        print("Error: Dictionary is None, cannot proceed with row generation.")
        return []

    # List to store new rows that need to be added
    new_rows = []

    # Get the name of the last column (used for key matching)
    last_column = df_csv.columns[-1]

    # Iterate over each row in the CSV
    for index, row in df_csv.iterrows():
        key = str(row[last_column]).strip()  # The key is the value in the last column, stripped of spaces
        
        # Extract the frame number from the key
        frame_number = extract_frame_number(key)
        
        # Process the frame number (stripping leading zeros)
        processed_frame_number = process_item(frame_number)
        
        if processed_frame_number in dictionary:  # Check if the processed frame number exists in the dictionary
            print(f"Match found: Frame number '{processed_frame_number}' matches row {index + 1} in CSV.")
            for value in dictionary[processed_frame_number]:  # For each value associated with the frame number
                print(f"  Adding new row for value '{value}' (from dictionary key '{processed_frame_number}').")
                # Assuming 'row' is a single string like: 'Perth\tTVGI Logo\t0:04:59\t1\tA\t31.756\t1\t1\t299'

                # Split the row into individual values based on the tab character
                row_values = row[0].split('\t')  # Split the first element (the entire row) by tab

                # Print to see the split values
                print("Row values before update:", row_values)

                # Update the last column with the new value from the dictionary
                row_values[-1] = value  # Replace the last value (the frame number) with the new value

                # Reassemble the row into a string (tab-separated format)
                new_row = '\t'.join(row_values)

                # Print the updated row
                print("Updated row:", new_row)

                new_rows.append(new_row)  # Add the new row to the list
        else:
            print(f"No match for frame number '{processed_frame_number}' (row {index + 1}).")

    return new_rows

# Step 2: Append the new rows to the CSV
def append_new_rows_to_csv(csv_path, new_rows):
    """
    Appends the new rows to the existing CSV file.
    """
    if not new_rows:
        print("No new rows to append.")
        return

    # Load the original CSV file
    df_csv = pd.read_csv(csv_path)
    
    # Add the new rows to the original DataFrame
    print(f"Appending {len(new_rows)} new rows to the CSV.")
    df_new_rows = pd.DataFrame(new_rows, columns=df_csv.columns)
    df_csv = pd.concat([df_csv, df_new_rows], ignore_index=True)
    
    # Save the updated CSV back to the original file
    df_csv.to_csv(csv_path, index=False)
    print(f"CSV file '{csv_path}' has been updated.")

# Main function
def main():
    """
    Main function to handle command-line arguments, process the Excel and CSV files,
    generate new rows, and then append them to the CSV.
    """
    # Check if the script received the correct number of arguments
    if len(sys.argv) != 3:
        print("Usage: python script.py <excel_file.xlsx> <csv_file.csv>")
        sys.exit(1)
    
    # Get file paths from the command-line arguments
    excel_path = sys.argv[1]
    csv_path = sys.argv[2]
    
    # Process the Excel file and create the dictionary
    print(f"Reading Excel file: {excel_path}")
    dictionary = create_dictionary_from_excel(excel_path)
    
    # If dictionary is None, stop processing
    if dictionary is None:
        print("Exiting due to error in dictionary creation.")
        sys.exit(1)
    
    # Load the CSV file
    df_csv = pd.read_csv(csv_path)
    
    # Step 1: Generate new rows based on the dictionary
    new_rows = generate_new_rows(df_csv, dictionary)
    
    # Step 2: Append the new rows to the CSV
    print(f"Updating CSV file: {csv_path}")
    append_new_rows_to_csv(csv_path, new_rows)

if __name__ == "__main__":
    main()
