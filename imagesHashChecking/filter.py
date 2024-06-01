import pandas as pd

# Load the XLSX file
file_path = 'output.xlsx' 
df = pd.read_excel(file_path, sheet_name='all')

# Get the counts of each value in the 'Hash' column
hash_counts = df['Hash'].value_counts()

# Filter the dataframe to keep only rows where the 'Hash' value occurs more than once
df_multiple_hashes = df[df['Hash'].isin(hash_counts[hash_counts > 1].index)]

# Further filter to keep only rows where the 'Image Name' starts with 'WRC' for at least one entry in the same hash group
filtered_hashes = df_multiple_hashes.groupby('Hash').filter(lambda x: x['Image Name'].str.startswith('WRC').any())

# Save the filtered dataframe to a new Excel file
filtered_file_path = 'output_filtered.xlsx'
filtered_hashes.to_excel(filtered_file_path, index=False)

print(f"Filtered file saved to {filtered_file_path}")

