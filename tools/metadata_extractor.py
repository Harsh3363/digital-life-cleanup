"""
Metadata Extractor — PDF and Image Metadata

Pure deterministic tool. No AI/classification logic.
Accomplish decides how to use the extracted metadata.

Features:
  - PDF metadata via PyPDF2 (title, author, pages, creation date, producer)
  - Image EXIF via Pillow (camera, dimensions, GPS, date taken)
  - Graceful handling of corrupt or missing metadata
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import IMAGE_EXTENSIONS, PDF_EXTENSIONS

logger = logging.getLogger(__name__)


def _extract_pdf_metadata(filepath: str) -> Optional[Dict[str, Any]]:
    """Extract metadata from a PDF file using PyPDF2."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(filepath)
        info = reader.metadata

        metadata = {
            "type": "pdf",
            "path": filepath,
            "filename": os.path.basename(filepath),
            "file_size_bytes": os.path.getsize(filepath),
            "page_count": len(reader.pages),
            "title": None,
            "author": None,
            "subject": None,
            "creator": None,
            "producer": None,
            "creation_date": None,
            "modification_date": None,
        }

        if info:
            metadata["title"] = str(info.title) if info.title else None
            metadata["author"] = str(info.author) if info.author else None
            metadata["subject"] = str(info.subject) if info.subject else None
            metadata["creator"] = str(info.creator) if info.creator else None
            metadata["producer"] = str(info.producer) if info.producer else None

            if info.creation_date:
                try:
                    metadata["creation_date"] = info.creation_date.isoformat()
                except (AttributeError, ValueError):
                    metadata["creation_date"] = str(info.creation_date)

            if info.modification_date:
                try:
                    metadata["modification_date"] = info.modification_date.isoformat()
                except (AttributeError, ValueError):
                    metadata["modification_date"] = str(info.modification_date)

        return metadata

    except ImportError:
        logger.warning("PyPDF2 not installed. PDF metadata extraction unavailable.")
        return {"type": "pdf", "path": filepath, "error": "PyPDF2 not installed"}
    except Exception as e:
        logger.warning(f"Failed to extract PDF metadata from {filepath}: {e}")
        return {"type": "pdf", "path": filepath, "error": str(e)}


def _extract_image_metadata(filepath: str) -> Optional[Dict[str, Any]]:
    """Extract EXIF metadata from an image file using Pillow."""
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS

        img = Image.open(filepath)

        metadata = {
            "type": "image",
            "path": filepath,
            "filename": os.path.basename(filepath),
            "file_size_bytes": os.path.getsize(filepath),
            "format": img.format,
            "mode": img.mode,
            "width": img.width,
            "height": img.height,
            "resolution_mpx": round((img.width * img.height) / 1_000_000, 2),
        }

        # Extract EXIF data
        exif_data = {}
        try:
            raw_exif = img._getexif()
            if raw_exif:
                for tag_id, value in raw_exif.items():
                    tag_name = TAGS.get(tag_id, f"Unknown_{tag_id}")

                    # Handle GPS data specially
                    if tag_name == "GPSInfo":
                        gps_data = {}
                        for gps_tag_id, gps_value in value.items():
                            gps_tag_name = GPSTAGS.get(gps_tag_id, f"Unknown_{gps_tag_id}")
                            gps_data[gps_tag_name] = str(gps_value)
                        exif_data["gps"] = gps_data
                    elif isinstance(value, bytes):
                        # Skip binary blobs
                        continue
                    else:
                        try:
                            exif_data[tag_name] = str(value)
                        except Exception:
                            continue
        except (AttributeError, Exception):
            pass

        # Extract key fields into top-level
        metadata["camera_make"] = exif_data.get("Make")
        metadata["camera_model"] = exif_data.get("Model")
        metadata["date_taken"] = exif_data.get("DateTimeOriginal") or exif_data.get("DateTime")
        metadata["software"] = exif_data.get("Software")
        metadata["orientation"] = exif_data.get("Orientation")
        metadata["has_gps"] = "gps" in exif_data
        metadata["gps_data"] = exif_data.get("gps")

        # Add raw EXIF count
        metadata["exif_tag_count"] = len(exif_data)

        img.close()
        return metadata

    except ImportError:
        logger.warning("Pillow not installed. Image metadata extraction unavailable.")
        return {"type": "image", "path": filepath, "error": "Pillow not installed"}
    except Exception as e:
        logger.warning(f"Failed to extract image metadata from {filepath}: {e}")
        return {"type": "image", "path": filepath, "error": str(e)}


def extract_metadata(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Extract metadata from a single file (PDF or image).

    Args:
        filepath: Path to the file.

    Returns:
        Dictionary containing extracted metadata, or None if unsupported type.
    """
    ext = Path(filepath).suffix.lower()

    if ext in PDF_EXTENSIONS:
        return _extract_pdf_metadata(filepath)
    elif ext in IMAGE_EXTENSIONS:
        return _extract_image_metadata(filepath)
    else:
        return {
            "type": "other",
            "path": filepath,
            "filename": os.path.basename(filepath),
            "file_size_bytes": os.path.getsize(filepath),
            "extension": ext,
            "last_modified": datetime.fromtimestamp(
                os.path.getmtime(filepath)
            ).isoformat(),
        }


def scan_metadata(folder_path: str, extensions: Optional[set] = None) -> List[Dict[str, Any]]:
    """
    Scan a folder recursively and extract metadata from supported files.

    Args:
        folder_path: Root directory to scan.
        extensions: Optional set of extensions to filter (default: PDF + images).

    Returns:
        List of metadata dictionaries.
    """
    if extensions is None:
        extensions = PDF_EXTENSIONS | IMAGE_EXTENSIONS

    folder = Path(folder_path)
    if not folder.is_dir():
        logger.error(f"Not a valid directory: {folder_path}")
        return []

    logger.info(f"Scanning metadata in: {folder_path}")
    results = []

    for root, _dirs, files in os.walk(folder_path):
        for filename in files:
            ext = Path(filename).suffix.lower()
            if ext in extensions:
                filepath = os.path.join(root, filename)
                meta = extract_metadata(filepath)
                if meta:
                    results.append(meta)

    logger.info(f"Extracted metadata from {len(results)} files")
    return results


def get_metadata_summary(metadata_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a summary of metadata extraction results.

    Returns:
        {
            "total_files": int,
            "pdf_count": int,
            "image_count": int,
            "other_count": int,
            "total_size_bytes": int,
            "total_size_mb": float,
            "files_with_gps": int,
            "files": [...]
        }
    """
    pdf_count = sum(1 for m in metadata_list if m.get("type") == "pdf")
    image_count = sum(1 for m in metadata_list if m.get("type") == "image")
    other_count = sum(1 for m in metadata_list if m.get("type") == "other")
    total_size = sum(m.get("file_size_bytes", 0) for m in metadata_list)
    gps_count = sum(1 for m in metadata_list if m.get("has_gps", False))

    return {
        "total_files": len(metadata_list),
        "pdf_count": pdf_count,
        "image_count": image_count,
        "other_count": other_count,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "files_with_gps": gps_count,
        "files": metadata_list
    }
