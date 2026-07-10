import pandas as pd
import sys
import os
import re

def convert_seconds_to_time(seconds: int) -> str:
    """Convert integer seconds to hh:mm:ss format."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02}:{m:02}:{s:02}"

def extract_time_from_sequence(seq: str) -> str:
    """Extract last 6 digits from Sequence Frame Number and convert to hh:mm:ss.
       If not exactly 6 digits, return 00:00:00."""
    match = re.search(r"(\d{6})$", str(seq))
    if match:
        return convert_seconds_to_time(int(match.group(1)))
    return "00:00:00"

def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <excel_file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        sys.exit(1)

    # Load Excel
    df = pd.read_excel(file_path)

    # Update column in place
    df["Time the brand is at screen"] = df["Sequence Frame Number"].apply(extract_time_from_sequence)

    # Overwrite same file
    with pd.ExcelWriter(file_path, engine="openpyxl", mode="w") as writer:
        df.to_excel(writer, index=False)

    print(f"✅ File updated successfully: {file_path}")

if __name__ == "__main__":
    main()
