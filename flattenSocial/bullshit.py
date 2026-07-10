import pandas as pd
import random
import re
import chardet

# File paths
txt_file = "filenames.txt"
xlsx_file = "20250120_Tennis_Facebook_Images.xlsx"
sheet_name = "Sheet1"  # Adjust if necessary

# Detect file encoding
with open(txt_file, "rb") as file:
    raw_data = file.read()
detected = chardet.detect(raw_data)
encoding = detected["encoding"]

# Read filenames from txt with detected encoding
with open(txt_file, "r", encoding=encoding) as file:
    filenames = file.read().splitlines()

# Create a mapping of base filenames to full filenames
filename_mapping = {}
for name in filenames:
    match = re.match(r"(.*)\.(\d+)$", name)
    if match:
        base_name, number = match.groups()
        filename_mapping.setdefault(base_name, []).append(name)

# Read Excel file
df = pd.read_excel(xlsx_file, sheet_name=sheet_name)

# Add a new column to store matched filenames
df["Matched Filename"] = None

# Find matching rows
matching_indices = [i for i, val in df["Sequence Frame Number"].items() if val in filename_mapping]

# Shuffle and select 80% to modify
random.shuffle(matching_indices)
num_to_change = int(len(matching_indices) * 0.8)
indices_to_change = set(matching_indices[:num_to_change])

# Update the new column with corresponding filenames from txt
for i in indices_to_change:
    base_name = df.at[i, "Sequence Frame Number"]
    if base_name in filename_mapping:
        df.at[i, "Matched Filename"] = random.choice(filename_mapping[base_name])

# Save the modified file
df.to_excel("updated_data.xlsx", index=False)
