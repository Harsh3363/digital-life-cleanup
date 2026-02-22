"""
Tool Registry — Registers Python tools for Accomplish orchestration.

Defines tool schemas (name, description, parameters) that Accomplish
uses to decide which tool to call. Each tool maps to a function in tools/.

No AI logic here — this is a pure schema registry.
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Tool Schema Definitions ─────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "scan_duplicates",
            "description": (
                "Scan a folder recursively for duplicate files using SHA256 hashing. "
                "Uses size-based pre-filtering and optional partial hashing for speed. "
                "Returns groups of duplicate files with their hashes, sizes, and paths. "
                "Never reads files fully into memory."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_path": {
                        "type": "string",
                        "description": "Absolute path to the folder to scan for duplicates."
                    },
                    "use_partial_hash": {
                        "type": "boolean",
                        "description": "Use partial hash pre-filtering for faster scanning. Default true.",
                        "default": True
                    },
                    "min_size": {
                        "type": "integer",
                        "description": "Minimum file size in bytes to consider. Default 1.",
                        "default": 1
                    }
                },
                "required": ["folder_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_metadata",
            "description": (
                "Extract metadata from PDF and image files in a folder. "
                "PDFs: title, author, pages, creation date, producer. "
                "Images: camera make/model, dimensions, GPS, date taken, EXIF tags. "
                "Returns structured metadata for each file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_path": {
                        "type": "string",
                        "description": "Absolute path to the folder to scan for metadata."
                    }
                },
                "required": ["folder_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "encrypt_files",
            "description": (
                "Create an AES-256 encrypted ZIP archive containing specified files. "
                "Use this to protect sensitive files identified during cleanup. "
                "Auto-generates a secure password if none is provided."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of absolute file paths to encrypt into an archive."
                    },
                    "archive_name": {
                        "type": "string",
                        "description": "Name for the output archive (without extension)."
                    },
                    "password": {
                        "type": "string",
                        "description": "Encryption password. Auto-generated if not provided."
                    }
                },
                "required": ["file_paths"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_large_files",
            "description": (
                "Scan a folder and find files above a size threshold. "
                "Returns a list of large files with their sizes, extensions, and modification dates. "
                "Default threshold is 100MB."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_path": {
                        "type": "string",
                        "description": "Absolute path to the folder to scan."
                    },
                    "threshold_mb": {
                        "type": "number",
                        "description": "Size threshold in megabytes. Default 100.",
                        "default": 100
                    }
                },
                "required": ["folder_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compress_file",
            "description": (
                "Compress a single file using gzip with streaming. "
                "Never loads the full file into memory. "
                "Returns compression stats including ratio and space saved."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Absolute path to the file to compress."
                    }
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compress_large_files",
            "description": (
                "Find and compress all files above a size threshold in a folder. "
                "Uses streaming gzip compression. "
                "Returns total stats and per-file compression results."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_path": {
                        "type": "string",
                        "description": "Absolute path to the folder to scan and compress."
                    },
                    "threshold_mb": {
                        "type": "number",
                        "description": "Size threshold in megabytes. Default 100.",
                        "default": 100
                    }
                },
                "required": ["folder_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_report",
            "description": (
                "Generate a Digital Life Report (Markdown + JSON) summarizing all cleanup actions. "
                "Call this after all other tools have been executed to produce the final report."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "report_data": {
                        "type": "object",
                        "description": "Complete data from all cleanup operations to include in the report.",
                        "properties": {
                            "folder_path": {"type": "string"},
                            "duplicates": {"type": "object"},
                            "metadata": {"type": "object"},
                            "protected": {"type": "object"},
                            "compressed": {"type": "object"}
                        }
                    }
                },
                "required": ["report_data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "organize_folder",
            "description": (
                "Organize a messy folder by sorting files into categorized subfolders. "
                "Categories include: Documents, Images, Videos, Audio, Archives, Code, Data, "
                "Logs, Financial, Work, Sensitive, Duplicates, and Other. "
                "Files are classified by extension and filename keywords. "
                "Exact duplicate files are detected and grouped."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_path": {
                        "type": "string",
                        "description": "Absolute path to the folder to organize."
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "If true, only report what would be done without moving files. Default false.",
                        "default": False
                    },
                    "handle_duplicates": {
                        "type": "boolean",
                        "description": "If true, put exact duplicates in a Duplicates subfolder. Default true.",
                        "default": True
                    }
                },
                "required": ["folder_path"]
            }
        }
    },
]


def get_tool_definitions() -> List[Dict]:
    """Return all tool definitions for the Accomplish orchestrator."""
    return TOOL_DEFINITIONS


def get_tool_names() -> List[str]:
    """Return list of available tool names."""
    return [t["function"]["name"] for t in TOOL_DEFINITIONS]


# ── Tool Dispatch Map ────────────────────────────────────────────

def _build_dispatch_map() -> Dict[str, Callable]:
    """
    Build the dispatch map lazily to avoid import issues.
    Maps tool names to their Python implementations.
    """
    from tools.duplicate_detector import scan_for_duplicates, get_duplicate_summary
    from tools.metadata_extractor import scan_metadata, get_metadata_summary
    from tools.file_encryptor import encrypt_files as _encrypt_files
    from tools.large_file_handler import (
        find_large_files as _find_large_files,
        compress_file as _compress_file,
        compress_large_files as _compress_large_files,
    )
    from tools.file_organizer import organize_folder as _organize_folder
    from reports.report_generator import ReportGenerator

    reporter = ReportGenerator()

    def handle_scan_duplicates(folder_path: str, use_partial_hash: bool = True, min_size: int = 1, **kwargs):
        dupes = scan_for_duplicates(folder_path, use_partial_hash=use_partial_hash, min_size=min_size)
        return get_duplicate_summary(dupes)

    def handle_extract_metadata(folder_path: str, **kwargs):
        meta = scan_metadata(folder_path)
        return get_metadata_summary(meta)

    def handle_encrypt_files(file_paths: list, archive_name: str = None, password: str = None, **kwargs):
        return _encrypt_files(file_paths=file_paths, archive_name=archive_name, password=password)

    def handle_find_large_files(folder_path: str, threshold_mb: float = 100, **kwargs):
        threshold_bytes = int(threshold_mb * 1024 * 1024)
        return _find_large_files(folder_path, threshold_bytes=threshold_bytes)

    def handle_compress_file(filepath: str, **kwargs):
        return _compress_file(filepath)

    def handle_compress_large_files(folder_path: str, threshold_mb: float = 100, **kwargs):
        threshold_bytes = int(threshold_mb * 1024 * 1024)
        return _compress_large_files(folder_path, threshold_bytes=threshold_bytes)

    def handle_generate_report(report_data: dict, **kwargs):
        folder_path = report_data.get("folder_path", "unknown")
        return reporter.generate(report_data, folder_path)

    def handle_organize_folder(folder_path: str, dry_run: bool = False, handle_duplicates: bool = True, **kwargs):
        return _organize_folder(folder_path, dry_run=dry_run, handle_duplicates=handle_duplicates)

    return {
        "scan_duplicates": handle_scan_duplicates,
        "extract_metadata": handle_extract_metadata,
        "encrypt_files": handle_encrypt_files,
        "find_large_files": handle_find_large_files,
        "compress_file": handle_compress_file,
        "compress_large_files": handle_compress_large_files,
        "generate_report": handle_generate_report,
        "organize_folder": handle_organize_folder,
    }


_dispatch_map: Optional[Dict[str, Callable]] = None


def get_dispatch_map() -> Dict[str, Callable]:
    """Get the tool dispatch map (built lazily on first call)."""
    global _dispatch_map
    if _dispatch_map is None:
        _dispatch_map = _build_dispatch_map()
    return _dispatch_map


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    Execute a tool by name with the given arguments.

    Args:
        tool_name: Name of the tool to execute (must match a registered tool).
        arguments: Dictionary of arguments to pass to the tool.

    Returns:
        Tool execution result (varies by tool).

    Raises:
        ValueError: If tool_name is not registered.
    """
    dispatch = get_dispatch_map()

    if tool_name not in dispatch:
        raise ValueError(f"Unknown tool: {tool_name}. Available: {list(dispatch.keys())}")

    logger.info(f"Executing tool: {tool_name}")
    logger.debug(f"  Arguments: {json.dumps(arguments, default=str)[:500]}")

    result = dispatch[tool_name](**arguments)

    logger.info(f"Tool {tool_name} completed")
    return result
