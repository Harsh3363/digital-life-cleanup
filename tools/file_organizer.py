"""
File Organizer — Sorts files into categorized subfolders.

Organizes a messy folder by moving files into structured subfolders
based on file type, content analysis, and naming patterns.

Categories:
  📄 Documents    — .txt, .md, .rtf, .doc, .docx, .pdf
  🖼️ Images       — .jpg, .jpeg, .png, .gif, .bmp, .tiff, .webp, .svg
  🎬 Videos       — .mp4, .avi, .mkv, .mov, .wmv, .flv, .webm
  🎵 Audio        — .mp3, .wav, .flac, .aac, .ogg, .wma
  📦 Archives     — .zip, .tar, .gz, .bz2, .7z, .rar
  💻 Code         — .py, .js, .ts, .java, .cpp, .c, .h, .go, .rs, .html, .css
  📊 Data         — .csv, .json, .xml, .yaml, .yml, .sql, .db
  📝 Logs         — .log
  💰 Financial    — files matching financial keywords (bank, invoice, tax, salary)
  📋 Work         — resume, meeting, project files
  🔑 Sensitive    — password, API key, credential files
  ❓ Other        — everything else
"""

import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Category Definitions ──────────────────────────────────────────

# Extension-based categories (priority order — first match wins)
EXTENSION_CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
               ".webp", ".svg", ".ico", ".heic", ".heif", ".raw"},
    "Videos": {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm",
               ".m4v", ".3gp", ".bin"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"},
    "Archives": {".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".xz"},
    "Code": {".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".hpp",
             ".go", ".rs", ".html", ".css", ".scss", ".php", ".rb",
             ".swift", ".kt", ".sh", ".bat", ".ps1"},
    "Data": {".csv", ".json", ".xml", ".yaml", ".yml", ".sql", ".db",
             ".sqlite", ".xlsx", ".xls"},
    "Documents": {".txt", ".md", ".rtf", ".doc", ".docx", ".pdf", ".odt",
                  ".tex", ".epub"},
    "Logs": {".log"},
}

# Keyword-based categories (checked against filename, takes priority over extension)
KEYWORD_CATEGORIES = {
    "Financial": ["bank", "invoice", "tax", "salary", "payment", "receipt",
                  "budget", "expense", "financial", "stmt", "ledger", "aadhaar"],
    "Work": ["resume", "cv", "meeting", "project", "report", "proposal",
             "presentation", "agenda", "minutes"],
    "Sensitive": ["password", "passwd", "credential", "secret", "api_key",
                  "apikey", "token", "private_key"],
}


def _classify_file(filename: str, filepath: str) -> str:
    """
    Classify a file into a category based on its name and extension.

    Priority:
    1. Keyword-based (financial, work, sensitive) — by filename
    2. Extension-based (images, code, etc.)
    3. Fallback to "Other"
    """
    name_lower = filename.lower()
    stem_lower = Path(filename).stem.lower()

    # 1. Keyword-based classification (highest priority)
    for category, keywords in KEYWORD_CATEGORIES.items():
        for kw in keywords:
            if kw in stem_lower:
                return category

    # 2. Extension-based classification
    ext = Path(filename).suffix.lower()
    if ext:
        for category, extensions in EXTENSION_CATEGORIES.items():
            if ext in extensions:
                return category

    # 3. Check if file has no extension but looks like a text file
    if not ext:
        try:
            with open(filepath, "rb") as f:
                sample = f.read(512)
            # If mostly printable ASCII, classify as Documents
            printable = sum(1 for b in sample if 32 <= b < 127 or b in (9, 10, 13))
            if len(sample) > 0 and printable / len(sample) > 0.8:
                return "Documents"
        except (IOError, OSError):
            pass

    return "Other"


def _detect_duplicates_in_list(files: List[Dict]) -> Dict[str, List[Dict]]:
    """Group files by stem to detect naming-pattern duplicates."""
    import hashlib

    # Group by content hash
    hash_groups = {}
    for f in files:
        try:
            hasher = hashlib.sha256()
            with open(f["source"], "rb") as fh:
                while True:
                    chunk = fh.read(8192)
                    if not chunk:
                        break
                    hasher.update(chunk)
            h = hasher.hexdigest()
            if h not in hash_groups:
                hash_groups[h] = []
            hash_groups[h].append(f)
        except (IOError, OSError):
            pass

    return hash_groups


def organize_folder(
    folder_path: str,
    dry_run: bool = False,
    handle_duplicates: bool = True,
) -> Dict[str, Any]:
    """
    Organize a messy folder by moving files into categorized subfolders.

    Args:
        folder_path: Path to the folder to organize.
        dry_run: If True, only report what would be done without moving files.
        handle_duplicates: If True, put exact duplicates in a Duplicates subfolder.

    Returns:
        {
            "status": "success",
            "folder_path": str,
            "total_files": int,
            "files_moved": int,
            "categories": {"Images": [...], "Documents": [...], ...},
            "duplicates_found": int,
            "dry_run": bool,
            "moves": [{"source": str, "destination": str, "category": str}, ...],
        }
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        return {"status": "error", "error": f"Not a directory: {folder_path}"}

    logger.info(f"Organizing folder: {folder_path} (dry_run={dry_run})")

    # Collect all files in the top-level directory (don't recurse into already-organized subfolders)
    all_files = []
    for item in folder.iterdir():
        if item.is_file() and not item.name.startswith("."):
            all_files.append({
                "filename": item.name,
                "source": str(item),
                "size": item.stat().st_size,
            })

    if not all_files:
        return {
            "status": "success",
            "folder_path": folder_path,
            "total_files": 0,
            "files_moved": 0,
            "categories": {},
            "duplicates_found": 0,
            "dry_run": dry_run,
            "moves": [],
        }

    # Classify each file
    for f in all_files:
        f["category"] = _classify_file(f["filename"], f["source"])

    # Detect exact duplicates by content hash
    duplicates_found = 0
    if handle_duplicates:
        hash_groups = _detect_duplicates_in_list(all_files)
        for h, group in hash_groups.items():
            if len(group) > 1:
                # Keep the first one in its category, move the rest to Duplicates
                for dup in group[1:]:
                    dup["category"] = "Duplicates"
                    duplicates_found += 1

    # Group files by category
    categories = {}
    for f in all_files:
        cat = f["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(f)

    # Plan and execute moves
    moves = []
    files_moved = 0

    for category, files in sorted(categories.items()):
        # Create category subfolder
        cat_folder = folder / category
        if not dry_run:
            cat_folder.mkdir(exist_ok=True)

        for f in files:
            source = Path(f["source"])
            dest = cat_folder / f["filename"]

            # Handle naming conflicts
            if dest.exists() and not dry_run:
                stem = dest.stem
                ext = dest.suffix
                counter = 1
                while dest.exists():
                    dest = cat_folder / f"{stem}_{counter}{ext}"
                    counter += 1

            move_info = {
                "source": str(source),
                "destination": str(dest),
                "category": category,
                "filename": f["filename"],
                "size_bytes": f["size"],
            }
            moves.append(move_info)

            if not dry_run:
                try:
                    shutil.move(str(source), str(dest))
                    files_moved += 1
                    logger.info(f"  Moved: {f['filename']} → {category}/")
                except (IOError, OSError) as e:
                    move_info["error"] = str(e)
                    logger.warning(f"  Failed to move {f['filename']}: {e}")
            else:
                files_moved += 1  # Count planned moves in dry run

    # Build category summary
    cat_summary = {}
    for cat, files in sorted(categories.items()):
        cat_summary[cat] = {
            "count": len(files),
            "total_size_mb": round(sum(f["size"] for f in files) / (1024 * 1024), 2),
            "files": [f["filename"] for f in files],
        }

    result = {
        "status": "success",
        "folder_path": folder_path,
        "total_files": len(all_files),
        "files_moved": files_moved,
        "categories": cat_summary,
        "duplicates_found": duplicates_found,
        "dry_run": dry_run,
        "moves": moves,
    }

    logger.info(f"Organization complete: {files_moved}/{len(all_files)} files → {len(categories)} categories")
    return result
