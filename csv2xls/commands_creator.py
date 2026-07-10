import os
import re
import pyperclip

# Define the folder path
folder_path = 'csvs'

# Initialize an empty string to store the output
output = ""

# List all files in the folder
csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]

# Generate the output
if csv_files:
    for csv in csv_files:
        split_csv = csv.split("_", 1)
        if len(split_csv) > 1:
            # Extract the part and stop at the first occurrence of '-cluster'
            part1 = split_csv[1].split("-cluster", 1)[0] + "-cluster" + split_csv[1].split("-cluster", 1)[1].split("-")[0]
            part2 = re.sub(r'-cluster_\d{1,2}', '', part1)
            part3 = part2.replace("reduced_", "")

            # Append the generated string to the output variable
            output += f"python addXtraLinesFromSort.py D:\\downloads\\toBeFinalized\\{part3}\\{part2}\\{part1}\\sequences_info_plus.xlsx csvs\\{csv}\n"
        else:
            output += "Unexpected format\n"
else:
    output = "No CSV files found in the folder.\n"

# Copy the output to the clipboard
pyperclip.copy(output)

# Optionally, print the output to confirm
print(output)