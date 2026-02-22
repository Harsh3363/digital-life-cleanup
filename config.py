"""
Digital Life Cleanup & Protection System — Configuration
Shared constants, paths, and default settings.
"""

import os
from pathlib import Path

# ── Project Paths ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports_output"

# ── File Handling ──────────────────────────────────────────────
CHUNK_SIZE = 8192  # 8KB — used for streaming reads (hashing, compression)
PARTIAL_HASH_SIZE = 4096  # 4KB — first + last bytes for quick dedup pre-filter
LARGE_FILE_THRESHOLD = 100 * 1024 * 1024  # 100MB — files above this get compressed

# ── Encryption ─────────────────────────────────────────────────
DEFAULT_ENCRYPTION_METHOD = "AES-256"  # pyzipper WZ_AES encryption

# ── Supported Extensions ──────────────────────────────────────
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif", ".webp"}
PDF_EXTENSIONS = {".pdf"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md", ".rtf"}
ARCHIVE_EXTENSIONS = {".zip", ".tar", ".gz", ".bz2", ".7z", ".rar"}
CODE_EXTENSIONS = {".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".go", ".rs"}

ALL_KNOWN_EXTENSIONS = (
    IMAGE_EXTENSIONS | PDF_EXTENSIONS | DOCUMENT_EXTENSIONS |
    ARCHIVE_EXTENSIONS | CODE_EXTENSIONS
)

# ── Operating Modes ───────────────────────────────────────────
MODE_SMART = "smart"       # Built-in rule-based (no AI needed)
MODE_OLLAMA = "ollama"     # Local Ollama LLM (free, no API key)
MODE_API = "api"           # External API (OpenAI, Anthropic, etc.)
DEFAULT_MODE = MODE_SMART

# ── Accomplish / AI Orchestrator ──────────────────────────────
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_API_BASE = "https://api.openai.com/v1"
MAX_ORCHESTRATOR_ITERATIONS = 20  # Safety cap on orchestrator loop

# ── Ollama Configuration ─────────────────────────────────────
OLLAMA_API_BASE = "http://localhost:11434/v1"
OLLAMA_DEFAULT_MODEL = "llama3.2"
OLLAMA_FALLBACK_MODELS = ["llama3.2", "llama3.1", "mistral", "qwen2.5", "phi3"]

# ── Smart Mode Configuration ─────────────────────────────────
LARGE_FILE_THRESHOLD_SMART = 500_000  # 500 KB for smart mode (lower for demos)
SENSITIVE_KEYWORDS = [
    "password", "passwd", "ssn", "social security",
    "credit card", "bank account", "api key", "api_key",
    "secret", "private key", "access key", "token",
    "confidential", "salary", "routing number",
]

# ── Scheduler ──────────────────────────────────────────────────
SCHEDULER_FREQUENCIES = ["daily", "weekly", "monthly"]

# ── Logging ────────────────────────────────────────────────────
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def ensure_dirs():
    """Create output directories if they don't exist."""
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
