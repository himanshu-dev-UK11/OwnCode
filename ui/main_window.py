"""
Consolidated Module: ui.main_window

Combines: ui.inline_ai, ui.main_window
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['ui.inline_ai', 'ui.main_window']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ui.inline_ai (ui/inline_ai.py)
# ============================================================================
"""
Inline AI (editor) — v1.0

An optional, cloud-backed inline edit flow. It is DISABLED BY DEFAULT — the user
must turn on `ai.inline_ai_enabled` in Settings. When enabled, pressing Ctrl+K in
the editor with a selection asks the assistant to rewrite that selection; the
result is shown as a diff the user must accept before anything changes.

Because it reuses the configured cloud provider/model (via AIChatEngine), it
costs tokens — hence the opt-in. With the setting off, the editor works exactly
as before and no network calls are ever made.

Wiring: MainWindow creates one InlineAIController(window) and binds Ctrl+K to
`controller.trigger`. The controller reaches the active editor through
`window.center.editor_tabs.current_editor()` and the model through
`window.chat_engine`.
"""

import difflib

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit, QInputDialog,
    QLineEdit,
)

from ui.design_system import get_design_system, Spacing, FontSize
from ui.widgets.controls import TextButton


# Qt uses U+2029 (paragraph separator) for line breaks inside selectedText().
_QT_PARA_SEP = " "


class _DiffDialog(QDialog):
    """Shows a unified diff of the proposed rewrite with Apply / Cancel."""

    def __init__(self, original: str, proposed: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Inline AI — review changes")
        self.resize(720, 480)
        c = get_design_system().colors
        lay = QVBoxLayout(self)
        lay.setContentsMargins(Spacing.lg, Spacing.lg, Spacing.lg, Spacing.lg)
        lay.setSpacing(Spacing.md)

        info = QLabel("Review the assistant's proposed change. Nothing is applied "
                      "until you choose Apply.")
        info.setWordWrap(True)
        info.setProperty("role", "muted")
        lay.addWidget(info)

        diff = "\n".join(difflib.unified_diff(
            original.splitlines(), proposed.splitlines(),
            fromfile="current", tofile="proposed", lineterm=""))
        view = QPlainTextEdit()
        view.setReadOnly(True)
        view.setPlainText(diff or "(no textual difference)")
        view.setStyleSheet(
            f"background:{c.surface_inset}; color:{c.text_primary};"
            f" border:1px solid {c.border_subtle}; border-radius:4px;"
            f" font-family:monospace; font-size:{FontSize.small}px;")
        lay.addWidget(view, 1)

        row = QHBoxLayout()
        row.addStretch(1)
        cancel = TextButton("Cancel")
        cancel.clicked.connect(self.reject)
        apply_btn = TextButton("Apply", variant="primary")
        apply_btn.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(apply_btn)
        lay.addLayout(row)


class InlineAIController(QObject):
    """Coordinates a single Ctrl+K inline edit from trigger to applied diff."""

    _result_ready = Signal(str)
    _failed = Signal(str)

    def __init__(self, window):
        super().__init__(window)
        self._window = window
        self._pending_cursor = None
        self._pending_original = ""
        self._result_ready.connect(self._on_result)   # marshals to UI thread
        self._failed.connect(self._on_error)

    # -- settings ------------------------------------------------------------
    def _enabled(self) -> bool:
        try:
            from ui.settings_manager import get_settings_manager
            return bool(get_settings_manager().get("ai", "inline_ai_enabled", False))
        except Exception:
            return False

    def _notify(self, message: str, level: str = "info"):
        fn = getattr(getattr(self._window, "notifications", None), "notify", None)
        if callable(fn):
            fn(message, level)
        else:
            try:
                self._window.status_bar.showMessage(message, 4000)
            except Exception:
                pass

    # -- trigger -------------------------------------------------------------
    def trigger(self):
        if not self._enabled():
            self._notify(
                "Inline AI is off. Enable it in Settings → AI → Inline AI (editor).",
                "info")
            return

        editor = self._current_editor()
        if editor is None:
            self._notify("Open a file to use inline AI.", "info")
            return

        cursor = editor.textCursor()
        selected = cursor.selectedText().replace(_QT_PARA_SEP, "\n")
        if not selected.strip():
            self._notify("Select the code you want to rewrite, then press Ctrl+K.",
                         "info")
            return

        instruction, ok = QInputDialog.getText(
            self._window, "Inline AI",
            "Describe the change (e.g. 'add error handling', 'convert to async'):",
            QLineEdit.Normal, "")
        if not ok or not instruction.strip():
            return

        engine = getattr(self._window, "chat_engine", None)
        if engine is None or not hasattr(engine, "generate_once"):
            self._notify("AI engine is not available.", "error")
            return

        self._pending_cursor = cursor
        self._pending_original = selected
        language = self._language_of(editor)
        prompt = self._build_prompt(instruction.strip(), selected, language)
        self._notify("Inline AI: generating…", "info")
        engine.generate_once(
            prompt,
            on_complete=lambda text: self._result_ready.emit(text),
            on_error=lambda err: self._failed.emit(err))

    # -- helpers -------------------------------------------------------------
    def _current_editor(self):
        try:
            return self._window.center.editor_tabs.current_editor()
        except Exception:
            return None

    def _language_of(self, editor) -> str:
        for attr in ("language", "_language"):
            val = getattr(editor, attr, None)
            if isinstance(val, str) and val:
                return val
        return ""

    def _build_prompt(self, instruction: str, code: str, language: str) -> str:
        lang = f" ({language})" if language else ""
        return (
            "You are an inline code-editing assistant. Rewrite the code below "
            f"according to this instruction: {instruction}\n\n"
            "Return ONLY the rewritten code with no explanation, no commentary, "
            "and no Markdown code fences.\n\n"
            f"Code{lang}:\n{code}")

    def _clean(self, text: str) -> str:
        """Strip stray Markdown fences the model may add despite instructions."""
        t = text.strip()
        if t.startswith("```"):
            lines = t.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            t = "\n".join(lines)
        return t

    # -- results (UI thread) -------------------------------------------------
    def _on_result(self, text: str):
        proposed = self._clean(text)
        if not proposed:
            self._notify("Inline AI returned nothing.", "warning")
            return
        if proposed == self._pending_original:
            self._notify("Inline AI: no changes suggested.", "info")
            return
        dlg = _DiffDialog(self._pending_original, proposed, self._window)
        if dlg.exec() == QDialog.Accepted and self._pending_cursor is not None:
            cur = self._pending_cursor
            cur.beginEditBlock()
            cur.insertText(proposed)
            cur.endEditBlock()
            self._notify("Inline AI: applied.", "success")
        self._pending_cursor = None
        self._pending_original = ""

    def _on_error(self, err: str):
        self._notify(f"Inline AI failed: {err}", "error")
        self._pending_cursor = None
        self._pending_original = ""


# ============================================================================
# SECTION: ui.main_window (ui/main_window.py)
# ============================================================================
"""
Main Window — v2.1 (Graphite + Smart Program & Terminal Testing)

The application shell. Assembles the chrome (title bar, tool bar, activity bar,
status bar) around the primary work surfaces (sidebar, center editor/dashboard,
bottom dock, AI workspace) and wires every widget to the backend EventBus.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QMenu,
    QInputDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut, QCursor

from core.process_utils import HiddenProcess as QProcess, configure_qprocess_no_window
from ui.design_system import get_design_system, Sidebar as SB, AIPanel, Terminal
from ui.widgets.native_dialogs import (
    select_existing_directory, select_existing_file, select_save_file,
)
from ui.widgets.controls import restyle_atoms, vline
from ui.shell.titlebar import TitleBar
from ui.shell.activity_bar import ActivityBar
from ui.shell.status_bar import StatusBar
from ui.panels.sidebar import Sidebar
from ui.panels.center import CenterPanel
from ui.panels.bottom_dock import BottomDock
from ui.panels.ai_workspace import AIWorkspace
from ui.panels.command_palette import CommandPalette
from ui.panels.notifications import NotificationCenter


class _MainWindowMarshal(QObject):
    run = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.run.connect(self._exec)

    @staticmethod
    def _exec(fn):
        try:
            fn()
        except Exception:
            pass


class MainWindow(QMainWindow):

    def __init__(self, event_bus):
        super().__init__()
        self.event_bus = event_bus
        self._ui_marshal = _MainWindowMarshal(self)

        # backend handles (populated by main.py setters)
        self.theme_manager = None
        self.lsp_manager = None
        self.project_analyzer = None
        self.workspace_manager = None
        self.chat_engine = None
        self.provider_manager = None
        self.ai_integration = None
        self.llm_optimizer = None

        self._sidebar_visible = True
        self._last_sidebar_width = SB.DEFAULT_WIDTH
        # Keep the terminal out of the way until the user runs something or
        # explicitly toggles it. Chat requests must not change this view.
        self._bottom_visible = False
        self._ai_visible = True
        self._settings_dialog = None   # built lazily by open_settings()
        self._pending_preview = ""     # path the explorer asked to preview

        self.setWindowTitle("OwnCode")
        self.setMinimumSize(1100, 700)

        self._build_ui()
        self.bottom_dock.setVisible(False)
        self._wire_widgets()
        self._install_shortcuts()
        self._subscribe_events()
        try:
            restyle_atoms(self)
            restyle_atoms(self.command_palette)
        except Exception:
            pass
        self.status_bar.showMessage("Ready")

    # ── construction ──────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.titlebar = TitleBar()
        root.addWidget(self.titlebar)

        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)

        self.activity_bar = ActivityBar()
        body_lay.addWidget(self.activity_bar)
        self._rail_sep = vline()
        body_lay.addWidget(self._rail_sep)

        # main horizontal splitter: sidebar | (center/bottom) | ai
        self.main_split = QSplitter(Qt.Horizontal)
        self.main_split.setChildrenCollapsible(False)
        self.main_split.setHandleWidth(1)

        self.sidebar = Sidebar(event_bus=self.event_bus)
        self.sidebar.setMinimumWidth(SB.MIN_WIDTH)
        self.sidebar.setMaximumWidth(SB.MAX_WIDTH)

        # center + bottom dock in a vertical splitter
        self.center_split = QSplitter(Qt.Vertical)
        self.center_split.setChildrenCollapsible(False)
        self.center_split.setHandleWidth(1)
        self.center = CenterPanel(event_bus=self.event_bus)
        self.bottom_dock = BottomDock()
        self.center_split.addWidget(self.center)
        self.center_split.addWidget(self.bottom_dock)
        self.center_split.setStretchFactor(0, 5)
        self.center_split.setStretchFactor(1, 2)
        self.center_split.setSizes([600, Terminal.DEFAULT_HEIGHT])

        self.ai_workspace = AIWorkspace(event_bus=self.event_bus)
        self.ai_workspace.setMinimumWidth(AIPanel.MIN_WIDTH)
        self.ai_workspace.setMaximumWidth(AIPanel.MAX_WIDTH)

        self.main_split.addWidget(self.sidebar)
        self.main_split.addWidget(self.center_split)
        self.main_split.addWidget(self.ai_workspace)
        self.main_split.setStretchFactor(0, 0)
        self.main_split.setStretchFactor(1, 1)
        self.main_split.setStretchFactor(2, 0)
        self.main_split.setSizes([SB.DEFAULT_WIDTH, 900, AIPanel.DEFAULT_WIDTH])

        body_lay.addWidget(self.main_split, 1)
        root.addWidget(body, 1)

        self.status_bar = StatusBar()
        root.addWidget(self.status_bar)

        # overlays
        self.command_palette = CommandPalette(self)
        self.notifications = NotificationCenter(self)

    # ── widget wiring (Qt signals → EventBus / local) ─────────────────────
    def _wire_widgets(self):
        # Activity bar & Sidebar collapse
        self.activity_bar.view_changed.connect(self._on_view_changed)
        self.activity_bar.sidebar_toggled.connect(self.toggle_sidebar)
        self.activity_bar.ai_toggled.connect(self.toggle_ai)
        self.activity_bar.settings_requested.connect(self.open_settings)
        self.sidebar.collapse_requested.connect(self.toggle_sidebar)
        if hasattr(self.sidebar, 'view_selected') and hasattr(self.activity_bar, 'set_active'):
            self.sidebar.view_selected.connect(self.activity_bar.set_active)

        # Title bar (unified chrome — identity, file/run/test actions, toggles)
        self.titlebar.command_palette_requested.connect(lambda: self.open_command_palette("file"))
        self.titlebar.notifications_requested.connect(
            lambda: self.notifications.notify("You're all caught up.", "info"))
        self.titlebar.ai_toggled.connect(self.toggle_ai)
        self.titlebar.theme_selected.connect(self._on_theme_selected)
        self.titlebar.all_themes_requested.connect(
            lambda: self.open_settings("appearance"))
        self.titlebar.menu_requested.connect(lambda: self.open_command_palette("command"))
        self.titlebar.run_requested.connect(self._on_run)
        self.titlebar.test_requested.connect(self._on_quick_test)
        self.titlebar.stop_requested.connect(self._on_stop)
        self.titlebar.save_requested.connect(self._on_save)
        self.titlebar.new_file_requested.connect(self._on_new_file)
        self.titlebar.open_folder_requested.connect(self.open_folder)
        self.titlebar.toggle_sidebar.connect(self.toggle_sidebar)
        self.titlebar.toggle_terminal.connect(self.toggle_bottom)

        # Explorer
        self.sidebar.explorer.file_activated.connect(
            lambda path: self.event_bus.publish("file_open_requested", {"path": path}))
        self.sidebar.explorer.file_previewed.connect(self._on_file_previewed)
        self.sidebar.explorer.open_folder_requested.connect(self.open_folder)
        self.sidebar.explorer.open_recent_requested.connect(self._open_workspace)
        self.sidebar.explorer.clone_repo_requested.connect(self._on_clone_repo)
        self.sidebar.explorer.refresh_requested.connect(
            lambda: self.event_bus.publish("request_refresh_workspace", {}))

        # Feature panels (search / GitHub-Git / run / tests / tasks / memory)
        self.sidebar.search.file_open_requested.connect(
            lambda path, line: self.event_bus.publish(
                "file_open_requested", {"path": path, "line": line}))
        self.sidebar.search.toast.connect(self._panel_toast)
        self.sidebar.git.file_open_requested.connect(
            lambda path: self.event_bus.publish("file_open_requested", {"path": path}))
        self.sidebar.git.diff_requested.connect(self._on_diff_requested)
        self.sidebar.git.toast.connect(self._panel_toast)
        self.sidebar.run.toast.connect(self._panel_toast)
        self.sidebar.tests.toast.connect(self._panel_toast)
        self.sidebar.tests.quick_test_requested.connect(self._on_quick_test)
        self.sidebar.tests.custom_test_requested.connect(self._on_custom_test)
        self.sidebar.tests.terminal_test_requested.connect(self._on_test_terminal)
        self.sidebar.tests.set_code_provider(self._active_editor_text)
        self.sidebar.tasks.toast.connect(self._panel_toast)
        self.sidebar.memory.toast.connect(self._panel_toast)

        # Dashboard
        self.center.dashboard.open_recent_requested.connect(self._open_workspace)
        self.center.dashboard.open_folder_requested.connect(self.open_folder)
        self.center.dashboard.new_file_requested.connect(self._on_new_file)
        self.center.dashboard.clone_repo_requested.connect(self._on_clone_repo)

        # Editor tabs
        self.center.editor_tabs.save_requested.connect(lambda _path: self._on_save())
        self.center.editor_tabs.close_requested.connect(
            lambda path: self.event_bus.publish("request_close_file", {"path": path}))
        self.center.editor_tabs.current_file_changed.connect(self._on_current_file_changed)
        self.center.editor_tabs.cursor_moved.connect(self.status_bar.set_cursor)
        self.center.editor_tabs.language_changed.connect(self.status_bar.set_language)
        self.center.editor_tabs.definition_found.connect(self._on_definition_found)
        self.center.editor_tabs.references_found.connect(self._on_references_found)
        self.center.editor_tabs.rename_requested.connect(self._on_rename_requested)
        self.sidebar.explorer.file_renamed.connect(self._on_file_renamed)
        self.center.reveal_requested.connect(self._on_breadcrumb_reveal)

        # Bottom dock
        self.bottom_dock.run_requested.connect(self._on_run)
        self.bottom_dock.stop_requested.connect(self._on_stop)
        self.bottom_dock.kill_requested.connect(self._on_stop)
        self.bottom_dock.reset_requested.connect(self._on_stop)
        self.bottom_dock.closed.connect(lambda: self._show_bottom(False))
        self.bottom_dock.stdin_submitted.connect(
            lambda text: self.event_bus.publish("stdin_input", {"text": text}))
        self.bottom_dock.problems.problem_activated.connect(self._on_problem_activated)
        self.bottom_dock.problems.scan_requested.connect(self._on_scan_active_code)
        self.main_split.splitterMoved.connect(lambda *_: self.notifications.resize_to_parent())

        # Status bar: the LSP segment opens a server-state popup.
        self.status_bar.lsp_clicked.connect(self._on_lsp_clicked)

        # Command palette
        self.command_palette.file_chosen.connect(
            lambda path: self.event_bus.publish("file_open_requested", {"path": path}))
        self.command_palette.command_chosen.connect(self._run_command_id)
        self.command_palette.set_commands(self._command_list())

    def _install_shortcuts(self):
        def sc(seq, fn):
            s = QShortcut(QKeySequence(seq), self)
            s.activated.connect(fn)
            return s
        # File
        sc("Ctrl+N", self._on_new_file)
        sc("Ctrl+O", self.open_folder)
        sc("Ctrl+S", self._on_save)
        sc("Ctrl+Shift+S", self._on_save_as)
        sc("Ctrl+W", self._close_current_tab)
        # Navigation / palette
        sc("Ctrl+P", lambda: self.open_command_palette("file"))
        sc("Ctrl+Shift+P", lambda: self.open_command_palette("command"))
        # View
        sc("Ctrl+B", self.toggle_sidebar)
        sc("Ctrl+`", self.toggle_bottom)
        sc("Ctrl+Shift+A", self.toggle_ai)
        sc("Ctrl+Shift+E", lambda: self._focus_view("explorer"))
        sc("Ctrl+Shift+F", lambda: self._focus_view("search"))
        sc("Ctrl+Shift+G", lambda: self._focus_view("git"))
        sc("Ctrl+Shift+T", lambda: self._focus_view("tests"))
        # Git actions
        sc("Ctrl+Alt+U", self._git_push)
        sc("Ctrl+Alt+D", self._git_pull)
        # Run / Quick Test / settings
        sc("F5", self._on_run)
        sc("F6", self._on_quick_test)
        sc("F2", self._on_f2)
        sc("Ctrl+,", self.open_settings)

        # Inline AI (editor)
        from ui.inline_ai import InlineAIController
        self.inline_ai = InlineAIController(self)
        sc("Ctrl+K", self.inline_ai.trigger)

    # ── EventBus subscriptions ────────────────────────────────────────────
    def _subscribe_events(self):
        b = self.event_bus
        b.subscribe("file_opened", self._on_file_opened)
        b.subscribe("file_reveal_requested", self._on_file_opened)
        b.subscribe("file_closed", self._on_file_closed)
        b.subscribe("workspace_loaded", self._on_workspace_loaded)
        b.subscribe("workspace_metadata_updated", self._on_workspace_metadata)
        b.subscribe("recent_projects_changed", self._on_recent_projects)
        b.subscribe("run_started", self._on_run_started)
        b.subscribe("process_output", self._on_process_output)
        b.subscribe("process_finished", self._on_process_finished)
        b.subscribe("test_finished", self._on_test_finished)
        b.subscribe("terminal_test_finished", self._on_terminal_test_finished)
        b.subscribe("log_message", self._on_log_message)
        b.subscribe("editor_saved", self._on_editor_saved)
        b.subscribe("file_saved", self._on_editor_saved)
        b.subscribe("editor_save_current_requested", lambda _d=None: self._on_save())
        b.subscribe("ai_chat_error", self._on_ai_error)
        b.subscribe("workspace_activated", self._on_workspace_loaded)
        b.subscribe("review_change_set", self._on_review_change_set)

    # ── backend setters (main.py contract) ───────────────────────────────
    def set_theme_manager(self, theme_manager):
        self.theme_manager = theme_manager
        try:
            active = None
            if hasattr(theme_manager, "current_theme"):
                active = theme_manager.current_theme
            elif hasattr(theme_manager, "get_current_theme"):
                active = theme_manager.get_current_theme()
            if isinstance(active, str):
                self.titlebar.set_active_theme(active)
        except Exception:
            pass
        for sig in ("theme_changed", "themeChanged"):
            obj = getattr(theme_manager, sig, None)
            if obj is not None and hasattr(obj, "connect"):
                try:
                    obj.connect(lambda *_: self.refresh_theme())
                except Exception:
                    pass
                break

    def set_lsp_manager(self, lsp_manager):
        self.lsp_manager = lsp_manager
        try:
            self.center.editor_tabs.set_lsp_manager(lsp_manager)
        except Exception:
            pass
        sig = getattr(lsp_manager, "diagnostics_received", None)
        if sig is not None and hasattr(sig, "connect"):
            try:
                sig.connect(self._on_diagnostics)
            except Exception:
                pass
        for name, handler in (("server_started", self._on_lsp_started),
                              ("server_stopped", self._on_lsp_stopped)):
            obj = getattr(lsp_manager, name, None)
            if obj is not None and hasattr(obj, "connect"):
                try:
                    obj.connect(handler)
                except Exception:
                    pass

    def set_project_analyzer(self, project_analyzer):
        self.project_analyzer = project_analyzer
        try:
            self.center.dashboard.set_project_analyzer(project_analyzer)
        except Exception:
            pass

    def set_workspace_manager(self, workspace_manager):
        self.workspace_manager = workspace_manager
        try:
            self.center.dashboard.set_workspace_manager(workspace_manager)
        except Exception:
            pass
        try:
            recents = list(getattr(workspace_manager, "recent_projects", []) or [])
            self._on_recent_projects({"projects": recents})
        except Exception:
            pass

    def set_chat_engine(self, chat_engine):
        self.chat_engine = chat_engine
        try:
            ws_root = getattr(self, "_workspace_root", None)
            if not ws_root and self.workspace_manager is not None:
                active_ws = getattr(self.workspace_manager, "active_workspace", None)
                ws_root = getattr(active_ws, "path", None)
            if ws_root and hasattr(chat_engine, "set_workspace_root"):
                chat_engine.set_workspace_root(str(ws_root))
            ed = self.center.editor_tabs.current_editor()
            if ed is not None and getattr(ed, "file_path", None):
                chat_engine.active_editor_file = str(ed.file_path)
            if hasattr(self.ai_workspace, "_mode"):
                chat_engine.active_mode = self.ai_workspace._mode
        except Exception:
            pass
        try:
            self.ai_workspace.set_chat_engine(chat_engine)
        except Exception:
            pass

    def set_provider_manager(self, provider_manager):
        self.provider_manager = provider_manager
        try:
            self.center.dashboard.set_provider_manager(provider_manager)
        except Exception:
            pass

    def set_ai_integration(self, ai_integration):
        self.ai_integration = ai_integration

    def set_llm_optimizer(self, llm_optimizer):
        self.llm_optimizer = llm_optimizer

    # ── EventBus handlers ─────────────────────────────────────────────────
    def _on_file_opened(self, data: dict):
        import threading as _th
        if _th.current_thread() is not _th.main_thread():
            self._ui_marshal.run.emit(lambda d=data: self._on_file_opened(d))
            return
        path = data.get("path_str") or str(data.get("path", ""))
        if not path:
            return
        preview = bool(data.get("preview")) or self._is_pending_preview(path)
        force_reload = bool(data.get("force_reload", False))
        try:
            self.center.open_file(
                path,
                data.get("content", ""),
                encoding=data.get("encoding", "utf-8"),
                read_only=data.get("read_only", False),
                preview=preview,
                force_reload=force_reload,
            )
        except TypeError:
            self.center.open_file(
                path,
                data.get("content", ""),
                encoding=data.get("encoding", "utf-8"),
                read_only=data.get("read_only", False),
                preview=preview,
            )
        try:
            self.sidebar.explorer.reveal(path)
        except Exception:
            pass
        line = data.get("line")
        if line:
            try:
                ed = self.center.editor_tabs.current_editor()
                if ed is not None:
                    ed.goto_line_column(int(line) - 1, int(data.get("column", 0)))
            except Exception:
                pass
        self.status_bar.showMessage(f"Opened {Path(path).name}", 2500)

    def _on_definition_found(self, path: str, line: int, column: int):
        if not path:
            return
        self.event_bus.publish(
            "file_open_requested",
            {"path": path, "line": line + 1, "column": column})

    def _on_references_found(self, symbol: str, locations: list):
        locs = locations or []
        self._panel_toast(f"{len(locs)} reference(s) to '{symbol}'.", "info")
        if locs:
            first = locs[0]
            self.event_bus.publish(
                "file_open_requested",
                {"path": first.path, "line": first.line + 1,
                 "column": first.column})

    def _on_rename_requested(self, change_set):
        self._on_review_change_set({"change_set": change_set,
                                    "prompt": "Rename symbol"})

    def _is_pending_preview(self, path: str) -> bool:
        pending = getattr(self, "_pending_preview", "")
        if not pending:
            return False
        try:
            match = Path(pending).resolve() == Path(path).resolve()
        except Exception:
            match = str(pending) == str(path)
        if match:
            self._pending_preview = ""
        return match

    def _on_file_previewed(self, path: str):
        self._pending_preview = path
        self.event_bus.publish("file_open_requested", {"path": path})

    def _on_file_closed(self, data: dict):
        path = data.get("path_str") or str(data.get("path", ""))
        if path:
            self.center.editor_tabs.force_close_tab(path)

    def _on_file_renamed(self, old_path: str, new_path: str):
        if self.center.editor_tabs.retarget_path(old_path, new_path):
            self.center.set_breadcrumb(new_path)
        self.status_bar.showMessage(f"Renamed to {Path(new_path).name}", 2500)

    def _on_f2(self):
        explorer = self.sidebar.explorer
        if explorer.has_tree_focus():
            explorer.rename_selected()
            return
        editor = self.center.editor_tabs.current_editor()
        if editor is not None:
            editor.request_rename()

    def _on_workspace_loaded(self, data: dict):
        path = data.get("path") or data.get("path_str") or ""
        if not path:
            return
        path = str(path)
        self._workspace_root = path
        self.sidebar.explorer.set_root(path)
        self.bottom_dock.terminal.set_cwd(path)
        try:
            self.center.set_workspace_root(path)
        except Exception:
            pass
        try:
            self.sidebar.set_root(path)
            name = Path(path).name or path
            self.sidebar.memory.set_project(name, path)
        except Exception:
            pass
        self.activity_bar.set_active("explorer")
        self.sidebar.set_view("explorer")
        self._show_sidebar(True)
        name = Path(path).name or path
        self.titlebar.set_workspace_name(name)
        self.status_bar.showMessage(f"Workspace: {name}", 3000)

    def _on_workspace_metadata(self, data: dict):
        name = data.get("project_name")
        if name:
            self.titlebar.set_workspace_name(name)
        lang = data.get("primary_language")
        if lang:
            self.status_bar.set_language(lang)

    def _on_recent_projects(self, data: dict):
        projects = data.get("projects", [])
        try:
            self.center.dashboard.set_recent_projects(projects)
        except Exception:
            pass
        try:
            self.sidebar.explorer.set_recent_projects(projects)
        except Exception:
            pass

    def _on_run_started(self, data: dict):
        self.titlebar.set_running(True)
        self.bottom_dock.clear_terminal_problems()
        self._show_bottom(True)
        if data.get("cwd"):
            self.bottom_dock.terminal.set_cwd(data["cwd"])
        self.bottom_dock.start_program_run(
            data.get("name", "Program"),
            data.get("command", ""),
        )

    def _on_process_output(self, data: dict):
        out = data.get("output", "")
        stream = data.get("stream", "stdout")
        if data.get("source") == "run":
            self.bottom_dock.append_run_output(out, stream)
        else:
            self.bottom_dock.append_output(out, stream)

    def _on_process_finished(self, data: dict):
        code = data.get("exit_code", 0)
        is_test = bool(data.get("is_test") or data.get("is_terminal_test"))
        stopped = bool(data.get("stopped"))
        self.bottom_dock.run_finished(code, is_test=is_test, stopped=stopped)
        self.titlebar.set_running(False)
        self.sidebar.tests.set_running(False)
        tone = "success" if code == 0 else "error"
        if not is_test and not stopped:
            self.status_bar.showMessage(f"Process finished (exit {code})", 3000)
            if code != 0:
                self.notifications.notify(f"Process exited with code {code}.", tone)

    def _on_test_finished(self, data: dict):
        ok = bool(data.get("success"))
        duration = data.get("duration_ms", 0.0)
        if ok:
            msg = f"✓ Test passed ({duration:.0f} ms)"
            self.status_bar.showMessage(msg, 4000)
            self.notifications.notify(msg, "success")
        else:
            issue = data.get("issue_summary") or "Test failed"
            fix = data.get("quick_fix") or ""
            msg = f"✗ {issue}" + (f" | Fix: {fix}" if fix else "")
            self.status_bar.showMessage(msg[:140], 6000)
            self.notifications.notify(msg[:220], "error")

    def _on_terminal_test_finished(self, data: dict):
        ok = bool(data.get("passed"))
        if ok:
            msg = f"✓ Terminal OK ({data.get('shell', 'shell')} · {data.get('latency_ms', 0):.1f} ms · 0 popup windows)"
            self.status_bar.showMessage(msg, 4000)
            self.notifications.notify(msg, "success")
        else:
            self.status_bar.showMessage("✗ Terminal self-test reported an issue", 4000)
            self.notifications.notify("Terminal self-test failed — check Output tab.", "error")

    def _on_log_message(self, data: dict):
        msg = data.get("message", "")
        if msg:
            self.status_bar.showMessage(msg, 4000)

    def _on_editor_saved(self, data: dict):
        path = data.get("path_str") or str(data.get("path", ""))
        if path:
            self.center.editor_tabs.mark_saved(path)
            self.status_bar.showMessage(f"Saved {Path(path).name}", 2000)

    def _on_ai_error(self, data: dict):
        self.notifications.notify(data.get("error", "AI request failed."), "error")

    def _on_diagnostics(self, path, diagnostics):
        try:
            self.bottom_dock.set_diagnostics(str(path), diagnostics or [])
        except Exception:
            pass
        n = len(diagnostics or [])
        self.status_bar.set_lsp_status(f"{n} problem{'s' if n != 1 else ''}" if n else "No problems")

    def _on_lsp_started(self, *args):
        self.status_bar.set_lsp_status("LSP ready")

    def _on_lsp_stopped(self, *args):
        self.status_bar.set_lsp_status("LSP stopped")

    def _on_problem_activated(self, path: str, line: int):
        if path:
            self.event_bus.publish(
                "file_open_requested", {"path": path, "line": int(line)})

    def _on_scan_active_code(self):
        path = self.center.editor_tabs.current_path() or "active_buffer.py"
        code = self._active_editor_text()
        n = self.bottom_dock.problems.scan_code(path, code)
        self.bottom_dock._update_problem_tab()
        if n == 0:
            self.status_bar.showMessage("✓ No syntax or code problems found.", 3000)
        else:
            self.status_bar.showMessage(f"⚠ Found {n} problem(s) in {Path(path).name}.", 4000)

    def _on_lsp_clicked(self):
        c = get_design_system().colors
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {c.surface_overlay};
                border: 1px solid {c.border_strong};
                border-radius: 6px;
                padding: 4px;
                color: {c.text_primary};
            }}
            QMenu::item {{
                padding: 5px 18px 5px 12px;
                border-radius: 4px;
                color: {c.text_secondary};
            }}
            QMenu::item:selected {{
                background: {c.accent_muted};
                color: {c.text_primary};
            }}
            QMenu::separator {{
                height: 1px;
                background: {c.border_subtle};
                margin: 4px 6px;
            }}
        """)
        describe = getattr(self.lsp_manager, "describe_state", None)
        state = None
        if callable(describe):
            try:
                state = describe()
            except Exception:
                state = None

        if state is None:
            menu.addAction("Language servers not initialized").setEnabled(False)
        else:
            ws = state.get("workspace")
            header = menu.addAction(f"Workspace: {Path(ws).name}" if ws else "No workspace")
            header.setEnabled(False)
            menu.addSeparator()

            servers = state.get("servers") or []
            if servers:
                for s in servers:
                    dot = "●" if s.get("running") else "○"
                    state_txt = "running" if s.get("running") else "stopped"
                    act = menu.addAction(f"{dot}  {s.get('name', s.get('language'))}  —  {state_txt}")
                    act.setEnabled(False)
            else:
                none_act = menu.addAction("No external servers started")
                none_act.setEnabled(False)

            py = menu.addAction(
                f"{'●' if state.get('python_inprocess') else '○'}  Python (in-process)  —  "
                f"{'available' if state.get('python_inprocess') else 'unavailable'}")
            py.setEnabled(False)

            configured = state.get("configured") or []
            if configured:
                menu.addSeparator()
                cfg = menu.addAction("Configured: " + ", ".join(configured))
                cfg.setEnabled(False)

            if callable(getattr(self.lsp_manager, "shutdown_all", None)):
                menu.addSeparator()
                menu.addAction("Restart language servers", self._restart_lsp)

        menu.addSeparator()
        menu.addAction("Open Problems", self._show_problems)
        menu.exec(QCursor.pos())

    def _restart_lsp(self):
        try:
            self.lsp_manager.shutdown_all()
            self.status_bar.set_lsp_status("restarting…")
            self.notifications.notify("Language servers stopped; they will restart on demand.", "info")
        except Exception:
            pass

    def _show_problems(self):
        self._show_bottom(True)
        try:
            self.bottom_dock.show_problems()
        except Exception:
            pass

    # ── run & smart test actions ──────────────────────────────────────────
    def _active_editor_text(self) -> str:
        editor = self.center.editor_tabs.current_editor()
        if editor is not None:
            try:
                return editor.toPlainText()
            except Exception:
                return ""
        return ""

    def _on_run(self):
        path = self.center.editor_tabs.current_path()
        editor = self.center.editor_tabs.current_editor()
        if path and self._is_unsaved_path(path):
            path = self._save_as(editor)
            if not path:
                return
        elif editor is not None and editor.document().isModified():
            self._save_editor(editor, path)
        if not path:
            path = select_existing_file(self, "Select a file to run", str(Path.home()))
            if not path:
                return
        self.titlebar.set_running(True)
        self.bottom_dock.clear_terminal_problems()
        self._show_bottom(True)
        self.bottom_dock.show_terminal()
        self.event_bus.publish("run_requested", {"file_path": path})

    def _on_quick_test(self):
        """Run 1-click Smart Program Test with randomized auto-detected inputs."""
        self._start_program_test(custom_config={"mode": "auto"})

    def _on_custom_test(self, custom_config: dict):
        """Run Smart Program Test with custom settings from the left Tests panel."""
        self._start_program_test(custom_config=custom_config or {"mode": "auto"})

    def _start_program_test(self, custom_config: dict):
        path = self.center.editor_tabs.current_path()
        editor = self.center.editor_tabs.current_editor()
        code = None
        if editor is not None:
            code = editor.toPlainText()
            if path and not self._is_unsaved_path(path) and editor.document().isModified():
                self._save_editor(editor, path)
        elif not path:
            path = select_existing_file(self, "Select a file to test", str(Path.home()))
            if not path:
                self.sidebar.tests.set_running(False)
                return

        self.titlebar.set_running(True)
        self.bottom_dock.clear_terminal_problems()
        self.bottom_dock.clear_output()
        self.bottom_dock.show_output()
        self._show_bottom(True)
        self.event_bus.publish("test_requested", {
            "file_path": path if (path and not self._is_unsaved_path(path)) else path,
            "code": code,
            "config": custom_config,
        })

    def _on_test_terminal(self):
        """Run the built-in Terminal Diagnostics & Self-Test with zero popup windows."""
        self._show_bottom(True)
        self.bottom_dock.clear_output()
        self.bottom_dock.show_output()
        cwd = getattr(self, "_workspace_root", "") or ""
        self.event_bus.publish("terminal_test_requested", {"cwd": cwd})

    def _on_stop(self):
        self.event_bus.publish("stop_requested", {})
        self.titlebar.set_running(False)
        self.sidebar.tests.set_running(False)

    # ── save ──────────────────────────────────────────────────────────────
    @staticmethod
    def _is_unsaved_path(path: str) -> bool:
        if not path:
            return True
        p = Path(path)
        return not p.is_absolute() or p.name.startswith("untitled")

    def _on_save(self):
        editor = self.center.editor_tabs.current_editor()
        if editor is None:
            return
        path = getattr(editor, "file_path", "") or ""
        if self._is_unsaved_path(path):
            self._save_as(editor)
            return
        self._save_editor(editor, path)

    def _on_save_as(self):
        editor = self.center.editor_tabs.current_editor()
        if editor is not None:
            self._save_as(editor)

    def _save_editor(self, editor, path: str):
        self.event_bus.publish("request_save_file", {"editor": editor, "path": path})

    def _save_as(self, editor) -> str:
        if editor is None:
            return ""
        current = getattr(editor, "file_path", "") or ""
        start = getattr(self, "_workspace_root", "") or str(Path.home())
        suggested = Path(current).name if current else ""
        if self._is_unsaved_path(current):
            suggested = "" if not suggested else suggested
        dest = select_save_file(self, "Save As", start, suggested)
        if not dest:
            return ""
        try:
            self.center.editor_tabs.retarget(editor, dest)
        except Exception:
            editor.file_path = dest
        self._save_editor(editor, dest)
        return dest

    def _on_new_file(self):
        try:
            name = self.center.editor_tabs.next_untitled_name()
        except Exception:
            name = "untitled-1"
        self.center.open_file(name, "", encoding="utf-8", read_only=False)

    def _close_current_tab(self):
        try:
            path = self.center.editor_tabs.current_path()
        except Exception:
            path = ""
        if path:
            self.event_bus.publish("request_close_file", {"path": path})

    def _focus_view(self, view_id: str):
        try:
            self.activity_bar.set_active(view_id)
        except Exception:
            pass
        self.sidebar.set_view(view_id)
        self._show_sidebar(True)

    def _on_current_file_changed(self, path: str):
        fn = getattr(self.center, "set_breadcrumb", None)
        if callable(fn):
            try:
                fn(path or "")
            except Exception:
                pass
        try:
            self.sidebar.run.set_current_file(path or "")
        except Exception:
            pass
        try:
            self.sidebar.tests.set_current_file(path or "")
        except Exception:
            pass

    def _on_breadcrumb_reveal(self, path: str):
        try:
            self.sidebar.explorer.reveal(path, force=True)
        except Exception:
            pass

    def _panel_toast(self, message: str, level: str = "info"):
        try:
            self.notifications.notify(message, level)
        except Exception:
            self.status_bar.showMessage(message, 3000)

    def _on_review_change_set(self, data: dict):
        import threading as _th
        if _th.current_thread() is not _th.main_thread():
            self._ui_marshal.run.emit(lambda d=data: self._on_review_change_set(d))
            return
        change_set = data.get("change_set")
        if change_set is None:
            return
        root = getattr(self, "_workspace_root", "") or str(Path.home())
        try:
            from ui.dialogs.change_review_dialog import ChangeReviewDialog
            dialog = ChangeReviewDialog(
                change_set, root, event_bus=self.event_bus,
                user_prompt=data.get("prompt", ""), parent=self)
            dialog.applied.connect(self._on_change_set_applied)
            dialog.exec()
        except Exception as exc:
            self._panel_toast(f"Could not open change review: {exc}", "error")

    def _on_change_set_applied(self, result):
        ok = getattr(result, "success", False)
        applied = getattr(result, "applied_count", 0)
        if ok:
            self._panel_toast(f"Applied {applied} change(s).", "success")
        else:
            errs = "; ".join(getattr(result, "errors", []) or [])[:200]
            self._panel_toast(f"Some changes failed: {errs}", "error")
        try:
            self.sidebar.git.refresh()
        except Exception:
            pass

    def _on_diff_requested(self, title: str, diff_text: str):
        try:
            self.center.open_diff(title, diff_text)
        except Exception:
            try:
                self.center.open_file(title, diff_text, read_only=True)
            except Exception:
                pass

    def _open_workspace(self, path: str):
        if path:
            self.event_bus.publish("request_open_workspace", {"path": path})

    def open_folder(self):
        start = str(Path.home())
        folder = select_existing_directory(self, "Open Folder", start)
        if folder:
            self._open_workspace(folder)

    def _on_clone_repo(self):
        url, ok = QInputDialog.getText(self, "Clone Repository", "Repository URL:")
        if not ok or not url.strip():
            return
        url = url.strip()
        parent = select_existing_directory(
            self, "Choose a destination folder", str(Path.home()))
        if not parent:
            return
        name = url.rstrip("/").rsplit("/", 1)[-1]
        if name.endswith(".git"):
            name = name[:-4]
        name = name or "repository"
        dest = str(Path(parent) / name)
        if Path(dest).exists():
            self._panel_toast(f"Destination already exists: {name}", "error")
            return

        self._show_bottom(True)
        self.bottom_dock.show_terminal()
        self.bottom_dock.append_output(f"$ git clone {url} {dest}\n", "stdout")

        proc = QProcess(self)
        configure_qprocess_no_window(proc)
        self._clone_proc = proc
        proc.setWorkingDirectory(parent)
        proc.readyReadStandardOutput.connect(
            lambda: self.bottom_dock.append_output(
                bytes(proc.readAllStandardOutput()).decode("utf-8", "replace"), "stdout"))
        proc.readyReadStandardError.connect(
            lambda: self.bottom_dock.append_output(
                bytes(proc.readAllStandardError()).decode("utf-8", "replace"), "stderr"))
        proc.errorOccurred.connect(
            lambda _e: self._panel_toast("Could not start git — is it installed?", "error"))
        proc.finished.connect(lambda code, _status: self._on_clone_finished(code, dest, name))
        self._panel_toast(f"Cloning {name}…", "info")
        proc.start("git", ["clone", "--progress", url, dest])

    def _on_clone_finished(self, code: int, dest: str, name: str):
        if code == 0 and Path(dest).exists():
            self._panel_toast(f"Cloned {name} — opening workspace", "success")
            self._open_workspace(dest)
        else:
            self._panel_toast(f"Clone failed ({name}) — see terminal", "error")

    def open_command_palette(self, mode: str = "command"):
        try:
            files = self.center.editor_tabs.open_paths()
        except Exception:
            files = []
        self.command_palette.set_files(files)
        self.command_palette.open_palette(mode)

    def _command_list(self):
        return [
            ("run", "Run: Run Current File"),
            ("test_file", "Test: Quick Test Current File (Smart Auto-Inputs)"),
            ("open_tests", "Test: Open Program & Terminal Tests Panel"),
            ("test_terminal", "Terminal: Test Terminal Diagnostics"),
            ("stop", "Run: Stop"),
            ("save", "File: Save"),
            ("save_as", "File: Save As…"),
            ("new_file", "File: New File"),
            ("open_folder", "File: Open Folder…"),
            ("toggle_sidebar", "View: Toggle Sidebar"),
            ("toggle_terminal", "View: Toggle Terminal"),
            ("toggle_ai", "View: Toggle AI Workspace"),
            ("settings", "Preferences: Open Settings"),
            ("settings_theme", "Preferences: Colour Theme"),
            ("settings_keyboard", "Preferences: Keyboard Shortcuts"),
            ("settings_providers", "Preferences: Providers & API Keys"),
            ("git_push", "Git: Push"),
            ("git_pull", "Git: Pull"),
            ("git_clone", "Git: Clone Repository…"),
            ("git_source_control", "Git: Open GitHub / Git"),
        ]

    def _run_command_id(self, command_id: str):
        {
            "run": self._on_run,
            "test_file": self._on_quick_test,
            "open_tests": lambda: self._focus_view("tests"),
            "test_terminal": self._on_test_terminal,
            "stop": self._on_stop,
            "save": self._on_save,
            "save_as": self._on_save_as,
            "new_file": self._on_new_file,
            "open_folder": self.open_folder,
            "toggle_sidebar": self.toggle_sidebar,
            "toggle_terminal": self.toggle_bottom,
            "toggle_ai": self.toggle_ai,
            "settings": self.open_settings,
            "settings_theme": lambda: self.open_settings("appearance"),
            "settings_keyboard": lambda: self.open_settings("keyboard"),
            "settings_providers": lambda: self.open_settings("providers"),
            "git_push": self._git_push,
            "git_pull": self._git_pull,
            "git_clone": self._on_clone_repo,
            "git_source_control": lambda: self._focus_view("git"),
        }.get(command_id, lambda: None)()

    def _git_push(self):
        self._show_bottom(True)
        self.sidebar.git.push()

    def _git_pull(self):
        self._show_bottom(True)
        self.sidebar.git.pull()

    # ── view toggles ──────────────────────────────────────────────────────
    def _on_view_changed(self, view_id: str):
        self.sidebar.set_view(view_id)
        self._show_sidebar(True)

    def _show_sidebar(self, visible: bool):
        visible = bool(visible)
        if not visible and self._sidebar_visible:
            cur_w = self.sidebar.width()
            if cur_w >= SB.MIN_WIDTH:
                self._last_sidebar_width = cur_w
        self._sidebar_visible = visible
        self.sidebar.setVisible(visible)
        try:
            sizes = list(self.main_split.sizes())
            if len(sizes) >= 3:
                if not visible:
                    reclaimed = sizes[0]
                    self.main_split.setSizes([0, sizes[1] + reclaimed, sizes[2]])
                else:
                    restore_w = max(SB.MIN_WIDTH, getattr(self, "_last_sidebar_width", SB.DEFAULT_WIDTH))
                    if sizes[0] < SB.MIN_WIDTH:
                        new_center = max(400, sizes[1] - restore_w)
                        self.main_split.setSizes([restore_w, new_center, sizes[2]])
        except Exception:
            pass
        try:
            self.activity_bar.set_sidebar_visible(visible)
        except Exception:
            pass
        try:
            self.titlebar.set_sidebar_visible(visible)
        except Exception:
            pass

    def toggle_sidebar(self):
        self._show_sidebar(not self._sidebar_visible)

    def _show_bottom(self, visible: bool):
        self._bottom_visible = visible
        self.bottom_dock.setVisible(visible)

    def toggle_bottom(self):
        self._show_bottom(not self._bottom_visible)

    def _show_ai(self, visible: bool):
        self._ai_visible = visible
        self.ai_workspace.setVisible(visible)
        try:
            self.notifications.resize_to_parent()
        except Exception:
            pass

    def toggle_ai(self, *args):
        self._show_ai(not self._ai_visible)

    # ── settings ──────────────────────────────────────────────────────────
    def open_settings(self, page: str = "", *args):
        from ui.dialogs.settings_dialog import SettingsDialog

        if getattr(self, "_settings_dialog", None) is None:
            registry = getattr(self.provider_manager, "registry", None)
            dlg = SettingsDialog(
                self,
                provider_registry=registry,
                provider_manager=self.provider_manager,
                current_theme=get_design_system().theme,
            )
            dlg.theme_selected.connect(self._on_theme_selected)
            dlg.setting_changed.connect(self._on_setting_changed)
            self._settings_dialog = dlg

        dlg = self._settings_dialog
        dlg.set_current_theme(get_design_system().theme)
        if isinstance(page, str) and page:
            dlg.show_page(page)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _on_setting_changed(self, category: str, key: str, value):
        self.event_bus.publish("settings_changed", {
            "category": category, "key": key, "value": value,
        })
        if category == "terminal":
            fn = getattr(self.bottom_dock, "apply_terminal_settings", None)
            if callable(fn):
                try:
                    fn()
                except Exception:
                    pass
        elif category == "appearance":
            self.refresh_theme()
            self._apply_editor_settings()
        elif category == "editor":
            self._apply_editor_settings()
        elif category == "general" and key == "theme":
            self._on_theme_selected(str(value))
        elif category == "workspace":
            fn = getattr(self.sidebar.explorer, "apply_workspace_settings", None)
            if callable(fn):
                try:
                    fn()
                except Exception:
                    pass

    def _apply_editor_settings(self):
        fn = getattr(self.center, "apply_editor_settings", None)
        if callable(fn):
            try:
                fn()
            except Exception:
                pass

    # ── theme ─────────────────────────────────────────────────────────────
    def _on_theme_selected(self, theme_name: str):
        applied = False
        if self.theme_manager is not None:
            for meth in ("apply_theme", "set_theme", "switch_theme"):
                fn = getattr(self.theme_manager, meth, None)
                if callable(fn):
                    try:
                        fn(theme_name)
                        applied = True
                        break
                    except Exception:
                        pass
        if not applied:
            try:
                ds = get_design_system()
                ds.set_theme(theme_name)
                from PySide6.QtWidgets import QApplication
                app = QApplication.instance()
                if app is not None:
                    app.setStyleSheet(ds.get_stylesheet("global"))
            except Exception:
                pass
        try:
            from ui.settings_manager import get_settings_manager
            get_settings_manager().set("general", "theme", get_design_system().theme)
        except Exception:
            pass
        self.titlebar.set_active_theme(get_design_system().theme)
        self.refresh_theme()

    def refresh_theme(self):
        for w in (self.ai_workspace, self.center, self.sidebar, self.bottom_dock,
                  self.titlebar, self.activity_bar, self.status_bar,
                  self.command_palette, self.notifications,
                  getattr(self, "_settings_dialog", None)):
            fn = getattr(w, "refresh_theme", None)
            if callable(fn):
                try:
                    fn()
                except Exception:
                    pass
        for root in (self, self.command_palette, getattr(self, "_settings_dialog", None)):
            if root is not None:
                try:
                    restyle_atoms(root)
                except Exception:
                    pass

    # ── overlay positioning ───────────────────────────────────────────────
    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            self.notifications.resize_to_parent()
        except Exception:
            pass

