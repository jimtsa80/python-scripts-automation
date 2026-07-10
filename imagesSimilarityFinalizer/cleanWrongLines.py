import pandas as pd
import sys

def main(filename):
    # Load the Excel file
    df = pd.read_excel(filename)
    df.columns = [col.strip() for col in df.columns]
    
    # Make sure these columns are numbers
    df['Duration'] = pd.to_numeric(df['Duration'], errors='coerce')
    df['Sequence Frame Number'] = pd.to_numeric(df['Sequence Frame Number'], errors='coerce')
    
    # To remember which rows to eliminate
    eliminated_indices = []

    # Group by Brand and Location
    for (brand, location), group in df.groupby(['Brand', 'Location']):
        # Sort the group in time order
        group_sorted = group.sort_values(by='Sequence Frame Number')
        # For consecutive pairs
        for i in range(len(group_sorted) - 1):
            current = group_sorted.iloc[i]
            nxt = group_sorted.iloc[i + 1]
            # Compare: frame + duration == next frame
            if (current['Sequence Frame Number'] + current['Duration']) == nxt['Sequence Frame Number']:
                # Mark NEXT row for elimination
                eliminated_indices.append(nxt.name)  # Use .name for original dataframe index

    # Create DataFrame of eliminated rows
    eliminated_rows = df.loc[eliminated_indices]
    # Save to new file
    eliminated_rows.to_excel("eliminated_rows.xlsx", index=False)

    print(f"Eliminated rows saved to eliminated_rows.xlsx")
    print(eliminated_rows)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python script.py yourfile.xlsx")
        sys.exit(1)
    main(sys.argv[1])