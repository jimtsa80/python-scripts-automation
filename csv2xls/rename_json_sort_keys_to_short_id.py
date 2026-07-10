"""
Μαζική επεξεργασία annotation JSON: μετονομασία κλειδιών/ονομάτων εικόνας
από μορφή sort_XXXXX_YYYYYY σε μόνο το YYYYYY (τελευταίο τμήμα μετά το τελευταίο _).

Παραδείγματα:
  sort_00171_005524 -> 005524

Ενημερώνει:
  - κλειδιά στο .images
  - imageName σε κάθε εγγραφή εικόνας
  - currentImage αν ταιριάζει

Χρήση:
  python rename_json_sort_keys_to_short_id.py "F:\\path\\to\\folder" --recursive
  python rename_json_sort_keys_to_short_id.py "*.json"
  python rename_json_sort_keys_to_short_id.py file.json --dry-run
"""
from __future__ import annotations

import argparse
import glob as glob_module
import json
import sys
from pathlib import Path


def short_id(name: str) -> str:
    """sort_XXXXX_YYYYYY -> YYYYYY (αφαιρεί prefix από sort μέχρι και το 2ο _)."""
    if name.startswith("sort_"):
        parts = name.split("_", 2)
        if len(parts) == 3 and parts[2]:
            return parts[2]
    if name and "_" in name:
        return name.rsplit("_", 1)[-1]
    return name


def transform_payload(data: dict) -> tuple[dict, int, list[str]]:
    """
    Επιστρέφει (νέο dict, αριθμός αλλαγών, λίστα αφαιρεθέντων κλειδιών).
    Σε σύγκρουση νέων κλειδιών κρατά το πρώτο και αφαιρεί το δεύτερο.
    """
    if not isinstance(data, dict) or "images" not in data:
        return data, 0, []

    images = data.get("images")
    if not isinstance(images, dict):
        return data, 0, []

    old_keys = list(images.keys())
    mapping: dict[str, str] = {}
    new_to_old: dict[str, str] = {}
    dropped: list[tuple[str, str, str]] = []
    for k in old_keys:
        new_k = short_id(k)
        if new_k in new_to_old and new_to_old[new_k] != k:
            dropped.append((k, new_to_old[new_k], new_k))
            continue
        new_to_old[new_k] = k
        mapping[k] = new_k

    new_images: dict = {}
    changes = 0
    for old_k, obj in images.items():
        if old_k not in mapping:
            continue
        new_k = mapping[old_k]
        if new_k != old_k:
            changes += 1
        if isinstance(obj, dict) and obj.get("imageName") == old_k:
            obj = {**obj, "imageName": new_k}
            if new_k != old_k:
                changes += 1
        new_images[new_k] = obj

    out = {**data, "images": new_images}

    cur = out.get("currentImage")
    if isinstance(cur, str) and cur in mapping:
        new_cur = mapping[cur]
        if new_cur != cur:
            out["currentImage"] = new_cur
            changes += 1

    return out, changes, dropped


def process_file(path: Path, *, dry_run: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        print(f"  [skip] όχι object στη ρίζα: {path}", file=sys.stderr)
        return False
    new_data, n, dropped = transform_payload(data)
    if dropped:
        for dropped_key, kept_key, new_id in dropped:
            print(
                f"  [προειδοποίηση] {path.name}: αφαιρέθηκε '{dropped_key}' "
                f"(κρατήθηκε '{kept_key}' -> '{new_id}')",
                file=sys.stderr,
            )
    if n == 0 and not dropped:
        print(f"  [ok] καμία αλλαγή: {path}")
        return True
    msg = f"  [ok] {n} αλλαγές"
    if dropped:
        msg += f", {len(dropped)} αφαιρέθηκαν"
    print(f"{msg}: {path}")
    if dry_run:
        return True
    path.write_text(json.dumps(new_data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return True


def iter_json_files(paths: list[Path], recursive: bool) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_file() and p.suffix.lower() == ".json":
            out.append(p)
        elif p.is_dir():
            if recursive:
                out.extend(sorted(p.rglob("*.json")))
            else:
                out.extend(sorted(p.glob("*.json")))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Μετονομασία sort_*_* κλειδιών σε short id σε JSON.")
    ap.add_argument(
        "inputs",
        nargs="+",
        help="Αρχεία .json, φάκελοι, ή glob (σε quotes στο shell)",
    )
    ap.add_argument("-r", "--recursive", action="store_true", help="Αναδρομικά σε υποφακέλους (για φακέλους)")
    ap.add_argument("-n", "--dry-run", action="store_true", help="Μόνο εμφάνιση, χωρίς εγγραφή")
    args = ap.parse_args()

    expanded: list[Path] = []
    for raw in args.inputs:
        s = str(raw)
        if "*" in s or "?" in s:
            matches = glob_module.glob(s, recursive="**" in s)
            if not matches:
                matches = glob_module.glob(str(Path.cwd() / s))
            expanded.extend(Path(p) for p in matches)
        else:
            expanded.append(Path(raw))

    files = iter_json_files(expanded, args.recursive)
    if not files:
        print("Δεν βρέθηκαν .json αρχεία.", file=sys.stderr)
        return 1

    ok = 0
    for f in files:
        if process_file(f, dry_run=args.dry_run):
            ok += 1
    print(f"Τέλος: {ok}/{len(files)} αρχεία επεξεργάστηκαν χωρίς σφάλμα.")
    return 0 if ok == len(files) else 2


if __name__ == "__main__":
    raise SystemExit(main())
