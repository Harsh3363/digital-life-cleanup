"""
Large File Handler — Size-Based Streaming Compression

Pure deterministic tool. No AI/classification logic.
Accomplish decides which files to compress.

Features:
  - Identifies files above configurable threshold
  - Compresses using gzip with streaming (8KB chunks)
  - Never reads full file into memory
  - Returns compression stats (original, compressed, ratio)
"""

import gzip
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CHUNK_SIZE, LARGE_FILE_THRESHOLD, DEFAULT_OUTPUT_DIR

logger = logging.getLogger(__name__)


def find_large_files(
    folder_path: str,
    threshold_bytes: int = LARGE_FILE_THRESHOLD,
) -> List[Dict[str, Any]]:
    """
    Scan a folder recursively and find files above the size threshold.

    Args:
        folder_path: Root directory to scan.
        threshold_bytes: Size threshold in bytes (default: 100MB).

    Returns:
        List of large file entries:
        [
            {
                "path": str,
                "filename": str,
                "size_bytes": int,
                "size_mb": float,
                "extension": str,
                "last_modified": str
            }
        ]
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        logger.error(f"Not a valid directory: {folder_path}")
        return []

    logger.info(f"Scanning for large files (>{threshold_bytes // (1024*1024)}MB) in: {folder_path}")
    large_files = []

    for root, _dirs, files in os.walk(folder_path):
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                file_size = os.path.getsize(filepath)
                if file_size >= threshold_bytes:
                    large_files.append({
                        "path": filepath,
                        "filename": filename,
                        "size_bytes": file_size,
                        "size_mb": round(file_size / (1024 * 1024), 2),
                        "extension": Path(filename).suffix.lower(),
                        "last_modified": datetime.fromtimestamp(
                            os.path.getmtime(filepath)
                        ).isoformat(),
                    })
            except (OSError, PermissionError):
                continue

    large_files.sort(key=lambda f: f["size_bytes"], reverse=True)
    logger.info(f"Found {len(large_files)} large files")
    return large_files


def compress_file(
    filepath: str,
    output_dir: Optional[str] = None,
    chunk_size: int = CHUNK_SIZE,
    compression_level: int = 6,
) -> Dict[str, Any]:
    """
    Compress a file using gzip with streaming (never loads full file into memory).

    Args:
        filepath: Path to the file to compress.
        output_dir: Directory for the compressed file. Defaults to project output dir.
        chunk_size: Read chunk size in bytes (default: 8KB).
        compression_level: gzip compression level 1-9 (default: 6).

    Returns:
        {
            "original_path": str,
            "compressed_path": str,
            "original_size": int,
            "compressed_size": int,
            "original_size_mb": float,
            "compressed_size_mb": float,
            "compression_ratio": float,
            "space_saved_mb": float,
            "timestamp": str
        }
    """
    if not os.path.isfile(filepath):
        logger.error(f"File not found: {filepath}")
        return {"error": f"File not found: {filepath}"}

    # Resolve output directory
    if output_dir is None:
        out_dir = DEFAULT_OUTPUT_DIR
    else:
        out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    original_name = os.path.basename(filepath)
    compressed_path = out_dir / f"{original_name}.gz"
    original_size = os.path.getsize(filepath)

    logger.info(f"Compressing: {filepath} ({original_size} bytes)")

    try:
        bytes_read = 0
        with open(filepath, "rb") as f_in:
            with gzip.open(str(compressed_path), "wb", compresslevel=compression_level) as f_out:
                while True:
                    chunk = f_in.read(chunk_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    bytes_read += len(chunk)

        compressed_size = os.path.getsize(compressed_path)
        ratio = round(compressed_size / original_size, 4) if original_size > 0 else 0
        saved = original_size - compressed_size

        result = {
            "original_path": filepath,
            "compressed_path": str(compressed_path),
            "original_size": original_size,
            "compressed_size": compressed_size,
            "original_size_mb": round(original_size / (1024 * 1024), 2),
            "compressed_size_mb": round(compressed_size / (1024 * 1024), 2),
            "compression_ratio": ratio,
            "space_saved_bytes": saved,
            "space_saved_mb": round(saved / (1024 * 1024), 2),
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(
            f"Compressed: {original_name} → {compressed_size} bytes "
            f"(ratio: {ratio}, saved: {saved} bytes)"
        )
        return result

    except Exception as e:
        logger.error(f"Compression failed for {filepath}: {e}")
        return {"error": str(e), "original_path": filepath}


def compress_large_files(
    folder_path: str,
    threshold_bytes: int = LARGE_FILE_THRESHOLD,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Find and compress all large files in a folder.

    Args:
        folder_path: Root directory to scan.
        threshold_bytes: Size threshold in bytes.
        output_dir: Directory for compressed files.

    Returns:
        {
            "total_files_found": int,
            "total_files_compressed": int,
            "total_original_size_mb": float,
            "total_compressed_size_mb": float,
            "total_space_saved_mb": float,
            "files": [...]
        }
    """
    large_files = find_large_files(folder_path, threshold_bytes)
    if not large_files:
        return {
            "total_files_found": 0,
            "total_files_compressed": 0,
            "total_original_size_mb": 0,
            "total_compressed_size_mb": 0,
            "total_space_saved_mb": 0,
            "files": [],
        }

    results = []
    for file_info in large_files:
        result = compress_file(file_info["path"], output_dir=output_dir)
        results.append(result)

    total_original = sum(r.get("original_size", 0) for r in results if "error" not in r)
    total_compressed = sum(r.get("compressed_size", 0) for r in results if "error" not in r)
    successful = [r for r in results if "error" not in r]

    return {
        "total_files_found": len(large_files),
        "total_files_compressed": len(successful),
        "total_original_size_mb": round(total_original / (1024 * 1024), 2),
        "total_compressed_size_mb": round(total_compressed / (1024 * 1024), 2),
        "total_space_saved_mb": round((total_original - total_compressed) / (1024 * 1024), 2),
        "files": results,
    }


def get_large_file_summary(folder_path: str, threshold_bytes: int = LARGE_FILE_THRESHOLD) -> Dict[str, Any]:
    """
    Generate a summary of large files in a folder (without compressing).

    Returns:
        {
            "total_large_files": int,
            "total_size_mb": float,
            "threshold_mb": float,
            "files": [...]
        }
    """
    large_files = find_large_files(folder_path, threshold_bytes)
    total_size = sum(f["size_bytes"] for f in large_files)

    return {
        "total_large_files": len(large_files),
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "threshold_mb": round(threshold_bytes / (1024 * 1024), 2),
        "files": large_files,
    }
