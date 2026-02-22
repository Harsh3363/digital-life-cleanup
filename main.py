#!/usr/bin/env python3
"""
Digital Life Cleanup & Protection System
=========================================
Powered by Accomplish AI Orchestrator

Entry point for both GUI and CLI modes.
Supports three operating modes:
  - smart:  Built-in rule-based orchestrator (DEFAULT — no AI needed)
  - ollama: Local Ollama LLM (free, no API key)
  - api:    External API (OpenAI, Anthropic, etc.)

Usage:
    python main.py                                     # Launch GUI
    python main.py --cli --folder <path>               # Smart Mode (default)
    python main.py --cli --folder <path> --mode ollama # Ollama Mode
    python main.py --cli --folder <path> --mode api --api-key <key>
    python main.py --schedule --folder <path>          # Generate scheduler config
    python main.py --help                              # Show help
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Fix Windows console encoding for emoji/unicode output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass  # Older Python or non-standard stdout

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    DEFAULT_MODEL,
    DEFAULT_API_BASE,
    DEFAULT_MODE,
    MODE_SMART,
    MODE_OLLAMA,
    MODE_API,
    ensure_dirs,
)


def setup_logging(verbose: bool = False):
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )


def run_gui():
    """Launch the Tkinter GUI."""
    from ui.app import launch_gui
    launch_gui()


def run_cli(args):
    """Run the cleanup workflow in headless CLI mode."""
    from orchestrator.workflow import run_cleanup_workflow

    folder = args.folder
    if not folder:
        print("Error: --folder is required in CLI mode")
        sys.exit(1)

    if not os.path.isdir(folder):
        print(f"Error: Folder does not exist: {folder}")
        sys.exit(1)

    mode = args.mode or DEFAULT_MODE

    # API key only required for API mode
    api_key = ""
    if mode == MODE_API:
        api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            print("Error: API key required for API mode.")
            print("       Use --api-key or set OPENAI_API_KEY env var.")
            print("       Or use --mode smart (no API needed)")
            sys.exit(1)
    elif mode == MODE_OLLAMA:
        api_key = "ollama"
    else:
        api_key = ""

    model = args.model or DEFAULT_MODEL
    api_base = args.api_base or DEFAULT_API_BASE

    mode_labels = {
        MODE_SMART: "🧠 Smart Mode (built-in, no AI)",
        MODE_OLLAMA: "🦙 Ollama (local AI)",
        MODE_API: "🔑 API Mode (external AI)",
    }

    print("=" * 60)
    print("🧹 Digital Life Cleanup & Protection System")
    print("   Powered by Accomplish AI Orchestrator")
    print("=" * 60)
    print(f"\n📁 Target folder: {folder}")
    print(f"⚡ Mode: {mode_labels.get(mode, mode)}")
    if mode == MODE_API:
        print(f"🤖 Model: {model}")
    elif mode == MODE_OLLAMA:
        print(f"🦙 Model: {model if model != DEFAULT_MODEL else 'auto-detect'}")
    print(f"🔍 Duplicates: {'✅' if not args.no_duplicates else '❌'}")
    print(f"🔒 Protection: {'✅' if not args.no_protection else '❌'}")
    print(f"📦 Compression: {'✅' if not args.no_compression else '❌'}")
    print()

    def log_callback(msg):
        print(msg)

    result = run_cleanup_workflow(
        folder_path=folder,
        mode=mode,
        api_key=api_key,
        model=model,
        api_base=api_base,
        enable_protection=not args.no_protection,
        enable_compression=not args.no_compression,
        enable_duplicates=not args.no_duplicates,
        log_callback=log_callback,
    )

    print("\n" + "=" * 60)
    status = result.get("status", "unknown")
    if status == "completed":
        print(f"✅ Cleanup completed!")
        print(f"   Iterations: {result.get('iterations', 0)}")
        print(f"   Tool calls: {result.get('tool_calls_made', 0)}")
        summary = result.get("final_summary", "")
        if summary:
            print(f"\n📋 Summary:\n{summary}")
    else:
        print(f"❌ Cleanup failed: {result.get('error', 'Unknown')}")

    print("=" * 60)


def run_schedule(args):
    """Generate scheduler configuration."""
    from scheduler.scheduler import SchedulerGenerator

    folder = args.folder
    if not folder:
        print("Error: --folder is required for schedule generation")
        sys.exit(1)

    frequency = args.frequency or "weekly"
    gen = SchedulerGenerator()

    print("=" * 60)
    print("📅 Digital Life Cleanup — Scheduler Configuration")
    print("=" * 60)
    print(f"\n📁 Target folder: {folder}")
    print(f"⏰ Frequency: {frequency}")
    print()

    if os.name == "nt":
        # Windows
        xml_path = gen.save_windows_task_xml(folder, frequency)
        print(f"✅ Windows Task Scheduler XML saved: {xml_path}")
        print()
        print(gen.generate_install_instructions(folder, frequency))
    else:
        # Unix
        print(gen.generate_cron_install_instructions(folder, frequency))

    print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="🧹 Digital Life Cleanup & Protection System — Powered by Accomplish",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                          # Launch GUI
  python main.py --cli --folder ~/Documents               # Smart Mode (no API!)
  python main.py --cli --folder ~/Documents --mode ollama # Ollama Mode (local AI)
  python main.py --cli --folder ~/Documents --mode api --api-key sk-...
  python main.py --schedule --folder ~/Documents          # Generate schedule
  python main.py --cli --folder ~/Documents --no-protection   # Skip encryption

Modes:
  smart   Built-in orchestrator (DEFAULT) — no AI, no API key needed
  ollama  Local Ollama LLM — free, runs on your machine
  api     External API — requires API key (OpenAI, Anthropic, etc.)
        """,
    )

    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in headless CLI mode (no GUI)",
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Generate scheduler configuration (cron/Windows Task Scheduler)",
    )
    parser.add_argument(
        "--folder",
        type=str,
        help="Target folder path to clean up",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["smart", "ollama", "api"],
        default=DEFAULT_MODE,
        help=f"Operating mode (default: {DEFAULT_MODE}). "
             "smart=no AI needed, ollama=local AI, api=external API",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="AI API key (only needed for --mode api, or set OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--api-base",
        type=str,
        default=DEFAULT_API_BASE,
        help=f"API base URL (default: {DEFAULT_API_BASE})",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"AI model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--frequency",
        type=str,
        choices=["daily", "weekly", "monthly"],
        default="weekly",
        help="Schedule frequency (default: weekly)",
    )
    parser.add_argument(
        "--no-protection",
        action="store_true",
        help="Disable file encryption",
    )
    parser.add_argument(
        "--no-compression",
        action="store_true",
        help="Disable file compression",
    )
    parser.add_argument(
        "--no-duplicates",
        action="store_true",
        help="Disable duplicate detection",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    setup_logging(args.verbose)
    ensure_dirs()

    if args.schedule:
        run_schedule(args)
    elif args.cli:
        run_cli(args)
    else:
        run_gui()


if __name__ == "__main__":
    main()
