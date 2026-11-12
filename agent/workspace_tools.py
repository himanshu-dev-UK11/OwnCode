"""
Consolidated Module: agent.workspace_tools

Combines: ai.tools.base_tool, ai.tools.tool_context, ai.tools.file_tool, ai.tools.editor_tool, ai.tools.search_tool, ai.tools.execution_tool, ai.tools.project_tool, ai.tools.browser_tool, ai.tools.tool_coordinator
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['ai.tools.base_tool', 'ai.tools.tool_context', 'ai.tools.file_tool', 'ai.tools.editor_tool', 'ai.tools.search_tool', 'ai.tools.execution_tool', 'ai.tools.project_tool', 'ai.tools.browser_tool', 'ai.tools.tool_coordinator', 'ai.tools.workspace_vfs', 'core.vfs', 'ai.tools.lsp_tool', 'ai.tools.tool_parser']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ai.tools.base_tool (ai/tools/base_tool.py)
# ============================================================================
"""
Base Tool for AI Agents

Defines the interface and common functionality for all AI tools.
"""

from typing import Any, Dict, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from core.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class ToolResult:
    """
    Standardized result from tool execution.
    
    Attributes:
        success: Whether the operation succeeded
        output: The primary output data
        error: Error message if failed
        metadata: Additional information
        requires_confirmation: If this needs user approval before proceeding
    """
    success: bool
    output: Any = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    requires_confirmation: bool = False
    
    def __str__(self) -> str:
        if self.success:
            return f"Success: {self.output}"
        return f"Error: {self.error}"


class BaseTool(ABC):
    """
    Base class for all AI tools.
    
    Tools provide capabilities to AI agents:
    - File operations (create, edit, delete)
    - Project management
    - Code execution
    - Search and analysis
    
    Each tool must implement:
    - name: Unique identifier
    - description: What the tool does
    - schema: JSON schema for parameters
    - execute: Main operation
    """
    
    def __init__(self, event_bus, workspace_root: Optional[str] = None):
        self.event_bus = event_bus
        self.workspace_root = workspace_root
        self.logger = logger
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name (e.g., 'file', 'project')."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""
        pass
    
    @property
    @abstractmethod
    def schema(self) -> Dict[str, Any]:
        """
        JSON schema describing the tool's parameters.
        
        Example:
        {
            "action": {
                "type": "string",
                "enum": ["create", "read", "update", "delete"],
                "description": "Operation to perform"
            },
            "path": {
                "type": "string",
                "description": "File path"
            }
        }
        """
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with the provided parameters.
        
        Args:
            **kwargs: Parameters matching the tool's schema
            
        Returns:
            ToolResult with success/failure and output
        """
        pass
    
    def validate_params(self, **kwargs) -> ToolResult:
        """
        Validate parameters against the schema.
        Override for custom validation.
        """
        required = {k: v for k, v in self.schema.items() 
                   if v.get('required', False)}
        
        missing = set(required.keys()) - set(kwargs.keys())
        if missing:
            return ToolResult(
                success=False,
                error=f"Missing required parameters: {', '.join(missing)}"
            )
        
        return ToolResult(success=True)
    
    def requires_confirmation(self, action: str, **kwargs) -> bool:
        """
        Check if this action requires user confirmation.
        Override in subclasses for specific logic.
        
        Default: Confirm destructive operations (delete, overwrite).
        """
        destructive_actions = {'delete', 'remove', 'rm', 'overwrite'}
        return action.lower() in destructive_actions
    
    def publish_event(self, event_name: str, data: Dict[str, Any]):
        """Publish event to the EventBus."""
        try:
            self.event_bus.publish(event_name, data)
        except Exception as e:
            self.logger.warning(f"Failed to publish event {event_name}: {e}")

# ============================================================================
# SECTION: ai.tools.tool_context (ai/tools/tool_context.py)
# ============================================================================
"""
Tool Context — v1.5

Context passed to every tool for context-aware execution.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class ToolContext:
    """
    Context passed to every tool for context-aware execution.
    
    Provides tools with project state information so they can
    make informed decisions and provide better results.
    """
    
    # Project information
    project_root: Optional[str] = None
    workspace: Optional[str] = None
    project_name: Optional[str] = None
    project_type: Optional[str] = None
    detected_language: Optional[str] = None
    detected_framework: Optional[str] = None
    
    # File information
    open_files: List[str] = field(default_factory=list)
    selected_text: Optional[str] = None
    current_file: Optional[str] = None
    cursor_position: Optional[Dict[str, Any]] = None  # {line, column}
    
    # Task information
    ai_task: Optional[str] = None
    task_id: Optional[str] = None
    task_type: Optional[str] = None  # coding, debugging, testing, etc.
    
    # Model information
    current_model: Optional[str] = None
    model_provider: Optional[str] = None
    
    # Intelligence
    project_intelligence: Optional[Dict[str, Any]] = None
    
    # Context metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "project_root": self.project_root,
            "workspace": self.workspace,
            "project_name": self.project_name,
            "project_type": self.project_type,
            "open_files": self.open_files[:5] if len(self.open_files) > 5 else self.open_files,
            "selected_text_length": len(self.selected_text) if self.selected_text else 0,
            "current_file": self.current_file,
            "cursor_position": self.cursor_position,
            "ai_task": self.ai_task,
            "current_model": self.current_model,
            "timestamp": self.timestamp.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolContext":
        """Create context from dictionary."""
        context = cls()
        
        context.project_root = data.get("project_root")
        context.workspace = data.get("workspace")
        context.project_name = data.get("project_name")
        context.project_type = data.get("project_type")
        context.detected_language = data.get("detected_language")
        context.detected_framework = data.get("detected_framework")
        context.open_files = data.get("open_files", [])
        context.selected_text = data.get("selected_text")
        context.current_file = data.get("current_file")
        context.cursor_position = data.get("cursor_position")
        context.ai_task = data.get("ai_task")
        context.task_id = data.get("task_id")
        context.task_type = data.get("task_type")
        context.current_model = data.get("current_model")
        context.model_provider = data.get("model_provider")
        context.project_intelligence = data.get("project_intelligence")
        
        if data.get("timestamp"):
            from datetime import datetime
            context.timestamp = datetime.fromisoformat(data["timestamp"])
        
        context.session_id = data.get("session_id")
        
        return context
    
    def merge(self, other: "ToolContext") -> None:
        """Merge another context into this one."""
        if other.project_root:
            self.project_root = other.project_root
        if other.workspace:
            self.workspace = other.workspace
        if other.project_name:
            self.project_name = other.project_name
        if other.project_type:
            self.project_type = other.project_type
        if other.detected_language:
            self.detected_language = other.detected_language
        if other.detected_framework:
            self.detected_framework = other.detected_framework
        if other.open_files:
            self.open_files = list(set(self.open_files + other.open_files))
        if other.selected_text:
            self.selected_text = other.selected_text
        if other.current_file:
            self.current_file = other.current_file
        if other.cursor_position:
            self.cursor_position = other.cursor_position
        if other.ai_task:
            self.ai_task = other.ai_task
        if other.task_id:
            self.task_id = other.task_id
        if other.task_type:
            self.task_type = other.task_type
        if other.current_model:
            self.current_model = other.current_model
        if other.model_provider:
            self.model_provider = other.model_provider
        if other.project_intelligence:
            self.project_intelligence = other.project_intelligence
        if other.timestamp:
            self.timestamp = other.timestamp
        if other.session_id:
            self.session_id = other.session_id


# ============================================================================
# SECTION: ai.tools.workspace_vfs (Sandboxed VFS & Live Buffer Bridge)
# ============================================================================
import ast as _vfs_ast
import fnmatch as _fnmatch
import os as _os
import re as _vfs_re
import threading as _threading
from pathlib import Path as _Path
from typing import Callable as _Callable, Dict as _Dict, Iterator as _Iterator, List as _List, Optional as _Optional, Set as _Set


class WorkspaceSecurityError(PermissionError):
    """Raised when a file operation attempts to escape the workspace sandbox."""


class WorkspaceVFS:
    DEFAULT_EXCLUDED_DIRS: _Set[str] = {
        ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
        "dist", "build", ".tox", ".mypy_cache", ".pytest_cache",
        ".idea", ".vscode", ".eggs", "target", ".next", ".nuxt", "coverage",
    }

    def __init__(self, workspace_root: _Optional[str] = None, event_bus=None) -> None:
        self._lock = _threading.RLock()
        self.event_bus = event_bus
        self._workspace_root: _Optional[_Path] = (
            _Path(workspace_root).resolve() if workspace_root else None
        )
        self._excluded_dirs: _Set[str] = set(self.DEFAULT_EXCLUDED_DIRS)
        self._gitignore_patterns: _List[str] = []
        self._buffer_getter: _Optional[_Callable[[str], _Optional[str]]] = None
        self._buffer_setter: _Optional[_Callable[[str, str], bool]] = None
        self._reload_gitignore()

    @property
    def workspace_root(self) -> _Optional[_Path]:
        return self._workspace_root

    def set_workspace_root(self, workspace_root: _Optional[str]) -> None:
        with self._lock:
            self._workspace_root = _Path(workspace_root).resolve() if workspace_root else None
            self._reload_gitignore()

    def register_editor_bridge(
        self,
        buffer_getter: _Optional[_Callable[[str], _Optional[str]]] = None,
        buffer_setter: _Optional[_Callable[[str, str], bool]] = None,
    ) -> None:
        with self._lock:
            self._buffer_getter = buffer_getter
            self._buffer_setter = buffer_setter

    def _reload_gitignore(self) -> None:
        self._gitignore_patterns.clear()
        if not self._workspace_root:
            return
        gi = self._workspace_root / ".gitignore"
        if gi.is_file():
            try:
                for raw in gi.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = raw.strip()
                    if line and not line.startswith("#") and not line.startswith("!"):
                        self._gitignore_patterns.append(line.rstrip("/"))
            except Exception:
                pass

    def resolve_path(self, user_path: str) -> _Path:
        return self.resolve_safe_path(user_path)

    def resolve_safe(self, user_path: str) -> _Path:
        return self.resolve_safe_path(user_path)

    def resolve_safe_path(self, user_path: str) -> _Path:
        if not user_path or "\x00" in str(user_path):
            raise WorkspaceSecurityError("Invalid or empty file path.")
        raw = _Path(str(user_path).strip())
        with self._lock:
            root = self._workspace_root
        if root is None:
            return raw.resolve()
        root_resolved = root.resolve()
        candidate = (root_resolved / raw).resolve() if not raw.is_absolute() else raw.resolve()
        try:
            candidate.relative_to(root_resolved)
        except ValueError as exc:
            raise WorkspaceSecurityError(
                f"Security violation: path '{user_path}' resolves to '{candidate}', "
                f"which is outside the workspace root '{root_resolved}'."
            ) from exc
        return candidate

    def iter_files(
        self,
        subpath: str = ".",
        extensions: _Optional[_List[str]] = None,
        max_files: int = 10000,
    ) -> _Iterator[_Path]:
        start_dir = self.resolve_safe_path(subpath)
        if not start_dir.exists() or not start_dir.is_dir():
            return
        ext_set = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in extensions} if extensions else None
        count = 0
        for root_str, dirs, files in _os.walk(str(start_dir), topdown=True, followlinks=False):
            dirs[:] = sorted(
                d for d in dirs
                if d not in self._excluded_dirs
                and not d.startswith(".git")
                and not any(_fnmatch.fnmatch(d, pat) for pat in self._gitignore_patterns)
            )
            root_path = _Path(root_str)
            for fname in sorted(files):
                if any(_fnmatch.fnmatch(fname, pat) for pat in self._gitignore_patterns):
                    continue
                fpath = root_path / fname
                if ext_set and fpath.suffix.lower() not in ext_set:
                    continue
                yield fpath
                count += 1
                if count >= max_files:
                    return

    def read_text(self, user_path: str) -> str:
        full_path = self.resolve_safe_path(user_path)
        key = str(full_path)
        with self._lock:
            getter = self._buffer_getter
        if callable(getter):
            try:
                live = getter(key)
                if live is not None:
                    return live
            except Exception:
                pass
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {user_path}")
        if full_path.is_dir():
            raise IsADirectoryError(f"Path is a directory, not a file: {user_path}")
        for enc in ("utf-8", "utf-8-sig", "utf-16", "latin-1"):
            try:
                return full_path.read_text(encoding=enc)
            except UnicodeDecodeError:
                continue
        raise UnicodeDecodeError("utf-8", b"", 0, 1, f"Cannot decode binary file: {user_path}")

    def write_text(self, user_path: str, content: str, create_backup: bool = True) -> _Path:
        full_path = self.resolve_safe_path(user_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        from core.system_managers import safe_write_text
        ok = safe_write_text(full_path, content or "", encoding="utf-8", create_backup=create_backup)
        if not ok:
            full_path.write_text(content or "", encoding="utf-8")
        key = str(full_path)
        with self._lock:
            setter = self._buffer_setter
        if callable(setter):
            try:
                setter(key, content or "")
            except Exception:
                pass
        if self.event_bus:
            try:
                self.event_bus.publish("vfs_file_updated", {"path": key, "content": content or ""})
                self.event_bus.publish("file_saved", {"path": key})
            except Exception:
                pass
        return full_path

    def read_range(
        self,
        user_path: str,
        start_line: int = 1,
        end_line: int = 200,
        with_line_numbers: bool = True,
    ) -> _Dict[str, object]:
        content = self.read_text(user_path)
        lines = content.splitlines()
        total = len(lines)
        s = max(1, int(start_line or 1))
        e = min(total, int(end_line or total)) if total > 0 else 0
        if total == 0 or s > total:
            return {"content": "", "raw_content": "", "start_line": s, "end_line": e, "total_lines": total}
        sliced = lines[s - 1 : e]
        formatted = "\n".join(f"{idx:4d} | {line}" for idx, line in enumerate(sliced, start=s)) if with_line_numbers else "\n".join(sliced)
        return {"content": formatted, "raw_content": "\n".join(sliced), "start_line": s, "end_line": e, "total_lines": total}

    def read_outline(self, user_path: str) -> _Dict[str, object]:
        full_path = self.resolve_safe_path(user_path)
        content = self.read_text(user_path)
        lines = content.splitlines()
        total_lines = len(lines)
        items: _List[_Dict[str, object]] = []

        if full_path.suffix.lower() == ".py":
            try:
                tree = _vfs_ast.parse(content)
                for node in tree.body:
                    if isinstance(node, _vfs_ast.ClassDef):
                        c_start = node.lineno
                        c_end = getattr(node, "end_lineno", c_start)
                        raw_doc = _vfs_ast.get_docstring(node) or ""
                        doc = raw_doc.splitlines()[0] if raw_doc else ""
                        methods = []
                        for sub in node.body:
                            if isinstance(sub, (_vfs_ast.FunctionDef, _vfs_ast.AsyncFunctionDef)):
                                args = [a.arg for a in sub.args.args]
                                methods.append({
                                    "name": sub.name,
                                    "signature": f"{sub.name}({', '.join(args)})",
                                    "start_line": sub.lineno,
                                    "end_line": getattr(sub, "end_lineno", sub.lineno),
                                })
                        items.append({
                            "type": "class",
                            "name": node.name,
                            "start_line": c_start,
                            "end_line": c_end,
                            "doc": doc[:120],
                            "methods": methods,
                        })
                    elif isinstance(node, (_vfs_ast.FunctionDef, _vfs_ast.AsyncFunctionDef)):
                        args = [a.arg for a in node.args.args]
                        raw_doc = _vfs_ast.get_docstring(node) or ""
                        doc = raw_doc.splitlines()[0] if raw_doc else ""
                        items.append({
                            "type": "function",
                            "name": node.name,
                            "signature": f"{node.name}({', '.join(args)})",
                            "start_line": node.lineno,
                            "end_line": getattr(node, "end_lineno", node.lineno),
                            "doc": doc[:120],
                        })
            except Exception:
                pass

        if not items:
            sym_re = _vfs_re.compile(
                r"^(\s*)(?:export\s+)?(?:public\s+|private\s+|protected\s+|static\s+|async\s+)*"
                r"(class|struct|interface|enum|def|fn|func|function)\s+([A-Za-z_][A-Za-z0-9_]*)"
            )
            for idx, ln in enumerate(lines, start=1):
                m = sym_re.match(ln)
                if m:
                    items.append({
                        "type": m.group(2),
                        "name": m.group(3),
                        "signature": ln.strip()[:100],
                        "start_line": idx,
                        "end_line": idx,
                    })

        summary_lines = [f"# Outline of {user_path} ({total_lines} lines)"]
        for it in items:
            if it["type"] == "class":
                doc_suffix = f" — {it['doc']}" if it.get("doc") else ""
                summary_lines.append(f"- class {it['name']} [L{it['start_line']}–L{it['end_line']}]{doc_suffix}")
                for m in it.get("methods", []):
                    summary_lines.append(f"    • def {m['signature']} [L{m['start_line']}–L{m['end_line']}]")
            else:
                sig = it.get("signature") or it["name"]
                doc_suffix = f" — {it['doc']}" if it.get("doc") else ""
                summary_lines.append(f"- {it['type']} {sig} [L{it['start_line']}–L{it['end_line']}]{doc_suffix}")

        return {"outline": "\n".join(summary_lines), "symbols": items, "total_lines": total_lines}

    def read_symbol(
        self,
        user_path: str,
        symbol_name: str,
        with_line_numbers: bool = True,
    ) -> _Dict[str, object]:
        if not symbol_name:
            raise ValueError("symbol_name is required for read_symbol")
        content = self.read_text(user_path)
        lines = content.splitlines()
        parts = [p.strip() for p in symbol_name.split(".") if p.strip()]
        target_name = parts[-1]
        parent_name = parts[0] if len(parts) > 1 else None

        try:
            tree = _vfs_ast.parse(content)
            for node in _vfs_ast.walk(tree):
                if parent_name and isinstance(node, _vfs_ast.ClassDef) and node.name == parent_name:
                    for sub in node.body:
                        if isinstance(sub, (_vfs_ast.FunctionDef, _vfs_ast.AsyncFunctionDef, _vfs_ast.ClassDef)) and sub.name == target_name:
                            s = sub.lineno
                            if getattr(sub, "decorator_list", None):
                                s = min(getattr(d, "lineno", s) for d in sub.decorator_list)
                            e = getattr(sub, "end_lineno", s)
                            return self.read_range(user_path, s, e, with_line_numbers=with_line_numbers)
                elif not parent_name and isinstance(node, (_vfs_ast.FunctionDef, _vfs_ast.AsyncFunctionDef, _vfs_ast.ClassDef)) and node.name == target_name:
                    s = node.lineno
                    if getattr(node, "decorator_list", None):
                        s = min(getattr(d, "lineno", s) for d in node.decorator_list)
                    e = getattr(node, "end_lineno", s)
                    return self.read_range(user_path, s, e, with_line_numbers=with_line_numbers)
        except Exception:
            pass

        pat = _vfs_re.compile(rf"^(\s*)(?:[\w\s]*?)\b{_vfs_re.escape(target_name)}\b")
        for idx, ln in enumerate(lines):
            m = pat.match(ln)
            if m:
                base_indent = len(m.group(1).expandtabs(4))
                end_idx = min(len(lines), idx + 80)
                for j in range(idx + 1, len(lines)):
                    stripped = lines[j].strip()
                    if not stripped:
                        continue
                    cur_indent = len((lines[j][: len(lines[j]) - len(lines[j].lstrip())]).expandtabs(4))
                    if cur_indent <= base_indent and not stripped.startswith((")", "}", "]")):
                        end_idx = j
                        break
                return self.read_range(user_path, idx + 1, end_idx, with_line_numbers=with_line_numbers)
        raise KeyError(f"Symbol '{symbol_name}' not found in {user_path}")


_GLOBAL_VFS: _Optional[WorkspaceVFS] = None


def get_workspace_vfs(workspace_root: _Optional[str] = None, event_bus=None) -> WorkspaceVFS:
    global _GLOBAL_VFS
    if _GLOBAL_VFS is None:
        _GLOBAL_VFS = WorkspaceVFS(workspace_root=workspace_root, event_bus=event_bus)
    else:
        if workspace_root is not None:
            _GLOBAL_VFS.set_workspace_root(workspace_root)
        if event_bus is not None and _GLOBAL_VFS.event_bus is None:
            _GLOBAL_VFS.event_bus = event_bus
    return _GLOBAL_VFS


# ============================================================================
# SECTION: ai.tools.file_tool (ai/tools/file_tool.py)
# ============================================================================
"""
File Tool for AI Agents

Provides comprehensive file and folder operations:
- Create files and folders
- Read file contents
- Update/modify files
- Delete files and folders (with confirmation)
- Move/rename files
- Copy files
"""

from pathlib import Path
from typing import Dict, Any, Optional
import shutil
from ai.tools.base_tool import BaseTool, ToolResult


class FileTool(BaseTool):
    """
    Complete file system operations for AI agents.
    
    Actions:
    - create: Create new file or folder
    - read: Read file contents
    - write: Write/overwrite file
    - update: Modify specific parts of file
    - delete: Remove file or folder (requires confirmation)
    - move: Move/rename file or folder
    - copy: Copy file or folder
    - exists: Check if path exists
    - list: List directory contents
    """
    
    @property
    def name(self) -> str:
        return "file"
    
    @property
    def description(self) -> str:
        return (
            "Perform file and folder operations. Can create, read, write, "
            "update, delete, move, and copy files. Deletions require user confirmation."
        )
    
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "action": {
                "type": "string",
                "enum": [
                    "create", "read", "read_range", "read_symbol", "read_outline",
                    "write", "update", "delete", "move", "copy", "exists", "list"
                ],
                "description": "Operation to perform",
                "required": True
            },
            "start_line": {"type": "integer", "description": "1-based start line"},
            "end_line": {"type": "integer", "description": "1-based end line"},
            "symbol_name": {"type": "string", "description": "Symbol name for read_symbol or AST update"},
            "path": {
                "type": "string",
                "description": "File or folder path (relative to workspace)",
                "required": True
            },
            "content": {
                "type": "string",
                "description": "Content for write/update operations"
            },
            "dest": {
                "type": "string",
                "description": "Destination path for move/copy operations"
            },
            "is_folder": {
                "type": "boolean",
                "description": "Create as folder (for create action)",
                "default": False
            },
            "old_text": {
                "type": "string",
                "description": "Text to find and replace (for update action)"
            },
            "new_text": {
                "type": "string",
                "description": "Replacement text (for update action)"
            },
            "confirmed": {
                "type": "boolean",
                "description": "User confirmed destructive operation",
                "default": False
            }
        }
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute file operation."""
        # Validate parameters
        validation = self.validate_params(**kwargs)
        if not validation.success:
            return validation
        
        action = kwargs.get('action')
        
        # Map actions to methods
        action_map = {
            'create': self._create,
            'read': self._read,
            'read_range': self._read_range,
            'read_symbol': self._read_symbol,
            'read_outline': self._read_outline,
            'write': self._write,
            'update': self._update,
            'delete': self._delete,
            'move': self._move,
            'copy': self._copy,
            'exists': self._exists,
            'list': self._list,
        }
        
        handler = action_map.get(action)
        if not handler:
            return ToolResult(
                success=False,
                error=f"Unknown action: {action}"
            )
        
        try:
            return handler(**kwargs)
        except Exception as e:
            self.logger.error(f"File tool error in {action}: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=str(e)
            )
    
    def _vfs(self) -> WorkspaceVFS:
        return get_workspace_vfs(self.workspace_root, self.event_bus)

    def _resolve_path(self, path: str) -> Path:
        return self._vfs().resolve_safe_path(path)
    
    def _create(self, path: str, is_folder: bool = False, content: str = "", **kwargs) -> ToolResult:
        full_path = self._resolve_path(path)
        if full_path.exists():
            return ToolResult(success=False, error=f"Path already exists: {path}")
        try:
            if is_folder:
                full_path.mkdir(parents=True, exist_ok=False)
                self.publish_event("file_created", {"path": str(full_path), "is_folder": True})
                return ToolResult(success=True, output=f"Folder created: {path}", metadata={"path": str(full_path), "type": "folder"})
            else:
                self._vfs().write_text(path, content or "", create_backup=False)
                self.publish_event("file_created", {"path": str(full_path), "is_folder": False})
                return ToolResult(success=True, output=f"File created: {path}", metadata={"path": str(full_path), "type": "file", "size": len(content or "")})
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to create: {e}")
    
    def _read(self, path: str, **kwargs) -> ToolResult:
        start_line = kwargs.get("start_line")
        end_line = kwargs.get("end_line")
        if start_line is not None or end_line is not None:
            return self._read_range(path=path, start_line=start_line or 1, end_line=end_line or 200, **kwargs)
        try:
            full_path = self._resolve_path(path)
            content = self._vfs().read_text(path)
            return ToolResult(success=True, output=content, metadata={"path": str(full_path), "size": len(content), "lines": content.count('\n') + 1})
        except WorkspaceSecurityError as se:
            return ToolResult(success=False, error=str(se))
        except FileNotFoundError:
            return ToolResult(success=False, error=f"File not found: {path}")
        except IsADirectoryError:
            return ToolResult(success=False, error=f"Path is a directory, not a file: {path}")
        except UnicodeDecodeError:
            return ToolResult(success=False, error=f"Cannot read file (binary or unsupported encoding): {path}")
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to read: {e}")

    def _read_range(self, path: str, start_line: int = 1, end_line: int = 200, **kwargs) -> ToolResult:
        try:
            full_path = self._resolve_path(path)
            info = self._vfs().read_range(path, start_line=int(start_line or 1), end_line=int(end_line or 200), with_line_numbers=bool(kwargs.get("with_line_numbers", True)))
            return ToolResult(success=True, output=info["content"], metadata={"path": str(full_path), "start_line": info["start_line"], "end_line": info["end_line"], "total_lines": info["total_lines"]})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _read_symbol(self, path: str, symbol_name: str = "", **kwargs) -> ToolResult:
        try:
            full_path = self._resolve_path(path)
            info = self._vfs().read_symbol(path, symbol_name=symbol_name, with_line_numbers=bool(kwargs.get("with_line_numbers", True)))
            return ToolResult(success=True, output=info["content"], metadata={"path": str(full_path), "symbol_name": symbol_name, "start_line": info["start_line"], "end_line": info["end_line"], "total_lines": info["total_lines"]})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _read_outline(self, path: str, **kwargs) -> ToolResult:
        try:
            full_path = self._resolve_path(path)
            info = self._vfs().read_outline(path)
            return ToolResult(success=True, output=info["outline"], metadata={"path": str(full_path), "symbols": info["symbols"], "total_lines": info["total_lines"]})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    def _write(self, path: str, content: str = "", **kwargs) -> ToolResult:
        full_path = self._resolve_path(path)
        if full_path.exists() and not kwargs.get('confirmed', False):
            return ToolResult(success=False, error=f"File exists: {path}. Set confirmed=True to overwrite.", requires_confirmation=True, metadata={"action": "overwrite", "path": str(full_path)})
        try:
            self._vfs().write_text(path, content or "", create_backup=True)
            return ToolResult(success=True, output=f"File written: {path}", metadata={"path": str(full_path), "size": len(content or "")})
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to write: {e}")
    
    def _update(self, path: str, old_text: str = None, new_text: str = None, content: str = None, **kwargs) -> ToolResult:
        full_path = self._resolve_path(path)
        if not full_path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")
        try:
            current_content = self._vfs().read_text(path)
            if old_text is not None and new_text is not None:
                from ai.editing.smart_patch_engine import SmartPatchEngine
                patch_res = SmartPatchEngine().apply_patch(
                    content=current_content,
                    old_text=old_text,
                    new_text=new_text,
                    start_line=kwargs.get("start_line"),
                    end_line=kwargs.get("end_line"),
                    symbol_name=kwargs.get("symbol_name"),
                    occurrence=kwargs.get("occurrence"),
                    replace_all=bool(kwargs.get("replace_all", False)),
                )
                if not patch_res.success:
                    return ToolResult(success=False, error=patch_res.error or f"Text not found in file: {old_text[:50]}...", metadata={"candidate_lines": patch_res.candidate_lines})
                new_content = patch_res.new_content
                replacements = patch_res.replacements
                stage_used = patch_res.stage_used
                matched_lines = (patch_res.matched_start_line, patch_res.matched_end_line)
            elif content is not None:
                new_content = current_content + content
                replacements = 0
                stage_used = "append"
                matched_lines = (current_content.count("\n") + 1, new_content.count("\n") + 1)
            else:
                return ToolResult(success=False, error="Must provide either (old_text + new_text) or content to append")
            self._vfs().write_text(path, new_content, create_backup=True)
            return ToolResult(
                success=True,
                output=f"File updated: {path} (matched via {stage_used} at lines {matched_lines[0]}–{matched_lines[1]})",
                metadata={
                    "path": str(full_path),
                    "replacements": replacements,
                    "stage_used": stage_used,
                    "matched_start_line": matched_lines[0],
                    "matched_end_line": matched_lines[1],
                    "old_size": len(current_content),
                    "new_size": len(new_content)
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to update: {e}")
    
    def _delete(self, path: str, confirmed: bool = False, **kwargs) -> ToolResult:
        """Delete file or folder with required confirmation."""
        full_path = self._resolve_path(path)
        
        if not full_path.exists():
            return ToolResult(
                success=False,
                error=f"Path not found: {path}"
            )
        
        # ALWAYS require confirmation for delete
        if not confirmed:
            is_dir = full_path.is_dir()
            item_type = "folder" if is_dir else "file"
            return ToolResult(
                success=False,
                error=f"Deletion requires confirmation. Set confirmed=True to delete this {item_type}: {path}",
                requires_confirmation=True,
                metadata={
                    "action": "delete",
                    "path": str(full_path),
                    "type": item_type
                }
            )
        
        try:
            if full_path.is_dir():
                shutil.rmtree(full_path)
                self.logger.info(f"Deleted folder: {path}")
            else:
                full_path.unlink()
                self.logger.info(f"Deleted file: {path}")
            
            self.publish_event("file_deleted", {"path": str(full_path)})
            return ToolResult(
                success=True,
                output=f"Deleted: {path}",
                metadata={"path": str(full_path)}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to delete: {e}")
    
    def _move(self, path: str, dest: str, **kwargs) -> ToolResult:
        """Move/rename file or folder."""
        full_path = self._resolve_path(path)
        dest_path = self._resolve_path(dest)
        
        if not full_path.exists():
            return ToolResult(
                success=False,
                error=f"Source not found: {path}"
            )
        
        if dest_path.exists():
            return ToolResult(
                success=False,
                error=f"Destination already exists: {dest}"
            )
        
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(full_path), str(dest_path))
            self.logger.info(f"Moved: {path} -> {dest}")
            self.publish_event("file_moved", {
                "source": str(full_path),
                "destination": str(dest_path)
            })
            return ToolResult(
                success=True,
                output=f"Moved: {path} -> {dest}",
                metadata={"source": str(full_path), "destination": str(dest_path)}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to move: {e}")
    
    def _copy(self, path: str, dest: str, **kwargs) -> ToolResult:
        """Copy file or folder."""
        full_path = self._resolve_path(path)
        dest_path = self._resolve_path(dest)
        
        if not full_path.exists():
            return ToolResult(
                success=False,
                error=f"Source not found: {path}"
            )
        
        if dest_path.exists():
            return ToolResult(
                success=False,
                error=f"Destination already exists: {dest}"
            )
        
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if full_path.is_dir():
                shutil.copytree(full_path, dest_path)
            else:
                shutil.copy2(full_path, dest_path)
            
            self.logger.info(f"Copied: {path} -> {dest}")
            self.publish_event("file_created", {"path": str(dest_path)})
            return ToolResult(
                success=True,
                output=f"Copied: {path} -> {dest}",
                metadata={"source": str(full_path), "destination": str(dest_path)}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to copy: {e}")
    
    def _exists(self, path: str, **kwargs) -> ToolResult:
        """Check if path exists."""
        full_path = self._resolve_path(path)
        exists = full_path.exists()
        
        metadata = {"path": str(full_path), "exists": exists}
        if exists:
            metadata["is_file"] = full_path.is_file()
            metadata["is_folder"] = full_path.is_dir()
            if full_path.is_file():
                metadata["size"] = full_path.stat().st_size
        
        return ToolResult(
            success=True,
            output=exists,
            metadata=metadata
        )
    
    def _list(self, path: str, **kwargs) -> ToolResult:
        """List directory contents."""
        full_path = self._resolve_path(path)
        
        if not full_path.exists():
            return ToolResult(
                success=False,
                error=f"Path not found: {path}"
            )
        
        if not full_path.is_dir():
            return ToolResult(
                success=False,
                error=f"Path is not a directory: {path}"
            )
        
        try:
            items = []
            for item in full_path.iterdir():
                items.append({
                    "name": item.name,
                    "path": str(item.relative_to(self.workspace_root) if self.workspace_root else item),
                    "is_file": item.is_file(),
                    "is_folder": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else None
                })
            
            return ToolResult(
                success=True,
                output=items,
                metadata={"path": str(full_path), "count": len(items)}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to list directory: {e}")

# ============================================================================
# SECTION: ai.tools.editor_tool (ai/tools/editor_tool.py)
# ============================================================================
"""
Editor Tool for AI Agents

Provides editor operations:
- Open files in editor
- Navigate to specific lines
- Get current editor state
- Format code
"""

from pathlib import Path
from typing import Dict, Any, Optional
from ai.tools.base_tool import BaseTool, ToolResult


class EditorTool(BaseTool):
    """
    Editor control operations for AI agents.
    
    Actions:
    - open: Open file in editor
    - goto: Navigate to line/position
    - current: Get current editor state
    - format: Format code
    - save: Save current file
    - close: Close file
    """
    
    @property
    def name(self) -> str:
        return "editor"
    
    @property
    def description(self) -> str:
        return "Control editor: open files, navigate, format, save"
    
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "action": {
                "type": "string",
                "enum": ["open", "goto", "current", "format", "save", "close"],
                "description": "Editor operation",
                "required": True
            },
            "path": {
                "type": "string",
                "description": "File path"
            },
            "line": {
                "type": "number",
                "description": "Line number to navigate to"
            },
            "column": {
                "type": "number",
                "description": "Column number"
            }
        }
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute editor operation."""
        validation = self.validate_params(**kwargs)
        if not validation.success:
            return validation
        
        action = kwargs.get('action')
        
        action_map = {
            'open': self._open_file,
            'goto': self._goto_position,
            'current': self._get_current,
            'format': self._format_code,
            'save': self._save_file,
            'close': self._close_file,
        }
        
        handler = action_map.get(action)
        if not handler:
            return ToolResult(
                success=False,
                error=f"Unknown action: {action}"
            )
        
        try:
            return handler(**kwargs)
        except Exception as e:
            self.logger.error(f"Editor tool error in {action}: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=str(e)
            )
    
    def _open_file(self, path: str, line: int = None, **kwargs) -> ToolResult:
        """Open file in editor."""
        file_path = Path(self.workspace_root) / path if self.workspace_root else Path(path)
        
        if not file_path.exists():
            return ToolResult(
                success=False,
                error=f"File not found: {path}"
            )
        
        # Publish event to open file
        event_data = {"path": str(file_path)}
        if line is not None:
            event_data["line"] = line
        
        self.publish_event("file_open_requested", event_data)
        
        return ToolResult(
            success=True,
            output=f"Opening file: {path}",
            metadata={"path": str(file_path), "line": line}
        )
    
    def _goto_position(self, path: str, line: int, column: int = 0, **kwargs) -> ToolResult:
        """Navigate to specific position."""
        file_path = Path(self.workspace_root) / path if self.workspace_root else Path(path)
        
        self.publish_event("editor_goto_position", {
            "path": str(file_path),
            "line": line,
            "column": column
        })
        
        return ToolResult(
            success=True,
            output=f"Navigating to {path}:{line}:{column}",
            metadata={"path": str(file_path), "line": line, "column": column}
        )
    
    def _get_current(self, **kwargs) -> ToolResult:
        """Get current editor state."""
        # This would query the editor manager for current state
        self.publish_event("editor_state_requested", {})
        
        return ToolResult(
            success=True,
            output="Current editor state requested",
            metadata={"action": "state_query"}
        )
    
    def _format_code(self, path: str = None, **kwargs) -> ToolResult:
        """Format code in file."""
        if path:
            file_path = Path(self.workspace_root) / path if self.workspace_root else Path(path)
            self.publish_event("format_file_requested", {"path": str(file_path)})
        else:
            self.publish_event("format_current_requested", {})
        
        return ToolResult(
            success=True,
            output=f"Formatting {path or 'current file'}",
            metadata={"path": path}
        )
    
    def _save_file(self, path: str = None, **kwargs) -> ToolResult:
        """Save file."""
        if path:
            file_path = Path(self.workspace_root) / path if self.workspace_root else Path(path)
            self.publish_event("request_save_file", {"path": str(file_path)})
        else:
            self.publish_event("request_save_current", {})
        
        return ToolResult(
            success=True,
            output=f"Saving {path or 'current file'}",
            metadata={"path": path}
        )
    
    def _close_file(self, path: str, **kwargs) -> ToolResult:
        """Close file."""
        file_path = Path(self.workspace_root) / path if self.workspace_root else Path(path)
        
        self.publish_event("request_close_file", {"path": str(file_path)})
        
        return ToolResult(
            success=True,
            output=f"Closing file: {path}",
            metadata={"path": str(file_path)}
        )

# ============================================================================
# SECTION: ai.tools.search_tool (ai/tools/search_tool.py)
# ============================================================================
"""
Search Tool for AI Agents

Provides search and query operations:
- Search in files
- Find by pattern
- Search symbols
- Find references
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import re
from ai.tools.base_tool import BaseTool, ToolResult


class SearchTool(BaseTool):
    """
    Search and query operations for AI agents.
    
    Actions:
    - find: Find files by name pattern
    - search: Search text in files
    - symbols: Find code symbols
    - references: Find symbol references
    """
    
    @property
    def name(self) -> str:
        return "search"
    
    @property
    def description(self) -> str:
        return "Search files, text, symbols, and references in the project"
    
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "action": {
                "type": "string",
                "enum": ["find", "search", "symbols", "references"],
                "description": "Search operation",
                "required": True
            },
            "query": {
                "type": "string",
                "description": "Search query or pattern",
                "required": True
            },
            "path": {
                "type": "string",
                "description": "Path to search in (default: workspace root)"
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Case-sensitive search",
                "default": False
            },
            "regex": {
                "type": "boolean",
                "description": "Use regex for search",
                "default": False
            },
            "extensions": {
                "type": "array",
                "description": "File extensions to include (e.g., ['.py', '.js'])"
            },
            "max_results": {
                "type": "number",
                "description": "Maximum results to return",
                "default": 100
            }
        }
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute search operation."""
        validation = self.validate_params(**kwargs)
        if not validation.success:
            return validation
        
        action = kwargs.get('action')
        
        action_map = {
            'find': self._find_files,
            'search': self._search_text,
            'symbols': self._search_symbols,
            'references': self._find_references,
        }
        
        handler = action_map.get(action)
        if not handler:
            return ToolResult(
                success=False,
                error=f"Unknown action: {action}"
            )
        
        try:
            return handler(**kwargs)
        except Exception as e:
            self.logger.error(f"Search tool error in {action}: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=str(e)
            )
    
    def _find_files(self, query: str, path: str = ".", extensions: List[str] = None,
                    max_results: int = 100, **kwargs) -> ToolResult:
        """Find files by name pattern."""
        search_path = Path(self.workspace_root) / path if self.workspace_root else Path(path)
        
        if not search_path.exists():
            return ToolResult(
                success=False,
                error=f"Path not found: {path}"
            )
        
        try:
            results = []
            pattern = re.compile(query, re.IGNORECASE)
            
            vfs = get_workspace_vfs(self.workspace_root, self.event_bus)
            search_path = vfs.resolve_safe_path(path)
            for item in vfs.iter_files(path, extensions=extensions):
                if len(results) >= max_results:
                    break
                if pattern.search(item.name):
                    rel_path = item.relative_to(search_path)
                    results.append({"path": str(rel_path), "name": item.name, "size": item.stat().st_size})
            
            return ToolResult(
                success=True,
                output=results,
                metadata={
                    "query": query,
                    "count": len(results),
                    "truncated": len(results) >= max_results
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to find files: {e}"
            )
    
    def _search_text(self, query: str, path: str = ".", case_sensitive: bool = False,
                     regex: bool = False, extensions: List[str] = None,
                     max_results: int = 100, **kwargs) -> ToolResult:
        """Search for text in files."""
        search_path = Path(self.workspace_root) / path if self.workspace_root else Path(path)
        
        if not search_path.exists():
            return ToolResult(
                success=False,
                error=f"Path not found: {path}"
            )
        
        try:
            results = []
            
            # Compile pattern
            flags = 0 if case_sensitive else re.IGNORECASE
            if regex:
                try:
                    pattern = re.compile(query, flags)
                except re.error as e:
                    return ToolResult(
                        success=False,
                        error=f"Invalid regex pattern: {e}"
                    )
            else:
                pattern = re.compile(re.escape(query), flags)
            
            vfs = get_workspace_vfs(self.workspace_root, self.event_bus)
            search_path = vfs.resolve_safe_path(path)
            for item in vfs.iter_files(path, extensions=extensions):
                if len(results) >= max_results:
                    break
                try:
                    content = item.read_text(encoding='utf-8')
                except (UnicodeDecodeError, PermissionError, OSError):
                    continue
                
                # Find matches
                for line_num, line in enumerate(content.splitlines(), start=1):
                    if len(results) >= max_results:
                        break
                    
                    match = pattern.search(line)
                    if match:
                        rel_path = item.relative_to(search_path)
                        results.append({
                            "file": str(rel_path),
                            "line": line_num,
                            "text": line.strip(),
                            "match": match.group(0)
                        })
            
            return ToolResult(
                success=True,
                output=results,
                metadata={
                    "query": query,
                    "count": len(results),
                    "truncated": len(results) >= max_results
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to search text: {e}"
            )
    
    def _search_symbols(self, query: str, **kwargs) -> ToolResult:
        """Search for code symbols (functions, classes, etc.)."""
        # Placeholder - would integrate with LSP or symbol index
        return ToolResult(
            success=True,
            output=[],
            metadata={"query": query, "note": "Symbol search not yet implemented"}
        )
    
    def _find_references(self, query: str, **kwargs) -> ToolResult:
        """Find references to a symbol."""
        # Placeholder - would integrate with LSP
        return ToolResult(
            success=True,
            output=[],
            metadata={"query": query, "note": "Reference finding not yet implemented"}
        )

# ============================================================================
# SECTION: ai.tools.execution_tool (ai/tools/execution_tool.py)
# ============================================================================
"""
Execution Tool for AI Agents

Provides code execution and terminal operations:
- Run shell commands
- Execute scripts
- Install packages
- Test code
"""

from pathlib import Path
from typing import Dict, Any, Optional
import subprocess
import threading
from ai.tools.base_tool import BaseTool, ToolResult


_HIDDEN_CONSOLE_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class ExecutionTool(BaseTool):
    """
    Execute code and commands for AI agents.
    
    Actions:
    - run: Run shell command
    - execute: Execute script file
    - test: Run tests
    - install: Install package
    """
    
    def __init__(self, event_bus, workspace_root: Optional[str] = None):
        super().__init__(event_bus, workspace_root)
        self._running_processes = {}
    
    @property
    def name(self) -> str:
        return "execute"
    
    @property
    def description(self) -> str:
        return "Execute shell commands, scripts, tests, and install packages"
    
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "action": {
                "type": "string",
                "enum": ["run", "execute", "test", "install"],
                "description": "Execution action",
                "required": True
            },
            "command": {
                "type": "string",
                "description": "Shell command to run"
            },
            "script": {
                "type": "string",
                "description": "Script file to execute"
            },
            "package": {
                "type": "string",
                "description": "Package name to install"
            },
            "timeout": {
                "type": "number",
                "description": "Execution timeout in seconds",
                "default": 30
            },
            "cwd": {
                "type": "string",
                "description": "Working directory"
            }
        }
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute operation."""
        validation = self.validate_params(**kwargs)
        if not validation.success:
            return validation
        
        action = kwargs.get('action')
        
        action_map = {
            'run': self._run_command,
            'execute': self._execute_script,
            'test': self._run_tests,
            'install': self._install_package,
        }
        
        handler = action_map.get(action)
        if not handler:
            return ToolResult(
                success=False,
                error=f"Unknown action: {action}"
            )
        
        try:
            return handler(**kwargs)
        except Exception as e:
            self.logger.error(f"Execution tool error in {action}: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=str(e)
            )
    
    def _run_command(self, command: str, timeout: int = 30, cwd: str = None, **kwargs) -> ToolResult:
        """Run shell command."""
        work_dir = None
        if cwd:
            work_dir = Path(self.workspace_root) / cwd if self.workspace_root else Path(cwd)
        elif self.workspace_root:
            work_dir = Path(self.workspace_root)
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(work_dir) if work_dir else None,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=_HIDDEN_CONSOLE_FLAGS,
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]: {result.stderr}"
            
            self.logger.info(f"Executed command: {command} (exit code: {result.returncode})")
            
            return ToolResult(
                success=result.returncode == 0,
                output=output,
                error=result.stderr if result.returncode != 0 else None,
                metadata={
                    "command": command,
                    "exit_code": result.returncode,
                    "cwd": str(work_dir) if work_dir else None
                }
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                error=f"Command timed out after {timeout} seconds: {command}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to execute command: {e}"
            )
    
    def _execute_script(self, script: str, timeout: int = 30, **kwargs) -> ToolResult:
        """Execute a script file."""
        script_path = Path(self.workspace_root) / script if self.workspace_root else Path(script)
        
        if not script_path.exists():
            return ToolResult(
                success=False,
                error=f"Script not found: {script}"
            )
        
        # Determine interpreter based on extension
        ext = script_path.suffix.lower()
        interpreters = {
            '.py': 'python',
            '.js': 'node',
            '.sh': 'bash',
            '.rb': 'ruby',
            '.php': 'php',
        }
        
        interpreter = interpreters.get(ext)
        if not interpreter:
            return ToolResult(
                success=False,
                error=f"Unknown script type: {ext}"
            )
        
        command = f"{interpreter} {script_path}"
        return self._run_command(command, timeout=timeout, **kwargs)
    
    def _run_tests(self, command: str = None, **kwargs) -> ToolResult:
        """Run project tests."""
        if not command:
            # Auto-detect test command
            if self.workspace_root:
                project_path = Path(self.workspace_root)
                if (project_path / "package.json").exists():
                    command = "npm test"
                elif (project_path / "pytest.ini").exists() or (project_path / "setup.py").exists():
                    command = "pytest"
                elif (project_path / "Cargo.toml").exists():
                    command = "cargo test"
                else:
                    return ToolResult(
                        success=False,
                        error="Could not detect test framework. Please specify test command."
                    )
        
        return self._run_command(command, timeout=60, **kwargs)
    
    def _install_package(self, package: str, **kwargs) -> ToolResult:
        """Install a package."""
        if not package:
            return ToolResult(
                success=False,
                error="Package name required"
            )
        
        # Auto-detect package manager
        command = None
        if self.workspace_root:
            project_path = Path(self.workspace_root)
            if (project_path / "package.json").exists():
                command = f"npm install {package}"
            elif (project_path / "requirements.txt").exists():
                command = f"pip install {package}"
            elif (project_path / "Cargo.toml").exists():
                command = f"cargo add {package}"
        
        if not command:
            # Default to pip
            command = f"pip install {package}"
        
        return self._run_command(command, timeout=300, **kwargs)

# ============================================================================
# SECTION: ai.tools.project_tool (ai/tools/project_tool.py)
# ============================================================================
"""
Project Tool for AI Agents

Provides project-level operations:
- Create new projects from templates
- Initialize project structures
- Manage project dependencies
- Analyze project structure
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import json
from ai.tools.base_tool import BaseTool, ToolResult


class ProjectTool(BaseTool):
    """
    Project management operations for AI agents.
    
    Actions:
    - create: Create new project from template
    - init: Initialize project structure
    - analyze: Analyze project metadata
    - dependencies: Manage project dependencies
    """
    
    @property
    def name(self) -> str:
        return "project"
    
    @property
    def description(self) -> str:
        return "Manage projects: create, initialize, analyze structure, manage dependencies"
    
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "action": {
                "type": "string",
                "enum": ["create", "init", "analyze", "dependencies"],
                "description": "Project operation to perform",
                "required": True
            },
            "name": {
                "type": "string",
                "description": "Project name"
            },
            "template": {
                "type": "string",
                "description": "Template to use (python, javascript, react, django, etc.)"
            },
            "path": {
                "type": "string",
                "description": "Project path"
            },
            "structure": {
                "type": "object",
                "description": "Custom project structure (folders and files)"
            }
        }
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute project operation."""
        validation = self.validate_params(**kwargs)
        if not validation.success:
            return validation
        
        action = kwargs.get('action')
        
        action_map = {
            'create': self._create_project,
            'init': self._init_structure,
            'analyze': self._analyze_project,
            'dependencies': self._manage_dependencies,
        }
        
        handler = action_map.get(action)
        if not handler:
            return ToolResult(
                success=False,
                error=f"Unknown action: {action}"
            )
        
        try:
            return handler(**kwargs)
        except Exception as e:
            self.logger.error(f"Project tool error in {action}: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=str(e)
            )
    
    def _create_project(self, name: str, template: str = "python", **kwargs) -> ToolResult:
        """Create a new project from template."""
        if not self.workspace_root:
            return ToolResult(success=False, error="No workspace root set")
        
        project_path = Path(self.workspace_root) / name
        
        if project_path.exists():
            return ToolResult(
                success=False,
                error=f"Project already exists: {name}"
            )
        
        try:
            # Create project directory
            project_path.mkdir(parents=True)
            
            # Apply template
            structure = self._get_template_structure(template)
            self._create_structure(project_path, structure)
            
            self.logger.info(f"Created project: {name} using template: {template}")
            self.publish_event("project_created", {
                "path": str(project_path),
                "name": name,
                "template": template
            })
            
            return ToolResult(
                success=True,
                output=f"Project created: {name}",
                metadata={
                    "path": str(project_path),
                    "template": template,
                    "files": len(structure.get('files', [])),
                    "folders": len(structure.get('folders', []))
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to create project: {e}")
    
    def _init_structure(self, path: str, structure: Dict[str, Any], **kwargs) -> ToolResult:
        """Initialize custom project structure."""
        base_path = Path(self.workspace_root) / path if self.workspace_root else Path(path)
        
        try:
            base_path.mkdir(parents=True, exist_ok=True)
            created = self._create_structure(base_path, structure)
            
            self.logger.info(f"Initialized structure at: {path}")
            return ToolResult(
                success=True,
                output=f"Structure initialized at: {path}",
                metadata={"path": str(base_path), "created": created}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to initialize structure: {e}")
    
    def _analyze_project(self, path: str = ".", **kwargs) -> ToolResult:
        """Analyze project metadata and structure."""
        project_path = Path(self.workspace_root) / path if self.workspace_root else Path(path)
        
        if not project_path.exists():
            return ToolResult(success=False, error=f"Project not found: {path}")
        
        try:
            analysis = {
                "name": project_path.name,
                "path": str(project_path),
                "type": self._detect_project_type(project_path),
                "files": self._count_files(project_path),
                "folders": self._count_folders(project_path),
                "size": self._calculate_size(project_path),
                "languages": self._detect_languages(project_path),
            }
            
            return ToolResult(
                success=True,
                output=analysis,
                metadata=analysis
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to analyze project: {e}")
    
    def _manage_dependencies(self, action: str = "list", **kwargs) -> ToolResult:
        """Manage project dependencies."""
        # Placeholder for dependency management
        return ToolResult(
            success=True,
            output="Dependency management not yet implemented",
            metadata={"action": action}
        )
    
    def _get_template_structure(self, template: str) -> Dict[str, Any]:
        """Get predefined project structure for template."""
        templates = {
            "python": {
                "folders": ["src", "tests", "docs"],
                "files": {
                    "README.md": f"# Python Project\n\nA Python project.\n",
                    "requirements.txt": "",
                    ".gitignore": "__pycache__/\n*.py[cod]\n*$py.class\n.venv/\n",
                    "src/__init__.py": "",
                    "tests/__init__.py": "",
                }
            },
            "javascript": {
                "folders": ["src", "tests", "public"],
                "files": {
                    "README.md": "# JavaScript Project\n\nA JavaScript project.\n",
                    "package.json": json.dumps({
                        "name": "project",
                        "version": "1.0.0",
                        "main": "src/index.js"
                    }, indent=2),
                    ".gitignore": "node_modules/\n.env\ndist/\n",
                    "src/index.js": "console.log('Hello World!');\n",
                }
            },
            "react": {
                "folders": ["src", "public"],
                "files": {
                    "README.md": "# React Project\n\nA React application.\n",
                    "package.json": json.dumps({
                        "name": "react-app",
                        "version": "1.0.0",
                        "dependencies": {
                            "react": "^18.0.0",
                            "react-dom": "^18.0.0"
                        }
                    }, indent=2),
                    ".gitignore": "node_modules/\n.env\nbuild/\n",
                    "src/App.js": "import React from 'react';\n\nfunction App() {\n  return <div>Hello React!</div>;\n}\n\nexport default App;\n",
                    "src/index.js": "import React from 'react';\nimport ReactDOM from 'react-dom';\nimport App from './App';\n\nReactDOM.render(<App />, document.getElementById('root'));\n",
                    "public/index.html": "<!DOCTYPE html>\n<html>\n<head>\n  <title>React App</title>\n</head>\n<body>\n  <div id=\"root\"></div>\n</body>\n</html>\n",
                }
            },
        }
        
        return templates.get(template, templates["python"])
    
    def _create_structure(self, base_path: Path, structure: Dict[str, Any]) -> int:
        """Create folder and file structure."""
        created = 0
        
        # Create folders
        for folder in structure.get('folders', []):
            folder_path = base_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)
            created += 1
        
        # Create files
        for file_path, content in structure.get('files', {}).items():
            full_path = base_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding='utf-8')
            created += 1
        
        return created
    
    def _detect_project_type(self, path: Path) -> str:
        """Detect project type based on files."""
        if (path / "package.json").exists():
            return "javascript/node"
        elif (path / "requirements.txt").exists() or (path / "setup.py").exists():
            return "python"
        elif (path / "Cargo.toml").exists():
            return "rust"
        elif (path / "pom.xml").exists():
            return "java/maven"
        elif (path / "go.mod").exists():
            return "go"
        return "unknown"
    
    def _count_files(self, path: Path) -> int:
        """Count files in project."""
        count = 0
        for item in path.rglob('*'):
            if item.is_file():
                count += 1
        return count
    
    def _count_folders(self, path: Path) -> int:
        """Count folders in project."""
        count = 0
        for item in path.rglob('*'):
            if item.is_dir():
                count += 1
        return count
    
    def _calculate_size(self, path: Path) -> int:
        """Calculate total project size in bytes."""
        total = 0
        for item in path.rglob('*'):
            if item.is_file():
                total += item.stat().st_size
        return total
    
    def _detect_languages(self, path: Path) -> List[str]:
        """Detect programming languages used."""
        extensions = set()
        for item in path.rglob('*'):
            if item.is_file() and item.suffix:
                extensions.add(item.suffix)
        
        lang_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.rs': 'Rust',
            '.go': 'Go',
            '.rb': 'Ruby',
            '.php': 'PHP',
        }
        
        languages = [lang_map.get(ext) for ext in extensions if ext in lang_map]
        return list(set(languages))

# ============================================================================
# SECTION: ai.tools.browser_tool (ai/tools/browser_tool.py)
# ============================================================================
"""
Web search tool.
"""

from ai.tools.base_tool import BaseTool

class BrowserTool(BaseTool):
    def __init__(self):
        super().__init__("browser")
        
    def search(self, query: str) -> list:
        self.logger.info(f"Searching web for: {query}")
        return []


# ============================================================================
# SECTION: ai.tools.lsp_tool & ai.tools.tool_parser
# ============================================================================
import ast as _lsp_ast
import json as _parser_json


class LspTool(BaseTool):
    @property
    def name(self) -> str:
        return "lsp"

    @property
    def description(self) -> str:
        return "Query code intelligence and diagnostics: diagnostics, definition, references, symbols."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "action": {"type": "string", "enum": ["diagnostics", "definition", "references", "symbols"], "required": True},
            "path": {"type": "string"},
            "symbol": {"type": "string"},
        }

    def execute(self, **kwargs) -> ToolResult:
        validation = self.validate_params(**kwargs)
        if not validation.success:
            return validation
        action = kwargs.get("action")
        try:
            if action == "diagnostics":
                return self._diagnostics(kwargs.get("path"))
            elif action == "symbols":
                return self._symbols(kwargs.get("path"))
            elif action == "definition":
                return self._definition(kwargs.get("symbol", ""), kwargs.get("path"))
            elif action == "references":
                return self._references(kwargs.get("symbol", ""), kwargs.get("path"))
            return ToolResult(success=False, error=f"Unknown lsp action: {action}")
        except Exception as exc:
            return ToolResult(success=False, error=f"LspTool error: {exc}")

    def _diagnostics(self, path: Optional[str] = None) -> ToolResult:
        vfs = get_workspace_vfs(self.workspace_root, self.event_bus)
        targets = [vfs.resolve_safe_path(path)] if path else list(vfs.iter_files(".", extensions=[".py"], max_files=200))
        diagnostics: List[Dict[str, Any]] = []
        for fpath in targets:
            try:
                rel = str(fpath.relative_to(vfs.workspace_root)) if vfs.workspace_root else str(fpath)
            except ValueError:
                rel = str(fpath)
            try:
                content = vfs.read_text(rel)
            except Exception as e:
                diagnostics.append({"file": rel, "line": 1, "col": 1, "severity": "error", "message": str(e)})
                continue
            if fpath.suffix.lower() == ".py":
                try:
                    tree = _lsp_ast.parse(content, filename=rel)
                    self._check_python_ast_warnings(tree, rel, diagnostics)
                except SyntaxError as syn:
                    lineno = int(syn.lineno or 1)
                    col = int(syn.offset or 1)
                    lines = content.splitlines()
                    offending = lines[lineno - 1].strip() if 1 <= lineno <= len(lines) else ""
                    diagnostics.append({
                        "file": rel,
                        "line": lineno,
                        "col": col,
                        "severity": "error",
                        "message": f"SyntaxError: {syn.msg}",
                        "code_line": offending,
                    })
        return ToolResult(
            success=True,
            output=diagnostics,
            metadata={"error_count": sum(1 for d in diagnostics if d["severity"] == "error"), "total": len(diagnostics)},
        )

    @staticmethod
    def _check_python_ast_warnings(tree: _lsp_ast.AST, rel: str, out: List[Dict[str, Any]]) -> None:
        for node in _lsp_ast.walk(tree):
            if isinstance(node, (_lsp_ast.Module, _lsp_ast.ClassDef)):
                seen_defs: Dict[str, int] = {}
                for child in node.body:
                    if isinstance(child, (_lsp_ast.FunctionDef, _lsp_ast.AsyncFunctionDef)):
                        if child.name in seen_defs:
                            out.append({
                                "file": rel,
                                "line": child.lineno,
                                "col": child.col_offset + 1,
                                "severity": "warning",
                                "message": f"Duplicate definition of '{child.name}' (first defined at line {seen_defs[child.name]})",
                            })
                        else:
                            seen_defs[child.name] = child.lineno

    def _symbols(self, path: Optional[str]) -> ToolResult:
        if not path:
            return ToolResult(success=False, error="Parameter 'path' is required")
        vfs = get_workspace_vfs(self.workspace_root, self.event_bus)
        info = vfs.read_outline(path)
        return ToolResult(success=True, output=info["outline"], metadata={"symbols": info["symbols"]})

    def _definition(self, symbol: str, path: Optional[str] = None) -> ToolResult:
        if not symbol:
            return ToolResult(success=False, error="Parameter 'symbol' is required")
        from ai.context.symbol_index import SymbolIndex
        vfs = get_workspace_vfs(self.workspace_root, self.event_bus)
        idx = SymbolIndex()
        matches: List[Dict[str, Any]] = []
        target_name = symbol.split(".")[-1].strip()
        files = [vfs.resolve_safe_path(path)] if path else list(vfs.iter_files(".", max_files=500))
        for f in files:
            for s in idx.index_file(str(f)):
                if s.name == target_name or s.name.lower() == target_name.lower():
                    try:
                        rel = str(f.relative_to(vfs.workspace_root)) if vfs.workspace_root else str(f)
                    except ValueError:
                        rel = str(f)
                    matches.append({"name": s.name, "kind": s.kind, "file": rel, "line": s.line, "parent": getattr(s, "parent", "")})
        return ToolResult(success=True, output=matches, metadata={"count": len(matches)})

    def _references(self, symbol: str, path: Optional[str] = None) -> ToolResult:
        if not symbol:
            return ToolResult(success=False, error="Parameter 'symbol' is required")
        vfs = get_workspace_vfs(self.workspace_root, self.event_bus)
        target_name = symbol.split(".")[-1].strip()
        pat = re.compile(rf"\b{re.escape(target_name)}\b")
        refs: List[Dict[str, Any]] = []
        files = [vfs.resolve_safe_path(path)] if path else list(vfs.iter_files(".", max_files=500))
        for f in files:
            try:
                rel = str(f.relative_to(vfs.workspace_root)) if vfs.workspace_root else str(f)
            except ValueError:
                rel = str(f)
            try:
                text = vfs.read_text(rel)
            except Exception:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if pat.search(line):
                    refs.append({"file": rel, "line": lineno, "text": line.strip()[:140]})
                    if len(refs) >= 100:
                        return ToolResult(success=True, output=refs, metadata={"count": len(refs), "truncated": True})
        return ToolResult(success=True, output=refs, metadata={"count": len(refs), "truncated": False})


class GitWorkspaceTool(BaseTool):
    @property
    def name(self) -> str:
        return "git"

    @property
    def description(self) -> str:
        return "Inspect Git repository state: status, diff, log, and branch."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "action": {"type": "string", "enum": ["status", "diff", "log", "branch"], "required": True},
            "path": {"type": "string"},
        }

    def execute(self, **kwargs) -> ToolResult:
        validation = self.validate_params(**kwargs)
        if not validation.success:
            return validation
        from ai.tools.git_tool import GitTool
        gt = GitTool(repo_path=self.workspace_root or ".")
        res = gt.execute(**kwargs)
        return ToolResult(success=res.success, output=res.output, error=res.error, metadata=res.metadata)


class ToolCallParser:
    _XML_TOOL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL | re.IGNORECASE)
    _FENCED_TOOL_RE = re.compile(r"```(?:tool_call|tool|function_call)\s*\n(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
    _REACT_RE = re.compile(r"Action\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*\nAction\s+Input\s*:\s*(\{.*?\})", re.DOTALL | re.IGNORECASE)

    @classmethod
    def parse_tool_calls(cls, raw: Any) -> List[Dict[str, Any]]:
        if not raw:
            return []
        if isinstance(raw, list):
            out = []
            for item in raw:
                out.extend(cls.parse_tool_calls(item))
            return out
        if isinstance(raw, dict):
            fn = raw.get("function") or raw
            name = fn.get("name") or raw.get("tool") or raw.get("name")
            args = fn.get("arguments") or raw.get("parameters") or raw.get("params") or {}
            if isinstance(args, str):
                try:
                    args = _parser_json.loads(args)
                except Exception:
                    args = {}
            if name and isinstance(args, dict):
                return [{"name": str(name).strip(), "parameters": args}]
            return []

        text = str(raw)
        calls: List[Dict[str, Any]] = []
        for m in cls._XML_TOOL_RE.finditer(text):
            parsed = cls._try_parse_json_call(m.group(1))
            if parsed:
                calls.append(parsed)
        if not calls:
            for m in cls._FENCED_TOOL_RE.finditer(text):
                parsed = cls._try_parse_json_call(m.group(1))
                if parsed:
                    calls.append(parsed)
        if not calls:
            for m in cls._REACT_RE.finditer(text):
                tname = m.group(1).strip()
                try:
                    tparams = _parser_json.loads(m.group(2).strip())
                    if isinstance(tparams, dict):
                        calls.append({"name": tname, "parameters": tparams})
                except Exception:
                    pass
        return calls

    @staticmethod
    def _try_parse_json_call(json_str: str) -> Optional[Dict[str, Any]]:
        try:
            obj = _parser_json.loads(json_str.strip())
            if not isinstance(obj, dict):
                return None
            name = obj.get("name") or obj.get("tool")
            params = obj.get("arguments") if "arguments" in obj else (obj.get("parameters") or obj.get("params") or {})
            if isinstance(params, str):
                params = _parser_json.loads(params)
            if name and isinstance(params, dict):
                return {"name": str(name).strip(), "parameters": params}
        except Exception:
            pass
        return None


class GBNFGrammarBuilder:
    @staticmethod
    def build_tool_grammar(tool_names: List[str]) -> str:
        names = [n for n in tool_names if n] or ["file", "search", "lsp", "git", "editor"]
        quoted_alts = " | ".join(f'"\\"{name}\\""' for name in names)
        return (
            "root ::= tool-call\n"
            "tool-call ::= \"<tool_call>\" ws \"{\" ws \"\\\"name\\\":\" ws tool-name \",\" ws \"\\\"arguments\\\":\" ws json-object ws \"}\" ws \"</tool_call>\"\n"
            f"tool-name ::= {quoted_alts}\n"
            "json-object ::= \"{\" ws (pair (ws \",\" ws pair)*)? ws \"}\"\n"
            "pair ::= string ws \":\" ws value\n"
            "value ::= string | number | boolean | null | json-object | array\n"
            "array ::= \"[\" ws (value (ws \",\" ws value)*)? ws \"]\"\n"
            "string ::= \"\\\"\" ([^\"\\\\] | \"\\\\\" .)* \"\\\"\"\n"
            "number ::= \"-\"? ([0-9]+)(\".\" [0-9]+)?\n"
            "boolean ::= \"true\" | \"false\"\n"
            "null ::= \"null\"\n"
            "ws ::= [ \\t\\n\\r]*\n"
        )


# ============================================================================
# SECTION: ai.tools.tool_coordinator (ai/tools/tool_coordinator.py)
# ============================================================================
"""
AI Tool Coordinator

Central coordinator for all AI tools with:
- Automatic tool registration
- Safety checks and confirmations
- Event publishing
- Tool result aggregation
"""

from typing import Dict, Any, Optional, List
from pathlib import Path

from core.event_bus import EventBus
from core.logger import setup_logger
from ai.tools.base_tool import BaseTool, ToolResult
from ai.tools.file_tool import FileTool
from ai.tools.project_tool import ProjectTool
from ai.tools.execution_tool import ExecutionTool
from ai.tools.search_tool import SearchTool
from ai.tools.editor_tool import EditorTool

logger = setup_logger(__name__)


class AIToolCoordinator:
    """
    Central coordinator for all AI tools.
    
    Provides:
    - Automatic tool discovery and registration
    - Unified tool execution interface
    - Safety checks and user confirmations
    - Event publishing for UI updates
    - Tool capability queries
    
    Usage:
        coordinator = AIToolCoordinator(event_bus, workspace_root)
        result = coordinator.execute_tool("file", action="create", path="new.py")
        
        # With AI agent
        tools = coordinator.get_available_tools()
        result = coordinator.execute_from_llm(tool_name, tool_params)
    """
    
    def __init__(self, event_bus: EventBus, workspace_root: Optional[str] = None):
        self.event_bus = event_bus
        self.workspace_root = workspace_root
        self._tools: Dict[str, BaseTool] = {}
        self._pending_confirmations: Dict[str, Dict[str, Any]] = {}
        
        # Register all tools
        self._register_default_tools()
        
        # Subscribe to confirmation events
        self._subscribe_events()
        
        logger.info(f"AIToolCoordinator initialized with {len(self._tools)} tools")
    
    def _register_default_tools(self):
        """Register all built-in tools."""
        tools = [
            FileTool(self.event_bus, self.workspace_root),
            ProjectTool(self.event_bus, self.workspace_root),
            ExecutionTool(self.event_bus, self.workspace_root),
            SearchTool(self.event_bus, self.workspace_root),
            EditorTool(self.event_bus, self.workspace_root),
            LspTool(self.event_bus, self.workspace_root),
            GitWorkspaceTool(self.event_bus, self.workspace_root),
        ]
        
        for tool in tools:
            self._tools[tool.name] = tool
            logger.info(f"Registered tool: {tool.name}")
    
    def _subscribe_events(self):
        """Subscribe to confirmation events."""
        self.event_bus.subscribe("tool_confirmation_approved", self._on_confirmation_approved)
        self.event_bus.subscribe("tool_confirmation_denied", self._on_confirmation_denied)
    
    def register_tool(self, tool: BaseTool):
        """Register a custom tool."""
        self._tools[tool.name] = tool
        logger.info(f"Registered custom tool: {tool.name}")
    
    def unregister_tool(self, tool_name: str):
        """Unregister a tool."""
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available tools with their schemas.
        Returns format suitable for LLM function calling.
        """
        tools = []
        for name, tool in self._tools.items():
            tools.append({
                "name": name,
                "description": tool.description,
                "parameters": tool.schema
            })
        return tools
    
    def execute_tool(self, tool_name: str, **params) -> ToolResult:
        """
        Execute a tool with parameters.
        
        Args:
            tool_name: Name of the tool to execute
            **params: Tool parameters
            
        Returns:
            ToolResult with success/failure and output
        """
        if tool_name not in self._tools:
            return ToolResult(
                success=False,
                error=f"Unknown tool: {tool_name}. Available: {list(self._tools.keys())}"
            )
        
        tool = self._tools[tool_name]
        
        logger.info(f"Executing tool: {tool_name} with params: {params}")
        
        try:
            result = tool.execute(**params)
            
            # Handle confirmation requirement
            if result.requires_confirmation:
                confirmation_id = self._request_confirmation(tool_name, params, result)
                result.metadata = result.metadata or {}
                result.metadata["confirmation_id"] = confirmation_id
                
                logger.info(f"Tool {tool_name} requires confirmation: {confirmation_id}")
            
            # Publish execution event
            self.event_bus.publish("tool_executed", {
                "tool": tool_name,
                "success": result.success,
                "requires_confirmation": result.requires_confirmation,
                "output": str(result.output)[:200] if result.output else None
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}"
            )
    
    def execute_from_llm(self, tool_call: Dict[str, Any]) -> ToolResult:
        """
        Execute tool from LLM function call format.
        
        Args:
            tool_call: Dict with 'name' and 'parameters'
            
        Returns:
            ToolResult
        """
        tool_name = tool_call.get('name')
        params = tool_call.get('parameters', {})
        
        if not tool_name:
            return ToolResult(
                success=False,
                error="Tool name required in tool_call"
            )
        
        return self.execute_tool(tool_name, **params)
    
    def _request_confirmation(self, tool_name: str, params: Dict[str, Any], 
                            result: ToolResult) -> str:
        """Request user confirmation for destructive operation."""
        import uuid
        confirmation_id = f"confirm_{uuid.uuid4().hex[:8]}"
        
        self._pending_confirmations[confirmation_id] = {
            "tool_name": tool_name,
            "params": params,
            "result": result
        }
        
        # Publish confirmation request event
        self.event_bus.publish("tool_confirmation_required", {
            "confirmation_id": confirmation_id,
            "tool": tool_name,
            "action": params.get('action'),
            "message": result.error,
            "metadata": result.metadata
        })
        
        return confirmation_id
    
    def _on_confirmation_approved(self, data: Dict[str, Any]):
        """Handle confirmation approval."""
        confirmation_id = data.get('confirmation_id')
        
        if confirmation_id not in self._pending_confirmations:
            logger.warning(f"Unknown confirmation ID: {confirmation_id}")
            return
        
        pending = self._pending_confirmations.pop(confirmation_id)
        tool_name = pending['tool_name']
        params = pending['params']
        
        # Retry with confirmed=True
        params['confirmed'] = True
        result = self.execute_tool(tool_name, **params)
        
        # Publish result
        self.event_bus.publish("tool_confirmation_completed", {
            "confirmation_id": confirmation_id,
            "success": result.success,
            "output": result.output,
            "error": result.error
        })
    
    def _on_confirmation_denied(self, data: Dict[str, Any]):
        """Handle confirmation denial."""
        confirmation_id = data.get('confirmation_id')
        
        if confirmation_id in self._pending_confirmations:
            self._pending_confirmations.pop(confirmation_id)
        
        self.event_bus.publish("tool_confirmation_completed", {
            "confirmation_id": confirmation_id,
            "success": False,
            "error": "Operation cancelled by user"
        })
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific tool."""
        if tool_name not in self._tools:
            return None
        
        tool = self._tools[tool_name]
        return {
            "name": tool.name,
            "description": tool.description,
            "schema": tool.schema
        }
    
    def get_tool_names(self) -> List[str]:
        """Get list of available tool names."""
        return list(self._tools.keys())
    
    def set_workspace_root(self, workspace_root: str):
        """Update workspace root for all tools and the shared WorkspaceVFS."""
        self.workspace_root = workspace_root
        get_workspace_vfs(workspace_root, self.event_bus)
        for tool in self._tools.values():
            tool.workspace_root = workspace_root
        logger.info(f"Updated workspace root to: {workspace_root}")


def initialize_tool_coordinator(event_bus: EventBus, 
                               workspace_root: Optional[str] = None) -> AIToolCoordinator:
    """
    Initialize and return the global AI tool coordinator.
    
    Args:
        event_bus: Event bus for communication
        workspace_root: Root directory for file operations
        
    Returns:
        AIToolCoordinator instance
    """
    coordinator = AIToolCoordinator(event_bus, workspace_root)
    logger.info("AI Tool Coordinator initialized successfully")
    return coordinator
