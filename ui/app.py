"""
Digital Life Cleanup — Tkinter UI

Modern dark-themed GUI for the Digital Life Cleanup & Protection System.
Features:
  - Folder selection dialog
  - Mode selector (Smart / Ollama / API) — Smart Mode needs zero config!
  - Toggle controls for protection, compression, and duplicate detection
  - Conditional API key/model fields (only shown for API mode)
  - Real-time log output panel
  - Ollama auto-detection indicator
  - Progress indication
  - Scheduler configuration
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    DEFAULT_MODE, MODE_SMART, MODE_OLLAMA, MODE_API,
    DEFAULT_MODEL, DEFAULT_API_BASE,
    OLLAMA_DEFAULT_MODEL, OLLAMA_API_BASE,
)


class DigitalLifeApp:
    """Main Tkinter application for Digital Life Cleanup."""

    # ── Color Palette (Dark Theme) ───────────────────────────────
    BG_DARK = "#1a1a2e"
    BG_CARD = "#16213e"
    BG_INPUT = "#0f3460"
    FG_PRIMARY = "#e2e8f0"
    FG_SECONDARY = "#94a3b8"
    FG_ACCENT = "#00d4aa"
    FG_WARNING = "#f59e0b"
    FG_ERROR = "#ef4444"
    FG_SUCCESS = "#22c55e"
    BORDER_COLOR = "#334155"
    BUTTON_BG = "#00d4aa"
    BUTTON_FG = "#1a1a2e"
    BUTTON_HOVER = "#00b894"

    MODE_DISPLAY = {
        MODE_SMART: "🧠 Smart Mode (No AI — Works Offline)",
        MODE_OLLAMA: "🦙 Ollama (Local AI — Free)",
        MODE_API: "🔑 API Mode (External AI — Needs Key)",
    }

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🧹 Digital Life Cleanup & Protection System")
        self.root.geometry("900x750")
        self.root.minsize(800, 650)
        self.root.configure(bg=self.BG_DARK)

        # State variables
        self.folder_path = tk.StringVar()
        self.selected_mode = tk.StringVar(value=self.MODE_DISPLAY[DEFAULT_MODE])
        self.api_key = tk.StringVar()
        self.api_base = tk.StringVar(value=DEFAULT_API_BASE)
        self.model = tk.StringVar(value=DEFAULT_MODEL)
        self.enable_protection = tk.BooleanVar(value=True)
        self.enable_compression = tk.BooleanVar(value=True)
        self.enable_duplicates = tk.BooleanVar(value=True)
        self.is_running = False
        self.ollama_status = "unknown"  # "available", "unavailable", "unknown"

        # UI references for dynamic show/hide
        self.api_config_frame = None
        self.ollama_status_label = None

        self._setup_styles()
        self._build_ui()

        # Auto-detect Ollama in background
        threading.Thread(target=self._check_ollama, daemon=True).start()

    def _get_mode_key(self) -> str:
        """Get the mode key from the display value."""
        display = self.selected_mode.get()
        for key, val in self.MODE_DISPLAY.items():
            if val == display:
                return key
        return MODE_SMART

    def _check_ollama(self):
        """Check Ollama availability in the background."""
        try:
            from orchestrator.workflow import detect_ollama
            result = detect_ollama()
            self.ollama_status = "available" if result["available"] else "unavailable"
            models = result.get("models", [])

            def _update():
                if self.ollama_status_label:
                    if self.ollama_status == "available":
                        model_text = ", ".join(models[:3]) if models else "no models"
                        self.ollama_status_label.configure(
                            text=f"✅ Ollama detected ({model_text})",
                            foreground=self.FG_SUCCESS,
                        )
                    else:
                        self.ollama_status_label.configure(
                            text="❌ Ollama not running — install at ollama.com",
                            foreground=self.FG_ERROR,
                        )
            self.root.after(0, _update)

        except Exception:
            self.ollama_status = "unavailable"

    def _setup_styles(self):
        """Configure ttk styles for the dark theme."""
        style = ttk.Style()
        style.theme_use("clam")

        # Frame styles
        style.configure("Dark.TFrame", background=self.BG_DARK)
        style.configure("Card.TFrame", background=self.BG_CARD)

        # Label styles
        style.configure(
            "Title.TLabel",
            background=self.BG_DARK,
            foreground=self.FG_ACCENT,
            font=("Segoe UI", 20, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=self.BG_DARK,
            foreground=self.FG_SECONDARY,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Dark.TLabel",
            background=self.BG_CARD,
            foreground=self.FG_PRIMARY,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Section.TLabel",
            background=self.BG_DARK,
            foreground=self.FG_PRIMARY,
            font=("Segoe UI", 12, "bold"),
        )
        style.configure(
            "SmallDark.TLabel",
            background=self.BG_CARD,
            foreground=self.FG_SECONDARY,
            font=("Segoe UI", 9),
        )

        # Entry style
        style.configure(
            "Dark.TEntry",
            fieldbackground=self.BG_INPUT,
            foreground=self.FG_PRIMARY,
            insertcolor=self.FG_PRIMARY,
        )

        # Checkbutton style
        style.configure(
            "Dark.TCheckbutton",
            background=self.BG_CARD,
            foreground=self.FG_PRIMARY,
            font=("Segoe UI", 10),
        )
        style.map(
            "Dark.TCheckbutton",
            background=[("active", self.BG_CARD)],
        )

        # Button styles
        style.configure(
            "Accent.TButton",
            background=self.BUTTON_BG,
            foreground=self.BUTTON_FG,
            font=("Segoe UI", 12, "bold"),
            padding=(20, 10),
        )
        style.map(
            "Accent.TButton",
            background=[("active", self.BUTTON_HOVER), ("disabled", self.BORDER_COLOR)],
        )

        style.configure(
            "Secondary.TButton",
            background=self.BG_INPUT,
            foreground=self.FG_PRIMARY,
            font=("Segoe UI", 9),
            padding=(10, 5),
        )

        # LabelFrame
        style.configure(
            "Dark.TLabelframe",
            background=self.BG_CARD,
            foreground=self.FG_PRIMARY,
        )
        style.configure(
            "Dark.TLabelframe.Label",
            background=self.BG_CARD,
            foreground=self.FG_ACCENT,
            font=("Segoe UI", 11, "bold"),
        )

    def _build_ui(self):
        """Build the main UI layout."""
        # ── Main Container ───────────────────────────────────────
        main_frame = ttk.Frame(self.root, style="Dark.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # ── Header ───────────────────────────────────────────────
        header_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(
            header_frame,
            text="🧹 Digital Life Cleanup",
            style="Title.TLabel",
        ).pack(anchor=tk.W)

        self.subtitle_label = ttk.Label(
            header_frame,
            text="Powered by Accomplish • Smart Mode — Ready to use, no setup needed!",
            style="Subtitle.TLabel",
        )
        self.subtitle_label.pack(anchor=tk.W)

        # ── Scrollable content area ──────────────────────────────
        canvas = tk.Canvas(main_frame, bg=self.BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas, style="Dark.TFrame")

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mousewheel support
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # ── Folder Selection ─────────────────────────────────────
        folder_frame = ttk.LabelFrame(
            scroll_frame, text="📁 Target Folder", style="Dark.TLabelframe"
        )
        folder_frame.pack(fill=tk.X, pady=(0, 10), padx=5, ipady=5)

        folder_inner = ttk.Frame(folder_frame, style="Card.TFrame")
        folder_inner.pack(fill=tk.X, padx=10, pady=5)

        folder_entry = tk.Entry(
            folder_inner,
            textvariable=self.folder_path,
            font=("Consolas", 10),
            bg=self.BG_INPUT,
            fg=self.FG_PRIMARY,
            insertbackground=self.FG_PRIMARY,
            relief=tk.FLAT,
            bd=5,
        )
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        browse_btn = tk.Button(
            folder_inner,
            text="Browse...",
            command=self._browse_folder,
            bg=self.BG_INPUT,
            fg=self.FG_ACCENT,
            activebackground=self.BUTTON_HOVER,
            activeforeground=self.BUTTON_FG,
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=5,
        )
        browse_btn.pack(side=tk.RIGHT)

        # ── Mode Selection ───────────────────────────────────────
        mode_frame = ttk.LabelFrame(
            scroll_frame, text="⚡ Operating Mode", style="Dark.TLabelframe"
        )
        mode_frame.pack(fill=tk.X, pady=(0, 10), padx=5, ipady=5)

        mode_inner = ttk.Frame(mode_frame, style="Card.TFrame")
        mode_inner.pack(fill=tk.X, padx=10, pady=5)

        mode_values = list(self.MODE_DISPLAY.values())
        mode_combo = ttk.Combobox(
            mode_inner,
            textvariable=self.selected_mode,
            values=mode_values,
            font=("Segoe UI", 10),
            state="readonly",
            width=45,
        )
        mode_combo.pack(side=tk.LEFT, padx=(0, 10))
        mode_combo.bind("<<ComboboxSelected>>", self._on_mode_changed)

        # Ollama status indicator
        self.ollama_status_label = ttk.Label(
            mode_inner,
            text="🔍 Checking Ollama...",
            style="SmallDark.TLabel",
        )
        self.ollama_status_label.pack(side=tk.LEFT)

        # Mode description
        self.mode_desc_label = ttk.Label(
            mode_frame,
            text="💡 Smart Mode runs everything locally with built-in rules. No API key needed!",
            style="SmallDark.TLabel",
        )
        self.mode_desc_label.pack(fill=tk.X, padx=15, pady=(0, 5))

        # ── AI Configuration (hidden by default, shown for API mode) ─
        self.api_config_frame = ttk.LabelFrame(
            scroll_frame, text="🔑 AI Configuration", style="Dark.TLabelframe"
        )
        # NOT packed initially — only shown for API/Ollama modes

        # API Key
        key_frame = ttk.Frame(self.api_config_frame, style="Card.TFrame")
        key_frame.pack(fill=tk.X, padx=10, pady=3)
        ttk.Label(key_frame, text="API Key:", style="Dark.TLabel").pack(side=tk.LEFT, padx=(0, 10))
        api_entry = tk.Entry(
            key_frame,
            textvariable=self.api_key,
            show="•",
            font=("Consolas", 10),
            bg=self.BG_INPUT,
            fg=self.FG_PRIMARY,
            insertbackground=self.FG_PRIMARY,
            relief=tk.FLAT,
            bd=5,
        )
        api_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # API Base URL
        base_frame = ttk.Frame(self.api_config_frame, style="Card.TFrame")
        base_frame.pack(fill=tk.X, padx=10, pady=3)
        ttk.Label(base_frame, text="API Base:", style="Dark.TLabel").pack(side=tk.LEFT, padx=(0, 10))
        base_entry = tk.Entry(
            base_frame,
            textvariable=self.api_base,
            font=("Consolas", 10),
            bg=self.BG_INPUT,
            fg=self.FG_PRIMARY,
            insertbackground=self.FG_PRIMARY,
            relief=tk.FLAT,
            bd=5,
        )
        base_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Model Selection
        model_frame = ttk.Frame(self.api_config_frame, style="Card.TFrame")
        model_frame.pack(fill=tk.X, padx=10, pady=3)
        ttk.Label(model_frame, text="Model:", style="Dark.TLabel").pack(side=tk.LEFT, padx=(0, 10))

        models = [
            "gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo",
            "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307",
            "gemini-1.5-flash", "gemini-1.5-pro",
        ]
        self.model_combo = ttk.Combobox(
            model_frame,
            textvariable=self.model,
            values=models,
            font=("Consolas", 10),
            state="normal",
        )
        self.model_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ── Feature Toggles ──────────────────────────────────────
        toggle_frame = ttk.LabelFrame(
            scroll_frame, text="⚙️ Features", style="Dark.TLabelframe"
        )
        toggle_frame.pack(fill=tk.X, pady=(0, 10), padx=5, ipady=5)

        toggles_inner = ttk.Frame(toggle_frame, style="Card.TFrame")
        toggles_inner.pack(fill=tk.X, padx=10, pady=5)

        ttk.Checkbutton(
            toggles_inner,
            text="🔍 Duplicate Detection — Find and report duplicate files",
            variable=self.enable_duplicates,
            style="Dark.TCheckbutton",
        ).pack(anchor=tk.W, pady=2)

        ttk.Checkbutton(
            toggles_inner,
            text="🔒 Protection — Encrypt sensitive files (GPS data, personal PDFs)",
            variable=self.enable_protection,
            style="Dark.TCheckbutton",
        ).pack(anchor=tk.W, pady=2)

        ttk.Checkbutton(
            toggles_inner,
            text="📦 Compression — Compress large files to save space",
            variable=self.enable_compression,
            style="Dark.TCheckbutton",
        ).pack(anchor=tk.W, pady=2)

        # ── Action Button ────────────────────────────────────────
        btn_frame = ttk.Frame(scroll_frame, style="Dark.TFrame")
        btn_frame.pack(fill=tk.X, pady=(5, 10), padx=5)

        self.run_button = tk.Button(
            btn_frame,
            text="✨ Clean My Digital Life ✨",
            command=self._start_cleanup,
            bg=self.BUTTON_BG,
            fg=self.BUTTON_FG,
            activebackground=self.BUTTON_HOVER,
            activeforeground=self.BUTTON_FG,
            font=("Segoe UI", 14, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=30,
            pady=12,
        )
        self.run_button.pack(fill=tk.X)

        # Secondary buttons row
        sec_frame = ttk.Frame(scroll_frame, style="Dark.TFrame")
        sec_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

        schedule_btn = tk.Button(
            sec_frame,
            text="📅 Generate Schedule",
            command=self._generate_schedule,
            bg=self.BG_INPUT,
            fg=self.FG_ACCENT,
            activebackground=self.BUTTON_HOVER,
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=6,
        )
        schedule_btn.pack(side=tk.LEFT, padx=(0, 10))

        report_btn = tk.Button(
            sec_frame,
            text="📂 Open Reports Folder",
            command=self._open_reports_folder,
            bg=self.BG_INPUT,
            fg=self.FG_ACCENT,
            activebackground=self.BUTTON_HOVER,
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=6,
        )
        report_btn.pack(side=tk.LEFT)

        # ── Log Output ───────────────────────────────────────────
        log_frame = ttk.LabelFrame(
            scroll_frame, text="📜 Activity Log", style="Dark.TLabelframe"
        )
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5), padx=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=12,
            font=("Consolas", 9),
            bg="#0d1117",
            fg=self.FG_PRIMARY,
            insertbackground=self.FG_PRIMARY,
            relief=tk.FLAT,
            bd=10,
            wrap=tk.WORD,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configure log text tags for coloring
        self.log_text.tag_configure("info", foreground=self.FG_PRIMARY)
        self.log_text.tag_configure("success", foreground=self.FG_SUCCESS)
        self.log_text.tag_configure("warning", foreground=self.FG_WARNING)
        self.log_text.tag_configure("error", foreground=self.FG_ERROR)
        self.log_text.tag_configure("accent", foreground=self.FG_ACCENT)

        # Status bar
        self.status_var = tk.StringVar(
            value="Ready — Smart Mode active. Select a folder and click 'Clean My Digital Life'!"
        )
        status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            bg=self.BG_CARD,
            fg=self.FG_SECONDARY,
            font=("Segoe UI", 9),
            anchor=tk.W,
            padx=15,
            pady=5,
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self._log_message("🚀 Digital Life Cleanup & Protection System initialized", "accent")
        self._log_message("🧠 Smart Mode active — no API key needed! Just pick a folder and go.", "success")
        self._log_message("ℹ️  Switch to Ollama or API mode for AI-powered orchestration.", "info")

    # ── Mode Switching ───────────────────────────────────────────

    def _on_mode_changed(self, event=None):
        """Handle mode selection change — show/hide relevant config fields."""
        mode = self._get_mode_key()

        mode_descriptions = {
            MODE_SMART: "💡 Smart Mode runs everything with built-in rules. No AI key needed!",
            MODE_OLLAMA: "💡 Ollama runs AI locally on your machine. Free! Install at ollama.com",
            MODE_API: "💡 API mode uses external AI services. Requires an API key.",
        }

        subtitle_texts = {
            MODE_SMART: "Powered by Accomplish • Smart Mode — Ready to use, no setup needed!",
            MODE_OLLAMA: "Powered by Accomplish • Ollama Mode — Local AI, free & private",
            MODE_API: "Powered by Accomplish • API Mode — External AI provider",
        }

        # Update description
        self.mode_desc_label.configure(text=mode_descriptions.get(mode, ""))
        self.subtitle_label.configure(text=subtitle_texts.get(mode, ""))

        # Show/hide API config
        if mode == MODE_API:
            self.api_config_frame.pack(
                fill=tk.X, pady=(0, 10), padx=5, ipady=5,
                after=self.api_config_frame.master.winfo_children()[2]  # After mode frame
            )
            self.api_base.set(DEFAULT_API_BASE)
        elif mode == MODE_OLLAMA:
            self.api_config_frame.pack_forget()
            self.api_base.set(OLLAMA_API_BASE)
            self.model.set(OLLAMA_DEFAULT_MODEL)
        else:
            self.api_config_frame.pack_forget()

        # Update status bar
        status_texts = {
            MODE_SMART: "Ready — Smart Mode. Select a folder and click 'Clean My Digital Life'!",
            MODE_OLLAMA: f"Ready — Ollama Mode. Status: {'✅ Connected' if self.ollama_status == 'available' else '⚠️ Not detected'}",
            MODE_API: "Ready — API Mode. Enter your API key to begin.",
        }
        self.status_var.set(status_texts.get(mode, "Ready"))

    # ── Actions ──────────────────────────────────────────────────

    def _browse_folder(self):
        """Open folder selection dialog."""
        folder = filedialog.askdirectory(title="Select folder to clean up")
        if folder:
            self.folder_path.set(folder)
            self._log_message(f"📁 Selected folder: {folder}", "info")

    def _log_message(self, message: str, tag: str = "info"):
        """Append a message to the log panel (thread-safe)."""
        def _append():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
            self.log_text.see(tk.END)
        self.root.after(0, _append)

    def _start_cleanup(self):
        """Start the cleanup workflow in a background thread."""
        if self.is_running:
            messagebox.showwarning("In Progress", "A cleanup is already running!")
            return

        folder = self.folder_path.get().strip()
        mode = self._get_mode_key()

        if not folder:
            messagebox.showerror("Error", "Please select a target folder.")
            return

        if not os.path.isdir(folder):
            messagebox.showerror("Error", f"Folder does not exist:\n{folder}")
            return

        # Only require API key for API mode
        if mode == MODE_API:
            api_key = self.api_key.get().strip()
            if not api_key:
                messagebox.showerror(
                    "Error",
                    "API key required for API Mode.\n\n"
                    "Switch to Smart Mode or Ollama Mode if you don't have an API key."
                )
                return

        self.is_running = True
        self.run_button.configure(state=tk.DISABLED, text="⏳ Running...")
        self.status_var.set("Running cleanup workflow...")
        self._log_message("=" * 60, "accent")
        self._log_message("🚀 Starting Digital Life Cleanup workflow...", "accent")

        # Run in background thread to keep UI responsive
        thread = threading.Thread(target=self._run_cleanup_thread, daemon=True)
        thread.start()

    def _run_cleanup_thread(self):
        """Background thread for running the cleanup workflow."""
        try:
            from orchestrator.workflow import CleanupWorkflow

            mode = self._get_mode_key()
            api_key = self.api_key.get().strip() if mode == MODE_API else ""

            workflow = CleanupWorkflow(
                mode=mode,
                api_key=api_key,
                model=self.model.get(),
                api_base=self.api_base.get().strip(),
            )
            workflow.set_log_callback(lambda msg: self._log_message(msg, "info"))

            result = workflow.run(
                folder_path=self.folder_path.get().strip(),
                enable_protection=self.enable_protection.get(),
                enable_compression=self.enable_compression.get(),
                enable_duplicates=self.enable_duplicates.get(),
            )

            # Show result
            status = result.get("status", "unknown")
            iterations = result.get("iterations", 0)
            tool_calls = result.get("tool_calls_made", 0)

            if status == "completed":
                self._log_message("=" * 60, "success")
                self._log_message(
                    f"✅ Cleanup completed! "
                    f"({iterations} iterations, {tool_calls} tool calls)",
                    "success",
                )
                summary = result.get("final_summary", "")
                if summary:
                    self._log_message(f"\n📋 Summary:\n{summary[:800]}", "info")

                self.root.after(0, lambda: self.status_var.set(
                    f"✅ Completed — {tool_calls} tools executed in {iterations} iterations"
                ))
            else:
                error = result.get("error", "Unknown error")
                self._log_message(f"❌ Cleanup failed: {error}", "error")
                self.root.after(0, lambda: self.status_var.set(f"❌ Error: {error}"))

        except Exception as e:
            self._log_message(f"❌ Error: {str(e)}", "error")
            self.root.after(0, lambda: self.status_var.set(f"❌ Error: {str(e)}"))

        finally:
            self.is_running = False
            self.root.after(0, lambda: self.run_button.configure(
                state=tk.NORMAL, text="✨ Clean My Digital Life ✨"
            ))

    def _generate_schedule(self):
        """Generate scheduler configuration."""
        folder = self.folder_path.get().strip()
        if not folder:
            messagebox.showerror("Error", "Please select a target folder first.")
            return

        try:
            from scheduler.scheduler import SchedulerGenerator

            gen = SchedulerGenerator()

            if os.name == "nt":
                xml_path = gen.save_windows_task_xml(folder, "weekly")
                self._log_message(f"📅 Windows Task Scheduler XML saved: {xml_path}", "success")
                instructions = gen.generate_install_instructions(folder, "weekly")
            else:
                instructions = gen.generate_cron_install_instructions(folder, "weekly")

            self._log_message(f"\n{instructions}", "info")
            messagebox.showinfo(
                "Schedule Generated",
                f"Schedule configuration generated!\n\nCheck the log for installation instructions."
            )
        except Exception as e:
            self._log_message(f"❌ Schedule generation failed: {e}", "error")
            messagebox.showerror("Error", f"Failed to generate schedule:\n{e}")

    def _open_reports_folder(self):
        """Open the reports output folder in the file explorer."""
        from config import DEFAULT_REPORT_DIR
        DEFAULT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_dir = str(DEFAULT_REPORT_DIR)

        if os.name == "nt":
            os.startfile(report_dir)
        elif sys.platform == "darwin":
            os.system(f'open "{report_dir}"')
        else:
            os.system(f'xdg-open "{report_dir}"')

        self._log_message(f"📂 Opened reports folder: {report_dir}", "info")


def launch_gui():
    """Launch the Tkinter GUI application."""
    root = tk.Tk()

    # Set icon (if available)
    try:
        root.iconbitmap(default="")
    except Exception:
        pass

    app = DigitalLifeApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
