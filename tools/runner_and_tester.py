"""
Consolidated Module: tools.runner_and_tester

Combines: core.run_manager, core.program_tester
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['core.run_manager', 'core.program_tester']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: core.run_manager (core/run_manager.py)
# ============================================================================
"""
Run Manager — v2.2

Intelligent project execution and automated testing system.
Automatically detects project/file type, executes with hidden console windows,
supports live interactive stdin/stdout streaming for the Terminal tab, and
integrates with the Smart Program Tester (`core.program_tester`) for one-click
program testing and built-in terminal diagnostics.
"""
import os
import sys
import subprocess
import json
import shutil
import threading
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from core.qt_compat import QObject, Signal
from core.process_utils import HiddenProcess as QProcess
from core.process_utils import (
    configure_qprocess_no_window,
    safe_delete_qprocess,
    run_terminal_self_test,
)
from core.logger import setup_logger

logger = setup_logger(__name__)


def python_command(working_dir: Optional[Path] = None) -> str:
    """The interpreter to run user Python with.

    Prefers a virtualenv inside the project (``.venv``/``venv``), then the
    interpreter running the IDE, and only falls back to a bare ``python`` name.
    """
    for base in filter(None, [working_dir]):
        for venv in (".venv", "venv", "env"):
            candidates = ("bin/python", "Scripts/python.exe")
            if os.name == "nt":
                candidates = ("Scripts/pythonw.exe",) + candidates
            for rel in candidates:
                cand = Path(base) / venv / rel
                if cand.exists():
                    return str(cand)
    exe = sys.executable or ""
    if exe and not getattr(sys, "frozen", False):
        if os.name == "nt":
            pythonw = Path(exe).with_name("pythonw.exe")
            if pythonw.exists():
                return str(pythonw)
        return exe
    if os.name == "nt":
        return shutil.which("pythonw") or shutil.which("python") or "python"
    return shutil.which("python3") or shutil.which("python") or "python"


def interactive_python_command(working_dir: Optional[Path] = None) -> str:
    """
    Return the standard `python` executable for piped interactive execution
    inside `HiddenProcess` (which already suppresses external console windows
    via `CREATE_NO_WINDOW` + `SW_HIDE`, while preserving full interactive
    stdin/stdout flushing for `input()` prompts).
    """
    cmd = python_command(working_dir)
    if os.name == "nt" and cmd.lower().endswith("pythonw.exe"):
        py_console = Path(cmd).with_name("python.exe")
        if py_console.exists():
            return str(py_console)
    return cmd


class RunConfiguration:
    """Represents a run configuration for a file or project."""
    def __init__(
        self,
        name: str,
        command: List[str],
        working_dir: Path,
        env: Optional[Dict[str, str]] = None,
        stdin_data: Optional[str] = None,
    ):
        self.name = name
        self.command = command
        self.working_dir = working_dir
        self.env = env or {}
        self.stdin_data = stdin_data


class RunManager(QObject):
    """
    Manages project and file execution, live interactive stdin/stdout in the
    Terminal tab, smart auto-testing, and terminal self-tests.
    """
    output_received = Signal(str)  # output text
    error_received = Signal(str)   # error text
    process_started = Signal(str)  # command
    process_finished = Signal(int) # exit code

    def __init__(self, event_bus):
        super().__init__()
        self.event_bus = event_bus
        self.current_process: Optional[QProcess] = None
        self.workspace_root: Optional[Path] = None
        self._pending_run: Optional[Tuple[str, List[str]]] = None
        self._test_running = False

        # Subscribe to events
        self.event_bus.subscribe("workspace_loaded", self._on_workspace_loaded)
        self.event_bus.subscribe("run_requested", self._on_run_requested)
        self.event_bus.subscribe("stop_requested", self._on_stop_requested)
        self.event_bus.subscribe("stdin_input", self._on_stdin_input)
        self.event_bus.subscribe("test_requested", self._on_test_requested)
        self.event_bus.subscribe("terminal_test_requested", self._on_terminal_test_requested)

    def is_running(self) -> bool:
        return bool(
            self.current_process is not None
            and self.current_process.state() != QProcess.NotRunning
        )

    def write_stdin(self, text: str) -> bool:
        """Write user-typed terminal input to the currently running process."""
        if not self.is_running() or self.current_process is None:
            return False
        payload = text if text.endswith("\n") else text + "\n"
        try:
            written = self.current_process.write(payload.encode("utf-8"))
            return written >= 0
        except Exception:
            return False

    def _on_stdin_input(self, data):
        if isinstance(data, dict):
            text = data.get("text", "")
            if text is not None:
                self.write_stdin(str(text))

    def _on_workspace_loaded(self, data):
        """Update workspace root when workspace is loaded."""
        if not isinstance(data, dict):
            return
        path = data.get("path") or data.get("root_path")
        if not path:
            context = data.get("context")
            path = getattr(context, "root_path", None) if context else None
        if path:
            try:
                self.workspace_root = Path(path)
            except Exception:
                self.workspace_root = None

    def _on_run_requested(self, data):
        """Handle run request from UI."""
        data = data or {}
        file_path = data.get("file_path")
        stdin_data = data.get("stdin_data")
        if file_path:
            self.run_file(Path(file_path), stdin_data=stdin_data)
        elif self.workspace_root:
            self.run_project(self.workspace_root)

    def _on_test_requested(self, data):
        """Handle Quick Test or Custom Test request from UI."""
        if not isinstance(data, dict):
            data = {}
        file_path = data.get("file_path")
        code = data.get("code")
        custom_config = data.get("config") or {}
        self.test_file(
            file_path=Path(file_path) if file_path else None,
            code=code,
            custom_config=custom_config,
        )

    def _on_terminal_test_requested(self, data):
        """Handle Terminal Self-Test request from UI."""
        cwd = (data or {}).get("cwd") or (str(self.workspace_root) if self.workspace_root else "")
        self.test_terminal(cwd=cwd)

    def _on_stop_requested(self, data):
        """Stop currently running process."""
        self.stop_process()

    def run_file(self, file_path: Path, stdin_data: Optional[str] = None):
        """Run a single file."""
        if not file_path.exists():
            self._fail(f"File not found: {file_path}")
            return

        config = self.detect_file_run_config(file_path)
        if config:
            if stdin_data is not None:
                config.stdin_data = stdin_data
            self.execute(config)
        else:
            self._fail(f"Unable to determine how to run: {file_path.name}")

    def test_file(
        self,
        file_path: Optional[Path] = None,
        code: Optional[str] = None,
        custom_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Run the Smart Program Tester on a file or code buffer in a worker thread
        so the UI stays responsive and zero external console windows appear.
        """
        if self._test_running:
            self.event_bus.publish("log_message", {
                "message": "A program test is already running."
            })
            return

        if file_path is None and not code:
            self._fail("No active file or code to test.")
            return

        if file_path is not None and not file_path.exists() and not code:
            self._fail(f"File not found: {file_path}")
            return

        self._test_running = True
        target_name = file_path.name if file_path else "buffer"
        self.event_bus.publish("log_message", {
            "message": f"🧪 Testing {target_name} with smart auto-generated inputs…"
        })

        def _worker():
            try:
                from core.program_tester import run_program_test
                result = run_program_test(
                    file_path=file_path,
                    code=code,
                    custom_config=custom_config,
                )
                self.event_bus.publish("process_output", {
                    "output": result.formatted_output,
                    "stream": "stdout" if result.success else "stderr",
                    "source": "test",
                })
                self.event_bus.publish("test_finished", {
                    "success": result.success,
                    "exit_code": result.exit_code,
                    "duration_ms": result.duration_ms,
                    "language": result.language,
                    "mode": result.mode,
                    "profile_summary": result.profile_summary,
                    "pattern_name": result.pattern_name,
                    "stdin_text": result.stdin_text,
                    "annotated_inputs": result.annotated_inputs,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "issue_summary": result.issue_summary,
                    "quick_fix": result.quick_fix,
                    "formatted_output": result.formatted_output,
                    "scenarios_run": result.scenarios_run,
                    "scenarios_passed": result.scenarios_passed,
                })
                exit_c = 0 if result.success else (result.exit_code if result.exit_code != 0 else 1)
                self.event_bus.publish("process_finished", {
                    "exit_code": exit_c,
                    "is_test": True,
                })
            except Exception as exc:
                logger.error(f"Program test failed: {exc}", exc_info=True)
                self._fail(f"Test execution error: {exc}")
            finally:
                self._test_running = False

        threading.Thread(target=_worker, daemon=True, name="smart-program-tester").start()

    def test_terminal(self, cwd: Optional[str] = None):
        """Run the built-in Terminal Diagnostics & Self-Test in a background thread."""
        work_dir = cwd or (str(self.workspace_root) if self.workspace_root else os.getcwd())
        self.event_bus.publish("log_message", {
            "message": "🔧 Running integrated terminal diagnostics…"
        })

        def _worker():
            try:
                report = run_terminal_self_test(cwd=work_dir)
                self.event_bus.publish("process_output", {
                    "output": report["formatted_report"],
                    "stream": "stdout" if report["passed"] else "stderr",
                    "source": "terminal_test",
                })
                self.event_bus.publish("terminal_test_finished", report)
                self.event_bus.publish("process_finished", {
                    "exit_code": 0 if report["passed"] else 1,
                    "is_terminal_test": True,
                })
            except Exception as exc:
                logger.error(f"Terminal self-test failed: {exc}", exc_info=True)
                self._fail(f"Terminal self-test error: {exc}")

        threading.Thread(target=_worker, daemon=True, name="terminal-self-test").start()

    def run_project(self, project_root: Path):
        """Run entire project."""
        config = self.detect_project_run_config(project_root)
        if config:
            self.execute(config)
        else:
            self._fail("Unable to determine how to run project. "
                       "Please configure a custom run command.")

    def _fail(self, message: str):
        """Report a run that never started."""
        logger.warning(message)
        self.event_bus.publish("log_message", {"message": message})
        self.event_bus.publish("process_output",
                               {"output": message + "\n", "stream": "stderr", "source": "run"})
        self.event_bus.publish("process_finished", {"exit_code": -1})

    def detect_file_run_config(self, file_path: Path) -> Optional[RunConfiguration]:
        """Detect how to run a single file based on its extension."""
        ext = file_path.suffix.lower()
        name = file_path.stem
        parent = file_path.parent

        # Python (unbuffered -u so interactive input() prompts flush immediately)
        if ext == ".py":
            return RunConfiguration(
                name=f"Python: {file_path.name}",
                command=[interactive_python_command(parent), "-u", str(file_path)],
                working_dir=parent,
                env={"PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"},
            )

        # JavaScript/Node.js
        if ext in [".js", ".mjs"]:
            return RunConfiguration(
                name=f"Node: {file_path.name}",
                command=["node", str(file_path)],
                working_dir=parent
            )

        # TypeScript
        if ext == ".ts":
            return RunConfiguration(
                name=f"TypeScript: {file_path.name}",
                command=["tsx", str(file_path)],
                working_dir=parent
            )

        # Dart
        if ext == ".dart":
            return RunConfiguration(
                name=f"Dart: {file_path.name}",
                command=["dart", "run", str(file_path)],
                working_dir=parent
            )

        # Rust (single file)
        if ext == ".rs":
            executable = f"{name}.exe" if os.name == "nt" else f"./{name}"
            return RunConfiguration(
                name=f"Rust: {file_path.name}",
                command=["rustc", str(file_path), "-o", executable, "&&", executable],
                working_dir=parent
            )

        # Go
        if ext == ".go":
            return RunConfiguration(
                name=f"Go: {file_path.name}",
                command=["go", "run", str(file_path)],
                working_dir=parent
            )

        # C
        if ext == ".c":
            executable = f"{name}.exe" if os.name == "nt" else name
            run_command = f".\\{executable}" if os.name == "nt" else f"./{executable}"
            return RunConfiguration(
                name=f"C: {file_path.name}",
                command=["gcc", str(file_path), "-o", executable, "&&", run_command],
                working_dir=parent
            )

        # C++
        if ext in [".cpp", ".cc", ".cxx"]:
            executable = f"{name}.exe" if os.name == "nt" else name
            run_command = f".\\{executable}" if os.name == "nt" else f"./{executable}"
            return RunConfiguration(
                name=f"C++: {file_path.name}",
                command=["g++", str(file_path), "-o", executable, "&&", run_command],
                working_dir=parent
            )

        # Java
        if ext == ".java":
            return RunConfiguration(
                name=f"Java: {file_path.name}",
                command=["javac", str(file_path), "&&", "java", name],
                working_dir=parent
            )

        # C#
        if ext == ".cs":
            return RunConfiguration(
                name=f"C#: {file_path.name}",
                command=["dotnet", "run"],
                working_dir=parent
            )

        # PHP
        if ext == ".php":
            return RunConfiguration(
                name=f"PHP: {file_path.name}",
                command=["php", str(file_path)],
                working_dir=parent
            )

        # Ruby
        if ext == ".rb":
            return RunConfiguration(
                name=f"Ruby: {file_path.name}",
                command=["ruby", str(file_path)],
                working_dir=parent
            )

        # Shell scripts
        if ext in [".sh", ".bash"]:
            return RunConfiguration(
                name=f"Bash: {file_path.name}",
                command=["bash", str(file_path)],
                working_dir=parent
            )

        # PowerShell
        if ext == ".ps1":
            return RunConfiguration(
                name=f"PowerShell: {file_path.name}",
                command=["powershell", "-ExecutionPolicy", "Bypass", "-File", str(file_path)],
                working_dir=parent
            )

        # Batch
        if ext in [".bat", ".cmd"]:
            return RunConfiguration(
                name=f"Batch: {file_path.name}",
                command=[str(file_path)],
                working_dir=parent
            )

        return None

    def detect_project_run_config(self, project_root: Path) -> Optional[RunConfiguration]:
        """Detect how to run a project based on its structure and configuration files."""
        # Flutter
        if (project_root / "pubspec.yaml").exists():
            with open(project_root / "pubspec.yaml", "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                if "flutter:" in content:
                    return RunConfiguration(
                        name="Flutter Run",
                        command=["flutter", "run"],
                        working_dir=project_root
                    )
                else:
                    return RunConfiguration(
                        name="Dart Run",
                        command=["dart", "run"],
                        working_dir=project_root
                    )

        # Django
        if (project_root / "manage.py").exists():
            return RunConfiguration(
                name="Django Development Server",
                command=[interactive_python_command(project_root), "-u", "manage.py", "runserver"],
                working_dir=project_root
            )

        # FastAPI
        main_py = project_root / "main.py"
        if main_py.exists():
            try:
                with open(main_py, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                    if "from fastapi" in content or "import fastapi" in content:
                        return RunConfiguration(
                            name="FastAPI Server",
                            command=["uvicorn", "main:app", "--reload"],
                            working_dir=project_root
                        )
            except Exception:
                pass

        # Node.js projects
        package_json = project_root / "package.json"
        if package_json.exists():
            try:
                with open(package_json, "r", encoding="utf-8", errors="replace") as f:
                    pkg = json.load(f)
                    scripts = pkg.get("scripts", {})
                    if "dev" in scripts:
                        return RunConfiguration(
                            name="npm run dev",
                            command=["npm", "run", "dev"],
                            working_dir=project_root
                        )
                    elif "start" in scripts:
                        return RunConfiguration(
                            name="npm start",
                            command=["npm", "start"],
                            working_dir=project_root
                        )
            except Exception:
                pass

        # Rust (Cargo)
        if (project_root / "Cargo.toml").exists():
            return RunConfiguration(
                name="Cargo Run",
                command=["cargo", "run"],
                working_dir=project_root
            )

        # Go
        if (project_root / "go.mod").exists():
            return RunConfiguration(
                name="Go Run",
                command=["go", "run", "."],
                working_dir=project_root
            )

        # .NET
        csproj_files = list(project_root.glob("*.csproj"))
        if csproj_files:
            return RunConfiguration(
                name=".NET Run",
                command=["dotnet", "run"],
                working_dir=project_root
            )

        # Maven
        if (project_root / "pom.xml").exists():
            return RunConfiguration(
                name="Maven Run",
                command=["mvn", "spring-boot:run"],
                working_dir=project_root
            )

        # Gradle
        if (project_root / "build.gradle").exists() or (project_root / "build.gradle.kts").exists():
            return RunConfiguration(
                name="Gradle Run",
                command=["gradle", "run"],
                working_dir=project_root
            )

        # Python script
        for entry_point in ["main.py", "app.py", "run.py"]:
            if (project_root / entry_point).exists():
                return RunConfiguration(
                    name=f"Python: {entry_point}",
                    command=[interactive_python_command(project_root), "-u", entry_point],
                    working_dir=project_root,
                    env={"PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"},
                )

        return None

    def execute(self, config: RunConfiguration):
        """Execute a run configuration (restarting cleanly if a previous run was still active)."""
        if self.current_process and self.current_process.state() != QProcess.NotRunning:
            self.stop_process()

        # Clean up previous process safely
        if self.current_process:
            safe_delete_qprocess(self.current_process)
            self.current_process = None

        self.current_process = QProcess()
        configure_qprocess_no_window(self.current_process)
        self.current_process.setWorkingDirectory(str(config.working_dir))

        # Set environment
        if config.env:
            env = self.current_process.processEnvironment()
            for key, value in config.env.items():
                if hasattr(env, "insert"):
                    env.insert(key, value)
                elif isinstance(env, dict):
                    env[key] = value
            self.current_process.setProcessEnvironment(env)

        # Connect signals
        self.current_process.readyReadStandardOutput.connect(self._on_output)
        self.current_process.readyReadStandardError.connect(self._on_error)
        self.current_process.finished.connect(self._on_finished)
        self.current_process.errorOccurred.connect(self._on_process_error)

        cmd_str = " ".join(config.command)
        logger.info(f"Executing: {cmd_str} in {config.working_dir}")
        self.event_bus.publish("run_started", {
            "name": config.name,
            "command": cmd_str,
            "cwd": str(config.working_dir),
        })
        self.event_bus.publish("log_message", {
            "message": f"▶ {config.name}: {cmd_str}"
        })

        # Compile C/C++/Rust/Java natively without cmd.exe shell popup
        if "&&" in config.command and config.command[0] in ("gcc", "g++", "rustc", "javac"):
            separator = config.command.index("&&")
            compile_program = config.command[0]
            compile_args = list(config.command[1:separator])
            run_tokens = list(config.command[separator + 1:])
            run_program = run_tokens[0]
            run_args = run_tokens[1:]
            if os.name == "nt" and run_program not in ("java",) and not Path(run_program).is_absolute():
                run_program = str(config.working_dir / run_program.lstrip(".\\/"))
            self._pending_run = (run_program, run_args)
            self.current_process.start(compile_program, compile_args)
        else:
            if "&&" in config.command:
                joined = " ".join(config.command)
                if os.name == "nt":
                    program, args = "cmd", ["/Q", "/D", "/C", joined]
                else:
                    program, args = "/bin/sh", ["-c", joined]
            else:
                program = config.command[0]
                args = list(config.command[1:])
            self.current_process.start(program, args)
            if config.stdin_data and self.current_process is not None:
                try:
                    self.current_process.write(config.stdin_data.encode("utf-8"))
                except Exception:
                    pass
        self.process_started.emit(cmd_str)

    def _on_process_error(self, error):
        """Surface a process that failed to launch as a finished-with-error run."""
        proc = self.current_process
        program = proc.program() if proc is not None else ""
        if error == QProcess.FailedToStart:
            msg = (f"Failed to start: {program or 'command'} — "
                   "is it installed and on your PATH?")
        elif error == QProcess.Crashed:
            msg = f"Process crashed: {program or 'command'}"
        else:
            msg = f"Process error ({int(error)}): {program or 'command'}"
        self._fail(msg)

    def _cleanup_process(self):
        """Clean up finished process safely."""
        if self.current_process:
            proc = self.current_process
            self.current_process = None
            safe_delete_qprocess(proc)

    def stop_process(self):
        """Stop currently running process immediately."""
        self._pending_run = None
        if self.current_process and self.current_process.state() != QProcess.NotRunning:
            logger.info("Terminating process...")
            try:
                self.current_process.terminate()
                if not self.current_process.waitForFinished(800):
                    logger.warning("Process did not terminate, killing...")
                    self.current_process.kill()
            except Exception:
                pass
            self._cleanup_process()
            self.event_bus.publish("log_message", {"message": "⏹ Process stopped"})
            self.event_bus.publish("process_finished", {"exit_code": -1, "stopped": True})

    def _on_output(self):
        """Handle stdout from process."""
        if self.current_process:
            try:
                data = self.current_process.readAllStandardOutput().data().decode('utf-8', errors='replace')
            except RuntimeError:
                return
            self.output_received.emit(data)
            self.event_bus.publish("process_output", {"output": data, "stream": "stdout", "source": "run"})

    def _on_error(self):
        """Handle stderr from process."""
        if self.current_process:
            try:
                data = self.current_process.readAllStandardError().data().decode('utf-8', errors='replace')
            except RuntimeError:
                return
            self.error_received.emit(data)
            self.event_bus.publish("process_output", {"output": data, "stream": "stderr", "source": "run"})

    def _on_finished(self, exit_code, exit_status):
        """Handle process completion."""
        if self._pending_run is not None and exit_code == 0 and self.current_process is not None:
            program, args = self._pending_run
            self._pending_run = None
            self.event_bus.publish("log_message", {
                "message": f"✓ Compilation succeeded; running {Path(program).name}"
            })
            self.current_process.start(program, args)
            return
        self._pending_run = None
        self.process_finished.emit(exit_code)

        if exit_code == 0:
            msg = f"✓ Process finished successfully (exit code {exit_code})"
        else:
            msg = f"✗ Process finished with error (exit code {exit_code})"

        self.event_bus.publish("log_message", {"message": msg})
        self.event_bus.publish("process_finished", {"exit_code": exit_code, "source": "run"})
        self._cleanup_process()


# ============================================================================
# SECTION: core.program_tester (core/program_tester.py)
# ============================================================================
"""
Smart Program & Algorithm Tester — v2.0

Automatically analyzes source code in any language (Python, C, C++, Java,
JavaScript/Node, TypeScript, Go, Rust, Ruby, PHP, C#, Dart, Bash, PowerShell),
detects what kind of inputs it expects, generates fresh randomized dummy inputs
on every run, executes the program with zero external console window flashing,
and produces either:
  - The clean execution result + dummy inputs used + "Code ran successfully", OR
  - A concise 1-2 line error description + a 1-line quick fix.

Key capabilities:
1. Interactive Menu / Data Structure Detection (Stack, Queue, Linked List, Tree,
   CRUD, Bank, Calculator):
   - Maps each menu option number to its action (Push/Insert, Pop/Delete,
     Peek/Search, Display, Exit) and inspects each branch for extra inputs.
   - Generates randomized multi-step operation sequences (Push multiple items,
     Peek, Display, Pop, Push again, Display, then Exit) instead of static
     samples or immediately exiting with '5'.
2. Array / N-Elements Detection:
   - Detects fixed-size loops (e.g., 10 elements) or dynamic count N + N elements,
     plus optional search targets (automatically sorting when binary search is
     detected).
3. Structured Entity / Record Detection (Student, Employee, Book, Product, etc.):
   - Detects fields (name, age, roll/id, marks/gpa, salary, dept, email, etc.)
     and generates realistic randomized records for 1 or N entities.
4. Customizable Testing:
   - Supports full customization from the Left Sidebar Tests panel (input type,
     count/size, value range, entity fields, menu choices, custom raw stdin,
     and multi-scenario batch testing).
"""

import os
import random
import re
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.process_utils import run_hidden_command
from core.run_manager import python_command

# Always use a hardware/OS-seeded RNG so every click produces fresh random values
_RNG = random.SystemRandom()

_FIRST_NAMES = [
    "Aarav", "Priya", "Rohan", "Ananya", "Vikram", "Neha", "Arjun", "Kavya",
    "Siddharth", "Meera", "Aditya", "Ishita", "Karan", "Divya", "Rahul", "Pooja",
    "Nikhil", "Sneha", "Varun", "Tanvi", "Dev", "Riya", "kabir", "Zoya",
]
_LAST_NAMES = [
    "Sharma", "Patel", "Verma", "Nair", "Gupta", "Singh", "Joshi", "Iyer",
    "Mehta", "Reddy", "Kapoor", "Malhotra", "Rao", "Bhatia", "Chauhan", "Das",
]
_DEPARTMENTS = ["Computer Science", "Electronics", "Mechanical", "Information Tech", "Civil", "AI & DS"]
_COURSES = ["B.Tech CSE", "BCA", "MCA", "B.Sc CS", "M.Tech AI", "B.Tech IT"]
_CITIES = ["Dehradun", "Delhi", "Mumbai", "Bengaluru", "Pune", "Hyderabad", "Chennai", "Kolkata"]
_WORDS = [
    "alpha", "bravo", "quantum", "nebula", "vertex", "matrix", "cipher", "photon",
    "cosmos", "zenith", "aurora", "falcon", "horizon", "prism", "vector", "nexus",
]
_GRADES = ["A+", "A", "B+", "B", "O"]


@dataclass
class MenuOptionSpec:
    """Represents a single option in a menu-driven program."""
    choice: str
    label: str
    role: str  # "push", "pop", "peek", "display", "search", "update", "exit", "other"
    extra_inputs: List[str] = field(default_factory=list)  # types of extra inputs needed


@dataclass
class ProgramInputProfile:
    """Detected input profile for a source file."""
    language: str
    requires_input: bool
    mode: str  # "no_input", "menu_loop", "entity_records", "array_elements", "sequence_inputs"
    summary: str
    count: int = 5
    has_count_prefix: bool = False
    fixed_count: Optional[int] = None
    element_type: str = "int"  # "int", "sorted_int", "float", "string", "name"
    needs_search_target: bool = False
    space_separated_elements: bool = False
    entity_fields: List[str] = field(default_factory=list)
    sequence_fields: List[Tuple[str, str]] = field(default_factory=list)  # [(label, field_type), ...]
    menu_options: List[MenuOptionSpec] = field(default_factory=list)
    exit_choice: str = "5"


@dataclass
class GeneratedTestCase:
    """A generated set of dummy inputs for one test execution."""
    stdin_text: str
    input_lines: List[str]
    description: str
    pattern_name: str
    annotated_steps: List[str] = field(default_factory=list)


@dataclass
class ProgramTestResult:
    """Outcome of running a program test (single or multi-scenario)."""
    success: bool
    exit_code: int
    duration_ms: float
    language: str
    mode: str
    profile_summary: str
    pattern_name: str
    stdin_text: str
    annotated_inputs: List[str]
    stdout: str
    stderr: str
    issue_summary: str       # 1-2 short lines if failed, empty if success
    quick_fix: str           # 1 short actionable line if failed, empty if success
    formatted_output: str    # Ready-to-display concise report
    scenarios_run: int = 1
    scenarios_passed: int = 0


# ============================================================================
# 1. Language & Comment Stripping Helpers
# ============================================================================

def detect_language_from_path_or_code(file_path: Optional[Path], code: str) -> str:
    if file_path is not None:
        ext = file_path.suffix.lower()
        ext_map = {
            ".py": "python",
            ".c": "c",
            ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp",
            ".java": "java",
            ".js": "javascript", ".mjs": "javascript",
            ".ts": "typescript",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".cs": "csharp",
            ".dart": "dart",
            ".sh": "bash", ".bash": "bash",
            ".ps1": "powershell",
        }
        if ext in ext_map:
            return ext_map[ext]
    if "#include <iostream>" in code or "std::cin" in code or "cout <<" in code:
        return "cpp"
    if "#include <stdio.h>" in code or "scanf(" in code:
        return "c"
    if "public static void main" in code or "Scanner(" in code:
        return "java"
    if "package main" in code and "func main()" in code:
        return "go"
    if "fn main()" in code and "std::io" in code:
        return "rust"
    return "python"


def _strip_comments(code: str, language: str) -> str:
    """Remove single-line and block comments so commented-out inputs are ignored."""
    if language in ("python", "ruby", "bash", "powershell"):
        lines = []
        for line in code.splitlines():
            # Strip # comments outside quotes (simple heuristic)
            cleaned = re.sub(r'(?<!["\'])#.*$', "", line)
            lines.append(cleaned)
        return "\n".join(lines)
    else:
        # C/C++/Java/JS/TS/Go/Rust/C#/PHP/Dart
        no_block = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
        no_line = re.sub(r"//.*$", "", no_block, flags=re.MULTILINE)
        return no_line


# ============================================================================
# 2. Field Type & Value Generation
# ============================================================================

def infer_field_type(hint: str, cast_type: str = "") -> str:
    """Infer semantic field type from a prompt string or variable name."""
    h = (hint or "").lower()
    c = (cast_type or "").lower()

    # Check count / size prompts first
    if re.search(r"\b(number of|how many|count|total|size)\b", h) or re.match(r"^n\b", h):
        return "int"
    # Check specific entity attributes before generic entity nouns
    if re.search(r"\b(age|years old)\b", h):
        return "age"
    if re.search(r"\b(marks|score|percentage|percent|gpa|cgpa|grade_point)\b", h):
        return " marks " .strip() if c not in ("float", "double", "%f", "%lf") and "gpa" not in h and "cgpa" not in h else "marks"
    if re.search(r"\b(roll|roll_no|rollno|reg_no|id|emp_id|student_id|code|pin)\b", h):
        return "id"
    if c not in ("int", "long", "float", "double", "%d", "%i", "%f", "%lf", "nextint", "nextdouble", "nextfloat"):
        if any(k in h for k in ("full name", "student name", "employee name", "emp name", "person name", "author")):
            return "name"
        if re.search(r"\b(name|fname|firstname|lname|lastname)\b", h) and "file" not in h:
            return "name"
    if re.search(r"\b(salary|price|amount|balance|cost|fee|deposit|withdraw)\b", h):
        return "salary" if c in ("int", "%d") else "float"
    if re.search(r"\b(grade|section|division)\b", h):
        return "grade"
    if re.search(r"\b(dept|department|branch)\b", h):
        return "department"
    if re.search(r"\b(course|degree|stream|subject)\b", h):
        return "course"
    if re.search(r"\b(email|mail)\b", h):
        return "email"
    if re.search(r"\b(phone|mobile|contact)\b", h):
        return "phone"
    if re.search(r"\b(city|address|location|town)\b", h):
        return "city"
    if re.search(r"\b(gender|sex)\b", h):
        return "gender"
    if re.search(r"\b(year|semester|sem)\b", h):
        return "year"

    if c in ("float", "double", "%f", "%lf", "nextdouble", "nextfloat", "parsefloat"):
        return "float"
    if c in ("int", "long", "%d", "%i", "%ld", "nextint", "nextlong", "parseint"):
        return "int"
    if c in ("str", "string", "%s", "nextline", "next"):
        if any(k in h for k in ("num", "val", "element", "item", "count", "size", "key", "choice", "option")):
            return "int"
        return "string"

    if any(k in h for k in ("number", "num", "val", "value", "element", "item", "count", "size", "length", "width", "height", "radius", "index", "pos", "key", "target")):
        return "int"
    return "string" if c == "str_explicit" else "int"


def generate_random_value(
    field_type: str,
    min_val: int = 10,
    max_val: int = 99,
    index: int = 0,
) -> str:
    """Generate a single realistic random value for the given semantic field type."""
    ft = (field_type or "int").lower().strip()
    lo, hi = min(min_val, max_val), max(min_val, max_val)
    if lo == hi:
        hi = lo + 50

    if ft in ("name", "full_name", "student_name"):
        return f"{_RNG.choice(_FIRST_NAMES)} {_RNG.choice(_LAST_NAMES)}"
    if ft in ("first_name", "fname"):
        return _RNG.choice(_FIRST_NAMES)
    if ft == "age":
        return str(_RNG.randint(18, 25))
    if ft in ("id", "roll", "roll_no", "rollno", "emp_id"):
        return str(101 + index + _RNG.randint(0, 80))
    if ft == "marks":
        return str(_RNG.randint(62, 98))
    if ft in ("gpa", "cgpa"):
        return f"{_RNG.uniform(7.1, 9.8):.2f}"
    if ft == "salary":
        return str(_RNG.randint(35, 95) * 1000)
    if ft == "float":
        clean_divisors = [d for d in (2, 4, 5, 8, 10, 16, 20, 25, 40, 50) if lo <= d <= hi] or [2, 4, 5, 8, 10]
        if index % 2 == 1:
            return str(_RNG.choice(clean_divisors))
        base = _RNG.randint(max(2, lo), max(10, hi))
        if _RNG.random() < 0.3:
            return f"{base + 0.5:.1f}"
        return str(base)
    if ft == "grade":
        return _RNG.choice(_GRADES)
    if ft in ("department", "dept"):
        return _RNG.choice(_DEPARTMENTS)
    if ft == "course":
        return _RNG.choice(_COURSES)
    if ft == "city":
        return _RNG.choice(_CITIES)
    if ft == "email":
        first = _RNG.choice(_FIRST_NAMES).lower()
        num = _RNG.randint(10, 99)
        return f"{first}{num}@example.com"
    if ft == "phone":
        return f"98{_RNG.randint(10000000, 99999999)}"
    if ft == "gender":
        return _RNG.choice(["M", "F"])
    if ft == "year":
        return str(_RNG.randint(1, 4))
    if ft in ("string", "str", "word", "text"):
        return f"{_RNG.choice(_WORDS)}_{_RNG.randint(10, 99)}"
    # Default: integer (non-zero to avoid accidental ZeroDivisionError)
    val = _RNG.randint(lo, hi)
    if val == 0:
        val = _RNG.randint(1, max(10, hi))
    return str(val)


# ============================================================================
# 3. Deep Code Analyzer (Menu Loops, Entities, Arrays, General Inputs)
# ============================================================================

def _has_any_input_call(cleaned: str, language: str) -> bool:
    patterns = [
        r"\binput\s*\(",
        r"\bsys\.stdin\b",
        r"\bscanf\s*\(",
        r"\bfgets\s*\(",
        r"\bgetchar\s*\(",
        r"\bgets\s*\(",
        r"\bcin\s*>>",
        r"\bgetline\s*\(\s*(?:std::)?cin",
        r"\bScanner\s*\(\s*System\.in\s*\)",
        r"\b(?:\w+)\.next(?:Int|Long|Double|Float|Line|Boolean)?\s*\(",
        r"\bBufferedReader\b",
        r"\breadline\b",
        r"\bprompt\s*\(",
        r"\bfmt\.Scan(?:ln|f)?\s*\(",
        r"\bstdin\s*\(\s*\)\s*\.read_line",
        r"\bgets\b",
        r"\bConsole\.ReadLine\s*\(",
        r"\bread\s+-",
        r"\bRead-Host\b",
    ]
    return any(re.search(p, cleaned) for p in patterns)


def _classify_menu_label(label: str) -> str:
    low = label.lower().strip()
    if any(w in low for w in ("exit", "quit", "stop", "terminate", "close", "end", "bye")):
        return "exit"
    if any(w in low for w in ("subtract", "multiply", "divide", "addition", "subtraction", "multiplication", "division", "modulo", "modulus", "power")):
        return "other"
    if low == "add":
        return "other"
    if any(w in low for w in ("push", "enqueue", "insert", "append", "create", "register", "deposit", "push_back", "push_front")) or low.startswith("add "):
        return "push"
    if any(w in low for w in ("pop", "dequeue", "delete", "remove", "withdraw", "erase", "pop_back", "pop_front")):
        return "pop"
    if any(w in low for w in ("peek", "top", "front", "rear", "isempty", "is_empty", "isfull", "is_full", "size", "count", "length", "balance")):
        return "peek"
    if any(w in low for w in ("display", "show", "print", "traverse", "view", "list", "dump", "all")):
        return "display"
    if any(w in low for w in ("search", "find", "lookup", "contains")):
        return "search"
    if any(w in low for w in ("update", "modify", "edit", "change")):
        return "update"
    return "other"


def _extract_branch_extra_inputs(cleaned: str, choice_str: str, role: str) -> List[str]:
    """
    Inspect the if/elif/case block for `choice_str` to see how many extra
    inputs that specific menu action reads and what types they are.
    """
    esc = re.escape(choice_str)
    # Match Python `if/elif choice == 1:` or `choice == '1':` or C/Java `case 1:` or `case '1':`
    branch_patterns = [
        rf"(?:if|elif)\s+\w+\s*==\s*['\"]?{esc}['\"]?\s*:(.*?)(?=\n\s*(?:elif|else)\b|\Z)",
        rf"case\s+['\"]?{esc}['\"]?\s*:(.*?)(?=\bcase\b|\bdefault\s*:|\Z)",
    ]
    block = ""
    for pat in branch_patterns:
        m = re.search(pat, cleaned, flags=re.DOTALL)
        if m:
            block = m.group(1)[:600]
            break

    if block:
        # Also check if the branch calls a helper function like `push()`, `insert()`, `add_student()`
        # and inspect that function body too!
        helper_calls = re.findall(r"\b([a-zA-Z_]\w*)\s*\(", block)
        for fn_name in helper_calls:
            if fn_name in ("print", "input", "int", "float", "str", "len", "range", "scanf", "printf", "append", "pop"):
                continue
            fn_match = re.search(
                rf"(?:def|void|int|bool|string|float|double)\s+{re.escape(fn_name)}\s*\([^)]*\)\s*(?::|\{{)(.*?)(?=\n(?:def|void|int|class)\b|\Z)",
                cleaned,
                flags=re.DOTALL,
            )
            if fn_match:
                block += "\n" + fn_match.group(1)[:600]

        extra: List[str] = []
        # Python input() calls in this branch
        for m in re.finditer(r"(?:(int|float|str)\s*\(\s*)?input\s*\(\s*(['\"][^'\"]*['\"])?\s*\)", block):
            cast_t = m.group(1) or ""
            prompt_t = (m.group(2) or "").strip("'\"")
            extra.append(infer_field_type(prompt_t, cast_t or "int"))
        # C scanf calls in this branch
        for m in re.finditer(r'scanf\s*\(\s*"([^"]+)"', block):
            fmt = m.group(1)
            for spec in re.findall(r"%[dliufsc]", fmt):
                if spec in ("%f", "%lf"):
                    extra.append("float")
                elif spec == "%s":
                    extra.append("string")
                else:
                    extra.append("int")
        # C++ cin >> calls in this branch
        for m in re.finditer(r"cin\s*((?:>>\s*\w+\s*)+)", block):
            vars_read = re.findall(r">>\s*(\w+)", m.group(1))
            for v in vars_read:
                extra.append(infer_field_type(v, "int"))
        # Java Scanner calls in this branch
        for m in re.finditer(r"\.next(Int|Long|Double|Float|Line)?\s*\(", block):
            kind = (m.group(1) or "Line").lower()
            extra.append("float" if kind in ("double", "float") else "int" if kind in ("int", "long") else "string")

        if extra:
            return extra

    # Fallback based on semantic role if inputs are inside an unparsed method
    if role == "push":
        return ["int"]
    if role == "search":
        return ["int"]
    if role == "update":
        return ["int", "int"]
    return []


def _detect_menu_loop(cleaned: str) -> Optional[Tuple[List[MenuOptionSpec], str]]:
    """
    Detect if the code is an interactive menu loop (e.g., Stack, Queue, Linked List, CRUD).
    Returns (menu_options, exit_choice) if detected, else None.
    """
    has_while_loop = bool(
        re.search(r"\bwhile\s*(?:\(\s*)?(?:True|1|true|\w+\s*!=\s*['\"]?\w+['\"]?)", cleaned)
        or re.search(r"\bdo\s*\{", cleaned)
        or re.search(r"\bfor\s*\(\s*;\s*;\s*\)", cleaned)
    )
    if not has_while_loop:
        return None

    # Extract numbered menu options ONLY from string literals on the same line
    string_segments: List[str] = []
    for m in re.finditer(
        r'"([^"\n\\]*(?:\\.[^"\n\\]*)*)"|\'([^\'\n\\]*(?:\\.[^\'\n\\]*)*)\'',
        cleaned,
    ):
        lit = next((g for g in m.groups() if g is not None), "")
        if lit:
            string_segments.extend(re.split(r"\\n|\r?\n", lit))

    options_by_choice: Dict[str, MenuOptionSpec] = {}
    for seg in string_segments:
        m = re.match(
            r"^\s*\[?([0-9]+)\]?[ \t]*[\.\)\:\-\]][ \t]*([A-Za-z][A-Za-z0-9_ /+\-&]{1,28})\s*$",
            seg.strip(),
        )
        if not m:
            continue
        num, raw_label = m.group(1), m.group(2).strip(" \"'.,;:")
        if not raw_label or len(raw_label) < 2:
            continue
        role = _classify_menu_label(raw_label)
        if num not in options_by_choice:
            extra = _extract_branch_extra_inputs(cleaned, num, role)
            options_by_choice[num] = MenuOptionSpec(
                choice=num, label=raw_label, role=role, extra_inputs=extra
            )

    # Also inspect `if/elif choice == N` or `case N:` in case menu labels weren't numbered with dots
    branch_nums = re.findall(
        r"(?:(?:if|elif)\s+\w+\s*==\s*['\"]?(\d+)['\"]?|case\s+['\"]?(\d+)['\"]?\s*:)",
        cleaned,
    )
    flat_nums = [a or b for a, b in branch_nums if (a or b)]
    for num in flat_nums:
        if num not in options_by_choice:
            # Inspect the branch text to guess its role
            esc = re.escape(num)
            m = re.search(
                rf"(?:(?:if|elif)\s+\w+\s*==\s*['\"]?{esc}['\"]?\s*:|case\s+['\"]?{esc}['\"]?\s*:)(.*?)(?=\n\s*(?:elif|else|case|default)\b|\Z)",
                cleaned,
                flags=re.DOTALL,
            )
            snippet = (m.group(1)[:300] if m else "").lower()
            if "break" in snippet or "exit(" in snippet or "return" in snippet:
                role, label = "exit", "Exit"
            elif any(k in snippet for k in ("push", "append", "insert", "enqueue", "add")):
                role, label = "push", "Push/Insert"
            elif any(k in snippet for k in ("pop", "remove", "delete", "dequeue")):
                role, label = "pop", "Pop/Delete"
            elif any(k in snippet for k in ("peek", "top", "[-1]")):
                role, label = "peek", "Peek"
            elif any(k in snippet for k in ("display", "show", "print", "cout", "printf")):
                role, label = "display", "Display"
            else:
                role, label = "other", f"Option {num}"
            extra = _extract_branch_extra_inputs(cleaned, num, role)
            options_by_choice[num] = MenuOptionSpec(
                choice=num, label=label, role=role, extra_inputs=extra
            )

    # Check if there is an explicit `while choice != N` exit condition
    while_neq = re.search(r"while\s*\(?\s*\w+\s*!=\s*['\"]?(\d+)['\"]?", cleaned)
    if while_neq:
        exit_num = while_neq.group(1)
        if exit_num not in options_by_choice:
            options_by_choice[exit_num] = MenuOptionSpec(
                choice=exit_num, label="Exit", role="exit", extra_inputs=[]
            )
        else:
            options_by_choice[exit_num].role = "exit"

    if len(options_by_choice) < 2:
        return None

    opts = [options_by_choice[k] for k in sorted(options_by_choice.keys(), key=lambda x: int(x) if x.isdigit() else 99)]
    exit_opt = next((o for o in opts if o.role == "exit"), None)
    if exit_opt is None:
        # Usually the highest numbered option (e.g., 4 or 5) or 0 is exit
        last_opt = opts[-1]
        last_opt.role = "exit"
        exit_choice = last_opt.choice
    else:
        exit_choice = exit_opt.choice

    return opts, exit_choice


def analyze_program(code: str, file_path: Optional[Path] = None) -> ProgramInputProfile:
    """
    Statically analyze source code to determine what inputs it needs, how many,
    and what structure (menu loop, entity records, N-element array, or sequence).
    """
    language = detect_language_from_path_or_code(file_path, code)
    cleaned = _strip_comments(code, language)

    if not _has_any_input_call(cleaned, language):
        return ProgramInputProfile(
            language=language,
            requires_input=False,
            mode="no_input",
            summary=f"{language.title()} program (no stdin input required)",
        )

    # 1. Check for Interactive Menu / Data Structure Loop (Stack, Queue, LinkedList, CRUD)
    menu_res = _detect_menu_loop(cleaned)
    if menu_res is not None:
        menu_opts, exit_choice = menu_res
        labels = ", ".join(f"{o.choice}:{o.label}" for o in menu_opts)
        return ProgramInputProfile(
            language=language,
            requires_input=True,
            mode="menu_loop",
            summary=f"Interactive Menu Program ({labels})",
            count=10,
            menu_options=menu_opts,
            exit_choice=exit_choice,
        )

    # Extract all prompts/inputs in order
    prompts: List[Tuple[str, str]] = []  # (hint_text, cast_type)
    if language == "python":
        for m in re.finditer(r"(?:(\w+)\s*=\s*)?(?:(int|float|str)\s*\(\s*)?input\s*\(\s*(?:f?['\"]([^'\"]*)['\"])?\s*\)", cleaned):
            var_name = m.group(1) or ""
            cast_t = m.group(2) or ""
            prompt_str = m.group(3) or ""
            hint = f"{var_name} {prompt_str}".strip()
            prompts.append((hint, cast_t))
    elif language in ("c", "cpp"):
        # Pair printf/cout prompts with subsequent scanf/cin
        for m in re.finditer(r'scanf\s*\(\s*"([^"]+)"([^)]*)\)', cleaned):
            fmt, args = m.group(1), m.group(2)
            var_names = re.findall(r"&?\s*([A-Za-z_]\w*(?:\.\w+)?)", args)
            specs = re.findall(r"%[dliufsc]", fmt)
            for idx, sp in enumerate(specs):
                vname = var_names[idx] if idx < len(var_names) else "value"
                prompts.append((vname, sp))
        for m in re.finditer(r"(?:std::)?cin\s*((?:>>\s*[A-Za-z_]\w*(?:\.\w+)?(?:\[\w+\])?\s*)+)", cleaned):
            for vname in re.findall(r">>\s*([A-Za-z_]\w*(?:\.\w+)?)", m.group(1)):
                prompts.append((vname, ""))
        for m in re.finditer(r"getline\s*\(\s*(?:std::)?cin\s*,\s*([A-Za-z_]\w*(?:\.\w+)?)", cleaned):
            prompts.append((m.group(1), "str_explicit"))
    elif language == "java":
        for m in re.finditer(r"(?:(\w+)\s*=\s*)?\w+\.next(Int|Long|Double|Float|Line)?\s*\(", cleaned):
            var_name = m.group(1) or "value"
            kind = f"next{(m.group(2) or 'Line').lower()}"
            prompts.append((var_name, kind))
    else:
        # Generic fallback for JS/Go/Rust/Ruby/PHP/C#
        for m in re.finditer(r"(?:prompt|Scan|read_line|gets|ReadLine)\s*\(\s*(['\"][^'\"]*['\"])?", cleaned):
            prompts.append(((m.group(1) or "value").strip("'\""), ""))

    # Check for for/while loops that repeat input reading
    # e.g. `for i in range(10):` or `for i in range(n):` or `for(int i=0; i<10; i++)` or `for(int i=0; i<n; i++)`
    fixed_loop_match = re.search(
        r"\bfor\s+(?:\w+\s+in\s+range\s*\(\s*(\d+)\s*\)|(?:\w+\s+)?\w+\s*=\s*0\s*;\s*\w+\s*<\s*(\d+)\s*;)",
        cleaned,
    )
    dynamic_loop_match = re.search(
        r"\bfor\s+(?:\w+\s+in\s+range\s*\(\s*([A-Za-z_]\w*)\s*\)|(?:\w+\s+)?\w+\s*=\s*0\s*;\s*\w+\s*<\s*([A-Za-z_]\w*)\s*;)",
        cleaned,
    )
    fixed_count = int(fixed_loop_match.group(1) or fixed_loop_match.group(2)) if fixed_loop_match else None
    has_dynamic_loop = bool(dynamic_loop_match)

    # Check if the code defines or reads entity/student/employee record fields
    inferred_types = [infer_field_type(h, c) for h, c in prompts]
    entity_Indicators = {"name", "age", "marks", "gpa", "salary", "grade", "department", "course", "email", "phone", "city"}
    entity_hits = [t for t in inferred_types if t in entity_Indicators]

    # Also check class/struct definitions for Student/Employee/Record
    has_entity_Keywords = bool(
        re.search(r"\b(?:class|struct)\s+(?:Student|Employee|Person|Book|Product|Customer|Record)\b", cleaned, re.IGNORECASE)
        or len(entity_hits) >= 2
    )

    if has_entity_Keywords and len(prompts) >= 2:
        # Determine which fields belong to the repeated record vs an initial count prompt
        fields: List[str] = []
        has_prefix = False
        if has_dynamic_loop and prompts and infer_field_type(prompts[0][0], prompts[0][1]) == "int" and any(
            k in prompts[0][0].lower() for k in ("n", "num", "count", "how many", "total", "size", "students", "records", "employees")
        ):
            has_prefix = True
            record_prompts = prompts[1:]
        else:
            record_prompts = prompts

        for h, c in record_prompts:
            ft = infer_field_type(h, c)
            # If a prompt says "id" or "roll", keep it distinct
            fields.append(ft)

        if not fields:
            fields = ["name", "age", "id", "marks"]

        rec_count = fixed_count if fixed_count is not None else (3 if (has_dynamic_loop or has_prefix) else 1)
        return ProgramInputProfile(
            language=language,
            requires_input=True,
            mode="entity_records",
            summary=f"Entity/Student Records ({rec_count} record(s) × [{', '.join(fields)}])",
            count=rec_count,
            has_count_prefix=has_prefix,
            fixed_count=fixed_count,
            entity_fields=fields,
        )

    # Check for Array / N-Elements input (either loop or `.split()` list comprehension)
    has_split_array = bool(re.search(r"input\s*\([^)]*\)\.split\s*\(", cleaned))
    if fixed_count is not None or has_dynamic_loop or has_split_array:
        has_prefix = False
        if has_dynamic_loop:
            has_prefix = True
        elif has_split_array and len(prompts) >= 2:
            has_prefix = True

        # Check if binary search is used (requires sorted elements)
        is_bsearch = bool(re.search(r"\b(?:binary_search|binarySearch|mid\s*=\s*\(?low\s*\+\s*high)\b", cleaned))
        elem_type = "sorted_int" if is_bsearch else "int"
        if any(infer_field_type(h, c) == "float" for h, c in prompts[1:]):
            elem_type = "float"
        elif any(infer_field_type(h, c) == "name" for h, c in prompts):
            elem_type = "name"

        # Check if there is a search target/key read after the loop
        needs_target = bool(
            re.search(r"\b(?:target|key|search|find|item|x)\b", prompts[-1][0].lower())
            and (len(prompts) >= 2 if not has_prefix else len(prompts) >= 3)
        )
        arr_count = fixed_count if fixed_count is not None else 8
        return ProgramInputProfile(
            language=language,
            requires_input=True,
            mode="array_elements",
            summary=f"Array / Collection Input ({arr_count} {elem_type} elements{' + search key' if needs_target else ''})",
            count=arr_count,
            has_count_prefix=has_prefix,
            fixed_count=fixed_count,
            element_type=elem_type,
            needs_search_target=needs_target,
            space_separated_elements=has_split_array and not (fixed_count or has_dynamic_loop),
        )

    # Otherwise: Sequence of individual inputs
    seq_fields: List[Tuple[str, str]] = []
    for idx, (h, c) in enumerate(prompts):
        ft = infer_field_type(h, c)
        label = h.strip() or f"input_{idx + 1}"
        seq_fields.append((label[:32], ft))
    if not seq_fields:
        seq_fields = [("input_1", "int"), ("input_2", "int"), ("input_3", "int")]

    return ProgramInputProfile(
        language=language,
        requires_input=True,
        mode="sequence_inputs",
        summary=f"Sequential Inputs ({len(seq_fields)} input(s): {', '.join(t for _, t in seq_fields[:5])})",
        count=len(seq_fields),
        sequence_fields=seq_fields,
    )


# ============================================================================
# 4. Smart Randomized Test Input Generator
# ============================================================================

def generate_test_inputs(
    profile: ProgramInputProfile,
    custom_config: Optional[Dict[str, Any]] = None,
) -> GeneratedTestCase:
    """
    Generate a fresh, randomized test case for the given ProgramInputProfile
    (or overridden by custom_config from the Left Sidebar Tests panel).
    """
    cfg = custom_config or {}
    mode_override = cfg.get("mode", "auto")
    effective_mode = profile.mode if mode_override in ("auto", "", None) else mode_override

    min_val = int(cfg.get("min_val", 10))
    max_val = int(cfg.get("max_val", 99))

    # Raw manual stdin mode
    if effective_mode == "raw":
        raw_text = str(cfg.get("raw_stdin", "") or "")
        lines = raw_text.splitlines()
        return GeneratedTestCase(
            stdin_text=raw_text if raw_text.endswith("\n") else raw_text + "\n",
            input_lines=lines,
            description=f"Custom Raw Stdin ({len(lines)} line(s))",
            pattern_name="Custom Stdin",
            annotated_steps=[f"Line {i+1}: {ln}" for i, ln in enumerate(lines[:20])],
        )

    # 1. Interactive Menu / Stack / Queue / CRUD Mode
    if effective_mode in ("menu_loop", "menu"):
        opts = list(profile.menu_options)
        if not opts or cfg.get("override_menu_choices"):
            push_c = str(cfg.get("menu_push", "1")).strip() or "1"
            pop_c = str(cfg.get("menu_pop", "2")).strip() or "2"
            peek_c = str(cfg.get("menu_peek", "3")).strip() or "3"
            disp_c = str(cfg.get("menu_display", "4")).strip() or "4"
            exit_c = str(cfg.get("menu_exit", profile.exit_choice or "5")).strip() or "5"
            opts = [
                MenuOptionSpec(push_c, "Push/Insert", "push", ["int"]),
                MenuOptionSpec(pop_c, "Pop/Delete", "pop", []),
                MenuOptionSpec(peek_c, "Peek/Top", "peek", []),
                MenuOptionSpec(disp_c, "Display", "display", []),
                MenuOptionSpec(exit_c, "Exit", "exit", []),
            ]
            exit_choice = exit_c
        else:
            exit_choice = profile.exit_choice

        push_opts = [o for o in opts if o.role == "push"]
        pop_opts = [o for o in opts if o.role == "pop"]
        peek_opts = [o for o in opts if o.role == "peek"]
        disp_opts = [o for o in opts if o.role == "display"]
        search_opts = [o for o in opts if o.role == "search"]
        other_opts = [o for o in opts if o.role not in ("push", "pop", "peek", "display", "search", "exit")]

        is_ds_menu = bool(push_opts and (pop_opts or peek_opts or disp_opts))
        val_type = cfg.get("value_type", "int")
        if val_type in ("auto", ""):
            val_type = "int"

        planned_actions: List[MenuOptionSpec] = []
        if is_ds_menu:
            num_ops = int(cfg.get("count", _RNG.randint(7, 10)))
            strategy = "Data Structure Menu Coverage"
            if _RNG.random() < 0.35 and (pop_opts or peek_opts):
                planned_actions.append(_RNG.choice(pop_opts or peek_opts))
            initial_pushes = _RNG.randint(3, max(3, min(4, num_ops // 2 + 1)))
            for _ in range(initial_pushes):
                planned_actions.append(_RNG.choice(push_opts))
            if peek_opts:
                planned_actions.append(_RNG.choice(peek_opts))
            if disp_opts:
                planned_actions.append(_RNG.choice(disp_opts))

            pool: List[MenuOptionSpec] = []
            pool.extend(push_opts * 3)
            pool.extend(pop_opts * 2)
            pool.extend(peek_opts * 2)
            pool.extend(disp_opts * 2)
            pool.extend(search_opts * 1)
            pool.extend(other_opts * 1)

            while len(planned_actions) < num_ops and pool:
                planned_actions.append(_RNG.choice(pool))

            if peek_opts and (not planned_actions or planned_actions[-1].role != "peek"):
                planned_actions.append(_RNG.choice(peek_opts))
            if disp_opts and (not planned_actions or planned_actions[-1].role != "display"):
                planned_actions.append(_RNG.choice(disp_opts))
        else:
            # General / Calculator / Utility Menu: test each non-exit option cleanly!
            non_exit_opts = [o for o in opts if o.role != "exit"]
            strategy = f"All Menu Options ({len(non_exit_opts)} options)"
            planned_actions.extend(non_exit_opts)
            if "count" in cfg and non_exit_opts:
                target_n = max(1, int(cfg["count"]))
                if target_n < len(planned_actions):
                    planned_actions = planned_actions[:target_n]
                else:
                    while len(planned_actions) < target_n:
                        planned_actions.append(_RNG.choice(non_exit_opts))

        exit_spec = next((o for o in opts if o.role == "exit"), MenuOptionSpec(exit_choice, "Exit", "exit"))
        planned_actions.append(exit_spec)

        input_lines: List[str] = []
        annotated: List[str] = []
        pushed_values: List[str] = []

        for step_idx, act in enumerate(planned_actions, 1):
            input_lines.append(act.choice)
            if act.role == "push":
                extra_types = act.extra_inputs or [val_type]
                vals = []
                for et in extra_types:
                    eff_t = val_type if (val_type != "int" and et == "int") else et
                    v = generate_random_value(eff_t, min_val, max_val, step_idx)
                    input_lines.append(v)
                    vals.append(v)
                    pushed_values.append(v)
                annotated.append(f"Step {step_idx}: Option {act.choice} ({act.label}) → {', '.join(vals)}")
            elif act.role == "search":
                target = _RNG.choice(pushed_values) if (pushed_values and _RNG.random() < 0.7) else generate_random_value(val_type, min_val, max_val, step_idx)
                input_lines.append(target)
                annotated.append(f"Step {step_idx}: Option {act.choice} ({act.label}) → {target}")
            elif act.extra_inputs:
                vals = [
                    generate_random_value(
                        val_type if (val_type != "int" and et == "int") else et,
                        min_val,
                        max_val,
                        step_idx + idx,
                    )
                    for idx, et in enumerate(act.extra_inputs)
                ]
                input_lines.extend(vals)
                annotated.append(f"Step {step_idx}: Option {act.choice} ({act.label}) → {', '.join(vals)}")
            else:
                annotated.append(f"Step {step_idx}: Option {act.choice} ({act.label})")

        stdin_text = "\n".join(input_lines) + "\n"
        return GeneratedTestCase(
            stdin_text=stdin_text,
            input_lines=input_lines,
            description=f"Menu Test ({len(planned_actions)} steps: {strategy})",
            pattern_name=strategy,
            annotated_steps=annotated,
        )

    # 2. Structured Entity / Student / Employee Records Mode
    if effective_mode in ("entity_records", "entity"):
        rec_count = int(cfg.get("count", profile.fixed_count or profile.count or 3))
        if profile.fixed_count is not None and "count" not in cfg:
            rec_count = profile.fixed_count

        include_prefix = cfg.get("include_count_prefix")
        if include_prefix is None:
            include_prefix = profile.has_count_prefix

        raw_fields = cfg.get("entity_fields") or profile.entity_fields or ["name", "age", "id", "marks"]
        if isinstance(raw_fields, str):
            fields = [f.strip() for f in raw_fields.split(",") if f.strip()]
        else:
            fields = list(raw_fields)
        if not fields:
            fields = ["name", "age", "id", "marks"]

        input_lines = []
        annotated = []
        if include_prefix:
            input_lines.append(str(rec_count))
            annotated.append(f"Count (N): {rec_count} record(s)")

        for r_idx in range(rec_count):
            rec_vals = []
            for f_name in fields:
                ft = infer_field_type(f_name) if f_name not in ("int", "float", "string", "name", "age", "id", "marks", "gpa", "salary", "grade", "department", "course", "email", "phone", "city") else f_name
                v = generate_random_value(ft, min_val, max_val, r_idx)
                input_lines.append(v)
                rec_vals.append(f"{f_name}={v}")
            annotated.append(f"Record #{r_idx + 1}: {', '.join(rec_vals)}")

        # Add a few safety fallback lines in case the program asks a trailing question
        stdin_text = "\n".join(input_lines) + "\n"
        return GeneratedTestCase(
            stdin_text=stdin_text,
            input_lines=input_lines,
            description=f"{rec_count} Entity Record(s) ({', '.join(fields)})",
            pattern_name=f"Random Entity Records (N={rec_count})",
            annotated_steps=annotated,
        )

    # 3. Array / List of N Elements Mode
    if effective_mode in ("array_elements", "array"):
        if profile.fixed_count is not None and "count" not in cfg:
            arr_count = profile.fixed_count
        else:
            arr_count = int(cfg.get("count", _RNG.randint(5, 10)))

        include_prefix = cfg.get("include_count_prefix")
        if include_prefix is None:
            include_prefix = profile.has_count_prefix

        elem_type = cfg.get("value_type", profile.element_type or "int")
        if elem_type in ("auto", ""):
            elem_type = profile.element_type or "int"

        raw_elements = [
            generate_random_value("int" if elem_type == "sorted_int" else elem_type, min_val, max_val, i)
            for i in range(arr_count)
        ]
        if elem_type == "sorted_int":
            raw_elements = [str(x) for x in sorted(int(v) for v in raw_elements)]

        input_lines = []
        annotated = []
        if include_prefix:
            input_lines.append(str(arr_count))
            annotated.append(f"Size (N): {arr_count}")

        if profile.space_separated_elements and not cfg.get("newline_elements", False):
            input_lines.append(" ".join(raw_elements))
        else:
            input_lines.extend(raw_elements)
        annotated.append(f"Elements ({arr_count}): [{', '.join(raw_elements)}]")

        if profile.needs_search_target or cfg.get("include_search_target"):
            target = _RNG.choice(raw_elements) if (raw_elements and not cfg.get("search_miss", False)) else generate_random_value("int", min_val, max_val)
            input_lines.append(target)
            annotated.append(f"Search Target: {target}")

        stdin_text = "\n".join(input_lines) + "\n"
        return GeneratedTestCase(
            stdin_text=stdin_text,
            input_lines=input_lines,
            description=f"Array of {arr_count} {elem_type} elements",
            pattern_name=f"Random Array (N={arr_count}, type={elem_type})",
            annotated_steps=annotated,
        )

    # 4. General Sequential Inputs Mode
    seq_fields = profile.sequence_fields
    if cfg.get("entity_fields"):
        raw_f = cfg["entity_fields"]
        f_list = [x.strip() for x in raw_f.split(",") if x.strip()] if isinstance(raw_f, str) else list(raw_f)
        seq_fields = [(f, infer_field_type(f)) for f in f_list]
    elif "count" in cfg and effective_mode == "sequence":
        n_seq = int(cfg["count"])
        vt = cfg.get("value_type", "int")
        seq_fields = [(f"input_{i+1}", vt if vt != "auto" else "int") for i in range(n_seq)]

    input_lines = []
    annotated = []
    for idx, (label, ft) in enumerate(seq_fields):
        v = generate_random_value(ft, min_val, max_val, idx)
        input_lines.append(v)
        annotated.append(f"{label} ({ft}): {v}")

    # Append a few extra fallback integers/exit tokens in case a loop asks for extra inputs
    fallback_lines = input_lines + [str(_RNG.randint(min_val, max_val)) for _ in range(3)] + ["0", "5"]
    stdin_text = "\n".join(fallback_lines) + "\n"
    return GeneratedTestCase(
        stdin_text=stdin_text,
        input_lines=input_lines,
        description=f"Sequential Inputs ({len(input_lines)} value(s))",
        pattern_name="Random Sequential Values",
        annotated_steps=annotated,
    )


# ============================================================================
# 5. Concise Error Diagnosis (1-2 Line Issue + 1-Line Quick Fix)
# ============================================================================

def diagnose_error(
    stdout: str,
    stderr: str,
    exit_code: int,
    timed_out: bool,
    language: str,
) -> Tuple[str, str]:
    """
    Produce a concise 1-2 line issue description and a 1-line quick fix.
    Never outputs long paragraphs.
    """
    combined = f"{stderr}\n{stdout}".strip()

    if timed_out:
        return (
            "Execution timed out — program is stuck in an infinite loop or waiting for extra input.",
            "Check your while/for loop exit condition or ensure the menu exit choice breaks the loop.",
        )

    # Extract line number if present
    line_no = ""
    py_lines = re.findall(r'File "[^"]+", line (\d+)', combined)
    if py_lines:
        line_no = f"Line {py_lines[-1]}: "
    else:
        c_line = re.search(r":(\d+)(?::\d+)?:\s*(?:error|fatal error):", combined, re.IGNORECASE)
        if c_line:
            line_no = f"Line {c_line.group(1)}: "

    # Python & common runtime exceptions
    if "EOFError" in combined or "NoSuchElementException" in combined:
        return (
            f"{line_no}Program kept asking for more input after all test inputs were consumed.",
            "Add a valid break/exit condition to your loop or increase the test input count in the Tests panel.",
        )
    if "ValueError: invalid literal for int()" in combined or "InputMismatchException" in combined:
        return (
            f"{line_no}Program expected an integer but received text/float input.",
            "Match the input order in your code (e.g. read Name as str and Age/Marks as int/float).",
        )
    if "ZeroDivisionError" in combined or "/ by zero" in combined:
        return (
            f"{line_no}Division by zero occurred during calculation.",
            "Check that the denominator/count is not 0 before dividing (e.g. `if n != 0:`).",
        )
    if "IndexError" in combined or "ArrayIndexOutOfBoundsException" in combined or "index out of range" in combined.lower():
        return (
            f"{line_no}List/array index is out of bounds (accessing an empty list or invalid index).",
            "Check `if len(stack) > 0:` before popping/indexing and keep loop bounds within `0 .. len(arr)-1`.",
        )
    if "SyntaxError" in combined or "IndentationError" in combined:
        last_line = next((ln.strip() for ln in reversed(combined.splitlines()) if "Error:" in ln), "SyntaxError")
        return (
            f"{line_no}{last_line[:120]}",
            "Fix the syntax/indentation on the reported line (check colons `:`, brackets, and quotes).",
        )
    if "NameError" in combined:
        m = re.search(r"NameError:\s*name '([^']+)' is not defined", combined)
        sym = m.group(1) if m else "variable"
        return (
            f"{line_no}'{sym}' is used before being defined or is misspelled.",
            f"Initialize `{sym}` before using it or fix the variable/function name spelling.",
        )
    if "TypeError" in combined:
        last_line = next((ln.strip() for ln in reversed(combined.splitlines()) if "TypeError:" in ln), "TypeError")
        return (
            f"{line_no}{last_line[:120]}",
            "Convert `input()` values with `int()` or `float()` before doing math or comparisons.",
        )
    if "KeyError" in combined:
        return (
            f"{line_no}Dictionary key was not found.",
            "Use `dict.get(key)` or check `if key in dict:` before accessing the key.",
        )
    if "AttributeError" in combined:
        last_line = next((ln.strip() for ln in reversed(combined.splitlines()) if "AttributeError:" in ln), "AttributeError")
        return (
            f"{line_no}{last_line[:120]}",
            "Check that the object is not `None` and that the method/attribute name is spelled correctly.",
        )
    if "RecursionError" in combined or "StackOverflowError" in combined:
        return (
            f"{line_no}Maximum recursion depth exceeded (infinite recursion).",
            "Add a proper base case that stops the recursive call.",
        )
    if "ModuleNotFoundError" in combined or "ImportError" in combined:
        last_line = next((ln.strip() for ln in reversed(combined.splitlines()) if "Error:" in ln), "ImportError")
        return (
            f"{line_no}{last_line[:120]}",
            "Install the missing package with `pip install <package>` or check the import name.",
        )

    # C / C++ / Java / Rust compilation errors
    err_match = re.search(r":(\d+)(?::\d+)?:\s*(?:fatal )?error:\s*(.+)", combined)
    if err_match:
        ln_num, msg = err_match.group(1), err_match.group(2).strip()
        return (
            f"Line {ln_num}: Compile error — {msg[:110]}",
            f"Check syntax, types, and semicolons around line {ln_num}.",
        )

    if exit_code == 127 or "is not installed or not on PATH" in combined:
        return (
            combined.splitlines()[0][:120] if combined else f"Compiler/runtime for {language} not found.",
            f"Install the {language} compiler/interpreter and ensure it is added to your system PATH.",
        )

    if exit_code in (-11, 139, 3221225477) or "segmentation fault" in combined.lower():
        return (
            "Segmentation fault (invalid memory/pointer or out-of-bounds array access).",
            "Check array bounds, uninitialized pointers, and `scanf` `&` address operators.",
        )

    # Generic concise fallback: grab the last meaningful error line
    err_lines = [ln.strip() for ln in (stderr or stdout).splitlines() if ln.strip()]
    tail = err_lines[-1][:120] if err_lines else f"Process exited with code {exit_code}."
    return (
        f"{line_no}{tail}",
        "Review the reported line and verify variable types and edge conditions.",
    )


# ============================================================================
# 6. Multi-Language Test Execution Engine
# ============================================================================

def _build_execution_plan(
    file_path: Path,
    language: str,
    build_dir: Path,
) -> Tuple[Optional[List[str]], List[str]]:
    """
    Return (compile_cmd_or_None, run_cmd) for executing `file_path` in `language`.
    """
    parent = file_path.parent
    stem = file_path.stem

    if language == "python":
        # Prefer standard python interpreter (with -u unbuffered) over pythonw for piped stdin/stdout testing
        py = python_command(parent)
        if os.name == "nt" and py.lower().endswith("pythonw.exe"):
            py_console = Path(py).with_name("python.exe")
            if py_console.exists():
                py = str(py_console)
        return None, [py, "-u", str(file_path)]

    if language == "c":
        out_bin = build_dir / (f"{stem}.exe" if os.name == "nt" else stem)
        return ["gcc", str(file_path), "-o", str(out_bin)], [str(out_bin)]

    if language == "cpp":
        out_bin = build_dir / (f"{stem}.exe" if os.name == "nt" else stem)
        return ["g++", str(file_path), "-o", str(out_bin)], [str(out_bin)]

    if language == "java":
        return ["javac", "-d", str(build_dir), str(file_path)], ["java", "-cp", str(build_dir), stem]

    if language == "javascript":
        return None, ["node", str(file_path)]

    if language == "typescript":
        runner = "tsx" if shutil.which("tsx") else "ts-node"
        return None, [runner, str(file_path)]

    if language == "go":
        return None, ["go", "run", str(file_path)]

    if language == "rust":
        out_bin = build_dir / (f"{stem}.exe" if os.name == "nt" else stem)
        return ["rustc", str(file_path), "-o", str(out_bin)], [str(out_bin)]

    if language == "ruby":
        return None, ["ruby", str(file_path)]

    if language == "php":
        return None, ["php", str(file_path)]

    if language == "csharp":
        return None, ["dotnet", "run"]

    if language == "dart":
        return None, ["dart", "run", str(file_path)]

    if language == "bash":
        return None, ["bash", str(file_path)]

    if language == "powershell":
        return None, ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(file_path)]

    return None, [python_command(parent), "-u", str(file_path)]


def run_program_test(
    file_path: Optional[Path] = None,
    code: Optional[str] = None,
    custom_config: Optional[Dict[str, Any]] = None,
    timeout: float = 8.0,
) -> ProgramTestResult:
    """
    Analyze, generate randomized dummy inputs, compile (if needed), and run the
    program across 1 or more scenarios. Never opens any external console window.
    """
    cfg = custom_config or {}
    scenarios_count = max(1, min(10, int(cfg.get("scenarios", 1))))

    # Resolve code & temporary file if code was passed from an unsaved buffer
    temp_dir_obj = tempfile.TemporaryDirectory(prefix="owncode_test_")
    temp_dir = Path(temp_dir_obj.name)

    try:
        if file_path is not None and Path(file_path).exists() and code is None:
            target_path = Path(file_path).resolve()
            source_code = target_path.read_text(encoding="utf-8", errors="replace")
            work_dir = target_path.parent
        else:
            source_code = code or ""
            ext = Path(file_path).suffix if file_path and Path(file_path).suffix else ".py"
            stem = Path(file_path).stem if file_path and Path(file_path).stem else "Main"
            target_path = temp_dir / f"{stem}{ext}"
            target_path.write_text(source_code, encoding="utf-8")
            work_dir = Path(file_path).parent if (file_path and Path(file_path).parent.exists()) else temp_dir

        profile = analyze_program(source_code, target_path)
        compile_cmd, run_cmd = _build_execution_plan(target_path, profile.language, temp_dir)

        # Compile once if compiled language (C, C++, Java, Rust)
        if compile_cmd is not None:
            c_code, c_out, c_err, c_ms, c_timeout = run_hidden_command(
                compile_cmd, cwd=work_dir, timeout=15.0
            )
            if c_code != 0 or c_timeout:
                issue, fix = diagnose_error(c_out, c_err, c_code, c_timeout, profile.language)
                report = _format_test_report(
                    success=False,
                    exit_code=c_code,
                    duration_ms=c_ms,
                    profile=profile,
                    test_case=GeneratedTestCase("", [], "Compilation", "Compile Check"),
                    stdout=c_out,
                    stderr=c_err,
                    issue=issue,
                    quick_fix=fix,
                    scenarios_run=1,
                    scenarios_passed=0,
                )
                return ProgramTestResult(
                    success=False,
                    exit_code=c_code,
                    duration_ms=c_ms,
                    language=profile.language,
                    mode=profile.mode,
                    profile_summary=profile.summary,
                    pattern_name="Compile Check",
                    stdin_text="",
                    annotated_inputs=[],
                    stdout=c_out,
                    stderr=c_err,
                    issue_summary=issue,
                    quick_fix=fix,
                    formatted_output=report,
                    scenarios_run=1,
                    scenarios_passed=0,
                )

        # Run 1 or N randomized test scenarios
        total_ms = 0.0
        passed_count = 0
        last_case = GeneratedTestCase("", [], "No input", "Direct Run")
        last_out = ""
        last_err = ""
        last_code = 0
        last_timeout = False
        scenario_logs: List[str] = []

        for s_idx in range(1, scenarios_count + 1):
            if profile.requires_input or cfg.get("mode") not in (None, "", "auto"):
                test_case = generate_test_inputs(profile, cfg)
            else:
                test_case = GeneratedTestCase(
                    stdin_text="",
                    input_lines=[],
                    description="No stdin needed",
                    pattern_name="Direct Execution",
                    annotated_steps=["(Program requires no user input)"],
                )

            r_code, r_out, r_err, r_ms, r_timeout = run_hidden_command(
                run_cmd,
                cwd=work_dir,
                input_text=test_case.stdin_text,
                timeout=timeout,
            )
            total_ms += r_ms
            last_case = test_case
            last_out = r_out
            last_err = r_err
            last_code = r_code
            last_timeout = r_timeout

            if r_code == 0 and not r_timeout:
                passed_count += 1
                if scenarios_count > 1:
                    preview_in = ", ".join(test_case.input_lines[:8])
                    if len(test_case.input_lines) > 8:
                        preview_in += ", ..."
                    scenario_logs.append(
                        f"  [Scenario {s_idx}/{scenarios_count}] ✓ PASSED ({r_ms:.0f} ms) | Inputs: [{preview_in}]"
                    )
            else:
                if scenarios_count > 1:
                    scenario_logs.append(
                        f"  [Scenario {s_idx}/{scenarios_count}] ✗ FAILED (exit {r_code}, {r_ms:.0f} ms)"
                    )
                break

        overall_ok = (passed_count == scenarios_count and last_code == 0 and not last_timeout)
        issue, fix = ("", "") if overall_ok else diagnose_error(
            last_out, last_err, last_code, last_timeout, profile.language
        )

        report = _format_test_report(
            success=overall_ok,
            exit_code=last_code,
            duration_ms=round(total_ms, 1),
            profile=profile,
            test_case=last_case,
            stdout=last_out,
            stderr=last_err,
            issue=issue,
            quick_fix=fix,
            scenarios_run=len(scenario_logs) if scenarios_count > 1 else 1,
            scenarios_passed=passed_count,
            scenario_logs=scenario_logs,
        )

        return ProgramTestResult(
            success=overall_ok,
            exit_code=last_code,
            duration_ms=round(total_ms, 1),
            language=profile.language,
            mode=profile.mode,
            profile_summary=profile.summary,
            pattern_name=last_case.pattern_name,
            stdin_text=last_case.stdin_text,
            annotated_inputs=last_case.annotated_steps,
            stdout=last_out,
            stderr=last_err,
            issue_summary=issue,
            quick_fix=fix,
            formatted_output=report,
            scenarios_run=len(scenario_logs) if scenarios_count > 1 else 1,
            scenarios_passed=passed_count,
        )
    finally:
        try:
            temp_dir_obj.cleanup()
        except Exception:
            pass


def _clean_stdout_for_report(raw_stdout: str, profile: ProgramInputProfile) -> List[str]:
    """
    Clean piped stdout for display in the test report:
    - Strips concatenated inline input() prompts (e.g. `Enter choice: Enter num1: Enter num2: Result: 40`)
      so the actual output (`Result: 40`) stands out clearly.
    - Deduplicates repeated identical menu banners in loop programs so the menu
      is shown once at the top followed by each step's result.
    """
    if not raw_stdout or not raw_stdout.strip():
        return []

    raw_lines = [ln.rstrip() for ln in raw_stdout.splitlines()]
    cleaned_lines: List[str] = []
    seen_menu_lines: set[str] = set()
    is_menu = (profile.mode == "menu_loop")

    for ln in raw_lines:
        s = ln.strip()
        if not s:
            continue

        # Strip chained inline prompts like `Enter your choice (1-5): Enter first number: Result: 40.0`
        stripped_prompts = re.sub(
            r"^(?:(?:Enter|Input|Select|Choose|Type|Give)[^:\n]{1,42}:\s*)+",
            "",
            s,
            flags=re.IGNORECASE,
        ).strip()

        # If the entire line was just a trailing prompt (e.g. `Enter your choice (1-5):` before break), skip it
        if not stripped_prompts and re.match(r"^(?:Enter|Input|Select|Choose|Type|Give)[^:]{1,42}:\s*$", s, flags=re.IGNORECASE):
            continue

        if stripped_prompts != s and stripped_prompts:
            cleaned_lines.append(f"→ {stripped_prompts}")
            continue

        # In menu_loop mode, avoid repeating the exact same menu header/option lines on every iteration
        if is_menu:
            is_menu_banner = (
                re.match(r"^\[?[0-9]+\]?\s*[\.\)\:\-\]]\s*[A-Za-z]", s)
                or ("menu" in s.lower() and len(s) < 50)
                or (s.startswith("---") and s.endswith("---"))
            )
            if is_menu_banner:
                if s in seen_menu_lines:
                    continue
                seen_menu_lines.add(s)

        cleaned_lines.append(s)

    return cleaned_lines


def _format_test_report(
    *,
    success: bool,
    exit_code: int,
    duration_ms: float,
    profile: ProgramInputProfile,
    test_case: GeneratedTestCase,
    stdout: str,
    stderr: str,
    issue: str,
    quick_fix: str,
    scenarios_run: int = 1,
    scenarios_passed: int = 1,
    scenario_logs: Optional[List[str]] = None,
) -> str:
    """Format a clean, scannable, concise test report for the Output / Tests panel."""
    lines = [
        "============================================================",
        f"  🧪 PROGRAM TEST — {profile.language.upper()}",
        "============================================================",
        f"  Program Type  : {profile.summary}",
    ]
    if scenarios_run > 1:
        lines.append(f"  Batch Runs    : {scenarios_passed}/{scenarios_run} scenarios passed ({duration_ms:.1f} ms total)")
        if scenario_logs:
            lines.extend(scenario_logs)

    if test_case.annotated_steps:
        lines.append("------------------------------------------------------------")
        lines.append(f"  Test Steps Executed ({len(test_case.annotated_steps)}):")
        for step in test_case.annotated_steps[:20]:
            lines.append(f"    • {step}")
        if len(test_case.annotated_steps) > 20:
            lines.append(f"    • ... (+{len(test_case.annotated_steps) - 20} more steps)")

    lines.append("------------------------------------------------------------")
    lines.append("  Program Output:")
    display_lines = _clean_stdout_for_report(stdout or "", profile)
    if display_lines:
        for ln in display_lines[:45]:
            lines.append(f"    {ln}")
        if len(display_lines) > 45:
            lines.append(f"    ... ({len(display_lines) - 45} more lines)")
    else:
        lines.append("    (no stdout output)")

    lines.append("------------------------------------------------------------")
    if success:
        lines.append(f"  ✓ RESULT: Code ran and tested successfully! (Exit 0 · {duration_ms:.1f} ms)")
    else:
        lines.append(f"  ✗ RESULT: Test failed (Exit {exit_code} · {duration_ms:.1f} ms)")
        lines.append(f"  Issue    : {issue}")
        lines.append(f"  Quick Fix: {quick_fix}")
    lines.append("============================================================\n")
    return "\n".join(lines)

