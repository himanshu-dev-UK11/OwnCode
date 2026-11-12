"""
Consolidated Module: core.event_and_compat

Combines: core.qt_compat, core.logger, core.exceptions, core.event_bus
"""
from __future__ import annotations
import sys as _sys
import core
for _alias in ['core.qt_compat', 'core.logger', 'core.exceptions', 'core.event_bus']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: core.qt_compat (core/qt_compat.py)
# ============================================================================
"""
Qt Compatibility Layer — v1.0

Uses real PySide6 classes whenever PySide6 is installed, and falls back to
lightweight pure-Python equivalents in headless CLI/CI environments where
PySide6 is not installed.
"""

import subprocess
import threading
from typing import Any, Callable, Dict, List, Optional

try:
    from PySide6.QtCore import (
        QCoreApplication,
        QFileSystemWatcher,
        QObject,
        QProcess,
        QSize,
        Qt,
        QThread,
        QTimer,
        QUrl,
        Signal,
    )
    PYSIDE6_AVAILABLE = True
except ImportError:  # pragma: no cover - headless fallback
    PYSIDE6_AVAILABLE = False

    class _BoundSignal:
        def __init__(self):
            self._slots: List[Callable] = []

        def connect(self, slot: Callable, *_args, **_kwargs):
            if slot not in self._slots:
                self._slots.append(slot)

        def disconnect(self, slot: Optional[Callable] = None):
            if slot is None:
                self._slots.clear()
            elif slot in self._slots:
                self._slots.remove(slot)

        def emit(self, *args, **kwargs):
            for slot in list(self._slots):
                slot(*args, **kwargs)

    class Signal:  # type: ignore[no-redef]
        def __init__(self, *_types):
            self._name = ""

        def __set_name__(self, owner, name):
            self._name = f"__signal_{name}"

        def __get__(self, instance, owner=None):
            if instance is None:
                return self
            sig = instance.__dict__.get(self._name)
            if sig is None:
                sig = _BoundSignal()
                instance.__dict__[self._name] = sig
            return sig

    class _QtMeta(type):
        def __getattr__(cls, _name: str) -> int:
            return 0

    class Qt(metaclass=_QtMeta):  # type: ignore[no-redef]
        QueuedConnection = 2
        DirectConnection = 1
        AutoConnection = 0
        UserRole = 256

    class QObject:  # type: ignore[no-redef]
        def __init__(self, parent: Any = None):
            self._parent = parent

        def moveToThread(self, _thread: Any):
            pass

        def deleteLater(self):
            pass

        def thread(self):
            return None

    class QCoreApplication(QObject):  # type: ignore[no-redef]
        _inst: Optional["QCoreApplication"] = None

        def __init__(self, args=None):
            super().__init__()
            self._quit_event = threading.Event()
            QCoreApplication._inst = self

        @classmethod
        def instance(cls):
            return cls._inst

        def exec(self):
            self._quit_event.wait(timeout=5.0)
            self._quit_event.clear()
            return 0

        def quit(self):
            self._quit_event.set()

    class QTimer(QObject):  # type: ignore[no-redef]
        timeout = Signal()

        def __init__(self, parent: Any = None):
            super().__init__(parent)
            self._single = False
            self._interval = 0
            self._active = False

        def setSingleShot(self, single: bool):
            self._single = bool(single)

        def setInterval(self, msec: int):
            self._interval = int(msec)

        def start(self, msec: Optional[int] = None):
            if msec is not None:
                self._interval = int(msec)
            self._active = True

        def stop(self):
            self._active = False

        def isActive(self) -> bool:
            return self._active

        @staticmethod
        def singleShot(msec: int, callback: Callable):
            if msec <= 0:
                callback()
            else:
                t = threading.Timer(msec / 1000.0, callback)
                t.daemon = True
                t.start()

    class QThread(QObject):  # type: ignore[no-redef]
        def __init__(self, parent: Any = None):
            super().__init__(parent)
            self._running = False

        def start(self):
            self._running = True
            try:
                self.run()
            finally:
                self._running = False

        def run(self):
            pass

        def isRunning(self) -> bool:
            return self._running

        def wait(self, _msecs: int = 0) -> bool:
            return True

    class QFileSystemWatcher(QObject):  # type: ignore[no-redef]
        fileChanged = Signal(str)
        directoryChanged = Signal(str)

        def __init__(self, parent: Any = None):
            super().__init__(parent)
            self._files: List[str] = []

        def addPath(self, path: str) -> bool:
            if path not in self._files:
                self._files.append(path)
            return True

        def removePath(self, path: str) -> bool:
            if path in self._files:
                self._files.remove(path)
            return True

        def files(self) -> List[str]:
            return list(self._files)

    class _ByteArray:
        def __init__(self, data: bytes):
            self._data = data

        def data(self) -> bytes:
            return self._data

        def __bytes__(self) -> bytes:
            return self._data

    class QProcess(QObject):  # type: ignore[no-redef]
        NotRunning = 0
        Starting = 1
        Running = 2
        FailedToStart = 0
        Crashed = 1
        NormalExit = 0
        MergedChannels = 1

        readyReadStandardOutput = Signal()
        readyReadStandardError = Signal()
        finished = Signal(int, int)
        errorOccurred = Signal(int)

        def __init__(self, parent: Any = None):
            super().__init__(parent)
            self._cwd: Optional[str] = None
            self._state = self.NotRunning
            self._stdout = b""
            self._stderr = b""
            self._program = ""
            self._proc: Optional[subprocess.Popen] = None

        def setWorkingDirectory(self, path: str):
            self._cwd = path

        def setProcessChannelMode(self, _mode: int):
            pass

        def processEnvironment(self) -> Dict[str, str]:
            return {}

        def setProcessEnvironment(self, _env: Any):
            pass

        def state(self) -> int:
            if self._proc is not None and self._proc.poll() is None:
                return self.Running
            return self._state

        def program(self) -> str:
            return self._program

        def processId(self) -> int:
            return self._proc.pid if self._proc else 0

        def start(self, program: str, args: Optional[List[str]] = None):
            from core.process_utils import hidden_subprocess_kwargs
            self._program = program
            cmd = [program] + list(args or [])
            try:
                res = subprocess.run(
                    cmd,
                    cwd=self._cwd,
                    capture_output=True,
                    timeout=10,
                    **hidden_subprocess_kwargs(),
                )
                self._stdout = res.stdout or b""
                self._stderr = res.stderr or b""
                self._state = self.NotRunning
                if self._stdout:
                    self.readyReadStandardOutput.emit()
                if self._stderr:
                    self.readyReadStandardError.emit()
                self.finished.emit(res.returncode, self.NormalExit)
            except FileNotFoundError:
                self._state = self.NotRunning
                self.errorOccurred.emit(self.FailedToStart)
            except Exception:
                self._state = self.NotRunning
                self.errorOccurred.emit(self.Crashed)

        def write(self, data: bytes):
            pass

        def waitForStarted(self, _msecs: int = 3000) -> bool:
            return True

        def waitForFinished(self, _msecs: int = 3000) -> bool:
            return True

        def terminate(self):
            self._state = self.NotRunning

        def kill(self):
            self._state = self.NotRunning

        def readAllStandardOutput(self) -> _ByteArray:
            out, self._stdout = self._stdout, b""
            return _ByteArray(out)


        def readAllStandardError(self) -> _ByteArray:
            err, self._stderr = self._stderr, b""
            return _ByteArray(err)

    import sys as _sys
    import types as _types

    class _DummyQtClass(QObject, metaclass=_QtMeta):
        def __init__(self, *args, **kwargs):
            super().__init__()
        @classmethod
        def instance(cls):
            return None
        @classmethod
        def clipboard(cls):
            return _DummyQtClass()
        @classmethod
        def processEvents(cls, *args, **kwargs):
            pass
        def __getattr__(self, name):
            if name.startswith("__") and name.endswith("__"):
                raise AttributeError(name)
            return _DummyQtClass()
        def __call__(self, *args, **kwargs):
            return _DummyQtClass()
        def __or__(self, other):
            return 0
        def __ror__(self, other):
            return 0
        def __and__(self, other):
            return 0
        def __bool__(self):
            return False
        def __int__(self):
            return 0

    class _QtModuleStub(_types.ModuleType):
        def __getattr__(self, name):
            if name.startswith("__") and name.endswith("__"):
                raise AttributeError(name)
            return _DummyQtClass

    _qt_pkg = _QtModuleStub("PySide6")
    _qt_core = _QtModuleStub("PySide6.QtCore")
    for _k, _v in {
        "QCoreApplication": QCoreApplication,
        "QFileSystemWatcher": QFileSystemWatcher,
        "QObject": QObject,
        "QProcess": QProcess,
        "Qt": Qt,
        "QThread": QThread,
        "QTimer": QTimer,
        "Signal": Signal,
    }.items():
        setattr(_qt_core, _k, _v)
    _qt_gui = _QtModuleStub("PySide6.QtGui")
    _qt_widgets = _QtModuleStub("PySide6.QtWidgets")
    _qt_pkg.QtCore = _qt_core
    _qt_pkg.QtGui = _qt_gui
    _qt_pkg.QtWidgets = _qt_widgets
    _sys.modules.setdefault("PySide6", _qt_pkg)
    _sys.modules.setdefault("PySide6.QtCore", _qt_core)
    _sys.modules.setdefault("PySide6.QtGui", _qt_gui)
    _sys.modules.setdefault("PySide6.QtWidgets", _qt_widgets)



# ============================================================================
# SECTION: core.logger (core/logger.py)
# ============================================================================
"""
Centralized structured logging system — v1.8.5

Enhanced with:
- File logging with automatic rotation
- Log compression for old files
- Log level configuration
- Structured log format
- Memory-efficient log management
"""

import logging
import logging.handlers
import sys
import gzip
import shutil
from pathlib import Path
from typing import Optional

# Global log level
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
DEFAULT_BACKUP_COUNT = 5  # Keep up to 5 rotated logs


def namer(name):
    """Custom namer for rotated log files."""
    return name + ".gz"


def rotator(source, dest):
    """Custom rotator that compresses rotated logs with gzip."""
    with open(source, "rb") as f_in:
        with gzip.open(dest, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    Path(source).unlink()


def setup_logger(
    name: str,
    log_level: int = DEFAULT_LOG_LEVEL,
    log_dir: str = "logs",
    max_bytes: int = DEFAULT_MAX_FILE_SIZE,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> logging.Logger:
    """
    Creates and configures a standard logger for a module.
    
    Args:
        name: Module name for logger
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
        max_bytes: Max size per log file before rotation
        backup_count: Number of rotated log files to keep
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger
    
    # Create log directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Log format
    formatter = logging.Formatter(
        "%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Console handler (for development)
    # Wrap sys.stdout in a UTF-8 stream to prevent UnicodeEncodeError on
    # Windows, where the default encoding (cp1252) cannot represent many
    # Unicode symbols commonly used in log messages (✓, ⚠, ✅, etc.).
    import io
    if sys.stdout is not None and hasattr(sys.stdout, "buffer"):
        try:
            utf8_stdout = io.TextIOWrapper(
                sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
            )
            console_handler = logging.StreamHandler(utf8_stdout)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        except Exception:
            pass
    
    # File handler with rotation and compression
    log_file = log_path / "app.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Attach custom rotator and namer for compression
    file_handler.rotator = rotator
    file_handler.namer = namer
    
    logger.addHandler(file_handler)
    
    # Also log uncaught exceptions
    def _handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
    
    sys.excepthook = _handle_exception
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get an existing logger or create a new one with default settings.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger


def set_global_log_level(level: int):
    """
    Set the log level for all existing loggers.
    """
    for logger in logging.Logger.manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            logger.setLevel(level)


def clean_old_logs(log_dir: str = "logs", keep_days: int = 30):
    """
    Clean up log files older than the specified number of days.
    """
    import time
    
    log_path = Path(log_dir)
    if not log_path.exists():
        return
    
    now = time.time()
    cutoff = now - (keep_days * 86400)
    
    for log_file in log_path.glob("*.log*"):
        if log_file.stat().st_mtime < cutoff:
            try:
                log_file.unlink()
            except Exception:
                pass


# ============================================================================
# SECTION: core.exceptions (core/exceptions.py)
# ============================================================================
"""
Custom application exceptions.

Provides clear, recognizable error types for easier debugging and crash reporting.
"""

class OwnCodeError(Exception):
    """Base exception for all application errors."""
    pass

class ModelTimeoutError(OwnCodeError):
    """Raised when an AI model takes too long to respond."""
    pass

class ToolExecutionError(OwnCodeError):
    """Raised when a tool (e.g., terminal, file) fails to execute."""
    pass

class ConfigurationError(OwnCodeError):
    """Raised when configuration is invalid or missing."""
    pass

class ProviderError(OwnCodeError):
    """Raised when a provider operation fails."""
    pass


# ============================================================================
# SECTION: core.event_bus (core/event_bus.py)
# ============================================================================
"""
Event Bus for asynchronous communication — v1.8

Decouples UI from heavy processing. Ensures UI callbacks ALWAYS execute on the
Qt main thread when a Qt application is running, while also supporting direct
synchronous dispatch in headless unit tests.
"""

import threading
from core.qt_compat import PYSIDE6_AVAILABLE, QCoreApplication, QObject, Qt, Signal
from core.logger import setup_logger

logger = setup_logger(__name__)


class EventBus(QObject):
    """
    Manages pub/sub event distribution across the app.
    Uses Qt's thread-safe signal system to ensure UI updates happen on main thread.
    """

    event_signal = Signal(str, dict)  # event_type, data

    def __init__(self):
        super().__init__()
        self.subscribers = {}
        self._lock = threading.RLock()
        if PYSIDE6_AVAILABLE:
            self.event_signal.connect(self._dispatch_event, Qt.QueuedConnection)
        else:
            self.event_signal.connect(self._dispatch_event)

    def subscribe(self, event_type: str, callback):
        """Register a callback for a specific event type."""
        with self._lock:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            if callback not in self.subscribers[event_type]:
                self.subscribers[event_type].append(callback)
        logger.debug(f"New subscriber added for event: {event_type}")

    def unsubscribe(self, event_type: str, callback):
        """Remove a registered callback for an event type."""
        with self._lock:
            if event_type in self.subscribers and callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)

    def publish(self, event_type: str, data: dict = None):
        """
        Broadcast an event to all subscribers.
        Uses Qt's QueuedConnection when an active QCoreApplication exists,
        or dispatches directly when running in a headless/no-event-loop test.
        """
        payload = data if isinstance(data, dict) else (data or {})
        logger.debug(f"Publishing event: {event_type}")
        if PYSIDE6_AVAILABLE and QCoreApplication.instance() is not None:
            # If called on the main thread, QueuedConnection still works with an
            # active event loop; if no event loop is spinning yet in a unit test
            # on the same thread, dispatch directly if needed.
            try:
                app = QCoreApplication.instance()
                if app is not None and threading.current_thread() is threading.main_thread():
                    self._dispatch_event(event_type, payload)
                    return
            except Exception:
                pass
            self.event_signal.emit(event_type, payload)
        else:
            self._dispatch_event(event_type, payload)

    def _dispatch_event(self, event_type: str, data: dict):
        """Internal dispatch method that runs callbacks safely."""
        with self._lock:
            callbacks = list(self.subscribers.get(event_type, ()))
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in event callback for {event_type}: {e}", exc_info=True)

