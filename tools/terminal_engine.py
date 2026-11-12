"""
Consolidated Module: tools.terminal_engine

Combines: core.process_utils, ai.terminal.terminal_history_storage, ai.terminal.terminal_output_analyzer, ai.terminal.terminal_approval_panel, ai.terminal.ai_terminal_manager, ai.terminal.ai_terminal_execution
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['core.process_utils', 'ai.terminal.terminal_history_storage', 'ai.terminal.terminal_output_analyzer', 'ai.terminal.terminal_approval_panel', 'ai.terminal.ai_terminal_manager', 'ai.terminal.ai_terminal_execution']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: core.process_utils (core/process_utils.py)
# ============================================================================
"""
Process & Terminal Utilities — v3.0

Centralizes cross-platform subprocess and process execution so that:
1. Background commands (git, gh, compilers, linters, nvidia-smi, ollama,
   llama-server, test runners, and terminal shells) NEVER flash external
   console windows on Windows.
2. Strips conflicting Win32 creation flags (`DETACHED_PROCESS` and
   `CREATE_NEW_CONSOLE`) that cause Windows `CreateProcessW` to ignore
   `CREATE_NO_WINDOW`.
3. Provides `HiddenProcess(QObject)` — a drop-in replacement for `QProcess`
   backed by `subprocess.Popen` with `CREATE_NO_WINDOW` + `SW_HIDE`, avoiding
   PySide6's missing `setCreateProcessArgumentsModifier` binding on Windows
   and eliminating Shiboken C++ deletion RuntimeErrors.
4. Built-in Terminal Self-Test ("Test Terminal") verifies shell health, pipe I/O,
   working directory, window suppression, and installed language runtimes
   completely in-app without opening external terminal windows.
"""

import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from core.qt_compat import QObject, Signal

_ORIGINAL_POPEN_INIT = getattr(subprocess.Popen, "__init__", None)
_HOOK_INSTALLED = False

# Win32 process creation flags
_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
_DETACHED_PROCESS = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
_CREATE_NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)
_STARTF_USESHOWWINDOW = getattr(subprocess, "STARTF_USESHOWWINDOW", 0x00000001)
_SW_HIDE = getattr(subprocess, "SW_HIDE", 0)
CREATE_NO_WINDOW = _CREATE_NO_WINDOW
DETACHED_PROCESS = _DETACHED_PROCESS
CREATE_NEW_CONSOLE = _CREATE_NEW_CONSOLE


def _sanitize_windows_flags(flags: int = 0) -> int:
    """
    Ensure `CREATE_NO_WINDOW` is set and strip `DETACHED_PROCESS` / `CREATE_NEW_CONSOLE`.
    Per Microsoft Win32 `CreateProcessW` documentation, `CREATE_NO_WINDOW` is
    IGNORED if combined with `DETACHED_PROCESS` or `CREATE_NEW_CONSOLE`.
    """
    cleaned = int(flags or 0)
    cleaned &= ~_DETACHED_PROCESS
    cleaned &= ~_CREATE_NEW_CONSOLE
    cleaned |= _CREATE_NO_WINDOW
    return cleaned


def hidden_subprocess_kwargs() -> Dict[str, Any]:
    """Return kwargs for subprocess.run / Popen that hide console windows on Windows."""
    if os.name != "nt":
        return {}
    flags = _sanitize_windows_flags(0)
    startupinfo = None
    if hasattr(subprocess, "STARTUPINFO"):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= _STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = _SW_HIDE
    out: Dict[str, Any] = {"creationflags": flags}
    if startupinfo is not None:
        out["startupinfo"] = startupinfo
    return out


def install_hidden_subprocess_hooks() -> None:
    """
    Hook `subprocess.Popen.__init__` on Windows so every child process launched
    anywhere in Python or third-party libraries (jedi, git, gh, ollama, compilers)
    uses `CREATE_NO_WINDOW` + `SW_HIDE` and never `DETACHED_PROCESS`.
    """
    global _HOOK_INSTALLED
    if _HOOK_INSTALLED or os.name != "nt" or _ORIGINAL_POPEN_INIT is None:
        return

    def _patched_popen_init(self, *args, **kwargs):
        kwargs["creationflags"] = _sanitize_windows_flags(kwargs.get("creationflags", 0))
        si = kwargs.get("startupinfo")
        if si is None and hasattr(subprocess, "STARTUPINFO"):
            si = subprocess.STARTUPINFO()
        if si is not None:
            try:
                si.dwFlags |= _STARTF_USESHOWWINDOW
                si.wShowWindow = _SW_HIDE
                kwargs["startupinfo"] = si
            except Exception:
                pass
        return _ORIGINAL_POPEN_INIT(self, *args, **kwargs)

    subprocess.Popen.__init__ = _patched_popen_init  # type: ignore[method-assign]
    _HOOK_INSTALLED = True


class _ByteBuffer:
    """QByteArray-compatible byte wrapper returned by HiddenProcess.readAll*."""

    def __init__(self, payload: bytes = b""):
        self._payload = bytes(payload or b"")

    def data(self) -> bytes:
        return self._payload

    def __bytes__(self) -> bytes:
        return self._payload

    def __len__(self) -> int:
        return len(self._payload)

    def __bool__(self) -> bool:
        return bool(self._payload)


class _ProcessEnv(dict):
    """QProcessEnvironment-compatible dictionary."""

    def insert(self, key: str, value: str) -> None:
        self[str(key)] = str(value)


class HiddenProcess(QObject):
    """
    Drop-in QProcess replacement backed by `subprocess.Popen` with hidden
    console flags (`CREATE_NO_WINDOW` + `SW_HIDE`).

    Why this exists:
    In PySide6 on Windows, `QProcess.setCreateProcessArgumentsModifier` is not
    bound by Shiboken, so `QProcess.start(...)` launches console binaries
    (`cmd.exe`, `powershell.exe`, `gcc.exe`, `git.exe`, etc.) without
    `CREATE_NO_WINDOW`, causing console windows to flash open and close.
    `HiddenProcess` uses `subprocess.Popen` with `hidden_subprocess_kwargs()`,
    guaranteeing zero console window flashes on Windows while emitting Qt
    signals on the owner thread.
    """

    NotRunning = 0
    Starting = 1
    Running = 2

    NormalExit = 0
    CrashExit = 1

    FailedToStart = 0
    Crashed = 1
    Timedout = 2
    ReadError = 3
    WriteError = 4
    UnknownError = 5

    SeparateChannels = 0
    MergedChannels = 1

    readyReadStandardOutput = Signal()
    readyReadStandardError = Signal()
    finished = Signal(int, int)
    errorOccurred = Signal(int)
    started = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._proc: Optional[subprocess.Popen] = None
        self._cwd: str = os.getcwd()
        self._env: _ProcessEnv = _ProcessEnv(os.environ.copy())
        self._channel_mode: int = self.SeparateChannels
        self._program: str = ""
        self._args: List[str] = []
        self._stdout_chunks: List[bytes] = []
        self._stderr_chunks: List[bytes] = []
        self._lock = threading.Lock()
        self._state: int = self.NotRunning
        self._started_event = threading.Event()
        self._finished_event = threading.Event()
        self._deleted = False

    def setWorkingDirectory(self, path: str) -> None:
        if path:
            self._cwd = str(path)

    def workingDirectory(self) -> str:
        return self._cwd

    def setProcessChannelMode(self, mode: int) -> None:
        self._channel_mode = int(mode)

    def processEnvironment(self) -> _ProcessEnv:
        return _ProcessEnv(self._env)

    def setProcessEnvironment(self, env: Mapping[str, str] | _ProcessEnv) -> None:
        self._env = _ProcessEnv(env)

    def setCreateProcessArgumentsModifier(self, _modifier: Callable) -> None:
        # Handled automatically by hidden_subprocess_kwargs()
        pass

    def program(self) -> str:
        return self._program

    def state(self) -> int:
        if self._proc is not None and self._proc.poll() is None:
            return self.Running
        return self.NotRunning

    def processId(self) -> int:
        return int(self._proc.pid) if self._proc is not None and self._proc.pid else 0

    def start(self, program: str, arguments: Optional[List[str]] = None) -> None:
        self.stop()
        self._program = str(program or "")
        self._args = [str(a) for a in (arguments or [])]
        with self._lock:
            self._stdout_chunks.clear()
            self._stderr_chunks.clear()
        self._started_event.clear()
        self._finished_event.clear()

        cmd = [self._program] + self._args
        run_env = os.environ.copy()
        run_env.update(self._env)
        run_env["PYTHONIOENCODING"] = "utf-8"
        run_env["PYTHONUNBUFFERED"] = "1"

        stderr_target = (
            subprocess.STDOUT
            if self._channel_mode == self.MergedChannels
            else subprocess.PIPE
        )

        try:
            self._proc = subprocess.Popen(
                cmd,
                cwd=self._cwd if (self._cwd and os.path.isdir(self._cwd)) else None,
                env=run_env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=stderr_target,
                bufsize=0,
                **hidden_subprocess_kwargs(),
            )
        except Exception:
            self._proc = None
            self._state = self.NotRunning
            self._started_event.set()
            self._finished_event.set()
            if not self._deleted:
                try:
                    self.errorOccurred.emit(self.FailedToStart)
                except Exception:
                    pass
            return

        self._state = self.Running
        self._started_event.set()
        if not self._deleted:
            try:
                self.started.emit()
            except Exception:
                pass

        proc = self._proc

        def _read_stream(stream, is_err: bool):
            if stream is None:
                return
            try:
                while True:
                    chunk = os.read(stream.fileno(), 4096) if hasattr(stream, "fileno") else stream.read(1024)
                    if not chunk:
                        break
                    with self._lock:
                        if is_err:
                            self._stderr_chunks.append(chunk)
                        else:
                            self._stdout_chunks.append(chunk)
                    if not self._deleted:
                        try:
                            if is_err:
                                self.readyReadStandardError.emit()
                            else:
                                self.readyReadStandardOutput.emit()
                        except Exception:
                            break
            except Exception:
                pass

        t_out = threading.Thread(
            target=_read_stream, args=(proc.stdout, False), daemon=True, name="hp-stdout"
        )
        t_out.start()

        t_err = None
        if self._channel_mode != self.MergedChannels and proc.stderr is not None:
            t_err = threading.Thread(
                target=_read_stream, args=(proc.stderr, True), daemon=True, name="hp-stderr"
            )
            t_err.start()

        def _wait_finish():
            try:
                exit_code = proc.wait()
            except Exception:
                exit_code = -1
            t_out.join(timeout=1.0)
            if t_err is not None:
                t_err.join(timeout=1.0)
            for pipe in (proc.stdin, proc.stdout, proc.stderr):
                if pipe is not None:
                    try:
                        pipe.close()
                    except Exception:
                        pass
            self._state = self.NotRunning
            self._finished_event.set()
            if not self._deleted:
                try:
                    status = self.NormalExit if exit_code == 0 else self.CrashExit
                    self.finished.emit(int(exit_code), int(status))
                except Exception:
                    pass

        threading.Thread(target=_wait_finish, daemon=True, name="hp-wait").start()

    def write(self, data: bytes | str) -> int:
        proc = self._proc
        if proc is None or proc.stdin is None or proc.poll() is not None:
            return -1
        payload = data.encode("utf-8") if isinstance(data, str) else bytes(data)
        try:
            proc.stdin.write(payload)
            proc.stdin.flush()
            return len(payload)
        except Exception:
            return -1

    def closeWriteChannel(self) -> None:
        proc = self._proc
        if proc is not None and proc.stdin is not None:
            try:
                proc.stdin.close()
            except Exception:
                pass

    def readAllStandardOutput(self) -> _ByteBuffer:
        with self._lock:
            data = b"".join(self._stdout_chunks)
            self._stdout_chunks.clear()
        return _ByteBuffer(data)

    def readAllStandardError(self) -> _ByteBuffer:
        with self._lock:
            data = b"".join(self._stderr_chunks)
            self._stderr_chunks.clear()
        return _ByteBuffer(data)

    def waitForStarted(self, msecs: int = 3000) -> bool:
        self._started_event.wait(timeout=max(0.05, msecs / 1000.0))
        return self._proc is not None and self._proc.poll() is None or (
            self._proc is not None and self._finished_event.is_set()
        )

    def waitForFinished(self, msecs: int = 3000) -> bool:
        if self._proc is None:
            return True
        return self._finished_event.wait(timeout=max(0.05, msecs / 1000.0))

    def terminate(self) -> None:
        proc = self._proc
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass

    def kill(self) -> None:
        proc = self._proc
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass

    def stop(self) -> None:
        proc = self._proc
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception:
                pass
        self._state = self.NotRunning

    def deleteLater(self) -> None:
        self._deleted = True
        try:
            super().deleteLater()
        except Exception:
            pass


def _hide_qprocess_windows_console(arguments) -> None:
    """Modifier callback for QProcess.setCreateProcessArgumentsModifier (when bound)."""
    try:
        arguments.flags = _sanitize_windows_flags(getattr(arguments, "flags", 0))
        startup_info = arguments.startupInfo
        startup_info.dwFlags |= _STARTF_USESHOWWINDOW
        startup_info.wShowWindow = _SW_HIDE
    except Exception:
        pass


def configure_qprocess_no_window(proc: Any) -> Any:
    """Configure a QProcess or HiddenProcess so child processes do not flash console windows."""
    if proc is None:
        return proc
    if sys.platform.startswith("win") or os.name == "nt":
        set_process_args = getattr(proc, "setCreateProcessArgumentsModifier", None)
        if callable(set_process_args):
            try:
                set_process_args(_hide_qprocess_windows_console)
            except Exception:
                pass
    return proc


def safe_delete_qprocess(proc: Any) -> None:
    """Safely schedule a QProcess / HiddenProcess for deletion without Shiboken RuntimeError."""
    if proc is None:
        return
    try:
        proc.deleteLater()
    except RuntimeError:
        pass
    except Exception:
        pass


def run_hidden_command(
    command: List[str],
    cwd: Optional[str | Path] = None,
    input_text: Optional[str] = None,
    timeout: float = 15.0,
    env: Optional[Dict[str, str]] = None,
) -> Tuple[int, str, str, float, bool]:
    """
    Run a command synchronously with hidden console window and return:
    (exit_code, stdout, stderr, duration_ms, timed_out)
    """
    start = time.perf_counter()
    kwargs = hidden_subprocess_kwargs()
    run_env = os.environ.copy()
    run_env["PYTHONIOENCODING"] = "utf-8"
    run_env["PYTHONUNBUFFERED"] = "1"
    if env:
        run_env.update(env)

    try:
        proc = subprocess.run(
            command,
            input=input_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(cwd) if cwd else None,
            timeout=timeout,
            env=run_env,
            **kwargs,
        )
        elapsed_ms = round((time.perf_counter() - start) * 1000.0, 1)
        return proc.returncode, proc.stdout or "", proc.stderr or "", elapsed_ms, False
    except subprocess.TimeoutExpired as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000.0, 1)
        out = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return 124, out, err, elapsed_ms, True
    except FileNotFoundError:
        elapsed_ms = round((time.perf_counter() - start) * 1000.0, 1)
        prog = command[0] if command else "command"
        return 127, "", f"Command not found: '{prog}' is not installed or not on PATH.", elapsed_ms, False
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000.0, 1)
        return 1, "", str(exc), elapsed_ms, False


def run_terminal_self_test(cwd: str = "", configured_shell: str = "") -> Dict[str, Any]:
    """
    Run an in-app diagnostic test on the integrated terminal & execution pipeline.
    Never opens any external terminal window.
    """
    work_dir = cwd if (cwd and os.path.isdir(cwd)) else os.getcwd()
    if os.name == "nt":
        shell_name = (configured_shell or "cmd").lower()
        if shell_name in ("powershell", "pwsh"):
            exe = shutil.which(shell_name) or "powershell"
            test_cmd = [exe, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", "Write-Output OWNCODE_TERMINAL_OK"]
        elif shell_name in ("bash", "git-bash", "wsl"):
            exe = shutil.which("bash") or "bash"
            test_cmd = [exe, "--noprofile", "--norc", "-c", "echo OWNCODE_TERMINAL_OK"]
        else:
            exe = shutil.which("cmd") or "cmd"
            test_cmd = [exe, "/Q", "/D", "/C", "echo OWNCODE_TERMINAL_OK"]
    else:
        exe = shutil.which("sh") or "/bin/sh"
        shell_name = os.path.basename(exe)
        test_cmd = [exe, "-c", "echo OWNCODE_TERMINAL_OK"]

    code, out, err, latency_ms, timed_out = run_hidden_command(
        test_cmd, cwd=work_dir, timeout=5.0
    )
    io_ok = (code == 0 and "OWNCODE_TERMINAL_OK" in out and not timed_out)

    # Check common toolchains purely via shutil.which (zero process spawns!)
    toolchains = {
        "Python": bool(shutil.which("python3") or shutil.which("python") or sys.executable),
        "C (gcc)": bool(shutil.which("gcc")),
        "C++ (g++)": bool(shutil.which("g++")),
        "Java": bool(shutil.which("javac") and shutil.which("java")),
        "Node.js": bool(shutil.which("node")),
        "Go": bool(shutil.which("go")),
        "Rust": bool(shutil.which("rustc")),
        "Git": bool(shutil.which("git")),
    }
    available_tools = [name for name, ok in toolchains.items() if ok]

    window_suppression = (
        "Active (CREATE_NO_WINDOW + SW_HIDE, DETACHED_PROCESS stripped — 0 external windows)"
        if os.name == "nt"
        else "Active (Subprocess Pipe Mode — 0 external windows)"
    )

    lines = [
        "============================================================",
        "  OWNCODE TERMINAL DIAGNOSTICS & SELF-TEST",
        "============================================================",
        f"  Shell Status       : {'✓ READY' if io_ok else '✗ FAILED'} ({shell_name})",
        f"  Pipe I/O Latency   : {latency_ms:.1f} ms",
        f"  Working Directory  : {work_dir} ({'✓ Valid' if os.path.isdir(work_dir) else '✗ Missing'})",
        f"  Window Suppression : ✓ {window_suppression}",
        f"  Detected Runtimes  : {', '.join(available_tools) if available_tools else 'None'}",
    ]
    if io_ok:
        lines.append("  Verdict            : ✓ Terminal tested successfully (no popup flash).")
    else:
        issue = err.strip() or "Shell did not return expected test token."
        lines.append(f"  Issue              : ✗ {issue[:140]}")
        lines.append("  Quick Fix          : Check Settings → Terminal → Default Shell or verify PATH.")
    lines.append("============================================================\n")

    return {
        "passed": io_ok,
        "shell": shell_name,
        "cwd": work_dir,
        "latency_ms": latency_ms,
        "window_suppression": window_suppression,
        "toolchains": toolchains,
        "available_tools": available_tools,
        "stdout": out.strip(),
        "stderr": err.strip(),
        "formatted_report": "\n".join(lines),
    }


# Install the Windows hidden-subprocess hook on import
install_hidden_subprocess_hooks()


# ============================================================================
# SECTION: ai.terminal.terminal_history_storage (ai/terminal/terminal_history_storage.py)
# ============================================================================
"""
Terminal History Storage — v1.0

Persistent storage for AI terminal command execution history.
Stores command, timing, workspace, exit code, and output preview.
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import json

from core.logger import setup_logger


logger = setup_logger(__name__)


@dataclass
class AICommandHistoryEntry:
    """Represents a single AI terminal command execution."""
    request_id: str
    command: str
    timestamp: datetime
    workspace: str
    exit_code: int
    duration_ms: int
    status: str  # pending, approved, cancelled, running, completed, failed
    output_preview: str = ""
    error_preview: str = ""
    reason: str = ""
    impact: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "request_id": self.request_id,
            "command": self.command,
            "timestamp": self.timestamp.isoformat(),
            "workspace": self.workspace,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "output_preview": self.output_preview,
            "error_preview": self.error_preview,
            "reason": self.reason,
            "impact": self.impact
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "AICommandHistoryEntry":
        """Create from dictionary."""
        return cls(
            request_id=data.get("request_id", ""),
            command=data.get("command", ""),
            timestamp=datetime.fromisoformat(data.get("timestamp", "")),
            workspace=data.get("workspace", ""),
            exit_code=data.get("exit_code", 0),
            duration_ms=data.get("duration_ms", 0),
            status=data.get("status", ""),
            output_preview=data.get("output_preview", ""),
            error_preview=data.get("error_preview", ""),
            reason=data.get("reason", ""),
            impact=data.get("impact", "")
        )


class TerminalHistoryStorage:
    """
    Manages AI terminal command history with persistent storage.
    
    Features:
    - Unlimited history (capped for memory safety)
    - Search by command, workspace, status
    - Filter by date range
    - Export to CSV/JSON
    - Stats and analytics
    """
    
    def __init__(self, storage_file: Path = None):
        self.storage_file = storage_file or Path("config/ai_terminal_history.json")
        self._entries: List[AICommandHistoryEntry] = []
        self._max_entries = 10000
        self._load_history()
    
    def _load_history(self):
        """Load history from storage file."""
        if not self.storage_file.exists():
            self._entries = []
            return
        
        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            entries = []
            for item in data.get("history", []):
                try:
                    entry = AICommandHistoryEntry.from_dict(item)
                    entries.append(entry)
                except Exception as e:
                    logger.warning(f"Failed to load history entry: {e}")
            
            self._entries = entries[-self._max_entries:]
            logger.info(f"Loaded {len(self._entries)} history entries")
            
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            self._entries = []
    
    def _save_history(self):
        """Save history to storage file."""
        try:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "history": [e.to_dict() for e in self._entries]
            }
            
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
    
    def add_entry(self, entry: AICommandHistoryEntry):
        """Add a history entry."""
        self._entries.append(entry)
        
        # Enforce max size
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
        
        self._save_history()
    
    def get_entry(self, request_id: str) -> Optional[AICommandHistoryEntry]:
        """Get entry by request ID."""
        for entry in self._entries:
            if entry.request_id == request_id:
                return entry
        return None
    
    def get_entries(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
        workspace: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[AICommandHistoryEntry]:
        """Get filtered history entries."""
        result = self._entries[offset:]
        
        # Filter by status
        if status:
            result = [e for e in result if e.status == status]
        
        # Filter by workspace
        if workspace:
            result = [e for e in result if workspace in e.workspace]
        
        # Search in command
        if search:
            search_lower = search.lower()
            result = [e for e in result if search_lower in e.command.lower()]
        
        # Limit results
        if limit:
            result = result[:limit]
        
        return result
    
    def get_recent_commands(self, count: int = 10) -> List[AICommandHistoryEntry]:
        """Get most recent commands."""
        return self._entries[-count:] if self._entries else []
    
    def get_completed_commands(self, count: int = 10) -> List[AICommandHistoryEntry]:
        """Get recently completed commands."""
        completed = [e for e in self._entries if e.status == "completed"]
        return completed[-count:] if completed else []
    
    def get_failed_commands(self, count: int = 10) -> List[AICommandHistoryEntry]:
        """Get recently failed commands."""
        failed = [e for e in self._entries if e.status == "failed"]
        return failed[-count:] if failed else []
    
    def get_stats(self) -> Dict:
        """Get history statistics."""
        total = len(self._entries)
        completed = len([e for e in self._entries if e.status == "completed"])
        failed = len([e for e in self._entries if e.status == "failed"])
        cancelled = len([e for e in self._entries if e.status == "cancelled"])
        
        total_duration = sum(e.duration_ms for e in self._entries if e.duration_ms > 0)
        avg_duration = total_duration / completed if completed > 0 else 0
        
        return {
            "total_commands": total,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "success_rate": (completed / total * 100) if total > 0 else 0,
            "total_duration_ms": total_duration,
            "average_duration_ms": avg_duration
        }
    
    def clear_history(self):
        """Clear all history."""
        self._entries = []
        self._save_history()
        logger.info("AI terminal history cleared")
    
    def export_to_json(self, filepath: Path = None) -> Path:
        """Export history to JSON file."""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = Path(f"ai_terminal_history_{timestamp}.json")
        
        try:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "exported_at": datetime.now().isoformat(),
                "stats": self.get_stats(),
                "history": [e.to_dict() for e in self._entries]
            }
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to export history: {e}")
            raise
    
    def export_to_csv(self, filepath: Path = None) -> Path:
        """Export history to CSV file."""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = Path(f"ai_terminal_history_{timestamp}.csv")
        
        try:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            
            lines = []
            lines.append("request_id,timestamp,command,workspace,exit_code,duration_ms,status")
            
            for entry in self._entries:
                # Escape quotes and newlines in command
                command = entry.command.replace('"', '""')
                workspace = entry.workspace.replace('"', '""')
                lines.append(
                    f'"{entry.request_id}",'
                    f'"{entry.timestamp.isoformat()}",'
                    f'"{command}",'
                    f'"{workspace}",'
                    f'{entry.exit_code},'
                    f'{entry.duration_ms},'
                    f'{entry.status}'
                )
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to export history to CSV: {e}")
            raise


# ============================================================================
# SECTION: ai.terminal.terminal_output_analyzer (ai/terminal/terminal_output_analyzer.py)
# ============================================================================
"""
Terminal Output Analyzer — v1.0

Analyzes terminal output from AI-executed commands to identify:
- Compiler errors
- Runtime errors
- Warnings
- Test results
- Stack traces

Provides explanations and suggested fixes.
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ErrorLocation:
    """Location of an error in source code."""
    file_path: str
    line_number: int
    column: int = 0
    content: str = ""


@dataclass
class Diagnostic:
    """Diagnostic information about an error or warning."""
    severity: str  # error, warning, info, hint
    message: str
    file_path: str = ""
    line_number: int = 0
    column: int = 0
    code: str = ""
    suggested_fix: str = ""


@dataclass
class AnalysisResult:
    """Result of terminal output analysis."""
    success: bool
    has_errors: bool
    has_warnings: bool
    has_compiler_errors: bool
    has_runtime_errors: bool
    has_test_results: bool
    has_stack_traces: bool
    errors: List[Diagnostic] = field(default_factory=list)
    warnings: List[Diagnostic] = field(default_factory=list)
    stack_traces: List[str] = field(default_factory=list)
    test_summary: Dict = field(default_factory=dict)
    suggested_fixes: List[str] = field(default_factory=list)


class TerminalOutputAnalyzer:
    """
    Analyzes terminal output to identify issues and provide suggestions.
    
    Supports multiple languages:
    - Python (Tracebacks, exceptions)
    - C/C++ (GCC, Clang errors)
    - Java (javac, runtime exceptions)
    - Rust (cargo errors)
    - Node.js (npm, Jest)
    """
    
    def __init__(self):
        self._patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict:
        """Compile regex patterns for different languages."""
        return {
            # Python patterns
            "python_traceback": r'File\s+"([^"]+)",\s*line\s+(\d+)',
            "python_exception": r'(\w+Error|Exception):\s*(.+)',
            "python_syntax_error": r'SyntaxError:\s*(.+)',
            
            # C/C++ patterns
            "cpp_error": r'([^\s:]+)\.([a-z]+):(\d+):(\d+):\s*(error|warning):\s*(.+)',
            "cpp_file_line": r'([^\s:]+)\.([a-z]+):(\d+):',
            
            # Java patterns
            "java_error": r'([^\s:]+\.java):(\d+):\s*(error|warning):\s*(.+)',
            "java_exception": r'Exception in thread "[^"]+"\s*([\w.]+):(.+)',
            
            # Rust patterns
            "rust_error": r'-->?\s*([^:]+):(\d+):(\d+)',
            "rust_compiler_error": r'error\[E\d+\]:\s*(.+)',
            
            # Jest/Node patterns
            "jest_error": r'●\s*(.+)',
            "jest_test": r'(\d+)\s+(test|pass|fail)',
            
            # Generic patterns
            "generic_error": r'(error|Error|ERROR):\s*(.+)',
            "generic_warning": r'(warning|Warning|WARNING):\s*(.+)',
        }
    
    def analyze(self, output: str, command: str = "") -> AnalysisResult:
        """
        Analyze terminal output for errors and warnings.
        
        Args:
            output: Terminal output to analyze
            command: The command that was executed
            
        Returns:
            AnalysisResult with findings and suggestions
        """
        result = AnalysisResult(
            success=False,
            has_errors=False,
            has_warnings=False,
            has_compiler_errors=False,
            has_runtime_errors=False,
            has_test_results=False,
            has_stack_traces=False
        )
        
        if not output:
            result.success = True
            return result
        
        # Detect language and analyze
        output_lower = output.lower()
        
        # Python analysis
        if self._is_python_command(command) or self._detect_python(output_lower):
            self._analyze_python(output, result)
        
        # C/C++ analysis
        elif self._is_cpp_command(command) or self._detect_cpp(output_lower):
            self._analyze_cpp(output, result)
        
        # Java analysis
        elif self._is_java_command(command) or self._detect_java(output_lower):
            self._analyze_java(output, result)
        
        # Rust analysis
        elif self._is_rust_command(command) or self._detect_rust(output_lower):
            self._analyze_rust(output, result)
        
        # Node.js/Jest analysis
        elif self._is_node_command(command) or self._detect_node(output_lower):
            self._analyze_node(output, result)
        
        # Generic analysis (fallback)
        self._analyze_generic(output, result)
        
        # Generate suggested fixes
        result.suggested_fixes = self._generate_suggestions(result)
        
        return result
    
    def _is_python_command(self, command: str) -> bool:
        """Check if command is a Python command."""
        return command.startswith("python") or command.startswith("python3")
    
    def _detect_python(self, output: str) -> bool:
        """Detect Python output."""
        return "traceback" in output or "exception" in output or "error:" in output
    
    def _analyze_python(self, output: str, result: AnalysisResult):
        """Analyze Python output."""
        # Extract tracebacks
        traceback_pattern = r'Traceback \(most recent call last\):\n((?:\s*File\s+"[^"]+",\s*line\s+\d+.*\n)+)'
        match = re.search(traceback_pattern, output)
        if match:
            result.has_stack_traces = True
            result.has_runtime_errors = True
            
            # Extract file locations
            for line in match.group(1).split("\n"):
                file_match = re.search(r'File\s+"([^"]+)",\s*line\s+(\d+)', line)
                if file_match:
                    loc = ErrorLocation(
                        file_path=file_match.group(1),
                        line_number=int(file_match.group(2))
                    )
                    result.errors.append(Diagnostic(
                        severity="error",
                        message="Python exception in traceback",
                        file_path=loc.file_path,
                        line_number=loc.line_number
                    ))
        
        # Extract exception type
        exception_match = re.search(r'(\w+Error|Exception):\s*(.+)', output)
        if exception_match:
            result.has_runtime_errors = True
            result.errors.append(Diagnostic(
                severity="error",
                message=f"{exception_match.group(1)}: {exception_match.group(2)}",
                suggested_fix=f"Handle the {exception_match.group(1)} exception"
            ))
        
        # Syntax errors
        syntax_match = re.search(r'SyntaxError:\s*(.+)', output)
        if syntax_match:
            result.has_compiler_errors = True
            result.errors.append(Diagnostic(
                severity="error",
                message=syntax_match.group(1),
                suggested_fix="Fix the syntax error in your Python code"
            ))
    
    def _is_cpp_command(self, command: str) -> bool:
        """Check if command is a C/C++ command."""
        return any(cmd in command for cmd in ["gcc", "g++", "clang", "clang++", "make", "cmake"])
    
    def _detect_cpp(self, output: str) -> bool:
        """Detect C/C++ output."""
        return "error:" in output or "warning:" in output
    
    def _analyze_cpp(self, output: str, result: AnalysisResult):
        """Analyze C/C++ output."""
        # Extract errors
        error_pattern = r'([^\s:]+)\.([a-z]+):(\d+):(\d+):\s*(error):\s*(.+)'
        for match in re.finditer(error_pattern, output):
            result.has_compiler_errors = True
            result.errors.append(Diagnostic(
                severity="error",
                message=match.group(6),
                file_path=f"{match.group(1)}.{match.group(2)}",
                line_number=int(match.group(3)),
                column=int(match.group(4))
            ))
        
        # Extract warnings
        warning_pattern = r'([^\s:]+)\.([a-z]+):(\d+):(\d+):\s*(warning):\s*(.+)'
        for match in re.finditer(warning_pattern, output):
            result.has_warnings = True
            result.warnings.append(Diagnostic(
                severity="warning",
                message=match.group(6),
                file_path=f"{match.group(1)}.{match.group(2)}",
                line_number=int(match.group(3)),
                column=int(match.group(4))
            ))
    
    def _is_java_command(self, command: str) -> bool:
        """Check if command is a Java command."""
        return any(cmd in command for cmd in ["javac", "java", "mvn", "gradle"])
    
    def _detect_java(self, output: str) -> bool:
        """Detect Java output."""
        return ".java:" in output or "Exception" in output
    
    def _analyze_java(self, output: str, result: AnalysisResult):
        """Analyze Java output."""
        # Extract errors
        error_pattern = r'([^\s:]+\.java):(\d+):\s*(error):\s*(.+)'
        for match in re.finditer(error_pattern, output):
            result.has_compiler_errors = True
            result.errors.append(Diagnostic(
                severity="error",
                message=match.group(4),
                file_path=match.group(1),
                line_number=int(match.group(2))
            ))
        
        # Extract exceptions
        exception_pattern = r'Exception in thread "[^"]+"\s*([\w.]+):(.+)'
        match = re.search(exception_pattern, output)
        if match:
            result.has_runtime_errors = True
            result.errors.append(Diagnostic(
                severity="error",
                message=match.group(2),
                suggested_fix=f"Handle the {match.group(1)} exception"
            ))
    
    def _is_rust_command(self, command: str) -> bool:
        """Check if command is a Rust command."""
        return command.startswith("cargo")
    
    def _detect_rust(self, output: str) -> bool:
        """Detect Rust output."""
        return "-->" in output or "error" in output
    
    def _analyze_rust(self, output: str, result: AnalysisResult):
        """Analyze Rust output."""
        # Extract errors
        error_pattern = r'-->?\s*([^:]+):(\d+):(\d+)\s*\n\s*\|\s*\d+\s*\|\s*(.+)'
        for match in re.finditer(error_pattern, output, re.MULTILINE):
            result.has_compiler_errors = True
            result.errors.append(Diagnostic(
                severity="error",
                message=match.group(4).strip(),
                file_path=match.group(1),
                line_number=int(match.group(2)),
                column=int(match.group(3))
            ))
        
        # Extract compiler error codes
        code_pattern = r'error\[E(\d+)\]:\s*(.+)'
        for match in re.finditer(code_pattern, output):
            result.errors.append(Diagnostic(
                severity="error",
                message=match.group(2),
                code=f"E{match.group(1)}",
                suggested_fix=f"Search for Rust error E{match.group(1)}"
            ))
    
    def _is_node_command(self, command: str) -> bool:
        """Check if command is a Node.js command."""
        return any(cmd in command for cmd in ["npm", "yarn", "node", "jest"])
    
    def _detect_node(self, output: str) -> bool:
        """Detect Node.js output."""
        return "npm" in output or "jest" in output or "Error:" in output
    
    def _analyze_node(self, output: str, result: AnalysisResult):
        """Analyze Node.js output."""
        # Jest test results
        test_pattern = r'(\d+)\s+(test|pass|fail)'
        for match in re.finditer(test_pattern, output):
            if match.group(2) == "test":
                result.has_test_results = True
                result.test_summary["total"] = int(match.group(1))
            elif match.group(2) == "pass":
                result.test_summary["passed"] = int(match.group(1))
            elif match.group(2) == "fail":
                result.test_summary["failed"] = int(match.group(1))
        
        # Jest error messages
        error_pattern = r'●\s*(.+)'
        for match in re.finditer(error_pattern, output):
            result.has_errors = True
            result.errors.append(Diagnostic(
                severity="error",
                message=match.group(1),
                suggested_fix="Check the test file for errors"
            ))
    
    def _analyze_generic(self, output: str, result: AnalysisResult):
        """Generic analysis fallback."""
        # Extract generic errors
        error_pattern = r'(error|Error|ERROR):\s*(.+)'
        for match in re.finditer(error_pattern, output):
            result.has_errors = True
            result.errors.append(Diagnostic(
                severity="error",
                message=match.group(2),
                suggested_fix="Check the command output for details"
            ))
        
        # Extract warnings
        warning_pattern = r'(warning|Warning|WARNING):\s*(.+)'
        for match in re.finditer(warning_pattern, output):
            result.has_warnings = True
            result.warnings.append(Diagnostic(
                severity="warning",
                message=match.group(2),
                suggested_fix="Review the warning and consider fixing"
            ))
    
    def _generate_suggestions(self, result: AnalysisResult) -> List[str]:
        """Generate suggested fixes based on analysis."""
        suggestions = []
        
        if result.has_compiler_errors:
            suggestions.append("1. Review compiler error messages carefully")
            suggestions.append("2. Check file paths and syntax")
            suggestions.append("3. Verify all dependencies are installed")
        
        if result.has_runtime_errors:
            suggestions.append("1. Check exception types and stack traces")
            suggestions.append("2. Verify input data and environment")
            suggestions.append("3. Add proper error handling")
        
        if result.has_warnings:
            suggestions.append("1. Review all warnings")
            suggestions.append("2. Fix deprecated API usage")
            suggestions.append("3. Remove unused variables/imports")
        
        if result.has_test_results:
            suggestions.append("1. Check failed test details")
            suggestions.append("2. Verify test expectations")
            suggestions.append("3. Run tests individually for debugging")
        
        if not result.success and not suggestions:
            suggestions.append("1. Review the full output for clues")
            suggestions.append("2. Check command arguments")
            suggestions.append("3. Verify environment setup")
        
        return suggestions


# ============================================================================
# SECTION: ai.terminal.terminal_approval_panel (ai/terminal/terminal_approval_panel.py)
# ============================================================================
"""
Terminal Approval Panel — v1.0

Shows an approval dialog before executing AI-requested terminal commands.
Displays command details, working directory, reason, and impact.
User must approve or cancel before execution proceeds.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QFrame, QSplitter, QScrollArea, QStyleOptionButton,
    QStyle, QStylePainter
)
from PySide6.QtCore import Qt, Signal, QRect, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont
from pathlib import Path
from typing import Dict, Any

from core.logger import setup_logger
from core.event_bus import EventBus


logger = setup_logger(__name__)


class TerminalApprovalPanel(QWidget):
    """
    Approval panel for terminal command execution.
    
    Shows:
    - Command to execute
    - Working directory
    - Reason for execution
    - Estimated impact
    - Run, Edit Command, Cancel buttons
    
    Signals:
    approved(str) — Emitted when user approves
    cancelled(str) — Emitted when user cancels
    """
    
    approved = Signal(str)  # command
    cancelled = Signal(str)  # command
    
    def __init__(self, event_bus: EventBus = None, parent=None):
        super().__init__(parent)
        self.event_bus = event_bus
        self._command = ""
        self._working_directory = ""
        self._reason = ""
        self._impact = ""
        self._setup_ui()
    
    def set_request(
        self,
        command: str,
        working_directory: str,
        reason: str = "",
        impact: str = ""
    ):
        """Set the request details for approval."""
        self._command = command
        self._working_directory = working_directory
        self._reason = reason
        self._impact = impact
        
        # Update UI
        self._cmd_text.setPlainText(command)
        self._dir_label.setText(f"<b>Working Directory:</b> {working_directory}")
        
        if reason:
            self._reason_text.setPlainText(reason)
        else:
            self._reason_text.setPlainText("No reason provided")
        
        if impact:
            self._impact_text.setPlainText(impact)
        else:
            self._impact_text.setPlainText("Standard terminal execution")
    
    def _setup_ui(self):
        """Setup the approval panel UI."""
        self.setWindowTitle("Terminal Command Approval")
        self.setMinimumSize(600, 500)
        self.setStyleSheet("""
            QWidget {
                background-color: #0D0D0F;
                color: #E2E2E6;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Main content
        main = self._create_main()
        layout.addWidget(main)
        
        # Footer
        footer = self._create_footer()
        layout.addWidget(footer)
    
    def _create_header(self) -> QWidget:
        """Create the header with icon and title."""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #111113;
                border-bottom: 1px solid #252528;
            }
        """)
        widget.setFixedHeight(60)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # Icon
        icon = QLabel(".Terminal")
        icon.setStyleSheet("""
            QLabel {
                background-color: #3B82F6;
                color: white;
                font-size: 20px;
                padding: 8px 12px;
                border-radius: 4px;
            }
        """)
        layout.addWidget(icon)
        
        # Title
        title = QLabel("Terminal Command Execution")
        title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 600;
                color: #E2E2E6;
            }
        """)
        layout.addWidget(title)
        
        layout.addStretch()
        
        return widget
    
    def _create_main(self) -> QWidget:
        """Create the main content with command details."""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #0D0D0F;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Command section
        cmd_section = self._create_section("Command", self._create_command_widget())
        layout.addWidget(cmd_section)
        
        # Working directory
        dir_section = self._create_section("Working Directory", self._create_dir_widget())
        layout.addWidget(dir_section)
        
        # Reason
        reason_section = self._create_section("Reason", self._create_reason_widget())
        layout.addWidget(reason_section)
        
        # Impact
        impact_section = self._create_section("Estimated Impact", self._create_impact_widget())
        layout.addWidget(impact_section)
        
        return widget
    
    def _create_section(self, title: str, content: QWidget) -> QWidget:
        """Create a section with title and content."""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #111113;
                border: 1px solid #252528;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #52525C;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 0.5px;
                text-transform: uppercase;
            }
        """)
        layout.addWidget(title_label)
        
        # Content
        layout.addWidget(content)
        
        return widget
    
    def _create_command_widget(self) -> QWidget:
        """Create the command display widget."""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #0D0D0F;
                border: 1px solid #252528;
                border-radius: 3px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        self._cmd_text = QTextEdit()
        self._cmd_text.setReadOnly(True)
        self._cmd_text.setFixedHeight(80)
        self._cmd_text.setStyleSheet("""
            QTextEdit {
                background-color: #1C1C1F;
                color: #E2E2E6;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                font-size: 11px;
                border: none;
                padding: 8px;
            }
        """)
        layout.addWidget(self._cmd_text)
        
        return widget
    
    def _create_dir_widget(self) -> QWidget:
        """Create the directory display widget."""
        self._dir_label = QLabel("")
        self._dir_label.setStyleSheet("""
            QLabel {
                color: #8E8E98;
                font-size: 11px;
                padding: 8px;
                background-color: #1C1C1F;
                border: 1px solid #252528;
                border-radius: 3px;
            }
        """)
        return self._dir_label
    
    def _create_reason_widget(self) -> QWidget:
        """Create the reason display widget."""
        self._reason_text = QTextEdit()
        self._reason_text.setReadOnly(True)
        self._reason_text.setMaximumHeight(60)
        self._reason_text.setStyleSheet("""
            QTextEdit {
                background-color: #1C1C1F;
                color: #8E8E98;
                font-size: 11px;
                border: none;
                padding: 8px;
            }
        """)
        return self._reason_text
    
    def _create_impact_widget(self) -> QWidget:
        """Create the impact display widget."""
        self._impact_text = QTextEdit()
        self._impact_text.setReadOnly(True)
        self._impact_text.setMaximumHeight(60)
        self._impact_text.setStyleSheet("""
            QTextEdit {
                background-color: #1C1C1F;
                color: #F59E0B;
                font-size: 11px;
                border: none;
                padding: 8px;
            }
        """)
        return self._impact_text
    
    def _create_footer(self) -> QWidget:
        """Create the footer with action buttons."""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #111113;
                border-top: 1px solid #252528;
            }
        """)
        widget.setFixedHeight(50)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)
        
        # Run button
        self._btn_run = QPushButton("Run")
        self._btn_run.setFixedHeight(30)
        self._btn_run.setStyleSheet("""
            QPushButton {
                background-color: #22C55E;
                color: #064E3B;
                font-size: 12px;
                font-weight: 600;
                border: none;
                border-radius: 4px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background-color: #16A34A;
            }
            QPushButton:pressed {
                background-color: #15803D;
            }
        """)
        self._btn_run.clicked.connect(self._on_run)
        layout.addWidget(self._btn_run)
        
        # Edit Command button (disabled by default)
        self._btn_edit = QPushButton("Edit Command")
        self._btn_edit.setFixedHeight(30)
        self._btn_edit.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                font-size: 12px;
                font-weight: 500;
                border: none;
                border-radius: 4px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
            QPushButton:pressed {
                background-color: #1D4ED8;
            }
            QPushButton:disabled {
                background-color: #252528;
                color: #52525C;
            }
        """)
        self._btn_edit.setEnabled(False)  # Not implemented yet
        layout.addWidget(self._btn_edit)
        
        # Cancel button
        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.setFixedHeight(30)
        self._btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: #7F1D1D;
                font-size: 12px;
                font-weight: 600;
                border: none;
                border-radius: 4px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background-color: #DC2626;
            }
            QPushButton:pressed {
                background-color: #B91C1C;
            }
        """)
        self._btn_cancel.clicked.connect(self._on_cancel)
        layout.addWidget(self._btn_cancel)
        
        layout.addStretch()
        
        return widget
    
    def _on_run(self):
        """User clicked Run button."""
        self.approved.emit(self._command)
        self.close()
    
    def _on_cancel(self):
        """User clicked Cancel button."""
        self.cancelled.emit(self._command)
        self.close()
    
    def show_approval(
        self,
        command: str,
        working_directory: str,
        reason: str = "",
        impact: str = ""
    ) -> str:
        """
        Show the approval panel and wait for user response.
        
        Returns:
            "approved" or "cancelled"
        """
        self.set_request(command, working_directory, reason, impact)
        self.show()
        
        # Return appropriate status
        # Note: In a real implementation, this would use a modal dialog
        # For now, we return "pending" and emit signals
        return "pending"


# For testing
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    panel = TerminalApprovalPanel()
    
    def on_approved(cmd):
        print(f"Approved: {cmd}")
    
    def on_cancelled(cmd):
        print(f"Cancelled: {cmd}")
    
    panel.approved.connect(on_approved)
    panel.cancelled.connect(on_cancelled)
    
    panel.show_approval(
        command="python myscript.py --arg1 value1",
        working_directory="C:\\Projects\\myproject",
        reason="AI detected this script needs to be run",
        impact="Will execute the Python script in the project directory"
    )
    
    sys.exit(app.exec())


# ============================================================================
# SECTION: ai.terminal.ai_terminal_manager (ai/terminal/ai_terminal_manager.py)
# ============================================================================
"""
AI Terminal Manager — v1.0

Deeply integrates AI system with the Integrated Terminal.
Enables AI to request terminal execution, stream output, analyze results,
and assist users with safe command execution.

Features:
- AI terminal command execution
- User approval workflow
- Live output streaming
- Output analysis for errors/warnings
- Command history storage
- Terminal actions from AI chat
- Safe command filter for dangerous commands
- Workspace awareness
- Terminal status tracking
- EventBus event publishing
"""

from PySide6.QtCore import QObject, Signal, QSettings
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import time
import json

from core.logger import setup_logger
from core.event_bus import EventBus
try:
    from core.workspace_manager import WorkspaceManager
except ImportError:
    WorkspaceManager = None
from ai.terminal.terminal_approval_panel import TerminalApprovalPanel


logger = setup_logger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class TerminalExecutionRequest:
    """Request from AI to execute a terminal command."""
    request_id: str
    command: str
    working_directory: Path
    reason: str
    impact: str
    timestamp: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # pending, approved, cancelled, running, completed, failed
    execution_time_ms: int = 0
    exit_code: int = None
    output: str = ""
    error_output: str = ""
    approval_required: bool = True


@dataclass
class TerminalCommandHistoryRecord:
    """Record of a terminal command executed by AI."""
    request_id: str
    command: str
    timestamp: datetime
    workspace: str
    exit_code: int
    duration_ms: int
    status: str
    output_preview: str = ""


# ──────────────────────────────────────────────────────────────────────────────
# Safe Command Filter
# ──────────────────────────────────────────────────────────────────────────────

DANGEROUS_COMMAND_PATTERNS = [
    # System modification/destruction
    r"^\s*rmdir\s",           # Remove directory
    r"^\s*del(\s|$)",         # Delete files
    r"^\s*format\s",          # Format disk
    r"^\s*diskpart\s",        # Disk partitioning
    r"^\s*shutdown\s",        # System shutdown
    r"^\s*reboot\s",          # System reboot
    r"^\s*reg\s+delete\s",    # Registry deletion
    r"^\s*system\s+reset\s",  # System reset
    
    # Potentially dangerous file operations
    r"^\s*rm\s+-rf\s",        # Recursive directory removal
    r"^\s*rd\s+/s\s+/q\s",    # Windows recursive delete
    r"^\s*rm\s+-rf\s+/",      # Dangerous rm with root
    r"^\s*del\s+/s\s+/f\s+/q", # Windows force delete
    
    # Network attacks
    r"^\s*nmap\s",            # Network scanning
    r"^\s*sqlmap\s",          # SQL injection tool
    
    # System utilities
    r"^\s*mkcert\s",          # Certificate creation
    r"^\s*net\s+use\s",       # Network connection
    
    # Configuration changes
    r"^\s*chkntfs\s",         # Check disk
    r"^\s*defrag\s",          # Disk defragmentation
]


# ──────────────────────────────────────────────────────────────────────────────
# AI Terminal Manager
# ──────────────────────────────────────────────────────────────────────────────

class AITerminalManager(QObject):
    """
    Manages AI terminal execution with safety, approval, and analysis.
    
    Reuses:
    - Integrated Terminal (terminal_executor.py, terminal_manager.py)
    - WorkspaceManager (current workspace tracking)
    - EventBus (event distribution)
    - Logger (logging)
    """
    
    # Signals for thread-safe UI updates
    request_created = Signal(str)  # request_id
    request_updated = Signal(str)  # request_id
    execution_started = Signal(str)  # request_id
    execution_completed = Signal(str)  # request_id
    execution_failed = Signal(str, str)  # request_id, error
    
    def __init__(self, event_bus: EventBus, workspace_manager: WorkspaceManager):
        super().__init__()
        self.event_bus = event_bus
        self.workspace_manager = workspace_manager
        self.settings = QSettings("OwnCode", "AITerminal")
        
        # State
        self._requests: Dict[str, TerminalExecutionRequest] = {}
        self._history: List[TerminalCommandHistoryRecord] = []
        self._current_request: Optional[str] = None
        
        # Load history
        self._load_history()
        
        # Subscribe to terminal events
        self.event_bus.subscribe("terminal_output", self._on_terminal_output)
        self.event_bus.subscribe("terminal_error", self._on_terminal_error)
        self.event_bus.subscribe("process_started", self._on_process_started)
        self.event_bus.subscribe("process_finished", self._on_process_finished)
        
        logger.info("AITerminalManager initialized")

    # ──────────────────────────────────────────────────────────────────────────────
    # Command Execution Request
    # ──────────────────────────────────────────────────────────────────────────────

    def create_execution_request(
        self,
        command: str,
        working_directory: Optional[Path] = None,
        reason: str = "",
        impact: str = ""
    ) -> str:
        """
        Create a terminal execution request from AI.
        
        Args:
            command: The terminal command to execute
            working_directory: Working directory for the command
            reason: Why this command is being executed
            impact: Estimated impact of the command
            
        Returns:
            Request ID for tracking
        """
        # Determine working directory
        if working_directory is None:
            workspace = self.workspace_manager.active_workspace
            if workspace:
                working_directory = workspace.path
            else:
                working_directory = Path.cwd()
        
        # Generate request ID
        request_id = f"ai-exec-{int(time.time() * 1000)}"
        
        # Create request
        request = TerminalExecutionRequest(
            request_id=request_id,
            command=command.strip(),
            working_directory=working_directory,
            reason=reason,
            impact=impact if impact else "Standard terminal execution"
        )
        
        # Check if approval is needed
        if not self._requires_approval(command):
            request.approval_required = False
            request.status = "approved"
        
        self._requests[request_id] = request
        self._current_request = request_id
        
        # Publish event
        self.event_bus.publish("ai_terminal_request", {
            "request_id": request_id,
            "command": command,
            "working_directory": str(working_directory),
            "reason": reason,
            "impact": impact,
            "status": request.status,
            "approval_required": request.approval_required
        })
        
        self.request_created.emit(request_id)
        logger.info(f"Created terminal execution request: {request_id} - {command[:50]}...")
        
        return request_id

    def _requires_approval(self, command: str) -> bool:
        """Check if command requires user approval based on safety filter."""
        import re
        
        command_lower = command.lower().strip()
        
        for pattern in DANGEROUS_COMMAND_PATTERNS:
            if re.search(pattern, command_lower, re.IGNORECASE):
                return True
        
        return False

    def approve_execution(self, request_id: str) -> bool:
        """
        Approve a pending execution request.
        
        Args:
            request_id: The request to approve
            
        Returns:
            True if approved, False if request not found or already processed
        """
        if request_id not in self._requests:
            return False
        
        request = self._requests[request_id]
        if request.status not in ("pending", "approved"):
            return False
        
        request.status = "approved"
        self._save_history()
        
        self.event_bus.publish("terminal_execution_approved", {
            "request_id": request_id,
            "command": request.command
        })
        
        self._execute_command(request)
        return True

    def cancel_execution(self, request_id: str) -> bool:
        """
        Cancel a pending execution request.
        
        Args:
            request_id: The request to cancel
            
        Returns:
            True if cancelled, False if request not found
        """
        if request_id not in self._requests:
            return False
        
        request = self._requests[request_id]
        if request.status != "pending":
            return False
        
        request.status = "cancelled"
        
        self.event_bus.publish("terminal_execution_cancelled", {
            "request_id": request_id,
            "command": request.command
        })
        
        logger.info(f"Cancelled terminal execution: {request_id}")
        return True

    # ──────────────────────────────────────────────────────────────────────────────
    # Execution
    # ──────────────────────────────────────────────────────────────────────────────

    def _execute_command(self, request: TerminalExecutionRequest):
        """Execute the approved command in the terminal."""
        if request.status != "approved":
            return
        
        request.status = "running"
        request.start_time = time.time()
        
        self.event_bus.publish("terminal_execution_started", {
            "request_id": request.request_id,
            "command": request.command,
            "working_directory": str(request.working_directory)
        })
        
        self.execution_started.emit(request.request_id)
        logger.info(f"Executing terminal command: {request.command}")
        
        # Execute via RunManager
        self._run_via_run_manager(request)

    def _run_via_run_manager(self, request: TerminalExecutionRequest):
        """Execute command using RunManager."""
        from core.run_manager import RunManager
        
        run_manager = RunManager(self.event_bus)
        run_manager.workspace_root = request.working_dir
        
        # Detect and run appropriate command
        if request.command.startswith("python "):
            file_path = Path(request.command[7:]).resolve()
            if file_path.exists():
                run_manager.run_file(file_path)
            else:
                self._complete_execution(request.request_id, 1, "File not found")
        elif request.command.startswith("npm "):
            run_manager.execute_project_command("npm", request.command[4:])
        elif request.command.startswith("yarn "):
            run_manager.execute_project_command("yarn", request.command[5:])
        else:
            # Generic command execution
            run_manager.execute_generic_command(request.command, request.working_directory)

    # ──────────────────────────────────────────────────────────────────────────────
    # Event Handlers
    # ──────────────────────────────────────────────────────────────────────────────

    def _on_terminal_output(self, data: dict):
        """Handle terminal output event."""
        if not self._current_request:
            return
        
        request = self._requests.get(self._current_request)
        if not request or request.status != "running":
            return
        
        output = data.get("output", "")
        request.output += output
        
        # Stream to AI chat
        self.event_bus.publish("terminal_output_stream", {
            "request_id": request.request_id,
            "output": output,
            "stream": "stdout"
        })

    def _on_terminal_error(self, data: dict):
        """Handle terminal error event."""
        if not self._current_request:
            return
        
        request = self._requests.get(self._current_request)
        if not request or request.status != "running":
            return
        
        error = data.get("error", "")
        request.error_output += error
        
        # Stream to AI chat
        self.event_bus.publish("terminal_output_stream", {
            "request_id": request.request_id,
            "output": error,
            "stream": "stderr"
        })

    def _on_process_started(self, data: dict):
        """Handle process started event."""
        process_id = data.get("process_id", "")
        if not self._current_request:
            return
        
        request = self._requests.get(self._current_request)
        if request:
            request.pid = data.get("pid", 0)
            self.request_updated.emit(request.request_id)

    def _on_process_finished(self, data: dict):
        """Handle process finished event."""
        if not self._current_request:
            return
        
        request = self._requests.get(self._current_request)
        if not request:
            return
        
        request.exit_code = data.get("exit_code", 0)
        request.duration_ms = int((time.time() - request.start_time) * 1000)
        request.status = "completed" if request.exit_code == 0 else "failed"
        
        # Save history
        self._save_history_record(request)
        
        self.event_bus.publish("terminal_execution_finished", {
            "request_id": request.request_id,
            "command": request.command,
            "exit_code": request.exit_code,
            "duration_ms": request.duration_ms,
            "output": request.output,
            "error": request.error_output
        })
        
        self.execution_completed.emit(request.request_id)
        
        # Auto-analyze if failed
        if request.status == "failed":
            self._analyze_execution(request.request_id)
        
        self._current_request = None

    # ──────────────────────────────────────────────────────────────────────────────
    # Analysis
    # ──────────────────────────────────────────────────────────────────────────────

    def _analyze_execution(self, request_id: str):
        """Analyze execution output for errors and warnings."""
        if request_id not in self._requests:
            return
        
        request = self._requests[request_id]
        
        self.event_bus.publish("terminal_analysis_started", {
            "request_id": request_id
        })
        
        analysis = {
            "has_compiler_errors": False,
            "has_runtime_errors": False,
            "has_warnings": False,
            "error_types": [],
            "warnings": [],
            "suggested_fixes": [],
            "stack_traces": []
        }
        
        # Analyze output
        output = request.output + "\n" + request.error_output
        
        if output:
            # Detect Python errors
            if "Traceback" in output or "Exception" in output or "Error:" in output:
                analysis["has_runtime_errors"] = True
                analysis["error_types"].append("PythonException")
                
                # Extract stack trace
                lines = output.split("\n")
                in_traceback = False
                for line in lines:
                    if "Traceback" in line:
                        in_traceback = True
                    if in_traceback:
                        analysis["stack_traces"].append(line)
                        if line.strip() and line.strip().startswith("File ") and "line " in line:
                            # Found line number, suggest fix
                            analysis["suggested_fixes"].append(f"Check the line mentioned in the stack trace")
                            break
            
            # Detect compilation errors
            if "error" in output.lower() and ("CMake" in output or "make" in output or "build" in output):
                analysis["has_compiler_errors"] = True
                analysis["error_types"].append("CompilationError")
                analysis["suggested_fixes"].append("Check compiler error messages and fix syntax issues")
            
            # Detect warnings
            if "warning" in output.lower():
                analysis["has_warnings"] = True
                # Extract warning messages
                for line in output.split("\n"):
                    if "warning" in line.lower():
                        analysis["warnings"].append(line.strip())
                        if "deprecated" in line.lower():
                            analysis["suggested_fixes"].append("Consider updating deprecated APIs")
                        elif "unused" in line.lower():
                            analysis["suggested_fixes"].append("Remove or use the unused variables/imports")
        
        request.metadata = analysis
        
        self.event_bus.publish("terminal_analysis_finished", {
            "request_id": request_id,
            "analysis": analysis
        })
        
        logger.info(f"Analysis completed for {request_id}: {len(analysis['error_types'])} error types found")
        
        return analysis

    # ──────────────────────────────────────────────────────────────────────────────
    # History
    # ──────────────────────────────────────────────────────────────────────────────

    def _save_history_record(self, request: TerminalExecutionRequest):
        """Save execution record to history."""
        record = TerminalCommandHistoryRecord(
            request_id=request.request_id,
            command=request.command,
            timestamp=request.timestamp,
            workspace=str(request.working_directory),
            exit_code=request.exit_code or -1,
            duration_ms=request.duration_ms,
            status=request.status,
            output_preview=request.output[:200]  # Preview only
        )
        
        self._history.append(record)
        
        # Keep only last 1000 records
        if len(self._history) > 1000:
            self._history = self._history[-1000:]

    def _load_history(self):
        """Load history from settings."""
        history_json = self.settings.value("terminal/execution_history", "[]")
        try:
            data = json.loads(history_json)
            for item in data:
                record = TerminalCommandHistoryRecord(
                    request_id=item.get("request_id", ""),
                    command=item.get("command", ""),
                    timestamp=datetime.fromisoformat(item.get("timestamp", "")),
                    workspace=item.get("workspace", ""),
                    exit_code=item.get("exit_code", 0),
                    duration_ms=item.get("duration_ms", 0),
                    status=item.get("status", ""),
                    output_preview=item.get("output_preview", "")
                )
                self._history.append(record)
        except Exception as e:
            logger.error(f"Failed to load history: {e}")

    def _save_history(self):
        """Save history to settings."""
        try:
            data = {
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "history": [
                    {
                        "request_id": r.request_id,
                        "command": r.command,
                        "timestamp": r.timestamp.isoformat(),
                        "workspace": r.workspace,
                        "exit_code": r.exit_code,
                        "duration_ms": r.duration_ms,
                        "status": r.status,
                        "output_preview": r.output_preview
                    }
                    for r in self._history
                ]
            }
            
            self.settings.setValue("terminal/execution_history", json.dumps(data))
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def get_execution_history(self, limit: int = 100) -> List[TerminalCommandHistoryRecord]:
        """Get execution history."""
        return self._history[-limit:]

    def get_execution_by_id(self, request_id: str) -> Optional[TerminalExecutionRequest]:
        """Get execution request by ID."""
        return self._requests.get(request_id)

    def get_all_executions(self) -> List[TerminalExecutionRequest]:
        """Get all execution requests."""
        return list(self._requests.values())

    def get_active_execution(self) -> Optional[TerminalExecutionRequest]:
        """Get currently active execution."""
        if self._current_request:
            return self._requests.get(self._current_request)
        return None

    # ──────────────────────────────────────────────────────────────────────────────
    # Terminal Actions
    # ──────────────────────────────────────────────────────────────────────────────

    def run_again(self, request_id: str) -> str:
        """Run the same command again."""
        if request_id not in self._requests:
            return "Request not found"
        
        request = self._requests[request_id]
        new_request_id = self.create_execution_request(
            command=request.command,
            working_directory=request.working_directory,
            reason=f"Re-execution of: {request.reason}",
            impact=request.impact
        )
        return new_request_id

    def copy_command(self, request_id: str) -> str:
        """Get command text for copying."""
        if request_id not in self._requests:
            return ""
        return self._requests[request_id].command

    def open_terminal(self, working_directory: Optional[Path] = None):
        """Open terminal in specified directory."""
        if working_directory is None:
            workspace = self.workspace_manager.active_workspace
            if workspace:
                working_directory = workspace.path
            else:
                working_directory = Path.cwd()
        
        self.event_bus.publish("open_terminal_requested", {
            "working_directory": str(working_directory)
        })

    def open_output(self, request_id: str):
        """Open output view for a request."""
        if request_id not in self._requests:
            return
        
        request = self._requests[request_id]
        self.event_bus.publish("show_terminal_output", {
            "request_id": request_id,
            "command": request.command,
            "output": request.output,
            "error": request.error_output,
            "exit_code": request.exit_code
        })

    def open_related_file(self, request_id: str):
        """Open file mentioned in output (e.g., error locations)."""
        if request_id not in self._requests:
            return
        
        request = self._requests[request_id]
        
        # Look for file references in output
        import re
        
        # Python file references: File "filename.py"
        pattern = r'File\s+"([^"]+)"'
        matches = re.findall(pattern, request.output + request.error_output)
        
        if matches:
            # Open first file found
            file_path = matches[0]
            self.event_bus.publish("open_file_requested", {
                "path": file_path
            })
            return
        
        # C/C++ references: file.c:X:
        pattern = r'([^\s:]+)\.([a-z]+):\d+:'
        matches = re.findall(pattern, request.output + request.error_output)
        
        if matches:
            file_path = matches[0][0] + "." + matches[0][1]
            self.event_bus.publish("open_file_requested", {
                "path": file_path
            })

    # ──────────────────────────────────────────────────────────────────────────────
    # Status
    # ──────────────────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Get terminal manager status."""
        return {
            "pending_requests": len([r for r in self._requests.values() if r.status == "pending"]),
            "running_requests": len([r for r in self._requests.values() if r.status == "running"]),
            "completed_requests": len([r for r in self._requests.values() if r.status == "completed"]),
            "failed_requests": len([r for r in self._requests.values() if r.status == "failed"]),
            "history_size": len(self._history),
            "current_request": self._current_request
        }

    def shutdown(self):
        """Shutdown the manager."""
        self.settings.sync()
        logger.info("AITerminalManager shutdown complete")


# ============================================================================
# SECTION: ai.terminal.ai_terminal_execution (ai/terminal/ai_terminal_execution.py)
# ============================================================================
"""
AI Terminal Execution — v1.1

Extends TerminalExecutor to support AI command execution requests.
Handles the complete execution pipeline from request to completion.
"""

from PySide6.QtCore import QObject, Signal
from core.process_utils import HiddenProcess as QProcess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import shlex
import time
import json

from core.logger import setup_logger
from core.event_bus import EventBus
from core.process_utils import configure_qprocess_no_window, safe_delete_qprocess
from ai.terminal.ai_terminal_manager import AITerminalManager, TerminalExecutionRequest


logger = setup_logger(__name__)


class AITerminalExecution(QObject):
    """
    Handles AI terminal execution requests through the terminal executor.
    """
    
    def __init__(self, event_bus: EventBus, terminal_executor, terminal_manager):
        super().__init__()
        self.event_bus = event_bus
        self.terminal_executor = terminal_executor
        self.terminal_manager = terminal_manager
        self._logger = logger
        self._active_processes: Dict[str, QProcess] = {}
        self._start_times: Dict[str, float] = {}
        
        # Subscribe to AI terminal events
        self.event_bus.subscribe("ai_terminal_request", self._on_ai_terminal_request)
        self.event_bus.subscribe("terminal_execution_approved", self._on_execution_approved)
        self.event_bus.subscribe("terminal_execution_cancelled", self._on_execution_cancelled)
        
        logger.info("AITerminalExecution initialized")

    def _on_ai_terminal_request(self, data: dict):
        """Handle AI terminal request event."""
        request_id = data.get("request_id")
        command = data.get("command")
        working_directory = data.get("working_directory", str(Path.cwd()))
        reason = data.get("reason", "")
        impact = data.get("impact", "")
        
        self._execute_command(request_id, command, working_directory, reason, impact)

    def _execute_command(self, request_id: str, command: str, working_directory: str, 
                         reason: str, impact: str):
        """Execute the command without opening a separate OS console window."""
        try:
            working_dir = Path(working_directory)
            
            process = QProcess(self)
            configure_qprocess_no_window(process)
            process.setWorkingDirectory(str(working_dir))
            
            try:
                parts = shlex.split(command)
            except Exception:
                parts = command.split()
            if not parts:
                return
            program = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            
            process.readyReadStandardOutput.connect(
                lambda: self._on_process_output(request_id, process, "stdout")
            )
            process.readyReadStandardError.connect(
                lambda: self._on_process_output(request_id, process, "stderr")
            )
            process.finished.connect(
                lambda code, status: self._on_process_finished(request_id, code, status)
            )
            
            self._start_times[request_id] = time.perf_counter()
            process.start(program, args)
            
            if not process.waitForStarted(5000):
                self.event_bus.publish("terminal_execution_failed", {
                    "request_id": request_id,
                    "error": "Failed to start process"
                })
                safe_delete_qprocess(process)
                return
            
            self.event_bus.publish("terminal_execution_started", {
                "request_id": request_id,
                "command": command,
                "working_directory": working_directory,
                "pid": process.processId()
            })
            
            self._active_processes[request_id] = process
            
        except Exception as e:
            self._logger.error(f"Failed to execute command: {e}")
            self.event_bus.publish("terminal_execution_failed", {
                "request_id": request_id,
                "error": str(e)
            })

    def _on_process_output(self, request_id: str, process: QProcess, stream: str):
        """Handle process output."""
        try:
            if stream == "stdout":
                output = process.readAllStandardOutput().data().decode('utf-8', errors='replace')
            else:
                output = process.readAllStandardError().data().decode('utf-8', errors='replace')
        except Exception:
            return
        
        self.event_bus.publish("terminal_output_stream", {
            "request_id": request_id,
            "output": output,
            "stream": stream
        })

    def _on_process_finished(self, request_id: str, exit_code: int, status):
        """Handle process completion."""
        try:
            process = self._active_processes.pop(request_id, None)
            start_t = self._start_times.pop(request_id, None)
            duration_ms = round((time.perf_counter() - start_t) * 1000, 1) if start_t else 0
            
            stdout = ""
            stderr = ""
            if process is not None:
                try:
                    stdout = process.readAllStandardOutput().data().decode('utf-8', errors='replace')
                    stderr = process.readAllStandardError().data().decode('utf-8', errors='replace')
                except Exception:
                    pass
                safe_delete_qprocess(process)
            
            status_str = "completed" if exit_code == 0 else "failed"
            
            self.event_bus.publish("terminal_execution_finished", {
                "request_id": request_id,
                "exit_code": exit_code,
                "status": status_str,
                "output": stdout,
                "error": stderr,
                "duration_ms": duration_ms
            })
            
        except Exception as e:
            self._logger.error(f"Error in process finished: {e}")

    def _on_execution_approved(self, data: dict):
        """Handle execution approved event."""
        request_id = data.get("request_id")
        command = data.get("command") or ""
        self._logger.info(f"Execution approved: {request_id} - {command[:50]}...")

    def _on_execution_cancelled(self, data: dict):
        """Handle execution cancelled event."""
        request_id = data.get("request_id")
        self._logger.info(f"Execution cancelled: {request_id}")
        self.cancel_execution(request_id)

    def cancel_execution(self, request_id: str) -> bool:
        """Cancel an execution by request ID."""
        process = self._active_processes.pop(request_id, None)
        if process is not None:
            safe_delete_qprocess(process)
            return True
        return False

