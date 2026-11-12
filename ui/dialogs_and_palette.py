"""
Consolidated Module: ui.dialogs_and_palette

Combines: ui.panels.command_palette, ui.dialogs.settings_schema, ui.dialogs.settings_fields, ui.dialogs.theme_gallery, ui.dialogs.settings_dialog, ui.dialogs.change_review_dialog, ui.dialogs.tool_confirmation_dialog
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['ui.panels.command_palette', 'ui.dialogs.settings_schema', 'ui.dialogs.settings_fields', 'ui.dialogs.theme_gallery', 'ui.dialogs.settings_dialog', 'ui.dialogs.change_review_dialog', 'ui.dialogs.tool_confirmation_dialog']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ui.panels.command_palette (ui/panels/command_palette.py)
# ============================================================================
"""
Command Palette & File Search — v3.0

A theme-aware centered overlay for quick file search (Ctrl+P / top search bar)
and command execution (Ctrl+Shift+P / top-left Menu button / '>' prefix).
Automatically syncs with the active DesignSystem theme palette on every theme
switch and every time the popup opens.
"""

from PySide6.QtWidgets import (
    QDialog, QFrame, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QLabel,
)
from PySide6.QtCore import Qt, Signal

from ui.design_system import get_design_system, Spacing, Radius, FontSize


class CommandPalette(QDialog):

    command_chosen = Signal(str)
    file_chosen = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CommandPalette")
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setModal(True)
        self._commands: list[tuple[str, str]] = []   # (id, label)
        self._files: list[str] = []
        self._mode = "command"
        self._build()
        self._apply_style()

    def _build(self):
        self.setFixedWidth(580)
        self.setMinimumHeight(340)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(0)

        self._container = QFrame(self)
        self._container.setObjectName("CommandPaletteContainer")
        self._container.setAttribute(Qt.WA_StyledBackground, True)
        lay = QVBoxLayout(self._container)
        lay.setContentsMargins(Spacing.md, Spacing.md, Spacing.md, Spacing.md)
        lay.setSpacing(Spacing.sm)

        # Header row: Mode tabs (Files vs Commands) + Close button
        header_row = QHBoxLayout()
        header_row.setContentsMargins(2, 0, 2, 2)
        header_row.setSpacing(Spacing.xs)

        self._files_mode_btn = QPushButton("Files (Ctrl+P)")
        self._files_mode_btn.setObjectName("PaletteModeBtn")
        self._files_mode_btn.setCursor(Qt.PointingHandCursor)
        self._files_mode_btn.setCheckable(True)
        self._files_mode_btn.setToolTip("Search and open files in workspace (Ctrl+P)")
        self._files_mode_btn.clicked.connect(lambda: self._switch_mode("file"))

        self._cmds_mode_btn = QPushButton("Commands (> / Ctrl+Shift+P)")
        self._cmds_mode_btn.setObjectName("PaletteModeBtn")
        self._cmds_mode_btn.setCursor(Qt.PointingHandCursor)
        self._cmds_mode_btn.setCheckable(True)
        self._cmds_mode_btn.setToolTip("Search and run IDE commands (Ctrl+Shift+P)")
        self._cmds_mode_btn.clicked.connect(lambda: self._switch_mode("command"))

        self._hint_label = QLabel("↑↓ to navigate · Enter to select · Esc to close")
        self._hint_label.setObjectName("PaletteHint")
        self._hint_label.setToolTip("Keyboard navigation shortcuts")

        self._close_btn = QPushButton("×")
        self._close_btn.setObjectName("PaletteCloseBtn")
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.setFixedSize(22, 22)
        self._close_btn.setToolTip("Close search window (Esc)")
        self._close_btn.clicked.connect(self.close)

        header_row.addWidget(self._files_mode_btn)
        header_row.addWidget(self._cmds_mode_btn)
        header_row.addStretch(1)
        header_row.addWidget(self._hint_label)
        header_row.addWidget(self._close_btn)
        lay.addLayout(header_row)

        self._input = QLineEdit()
        self._input.setObjectName("CommandPaletteInput")
        self._input.setPlaceholderText(
            "Type a filename to search, or prefix with '>' for IDE commands…"
        )
        self._input.setToolTip("Search query — prefix with '>' for commands, or type to filter files")
        self._input.textChanged.connect(self._refilter)
        self._input.returnPressed.connect(self._activate_current)
        lay.addWidget(self._input)

        self._list = QListWidget()
        self._list.setObjectName("CommandPaletteList")
        self._list.setFrameShape(QListWidget.NoFrame)
        self._list.setToolTip("Matching files and commands — click or press Enter to open")
        self._list.itemActivated.connect(lambda _: self._activate_current())
        self._list.itemClicked.connect(lambda _: self._activate_current())
        lay.addWidget(self._list, 1)

        outer.addWidget(self._container)

    def _switch_mode(self, mode: str):
        self._mode = mode
        current = self._input.text()
        if mode == "command":
            if not current.startswith(">"):
                self._input.setText("> " + current.lstrip("> "))
        else:
            if current.startswith(">"):
                self._input.setText(current.lstrip("> "))
        self._sync_mode_buttons()
        self._input.setFocus()
        self._refilter()

    def _sync_mode_buttons(self):
        is_cmd = self._input.text().startswith(">")
        self._cmds_mode_btn.blockSignals(True)
        self._files_mode_btn.blockSignals(True)
        self._cmds_mode_btn.setChecked(is_cmd)
        self._files_mode_btn.setChecked(not is_cmd)
        self._cmds_mode_btn.blockSignals(False)
        self._files_mode_btn.blockSignals(False)

    def set_commands(self, commands: list):
        self._commands = commands or []

    def set_files(self, files: list):
        self._files = files or []

    def showEvent(self, event):
        self._apply_style()
        super().showEvent(event)

    def open_palette(self, mode: str = "command"):
        self._mode = mode
        self._apply_style()
        self._input.setText(">" if mode == "command" else "")
        self._sync_mode_buttons()
        self._refilter()
        self._input.setFocus()
        if self.parent():
            geo = self.parent().geometry()
            self.move(geo.center().x() - self.width() // 2, geo.top() + 72)
        self.show()
        self.raise_()

    def _refilter(self):
        self._sync_mode_buttons()
        text = self._input.text()
        self._list.clear()
        if text.startswith(">"):
            needle = text[1:].strip().lower()
            for cid, label in self._commands:
                if needle in label.lower():
                    item = QListWidgetItem(label)
                    item.setToolTip(f"Run command: {label}")
                    item.setData(Qt.UserRole, ("command", cid))
                    self._list.addItem(item)
        else:
            needle = text.strip().lower()
            for path in self._files:
                if not needle or needle in path.lower():
                    item = QListWidgetItem(path)
                    item.setToolTip(f"Open file: {path}")
                    item.setData(Qt.UserRole, ("file", path))
                    self._list.addItem(item)
                if self._list.count() >= 200:
                    break
            if self._list.count() == 0 and not needle:
                # If no files are open yet, show helpful commands so the list is never blank
                for cid, label in self._commands[:8]:
                    item = QListWidgetItem(f"⌘  {label}")
                    item.setToolTip(f"Run command: {label}")
                    item.setData(Qt.UserRole, ("command", cid))
                    self._list.addItem(item)
        if self._list.count():
            self._list.setCurrentRow(0)

    def _activate_current(self):
        item = self._list.currentItem()
        if not item:
            return
        kind, value = item.data(Qt.UserRole)
        self.close()
        if kind == "command":
            self.command_chosen.emit(value)
        else:
            self.file_chosen.emit(value)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        if event.key() in (Qt.Key_Down, Qt.Key_Up):
            row = self._list.currentRow()
            row += 1 if event.key() == Qt.Key_Down else -1
            self._list.setCurrentRow(max(0, min(row, self._list.count() - 1)))
            return
        super().keyPressEvent(event)

    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            QDialog#CommandPalette {{
                background: {c.border_strong};
                border: 1px solid {c.border_strong};
                border-radius: {Radius.lg}px;
            }}
            QFrame#CommandPaletteContainer {{
                background: {c.surface_overlay};
                border: 1px solid {c.border_strong};
                border-radius: {Radius.lg}px;
            }}
            QPushButton#PaletteModeBtn {{
                background: {c.surface_raised};
                color: {c.text_muted};
                border: 1px solid {c.border_subtle};
                border-radius: {Radius.sm}px;
                padding: 3px 10px;
                font-size: {FontSize.tiny}px;
                font-weight: 600;
            }}
            QPushButton#PaletteModeBtn:hover {{
                background: {c.surface_high};
                color: {c.text_primary};
            }}
            QPushButton#PaletteModeBtn:checked {{
                background: {c.accent_muted};
                color: {c.accent};
                border: 1px solid {c.accent};
            }}
            QLabel#PaletteHint {{
                color: {c.text_faint};
                font-size: {FontSize.micro}px;
                background: transparent;
                padding-right: 4px;
            }}
            QPushButton#PaletteCloseBtn {{
                background: transparent;
                color: {c.text_muted};
                border: none;
                border-radius: {Radius.sm}px;
                font-size: 15px;
                font-weight: 600;
                padding: 0px;
            }}
            QPushButton#PaletteCloseBtn:hover {{
                background: {c.surface_high};
                color: {c.text_primary};
            }}
            QLineEdit#CommandPaletteInput {{
                background: {c.surface_inset};
                color: {c.text_primary};
                border: 1px solid {c.border};
                border-radius: {Radius.md}px;
                padding: 8px 12px;
                font-size: {FontSize.md}px;
                selection-background-color: {c.selection};
            }}
            QLineEdit#CommandPaletteInput:focus {{
                border: 1px solid {c.accent};
            }}
            QListWidget#CommandPaletteList {{
                background: {c.surface_overlay};
                color: {c.text_secondary};
                border: none;
                outline: none;
                font-size: {FontSize.base}px;
            }}
            QListWidget#CommandPaletteList::item {{
                padding: 7px 10px;
                border-radius: {Radius.sm}px;
                color: {c.text_secondary};
            }}
            QListWidget#CommandPaletteList::item:hover {{
                background: {c.surface_high};
                color: {c.text_primary};
            }}
            QListWidget#CommandPaletteList::item:selected {{
                background: {c.accent_muted};
                color: {c.text_primary};
                border-left: 2px solid {c.accent};
            }}
            QListWidget#CommandPaletteList QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 0;
            }}
            QListWidget#CommandPaletteList QScrollBar::handle:vertical {{
                background: {c.scrollbar};
                border-radius: 5px;
                min-height: 24px;
                margin: 2px;
            }}
            QListWidget#CommandPaletteList QScrollBar::handle:vertical:hover {{
                background: {c.scrollbar_hover};
            }}
        """)

    def refresh_theme(self):
        self._apply_style()


# ============================================================================
# SECTION: ui.dialogs.settings_schema (ui/dialogs/settings_schema.py)
# ============================================================================
"""
Settings schema — v1.0

Declarative description of every setting the Settings dialog exposes. Keeping
this as data (instead of hand-built widgets) means a new setting is one line
here, and the dialog's search/reset/persistence logic works for it for free.

Field kinds
  bool     QCheckBox
  int      QSpinBox           (lo, hi, step, suffix)
  float    QDoubleSpinBox     (lo, hi, step, decimals)
  choice   QComboBox          (options: [(value, label), ...])
  text     QLineEdit          (placeholder)
  secret   QLineEdit(Password)
  font     font-family combo + free text
  path     QLineEdit + Browse…
  list     one item per line in a QPlainTextEdit
  shortcut QKeySequenceEdit
"""

from dataclasses import dataclass, field as _field
from typing import Any, List, Tuple


@dataclass(frozen=True)
class Field:
    key: str                     # key inside the category
    label: str
    kind: str = "bool"
    hint: str = ""               # one-line explanation under the label
    options: Tuple = ()          # for "choice": ((value, label), ...)
    lo: float = 0
    hi: float = 1_000_000
    step: float = 1
    decimals: int = 2
    suffix: str = ""
    placeholder: str = ""
    depends_on: str = ""         # key in the same category that must be truthy


@dataclass(frozen=True)
class Group:
    title: str
    fields: Tuple[Field, ...] = ()
    note: str = ""


@dataclass(frozen=True)
class Page:
    name: str                    # stable id, also the settings category
    label: str                   # sidebar text
    icon: str = "settings"
    category: str = ""           # settings category (defaults to name)
    groups: Tuple[Group, ...] = ()
    custom: str = ""             # id of a hand-built widget to append
    blurb: str = ""

    @property
    def cat(self) -> str:
        return self.category or self.name


# ── option sets ──────────────────────────────────────────────────────────────
WHITESPACE = (("none", "Never"), ("boundary", "Boundary"),
              ("selection", "In selection"), ("all", "Always"))
CURSOR_STYLE = (("line", "Line"), ("block", "Block"),
                ("underline", "Underline"), ("line-thin", "Thin line"))
CURSOR_SHAPE = (("block", "Block"), ("beam", "Beam"), ("underline", "Underline"))
SHELLS = (("cmd", "Command Prompt"), ("powershell", "PowerShell"),
          ("pwsh", "PowerShell 7+"), ("bash", "Bash"), ("wsl", "WSL"),
          ("zsh", "Zsh"))
LANGUAGES = (("en", "English"), ("hi", "हिन्दी"), ("es", "Español"),
             ("fr", "Français"), ("de", "Deutsch"), ("pt", "Português"),
             ("ja", "日本語"), ("zh", "中文"))
BRANCHES = (("main", "main"), ("master", "master"), ("develop", "develop"))


# ── pages ────────────────────────────────────────────────────────────────────
GENERAL = Page(
    name="general", label="General", icon="settings",
    blurb="Startup behaviour, saving and language.",
    groups=(
        Group("Files", (
            Field("auto_save", "Auto-save edited files", "bool",
                  "Write changes to disk without pressing Ctrl+S."),
            Field("auto_save_delay", "Auto-save delay", "int",
                  "How long to wait after you stop typing.",
                  lo=200, hi=60000, step=100, suffix=" ms",
                  depends_on="auto_save"),
        )),
        Group("Startup", (
            Field("restore_session", "Reopen last session", "bool",
                  "Restore the previous workspace and open tabs on launch."),
            Field("show_welcome", "Show the welcome screen", "bool"),
        )),
        Group("Language", (
            Field("language", "Interface language", "choice",
                  "Takes effect after a restart.", options=LANGUAGES),
        )),
    ),
    custom="general_extras",
)

APPEARANCE = Page(
    name="appearance", label="Appearance", icon="palette",
    blurb="Theme, fonts and UI density.",
    custom="theme_gallery",
    groups=(
        Group("Font", (
            Field("font_family", "UI font", "font",
                  "Comma-separated stack; the first available font wins.",
                  placeholder="Inter, Segoe UI, sans-serif"),
            Field("font_size", "UI font size", "int",
                  lo=9, hi=24, suffix=" pt"),
            Field("font_ligatures", "Enable font ligatures", "bool",
                  "Renders -> and != as single glyphs in code fonts."),
        )),
        Group("Layout", (
            Field("line_height", "Line height", "float",
                  lo=1.0, hi=2.5, step=0.05),
            Field("letter_spacing", "Letter spacing", "float",
                  lo=-1.0, hi=3.0, step=0.1, suffix=" px"),
            Field("word_wrap", "Wrap long lines", "bool"),
            Field("minimap", "Show minimap", "bool",
                  "The scaled-down file overview on the right edge."),
            Field("scrollbar_size", "Scrollbar width", "int",
                  lo=4, hi=20, suffix=" px"),
        )),
    ),
)

EDITOR = Page(
    name="editor", label="Editor", icon="file",
    blurb="Indentation, cursor and completions.",
    groups=(
        Group("Indentation", (
            Field("tab_size", "Tab size", "int", lo=1, hi=16, suffix=" spaces"),
            Field("insert_spaces", "Insert spaces instead of tabs", "bool"),
            Field("render_whitespace", "Show whitespace", "choice",
                  options=WHITESPACE),
        )),
        Group("Cursor", (
            Field("cursor_style", "Cursor style", "choice", options=CURSOR_STYLE),
            Field("cursor_blinking", "Blink the cursor", "bool"),
        )),
        Group("Suggestions & formatting", (
            Field("automatic_completions", "Suggest as you type", "bool"),
            Field("word_based_suggestions", "Include words from the open file",
                  "bool", "Adds plain-text matches alongside real symbols."),
            Field("format_on_type", "Format while typing", "bool"),
            Field("format_on_save", "Format on save", "bool"),
        )),
    ),
)

TERMINAL = Page(
    name="terminal", label="Terminal", icon="terminal",
    blurb="Integrated terminal shell and rendering.",
    groups=(
        Group("Shell", (
            Field("default_shell", "Default shell", "choice", options=SHELLS),
            Field("default_working_dir", "Starting directory", "path",
                  "Leave empty to use the workspace root.",
                  placeholder="Workspace root"),
            Field("confirm_before_close", "Confirm before closing a busy terminal",
                  "bool"),
        )),
        Group("Appearance", (
            Field("font_family", "Terminal font", "font",
                  placeholder="JetBrains Mono, Consolas, monospace"),
            Field("font_size", "Font size", "int", lo=8, hi=24, suffix=" pt"),
            Field("line_height", "Line height", "float",
                  lo=1.0, hi=2.5, step=0.05),
            Field("padding", "Inner padding", "int", lo=0, hi=32, suffix=" px"),
            Field("cursor_shape", "Cursor shape", "choice", options=CURSOR_SHAPE),
            Field("cursor_blink", "Blink the cursor", "bool"),
        )),
        Group("Behaviour", (
            Field("scrollback_size", "Scrollback buffer", "int",
                  "Lines of history kept per terminal.",
                  lo=100, hi=200000, step=500, suffix=" lines"),
            Field("copy_on_select", "Copy on selection", "bool"),
            Field("smooth_scrolling", "Smooth scrolling", "bool"),
            Field("bell", "Audible bell", "bool"),
        )),
    ),
)

AI = Page(
    name="ai", label="AI", icon="ai",
    blurb="How the assistant gathers context and generates answers.",
    groups=(
        Group("Context", (
            Field("auto_context", "Attach relevant files automatically", "bool",
                  "Lets the assistant pick context instead of you @-mentioning it."),
            Field("max_context_files", "Context file limit", "int",
                  "More files means better answers but slower, costlier requests.",
                  lo=1, hi=100, depends_on="auto_context"),
            Field("context_window_size", "Model context window", "int",
                "Maximum tokens sent to Ollama per request. Lower values respond faster.",
                lo=512, hi=131072, step=512, suffix=" tokens"),
        )),
        Group("Generation", (
            Field("max_tokens", "Max response tokens", "int",
                  lo=256, hi=200000, step=256),
            Field("temperature", "Temperature", "float",
                  "0 is deterministic and best for code; higher is more creative.",
                  lo=0.0, hi=2.0, step=0.05),
            Field("streaming", "Stream responses", "bool",
                  "Show tokens as they arrive instead of waiting for the full reply."),
        )),
        Group("Assistance", (
            Field("smart_suggestions", "Proactive suggestions", "bool"),
            Field("auto_verify", "Verify generated edits", "bool",
                  "Runs syntax and lint checks on every file the AI writes."),
        )),
        Group("Inline AI (editor)", (
            Field("inline_ai_enabled", "Enable inline AI edits (Ctrl+K)", "bool",
                  "Off by default. When on, press Ctrl+K in the editor to ask the "
                  "AI to rewrite the selection; you review a diff before it applies. "
                  "Uses your selected cloud provider/model."),
            Field("inline_completions_enabled", "Inline completions (ghost text)", "bool",
                  "Off by default. Suggests the rest of a line as you pause typing. "
                  "Sends context to your cloud provider, so it costs tokens.",
                  depends_on="inline_ai_enabled"),
        )),
    ),
    custom="ai_model_defaults",
)

PROVIDERS = Page(
    name="providers", label="Providers & Keys", icon="plug",
    category="models",
    blurb="API keys, base URLs and connection tests for every model provider.",
    custom="providers",
)

WORKSPACE = Page(
    name="workspace", label="Workspace", icon="folder",
    blurb="File tree behaviour, project scanning and indexing.",
    groups=(
        Group("Explorer", (
            Field("single_click_open", "Open files with a single click", "bool",
                  "On, like VS Code. Turn this off to require a double-click."),
            Field("preview_single_click", "Single click only previews the file",
                  "bool",
                  "Reuses one preview tab until you double-click or edit the "
                  "file, so browsing does not fill the tab bar.",
                  depends_on="single_click_open"),
            Field("reveal_active_file", "Reveal the active file in the tree",
                  "bool", "Selects and scrolls to the file you switch to."),
        )),
        Group("Scanning", (
            Field("auto_scan", "Index the project automatically", "bool"),
            Field("scan_delay", "Rescan delay after a change", "int",
                  lo=100, hi=60000, step=100, suffix=" ms",
                  depends_on="auto_scan"),
            Field("follow_symlinks", "Follow symbolic links", "bool",
                  "Off by default — symlink loops can make indexing hang."),
        )),
        Group("Exclusions", (
            Field("exclude_patterns", "Ignored paths", "list",
                  "One pattern per line. Applies to the file tree, search and "
                  "AI context."),
        )),
    ),
)

GIT = Page(
    name="git", label="Git & GitHub", icon="git",
    blurb="Source-control integration.",
    groups=(
        Group("Git", (
            Field("enabled", "Enable Git integration", "bool"),
            Field("auto_refresh", "Refresh status automatically", "bool",
                  depends_on="enabled"),
            Field("refresh_interval", "Refresh interval", "int",
                  lo=500, hi=120000, step=500, suffix=" ms",
                  depends_on="enabled"),
            Field("commit_on_save", "Commit on save", "bool",
                  "Creates a commit every time you save. Noisy — off by default.",
                  depends_on="enabled"),
            Field("push_on_close", "Push when closing the app", "bool",
                  depends_on="enabled"),
        )),
    ),
    custom="github",
)

KEYBOARD = Page(
    name="keyboard", label="Keyboard", icon="keyboard",
    blurb="Every shortcut, editable. Chords are separated by commas.",
    custom="keyboard",
)

WINDOW = Page(
    name="window", label="Window", icon="window",
    blurb="What gets restored the next time you open the app.",
    groups=(
        Group("Restore on launch", (
            Field("restore_layout", "Panel layout and sizes", "bool"),
            Field("remember_position", "Window position", "bool"),
            Field("remember_size", "Window size", "bool"),
            Field("remember_maximized", "Maximized state", "bool"),
        )),
    ),
)

ADVANCED = Page(
    name="advanced", label="Advanced", icon="wrench",
    category="general",
    blurb="Configuration files and factory reset.",
    custom="advanced",
)

PAGES: List[Page] = [GENERAL, APPEARANCE, EDITOR, TERMINAL, AI, PROVIDERS,
                     WORKSPACE, GIT, KEYBOARD, WINDOW, ADVANCED]


# Human-readable labels for keyboard.shortcuts keys.
ACTION_LABELS = {
    "command_palette": "Command palette",
    "new_file": "New file",
    "open_folder": "Open folder",
    "save": "Save",
    "save_all": "Save all",
    "close": "Close tab",
    "next_tab": "Next tab",
    "prev_tab": "Previous tab",
    "run": "Run",
    "stop": "Stop",
    "toggle_terminal": "Toggle terminal",
    "toggle_explorer": "Toggle explorer",
    "toggle_ai_panel": "Toggle AI workspace",
}


def search_hits(page: Page, needle: str) -> bool:
    """True if a page mentions `needle` in its label, blurb or any field."""
    needle = needle.strip().lower()
    if not needle:
        return True
    haystack = [page.label, page.blurb, page.name]
    for group in page.groups:
        haystack.append(group.title)
        for f in group.fields:
            haystack += [f.label, f.hint, f.key]
    if page.custom == "keyboard":
        haystack += list(ACTION_LABELS.values())
    return any(needle in h.lower() for h in haystack if h)





# ============================================================================
# SECTION: ui.dialogs.settings_fields (ui/dialogs/settings_fields.py)
# ============================================================================
"""
Settings field widgets — v1.0

One editor widget per `Field` kind from settings_schema, each wrapped in a row
with its label and hint. Every widget exposes the same tiny interface so the
dialog never needs to know what kind it is:

    row.value()          -> current value, already the right Python type
    row.set_value(v)     -> load a value in without emitting changed
    row.changed          -> Signal() fired on any user edit
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QCheckBox, QSpinBox,
    QDoubleSpinBox, QComboBox, QLineEdit, QPlainTextEdit, QPushButton,
    QKeySequenceEdit, QFileDialog, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence

from ui.design_system import get_design_system, Spacing, FontSize, Radius


class FieldRow(QWidget):
    """Label + hint on the left, editor on the right."""

    changed = Signal()

    def __init__(self, field, parent=None):
        super().__init__(parent)
        self.field = field
        self._loading = False
        self._editor = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, Spacing.sm, 0, Spacing.sm)
        lay.setSpacing(Spacing.lg)

        text = QVBoxLayout()
        text.setSpacing(2)
        self._label = QLabel(field.label)
        self._label.setObjectName("FieldLabel")
        text.addWidget(self._label)
        if field.hint:
            self._hint = QLabel(field.hint)
            self._hint.setObjectName("FieldHint")
            self._hint.setWordWrap(True)
            text.addWidget(self._hint)
        lay.addLayout(text, 1)

        self._editor = self._build_editor()
        if self._editor is not None:
            lay.addWidget(self._editor, 0, Qt.AlignTop)
        self._apply_style()

    # -- construction --------------------------------------------------------
    def _build_editor(self):
        f = self.field
        kind = f.kind

        if kind == "bool":
            w = QCheckBox()
            w.toggled.connect(self._emit)
            return w

        if kind == "int":
            w = QSpinBox()
            w.setRange(int(f.lo), int(f.hi))
            w.setSingleStep(int(f.step) or 1)
            w.setSuffix(f.suffix)
            w.setFixedWidth(150)
            w.valueChanged.connect(self._emit)
            return w

        if kind == "float":
            w = QDoubleSpinBox()
            w.setRange(float(f.lo), float(f.hi))
            w.setSingleStep(float(f.step))
            w.setDecimals(f.decimals)
            w.setSuffix(f.suffix)
            w.setFixedWidth(150)
            w.valueChanged.connect(self._emit)
            return w

        if kind == "choice":
            w = QComboBox()
            for value, label in f.options:
                w.addItem(label, value)
            w.setMinimumWidth(200)
            w.currentIndexChanged.connect(self._emit)
            return w

        if kind in ("text", "secret", "font"):
            w = QLineEdit()
            w.setPlaceholderText(f.placeholder)
            w.setMinimumWidth(280)
            if kind == "secret":
                w.setEchoMode(QLineEdit.Password)
            w.textChanged.connect(self._emit)
            return w

        if kind == "path":
            return _PathEditor(f, self._emit)

        if kind == "list":
            w = QPlainTextEdit()
            w.setFixedHeight(120)
            w.setMinimumWidth(280)
            w.setPlaceholderText(f.placeholder or "One entry per line")
            w.textChanged.connect(self._emit)
            return w

        if kind == "shortcut":
            return _ShortcutEditor(self._emit)

        return None

    # -- value plumbing ------------------------------------------------------
    def _emit(self, *_):
        if not self._loading:
            self.changed.emit()

    def value(self):
        w, kind = self._editor, self.field.kind
        if w is None:
            return None
        if kind == "bool":
            return w.isChecked()
        if kind == "int":
            return int(w.value())
        if kind == "float":
            return round(float(w.value()), self.field.decimals)
        if kind == "choice":
            return w.currentData()
        if kind in ("text", "secret", "font"):
            return w.text()
        if kind in ("path", "shortcut"):
            return w.value()
        if kind == "list":
            return [ln.strip() for ln in w.toPlainText().splitlines() if ln.strip()]
        return None

    def set_value(self, value):
        w, kind = self._editor, self.field.kind
        if w is None:
            return
        self._loading = True
        try:
            if kind == "bool":
                w.setChecked(bool(value))
            elif kind == "int":
                w.setValue(int(value if value is not None else self.field.lo))
            elif kind == "float":
                w.setValue(float(value if value is not None else self.field.lo))
            elif kind == "choice":
                idx = w.findData(value)
                # Unknown stored value: keep it visible rather than silently
                # snapping to the first option and overwriting the user's config.
                if idx < 0 and value not in (None, ""):
                    w.addItem(str(value), value)
                    idx = w.count() - 1
                w.setCurrentIndex(max(idx, 0))
            elif kind in ("text", "secret", "font"):
                w.setText("" if value is None else str(value))
            elif kind in ("path", "shortcut"):
                w.set_value(value)
            elif kind == "list":
                w.setPlainText("\n".join(value or []))
        finally:
            self._loading = False

    def set_enabled_state(self, enabled: bool):
        """Grey out the whole row when its `depends_on` field is off."""
        self.setEnabled(enabled)

    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #FieldLabel {{
                color: {c.text_primary};
                font-size: {FontSize.base}px;
            }}
            #FieldHint {{
                color: {c.text_muted};
                font-size: {FontSize.small}px;
            }}
        """)


class _PathEditor(QWidget):
    """Line edit plus a Browse… button that opens a directory picker."""

    def __init__(self, field, on_change, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(Spacing.sm)
        self._edit = QLineEdit()
        self._edit.setPlaceholderText(field.placeholder)
        self._edit.setMinimumWidth(240)
        self._edit.textChanged.connect(on_change)
        lay.addWidget(self._edit)
        btn = QPushButton("Browse…")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self._browse)
        lay.addWidget(btn)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Choose a directory",
                                                self._edit.text() or "")
        if path:
            self._edit.setText(path)

    def value(self):
        return self._edit.text()

    def set_value(self, value):
        self._edit.setText("" if value is None else str(value))


class _ShortcutEditor(QWidget):
    """Captures a key sequence; value() returns a list of chord strings."""

    def __init__(self, on_change, parent=None):
        super().__init__(parent)
        self._on_change = on_change
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(Spacing.sm)
        self._edit = QKeySequenceEdit()
        self._edit.setFixedWidth(190)
        self._edit.keySequenceChanged.connect(lambda *_: on_change())
        lay.addWidget(self._edit)
        clear = QPushButton("Clear")
        clear.setCursor(Qt.PointingHandCursor)
        clear.clicked.connect(self._edit.clear)
        lay.addWidget(clear)

    def value(self) -> list:
        text = self._edit.keySequence().toString(QKeySequence.PortableText)
        # Qt joins multi-chord sequences with ", "; settings.json stores a list.
        return [part.strip() for part in text.split(",") if part.strip()]

    def set_value(self, value):
        if isinstance(value, str):
            value = [value]
        self._edit.setKeySequence(QKeySequence(", ".join(value or []),
                                               QKeySequence.PortableText))


# ============================================================================
# SECTION: ui.dialogs.theme_gallery (ui/dialogs/theme_gallery.py)
# ============================================================================
"""
Theme gallery — v1.0

A grid of clickable theme cards for Settings → Appearance. Each card paints a
miniature of the actual palette (titlebar, sidebar, editor, accent) so the user
can see what they're picking without applying it first.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
)
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QPainter, QColor, QPen

from ui.design_system import (get_design_system, PALETTES, THEME_META,
                              Spacing, Radius, FontSize, FontWeight)


class _Preview(QWidget):
    """Miniature mock of an IDE window drawn in one palette's colours."""

    def __init__(self, palette, parent=None):
        super().__init__(parent)
        self._p = palette
        self.setFixedHeight(112)
        self.setMinimumWidth(210)

    def paintEvent(self, event):
        c = self._p
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        # The mock was drawn against a 76px-tall box; scale every offset so the
        # proportions survive the bigger card without re-deriving the geometry.
        s = h / 76.0

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(c.canvas))
        p.drawRoundedRect(QRectF(0, 0, w, h), Radius.sm, Radius.sm)

        # title bar + three dots
        bar = 12 * s
        p.setBrush(QColor(c.surface))
        p.drawRoundedRect(QRectF(0, 0, w, bar), Radius.sm, Radius.sm)
        p.setBrush(QColor(c.text_faint))
        for i in range(3):
            d = 3.5 * s
            p.drawEllipse(QRectF(6 * s + i * 7 * s, (bar - d) / 2, d, d))

        # activity bar, sidebar, editor
        act, side = 14 * s, 62 * s
        p.setBrush(QColor(c.surface_raised))
        p.drawRect(QRectF(0, bar, act, h - bar))
        p.setBrush(QColor(c.surface))
        p.drawRect(QRectF(act, bar, side - act, h - bar))
        p.setBrush(QColor(c.surface_inset))
        p.drawRect(QRectF(side, bar, w - side, h - bar))

        # accent marker on the activity bar
        p.setBrush(QColor(c.accent))
        p.drawRoundedRect(QRectF(1.5 * s, 20 * s, 3 * s, 12 * s), 1, 1)

        # sidebar rows
        p.setBrush(QColor(c.text_faint))
        for i, width in enumerate((36, 26, 31, 21)):
            p.drawRoundedRect(
                QRectF(19 * s, (20 + i * 9) * s, width * s, 3 * s), 1, 1)

        # fake code lines, tinted with real syntax colours
        tints = (c.syn_keyword, c.syn_function, c.syn_string,
                 c.text_secondary, c.syn_comment)
        for i, (width, tint) in enumerate(zip((44, 34, 56, 26, 40), tints)):
            p.setBrush(QColor(tint))
            p.drawRoundedRect(
                QRectF(side + 6 * s, (19 + i * 9) * s, width * s, 3 * s), 1, 1)

        # terminal strip along the bottom of the editor well, so the preview
        # also shows what the panel the user complained about will look like
        term_h = 20 * s
        p.setBrush(QColor(c.canvas))
        p.drawRect(QRectF(side, h - term_h, w - side, term_h))
        p.setBrush(QColor(c.success))
        p.drawRoundedRect(
            QRectF(side + 6 * s, h - term_h + 7 * s, 8 * s, 3 * s), 1, 1)
        p.setBrush(QColor(c.text_secondary))
        p.drawRoundedRect(
            QRectF(side + 18 * s, h - term_h + 7 * s, 28 * s, 3 * s), 1, 1)

        p.setPen(QPen(QColor(c.border), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), Radius.sm, Radius.sm)
        p.end()


class ThemeCard(QFrame):
    """Selectable card: preview, name, one-line description.

    This was a QToolButton, which is why the cards rendered as tiny glyphs — a
    QToolButton ignores a child QLayout, so the preview and labels collapsed to
    nothing. A QFrame lays its children out normally; the checked state and the
    click-to-pick behaviour are handled manually below.
    """

    picked = Signal(str)

    def __init__(self, info, parent=None):
        super().__init__(parent)
        self.info = info
        self._checked = False
        self._hover = False
        self.setObjectName("ThemeCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(info.blurb)
        self.setAttribute(Qt.WA_Hover, True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(Spacing.md, Spacing.md, Spacing.md, Spacing.md)
        lay.setSpacing(Spacing.sm)
        self._preview = _Preview(PALETTES[info.name])
        lay.addWidget(self._preview)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(Spacing.sm)
        name = QLabel(info.label)
        name.setObjectName("ThemeName")
        row.addWidget(name)
        row.addStretch(1)
        self._check = QLabel("✓")
        self._check.setObjectName("ThemeCheck")
        self._check.setVisible(False)
        row.addWidget(self._check)
        lay.addLayout(row)

        blurb = QLabel(info.blurb)
        blurb.setObjectName("ThemeBlurb")
        blurb.setWordWrap(True)
        blurb.setMinimumHeight(30)
        lay.addWidget(blurb)
        self._restyle()

    # --- selection -------------------------------------------------------
    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, on: bool):
        if on == self._checked:
            return
        self._checked = bool(on)
        self._check.setVisible(self._checked)
        self._restyle()

    # --- interaction -----------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.picked.emit(self.info.name)
            event.accept()
            return
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._hover = True
        self._restyle()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self._restyle()
        super().leaveEvent(event)

    def _restyle(self):
        c = get_design_system().colors
        if self._checked:
            border, bg = f"2px solid {c.accent}", c.surface_high
        elif self._hover:
            border, bg = f"1px solid {c.border_strong}", c.surface_raised
        else:
            border, bg = f"1px solid {c.border}", c.surface_raised
        self.setStyleSheet(f"""
            #ThemeCard {{
                background: {bg};
                border: {border};
                border-radius: {Radius.lg}px;
            }}
            #ThemeName {{
                color: {c.text_primary};
                font-size: {FontSize.base}px;
                font-weight: {FontWeight.semibold};
                background: transparent;
            }}
            #ThemeCheck {{
                color: {c.accent};
                font-size: {FontSize.base}px;
                font-weight: {FontWeight.bold};
                background: transparent;
            }}
            #ThemeBlurb {{
                color: {c.text_muted};
                font-size: {FontSize.small}px;
                background: transparent;
            }}
        """)


class ThemeGallery(QWidget):
    """Dark and light theme cards in a responsive grid."""

    theme_picked = Signal(str)

    COLUMNS = 3

    def __init__(self, current: str = "", parent=None):
        super().__init__(parent)
        self._cards = {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(Spacing.lg)

        for group_name in ("Dark", "Light"):
            infos = [i for i in THEME_META.values() if i.group == group_name]
            if not infos:
                continue
            header = QLabel(f"{group_name} themes")
            header.setObjectName("GalleryHeader")
            lay.addWidget(header)

            grid = QGridLayout()
            grid.setSpacing(Spacing.lg)
            for idx, info in enumerate(infos):
                card = ThemeCard(info)
                card.picked.connect(self._on_picked)
                self._cards[info.name] = card
                grid.addWidget(card, idx // self.COLUMNS, idx % self.COLUMNS)
            for col in range(self.COLUMNS):
                grid.setColumnStretch(col, 1)
            lay.addLayout(grid)

        self.set_current(current)
        self._restyle()

    def _on_picked(self, name: str):
        self.set_current(name)
        self.theme_picked.emit(name)

    def set_current(self, name: str):
        """Check the card for `name` without re-emitting theme_picked."""
        for theme, card in self._cards.items():
            card.setChecked(theme == name)

    def refresh_theme(self):
        """Re-skin every card after the app theme changed."""
        self._restyle()
        for card in self._cards.values():
            card._restyle()
            card.update()

    def _restyle(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #GalleryHeader {{
                color: {c.text_secondary};
                font-size: {FontSize.small}px;
                font-weight: {FontWeight.semibold};
                text-transform: uppercase;
            }}
        """)


# ============================================================================
# SECTION: ui.dialogs.settings_dialog (ui/dialogs/settings_dialog.py)
# ============================================================================
"""
Settings dialog — v1.0

A full IDE settings surface: searchable category list on the left, a stack of
pages on the right. Most pages are generated from `settings_schema.PAGES`;
Appearance, Providers, Keyboard, GitHub and Advanced add hand-built sections.

Changes apply and persist immediately (no OK/Apply dance), which is what modern
editors do and what the rest of this app already assumes. Theme picks are
broadcast via `theme_selected` so the main window can restyle live.
"""

from PySide6.QtWidgets import (
    QDialog, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QStackedWidget, QScrollArea, QFrame, QPushButton,
    QMessageBox, QComboBox, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon

from ui.design_system import (get_design_system, PALETTES, THEME_META,
                              Spacing, Radius, FontSize, FontWeight)
from ui.settings_manager import get_settings_manager
from ui.widgets.icons import icon as make_icon
from ui.dialogs.settings_schema import PAGES, ACTION_LABELS, Field, search_hits
from ui.dialogs.settings_fields import FieldRow
from ui.dialogs.theme_gallery import ThemeGallery


class SettingsDialog(QDialog):
    """Category list + stacked pages, driven by SettingsManager."""

    theme_selected = Signal(str)
    setting_changed = Signal(str, str, object)   # category, key, value

    def __init__(self, parent=None, provider_registry=None,
                 provider_manager=None, current_theme: str = ""):
        super().__init__(parent)
        self.settings = get_settings_manager()
        self._registry = provider_registry
        self._manager = provider_manager
        self._current_theme = current_theme or get_design_system().theme
        self._rows = {}          # (category, key) -> FieldRow
        self._page_index = {}    # page name -> stack index
        self._gallery = None
        self._provider_rows = []

        self.setWindowTitle("Settings")
        self.setObjectName("SettingsDialog")
        self.setMinimumSize(980, 660)
        self.resize(1100, 740)

        self._build()
        self._load_all()
        self._apply_style()

    # ── layout ──────────────────────────────────────────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())
        body.addWidget(self._build_stack(), 1)
        root.addLayout(body, 1)
        root.addWidget(self._build_footer())

    def _build_sidebar(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("SettingsSidebar")
        panel.setFixedWidth(240)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(Spacing.lg, Spacing.lg, Spacing.lg, Spacing.lg)
        lay.setSpacing(Spacing.md)

        self._search = QLineEdit()
        self._search.setObjectName("SettingsSearch")
        self._search.setPlaceholderText("Search settings…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter)
        lay.addWidget(self._search)

        self._list = QListWidget()
        self._list.setObjectName("SettingsCategories")
        self._list.setIconSize(QSize(18, 18))
        self._list.currentRowChanged.connect(self._on_category)
        lay.addWidget(self._list, 1)
        return panel

    def _build_stack(self) -> QWidget:
        self._stack = QStackedWidget()
        for page in PAGES:
            item = QListWidgetItem(make_icon(page.icon, 18), page.label)
            item.setData(Qt.UserRole, page.name)
            self._list.addItem(item)
            self._page_index[page.name] = self._stack.addWidget(
                self._build_page(page))
        self._list.setCurrentRow(0)
        return self._stack

    def _build_footer(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("SettingsFooter")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(Spacing.xl, Spacing.lg, Spacing.xl, Spacing.lg)
        lay.setSpacing(Spacing.md)

        self._status = QLabel("Changes are saved as you make them.")
        self._status.setObjectName("SettingsStatus")
        lay.addWidget(self._status)
        lay.addStretch(1)

        reset = QPushButton("Reset this page")
        reset.clicked.connect(self._reset_current_page)
        lay.addWidget(reset)

        close = QPushButton("Close")
        close.setObjectName("PrimaryButton")
        close.setDefault(True)
        close.clicked.connect(self.accept)
        lay.addWidget(close)
        return bar

    # ── generated pages ─────────────────────────────────────────────────────
    def _build_page(self, page) -> QWidget:
        """Scrollable page: heading, schema groups, then any custom section."""
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(Spacing.xxxl, Spacing.xxl, Spacing.xxxl, Spacing.xxl)
        lay.setSpacing(Spacing.xl)

        title = QLabel(page.label)
        title.setObjectName("PageTitle")
        lay.addWidget(title)
        if page.blurb:
            blurb = QLabel(page.blurb)
            blurb.setObjectName("PageBlurb")
            blurb.setWordWrap(True)
            lay.addWidget(blurb)

        if page.custom:
            section = self._build_custom(page.custom, page)
            if section is not None:
                lay.addWidget(section)

        for group in page.groups:
            lay.addWidget(self._build_group(page.cat, group))

        lay.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(inner)
        return scroll

    def _build_group(self, category: str, group) -> QWidget:
        card = QFrame()
        card.setObjectName("SettingsGroup")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(Spacing.xl, Spacing.lg, Spacing.xl, Spacing.lg)
        lay.setSpacing(0)

        head = QLabel(group.title)
        head.setObjectName("GroupTitle")
        lay.addWidget(head)
        if group.note:
            note = QLabel(group.note)
            note.setObjectName("PageBlurb")
            note.setWordWrap(True)
            lay.addWidget(note)

        for f in group.fields:
            row = FieldRow(f)
            row.changed.connect(lambda c=category, fl=f: self._on_row_changed(c, fl))
            self._rows[(category, f.key)] = row
            lay.addWidget(row)
        return card

    def _build_custom(self, kind: str, page):
        builder = {
            "theme_gallery": self._build_theme_section,
            "providers": self._build_providers_section,
            "keyboard": self._build_keyboard_section,
            "github": self._build_github_section,
            "advanced": self._build_advanced_section,
            "ai_model_defaults": self._build_model_defaults_section,
            "general_extras": self._build_general_extras_section,
        }.get(kind)
        return None if builder is None else builder()

    # ── value plumbing ──────────────────────────────────────────────────────
    def _load_all(self):
        for (category, key), row in self._rows.items():
            stored = self.settings.get(category, key,
                                       self.settings.get_default(category, key))
            row.set_value(stored)
        # Shortcut rows live outside self._rows (they're keyed by action, not by
        # a schema field), so reload them explicitly — otherwise "Reset this
        # page" on Keyboard would rewrite the file but leave the UI stale.
        stored = self.settings.get("keyboard", "shortcuts", {}) or {}
        for action, row in getattr(self, "_shortcut_rows", {}).items():
            row.set_value(stored.get(action, []))
        self._update_dependencies()

    def _on_row_changed(self, category: str, field: Field):
        row = self._rows.get((category, field.key))
        if row is None:
            return
        value = row.value()
        self.settings.set(category, field.key, value)
        self.setting_changed.emit(category, field.key, value)
        self._update_dependencies()
        self._flash(f"Saved {category}.{field.key}")

    def _update_dependencies(self):
        """Enable/disable rows whose `depends_on` master toggle is off."""
        for (category, key), row in self._rows.items():
            master = row.field.depends_on
            if not master:
                continue
            parent = self._rows.get((category, master))
            row.set_enabled_state(bool(parent.value()) if parent else True)

    def _flash(self, message: str):
        self._status.setText(message)

    # ── navigation & search ─────────────────────────────────────────────────
    def show_page(self, name: str):
        """Jump to a page by its schema name (e.g. "appearance")."""
        for i, page in enumerate(PAGES):
            if page.name == name:
                self._search.clear()
                self._list.setCurrentRow(i)
                return

    def _on_category(self, row: int):
        item = self._list.item(row)
        if item is None:
            return
        name = item.data(Qt.UserRole)
        if name in self._page_index:
            self._stack.setCurrentIndex(self._page_index[name])

    def _filter(self, text: str):
        """Hide categories that don't mention the query; jump to the first hit."""
        first = -1
        for i, page in enumerate(PAGES):
            hit = search_hits(page, text)
            self._list.item(i).setHidden(not hit)
            if hit and first < 0:
                first = i
        if first >= 0 and self._list.currentItem() is not None \
                and self._list.currentItem().isHidden():
            self._list.setCurrentRow(first)

    def _reset_current_page(self):
        page = PAGES[self._list.currentRow()] if 0 <= self._list.currentRow() < len(PAGES) else None
        if page is None:
            return
        confirm = QMessageBox.question(
            self, "Reset settings",
            f"Restore every setting on the {page.label} page to its default?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return
        self.settings.reset_category(page.cat)
        self._load_all()
        self._flash(f"{page.label} reset to defaults")

    # ── custom section: themes ──────────────────────────────────────────────
    def _build_theme_section(self) -> QWidget:
        card = QFrame()
        card.setObjectName("SettingsGroup")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(Spacing.xl, Spacing.lg, Spacing.xl, Spacing.lg)
        lay.setSpacing(Spacing.lg)

        head = QLabel("Theme")
        head.setObjectName("GroupTitle")
        lay.addWidget(head)

        self._gallery = ThemeGallery(self._current_theme)
        self._gallery.theme_picked.connect(self._on_theme_picked)
        lay.addWidget(self._gallery)
        return card

    def _on_theme_picked(self, name: str):
        """Persist the choice and let the window restyle the running app."""
        self._current_theme = name
        self.settings.set("general", "theme", name)
        self.theme_selected.emit(name)
        info = THEME_META.get(name)
        self._flash(f"Theme: {info.label if info else name}")

    def set_current_theme(self, name: str):
        self._current_theme = name
        if self._gallery is not None:
            self._gallery.set_current(name)

    def refresh_theme(self):
        """Re-skin the dialog itself after the app theme changed."""
        self._apply_style()
        if self._gallery is not None:
            self._gallery.refresh_theme()
        for row in self._rows.values():
            row._apply_style()
        for i in range(self._list.count()):
            page = PAGES[i]
            self._list.item(i).setIcon(make_icon(page.icon, 18))

    # ── custom section: providers & keys ────────────────────────────────────
    def _build_providers_section(self) -> QWidget:
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(Spacing.lg)

        if self._registry is None:
            lay.addWidget(self._notice(
                "The provider registry isn't available in this window, so keys "
                "can't be edited here. Open Settings from the main window."))
            return wrap

        lay.addWidget(self._notice(
            "Keys are written to config/providers/*.json in plain text today. "
            "Treat that directory as a secret and keep it out of version "
            "control until keyring storage lands."))

        providers = self._registry.get_all_providers()
        if not providers:
            lay.addWidget(self._notice("No providers are configured yet."))
            return wrap

        for name in sorted(providers):
            lay.addWidget(ProviderCard(name, providers[name], self._registry,
                                       self._manager, self._flash))
        return wrap

    def _notice(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SettingsNotice")
        label.setWordWrap(True)
        return label

    # ── custom section: keyboard shortcuts ──────────────────────────────────
    def _build_keyboard_section(self) -> QWidget:
        """One shortcut row per action, generated from the stored dict."""
        card = QFrame()
        card.setObjectName("SettingsGroup")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(Spacing.xl, Spacing.lg, Spacing.xl, Spacing.lg)
        lay.setSpacing(0)

        head = QLabel("Shortcuts")
        head.setObjectName("GroupTitle")
        lay.addWidget(head)

        stored = self.settings.get("keyboard", "shortcuts", {}) or {}
        actions = list(ACTION_LABELS) + [a for a in stored if a not in ACTION_LABELS]
        self._shortcut_rows = {}
        for action in actions:
            f = Field(action, ACTION_LABELS.get(action, action.replace("_", " ").title()),
                      "shortcut")
            row = FieldRow(f)
            row.set_value(stored.get(action, []))
            row.changed.connect(lambda a=action: self._on_shortcut_changed(a))
            self._shortcut_rows[action] = row
            lay.addWidget(row)
        return card

    def _on_shortcut_changed(self, action: str):
        row = self._shortcut_rows[action]
        keys = row.value()
        clash = self._shortcut_clash(action, keys)
        self.settings.set_keyboard_shortcut(action, keys)
        self.setting_changed.emit("keyboard", "shortcuts", {action: keys})
        if clash:
            # Don't block the edit — just say who else answers to this chord.
            self._flash(f"Warning: {' '.join(keys)} is also bound to "
                        f"{ACTION_LABELS.get(clash, clash)}")
        else:
            self._flash(f"Shortcut saved: {' '.join(keys) or 'none'}")

    def _shortcut_clash(self, action: str, keys: list) -> str:
        if not keys:
            return ""
        mine = [k.lower() for k in keys]
        for other, row in self._shortcut_rows.items():
            if other == action:
                continue
            if [k.lower() for k in row.value()] == mine:
                return other
        return ""

    # ── custom section: GitHub ──────────────────────────────────────────────
    def _build_github_section(self) -> QWidget:
        from ui.dialogs.settings_schema import Group, BRANCHES
        group = Group("GitHub", (
            Field("enabled", "Enable GitHub integration", "bool"),
            Field("username", "Username", "text", placeholder="octocat",
                  depends_on="enabled"),
            Field("token", "Personal access token", "secret",
                  "Needs repo scope. Stored in config/settings.json — plain "
                  "text for now.", placeholder="ghp_…", depends_on="enabled"),
            Field("default_branch", "Default branch", "choice",
                  options=BRANCHES, depends_on="enabled"),
        ))
        return self._build_group("github", group)

    # ── custom section: default model ───────────────────────────────────────
    def _build_model_defaults_section(self) -> QWidget:
        """Default model picker, populated from live provider discovery."""
        from ui.dialogs.settings_schema import Group
        options = [("auto", "Auto — route by task type")]
        for name, provider in (self._registry.get_all_providers().items()
                               if self._registry else []):
            try:
                for model_id in provider.get_models():
                    options.append((f"{name}:{model_id}", f"{model_id}  ({name})"))
            except Exception:
                continue
        group = Group("Model", (
            Field("default_model", "Default model", "choice",
                  "Auto picks per task: a fast model for chat, a stronger one "
                  "for planning and edits.", options=tuple(options)),
            Field("banned_models", "Never use these models", "list",
                  "One name or substring per line."),
            Field("routing_policy", "Automatic routing", "choice",
                  "Local only never sends automatic requests to cloud providers.",
                  options=(("local_only", "Local only"),
                           ("automatic", "Local preferred, cloud allowed"))),
        ))
        return self._build_group("models", group)

    # ── custom section: general extras ──────────────────────────────────────
    def _build_general_extras_section(self) -> QWidget:
        return self._notice(
            "Theme lives on the Appearance page. Keyboard shortcuts have their "
            "own page. Everything here is stored in config/settings.json.")

    # ── custom section: advanced ────────────────────────────────────────────
    def _build_advanced_section(self) -> QWidget:
        from pathlib import Path
        card = QFrame()
        card.setObjectName("SettingsGroup")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(Spacing.xl, Spacing.lg, Spacing.xl, Spacing.lg)
        lay.setSpacing(Spacing.md)

        head = QLabel("Configuration")
        head.setObjectName("GroupTitle")
        lay.addWidget(head)

        config = Path("config").resolve()
        lay.addWidget(self._notice(
            f"Settings file: {config / 'settings.json'}\n"
            f"Provider configs: {config / 'providers'}\n"
            f"Logs: {Path('logs').resolve() / 'app.log'}"))

        buttons = QHBoxLayout()
        buttons.setSpacing(Spacing.md)
        reveal = QPushButton("Open config folder")
        reveal.clicked.connect(lambda: self._reveal(config))
        buttons.addWidget(reveal)

        reset = QPushButton("Reset all settings…")
        reset.setObjectName("DangerButton")
        reset.clicked.connect(self._reset_everything)
        buttons.addWidget(reset)
        buttons.addStretch(1)
        lay.addLayout(buttons)
        return card

    def _reveal(self, path):
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _reset_everything(self):
        confirm = QMessageBox.warning(
            self, "Reset all settings",
            "Every setting returns to its factory default. Provider API keys "
            "are stored separately and are not touched.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return
        self.settings.reset_to_defaults()
        self._load_all()
        theme = self.settings.get("general", "theme", "graphite")
        if theme in PALETTES:
            self.set_current_theme(theme)
            self.theme_selected.emit(theme)
        self._flash("All settings reset to defaults")

    # ── style ───────────────────────────────────────────────────────────────
    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #SettingsDialog {{ background: {c.canvas}; }}
            #SettingsSidebar {{
                background: {c.surface};
                border-right: 1px solid {c.border_subtle};
            }}
            #SettingsFooter {{
                background: {c.surface};
                border-top: 1px solid {c.border_subtle};
            }}
            #SettingsStatus {{
                color: {c.text_muted};
                font-size: {FontSize.small}px;
            }}
            #SettingsSearch {{
                background: {c.surface_inset};
                border: 1px solid {c.border};
                border-radius: {Radius.md}px;
                padding: 6px 8px;
                color: {c.text_primary};
            }}
            #SettingsSearch:focus {{ border-color: {c.accent}; }}
            #SettingsCategories {{
                background: transparent;
                border: none;
                outline: none;
            }}
            #SettingsCategories::item {{
                color: {c.text_secondary};
                padding: 7px 8px;
                border-radius: {Radius.md}px;
            }}
            #SettingsCategories::item:hover {{
                background: {c.surface_overlay};
                color: {c.text_primary};
            }}
            #SettingsCategories::item:selected {{
                background: {c.accent_muted};
                color: {c.text_primary};
            }}
            #PageTitle {{
                color: {c.text_primary};
                font-size: {FontSize.xl}px;
                font-weight: {FontWeight.semibold};
            }}
            #PageBlurb {{
                color: {c.text_muted};
                font-size: {FontSize.base}px;
            }}
            #SettingsGroup {{
                background: {c.surface};
                border: 1px solid {c.border_subtle};
                border-radius: {Radius.lg}px;
            }}
            #GroupTitle {{
                color: {c.text_secondary};
                font-size: {FontSize.small}px;
                font-weight: {FontWeight.semibold};
                padding-bottom: {Spacing.sm}px;
            }}
            #SettingsNotice {{
                color: {c.text_muted};
                background: {c.surface_raised};
                border: 1px solid {c.border_subtle};
                border-left: 3px solid {c.warning};
                border-radius: {Radius.md}px;
                padding: {Spacing.lg}px;
                font-size: {FontSize.small}px;
            }}
            QCheckBox::indicator {{
                width: 16px; height: 16px;
                border: 1px solid {c.border_strong};
                border-radius: {Radius.sm}px;
                background: {c.surface_inset};
            }}
            QCheckBox::indicator:checked {{
                background: {c.accent};
                border-color: {c.accent};
            }}
            QPushButton {{
                background: {c.surface_raised};
                border: 1px solid {c.border};
                border-radius: {Radius.md}px;
                padding: 6px 14px;
                color: {c.text_primary};
            }}
            QPushButton:hover {{ background: {c.surface_overlay}; }}
            #PrimaryButton {{
                background: {c.accent};
                border-color: {c.accent};
                color: {c.text_on_accent};
            }}
            #PrimaryButton:hover {{ background: {c.accent_hover}; }}
            #DangerButton {{ color: {c.error}; border-color: {c.error}; }}
            QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit, QPlainTextEdit,
            QKeySequenceEdit {{
                background: {c.surface_inset};
                border: 1px solid {c.border};
                border-radius: {Radius.md}px;
                padding: 5px 8px;
                color: {c.text_primary};
                selection-background-color: {c.accent};
            }}
            QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus,
            QLineEdit:focus, QPlainTextEdit:focus {{ border-color: {c.accent}; }}
            QComboBox QAbstractItemView {{
                background: {c.surface_overlay};
                border: 1px solid {c.border};
                selection-background-color: {c.accent_muted};
                color: {c.text_primary};
            }}
            QScrollArea {{ background: transparent; border: none; }}
        """)


class ProviderCard(QFrame):
    """Enable toggle, base URL, API key and a live connection test."""

    def __init__(self, name, provider, registry, manager, flash, parent=None):
        super().__init__(parent)
        self._name = name
        self._provider = provider
        self._registry = registry
        self._manager = manager
        self._flash = flash
        self.setObjectName("SettingsGroup")

        cfg = provider.config
        needs_key = getattr(cfg.auth_type, "value", str(cfg.auth_type)) != "none"

        lay = QVBoxLayout(self)
        lay.setContentsMargins(Spacing.xl, Spacing.lg, Spacing.xl, Spacing.lg)
        lay.setSpacing(0)

        header = QHBoxLayout()
        header.setSpacing(Spacing.md)
        title = QLabel(name)
        title.setObjectName("GroupTitle")
        header.addWidget(title)
        self._state = QLabel()
        self._state.setObjectName("PageBlurb")
        header.addWidget(self._state)
        header.addStretch(1)
        lay.addLayout(header)

        self._enabled = FieldRow(Field("enabled", "Enabled", "bool"))
        self._enabled.set_value(bool(cfg.enabled))
        self._enabled.changed.connect(self._on_enabled)
        lay.addWidget(self._enabled)

        self._endpoint = FieldRow(Field(
            "endpoint", "Base URL", "text",
            "Point this at a proxy, a self-hosted server or a compatible API.",
            placeholder="https://api.example.com/v1"))
        self._endpoint.set_value(cfg.endpoint or "")
        self._endpoint.changed.connect(self._on_endpoint)
        lay.addWidget(self._endpoint)

        if needs_key:
            self._key = FieldRow(Field(
                "api_key", "API key", "secret",
                "Saved to config/providers/%s.json." % name,
                placeholder="Paste a key to change it"))
            self._key.set_value(cfg.api_key or "")
            self._key.changed.connect(self._on_key)
            lay.addWidget(self._key)
        else:
            self._key = None
            lay.addWidget(QLabel("Local provider — no API key needed."))

        self._option_rows = {}
        if name == "llama_cpp":
            for key, label, hint, placeholder in (
                ("model_directory", "GGUF model directory",
                 "Models are discovered locally and are never queried from Ollama.",
                 r"D:\llama_models"),
                ("server_executable", "llama-server executable",
                 "Leave empty to resolve llama-server from PATH.",
                 r"C:\path\to\llama-server.exe"),
            ):
                row = FieldRow(Field(key, label, "path", hint, placeholder=placeholder))
                row.set_value(str(cfg.options.get(key, "")))
                row.changed.connect(lambda k=key, r=row: self._on_option(k, r.value()))
                self._option_rows[key] = row
                lay.addWidget(row)

        actions = QHBoxLayout()
        actions.setSpacing(Spacing.md)
        test = QPushButton("Test connection")
        test.clicked.connect(self._on_test)
        actions.addWidget(test)
        refresh = QPushButton("Refresh models")
        refresh.clicked.connect(self._on_refresh)
        actions.addWidget(refresh)
        actions.addStretch(1)
        lay.addLayout(actions)

        self._update_state()

    # -- state ---------------------------------------------------------------
    def _update_state(self):
        try:
            connected = self._provider.is_connected()
            count = len(self._provider.get_models() or {})
        except Exception:
            connected, count = False, 0
        dot = "Connected" if connected else "Not connected"
        self._state.setText(f"· {dot} · {count} model(s)")

    def _persist(self):
        """Write the edited config back to config/providers/<name>.json."""
        try:
            self._registry._save_provider_config(self._provider)
        except Exception as exc:
            self._flash(f"Could not save {self._name}: {exc}")

    # -- handlers ------------------------------------------------------------
    def _on_enabled(self):
        want = bool(self._enabled.value())
        if self._manager is not None:
            (self._manager.enable_provider if want
             else self._manager.disable_provider)(self._name)
        else:
            self._provider.config.enabled = want
            self._persist()
        self._flash(f"{self._name} {'enabled' if want else 'disabled'}")
        self._update_state()

    def _on_endpoint(self):
        self._provider.config.endpoint = self._endpoint.value().strip()
        self._persist()
        # The manager's config watcher notices the hash change within ~5s and
        # reconnects, so no explicit reconnect is needed here.
        self._flash(f"{self._name} base URL saved")

    def _on_key(self):
        self._provider.config.api_key = self._key.value().strip()
        self._persist()
        self._flash(f"{self._name} API key saved")

    def _on_option(self, key, value):
        self._provider.config.options[key] = str(value).strip()
        self._persist()
        self._flash(f"{self._name} {key.replace('_', ' ')} saved")

    def _on_test(self):
        try:
            ok = (self._manager.test_connection(self._name)
                  if self._manager is not None else self._provider.test_connection())
        except Exception as exc:
            self._flash(f"{self._name}: {exc}")
            return
        self._flash(f"{self._name}: {'connection OK' if ok else 'connection failed'}")
        self._update_state()

    def _on_refresh(self):
        try:
            if self._manager is not None:
                found = self._manager.refresh_models(self._name).get(self._name, [])
            else:
                models = self._provider.refresh_models()
                self._provider._set_models(models)
                found = [m.get("id", m.get("name", "")) for m in models]
        except Exception as exc:
            self._flash(f"{self._name}: {exc}")
            return
        self._flash(f"{self._name}: {len(found)} model(s) found")
        self._update_state()


# ============================================================================
# SECTION: ui.dialogs.change_review_dialog (ui/dialogs/change_review_dialog.py)
# ============================================================================
"""
change_review_dialog.py — Multi-file agentic edit review UI (Phase 2 item 10).

The agent proposes a :class:`ChangeSet` spanning several files. This dialog lets
the user review a combined, side-by-side diff and accept or reject changes at
two granularities:

  * per file  — tick/untick a file to include or drop it wholesale
  * per hunk  — for modified files, tick/untick individual change hunks

Accepted changes are re-assembled by :class:`ReviewModel` into a filtered
ChangeSet and applied through :class:`ChangeApplier`, which creates a rollback
checkpoint first. The right pane always reflects the *effective* result (only
the currently-accepted hunks), so the preview matches exactly what will land.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QLabel, QWidget, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal

from ui.design_system import get_design_system, Spacing, FontSize
from ui.widgets.controls import TextButton, SectionHeader
from ui.widgets.diff_view import DiffView

_OP_LABEL = {}


def _ensure_editing_imports():
    global ChangeSet, OperationType, ReviewModel, ChangeRequest, ChangePriority, ChangeApplier, _OP_LABEL
    if _OP_LABEL:
        return
    from ai.editing.change_set import ChangeSet as _CS, OperationType as _OT
    from ai.editing.review_model import ReviewModel as _RM
    from ai.editing.change_request import ChangeRequest as _CR, ChangePriority as _CP
    from ai.editing.change_applier import ChangeApplier as _CA
    ChangeSet, OperationType, ReviewModel = _CS, _OT, _RM
    ChangeRequest, ChangePriority, ChangeApplier = _CR, _CP, _CA
    _OP_LABEL.update({
        OperationType.CREATE: ("＋", "created"),
        OperationType.DELETE: ("－", "deleted"),
        OperationType.MODIFY: ("✎", "modified"),
        OperationType.RENAME: ("→", "renamed"),
        OperationType.MOVE:   ("→", "moved"),
    })

# Roles for locating model indices back from tree items.
_ROLE_OP = Qt.UserRole + 1
_ROLE_HUNK = Qt.UserRole + 2


class ChangeReviewDialog(QDialog):
    """Review + accept/reject a multi-file change set, then apply it."""

    applied = Signal(object)  # emits ApplyResult

    def __init__(self, change_set: ChangeSet, project_root: str,
                 event_bus=None, user_prompt: str = "", parent=None):
        super().__init__(parent)
        _ensure_editing_imports()
        self.setObjectName("ChangeReviewDialog")
        self.setWindowTitle("Review proposed changes")
        self.resize(1000, 640)
        self._model = ReviewModel(change_set, project_root)
        self._root = project_root
        self._event_bus = event_bus
        self._prompt = user_prompt
        self._build()
        self._populate()
        self._apply_style()
        self._update_summary()

    # ── construction ─────────────────────────────────────────────────────────
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(Spacing.lg, Spacing.lg, Spacing.lg, Spacing.lg)
        root.setSpacing(Spacing.md)

        self._header = SectionHeader("Review proposed changes")
        root.addWidget(self._header)

        splitter = QSplitter(Qt.Horizontal)

        self._tree = QTreeWidget()
        self._tree.setObjectName("ReviewTree")
        self._tree.setHeaderHidden(True)
        self._tree.setColumnCount(1)
        self._tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tree.setMinimumWidth(300)
        self._tree.itemChanged.connect(self._on_item_changed)
        self._tree.currentItemChanged.connect(self._on_current_changed)
        splitter.addWidget(self._tree)

        self._diff = DiffView()
        splitter.addWidget(self._diff)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 680])
        root.addWidget(splitter, 1)

        self._summary = QLabel("")
        self._summary.setProperty("role", "muted")
        root.addWidget(self._summary)

        btn_row = QWidget()
        br = QHBoxLayout(btn_row)
        br.setContentsMargins(0, 0, 0, 0)
        self._all_btn = TextButton("Accept All")
        self._all_btn.clicked.connect(lambda: self._set_all(True))
        self._none_btn = TextButton("Reject All")
        self._none_btn.clicked.connect(lambda: self._set_all(False))
        self._cancel_btn = TextButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        self._apply_btn = TextButton("Apply", variant="primary")
        self._apply_btn.clicked.connect(self._on_apply)
        br.addWidget(self._all_btn)
        br.addWidget(self._none_btn)
        br.addStretch(1)
        br.addWidget(self._cancel_btn)
        br.addWidget(self._apply_btn)
        root.addWidget(btn_row)

    # ── population ───────────────────────────────────────────────────────────
    def _populate(self) -> None:
        self._tree.blockSignals(True)
        self._tree.clear()
        for oi, op in enumerate(self._model.operations()):
            glyph, verb = _OP_LABEL.get(op.op_type, ("•", "changed"))
            path = op.source_path
            fitem = QTreeWidgetItem([f"{glyph}  {path}   ({verb})"])
            fitem.setFlags(fitem.flags() | Qt.ItemIsUserCheckable)
            fitem.setCheckState(
                0, Qt.Checked if self._model.is_op_selected(oi) else Qt.Unchecked)
            fitem.setData(0, _ROLE_OP, oi)
            fitem.setData(0, _ROLE_HUNK, -1)
            self._tree.addTopLevelItem(fitem)

            if op.op_type == OperationType.MODIFY and len(op.hunks) > 1:
                for hi, hunk in enumerate(op.hunks):
                    label = f"hunk @ line {hunk.old_start}"
                    hitem = QTreeWidgetItem([label])
                    hitem.setFlags(hitem.flags() | Qt.ItemIsUserCheckable)
                    hitem.setCheckState(
                        0, Qt.Checked if self._model.is_hunk_selected(oi, hi)
                        else Qt.Unchecked)
                    hitem.setData(0, _ROLE_OP, oi)
                    hitem.setData(0, _ROLE_HUNK, hi)
                    fitem.addChild(hitem)
                fitem.setExpanded(True)
        self._tree.blockSignals(False)
        if self._tree.topLevelItemCount():
            self._tree.setCurrentItem(self._tree.topLevelItem(0))

    # ── interaction ──────────────────────────────────────────────────────────
    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        oi = item.data(0, _ROLE_OP)
        hi = item.data(0, _ROLE_HUNK)
        if oi is None:
            return
        checked = item.checkState(0) == Qt.Checked
        self._tree.blockSignals(True)
        if hi is None or hi == -1:
            self._model.set_op_selected(oi, checked)
            # Cascade the visual state to child hunks.
            for c in range(item.childCount()):
                item.child(c).setCheckState(
                    0, Qt.Checked if checked else Qt.Unchecked)
        else:
            self._model.set_hunk_selected(oi, hi, checked)
            # Reflect the (possibly updated) parent op state.
            parent = item.parent()
            if parent is not None:
                poi = parent.data(0, _ROLE_OP)
                parent.setCheckState(
                    0, Qt.Checked if self._model.is_op_selected(poi)
                    else Qt.Unchecked)
        self._tree.blockSignals(False)
        self._show_current_diff()
        self._update_summary()

    def _on_current_changed(self, *_args) -> None:
        self._show_current_diff()

    def _set_all(self, value: bool) -> None:
        for oi in range(self._model.count()):
            self._model.set_op_selected(oi, value)
        self._populate()
        self._show_current_diff()
        self._update_summary()

    # ── preview ──────────────────────────────────────────────────────────────
    def _show_current_diff(self) -> None:
        item = self._tree.currentItem()
        if item is None:
            self._diff.clear()
            return
        oi = item.data(0, _ROLE_OP)
        if oi is None:
            self._diff.clear()
            return
        old = self._model.original_content(oi) or ""
        new = self._model.effective_content(oi)
        self._diff.set_texts(old, new if new is not None else "")

    def _update_summary(self) -> None:
        s = self._model.stats()
        self._summary.setText(
            f"{s['files']} file(s) · +{s['created']} created · "
            f"~{s['modified']} modified · −{s['deleted']} deleted · "
            f"{s['hunks']} hunk(s) accepted"
        )
        self._apply_btn.setEnabled(s["files"] > 0)

    # ── apply ────────────────────────────────────────────────────────────────
    def _on_apply(self) -> None:
        selected = self._model.selected_change_set()
        if not selected.operations:
            self.reject()
            return
        request = ChangeRequest.create(
            user_prompt=self._prompt or "Reviewed multi-file edit",
            files=list(selected.files),
            changes=[],
            reason="Applied from change-review dialog",
            priority=ChangePriority.NORMAL,
            metadata={"confirmed_destructive": True, "source": "review_dialog"},
        )
        applier = ChangeApplier(self._event_bus, self._root)
        result = applier.apply(selected, request)
        self.applied.emit(result)
        self.accept()

    # ── style ────────────────────────────────────────────────────────────────
    def _apply_style(self) -> None:
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #ChangeReviewDialog {{ background: {c.surface}; }}
            #ReviewTree {{
                background: {c.surface_inset}; color: {c.text_secondary};
                border: 1px solid {c.border_subtle}; border-radius: 4px;
                font-size: {FontSize.small}px; outline: none;
            }}
            #ReviewTree::item {{ padding: 3px 4px; }}
            #ReviewTree::item:selected {{
                background: {c.selection}; color: {c.text_primary};
            }}
        """)

    def refresh_theme(self) -> None:
        self._apply_style()
        self._diff.refresh_theme()



# ============================================================================
# SECTION: ui.dialogs.tool_confirmation_dialog (ui/dialogs/tool_confirmation_dialog.py)
# ============================================================================
"""
Tool Confirmation Dialog — v2.0 (PySide6)

Shown when the AI wants to run a tool/action that requires the user's approval.
Interface kept identical to what ai/integration/ai_ide_integration.py expects:

    ToolConfirmationDialog(confirmation_id, tool_name, action, message,
                           metadata, parent)
    signals: confirmed(str), denied(str)   # emit the confirmation_id
"""

import json

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
)
from PySide6.QtCore import Qt, Signal

from ui.design_system import get_design_system, Spacing, Radius, FontSize, FontFamily
from ui.widgets.controls import TextButton


class ToolConfirmationDialog(QDialog):

    confirmed = Signal(str)
    denied = Signal(str)

    def __init__(self, confirmation_id="", tool_name="", action="", message="",
                 metadata=None, parent=None):
        super().__init__(parent)
        self.confirmation_id = confirmation_id
        self.tool_name = tool_name
        self.action = action
        self.message = message
        self.metadata = metadata or {}
        self._decided = False

        self.setWindowTitle("Confirm AI Action")
        self.setModal(True)
        self.setMinimumWidth(480)
        self._build()
        self._apply_style()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(Spacing.xl, Spacing.xl, Spacing.xl, Spacing.xl)
        lay.setSpacing(Spacing.md)

        title = QLabel(f"{self.tool_name or 'Tool'} — {self.action or 'action'}")
        title.setObjectName("DialogTitle")
        title.setWordWrap(True)
        lay.addWidget(title)

        body = QLabel(self.message or "The assistant requests permission to proceed.")
        body.setWordWrap(True)
        body.setProperty("role", "muted")
        lay.addWidget(body)

        if self.metadata:
            details = QPlainTextEdit()
            details.setReadOnly(True)
            try:
                details.setPlainText(json.dumps(self.metadata, indent=2, default=str))
            except Exception:
                details.setPlainText(str(self.metadata))
            details.setFixedHeight(140)
            lay.addWidget(details)

        row = QHBoxLayout()
        row.addStretch(1)
        deny_btn = TextButton("Deny")
        deny_btn.clicked.connect(self._deny)
        approve_btn = TextButton("Approve", variant="primary")
        approve_btn.clicked.connect(self._approve)
        row.addWidget(deny_btn)
        row.addWidget(approve_btn)
        lay.addLayout(row)

    def _approve(self):
        self._decided = True
        self.confirmed.emit(self.confirmation_id)
        self.accept()

    def _deny(self):
        self._decided = True
        self.denied.emit(self.confirmation_id)
        self.reject()

    def reject(self):
        # Treat window-close / Esc as denial exactly once.
        if not self._decided:
            self._decided = True
            self.denied.emit(self.confirmation_id)
        super().reject()

    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            QDialog {{ background: {c.surface}; border: 1px solid {c.border}; }}
            #DialogTitle {{ font-size: {FontSize.lg}px; font-weight: 700; color: {c.text_primary}; }}
            QPlainTextEdit {{
                background: {c.surface_inset};
                border: 1px solid {c.border_subtle};
                border-radius: {Radius.md}px;
                font-family: {FontFamily.mono};
            }}
        """)

