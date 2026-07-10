"""Load expected brands from project folder (projects/<name>/*.txt) or legacy brands_db/."""
from __future__ import annotations

import os

from .config import ANNOTATION_PROJECT, CURRENT_PROJECT_OVERRIDE


def _project_root() -> str:
    """Root of mcp-annotation-audit (folder that contains src/ and projects/)."""
    # Allow override so MCP can find workspace when run from another cwd/install path
    env_root = os.environ.get("ANNOTATION_PROJECT_ROOT", "").strip()
    if env_root and os.path.isdir(env_root):
        return os.path.abspath(env_root)
    package_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(package_dir))


def _brands_db_dir() -> str:
    """Path to folder with .txt brand files: projects/<project>/ or legacy brands_db/."""
    root = _project_root()
    if CURRENT_PROJECT_OVERRIDE:
        return os.path.join(root, "projects", CURRENT_PROJECT_OVERRIDE.strip())
    if ANNOTATION_PROJECT:
        return os.path.join(root, "projects", ANNOTATION_PROJECT)
    return os.path.join(root, "brands_db")


def list_brands_files() -> list[str]:
    """Return list of available brands file names (without .txt)."""
    db_dir = _brands_db_dir()
    if not os.path.isdir(db_dir):
        return []
    return [
        os.path.splitext(f)[0]
        for f in os.listdir(db_dir)
        if f.endswith(".txt")
    ]


def load_expected_brands(brands_file: str) -> list[str] | None:
    """
    Load expected brands from project folder (or brands_db/) as {brands_file}.txt.
    Lines starting with # are treated as brand names (e.g. #Aramco -> Aramco).
    Returns list of unique brands, or None if file not found / error.
    """
    db_dir = _brands_db_dir()
    # Allow with or without .txt
    base = brands_file.strip()
    if base.endswith(".txt"):
        base = base[:-4]
    path = os.path.join(db_dir, base + ".txt")
    if not os.path.isfile(path):
        return None
    brands = []
    seen = set()
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or not line.startswith("#"):
                    continue
                name = line[1:].strip()
                if not name:
                    continue
                key = name.lower()
                if key not in seen:
                    seen.add(key)
                    brands.append(name)
    except OSError:
        return None
    return brands


def get_project_instructions() -> dict[str, str]:
    """
    Read general instructions (root INSTRUCTIONS.md) and project instructions/audit rules.
    Returns {"general_instructions": root INSTRUCTIONS.md, "instructions": project instructions.txt,
             "audit_rules": project audit_rules.md}.
    """
    root = _project_root()
    out: dict[str, str] = {"general_instructions": "", "instructions": "", "audit_rules": ""}
    # Root: γενικές οδηγίες (report format, no scripts) – ισχύουν για όλα τα projects
    for name in ("INSTRUCTIONS.md", "instructions.txt"):
        path = os.path.join(root, name)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    out["general_instructions"] = f.read().strip()
                break
            except OSError:
                pass
    # Project folder
    d = _brands_db_dir()
    if os.path.isdir(d):
        for name, key in [("instructions.txt", "instructions"), ("audit_rules.md", "audit_rules")]:
            path = os.path.join(d, name)
            if os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        out[key] = f.read().strip()
                except OSError:
                    pass
    return out
