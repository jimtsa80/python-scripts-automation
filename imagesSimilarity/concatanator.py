import pandas as pd
import re
import sys
import os

SEQ_COL = "Sequence Frame Number"

# ---------------- Helpers -----------------
def extract_frame(seq: str):
    """Return integer last 6 digits of Sequence Frame Number or None if missing."""
    m = re.search(r'(\d{6})$', str(seq))
    return int(m.group(1)) if m else None

def extract_prefix(seq: str):
    """Return everything before the last 6 digits."""
    return re.sub(r'\d{6}$', '', str(seq))

# ---------------- Main Processing -----------------
def process_file(path: str):
    # Read CSV or Excel
    if path.lower().endswith(".csv"):
        try:
            df = pd.read_csv(path, sep=";", dtype=str, encoding="utf-8")
        except UnicodeDecodeError:
            print("utf-8 failed, trying cp1252 encoding")
            df = pd.read_csv(path, sep=";", dtype=str, encoding="cp1252")
    else:
        df = pd.read_excel(path, dtype=str)

    # Ensure required columns exist
    for col in ["Brand", "Location", SEQ_COL, "Duration", "Total Hits"]:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # Convert Duration and Total Hits to float for summing
    df["Duration"] = df["Duration"].astype(float)
    df["Total Hits"] = df["Total Hits"].astype(float)

    # Extract frame numbers and prefixes
    df["__frame"] = df[SEQ_COL].apply(extract_frame)
    df["__prefix"] = df[SEQ_COL].apply(extract_prefix)

    # Sort for consecutive detection
    df = df.sort_values(["Brand", "Location", "__prefix", "__frame"], kind="stable").reset_index(drop=True)

    merged_rows = []

    # Group by Brand + Location + Prefix
    for (_, _, _), g in df.groupby(["Brand", "Location", "__prefix"], sort=False):
        g = g.reset_index(drop=True)
        i = 0
        while i < len(g):
            start = i
            j = i
            while j + 1 < len(g) and g.loc[j + 1, "__frame"] == g.loc[j, "__frame"] + 1:
                j += 1
            run_len = j - i + 1
            first = g.loc[start].copy()

            # Sum Duration and Total Hits, convert to int string
            first["Duration"] = str(int(sum(g.loc[start:j, "Duration"])))
            first["Total Hits"] = str(int(sum(g.loc[start:j, "Total Hits"])))

            # Keep Sequence Frame Number as first frame
            first[SEQ_COL] = g.loc[start, SEQ_COL]

            # Print debug info when concatenation happens
            if run_len > 1:
                frames = [g.loc[k, SEQ_COL] for k in range(start, j+1)]
                print(f"Concatenating Brand='{first['Brand']}', Location='{first['Location']}', Prefix='{first['__prefix']}'")
                print(f"Frames: {frames} → Duration={first['Duration']}, Total Hits={first['Total Hits']}")

            merged_rows.append(first.to_dict())
            i = j + 1

    out_df = pd.DataFrame(merged_rows)
    out_df.drop(columns=["__frame", "__prefix"], inplace=True)

    # Save back to the same file
    if path.lower().endswith(".csv"):
        out_df.to_csv(path, sep=";", index=False, encoding="utf-8-sig")  # Excel compatible
    else:
        out_df.to_excel(path, index=False)

    print(f"✅ File updated: {path}")

# ---------------- Main Script -----------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python merge_consecutive.py <input_file.csv|xlsx>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: file not found: {file_path}")
        sys.exit(1)

    process_file(file_path)
