# 🧹 Digital Life Cleanup & Protection System

**Powered by [Accomplish](https://github.com/accomplish-ai/accomplish) AI Orchestrator**

A modular system where Accomplish acts as the AI decision-maker and Python modules serve as deterministic tools for filesystem cleanup, protection, and reporting.

> **This is NOT a standalone automation script.** It's an orchestration showcase where Accomplish decides what to do, and Python tools execute the actions.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Duplicate Detection** | SHA256 + partial hash pre-filtering, streams in 8KB chunks |
| 📋 **Metadata Extraction** | PDF metadata (PyPDF2) + Image EXIF (Pillow) |
| 🔒 **File Protection** | AES-256 encrypted ZIP archives (pyzipper) |
| 📦 **Large File Compression** | Streaming gzip, never loads full files into memory |
| 🤖 **AI Orchestration** | Accomplish decides classification + tool selection |
| 🖥️ **Tkinter GUI** | Dark-themed UI with real-time logs |
| 📅 **Scheduler** | Cron (Unix) + Windows Task Scheduler XML |
| 📊 **Reporting** | Markdown + JSON reports |

## 🏗️ Architecture

```
Accomplish AI (Orchestrator)
    ↕  Decides what to do, calls tools
Python Tool Modules (Executors)
    ├── duplicate_detector.py    ← SHA256 streaming hash
    ├── metadata_extractor.py    ← PDF/Image metadata
    ├── file_encryptor.py        ← AES-256 ZIP creation
    └── large_file_handler.py    ← Streaming gzip compression
```

**Key principle:** Python tools contain ZERO classification logic. Accomplish is the brain — it analyzes scan results and decides which tools to call next.

## 📁 Project Structure

```
digital-life-cleanup/
├── main.py                    # Entry point (GUI / CLI / Scheduler)
├── config.py                  # Shared constants and settings
├── requirements.txt           # Python dependencies
├── tools/
│   ├── duplicate_detector.py  # SHA256 + partial hash dedup
│   ├── metadata_extractor.py  # PDF/image metadata extraction
│   ├── file_encryptor.py      # AES-256 encrypted ZIP
│   └── large_file_handler.py  # Streaming gzip compression
├── orchestrator/
│   ├── accomplish_bridge.py   # AI ↔ Tool communication bridge
│   ├── workflow.py            # High-level workflow controller
│   └── tool_registry.py      # Tool schemas + dispatch map
├── scheduler/
│   └── scheduler.py           # Cron / Windows Task Scheduler
├── reports/
│   └── report_generator.py    # Markdown + JSON reports
└── ui/
    └── app.py                 # Tkinter GUI
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd digital-life-cleanup
pip install -r requirements.txt
```

### 2. Launch GUI

```bash
python main.py
```

### 3. CLI Mode

```bash
# Basic usage
python main.py --cli --folder "C:\Users\you\Documents" --api-key sk-...

# With options
python main.py --cli --folder ~/Documents --model gpt-4o --no-compression

# Use environment variable for API key
set OPENAI_API_KEY=sk-...
python main.py --cli --folder ~/Documents
```

### 4. Generate Schedule

```bash
python main.py --schedule --folder "C:\Users\you\Documents" --frequency weekly
```

## 🔧 Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Model | `gpt-4o-mini` | AI model for orchestration |
| API Base | `https://api.openai.com/v1` | OpenAI-compatible endpoint |
| Chunk Size | 8 KB | Streaming read size |
| Large File Threshold | 100 MB | Files above this get flagged |
| Max Iterations | 20 | Safety cap on AI orchestration loop |

Supports any OpenAI-compatible API (OpenAI, Anthropic via proxy, Ollama, etc.)

## 🛡️ Privacy & Security

- **100% local** — no data leaves your machine (except AI API calls)
- **You control the AI** — bring your own API key
- **No telemetry** — zero tracking, zero analytics
- **AES-256 encryption** — military-grade file protection

## 📊 Reports

After each run, the system generates:
- `Digital_Life_Report.md` — Human-readable summary
- `DigitalLife_Index.json` — Machine-readable index

Reports include: duplicate analysis, metadata findings, protection actions, and compression results.

## 🔗 How Accomplish Orchestrates

1. User triggers "Clean My Digital Life"
2. Accomplish receives the command + tool definitions
3. Accomplish decides to scan for duplicates → calls `scan_duplicates`
4. Accomplish analyzes results → decides to extract metadata → calls `extract_metadata`
5. Accomplish identifies sensitive files → calls `encrypt_files`
6. Accomplish finds large files → calls `compress_large_files`
7. Accomplish generates final report → calls `generate_report`

**Accomplish is the brain. Python tools are the hands.**

---

*Built for the WeMakeDev Hackathon — demonstrating AI-orchestrated local workflows.*
