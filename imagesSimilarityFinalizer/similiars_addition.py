import pandas as pd
import sys
import os
import re

def _split_prefix_and_frame(seq: str):
    """
    Split a sequence frame id like 'Facebook_..._1_000012' into:
      - prefix: 'Facebook_..._1_'  (everything up to and including the last underscore)
      - frame_str: '000012'
      - frame_int: 12  (or None if not numeric)
    """
    if seq is None:
        return None, None, None
    s = str(seq).strip()
    if not s or s.lower() == "nan":
        return None, None, None
    if "_" not in s:
        return s, None, None
    prefix, frame_str = s.rsplit("_", 1)
    prefix = prefix + "_"
    frame_str = frame_str.strip()
    frame_int = None
    if frame_str.isdigit():
        frame_int = int(frame_str)
    return prefix, frame_str, frame_int

def _hhmmss_from_seconds(seconds: int) -> str:
    if seconds is None or pd.isna(seconds):
        return ""
    seconds = int(seconds)
    if seconds < 0:
        seconds = 0
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def _drop_null_like_rows(df: pd.DataFrame, required_cols: list[str]) -> pd.DataFrame:
    # Drop NaNs in required columns
    df2 = df.dropna(subset=[c for c in required_cols if c in df.columns]).copy()
    # Drop blank strings in required columns
    for c in required_cols:
        if c in df2.columns:
            df2 = df2[df2[c].astype(str).str.strip().ne("")]
            df2 = df2[df2[c].astype(str).str.strip().str.lower().ne("nan")]
    return df2

def _recalc_hits_for_duration(df: pd.DataFrame, idx, duration_col: str | None):
    """
    For video rows: keep Average Hits stable, recompute Total Hits = Duration * Average Hits,
    and Average Hits = Total Hits / Duration (so it stays consistent).
    """
    if duration_col is None or duration_col not in df.columns:
        return
    if "Total Hits" not in df.columns or "Average Hits" not in df.columns:
        return
    dur = pd.to_numeric(df.at[idx, duration_col], errors="coerce")
    if pd.isna(dur) or dur <= 0:
        return
    avg = pd.to_numeric(df.at[idx, "Average Hits"], errors="coerce")
    if pd.isna(avg):
        # If avg is missing, try to preserve total by leaving it as-is.
        return
    total = int(round(float(dur) * float(avg)))
    df.at[idx, "Total Hits"] = total
    df.at[idx, "Average Hits"] = round(float(total) / float(dur), 2)

def _collapse_videos_keep_first(df: pd.DataFrame, seq_col: str) -> pd.DataFrame:
    """
    For *_videos datasets:
      - find consecutive frame runs within each (prefix + Brand + Location + Screen Location + Screen Size %)
      - keep ONLY the first row of each consecutive run
      - Duration = sum(Duration) across the run (fallback: run length)
      - Total Hits = sum(Total Hits) across the run (fallback: Duration)
      - Average Hits = Total Hits / Duration
    """
    if df.empty or seq_col not in df.columns:
        return df

    duration_col = None
    for col in df.columns:
        if col.strip().lower() == "duration" or "duration" in col.lower():
            duration_col = col
            break

    key_cols = [c for c in ["Brand", "Location", "Screen Location", "Screen Size %"] if c in df.columns]

    work = df.copy()
    work["_seq_prefix"], work["_seq_frame_str"], work["_seq_frame_int"] = zip(
        *work[seq_col].astype(str).map(_split_prefix_and_frame)
    )
    # Only collapse where frames are parseable
    work["_seq_frame_int"] = pd.to_numeric(work["_seq_frame_int"], errors="coerce")
    parseable = work["_seq_frame_int"].notna()
    if not parseable.any():
        return df

    # Sort within streams for correct run detection
    sort_cols = ["_seq_prefix"] + key_cols + ["_seq_frame_int"]
    for c in key_cols:
        work[c] = work[c].astype(str)
    work = work.sort_values(by=sort_cols, kind="mergesort")

    # Run boundaries: new run if stream changes OR frame not consecutive
    same_stream = (work["_seq_prefix"] == work["_seq_prefix"].shift(1))
    for c in key_cols:
        same_stream &= (work[c] == work[c].shift(1))
    consecutive = (work["_seq_frame_int"] == (work["_seq_frame_int"].shift(1) + 1))
    work["_new_run"] = ~(same_stream & consecutive)
    work["_run_id"] = work["_new_run"].cumsum()

    # Compute aggregations
    if duration_col and duration_col in work.columns:
        dur_num = pd.to_numeric(work[duration_col], errors="coerce")
        run_dur = work.groupby("_run_id")[duration_col].apply(lambda s: pd.to_numeric(s, errors="coerce").sum(min_count=1))
        run_cnt = work.groupby("_run_id")["_seq_frame_int"].count()
        run_dur = run_dur.fillna(run_cnt).astype(int)
    else:
        run_cnt = work.groupby("_run_id")["_seq_frame_int"].count()
        run_dur = run_cnt.astype(int)

    if "Total Hits" in work.columns:
        run_total = work.groupby("_run_id")["Total Hits"].apply(lambda s: pd.to_numeric(s, errors="coerce").sum(min_count=1))
        run_total = run_total.fillna(run_dur).astype(int)
    else:
        run_total = run_dur.astype(int)

    # Keep first row per run
    first_rows = work.groupby("_run_id").head(1).copy()
    first_rows["Duration"] = first_rows["_run_id"].map(run_dur)
    if "Total Hits" in first_rows.columns:
        first_rows["Total Hits"] = first_rows["_run_id"].map(run_total)
    if "Average Hits" in first_rows.columns:
        first_rows["Average Hits"] = (
            first_rows["Total Hits"].astype(float) / first_rows["Duration"].astype(float)
        ).round(2)

    # Drop helper cols
    first_rows = first_rows.drop(columns=[c for c in first_rows.columns if c.startswith("_")], errors="ignore")
    # Preserve original column order
    return first_rows[df.columns]

def _collapse_consecutive_frames(df: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse runs of consecutive frames where Brand/Location/Screen Location/Screen Size % match
    and the Sequence Frame Number shares the same prefix.

    Keeps the LAST row in each run, but:
      - Duration becomes the SUM of Duration across the run (defaults to count if non-numeric)
      - Time the brand is at screen becomes hh:mm:ss derived from the LAST frame number
    """
    if df.empty:
        return df

    seq_col = df.columns[-1]
    duration_col = None
    for col in df.columns:
        if col.strip().lower() == "duration" or "duration" in col.lower():
            duration_col = col
            break

    time_col = None
    for col in df.columns:
        if "time the brand is at screen" in col.lower():
            time_col = col
            break

    # Columns that define "same brand/location/size"
    key_cols = [c for c in ["Brand", "Location", "Screen Location", "Screen Size %"] if c in df.columns]

    work = df.copy()
    work["_seq_prefix"], work["_seq_frame_str"], work["_seq_frame_int"] = zip(
        *work[seq_col].map(_split_prefix_and_frame)
    )

    # If we can't parse frames, skip collapsing
    if work["_seq_frame_int"].isna().all():
        return df

    # Sort within logical streams (prefix + keys) by frame number
    sort_cols = ["_seq_prefix"] + key_cols + ["_seq_frame_int"]
    work = work.sort_values(by=sort_cols, kind="mergesort")  # stable

    # Identify run boundaries: new run if prefix/keys change OR frame is not consecutive
    same_stream = True
    for c in ["_seq_prefix"] + key_cols:
        if c in work.columns:
            same_stream = same_stream & (work[c] == work[c].shift(1))
    consecutive = (work["_seq_frame_int"] == (work["_seq_frame_int"].shift(1) + 1))
    work["_new_run"] = ~(same_stream & consecutive)
    work["_run_id"] = work["_new_run"].cumsum()

    # Duration sum per run
    if duration_col and duration_col in work.columns:
        dur_num = pd.to_numeric(work[duration_col], errors="coerce")
        work["_dur_num"] = dur_num
        run_dur = work.groupby("_run_id")["_dur_num"].sum(min_count=1)
        # If a run has all NaNs in duration, fallback to frame count
        run_cnt = work.groupby("_run_id")["_seq_frame_int"].count()
        run_dur = run_dur.fillna(run_cnt)
    else:
        run_dur = work.groupby("_run_id")["_seq_frame_int"].count()

    # Keep last row in each run
    last_idx = work.groupby("_run_id").tail(1).index
    out = work.loc[last_idx].copy()

    # Apply recomputed duration + time (derived from last frame number)
    if duration_col and duration_col in out.columns:
        out[duration_col] = out["_run_id"].map(run_dur).astype(int)

    if time_col and time_col in out.columns:
        out[time_col] = out["_seq_frame_int"].map(lambda x: _hhmmss_from_seconds(int(x)) if pd.notna(x) else "")

    # Cleanup helper cols
    out = out.drop(columns=[c for c in out.columns if c.startswith("_")], errors="ignore")

    # Restore original column order
    out = out[df.columns]
    return out

def process_files(first_xlsx, second_xlsx, verbose=False, debug_limit=25):
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

    if verbose:
        print(f"📥 Loaded base dataset: {len(df2)} rows, {len(df2.columns)} cols")

    # Capture the true last column name BEFORE we add helper columns
    seq_col = df2.columns[-1]
    base_name = os.path.basename(second_xlsx).lower()
    is_videos = base_name.endswith("_videos.xlsx") or base_name.endswith("_videos.xls") or base_name.endswith("_videos.csv") or base_name.endswith("_videos")

    # Drop null/blank rows early (requested)
    required_cols = ["Brand", "Location", "Screen Location", "Screen Size %", seq_col]
    before_drop = len(df2)
    df2 = _drop_null_like_rows(df2, required_cols)
    if verbose and before_drop != len(df2):
        print(f"🧹 Dropped null/blank rows from base dataset: {before_drop - len(df2)}")
    
    # Strip file extensions from "Representative Image"
    df1["Representative Image"] = df1["Representative Image"].str.replace(r"\.[a-zA-Z0-9]+$", "", regex=True)
    
    # Create a DataFrame to store the updated rows
    updated_rows = []
    match_count = 0
    new_entry_count = 0

    # Prepare helpers for collision detection / targeted merging (ONLY for added rows)
    duration_col = None
    for col in df2.columns:
        if col.strip().lower() == "duration" or "duration" in col.lower():
            duration_col = col
            break
    time_col = None
    for col in df2.columns:
        if "time the brand is at screen" in col.lower():
            time_col = col
            break
    key_cols = [c for c in ["Brand", "Location", "Screen Location", "Screen Size %"] if c in df2.columns]

    # Build an index of existing rows by (prefix, frame_int, keys) so we can skip duplicates
    df2 = df2.copy()
    df2["_seq_prefix"], _, df2["_seq_frame_int"] = zip(*df2[seq_col].map(_split_prefix_and_frame))
    for c in key_cols:
        df2[c] = df2[c].astype(str)
    # Build a per-row key: prefix|frame_int|Brand|Location|Screen Location|Screen Size %
    if key_cols:
        df2["_keys_joined"] = df2[key_cols].astype(str).agg("|".join, axis=1)
    else:
        df2["_keys_joined"] = ""
    df2["_row_key"] = (
        df2["_seq_prefix"].astype(str)
        + "|"
        + df2["_seq_frame_int"].astype("Int64").astype(str)
        + "|"
        + df2["_keys_joined"].astype(str)
    )
    key_to_idx = {}
    for idx, k in zip(df2.index.tolist(), df2["_row_key"].tolist()):
        if k not in key_to_idx:
            key_to_idx[k] = idx

    # Debug counters
    skipped_duplicates = 0
    merged_into_prev = 0
    added_new = 0
    added_fallback_unparsed = 0
    debug_shown = 0

    # Iterate over the first file
    for _, row in df1.iterrows():
        representative = row["Representative Image"]
        similar_images = row["Similar Images"].split(", ")  # Handle multiple similar images
        
        rep_prefix, rep_frame_str, rep_frame_int = _split_prefix_and_frame(representative)
        seq_series = df2[seq_col].astype(str)
        # Always match by prefix + numeric frame (last part after last '_'), ignoring leading zeros in that frame part.
        if rep_prefix and rep_frame_int is not None:
            prefixes, _, frames = zip(*seq_series.map(_split_prefix_and_frame))
            tmp = df2.copy()
            tmp["_p"] = prefixes
            tmp["_f"] = frames
            matching_rows = tmp[(tmp["_p"] == rep_prefix) & (tmp["_f"] == rep_frame_int)].drop(columns=["_p", "_f"])
        else:
            matching_rows = df2[seq_series == str(representative)]
        
        # Update and duplicate matching rows
        for _, match_row in matching_rows.iterrows():
            # Count matches but DO NOT duplicate the original row (it's already in df2)
            match_count += 1
            
            for sim_img in similar_images:
                sim_clean = re.sub(r"\.[a-zA-Z0-9]+$", "", sim_img)  # Remove file extension from last column
                sim_prefix, sim_frame_str, sim_frame_int = _split_prefix_and_frame(sim_clean)

                # If we can't parse frame, just add it as a new row (legacy)
                if sim_prefix is None or sim_frame_int is None:
                    new_row = match_row.copy()
                    new_row.iloc[-1] = sim_clean
                    updated_rows.append(new_row)
                    new_entry_count += 1
                    added_fallback_unparsed += 1
                    continue

                # Build row key for duplicate/collision checks
                parts = [sim_prefix, str(sim_frame_int)]
                for c in key_cols:
                    parts.append(str(match_row.get(c, "")))
                row_key = "|".join(parts)

                # If this exact frame+keys already exists, skip adding
                if row_key in key_to_idx:
                    skipped_duplicates += 1
                    continue

                # If previous consecutive frame exists with same keys+prefix, extend that row's duration and move it to this frame
                prev_parts = [sim_prefix, str(sim_frame_int - 1)]
                for c in key_cols:
                    prev_parts.append(str(match_row.get(c, "")))
                prev_key = "|".join(prev_parts)
                prev_idx = key_to_idx.get(prev_key)

                if prev_idx is not None and duration_col and duration_col in df2.columns:
                    # Extend duration (+1) on the existing row.
                    # For *_videos: keep ONLY the first line (do NOT move Sequence/Time forward), just extend duration/hits.
                    # For *_images: legacy behavior is to move the row to the latest frame/time.
                    df2.at[prev_idx, duration_col] = int(pd.to_numeric(df2.at[prev_idx, duration_col], errors="coerce") or 0) + 1
                    if is_videos:
                        _recalc_hits_for_duration(df2, prev_idx, duration_col)
                    else:
                        df2.at[prev_idx, seq_col] = f"{sim_prefix}{sim_frame_str}"
                        if time_col and time_col in df2.columns:
                            df2.at[prev_idx, time_col] = _hhmmss_from_seconds(sim_frame_int)

                    # Update key index: this consolidated row now represents the latest frame too
                    key_to_idx[row_key] = prev_idx
                    merged_into_prev += 1
                    if verbose and debug_shown < debug_limit:
                        mode = "videos" if is_videos else "images"
                        print(f"🔁 MERGE +1s ({mode}): {sim_prefix}{sim_frame_str} (extended prev frame {sim_frame_int-1})")
                        debug_shown += 1
                    continue

                # Otherwise create a NEW entry (added row) with duration=1 and time derived from frame
                new_row = match_row.copy()
                new_row[seq_col] = f"{sim_prefix}{sim_frame_str}"
                if duration_col and duration_col in df2.columns:
                    new_row[duration_col] = 1
                if time_col and time_col in df2.columns:
                    # For videos, keep time as the frame's time (first occurrence).
                    # For images, this is still fine as a per-frame time.
                    new_row[time_col] = _hhmmss_from_seconds(sim_frame_int)
                if is_videos:
                    # Ensure Total/Average hits align to duration=1
                    # (Total = 1 * Average, Average stays same)
                    try:
                        avg = pd.to_numeric(new_row.get("Average Hits", None), errors="coerce")
                        if pd.notna(avg):
                            new_row["Total Hits"] = int(round(float(avg)))
                            new_row["Average Hits"] = float(new_row["Total Hits"]) / 1.0
                    except Exception:
                        pass
                updated_rows.append(new_row)
                new_entry_count += 1
                added_new += 1
                if verbose and debug_shown < debug_limit:
                    print(f"➕ ADD 1s:   {sim_prefix}{sim_frame_str}")
                    debug_shown += 1
    
    # Create a DataFrame with the updated rows
    # Ensure we only keep the original output columns (no helper columns)
    base_output_cols = [c for c in df2.columns if not c.startswith("_")]
    updated_df = pd.DataFrame(updated_rows, columns=base_output_cols)

    # Ensure last column does not have file extensions
    updated_df.iloc[:, -1] = updated_df.iloc[:, -1].astype(str).str.replace(r"\.[a-zA-Z0-9]+$", "", regex=True)
    
    # Merge with original data to retain all rows
    if not updated_df.empty:
        # df2 may have been modified in-place by collision merges above
        combined_df = pd.concat([df2[base_output_cols], updated_df])
    else:
        combined_df = df2[base_output_cols].copy()
    
    last_col = seq_col  # True last column name from the original dataset

    # Only sort numerically for videos/images (safe for both)
    if True:
        # Remove leading zeros and sort numerically in non-social mode
        # Sort by prefix + numeric frame, not by full-string numeric conversion
        combined_df["_seq_prefix"], _, combined_df["_seq_frame_int"] = zip(
            *combined_df[last_col].astype(str).map(_split_prefix_and_frame)
        )
        combined_df = combined_df.sort_values(by=["_seq_prefix", "_seq_frame_int"], kind="mergesort")
        combined_df = combined_df.drop(columns=["_seq_prefix", "_seq_frame_int"], errors="ignore")

    # For *_videos: collapse consecutive runs everywhere (not only for collisions)
    if is_videos:
        before_rows = len(combined_df)
        combined_df = _collapse_videos_keep_first(combined_df, seq_col)
        if verbose:
            print(f"🧩 Collapsed consecutive video runs: {before_rows} -> {len(combined_df)} rows")

    # Drop null/blank rows again after expansion/collapse (requested)
    combined_df = _drop_null_like_rows(combined_df, required_cols)

    # Final sort: last column ascending (by prefix, then numeric frame)
    if seq_col in combined_df.columns:
        combined_df["_seq_prefix"], _, combined_df["_seq_frame_int"] = zip(
            *combined_df[seq_col].astype(str).map(_split_prefix_and_frame)
        )
        combined_df["_seq_frame_int"] = pd.to_numeric(combined_df["_seq_frame_int"], errors="coerce")
        combined_df = combined_df.sort_values(by=["_seq_prefix", "_seq_frame_int"], kind="mergesort")
        combined_df = combined_df.drop(columns=["_seq_prefix", "_seq_frame_int"], errors="ignore")

    # Calculate new duration sum if the column exists
    if duration_col:
        new_duration_sum = combined_df[duration_col].sum()
    else:
        new_duration_sum = "N/A"

    # Format Average Hits to 2 decimals (requested)
    if "Average Hits" in combined_df.columns:
        combined_df["Average Hits"] = pd.to_numeric(combined_df["Average Hits"], errors="coerce").round(2)

    # Generate output filename
    output_xlsx = os.path.join(os.path.dirname(second_xlsx), f"final_{os.path.basename(second_xlsx)}")

    # Save to a new Excel file
    combined_df.to_excel(output_xlsx, index=False)
    
    # Print summary
    print(f"✅ Output saved to {output_xlsx}")
    print(f"🔹 Total lines updated: {match_count}")
    print(f"🔹 New entries added: {new_entry_count}")
    print(f"🔹 Total rows in final file: {len(combined_df)}")
    if verbose:
        print("🧾 Similar-frame processing summary:")
        print(f"   - skipped duplicates (already existed): {skipped_duplicates}")
        print(f"   - merged into previous consecutive frame: {merged_into_prev}")
        print(f"   - added new (duration=1): {added_new}")
        print(f"   - added fallback (unparsed frame id): {added_fallback_unparsed}")

    if duration_col:
        print(f"⏳ Initial 'Duration' sum: {initial_duration_sum}")
        print(f"⏳ New 'Duration' sum after updates: {new_duration_sum}")

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python script.py similar_images_info.xlsx dataset.xlsx [-v]")
        sys.exit(1)
    
    first_xlsx = sys.argv[1]
    second_xlsx = sys.argv[2]
    verbose = "-v" in sys.argv
    
    process_files(first_xlsx, second_xlsx, verbose=verbose)
