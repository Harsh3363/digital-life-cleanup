"""
Report Generator — Markdown and JSON Report Output

Generates comprehensive reports summarizing all cleanup actions:
  - Digital_Life_Report.md   (human-readable Markdown)
  - DigitalLife_Index.json   (machine-readable JSON index)
"""

import json
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DEFAULT_REPORT_DIR

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate Markdown and JSON reports for Digital Life Cleanup."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else DEFAULT_REPORT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        data: Dict[str, Any],
        folder_path: str,
    ) -> Dict[str, str]:
        """
        Generate both Markdown and JSON reports.

        Args:
            data: Consolidated cleanup results containing:
                - duplicates: Duplicate scan results
                - metadata: Metadata extraction results
                - protected: Encryption results
                - compressed: Compression results
            folder_path: The folder that was cleaned.

        Returns:
            {"markdown_path": str, "json_path": str, "summary": str}
        """
        timestamp = datetime.now()
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        timestamp_file = timestamp.strftime("%Y%m%d_%H%M%S")

        # Generate markdown report
        md_path = self._generate_markdown(data, folder_path, timestamp_str, timestamp_file)

        # Generate JSON index
        json_path = self._generate_json(data, folder_path, timestamp_str, timestamp_file)

        summary = self._build_summary(data)

        logger.info(f"Reports generated: {md_path}, {json_path}")
        return {
            "markdown_path": str(md_path),
            "json_path": str(json_path),
            "summary": summary,
        }

    def _generate_markdown(
        self,
        data: Dict[str, Any],
        folder_path: str,
        timestamp_str: str,
        timestamp_file: str,
    ) -> Path:
        """Generate the Digital_Life_Report.md file."""
        md_path = self.output_dir / f"Digital_Life_Report_{timestamp_file}.md"

        duplicates = data.get("duplicates", {})
        metadata = data.get("metadata", {})
        protected = data.get("protected", {})
        compressed = data.get("compressed", {})
        organized = data.get("organized", {})

        lines = [
            "# 🧹 Digital Life Cleanup Report",
            "",
            f"**Generated:** {timestamp_str}  ",
            f"**Target Folder:** `{folder_path}`  ",
            f"**Powered by:** Accomplish AI Orchestrator",
            "",
            "---",
            "",
            "## 📊 Summary",
            "",
        ]

        # Summary stats
        dup_groups = duplicates.get("total_groups", 0)
        dup_wasted = duplicates.get("total_wasted_mb", 0)
        meta_files = metadata.get("total_files", 0)
        gps_files = metadata.get("files_with_gps", 0)
        prot_count = protected.get("file_count", 0) if isinstance(protected, dict) else 0
        comp_saved = compressed.get("total_space_saved_mb", 0) if isinstance(compressed, dict) else 0
        org_moved = organized.get("files_moved", 0) if isinstance(organized, dict) else 0
        org_cats = len(organized.get("categories", {})) if isinstance(organized, dict) else 0

        lines.extend([
            "| Metric | Value |",
            "|--------|-------|",
            f"| Duplicate Groups Found | {dup_groups} |",
            f"| Wasted Space (Duplicates) | {dup_wasted} MB |",
            f"| Files Analyzed (Metadata) | {meta_files} |",
            f"| Files with GPS Data | {gps_files} |",
            f"| Files Protected (Encrypted) | {prot_count} |",
            f"| Space Saved (Compression) | {comp_saved} MB |",
            f"| Files Organized | {org_moved} |",
            f"| Categories Created | {org_cats} |",
            "",
            "---",
            "",
        ])

        # Duplicates section
        lines.extend([
            "## 🔍 Duplicate Files",
            "",
        ])

        if dup_groups > 0:
            dup_files = duplicates.get("groups", [])
            lines.append(f"Found **{dup_groups}** groups of duplicate files "
                        f"wasting **{dup_wasted} MB**.\n")
            for i, group in enumerate(dup_files[:20], 1):  # Show max 20 groups
                size_mb = round(group.get("size", 0) / (1024 * 1024), 2)
                lines.append(f"### Group {i} — {group.get('count', 0)} copies ({size_mb} MB each)")
                lines.append(f"Hash: `{group.get('hash', 'N/A')[:16]}...`\n")
                for fp in group.get("files", []):
                    lines.append(f"- `{fp}`")
                lines.append("")
        else:
            lines.append("No duplicate files found. ✅\n")

        lines.extend(["---", ""])

        # Metadata section
        lines.extend([
            "## 📋 Metadata Extraction",
            "",
        ])

        if meta_files > 0:
            pdf_count = metadata.get("pdf_count", 0)
            img_count = metadata.get("image_count", 0)
            lines.append(f"Analyzed **{meta_files}** files "
                        f"({pdf_count} PDFs, {img_count} images).\n")

            if gps_files > 0:
                lines.append(f"⚠️ **{gps_files} files contain GPS location data** — "
                            "consider protecting these.\n")

            # Show a few metadata entries
            meta_entries = metadata.get("files", [])
            for entry in meta_entries[:10]:
                etype = entry.get("type", "unknown")
                fname = entry.get("filename", "unknown")
                if etype == "pdf":
                    pages = entry.get("page_count", "?")
                    author = entry.get("author", "Unknown")
                    lines.append(f"- 📄 **{fname}** — {pages} pages, author: {author}")
                elif etype == "image":
                    dims = f"{entry.get('width', '?')}×{entry.get('height', '?')}"
                    camera = entry.get("camera_model", "Unknown camera")
                    gps = "📍 GPS" if entry.get("has_gps") else ""
                    lines.append(f"- 🖼️ **{fname}** — {dims}, {camera} {gps}")
            lines.append("")
        else:
            lines.append("No PDF or image files analyzed.\n")

        lines.extend(["---", ""])

        # Protection section
        lines.extend([
            "## 🔒 File Protection",
            "",
        ])

        if isinstance(protected, dict) and protected.get("archive_path"):
            lines.extend([
                f"Created encrypted archive: `{protected.get('archive_path')}`",
                f"- **Encryption:** {protected.get('encryption', 'AES-256')}",
                f"- **Files included:** {protected.get('file_count', 0)}",
                f"- **Archive size:** {protected.get('archive_size_mb', 0)} MB",
                "",
                "**Files protected:**",
            ])
            for f in protected.get("files_included", []):
                lines.append(f"- `{f}`")
            lines.append("")
        else:
            lines.append("No files were encrypted in this run.\n")

        lines.extend(["---", ""])

        # Compression section
        lines.extend([
            "## 📦 Compression",
            "",
        ])

        if isinstance(compressed, dict) and compressed.get("total_files_compressed", 0) > 0:
            lines.extend([
                f"Compressed **{compressed.get('total_files_compressed', 0)}** files, "
                f"saving **{compressed.get('total_space_saved_mb', 0)} MB**.\n",
            ])
            for f in compressed.get("files", []):
                if "error" not in f:
                    fname = os.path.basename(f.get("original_path", ""))
                    ratio = f.get("compression_ratio", 0)
                    saved = f.get("space_saved_mb", 0)
                    lines.append(f"- `{fname}` — ratio: {ratio}, saved: {saved} MB")
            lines.append("")
        else:
            lines.append("No files were compressed in this run.\n")

        lines.extend(["---", ""])

        # Organization section
        lines.extend([
            "## 📂 Folder Organization",
            "",
        ])

        if isinstance(organized, dict) and organized.get("status") == "success" and org_moved > 0:
            lines.append(f"Organized **{org_moved}** files into **{org_cats}** categories.\n")
            org_categories = organized.get("categories", {})
            if org_categories:
                lines.extend([
                    "| Category | Files | Size |",
                    "|----------|-------|------|",
                ])
                for cat_name, cat_info in sorted(org_categories.items()):
                    if isinstance(cat_info, dict):
                        count = cat_info.get("count", 0)
                        size = cat_info.get("total_size_mb", 0)
                        lines.append(f"| {cat_name} | {count} | {size} MB |")
                lines.append("")

            dups_found = organized.get("duplicates_found", 0)
            if dups_found > 0:
                lines.append(f"\n🔁 **{dups_found}** exact duplicate files moved to `Duplicates/` folder.\n")
        else:
            lines.append("No files were organized in this run.\n")

        lines.extend([
            "---",
            "",
            f"*Report generated by Digital Life Cleanup & Protection System — {timestamp_str}*",
        ])

        # Write markdown
        md_content = "\n".join(lines)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # Also write a copy without timestamp in name for easy access
        latest_path = self.output_dir / "Digital_Life_Report.md"
        with open(latest_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        logger.info(f"Markdown report saved: {md_path}")
        return md_path

    def _generate_json(
        self,
        data: Dict[str, Any],
        folder_path: str,
        timestamp_str: str,
        timestamp_file: str,
    ) -> Path:
        """Generate the DigitalLife_Index.json file."""
        json_path = self.output_dir / f"DigitalLife_Index_{timestamp_file}.json"

        index = {
            "report_version": "1.0",
            "generated_at": timestamp_str,
            "target_folder": folder_path,
            "orchestrator": "Accomplish AI",
            "summary": {
                "duplicate_groups": data.get("duplicates", {}).get("total_groups", 0),
                "redundant_files": data.get("duplicates", {}).get("total_redundant_files", 0),
                "wasted_space_mb": data.get("duplicates", {}).get("total_wasted_mb", 0),
                "files_analyzed": data.get("metadata", {}).get("total_files", 0),
                "files_with_gps": data.get("metadata", {}).get("files_with_gps", 0),
                "files_protected": (
                    data.get("protected", {}).get("file_count", 0)
                    if isinstance(data.get("protected"), dict) else 0
                ),
                "files_compressed": (
                    data.get("compressed", {}).get("total_files_compressed", 0)
                    if isinstance(data.get("compressed"), dict) else 0
                ),
                "space_saved_mb": (
                    data.get("compressed", {}).get("total_space_saved_mb", 0)
                    if isinstance(data.get("compressed"), dict) else 0
                ),
            },
            "organization": {
                "files_organized": (
                    data.get("organized", {}).get("files_moved", 0)
                    if isinstance(data.get("organized"), dict) else 0
                ),
                "categories_created": (
                    len(data.get("organized", {}).get("categories", {}))
                    if isinstance(data.get("organized"), dict) else 0
                ),
            },
            "details": {
                "duplicates": data.get("duplicates", {}),
                "metadata": data.get("metadata", {}),
                "protected": data.get("protected", {}),
                "compressed": data.get("compressed", {}),
                "organized": data.get("organized", {}),
            },
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, default=str)

        # Also write a copy without timestamp for easy access
        latest_path = self.output_dir / "DigitalLife_Index.json"
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, default=str)

        logger.info(f"JSON index saved: {json_path}")
        return json_path

    def _build_summary(self, data: Dict[str, Any]) -> str:
        """Build a one-line summary of the cleanup results."""
        parts = []

        dup_groups = data.get("duplicates", {}).get("total_groups", 0)
        if dup_groups > 0:
            parts.append(f"{dup_groups} duplicate groups found")

        meta_files = data.get("metadata", {}).get("total_files", 0)
        if meta_files > 0:
            parts.append(f"{meta_files} files analyzed")

        prot = data.get("protected", {})
        if isinstance(prot, dict) and prot.get("file_count", 0) > 0:
            parts.append(f"{prot['file_count']} files protected")

        comp = data.get("compressed", {})
        if isinstance(comp, dict) and comp.get("total_files_compressed", 0) > 0:
            parts.append(f"{comp['total_files_compressed']} files compressed")

        org = data.get("organized", {})
        if isinstance(org, dict) and org.get("files_moved", 0) > 0:
            parts.append(f"{org['files_moved']} files organized into {len(org.get('categories', {}))} folders")

        return "; ".join(parts) if parts else "No actions taken"
