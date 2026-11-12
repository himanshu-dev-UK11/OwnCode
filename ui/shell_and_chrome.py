"""
Consolidated Module: ui.shell_and_chrome

Combines: ui.shell.titlebar, ui.shell.activity_bar, ui.shell.status_bar, ui.shell.toolbar, ui.panels.notifications
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['ui.shell.titlebar', 'ui.shell.activity_bar', 'ui.shell.status_bar', 'ui.shell.toolbar', 'ui.panels.notifications']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ui.shell.titlebar (ui/shell/titlebar.py)
# ============================================================================
"""
Title Bar — v3.2 (unified chrome with Quick Test button & active Sidebar toggle)

A single top strip that hosts: app menu and identity, primary file actions
(toggle sidebar, open folder, new file, save), a click-to-open command-palette
search, and a right-aligned cluster — Run / Quick Test / Stop, theme picker,
and layout toggles.
"""

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QToolButton, QMenu,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QActionGroup

from ui.design_system import (get_design_system, Titlebar, Spacing, Radius,
                              FontSize, FontWeight, THEME_META, list_themes)
from ui.widgets.controls import IconButton, TextButton, vline


class TitleBar(QFrame):

    # identity / navigation
    menu_requested = Signal()
    command_palette_requested = Signal()
    notifications_requested = Signal()
    # theme
    theme_selected = Signal(str)
    all_themes_requested = Signal()
    # file / run / test actions
    run_requested = Signal()
    test_requested = Signal()
    stop_requested = Signal()
    save_requested = Signal()
    new_file_requested = Signal()
    open_folder_requested = Signal()
    # layout toggles
    toggle_sidebar = Signal()
    toggle_terminal = Signal()
    ai_toggled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(Titlebar.HEIGHT)
        self._theme_actions: dict[str, object] = {}
        self._running = False
        self._sidebar_open = True
        self._build()
        self._apply_style()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(Spacing.sm, 0, Spacing.sm, 0)
        lay.setSpacing(Spacing.xs)

        # ── identity ─────────────────────────────────────────────────
        self._menu_btn = IconButton("menu", "Main Menu & Command Palette (Ctrl+Shift+P)", size=30, icon_size=18)
        self._menu_btn.clicked.connect(self.menu_requested.emit)
        lay.addWidget(self._menu_btn)

        self._logo_lbl = QLabel("OC")
        self._logo_lbl.setObjectName("AppLogoBadge")
        self._logo_lbl.setFixedSize(22, 22)
        self._logo_lbl.setToolTip("OwnCode IDE")
        try:
            from pathlib import Path as _Path
            from PySide6.QtGui import QPixmap
            logo_p = _Path(__file__).resolve().parent.parent / "docs & resources" / "owncode_logo.png"
            if logo_p.exists():
                pm = QPixmap(str(logo_p))
                if not pm.isNull():
                    self._logo_lbl.setPixmap(
                        pm.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    )
        except Exception:
            pass
        lay.addWidget(self._logo_lbl)

        self._app = QLabel("OwnCode")
        self._app.setObjectName("AppName")
        self._app.setToolTip("OwnCode IDE")
        lay.addWidget(self._app)

        self._sep = QLabel("—")
        self._sep.setObjectName("TitleSep")
        lay.addWidget(self._sep)

        self._workspace = QLabel("No workspace")
        self._workspace.setObjectName("WorkspaceName")
        self._workspace.setToolTip("Active Workspace Folder")
        lay.addWidget(self._workspace)

        lay.addSpacing(Spacing.sm)
        lay.addWidget(vline())
        lay.addSpacing(Spacing.xs)

        # ── file & sidebar actions ───────────────────────────────────
        self._sidebar_btn = IconButton(
            "collapse",
            "Hide / Show Left Sidebar Panel  (Ctrl+B)",
            size=30,
            icon_size=17,
            checkable=True,
        )
        self._sidebar_btn.setChecked(True)
        self._sidebar_btn.clicked.connect(self.toggle_sidebar.emit)
        lay.addWidget(self._sidebar_btn)

        self._open_btn = IconButton("folder", "Open Folder  (Ctrl+O)", size=30, icon_size=17)
        self._open_btn.clicked.connect(self.open_folder_requested.emit)
        lay.addWidget(self._open_btn)

        self._new_btn = IconButton("plus", "New File  (Ctrl+N)", size=30, icon_size=17)
        self._new_btn.clicked.connect(self.new_file_requested.emit)
        lay.addWidget(self._new_btn)

        self._save_btn = IconButton("file", "Save  (Ctrl+S)", size=30, icon_size=17)
        self._save_btn.clicked.connect(self.save_requested.emit)
        lay.addWidget(self._save_btn)

        lay.addStretch(1)

        # ── command palette trigger ──────────────────────────────────
        self._palette = QLineEdit()
        self._palette.setObjectName("PaletteTrigger")
        self._palette.setReadOnly(True)
        self._palette.setPlaceholderText("Search files and commands…   Ctrl+P")
        self._palette.setToolTip("Click to search workspace files (Ctrl+P) or run IDE commands (Ctrl+Shift+P)")
        self._palette.setFixedWidth(300)
        self._palette.setCursor(Qt.PointingHandCursor)
        self._palette.mousePressEvent = lambda e: self.command_palette_requested.emit()
        lay.addWidget(self._palette)

        lay.addStretch(1)

        # ── run / quick test / stop (right cluster) ──────────────────
        self._run_btn = TextButton("▶ Run", icon_name="", variant="primary")
        self._run_btn.setObjectName("RunButton")
        self._run_btn.setToolTip("Run current file  (F5)")
        self._run_btn.setFixedHeight(28)
        self._run_btn.clicked.connect(self.run_requested.emit)
        lay.addWidget(self._run_btn)

        self._test_btn = TextButton("⚗ Test", icon_name="")
        self._test_btn.setObjectName("TestButton")
        self._test_btn.setToolTip(
            "Quick Test: Auto-detect required inputs, pass random dummy values, and verify program  (F6)"
        )
        self._test_btn.setFixedHeight(28)
        self._test_btn.clicked.connect(self.test_requested.emit)
        lay.addWidget(self._test_btn)

        self._stop_btn = IconButton("stop", "Stop Running Program (Shift+F5)", size=30, icon_size=16)
        self._stop_btn.clicked.connect(self.stop_requested.emit)
        self._stop_btn.setEnabled(False)
        lay.addWidget(self._stop_btn)

        lay.addSpacing(Spacing.xs)
        lay.addWidget(vline())
        lay.addSpacing(Spacing.xs)

        # ── theme dropdown ───────────────────────────────────────────
        self._theme_btn = QToolButton()
        self._theme_btn.setObjectName("ThemeButton")
        self._theme_btn.setCursor(Qt.PointingHandCursor)
        self._theme_btn.setToolTip("Change theme")
        self._theme_btn.setPopupMode(QToolButton.InstantPopup)
        self._theme_btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self._theme_btn.setFixedHeight(26)
        self._theme_btn.setMenu(self._build_theme_menu())
        lay.addWidget(self._theme_btn)

        lay.addSpacing(Spacing.xs)
        lay.addWidget(vline())
        lay.addSpacing(Spacing.xs)

        # ── layout toggles ───────────────────────────────────────────
        self._term_btn = IconButton("terminal", "Toggle Terminal  (Ctrl+`)", size=30, icon_size=17)
        self._term_btn.clicked.connect(self.toggle_terminal.emit)
        lay.addWidget(self._term_btn)

        self._bell = IconButton("bell", "Notifications", size=30, icon_size=18)
        self._bell.clicked.connect(self.notifications_requested.emit)
        lay.addWidget(self._bell)

        self._ai = IconButton("ai", "Toggle AI Workspace  (Ctrl+Shift+A)", size=30, icon_size=18)
        self._ai.clicked.connect(self.ai_toggled.emit)
        lay.addWidget(self._ai)

        self.set_active_theme(get_design_system().theme)

    def _build_theme_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.setObjectName("ThemeMenu")
        group = QActionGroup(menu)
        group.setExclusive(True)
        self._theme_actions.clear()

        for section in ("Light", "Dark"):
            menu.addSection(section)
            for info in list_themes(section):
                act = menu.addAction(info.label)
                act.setCheckable(True)
                act.setToolTip(info.blurb)
                act.triggered.connect(lambda _=False, n=info.name: self._on_theme_chosen(n))
                group.addAction(act)
                self._theme_actions[info.name] = act

        menu.addSeparator()
        more = menu.addAction("All appearance settings…")
        more.triggered.connect(self.all_themes_requested.emit)
        return menu

    # ------------------------------------------------------------------ #
    #  Public API (called by MainWindow)                                   #
    # ------------------------------------------------------------------ #
    def set_workspace_name(self, name: str):
        self._workspace.setText(name or "No workspace")

    def set_sidebar_visible(self, visible: bool):
        self._sidebar_open = bool(visible)
        self._sidebar_btn.blockSignals(True)
        self._sidebar_btn.setChecked(self._sidebar_open)
        self._sidebar_btn.blockSignals(False)
        c = get_design_system().colors
        self._sidebar_btn.refresh_icon(c.accent if self._sidebar_open else c.text_muted)

    def set_running(self, running: bool):
        self._running = running
        self._run_btn.setEnabled(not running)
        self._test_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)

    def set_active_theme(self, theme: str):
        info = THEME_META.get(theme)
        label = info.label if info else 'Paper Ink'
        self._theme_btn.setText(label)
        act = self._theme_actions.get(theme)
        if act is not None:
            act.setChecked(True)

    def _on_theme_chosen(self, theme: str):
        self.set_active_theme(theme)
        self.theme_selected.emit(theme)

    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #TitleBar {{
                background-color: {c.canvas};
                border-bottom: 1px solid {c.border};
            }}
            #AppLogoBadge {{
                background: {c.accent};
                color: {c.text_on_accent};
                border-radius: 5px;
                font-family: "Georgia", serif;
                font-weight: 700;
                font-size: 11px;
            }}
            #AppName {{ font-weight: 700; color: {c.text_primary}; }}
            #TitleSep {{ color: {c.text_faint}; }}
            #WorkspaceName {{
                background: {c.surface_raised};
                border: 1px solid {c.border};
                border-radius: 4px;
                padding: 2px 8px;
                color: {c.text_muted};
                font-family: "JetBrains Mono", "Cascadia Code", Consolas, monospace;
                font-size: {FontSize.tiny}px;
                font-weight: 500;
            }}
            #PaletteTrigger {{
                background: {c.surface_inset};
                border: 1px solid {c.border};
                border-radius: {Radius.pill}px;
                padding: 4px 14px;
                color: {c.text_muted};
                font-size: {FontSize.small}px;
            }}
            #PaletteTrigger:hover {{ border-color: {c.border_strong}; }}
            #ThemeButton {{
                background: transparent;
                color: {c.text_muted};
                border: 1px solid {c.border};
                border-radius: {Radius.pill}px;
                padding: 2px 12px;
                font-size: {FontSize.tiny}px;
                font-weight: {FontWeight.medium};
            }}
            #ThemeButton:hover {{
                color: {c.text_primary};
                border-color: {c.border_strong};
            }}
            #ThemeButton::menu-indicator {{ image: none; width: 0; }}
            #ThemeMenu {{
                background: {c.surface_overlay};
                border: 1px solid {c.border};
                border-radius: {Radius.md}px;
                padding: 4px;
                color: {c.text_primary};
            }}
            #ThemeMenu::item {{
                padding: 5px 26px 5px 22px;
                border-radius: {Radius.sm}px;
            }}
            #ThemeMenu::item:selected {{
                background: {c.accent_muted};
                color: {c.text_primary};
            }}
            #ThemeMenu::separator {{
                height: 1px;
                background: {c.border_subtle};
                margin: 4px 8px;
            }}
        """)
        if self._theme_btn.menu() is not None:
            self._theme_btn.menu().setStyleSheet(f"""
                QMenu {{
                    background: {c.surface_overlay};
                    border: 1px solid {c.border_strong};
                    border-radius: {Radius.md}px;
                    padding: 4px;
                    color: {c.text_primary};
                }}
                QMenu::item {{
                    padding: 5px 26px 5px 22px;
                    border-radius: {Radius.sm}px;
                    color: {c.text_secondary};
                }}
                QMenu::item:selected {{
                    background: {c.accent_muted};
                    color: {c.text_primary};
                }}
                QMenu::separator {{
                    height: 1px;
                    background: {c.border_subtle};
                    margin: 4px 8px;
                }}
            """)
        self.set_sidebar_visible(self._sidebar_open)

    def refresh_theme(self):
        self._apply_style()


# ============================================================================
# SECTION: ui.shell.activity_bar (ui/shell/activity_bar.py)
# ============================================================================
"""
Activity Bar — v3.2

The vertical rail on the far left. Switches the primary sidebar view, supports
1-click collapse/expand when clicking the active tab (so users can hide the
sidebar panel and leave only the icon rail visible), and draws a crisp 1px
right border separating the rail from the sidebar/editor.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QButtonGroup, QToolButton, QSizePolicy
from PySide6.QtCore import Qt, QSize, Signal

from ui.design_system import (get_design_system, ActivityBar as AB, Spacing,
                              FontSize, FontWeight)
from ui.widgets.controls import IconButton
from ui.widgets.icons import icon


class _RailButton(QToolButton):
    """A full-width rail destination: icon over a small caption, checkable."""

    def __init__(self, name: str, label: str, tooltip: str = "", parent=None):
        super().__init__(parent)
        self._name = name
        self._icon_px = AB.ICON
        self._icon_color: str | None = None
        self.setProperty("rail", "true")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setText(label)
        if tooltip:
            self.setToolTip(tooltip)
        self.setIconSize(QSize(AB.ICON, AB.ICON))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(AB.RAIL_BUTTON)
        self.refresh_icon()

    def refresh_icon(self, color: str | None = None):
        if color is not None:
            self._icon_color = color
        self.setIcon(icon(self._name, size=self._icon_px, color=self._icon_color))


class ActivityBar(QFrame):

    view_changed = Signal(str)          # primary sidebar view id
    sidebar_toggled = Signal()          # emitted when clicking the already-active view to collapse/expand
    ai_toggled = Signal()               # request AI panel toggle
    settings_requested = Signal()

    # (view id, icon name, tooltip, caption)
    PRIMARY = [
        ("explorer", "explorer", "Explorer (Click again to hide sidebar · Ctrl+B)", "Explorer"),
        ("search", "search", "Search (Ctrl+Shift+F)", "Search"),
        ("git", "git", "GitHub / Git (Ctrl+Shift+G)", "GitHub"),
        ("run", "debug", "Run & Debug", "Run"),
        ("tests", "flask", "Program & Terminal Tests (Ctrl+Shift+T)", "Tests"),
        ("tasks", "tasks", "Tasks", "Tasks"),
        ("memory", "memory", "Project Memory", "Memory"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ActivityBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(AB.WIDTH)
        self._buttons: dict[str, _RailButton] = {}
        self._current = "explorer"
        self._sidebar_open = True
        self._build()
        self._apply_style()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, Spacing.sm, 1, Spacing.md)
        lay.setSpacing(Spacing.xxs)

        self._group = QButtonGroup(self)
        self._group.setExclusive(False)

        for view_id, icon_name, tip, caption in self.PRIMARY:
            btn = _RailButton(icon_name, caption, tip)
            btn.clicked.connect(lambda _=False, v=view_id: self._on_rail_clicked(v))
            self._group.addButton(btn)
            self._buttons[view_id] = btn
            lay.addWidget(btn)

        lay.addStretch(1)

        self._ai_btn = IconButton("ai", "AI Workspace  (Ctrl+Shift+A)",
                                  size=AB.BUTTON, icon_size=AB.ICON)
        self._ai_btn.clicked.connect(self.ai_toggled.emit)
        lay.addWidget(self._ai_btn, 0, Qt.AlignHCenter)

        self._settings_btn = IconButton("settings", "Settings  (Ctrl+,)",
                                        size=AB.BUTTON, icon_size=AB.ICON)
        self._settings_btn.clicked.connect(self.settings_requested.emit)
        lay.addWidget(self._settings_btn, 0, Qt.AlignHCenter)

        self._sync_checked_state()

    def _on_rail_clicked(self, view_id: str):
        """
        VS Code style toggle:
        - Clicking the already-active tab while the sidebar is open collapses the sidebar.
        - Clicking any tab while collapsed (or clicking a different tab) opens that tab.
        """
        if self._sidebar_open and view_id == self._current:
            self._sidebar_open = False
            self._sync_checked_state()
            self.sidebar_toggled.emit()
            return

        self._current = view_id
        self._sidebar_open = True
        self._sync_checked_state()
        self.view_changed.emit(view_id)

    def set_active(self, view_id: str, sidebar_open: bool = True):
        if view_id in self._buttons:
            self._current = view_id
            self._sidebar_open = sidebar_open
            self._sync_checked_state()

    def set_sidebar_visible(self, visible: bool):
        """Sync rail button checked highlight when sidebar visibility changes externally."""
        self._sidebar_open = bool(visible)
        self._sync_checked_state()

    def _sync_checked_state(self):
        for vid, btn in self._buttons.items():
            btn.blockSignals(True)
            btn.setChecked(bool(self._sidebar_open and vid == self._current))
            btn.blockSignals(False)
        self._refresh_icons()

    def current_view(self) -> str:
        return self._current

    def _refresh_icons(self):
        c = get_design_system().colors
        for vid, btn in self._buttons.items():
            btn.refresh_icon(c.text_primary if btn.isChecked() else c.text_muted)
        for btn in (getattr(self, "_ai_btn", None), getattr(self, "_settings_btn", None)):
            if btn is not None:
                btn.refresh_icon(c.text_muted)

    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #ActivityBar {{
                background-color: {c.canvas};
                border-right: 1px solid {c.border};
            }}
            #ActivityBar QToolButton {{
                border: none;
                border-radius: {Spacing.md}px;
                background: transparent;
            }}
            #ActivityBar QToolButton:hover {{ background: {c.surface_overlay}; }}
            #ActivityBar QToolButton[rail="true"] {{
                border-radius: 0px;
                border-left: 3px solid transparent;
                color: {c.text_muted};
                padding: 5px 0 4px 0;
                font-size: {FontSize.micro}px;
                font-weight: {FontWeight.medium};
            }}
            #ActivityBar QToolButton[rail="true"]:hover {{
                background: {c.surface_overlay};
                color: {c.text_primary};
            }}
            #ActivityBar QToolButton[rail="true"]:checked {{
                background: {c.surface_high};
                color: {c.text_primary};
                border-left: 3px solid {c.accent};
            }}
        """)
        self._refresh_icons()

    def refresh_theme(self):
        self._apply_style()
        self._refresh_icons()


# ============================================================================
# SECTION: ui.shell.status_bar (ui/shell/status_bar.py)
# ============================================================================
"""
Status Bar — v2.0

The thin bottom strip. Provides `showMessage(text, timeout=0)` (the exact API
main.py calls) plus segmented indicators for git branch, language, LSP status,
cursor position, and encoding.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer, Signal

from ui.design_system import get_design_system, StatusBar as SB, Spacing, FontSize


class _Segment(QLabel):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignVCenter)
        self.setContentsMargins(Spacing.md, 0, Spacing.md, 0)


class _ClickableSegment(_Segment):
    """A status segment that behaves like a button (pointer cursor + click)."""

    clicked = Signal()

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class StatusBar(QWidget):
    """Bottom status strip with a main message region and right-side segments."""

    lsp_clicked = Signal()   # the LSP segment was clicked (show server state)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusBar")
        self.setFixedHeight(SB.HEIGHT)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._clear_message)
        self._persistent = "Ready"
        self._build()
        self._apply_style()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 0, 8, 0)
        lay.setSpacing(0)

        self._message = _Segment("Ready")
        self._message.setObjectName("StatusMessage")
        self._message.setToolTip("Current IDE Status Message")
        lay.addWidget(self._message)

        self._status_sep = _Segment("·")
        self._status_sep.setObjectName("StatusSep")
        lay.addWidget(self._status_sep)

        self._lsp = _ClickableSegment("LSP: idle")
        self._lsp.setObjectName("StatusLsp")
        self._lsp.setToolTip("Language Server Status — click for details")
        self._lsp.clicked.connect(self.lsp_clicked.emit)
        lay.addWidget(self._lsp)

        lay.addStretch(1)

        self._git = _Segment("")
        self._git.setObjectName("Seg")
        self._git.setToolTip("Active Git Branch")
        self._lang = _Segment("")
        self._lang.setObjectName("Seg")
        self._lang.setToolTip("Active File Programming Language")
        
        self._vram = _Segment("VRAM 5037 MB")
        self._vram.setObjectName("StatusVram")
        self._vram.setToolTip("Local VRAM Usage")

        self._cursor = _Segment("Ln 1, Col 1")
        self._cursor.setObjectName("Seg")
        self._cursor.setToolTip("Current Cursor Position (Line, Column)")
        
        self._encoding = _Segment("UTF-8")
        self._encoding.setObjectName("Seg")
        self._encoding.setToolTip("Active File Character Encoding")

        for seg in (self._git, self._lang, self._vram, self._cursor, self._encoding):
            lay.addWidget(seg)

        self._git.hide()
        self._lang.hide()

    def set_vram_info(self, text: str):
        if hasattr(self, "_vram"):
            self._vram.setText(text)

    # -- main.py-compatible API ---------------------------------------------
    def showMessage(self, text: str, timeout: int = 0):
        self._message.setText(text)
        self._timer.stop()
        if timeout and timeout > 0:
            self._timer.start(int(timeout))

    def set_persistent(self, text: str):
        self._persistent = text or "Ready"
        if not self._timer.isActive():
            self._message.setText(self._persistent)

    def _clear_message(self):
        self._message.setText(self._persistent)

    # -- segment setters -----------------------------------------------------
    def set_git_branch(self, branch: str):
        if branch:
            self._git.setText(f"⎇ {branch}")
            self._git.show()
        else:
            self._git.hide()

    def set_language(self, language: str):
        if language:
            self._lang.setText(language)
            self._lang.show()
        else:
            self._lang.hide()

    def set_lsp_status(self, status: str):
        self._lsp.setText(f"LSP: {status}")

    def set_cursor(self, line: int, col: int):
        self._cursor.setText(f"Ln {line}, Col {col}")

    def set_encoding(self, encoding: str):
        self._encoding.setText(encoding or "UTF-8")

    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #StatusBar {{
                background: {c.canvas};
                border-top: 1px solid {c.border_subtle};
            }}
            #StatusBar QLabel {{
                color: {c.text_muted};
                font-size: {FontSize.tiny}px;
            }}
            #StatusMessage {{ color: {c.text_secondary}; }}
            #Seg:hover {{ background: {c.surface_overlay}; }}
        """)

    def refresh_theme(self):
        self._apply_style()


# ============================================================================
# SECTION: ui.shell.toolbar (ui/shell/toolbar.py)
# ============================================================================
"""
Tool Bar — DEPRECATED (superseded by the unified TitleBar)

Kept in sync with TitleBar signals (`run_requested`, `test_requested`, `stop_requested`).
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal

from ui.design_system import get_design_system, Toolbar, Spacing, Radius
from ui.widgets.controls import IconButton, TextButton, vline


class ToolBar(QWidget):

    run_requested = Signal()
    test_requested = Signal()
    stop_requested = Signal()
    save_requested = Signal()
    new_file_requested = Signal()
    open_folder_requested = Signal()
    toggle_sidebar = Signal()
    toggle_terminal = Signal()
    toggle_ai = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToolBar")
        self.setFixedHeight(Toolbar.HEIGHT)
        self._running = False
        self._build()
        self._apply_style()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(Spacing.md, Spacing.sm, Spacing.md, Spacing.sm)
        lay.setSpacing(Spacing.sm)

        self._sidebar_btn = IconButton("collapse", "Toggle Sidebar  (Ctrl+B)", size=30, icon_size=17)
        self._sidebar_btn.clicked.connect(self.toggle_sidebar.emit)
        lay.addWidget(self._sidebar_btn)

        self._open_btn = IconButton("folder", "Open Folder", size=30, icon_size=17)
        self._open_btn.clicked.connect(self.open_folder_requested.emit)
        lay.addWidget(self._open_btn)

        self._new_btn = IconButton("plus", "New File", size=30, icon_size=17)
        self._new_btn.clicked.connect(self.new_file_requested.emit)
        lay.addWidget(self._new_btn)

        self._save_btn = IconButton("file", "Save  (Ctrl+S)", size=30, icon_size=17)
        self._save_btn.clicked.connect(self.save_requested.emit)
        lay.addWidget(self._save_btn)

        lay.addWidget(vline())

        # Breadcrumb
        self._crumb = QLabel("No file open")
        self._crumb.setObjectName("Breadcrumb")
        self._crumb.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self._crumb)

        lay.addStretch(1)

        self._run_btn = TextButton("Run", icon_name="run", variant="primary")
        self._run_btn.setToolTip("Run current file  (F5)")
        self._run_btn.clicked.connect(self._on_run)
        lay.addWidget(self._run_btn)

        self._test_btn = TextButton("Test", icon_name="flask")
        self._test_btn.setToolTip("Quick Test current file with smart random inputs  (F6)")
        self._test_btn.clicked.connect(self._on_test)
        lay.addWidget(self._test_btn)

        self._stop_btn = IconButton("stop", "Stop", size=30, icon_size=16)
        self._stop_btn.clicked.connect(self._on_stop)
        self._stop_btn.setEnabled(False)
        lay.addWidget(self._stop_btn)

        lay.addWidget(vline())

        self._term_btn = IconButton("terminal", "Toggle Terminal  (Ctrl+`)", size=30, icon_size=17)
        self._term_btn.clicked.connect(self.toggle_terminal.emit)
        lay.addWidget(self._term_btn)

        self._ai_btn = IconButton("ai", "Toggle AI Workspace", size=30, icon_size=17)
        self._ai_btn.clicked.connect(self.toggle_ai.emit)
        lay.addWidget(self._ai_btn)

    def _on_run(self):
        self.run_requested.emit()

    def _on_test(self):
        self.test_requested.emit()

    def _on_stop(self):
        self.stop_requested.emit()

    def set_running(self, running: bool):
        self._running = running
        self._run_btn.setEnabled(not running)
        self._test_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)

    def set_breadcrumb(self, text: str):
        self._crumb.setText(text or "No file open")

    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #ToolBar {{
                background: {c.surface};
                border-bottom: 1px solid {c.border_subtle};
            }}
            #Breadcrumb {{
                color: {c.text_muted};
                padding: 2px 8px;
                background: {c.surface_inset};
                border-radius: {Radius.sm}px;
            }}
        """)

    def refresh_theme(self):
        self._apply_style()


# ============================================================================
# SECTION: ui.panels.notifications (ui/panels/notifications.py)
# ============================================================================
"""
Notifications — v3.0

Non-blocking, professional toast notification cards:
- Strictly sized to the exact bounding box of active toast cards (never covers
  the full window height or blocks clicks in the AI Workspace / Editor).
- Anchored cleanly above the status bar and to the left of the AI Workspace
  when the AI panel is open, so the chat input and Send button are never covered.
- Automatically replaces transient "Starting…" / "Loading…" progress toasts
  when their completion toast arrives, preventing overlapping stacks.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontMetrics

from ui.design_system import get_design_system, Spacing, Radius, FontSize


class _Toast(QFrame):
    """Single compact, non-clipping notification card."""

    CARD_WIDTH = 320
    TEXT_WIDTH = 228

    _TONE_META = {
        "info": ("ℹ", "Notification"),
        "success": ("✓", "Completed"),
        "warning": ("!", "Warning"),
        "error": ("✕", "Error"),
    }

    def __init__(self, message: str, tone: str, on_close, parent=None):
        super().__init__(parent)
        self.setObjectName("ToastCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self._tone = (tone or "info").lower()
        self._message = (message or "").strip()
        self._on_close = on_close

        self.setFixedWidth(self.CARD_WIDTH)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 10, 10)
        lay.setSpacing(10)

        badge_char, _ = self._TONE_META.get(self._tone, ("ℹ", "Notification"))
        self._badge = QLabel(badge_char)
        self._badge.setObjectName("ToastBadge")
        self._badge.setAlignment(Qt.AlignCenter)
        self._badge.setFixedSize(22, 22)
        lay.addWidget(self._badge, 0, Qt.AlignTop)

        self._label = QLabel(self._message)
        self._label.setObjectName("ToastMessage")
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._label.setFixedWidth(self.TEXT_WIDTH)
        lay.addWidget(self._label, 1)

        self._close_btn = QPushButton("×")
        self._close_btn.setObjectName("ToastCloseBtn")
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.setToolTip("Dismiss notification")
        self._close_btn.setFixedSize(22, 22)
        self._close_btn.clicked.connect(self._on_close)
        lay.addWidget(self._close_btn, 0, Qt.AlignTop)

        self._apply_style()
        self._recalc_height()

    @property
    def message(self) -> str:
        return self._message

    @property
    def tone(self) -> str:
        return self._tone

    def set_content(self, message: str, tone: str):
        self._message = (message or "").strip()
        self._tone = (tone or "info").lower()
        badge_char, _ = self._TONE_META.get(self._tone, ("ℹ", "Notification"))
        self._badge.setText(badge_char)
        self._label.setText(self._message)
        self._apply_style()
        self._recalc_height()

    def _recalc_height(self):
        fm = QFontMetrics(self._label.font())
        rect = fm.boundingRect(
            0, 0, self.TEXT_WIDTH, 1000,
            int(Qt.TextWordWrap | Qt.AlignLeft),
            self._message,
        )
        text_h = max(22, rect.height() + 4)
        self._label.setMinimumHeight(text_h)
        card_h = max(44, text_h + 22)
        self.setFixedHeight(card_h)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_close()
            event.accept()
            return
        super().mousePressEvent(event)

    def _apply_style(self):
        c = get_design_system().colors
        accent = {
            "error": c.error,
            "warning": c.warning,
            "success": c.success,
            "info": c.info,
        }.get(self._tone, c.accent)
        badge_bg = {
            "error": "rgba(239, 68, 68, 0.18)",
            "warning": "rgba(245, 158, 11, 0.18)",
            "success": "rgba(16, 185, 129, 0.18)",
            "info": "rgba(59, 130, 246, 0.18)",
        }.get(self._tone, c.accent_muted)

        self.setStyleSheet(f"""
            #ToastCard {{
                background: {c.surface_raised};
                border: 1px solid {c.border};
                border-left: 3px solid {accent};
                border-radius: {Radius.md}px;
            }}
            #ToastBadge {{
                background: {badge_bg};
                color: {accent};
                border: none;
                border-radius: 11px;
                font-size: 12px;
                font-weight: 700;
            }}
            #ToastMessage {{
                background: transparent;
                border: none;
                color: {c.text_primary};
                font-size: {FontSize.small}px;
                line-height: 1.35;
            }}
            #ToastCloseBtn {{
                background: transparent;
                color: {c.text_muted};
                border: none;
                border-radius: 11px;
                font-size: 15px;
                font-weight: 600;
                padding: 0px;
                min-width: 22px;
                max-width: 22px;
                min-height: 22px;
                max-height: 22px;
            }}
            #ToastCloseBtn:hover {{
                background: {c.surface_overlay};
                color: {c.text_primary};
            }}
        """)


class NotificationCenter(QWidget):
    """
    Compact, non-blocking toast stack anchored above the status bar.
    Only occupies the exact rectangle of visible toasts so it never intercepts
    mouse events in the AI Workspace, chat input, or code editor.
    """

    MAX_VISIBLE = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NotificationCenter")
        self.setAttribute(Qt.WA_StyledBackground, False)
        self._toasts: list[_Toast] = []
        self._timers: dict[_Toast, QTimer] = {}

        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(Spacing.sm)
        self.setGeometry(0, 0, 0, 0)
        self.hide()

    @staticmethod
    def _is_transient_progress(msg: str) -> bool:
        low = (msg or "").lower().strip()
        return low.startswith((
            "starting ",
            "loading ",
            "connecting ",
            "running ",
            "testing ",
            "inline ai: generating",
            "cloning ",
        )) or low.endswith(("…", "..."))

    def notify(self, message: str, tone: str = "info", timeout: int = 3800):
        clean_msg = (message or "").strip()
        if not clean_msg:
            return

        # 1. If an identical toast is already visible, refresh it in place
        for existing in list(self._toasts):
            if existing.message == clean_msg:
                existing.set_content(clean_msg, tone)
                self._schedule_dismiss(existing, tone, timeout)
                self._reposition()
                return

        # 2. If the latest toast is a transient "Starting..." progress toast, replace it in place
        if self._toasts and self._is_transient_progress(self._toasts[-1].message):
            latest = self._toasts[-1]
            latest.set_content(clean_msg, tone)
            self._schedule_dismiss(latest, tone, timeout)
            self._reposition()
            return

        # 3. Cap maximum visible toasts so they never form a tall wall
        while len(self._toasts) >= self.MAX_VISIBLE:
            self._remove(self._toasts[0])

        toast = _Toast(clean_msg, tone, on_close=lambda: self._remove(toast), parent=self)
        self._lay.addWidget(toast, 0, Qt.AlignRight | Qt.AlignBottom)
        self._toasts.append(toast)
        self.show()
        self.raise_()
        self._reposition()
        self._schedule_dismiss(toast, tone, timeout)

    def _schedule_dismiss(self, toast: _Toast, tone: str, timeout: int):
        old_timer = self._timers.pop(toast, None)
        if old_timer is not None:
            old_timer.stop()
            old_timer.deleteLater()

        effective_timeout = timeout if tone != "error" else max(timeout, 6500)
        if effective_timeout > 0:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda t=toast: self._remove(t))
            timer.start(effective_timeout)
            self._timers[toast] = timer

    def _remove(self, toast: _Toast):
        timer = self._timers.pop(toast, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()
        if toast in self._toasts:
            self._toasts.remove(toast)
            self._lay.removeWidget(toast)
            toast.setParent(None)
            toast.deleteLater()
        if not self._toasts:
            self.setGeometry(0, 0, 0, 0)
            self.hide()
        else:
            self._reposition()

    def clear_all(self):
        for t in list(self._toasts):
            self._remove(t)

    def _reposition(self):
        pw = self.parent()
        if pw is None or not self._toasts:
            self.setGeometry(0, 0, 0, 0)
            self.hide()
            return

        w = _Toast.CARD_WIDTH
        spacing = self._lay.spacing()
        stack_h = sum(t.height() for t in self._toasts) + spacing * max(0, len(self._toasts) - 1)

        # Position to the left of AI Workspace when it is visible so the AI chat input & Send button are never blocked
        right_edge = pw.width() - Spacing.lg
        ai_panel = getattr(pw, "ai_workspace", None)
        if ai_panel is not None and ai_panel.isVisible() and ai_panel.width() > 50:
            right_edge = max(w + Spacing.lg, pw.width() - ai_panel.width() - Spacing.lg)

        # Position cleanly above the status bar (36px from bottom)
        status_h = 28
        status_bar = getattr(pw, "status_bar", None)
        if status_bar is not None and status_bar.isVisible():
            status_h = max(26, status_bar.height())
        bottom_margin = status_h + 12

        x = max(Spacing.md, right_edge - w)
        y = max(Spacing.xl, pw.height() - stack_h - bottom_margin)
        self.setGeometry(x, y, w, stack_h)

    def resize_to_parent(self):
        if self._toasts:
            self._reposition()

    def refresh_theme(self):
        for t in self._toasts:
            t._apply_style()

