import sys
import pandas as pd
import os

def brand_duration_summary(df, label):
    summary = df.groupby('Brand')['Duration'].sum().reset_index()
    print(f"\n>>> Brand duration summary ({label}) <<<")
    grand_total = summary['Duration'].sum()
    for _, row in summary.iterrows():
        print(f"Brand: {row['Brand']:30} Total Duration: {row['Duration']}")
    print(f"GRAND TOTAL (all shown brands): {grand_total}\n")

def main():
    file1, file2 = sys.argv[1], sys.argv[2]
    base2 = os.path.splitext(file2)[0]
    outname = f"{base2}_concatenated_output.xlsx"

    # Detect 'addendum'
    if 'addendum' in file1.lower():
        addendum_file, other_file = file1, file2
    elif 'addendum' in file2.lower():
        addendum_file, other_file = file2, file1
    else:
        raise ValueError("No 'addendum' in any filename!")

    keep_locations = ["Playing Kit - Shirt Front", "Playing Kit - Arm"]
    df_add = pd.read_excel(addendum_file)
    df_main = pd.read_excel(other_file)
    df_add = df_add[df_add['Location'].isin(keep_locations)].copy()
    df_main = df_main[df_main['Location'].isin(keep_locations)].copy()

    # Merge: keep the one with greater Duration in the same (Brand, Location, Sequence Frame Number) group
    merge_keys = ['Brand', 'Location', 'Sequence Frame Number']

    # Merge and keep max Duration per group
    merged = pd.concat([df_add, df_main], ignore_index=True)
    # For audit, find out-of-order replacement
    merged['_row_source'] = merged.index.map(lambda x: 'addendum' if x < len(df_add) else 'original')
    merged_sorted = merged.sort_values(merge_keys + ['Duration'], ascending=[True, True, True, False])

    # Keep only the row with the largest Duration for any duplicate triplet
    merged_final = merged_sorted.drop_duplicates(subset=merge_keys, keep='first').drop(columns='_row_source')

    # Optional audit: find replacements (where both addendum and original have same Brand/Loc/Frame, and Duration differs)
    audit_duplicates = pd.merge(
        df_main, df_add, on=merge_keys, suffixes=('_orig', '_add')
    )
    differing = audit_duplicates[audit_duplicates['Duration_add'] != audit_duplicates['Duration_orig']]
    if not differing.empty:
        print("\nRows where entry with bigger Duration was kept due to differing durations for (Brand, Location, Frame):")
        for _, row in differing.iterrows():
            kept = row['Duration_add'] if row['Duration_add'] > row['Duration_orig'] else row['Duration_orig']
            print(f"Brand: {row['Brand']}, Location: {row['Location']}, Frame: {row['Sequence Frame Number']}, "
                  f"Addendum Duration: {row['Duration_add']}, Original Duration: {row['Duration_orig']}, "
                  f"Kept Duration: {kept}")
        increases = differing[differing['Duration_add'] > differing['Duration_orig']]
        print(f"\nNumber of (Brand, Location, Frame) overlaps where Duration increased (Kept > Original): {len(increases)}")
        print(f"Total added Duration from these increases: {increases['Duration_add'].sum() - increases['Duration_orig'].sum()}")
    else:
        print("\nNo overlapping (Brand, Location, Frame) entries with differing Duration found.")

    # Output and summary
    merged_final.to_excel(outname, index=False)
    print(f"\n> Concatenated output written to {outname}")

    print(f'\nRows in original (filtered second file): {len(df_main)}')
    print(f'Rows in addendum (filtered): {len(df_add)}')
    print(f'Rows in output (merged): {len(merged_final)}')
    print(f"Unique (Brand, Location, Frame) in merged: {merged_final[merge_keys].drop_duplicates().shape[0]}")

    brand_duration_summary(merged_final, f'CONCATENATED ({os.path.basename(outname)})')
    brand_duration_summary(df_main, f'SECOND INPUT ({os.path.basename(file2)})')

if __name__ == "__main__":
    main()