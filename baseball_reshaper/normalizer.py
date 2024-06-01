import pandas as pd
import sys

# Check if the file path is provided as an argument
if len(sys.argv) != 2:
    print("Usage: python update_excel.py <path_to_excel_file>")
    sys.exit(1)

# Get the file path from the command line argument
file_path = sys.argv[1]

# Load the Excel file
xls = pd.ExcelFile(file_path)

# Load the Homeplate sheet into a DataFrame
df = xls.parse('Homeplate')

# Function to get the most common value in a series
def majority_vote(series):
    return series.value_counts().idxmax()

# Group by 'Sequence Frame Number'
grouped = df.groupby('Sequence Frame Number')

# Initialize lists to track changes
player_changes = []
inning_changes = []

# Process each group
for name, group in grouped:
    if group['Player'].nunique() > 1:
        most_common_player = majority_vote(group['Player'])
        if (group['Player'] != most_common_player).any():
            player_changes.append((name, group['Player'].tolist(), most_common_player))
            df.loc[df['Sequence Frame Number'] == name, 'Player'] = most_common_player
    if group['Inning'].nunique() > 1:
        most_common_inning = majority_vote(group['Inning'])
        if (group['Inning'] != most_common_inning).any():
            inning_changes.append((name, group['Inning'].tolist(), most_common_inning))
            df.loc[df['Sequence Frame Number'] == name, 'Inning'] = most_common_inning

# Print the changes
print("Player Changes:")
for change in player_changes:
    print(f"Sequence Frame Number: {change[0]} | Original: {change[1]} | Changed to: {change[2]}")

print("\nInning Changes:")
for change in inning_changes:
    print(f"Sequence Frame Number: {change[0]} | Original: {change[1]} | Changed to: {change[2]}")

# Save the updated DataFrame back to the Homeplate sheet
with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
    df.to_excel(writer, sheet_name='Homeplate', index=False)
