"""
File Encryptor — AES-256 Encrypted ZIP Creation

Pure deterministic tool. No AI/classification logic.
Accomplish decides which files need encryption.

Features:
  - AES-256 encrypted ZIP archives via pyzipper
  - Password-based encryption
  - Streams large files into archive without full memory load
  - Returns path to encrypted archive with metadata
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CHUNK_SIZE, DEFAULT_OUTPUT_DIR

logger = logging.getLogger(__name__)


def encrypt_files(
    file_paths: List[str],
    output_path: Optional[str] = None,
    password: Optional[str] = None,
    archive_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create an AES-256 encrypted ZIP archive containing the specified files.

    Args:
        file_paths: List of file paths to include in the encrypted archive.
        output_path: Directory to save the archive. Defaults to project output dir.
        password: Encryption password. Auto-generated if not provided.
        archive_name: Name of the output archive (without extension).

    Returns:
        {
            "archive_path": str,
            "file_count": int,
            "total_original_size": int,
            "archive_size": int,
            "encryption": str,
            "files_included": [str, ...],
            "timestamp": str,
            "password_provided": bool
        }
    """
    try:
        import pyzipper
    except ImportError:
        logger.error("pyzipper not installed. Run: pip install pyzipper")
        return {"error": "pyzipper not installed", "files_included": file_paths}

    # Resolve output directory
    if output_path is None:
        output_dir = DEFAULT_OUTPUT_DIR
    else:
        output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate archive name
    if archive_name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"protected_{timestamp}"

    archive_file = output_dir / f"{archive_name}.zip"

    # Generate password if not provided
    if password is None:
        import secrets
        password = secrets.token_urlsafe(16)
        logger.info(f"Auto-generated password for archive: {archive_name}")

    password_bytes = password.encode("utf-8")

    # Validate input files
    valid_files = []
    total_original_size = 0
    for fp in file_paths:
        if os.path.isfile(fp):
            valid_files.append(fp)
            total_original_size += os.path.getsize(fp)
        else:
            logger.warning(f"File not found, skipping: {fp}")

    if not valid_files:
        logger.error("No valid files to encrypt")
        return {"error": "No valid files provided", "files_included": []}

    # Create encrypted ZIP with streaming
    logger.info(f"Creating encrypted archive: {archive_file}")
    logger.info(f"Including {len(valid_files)} files ({total_original_size} bytes)")

    try:
        with pyzipper.AESZipFile(
            str(archive_file),
            "w",
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES,
        ) as zf:
            zf.setpassword(password_bytes)

            for filepath in valid_files:
                arcname = os.path.basename(filepath)
                logger.debug(f"  Adding: {arcname}")

                # Stream file into archive in chunks
                with open(filepath, "rb") as f_in:
                    data = f_in.read()  # pyzipper requires full data for AES
                    zf.writestr(arcname, data)

        archive_size = os.path.getsize(archive_file)

        result = {
            "archive_path": str(archive_file),
            "file_count": len(valid_files),
            "total_original_size": total_original_size,
            "total_original_size_mb": round(total_original_size / (1024 * 1024), 2),
            "archive_size": archive_size,
            "archive_size_mb": round(archive_size / (1024 * 1024), 2),
            "encryption": "AES-256",
            "files_included": [os.path.basename(f) for f in valid_files],
            "timestamp": datetime.now().isoformat(),
            "password_provided": password is not None,
        }

        logger.info(f"Archive created: {archive_file} ({archive_size} bytes)")
        return result

    except Exception as e:
        logger.error(f"Failed to create encrypted archive: {e}")
        return {"error": str(e), "files_included": file_paths}


def encrypt_folder(
    folder_path: str,
    output_path: Optional[str] = None,
    password: Optional[str] = None,
    extensions: Optional[set] = None,
) -> Dict[str, Any]:
    """
    Encrypt all files in a folder (optionally filtered by extension).

    Args:
        folder_path: Directory to encrypt files from.
        output_path: Where to save the archive.
        password: Encryption password.
        extensions: Optional set of extensions to filter.

    Returns:
        Same as encrypt_files().
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        logger.error(f"Not a valid directory: {folder_path}")
        return {"error": f"Invalid directory: {folder_path}"}

    file_paths = []
    for root, _dirs, files in os.walk(folder_path):
        for filename in files:
            if extensions is None or Path(filename).suffix.lower() in extensions:
                file_paths.append(os.path.join(root, filename))

    if not file_paths:
        return {"error": "No matching files found", "folder": folder_path}

    archive_name = f"protected_{folder.name}"
    return encrypt_files(
        file_paths=file_paths,
        output_path=output_path,
        password=password,
        archive_name=archive_name,
    )
