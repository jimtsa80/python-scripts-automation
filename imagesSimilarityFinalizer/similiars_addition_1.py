import pandas as pd
import sys
import os
import re

def process_files(first_xlsx, second_xlsx, social_mode=False):
    # Load the first Excel file
    df1 = pd.read_excel(first_xlsx)
    df1.columns = ["Representative Image", "Similar Images"]
    
    # Load the second Excel file
    df2 = pd.read_excel(second_xlsx)
    
    # Find the column containing "Duration"
    duration_col = None
    for col in df2.columns:
        if "duration" in col.lower():  # Case-insensitive search for duration column
            duration_col = col
            break

    if duration_col is None:
        print("⚠ Warning: No 'Duration' column found in the dataset.")
    else:
        initial_duration_sum = df2[duration_col].sum()  # Sum of duration before processing
    
    # Strip file extensions from "Representative Image"
    df1["Representative Image"] = df1["Representative Image"].str.replace(r"\.[a-zA-Z0-9]+$", "", regex=True)
    
    # Create a DataFrame to store the updated rows
    updated_rows = []
    match_count = 0
    new_entry_count = 0

    # Iterate over the first file
    for _, row in df1.iterrows():
        representative = row["Representative Image"]
        similar_images = row["Similar Images"].split(", ")  # Handle multiple similar images
        
        if social_mode:
            # Social mode: Exact string match
            matching_rows = df2[df2.iloc[:, -1].astype(str) == representative]
        else:
            # New mode: Ignore leading zeros for matching
            matching_rows = df2[df2.iloc[:, -1].astype(str).str.lstrip("0") == representative.lstrip("0")]
        
        # Update and duplicate matching rows
        for _, match_row in matching_rows.iterrows():
            updated_rows.append(match_row.copy())  # Keep the original entry
            match_count += 1
            
            for sim_img in similar_images:
                new_row = match_row.copy()
                new_row.iloc[-1] = re.sub(r"\.[a-zA-Z0-9]+$", "", sim_img)  # Remove file extension from last column
                updated_rows.append(new_row)
                new_entry_count += 1
    
    # Create a DataFrame with the updated rows
    updated_df = pd.DataFrame(updated_rows, columns=df2.columns)

    # Ensure last column does not have file extensions
    updated_df.iloc[:, -1] = updated_df.iloc[:, -1].astype(str).str.replace(r"\.[a-zA-Z0-9]+$", "", regex=True)
    
    # Merge with original data to retain all rows
    if not updated_df.empty:
        combined_df = pd.concat([df2, updated_df])
    else:
        combined_df = df2.copy()
    
    last_col = df2.columns[-1]  # Get the last column name

    if not social_mode:
        # Remove leading zeros and sort numerically in non-social mode
        combined_df[last_col] = combined_df[last_col].astype(str).str.lstrip("0")
        combined_df[last_col] = pd.to_numeric(combined_df[last_col], errors="coerce")
        combined_df = combined_df.sort_values(by=last_col)

    # Calculate new duration sum if the column exists
    if duration_col:
        new_duration_sum = combined_df[duration_col].sum()
    else:
        new_duration_sum = "N/A"

    # Generate output filename
    output_xlsx = os.path.join(os.path.dirname(second_xlsx), f"final_{os.path.basename(second_xlsx)}")

    # Save to a new Excel file
    combined_df.to_excel(output_xlsx, index=False)
    
    # Print summary
    print(f"✅ Output saved to {output_xlsx}")
    print(f"🔹 Total lines updated: {match_count}")
    print(f"🔹 New entries added: {new_entry_count}")
    print(f"🔹 Total rows in final file: {len(combined_df)}")

    if duration_col:
        print(f"⏳ Initial 'Duration' sum: {initial_duration_sum}")
        print(f"⏳ New 'Duration' sum after updates: {new_duration_sum}")

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python script.py first.xlsx second.xlsx [-social]")
        sys.exit(1)
    
    first_xlsx = sys.argv[1]
    second_xlsx = sys.argv[2]
    social_mode = "-social" in sys.argv  # Check if the -social argument is provided
    
    process_files(first_xlsx, second_xlsx, social_mode)
