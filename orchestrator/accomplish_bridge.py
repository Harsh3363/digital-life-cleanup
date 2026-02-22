"""
Accomplish Bridge — Connects to Accomplish AI as the Decision-Making Orchestrator

This module sends the "Clean My Digital Life" command to an AI model
(via OpenAI-compatible API) and processes tool_call responses,
dispatching them to our Python tool modules.

Accomplish / the AI model is the ORCHESTRATOR — it decides:
  - What to classify
  - Which tool to call
  - What order to process files
  - When to stop

Python tools are DETERMINISTIC — they execute and return results.
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from openai import OpenAI

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DEFAULT_MODEL, DEFAULT_API_BASE, MAX_ORCHESTRATOR_ITERATIONS
from orchestrator.tool_registry import get_tool_definitions, execute_tool

logger = logging.getLogger(__name__)


# ── System Prompt ────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the Accomplish AI Orchestrator for the "Digital Life Cleanup & Protection System".

Your role is to intelligently manage a user's messy filesystem by calling the available tools.

## Your Responsibilities:
1. **Analyze** the target folder by scanning for duplicates, extracting metadata, and finding large files
2. **Classify** files based on scan results (you decide what's important, what's redundant, what needs protection)
3. **Protect** sensitive files by encrypting them (PDFs with personal info, images with GPS data)
4. **Compress** large files to save space
5. **Report** — always generate a final report summarizing all actions

## Your Workflow:
1. First call `scan_duplicates` to find duplicate files
2. Call `extract_metadata` to understand file contents and identify sensitive files
3. Call `find_large_files` to identify files that could be compressed
4. Based on the results, decide:
   - Which files with GPS/personal data should be encrypted (call `encrypt_files`)
   - Which large files should be compressed (call `compress_file` or `compress_large_files`)
5. Finally, call `generate_report` with all gathered data

## Rules:
- Always start with scanning/analysis before taking actions
- Be conservative: only encrypt files that actually contain sensitive metadata
- Only compress files above the threshold
- ALWAYS generate a final report at the end
- Explain your reasoning in your responses
- If a tool returns an error, note it and continue with other tools

## Available toggles from user:
- Protection (encryption) may be disabled
- Compression may be disabled
- Duplicate detection may be disabled
Respect these toggles — skip disabled features.
"""


class AccomplishBridge:
    """
    Bridge between Python tools and Accomplish AI orchestrator.

    The AI model acts as the brain — this bridge facilitates communication
    between AI decisions (tool_calls) and Python tool execution.
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        api_base: str = DEFAULT_API_BASE,
        max_iterations: int = MAX_ORCHESTRATOR_ITERATIONS,
    ):
        self.client = OpenAI(api_key=api_key, base_url=api_base)
        self.model = model
        self.max_iterations = max_iterations
        self.conversation_history: List[Dict] = []
        self.tool_results: List[Dict] = []
        self._log_callback: Optional[Callable] = None

    def set_log_callback(self, callback: Callable[[str], None]):
        """Set a callback for real-time log messages (used by UI)."""
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
        Run the full "Clean My Digital Life" workflow.

        Accomplish AI acts as orchestrator:
        1. Receives the command and folder path
        2. Decides which tools to call and in what order
        3. Python tools execute and return results
        4. AI processes results and decides next action
        5. Loop continues until AI is satisfied or max iterations reached

        Args:
            folder_path: Absolute path to the folder to clean up.
            enable_protection: Allow file encryption.
            enable_compression: Allow file compression.
            enable_duplicates: Allow duplicate detection.

        Returns:
            {
                "status": "completed" | "error",
                "iterations": int,
                "tool_calls_made": int,
                "conversation": [...],
                "tool_results": [...],
                "final_summary": str
            }
        """
        self._log(f"🚀 Starting Digital Life Cleanup for: {folder_path}")
        self._log(f"   Protection: {'✅' if enable_protection else '❌'}")
        self._log(f"   Compression: {'✅' if enable_compression else '❌'}")
        self._log(f"   Duplicates: {'✅' if enable_duplicates else '❌'}")

        # Build the user command with toggle info
        toggles = []
        if not enable_duplicates:
            toggles.append("Duplicate detection is DISABLED — skip scan_duplicates")
        if not enable_protection:
            toggles.append("Protection/encryption is DISABLED — skip encrypt_files")
        if not enable_compression:
            toggles.append("Compression is DISABLED — skip compress_file and compress_large_files")

        toggle_text = "\n".join(toggles) if toggles else "All features are enabled."

        user_message = (
            f"Clean My Digital Life!\n\n"
            f"Target folder: {folder_path}\n\n"
            f"Feature toggles:\n{toggle_text}\n\n"
            f"Please analyze this folder, take appropriate cleanup actions, "
            f"and generate a comprehensive report."
        )

        # Initialize conversation
        self.conversation_history = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        self.tool_results = []
        tool_calls_made = 0

        # Orchestration loop — AI decides, Python executes
        for iteration in range(1, self.max_iterations + 1):
            self._log(f"\n🔄 Orchestrator iteration {iteration}/{self.max_iterations}")

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.conversation_history,
                    tools=get_tool_definitions(),
                    tool_choice="auto",
                )
            except Exception as e:
                self._log(f"❌ API call failed: {e}")
                return {
                    "status": "error",
                    "error": str(e),
                    "iterations": iteration,
                    "tool_calls_made": tool_calls_made,
                    "tool_results": self.tool_results,
                }

            choice = response.choices[0]
            message = choice.message

            # Add assistant message to history
            self.conversation_history.append(message.model_dump())

            # Check if the AI wants to call tools
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    self._log(f"🔧 AI calls tool: {tool_name}")
                    self._log(f"   Args: {json.dumps(arguments, default=str)[:200]}")

                    # Execute the tool
                    try:
                        result = execute_tool(tool_name, arguments)
                        result_str = json.dumps(result, default=str)
                        self._log(f"✅ Tool {tool_name} completed successfully")
                    except Exception as e:
                        result_str = json.dumps({"error": str(e)})
                        self._log(f"❌ Tool {tool_name} failed: {e}")

                    # Record the result
                    self.tool_results.append({
                        "iteration": iteration,
                        "tool": tool_name,
                        "arguments": arguments,
                        "result_preview": result_str[:500],
                    })

                    # Feed result back to AI
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_str,
                    })

                    tool_calls_made += 1

            # If no tool calls, AI is done — check for final message
            elif message.content:
                self._log(f"\n📋 Orchestrator final summary:\n{message.content[:500]}")
                return {
                    "status": "completed",
                    "iterations": iteration,
                    "tool_calls_made": tool_calls_made,
                    "tool_results": self.tool_results,
                    "final_summary": message.content,
                }

            # Check for finish reason
            if choice.finish_reason == "stop" and not message.tool_calls:
                self._log("✅ Orchestrator completed")
                return {
                    "status": "completed",
                    "iterations": iteration,
                    "tool_calls_made": tool_calls_made,
                    "tool_results": self.tool_results,
                    "final_summary": message.content or "Cleanup completed.",
                }

        # Max iterations reached
        self._log(f"⚠️ Max iterations ({self.max_iterations}) reached")
        return {
            "status": "completed",
            "iterations": self.max_iterations,
            "tool_calls_made": tool_calls_made,
            "tool_results": self.tool_results,
            "final_summary": "Cleanup completed (max iterations reached).",
        }
