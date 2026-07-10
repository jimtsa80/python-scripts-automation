#!/usr/bin/env python3
"""
Υπολογίζει τον «εργάσιμο» χρόνο μεταξύ annotations σε JSON export του annotation tool.

Λογική:
- Υπολογίζονται τα κενά χρόνου (gaps) μεταξύ διαδοχικών timestamps.
- Αν ένα gap είναι <= 10 λεπτά, προστίθεται στον εργάσιμο χρόνο.
- Αν ένα gap είναι > 10 λεπτά, θεωρείται idle-time και ΔΕΝ προστίθεται στον εργάσιμο χρόνο.

Δέχεται: μεμονωμένο .json αρχείο ή φάκελο με .json αρχεία.
Εκτύπωση: αρχείο -> εργάσιμος χρόνος (HH:MM:SS).
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


def collect_timestamps(data):
    """Συλλέγει όλα τα timestamp από annotations σε όλες τις εικόνες."""
    timestamps = []
    images = data.get("images") or {}
    for img_key, img_data in images.items():
        for ann in (img_data.get("annotations") or []):
            ts = ann.get("timestamp")
            if ts:
                timestamps.append(ts)
    return timestamps


def parse_iso(ts_str):
    """Parse ISO timestamp, υποστηρίζει και μικρό αριθμό δευτερολέπτων."""
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except Exception:
        return None


def elapsed_seconds(timestamps):
    """
    Δίνει (first_ts, last_ts, working_seconds) με βάση gaps μεταξύ διαδοχικών timestamps.

    - Αν υπάρχουν < 2 έγκυρα timestamps, duration = 0.
    - Για κάθε gap:
        * gap <= 10 λεπτά -> μετράει ως εργάσιμος χρόνος
        * gap > 10 λεπτά  -> μετράει ως idle-time (δεν προστίθεται στον εργάσιμο χρόνο)
    """
    if not timestamps:
        return None, None, None
    parsed = []
    for ts in timestamps:
        dt = parse_iso(ts)
        if dt is not None:
            parsed.append(dt)
    if not parsed:
        return None, None, None
    # Ταξινόμηση για ασφαλή υπολογισμό διαδοχικών gaps
    parsed.sort()
    first = parsed[0]
    last = parsed[-1]

    working_seconds = 0
    ten_minutes = 10 * 60

    for prev, curr in zip(parsed, parsed[1:]):
        gap = (curr - prev).total_seconds()
        if gap <= ten_minutes:
            working_seconds += gap
        # αλλιώς gap θεωρείται idle-time και δεν προστίθεται

    return first, last, working_seconds


def format_duration(seconds):
    """Μορφή HH:MM:SS."""
    if seconds is None or seconds < 0:
        return "N/A"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def process_file(path):
    """Επεξεργασία ενός JSON αρχείου. Επιστρέφει (display_name, duration_sec, err)."""
    path = Path(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return path.name, None, str(e)
    timestamps = collect_timestamps(data)
    first, last, duration = elapsed_seconds(timestamps)
    if duration is None:
        return path.name, None, "no valid timestamps"
    return path.name, duration, None


def extract_tag_between_hyphens(filename):
    """Επιστρέφει το τμήμα μεταξύ 1ου και 2ου '-' (π.χ. ..._1650-GT-260225-... -> GT)."""
    parts = filename.split("-", 2)
    return parts[1].strip() if len(parts) >= 3 else ""


def export_xlsx(rows, out_path):
    """Εγγραφή λίστας (filename, duration_sec, tag) σε xlsx με στήλες Αρχείο, Χρόνος, Τιμή."""
    if not HAS_OPENPYXL:
        print("Για export xlsx: pip install openpyxl")
        return False
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Χρόνοι"
    ws.append(["Αρχείο", "Χρόνος", "Τιμή"])
    header_font = Font(bold=True)
    for c in range(1, 4):
        ws.cell(row=1, column=c).font = header_font
        ws.cell(row=1, column=c).alignment = Alignment(horizontal="center")
    for name, sec, tag in rows:
        dur_str = format_duration(sec)
        ws.append([name, dur_str, tag])
    out_path = Path(out_path)
    if out_path.suffix.lower() != ".xlsx":
        out_path = out_path.with_suffix(".xlsx")
    wb.save(out_path)
    print(f"\nΕξαγωγή: {out_path.resolve()}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Υπολογισμός χρόνου μεταξύ 1ου και τελευταίου entry σε JSON annotation exports."
    )
    parser.add_argument(
        "input",
        help="Μεμονωμένο .json αρχείο ή φάκελος με .json αρχεία",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Εμφάνιση πρώτου/τελευταίου timestamp και σφαλμάτων",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Εξαγωγή αποτελεσμάτων σε αρχείο .xlsx (Αρχείο, Χρόνος, Τιμή)",
    )
    args = parser.parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Σφάλμα: δεν υπάρχει: {input_path}")
        return 1

    if input_path.is_file():
        files = [input_path]
    else:
        files = sorted(input_path.glob("*.json"))

    if not files:
        print("Δεν βρέθηκαν .json αρχεία.")
        return 1

    results = []
    for fpath in files:
        name, duration_sec, err = process_file(fpath)
        if err:
            if args.verbose:
                print(f"{name} -> Σφάλμα: {err}")
            else:
                print(f"{name} -> N/A")
            continue
        dur_str = format_duration(duration_sec)
        tag = extract_tag_between_hyphens(name)
        print(f"{name} -> {dur_str}")
        results.append((name, duration_sec, tag))

    if args.output and results:
        export_xlsx(results, args.output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
