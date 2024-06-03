import pandas as pd
import sys
import os

# Check if the file path is provided as an argument
if len(sys.argv) != 2:
    print("Usage: python update_excel.py <path_to_excel_file>")
    sys.exit(1)

# Get the file path from the command line argument
file_path = sys.argv[1]

# Load the Excel file
xls = pd.ExcelFile(file_path)

# Load the Homeplate and NoHomeplate sheets into DataFrames
df_homeplate = xls.parse('Homeplate')
df_nohomeplate = xls.parse('NoHomeplate')

# Function to get the most common value in a series
def majority_vote(series):
    return series.value_counts().idxmax()

# Group by 'Sequence Frame Number'
grouped = df_homeplate.groupby('Sequence Frame Number')

# Initialize lists to track changes
player_changes = []
inning_changes = []

# Process each group
for name, group in grouped:
    if group['Player'].nunique() > 1:
        most_common_player = majority_vote(group['Player'])
        if (group['Player'] != most_common_player).any():
            player_changes.append((name, group['Player'].tolist(), most_common_player))
            df_homeplate.loc[df_homeplate['Sequence Frame Number'] == name, 'Player'] = most_common_player
    if group['Inning'].nunique() > 1:
        most_common_inning = majority_vote(group['Inning'])
        if (group['Inning'] != most_common_inning).any():
            inning_changes.append((name, group['Inning'].tolist(), most_common_inning))
            df_homeplate.loc[df_homeplate['Sequence Frame Number'] == name, 'Inning'] = most_common_inning

# Print the changes
print("Player Changes:")
for change in player_changes:
    print(f"Sequence Frame Number: {change[0]} | Original: {change[1]} | Changed to: {change[2]}")

print("\nInning Changes:")
for change in inning_changes:
    print(f"Sequence Frame Number: {change[0]} | Original: {change[1]} | Changed to: {change[2]}")

# Create the new file path with "final_" prefix
directory, filename = os.path.split(file_path)
new_filename = f"final_{filename}"
new_file_path = os.path.join(directory, new_filename)

# Save the updated DataFrame to the new file, including the NoHomeplate sheet
with pd.ExcelWriter(new_file_path, engine='openpyxl') as writer:
    df_homeplate.to_excel(writer, sheet_name='Homeplate', index=False)
    df_nohomeplate.to_excel(writer, sheet_name='NoHomeplate', index=False)
