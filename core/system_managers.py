"""
Consolidated Module: core.system_managers

Combines: core.error_manager, core.safe_file_ops, core.startup_profiler, core.startup_validator, core.config_validator, core.resource_manager, core.session_manager, core.performance_watchdog, core.background_initializer
"""
from __future__ import annotations
import sys as _sys
import core
for _alias in ['core.error_manager', 'core.safe_file_ops', 'core.startup_profiler', 'core.startup_validator', 'core.config_validator', 'core.resource_manager', 'core.session_manager', 'core.performance_watchdog', 'core.background_initializer']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: core.error_manager (core/error_manager.py)
# ============================================================================
"""
Global Error Manager — v1.8.6

Centralized exception handling and recovery:
- Catches all uncaught exceptions
- Logs with full stack trace
- Publishes error events for UI
- Prevents app crashes from single component failures
- Tracks error statistics for diagnostics
"""

import sys
import traceback
from typing import Callable, Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from core.qt_compat import QObject, Signal
from core.logger import setup_logger

logger = setup_logger(__name__)


class ErrorSeverity(Enum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


@dataclass
class ErrorRecord:
    timestamp: datetime = field(default_factory=datetime.now)
    severity: ErrorSeverity = ErrorSeverity.ERROR
    message: str = ""
    exception_type: Optional[str] = None
    stack_trace: Optional[str] = None
    traceback: Optional[str] = None  # Alias for stack_trace, for diagnostics panel
    component: str = "unknown"
    recoverable: bool = False
    context: Optional[dict] = None


class ErrorManager(QObject):
    """
    Central error manager singleton.
    """

    error_occurred = Signal(ErrorRecord)
    critical_error = Signal(ErrorRecord)

    _instance: Optional["ErrorManager"] = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if ErrorManager._initialized:
            return
        super().__init__()
        self._errors: List[ErrorRecord] = []
        self._max_errors = 1000
        self._handlers: Dict[ErrorSeverity, List[Callable]] = {}
        self._event_bus = None
        self._install_global_hooks()
        ErrorManager._initialized = True

    def set_event_bus(self, event_bus):
        """Set the event bus for communication."""
        self._event_bus = event_bus

    def _install_global_hooks(self):
        """Install global exception hooks."""
        original_excepthook = sys.excepthook

        def _custom_excepthook(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                original_excepthook(exc_type, exc_value, exc_traceback)
                return
            self.handle_exception(exc_type, exc_value, exc_traceback, component="global")

        sys.excepthook = _custom_excepthook

        # Also handle thread exceptions
        import threading
        original_thread_run = threading.Thread.run

        def _thread_run_with_exception_handling(self):
            try:
                original_thread_run(self)
            except Exception as e:
                ErrorManager().handle_exception(
                    type(e), e, e.__traceback__, component=f"thread:{self.name}"
                )

        threading.Thread.run = _thread_run_with_exception_handling

    def handle_exception(
        self,
        exc_type,
        exc_value,
        exc_traceback,
        component: str = "unknown",
        recoverable: bool = True,
    ):
        """Handle an exception with full stack trace."""
        stack_trace = "".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        )
        record = ErrorRecord(
            severity=ErrorSeverity.CRITICAL,
            message=str(exc_value),
            exception_type=exc_type.__name__,
            stack_trace=stack_trace,
            component=component,
            recoverable=recoverable,
        )
        self._add_error(record)
        logger.critical(
            f"Uncaught exception in {component}: {exc_value}",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        self.error_occurred.emit(record)
        self.critical_error.emit(record)
        return record

    def report_error(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        component: str = "unknown",
        exc_info: Optional[tuple] = None,
        recoverable: bool = True,
    ):
        """Report an error without raising an exception."""
        stack_trace = None
        exception_type = None
        if exc_info:
            exc_type, exc_value, tb = exc_info
            stack_trace = "".join(traceback.format_exception(exc_type, exc_value, tb))
            exception_type = exc_type.__name__

        record = ErrorRecord(
            severity=severity,
            message=message,
            exception_type=exception_type,
            stack_trace=stack_trace,
            component=component,
            recoverable=recoverable,
        )
        self._add_error(record)
        log_func = {
            ErrorSeverity.DEBUG: logger.debug,
            ErrorSeverity.INFO: logger.info,
            ErrorSeverity.WARNING: logger.warning,
            ErrorSeverity.ERROR: logger.error,
            ErrorSeverity.CRITICAL: logger.critical,
        }[severity]
        log_func(f"Error in {component}: {message}")
        self.error_occurred.emit(record)
        return record

    def _add_error(self, record: ErrorRecord):
        """Add an error record to the history."""
        record.traceback = record.stack_trace
        self._errors.append(record)
        if len(self._errors) > self._max_errors:
            self._errors.pop(0)

    def get_errors(
        self,
        severity: Optional[ErrorSeverity] = None,
        component: Optional[str] = None,
        limit: int = 100,
    ) -> List[ErrorRecord]:
        """Get error records with optional filters."""
        errors = self._errors
        if severity:
            errors = [e for e in errors if e.severity == severity]
        if component:
            errors = [e for e in errors if e.component == component]
        return errors[-limit:]

    def clear_errors(self):
        """Clear all error history."""
        self._errors.clear()

    def clear_history(self):
        """Alias for clear_errors (for diagnostics panel)."""
        self.clear_errors()

    def get_error_history(self, limit: int = 100):
        """Get the error history (alias for get_errors)."""
        return self.get_errors(limit=limit)

    def save_history(self):
        """Save error history (for shutdown, no-op for now)."""
        pass

    def safe_execute(
        self,
        func: Callable,
        component: str = "unknown",
        fallback_return=None,
        recoverable: bool = True,
        *args,
        **kwargs,
    ):
        """Safely execute a function, catching all exceptions."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.handle_exception(
                type(e), e, e.__traceback__, component=component, recoverable=recoverable
            )
            return fallback_return


def get_error_manager() -> ErrorManager:
    """Get the global ErrorManager singleton."""
    return ErrorManager()


# ============================================================================
# SECTION: core.safe_file_ops (core/safe_file_ops.py)
# ============================================================================
"""
Safe File Operations — v1.8.5

Guarantees no file corruption:
- Atomic writes using temp files
- Pre-write validation
- Post-write verification
- Permission checks
- Locking prevention
- Backup creation
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple
from contextlib import contextmanager

from core.logger import setup_logger
from core.error_manager import get_error_manager, ErrorSeverity

logger = setup_logger(__name__)
error_manager = get_error_manager()


def safe_write_text(
    path: Path,
    content: str,
    encoding: str = "utf-8",
    create_backup: bool = True,
    verify: bool = True,
) -> bool:
    """
    Safely write text to a file using atomic replace.

    Args:
        path: Target file path
        content: Content to write
        encoding: File encoding
        create_backup: Whether to create a backup of existing file
        verify: Whether to verify the write was successful

    Returns:
        True if successful
    """
    path = Path(path).resolve()
    temp_path = None
    backup_path = None

    try:
        # 1. Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # 2. Create backup of existing file if requested
        if create_backup and path.exists():
            backup_path = path.with_suffix(path.suffix + ".bak")
            shutil.copy2(path, backup_path)

        # 3. Write to temporary file in the same directory (for atomic rename)
        temp_dir = path.parent
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            dir=temp_dir,
            prefix=f".{path.name}.tmp.",
            delete=False,
        ) as f:
            temp_path = Path(f.name)
            f.write(content)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is written to disk

        # 4. Verify the temp file if requested
        if verify:
            verify_content = temp_path.read_text(encoding=encoding)
            if verify_content != content:
                raise IOError("File content verification failed")

        # 5. Atomic replace
        if os.name == "nt":
            # Windows: Need to handle read-only files
            if path.exists():
                try:
                    os.chmod(path, 0o666)
                except OSError:
                    pass
            try:
                os.replace(temp_path, path)
            except PermissionError:
                # Fallback for Windows: copy then delete
                shutil.copy2(temp_path, path)
                temp_path.unlink()
        else:
            # Unix: Atomic rename
            os.replace(temp_path, path)

        # 6. Clean up backup if everything succeeded
        if backup_path and backup_path.exists():
            try:
                backup_path.unlink()
            except OSError:
                pass

        logger.info(f"Safely wrote file: {path}")
        return True

    except Exception as e:
        error_manager.handle_exception(
            type(e), e, e.__traceback__, component="safe_file_ops", recoverable=True
        )
        # Clean up temp file
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        # Restore backup if available
        if backup_path and backup_path.exists() and not path.exists():
            try:
                shutil.copy2(backup_path, path)
                backup_path.unlink()
            except OSError:
                pass
        return False


def safe_read_text(
    path: Path,
    encoding: str = "utf-8",
    fallback_encodings: Tuple[str, ...] = ("utf-8", "utf-16", "latin-1"),
) -> Tuple[Optional[str], Optional[str]]:
    """
    Safely read text from a file with validation and encoding fallback.

    Args:
        path: File path to read
        encoding: Primary encoding to try
        fallback_encodings: Tuple of encodings to try if primary fails

    Returns:
        Tuple of (content, actual_encoding) or (None, None) on failure
    """
    path = Path(path).resolve()

    try:
        # Validate file exists and is readable
        if not path.exists():
            error_manager.report_error(
                f"File not found: {path}",
                severity=ErrorSeverity.WARNING,
                component="safe_file_ops",
            )
            return None, None

        if not path.is_file():
            error_manager.report_error(
                f"Path is not a file: {path}",
                severity=ErrorSeverity.WARNING,
                component="safe_file_ops",
            )
            return None, None

        # Try each encoding
        for enc in fallback_encodings:
            try:
                content = path.read_text(encoding=enc)
                logger.debug(f"Read file with {enc}: {path}")
                return content, enc
            except UnicodeDecodeError:
                continue
            except OSError as e:
                error_manager.report_error(
                    f"OS error reading {path}: {e}",
                    severity=ErrorSeverity.ERROR,
                    component="safe_file_ops",
                )
                return None, None

        error_manager.report_error(
            f"Failed to decode file with any encoding: {path}",
            severity=ErrorSeverity.ERROR,
            component="safe_file_ops",
        )
        return None, None

    except Exception as e:
        error_manager.handle_exception(
            type(e), e, e.__traceback__, component="safe_file_ops", recoverable=True
        )
        return None, None


def validate_file(
    path: Path,
    max_size: Optional[int] = 10 * 1024 * 1024,  # 10 MB
) -> Tuple[bool, Optional[str]]:
    """
    Validate a file before reading/writing.

    Args:
        path: File path to validate
        max_size: Maximum allowed file size (None for unlimited)

    Returns:
        Tuple of (is_valid, error_message)
    """
    path = Path(path).resolve()

    try:
        if not path.exists():
            return False, "File does not exist"

        if not path.is_file():
            return False, "Path is not a file"

        if not os.access(path, os.R_OK):
            return False, "File is not readable"

        if max_size is not None:
            size = path.stat().st_size
            if size > max_size:
                return False, f"File too large ({size} bytes > {max_size} bytes)"

        return True, None

    except Exception as e:
        error_manager.handle_exception(
            type(e), e, e.__traceback__, component="safe_file_ops", recoverable=True
        )
        return False, str(e)


@contextmanager
def safe_file_lock(path: Path, timeout: float = 10.0):
    """
    Context manager for safe file locking (simple advisory lock).

    Args:
        path: File path to lock
        timeout: Timeout in seconds
    """
    lock_path = path.with_suffix(path.suffix + ".lock")
    acquired = False
    try:
        import time
        start = time.time()
        while time.time() - start < timeout:
            try:
                lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(lock_fd)
                acquired = True
                yield
                break
            except FileExistsError:
                time.sleep(0.1)
        if not acquired:
            raise TimeoutError(f"Could not acquire lock for {path}")
    finally:
        if acquired and lock_path.exists():
            try:
                lock_path.unlink()
            except OSError:
                pass


# ============================================================================
# SECTION: core.startup_profiler (core/startup_profiler.py)
# ============================================================================
"""
Startup Performance Profiler

Tracks timing for all initialization phases to identify bottlenecks.
Generates detailed reports showing which operations exceed the 16ms UI thread threshold.
"""

import time
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json


def _safe_print(*args, **kwargs):
    """Print safely even when stdout uses cp1252 or is detached on Windows."""
    try:
        print(*args, **kwargs)
    except Exception:
        pass


@dataclass
class TimingEntry:
    """Records timing for a single initialization step."""
    name: str
    start_time: float
    end_time: float = 0.0
    duration_ms: float = 0.0
    thread_id: int = 0
    parent: Optional[str] = None
    is_ui_thread: bool = True
    children: List[str] = field(default_factory=list)
    
    @property
    def exceeds_threshold(self) -> bool:
        """Returns True if this operation exceeds the 16ms UI thread threshold."""
        return self.is_ui_thread and self.duration_ms > 16.0


class StartupProfiler:
    """
    Profiles application startup performance.
    """
    
    def __init__(self):
        self._entries: Dict[str, TimingEntry] = {}
        self._active_stack: List[str] = []
        self._main_thread_id = threading.get_ident()
        self._app_start_time = time.perf_counter()
        self._hierarchy: Dict[str, List[str]] = {}
        
    def start(self, name: str, is_ui_thread: bool = True):
        """Start timing a phase."""
        current_time = time.perf_counter()
        thread_id = threading.get_ident()
        
        parent = self._active_stack[-1] if self._active_stack else None
        
        entry = TimingEntry(
            name=name,
            start_time=current_time,
            thread_id=thread_id,
            is_ui_thread=is_ui_thread or (thread_id == self._main_thread_id),
            parent=parent
        )
        
        self._entries[name] = entry
        self._active_stack.append(name)
        
        if parent:
            if parent not in self._hierarchy:
                self._hierarchy[parent] = []
            self._hierarchy[parent].append(name)
            
    def end(self, name: str):
        """End timing a phase."""
        current_time = time.perf_counter()
        
        if name not in self._entries:
            _safe_print(f"Warning: Timing entry '{name}' not found")
            return
            
        entry = self._entries[name]
        entry.end_time = current_time
        entry.duration_ms = (current_time - entry.start_time) * 1000
        
        if name in self._hierarchy:
            entry.children = self._hierarchy[name]
        
        if self._active_stack and self._active_stack[-1] == name:
            self._active_stack.pop()
    
    def get_total_time(self) -> float:
        """Get total elapsed time since profiler creation (ms)."""
        return (time.perf_counter() - self._app_start_time) * 1000
    
    def get_entry(self, name: str) -> Optional[TimingEntry]:
        """Get a timing entry by name."""
        return self._entries.get(name)
    
    def get_all_entries(self) -> List[TimingEntry]:
        """Get all timing entries sorted by start time."""
        return sorted(self._entries.values(), key=lambda e: e.start_time)
    
    def get_bottlenecks(self, threshold_ms: float = 16.0) -> List[TimingEntry]:
        """Get all UI thread operations exceeding the threshold."""
        return [
            entry for entry in self._entries.values()
            if entry.is_ui_thread and entry.duration_ms > threshold_ms
        ]
    
    def get_top_level_phases(self) -> List[TimingEntry]:
        """Get all top-level phases (no parent)."""
        return [entry for entry in self._entries.values() if entry.parent is None]
    
    def generate_report(self) -> Dict:
        """Generate a comprehensive timing report."""
        total_time = self.get_total_time()
        bottlenecks = self.get_bottlenecks()
        
        return {
            "total_startup_time_ms": total_time,
            "total_phases": len(self._entries),
            "bottlenecks_count": len(bottlenecks),
            "bottlenecks": [
                {
                    "name": entry.name,
                    "duration_ms": round(entry.duration_ms, 2),
                    "parent": entry.parent,
                    "thread": "UI" if entry.is_ui_thread else "Background"
                }
                for entry in sorted(bottlenecks, key=lambda e: e.duration_ms, reverse=True)
            ],
            "phases": [
                {
                    "name": entry.name,
                    "duration_ms": round(entry.duration_ms, 2),
                    "start_offset_ms": round((entry.start_time - self._app_start_time) * 1000, 2),
                    "parent": entry.parent,
                    "children": entry.children,
                    "thread": "UI" if entry.is_ui_thread else "Background",
                    "exceeds_threshold": entry.exceeds_threshold
                }
                for entry in sorted(self._entries.values(), key=lambda e: e.start_time)
            ]
        }
    
    def print_report(self):
        """Print a formatted timing report to console."""
        report = self.generate_report()
        
        _safe_print("\n" + "=" * 80)
        _safe_print("STARTUP PERFORMANCE AUDIT REPORT")
        _safe_print("=" * 80)
        _safe_print(f"\nTotal Startup Time: {report['total_startup_time_ms']:.2f} ms")
        _safe_print(f"Total Phases Tracked: {report['total_phases']}")
        _safe_print(f"UI Thread Bottlenecks (>16ms): {report['bottlenecks_count']}")
        
        if report['bottlenecks']:
            _safe_print("\n" + "-" * 80)
            _safe_print("CRITICAL BOTTLENECKS (Operations >16ms on UI thread)")
            _safe_print("-" * 80)
            _safe_print(f"{'Phase Name':<50} {'Duration':<12} {'Parent':<20}")
            _safe_print("-" * 80)
            for bottleneck in report['bottlenecks']:
                parent = bottleneck['parent'] or "ROOT"
                _safe_print(f"{bottleneck['name']:<50} {bottleneck['duration_ms']:>8.2f} ms  {parent:<20}")
        
        _safe_print("\n" + "-" * 80)
        _safe_print("ALL PHASES (Chronological Order)")
        _safe_print("-" * 80)
        _safe_print(f"{'Phase Name':<50} {'Duration':<12} {'Thread':<12} {'Status':<10}")
        _safe_print("-" * 80)
        
        for phase in report['phases']:
            status = "! SLOW" if phase['exceeds_threshold'] else "+ OK"
            thread = phase['thread']
            indent = "  " * self._get_depth(phase['name'])
            name = f"{indent}{phase['name']}"
            _safe_print(f"{name:<50} {phase['duration_ms']:>8.2f} ms  {thread:<12} {status:<10}")
        
        _safe_print("=" * 80 + "\n")
    
    def _get_depth(self, name: str) -> int:
        """Calculate the hierarchy depth of a phase."""
        depth = 0
        entry = self._entries.get(name)
        while entry and entry.parent:
            depth += 1
            entry = self._entries.get(entry.parent)
        return depth
    
    def save_report(self, filepath: str = "startup_timing.json"):
        """Save the timing report to a JSON file."""
        report = self.generate_report()
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        _safe_print(f"Timing report saved to: {output_path.absolute()}")
    
    def print_summary_table(self):
        """Print a compact summary table of major phases."""
        _safe_print("\n" + "=" * 100)
        _safe_print("STARTUP TIMING SUMMARY")
        _safe_print("=" * 100)
        _safe_print(f"{'Component':<40} {'Time (ms)':<15} {'Thread':<12} {'Status':<15}")
        _safe_print("=" * 100)
        
        categories = {
            "Application Initialization": [],
            "Core Systems": [],
            "UI Creation": [],
            "Workspace & Editor": [],
            "AI Systems": [],
            "Provider Platform": [],
            "Model Loading": [],
            "Context & Memory": [],
            "Session Restoration": [],
            "Other": []
        }
        
        for entry in self.get_all_entries():
            name_lower = entry.name.lower()
            
            if any(x in name_lower for x in ['validate_startup', 'app_init', 'qapplication']):
                categories["Application Initialization"].append(entry)
            elif any(x in name_lower for x in ['event_bus', 'error_manager', 'resource_manager', 'watchdog']):
                categories["Core Systems"].append(entry)
            elif any(x in name_lower for x in ['mainwindow', 'ui', 'theme', 'design_system', 'toolbar', 'dock', 'status', 'explorer', 'activity_bar']):
                categories["UI Creation"].append(entry)
            elif any(x in name_lower for x in ['workspace', 'editor', 'lsp']):
                categories["Workspace & Editor"].append(entry)
            elif any(x in name_lower for x in ['chat_engine', 'workflow', 'agent', 'analyzer']):
                categories["AI Systems"].append(entry)
            elif any(x in name_lower for x in ['provider', 'discovery']):
                categories["Provider Platform"].append(entry)
            elif any(x in name_lower for x in ['model', 'registry', 'catalog', 'router']):
                categories["Model Loading"].append(entry)
            elif any(x in name_lower for x in ['context', 'memory', 'index', 'graph']):
                categories["Context & Memory"].append(entry)
            elif any(x in name_lower for x in ['session', 'load_session', 'restore']):
                categories["Session Restoration"].append(entry)
            else:
                categories["Other"].append(entry)
        
        for category, entries in categories.items():
            if entries:
                total_time = sum(e.duration_ms for e in entries)
                _safe_print(f"\n{category}")
                _safe_print("-" * 100)
                for entry in sorted(entries, key=lambda e: e.duration_ms, reverse=True):
                    thread = "UI" if entry.is_ui_thread else "Background"
                    status = "! >16ms" if entry.exceeds_threshold else "+ OK"
                    _safe_print(f"  {entry.name:<38} {entry.duration_ms:>10.2f} ms  {thread:<12} {status:<15}")
                _safe_print(f"  {'Subtotal:':<38} {total_time:>10.2f} ms")
        
        _safe_print("=" * 100)


# Global singleton instance
_profiler: Optional[StartupProfiler] = None


def get_startup_profiler() -> StartupProfiler:
    """Get or create the global startup profiler instance."""
    global _profiler
    if _profiler is None:
        _profiler = StartupProfiler()
    return _profiler


def reset_profiler():
    """Reset the global profiler (useful for testing)."""
    global _profiler
    _profiler = None


class ProfilePhase:
    """Context manager for timing a phase."""
    
    def __init__(self, name: str, is_ui_thread: bool = True):
        self.name = name
        self.is_ui_thread = is_ui_thread
        self.profiler = get_startup_profiler()
    
    def __enter__(self):
        self.profiler.start(self.name, self.is_ui_thread)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.profiler.end(self.name)
        return False


# ============================================================================
# SECTION: core.startup_validator (core/startup_validator.py)
# ============================================================================
"""
Application Startup Validator — v1.8.5

Validates and repairs the application environment on startup:
- Required directories
- Configuration files
- Permissions
- Python environment
- Cache directories
- Log directories
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

from core.logger import setup_logger
from core.error_manager import get_error_manager, ErrorSeverity

logger = setup_logger(__name__)
error_manager = get_error_manager()


class ValidationStatus(Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    REPAIRED = "repaired"


@dataclass
class ValidationResult:
    component: str
    status: ValidationStatus
    message: str
    repaired: bool = False


@dataclass
class StartupReport:
    results: List[ValidationResult] = field(default_factory=list)
    success: bool = True
    warnings: int = 0
    errors: int = 0


class StartupValidator:
    """
    Validates application environment on startup.
    """

    def __init__(self):
        self.report = StartupReport()
        self.required_dirs = [
            "config",
            "config/providers",
            "logs",
        ]
        self.config_defaults = {
            "config/settings.json": {
                "theme": "dark",
                "font_size": 12,
                "auto_save": True,
            },
            "config/recent_projects.json": [],
            "config/pinned_projects.json": [],
        }

    def validate(self) -> StartupReport:
        """
        Run all startup validations.

        Returns:
            StartupReport with all validation results
        """
        logger.info("Starting application environment validation...")

        self._validate_directories()
        self._validate_config_files()
        self._validate_permissions()
        self._validate_python_environment()
        self._validate_cache()
        self._cleanup_temp()

        # Final summary
        self._finalize_report()

        logger.info("Startup validation complete")
        return self.report

    def _validate_directories(self):
        """Validate and create required directories."""
        for dir_path in self.required_dirs:
            path = Path(dir_path)
            try:
                if not path.exists():
                    path.mkdir(parents=True, exist_ok=True)
                    self.report.results.append(
                        ValidationResult(
                            component=f"directory:{dir_path}",
                            status=ValidationStatus.REPAIRED,
                            message=f"Created missing directory: {dir_path}",
                            repaired=True,
                        )
                    )
                    logger.info(f"Created directory: {dir_path}")
                elif not path.is_dir():
                    self.report.results.append(
                        ValidationResult(
                            component=f"directory:{dir_path}",
                            status=ValidationStatus.ERROR,
                            message=f"Path exists but is not a directory: {dir_path}",
                        )
                    )
                    self.report.errors += 1
                else:
                    self.report.results.append(
                        ValidationResult(
                            component=f"directory:{dir_path}",
                            status=ValidationStatus.OK,
                            message=f"Directory OK: {dir_path}",
                        )
                    )
            except Exception as e:
                error_manager.handle_exception(
                    type(e),
                    e,
                    e.__traceback__,
                    component=f"startup:directory:{dir_path}",
                    recoverable=True,
                )
                self.report.results.append(
                    ValidationResult(
                        component=f"directory:{dir_path}",
                        status=ValidationStatus.ERROR,
                        message=f"Failed to create directory: {dir_path}: {e}",
                    )
                )
                self.report.errors += 1

    def _validate_config_files(self):
        """Validate and restore config files with defaults."""
        for file_path, default_data in self.config_defaults.items():
            path = Path(file_path)
            try:
                if not path.exists():
                    # Create with defaults
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(default_data, f, indent=4)
                    self.report.results.append(
                        ValidationResult(
                            component=f"config:{file_path}",
                            status=ValidationStatus.REPAIRED,
                            message=f"Created config with defaults: {file_path}",
                            repaired=True,
                        )
                    )
                    logger.info(f"Created default config: {file_path}")
                else:
                    # Validate JSON
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            json.load(f)
                        self.report.results.append(
                            ValidationResult(
                                component=f"config:{file_path}",
                                status=ValidationStatus.OK,
                                message=f"Config OK: {file_path}",
                            )
                        )
                    except json.JSONDecodeError:
                        # Restore from backup or defaults
                        backup_path = path.with_suffix(path.suffix + ".corrupted")
                        if path.exists():
                            path.rename(backup_path)
                        with open(path, "w", encoding="utf-8") as f:
                            json.dump(default_data, f, indent=4)
                        self.report.results.append(
                            ValidationResult(
                                component=f"config:{file_path}",
                                status=ValidationStatus.REPAIRED,
                                message=f"Restored corrupted config: {file_path}",
                                repaired=True,
                            )
                        )
                        self.report.warnings += 1
                        logger.warning(f"Restored corrupted config: {file_path}")
            except Exception as e:
                error_manager.handle_exception(
                    type(e),
                    e,
                    e.__traceback__,
                    component=f"startup:config:{file_path}",
                    recoverable=True,
                )
                self.report.results.append(
                    ValidationResult(
                        component=f"config:{file_path}",
                        status=ValidationStatus.ERROR,
                        message=f"Failed to validate config: {file_path}: {e}",
                    )
                )
                self.report.errors += 1

    def _validate_permissions(self):
        """Validate read/write permissions for key directories."""
        check_paths = ["config", "logs", "cache", "temp"]
        for dir_path in check_paths:
            path = Path(dir_path)
            try:
                if not path.exists():
                    continue
                # Test write permission
                test_file = path / ".write_test"
                test_file.touch()
                test_file.unlink()
                self.report.results.append(
                    ValidationResult(
                        component=f"permissions:{dir_path}",
                        status=ValidationStatus.OK,
                        message=f"Permissions OK: {dir_path}",
                    )
                )
            except Exception as e:
                self.report.results.append(
                    ValidationResult(
                        component=f"permissions:{dir_path}",
                        status=ValidationStatus.WARNING,
                        message=f"Permission issues for {dir_path}: {e}",
                    )
                )
                self.report.warnings += 1

    def _validate_python_environment(self):
        """Validate Python version and required modules."""
        try:
            # Check Python version
            version = sys.version_info
            if version < (3, 9):
                self.report.results.append(
                    ValidationResult(
                        component="python:version",
                        status=ValidationStatus.WARNING,
                        message=f"Python {version.major}.{version.minor} detected, 3.9+ recommended",
                    )
                )
                self.report.warnings += 1
            else:
                self.report.results.append(
                    ValidationResult(
                        component="python:version",
                        status=ValidationStatus.OK,
                        message=f"Python {version.major}.{version.minor}.{version.micro} OK",
                    )
                )

            # Check core modules
            required_modules = ["PySide6"]
            for module in required_modules:
                try:
                    __import__(module)
                    self.report.results.append(
                        ValidationResult(
                            component=f"python:module:{module}",
                            status=ValidationStatus.OK,
                            message=f"Module OK: {module}",
                        )
                    )
                except ImportError:
                    self.report.results.append(
                        ValidationResult(
                            component=f"python:module:{module}",
                            status=ValidationStatus.ERROR,
                            message=f"Required module missing: {module}",
                        )
                    )
                    self.report.errors += 1
        except Exception as e:
            error_manager.handle_exception(
                type(e),
                e,
                e.__traceback__,
                component="startup:python",
                recoverable=True,
            )

    def _validate_cache(self):
        """Validate cache directories and clean old files."""
        try:
            cache_dir = Path("cache")
            if cache_dir.exists():
                # Clean old files (>7 days)
                import time
                now = time.time()
                cutoff = now - (7 * 86400)
                cleaned = 0
                for item in cache_dir.rglob("*"):
                    if item.is_file() and item.stat().st_mtime < cutoff:
                        try:
                            item.unlink()
                            cleaned += 1
                        except OSError:
                            pass
                if cleaned > 0:
                    self.report.results.append(
                        ValidationResult(
                            component="cache:cleanup",
                            status=ValidationStatus.OK,
                            message=f"Cleaned {cleaned} old cache files",
                        )
                    )
        except Exception as e:
            error_manager.handle_exception(
                type(e),
                e,
                e.__traceback__,
                component="startup:cache",
                recoverable=True,
            )

    def _cleanup_temp(self):
        """Clean up temporary files from previous runs."""
        try:
            temp_dir = Path("temp")
            if temp_dir.exists():
                removed = 0
                for item in temp_dir.iterdir():
                    try:
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
                        removed += 1
                    except OSError:
                        pass
                if removed > 0:
                    self.report.results.append(
                        ValidationResult(
                            component="temp:cleanup",
                            status=ValidationStatus.OK,
                            message=f"Cleaned {removed} temp items",
                        )
                    )
        except Exception as e:
            error_manager.handle_exception(
                type(e),
                e,
                e.__traceback__,
                component="startup:temp",
                recoverable=True,
            )

    def _finalize_report(self):
        """Finalize the report summary."""
        self.report.success = self.report.errors == 0
        logger.info(
            f"Startup validation complete: {len(self.report.results)} checks, "
            f"{self.report.warnings} warnings, {self.report.errors} errors"
        )


def run_startup_validation() -> StartupReport:
    """
    Run the complete startup validation.

    Returns:
        StartupReport with all results
    """
    validator = StartupValidator()
    return validator.validate()


# Import shutil here to avoid circular imports
import shutil


# ============================================================================
# SECTION: core.config_validator (core/config_validator.py)
# ============================================================================
"""
Configuration Validator — v1.8.5

Validates and repairs configuration files:
- JSON validation
- Schema validation
- Default values restoration
- Backup creation
- Corruption recovery
"""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass

from core.logger import setup_logger
from core.error_manager import get_error_manager, ErrorSeverity
from core.safe_file_ops import safe_write_text

logger = setup_logger(__name__)
error_manager = get_error_manager()


@dataclass
class SchemaRule:
    key: str
    type: type
    default: Any
    required: bool = False


class ConfigValidator:
    """
    Validates and repairs JSON configuration files.
    """

    _instance: Optional["ConfigValidator"] = None
    _initialized = False

    def __init__(self):
        if ConfigValidator._initialized:
            return
        super().__init__()
        self._config_dir = Path("config")
        self._defaults: Dict[str, Dict[str, Any]] = {
            "settings.json": {
                "theme": "dark",
                "font_size": 12,
                "auto_save": True,
                "show_line_numbers": True,
                "word_wrap": False,
                "tab_size": 4,
                "insert_spaces": True,
            },
            "recent_projects.json": [],
            "pinned_projects.json": [],
            "workspace_session.json": {},
            "editor_session.json": {"open_tabs": []},
            "chat_sessions.json": [],
            "recent_commands.json": [],
        }
        ConfigValidator._initialized = True

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def validate_and_load(self, filename: str) -> Dict[str, Any]:
        """
        Validate a config file, repair if needed, and return the data.

        Args:
            filename: Config filename (in config/ directory)

        Returns:
            Validated config data
        """
        file_path = self._config_dir / filename
        defaults = self._defaults.get(filename, {})

        try:
            if not file_path.exists():
                logger.info(f"Creating missing config: {filename}")
                return self._save_config(file_path, defaults)

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate and merge with defaults
            validated = self._merge_with_defaults(data, defaults)

            if validated != data:
                logger.info(f"Repaired config: {filename}")
                self._save_config(file_path, validated)

            return validated

        except json.JSONDecodeError as e:
            error_manager.report_error(
                f"Corrupted config: {filename}: {e}",
                severity=ErrorSeverity.WARNING,
                component="config_validator",
            )
            return self._recover_config(file_path, defaults)

        except Exception as e:
            error_manager.handle_exception(
                type(e),
                e,
                e.__traceback__,
                component=f"config_validator:{filename}",
                recoverable=True,
            )
            return self._recover_config(file_path, defaults)

    def _merge_with_defaults(
        self, data: Any, defaults: Any
    ) -> Any:
        """Recursively merge data with defaults."""
        if isinstance(defaults, dict):
            if not isinstance(data, dict):
                return defaults
            result = defaults.copy()
            for key, value in data.items():
                if key in defaults:
                    result[key] = self._merge_with_defaults(value, defaults[key])
                else:
                    result[key] = value
            return result
        elif isinstance(defaults, list):
            if not isinstance(data, list):
                return defaults
            return data
        else:
            # Primitive type - use data if type matches, else default
            if isinstance(data, type(defaults)):
                return data
            return defaults

    def _save_config(self, file_path: Path, data: Any) -> Any:
        """Save config data to file."""
        try:
            content = json.dumps(data, indent=4) + "\n"
            if not safe_write_text(
                file_path,
                content,
                create_backup=False,
                verify=True,
            ):
                logger.error(f"Could not save config: {file_path}")
            return data
        except Exception as e:
            error_manager.handle_exception(
                type(e),
                e,
                e.__traceback__,
                component=f"config_validator:save:{file_path.name}",
                recoverable=True,
            )
            return data

    def _recover_config(self, file_path: Path, defaults: Any) -> Any:
        """Recover a corrupted config file."""
        try:
            if file_path.exists():
                backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                shutil.copy2(file_path, backup_path)
                logger.info(f"Created backup: {backup_path}")
        except Exception as e:
            logger.debug(f"Could not create backup: {e}")

        return self._save_config(file_path, defaults)

    def save(self, filename: str, data: Any):
        """Save data to a config file."""
        file_path = self._config_dir / filename
        self._save_config(file_path, data)


def get_config_validator() -> ConfigValidator:
    """Get the global ConfigValidator singleton."""
    return ConfigValidator()


# ============================================================================
# SECTION: core.resource_manager (core/resource_manager.py)
# ============================================================================
"""
Resource Manager — v1.8.6

Tracks and manages application resources:
- Threads
- Processes
- File handles
- Network connections
- Timers
- Memory usage
- Auto-cleanup on shutdown
"""

import sys
import gc
import threading
try:
    import psutil
except ImportError:
    psutil = None
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from core.qt_compat import QObject, Signal, QTimer
from core.logger import setup_logger
from core.error_manager import get_error_manager

logger = setup_logger(__name__)
error_manager = get_error_manager()


class ResourceType(Enum):
    THREAD = "thread"
    PROCESS = "process"
    FILE_HANDLE = "file_handle"
    TIMER = "timer"
    NETWORK = "network"


@dataclass
class ResourceRecord:
    resource_id: str
    resource_type: ResourceType
    created_at: datetime
    metadata: dict
    owner: str = "unknown"


class ResourceManager(QObject):
    """
    Tracks and manages all application resources.
    """

    resource_leak_detected = Signal(ResourceRecord)
    cleanup_performed = Signal(int)

    _instance: Optional["ResourceManager"] = None
    _initialized = False

    def __init__(self):
        if ResourceManager._initialized:
            return
        super().__init__()
        self._resources: Dict[str, ResourceRecord] = {}
        self._process = psutil.Process() if psutil is not None else None
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.timeout.connect(self._periodic_cleanup)
        self._cleanup_timer.start(30000)  # 30 seconds
        self._event_bus = None
        ResourceManager._initialized = True

    def set_event_bus(self, event_bus):
        """Set the event bus for communication."""
        self._event_bus = event_bus

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register_resource(
        self,
        resource_id: str,
        resource_type: ResourceType,
        owner: str = "unknown",
        metadata: Optional[dict] = None,
    ):
        """Register a new resource for tracking."""
        record = ResourceRecord(
            resource_id=resource_id,
            resource_type=resource_type,
            created_at=datetime.now(),
            metadata=metadata or {},
            owner=owner,
        )
        self._resources[resource_id] = record
        logger.debug(f"Registered {resource_type.value}: {resource_id} (owner: {owner})")

    def unregister_resource(self, resource_id: str):
        """Unregister a resource when it's no longer needed."""
        if resource_id in self._resources:
            del self._resources[resource_id]
            logger.debug(f"Unregistered resource: {resource_id}")

    def get_resources(
        self, resource_type: Optional[ResourceType] = None
    ) -> List[ResourceRecord]:
        """Get all tracked resources, optionally filtered by type."""
        resources = list(self._resources.values())
        if resource_type:
            resources = [r for r in resources if r.resource_type == resource_type]
        return resources

    def get_memory_usage(self) -> dict:
        """Get current memory usage statistics."""
        try:
            mem_info = self._process.memory_info()
            return {
                "rss": mem_info.rss,
                "vms": mem_info.vms,
                "percent": self._process.memory_percent(),
            }
        except Exception as e:
            logger.debug(f"Could not get memory usage: {e}")
            return {}

    def get_thread_count(self) -> int:
        """Get current thread count."""
        try:
            return self._process.num_threads()
        except Exception as e:
            logger.debug(f"Could not get thread count: {e}")
            return 0

    def get_open_files(self) -> List[dict]:
        """Get list of open files."""
        try:
            files = self._process.open_files()
            return [{"path": f.path, "fd": f.fd} for f in files]
        except Exception as e:
            logger.debug(f"Could not get open files: {e}")
            return []

    def collect_garbage(self):
        """Force garbage collection."""
        try:
            gc.collect()
            logger.debug("Garbage collection completed")
        except Exception as e:
            logger.debug(f"Garbage collection failed: {e}")

    def _periodic_cleanup(self):
        """Periodic cleanup routine."""
        try:
            self.collect_garbage()
            temp_dir = Path("temp")
            if temp_dir.exists():
                import time
                now = time.time()
                cutoff = now - 3600
                cleaned = 0
                for item in temp_dir.iterdir():
                    try:
                        if item.stat().st_mtime < cutoff:
                            if item.is_file():
                                item.unlink()
                            elif item.is_dir():
                                import shutil
                                shutil.rmtree(item)
                            cleaned += 1
                    except Exception:
                        pass
                if cleaned > 0:
                    logger.debug(f"Cleaned up {cleaned} old temp items")
        except Exception as e:
            error_manager.handle_exception(
                type(e), e, e.__traceback__, component="resource_manager", recoverable=True
            )

    def cleanup_all(self):
        """Clean up all resources on shutdown."""
        logger.info("Cleaning up all resources...")
        try:
            self._cleanup_timer.stop()
        except Exception:
            pass
        count = len(self._resources)
        self._resources.clear()
        self.collect_garbage()
        self.cleanup_performed.emit(count)
        logger.info(f"Resource cleanup complete: {count} resources released")

    def get_resource_count(self):
        """Get the number of tracked resources."""
        from collections import defaultdict
        counts = defaultdict(int)
        for resource in self._resources.values():
            counts[resource.resource_type] += 1
        return counts

    def get_active_resources(self):
        """Get all active resources (for diagnostics panel)."""
        return list(self._resources.values())


def get_resource_manager() -> ResourceManager:
    """Get the global ResourceManager singleton."""
    return ResourceManager()


# ============================================================================
# SECTION: core.session_manager (core/session_manager.py)
# ============================================================================
"""
Session Manager — v1.6

Saves and restores editor session state including:
- Open files list
- Cursor positions per file
- Window layout state
- Panel visibility states
- Active file
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from core.logger import setup_logger
from core.safe_file_ops import safe_write_text

logger = setup_logger(__name__)


class SessionManager:
    """
    Manages editor session state persistence.
    """
    def __init__(self, event_bus, session_file: Path = None):
        self.event_bus = event_bus
        self.session_file = session_file or Path.home() / ".owncode" / "session.json"
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        
    def save_session(self, session_data: dict) -> bool:
        """
        Save session state to file.
        
        Args:
            session_data: Dictionary containing session state
            
        Expected structure:
        {
            "workspace": str,  # Current workspace path
            "open_files": [str],  # List of open file paths
            "active_file": str,  # Currently active file path
            "cursor_positions": {  # Cursor position per file
                "file_path": {"line": int, "column": int}
            },
            "layout": {  # Window layout state
                "explorer_visible": bool,
                "ai_panel_visible": bool,
                "bottom_dock_visible": bool,
                "bottom_dock_height": int,
                "splitter_sizes": [int]
            },
            "panels": {  # Panel states
                "active_explorer_panel": str,  # "explorer", "search", "git", etc.
                "active_dock_tab": int  # 0=terminal, 1=problems, 2=output
            }
        }
        """
        try:
            content = json.dumps(session_data, indent=2) + "\n"
            if not safe_write_text(
                self.session_file,
                content,
                create_backup=False,
                verify=True,
            ):
                return False
            logger.info(f"Session saved to {self.session_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False
            
    def load_session(self) -> Optional[dict]:
        """
        Load session state from file.
        
        Returns:
            Dictionary containing session state, or None if file doesn't exist
        """
        if not self.session_file.exists():
            logger.debug("No session file found")
            return None
            
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            if not isinstance(session_data, dict):
                raise ValueError("Session data must be a JSON object")
            logger.info(f"Session loaded from {self.session_file}")
            return session_data
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            self._quarantine_corrupt_session()
            return None

    def _quarantine_corrupt_session(self) -> None:
        """Move an unreadable session aside so it cannot break future startups."""
        corrupt_file = self.session_file.with_suffix(
            self.session_file.suffix + ".corrupt"
        )
        try:
            if self.session_file.exists():
                if corrupt_file.exists():
                    corrupt_file.unlink()
                self.session_file.replace(corrupt_file)
                logger.warning(
                    f"Quarantined unreadable session file: {corrupt_file}"
                )
        except OSError as e:
            logger.error(f"Failed to quarantine session file: {e}")
            
    def clear_session(self) -> bool:
        """
        Clear/delete the session file.
        """
        try:
            if self.session_file.exists():
                self.session_file.unlink()
                logger.info("Session cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear session: {e}")
            return False
            
    def get_recent_workspaces(self, max_count: int = 10) -> List[str]:
        """
        Get list of recent workspaces from session history.
        
        Returns:
            List of workspace paths (most recent first)
        """
        history_file = self.session_file.parent / "workspace_history.json"
        
        if not history_file.exists():
            return []
            
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            workspaces = history.get("workspaces", [])
            return workspaces[:max_count]
        except Exception as e:
            logger.error(f"Failed to load workspace history: {e}")
            return []
            
    def add_recent_workspace(self, workspace_path: str):
        """
        Add workspace to recent history.
        """
        history_file = self.session_file.parent / "workspace_history.json"
        
        # Load existing history
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                if not isinstance(history, dict):
                    raise ValueError("Workspace history must be a JSON object")
            except (OSError, ValueError, json.JSONDecodeError):
                history = {"workspaces": []}
        else:
            history = {"workspaces": []}
            
        workspaces = history.get("workspaces", [])
        
        # Remove if already exists (to move to front)
        if workspace_path in workspaces:
            workspaces.remove(workspace_path)
            
        # Add to front
        workspaces.insert(0, workspace_path)
        
        # Limit to 20 recent workspaces
        workspaces = workspaces[:20]
        
        history["workspaces"] = workspaces
        
        # Save
        try:
            content = json.dumps(history, indent=2) + "\n"
            if not safe_write_text(
                history_file,
                content,
                create_backup=False,
                verify=True,
            ):
                return
            logger.debug(f"Added workspace to history: {workspace_path}")
        except Exception as e:
            logger.error(f"Failed to save workspace history: {e}")
            
    def create_session_snapshot(
        self,
        workspace: Optional[str] = None,
        open_files: Optional[List[str]] = None,
        active_file: Optional[str] = None,
        cursor_positions: Optional[Dict[str, Dict[str, int]]] = None,
        layout: Optional[dict] = None,
        panels: Optional[dict] = None
    ) -> dict:
        """
        Create a session snapshot from provided data.
        
        Convenience method to build session_data dictionary.
        """
        return {
            "workspace": workspace or "",
            "open_files": open_files or [],
            "active_file": active_file or "",
            "cursor_positions": cursor_positions or {},
            "layout": layout or {
                "explorer_visible": True,
                "ai_panel_visible": True,
                "bottom_dock_visible": True,
                "bottom_dock_height": 180,
                "splitter_sizes": [240, 860, 320]
            },
            "panels": panels or {
                "active_explorer_panel": "explorer",
                "active_dock_tab": 0
            }
        }


# ============================================================================
# SECTION: core.performance_watchdog (core/performance_watchdog.py)
# ============================================================================
"""
Performance Watchdog — v1.8.6

Monitors application performance:
- Memory usage
- CPU usage
- UI responsiveness
- Long operations
- Deadlock detection
- Event loop health
"""

import time
try:
    import psutil
except ImportError:
    psutil = None
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from core.qt_compat import QObject, Signal, QTimer
from core.logger import setup_logger
from core.error_manager import get_error_manager

logger = setup_logger(__name__)
error_manager = get_error_manager()


@dataclass
class PerformanceSnapshot:
    timestamp: datetime
    memory_rss: int
    memory_percent: float
    cpu_percent: float
    thread_count: int
    open_files: int
    event_loop_lag: float


@dataclass
class CurrentMetrics:
    memory_used_mb: float
    memory_percent: float
    cpu_percent: float
    thread_count: int
    object_count: int


class PerformanceWatchdog(QObject):
    """
    Monitors application performance and reports issues.
    """

    health_warning = Signal(str)
    snapshot_taken = Signal(PerformanceSnapshot)

    _instance: Optional["PerformanceWatchdog"] = None
    _initialized = False

    def __init__(self):
        if PerformanceWatchdog._initialized:
            return
        super().__init__()
        self._process = psutil.Process() if psutil is not None else None
        self._snapshots: List[PerformanceSnapshot] = []
        self._max_snapshots = 100
        self._monitor_timer = QTimer(self)
        self._monitor_timer.timeout.connect(self._take_snapshot)
        self._monitor_interval = 5000  # 5 seconds
        self._ui_lag_threshold = 0.25  # 250ms
        self._last_tick = time.time()
        self._event_bus = None
        PerformanceWatchdog._initialized = True

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def set_event_bus(self, event_bus):
        """Set the event bus for communication."""
        self._event_bus = event_bus

    def start(self):
        """Start monitoring."""
        self._last_tick = time.time()
        self._monitor_timer.start(self._monitor_interval)
        logger.info("Performance watchdog started")

    def stop(self):
        """Stop monitoring."""
        self._monitor_timer.stop()
        logger.info("Performance watchdog stopped")

    def _take_snapshot(self):
        """Take a performance snapshot without blocking on Windows file-handle enumeration."""
        try:
            now = time.time()
            lag = now - self._last_tick - (self._monitor_interval / 1000.0)
            self._last_tick = now

            mem_info = self._process.memory_info()
            snapshot = PerformanceSnapshot(
                timestamp=datetime.now(),
                memory_rss=mem_info.rss,
                memory_percent=self._process.memory_percent(),
                cpu_percent=self._process.cpu_percent(),
                thread_count=self._process.num_threads(),
                open_files=0,  # Avoid psutil.open_files() which stalls the Windows UI thread
                event_loop_lag=max(0.0, lag),
            )

            self._snapshots.append(snapshot)
            if len(self._snapshots) > self._max_snapshots:
                self._snapshots.pop(0)

            self.snapshot_taken.emit(snapshot)
            self._check_snapshot(snapshot)

        except Exception as e:
            logger.debug(f"Could not take performance snapshot: {e}")

    def _check_snapshot(self, snapshot: PerformanceSnapshot):
        """Check snapshot for potential issues."""
        warnings = []

        if snapshot.memory_percent > 85:
            warnings.append(f"High memory usage: {snapshot.memory_percent:.1f}%")

        if snapshot.cpu_percent > 92:
            warnings.append(f"High CPU usage: {snapshot.cpu_percent:.1f}%")

        if snapshot.event_loop_lag > self._ui_lag_threshold:
            warnings.append(f"UI lag detected: {snapshot.event_loop_lag*1000:.0f}ms")

        if snapshot.thread_count > 120:
            warnings.append(f"High thread count: {snapshot.thread_count}")

        for warning in warnings:
            logger.warning(warning)
            self.health_warning.emit(warning)

    def get_latest_snapshot(self) -> Optional[PerformanceSnapshot]:
        """Get the most recent snapshot."""
        return self._snapshots[-1] if self._snapshots else None

    def get_current_metrics(self) -> Optional[CurrentMetrics]:
        """Get current performance metrics."""
        import gc
        try:
            mem_info = self._process.memory_info()
            return CurrentMetrics(
                memory_used_mb=mem_info.rss / (1024 * 1024),
                memory_percent=self._process.memory_percent(),
                cpu_percent=self._process.cpu_percent(),
                thread_count=self._process.num_threads(),
                object_count=len(gc.get_objects())
            )
        except Exception as e:
            logger.debug(f"Could not get current metrics: {e}")
            return None

    def get_statistics(self) -> Dict[str, any]:
        """Get performance statistics from stored snapshots."""
        if not self._snapshots:
            return {}

        snapshots = self._snapshots
        return {
            "samples": len(snapshots),
            "memory": {
                "min": min(s.memory_percent for s in snapshots),
                "max": max(s.memory_percent for s in snapshots),
                "avg": sum(s.memory_percent for s in snapshots) / len(snapshots)
            },
            "cpu": {
                "min": min(s.cpu_percent for s in snapshots),
                "max": max(s.cpu_percent for s in snapshots),
                "avg": sum(s.cpu_percent for s in snapshots) / len(snapshots)
            }
        }


def get_performance_watchdog() -> PerformanceWatchdog:
    """Get the global PerformanceWatchdog singleton."""
    return PerformanceWatchdog()


# ============================================================================
# SECTION: core.background_initializer (core/background_initializer.py)
# ============================================================================
"""
Background Initialization System

Manages initialization of heavy systems in background threads after the UI is shown.
Provides progress tracking and enables features as they become ready.
"""

from core.qt_compat import QThread, Signal, QObject
from typing import Callable, Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

from core.logger import setup_logger

logger = setup_logger(__name__)


class InitState(Enum):
    """Initialization state for a component."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class InitTask:
    """Represents a background initialization task."""
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: int = 0  # Higher priority runs first
    dependencies: List[str] = field(default_factory=list)
    state: InitState = InitState.PENDING
    result: Any = None
    error: Optional[Exception] = None
    duration_ms: float = 0.0


class BackgroundInitWorker(QThread):
    """Worker thread for background initialization."""

    task_started = Signal(str)  # task_name
    task_completed = Signal(str, object)  # task_name, result
    task_failed = Signal(str, Exception)  # task_name, error
    all_completed = Signal()
    progress_updated = Signal(int, int)  # completed, total

    def __init__(self, tasks: List[InitTask]):
        super().__init__()
        self.tasks = {task.name: task for task in tasks}
        self.completed_tasks: set = set()
        self.failed_tasks: set = set()
        self._stop_requested = False

    def run(self):
        """Execute ready tasks concurrently while respecting dependencies."""
        logger.info(f"Background initialization started with {len(self.tasks)} tasks")

        pending = set(self.tasks)
        running = {}
        with ThreadPoolExecutor(max_workers=max(1, min(4, len(pending))),
                                thread_name_prefix="init") as executor:
            while pending or running:
                if self._stop_requested:
                    for future in running:
                        future.cancel()
                    break

                ready = sorted(
                    (self.tasks[name] for name in pending
                     if self._dependencies_met(self.tasks[name])),
                    key=lambda task: task.priority,
                    reverse=True,
                )
                for task in ready:
                    pending.remove(task.name)
                    running[executor.submit(self._execute_task, task)] = task.name

                if not running:
                    for name in pending:
                        self.tasks[name].state = InitState.SKIPPED
                    logger.warning("Initialization stopped: unresolved dependency graph")
                    break

                done, _ = wait(tuple(running), return_when=FIRST_COMPLETED)
                for future in done:
                    running.pop(future, None)
                    future.result()
                    completed = (len(self.completed_tasks) + len(self.failed_tasks)
                                 + sum(task.state == InitState.SKIPPED
                                       for task in self.tasks.values()))
                    self.progress_updated.emit(completed, len(self.tasks))

        logger.info(f"Background initialization completed: {len(self.completed_tasks)} succeeded, {len(self.failed_tasks)} failed")
        self.all_completed.emit()

    def _dependencies_met(self, task: InitTask) -> bool:
        """Check if all dependencies are completed."""
        for dep_name in task.dependencies:
            if dep_name not in self.completed_tasks:
                return False
        return True

    def _execute_task(self, task: InitTask):
        """Execute a single task."""
        try:
            logger.info(f"Background task starting: {task.name}")
            task.state = InitState.IN_PROGRESS
            self.task_started.emit(task.name)

            start_time = time.perf_counter()
            result = task.func(*task.args, **task.kwargs)
            duration = (time.perf_counter() - start_time) * 1000

            task.result = result
            task.duration_ms = duration
            task.state = InitState.COMPLETED
            self.completed_tasks.add(task.name)

            logger.info(f"Background task completed: {task.name} ({duration:.2f}ms)")
            self.task_completed.emit(task.name, result)

        except Exception as e:
            task.error = e
            task.state = InitState.FAILED
            self.failed_tasks.add(task.name)

            logger.error(f"Background task failed: {task.name} - {str(e)}")
            self.task_failed.emit(task.name, e)

    def stop(self):
        """Request the worker to stop."""
        self._stop_requested = True


class BackgroundInitializer(QObject):
    """Manages background initialization of heavy systems."""

    task_started = Signal(str)
    task_completed = Signal(str, object)
    task_failed = Signal(str, Exception)
    all_completed = Signal()
    progress_updated = Signal(int, int)

    def __init__(self):
        super().__init__()
        self.tasks: List[InitTask] = []
        self.worker: Optional[BackgroundInitWorker] = None
        self._is_running = False

    def add_task(self,
                 name: str,
                 func: Callable,
                 *args,
                 priority: int = 0,
                 dependencies: Optional[List[str]] = None,
                 **kwargs):
        """Add a background initialization task."""
        task = InitTask(
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            dependencies=dependencies or []
        )
        self.tasks.append(task)
        logger.debug(f"Added background task: {name} (priority={priority})")

    def start(self):
        """Start background initialization."""
        if self._is_running:
            logger.warning("Background initialization already running")
            return

        if not self.tasks:
            logger.warning("No background tasks to execute")
            return

        self._is_running = True

        self.worker = BackgroundInitWorker(self.tasks)
        self.worker.task_started.connect(self.task_started.emit)
        self.worker.task_completed.connect(self.task_completed.emit)
        self.worker.task_failed.connect(self.task_failed.emit)
        self.worker.all_completed.connect(self._on_all_completed)
        self.worker.progress_updated.connect(self.progress_updated.emit)

        logger.info("Starting background initialization worker")
        self.worker.start()

    def _on_all_completed(self):
        """Handle completion of all tasks."""
        self._is_running = False
        self.all_completed.emit()

    def stop(self):
        """Stop background initialization."""
        if self.worker and self.worker.isRunning():
            logger.info("Stopping background initialization")
            self.worker.stop()
            self.worker.wait(5000)

    def is_running(self) -> bool:
        """Check if initialization is in progress."""
        return self._is_running

    def get_status(self) -> Dict[str, Any]:
        """Get current status of all tasks."""
        if not self.worker:
            return {"state": "not_started", "tasks": []}

        return {
            "state": "running" if self._is_running else "completed",
            "completed": len(self.worker.completed_tasks),
            "failed": len(self.worker.failed_tasks),
            "total": len(self.tasks),
            "tasks": [
                {
                    "name": task.name,
                    "state": task.state.value,
                    "duration_ms": task.duration_ms,
                    "error": str(task.error) if task.error else None
                }
                for task in self.tasks
            ]
        }

