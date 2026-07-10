"""Configuration from environment."""
import os

# Google Sheet: ID from the URL (docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit...).
# Default = results spreadsheet; override with ANNOTATION_SPREADSHEET_ID if needed.
SPREADSHEET_ID = os.environ.get(
    "ANNOTATION_SPREADSHEET_ID",
    "1MA5KmcDq4ZsxXH5dWlIz7Tp3r0A9ajcI8VyJkBFtyrU",
)
# Project folder name = sheet tab name. Each project lives in projects/<ANNOTATION_PROJECT>/ (instructions, .txt, rules).
# When set, the server reads from that tab and from that folder. When empty, uses SHEET_NAME_OR_GID / legacy brands_db.
ANNOTATION_PROJECT = os.environ.get("ANNOTATION_PROJECT", "").strip()
# Optional: sheet by name or gid. Used only when ANNOTATION_PROJECT is empty.
SHEET_NAME_OR_GID = os.environ.get("ANNOTATION_SHEET_NAME_OR_GID", "ICC_Rest")
# Path to service account JSON. Or use default gspread location: ~/.config/gspread/service_account.json
CREDENTIALS_PATH = os.environ.get("GSPREAD_CREDENTIALS", "")
# Root folder of mcp-annotation-audit (contains src/ and projects/). Set ANNOTATION_PROJECT_ROOT if the MCP
# runs from another cwd/install so that projects/<name>/*.txt and audit_rules are found.
# E.g. ANNOTATION_PROJECT_ROOT=F:\cursor\python-scripts-automation\mcp-annotation-audit

# Runtime override: when set (e.g. by annotation_use_project("ICC_Rest")), all tools use this tab and project folder.
# Lets the user explicitly request a tab (e.g. ICC_Rest) regardless of ANNOTATION_PROJECT env.
CURRENT_PROJECT_OVERRIDE: str | None = None
# When set (e.g. sheet_gid=395374545 from URL #gid=395374545), open worksheet by ID instead of by name.
# Use this when the tab name and the desired tab differ (e.g. user gives gid from the URL).
SHEET_GID_OVERRIDE: int | None = None
