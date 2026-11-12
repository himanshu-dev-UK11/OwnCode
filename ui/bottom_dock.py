"""
Consolidated Module: ui.bottom_dock

Combines: ui.panels.bottom_dock
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['ui.panels.bottom_dock']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ui.panels.bottom_dock (ui/panels/bottom_dock.py)
# ============================================================================
"""
Bottom Dock — v4.0

The collapsible bottom area with three enhanced tabs and top-right control toolbar:
  - Terminal   : Interactive shell + live interactive execution for `▶ Run`
                 (supports real-time `input()` / `scanf` stdin, `↵ Send`,
                 `■ Kill`, and `↻ Reset` — with the old `Test Terminal` button removed)
  - Output     : Program & Smart Test output with its own interactive `stdin ›`
                 input bar so users can also provide program input directly in Output
  - Problems   : Smart Problem Finder — gives a concise, minimal-word explanation
                 of each problem along with a 1-line smart fix, or confirms
                 `✓ No problems detected — program ran successfully` when clean
"""

import ast
import os
import re
import sys

from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QTabWidget, QPlainTextEdit,
    QLineEdit, QListWidget, QListWidgetItem, QLabel, QPushButton,
)
from PySide6.QtCore import Qt, Signal
from core.process_utils import HiddenProcess as QProcess
from PySide6.QtGui import QFont, QColor, QBrush, QTextCursor

from ui.design_system import (
    get_design_system, Terminal, FontFamily, FontSize, Spacing, Radius,
)
from ui.settings_manager import get_settings_manager
from ui.widgets.controls import Pill
from core.process_utils import (
    configure_qprocess_no_window,
    safe_delete_qprocess,
    run_terminal_self_test,
)


def _mono_font(size: int = 0, family: str = "") -> QFont:
    """Monospace font honouring the terminal settings, with a safe fallback."""
    if not family or not size:
        try:
            sm = get_settings_manager()
            family = family or sm.get("terminal", "font_family", FontFamily.mono)
            size = size or int(sm.get("terminal", "font_size", 11))
        except Exception:
            family, size = family or FontFamily.mono, size or 11
    f = QFont(str(family).split(",")[0].strip('"\' '), max(8, int(size or 11)))
    f.setStyleHint(QFont.Monospace)
    f.setFixedPitch(True)
    return f


def _terminal_colors():
    """Terminal surface/text/prompt derived from the active palette."""
    c = get_design_system().colors
    return {
        "bg": c.canvas if c.is_dark else c.surface_inset,
        "fg": c.text_secondary,
        "bright": c.text_primary,
        "prompt": c.accent,
        "border": c.border_subtle,
        "sel_bg": c.selection,
        "scroll": c.scrollbar,
        "scroll_hover": c.scrollbar_hover,
    }


class _Console(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(_mono_font())
        self.setMaximumBlockCount(5000)
        self.setFrameShape(QPlainTextEdit.NoFrame)
        self._apply_style()

    def append_text(self, text: str):
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.insertPlainText(text)
        self.moveCursor(QTextCursor.MoveOperation.End)
        sb = self.verticalScrollBar()
        if sb is not None:
            sb.setValue(sb.maximum())

    def _apply_style(self):
        t = _terminal_colors()
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {t['bg']};
                color: {t['fg']};
                border: none;
                selection-background-color: {t['sel_bg']};
                selection-color: {t['bright']};
            }}
            QScrollBar:vertical {{
                background: transparent; width: 10px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {t['scroll']};
                border-radius: {Radius.sm}px; min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {t['scroll_hover']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0; background: transparent;
            }}
        """)

    def refresh_theme(self):
        self._apply_style()

    def apply_terminal_settings(self):
        self.setFont(_mono_font())
        try:
            self.setMaximumBlockCount(
                int(get_settings_manager().get("terminal", "scrollback_size", 5000)))
        except Exception:
            pass


class OutputView(QWidget):
    """
    Enhanced Output tab with a console display plus an interactive `stdin ›`
    input bar at the bottom so users can also send input to running programs
    directly from the Output tab if they view Output instead of Terminal.
    """

    stdin_submitted = Signal(str)
    kill_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("OutputView")
        self._program_running = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._console = _Console()
        lay.addWidget(self._console, 1)

        row = QFrame()
        row.setObjectName("OutputInputRow")
        row.setAttribute(Qt.WA_StyledBackground, True)
        self._row = row
        rlay = QHBoxLayout(row)
        rlay.setContentsMargins(Spacing.md, Spacing.xs, Spacing.md, Spacing.xs)
        rlay.setSpacing(Spacing.xs)

        self._prompt = QLabel("stdin ›")
        self._prompt.setObjectName("OutputPrompt")
        self._prompt.setFont(_mono_font())
        self._prompt.setToolTip("Interactive program input prompt")

        self._input = QLineEdit()
        self._input.setObjectName("OutputInput")
        self._input.setFont(_mono_font())
        self._input.setPlaceholderText("Type program input here and press Enter…")
        self._input.setToolTip("Type input for your running program and press Enter")
        self._input.returnPressed.connect(self._send_input)

        self._send_btn = QPushButton("↵ Send")
        self._send_btn.setObjectName("OutputSendBtn")
        self._send_btn.setCursor(Qt.PointingHandCursor)
        self._send_btn.setToolTip("Send typed input to the running program (Enter)")
        self._send_btn.clicked.connect(self._send_input)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setObjectName("OutputClearBtn")
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.setToolTip("Clear Output console")
        self._clear_btn.clicked.connect(self.clear)

        rlay.addWidget(self._prompt)
        rlay.addWidget(self._input, 1)
        rlay.addWidget(self._send_btn)
        rlay.addWidget(self._clear_btn)
        lay.addWidget(row)

        self._apply_style()

    def _send_input(self):
        raw = self._input.text()
        self._input.clear()
        self._console.append_text(f"{raw}\n")
        self.stdin_submitted.emit(raw + "\n")

    def set_program_running(self, running: bool):
        self._program_running = bool(running)
        if running:
            self._prompt.setText("● stdin ›")
            self._input.setPlaceholderText("Program running — type input here and press Enter…")
        else:
            self._prompt.setText("stdin ›")
            self._input.setPlaceholderText("Type program input here and press Enter…")

    # Delegate standard _Console methods so callers of `bottom_dock.output` work transparently
    def append_text(self, text: str):
        self._console.append_text(text)

    def clear(self):
        self._console.clear()

    def toPlainText(self) -> str:
        return self._console.toPlainText()

    def setPlainText(self, text: str):
        self._console.setPlainText(text)

    def moveCursor(self, *args, **kwargs):
        self._console.moveCursor(*args, **kwargs)

    def insertPlainText(self, text: str):
        self._console.insertPlainText(text)

    def _apply_style(self):
        c = get_design_system().colors
        t = _terminal_colors()
        self.setStyleSheet(f"""
            #OutputView {{ background: {t['bg']}; }}
            #OutputInputRow {{
                background: {c.surface};
                border-top: 1px solid {c.border};
            }}
            #OutputPrompt {{
                color: {t['prompt']};
                background: transparent;
                font-weight: 600;
                padding-right: 4px;
            }}
            #OutputInput {{
                background: {c.surface_inset};
                border: 1px solid {c.border_subtle};
                border-radius: {Radius.sm}px;
                padding: 3px 8px;
                color: {t['bright']};
                selection-background-color: {t['sel_bg']};
            }}
            #OutputInput:focus {{
                border: 1px solid {c.accent};
            }}
            #OutputSendBtn {{
                background: {c.accent_muted};
                color: {c.accent};
                border: 1px solid {c.accent};
                border-radius: {Radius.sm}px;
                padding: 3px 10px;
                font-size: {FontSize.tiny}px;
                font-weight: 600;
            }}
            #OutputSendBtn:hover {{
                background: {c.accent};
                color: {c.text_on_accent};
            }}
            #OutputClearBtn {{
                background: {c.surface_raised};
                color: {c.text_secondary};
                border: 1px solid {c.border};
                border-radius: {Radius.sm}px;
                padding: 3px 9px;
                font-size: {FontSize.tiny}px;
            }}
            #OutputClearBtn:hover {{
                background: {c.surface_overlay};
                color: {c.text_primary};
                border-color: {c.accent};
            }}
        """)
        self._console._apply_style()

    def refresh_theme(self):
        self._apply_style()

    def apply_terminal_settings(self):
        self._console.apply_terminal_settings()
        font = _mono_font()
        self._prompt.setFont(font)
        self._input.setFont(font)


class TerminalView(QWidget):
    """
    Persistent integrated terminal supporting both interactive shell commands
    and live interactive program runs (`▶ Run`) with real-time stdin input,
    send, kill, and reset/restore controls.
    """

    _self_test_ready = Signal(str)
    stdin_submitted = Signal(str)
    kill_requested = Signal()
    reset_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TerminalView")
        self._proc = None
        self._program_running = False
        self._shell_prompt_text = "$"

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._out = _Console()
        lay.addWidget(self._out, 1)

        row = QFrame()
        row.setObjectName("TerminalInputRow")
        row.setAttribute(Qt.WA_StyledBackground, True)
        self._row = row
        rlay = QHBoxLayout(row)
        rlay.setContentsMargins(Spacing.md, Spacing.xs, Spacing.md, Spacing.xs)
        rlay.setSpacing(Spacing.xs)

        self._prompt = QLabel("$")
        self._prompt.setObjectName("TerminalPrompt")
        self._prompt.setFont(_mono_font())
        self._prompt.setToolTip("Current terminal / program input prompt")

        self._input = QLineEdit()
        self._input.setObjectName("TerminalInput")
        self._input.setFont(_mono_font())
        self._input.setPlaceholderText("Type a command or program input and press Enter…")
        self._input.setToolTip("Type a shell command or program input and press Enter")
        self._input.returnPressed.connect(self._run_command)

        self._send_btn = QPushButton("↵ Send")
        self._send_btn.setObjectName("TerminalSendBtn")
        self._send_btn.setCursor(Qt.PointingHandCursor)
        self._send_btn.setToolTip("Submit command or program input (Enter)")
        self._send_btn.clicked.connect(self._run_command)

        self._kill_btn = QPushButton("■ Kill")
        self._kill_btn.setObjectName("TerminalKillBtn")
        self._kill_btn.setCursor(Qt.PointingHandCursor)
        self._kill_btn.setToolTip("Kill running program or terminal process")
        self._kill_btn.clicked.connect(self.kill_requested.emit)

        self._reset_btn = QPushButton("↻ Reset")
        self._reset_btn.setObjectName("TerminalResetBtn")
        self._reset_btn.setCursor(Qt.PointingHandCursor)
        self._reset_btn.setToolTip("Kill process, clear output, and restore fresh terminal session")
        self._reset_btn.clicked.connect(self.reset_requested.emit)

        rlay.addWidget(self._prompt)
        rlay.addWidget(self._input, 1)
        rlay.addWidget(self._send_btn)
        rlay.addWidget(self._kill_btn)
        rlay.addWidget(self._reset_btn)
        lay.addWidget(row)

        configured_cwd = str(self._setting("default_working_dir", "") or "").strip()
        self._cwd = configured_cwd if os.path.isdir(configured_cwd) else os.getcwd()
        self._update_prompt_label()
        self._self_test_ready.connect(self._on_self_test_ready)
        self._apply_style()

    def _update_prompt_label(self):
        if self._program_running:
            self._prompt.setText("● stdin ›")
            self._input.setPlaceholderText("Program running — type input here and press Enter…")
        else:
            folder = os.path.basename(self._cwd.rstrip(os.sep)) or self._cwd
            self._shell_prompt_text = f"{folder} $"
            self._prompt.setText(self._shell_prompt_text)
            self._input.setPlaceholderText("Type a command and press Enter… (or click ▶ Run)")

    def set_cwd(self, path: str):
        if path and os.path.isdir(path):
            self._cwd = path
            self._update_prompt_label()

    def focus_input(self):
        self._input.setFocus()

    def clear_console(self):
        self._out.clear()

    def start_program_session(self, name: str, command: str):
        """Prepare TerminalView for an interactive `▶ Run` execution."""
        self._program_running = True
        self._update_prompt_label()
        header = f"\n▶ Running {name or 'program'}: {command}\n" if command else f"\n▶ Running {name}\n"
        self._out.append_text(header)
        self._input.setFocus()

    def append_program_output(self, text: str):
        if text:
            self._out.append_text(text)

    def finish_program_session(self, exit_code: int, stopped: bool = False):
        was_running = self._program_running
        self._program_running = False
        self._update_prompt_label()
        if stopped:
            self._out.append_text("\n[Process terminated]\n")
        elif was_running or exit_code != 0:
            self._out.append_text(f"\n[Process exited with code {exit_code}]\n")

    def kill_active(self) -> bool:
        """Kill any running shell or interactive program state."""
        had_proc = (self._proc is not None and self._proc.state() != QProcess.NotRunning)
        was_prog = self._program_running
        self._stop_process()
        self._program_running = False
        self._update_prompt_label()
        if had_proc or was_prog:
            self._out.append_text("\n[Process killed — terminal ready]\n")
            return True
        return False

    def reset_session(self):
        """Kill active processes, clear console, and restore a fresh terminal state."""
        self._stop_process()
        self._program_running = False
        self._out.clear()
        self._update_prompt_label()
        self._out.append_text(f"[Terminal restored — working directory: {self._cwd}]\n")
        self._input.clear()
        self._input.setFocus()

    def run_self_test(self) -> dict:
        """Programmatic diagnostic check (kept for unit test compatibility)."""
        shell_cfg = str(self._setting("default_shell", "cmd"))
        report = run_terminal_self_test(cwd=self._cwd, configured_shell=shell_cfg)
        self._self_test_ready.emit(report["formatted_report"])
        return report

    def _on_self_test_ready(self, report_text: str):
        self._out.append_text(report_text)

    def _run_command(self):
        raw = self._input.text()
        self._input.clear()

        # If a program launched via ▶ Run is currently executing, route input directly to its stdin!
        if self._program_running:
            self._out.append_text(f"{raw}\n")
            self.stdin_submitted.emit(raw + "\n")
            return

        cmd = raw.strip()
        if not cmd:
            return
        self._out.append_text(f"\n{self._prompt.text()} {cmd}\n")
        if cmd in ("clear", "cls"):
            self._out.clear()
            return
        self._ensure_process()
        if self._proc is None or self._proc.state() == QProcess.NotRunning:
            self._out.append_text("\n[terminal shell failed to start]\n")
            return
        self._proc.write((cmd + "\r\n").encode("utf-8"))

    def _ensure_process(self):
        if self._proc is not None and self._proc.state() != QProcess.NotRunning:
            return
        if self._proc is not None:
            safe_delete_qprocess(self._proc)
            self._proc = None
        proc = QProcess(self)
        configure_qprocess_no_window(proc)
        proc.setWorkingDirectory(self._cwd)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(self._on_output)
        proc.finished.connect(
            lambda _code, _status, process=proc: self._on_process_finished(process))
        proc.errorOccurred.connect(
            lambda error: self._out.append_text(
                f"\n[terminal error: {error}]\n"))
        if sys.platform.startswith("win"):
            set_process_args = getattr(
                proc, "setCreateProcessArgumentsModifier", None)
            if callable(set_process_args):
                set_process_args(self._hide_windows_console)
            shell = str(self._setting("default_shell", "cmd")).lower()
            if shell in ("powershell", "pwsh"):
                proc.start(shell, ["-NoLogo", "-NoProfile", "-Command", "-"])
            elif shell in ("bash", "git-bash", "wsl"):
                proc.start("bash", ["--noprofile", "--norc", "-i"])
            else:
                proc.start("cmd", ["/Q", "/D", "/K"])
        else:
            proc.start("/bin/sh", ["-i"])
        self._proc = proc
        if not proc.waitForStarted(2000):
            self._out.append_text("\n[terminal shell is unavailable]\n")

    def _on_process_finished(self, process):
        if process is self._proc:
            self._proc = None
        safe_delete_qprocess(process)

    @staticmethod
    def _hide_windows_console(arguments):
        import subprocess
        arguments.flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
        startup_info = arguments.startupInfo
        startup_info.dwFlags |= 0x00000001
        startup_info.wShowWindow = 0

    def _on_output(self):
        if self._proc is not None:
            try:
                data = bytes(self._proc.readAllStandardOutput()).decode(errors="replace")
            except RuntimeError:
                return
            if data:
                self._out.append_text(data)

    def _stop_process(self):
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            proc.readyReadStandardOutput.disconnect()
            proc.errorOccurred.disconnect()
            proc.finished.disconnect()
        except (RuntimeError, TypeError):
            pass
        try:
            if proc.state() != QProcess.NotRunning:
                proc.terminate()
                if not proc.waitForFinished(800):
                    proc.kill()
        except RuntimeError:
            pass
        safe_delete_qprocess(proc)

    def closeEvent(self, event):
        self._stop_process()
        super().closeEvent(event)

    @staticmethod
    def _setting(key: str, fallback):
        try:
            return get_settings_manager().get("terminal", key, fallback)
        except Exception:
            return fallback

    def _apply_style(self):
        c = get_design_system().colors
        t = _terminal_colors()
        self.setStyleSheet(f"""
            #TerminalView {{ background: {t['bg']}; }}
            #TerminalInputRow {{
                background: {c.surface};
                border-top: 1px solid {c.border};
            }}
            #TerminalPrompt {{
                color: {t['prompt']};
                background: transparent;
                font-weight: 600;
                padding-right: 4px;
            }}
            #TerminalInput {{
                background: {c.surface_inset};
                border: 1px solid {c.border_subtle};
                border-radius: {Radius.sm}px;
                padding: 3px 8px;
                color: {t['bright']};
                selection-background-color: {t['sel_bg']};
            }}
            #TerminalInput:focus {{
                border: 1px solid {c.accent};
            }}
            #TerminalSendBtn {{
                background: {c.accent_muted};
                color: {c.accent};
                border: 1px solid {c.accent};
                border-radius: {Radius.sm}px;
                padding: 3px 10px;
                font-size: {FontSize.tiny}px;
                font-weight: 600;
            }}
            #TerminalSendBtn:hover {{
                background: {c.accent};
                color: {c.text_on_accent};
            }}
            #TerminalKillBtn {{
                background: {c.surface_raised};
                color: {c.error};
                border: 1px solid {c.border};
                border-radius: {Radius.sm}px;
                padding: 3px 9px;
                font-size: {FontSize.tiny}px;
                font-weight: 600;
            }}
            #TerminalKillBtn:hover {{
                background: {c.error};
                color: #ffffff;
                border-color: {c.error};
            }}
            #TerminalResetBtn {{
                background: {c.surface_raised};
                color: {c.text_secondary};
                border: 1px solid {c.border};
                border-radius: {Radius.sm}px;
                padding: 3px 9px;
                font-size: {FontSize.tiny}px;
            }}
            #TerminalResetBtn:hover {{
                background: {c.surface_overlay};
                color: {c.text_primary};
                border-color: {c.accent};
            }}
        """)
        self._out._apply_style()

    def refresh_theme(self):
        self._apply_style()

    def apply_terminal_settings(self):
        self._out.apply_terminal_settings()
        font = _mono_font()
        self._prompt.setFont(font)
        self._input.setFont(font)
        try:
            pad = int(get_settings_manager().get("terminal", "padding", Spacing.md))
        except Exception:
            pad = Spacing.md
        self._row.layout().setContentsMargins(pad, Spacing.xs, pad, Spacing.xs)
        self._out.setViewportMargins(pad, Spacing.xs, 0, 0)


class ProblemsPanel(QWidget):
    """
    Smart Problem Finder — analyzes LSP diagnostics, compiler errors, and
    runtime tracebacks to present a minimal-word summary of what went wrong
    plus a concise 1-line smart fix, or confirms when no problems exist.
    """

    problem_activated = Signal(str, int)  # path, line (1-based)
    scan_requested = Signal()

    _SEV_ORDER = {"error": 0, "warning": 1, "info": 2}
    _SEV_ICON = {"error": "✕", "warning": "⚠", "info": "ℹ"}

    _RE_TOOL = re.compile(
        r'^\s*(?P<path>(?:[A-Za-z]:)?[^\s:][^:\n]*\.[A-Za-z0-9_]+)'
        r':(?P<line>\d+)(?::(?P<col>\d+))?:\s*(?P<msg>\S.*?)\s*$')
    _RE_FRAME = re.compile(r'^\s*File "(?P<path>[^"]+)", line (?P<line>\d+)')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ProblemsPanel")
        self._sources: dict[str, dict[str, list]] = {"lsp": {}, "terminal": {}, "scan": {}}
        self._term_buf = ""
        self._counts = {"error": 0, "warning": 0, "info": 0}
        self._last_run_clean = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Smart Problem Finder header bar
        hbar = QFrame()
        hbar.setObjectName("ProblemsHeaderBar")
        hbar.setAttribute(Qt.WA_StyledBackground, True)
        hlay = QHBoxLayout(hbar)
        hlay.setContentsMargins(Spacing.md, Spacing.xs, Spacing.md, Spacing.xs)
        hlay.setSpacing(Spacing.sm)

        self._badge = Pill("✓ 0 Problems", "success")
        self._summary_lbl = QLabel("Smart Problem Finder — ready to analyze your code.")
        self._summary_lbl.setObjectName("ProblemsSummaryLbl")

        self._scan_btn = QPushButton("🔍 Check Active Code")
        self._scan_btn.setObjectName("ProblemsScanBtn")
        self._scan_btn.setCursor(Qt.PointingHandCursor)
        self._scan_btn.setToolTip("Scan the active editor file for syntax and common errors")
        self._scan_btn.clicked.connect(self.scan_requested.emit)

        hlay.addWidget(self._badge)
        hlay.addWidget(self._summary_lbl, 1)
        hlay.addWidget(self._scan_btn)
        lay.addWidget(hbar)

        self._list = QListWidget()
        self._list.setObjectName("ProblemsList")
        self._list.setFrameShape(QListWidget.NoFrame)
        self._list.setFont(_mono_font())
        self._list.setWordWrap(True)
        self._list.setSpacing(3)
        self._list.itemActivated.connect(self._activate)
        self._list.itemClicked.connect(self._activate)
        self._list.itemDoubleClicked.connect(self._activate)

        self._empty = QLabel("✓ No problems detected — your code is clean.")
        self._empty.setObjectName("ProblemsEmptyBanner")
        self._empty.setContentsMargins(Spacing.lg, Spacing.lg, Spacing.lg, Spacing.lg)

        lay.addWidget(self._empty)
        lay.addWidget(self._list, 1)
        self._list.hide()
        self._apply_style()

    @staticmethod
    def _smart_explain_problem(raw_msg: str) -> tuple[str, str]:
        """
        Convert a raw compiler/LSP/runtime error string into:
          (minimal_problem_summary, one_line_smart_fix)
        """
        msg = (raw_msg or "").strip()
        low = msg.lower()

        if "zerodivisionerror" in low or "division by zero" in low:
            return (
                "Division by zero (ZeroDivisionError)",
                "Check that the divisor is not 0 before dividing (e.g. `if num2 != 0:`).",
            )
        if "syntaxerror" in low:
            if "expected ':'" in low or "invalid syntax" in low:
                return (
                    f"Syntax error — {msg}",
                    "Add a missing colon `:`, closing bracket `)`, or quote on this line.",
                )
            return (
                f"Syntax error — {msg}",
                "Fix the syntax on this line (check colons, brackets, and quotes).",
            )
        if "indentationerror" in low or "unexpected indent" in low or "expected an indented block" in low:
            return (
                f"Indentation error — {msg}",
                "Align indentation consistently (use 4 spaces after `if`, `for`, `while`, `def`).",
            )
        if "nameerror" in low or "is not defined" in low or "undeclared" in low:
            m = re.search(r"name '([^']+)' is not defined", msg)
            sym = m.group(1) if m else "variable"
            return (
                f"Undefined name `{sym}` ({msg})",
                f"Define or initialize `{sym}` before using it, or fix its spelling.",
            )
        if "valueerror" in low and ("int()" in low or "float()" in low):
            return (
                "Invalid numeric input conversion (ValueError)",
                "Ensure input is a valid number or use `float()` for decimal values.",
            )
        if "typeerror" in low:
            return (
                f"Type mismatch — {msg[:95]}",
                "Convert `input()` strings with `int()` or `float()` before math/comparisons.",
            )
        if "indexerror" in low or "out of range" in low or "out of bounds" in low:
            return (
                "List/array index out of range (IndexError)",
                "Verify the list is not empty (`if len(arr) > 0:`) and index is `< len(arr)`.",
            )
        if "keyerror" in low:
            return (
                f"Missing dictionary key ({msg})",
                "Use `dict.get(key)` or check `if key in my_dict:` before reading.",
            )
        if "attributeerror" in low:
            return (
                f"Missing attribute/method — {msg[:95]}",
                "Check that the object is not `None` and the method name is spelled right.",
            )
        if "eoferror" in low:
            return (
                "Program read past end of input (EOFError)",
                "Ensure your `while` loop breaks on the Exit option or provide enough inputs.",
            )
        if "modulenotfounderror" in low or "importerror" in low:
            return (
                f"Missing module — {msg[:95]}",
                "Install the required package (`pip install <pkg>`) or check the import name.",
            )
        if "unused" in low:
            return (
                msg[:100],
                "Remove the unused variable/import or prefix it with `_`.",
            )
        if "expected ';'" in low:
            return (
                "Missing semicolon `;`",
                "Add a semicolon `;` at the end of the statement.",
            )
        return (
            msg[:110] or "Code issue detected",
            "Inspect this line and verify variable types, syntax, and edge cases.",
        )

    def scan_code(self, file_path: str, code: str) -> int:
        """
        Instantly scan `code` for syntax/indentation errors and common mistakes,
        populating the Smart Problem Finder. Returns number of issues found.
        """
        path = file_path or "active_buffer.py"
        ext = os.path.splitext(path)[1].lower()
        issues: list[dict] = []

        if ext in ("", ".py"):
            try:
                ast.parse(code or "", filename=path)
            except IndentationError as exc:
                ln = int(getattr(exc, "lineno", 1) or 1)
                col = int(getattr(exc, "offset", 0) or 0)
                summary, fix = self._smart_explain_problem(f"IndentationError: {exc.msg}")
                issues.append({
                    "line": ln, "col": col, "severity": "error",
                    "message": summary, "fix": fix, "src": "scan",
                })
            except SyntaxError as exc:
                ln = int(getattr(exc, "lineno", 1) or 1)
                col = int(getattr(exc, "offset", 0) or 0)
                summary, fix = self._smart_explain_problem(f"SyntaxError: {exc.msg}")
                issues.append({
                    "line": ln, "col": col, "severity": "error",
                    "message": summary, "fix": fix, "src": "scan",
                })

        if issues:
            self._sources["scan"][path] = issues
        else:
            self._sources["scan"].pop(path, None)
        self._rebuild()
        return len(issues)

    def mark_run_succeeded(self):
        """Called when a program run or smart test finishes cleanly (exit code 0)."""
        self._last_run_clean = True
        self._sources["terminal"].clear()
        self._sources["scan"].clear()
        self._term_buf = ""
        self._rebuild()

    def set_diagnostics(self, file_path: str, diagnostics: list):
        norm = [self._normalize_lsp(d) for d in (diagnostics or [])]
        if norm:
            self._sources["lsp"][file_path] = norm
        else:
            self._sources["lsp"].pop(file_path, None)
        self._rebuild()

    def add_terminal_output(self, text: str):
        if not text:
            return
        self._term_buf += text
        if len(self._term_buf) > 200_000:
            self._term_buf = self._term_buf[-200_000:]
        parsed = self._parse_terminal(self._term_buf)
        if parsed:
            self._last_run_clean = False
        self._sources["terminal"] = parsed
        self._rebuild()

    def clear_terminal(self):
        self._sources["terminal"].clear()
        self._sources["scan"].clear()
        self._term_buf = ""
        self._rebuild()

    def total_count(self) -> int:
        return sum(self._counts.values())

    @classmethod
    def _normalize_lsp(cls, d: dict) -> dict:
        try:
            start = (d.get("range") or {}).get("start") or {}
            line = int(d.get("line", start.get("line", 0))) + 1
            col = int(d.get("column", start.get("character", 0)))
        except Exception:
            line, col = 1, 0
        sev = {1: "error", 2: "warning", 3: "info", 4: "info"}.get(
            d.get("severity", 1), "info")
        raw_msg = str(d.get("message", "")).strip()
        summary, fix = cls._smart_explain_problem(raw_msg)
        return {
            "line": max(line, 1),
            "col": col,
            "severity": sev,
            "message": summary,
            "fix": fix,
            "src": "lsp",
        }

    def _parse_terminal(self, buf: str) -> dict:
        out: dict[str, list] = {}
        total = 0

        def add(path: str, line: int, sev: str, msg: str):
            nonlocal total
            path = (path or "").strip()
            if not path or total >= 200:
                return
            summary, fix = self._smart_explain_problem(msg)
            lst = out.setdefault(path, [])
            entry = {
                "line": int(line),
                "col": 0,
                "severity": sev,
                "message": summary,
                "fix": fix,
                "src": "run",
            }
            if len(lst) >= 100 or any(
                e["line"] == entry["line"] and e["message"] == entry["message"]
                for e in lst
            ):
                return
            lst.append(entry)
            total += 1

        lines = buf.splitlines()
        i, n = 0, len(lines)
        while i < n and total < 200:
            ln = lines[i]
            if ln.strip().startswith("Traceback (most recent call last)") or 'File "' in ln:
                j = i + 1 if ln.strip().startswith("Traceback") else i
                last = None
                while j < n:
                    m = self._RE_FRAME.match(lines[j])
                    if m:
                        last = (m.group("path"), int(m.group("line")))
                        j += 1
                        while j < n and (lines[j].startswith("    ") or set(lines[j].strip()) <= {"^", "~"}):
                            j += 1
                        continue
                    break
                msg = lines[j].strip() if j < n else "Runtime Error"
                if last:
                    add(last[0], last[1], "error", msg or "Runtime Error")
                i = max(i + 1, j + 1)
                continue
            m = self._RE_TOOL.match(ln)
            if m:
                low = m.group("msg").lower()
                sev = ("error" if ("error" in low or "fatal" in low)
                       else "warning" if "warn" in low else "info")
                add(m.group("path"), int(m.group("line")), sev, m.group("msg"))
            i += 1
        return out

    def _rebuild(self):
        c = get_design_system().colors
        self._list.clear()
        self._counts = {"error": 0, "warning": 0, "info": 0}

        merged: dict[str, list] = {}
        for src in self._sources.values():
            for path, diags in src.items():
                if diags:
                    merged.setdefault(path, []).extend(diags)

        sev_color = {"error": c.error, "warning": c.warning, "info": c.info}
        any_rows = False
        for path in sorted(merged, key=lambda p: os.path.basename(p).lower()):
            diags = sorted(
                merged[path],
                key=lambda d: (self._SEV_ORDER.get(d["severity"], 2), d["line"]),
            )
            fname = os.path.basename(path)
            for d in diags:
                sev = d["severity"]
                self._counts[sev] = self._counts.get(sev, 0) + 1
                icon_ch = self._SEV_ICON.get(sev, "•")
                fix_txt = d.get("fix") or "Review this line and check syntax/types."
                text = (
                    f" {icon_ch}  {fname} · Line {d['line']}  —  {d['message']}\n"
                    f"     💡 Fix: {fix_txt}"
                )
                it = QListWidgetItem(text)
                it.setData(Qt.UserRole, (path, int(d["line"])))
                it.setForeground(QBrush(QColor(sev_color.get(sev, c.text_primary))))
                it.setToolTip(f"Click to jump to {path} (Line {d['line']})\nFix: {fix_txt}")
                self._list.addItem(it)
                any_rows = True

        total = self.total_count()
        if total == 0:
            self._badge.set_tone("success")
            self._badge.setText("✓ 0 Problems")
            if self._last_run_clean:
                self._summary_lbl.setText("Program ran successfully with 0 problems.")
                self._empty.setText(
                    "✓ No problems detected — your program ran successfully with zero errors."
                )
            else:
                self._summary_lbl.setText("No syntax or runtime problems detected.")
                self._empty.setText("✓ No problems detected — your code is clean.")
        else:
            errs = self._counts.get("error", 0)
            warns = self._counts.get("warning", 0)
            self._badge.set_tone("error" if errs else "warning")
            self._badge.setText(f"⚠ {total} Problem{'s' if total != 1 else ''}")
            self._summary_lbl.setText(
                f"Found {errs} error(s) and {warns} warning(s) — click any item to jump to the line."
            )

        self._list.setVisible(any_rows)
        self._empty.setVisible(not any_rows)

    def _activate(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole) if item else None
        if data:
            path, line = data
            self.problem_activated.emit(str(path), int(line))

    def _apply_style(self):
        c = get_design_system().colors
        self._list.setStyleSheet(f"""
            QListWidget#ProblemsList {{
                background: {c.surface_inset};
                border: none;
                outline: none;
                padding: 6px 8px;
            }}
            QListWidget#ProblemsList::item {{
                background: {c.surface_raised};
                border: 1px solid {c.border_subtle};
                border-radius: {Radius.sm}px;
                padding: 6px 10px;
                margin-bottom: 4px;
            }}
            QListWidget#ProblemsList::item:hover {{
                background: {c.surface_overlay};
                border-color: {c.border_strong};
            }}
            QListWidget#ProblemsList::item:selected {{
                background: {c.accent_muted};
                color: {c.text_primary};
                border-color: {c.accent};
            }}
        """)
        self.setStyleSheet(f"""
            #ProblemsHeaderBar {{
                background: {c.surface};
                border-bottom: 1px solid {c.border_subtle};
            }}
            #ProblemsSummaryLbl {{
                color: {c.text_secondary};
                font-size: {FontSize.tiny}px;
            }}
            #ProblemsEmptyBanner {{
                color: {c.success};
                font-size: {FontSize.small}px;
                font-weight: 600;
            }}
            #ProblemsScanBtn {{
                background: {c.surface_raised};
                color: {c.text_secondary};
                border: 1px solid {c.border};
                border-radius: {Radius.sm}px;
                padding: 2px 8px;
                font-size: {FontSize.tiny}px;
            }}
            #ProblemsScanBtn:hover {{
                background: {c.surface_overlay};
                color: {c.text_primary};
                border-color: {c.accent};
            }}
        """)

    def refresh_theme(self):
        self._list.setFont(_mono_font())
        self._badge.refresh_theme()
        self._apply_style()
        self._rebuild()


class BottomDock(QFrame):

    run_requested = Signal()
    stop_requested = Signal()
    kill_requested = Signal()
    reset_requested = Signal()
    stdin_submitted = Signal(str)
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BottomDock")
        self.setAttribute(Qt.WA_StyledBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self.terminal = TerminalView()
        self.output = OutputView()
        self.problems = ProblemsPanel()
        self._tabs.addTab(self.terminal, "Terminal")
        self._tabs.addTab(self.output, "Output")
        self._tabs.addTab(self.problems, "Problems")

        # Top-right corner action bar for Terminal / Output / Problems
        corner = QWidget()
        corner.setObjectName("DockCornerBar")
        clay = QHBoxLayout(corner)
        clay.setContentsMargins(Spacing.sm, 2, Spacing.sm, 2)
        clay.setSpacing(Spacing.xs)

        self._kill_btn = QPushButton("■ Kill")
        self._kill_btn.setObjectName("DockKillBtn")
        self._kill_btn.setCursor(Qt.PointingHandCursor)
        self._kill_btn.setToolTip("Kill running process or terminal session")
        self._kill_btn.clicked.connect(self._on_kill_clicked)

        self._reset_btn = QPushButton("↻ Reset / Restore")
        self._reset_btn.setObjectName("DockResetBtn")
        self._reset_btn.setCursor(Qt.PointingHandCursor)
        self._reset_btn.setToolTip("Kill process, clear console, and restore fresh Terminal or Output tab")
        self._reset_btn.clicked.connect(self._on_reset_clicked)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setObjectName("DockClearBtn")
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.setToolTip("Clear current tab output")
        self._clear_btn.clicked.connect(self.clear_active_tab)

        self._close_btn = QPushButton("×")
        self._close_btn.setObjectName("DockCloseBtn")
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.setToolTip("Hide bottom panel (Ctrl+`)")
        self._close_btn.setFixedSize(22, 22)
        self._close_btn.clicked.connect(self.closed.emit)

        clay.addWidget(self._kill_btn)
        clay.addWidget(self._reset_btn)
        clay.addWidget(self._clear_btn)
        clay.addWidget(self._close_btn)
        self._tabs.setCornerWidget(corner, Qt.TopRightCorner)

        # Forward interactive stdin & kill/reset signals from both Terminal and Output
        self.terminal.stdin_submitted.connect(self.stdin_submitted.emit)
        self.output.stdin_submitted.connect(self.stdin_submitted.emit)
        self.terminal.kill_requested.connect(self._on_kill_clicked)
        self.output.kill_requested.connect(self._on_kill_clicked)
        self.terminal.reset_requested.connect(self._on_reset_clicked)

        lay.addWidget(self._tabs)
        self.setMinimumHeight(Terminal.MIN_HEIGHT)
        self._apply_style()

    def _on_kill_clicked(self):
        self.stop_requested.emit()
        self.kill_requested.emit()
        killed_term = self.terminal.kill_active()
        self.output.set_program_running(False)
        if self._tabs.currentWidget() is self.output and not killed_term:
            self.output.append_text("\n[Process killed]\n")

    def _on_reset_clicked(self):
        self.stop_requested.emit()
        self.reset_requested.emit()
        self.output.set_program_running(False)
        cur = self._tabs.currentWidget()
        if cur is self.output:
            self.output.clear()
            self.output.append_text("[Output cleared and restored — ready]\n")
        elif cur is self.problems:
            self.clear_terminal_problems()
        else:
            self.terminal.reset_session()
            self._tabs.setCurrentWidget(self.terminal)

    def clear_active_tab(self):
        cur = self._tabs.currentWidget()
        if cur is self.terminal:
            self.terminal.clear_console()
        elif cur is self.output:
            self.output.clear()
        elif cur is self.problems:
            self.clear_terminal_problems()

    def clear_output(self):
        self.output.clear()

    def start_program_run(self, name: str, command: str):
        """Switch to the interactive Terminal tab and start a live program session."""
        self.output.set_program_running(True)
        self._tabs.setCurrentWidget(self.terminal)
        self.terminal.start_program_session(name, command)

    def append_run_output(self, text: str, stream: str = "stdout"):
        """Route live program output (`▶ Run`) to the interactive Terminal tab (and mirror to Output)."""
        self.terminal.append_program_output(text)
        self.output.append_text(text)
        self._tabs.setCurrentWidget(self.terminal)
        self.problems.add_terminal_output(text)
        self._update_problem_tab()

    def append_output(self, text: str, stream: str = "stdout"):
        """Route test/diagnostic output (`🧪 Test`) to the Output tab."""
        self.output.append_text(text)
        self._tabs.setCurrentWidget(self.output)
        self.problems.add_terminal_output(text)
        self._update_problem_tab()

    def run_finished(self, exit_code: int, is_test: bool = False, stopped: bool = False):
        self.output.set_program_running(False)
        if is_test:
            self.output.append_text(f"\n[process exited with code {exit_code}]\n")
        else:
            self.terminal.finish_program_session(exit_code, stopped=stopped)
        if exit_code == 0 and not stopped:
            self.problems.mark_run_succeeded()
        self._update_problem_tab()

    def set_diagnostics(self, path: str, diagnostics: list):
        self.problems.set_diagnostics(path, diagnostics)
        self._update_problem_tab()

    def clear_terminal_problems(self):
        self.problems.clear_terminal()
        self._update_problem_tab()

    def _update_problem_tab(self):
        try:
            idx = self._tabs.indexOf(self.problems)
            n = self.problems.total_count()
            self._tabs.setTabText(idx, f"Problems ({n})" if n else "Problems (0)")
        except Exception:
            pass

    def show_terminal(self):
        self._tabs.setCurrentWidget(self.terminal)
        self.terminal.focus_input()

    def show_output(self):
        self._tabs.setCurrentWidget(self.output)

    def show_problems(self):
        self._tabs.setCurrentWidget(self.problems)

    def _apply_style(self):
        c = get_design_system().colors
        t = _terminal_colors()
        self.setStyleSheet(f"""
            #BottomDock {{
                background: {t['bg']};
                border-top: 1px solid {c.border};
            }}
            #BottomDock QTabWidget::pane {{
                border: none;
                background: {t['bg']};
            }}
            #BottomDock QTabBar {{ background: {c.surface}; }}
            #BottomDock QTabBar::tab {{
                background: {c.surface};
                color: {c.text_muted};
                border: none;
                border-bottom: 2px solid transparent;
                padding: {Spacing.xs}px {Spacing.md}px;
                font-size: {FontSize.small}px;
            }}
            #BottomDock QTabBar::tab:hover {{ color: {c.text_secondary}; }}
            #BottomDock QTabBar::tab:selected {{
                color: {c.text_primary};
                border-bottom: 2px solid {c.accent};
                background: {t['bg']};
            }}
            #DockCornerBar {{
                background: {c.surface};
            }}
            #DockKillBtn {{
                background: {c.surface_raised};
                color: {c.error};
                border: 1px solid {c.border};
                border-radius: {Radius.sm}px;
                padding: 2px 8px;
                font-size: {FontSize.tiny}px;
                font-weight: 600;
            }}
            #DockKillBtn:hover {{
                background: {c.error};
                color: #ffffff;
                border-color: {c.error};
            }}
            #DockResetBtn, #DockClearBtn {{
                background: {c.surface_raised};
                color: {c.text_secondary};
                border: 1px solid {c.border};
                border-radius: {Radius.sm}px;
                padding: 2px 8px;
                font-size: {FontSize.tiny}px;
            }}
            #DockResetBtn:hover, #DockClearBtn:hover {{
                background: {c.surface_overlay};
                color: {c.text_primary};
                border-color: {c.accent};
            }}
            #DockCloseBtn {{
                background: transparent;
                color: {c.text_muted};
                border: none;
                border-radius: {Radius.sm}px;
                font-size: 14px;
                font-weight: 600;
                padding: 0px;
            }}
            #DockCloseBtn:hover {{
                background: {c.surface_overlay};
                color: {c.text_primary};
            }}
        """)

    def refresh_theme(self):
        self._apply_style()
        for child in (self.terminal, self.output, self.problems):
            fn = getattr(child, "refresh_theme", None)
            if callable(fn):
                fn()

    def apply_terminal_settings(self):
        for child in (self.terminal, self.output):
            fn = getattr(child, "apply_terminal_settings", None)
            if callable(fn):
                fn()

