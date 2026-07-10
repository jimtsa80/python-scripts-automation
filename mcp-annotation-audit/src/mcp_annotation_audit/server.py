"""
MCP server for annotation audit: query Google Sheets, find inconsistencies, missing brands, reports.
"""
from __future__ import annotations

import json
from mcp.server.fastmcp import FastMCP

from . import config
from . import sheet_client
from . import brands_db

mcp = FastMCP(
    "Annotation Audit",
    json_response=True,
)


def _safe_get_records():
    try:
        return sheet_client.get_records()
    except Exception as e:
        return {"error": str(e), "records": []}


@mcp.tool()
def annotation_use_project(project: str = "", sheet_gid: str = "") -> str:
    """
    Set which sheet tab (and project folder) to use for all subsequent tool calls.
    Call this first when the user explicitly asks for a specific tab (e.g. ICC_Rest) or gives a URL with #gid=...
    project: project folder name and fallback tab name, e.g. "ICC_Rest" (used for projects/<project>/ and for tab if sheet_gid empty).
    sheet_gid: worksheet ID from the URL (#gid=395374545). When set, the worksheet is opened by ID so the correct tab is used even if its name differs.
    """
    try:
        config.CURRENT_PROJECT_OVERRIDE = project.strip() or None
        gid_str = sheet_gid.strip()
        if gid_str and gid_str.isdigit():
            config.SHEET_GID_OVERRIDE = int(gid_str)
        else:
            config.SHEET_GID_OVERRIDE = None
        msg = f"Using tab/folder: {config.CURRENT_PROJECT_OVERRIDE or '(cleared)'}"
        if config.SHEET_GID_OVERRIDE is not None:
            msg += f", sheet by gid={config.SHEET_GID_OVERRIDE}"
        return json.dumps({
            "project": config.CURRENT_PROJECT_OVERRIDE or "(cleared)",
            "sheet_gid": config.SHEET_GID_OVERRIDE,
            "message": msg,
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def annotation_get_schema() -> str:
    """
    Return the column headers (first row) of the annotation spreadsheet.
    Use this to know which columns exist before querying or auditing.
    """
    try:
        headers = sheet_client.get_headers()
        return json.dumps({"headers": headers, "count": len(headers)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def annotation_get_summary() -> str:
    """
    Return a short summary of the annotation data: row count, column names, and sample row.
    """
    try:
        data = sheet_client.get_sheet_data()
        if not data:
            return json.dumps({"message": "Sheet is empty"})
        headers = [str(h).strip() for h in data[0]]
        sample = data[1] if len(data) > 1 else []
        row_count = len(data) - 1
        return json.dumps({
            "row_count": row_count,
            "headers": headers,
            "sample_row": dict(zip(headers, sample)) if headers and sample else None,
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def annotation_find_inconsistencies(key_columns: str = "") -> str:
    """
    Find large inconsistencies: same logical value with different spelling, casing, or whitespace.
    key_columns: comma-separated column names to check (e.g. "Brand,Annotator"). If empty, uses Brand or first column.
    Returns groups of variants that should probably be unified.
    """
    try:
        records = sheet_client.get_records()
        if isinstance(records, dict) and "error" in records:
            return json.dumps(records)
        cols = [c.strip() for c in key_columns.split(",") if c.strip()] or None
        result = sheet_client.find_inconsistencies(records, key_columns=cols)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def annotation_get_instructions() -> str:
    """
    Return general instructions (root INSTRUCTIONS.md) and project instructions + audit_rules (projects/<name>/).
    Call this first so the LLM knows report format (missing brands, deviations by brand/location/brand·location, priority by duration) and project-specific rules.
    """
    try:
        from .config import ANNOTATION_PROJECT, CURRENT_PROJECT_OVERRIDE
        data = brands_db.get_project_instructions()
        data["project"] = CURRENT_PROJECT_OVERRIDE or ANNOTATION_PROJECT or "(none; using SHEET_NAME_OR_GID / brands_db)"
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def annotation_list_brands_files() -> str:
    """
    List available .txt brand files in the current project folder (projects/<name>/) or legacy brands_db/.
    Use the returned name in annotation_find_missing_brands(brands_file=...).
    """
    try:
        files = brands_db.list_brands_files()
        return json.dumps({"brands_files": files, "usage": "Use brands_file='2026_ICC_T20' (or another name) in annotation_find_missing_brands"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def annotation_find_missing_brands(
    brand_column: str = "",
    expected_brands: str = "",
    brands_file: str = "",
) -> str:
    """
    Find rows with missing/empty brand and optionally which expected brands never appear.
    brand_column: name of the column that holds the brand (default: Brand or first column).
    expected_brands: comma-separated list of brands (e.g. "Dunlop,Super2"). Ignored if brands_file is set.
    brands_file: load expected brands from project folder (or brands_db/) as {brands_file}.txt. Use annotation_list_brands_files to see available files.
    """
    try:
        records = sheet_client.get_records()
        if isinstance(records, dict) and "error" in records:
            return json.dumps(records)
        expected = None
        if brands_file.strip():
            expected = brands_db.load_expected_brands(brands_file.strip())
            if expected is None:
                available = brands_db.list_brands_files()
                return json.dumps({
                    "error": f"Brands file '{brands_file.strip()}' not found in project folder (or brands_db/)",
                    "available_brands_files": available,
                })
        if expected is None and expected_brands:
            expected = [b.strip() for b in expected_brands.split(",") if b.strip()] or None
        result = sheet_client.find_missing_brands(
            records,
            brand_column=brand_column.strip() or None,
            expected_brands=expected,
        )
        if brands_file.strip():
            result["expected_brands_source"] = f"project folder (or brands_db)/{brands_file.strip()}.txt"
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def annotation_value_counts(column: str = "") -> str:
    """
    Count rows per value of a column (default: Brand). Returns value + count sorted by count desc.
    Use to get e.g. top brands by appearances, then combine with other tools for the rest of the question.
    """
    try:
        records = sheet_client.get_records()
        if isinstance(records, dict) and "error" in records:
            return json.dumps(records)
        result = sheet_client.value_counts(records, column=column.strip() or None)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def annotation_inconsistencies_by_group(
    group_column: str = "",
    value_column: str = "",
) -> str:
    """
    For each value of group_column (e.g. Brand), report inconsistencies in value_column (e.g. Location):
    same value with different spelling/casing, and empty count. Combine with annotation_value_counts to
    answer e.g. 'do top 3 brands have Location mismatch?' (value_counts(Brand) -> top 3, then check
    these in by_group from this tool).
    """
    try:
        records = sheet_client.get_records()
        if isinstance(records, dict) and "error" in records:
            return json.dumps(records)
        result = sheet_client.inconsistencies_by_group(
            records,
            group_column=group_column.strip() or None,
            value_column=value_column.strip() or None,
        )
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def annotation_get_expected_brands(brands_file: str = "") -> str:
    """
    Return the list of expected brand names from project folder (or brands_db/) as {brands_file}.txt.
    Use with annotation_get_data so the LLM can do per-match or other analysis (grouping, missing, minimal) in reasoning.
    """
    try:
        if not brands_file.strip():
            return json.dumps({"error": "Provide brands_file.", "available": brands_db.list_brands_files()})
        expected = brands_db.load_expected_brands(brands_file.strip())
        if expected is None:
            return json.dumps({"error": f"File '{brands_file.strip()}' not found in project folder (or brands_db).", "available": brands_db.list_brands_files()})
        return json.dumps({"brands_file": brands_file.strip(), "expected_brands": expected})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def annotation_audit_report() -> str:
    """
    Generate a full audit report: inconsistencies, missing brands, and sample problematic rows.
    Returns markdown-style text suitable for review.
    """
    try:
        records = sheet_client.get_records()
        if isinstance(records, dict) and "error" in records:
            return json.dumps(records)
        report = sheet_client.build_report(records)
        return report
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def annotation_query(
    filter_column: str = "",
    filter_value: str = "",
    max_rows: int = 100,
) -> str:
    """
    Query annotation data: return rows where a column equals (or contains) a value.
    filter_column: header name to filter on (e.g. Brand, Annotator).
    filter_value: value to match (case-insensitive substring match if no exact match).
    max_rows: maximum number of rows to return (default 100).
    """
    try:
        records = sheet_client.get_records()
        if isinstance(records, dict) and "error" in records:
            return json.dumps(records)
        if not filter_column or not filter_value:
            return json.dumps({
                "message": "Provide filter_column and filter_value",
                "sample_headers": list(records[0].keys()) if records else [],
            })
        key = filter_column.strip()
        val = filter_value.strip().lower()
        if key not in (records[0].keys() if records else []):
            return json.dumps({"error": f"Column '{key}' not found", "headers": list(records[0].keys()) if records else []})
        matched = []
        for r in records:
            cell = (r.get(key) or "").strip().lower()
            if val in cell or cell == val:
                matched.append(r)
                if len(matched) >= max_rows:
                    break
        return json.dumps({
            "filter_column": key,
            "filter_value": filter_value.strip(),
            "count": len(matched),
            "truncated": len(matched) == max_rows,
            "rows": matched,
        }, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def annotation_get_data(max_rows: int = 500, columns: str = "") -> str:
    """
    Return annotation rows as JSON. Use columns to limit payload (e.g. "Brand,Location").
    max_rows: cap (default 500). columns: comma-separated column names; empty = all columns.
    Combine with other tools to answer questions without pulling full data when not needed.
    """
    try:
        records = sheet_client.get_records()
        if isinstance(records, dict) and "error" in records:
            return json.dumps(records)
        if columns.strip():
            want = [c.strip() for c in columns.split(",") if c.strip()]
            headers = list(records[0].keys()) if records else []
            allowed = [h for h in want if h in headers]
            if allowed:
                records = [{k: r.get(k) for k in allowed} for r in records]
        truncated = records[:max_rows]
        return json.dumps({
            "total_available": len(records),
            "returned": len(truncated),
            "truncated": len(records) > max_rows,
            "data": truncated,
        }, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def run():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run()
