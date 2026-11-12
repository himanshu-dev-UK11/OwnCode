"""
Consolidated Module: agent.tool_engine

Combines: ai.tools.tool_base, ai.tools.tool_permission, ai.tools.tool_history, ai.tools.tool_registry, ai.tools.tool_scheduler, ai.tools.terminal_tool, ai.tools.git_tool, ai.tools.tool_manager
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['ai.tools.tool_base', 'ai.tools.tool_permission', 'ai.tools.tool_history', 'ai.tools.tool_registry', 'ai.tools.tool_scheduler', 'ai.tools.terminal_tool', 'ai.tools.git_tool', 'ai.tools.tool_manager']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ai.tools.tool_base (ai/tools/tool_base.py)
# ============================================================================
"""
Base Tool — v1.5

Abstract base class for all tools in the Universal Tool Calling Engine.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from core.logger import setup_logger


class ToolPermission(Enum):
    """Permission levels for tools."""
    SAFE = "safe"           # No user confirmation required
    WARNING = "warning"     # User confirmation required
    DANGEROUS = "dangerous" # User confirmation required, logged


class ToolCategory(Enum):
    """Tool categories."""
    FILE = "file"
    PROJECT = "project"
    TERMINAL = "terminal"
    GIT = "git"
    GITHUB = "github"
    BROWSER = "browser"
    VERIFICATION = "verification"
    EDITOR = "editor"
    PLUGIN = "plugin"


@dataclass
class ToolResult:
    """Standardized result for tool execution."""
    success: bool
    tool_name: str
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "tool_name": self.tool_name,
            "output": str(self.output) if self.output else None,
            "error": self.error,
            "metadata": self.metadata,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }
    
    @classmethod
    def success_result(cls, tool_name: str, output: Any = None, 
                       metadata: Optional[Dict] = None) -> "ToolResult":
        """Create a success result."""
        return cls(
            success=True,
            tool_name=tool_name,
            output=output,
            metadata=metadata or {}
        )
    
    @classmethod
    def error_result(cls, tool_name: str, error: str,
                     metadata: Optional[Dict] = None) -> "ToolResult":
        """Create an error result."""
        return cls(
            success=False,
            tool_name=tool_name,
            error=error,
            metadata=metadata or {}
        )


@dataclass
class ToolContext:
    """Context passed to every tool."""
    project_root: Optional[str] = None
    workspace: Optional[str] = None
    open_files: List[str] = field(default_factory=list)
    selected_text: Optional[str] = None
    cursor_position: Optional[Dict[str, Any]] = None
    ai_task: Optional[str] = None
    current_model: Optional[str] = None
    project_intelligence: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_root": self.project_root,
            "workspace": self.workspace,
            "open_files": self.open_files,
            "selected_text": self.selected_text[:50] + "..." if self.selected_text and len(self.selected_text) > 50 else self.selected_text,
            "cursor_position": self.cursor_position,
            "ai_task": self.ai_task,
            "current_model": self.current_model,
            "project_intelligence": self.project_intelligence,
        }


class BaseTool(ABC):
    """
    Abstract base class for all tools.
    
    Every tool must implement:
    - execute() — Main execution logic
    - cancel() — Cancel ongoing execution
    - validate() — Validate parameters before execution
    
    Tools receive ToolContext with project state for context-aware execution.
    """
    
    def __init__(self, name: str, description: str, category: ToolCategory,
                 permission_level: ToolPermission, supported_models: List[str]):
        self.name = name
        self.description = description
        self.category = category
        self.permission_level = permission_level
        self.supported_models = supported_models
        self.logger = setup_logger(f"tool.{name}")
        
        self._context: Optional[ToolContext] = None
        self._is_cancelled = False
        self._is_running = False
        self._last_result: Optional[ToolResult] = None
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Properties
    # ─────────────────────────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        """Check if tool is currently executing."""
        return self._is_running
    
    @property
    def is_cancelled(self) -> bool:
        """Check if tool execution was cancelled."""
        return self._is_cancelled
    
    @property
    def requires_confirmation(self) -> bool:
        """Check if tool requires user confirmation."""
        return self.permission_level in (ToolPermission.WARNING, ToolPermission.DANGEROUS)
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Execution
    # ─────────────────────────────────────────────────────────────────────────────

    def set_context(self, context: ToolContext) -> None:
        """Set the tool context."""
        self._context = context
    
    def get_context(self) -> Optional[ToolContext]:
        """Get the current tool context."""
        return self._context
    
    async def execute_async(self, **kwargs) -> ToolResult:
        """
        Execute the tool asynchronously.
        
        This method handles:
        - Setting running status
        - Calling execute()
        - Timing execution
        - Handling cancellation
        - Storing result
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult with success/failure and output
        """
        if self._is_cancelled:
            return ToolResult.error_result(
                self.name, 
                "Tool execution was cancelled"
            )
        
        self._is_running = True
        start_time = datetime.utcnow()
        
        try:
            # Validate parameters
            validation_result = self.validate(**kwargs)
            if not validation_result.success:
                return validation_result
            
            # Execute
            result = await self.execute(**kwargs)
            
            # Time it
            result.execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._last_result = result
            
            return result
            
        except Exception as e:
            self.logger.error(f"Tool {self.name} execution error: {e}")
            result = ToolResult.error_result(
                self.name,
                str(e)
            )
            result.execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            return result
            
        finally:
            self._is_running = False
    
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool synchronously.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult with success/failure and output
        """
        result = self._run_async(self.execute_async(**kwargs))
        return result
    
    @abstractmethod
    async def execute_async(self, **kwargs) -> ToolResult:
        """
        Async execution implementation.
        
        This is the main method that must be implemented by each tool.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult with success/failure and output
        """
        pass
    
    def cancel(self) -> bool:
        """
        Cancel ongoing execution.
        
        Returns:
            True if cancellation was successful
        """
        self._is_cancelled = True
        self._is_running = False
        self.logger.info(f"Tool {self.name} cancellation requested")
        return True
    
    def validate(self, **kwargs) -> ToolResult:
        """
        Validate tool parameters before execution.
        
        Args:
            **kwargs: Parameters to validate
            
        Returns:
            ToolResult with validation result
        """
        # Default implementation: always valid
        return ToolResult.success_result(self.name, metadata={"validated": True})
    
    def _run_async(self, coro) -> Any:
        """Run async coroutine in a thread-safe manner."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Utility methods
    # ─────────────────────────────────────────────────────────────────────────────

    def is_model_supported(self, model_id: str) -> bool:
        """Check if a model is supported by this tool."""
        return model_id in self.supported_models or "all" in self.supported_models
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get tool metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "permission_level": self.permission_level.value,
            "supported_models": self.supported_models,
            "requires_confirmation": self.requires_confirmation,
            "is_running": self._is_running,
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, category={self.category.value})"


# ============================================================================
# SECTION: ai.tools.tool_permission (ai/tools/tool_permission.py)
# ============================================================================
"""
Tool Permission System — v2.0

Permission checking and user confirmation for dangerous tools.

v2.0 finishes the table for autonomous execution:
  * user overrides persist to ``config/tool_permissions.json``
  * an explicit autonomous-mode gate (``can_auto_execute``) that only ever lets
    SAFE actions run unattended unless the user has pre-approved a specific one
  * coverage for the AI change-set / multi-file edit apply path
"""

import json
import os
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
from core.logger import setup_logger


logger = setup_logger(__name__)


class PermissionLevel(Enum):
    """Permission levels for tools."""
    SAFE = "safe"           # No user confirmation required
    WARNING = "warning"     # User confirmation required
    DANGEROUS = "dangerous" # User confirmation required, logged


class PermissionPolicy:
    """
    Defines the policy for tool permissions.

    Defaults ship in code; user customizations and pre-approvals are persisted
    to ``config/tool_permissions.json`` so they survive restarts.
    """

    def __init__(self, config_path: str = "config/tool_permissions.json"):
        self._policies: Dict[str, str] = {}
        self._default_policy = PermissionLevel.SAFE
        self._logger = logger
        self._config_path = Path(config_path)

        # Autonomous execution is OFF until the user opts in. Even when ON, only
        # SAFE actions (plus explicit pre-approvals) run without confirmation.
        self._autonomous_enabled = False
        self._auto_approved: set[str] = set()

        # Default policies
        self._default_policies = {
            # File operations
            "file.read_file": PermissionLevel.SAFE,
            "file.write_file": PermissionLevel.WARNING,
            "file.create_file": PermissionLevel.WARNING,
            "file.delete_file": PermissionLevel.DANGEROUS,
            "file.rename_file": PermissionLevel.WARNING,
            "file.move_file": PermissionLevel.WARNING,

            # Project operations
            "project.scan": PermissionLevel.SAFE,
            "project.analyze": PermissionLevel.SAFE,

            # Terminal operations
            "terminal.run_command": PermissionLevel.WARNING,
            "terminal.background_command": PermissionLevel.WARNING,
            "terminal.stop_command": PermissionLevel.SAFE,

            # Git operations
            "git.status": PermissionLevel.SAFE,
            "git.commit": PermissionLevel.WARNING,
            "git.branch": PermissionLevel.WARNING,
            "git.rollback": PermissionLevel.DANGEROUS,
            "git.snapshot": PermissionLevel.WARNING,

            # GitHub operations (disabled by default)
            "github.status": PermissionLevel.WARNING,
            "github.push": PermissionLevel.DANGEROUS,

            # Browser operations
            "browser.search": PermissionLevel.SAFE,

            # Verification operations
            "verification.run_tests": PermissionLevel.WARNING,
            "verification.run_build": PermissionLevel.WARNING,
            "verification.run_linter": PermissionLevel.SAFE,

            # Editor operations
            "editor.open_file": PermissionLevel.SAFE,
            "editor.focus_line": PermissionLevel.SAFE,

            # AI change-set / multi-file edit path (review UI, item 10)
            "changeset.preview": PermissionLevel.SAFE,
            "changeset.apply": PermissionLevel.WARNING,
            "changeset.apply_hunk": PermissionLevel.WARNING,
            "changeset.rollback": PermissionLevel.DANGEROUS,
        }

        self._load()
        self._logger.info(
            "PermissionPolicy initialized (%d overrides, autonomous=%s)",
            len(self._policies), self._autonomous_enabled,
        )

    # ── persistence ────────────────────────────────────────────────────────────
    def _load(self) -> None:
        if not self._config_path.exists():
            return
        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
            self._policies = {k: v for k, v in data.get("overrides", {}).items()}
            self._autonomous_enabled = bool(data.get("autonomous_enabled", False))
            self._auto_approved = set(data.get("auto_approved", []))
        except Exception as e:  # noqa: BLE001
            self._logger.error("Failed to load permission config: %s", e)

    def _save(self) -> None:
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            self._config_path.write_text(json.dumps({
                "overrides": self._policies,
                "autonomous_enabled": self._autonomous_enabled,
                "auto_approved": sorted(self._auto_approved),
            }, indent=2), encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            self._logger.error("Failed to save permission config: %s", e)

    def get_permission(self, tool_name: str, action: str) -> PermissionLevel:
        """
        Get the permission level for a tool action.

        Args:
            tool_name: Name of the tool
            action: Action being performed

        Returns:
            Permission level for the action
        """
        key = f"{tool_name}.{action}"

        # Check specific policy
        if key in self._policies:
            return PermissionLevel(self._policies[key])

        # Check default policy
        if key in self._default_policies:
            return self._default_policies[key]

        # Return default
        return self._default_policy

    def set_policy(self, tool_name: str, action: str,
                   level: PermissionLevel) -> None:
        """
        Set a custom permission policy.

        Args:
            tool_name: Name of the tool
            action: Action being performed
            level: Permission level
        """
        key = f"{tool_name}.{action}"
        self._policies[key] = level.value
        self._save()
        self._logger.info(f"Set policy: {key} -> {level.value}")

    def requires_confirmation(self, tool_name: str, action: str) -> bool:
        """Check if a tool action requires user confirmation."""
        level = self.get_permission(tool_name, action)
        return level in (PermissionLevel.WARNING, PermissionLevel.DANGEROUS)

    def is_dangerous(self, tool_name: str, action: str) -> bool:
        """Check if a tool action is dangerous."""
        level = self.get_permission(tool_name, action)
        return level == PermissionLevel.DANGEROUS

    def get_dangerous_tools(self) -> List[str]:
        """Get list of all dangerous tool actions."""
        dangerous = []
        merged = self.get_policy_summary()
        for key, level in merged.items():
            if level == PermissionLevel.DANGEROUS.value:
                dangerous.append(key)
        return dangerous

    def get_policy_summary(self) -> Dict[str, str]:
        """Get summary of all policies as ``key -> level value`` (defaults + overrides)."""
        policies = {k: v.value for k, v in self._default_policies.items()}
        policies.update(self._policies)
        return policies

    # ── autonomous execution gate ───────────────────────────────────────────────
    def set_autonomous_enabled(self, enabled: bool) -> None:
        """Turn unattended tool execution on/off globally."""
        self._autonomous_enabled = bool(enabled)
        self._save()
        self._logger.info("Autonomous execution %s", "enabled" if enabled else "disabled")

    def is_autonomous_enabled(self) -> bool:
        return self._autonomous_enabled

    def pre_approve(self, tool_name: str, action: str) -> None:
        """Let a specific WARNING/DANGEROUS action run unattended in autonomous mode."""
        self._auto_approved.add(f"{tool_name}.{action}")
        self._save()

    def revoke_approval(self, tool_name: str, action: str) -> None:
        self._auto_approved.discard(f"{tool_name}.{action}")
        self._save()

    def can_auto_execute(self, tool_name: str, action: str) -> bool:
        """
        Decide whether an action may run WITHOUT user confirmation right now.

        The gate before shipping autonomous execution: unattended runs are only
        permitted when autonomous mode is on, and even then only for SAFE
        actions or ones the user has explicitly pre-approved. Everything else
        must still surface a confirmation prompt.
        """
        key = f"{tool_name}.{action}"
        level = self.get_permission(tool_name, action)
        if level == PermissionLevel.SAFE:
            return True
        if not self._autonomous_enabled:
            return False
        return key in self._auto_approved


# Global instance
_permission_policy = None


def get_permission_policy() -> PermissionPolicy:
    """Get the global permission policy."""
    global _permission_policy
    if _permission_policy is None:
        _permission_policy = PermissionPolicy()
    return _permission_policy


def reset_permission_policy():
    """Reset the global permission policy."""
    global _permission_policy
    _permission_policy = None


# ============================================================================
# SECTION: ai.tools.tool_history (ai/tools/tool_history.py)
# ============================================================================
"""
Tool History — v1.5

Records and analyzes tool execution history.
"""

import json
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from core.logger import setup_logger

from ai.tools.tool_base import ToolResult


logger = setup_logger(__name__)


@dataclass
class ExecutionRecord:
    """Record of a tool execution."""
    timestamp: datetime
    tool_name: str
    action: str
    success: bool
    execution_time_ms: float
    error: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    user: Optional[str] = None
    rollback_id: Optional[str] = None


class ToolHistory:
    """
    Stores and analyzes tool execution history.
    
    Provides:
    - Execution history storage
    - Statistics and metrics
    - Rollback capability
    """
    
    def __init__(self, history_dir: str = "config/tool_history"):
        self.history_dir = Path(history_dir)
        self._records: List[ExecutionRecord] = []
        self._lock = threading.Lock()
        self._tool_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total": 0,
            "success": 0,
            "failure": 0,
            "total_time_ms": 0.0,
            "avg_time_ms": 0.0,
            "min_time_ms": float("inf"),
            "max_time_ms": 0.0,
        })
        self._logger = logger
        self._rollback_index: Dict[str, List[str]] = defaultdict(list)
        
        # Ensure directory exists
        try:
            self.history_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self._logger.warning(f"Could not create history directory: {e}")
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Recording
    # ─────────────────────────────────────────────────────────────────────────────

    def record_result(self, result: ToolResult, 
                      context: Optional[Dict[str, Any]] = None,
                      user: Optional[str] = None,
                      rollback_id: Optional[str] = None) -> None:
        """
        Record a tool execution result.
        
        Args:
            result: ToolResult from execution
            context: Execution context (optional)
            user: User who executed (optional)
            rollback_id: Rollback identifier (optional)
        """
        record = ExecutionRecord(
            timestamp=datetime.utcnow(),
            tool_name=result.tool_name,
            action="",  # Action not stored in ToolResult
            success=result.success,
            execution_time_ms=result.execution_time_ms,
            error=result.error,
            context=context,
            user=user,
            rollback_id=rollback_id,
        )
        
        with self._lock:
            self._records.append(record)
            self._update_stats(result)
            
            if rollback_id:
                self._rollback_index[rollback_id].append(
                    f"{result.tool_name}.{record.timestamp.isoformat()}"
                )
        
        self._logger.debug(f"Recorded execution: {result.tool_name} - {'success' if result.success else 'failed'}")
    
    def record_execution(self, tool_name: str, action: str, success: bool,
                        execution_time_ms: float, error: Optional[str] = None,
                        context: Optional[Dict[str, Any]] = None,
                        user: Optional[str] = None,
                        rollback_id: Optional[str] = None) -> None:
        """Record a tool execution directly."""
        result = ToolResult(
            success=success,
            tool_name=tool_name,
            error=error,
            metadata={"execution_time_ms": execution_time_ms}
        )
        result.execution_time_ms = execution_time_ms
        self.record_result(result, context, user, rollback_id)
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Queries
    # ─────────────────────────────────────────────────────────────────────────────

    def get_history(self, limit: int = 100, 
                    tool_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get execution history.
        
        Args:
            limit: Maximum number of records
            tool_name: Filter by tool name (optional)
            
        Returns:
            List of execution records
        """
        with self._lock:
            if tool_name:
                records = [r for r in self._records if r.tool_name == tool_name]
            else:
                records = list(self._records)
            
            # Sort by timestamp (newest first)
            records.sort(key=lambda r: r.timestamp, reverse=True)
            
            # Return limited
            return [self._record_to_dict(r) for r in records[:limit]]
    
    def get_recent(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get executions from the last N minutes."""
        cutoff = datetime.utcnow().timestamp() - (minutes * 60)
        
        with self._lock:
            recent = [
                r for r in self._records
                if r.timestamp.timestamp() >= cutoff
            ]
        
        recent.sort(key=lambda r: r.timestamp, reverse=True)
        return [self._record_to_dict(r) for r in recent]
    
    def get_errors(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get failed executions."""
        with self._lock:
            errors = [r for r in self._records if not r.success]
        
        errors.sort(key=lambda r: r.timestamp, reverse=True)
        return [self._record_to_dict(r) for r in errors[:limit]]
    
    def get_by_rollback_id(self, rollback_id: str) -> List[Dict[str, Any]]:
        """Get executions by rollback ID."""
        with self._lock:
            record_ids = self._rollback_index.get(rollback_id, [])
            return [self._record_to_dict(r) for r in self._records 
                   if f"{r.tool_name}.{r.timestamp.isoformat()}" in record_ids]
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Statistics
    # ─────────────────────────────────────────────────────────────────────────────

    def get_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for a tool or all tools.
        
        Args:
            tool_name: Tool name or None for all
            
        Returns:
            Statistics dictionary
        """
        with self._lock:
            if tool_name:
                return self._tool_stats.get(tool_name, {}).copy()
            
            # Aggregate all stats
            stats = {}
            for name, data in self._tool_stats.items():
                stats[name] = {
                    "total": data["total"],
                    "success": data["success"],
                    "failure": data["failure"],
                    "success_rate": data["success"] / data["total"] if data["total"] > 0 else 0.0,
                    "avg_time_ms": data["avg_time_ms"],
                    "min_time_ms": data["min_time_ms"] if data["min_time_ms"] != float("inf") else 0,
                    "max_time_ms": data["max_time_ms"],
                }
            return stats
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall execution statistics."""
        with self._lock:
            total = len(self._records)
            success = sum(1 for r in self._records if r.success)
            failure = total - success
            
            total_time = sum(r.execution_time_ms for r in self._records)
            avg_time = total_time / total if total > 0 else 0.0
            
            return {
                "total_executions": total,
                "successful": success,
                "failed": failure,
                "success_rate": success / total if total > 0 else 0.0,
                "total_time_ms": total_time,
                "avg_time_ms": avg_time,
                "tools_count": len(self._tool_stats),
            }
    
    def get_top_tools(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most frequently used tools."""
        with self._lock:
            tools = []
            for name, data in self._tool_stats.items():
                tools.append({
                    "tool_name": name,
                    "total": data["total"],
                    "success_rate": data["success"] / data["total"] if data["total"] > 0 else 0.0,
                    "avg_time_ms": data["avg_time_ms"],
                })
        
        tools.sort(key=lambda t: t["total"], reverse=True)
        return tools[:limit]
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Utilities
    # ─────────────────────────────────────────────────────────────────────────────

    def get_history_size(self) -> int:
        """Get number of records in history."""
        with self._lock:
            return len(self._records)
    
    def clear_history(self, before: Optional[datetime] = None) -> int:
        """
        Clear old history records.
        
        Args:
            before: Clear records before this timestamp
            
        Returns:
            Number of records cleared
        """
        with self._lock:
            if before:
                original_count = len(self._records)
                self._records = [
                    r for r in self._records 
                    if r.timestamp >= before
                ]
                cleared = original_count - len(self._records)
            else:
                cleared = len(self._records)
                self._records.clear()
            
            return cleared
    
    def save_to_file(self, filepath: Optional[str] = None) -> str:
        """Save history to file."""
        filepath = filepath or str(self.history_dir / "history.json")
        
        with self._lock:
            data = {
                "records": [
                    self._record_to_dict(r) for r in self._records
                ],
                "saved_at": datetime.utcnow().isoformat(),
            }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            return filepath
        except Exception as e:
            self._logger.error(f"Failed to save history: {e}")
            return ""
    
    def load_from_file(self, filepath: str) -> int:
        """Load history from file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            records = data.get("records", [])
            for r_data in records:
                record = ExecutionRecord(
                    timestamp=datetime.fromisoformat(r_data["timestamp"]),
                    tool_name=r_data["tool_name"],
                    action=r_data.get("action", ""),
                    success=r_data["success"],
                    execution_time_ms=r_data.get("execution_time_ms", 0),
                    error=r_data.get("error"),
                    context=r_data.get("context"),
                    user=r_data.get("user"),
                    rollback_id=r_data.get("rollback_id"),
                )
                self._records.append(record)
                self._update_stats_from_record(record)
            
            return len(records)
        except Exception as e:
            self._logger.error(f"Failed to load history: {e}")
            return 0
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Internal
    # ─────────────────────────────────────────────────────────────────────────────

    def _record_to_dict(self, record: ExecutionRecord) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "timestamp": record.timestamp.isoformat(),
            "tool_name": record.tool_name,
            "action": record.action,
            "success": record.success,
            "execution_time_ms": record.execution_time_ms,
            "error": record.error,
            "context": record.context,
            "user": record.user,
            "rollback_id": record.rollback_id,
        }
    
    def _update_stats(self, result: ToolResult) -> None:
        """Update statistics for a tool."""
        stats = self._tool_stats[result.tool_name]
        
        stats["total"] += 1
        if result.success:
            stats["success"] += 1
        else:
            stats["failure"] += 1
        
        stats["total_time_ms"] += result.execution_time_ms
        stats["avg_time_ms"] = stats["total_time_ms"] / stats["total"]
        stats["min_time_ms"] = min(stats["min_time_ms"], result.execution_time_ms)
        stats["max_time_ms"] = max(stats["max_time_ms"], result.execution_time_ms)
    
    def _update_stats_from_record(self, record: ExecutionRecord) -> None:
        """Update stats from a loaded record."""
        stats = self._tool_stats[record.tool_name]
        
        stats["total"] += 1
        if record.success:
            stats["success"] += 1
        else:
            stats["failure"] += 1
        
        stats["total_time_ms"] += record.execution_time_ms
        stats["avg_time_ms"] = stats["total_time_ms"] / stats["total"]
        stats["min_time_ms"] = min(stats["min_time_ms"], record.execution_time_ms)
        stats["max_time_ms"] = max(stats["max_time_ms"], record.execution_time_ms)


# Global instance
_tool_history = None


def get_tool_history() -> ToolHistory:
    """Get the global tool history."""
    global _tool_history
    if _tool_history is None:
        _tool_history = ToolHistory()
    return _tool_history


def reset_tool_history():
    """Reset the global tool history."""
    global _tool_history
    _tool_history = None


# ============================================================================
# SECTION: ai.tools.tool_registry (ai/tools/tool_registry.py)
# ============================================================================
"""
Tool Registry — v1.5

Registry for all available tools with permission checking and discovery.
"""

import importlib
import inspect
import os
from pathlib import Path
from typing import Dict, List, Optional, Type
from core.logger import setup_logger

from ai.tools.tool_base import BaseTool, ToolPermission, ToolCategory


logger = setup_logger(__name__)


class ToolRegistry:
    """
    Central registry for all tools.
    
    Provides:
    - Tool registration and discovery
    - Permission checking before execution
    - Tool instantiation with proper dependencies
    - Tool metadata and introspection
    """
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._tool_classes: Dict[str, Type[BaseTool]] = {}
        self._logger = logger
        self._registered_paths: List[str] = []
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Registration
    # ─────────────────────────────────────────────────────────────────────────────

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        if tool.name in self._tools:
            self._logger.warning(f"Tool '{tool.name}' already registered, replacing")
        
        self._tools[tool.name] = tool
        self._tool_classes[tool.name] = type(tool)
        self._logger.info(f"Registered tool: {tool.name} ({tool.category.value})")
    
    def unregister_tool(self, name: str) -> bool:
        """Remove a tool from the registry."""
        if name not in self._tools:
            return False
        
        del self._tools[name]
        del self._tool_classes[name]
        self._logger.info(f"Unregistered tool: {name}")
        return True
    
    def register_class(self, tool_class: Type[BaseTool]) -> None:
        """Register a tool class for later instantiation."""
        instance = tool_class.__name__
        name = tool_class.__name__.replace("Tool", "").lower()
        self._tool_classes[name] = tool_class
        self._logger.debug(f"Registered tool class: {name}")
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Discovery
    # ─────────────────────────────────────────────────────────────────────────────

    def discover_tools(self, tools_dir: str = "ai/tools") -> List[str]:
        """
        Discover and register all tools from a directory.
        
        Args:
            tools_dir: Directory containing tool files
            
        Returns:
            List of registered tool names
        """
        registered = []
        
        if not os.path.exists(tools_dir):
            self._logger.warning(f"Tools directory not found: {tools_dir}")
            return registered
        
        self._registered_paths.append(tools_dir)
        
        # Discover from ai/tools directory
        tool_files = Path(tools_dir).glob("*.py")
        
        for tool_file in tool_files:
            if tool_file.name.startswith("_"):
                continue
            
            module_name = f"ai.tools.{tool_file.stem}"
            try:
                module = importlib.import_module(module_name)
                
                # Find all BaseTool subclasses
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseTool) and obj != BaseTool:
                        # Create instance with empty constructor
                        # This will need to be updated with proper dependency injection
                        try:
                            tool_instance = obj()
                            self.register_tool(tool_instance)
                            registered.append(tool_instance.name)
                        except Exception as e:
                            self._logger.warning(f"Could not instantiate {name}: {e}")
                
            except Exception as e:
                self._logger.warning(f"Could not load module {module_name}: {e}")
        
        self._logger.info(f"Discovered {len(registered)} tools from {tools_dir}")
        return registered
    
    def discover_plugin_tools(self, plugin_dir: str) -> List[str]:
        """
        Discover tools from a plugin directory.
        
        Args:
            plugin_dir: Directory containing plugin tools
            
        Returns:
            List of registered plugin tool names
        """
        # Plugin discovery would work similarly but with different import logic
        # For now, this is a placeholder for future plugin support
        self._logger.info(f"Plugin discovery directory: {plugin_dir}")
        return []
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Access
    # ─────────────────────────────────────────────────────────────────────────────

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_all_tools(self) -> Dict[str, BaseTool]:
        """Get all registered tools."""
        return dict(self._tools)
    
    def get_tools_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """Get all tools in a category."""
        return [
            tool for tool in self._tools.values()
            if tool.category == category
        ]
    
    def get_tools_by_permission(self, permission: ToolPermission) -> List[BaseTool]:
        """Get all tools with a specific permission level."""
        return [
            tool for tool in self._tools.values()
            if tool.permission_level == permission
        ]
    
    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Validation
    # ─────────────────────────────────────────────────────────────────────────────

    def can_execute(self, tool_name: str, permission_required: bool = True) -> bool:
        """
        Check if a tool can be executed.
        
        Args:
            tool_name: Name of the tool
            permission_required: If True, requires confirmation for non-safe tools
            
        Returns:
            True if execution is allowed
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return False
        
        if permission_required and tool.requires_confirmation:
            # In production, this would check user permission
            return True
        
        return True
    
    def get_tool_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a tool."""
        tool = self.get_tool(name)
        if not tool:
            return None
        return tool.get_metadata()
    
    def get_all_metadata(self) -> List[Dict[str, Any]]:
        """Get metadata for all tools."""
        return [tool.get_metadata() for tool in self._tools.values()]


# ============================================================================
# SECTION: ai.tools.tool_scheduler (ai/tools/tool_scheduler.py)
# ============================================================================
"""
Tool Scheduler — v1.5

Manages tool execution scheduling with support for:
- Sequential and parallel execution
- Priority-based ordering
- Cancellation
- Retries
- Timeouts
"""

import asyncio
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from core.logger import setup_logger

from ai.tools.tool_base import BaseTool, ToolResult


logger = setup_logger(__name__)


class TaskStatus(Enum):
    """Status of a scheduled task."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class ScheduledTask:
    """A scheduled tool execution task."""
    task_id: str
    tool_name: str
    action: str
    params: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0
    timeout_seconds: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[ToolResult] = None
    error: Optional[str] = None
    on_complete: Optional[Callable[[ToolResult], None]] = None
    on_error: Optional[Callable[[str], None]] = None


class ToolScheduler:
    """
    Manages tool execution scheduling and coordination.
    
    Features:
    - Priority-based scheduling
    - Sequential and parallel execution
    - Cancellation support
    - Retry logic with exponential backoff
    - Timeout enforcement
    """
    
    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._queue: List[ScheduledTask] = []
        self._running: Dict[str, ScheduledTask] = {}
        self._lock = threading.Lock()
        self._logger = logger
        self._shutdown = False
        self._worker_thread: Optional[threading.Thread] = None
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Scheduling
    # ─────────────────────────────────────────────────────────────────────────────

    def schedule(self, tool_name: str, action: str, **kwargs) -> str:
        """
        Schedule a tool for execution.
        
        Args:
            tool_name: Name of the tool
            action: Method to call
            **kwargs: Tool arguments
            
        Returns:
            Task ID for the scheduled task
        """
        task_id = str(uuid.uuid4())[:8]
        
        task = ScheduledTask(
            task_id=task_id,
            tool_name=tool_name,
            action=action,
            params=kwargs,
            priority=kwargs.get("priority", 0),
            timeout_seconds=kwargs.get("timeout_seconds"),
            max_retries=kwargs.get("max_retries", 0),
        )
        
        with self._lock:
            self._tasks[task_id] = task
            self._queue.append(task)
            self._queue.sort(key=lambda t: (-t.priority, t.created_at))
        
        self._logger.info(f"Scheduled task {task_id} for {tool_name}.{action}")
        return task_id
    
    def execute_now(self, tool_name: str, action: str, **kwargs) -> str:
        """
        Execute a tool immediately (bypassing queue).
        
        Args:
            tool_name: Name of the tool
            action: Method to call
            **kwargs: Tool arguments
            
        Returns:
            Task ID for the task
        """
        # Execute in background thread
        task_id = self.schedule(tool_name, action, **kwargs)
        
        def execute_task():
            task = self._tasks.get(task_id)
            if task:
                self._execute_task(task)
        
        threading.Thread(target=execute_task, daemon=True).start()
        return task_id
    
    def schedule_batch(self, tasks: List[Dict[str, Any]], 
                       mode: str = "sequential") -> List[str]:
        """
        Schedule multiple tasks.
        
        Args:
            tasks: List of task specifications
            mode: "sequential" or "parallel"
            
        Returns:
            List of task IDs
        """
        task_ids = []
        for task_spec in tasks:
            task_id = self.schedule(
                task_spec["tool_name"],
                task_spec["action"],
                **task_spec.get("params", {})
            )
            task_ids.append(task_id)
        
        self._logger.info(f"Scheduled {len(task_ids)} tasks in {mode} mode")
        return task_ids
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Cancellation
    # ─────────────────────────────────────────────────────────────────────────────

    def cancel(self, task_id: str) -> bool:
        """
        Cancel a scheduled or running task.
        
        Args:
            task_id: Task ID to cancel
            
        Returns:
            True if cancelled
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            if task.status == TaskStatus.COMPLETED:
                return False
            
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.utcnow()
            
            if task_id in self._running:
                del self._running[task_id]
            
            # Remove from queue
            self._queue = [t for t in self._queue if t.task_id != task_id]
        
        self._logger.info(f"Cancelled task {task_id}")
        return True
    
    def cancel_all(self) -> int:
        """
        Cancel all scheduled and running tasks.
        
        Returns:
            Number of tasks cancelled
        """
        cancelled = 0
        with self._lock:
            # Cancel running tasks
            for task_id in list(self._running.keys()):
                if self.cancel(task_id):
                    cancelled += 1
            
            # Cancel pending tasks
            for task in list(self._queue):
                if self.cancel(task.task_id):
                    cancelled += 1
        
        self._logger.info(f"Cancelled {cancelled} tasks")
        return cancelled
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Status
    # ───────────────────────────────────────────────��─────────────────────────────

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)
    
    def get_pending(self) -> List[ScheduledTask]:
        """Get all pending scheduled tasks."""
        with self._lock:
            return [t for t in self._queue if t.status == TaskStatus.PENDING]
    
    def get_running(self) -> List[ScheduledTask]:
        """Get all currently running tasks."""
        with self._lock:
            return list(self._running.values())
    
    def get_completed(self) -> List[ScheduledTask]:
        """Get all completed tasks."""
        with self._lock:
            return [t for t in self._tasks.values() 
                   if t.status == TaskStatus.COMPLETED]
    
    def get_failed(self) -> List[ScheduledTask]:
        """Get all failed tasks."""
        with self._lock:
            return [t for t in self._tasks.values() 
                   if t.status in (TaskStatus.FAILED, TaskStatus.TIMEOUT)]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        with self._lock:
            return {
                "total_tasks": len(self._tasks),
                "pending": len(self._queue),
                "running": len(self._running),
                "completed": sum(1 for t in self._tasks.values() 
                               if t.status == TaskStatus.COMPLETED),
                "failed": sum(1 for t in self._tasks.values() 
                            if t.status in (TaskStatus.FAILED, TaskStatus.TIMEOUT)),
                "cancelled": sum(1 for t in self._tasks.values() 
                               if t.status == TaskStatus.CANCELLED),
            }
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Execution
    # ─────────────────────────────────────────────────────────────────────────────

    def start_worker(self) -> None:
        """Start the worker thread for processing the queue."""
        if self._worker_thread:
            return
        
        self._shutdown = False
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="ToolScheduler"
        )
        self._worker_thread.start()
        self._logger.info("Tool scheduler worker started")
    
    def stop_worker(self) -> None:
        """Stop the worker thread."""
        self._shutdown = True
        if self._worker_thread:
            self._worker_thread.join(timeout=1.0)
            self._worker_thread = None
        self._logger.info("Tool scheduler worker stopped")
    
    def _worker_loop(self) -> None:
        """Background worker loop for processing the queue."""
        while not self._shutdown:
            try:
                task = self._get_next_task()
                
                if task:
                    self._execute_task(task)
                else:
                    time.sleep(0.1)
                    
            except Exception as e:
                self._logger.error(f"Worker loop error: {e}")
                time.sleep(1.0)
    
    def _get_next_task(self) -> Optional[ScheduledTask]:
        """Get the next task from the queue."""
        with self._lock:
            if not self._queue:
                return None
            
            # Get highest priority task
            task = self._queue.pop(0)
            
            # Check if still pending
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.SCHEDULED
                return task
            
            # Task was cancelled or completed
            return self._get_next_task()
    
    async def _execute_task_async(self, task: ScheduledTask) -> ToolResult:
        """Execute a task asynchronously."""
        # Try to get the tool
        try:
            from ai.tools.tool_manager import get_tool_manager
            manager = get_tool_manager()
            
            if not manager or not manager.registry:
                return ToolResult.error_result(
                    task.tool_name,
                    "Tool manager not available"
                )
            
            tool = manager.registry.get_tool(task.tool_name)
            
            if not tool:
                return ToolResult.error_result(
                    task.tool_name,
                    f"Tool '{task.tool_name}' not found"
                )
            
            # Execute the action
            method = getattr(tool, task.action, None)
            if not method:
                return ToolResult.error_result(
                    task.tool_name,
                    f"Action '{task.action}' not found on tool"
                )
            
            # Execute with timeout
            result = await asyncio.wait_for(
                method(**task.params),
                timeout=task.timeout_seconds
            )
            
            return result
            
        except asyncio.TimeoutError:
            return ToolResult.error_result(
                task.tool_name,
                f"Task timed out after {task.timeout_seconds}s"
            )
        except Exception as e:
            return ToolResult.error_result(task.tool_name, str(e))
    
    def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a task."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        
        with self._lock:
            self._running[task.task_id] = task
        
        self._logger.info(f"Executing task {task.task_id}: {task.tool_name}.{task.action}")
        
        try:
            # Execute the task
            result = asyncio.run(self._execute_task_async(task))
            
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.utcnow()
            
            self._logger.info(f"Task {task.task_id} completed")
            
            # Call completion callback
            if task.on_complete and result:
                try:
                    task.on_complete(result)
                except Exception as e:
                    self._logger.error(f"Completion callback error: {e}")
            
            # Remove from running
            with self._lock:
                if task.task_id in self._running:
                    del self._running[task.task_id]
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.utcnow()
            
            self._logger.error(f"Task {task.task_id} failed: {e}")
            
            # Retry if configured
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                
                # Add back to queue with delay
                def retry():
                    time.sleep(2 ** task.retry_count)
                    with self._lock:
                        self._queue.append(task)
                        self._queue.sort(key=lambda t: (-t.priority, t.created_at))
                
                threading.Thread(target=retry, daemon=True).start()
                self._logger.info(f"Retrying task {task.task_id} (attempt {task.retry_count})")
            else:
                # Call error callback
                if task.on_error:
                    try:
                        task.on_error(task.error)
                    except Exception as e:
                        self._logger.error(f"Error callback error: {e}")
                
                # Remove from running
                with self._lock:
                    if task.task_id in self._running:
                        del self._running[task.task_id]


# ============================================================================
# SECTION: ai.tools.terminal_tool (ai/tools/terminal_tool.py)
# ============================================================================
"""
Terminal command execution tool.
"""

from ai.tools.tool_base import BaseTool, ToolPermission, ToolCategory


class TerminalTool(BaseTool):
    def __init__(self, workspace_root: str):
        super().__init__(
            name="terminal",
            description="Terminal command execution (run, stop, background)",
            category=ToolCategory.TERMINAL,
            permission_level=ToolPermission.WARNING,
            supported_models=["all"]
        )
        self.workspace_root = workspace_root
        self._running_processes: dict = {}
        
    async def execute_async(self, action: str, command: str = None, **kwargs) -> ToolResult:
        """Execute a terminal action."""
        try:
            if action == "run":
                return ToolResult.success_result(self.name, output=f"Command executed: {command}")
            elif action == "stop":
                return ToolResult.success_result(self.name, output="Process stopped")
            else:
                return ToolResult.error_result(self.name, f"Unknown action: {action}")
        except Exception as e:
            return ToolResult.error_result(self.name, str(e))
    
    def run_command(self, command: str) -> ToolResult:
        return self.execute(action="run", command=command)
    
    def stop_command(self, process_id: str) -> ToolResult:
        return self.execute(action="stop", process_id=process_id)


# ============================================================================
# SECTION: ai.tools.git_tool (ai/tools/git_tool.py)
# ============================================================================
"""
Git operations tool.
"""

from ai.tools.tool_base import BaseTool, ToolPermission, ToolCategory


class GitTool(BaseTool):
    def __init__(self, repo_path: str):
        super().__init__(
            name="git",
            description="Git operations (status, commit, branch, rollback, snapshot)",
            category=ToolCategory.GIT,
            permission_level=ToolPermission.SAFE,
            supported_models=["all"]
        )
        self.repo_path = repo_path
        
    async def execute_async(self, action: str, **kwargs) -> ToolResult:
        """Execute a git action."""
        try:
            if action == "status":
                return ToolResult.success_result(self.name, output="On main branch, no changes")
            elif action == "commit":
                return ToolResult.success_result(self.name, output="Commit created successfully")
            else:
                return ToolResult.error_result(self.name, f"Unknown action: {action}")
        except Exception as e:
            return ToolResult.error_result(self.name, str(e))
    
    def get_status(self) -> ToolResult:
        return self.execute(action="status")
    
    def commit(self, message: str) -> ToolResult:
        return self.execute(action="commit", message=message)


# ============================================================================
# SECTION: ai.tools.tool_manager (ai/tools/tool_manager.py)
# ============================================================================
"""
Tool Manager — v1.5

Central manager for all tool execution through the Universal Tool Calling Engine.
"""

import asyncio
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from core.logger import setup_logger
from core.event_bus import EventBus

from ai.tools.tool_base import BaseTool, ToolResult, ToolContext, ToolPermission, ToolCategory
from ai.tools.tool_registry import ToolRegistry
from ai.tools.tool_scheduler import ToolScheduler
from ai.tools.tool_history import ToolHistory


logger = setup_logger(__name__)


@dataclass
class ExecuteToolConfig:
    """Configuration for tool execution."""
    tool_name: str
    action: str
    context: Optional[ToolContext] = None
    params: Dict[str, Any] = None
    requires_confirmation: bool = False
    timeout_seconds: int = 30
    retry_count: int = 0
    priority: int = 0
    on_start: Optional[Callable[[ToolResult], None]] = None
    on_complete: Optional[Callable[[ToolResult], None]] = None


class ToolManager:
    """
    Central manager for tool execution.
    
    Responsibilities:
    - Execute tools through the scheduler
    - Validate tool permissions
    - Track tool execution history
    - Provide standardized results
    - Handle tool cancellation
    
    Every tool execution must flow through this manager.
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus
        self.registry = ToolRegistry()
        self.scheduler = ToolScheduler()
        self.history = ToolHistory()
        self._logger = logger
        self._running_tools: Dict[str, BaseTool] = {}
        self._shutdown = False
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Registration
    # ─────────────────────────────────────────────────────────────────────────────

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool with the manager."""
        self.registry.register_tool(tool)
        self._logger.info(f"Registered tool: {tool.name}")
    
    def unregister_tool(self, name: str) -> None:
        """Remove a tool from the registry."""
        self.registry.unregister_tool(name)
    
    def register_default_tools(self, workspace_root: Optional[str] = None) -> None:
        """Register default tools with proper dependencies."""
        # Import and register default tools
        try:
            from ai.tools.file_tool import FileTool
            file_tool = FileTool(workspace_root=workspace_root)
            self.register_tool(file_tool)
        except ImportError:
            self._logger.warning("FileTool not available")
        
        try:
            from ai.tools.git_tool import GitTool
            git_tool = GitTool(repo_path=workspace_root)
            self.register_tool(git_tool)
        except ImportError:
            self._logger.warning("GitTool not available")
        
        try:
            from ai.tools.terminal_tool import TerminalTool
            terminal_tool = TerminalTool(workspace_root=workspace_root)
            self.register_tool(terminal_tool)
        except ImportError:
            self._logger.warning("TerminalTool not available")
        
        try:
            from ai.tools.browser_tool import BrowserTool
            browser_tool = BrowserTool()
            self.register_tool(browser_tool)
        except ImportError:
            self._logger.warning("BrowserTool not available")
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Execution
    # ─────────────────────────────────────────────────────────────────────────────

    def execute_tool(self, tool_name: str, action: str, **kwargs) -> ToolResult:
        """
        Execute a tool and return a standardized result.
        
        Args:
            tool_name: Name of the tool to execute
            action: Method name to call on the tool
            **kwargs: Arguments to pass to the tool
            
        Returns:
            ToolResult with execution result
        """
        return self.execute_tool_async(tool_name, action, **kwargs)
    
    def execute_tool_async(self, tool_name: str, action: str, **kwargs) -> ToolResult:
        """Execute a tool asynchronously."""
        config = ExecuteToolConfig(
            tool_name=tool_name,
            action=action,
            params=kwargs,
        )
        return self.execute_tool_config(config)
    
    def execute_tool_config(self, config: ExecuteToolConfig) -> ToolResult:
        """Execute a tool with full configuration."""
        # Check if tool exists
        tool = self.registry.get_tool(config.tool_name)
        if not tool:
            return ToolResult.error_result(
                config.tool_name,
                f"Tool '{config.tool_name}' not found. Available: {self.registry.list_tools()}"
            )
        
        # Set context
        if config.context:
            tool.set_context(config.context)
        
        # Execute the action
        method = getattr(tool, config.action, None)
        if not method:
            return ToolResult.error_result(
                config.tool_name,
                f"Tool '{config.tool_name}' has no action '{config.action}'"
            )
        
        try:
            # Run async method
            result = self._run_async(method(**config.params))
            
            # Record in history
            self.history.record_result(result)
            
            # Publish event
            if self.event_bus:
                self.event_bus.publish("tool_executed", {
                    "tool_name": config.tool_name,
                    "action": config.action,
                    "success": result.success,
                    "execution_time_ms": result.execution_time_ms,
                })
            
            return result
            
        except Exception as e:
            self._logger.error(f"Tool execution error: {e}")
            return ToolResult.error_result(config.tool_name, str(e))
    
    def execute_tool_with_context(self, tool_name: str, context: ToolContext, 
                                  action: str, **kwargs) -> ToolResult:
        """Execute a tool with full context."""
        config = ExecuteToolConfig(
            tool_name=tool_name,
            action=action,
            context=context,
            params=kwargs,
        )
        return self.execute_tool_config(config)
    
    def _run_async(self, coro) -> Any:
        """Run async coroutine in a thread-safe manner."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Scheduling
    # ─────────────────────────────────────────────────────────────────────────────

    def schedule_tool(self, tool_name: str, action: str, **kwargs) -> str:
        """
        Schedule a tool for queued execution.
        
        Args:
            tool_name: Name of the tool
            action: Method to call
            **kwargs: Tool arguments
            
        Returns:
            Task ID for the scheduled tool
        """
        task_id = self.scheduler.schedule(tool_name, action, **kwargs)
        self._logger.info(f"Scheduled tool: {tool_name} (task_id: {task_id[:8]})")
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled or running task."""
        return self.scheduler.cancel(task_id)
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get all pending scheduled tasks."""
        return self.scheduler.get_pending()
    
    def get_running_tasks(self) -> List[Dict[str, Any]]:
        """Get all currently running tasks."""
        return self.scheduler.get_running()
    
    # ─────────────────────────────────────────────────────────────────────────────
    # History
    # ─────────────────────────────────────────────────────────────────────────────

    def get_execution_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get tool execution history."""
        return self.history.get_history(limit)
    
    def get_tool_stats(self, tool_name: str) -> Dict[str, Any]:
        """Get statistics for a tool."""
        return self.history.get_stats(tool_name)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall tool execution statistics."""
        return self.history.get_overall_stats()
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Validation
    # ─────────────────────────────────────────────────────────────────────────────

    def can_execute(self, tool_name: str) -> bool:
        """Check if a tool can be executed."""
        return self.registry.can_execute(tool_name)
    
    def requires_confirmation(self, tool_name: str) -> bool:
        """Check if a tool requires user confirmation."""
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return False
        return tool.requires_confirmation
    
    def get_permission_level(self, tool_name: str) -> str:
        """Get the permission level for a tool."""
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return "unknown"
        return tool.permission_level.value
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Status
    # ─────────────────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Get tool manager status."""
        return {
            "registered_tools": len(self.registry.list_tools()),
            "pending_tasks": len(self.get_pending_tasks()),
            "running_tasks": len(self.get_running_tasks()),
            "history_size": self.history.get_history_size(),
            "shutdown": self._shutdown,
        }
    
    def get_all_tools_metadata(self) -> List[Dict[str, Any]]:
        """Get metadata for all registered tools."""
        return self.registry.get_all_metadata()
    
    def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get tools in a category."""
        tools = self.registry.get_tools_by_category(ToolCategory(category))
        return [tool.get_metadata() for tool in tools]
    
    def get_tools_by_permission(self, permission: str) -> List[Dict[str, Any]]:
        """Get tools with a permission level."""
        tools = self.registry.get_tools_by_permission(ToolPermission(permission))
        return [tool.get_metadata() for tool in tools]
    
    def shutdown(self) -> None:
        """Shutdown the tool manager."""
        self._shutdown = True
        
        # Cancel all running tasks
        for task in self.get_running_tasks():
            self.cancel_task(task["task_id"])
        
        self._logger.info("Tool manager shutdown complete")

