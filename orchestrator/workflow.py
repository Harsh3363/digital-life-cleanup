"""
Workflow — High-Level Workflow Definition for Digital Life Cleanup

Defines the "Clean My Digital Life" workflow that routes to the correct
orchestrator based on the selected mode:
  - smart:  Built-in rule-based orchestrator (no AI needed)
  - ollama: Local Ollama LLM (free, no API key)
  - api:    External API (OpenAI, Anthropic, etc.)
"""

import logging
import urllib.request
import json
from typing import Any, Callable, Dict, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    DEFAULT_MODEL, DEFAULT_API_BASE, DEFAULT_MODE,
    MODE_SMART, MODE_OLLAMA, MODE_API,
    OLLAMA_API_BASE, OLLAMA_DEFAULT_MODEL, OLLAMA_FALLBACK_MODELS,
)

logger = logging.getLogger(__name__)


def detect_ollama() -> Dict[str, Any]:
    """
    Check if Ollama is running and which models are available.

    Returns:
        {
            "available": bool,
            "models": [str, ...],
            "recommended_model": str or None,
            "error": str or None,
        }
    """
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/tags",
            method="GET",
        )
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())

        models = [m["name"].split(":")[0] for m in data.get("models", [])]
        # Find the best available model
        recommended = None
        for preferred in OLLAMA_FALLBACK_MODELS:
            if preferred in models:
                recommended = preferred
                break
        if not recommended and models:
            recommended = models[0]

        return {
            "available": True,
            "models": models,
            "recommended_model": recommended,
            "error": None,
        }
    except Exception as e:
        return {
            "available": False,
            "models": [],
            "recommended_model": None,
            "error": str(e),
        }


def pull_ollama_model(model: str, log_callback: Optional[Callable] = None) -> bool:
    """
    Pull a model in Ollama if it's not already available.

    Returns True if the model is ready to use.
    """
    try:
        if log_callback:
            log_callback(f"🦙 Pulling Ollama model '{model}'... (this may take a few minutes)")

        data = json.dumps({"name": model}).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/pull",
            data=data,
            method="POST",
        )
        req.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(req, timeout=600) as resp:
            # Stream the response to show progress
            for line in resp:
                try:
                    status = json.loads(line.decode())
                    if status.get("status") == "success":
                        if log_callback:
                            log_callback(f"   ✅ Model '{model}' ready!")
                        return True
                except json.JSONDecodeError:
                    continue

        return True
    except Exception as e:
        if log_callback:
            log_callback(f"   ⚠️ Failed to pull model: {e}")
        return False


class CleanupWorkflow:
    """
    High-level workflow controller for the Digital Life Cleanup system.

    Routes to the correct orchestrator based on mode:
    - smart: SmartOrchestrator (no AI)
    - ollama: AccomplishBridge with Ollama backend
    - api: AccomplishBridge with external API
    """

    def __init__(
        self,
        mode: str = DEFAULT_MODE,
        api_key: str = "",
        model: str = DEFAULT_MODEL,
        api_base: str = DEFAULT_API_BASE,
    ):
        self.mode = mode
        self.api_key = api_key
        self.model = model
        self.api_base = api_base
        self._log_callback: Optional[Callable] = None

    def set_log_callback(self, callback: Callable[[str], None]):
        """Set a callback for real-time log messages."""
        self._log_callback = callback

    def _log(self, message: str):
        logger.info(message)
        if self._log_callback:
            self._log_callback(message)

    def run(
        self,
        folder_path: str,
        enable_protection: bool = True,
        enable_compression: bool = True,
        enable_duplicates: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute the cleanup workflow using the selected mode.
        """
        logger.info(f"Starting CleanupWorkflow (mode={self.mode}) for: {folder_path}")

        if self.mode == MODE_SMART:
            return self._run_smart(folder_path, enable_protection, enable_compression, enable_duplicates)
        elif self.mode == MODE_OLLAMA:
            return self._run_ollama(folder_path, enable_protection, enable_compression, enable_duplicates)
        elif self.mode == MODE_API:
            return self._run_api(folder_path, enable_protection, enable_compression, enable_duplicates)
        else:
            return {"status": "error", "error": f"Unknown mode: {self.mode}"}

    def _run_smart(self, folder_path, enable_protection, enable_compression, enable_duplicates):
        """Run with the built-in smart orchestrator (no AI)."""
        from orchestrator.smart_orchestrator import SmartOrchestrator

        orchestrator = SmartOrchestrator()
        if self._log_callback:
            orchestrator.set_log_callback(self._log_callback)

        return orchestrator.run_cleanup(
            folder_path=folder_path,
            enable_protection=enable_protection,
            enable_compression=enable_compression,
            enable_duplicates=enable_duplicates,
        )

    def _run_ollama(self, folder_path, enable_protection, enable_compression, enable_duplicates):
        """Run with Ollama local LLM."""
        self._log("🦙 Connecting to Ollama (local AI)...")

        # Detect Ollama
        ollama_info = detect_ollama()
        if not ollama_info["available"]:
            self._log("⚠️ Ollama not detected! Falling back to Smart Mode.")
            self._log("   Install Ollama: https://ollama.com")
            return self._run_smart(folder_path, enable_protection, enable_compression, enable_duplicates)

        # Determine model
        model = self.model if self.model != DEFAULT_MODEL else (
            ollama_info["recommended_model"] or OLLAMA_DEFAULT_MODEL
        )

        # Check if model exists, pull if needed
        if model.split(":")[0] not in ollama_info["models"]:
            self._log(f"   Model '{model}' not found locally. Pulling...")
            success = pull_ollama_model(model, self._log_callback)
            if not success:
                self._log("   ⚠️ Model pull failed. Falling back to Smart Mode.")
                return self._run_smart(folder_path, enable_protection, enable_compression, enable_duplicates)

        self._log(f"   ✅ Using Ollama model: {model}")
        self._log(f"   📋 Available models: {', '.join(ollama_info['models'][:5])}")

        # Use AccomplishBridge with Ollama settings
        try:
            from orchestrator.accomplish_bridge import AccomplishBridge

            bridge = AccomplishBridge(
                api_key="ollama",  # Ollama doesn't need a real key
                model=model,
                api_base=OLLAMA_API_BASE,
            )
            if self._log_callback:
                bridge.set_log_callback(self._log_callback)

            return bridge.run_cleanup(
                folder_path=folder_path,
                enable_protection=enable_protection,
                enable_compression=enable_compression,
                enable_duplicates=enable_duplicates,
            )
        except Exception as e:
            self._log(f"⚠️ Ollama error: {e}. Falling back to Smart Mode.")
            return self._run_smart(folder_path, enable_protection, enable_compression, enable_duplicates)

    def _run_api(self, folder_path, enable_protection, enable_compression, enable_duplicates):
        """Run with external API (OpenAI, Anthropic, etc.)."""
        if not self.api_key:
            return {"status": "error", "error": "API key required for API mode."}

        from orchestrator.accomplish_bridge import AccomplishBridge

        bridge = AccomplishBridge(
            api_key=self.api_key,
            model=self.model,
            api_base=self.api_base,
        )
        if self._log_callback:
            bridge.set_log_callback(self._log_callback)

        return bridge.run_cleanup(
            folder_path=folder_path,
            enable_protection=enable_protection,
            enable_compression=enable_compression,
            enable_duplicates=enable_duplicates,
        )


def run_cleanup_workflow(
    folder_path: str,
    mode: str = DEFAULT_MODE,
    api_key: str = "",
    model: str = DEFAULT_MODEL,
    api_base: str = DEFAULT_API_BASE,
    enable_protection: bool = True,
    enable_compression: bool = True,
    enable_duplicates: bool = True,
    log_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Convenience function to run the full cleanup workflow.

    Args:
        folder_path: Target folder path.
        mode: Operating mode ("smart", "ollama", "api").
        api_key: AI API key (only needed for "api" mode).
        model: AI model to use.
        api_base: API base URL.
        enable_protection: Toggle encryption.
        enable_compression: Toggle compression.
        enable_duplicates: Toggle duplicate detection.
        log_callback: Optional callback for log messages.

    Returns:
        Workflow result dictionary.
    """
    workflow = CleanupWorkflow(
        mode=mode,
        api_key=api_key,
        model=model,
        api_base=api_base,
    )

    if log_callback:
        workflow.set_log_callback(log_callback)

    return workflow.run(
        folder_path=folder_path,
        enable_protection=enable_protection,
        enable_compression=enable_compression,
        enable_duplicates=enable_duplicates,
    )
