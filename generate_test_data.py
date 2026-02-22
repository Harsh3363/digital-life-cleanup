#!/usr/bin/env python3
"""
Generate a comprehensive test folder with diverse files to exercise
EVERY tool and edge case in the Digital Life Cleanup system.

Coverage:
  ─── Duplicate Detector ───────────────────────────────
  ✓ Identical text files in different locations
  ✓ Identical binary blobs in different locations
  ✓ Identical image files (photo copy)
  ✓ Identical JSON configs across directories
  ✓ Near-duplicates (same name, different content) — NOT matched
  ✓ Empty files (edge case: 0-byte dedup)

  ─── Metadata Extractor ───────────────────────────────
  ✓ PDF files with full metadata (title, author, creation date)
  ✓ PDF with no metadata
  ✓ PDF with many pages
  ✓ JPEG images (various sizes, with EXIF if Pillow available)
  ✓ PNG images
  ✓ BMP images (fallback when no Pillow)
  ✓ TIFF images
  ✓ GIF images
  ✓ WEBP images
  ✓ Images without EXIF data

  ─── Large File Handler ──────────────────────────────
  ✓ Highly compressible log file (>1 MB)
  ✓ Highly compressible CSV (>1 MB)
  ✓ Incompressible random binary (>1 MB)
  ✓ Large JSON dataset (>1 MB)
  ✓ Borderline file (just at threshold)
  ✓ Just under threshold (should NOT be flagged)

  ─── File Encryptor ───────────────────────────────────
  ✓ Sensitive text files (diary with SSN/bank info)
  ✓ Tax/financial PDF documents
  ✓ Config files with API keys
  ✓ Mix of file types for multi-file archive

  ─── General / All Extensions from config.py ─────────
  ✓ Image:   .jpg .jpeg .png .tiff .tif .bmp .gif .webp
  ✓ PDF:     .pdf
  ✓ Docs:    .docx .doc .txt .md .rtf
  ✓ Archive: .zip .tar .gz .bz2 .7z .rar
  ✓ Code:    .py .js .ts .java .cpp .c .h .go .rs

  ─── Edge Cases ───────────────────────────────────────
  ✓ Empty directory
  ✓ Deeply nested directory (4+ levels)
  ✓ Files with spaces in names
  ✓ Files with special characters
  ✓ Zero-byte files
  ✓ Very small files (<100 bytes)
  ✓ Hidden-style dotfiles
  ✓ Multiple extensions (.tar.gz)
  ✓ Unicode filename
"""

import os
import sys
import json
import random
import string
import hashlib
import struct
import tarfile
import gzip
import zipfile
import io
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TEST_DIR = Path(__file__).parent / "test_sample_folder"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _random_text(paragraphs: int = 3) -> str:
    words = (
        "lorem ipsum dolor sit amet consectetur adipiscing elit sed do "
        "eiusmod tempor incididunt ut labore et dolore magna aliqua ut enim "
        "ad minim veniam quis nostrud exercitation ullamco laboris nisi ut "
        "aliquip ex ea commodo consequat duis aute irure dolor in reprehenderit "
        "in voluptate velit esse cillum dolore eu fugiat nulla pariatur"
    ).split()
    lines = []
    for _ in range(paragraphs):
        length = random.randint(40, 80)
        line = " ".join(random.choices(words, k=length))
        lines.append(line.capitalize() + ".")
    return "\n\n".join(lines)


def _ensure(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)


def _mini_pdf(title: str, author: str, body: str, pages: int = 1) -> bytes:
    """Generate a minimal valid PDF 1.4 with metadata."""
    text_lines = body.replace("\n", " ")[:500]
    objects = []

    # 1 – Catalog
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj")

    # Build page references
    page_refs = " ".join(f"{3 + i} 0 R" for i in range(pages))
    # 2 – Pages
    objects.append(
        f"2 0 obj\n<< /Type /Pages /Kids [{page_refs}] /Count {pages} >>\nendobj".encode()
    )

    # Pages + Content streams
    obj_num = 3
    font_obj = 3 + pages * 2  # font object number

    for p in range(pages):
        page_obj = obj_num
        content_obj = obj_num + 1

        # Page
        objects.append(
            f"{page_obj} 0 obj\n<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 612 792] /Contents {content_obj} 0 R "
            f"/Resources << /Font << /F1 {font_obj} 0 R >> >> >>\nendobj".encode()
        )

        # Content stream
        page_text = f"Page {p+1}: {text_lines}" if pages > 1 else text_lines
        stream = f"BT /F1 12 Tf 72 720 Td ({page_text}) Tj ET".encode()
        objects.append(
            f"{content_obj} 0 obj\n<< /Length {len(stream)} >>\nstream\n".encode() +
            stream + b"\nendstream\nendobj"
        )
        obj_num += 2

    # Font
    objects.append(
        f"{font_obj} 0 obj\n<< /Type /Font /Subtype /Type1 "
        f"/BaseFont /Helvetica >>\nendobj".encode()
    )

    # Info (metadata)
    info_obj = font_obj + 1
    info = (
        f"{info_obj} 0 obj\n<< /Title ({title}) /Author ({author}) "
        f"/CreationDate (D:{datetime.now().strftime('%Y%m%d%H%M%S')}) "
        f"/Producer (DigitalLifeCleanup TestGen) >>\nendobj"
    ).encode()
    objects.append(info)

    # Assemble
    pdf = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj + b"\n"
    xref_offset = len(pdf)
    pdf += b"xref\n"
    pdf += f"0 {len(objects)+1}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += b"trailer\n"
    pdf += f"<< /Size {len(objects)+1} /Root 1 0 R /Info {info_obj} 0 R >>\n".encode()
    pdf += b"startxref\n"
    pdf += f"{xref_offset}\n".encode()
    pdf += b"%%EOF\n"
    return pdf


def _mini_bmp(width: int, height: int, base_color: tuple) -> bytes:
    """Generate a minimal BMP file."""
    row_size = (width * 3 + 3) & ~3  # Rows padded to 4-byte boundary
    pixel_data_size = row_size * height
    file_size = 54 + pixel_data_size

    # BMP header
    header = struct.pack('<2sIHHI', b'BM', file_size, 0, 0, 54)
    # DIB header (BITMAPINFOHEADER)
    dib = struct.pack('<IiiHHIIiiII',
                      40, width, height, 1, 24, 0,
                      pixel_data_size, 2835, 2835, 0, 0)

    # Pixel data (BGR format, bottom-to-top)
    pixels = bytearray()
    for y in range(height):
        for x in range(width):
            r = min(255, base_color[0] + (x * 30 // max(width, 1)))
            g = min(255, base_color[1] + (y * 30 // max(height, 1)))
            b = base_color[2]
            pixels.extend([b, g, r])  # BGR
        # Row padding
        pixels.extend(b'\x00' * (row_size - width * 3))

    return header + dib + bytes(pixels)


def _mini_gif(width: int = 10, height: int = 10, color: tuple = (255, 0, 0)) -> bytes:
    """Generate a minimal valid GIF89a file."""
    gif = bytearray()
    # Header
    gif.extend(b'GIF89a')
    # Logical Screen Descriptor
    gif.extend(struct.pack('<HH', width, height))
    gif.extend(bytes([0x80, 0, 0]))  # GCT flag, bg color, aspect ratio
    # Global Color Table (2 entries: color + black)
    gif.extend(bytes(color))
    gif.extend(bytes([0, 0, 0]))
    # Image Descriptor
    gif.extend(b'\x2C')
    gif.extend(struct.pack('<HHHH', 0, 0, width, height))
    gif.extend(bytes([0]))  # no local color table
    # Image Data
    gif.extend(bytes([2]))  # LZW minimum code size
    # Minimal compressed data block
    block = bytes([2, 0x4C, 0x01, 0])
    gif.extend(bytes([len(block) - 1]))
    gif.extend(block[:-1])
    gif.extend(bytes([0]))  # block terminator
    # Trailer
    gif.extend(b'\x3B')
    return bytes(gif)


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def create_duplicate_files():
    """Create sets of identical files in different locations."""
    print("📄 Creating duplicate files...")

    # --- Duplicate set 1: a text note ---
    content_a = "This is an important meeting note from Q3 planning.\n" * 50
    for name in ["meeting_notes.txt", "meeting_notes_copy.txt",
                  "old/meeting_notes_backup.txt"]:
        path = TEST_DIR / "documents" / name
        _ensure(path.parent)
        path.write_text(content_a, encoding="utf-8")

    # --- Duplicate set 2: a JSON config ---
    config = json.dumps({"version": "2.1", "debug": False,
                          "features": ["auth", "logging", "cache"]}, indent=2)
    for name in ["config.json", "backup/config.json",
                  "projects/app/config.json"]:
        path = TEST_DIR / name
        _ensure(path.parent)
        path.write_text(config, encoding="utf-8")

    # --- Duplicate set 3: binary-ish data ---
    data = bytes(range(256)) * 200  # 51.2 KB identical blob
    for name in ["data/blob.bin", "archive/blob_copy.bin",
                  "temp/blob.bin"]:
        path = TEST_DIR / name
        _ensure(path.parent)
        path.write_bytes(data)

    # --- Duplicate set 4: code file duplicates ---
    py_content = '''"""Utility module — shared helper functions."""

def format_bytes(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"

def validate_path(path: str) -> bool:
    import os
    return os.path.exists(path)
'''
    for name in ["projects/app/src/helpers.py",
                  "projects/backup/helpers.py",
                  "temp/old_helpers.py"]:
        path = TEST_DIR / name
        _ensure(path.parent)
        path.write_text(py_content, encoding="utf-8")

    # --- Near-duplicate (same name, DIFFERENT content — should NOT match) ---
    (TEST_DIR / "documents" / "readme_v1.txt").write_text(
        "Version 1 of the readme file.\n" * 20, encoding="utf-8"
    )
    (TEST_DIR / "documents" / "readme_v2.txt").write_text(
        "Version 2 of the readme file with updates.\n" * 20, encoding="utf-8"
    )

    print("   ✅ 4 duplicate groups (12 files) + 2 near-duplicates")


def create_pdf_files():
    """Create PDF files with metadata."""
    print("📄 Creating PDF files...")
    pdf_dir = TEST_DIR / "documents" / "pdfs"
    _ensure(pdf_dir)

    pdfs = [
        ("Quarterly_Report_Q3.pdf", "Q3 Financial Report", "Finance Team",
         "Revenue increased by 15% compared to Q2. Key growth areas include cloud services.", 1),
        ("Employee_Handbook_2024.pdf", "Employee Handbook 2024", "HR Department",
         "Welcome to the company. This handbook outlines policies and benefits.", 3),
        ("Project_Proposal_Alpha.pdf", "Project Alpha Proposal", "Jane Smith",
         "Project Alpha aims to develop a next-gen AI analytics platform.", 1),
        ("Meeting_Minutes_Jan.pdf", "January Board Meeting Minutes", "Secretary",
         "The board approved the new budget allocation and strategic initiatives.", 1),
        ("Tax_Document_2024.pdf", "Tax Filing Document 2024", "Accounting",
         "Annual tax filing: financial statements, deductions, taxable income.", 2),
    ]

    for filename, title, author, body, pages in pdfs:
        pdf_bytes = _mini_pdf(title, author, body, pages)
        (pdf_dir / filename).write_bytes(pdf_bytes)

    # --- PDF with no metadata (edge case) ---
    bare_pdf = b"%PDF-1.4\n"
    bare_pdf += b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    bare_pdf += b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    bare_pdf += b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
    xref_off = len(bare_pdf)
    bare_pdf += b"xref\n0 4\n"
    bare_pdf += b"0000000000 65535 f \n"
    bare_pdf += b"0000000009 00000 n \n"
    bare_pdf += b"0000000058 00000 n \n"
    bare_pdf += b"0000000115 00000 n \n"
    bare_pdf += b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
    bare_pdf += b"startxref\n"
    bare_pdf += f"{xref_off}\n".encode()
    bare_pdf += b"%%EOF\n"
    (pdf_dir / "no_metadata_blank.pdf").write_bytes(bare_pdf)

    # --- Large multi-page PDF ---
    big_body = "This is a long document. " * 200
    big_pdf = _mini_pdf("Annual Report Complete", "Board of Directors", big_body, pages=5)
    (pdf_dir / "Annual_Report_Full.pdf").write_bytes(big_pdf)

    print(f"   ✅ {len(pdfs) + 2} PDF files (with metadata, no metadata, multi-page)")


def create_image_files():
    """Create image files in ALL supported formats."""
    print("🖼️  Creating image files...")
    img_dir = TEST_DIR / "photos"
    _ensure(img_dir)

    has_pillow = False
    try:
        from PIL import Image
        has_pillow = True
    except ImportError:
        pass

    if has_pillow:
        from PIL import Image

        images_spec = [
            ("vacation_beach.jpg", (1920, 1080), "JPEG", (65, 150, 220)),
            ("office_team.jpg", (1280, 720), "JPEG", (180, 160, 140)),
            ("product_photo.jpg", (800, 800), "JPEG", (240, 240, 240)),
            ("sunset_mountains.png", (2560, 1440), "PNG", (255, 130, 50)),
            ("family_dinner.jpg", (1600, 1200), "JPEG", (200, 170, 100)),
            ("screenshot_dashboard.png", (1920, 1080), "PNG", (30, 30, 50)),
            ("cat_sleeping.jpg", (640, 480), "JPEG", (160, 140, 120)),
            ("architecture_building.jpg", (3000, 2000), "JPEG", (130, 130, 150)),
            # Additional formats for full coverage
            ("texture_sample.tiff", (512, 512), "TIFF", (100, 200, 150)),
            ("icon_small.bmp", (64, 64), "BMP", (0, 120, 255)),
            ("animation_frame.gif", (200, 200), "GIF", (255, 100, 50)),
            ("modern_photo.webp", (1024, 768), "WEBP", (80, 180, 220)),
            ("scan_document.tif", (800, 600), "TIFF", (240, 240, 240)),
            ("tiny_thumb.jpeg", (32, 32), "JPEG", (200, 100, 50)),
        ]

        for filename, (w, h), fmt, base_color in images_spec:
            img = Image.new("RGB", (w, h))
            pixels_data = img.load()
            for y in range(h):
                for x in range(w):
                    r = min(255, base_color[0] + (x * 30 // max(w, 1)))
                    g = min(255, base_color[1] + (y * 30 // max(h, 1)))
                    b = base_color[2]
                    pixels_data[x, y] = (r, g, b)

            filepath = img_dir / filename
            if fmt == "JPEG":
                img.save(str(filepath), "JPEG", quality=85)
            elif fmt == "WEBP":
                img.save(str(filepath), "WEBP", quality=80)
            elif fmt == "GIF":
                img = img.convert("P")
                img.save(str(filepath), "GIF")
            else:
                img.save(str(filepath), fmt)

        # Duplicate image
        import shutil
        shutil.copy2(img_dir / "vacation_beach.jpg", img_dir / "vacation_beach_copy.jpg")

        print(f"   ✅ {len(images_spec)} images + 1 duplicate (Pillow-generated)")

    else:
        print("   ⚠️  Pillow not installed — creating minimal binary images")

        # BMP files
        for name, (w, h), color in [
            ("vacation_beach.bmp", (100, 60), (65, 150, 220)),
            ("office_team.bmp", (80, 60), (180, 160, 140)),
            ("product_photo.bmp", (64, 64), (240, 240, 240)),
            ("icon_small.bmp", (32, 32), (0, 120, 255)),
        ]:
            (img_dir / name).write_bytes(_mini_bmp(w, h, color))

        # GIF files
        for name, color in [
            ("animation_frame.gif", (255, 100, 50)),
            ("cat_sleeping.gif", (160, 140, 120)),
        ]:
            (img_dir / name).write_bytes(_mini_gif(10, 10, color))

        # PNG (minimal valid 1x1 PNG)
        # Signature + IHDR + IDAT + IEND
        png_sig = b'\x89PNG\r\n\x1a\n'
        import zlib

        def _make_png(w, h, r, g, b_val):
            ihdr_data = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
            ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
            ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)

            raw = b''
            for _ in range(h):
                raw += b'\x00'  # filter byte
                for _ in range(w):
                    raw += bytes([r, g, b_val])
            compressed = zlib.compress(raw)
            idat_crc = zlib.crc32(b'IDAT' + compressed) & 0xffffffff
            idat = struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', idat_crc)

            iend_crc = zlib.crc32(b'IEND') & 0xffffffff
            iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)
            return png_sig + ihdr + idat + iend

        for name, (w, h), color in [
            ("sunset_mountains.png", (20, 15), (255, 130, 50)),
            ("screenshot_dashboard.png", (20, 15), (30, 30, 50)),
        ]:
            (img_dir / name).write_bytes(_make_png(w, h, *color))

        # JPEG (minimal valid JFIF)
        # Just create a minimal marker-based JPEG
        jpeg_min = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
            b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
            b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00'
            b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b'
            b'\xff\xda\x00\x08\x01\x01\x00\x00?\x00T\xdb\x9e\xa7\xa4\x00\x1f'
            b'\xff\xd9'
        )
        for name in ["family_dinner.jpg", "architecture_building.jpg"]:
            (img_dir / name).write_bytes(jpeg_min)

        # Duplicate
        import shutil
        if (img_dir / "vacation_beach.bmp").exists():
            shutil.copy2(img_dir / "vacation_beach.bmp", img_dir / "vacation_beach_copy.bmp")

        print("   ✅ Fallback images created (BMP/GIF/PNG/JPEG)")


def create_large_files():
    """Create files large enough to trigger compression (>1 MB for testing)."""
    print("📦 Creating large files...")
    large_dir = TEST_DIR / "large_files"
    _ensure(large_dir)

    # --- 2 MB log file (highly compressible) ---
    log_lines = []
    for i in range(20000):
        ts = f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d} "
        ts += f"{random.randint(0,23):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"
        level = random.choice(["INFO", "DEBUG", "WARN", "ERROR"])
        messages = [
            "Request processed successfully",
            "Database query completed in 45ms",
            "Cache hit for user session",
            "API rate limit approaching threshold",
            "Memory usage at 72% capacity",
            "Background job finished processing batch",
            "Connection pool recycled",
            "Health check passed all verifications",
        ]
        log_lines.append(f"[{ts}] [{level}] {random.choice(messages)}")
    (large_dir / "server_access.log").write_text("\n".join(log_lines), encoding="utf-8")

    # --- 1.5 MB CSV ---
    csv_lines = ["id,name,email,department,salary,hire_date"]
    first_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank",
                   "Grace", "Hank", "Ivy", "Jack", "Karen", "Leo"]
    depts = ["Engineering", "Marketing", "Sales", "HR", "Finance", "Support"]
    for i in range(15000):
        name = random.choice(first_names) + " " + "".join(random.choices(string.ascii_uppercase, k=1)) + "."
        email = name.split()[0].lower() + f"{i}@company.com"
        dept = random.choice(depts)
        salary = random.randint(45000, 180000)
        hire = f"20{random.randint(15,24):02d}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        csv_lines.append(f"{i},{name},{email},{dept},{salary},{hire}")
    (large_dir / "employees_database.csv").write_text("\n".join(csv_lines), encoding="utf-8")

    # --- 1 MB random-ish binary (less compressible) ---
    random_data = bytes([random.randint(0, 255) for _ in range(1_000_000)])
    (large_dir / "firmware_blob.bin").write_bytes(random_data)

    # --- 3 MB JSON dataset ---
    records = []
    for i in range(5000):
        records.append({
            "id": i,
            "timestamp": f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}T{random.randint(0,23):02d}:{random.randint(0,59):02d}:00Z",
            "sensor": f"sensor_{random.randint(1, 50)}",
            "temperature": round(random.uniform(15.0, 45.0), 2),
            "humidity": round(random.uniform(20.0, 95.0), 2),
            "pressure": round(random.uniform(980.0, 1040.0), 2),
            "status": random.choice(["active", "idle", "warning", "error"]),
            "location": {"lat": round(random.uniform(25.0, 50.0), 6),
                         "lon": round(random.uniform(-120.0, -70.0), 6)},
        })
    (large_dir / "sensor_readings.json").write_text(
        json.dumps(records, indent=2), encoding="utf-8"
    )

    # --- Borderline file: just at 500 KB (verify_tools test uses 500KB threshold) ---
    borderline = "X" * 512_000  # exactly 500 KB
    (large_dir / "borderline_500kb.txt").write_text(borderline, encoding="utf-8")

    # --- Just under threshold: 490 KB (should NOT be flagged at 500KB) ---
    under = "Y" * 490_000
    (large_dir / "under_threshold_490kb.txt").write_text(under, encoding="utf-8")

    sizes = []
    for f in large_dir.iterdir():
        s = f.stat().st_size
        sizes.append(f"{f.name}: {s / (1024*1024):.1f} MB")

    print(f"   ✅ {len(sizes)} large files (+ borderline tests)")
    for s in sizes:
        print(f"      {s}")


def create_document_files():
    """Create document files covering .docx, .doc, .txt, .md, .rtf extensions."""
    print("📝 Creating document files...")
    docs_dir = TEST_DIR / "documents" / "office"
    _ensure(docs_dir)

    # --- .txt files ---
    (docs_dir / "project_notes.txt").write_text(
        "Project Notes\n" + "=" * 40 + "\n\n" + _random_text(4),
        encoding="utf-8",
    )

    # --- .md files ---
    (docs_dir / "architecture.md").write_text(
        "# System Architecture\n\n"
        "## Overview\n"
        "The system uses a microservices architecture with the following components:\n\n"
        "- **API Gateway** — Routes requests to services\n"
        "- **Auth Service** — Handles authentication & authorization\n"
        "- **Data Pipeline** — Processes incoming data streams\n"
        "- **Storage Layer** — PostgreSQL + Redis\n\n"
        "## Diagrams\n"
        "See `diagrams/` folder for architecture diagrams.\n",
        encoding="utf-8",
    )

    # --- .rtf file (minimal valid RTF) ---
    rtf_content = (
        r"{\rtf1\ansi\deff0"
        r"{\fonttbl{\f0\fswiss Helvetica;}}"
        r"{\colortbl;\red0\green0\blue0;}"
        r"\pard\plain\f0\fs24 "
        "This is a Rich Text Format document for testing the Digital Life Cleanup system. "
        "It contains sample text that should be detected as a document file type.\par "
        "Created: 2024-01-15\par "
        "Author: Test Generator\par"
        "}"
    )
    (docs_dir / "report_draft.rtf").write_text(rtf_content, encoding="utf-8")

    # --- .docx file (minimal valid — it's actually a ZIP) ---
    docx_path = docs_dir / "quarterly_plan.docx"
    try:
        with zipfile.ZipFile(str(docx_path), 'w', zipfile.ZIP_DEFLATED) as zf:
            # Minimal OOXML structure
            zf.writestr('[Content_Types].xml',
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/word/document.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                '</Types>')
            zf.writestr('_rels/.rels',
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                'Target="word/document.xml"/>'
                '</Relationships>')
            zf.writestr('word/document.xml',
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:body>'
                '<w:p><w:r><w:t>Quarterly Plan 2024 - Digital Life Cleanup Test Document</w:t></w:r></w:p>'
                '<w:p><w:r><w:t>This document tests DOCX file type detection.</w:t></w:r></w:p>'
                '</w:body>'
                '</w:document>')
    except Exception as e:
        print(f"   ⚠️  DOCX creation failed: {e}")

    # --- .doc file (minimal binary — just a marker, not real OLE) ---
    doc_content = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'  # OLE magic bytes
    doc_content += b'\x00' * 100
    doc_content += b'Test document content for .doc format detection'
    (docs_dir / "legacy_report.doc").write_bytes(doc_content)

    print("   ✅ Document files: .txt, .md, .rtf, .docx, .doc")


def create_archive_files():
    """Create archive files covering .zip, .tar, .gz, .bz2 extensions."""
    print("📦 Creating archive files...")
    archive_dir = TEST_DIR / "archives"
    _ensure(archive_dir)

    sample_content = "Sample file content for archive testing.\n" * 10

    # --- .zip ---
    try:
        with zipfile.ZipFile(str(archive_dir / "backup_2024.zip"), 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("readme.txt", "This is a test archive.\n")
            zf.writestr("data/sample.csv", "id,value\n1,hello\n2,world\n")
            zf.writestr("config.json", json.dumps({"archived": True}))
        print("      .zip ✓")
    except Exception as e:
        print(f"      .zip ✗ ({e})")

    # --- .tar ---
    try:
        with tarfile.open(str(archive_dir / "project_backup.tar"), 'w') as tf:
            info = tarfile.TarInfo(name="readme.txt")
            content = b"Tar archive test file.\n"
            info.size = len(content)
            tf.addfile(info, io.BytesIO(content))
        print("      .tar ✓")
    except Exception as e:
        print(f"      .tar ✗ ({e})")

    # --- .tar.gz (double extension) ---
    try:
        with tarfile.open(str(archive_dir / "logs_archive.tar.gz"), 'w:gz') as tf:
            info = tarfile.TarInfo(name="access.log")
            content = b"2024-01-01 Server started\n" * 100
            info.size = len(content)
            tf.addfile(info, io.BytesIO(content))
        print("      .tar.gz ✓")
    except Exception as e:
        print(f"      .tar.gz ✗ ({e})")

    # --- .gz ---
    try:
        with gzip.open(str(archive_dir / "compressed_data.gz"), 'wb') as f:
            f.write(sample_content.encode())
        print("      .gz ✓")
    except Exception as e:
        print(f"      .gz ✗ ({e})")

    # --- .bz2 ---
    try:
        import bz2
        with bz2.open(str(archive_dir / "compressed_logs.bz2"), 'wb') as f:
            f.write(("Log entry sample.\n" * 500).encode())
        print("      .bz2 ✓")
    except Exception as e:
        print(f"      .bz2 ✗ ({e})")

    # --- .7z and .rar — create placeholder with magic bytes ---
    # 7z magic: 37 7A BC AF 27 1C
    (archive_dir / "old_backup.7z").write_bytes(
        b'\x37\x7a\xbc\xaf\x27\x1c' + b'\x00' * 100 + b'7z placeholder'
    )
    # RAR magic: 52 61 72 21 1A 07
    (archive_dir / "media_archive.rar").write_bytes(
        b'\x52\x61\x72\x21\x1a\x07' + b'\x00' * 100 + b'RAR placeholder'
    )

    print("   ✅ Archive files: .zip, .tar, .tar.gz, .gz, .bz2, .7z, .rar")


def create_code_files():
    """Create code files covering ALL extensions from config.py."""
    print("💻 Creating code files...")
    code_dir = TEST_DIR / "projects" / "app" / "src"
    _ensure(code_dir)

    # --- Python (.py) ---
    (code_dir / "main.py").write_text(
        '"""Main application entry point."""\n\n'
        "import sys\n\ndef main():\n    print('Hello World')\n\n"
        "if __name__ == '__main__':\n    main()\n",
        encoding="utf-8",
    )
    (code_dir / "utils.py").write_text(
        "def format_size(size_bytes: int) -> str:\n"
        "    for unit in ['B', 'KB', 'MB', 'GB']:\n"
        "        if size_bytes < 1024:\n"
        "            return f'{size_bytes:.1f} {unit}'\n"
        "        size_bytes /= 1024\n"
        "    return f'{size_bytes:.1f} TB'\n",
        encoding="utf-8",
    )

    # --- JavaScript (.js) ---
    (code_dir / "app.js").write_text(
        "// Frontend application\n"
        "const App = () => {\n"
        "  console.log('App initialized');\n"
        "  return { status: 'running' };\n"
        "};\n"
        "module.exports = App;\n",
        encoding="utf-8",
    )

    # --- TypeScript (.ts) ---
    (code_dir / "service.ts").write_text(
        "interface UserService {\n"
        "  getUser(id: string): Promise<User>;\n"
        "  createUser(data: CreateUserDTO): Promise<User>;\n"
        "}\n\n"
        "interface User {\n"
        "  id: string;\n"
        "  name: string;\n"
        "  email: string;\n"
        "}\n\n"
        "interface CreateUserDTO {\n"
        "  name: string;\n"
        "  email: string;\n"
        "}\n\n"
        "class UserServiceImpl implements UserService {\n"
        "  async getUser(id: string): Promise<User> {\n"
        "    return { id, name: 'Test', email: 'test@example.com' };\n"
        "  }\n"
        "  async createUser(data: CreateUserDTO): Promise<User> {\n"
        "    return { id: 'new-id', ...data };\n"
        "  }\n"
        "}\n\n"
        "export default UserServiceImpl;\n",
        encoding="utf-8",
    )

    # --- Java (.java) ---
    (code_dir / "Application.java").write_text(
        "package com.example.app;\n\n"
        "public class Application {\n"
        "    public static void main(String[] args) {\n"
        '        System.out.println("Digital Life Cleanup - Java Test");\n'
        "    }\n\n"
        "    public static String formatSize(long bytes) {\n"
        '        String[] units = {"B", "KB", "MB", "GB"};\n'
        "        double size = bytes;\n"
        "        int unitIndex = 0;\n"
        "        while (size >= 1024 && unitIndex < units.length - 1) {\n"
        "            size /= 1024;\n"
        "            unitIndex++;\n"
        "        }\n"
        '        return String.format("%.1f %s", size, units[unitIndex]);\n'
        "    }\n"
        "}\n",
        encoding="utf-8",
    )

    # --- C++ (.cpp) ---
    (code_dir / "processor.cpp").write_text(
        "#include <iostream>\n"
        "#include <string>\n"
        "#include <vector>\n\n"
        "class FileProcessor {\n"
        "public:\n"
        "    void processFile(const std::string& path) {\n"
        '        std::cout << "Processing: " << path << std::endl;\n'
        "    }\n\n"
        "    size_t getFileCount() const { return fileCount_; }\n\n"
        "private:\n"
        "    size_t fileCount_ = 0;\n"
        "};\n\n"
        "int main() {\n"
        "    FileProcessor processor;\n"
        '    processor.processFile("test.txt");\n'
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )

    # --- C (.c) ---
    (code_dir / "hash.c").write_text(
        "#include <stdio.h>\n"
        "#include <stdlib.h>\n"
        "#include <string.h>\n\n"
        "unsigned long simple_hash(const char* str) {\n"
        "    unsigned long hash = 5381;\n"
        "    int c;\n"
        "    while ((c = *str++))\n"
        "        hash = ((hash << 5) + hash) + c;\n"
        "    return hash;\n"
        "}\n\n"
        "int main() {\n"
        '    printf("Hash: %lu\\n", simple_hash("hello"));\n'
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )

    # --- Header (.h) ---
    (code_dir / "hash.h").write_text(
        "#ifndef HASH_H\n"
        "#define HASH_H\n\n"
        "#ifdef __cplusplus\n"
        'extern "C" {\n'
        "#endif\n\n"
        "unsigned long simple_hash(const char* str);\n\n"
        "#ifdef __cplusplus\n"
        "}\n"
        "#endif\n\n"
        "#endif /* HASH_H */\n",
        encoding="utf-8",
    )

    # --- Go (.go) ---
    (code_dir / "scanner.go").write_text(
        "package main\n\n"
        "import (\n"
        '\t"fmt"\n'
        '\t"os"\n'
        '\t"path/filepath"\n'
        ")\n\n"
        "func scanDirectory(root string) ([]string, error) {\n"
        "\tvar files []string\n"
        "\terr := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {\n"
        "\t\tif err != nil {\n"
        "\t\t\treturn err\n"
        "\t\t}\n"
        "\t\tif !info.IsDir() {\n"
        "\t\t\tfiles = append(files, path)\n"
        "\t\t}\n"
        "\t\treturn nil\n"
        "\t})\n"
        "\treturn files, err\n"
        "}\n\n"
        "func main() {\n"
        '\tfiles, _ := scanDirectory(".")\n'
        '\tfmt.Printf("Found %d files\\n", len(files))\n'
        "}\n",
        encoding="utf-8",
    )

    # --- Rust (.rs) ---
    (code_dir / "dedup.rs").write_text(
        "use std::collections::HashMap;\n"
        "use std::fs;\n"
        "use std::path::Path;\n\n"
        "fn find_duplicates(dir: &Path) -> HashMap<u64, Vec<String>> {\n"
        "    let mut size_groups: HashMap<u64, Vec<String>> = HashMap::new();\n\n"
        "    if let Ok(entries) = fs::read_dir(dir) {\n"
        "        for entry in entries.flatten() {\n"
        "            if let Ok(metadata) = entry.metadata() {\n"
        "                if metadata.is_file() {\n"
        "                    size_groups\n"
        "                        .entry(metadata.len())\n"
        "                        .or_default()\n"
        "                        .push(entry.path().display().to_string());\n"
        "                }\n"
        "            }\n"
        "        }\n"
        "    }\n\n"
        "    size_groups.retain(|_, v| v.len() > 1);\n"
        "    size_groups\n"
        "}\n\n"
        'fn main() {\n'
        '    let dupes = find_duplicates(Path::new("."));\n'
        '    println!("Found {} duplicate groups", dupes.len());\n'
        "}\n",
        encoding="utf-8",
    )

    print("   ✅ Code files: .py, .js, .ts, .java, .cpp, .c, .h, .go, .rs")


def create_sensitive_files():
    """Create files with sensitive content for encryption testing."""
    print("🔒 Creating sensitive files...")
    sensitive_dir = TEST_DIR / "documents" / "sensitive"
    _ensure(sensitive_dir)

    (sensitive_dir / "personal_diary.txt").write_text(
        "Dear Diary,\n\n"
        "Today was a wonderful day. I went to the park and saw beautiful flowers.\n"
        "The weather was perfect for a walk. I also met an old friend at the cafe.\n\n"
        "Note to self: Remember to call mom on her birthday next week.\n"
        "Bank account: XXXX-1234\nSSN: Should not store this here!\n"
        "Credit Card: 4111-1111-1111-1111\n"
        "API Key: sk-proj-abc123def456ghi789\n",
        encoding="utf-8",
    )

    (sensitive_dir / "passwords.txt").write_text(
        "=== DO NOT SHARE ===\n"
        "Email: user@example.com / P@ssw0rd123!\n"
        "Server: admin / SuperSecret2024\n"
        "Database: root / db_master_key_2024\n"
        "AWS Access Key: AKIAIOSFODNN7EXAMPLE\n"
        "AWS Secret: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\n",
        encoding="utf-8",
    )

    (sensitive_dir / "api_config.json").write_text(
        json.dumps({
            "openai_api_key": "sk-proj-fake-key-for-testing-only",
            "stripe_secret": "sk_live_fake_stripe_key",
            "database_url": "postgresql://admin:password@db.example.com:5432/prod",
            "jwt_secret": "super-secret-jwt-signing-key-2024",
        }, indent=2),
        encoding="utf-8",
    )

    (sensitive_dir / "employee_salaries.csv").write_text(
        "name,email,salary,ssn,bank_account\n"
        "John Doe,john@company.com,150000,123-45-6789,ACC-001234\n"
        "Jane Smith,jane@company.com,165000,987-65-4321,ACC-005678\n"
        "Bob Wilson,bob@company.com,142000,456-78-9012,ACC-009012\n",
        encoding="utf-8",
    )

    print("   ✅ 4 sensitive files (diary, passwords, API keys, salary data)")


def create_edge_case_files():
    """Create files for various edge cases."""
    print("🔧 Creating edge case files...")

    # --- Empty directory ---
    _ensure(TEST_DIR / "empty_folder")

    # --- Deeply nested file ---
    deep = TEST_DIR / "level1" / "level2" / "level3" / "level4"
    _ensure(deep)
    (deep / "deeply_nested.txt").write_text("Found me!\n", encoding="utf-8")

    # --- Even deeper ---
    very_deep = TEST_DIR / "level1" / "level2" / "level3" / "level4" / "level5" / "level6"
    _ensure(very_deep)
    (very_deep / "very_deep_file.log").write_text("Very deep file!\n", encoding="utf-8")

    # --- Zero-byte files ---
    edge_dir = TEST_DIR / "edge_cases"
    _ensure(edge_dir)
    (edge_dir / "empty_file.txt").write_bytes(b"")
    (edge_dir / "empty_file.json").write_bytes(b"")
    (edge_dir / "empty_file.csv").write_bytes(b"")

    # --- Very small files ---
    (edge_dir / "tiny.txt").write_text("Hi", encoding="utf-8")
    (edge_dir / "one_byte.bin").write_bytes(b"\x42")

    # --- Files with spaces in names ---
    spaces_dir = TEST_DIR / "edge_cases" / "spaced names"
    _ensure(spaces_dir)
    (spaces_dir / "my document (final).txt").write_text(
        "Document with spaces and parens in filename.\n", encoding="utf-8"
    )
    (spaces_dir / "report 2024 Q3.md").write_text(
        "# Report Q3 2024\n\nContent here.\n", encoding="utf-8"
    )

    # --- Files with special characters ---
    (edge_dir / "file-with-dashes.txt").write_text("Dashes in name.\n", encoding="utf-8")
    (edge_dir / "file_with_underscores.txt").write_text("Underscores in name.\n", encoding="utf-8")
    (edge_dir / "FILE.UPPERCASE.TXT").write_text("Uppercase extension.\n", encoding="utf-8")
    (edge_dir / "mixedCase.Txt").write_text("Mixed case extension.\n", encoding="utf-8")

    # --- Hidden-style dotfiles ---
    (edge_dir / ".hidden_config").write_text(
        "HIDDEN=true\nDEBUG=false\n", encoding="utf-8"
    )
    (edge_dir / ".gitignore").write_text(
        "*.pyc\n__pycache__/\n.env\nnode_modules/\n", encoding="utf-8"
    )
    (edge_dir / ".env").write_text(
        "DATABASE_URL=postgres://user:pass@localhost/db\n"
        "SECRET_KEY=not-a-real-secret\n"
        "API_KEY=test-api-key-12345\n",
        encoding="utf-8",
    )

    # --- Unicode filename ---
    try:
        (edge_dir / "données_rapport.txt").write_text(
            "Rapport avec des caractères spéciaux: é, è, ê, ë, à, â, ç\n",
            encoding="utf-8",
        )
    except (OSError, UnicodeError):
        print("   ⚠️  Unicode filename not supported on this filesystem")

    # --- Multiple extension file ---
    (edge_dir / "data.backup.2024.json").write_text(
        json.dumps({"type": "backup", "date": "2024-01-15"}), encoding="utf-8"
    )

    # --- Binary files with known extensions ---
    (edge_dir / "corrupted.pdf").write_bytes(b"This is not a real PDF\x00\xff\xfe")
    (edge_dir / "corrupted.jpg").write_bytes(b"This is not a real JPEG\x00\xff\xfe")

    print("   ✅ Edge cases: empty dirs, nested files, zero-byte, spaces, "
          "dotfiles, unicode, corrupted files")


def create_misc_files():
    """Create miscellaneous text/notes files."""
    print("📝 Creating miscellaneous files...")

    # --- Text documents ---
    docs_dir = TEST_DIR / "documents" / "notes"
    _ensure(docs_dir)

    (docs_dir / "todo_list.md").write_text(
        "# TODO List\n\n"
        "- [x] Set up project structure\n"
        "- [x] Implement core features\n"
        "- [ ] Write unit tests\n"
        "- [ ] Deploy to production\n"
        "- [ ] Update documentation\n",
        encoding="utf-8",
    )
    (docs_dir / "ideas.txt").write_text(_random_text(5), encoding="utf-8")

    # --- README ---
    (TEST_DIR / "README.md").write_text(
        "# Test Sample Folder\n\n"
        "This folder was auto-generated to test the Digital Life Cleanup system.\n\n"
        "## Contents\n"
        "- `documents/` — PDFs, notes, meeting minutes, office docs (with duplicates)\n"
        "- `documents/sensitive/` — Files with sensitive data (for encryption testing)\n"
        "- `documents/office/` — .docx, .doc, .rtf, .txt, .md files\n"
        "- `photos/` — Images in JPEG/PNG/BMP/GIF/TIFF/WEBP format\n"
        "- `large_files/` — Log, CSV, binary, and JSON files >1 MB\n"
        "- `projects/` — Source code files (.py, .js, .ts, .java, .cpp, .c, .h, .go, .rs)\n"
        "- `archives/` — Archive files (.zip, .tar, .gz, .bz2, .7z, .rar)\n"
        "- `data/`, `temp/`, `archive/`, `backup/` — Duplicate binary blobs\n"
        "- `edge_cases/` — Zero-byte, dotfiles, unicode, corrupted, special chars\n"
        "- `empty_folder/` — Edge case: empty directory\n"
        "- `level1/.../level6/` — Deeply nested files\n",
        encoding="utf-8",
    )

    print("   ✅ Misc files: notes, README")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("🧪 Digital Life Cleanup — Comprehensive Test Data Generator")
    print("=" * 60)
    print(f"\n📁 Target: {TEST_DIR}\n")

    if TEST_DIR.exists():
        import shutil
        shutil.rmtree(TEST_DIR)
        print("   (cleared existing test folder)\n")

    _ensure(TEST_DIR)

    create_duplicate_files()
    create_pdf_files()
    create_image_files()
    create_large_files()
    create_document_files()
    create_archive_files()
    create_code_files()
    create_sensitive_files()
    create_edge_case_files()
    create_misc_files()

    # --- Summary ---
    total_files = 0
    total_size = 0
    ext_counts = {}
    for root, dirs, files in os.walk(TEST_DIR):
        for f in files:
            fp = os.path.join(root, f)
            total_files += 1
            total_size += os.path.getsize(fp)
            ext = Path(f).suffix.lower() or "(no ext)"
            ext_counts[ext] = ext_counts.get(ext, 0) + 1

    print(f"\n{'=' * 60}")
    print(f"✅ Test folder ready!")
    print(f"   📁 Path:  {TEST_DIR}")
    print(f"   📄 Files: {total_files}")
    print(f"   💾 Size:  {total_size / (1024*1024):.1f} MB")
    print(f"\n   📊 Extensions breakdown:")
    for ext, count in sorted(ext_counts.items(), key=lambda x: -x[1]):
        print(f"      {ext:12s} → {count} files")
    print(f"{'=' * 60}")
    print(f"\nNow run:  python main.py")
    print(f"And select: {TEST_DIR}")


if __name__ == "__main__":
    main()
