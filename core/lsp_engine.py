"""
Consolidated Module: core.lsp_engine

Combines: core.lsp.language_server_config, core.lsp.jedi_provider, core.lsp.lsp_client, core.lsp.lsp_manager
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['core.lsp.language_server_config', 'core.lsp.jedi_provider', 'core.lsp.lsp_client', 'core.lsp.lsp_manager']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: core.lsp.language_server_config (core/lsp/language_server_config.py)
# ============================================================================
"""
Language Server Configuration classes.

Defines configurations for different language servers.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class LanguageServerConfig:
    """Configuration for a language server."""
    
    language_id: str
    name: str
    command: List[str]
    args: List[str] = field(default_factory=list)
    initialization_options: Dict[str, Any] = field(default_factory=dict)
    root_uri: Optional[str] = None
    workspace_folders: List[Dict[str, str]] = field(default_factory=list)
    supported_extensions: List[str] = field(default_factory=list)


# Predefined language server configurations
def get_standard_language_servers() -> Dict[str, LanguageServerConfig]:
    """Get standard language server configurations."""
    return {
        "python": LanguageServerConfig(
            language_id="python",
            name="Pyright",
            command=["pyright-langserver", "--stdio"],
            supported_extensions=[".py"],
        ),
        "javascript": LanguageServerConfig(
            language_id="javascript",
            name="TypeScript Language Server",
            command=["typescript-language-server", "--stdio"],
            supported_extensions=[".js", ".jsx"],
        ),
        "typescript": LanguageServerConfig(
            language_id="typescript",
            name="TypeScript Language Server",
            command=["typescript-language-server", "--stdio"],
            supported_extensions=[".ts", ".tsx"],
        ),
        "cpp": LanguageServerConfig(
            language_id="cpp",
            name="clangd",
            command=["clangd", "--background-index"],
            supported_extensions=[".cpp", ".cc", ".cxx", ".hpp", ".h", ".hxx"],
        ),
        "c": LanguageServerConfig(
            language_id="c",
            name="clangd",
            command=["clangd", "--background-index"],
            supported_extensions=[".c", ".h"],
        ),
        "java": LanguageServerConfig(
            language_id="java",
            name="Eclipse JDT Language Server",
            command=["java", "-jar", "path/to/jdt-language-server.jar"],
            supported_extensions=[".java"],
        ),
        "html": LanguageServerConfig(
            language_id="html",
            name="HTML Language Server",
            command=["vscode-html-language-server", "--stdio"],
            supported_extensions=[".html", ".htm"],
        ),
        "css": LanguageServerConfig(
            language_id="css",
            name="CSS Language Server",
            command=["vscode-css-language-server", "--stdio"],
            supported_extensions=[".css", ".scss", ".less"],
        ),
        "json": LanguageServerConfig(
            language_id="json",
            name="JSON Language Server",
            command=["vscode-json-language-server", "--stdio"],
            supported_extensions=[".json"],
        ),
        "yaml": LanguageServerConfig(
            language_id="yaml",
            name="YAML Language Server",
            command=["yaml-language-server", "--stdio"],
            supported_extensions=[".yaml", ".yml"],
        ),
        "markdown": LanguageServerConfig(
            language_id="markdown",
            name="Markdown Language Server",
            command=["markdown-language-server", "--stdio"],
            supported_extensions=[".md"],
        ),
        "rust": LanguageServerConfig(
            language_id="rust",
            name="rust-analyzer",
            command=["rust-analyzer"],
            supported_extensions=[".rs"],
        ),
        "go": LanguageServerConfig(
            language_id="go",
            name="gopls",
            command=["gopls", "serve"],
            supported_extensions=[".go"],
        ),
        "php": LanguageServerConfig(
            language_id="php",
            name="Intelephense",
            command=["intelephense", "--stdio"],
            supported_extensions=[".php"],
        ),
    }


# ============================================================================
# SECTION: core.lsp.jedi_provider (core/lsp/jedi_provider.py)
# ============================================================================
"""
jedi_provider.py — In-process Python language intelligence (Phase 2 item 7).

The subprocess :class:`LSPClient` speaks the LSP wire protocol to *external*
language servers, which the user must install. This provider is the batteries-
included alternative: it uses `jedi <https://jedi.readthedocs.io>`_ — a pure-
Python static-analysis library — to answer the same requests **in-process and
synchronously**, so Python intelligence works out of the box with no server.

Features provided: completion, hover docs, signature help, go-to-definition,
find-references and rename-symbol.

Graceful degradation
--------------------
`jedi` is listed in requirements but may be absent (e.g. a minimal install or a
sandbox with no network). When it cannot be imported, :data:`JEDI_AVAILABLE` is
False and every method returns an empty result rather than raising — callers can
treat "no jedi" and "nothing found" identically. This module is Qt-free so it can
be unit-tested headlessly.

Positions are **0-based line, 0-based column** on the way in (editor convention);
jedi's own API is 1-based line / 0-based column, and the translation is handled
here so callers never see it.
"""

from dataclasses import dataclass, field
from typing import List, Optional

try:  # pragma: no cover - import guard
    import jedi
    JEDI_AVAILABLE = True
except Exception:  # ImportError or any transitive failure
    jedi = None
    JEDI_AVAILABLE = False


@dataclass
class Completion:
    """One completion candidate."""
    label: str
    kind: str = ""          # e.g. "function", "class", "keyword", "module"
    detail: str = ""        # short type/signature hint
    documentation: str = ""
    insert_text: str = ""   # what to actually insert (defaults to label)


@dataclass
class Location:
    """A source location for definitions / references."""
    path: str
    line: int               # 0-based
    column: int             # 0-based
    text: str = ""          # the line's text, for preview lists


@dataclass
class Signature:
    """One call signature for signature help."""
    label: str
    documentation: str = ""
    parameters: List[str] = field(default_factory=list)
    active_parameter: int = 0


@dataclass
class Hover:
    """Hover information at a position."""
    text: str
    signature: str = ""


class JediProvider:
    """Answer language-intelligence requests for Python source via jedi.

    All methods accept the *current* buffer ``source`` (unsaved edits included),
    a ``path`` for the file, and a 0-based ``line``/``column`` cursor position.
    Nothing is cached: jedi builds its own module cache, and passing the live
    buffer each call keeps results correct while the user types.
    """

    def __init__(self, project_root: Optional[str] = None) -> None:
        self._root = project_root
        self._project = None
        if JEDI_AVAILABLE and project_root:
            try:
                self._project = jedi.Project(project_root)
            except Exception:
                self._project = None

    @property
    def available(self) -> bool:
        return JEDI_AVAILABLE

    # ── internal ────────────────────────────────────────────────────────────
    def _script(self, source: str, path: Optional[str]):
        """Build a jedi Script, or None if jedi is unavailable/errored."""
        if not JEDI_AVAILABLE:
            return None
        try:
            return jedi.Script(code=source, path=path or None,
                               project=self._project)
        except Exception:
            return None

    @staticmethod
    def _kind(name) -> str:
        try:
            return name.type or ""
        except Exception:
            return ""

    # ── features ──────────────────────────────────────────────────────────────
    def complete(self, source: str, path: str, line: int,
                 column: int) -> List[Completion]:
        """Completion candidates at the cursor (jedi line is 1-based)."""
        script = self._script(source, path)
        if script is None:
            return []
        out: List[Completion] = []
        try:
            for c in script.complete(line + 1, column):
                detail = ""
                try:
                    detail = c.description or ""
                except Exception:
                    pass
                out.append(Completion(
                    label=c.name,
                    kind=self._kind(c),
                    detail=detail,
                    insert_text=c.name,
                ))
        except Exception:
            return []
        return out

    def hover(self, source: str, path: str, line: int,
              column: int) -> Optional[Hover]:
        """Type/docstring info for the symbol under the cursor."""
        script = self._script(source, path)
        if script is None:
            return None
        try:
            names = script.help(line + 1, column)
        except Exception:
            return None
        if not names:
            return None
        name = names[0]
        try:
            sig_list = name.get_signatures()
            signature = sig_list[0].to_string() if sig_list else ""
        except Exception:
            signature = ""
        try:
            doc = name.docstring() or ""
        except Exception:
            doc = ""
        if not doc and not signature:
            return None
        return Hover(text=doc, signature=signature)

    def signatures(self, source: str, path: str, line: int,
                   column: int) -> List[Signature]:
        """Call-signature help at the cursor (e.g. inside a call's parens)."""
        script = self._script(source, path)
        if script is None:
            return []
        out: List[Signature] = []
        try:
            for s in script.get_signatures(line + 1, column):
                params = []
                try:
                    params = [p.to_string() for p in s.params]
                except Exception:
                    pass
                active = s.index if s.index is not None else 0
                out.append(Signature(
                    label=s.to_string(),
                    documentation=(s.docstring() or ""),
                    parameters=params,
                    active_parameter=active,
                ))
        except Exception:
            return []
        return out

    def definition(self, source: str, path: str, line: int,
                   column: int) -> List[Location]:
        """Go-to-definition targets for the symbol under the cursor."""
        script = self._script(source, path)
        if script is None:
            return []
        try:
            defs = script.goto(line + 1, column, follow_imports=True,
                               follow_builtin_imports=True)
        except Exception:
            return []
        return self._to_locations(defs)

    def references(self, source: str, path: str, line: int,
                   column: int) -> List[Location]:
        """All references to the symbol under the cursor."""
        script = self._script(source, path)
        if script is None:
            return []
        try:
            refs = script.get_references(line + 1, column,
                                         include_builtins=False)
        except Exception:
            return []
        return self._to_locations(refs)

    def rename(self, source: str, path: str, line: int, column: int,
               new_name: str) -> List[Location]:
        """Return every reference that a rename would touch.

        jedi's ``Refactoring`` API can rewrite files directly, but the editor
        owns unsaved buffers, so we return the reference sites and let the caller
        apply edits through its own change pipeline.
        """
        return self.references(source, path, line, column)

    @staticmethod
    def _to_locations(names) -> List[Location]:
        out: List[Location] = []
        for n in names or []:
            try:
                mod_path = str(n.module_path) if n.module_path else ""
                ln = (n.line - 1) if n.line else 0
                col = n.column or 0
            except Exception:
                continue
            text = ""
            try:
                text = (n.get_line_code() or "").rstrip("\n")
            except Exception:
                pass
            out.append(Location(path=mod_path, line=ln, column=col, text=text))
        return out



# ============================================================================
# SECTION: core.lsp.lsp_client (core/lsp/lsp_client.py)
# ============================================================================
"""
LSP Client - Handles JSON-RPC communication with language servers.
"""

import json
import subprocess
import threading
import queue
from typing import Dict, Any, Optional, Callable
from PySide6.QtCore import QObject, Signal
from core.logger import setup_logger
from core.process_utils import hidden_subprocess_kwargs

logger = setup_logger(__name__)


class LSPClient(QObject):
    """Client for communicating with a language server via JSON-RPC."""
    
    # Signals
    message_received = Signal(object)  # Emits (message)
    error_occurred = Signal(str)       # Emits error message
    connection_closed = Signal()       # Emits when connection closes
    
    def __init__(self, config: "LanguageServerConfig"):
        super().__init__()
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self.pending_requests: Dict[int, Callable] = {}
        self.message_queue = queue.Queue()
        self.running = False
        self.read_thread: Optional[threading.Thread] = None
        
    def start(self, root_uri: str, workspace_folders: Optional[list] = None) -> bool:
        """Start the language server process."""
        try:
            cmd = self.config.command + self.config.args
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                **hidden_subprocess_kwargs(),
            )
            
            self.running = True
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()
            
            # Send initialize request
            initialize_params = {
                "processId": None,
                "rootUri": root_uri,
                "workspaceFolders": workspace_folders or [{"uri": root_uri, "name": "workspace"}],
                "capabilities": {
                    "textDocument": {
                        "completion": {"dynamicRegistration": False},
                        "hover": {"dynamicRegistration": False},
                        "definition": {"dynamicRegistration": False},
                        "references": {"dynamicRegistration": False},
                        "publishDiagnostics": {},
                    },
                    "workspace": {
                        "workspaceFolders": True,
                    },
                },
            }
            
            self.send_request("initialize", initialize_params, self._on_initialize_response)
            return True
            
        except Exception as e:
            logger.error(f"Failed to start language server: {e}")
            self.error_occurred.emit(str(e))
            return False
            
    def stop(self):
        """Stop the language server process."""
        self.running = False
        if self.process:
            try:
                self.send_notification("shutdown")
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception as e:
                logger.error(f"Error stopping language server: {e}")
                self.process.kill()
            finally:
                self.process = None
                self.connection_closed.emit()
                
    def _read_loop(self):
        """Read messages from the server."""
        buffer = b""
        try:
            while self.running and self.process and self.process.stdout:
                chunk = self.process.stdout.read(4096)
                if not chunk:
                    break
                buffer += chunk
                
                # Parse messages
                while b"\r\n\r\n" in buffer:
                    header_part, buffer = buffer.split(b"\r\n\r\n", 1)
                    headers = {}
                    for line in header_part.split(b"\r\n"):
                        if b":" in line:
                            key, value = line.split(b":", 1)
                            headers[key.decode().strip()] = value.decode().strip()
                            
                    content_length = int(headers.get("Content-Length", 0))
                    if len(buffer) >= content_length:
                        content = buffer[:content_length].decode("utf-8")
                        buffer = buffer[content_length:]
                        try:
                            message = json.loads(content)
                            self._handle_message(message)
                        except Exception as e:
                            logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"Read loop error: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.running = False
            self.connection_closed.emit()
            
    def _handle_message(self, message: Dict[str, Any]):
        """Handle an incoming message from the server."""
        if "id" in message:
            # Response
            if "error" in message:
                logger.error(f"Request error: {message['error']}")
                if message["id"] in self.pending_requests:
                    callback = self.pending_requests.pop(message["id"])
                    try:
                        callback({"error": message["error"]})
                    except Exception:
                        pass
            elif "result" in message and message["id"] in self.pending_requests:
                callback = self.pending_requests.pop(message["id"])
                callback(message["result"])
        else:
            # Notification
            self.message_received.emit(message)
            
    def send_request(self, method: str, params: Any, callback: Callable) -> int:
        """Send a request to the server."""
        self.request_id += 1
        req_id = self.request_id
        self.pending_requests[req_id] = callback
        
        message = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }
        
        self._send_message(message)
        return req_id
        
    def send_notification(self, method: str, params: Any = None):
        """Send a notification to the server."""
        message = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            message["params"] = params
            
        self._send_message(message)
        
    def _send_message(self, message: Dict[str, Any]):
        """Send a message to the server's stdin."""
        try:
            content = json.dumps(message, ensure_ascii=False)
            content_bytes = content.encode("utf-8")
            header = f"Content-Length: {len(content_bytes)}\r\n\r\n"
            header_bytes = header.encode("utf-8")
            
            if self.process and self.process.stdin:
                self.process.stdin.write(header_bytes)
                self.process.stdin.write(content_bytes)
                self.process.stdin.flush()
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            self.error_occurred.emit(str(e))
            
    def _on_initialize_response(self, result):
        """Handle initialize response."""
        logger.info("Language server initialized")
        self.send_notification("initialized")


# ============================================================================
# SECTION: core.lsp.lsp_manager (core/lsp/lsp_manager.py)
# ============================================================================
"""
LSP Manager - Manages multiple language server clients.
"""

from typing import Dict, Optional
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from core.logger import setup_logger
from core.lsp.lsp_client import LSPClient
from core.lsp.language_server_config import LanguageServerConfig, get_standard_language_servers
from core.lsp.jedi_provider import JediProvider, JEDI_AVAILABLE


logger = setup_logger(__name__)


class LSPManager(QObject):
    """Manages multiple language server clients for different languages."""

    # Signals
    diagnostics_received = Signal(str, list)  # (file_path, diagnostics)
    server_started = Signal(str)              # (language_id)
    server_stopped = Signal(str)              # (language_id)

    def __init__(self, event_bus):
        super().__init__()
        self.event_bus = event_bus
        self.clients: Dict[str, LSPClient] = {}
        self.configs = get_standard_language_servers()
        self.workspace_path: Optional[Path] = None
        self._jedi: Optional[JediProvider] = None

    def set_workspace(self, workspace_path: Path):
        """Set the workspace path and start appropriate servers."""
        self.workspace_path = workspace_path
        # Rebuild the in-process Python provider against the new root.
        self._jedi = None
        logger.info(f"Workspace set to: {workspace_path}")

    # ── In-process Python intelligence (jedi) ─────────────────────────────────
    def python_intelligence(self) -> JediProvider:
        """Return a jedi-backed provider for synchronous Python features.

        This needs no external server and works out of the box; when jedi is not
        installed the provider degrades to empty results (``.available`` False).
        """
        if self._jedi is None:
            root = str(self.workspace_path) if self.workspace_path else None
            self._jedi = JediProvider(root)
        return self._jedi

    @staticmethod
    def supports_inprocess(file_path) -> bool:
        """True for files the in-process provider (jedi → Python) can handle."""
        try:
            return Path(file_path).suffix in (".py", ".pyi")
        except Exception:
            return False

        
    def get_client_for_language(self, language_id: str) -> Optional[LSPClient]:
        """Get or create a client for the specified language."""
        if language_id in self.clients:
            return self.clients[language_id]
            
        if language_id not in self.configs:
            logger.warning(f"No language server configured for: {language_id}")
            return None
            
        config = self.configs[language_id]
        client = LSPClient(config)
        
        # Connect signals
        client.message_received.connect(lambda msg: self._on_server_message(language_id, msg))
        client.error_occurred.connect(lambda err: self._on_server_error(language_id, err))
        client.connection_closed.connect(lambda: self._on_server_closed(language_id))
        
        # Start client with workspace URI
        if self.workspace_path:
            root_uri = f"file:///{str(self.workspace_path.as_posix())}"
            if client.start(root_uri):
                self.clients[language_id] = client
                self.server_started.emit(language_id)
                return client
                
        return None
        
    def get_client_for_file(self, file_path: Path) -> Optional[LSPClient]:
        """Get a client appropriate for the given file based on extension."""
        for lang_id, config in self.configs.items():
            if file_path.suffix in config.supported_extensions:
                return self.get_client_for_language(lang_id)
        return None
        
    def open_document(self, file_path: Path, language_id: str, content: str):
        """Notify language server of an open document."""
        client = self.get_client_for_language(language_id)
        if client:
            uri = f"file:///{str(file_path.as_posix())}"
            client.send_notification("textDocument/didOpen", {
                "textDocument": {
                    "uri": uri,
                    "languageId": language_id,
                    "version": 1,
                    "text": content,
                }
            })
            
    def change_document(self, file_path: Path, content: str, version: int):
        """Notify language server of document changes."""
        client = self.get_client_for_file(file_path)
        if client:
            uri = f"file:///{str(file_path.as_posix())}"
            client.send_notification("textDocument/didChange", {
                "textDocument": {
                    "uri": uri,
                    "version": version,
                },
                "contentChanges": [{"text": content}],
            })
            
    def close_document(self, file_path: Path):
        """Notify language server that a document has closed."""
        client = self.get_client_for_file(file_path)
        if client:
            uri = f"file:///{str(file_path.as_posix())}"
            client.send_notification("textDocument/didClose", {
                "textDocument": {"uri": uri},
            })
            
    def save_document(self, file_path: Path, content: str):
        """Notify language server that a document was saved."""
        client = self.get_client_for_file(file_path)
        if client:
            uri = f"file:///{str(file_path.as_posix())}"
            client.send_notification("textDocument/didSave", {
                "textDocument": {"uri": uri},
                "text": content,
            })
            
    def request_completion(self, file_path: Path, line: int, character: int, callback):
        """Request completions from language server."""
        client = self.get_client_for_file(file_path)
        if client:
            uri = f"file:///{str(file_path.as_posix())}"
            client.send_request("textDocument/completion", {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
            }, callback)
            
    def request_hover(self, file_path: Path, line: int, character: int, callback):
        """Request hover information from language server."""
        client = self.get_client_for_file(file_path)
        if client:
            uri = f"file:///{str(file_path.as_posix())}"
            client.send_request("textDocument/hover", {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
            }, callback)
            
    def request_definition(self, file_path: Path, line: int, character: int, callback):
        """Request definition from language server."""
        client = self.get_client_for_file(file_path)
        if client:
            uri = f"file:///{str(file_path.as_posix())}"
            client.send_request("textDocument/definition", {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
            }, callback)
            
    def request_references(self, file_path: Path, line: int, character: int, callback):
        """Request references from language server."""
        client = self.get_client_for_file(file_path)
        if client:
            uri = f"file:///{str(file_path.as_posix())}"
            client.send_request("textDocument/references", {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
                "context": {"includeDeclaration": True},
            }, callback)
            
    def request_formatting(self, file_path: Path, callback):
        """Request document formatting from language server."""
        client = self.get_client_for_file(file_path)
        if client:
            uri = f"file:///{str(file_path.as_posix())}"
            client.send_request("textDocument/formatting", {
                "textDocument": {"uri": uri},
                "options": {
                    "tabSize": 4,
                    "insertSpaces": True,
                },
            }, callback)
            
    def _on_server_message(self, language_id: str, message: dict):
        """Handle messages from the language server."""
        method = message.get("method")
        if method == "textDocument/publishDiagnostics":
            uri = message["params"]["uri"]
            diagnostics = message["params"]["diagnostics"]
            # Convert file URI to path
            if uri.startswith("file:///"):
                file_path = uri[8:]
                self.diagnostics_received.emit(file_path, diagnostics)
                
    def _on_server_error(self, language_id: str, error: str):
        logger.error(f"Language server ({language_id}) error: {error}")
        
    def _on_server_closed(self, language_id: str):
        logger.info(f"Language server ({language_id}) closed")
        if language_id in self.clients:
            del self.clients[language_id]
            self.server_stopped.emit(language_id)
            
    def shutdown_all(self):
        """Shutdown all language servers."""
        for language_id, client in list(self.clients.items()):
            client.stop()
        self.clients.clear()

    def describe_state(self) -> dict:
        """A UI-friendly snapshot of language-server state.

        Used by the status bar's clickable LSP indicator to explain what is
        actually running: the workspace, each spawned server and whether it is
        alive, the in-process Python (jedi) fallback, and everything configured
        but not yet started.
        """
        servers = []
        for language_id, client in self.clients.items():
            cfg = getattr(client, "config", None)
            servers.append({
                "language": language_id,
                "name": getattr(cfg, "name", language_id),
                "running": bool(getattr(client, "running", False)),
            })
        try:
            jedi_ok = bool(self.python_intelligence().available)
        except Exception:
            jedi_ok = False
        return {
            "workspace": str(self.workspace_path) if self.workspace_path else None,
            "python_inprocess": jedi_ok,
            "servers": servers,
            "configured": sorted(self.configs.keys()),
        }

