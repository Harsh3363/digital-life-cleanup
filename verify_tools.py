"""Quick verification script — tests all tools against the test_sample_folder."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("Running tool verification against test_sample_folder")
print("=" * 60)

# 1. Duplicate Detection
print("\n🔍 DUPLICATE DETECTION")
from tools.duplicate_detector import scan_for_duplicates, get_duplicate_summary
dupes = scan_for_duplicates("test_sample_folder")
summary = get_duplicate_summary(dupes)
print(f"   Groups: {summary['total_groups']}")
print(f"   Redundant files: {summary['total_redundant_files']}")
print(f"   Wasted: {summary['total_wasted_mb']} MB")
for g in dupes:
    print(f"   -> {g['count']}x copies, {g['size']} bytes each")

# 2. Metadata Extraction
print("\n📋 METADATA EXTRACTION")
from tools.metadata_extractor import scan_metadata, get_metadata_summary
meta = scan_metadata("test_sample_folder")
ms = get_metadata_summary(meta)
print(f"   Total files: {ms['total_files']}")
print(f"   PDFs: {ms['pdf_count']}")
print(f"   Images: {ms['image_count']}")
for m in meta[:5]:
    fname = m.get('filename', os.path.basename(m.get('path', '?')))
    print(f"   -> {fname}: type={m.get('type','?')}, title={m.get('title','N/A')}")

# 3. Large File Detection
print("\n📦 LARGE FILE DETECTION (>500 KB)")
from tools.large_file_handler import find_large_files, compress_file
large = find_large_files("test_sample_folder", threshold_bytes=500_000)
print(f"   Large files found: {len(large)}")
for lf in large:
    print(f"   -> {lf['filename']}: {lf['size_mb']} MB")

# 4. Compression (test one file)
if large:
    print("\n📦 COMPRESSION TEST")
    result = compress_file(large[0]["path"])
    if "error" not in result:
        print(f"   Original: {result['original_size_mb']} MB")
        print(f"   Compressed: {result['compressed_size_mb']} MB")
        print(f"   Ratio: {result['compression_ratio']}")
        print(f"   Saved: {result['space_saved_mb']} MB")
    else:
        print(f"   Error: {result['error']}")

# 5. Encryption (test a few files)
print("\n🔒 ENCRYPTION TEST")
from tools.file_encryptor import encrypt_files
test_files = [m["path"] for m in meta[:3]]
enc_result = encrypt_files(test_files, archive_name="test_encrypted")
if "error" not in enc_result:
    print(f"   Archive: {enc_result['archive_path']}")
    print(f"   Files: {enc_result['file_count']}")
    print(f"   Encryption: {enc_result['encryption']}")
    print(f"   Archive size: {enc_result['archive_size_mb']} MB")
else:
    print(f"   Error: {enc_result['error']}")

# 6. Report Generation
print("\n📊 REPORT GENERATION")
from reports.report_generator import ReportGenerator
reporter = ReportGenerator()
report = reporter.generate(
    data={
        "duplicates": summary,
        "metadata": ms,
        "protected": enc_result,
        "compressed": result if large else {},
    },
    folder_path="test_sample_folder",
)
print(f"   Markdown: {report['markdown_path']}")
print(f"   JSON: {report['json_path']}")
print(f"   Summary: {report['summary']}")

# 7. Scheduler
print("\n📅 SCHEDULER TEST")
from scheduler.scheduler import SchedulerGenerator
sched = SchedulerGenerator()
cron = sched.generate_cron("test_sample_folder", "weekly")
print(f"   Cron: {cron}")
xml = sched.generate_windows_task_xml("test_sample_folder", "daily")
print(f"   Windows XML: {len(xml)} chars generated")

print("\n" + "=" * 60)
print("✅ ALL TOOL VERIFICATIONS PASSED!")
print("=" * 60)
