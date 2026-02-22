"""
Smart Orchestrator — Built-in Rule-Based Cleanup Engine (No AI Required)

This module provides a fully deterministic orchestrator that performs
the same cleanup workflow that the AI would decide to do, but without
needing any API keys or external services.

It follows the same workflow as the SYSTEM_PROMPT in accomplish_bridge.py:
  1. Scan for duplicates
  2. Extract metadata (identify sensitive files)
  3. Find large files
  4. Encrypt sensitive files
  5. Compress large files
  6. Organize files into categorized subfolders
  7. Generate report

All decisions are rule-based — no LLM calls are made.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SENSITIVE_KEYWORDS,
    LARGE_FILE_THRESHOLD_SMART,
)
from orchestrator.tool_registry import execute_tool

logger = logging.getLogger(__name__)


def _has_sensitive_content(filepath: str, keywords: List[str] = None) -> bool:
    """Check if a text file contains sensitive keywords."""
    if keywords is None:
        keywords = SENSITIVE_KEYWORDS

    try:
        # Only check text-like files (< 1MB)
        if os.path.getsize(filepath) > 1_000_000:
            return False

        ext = Path(filepath).suffix.lower()
        text_extensions = {".txt", ".md", ".csv", ".json", ".log", ".rtf", ".py", ".js", ".env"}
        if ext not in text_extensions:
            return False

        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(50_000).lower()  # Read first 50KB

        return any(kw in content for kw in keywords)
    except (IOError, OSError):
        return False


def _identify_sensitive_files(metadata_result: Dict, folder_path: str) -> List[str]:
    """
    Identify files that should be encrypted based on:
    - Images with GPS data
    - PDFs with personal/financial metadata
    - Text files containing sensitive keywords
    """
    sensitive = []

    # Check metadata results for images with GPS
    for file_meta in metadata_result.get("files", []):
        if file_meta.get("has_gps", False):
            sensitive.append(file_meta["path"])
            continue

        # Check PDFs with suggestive titles
        if file_meta.get("type") == "pdf":
            title = (file_meta.get("title") or "").lower()
            sensitive_pdf_words = ["tax", "salary", "personal", "confidential",
                                   "financial", "employee", "medical", "contract"]
            if any(w in title for w in sensitive_pdf_words):
                sensitive.append(file_meta["path"])
                continue

    # Scan text files for sensitive keywords
    for root, _dirs, files in os.walk(folder_path):
        for fname in files:
            fpath = os.path.join(root, fname)
            if fpath not in sensitive and _has_sensitive_content(fpath):
                sensitive.append(fpath)

    return sensitive


class SmartOrchestrator:
    """
    Built-in rule-based orchestrator — no AI required.

    Executes the same cleanup workflow as the AI orchestrator,
    but using deterministic rules instead of LLM decisions.
    """

    def __init__(self):
        self._log_callback: Optional[Callable] = None
        self.tool_results: List[Dict] = []

    def set_log_callback(self, callback: Callable[[str], None]):
        """Set a callback for real-time log messages."""
        self._log_callback = callback

    def _log(self, message: str):
        """Log a message and send to callback if set."""
        logger.info(message)
        if self._log_callback:
            self._log_callback(message)

    def run_cleanup(
        self,
        folder_path: str,
        enable_protection: bool = True,
        enable_compression: bool = True,
        enable_duplicates: bool = True,
    ) -> Dict[str, Any]:
        """
        Run the full cleanup workflow using deterministic rules.

        This follows the exact same steps the AI would take,
        but without needing any API calls.
        """
        self._log("🚀 Starting Digital Life Cleanup (Smart Mode — No AI Required)")
        self._log(f"📁 Target folder: {folder_path}")
        self._log(f"   Duplicates: {'✅' if enable_duplicates else '❌'}")
        self._log(f"   Protection: {'✅' if enable_protection else '❌'}")
        self._log(f"   Compression: {'✅' if enable_compression else '❌'}")

        self.tool_results = []
        tool_calls_made = 0
        duplicate_summary = {}
        metadata_summary = {}
        large_files_result = []
        encrypt_result = {}
        compress_results = []
        organize_result = {}

        try:
            # ── Step 1: Scan for Duplicates ──────────────────────────
            if enable_duplicates:
                self._log("\n🔄 Step 1/7: Scanning for duplicate files...")
                try:
                    duplicate_summary = execute_tool("scan_duplicates", {
                        "folder_path": folder_path
                    })
                    tool_calls_made += 1
                    self.tool_results.append({
                        "tool": "scan_duplicates",
                        "result_preview": json.dumps(duplicate_summary, default=str)[:500],
                    })

                    groups = duplicate_summary.get("total_groups", 0)
                    redundant = duplicate_summary.get("total_redundant_files", 0)
                    wasted = duplicate_summary.get("total_wasted_mb", 0)
                    self._log(f"   ✅ Found {groups} duplicate groups "
                              f"({redundant} redundant files, {wasted} MB wasted)")

                    # Log duplicate details
                    for g in duplicate_summary.get("groups", [])[:5]:
                        self._log(f"      → {g['count']} copies × {g['size']} bytes: "
                                  f"{', '.join(os.path.basename(f) for f in g['files'][:3])}")

                except Exception as e:
                    self._log(f"   ⚠️ Duplicate scan failed: {e}")
            else:
                self._log("\n⏭️ Step 1/7: Duplicate detection — SKIPPED (disabled)")

            # ── Step 2: Extract Metadata ─────────────────────────────
            self._log("\n🔄 Step 2/7: Extracting file metadata...")
            try:
                metadata_summary = execute_tool("extract_metadata", {
                    "folder_path": folder_path
                })
                tool_calls_made += 1
                self.tool_results.append({
                    "tool": "extract_metadata",
                    "result_preview": json.dumps(metadata_summary, default=str)[:500],
                })

                total = metadata_summary.get("total_files", 0)
                pdfs = metadata_summary.get("pdf_count", 0)
                images = metadata_summary.get("image_count", 0)
                gps = metadata_summary.get("files_with_gps", 0)
                self._log(f"   ✅ Extracted metadata from {total} files "
                          f"({pdfs} PDFs, {images} images, {gps} with GPS)")

                # Log a few interesting files
                for m in metadata_summary.get("files", [])[:3]:
                    fname = m.get("filename", "?")
                    ftype = m.get("type", "?")
                    title = m.get("title", "N/A")
                    self._log(f"      → {fname}: type={ftype}, title={title}")

            except Exception as e:
                self._log(f"   ⚠️ Metadata extraction failed: {e}")

            # ── Step 3: Find Large Files ─────────────────────────────
            self._log("\n🔄 Step 3/7: Scanning for large files...")
            try:
                threshold_mb = LARGE_FILE_THRESHOLD_SMART / (1024 * 1024)
                large_files_result = execute_tool("find_large_files", {
                    "folder_path": folder_path,
                    "threshold_mb": threshold_mb,
                })
                tool_calls_made += 1
                self.tool_results.append({
                    "tool": "find_large_files",
                    "result_preview": json.dumps(large_files_result, default=str)[:500],
                })

                count = len(large_files_result) if isinstance(large_files_result, list) else 0
                self._log(f"   ✅ Found {count} large files (>{threshold_mb:.0f} MB)")
                if isinstance(large_files_result, list):
                    for lf in large_files_result[:5]:
                        self._log(f"      → {lf['filename']}: {lf['size_mb']} MB")

            except Exception as e:
                self._log(f"   ⚠️ Large file scan failed: {e}")

            # ── Step 4: Identify & Encrypt Sensitive Files ───────────
            if enable_protection:
                self._log("\n🔄 Step 4/7: Identifying and protecting sensitive files...")
                try:
                    sensitive_files = _identify_sensitive_files(metadata_summary, folder_path)

                    if sensitive_files:
                        self._log(f"   🔍 Found {len(sensitive_files)} sensitive files:")
                        for sf in sensitive_files[:10]:
                            self._log(f"      → {os.path.basename(sf)}")

                        encrypt_result = execute_tool("encrypt_files", {
                            "file_paths": sensitive_files,
                            "archive_name": "protected_sensitive_files",
                        })
                        tool_calls_made += 1
                        self.tool_results.append({
                            "tool": "encrypt_files",
                            "result_preview": json.dumps(encrypt_result, default=str)[:500],
                        })

                        if "error" not in encrypt_result:
                            self._log(f"   ✅ Encrypted {encrypt_result.get('file_count', 0)} files "
                                      f"→ {encrypt_result.get('archive_path', '?')}")
                            self._log(f"      Encryption: {encrypt_result.get('encryption', 'AES-256')}")
                        else:
                            self._log(f"   ⚠️ Encryption failed: {encrypt_result.get('error')}")
                    else:
                        self._log("   ℹ️ No sensitive files detected — nothing to encrypt")

                except Exception as e:
                    self._log(f"   ⚠️ Protection step failed: {e}")
            else:
                self._log("\n⏭️ Step 4/7: Protection — SKIPPED (disabled)")

            # ── Step 5: Compress Large Files ─────────────────────────
            if enable_compression:
                self._log("\n🔄 Step 5/7: Compressing large files...")
                try:
                    if isinstance(large_files_result, list) and large_files_result:
                        for lf in large_files_result:
                            self._log(f"   📦 Compressing {lf['filename']}...")
                            result = execute_tool("compress_file", {
                                "filepath": lf["path"]
                            })
                            tool_calls_made += 1
                            compress_results.append(result)

                            if "error" not in result:
                                self._log(f"      ✅ {result.get('original_size_mb', '?')} MB → "
                                          f"{result.get('compressed_size_mb', '?')} MB "
                                          f"(ratio: {result.get('compression_ratio', '?')}, "
                                          f"saved: {result.get('space_saved_mb', '?')} MB)")
                            else:
                                self._log(f"      ⚠️ Failed: {result.get('error')}")

                        self.tool_results.append({
                            "tool": "compress_file (batch)",
                            "result_preview": json.dumps(compress_results[:3], default=str)[:500],
                        })
                    else:
                        self._log("   ℹ️ No large files found — nothing to compress")

                except Exception as e:
                    self._log(f"   ⚠️ Compression step failed: {e}")
            else:
                self._log("\n⏭️ Step 5/7: Compression — SKIPPED (disabled)")

            # ── Step 6: Organize Files into Subfolders ────────────────
            self._log("\n🔄 Step 6/7: Organizing files into categorized subfolders...")
            try:
                organize_result = execute_tool("organize_folder", {
                    "folder_path": folder_path,
                    "dry_run": False,
                    "handle_duplicates": enable_duplicates,
                })
                tool_calls_made += 1
                self.tool_results.append({
                    "tool": "organize_folder",
                    "result_preview": json.dumps(organize_result, default=str)[:500],
                })

                if organize_result.get("status") == "success":
                    moved = organize_result.get("files_moved", 0)
                    total = organize_result.get("total_files", 0)
                    cats = organize_result.get("categories", {})
                    dups = organize_result.get("duplicates_found", 0)
                    self._log(f"   ✅ Organized {moved}/{total} files into {len(cats)} categories")
                    for cat_name, cat_info in sorted(cats.items()):
                        count = cat_info.get("count", 0) if isinstance(cat_info, dict) else 0
                        self._log(f"      → {cat_name}: {count} files")
                    if dups > 0:
                        self._log(f"      → {dups} exact duplicates grouped")
                else:
                    self._log(f"   ⚠️ Organization failed: {organize_result.get('error', 'unknown')}")

            except Exception as e:
                self._log(f"   ⚠️ Organization step failed: {e}")

            # ── Step 7: Generate Report ──────────────────────────────
            self._log("\n🔄 Step 7/7: Generating cleanup report...")
            try:
                # Build compression summary
                if compress_results:
                    successful_compressions = [r for r in compress_results if "error" not in r]
                    compress_summary = {
                        "total_files_compressed": len(successful_compressions),
                        "total_original_size_mb": sum(r.get("original_size_mb", 0) for r in successful_compressions),
                        "total_compressed_size_mb": sum(r.get("compressed_size_mb", 0) for r in successful_compressions),
                        "total_space_saved_mb": sum(r.get("space_saved_mb", 0) for r in successful_compressions),
                        "files": compress_results,
                    }
                else:
                    compress_summary = {}

                report_data = {
                    "folder_path": folder_path,
                    "duplicates": duplicate_summary,
                    "metadata": metadata_summary,
                    "protected": encrypt_result,
                    "compressed": compress_summary,
                    "organized": organize_result,
                }

                report_result = execute_tool("generate_report", {
                    "report_data": report_data
                })
                tool_calls_made += 1
                self.tool_results.append({
                    "tool": "generate_report",
                    "result_preview": json.dumps(report_result, default=str)[:500],
                })

                self._log(f"   ✅ Report generated:")
                self._log(f"      Markdown: {report_result.get('markdown_path', 'N/A')}")
                self._log(f"      JSON: {report_result.get('json_path', 'N/A')}")

            except Exception as e:
                self._log(f"   ⚠️ Report generation failed: {e}")

            # ── Final Summary ────────────────────────────────────────
            summary_parts = []
            summary_parts.append(f"Digital Life Cleanup completed for: {folder_path}")

            if enable_duplicates and duplicate_summary:
                groups = duplicate_summary.get("total_groups", 0)
                wasted = duplicate_summary.get("total_wasted_mb", 0)
                summary_parts.append(f"• Duplicates: {groups} groups found ({wasted} MB wasted)")

            if metadata_summary:
                total = metadata_summary.get("total_files", 0)
                summary_parts.append(f"• Metadata: Extracted from {total} files")

            if enable_protection and encrypt_result and "error" not in encrypt_result:
                enc_count = encrypt_result.get("file_count", 0)
                summary_parts.append(f"• Protection: {enc_count} sensitive files encrypted (AES-256)")

            if enable_compression and compress_results:
                saved = sum(r.get("space_saved_mb", 0) for r in compress_results if "error" not in r)
                summary_parts.append(f"• Compression: Saved {saved:.1f} MB")

            if organize_result and organize_result.get("status") == "success":
                moved = organize_result.get("files_moved", 0)
                cats = len(organize_result.get("categories", {}))
                summary_parts.append(f"• Organization: {moved} files sorted into {cats} folders")

            summary_parts.append(f"• Total tool calls: {tool_calls_made}")
            summary_parts.append("\n🧠 Powered by Smart Mode (built-in orchestrator, no AI required)")

            final_summary = "\n".join(summary_parts)
            self._log(f"\n{'=' * 60}")
            self._log(f"📋 Final Summary:")
            self._log(final_summary)
            self._log(f"{'=' * 60}")

            return {
                "status": "completed",
                "iterations": 1,
                "tool_calls_made": tool_calls_made,
                "tool_results": self.tool_results,
                "final_summary": final_summary,
            }

        except Exception as e:
            self._log(f"\n❌ Smart Orchestrator error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "iterations": 1,
                "tool_calls_made": tool_calls_made,
                "tool_results": self.tool_results,
            }
