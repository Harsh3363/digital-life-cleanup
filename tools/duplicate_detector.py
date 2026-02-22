"""
Duplicate Detector — SHA256 + Partial Hash Support

Pure deterministic tool. No AI/classification logic.
Accomplish decides what to do with the duplicates found.

Features:
  - Full SHA256 hash with streaming (never reads full file into memory)
  - Partial hash mode: first 4KB + last 4KB for fast pre-filtering
  - Groups files by hash and reports duplicate clusters
"""

import hashlib
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CHUNK_SIZE, PARTIAL_HASH_SIZE

logger = logging.getLogger(__name__)


def _stream_hash(filepath: str, chunk_size: int = CHUNK_SIZE) -> Optional[str]:
    """
    Compute SHA256 of a file by streaming in chunks.
    Never loads full file into memory.
    """
    sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                sha256.update(chunk)
        return sha256.hexdigest()
    except (IOError, OSError, PermissionError) as e:
        logger.warning(f"Cannot hash {filepath}: {e}")
        return None


def _partial_hash(filepath: str, partial_size: int = PARTIAL_HASH_SIZE) -> Optional[str]:
    """
    Quick partial hash: reads first `partial_size` bytes + last `partial_size` bytes.
    Used as a fast pre-filter before computing full hashes.
    """
    sha256 = hashlib.sha256()
    try:
        file_size = os.path.getsize(filepath)
        with open(filepath, "rb") as f:
            # Read head
            head = f.read(partial_size)
            sha256.update(head)

            # Read tail (only if file is large enough to have a separate tail)
            if file_size > partial_size * 2:
                f.seek(-partial_size, 2)  # Seek from end
                tail = f.read(partial_size)
                sha256.update(tail)
            elif file_size > partial_size:
                # File is between partial_size and 2*partial_size
                f.seek(partial_size)
                remaining = f.read()
                sha256.update(remaining)

        # Include file size in hash to reduce false positives
        sha256.update(str(file_size).encode())
        return sha256.hexdigest()
    except (IOError, OSError, PermissionError) as e:
        logger.warning(f"Cannot partial-hash {filepath}: {e}")
        return None


def scan_for_duplicates(
    folder_path: str,
    use_partial_hash: bool = True,
    min_size: int = 1
) -> List[Dict]:
    """
    Scan a folder recursively for duplicate files.

    Args:
        folder_path: Root directory to scan.
        use_partial_hash: If True, use partial hash as a pre-filter
                         before computing full hashes (faster for large dirs).
        min_size: Minimum file size in bytes to consider (skip empty files).

    Returns:
        List of duplicate groups, each containing:
        {
            "hash": str,           # SHA256 hash
            "size": int,           # File size in bytes
            "count": int,          # Number of duplicates
            "files": [str, ...]    # List of file paths
        }
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        logger.error(f"Not a valid directory: {folder_path}")
        return []

    logger.info(f"Scanning for duplicates in: {folder_path}")

    # Phase 1: Group files by size (quick filter — different sizes can't be dupes)
    size_groups: Dict[int, List[str]] = {}
    file_count = 0

    for root, _dirs, files in os.walk(folder_path):
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                file_size = os.path.getsize(filepath)
                if file_size >= min_size:
                    size_groups.setdefault(file_size, []).append(filepath)
                    file_count += 1
            except (OSError, PermissionError):
                continue

    logger.info(f"Found {file_count} files, {len(size_groups)} unique sizes")

    # Keep only sizes with multiple files
    candidate_groups = {
        size: paths for size, paths in size_groups.items()
        if len(paths) > 1
    }
    logger.info(f"Size-matched candidate groups: {len(candidate_groups)}")

    # Phase 2: Partial hash pre-filter (optional)
    if use_partial_hash:
        partial_groups: Dict[str, List[Tuple[str, int]]] = {}
        for size, paths in candidate_groups.items():
            for filepath in paths:
                phash = _partial_hash(filepath)
                if phash:
                    partial_groups.setdefault(phash, []).append((filepath, size))

        # Keep only partial-hash groups with multiple files
        hash_candidates = {
            phash: entries for phash, entries in partial_groups.items()
            if len(entries) > 1
        }
        logger.info(f"Partial-hash matched groups: {len(hash_candidates)}")
    else:
        # Without partial hash, use all size-matched candidates
        hash_candidates = {}
        for size, paths in candidate_groups.items():
            for filepath in paths:
                key = f"size_{size}"
                hash_candidates.setdefault(key, []).append((filepath, size))

    # Phase 3: Full SHA256 hash for confirmation
    full_hash_groups: Dict[str, List[Tuple[str, int]]] = {}
    for _key, entries in hash_candidates.items():
        for filepath, size in entries:
            full_hash = _stream_hash(filepath)
            if full_hash:
                full_hash_groups.setdefault(full_hash, []).append((filepath, size))

    # Phase 4: Build result — only groups with actual duplicates
    duplicates = []
    for file_hash, entries in full_hash_groups.items():
        if len(entries) > 1:
            duplicates.append({
                "hash": file_hash,
                "size": entries[0][1],
                "count": len(entries),
                "files": [entry[0] for entry in entries]
            })

    duplicates.sort(key=lambda d: d["size"] * d["count"], reverse=True)
    logger.info(f"Found {len(duplicates)} duplicate groups "
                f"({sum(d['count'] - 1 for d in duplicates)} redundant files)")

    return duplicates


def get_duplicate_summary(duplicates: List[Dict]) -> Dict:
    """
    Generate a summary of duplicate scan results.

    Returns:
        {
            "total_groups": int,
            "total_redundant_files": int,
            "total_wasted_bytes": int,
            "total_wasted_mb": float,
            "groups": [...]
        }
    """
    total_redundant = sum(d["count"] - 1 for d in duplicates)
    total_wasted = sum(d["size"] * (d["count"] - 1) for d in duplicates)

    return {
        "total_groups": len(duplicates),
        "total_redundant_files": total_redundant,
        "total_wasted_bytes": total_wasted,
        "total_wasted_mb": round(total_wasted / (1024 * 1024), 2),
        "groups": duplicates
    }
