import pandas as pd
import sys
import os

def excel_to_txt(excel_path):
    # Get the directory of the input file
    dir_path = os.path.dirname(excel_path)
    
    # Define the output file path
    output_txt_path = os.path.join(dir_path, "output.txt")
    
    with open(output_txt_path, 'w', encoding='utf-8') as txt_file:
        xls = pd.ExcelFile(excel_path)
        
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name, dtype=str, header=None)  # Read as strings, no header
            
            # Flatten the DataFrame to a single list of values, excluding NaNs
            text_data = df.values.flatten()
            text_data = {str(item) for item in text_data if pd.notna(item)}  # Use set to remove duplicates
            
            # Write the sheet name and the unique text to the file
            txt_file.write(f"#{sheet_name}\n")
            txt_file.write("\n".join(sorted(text_data)))  # Sort for consistency
            txt_file.write("\n\n")  # Add spacing between sheets

    print(f"Text extracted and saved to {output_txt_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <path_to_excel>")
        sys.exit(1)
    
    excel_path = sys.argv[1]  # Get file path from command-line argument
    excel_to_txt(excel_path)