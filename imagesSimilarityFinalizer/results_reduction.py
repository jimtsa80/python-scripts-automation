import pandas as pd
import sys

# Read the file from the command-line argument
if len(sys.argv) < 2:
    print("Usage: python script.py <path_to_excel>")
    sys.exit(1)

file_path = sys.argv[1]
df = pd.read_excel(file_path)

# Check if required columns exist
required_columns = {"Brand", "Location", "Duration"}
if not required_columns.issubset(df.columns):
    print("Missing required columns in the Excel file")
    sys.exit(1)

# Calculate total Duration
total_duration = df["Duration"].sum()
print(f"Total Duration: {total_duration}")

# Get the target duration from the user
try:
    target_duration = float(input("Enter the target total duration: "))
    if target_duration >= total_duration:
        print("Target duration must be less than the current total duration.")
        sys.exit(1)
except ValueError:
    print("Invalid input. Please enter a number.")
    sys.exit(1)

# Store original durations
original_durations = df.copy()

# Compute the reduction amount per row
num_rows = len(df)
reduction_per_row = (total_duration - target_duration) / num_rows

# Apply the reduction and round to integers
df["Duration"] = (df["Duration"] - reduction_per_row).round().astype(int)

# Remove rows where Duration is 0
df = df[df["Duration"] > 0]

# Save the updated file with the same column structure
df.to_excel(file_path.replace(".xlsx", "_reduced.xlsx"), index=False, columns=df.columns)
print(f"Updated file saved as: {file_path.replace('.xlsx', '_reduced.xlsx')}")

# Print the changes
print("Original vs Reduced Durations:")
comparison = original_durations.merge(df, on=["Brand", "Location"], how="left", suffixes=("_original", "_reduced"))
comparison["Reduction"] = comparison["Duration_original"] - comparison["Duration_reduced"].fillna(0).astype(int)
comparison = comparison.dropna(subset=["Duration_reduced"])
print(comparison[["Brand", "Location", "Duration_original", "Duration_reduced", "Reduction"]])
