"""Google Sheets client: fetch annotation data."""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from .config import (
    ANNOTATION_PROJECT,
    CREDENTIALS_PATH,
    CURRENT_PROJECT_OVERRIDE,
    SHEET_GID_OVERRIDE,
    SHEET_NAME_OR_GID,
    SPREADSHEET_ID,
)


def _get_client() -> gspread.Client:
    if not SPREADSHEET_ID:
        raise ValueError(
            "Set ANNOTATION_SPREADSHEET_ID to your Google Sheet ID. "
            "Example: 1MA5KmcDq4ZsxXH5dWlIz7Tp3r0A9ajcI8VyJkBFtyrU"
        )
    if CREDENTIALS_PATH:
        gc = gspread.service_account(filename=CREDENTIALS_PATH)
    else:
        gc = gspread.service_account()
    return gc


def _get_worksheet(gc: gspread.Client):
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    # When user gave gid from URL (#gid=395374545), open by worksheet ID (reliable)
    if SHEET_GID_OVERRIDE is not None:
        return spreadsheet.get_worksheet_by_id(SHEET_GID_OVERRIDE)
    # Runtime override: user asked explicitly for this tab (e.g. ICC_Rest)
    if CURRENT_PROJECT_OVERRIDE:
        name = CURRENT_PROJECT_OVERRIDE.strip()
        if name.isdigit():
            return spreadsheet.get_worksheet_by_id(int(name))
        return spreadsheet.worksheet(name)
    # Tab = worksheet with the same name as the project (e.g. ANNOTATION_PROJECT=ICC_IND → tab "ICC_IND")
    if ANNOTATION_PROJECT:
        return spreadsheet.worksheet(ANNOTATION_PROJECT)
    if SHEET_NAME_OR_GID:
        if SHEET_NAME_OR_GID.isdigit():
            return spreadsheet.get_worksheet_by_id(int(SHEET_NAME_OR_GID))
        return spreadsheet.worksheet(SHEET_NAME_OR_GID)
    return spreadsheet.sheet1


def get_sheet_data() -> list[list[Any]]:
    """Return full sheet as list of rows (first row = headers)."""
    gc = _get_client()
    wks = _get_worksheet(gc)
    return wks.get_all_values()


def get_records() -> list[dict[str, Any]]:
    """Return sheet as list of dicts (header row = keys)."""
    gc = _get_client()
    wks = _get_worksheet(gc)
    return wks.get_all_records()


def get_headers() -> list[str]:
    """Return first row as headers."""
    data = get_sheet_data()
    if not data:
        return []
    return [str(h).strip() for h in data[0]]


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip()).lower() if s else ""


def find_inconsistencies(records: list[dict], key_columns: list[str] | None = None) -> dict[str, Any]:
    """
    Find likely inconsistencies: same value with different spellings/casing/whitespace.
    If key_columns given (e.g. ['Brand']), group by that and report variants.
    """
    if not records:
        return {"message": "No data", "groups": [], "suggestions": [] }

    headers = list(records[0].keys())
    key_cols = key_columns or []
    if not key_cols and "Brand" in headers:
        key_cols = ["Brand"]
    if not key_cols and "brand" in headers:
        key_cols = ["brand"]
    if not key_cols and headers:
        key_cols = [headers[0]]

    # Group raw values by normalized form
    by_normalized: dict[str, list[str]] = defaultdict(list)
    for r in records:
        for col in key_cols:
            if col not in r:
                continue
            val = (r.get(col) or "").strip()
            if not val:
                continue
            norm = _normalize(val)
            if norm and val not in by_normalized[norm]:
                by_normalized[norm].append(val)

    inconsistencies = []
    for norm, variants in by_normalized.items():
        if len(variants) > 1:
            inconsistencies.append({"normalized": norm, "variants": variants})

    return {
        "total_rows": len(records),
        "columns_checked": key_cols,
        "inconsistencies": inconsistencies,
        "summary": f"Found {len(inconsistencies)} groups with different spellings/casing for the same value.",
    }


def find_missing_brands(
    records: list[dict],
    brand_column: str | None = None,
    expected_brands: list[str] | None = None,
) -> dict[str, Any]:
    """
    Find rows with empty brand and optionally list expected brands that never appear.
    """
    if not records:
        return {"message": "No data", "empty_brand_rows": [], "missing_expected": []}

    headers = list(records[0].keys())
    brand_col = brand_column or "Brand" if "Brand" in headers else (headers[0] if headers else None)
    if not brand_col:
        return {"message": "No brand column found", "headers": headers}

    empty_rows = []
    seen_brands: set[str] = set()
    for i, r in enumerate(records):
        val = (r.get(brand_col) or "").strip()
        if not val:
            empty_rows.append({"row_index": i + 2, "row": r })  # +2 = 1-based + header
        else:
            seen_brands.add(_normalize(val))

    missing_expected = []
    if expected_brands:
        for b in expected_brands:
            if _normalize(b) not in seen_brands:
                missing_expected.append(b)

    return {
        "brand_column": brand_col,
        "total_rows": len(records),
        "empty_brand_count": len(empty_rows),
        "empty_brand_rows": empty_rows[:50],
        "truncated_empty": len(empty_rows) > 50,
        "unique_brands_seen": len(seen_brands),
        "expected_brands_not_found": missing_expected,
    }


def value_counts(records: list[dict], column: str | None = None) -> dict[str, Any]:
    """
    Count rows per value of a column. Returns list of {value, count} sorted by count desc.
    Use for: top N brands, top N locations, etc. Column default: Brand if present else first.
    """
    if not records:
        return {"message": "No data", "counts": []}
    headers = list(records[0].keys())
    col = column if column and column in headers else ("Brand" if "Brand" in headers else (headers[0] if headers else None))
    if not col:
        return {"message": "No column found", "headers": headers}
    # Normalize for grouping; keep one raw form per normalized
    raw_by_norm: dict[str, str] = {}
    cnt: dict[str, int] = defaultdict(int)
    for r in records:
        val = (r.get(col) or "").strip()
        if not val:
            cnt[""] += 1
            continue
        norm = _normalize(val)
        raw_by_norm[norm] = val
        cnt[norm] += 1
    counts = [{"value": raw_by_norm.get(k, k), "count": c} for k, c in cnt.items() if k != ""]
    counts.sort(key=lambda x: x["count"], reverse=True)
    return {"column": col, "counts": counts, "empty_count": cnt.get("", 0)}


def inconsistencies_by_group(
    records: list[dict],
    group_column: str | None = None,
    value_column: str | None = None,
) -> dict[str, Any]:
    """
    For each value of group_column (e.g. Brand), report inconsistencies in value_column (e.g. Location):
    same value with different spelling/casing, and count of empty value_column.
    Combine with value_counts to answer e.g. 'do top 3 brands have Location mismatch?'.
    """
    if not records:
        return {"message": "No data", "by_group": []}
    headers = list(records[0].keys())
    gc = group_column if group_column and group_column in headers else ("Brand" if "Brand" in headers else headers[0])
    vc = value_column if value_column and value_column in headers else ("Location" if "Location" in headers else None)
    if not vc:
        return {"message": "value_column not found", "headers": headers}
    groups: dict[str, list[dict]] = defaultdict(list)
    raw_name: dict[str, str] = {}
    for r in records:
        g = (r.get(gc) or "").strip()
        if not g:
            continue
        key = _normalize(g)
        raw_name[key] = g
        groups[key].append(r)
    result = []
    for norm, rows in groups.items():
        empty = sum(1 for r in rows if not (r.get(vc) or "").strip())
        by_norm: dict[str, list[str]] = defaultdict(list)
        for r in rows:
            val = (r.get(vc) or "").strip()
            if not val:
                continue
            kn = _normalize(val)
            if val not in by_norm[kn]:
                by_norm[kn].append(val)
        inconsistencies = [{"normalized": k, "variants": v} for k, v in by_norm.items() if len(v) > 1]
        result.append({
            "group_value": raw_name.get(norm, norm),
            "empty_count": empty,
            "inconsistencies": inconsistencies,
            "has_mismatch": empty > 0 or len(inconsistencies) > 0,
        })
    result.sort(key=lambda x: x["group_value"].lower())
    return {"group_column": gc, "value_column": vc, "by_group": result}


def build_report(records: list[dict]) -> str:
    """Generate a short text report for the annotation sheet."""
    if not records:
        return "No data in sheet."

    inc = find_inconsistencies(records)
    miss = find_missing_brands(records)
    lines = [
        "# Annotation audit report",
        "",
        f"- Total rows: {len(records)}",
        f"- Inconsistencies (same value, different spelling/case): {len(inc.get('inconsistencies', []))}",
        f"- Rows with empty brand: {miss.get('empty_brand_count', 0)}",
        "",
    ]
    if inc.get("inconsistencies"):
        lines.append("## Inconsistencies")
        for g in inc["inconsistencies"][:20]:
            lines.append(f"- '{g['normalized']}' → variants: {g['variants']}")
        if len(inc["inconsistencies"]) > 20:
            lines.append(f"- ... and {len(inc['inconsistencies']) - 20} more")
        lines.append("")
    if miss.get("empty_brand_count", 0) > 0:
        lines.append("## Sample rows with missing brand")
        for r in (miss.get("empty_brand_rows") or [])[:10]:
            lines.append(f"- Row {r['row_index']}: {r['row']}")
    return "\n".join(lines)
