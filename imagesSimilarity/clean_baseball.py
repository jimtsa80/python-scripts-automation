"""
Διαγραφή εικόνων εκτός των δοσμένων αριθμητικών ορίων.

Αναγνωρίζει αριθμό από:
  - sort_00031_006166.jpg  → 6166 (τελευταίο τμήμα μετά το _)
  - 00001.jpg, 00002.png   → 1, 2 (καθαρά αριθμητικό όνομα)

Κρατά μόνο αρχεία όπου ο αριθμός ανήκει σε ΟΠΟΙΟΔΗΠΟΤΕ από τα ορίια· διαγράφει τα υπόλοιπα.

Χρήση:
  python clean_baseball.py "F:\\images" --range 1 1000 --range 4000 5000
  python clean_baseball.py "F:\\images" --ranges 1-1000,4000-5000
  python clean_baseball.py "F:\\images" --ranges 1:1000,4000:5000 --dry-run

Batch mode (διαβάζει το clean_ranges.txt με γραμμές: όνομα_φακέλου,start,end):
  python clean_baseball.py --batch "F:\\downloads\\batch17"
  python clean_baseball.py --batch "F:\\downloads\\batch17" --dry-run
  - Για κάθε γραμμή βρίσκει F:\\downloads\\batch17\\<όνομα>\\...\\reduced_<όνομα>
    και καθαρίζει τα ranges στους υποφακέλους του.

    python clean_baseball.py --batch "F:\downloads\batch17" --ranges-file "C:\path\to\clean_ranges.txt"
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

_RANGE_TOKEN = re.compile(r"^\s*(\d+)\s*[-:]\s*(\d+)\s*$")


def _number_from_filename(filename: str) -> int | None:
    stem = os.path.splitext(filename)[0]
    if "_" in stem:
        number_part = stem.rsplit("_", 1)[-1]
    else:
        number_part = stem
    if not number_part.isdigit():
        return None
    return int(number_part.lstrip("0") or "0")


def parse_ranges_csv(text: str) -> list[tuple[int, int]]:
    """Παράδειγμα: '1-1000,4000-5000' ή '1:1000,4000:5000'."""
    out: list[tuple[int, int]] = []
    for token in text.split(","):
        token = token.strip()
        if not token:
            continue
        m = _RANGE_TOKEN.match(token)
        if not m:
            raise ValueError(
                f"Μη έγκυρο όριο '{token}'. Χρησιμοποίησε START-END π.χ. 1-1000"
            )
        out.append(_normalize_range(int(m.group(1)), int(m.group(2))))
    return out


def _normalize_range(start: int, end: int) -> tuple[int, int]:
    if start > end:
        start, end = end, start
    return start, end


def in_any_range(number: int, ranges: list[tuple[int, int]]) -> bool:
    return any(lo <= number <= hi for lo, hi in ranges)


def remove_files_outside_ranges(
    root_folder: str | Path,
    ranges: list[tuple[int, int]],
    *,
    dry_run: bool = False,
    verbose: bool = True,
) -> tuple[int, int]:
    """
    Διαγράφει αρχεία εκτός των ορίων.
    Επιστρέφει (διαγραφές, παραλείψεις/άκυρα ονόματα).
    """
    root = Path(root_folder)
    deleted = 0
    skipped = 0

    for foldername, _subfolders, filenames in os.walk(root):
        for filename in filenames:
            number = _number_from_filename(filename)
            if number is None:
                skipped += 1
                continue

            if in_any_range(number, ranges):
                continue

            file_path = os.path.join(foldername, filename)
            if verbose:
                print(f"{'[dry-run] ' if dry_run else ''}Deleting: {file_path}")
            if not dry_run:
                os.remove(file_path)
            deleted += 1

    return deleted, skipped


def parse_clean_ranges_file(
    path: str | Path,
) -> tuple[list[tuple[str, tuple[int, int]]], list[str]]:
    """
    Διαβάζει το clean_ranges.txt. Κάθε γραμμή: όνομα_φακέλου,start,end
    Επιστρέφει (entries, problems).
    """
    entries: list[tuple[str, tuple[int, int]]] = []
    problems: list[str] = []
    p = Path(path)
    with p.open("r", encoding="utf-8-sig") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line:
                continue
            cols = [c.strip() for c in line.split(",")]
            if len(cols) < 3:
                problems.append(f"Γραμμή {lineno}: λείπουν στήλες -> '{line}'")
                continue
            name = cols[0]
            try:
                start, end = int(cols[1]), int(cols[2])
            except ValueError:
                problems.append(f"Γραμμή {lineno}: μη αριθμητικά όρια -> '{line}'")
                continue
            entries.append((name, _normalize_range(start, end)))
    return entries, problems


def find_reduced_folder(base: Path, name: str) -> Path | None:
    """
    Βρίσκει τον φάκελο reduced_<name> κάτω από base/<name> (αναδρομικά).
    """
    matched = base / name
    if not matched.is_dir():
        return None
    target = f"reduced_{name}"
    if (matched / target).is_dir():
        return matched / target
    for foldername, subfolders, _files in os.walk(matched):
        for sub in subfolders:
            if sub == target:
                return Path(foldername) / sub
    return None


def run_batch(
    batch_path: Path,
    ranges_file: Path,
    *,
    dry_run: bool = False,
) -> int:
    if not batch_path.is_dir():
        print(f"Δεν είναι φάκελος: {batch_path}", file=sys.stderr)
        return 1
    if not ranges_file.is_file():
        print(f"Δεν βρέθηκε το αρχείο ορίων: {ranges_file}", file=sys.stderr)
        return 1

    entries, problems = parse_clean_ranges_file(ranges_file)
    print(f"Πήρα {len(entries)} φακέλους ως είσοδο από: {ranges_file}")
    print(f"Batch path: {batch_path}")
    if dry_run:
        print("(dry-run — χωρίς διαγραφή)")

    processed = 0
    for name, (lo, hi) in entries:
        matched = batch_path / name
        if not matched.is_dir():
            problems.append(f"Δεν βρέθηκε φάκελος: {name}")
            continue

        reduced = find_reduced_folder(batch_path, name)
        if reduced is None:
            problems.append(f"Δεν βρέθηκε reduced_ φάκελος για: {name}")
            continue

        subfolders = sorted(d for d in reduced.iterdir() if d.is_dir())
        targets = subfolders if subfolders else [reduced]

        print(f"\n{name}  (όρια {lo}-{hi})")
        for sub in targets:
            if sub.name == name:
                label = "θα σβηνόταν ολόκληρος" if dry_run else "σβήστηκε ολόκληρος"
                print(f"  {sub.name}: {label}")
                if not dry_run:
                    shutil.rmtree(sub)
                continue
            deleted, _skipped = remove_files_outside_ranges(
                sub, [(lo, hi)], dry_run=dry_run, verbose=False
            )
            label = "θα σβηνόταν" if dry_run else "σβήστηκαν"
            print(f"  {sub.name}: {deleted} εικόνες {label}")
        processed += 1

    print(f"\nΕπεξεργάστηκα {processed}/{len(entries)} φακέλους.")
    if processed != len(entries):
        print("ΠΡΟΣΟΧΗ: δεν επεξεργάστηκαν όλοι οι φάκελοι.")
    if problems:
        print(f"\nΠροβλήματα ({len(problems)}):")
        for prob in problems:
            print(f"  - {prob}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Κράτα εικόνες μόνο μέσα σε ένα ή περισσότερα αριθμητικά όρια."
    )
    p.add_argument(
        "folder",
        type=Path,
        nargs="?",
        help="Ριζικός φάκελος (αναδρομικά). Στο batch mode δεν χρειάζεται.",
    )
    p.add_argument(
        "--batch",
        type=Path,
        metavar="BATCH_PATH",
        help="Batch mode: π.χ. F:\\downloads\\batch17 — διαβάζει το clean_ranges.txt",
    )
    p.add_argument(
        "--ranges-file",
        type=Path,
        default=Path(__file__).with_name("clean_ranges.txt"),
        metavar="FILE",
        help="Αρχείο ορίων για το batch mode (default: clean_ranges.txt δίπλα στο script)",
    )
    p.add_argument(
        "--range",
        nargs=2,
        metavar=("START", "END"),
        type=int,
        action="append",
        default=[],
        help="Όριο κράτησης (επαναλήψιμο). Παράδειγμα: --range 1 1000 --range 4000 5000",
    )
    p.add_argument(
        "--ranges",
        metavar="LIST",
        help="Όλα τα όρια σε μία γραμμή: 1-1000,4000-5000",
    )
    p.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Εμφάνιση διαγραφών χωρίς πραγματική διαγραφή",
    )
    return p


def collect_ranges(args: argparse.Namespace) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    if args.ranges:
        ranges.extend(parse_ranges_csv(args.ranges))
    for pair in args.range or []:
        ranges.append(_normalize_range(pair[0], pair[1]))
    # αφαίρεση διπλότυπων, διατήρηση σειράς
    seen: set[tuple[int, int]] = set()
    unique: list[tuple[int, int]] = []
    for r in ranges:
        if r not in seen:
            seen.add(r)
            unique.append(r)
    return unique


def main() -> int:
    args = build_parser().parse_args()

    if args.batch is not None:
        return run_batch(args.batch, args.ranges_file, dry_run=args.dry_run)

    if args.folder is None:
        print(
            "Δώσε φάκελο + όρια, ή χρησιμοποίησε batch mode:\n"
            '  python clean_baseball.py "F:\\images" --ranges 1-1000\n'
            '  python clean_baseball.py --batch "F:\\downloads\\batch17"',
            file=sys.stderr,
        )
        return 1

    if not args.folder.is_dir():
        print(f"Δεν είναι φάκελος: {args.folder}", file=sys.stderr)
        return 1

    ranges = collect_ranges(args)
    if not ranges:
        print(
            "Δώσε τουλάχιστον ένα όριο:\n"
            "  --range 1 1000 --range 4000 5000\n"
            "  ή --ranges 1-1000,4000-5000",
            file=sys.stderr,
        )
        return 1

    parts = ", ".join(f"{lo}-{hi}" for lo, hi in ranges)
    print(f"Φάκελος: {args.folder}")
    print(f"Κρατάω αριθμούς στα όρια: {parts}")
    if args.dry_run:
        print("(dry-run — χωρίς διαγραφή)")

    deleted, skipped = remove_files_outside_ranges(
        args.folder, ranges, dry_run=args.dry_run
    )
    print(f"Τέλος: {deleted} διαγραφές, {skipped} αρχεία χωρίς έγκυρο id.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
