#!/usr/bin/env python3
"""
Suggest ICC brand thresholds from --debug logs (and optional ground truth).

Usage:
  # From log file (save debug output: python icc_template_matcher.py ... --debug 2>&1 | tee debug.log)
  python suggest_icc_thresholds.py debug.log

  # With ground truth (CSV: image_name_or_stem,brand) - best results
  python suggest_icc_thresholds.py debug.log --ground-truth truth.csv

  # Pipe directly
  python icc_template_matcher.py ... --debug 2>&1 | python suggest_icc_thresholds.py -

Ground truth CSV format (optional):
  image_stem,brand
  001234,Emirates
  001235,Aramco
  001236,

(Empty brand = no logo in that image.)
"""

import re
import sys
from pathlib import Path
from collections import defaultdict


# Image name (no spaces), then brand (one or more words), then [zone], best: x (threshold y, gap z)
DEBUG_LINE = re.compile(
    r"^\s*\[debug\]\s+(\S+)\s+(.+?)\s+\[([^\]]+)\]\s+best:\s+([\d.]+)\s+\(threshold\s+([\d.]+),\s+gap\s+([+-][\d.]+)\)"
)


def parse_debug_log(lines):
    """Parse debug lines. Returns list of (image_stem, brand, zone, best_val, threshold, gap)."""
    results = []
    for line in lines:
        line = line.strip()
        if "[debug]" not in line:
            continue
        m = DEBUG_LINE.search(line)
        if not m:
            # Try looser: image name may have spaces; brand may have spaces
            parts = line.split()
            if len(parts) < 8:
                continue
            try:
                # ... [debug] 001234.jpg Google [bottom_right] best: 0.420 (threshold 0.45, gap +0.03)
                idx = next(i for i, p in enumerate(parts) if p == "[debug]")
                img = parts[idx + 1].rstrip(",")
                brand = parts[idx + 2]
                # If next is not zone, brand might be "DP World" etc
                if parts[idx + 3] != "[":
                    brand = brand + " " + parts[idx + 3]
                    zone_start = idx + 4
                else:
                    zone_start = idx + 3
                zone = "".join(parts[zone_start])  # [zone_name]
                best_val = float(parts[parts.index("best:") + 1].rstrip(")"))
                th_str = next(p for p in parts if p.startswith("threshold"))
                th = float(th_str.replace("threshold", "").strip("()"))
                results.append((Path(img).stem, brand, zone, best_val, th, 0.0))
            except (ValueError, StopIteration):
                continue
            continue
        img_name, brand, zone, best_s, th_s, gap_s = m.groups()
        image_stem = Path(img_name).stem
        brand = brand.strip()
        best_val = float(best_s)
        th = float(th_s)
        gap = float(gap_s)
        results.append((image_stem, brand, zone, best_val, th, gap))
    return results


def load_ground_truth(path):
    """Load CSV: image_stem,brand. Returns dict image_stem -> brand (or '' for no logo)."""
    truth = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",", 1)
            stem = Path(parts[0].strip()).stem
            brand = parts[1].strip() if len(parts) > 1 else ""
            truth[stem] = brand
    return truth


def suggest_with_ground_truth(records, truth):
    """Suggest threshold per brand using ground truth."""
    # records: (image_stem, brand, zone, best_val, threshold, gap)
    # truth: image_stem -> true_brand (empty = no logo)
    by_brand = defaultdict(list)  # brand -> [(image_stem, best_val, is_positive)]
    for (stem, brand, zone, best_val, th, gap) in records:
        true_brand = truth.get(stem, None)
        is_positive = true_brand is not None and brand.lower() == true_brand.lower()
        by_brand[brand].append((stem, best_val, is_positive))

    suggestions = {}
    for brand in sorted(by_brand.keys()):
        entries = by_brand[brand]
        positives = [e[1] for e in entries if e[2]]
        negatives = [e[1] for e in entries if not e[2]]
        if not positives and not negatives:
            continue
        if positives:
            min_when_present = min(positives)
            # To not miss these: threshold must be <= min_when_present
            suggest_low = min_when_present
        else:
            suggest_low = None
        if negatives:
            max_when_absent = max(negatives)
            # To avoid FP: threshold must be > max_when_absent
            suggest_high = max_when_absent
        else:
            suggest_high = None

        if suggest_low is not None and suggest_high is not None:
            if suggest_high < suggest_low:
                # Sweet spot in between
                suggested = round((suggest_high + suggest_low) / 2, 2)
                suggestions[brand] = (suggested, suggest_high, suggest_low, len(positives), len(negatives))
            else:
                # Overlap: can't have both zero FP and zero miss. Prefer no FP: use above max_absent, accept some miss
                suggested = round(suggest_high + 0.02, 2)
                suggestions[brand] = (suggested, suggest_high, suggest_low, len(positives), len(negatives))
        elif suggest_low is not None:
            suggested = round(suggest_low - 0.02, 2)
            suggested = max(0.35, min(0.95, suggested))
            suggestions[brand] = (suggested, None, suggest_low, len(positives), len(negatives))
        elif suggest_high is not None:
            suggested = round(suggest_high + 0.03, 2)
            suggested = max(0.35, min(0.95, suggested))
            suggestions[brand] = (suggested, suggest_high, None, 0, len(negatives))

    return suggestions


def suggest_without_ground_truth(records):
    """Suggest threshold per brand using percentiles (no ground truth)."""
    by_brand = defaultdict(list)
    for (stem, brand, zone, best_val, th, gap) in records:
        by_brand[brand].append(best_val)

    suggestions = {}
    for brand in sorted(by_brand.keys()):
        vals = sorted(by_brand[brand])
        n = len(vals)
        if n == 0:
            continue
        p50 = vals[n // 2]
        p90 = vals[int(n * 0.9)] if n >= 10 else vals[-1]
        min_v, max_v = vals[0], vals[-1]
        # Heuristic: set threshold just below p90 so we "catch" most of the high scores (likely true logos)
        # and above many of the low scores (likely no logo). Without ground truth we can't be precise.
        suggested = round(p90 - 0.03, 2)
        suggested = max(0.35, min(0.95, suggested))
        suggestions[brand] = (suggested, min_v, max_v, p50, p90, n)
    return suggestions


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Suggest ICC thresholds from debug log")
    ap.add_argument("log", nargs="?", default="-", help="Debug log file or - for stdin")
    ap.add_argument("--ground-truth", "-g", help="CSV: image_stem,brand (optional)")
    ap.add_argument("--output", "-o", help="Write suggested thresholds to file (icc_brand_thresholds format)")
    args = ap.parse_args()

    if args.log == "-":
        lines = sys.stdin.readlines()
    else:
        with open(args.log, "r", encoding="utf-8") as f:
            lines = f.readlines()

    records = parse_debug_log(lines)
    if not records:
        print("No [debug] lines found in input. Run icc_template_matcher with --debug and pass the log.")
        return 1

    print(f"Parsed {len(records)} debug lines for {len(set(r[1] for r in records))} brands.\n")

    if args.ground_truth and Path(args.ground_truth).exists():
        truth = load_ground_truth(args.ground_truth)
        print(f"Loaded ground truth for {len(truth)} images.\n")
        suggestions = suggest_with_ground_truth(records, truth)
        print("Suggested thresholds (with ground truth):")
        print("-" * 60)
        for brand, tup in sorted(suggestions.items()):
            suggested, sh, sl, np, nn = tup
            extra = f"  (when present: min={sl}; when absent: max={sh}; +{np}/-{nn})"
            print(f"  {brand}: {suggested}{extra}")
    else:
        if args.ground_truth:
            print("Ground truth file not found; using percentile heuristic.\n")
        suggestions = suggest_without_ground_truth(records)
        print("Suggested thresholds (no ground truth – percentile heuristic):")
        print("-" * 60)
        for brand, tup in sorted(suggestions.items()):
            suggested, min_v, max_v, p50, p90, n = tup
            print(f"  {brand}: {suggested}  (min={min_v:.2f} max={max_v:.2f} p50={p50:.2f} p90={p90:.2f} n={n})")

    # Output file for icc_brand_thresholds.txt
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write("# Suggested by suggest_icc_thresholds.py\n")
            for brand, tup in sorted(suggestions.items()):
                suggested = tup[0]
                f.write(f"{brand}:{suggested}\n")
        print(f"\nWrote {args.output}")
    else:
        print("\nPaste into icc_brand_thresholds.txt or run with -o icc_brand_thresholds.txt")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
