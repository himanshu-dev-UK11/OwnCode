"""
Consolidated Module: agent.providers.local_providers

Combines: ai.providers.llama_cpp_loader, ai.providers.llama_cpp_provider, ai.providers.ollama_provider, ai.providers.qwen_provider
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['ai.providers.llama_cpp_loader', 'ai.providers.llama_cpp_provider', 'ai.providers.ollama_provider', 'ai.providers.qwen_provider']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ai.providers.llama_cpp_loader (ai/providers/llama_cpp_loader.py)
# ============================================================================
"""Discovery and owned-process lifecycle for local llama.cpp GGUF models."""

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import threading
import time
from typing import Dict, List, Optional
import urllib.error
import urllib.request
from urllib.parse import urlparse

from core.logger import setup_logger


logger = setup_logger(__name__)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise LlamaCppLoaderError("llama-server endpoint redirects are not allowed")


class LlamaCppLoaderError(RuntimeError):
    """Raised when a local llama-server cannot be prepared safely."""


class LlamaCppLoader:
    """Find GGUF files and manage at most one IDE-owned llama-server process."""

    def __init__(self, options: Optional[dict] = None):
        self.options = {}
        self.model_directory = Path(r"D:\llama_models")
        self.host = "127.0.0.1"
        self.preferred_port = 8080
        self.startup_timeout = 180.0
        self._process: Optional[subprocess.Popen] = None
        self._active_model_id: Optional[str] = None
        self._api_model_id: Optional[str] = None
        self._port: Optional[int] = None
        self._owned = False
        self._lock = threading.RLock()
        self.update_options(options or {})

    def update_options(self, options: dict) -> None:
        """Apply persisted settings without discarding a running owned process."""
        self.options.update(options)
        self.model_directory = Path(
            self.options.get("model_directory", r"D:\llama_models")
        ).expanduser()
        self.preferred_port = int(self.options.get("port", 8080) or 8080)
        self.startup_timeout = float(
            self.options.get("startup_timeout_seconds", 180)
        )

    @property
    def endpoint(self) -> Optional[str]:
        return f"http://{self.host}:{self._port}/v1" if self._port else None

    @property
    def active_model_id(self) -> Optional[str]:
        return self._active_model_id

    @property
    def api_model_id(self) -> Optional[str]:
        return self._api_model_id

    @property
    def owns_process(self) -> bool:
        return self._owned and self._process is not None


    def discover_draft_model(self, primary_model_name: str) -> Optional[str]:
        """Auto-discover a small compatible GGUF draft model (0.5B-1.5B) for speculative decoding."""
        models = self.discover_models()
        if len(models) < 2:
            return None
        primary_lower = (primary_model_name or "").lower()
        primary_family = None
        for fam in ("qwen", "llama", "deepseek", "codellama", "starcoder", "gemma", "phi"):
            if fam in primary_lower:
                primary_family = fam
                break
        candidates = []
        for m in models:
            m_name = m.get("name", "") if isinstance(m, dict) else getattr(m, "name", "")
            m_id = m.get("id", "") if isinstance(m, dict) else getattr(m, "id", "")
            m_path = m.get("path", "") if isinstance(m, dict) else getattr(m, "path", "")
            m_size_bytes = m.get("size", 0) if isinstance(m, dict) else int(getattr(m, "size_gb", 0) * (1024**3))
            m_size_gb = float(m_size_bytes) / (1024**3) if m_size_bytes else 0.0
            if m_name == primary_model_name or m_id == primary_model_name:
                continue
            lname = str(m_name).lower()
            is_small = any(tag in lname for tag in ("0.5b", "1b", "1.3b", "1.5b", "draft", "tiny", "mini")) or (0 < m_size_gb <= 1.6)
            if is_small:
                same_fam = 1 if (primary_family and primary_family in lname) else 0
                candidates.append((same_fam, -m_size_gb, str(m_path)))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        return candidates[0][2]

    def discover_models(self) -> List[Dict[str, object]]:
        """Return deterministic metadata for GGUF files directly in the model directory."""
        if not self.model_directory.is_dir():
            return []
        models = []
        for path in sorted(self.model_directory.iterdir(), key=lambda p: p.name.lower()):
            if not path.is_file() or path.suffix.lower() != ".gguf":
                continue
            resolved = path.resolve()
            try:
                resolved.relative_to(self.model_directory.resolve())
            except ValueError:
                continue
            stem_low = path.stem.lower()
            is_tool_capable = bool(
                self.options.get("jinja", False)
                or any(k in stem_low for k in ("coder", "instruct", "qwen", "llama-3", "llama3", "mistral", "function"))
            )
            models.append({
                "id": path.stem,
                "name": path.stem,
                "path": str(resolved),
                "size": path.stat().st_size,
                "type": "local",
                "context_window": int(self.options.get("context_size", 8192)),
                "max_output_tokens": int(self.options.get("max_output_tokens", 4096)),
                "supports_streaming": True,
                "supports_tool_calling": is_tool_capable,
                "supports_vision": False,
                "supports_function_calling": is_tool_capable,
                "capabilities": ["coding"] if "coder" in stem_low else [],
            })
        return models

    def model_path(self, model_id: str) -> Path:
        for model in self.discover_models():
            if model["id"] == model_id:
                return Path(str(model["path"]))
        raise LlamaCppLoaderError(f"GGUF model not found in {self.model_directory}: {model_id}")

    def resolve_executable(self) -> str:
        configured = str(self.options.get("server_executable", "")).strip()
        candidate = configured or shutil.which("llama-server") or shutil.which("llama-server.exe")
        if not candidate or not Path(candidate).is_file():
            raise LlamaCppLoaderError(
                "llama-server executable not found. Configure its path in llama.cpp settings."
            )
        return str(Path(candidate).resolve())

    def ensure_server(self, model_id: str) -> str:
        """Reuse a matching server or start an owned server on an available port."""
        with self._lock:
            if self._process and self._process.poll() is not None:
                self._clear_process()
            if self._active_model_id == model_id and self.endpoint and self._probe(self.endpoint):
                return self.endpoint

            configured_endpoint = str(self.options.get("endpoint", "")).rstrip("/")
            if configured_endpoint.endswith("/v1") and self._probe(configured_endpoint, model_id):
                self._set_external(configured_endpoint, model_id)
                return configured_endpoint

            if self.owns_process:
                self.stop()

            model_path = self.model_path(model_id)
            executable = self.resolve_executable()
            port = self._available_port(self.preferred_port)
            command = [
                executable, "--model", str(model_path), "--host", self.host,
                "--port", str(port),
            ]
            context_size = int(self.options.get("context_size", 0) or 0)
            if context_size:
                command.extend(["--ctx-size", str(context_size)])
            threads = int(self.options.get("threads", 0) or 0)
            if threads:
                command.extend(["--threads", str(threads)])
                threads_batch = int(self.options.get("threads_batch", threads) or threads)
                command.extend(["--threads-batch", str(threads_batch)])
            gpu_layers = self.options.get("gpu_layers")
            if gpu_layers not in (None, ""):
                # "auto" means full offload for this local server. Omitting
                # the flag leaves llama.cpp on its CPU default.
                layers = -1 if str(gpu_layers).lower() == "auto" else int(gpu_layers)
                command.extend(["--n-gpu-layers", str(layers)])
            device = str(self.options.get("device", "")).strip()
            if device:
                command.extend(["--device", device])
            fit = str(self.options.get("fit", "on")).lower()
            if fit in ("on", "off"):
                command.extend(["--fit", fit])
            fit_target = int(self.options.get("fit_target_mib", 0) or 0)
            if fit_target:
                command.extend(["--fit-target", str(fit_target)])
            flash_attention = str(self.options.get("flash_attention", "auto")).lower()
            if flash_attention in ("on", "off", "auto"):
                command.extend(["--flash-attn", flash_attention])
            batch_size = int(self.options.get("batch_size", 0) or 0)
            if batch_size:
                command.extend(["--batch-size", str(batch_size)])
            ubatch_size = int(self.options.get("ubatch_size", 0) or 0)
            if ubatch_size:
                command.extend(["--ubatch-size", str(ubatch_size)])
            if self.options.get("jinja"):
                command.append("--jinja")
            cache_reuse = int(self.options.get("cache_reuse", 0) or 0)
            if cache_reuse > 0:
                command.extend(["--cache-reuse", str(cache_reuse)])
            slot_save_path = str(self.options.get("slot_save_path", "")).strip()
            if slot_save_path:
                try:
                    slot_dir = Path(slot_save_path)
                    slot_dir.mkdir(parents=True, exist_ok=True)
                    command.extend(["--slot-save-path", str(slot_dir.resolve())])
                except OSError:
                    pass
            draft_model_path = str(self.options.get("draft_model_path", "")).strip()
            if draft_model_path and Path(draft_model_path).is_file():
                command.extend(["--model-draft", str(Path(draft_model_path).resolve())])
                draft_max = int(self.options.get("draft_max", 8) or 8)
                command.extend(["--draft-max", str(draft_max)])
                draft_p_min = float(self.options.get("draft_p_min", 0.75) or 0.75)
                command.extend(["--draft-p-min", str(draft_p_min)])

            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            startupinfo = None
            if os.name == "nt":
                # CREATE_NO_WINDOW is not honored consistently by every
                # Windows llama-server build. Explicitly hide the child
                # startup window as well, so model switches never flash a
                # terminal.
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            logger.info("Starting llama-server for model '%s' on 127.0.0.1:%s", model_id, port)
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
                startupinfo=startupinfo,
                shell=False,
            )
            self._owned = True
            self._port = port
            self._active_model_id = model_id
            endpoint = self.endpoint
            deadline = time.monotonic() + self.startup_timeout
            while time.monotonic() < deadline:
                if self._process.poll() is not None:
                    code = self._process.returncode
                    self._clear_process()
                    raise LlamaCppLoaderError(f"llama-server exited during startup (code {code})")
                if endpoint and self._probe(endpoint):
                    self._api_model_id = self._first_api_model(endpoint) or model_id
                    return endpoint
                time.sleep(0.25)
            self.stop()
            raise LlamaCppLoaderError(
                f"llama-server did not become ready within {self.startup_timeout:g} seconds"
            )

    def stop(self) -> None:
        """Stop only a process created by this loader."""
        with self._lock:
            process = self._process
            if process is not None and self._owned and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            self._clear_process()

    def _clear_process(self) -> None:
        self._process = None
        self._owned = False
        self._active_model_id = None
        self._api_model_id = None
        self._port = None

    def _set_external(self, endpoint: str, model_id: str) -> None:
        parsed = self._validate_endpoint(endpoint)
        self._process = None
        self._owned = False
        self._port = parsed.port
        self._active_model_id = model_id
        self._api_model_id = self._first_api_model(endpoint) or model_id

    def _probe(self, endpoint: str, expected_model: Optional[str] = None) -> bool:
        try:
            models = self._api_models(endpoint)
            if expected_model is None:
                return bool(models)
            expected = expected_model.lower()
            return any(expected in model.lower() or model.lower() in expected for model in models)
        except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError):
            return False

    def _first_api_model(self, endpoint: str) -> Optional[str]:
        models = self._api_models(endpoint)
        return models[0] if models else None

    def _api_models(self, endpoint: str) -> List[str]:
        self._validate_endpoint(endpoint)
        request = urllib.request.Request(f"{endpoint.rstrip('/')}/models")
        request.add_header("User-Agent", "OwnCode/0.4")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        with opener.open(request, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return [str(item.get("id")) for item in payload.get("data", []) if item.get("id")]

    def _validate_endpoint(self, endpoint: str):
        parsed = urlparse(endpoint)
        if (parsed.scheme != "http" or parsed.hostname != self.host or not parsed.port
                or parsed.path.rstrip("/") != "/v1" or parsed.username or parsed.password):
            raise LlamaCppLoaderError(
                "llama.cpp endpoint must be http://127.0.0.1:<port>/v1"
            )
        return parsed

    def _available_port(self, preferred: int) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((self.host, preferred))
                return preferred
            except OSError:
                pass
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.host, 0))
            return int(sock.getsockname()[1])


# ============================================================================
# SECTION: ai.providers.llama_cpp_provider (ai/providers/llama_cpp_provider.py)
# ============================================================================
"""First-class provider for an automatically managed local llama-server."""

import json
import threading
from typing import Any, Callable, Dict, List, Optional
import urllib.error
import urllib.request

from ai.providers.base_provider import BaseProvider, ProviderConfig, ProviderStatus
from ai.providers.llama_cpp_loader import LlamaCppLoader
from ai.providers.llama_cpp_loader import _NoRedirect


class LlamaCppCancelledError(RuntimeError):
    pass


class LlamaCppProvider(BaseProvider):
    """Serve GGUF files through llama-server's local OpenAI-compatible API."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.loader = LlamaCppLoader({**config.options, "endpoint": config.endpoint})
        self._active_endpoint: Optional[str] = None
        self._cancel = threading.Event()
        self._response = None
        self._response_lock = threading.Lock()
        self._set_models(self.loader.discover_models())

    def connect(self, lazy_startup: bool = False) -> bool:
        try:
            self._update_status(ProviderStatus.CONNECTING)
            models = self.refresh_models()
            if not models:
                self._update_status(ProviderStatus.ERROR, "No GGUF models found")
                return False
            if self.loader.active_model_id and self.loader.endpoint:
                self._active_endpoint = self.loader.endpoint
            else:
                model_id = self.config.default_model or str(models[0]["id"])
                if lazy_startup:
                    # Fast IDE launch path: register discovered GGUF models immediately
                    # without spawning llama-server.exe synchronously on the startup path.
                    self.config.default_model = model_id
                else:
                    self.activate_model(model_id)
            self._update_status(ProviderStatus.CONNECTED)
            return True
        except Exception as exc:
            self._update_status(ProviderStatus.ERROR, str(exc))
            self.logger.error("llama.cpp connection failed: %s", exc)
            return False

    def disconnect(self) -> None:
        self.cancel_generation()
        if bool(self.config.options.get("stop_owned_server_on_exit", True)):
            self.loader.stop()
        self._update_status(ProviderStatus.DISCONNECTED)

    def ensure_server(self, model_id: Optional[str] = None) -> bool:
        target = model_id or self.config.default_model or self._get_model_id()
        self.activate_model(target)
        return True

    def activate_model(self, model_id: str) -> str:
        self.loader.update_options({**self.config.options, "endpoint": self.config.endpoint})
        endpoint = self.loader.ensure_server(model_id)
        self._active_endpoint = endpoint
        self.config.default_model = model_id
        self._update_status(ProviderStatus.CONNECTED)
        return endpoint

    def warm_model(self, model_id: str, **_kwargs) -> bool:
        self.activate_model(model_id)
        return True

    def cancel_generation(self) -> None:
        self._cancel.set()
        with self._response_lock:
            response = self._response
        if response is not None:
            try:
                response.close()
            except Exception:
                pass

    def refresh_models(self) -> List[Dict[str, Any]]:
        self.loader.update_options({**self.config.options, "endpoint": self.config.endpoint})
        models = self.loader.discover_models()
        self._set_models(models)
        return models

    def generate_response(self, prompt: str, model_id: Optional[str] = None,
                          system_prompt: Optional[str] = None, **kwargs) -> str:
        return self._request(prompt, model_id, system_prompt, False, None, **kwargs)

    def stream_response(self, prompt: str, model_id: Optional[str] = None,
                        system_prompt: Optional[str] = None,
                        on_chunk: Optional[Callable[[str], None]] = None,
                        **kwargs) -> str:
        return self._request(prompt, model_id, system_prompt, True, on_chunk, **kwargs)

    def _request(self, prompt: str, model_id: Optional[str], system_prompt: Optional[str],
                 stream: bool, on_chunk: Optional[Callable[[str], None]], **kwargs) -> str:
        selected = self._get_model_id(model_id)
        self._cancel.clear()
        self.activate_model(selected)
        if self._cancel.is_set():
            raise LlamaCppCancelledError("Streaming cancelled")
        custom_messages = kwargs.pop("messages", None)
        tools = kwargs.pop("tools", None)
        if custom_messages and isinstance(custom_messages, list):
            messages = [dict(m) for m in custom_messages if isinstance(m, dict)]
            if system_prompt and (not messages or messages[0].get("role") != "system"):
                messages.insert(0, {"role": "system", "content": system_prompt})
        else:
            messages = [{"role": "user", "content": prompt}]
            if system_prompt:
                messages.insert(0, {"role": "system", "content": system_prompt})
        payload: Dict[str, Any] = {
            "model": self.loader.api_model_id or selected,
            "messages": messages,
            "stream": stream,
        }
        if kwargs.get("cache_prompt") is not None:
            payload["cache_prompt"] = bool(kwargs.pop("cache_prompt"))
        if tools:
            payload["tools"] = tools
        for key in ("temperature", "max_tokens", "top_p", "stop", "grammar", "response_format"):
            if key in kwargs:
                payload[key] = kwargs[key]
        request = urllib.request.Request(
            f"{(self._active_endpoint or self.config.endpoint).rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "OwnCode/0.4"},
            method="POST",
        )
        self.loader._validate_endpoint(self._active_endpoint or self.config.endpoint)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        full: List[str] = []
        try:
            response = opener.open(request, timeout=self.config.timeout_seconds)
            with self._response_lock:
                self._response = response
            if not stream:
                result = json.loads(response.read().decode("utf-8"))
                return str(result.get("choices", [{}])[0].get("message", {}).get("content", ""))
            for raw_line in response:
                if self._cancel.is_set():
                    raise LlamaCppCancelledError("Streaming cancelled")
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                content = str(chunk.get("choices", [{}])[0].get("delta", {}).get("content") or "")
                if content:
                    full.append(content)
                    if on_chunk:
                        on_chunk(content)
            return "".join(full)
        except LlamaCppCancelledError:
            raise
        except (urllib.error.HTTPError, AttributeError, OSError) as exc:
            if self._cancel.is_set():
                raise LlamaCppCancelledError("Streaming cancelled") from exc
            # When http.client's underlying socket is closed mid-stream (or at EOF),
            # iterating over `response` can raise AttributeError: 'NoneType' object has no attribute 'peek'.
            if isinstance(exc, AttributeError) and "peek" in str(exc):
                if full:
                    return "".join(full)
                raise LlamaCppCancelledError("Streaming connection closed") from exc
            if not isinstance(exc, urllib.error.HTTPError):
                raise RuntimeError(f"llama-server connection failed: {exc}") from exc
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"llama-server HTTP {exc.code}: {detail[:500]}") from exc
        finally:
            with self._response_lock:
                response = self._response
                self._response = None
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass


# ============================================================================
# SECTION: ai.providers.ollama_provider (ai/providers/ollama_provider.py)
# ============================================================================
"""
Ollama Provider.

Local LLM provider using Ollama API.
"""

import json
import os
import shutil
import subprocess
import threading
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
import socket
from urllib.parse import urlparse
from core.logger import setup_logger
from core.process_utils import hidden_subprocess_kwargs

from ai.providers.base_provider import BaseProvider, ProviderConfig, ProviderStatus


logger = setup_logger(__name__)

# Keys Ollama accepts at the TOP level of an /api/generate body. Everything
# else that looks like a runtime knob has to travel inside "options" — Ollama
# silently ignores unknown top-level keys, so `num_ctx=2048` sitting next to
# "prompt" did nothing at all and every request used the model's default
# context (usually far larger, and therefore slower to evaluate).
_TOP_LEVEL_KEYS = frozenset({
    "model", "prompt", "suffix", "system", "template", "context", "stream",
    "raw", "format", "images", "keep_alive", "think", "options",
})

# Ollama keys a loaded model by (name + runner options). Changing num_ctx
# between calls therefore *evicts and reloads* the model — the exact stall we
# are trying to remove. So one stable value is used for warm-ups and for real
# requests alike; see `OllamaProvider.default_num_ctx`.
DEFAULT_NUM_CTX = 8192
DEFAULT_KEEP_ALIVE = "30m"


def _split_options(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Return a payload fragment with runtime knobs nested under "options"."""
    payload: Dict[str, Any] = {}
    options: Dict[str, Any] = dict(kwargs.pop("options", None) or {})
    for key, value in kwargs.items():
        if key in _TOP_LEVEL_KEYS:
            payload[key] = value
        else:
            options.setdefault(key, value)
    if options:
        payload["options"] = options
    return payload


class OllamaProvider(BaseProvider):
    """
    Provider implementation for Ollama local LLM server.
    
    Supports:
    - Text generation
    - Streaming responses
    - Model listing
    
    Does NOT support:
    - Vision
    - Tool calling (currently)
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)

        # Update config with defaults if not set
        if not self.config.endpoint:
            self.config.endpoint = "http://localhost:11434"
        if not self.config.supports_streaming:
            self.config.supports_streaming = True
        if not self.config.supports_tool_calling:
            self.config.supports_tool_calling = False
        if not self.config.supports_vision:
            self.config.supports_vision = False

        # Serialises `ensure_server` so two callers racing on a dead socket
        # don't each spawn their own `ollama serve`.
        self._server_lock = threading.Lock()
        self._server_spawned = False
        # Cheap positive cache for is_server_up(); a live daemon stays live.
        self._server_seen_up_at = 0.0

        # Runner options must be identical for the warm-up and the real request
        # or Ollama reloads the model. The optimizer overwrites these from
        # config/llm_optimizer.json at startup.
        self.default_num_ctx = DEFAULT_NUM_CTX
        self.default_keep_alive = DEFAULT_KEEP_ALIVE

    # ── Server lifecycle ────────────────────────────────────────────────────

    def is_server_up(self, timeout: float = 1.5, cache_seconds: float = 20.0) -> bool:
        """True if the Ollama daemon answers on the configured endpoint."""
        if cache_seconds and (time.time() - self._server_seen_up_at) < cache_seconds:
            return True
        try:
            parsed = urlparse(self.config.endpoint or "http://127.0.0.1:11434")
            host = "127.0.0.1" if (parsed.hostname or "").lower() in ("localhost", "127.0.0.1", "") else parsed.hostname
            port = parsed.port or 11434
            with socket.create_connection((host, int(port)), timeout=min(0.2, timeout)):
                pass
            request = urllib.request.Request(f"{self.config.endpoint}/api/tags")
            request.add_header("User-Agent", "OwnCode/0.4")
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response.status == 200:
                    response.read()  # drain so the socket can be reused
                    self._server_seen_up_at = time.time()
                    return True
        except Exception:
            pass
        return False

    def ensure_server(self, wait_seconds: float = 20.0) -> bool:
        """Make sure the Ollama daemon is running, starting it if it isn't.

        The old behaviour was to fail the user's first message with "please run
        `ollama serve`" — which meant the very first reply of a session cost a
        round trip through the user's terminal. Now we start the daemon
        ourselves and wait for it to answer.

        Returns True if the server is reachable by the time we give up.
        """
        if self.is_server_up():
            return True

        with self._server_lock:
            # Another thread may have started it while we waited on the lock.
            if self.is_server_up(cache_seconds=0):
                return True

            exe = shutil.which("ollama")
            if not exe:
                self.logger.warning(
                    "Ollama is not reachable and the `ollama` executable is not "
                    "on PATH — cannot start it automatically."
                )
                return False

            if not self._is_local_endpoint():
                self.logger.info(
                    f"Ollama endpoint {self.config.endpoint} is remote; not "
                    "starting a local server."
                )
                return False

            try:
                self.logger.info("Ollama is not running — starting `ollama serve`…")
                kwargs: Dict[str, Any] = {
                    "stdout": subprocess.DEVNULL,
                    "stderr": subprocess.DEVNULL,
                    "stdin": subprocess.DEVNULL,
                }
                if os.name == "nt":
                    # CRITICAL: Do NOT pass DETACHED_PROCESS! On Windows, Win32
                    # CreateProcessW ignores CREATE_NO_WINDOW when combined with
                    # DETACHED_PROCESS, causing ollama.exe child GPU probes to
                    # flash 20-30 console windows.
                    kwargs.update(hidden_subprocess_kwargs())
                else:
                    kwargs["start_new_session"] = True
                subprocess.Popen([exe, "serve"], **kwargs)
                self._server_spawned = True
            except Exception as e:
                self.logger.error(f"Failed to start `ollama serve`: {e}")
                return False

        # Poll outside the lock so other callers can piggy-back on the result.
        deadline = time.time() + max(wait_seconds, 0.0)
        delay = 0.25
        while time.time() < deadline:
            if self.is_server_up(timeout=1.5, cache_seconds=0):
                self.logger.info("Ollama server is up.")
                return True
            time.sleep(delay)
            delay = min(delay * 1.5, 2.0)

        self.logger.warning(
            f"Started `ollama serve` but it did not answer within {wait_seconds:.0f}s."
        )
        return False

    def _is_local_endpoint(self) -> bool:
        """True when the endpoint points at this machine."""
        endpoint = (self.config.endpoint or "").lower()
        return any(host in endpoint for host in
                   ("localhost", "127.0.0.1", "0.0.0.0", "[::1]", "//::1"))

    def connect(self) -> bool:
        """Connect to Ollama server.

        The /api/tags probe already returns the full installed-model list, so we
        cache it here instead of throwing the body away. Previously connect()
        discarded it and the UI depended on a *separate* refresh_models() call —
        if Ollama wasn't up yet at startup that call failed and the model list
        stayed empty even after a later reconnect succeeded.
        """
        try:
            self._update_status(ProviderStatus.CONNECTING)

            # Test connection
            url = f"{self.config.endpoint}/api/tags"
            request = urllib.request.Request(url)
            request.add_header("User-Agent", "OwnCode/0.4")

            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                if response.status == 200:
                    models = self._parse_tags(response.read().decode("utf-8"))
                    if models:
                        self._set_models(models)
                    self._set_connected()
                    self._server_seen_up_at = time.time()
                    self.logger.info(
                        f"Connected to Ollama at {self.config.endpoint} "
                        f"({len(models)} installed model(s))"
                    )
                    return True

        except urllib.error.URLError as e:
            self._update_status(ProviderStatus.ERROR, str(e))
            self.logger.warning(f"Failed to connect to Ollama: {e}")
        except Exception as e:
            self._update_status(ProviderStatus.ERROR, str(e))
            self.logger.error(f"Unexpected error connecting to Ollama: {e}")
        
        return False

    def disconnect(self) -> None:
        """Disconnect from Ollama server."""
        self._update_status(ProviderStatus.DISCONNECTED)
        self.logger.info(f"Disconnected from Ollama at {self.config.endpoint}")

    def list_running_models(self) -> List[str]:
        """Return the model names Ollama currently holds in memory (via /api/ps)."""
        try:
            url = f"{self.config.endpoint}/api/ps"
            request = urllib.request.Request(url)
            request.add_header("User-Agent", "OwnCode/0.4")
            with urllib.request.urlopen(request, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    return [m.get("name") or m.get("model") for m in data.get("models", []) if m]
        except Exception as e:
            self.logger.debug(f"Could not list running Ollama models: {e}")
        return []

    def unload_models(self, models: Optional[List[str]] = None) -> int:
        """Evict models from VRAM/RAM by sending keep_alive=0 to Ollama.

        Ollama frees a model's memory when a request sets keep_alive to 0.
        Called on app exit so local LLMs don't keep consuming VRAM/RAM.
        Returns the number of models we asked Ollama to unload.
        """
        targets = models if models is not None else self.list_running_models()
        unloaded = 0
        for name in targets:
            if not name:
                continue
            try:
                payload = json.dumps({"model": name, "keep_alive": 0}).encode("utf-8")
                request = urllib.request.Request(
                    f"{self.config.endpoint}/api/generate",
                    data=payload,
                    method="POST",
                )
                request.add_header("Content-Type", "application/json")
                request.add_header("User-Agent", "OwnCode/0.4")
                with urllib.request.urlopen(request, timeout=10) as response:
                    if response.status == 200:
                        response.read()  # drain
                        unloaded += 1
                        self.logger.info(f"Unloaded Ollama model from memory: {name}")
            except Exception as e:
                self.logger.warning(f"Failed to unload Ollama model {name}: {e}")
        return unloaded

    # ── Warm-up ─────────────────────────────────────────────────────────────

    @staticmethod
    def _normalise_tag(name: str) -> str:
        """`qwen2.5-coder` and `qwen2.5-coder:latest` are the same model."""
        name = (name or "").strip()
        return name if ":" in name else f"{name}:latest"

    def is_model_loaded(self, model_id: str) -> bool:
        """True if Ollama already holds this model in memory (no load needed)."""
        if not model_id:
            return False
        want = self._normalise_tag(model_id)
        return any(self._normalise_tag(n) == want for n in self.list_running_models())

    def warm_model(self, model_id: Optional[str] = None,
                   keep_alive: Optional[str] = None, force: bool = False,
                   timeout: float = 300.0) -> bool:
        """Load a model into memory *before* the user needs it.

        Posting an empty prompt to /api/generate makes Ollama load the weights
        and return immediately without generating anything, which is the whole
        cost of a "cold" first message. Doing it ahead of time is what turns the
        first reply from a multi-second stall into a normal one.

        The options here MUST match what generate/stream send, or Ollama treats
        it as a different runner and reloads the model anyway.

        Returns True if the model is resident when we return.
        """
        try:
            model = self._get_model_id(model_id)
        except Exception as e:
            self.logger.debug(f"Cannot warm — no model to warm: {e}")
            return False

        if not self.ensure_server():
            return False

        if not force and self.is_model_loaded(model):
            self.logger.debug(f"Model already resident, skipping warm: {model}")
            return True

        keep_alive = keep_alive or self.default_keep_alive
        payload = json.dumps({
            "model": model,
            "prompt": "",          # load only — Ollama generates nothing
            "stream": False,
            "keep_alive": keep_alive,
            "options": {"num_ctx": self.default_num_ctx},
        }).encode("utf-8")

        try:
            started = time.time()
            request = urllib.request.Request(
                f"{self.config.endpoint}/api/generate", data=payload, method="POST")
            request.add_header("Content-Type", "application/json")
            request.add_header("User-Agent", "OwnCode/0.4")
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response.status == 200:
                    response.read()  # drain
                    self.logger.info(
                        f"Warmed Ollama model {model} in {time.time() - started:.1f}s "
                        f"(keep_alive={keep_alive})"
                    )
                    return True
        except Exception as e:
            self.logger.warning(f"Failed to warm Ollama model {model}: {e}")
        return False


    def generate_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response from Ollama (supports both /api/chat multi-turn and /api/generate)."""
        model = self._get_model_id(model_id)
        custom_messages = kwargs.pop("messages", None)
        tools = kwargs.pop("tools", None)
        use_chat_api = bool(custom_messages and isinstance(custom_messages, list))

        if use_chat_api:
            messages = [dict(m) for m in custom_messages if isinstance(m, dict)]
            if system_prompt and (not messages or messages[0].get("role") != "system"):
                messages.insert(0, {"role": "system", "content": system_prompt})
            payload: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "stream": False,
            }
            if tools:
                payload["tools"] = tools
        else:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
            }
            if system_prompt:
                payload["system"] = system_prompt

        # Add optimization parameters
        # Set default context size if not specified
        if 'num_ctx' not in kwargs:
            kwargs['num_ctx'] = self.default_num_ctx

        # Keep model loaded in memory
        if 'keep_alive' not in kwargs:
            kwargs['keep_alive'] = self.default_keep_alive

        # Runtime knobs belong under "options"; top-level ones stay put.
        payload.update(_split_options(kwargs))

        endpoint_path = "/api/chat" if use_chat_api else "/api/generate"
        url = f"{self.config.endpoint}{endpoint_path}"
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                if use_chat_api:
                    msg = result.get("message") or {}
                    return msg.get("content", "") or result.get("response", "")
                return result.get("response", "")
                
        except Exception as e:
            self.logger.error(f"Ollama generation failed: {e}")
            raise

    def stream_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        on_chunk: Optional[callable] = None,
        **kwargs
    ) -> str:
        """Stream a response from Ollama."""
        model = self._get_model_id(model_id)

        # A dead daemon used to surface as "please run `ollama serve`" on the
        # user's first message; start it instead so the message just works.
        self.ensure_server()

        custom_messages = kwargs.pop("messages", None)
        tools = kwargs.pop("tools", None)
        use_chat_api = bool(custom_messages and isinstance(custom_messages, list))

        if use_chat_api:
            messages = [dict(m) for m in custom_messages if isinstance(m, dict)]
            if system_prompt and (not messages or messages[0].get("role") != "system"):
                messages.insert(0, {"role": "system", "content": system_prompt})
            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
            }
            if tools:
                payload["tools"] = tools
        else:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True,
            }
            if system_prompt:
                payload["system"] = system_prompt

        # Add optimization parameters
        if 'num_ctx' not in kwargs:
            kwargs['num_ctx'] = self.default_num_ctx

        if 'keep_alive' not in kwargs:
            kwargs['keep_alive'] = self.default_keep_alive

        payload.update(_split_options(kwargs))

        endpoint_path = "/api/chat" if use_chat_api else "/api/generate"
        url = f"{self.config.endpoint}{endpoint_path}"
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        full_response = ""
        
        # Reduced timeout - model should be preloaded
        stream_timeout = max(self.config.timeout_seconds, 120)
        
        try:
            with urllib.request.urlopen(request, timeout=stream_timeout) as response:
                for line in response:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str:
                            try:
                                chunk = json.loads(line_str)
                                response_text = (
                                    (chunk.get("message") or {}).get("content", "")
                                    if use_chat_api
                                    else chunk.get("response", "")
                                ) or chunk.get("response", "")
                                full_response += response_text
                                
                                if on_chunk and response_text:
                                    on_chunk(response_text)
                                
                                if chunk.get("done", False):
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
                                
        except urllib.error.URLError as e:
            self.logger.error(f"Ollama streaming failed (URLError): {e}")
            # Try to reconnect for next call
            self._update_status(ProviderStatus.ERROR, str(e))
            raise
        except Exception as e:
            self.logger.error(f"Ollama streaming failed: {e}")
            raise
        
        return full_response

    @staticmethod
    def _parse_tags(raw: str) -> List[Dict[str, Any]]:
        """Turn an /api/tags response body into our model-dict list.

        Ollama returns the tag (e.g. "qwen2.5-coder:7b") under "name"; newer
        builds also send "model". We accept either so the list is never empty
        just because of a field rename.
        """
        try:
            result = json.loads(raw)
        except Exception:
            return []
        parsed: List[Dict[str, Any]] = []
        for model in result.get("models", []) or []:
            name = model.get("name") or model.get("model") or ""
            if not name:
                continue
            parsed.append({
                "id": name,
                "name": name,
                "size": model.get("size", 0),
                "digest": model.get("digest", ""),
                "details": model.get("details", {}),
            })
        return parsed

    def refresh_models(self) -> List[Dict[str, Any]]:
        """Refresh available models from Ollama (GET /api/tags)."""
        url = f"{self.config.endpoint}/api/tags"
        request = urllib.request.Request(url)
        request.add_header("User-Agent", "OwnCode/0.4")

        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                parsed_models = self._parse_tags(response.read().decode("utf-8"))
                self.logger.info(f"Refreshed {len(parsed_models)} Ollama model(s)")
                return parsed_models

        except Exception as e:
            self.logger.error(f"Failed to refresh Ollama models: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────────────────────────────

    def _set_connected(self) -> None:
        """Set provider to connected status."""
        self._update_status(ProviderStatus.CONNECTED)


# ============================================================================
# SECTION: ai.providers.qwen_provider (ai/providers/qwen_provider.py)
# ============================================================================
"""
Qwen Provider.

Local Qwen3 8B coding agent integration using OpenAI-compatible API.
Optimized for code generation, completion, and debugging tasks.
"""

import json
import socket
from urllib.parse import urlparse
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Callable
from core.logger import setup_logger

from ai.providers.base_provider import BaseProvider, ProviderConfig, ProviderStatus


logger = setup_logger(__name__)


class QwenProvider(BaseProvider):
    """
    Provider implementation for Qwen3 8B local coding agent.
    
    Supports:
    - Text generation
    - Streaming responses
    - Code completion
    - Code explanation
    - Debugging assistance
    
    Optimized for:
    - Python, JavaScript, TypeScript
    - Code generation and refactoring
    - API design
    - Documentation generation
    
    Does NOT support:
    - Vision (text-only model)
    - Tool calling (may be added in future)
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        
        # Update config with defaults
        if not self.config.endpoint:
            # Default to localhost Ollama
            self.config.endpoint = "http://localhost:11434"
        if not self.config.supports_streaming:
            self.config.supports_streaming = True
        if not self.config.supports_tool_calling:
            self.config.supports_tool_calling = False
        if not self.config.supports_vision:
            self.config.supports_vision = False
        if not self.config.supports_function_calling:
            self.config.supports_function_calling = True  # Qwen3 supports function calling
        
        # Detect API type from endpoint
        self.is_ollama = "11434" in self.config.endpoint or "/api/" in self.config.endpoint.lower()
        
        # Qwen-specific optimizations
        self.default_temperature = 0.7
        self.default_top_p = 0.95
        self.default_max_tokens = 4096
        self.context_window = 32768  # Qwen3 8B supports 32K context

    def is_server_up(self, timeout: float = 0.2, cache_seconds: float = 0.0) -> bool:
        try:
            parsed = urlparse(self.config.endpoint or "http://127.0.0.1:11434")
            host = "127.0.0.1" if (parsed.hostname or "").lower() in ("localhost", "127.0.0.1", "") else parsed.hostname
            port = parsed.port or 11434
            with socket.create_connection((host, int(port)), timeout=timeout):
                return True
        except OSError:
            return False

    def connect(self) -> bool:
        """Connect to Qwen3 local server (Ollama or OpenAI-compatible)."""
        if not self.is_server_up(timeout=0.2):
            self._update_status(ProviderStatus.DISCONNECTED, "Server not running")
            return False
        try:
            self._update_status(ProviderStatus.CONNECTING)
            
            # Test connection based on API type
            if self.is_ollama:
                # Ollama API
                url = f"{self.config.endpoint}/api/tags"
            else:
                # OpenAI-compatible API
                url = f"{self.config.endpoint}/models"
            
            request = urllib.request.Request(url)
            request.add_header("Content-Type", "application/json")
            request.add_header("User-Agent", "OwnCode/0.4-Qwen")
            
            # Add API key if provided (some local servers use auth)
            if self.config.api_key:
                request.add_header("Authorization", f"Bearer {self.config.api_key}")
            
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    
                    # Check for models
                    if self.is_ollama:
                        models = result.get("models", [])
                    else:
                        models = result.get("data", [])
                    
                    if models:
                        self._set_connected()
                        self.logger.info(f"Connected to Qwen3 at {self.config.endpoint} (Ollama: {self.is_ollama})")
                        
                        # Refresh models on successful connection
                        self.refresh_models()
                        return True
                    else:
                        self._update_status(ProviderStatus.ERROR, "No models available")
                        return False
                        
        except urllib.error.URLError as e:
            self._update_status(ProviderStatus.ERROR, f"Connection failed: {str(e)}")
            self.logger.warning(f"Failed to connect to Qwen3: {e}")
        except Exception as e:
            self._update_status(ProviderStatus.ERROR, str(e))
            self.logger.error(f"Unexpected error connecting to Qwen3: {e}")
        
        return False

    def disconnect(self) -> None:
        """Disconnect from Qwen3 server."""
        self._update_status(ProviderStatus.DISCONNECTED)
        self.logger.info(f"Disconnected from Qwen3 at {self.config.endpoint}")

    def generate_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate a response from Qwen3.
        
        Args:
            prompt: User prompt
            model_id: Model to use (defaults to qwen3:8b for Ollama or qwen3-8b for OpenAI)
            system_prompt: System prompt for context
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            Generated response text
        """
        model = self._get_model_id(model_id)
        
        if self.is_ollama:
            # Ollama API format - use /api/generate
            url = f"{self.config.endpoint}/api/generate"
            
            # Build prompt with system message if provided
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            payload = {
                "model": model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", self.default_temperature),
                    "top_p": kwargs.get("top_p", self.default_top_p),
                    "num_predict": kwargs.get("max_tokens", self.default_max_tokens),
                }
            }
        else:
            # OpenAI-compatible API format
            url = f"{self.config.endpoint}/chat/completions"
            
            # Build messages array
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "temperature": kwargs.get("temperature", self.default_temperature),
                "top_p": kwargs.get("top_p", self.default_top_p),
                "max_tokens": kwargs.get("max_tokens", self.default_max_tokens),
            }
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("User-Agent", "OwnCode/0.4-Qwen")
        
        if self.config.api_key:
            request.add_header("Authorization", f"Bearer {self.config.api_key}")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if self.is_ollama:
                    # Ollama generate format
                    return result.get("response", "")
                else:
                    # OpenAI format
                    choices = result.get("choices", [])
                    if choices:
                        message = choices[0].get("message", {})
                        content = message.get("content", "")
                        return content
                
                return ""
                
        except urllib.error.HTTPError as e:
            error_msg = f"Qwen3 API error: {e.code} - {e.reason}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            self.logger.error(f"Qwen3 generation failed: {e}")
            raise

    def stream_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> str:
        """
        Stream a response from Qwen3.
        
        Args:
            prompt: User prompt
            model_id: Model to use
            system_prompt: System prompt for context
            on_chunk: Callback for each chunk
            **kwargs: Additional parameters
            
        Returns:
            Complete generated response
        """
        model = self._get_model_id(model_id)
        full_response = ""
        
        if self.is_ollama:
            # Ollama API format - use generate endpoint
            url = f"{self.config.endpoint}/api/generate"
            
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            payload = {
                "model": model,
                "prompt": full_prompt,
                "stream": True,
                "options": {
                    "temperature": kwargs.get("temperature", self.default_temperature),
                    "top_p": kwargs.get("top_p", self.default_top_p),
                    "num_predict": kwargs.get("max_tokens", self.default_max_tokens),
                }
            }
        else:
            # OpenAI-compatible API format
            url = f"{self.config.endpoint}/chat/completions"
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
                "temperature": kwargs.get("temperature", self.default_temperature),
                "top_p": kwargs.get("top_p", self.default_top_p),
                "max_tokens": kwargs.get("max_tokens", self.default_max_tokens),
            }
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("User-Agent", "OwnCode/0.4-Qwen")
        
        if self.config.api_key:
            request.add_header("Authorization", f"Bearer {self.config.api_key}")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                for line in response:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        
                        if not line_str:
                            continue
                        
                        try:
                            if self.is_ollama:
                                # Ollama generate format - direct JSON per line
                                chunk = json.loads(line_str)
                                response_text = chunk.get("response", "")
                                
                                if response_text:
                                    full_response += response_text
                                    if on_chunk:
                                        on_chunk(response_text)
                                
                                if chunk.get("done", False):
                                    break
                            else:
                                # OpenAI format - SSE with "data: " prefix
                                if line_str.startswith(':'):
                                    continue
                                
                                if line_str.startswith('data: '):
                                    data_str = line_str[6:]
                                    
                                    if data_str == '[DONE]':
                                        break
                                    
                                    chunk = json.loads(data_str)
                                    choices = chunk.get("choices", [])
                                    
                                    if choices:
                                        delta = choices[0].get("delta", {})
                                        content = delta.get("content", "")
                                        
                                        if content:
                                            full_response += content
                                            if on_chunk:
                                                on_chunk(content)
                                        
                                        if choices[0].get("finish_reason"):
                                            break
                                            
                        except json.JSONDecodeError:
                            continue
                                
        except Exception as e:
            self.logger.error(f"Qwen3 streaming failed: {e}")
            raise
        
        return full_response

    def refresh_models(self) -> List[Dict[str, Any]]:
        """
        Refresh available models from Qwen3 server.
        
        Returns:
            List of model information dictionaries
        """
        if self.is_ollama:
            url = f"{self.config.endpoint}/api/tags"
        else:
            url = f"{self.config.endpoint}/models"
        
        request = urllib.request.Request(url)
        request.add_header("User-Agent", "OwnCode/0.4-Qwen")
        
        if self.config.api_key:
            request.add_header("Authorization", f"Bearer {self.config.api_key}")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if self.is_ollama:
                    # Ollama format
                    models = result.get("models", [])
                    parsed_models = []
                    
                    for model in models:
                        model_name = model.get("name", "")
                        
                        # Only include Qwen models
                        if "qwen" in model_name.lower():
                            is_coder = "coder" in model_name.lower()
                            
                            model_info = {
                                "id": model_name,
                                "name": model_name,
                                "size": model.get("size", 0),
                                "digest": model.get("digest", ""),
                                "context_window": self.context_window,
                                "max_output_tokens": self.default_max_tokens,
                                "type": "local",
                                "provider": "qwen",
                                "capabilities": ["code_generation", "code_completion", "chat"] if is_coder else ["chat"],
                                "supports_streaming": True,
                                "supports_function_calling": True,
                                "supports_vision": False,
                                "supported_languages": [
                                    "python", "javascript", "typescript", "java", 
                                    "c++", "c#", "go", "rust", "ruby", "php"
                                ] if is_coder else ["*"],
                                "strengths": [
                                    "code_generation",
                                    "code_completion", 
                                    "debugging",
                                    "refactoring"
                                ] if is_coder else ["general"],
                            }
                            parsed_models.append(model_info)
                else:
                    # OpenAI-compatible format
                    models = result.get("data", [])
                    parsed_models = []
                    
                    for model in models:
                        model_id = model.get("id", "")
                        
                        # Extract model capabilities
                        is_qwen = "qwen" in model_id.lower()
                        is_coder = any(x in model_id.lower() for x in ["coder", "code", "qwen3"])
                        
                        model_info = {
                            "id": model_id,
                            "name": model.get("name", model_id),
                            "context_window": self.context_window,
                            "max_output_tokens": self.default_max_tokens,
                            "type": "local",
                            "provider": "qwen",
                            "capabilities": self._extract_capabilities(model_id),
                            "supports_streaming": True,
                            "supports_function_calling": is_qwen,
                            "supports_vision": False,
                            "supported_languages": [
                                "python", "javascript", "typescript", "java", 
                                "c++", "c#", "go", "rust", "ruby", "php"
                            ] if is_coder else ["*"],
                            "strengths": [
                                "code_generation",
                                "code_completion", 
                                "debugging",
                                "refactoring"
                            ] if is_coder else ["general"],
                        }
                        parsed_models.append(model_info)
                
                # Store models
                self._set_models(parsed_models)
                self.logger.info(f"Refreshed {len(parsed_models)} Qwen models")
                
                return parsed_models
                
        except Exception as e:
            self.logger.error(f"Failed to refresh Qwen3 models: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────────
    # Qwen-Specific Features
    # ─────────────────────────────────────────────────────────────────────────────

    def generate_code(
        self,
        task: str,
        language: str = "python",
        context: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate code for a specific task.
        
        Args:
            task: Description of code to generate
            language: Programming language
            context: Additional context or existing code
            **kwargs: Additional parameters
            
        Returns:
            Generated code
        """
        system_prompt = f"""You are an expert {language} programmer. Generate clean, 
efficient, and well-documented code. Follow best practices and modern patterns."""
        
        prompt = f"Task: {task}"
        if context:
            prompt = f"Context:\n{context}\n\n{prompt}"
        
        return self.generate_response(prompt, system_prompt=system_prompt, **kwargs)

    def explain_code(
        self,
        code: str,
        language: str = "python",
        **kwargs
    ) -> str:
        """
        Explain what code does.
        
        Args:
            code: Code to explain
            language: Programming language
            **kwargs: Additional parameters
            
        Returns:
            Code explanation
        """
        system_prompt = "You are an expert code reviewer. Explain code clearly and concisely."
        
        prompt = f"Explain this {language} code:\n\n```{language}\n{code}\n```"
        
        return self.generate_response(prompt, system_prompt=system_prompt, **kwargs)

    def debug_code(
        self,
        code: str,
        error: str,
        language: str = "python",
        **kwargs
    ) -> str:
        """
        Help debug code with an error.
        
        Args:
            code: Code with error
            error: Error message
            language: Programming language
            **kwargs: Additional parameters
            
        Returns:
            Debugging suggestions
        """
        system_prompt = "You are an expert debugger. Identify issues and provide solutions."
        
        prompt = f"""Debug this {language} code:

```{language}
{code}
```

Error:
{error}

Identify the issue and suggest a fix."""
        
        return self.generate_response(prompt, system_prompt=system_prompt, **kwargs)

    def refactor_code(
        self,
        code: str,
        goal: str,
        language: str = "python",
        **kwargs
    ) -> str:
        """
        Refactor code for improvement.
        
        Args:
            code: Code to refactor
            goal: Refactoring goal (e.g., "improve performance", "add error handling")
            language: Programming language
            **kwargs: Additional parameters
            
        Returns:
            Refactored code
        """
        system_prompt = f"You are an expert {language} developer. Refactor code to improve quality."
        
        prompt = f"""Refactor this code to {goal}:

```{language}
{code}
```"""
        
        return self.generate_response(prompt, system_prompt=system_prompt, **kwargs)

    # ─────────────────────────────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────────────────────────────

    def _set_connected(self) -> None:
        """Set provider to connected status."""
        self._update_status(ProviderStatus.CONNECTED)

    def _extract_capabilities(self, model_id: str) -> List[str]:
        """Extract model capabilities from model ID."""
        capabilities = []
        
        model_lower = model_id.lower()
        
        if "qwen" in model_lower:
            capabilities.append("chat")
        if any(x in model_lower for x in ["coder", "code", "qwen3"]):
            capabilities.extend(["code_generation", "code_completion"])
        if "instruct" in model_lower or "chat" in model_lower:
            capabilities.append("instruction_following")
        
        return capabilities if capabilities else ["general"]


