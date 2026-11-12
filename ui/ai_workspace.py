"""
Consolidated Module: ui.ai_workspace

Combines: ui.panels.ai_workspace
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['ui.panels.ai_workspace']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ui.panels.ai_workspace (ui/panels/ai_workspace.py)
# ============================================================================
"""
AI Workspace — v2.1

The right-hand assistant panel: a streaming chat surface plus a
provider → model selector with API-key / base-URL setup for cloud providers.

Talks to the backend two ways:
  • EventBus (chat traffic):
      publishes : ai_chat_send {message, model_id}, ai_chat_switch_model {model_id},
                  ai_chat_cancel {}, ai_chat_new_session {}
      subscribes: ai_chat_streaming_started, ai_chat_chunk, ai_chat_streaming_complete,
                  ai_chat_error, ai_model_auto_selected
  • Direct object access (provider config) via `set_providers(registry, manager)`:
      lists providers, discovers models, and connects cloud providers with an API key.

Model ids are always emitted as "<provider>:<model>" (e.g. "ollama:qwen2.5-coder:7b"),
which the chat engine splits on the first ":" to resolve provider + model.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox,
    QPlainTextEdit, QScrollArea, QFrame, QSizePolicy, QInputDialog, QLineEdit,
    QListWidget, QListWidgetItem, QFileDialog, QMenu, QApplication,
    QToolButton, QButtonGroup,
)
from PySide6.QtCore import Qt, Signal, QTimer

from ui.design_system import (get_design_system, AIPanel, Spacing, Radius,
                              FontSize, FontWeight)
from ui.widgets.controls import IconButton, TextButton, SectionHeader, hline, Pill
from ui.widgets.icons import icon
def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4) if text else 0
from core.logger import setup_logger

from pathlib import Path
import json
import threading
import time

logger = setup_logger(__name__)


def _render_markdown_prose(text: str) -> str:
    """Render inline markdown (inline code, bold, linebreaks) for prose sections."""
    import html
    import re
    if not text:
        return ""
    c = get_design_system().colors
    esc = html.escape(text)
    esc = re.sub(r"`([^`]+)`",
                 rf'<code style="background:{c.surface_inset};padding:1px 4px;border-radius:3px;font-family:monospace;">\1</code>', esc)
    esc = re.sub(r"\*\*([^\*]+)\*\*", r"<b>\1</b>", esc)
    esc = esc.replace("\n", "<br>")
    return esc


def _render_markdown_prose(text: str) -> str:
    """Render inline markdown (inline code, bold, linebreaks) for prose sections."""
    import html
    import re
    if not text:
        return ""
    c = get_design_system().colors
    esc = html.escape(text)
    esc = re.sub(r"`([^`]+)`",
                 rf'<code style="background:{c.surface_inset};padding:1px 4px;border-radius:3px;font-family:monospace;">\1</code>', esc)
    esc = re.sub(r"\*\*([^\*]+)\*\*", r"<b>\1</b>", esc)
    esc = esc.replace("\n", "<br>")
    return esc


def _render_markdown(text: str) -> str:
    """Backward-compatible markdown renderer for plain HTML contexts."""
    import html
    import re
    if not text:
        return ""
    c = get_design_system().colors
    parts = text.split("```")
    out = []
    for i, seg in enumerate(parts):
        if i % 2 == 1:
            body = seg
            if "\n" in seg:
                first, rest = seg.split("\n", 1)
                if first.strip() and " " not in first.strip():
                    body = rest
            esc = html.escape(body.strip("\n"))
            out.append(
                f'<pre style="background:{c.surface_inset};'
                f'border:1px solid {c.border_subtle};border-radius:4px;'
                f'padding:6px;white-space:pre-wrap;font-family:monospace;">{esc}</pre>')
        else:
            out.append(_render_markdown_prose(seg))
    return "".join(out)


class _CodeBlockWidget(QFrame):
    """Dedicated code snippet card with language badge and a direct 'Copy Code' button.

    Lets the user copy ONLY the code directly without including conversational text.
    """

    def __init__(self, code: str, lang: str = "", parent=None):
        super().__init__(parent)
        self._code = code
        self._lang = lang.strip() or "code"
        self.setObjectName("AICodeBlock")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header bar: Language badge (left) + Direct Copy Button (right)
        hdr = QWidget()
        hdr.setObjectName("AICodeBlockHeader")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(10, 4, 8, 4)
        hl.setSpacing(8)

        lang_lbl = QLabel(self._lang.lower())
        lang_lbl.setObjectName("AICodeBlockLang")
        hl.addWidget(lang_lbl)
        hl.addStretch(1)

        self._apply_btn = QToolButton()
        self._apply_btn.setObjectName("AICodeApplyBtn")
        self._apply_btn.setText("Apply to File")
        self._apply_btn.setIcon(icon("check", 13))
        self._apply_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._apply_btn.setCursor(Qt.PointingHandCursor)
        self._apply_btn.setToolTip("Create or update this file in the active workspace and open in editor")
        self._apply_btn.clicked.connect(self._apply_code_to_workspace)
        hl.addWidget(self._apply_btn)

        self._run_btn = QToolButton()
        self._run_btn.setObjectName("AICodeRunBtn")
        self._run_btn.setText("Run")
        self._run_btn.setIcon(icon("play", 12))
        self._run_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._run_btn.setCursor(Qt.PointingHandCursor)
        self._run_btn.setToolTip("Apply this code block to the workspace and execute/verify it")
        self._run_btn.clicked.connect(self._run_code_in_workspace)
        hl.addWidget(self._run_btn)

        self._copy_btn = QToolButton()
        self._copy_btn.setObjectName("AICodeCopyBtn")
        self._copy_btn.setText("Copy")
        self._copy_btn.setIcon(icon("copy", 13))
        self._copy_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._copy_btn.setCursor(Qt.PointingHandCursor)
        self._copy_btn.setToolTip("Copy code directly to clipboard")
        self._copy_btn.clicked.connect(self._copy_code)
        hl.addWidget(self._copy_btn)

        lay.addWidget(hdr)

        # Code content area
        self._code_view = QPlainTextEdit()
        self._code_view.setObjectName("AICodeView")
        self._code_view.setReadOnly(True)
        self._code_view.setPlainText(self._code)
        self._code_view.setLineWrapMode(QPlainTextEdit.NoWrap)

        font = self._code_view.font()
        font.setFamily("Consolas, Menlo, Monaco, Courier New, monospace")
        font.setPointSize(9)
        self._code_view.setFont(font)

        line_count = max(1, self._code.count("\n") + 1)
        target_h = min(420, max(56, line_count * 18 + 18))
        self._code_view.setFixedHeight(target_h)
        if target_h < 420:
            self._code_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            self._code_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._code_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        lay.addWidget(self._code_view)
        self._apply_style()

    def _copy_code(self):
        clip_fn = getattr(QApplication, "clipboard", None)
        if callable(clip_fn):
            cb = clip_fn()
            if cb is not None and hasattr(cb, "setText"):
                cb.setText(self._code)
        self._copy_btn.setText("Copied!")
        self._copy_btn.setIcon(icon("check", 13))
        c = get_design_system().colors
        accent_color = getattr(c, "success", getattr(c, "accent", "#10b981"))
        self._copy_btn.setStyleSheet(f"color: {accent_color}; font-weight: bold;")
        QTimer.singleShot(1800, self._reset_copy_btn)

    def _reset_copy_btn(self):
        self._copy_btn.setText("Copy")
        self._copy_btn.setIcon(icon("copy", 13))
        self._copy_btn.setStyleSheet("")

    def _apply_code_to_workspace(self):
        curr = self.parent()
        while curr is not None:
            pub = getattr(curr, "_publish", None)
            if callable(pub):
                pub("ai_apply_code_block", {"code": self._code, "lang": self._lang})
                break
            curr = curr.parent() if hasattr(curr, "parent") and callable(curr.parent) else None
        self._apply_btn.setText("Applied ✓")
        c = get_design_system().colors
        accent_color = getattr(c, "success", getattr(c, "accent", "#10b981"))
        self._apply_btn.setStyleSheet(f"color: {accent_color}; font-weight: bold;")
        QTimer.singleShot(2200, self._reset_apply_btn)

    def _reset_apply_btn(self):
        self._apply_btn.setText("Apply to File")
        self._apply_btn.setStyleSheet("")

    def _run_code_in_workspace(self):
        curr = self.parent()
        while curr is not None:
            pub = getattr(curr, "_publish", None)
            if callable(pub):
                pub("ai_run_code_block", {"code": self._code, "lang": self._lang})
                break
            curr = curr.parent() if hasattr(curr, "parent") and callable(curr.parent) else None
        self._run_btn.setText("Running…")
        QTimer.singleShot(1800, self._reset_run_btn)

    def _reset_run_btn(self):
        self._run_btn.setText("Run")
        self._run_btn.setStyleSheet("")

    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #AICodeBlock {{
                background: {c.surface_inset};
                border: 1px solid {c.border_subtle};
                border-radius: 6px;
                margin-top: 4px;
                margin-bottom: 6px;
            }}
            #AICodeBlockHeader {{
                background: {c.surface_raised};
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                border-bottom: 1px solid {c.border_subtle};
            }}
            #AICodeBlockLang {{
                color: {c.text_muted};
                font-size: {FontSize.tiny}px;
                font-weight: {FontWeight.semibold};
                letter-spacing: 0.5px;
            }}
            #AICodeRunBtn {{
                background: transparent;
                color: {c.text_secondary};
                border: 1px solid {c.border_subtle};
                border-radius: 4px;
                padding: 2px 7px;
                font-size: {FontSize.tiny}px;
                font-weight: {FontWeight.medium};
            }}
            #AICodeRunBtn:hover {{
                background: {c.surface_overlay};
                color: {c.accent};
                border-color: {c.accent};
            }}
            #AICodeApplyBtn {{
                background: transparent;
                color: {c.accent};
                border: 1px solid {c.border_subtle};
                border-radius: 4px;
                padding: 2px 8px;
                font-size: {FontSize.tiny}px;
                font-weight: {FontWeight.semibold};
            }}
            #AICodeApplyBtn:hover {{
                background: {c.accent_muted};
                color: {c.accent};
                border-color: {c.accent};
            }}
            #AICodeCopyBtn {{
                background: transparent;
                color: {c.text_muted};
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: {FontSize.tiny}px;
                font-weight: {FontWeight.medium};
            }}
            #AICodeCopyBtn:hover {{
                background: {c.surface_overlay};
                color: {c.text_primary};
                border-color: {c.border_subtle};
            }}
            #AICodeView {{
                background: transparent;
                color: {c.text_primary};
                border: none;
                padding: 4px 6px;
                font-family: Consolas, Menlo, Monaco, Courier New, monospace;
            }}
        """)

    def refresh_theme(self):
        self._apply_style()


class _Bubble(QFrame):
    def __init__(self, role: str, text: str = "", parent=None):
        super().__init__(parent)
        self._role = role
        self.setObjectName("UserBubble" if role == "user" else "AssistantBubble")
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(Spacing.lg, Spacing.md, Spacing.lg, Spacing.md)
        self._lay.setSpacing(Spacing.xs)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        who = QLabel("You" if role == "user" else "Assistant")
        who.setObjectName("BubbleRole")
        top.addWidget(who)
        top.addStretch(1)
        # Message-level copy button (copies entire transcript message)
        self._copy_btn = IconButton("copy", "Copy entire message", size=20, icon_size=13)
        self._copy_btn.clicked.connect(self._copy)
        top.addWidget(self._copy_btn)
        self._lay.addLayout(top)

        # Dynamic content container supporting both prose text and code blocks
        self._code_blocks: list[_CodeBlockWidget] = []
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(Spacing.xs)

        self._body = QLabel(text)
        self._raw = text
        self._body.setWordWrap(True)
        self._body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._body.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self._content_layout.addWidget(self._body)

        self._lay.addWidget(self._content_widget)

        # Per-message token footer (assistant messages only, filled on complete)
        self._footer = QLabel("")
        self._footer.setObjectName("BubbleFooter")
        self._footer.setVisible(False)
        self._lay.addWidget(self._footer)

        if text and "```" in text:
            self.finalize()

    def append(self, chunk: str):
        # Plain text while streaming (cheap); rich rendering happens on finalize.
        self._raw += chunk
        self._body.setTextFormat(Qt.PlainText)
        self._body.setText(self._raw)

    def set_live_process(self, headline: str, detail: str = ""):
        """Render a live, Gemini/ChatGPT/Cursor-style process status header while the Agent is working."""
        import html as _html
        h_esc = _html.escape(headline or "Working…")
        d_esc = _html.escape(detail or "")
        c = get_design_system().colors
        accent = getattr(c, "accent", "#1a633e")
        muted = getattr(c, "text_secondary", "#5c5a54")
        html_status = (
            f"<div style='line-height:1.45;'>"
            f"<span style='color:{accent}; font-weight:600;'>⚡ {h_esc}</span>"
            + (f"<br><span style='color:{muted}; font-size:11px;'>{d_esc}</span>" if d_esc else "")
            + "</div>"
        )
        self._body.setTextFormat(Qt.RichText)
        self._body.setText(html_status)
        self._body.setVisible(True)

    def set_summary_markdown(self, markdown_text: str):
        """Replace bubble content with the clean completed Agent Process Summary."""
        self._raw = markdown_text or ""
        self.finalize()

    def text(self) -> str:
        return self._raw

    def finalize(self):
        """Re-render accumulated text into prose and dedicated code block widgets."""
        if "```" not in self._raw:
            html = _render_markdown_prose(self._raw)
            if html:
                self._body.setTextFormat(Qt.RichText)
                self._body.setText(html)
                self._body.setVisible(True)
            return

        # Clear initial body / previous widgets in content layout
        self._code_blocks.clear()
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        parts = self._raw.split("```")
        for i, seg in enumerate(parts):
            if i % 2 == 1:  # Fenced code block
                lang = ""
                code_body = seg
                if "\n" in seg:
                    first, rest = seg.split("\n", 1)
                    if first.strip() and " " not in first.strip() and len(first.strip()) <= 20:
                        lang = first.strip()
                        code_body = rest
                clean_code = code_body.strip("\r\n")
                code_widget = _CodeBlockWidget(clean_code, lang=lang, parent=self)
                self._code_blocks.append(code_widget)
                self._content_layout.addWidget(code_widget)
            else:  # Prose segment
                prose = seg.strip("\r\n")
                if prose:
                    html = _render_markdown_prose(prose)
                    lbl = QLabel()
                    lbl.setTextFormat(Qt.RichText)
                    lbl.setText(html)
                    lbl.setWordWrap(True)
                    lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
                    lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
                    self._content_layout.addWidget(lbl)

    def set_footer(self, text: str):
        if text:
            self._footer.setText(text)
            self._footer.setVisible(True)

    def _copy(self):
        clip_fn = getattr(QApplication, "clipboard", None)
        if callable(clip_fn):
            cb = clip_fn()
            if cb is not None and hasattr(cb, "setText"):
                cb.setText(self._raw)

    def refresh_theme(self):
        for cb in self._code_blocks:
            cb.refresh_theme()


class _ModeSwitch(QWidget):
    """A compact Chat / Edit / Agent segmented control.

    As the assistant gains autonomy, users need an obvious, always-visible dial
    for *how much rope* it has — safe Q&A, reviewable edits, or full agent runs.
    Keeping it in the panel header (not buried in Settings) makes that control
    a deliberate, per-conversation choice.
    """

    mode_changed = Signal(str)

    _MODES = (
        ("chat", "Chat", "Ask questions and discuss code — nothing is changed."),
        ("edit", "Edit", "Proposed file changes open in a diff for review."),
        ("agent", "Agent", "Autonomous multi-step planning, RepoMap context, and verified code edits."),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ModeSwitch")
        self._buttons: dict[str, QToolButton] = {}
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for mode, label, tip in self._MODES:
            b = QToolButton()
            b.setText(label)
            b.setToolTip(tip)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setProperty("seg", "true")
            b.clicked.connect(lambda _=False, m=mode: self._choose(m))
            self._group.addButton(b)
            self._buttons[mode] = b
            lay.addWidget(b)
        self._apply_style()

    def _choose(self, mode: str):
        self.set_mode(mode)
        self.mode_changed.emit(mode)

    def set_mode(self, mode: str):
        b = self._buttons.get(mode)
        if b is not None:
            b.setChecked(True)

    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #ModeSwitch QToolButton[seg="true"] {{
                background: {c.surface_inset};
                color: {c.text_muted};
                border: 1px solid {c.border};
                padding: 3px 11px;
                font-size: {FontSize.tiny}px;
                font-weight: {FontWeight.medium};
            }}
            #ModeSwitch QToolButton[seg="true"]:hover {{ color: {c.text_primary}; }}
            #ModeSwitch QToolButton[seg="true"]:checked {{
                background: {c.accent_muted};
                color: {c.text_primary};
                border-color: {c.accent_border};
            }}
        """)

    def refresh_theme(self):
        self._apply_style()



class AIWorkspace(QWidget):

    _OTHER = "Other model…"
    _LOCAL_HINTS = ("llama_cpp", "ollama", "local", "qwen")

    # Where the remembered Chat/Edit/Agent choice is persisted (relative to the
    # app's working dir, like the other config/*.json files).
    _MODE_FILE = Path("config/ai_panel.json")
    _MODES = ("chat", "edit", "agent")

    # Local servers (Ollama especially) are often not listening yet when the app
    # starts, so the first discovery attempt comes back empty. These control a
    # short retry burst so the list fills in on its own instead of being stuck
    # on "No models available" until the user restarts.
    _DISCOVERY_RETRY_MS = 4000
    _DISCOVERY_MAX_RETRIES = 8

    # Local models take seconds to load off disk. Asking for a warm-up the
    # moment the user shows intent (focuses the box, starts typing) usually
    # hides the whole load behind their typing. Re-asking more often than this
    # is pointless — the optimizer de-duplicates anyway.
    _WARM_MIN_INTERVAL_S = 20.0

    # The provider health monitor and recovery loop publish provider events
    # synchronously on *their own* threads. Touching a QComboBox from a non-GUI
    # thread is illegal in Qt, so those events are bounced through this signal,
    # which Qt delivers on the GUI thread.
    _provider_models_arrived = Signal(str, list)

    def __init__(self, event_bus=None, parent=None):
        super().__init__(parent)
        self.setObjectName("AIWorkspace")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.event_bus = event_bus
        self.provider_registry = None
        self.provider_manager = None
        self.chat_engine = None
        self._pending_chat_messages = []
        self._current_assistant: _Bubble | None = None
        self._streaming = False
        self._discovery_retries = 0
        self._discovery_timer: QTimer | None = None
        self._discovery_in_flight = False
        self._mode = self._load_mode()
        # Warm-up state, shown next to the model pill so a slow first reply is
        # legible instead of looking like a hang.
        self._warming = False
        self._warm_ready = False
        self._last_warm_request = 0.0
        self._last_emitted_model = ""
        self._model_diagnostics = ""

        self._build()
        self._apply_style()
        self._subscribe()
        self._provider_models_arrived.connect(self._apply_provider_models)

    # -- construction --------------------------------------------------------
    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        header = SectionHeader("AI Workspace")
        self._context_btn = IconButton("paperclip", "AI memory / context", size=24, icon_size=15)
        self._context_btn.clicked.connect(self._toggle_context)
        self._history_btn = IconButton("history", "Chat history", size=24, icon_size=15)
        self._history_btn.clicked.connect(self._toggle_history)
        self._new_btn = IconButton("plus", "New chat", size=24, icon_size=15)
        self._new_btn.clicked.connect(self._on_new_chat)
        header.add_action(self._context_btn)
        header.add_action(self._history_btn)
        header.add_action(self._new_btn)
        lay.addWidget(header)

        # Sub-header: the interaction-mode switch (left) and a compact model
        # "pill" (right). The pill replaces the two always-on Provider/Model
        # combos below — it shows the active model and toggles the full picker.
        sub = QWidget()
        subl = QHBoxLayout(sub)
        subl.setContentsMargins(Spacing.lg, 0, Spacing.lg, Spacing.xs)
        subl.setSpacing(Spacing.sm)
        self._mode_switch = _ModeSwitch()
        self._mode_switch.mode_changed.connect(self._on_mode_changed)
        subl.addWidget(self._mode_switch)
        subl.addStretch(1)
        self._model_pill = QToolButton()
        self._model_pill.setObjectName("ModelPill")
        self._model_pill.setText("Select model  ▾")
        self._model_pill.setCursor(Qt.PointingHandCursor)
        self._model_pill.setToolTip("Provider & model — click to change")
        self._model_pill.clicked.connect(self._toggle_model_panel)
        subl.addWidget(self._model_pill)
        lay.addWidget(sub)

        # A one-line notice that explains what the non-default modes do (and that
        # Agent isn't live yet). Hidden in plain Chat mode.
        self._mode_banner = QLabel("")
        self._mode_banner.setObjectName("ModeBanner")
        self._mode_banner.setWordWrap(True)
        self._mode_banner.setVisible(False)
        lay.addWidget(self._mode_banner)

        # Collapsible AI-memory + history panels (built once, hidden by default).
        self._context_panel = self._build_context_panel()
        self._context_panel.setVisible(False)
        lay.addWidget(self._context_panel)
        self._history_panel = self._build_history_panel()
        self._history_panel.setVisible(False)
        lay.addWidget(self._history_panel)

        # Provider + model selectors — tucked into a collapsible panel that the
        # header model pill toggles. Most sessions pick a model once, so the two
        # combos no longer need to occupy the panel permanently.
        self._model_panel = QFrame()
        self._model_panel.setObjectName("ModelPanel")
        mp = QVBoxLayout(self._model_panel)
        mp.setContentsMargins(0, 0, 0, 0)
        mp.setSpacing(0)

        sel = QWidget()
        grid = QGridLayout(sel)
        grid.setContentsMargins(Spacing.lg, Spacing.xs, Spacing.lg, Spacing.sm)
        grid.setHorizontalSpacing(Spacing.sm)
        grid.setVerticalSpacing(Spacing.xs)

        self._provider_combo = QComboBox()
        self._provider_combo.setToolTip("Select AI Provider")
        self._provider_combo.addItem("No providers")
        self._provider_combo.currentTextChanged.connect(self._on_provider_changed)

        self._model_combo = QComboBox()
        self._model_combo.setToolTip("Select Active AI Model")
        self._model_combo.addItem("No models available")
        self._model_combo.currentTextChanged.connect(self._on_model_changed)

        self._detect_btn = IconButton("refresh", "Auto-detect models", size=26, icon_size=15)
        self._detect_btn.clicked.connect(self._auto_detect)

        grid.addWidget(QLabel("Provider"), 0, 0)
        grid.addWidget(self._provider_combo, 0, 1, 1, 2)
        grid.addWidget(QLabel("Model"), 1, 0)
        grid.addWidget(self._model_combo, 1, 1)
        grid.addWidget(self._detect_btn, 1, 2)
        grid.setColumnStretch(1, 1)
        mp.addWidget(sel)

        # -- API-key / base-URL setup (only shown for cloud providers) -------
        self._auth_box = QWidget()
        self._auth_box.setObjectName("AuthBox")
        ag = QGridLayout(self._auth_box)
        ag.setContentsMargins(Spacing.lg, Spacing.xs, Spacing.lg, Spacing.sm)
        ag.setHorizontalSpacing(Spacing.sm)
        ag.setVerticalSpacing(Spacing.xs)

        self._key_edit = QLineEdit()
        self._key_edit.setEchoMode(QLineEdit.Password)
        self._key_edit.setPlaceholderText("Paste API key…")
        self._key_edit.returnPressed.connect(self._on_connect_clicked)

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("Base URL (optional — leave blank for default)")

        self._connect_btn = TextButton("Connect", variant="primary", tooltip="Connect to the selected AI provider")
        self._connect_btn.clicked.connect(self._on_connect_clicked)

        self._auth_status = QLabel("")
        self._auth_status.setObjectName("AuthStatus")
        self._auth_status.setWordWrap(True)

        ag.addWidget(QLabel("API Key"), 0, 0)
        ag.addWidget(self._key_edit, 0, 1)
        ag.addWidget(self._connect_btn, 0, 2)
        ag.addWidget(QLabel("Base URL"), 1, 0)
        ag.addWidget(self._url_edit, 1, 1, 1, 2)
        ag.addWidget(self._auth_status, 2, 0, 1, 3)
        ag.setColumnStretch(1, 1)
        mp.addWidget(self._auth_box)
        self._auth_box.setVisible(False)

        self._model_panel.setVisible(False)
        lay.addWidget(self._model_panel)

        lay.addWidget(hline())

        # Message scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._msg_host = QWidget()
        self._msg_layout = QVBoxLayout(self._msg_host)
        self._msg_layout.setContentsMargins(Spacing.lg, Spacing.lg, Spacing.lg, Spacing.lg)
        self._msg_layout.setSpacing(Spacing.md)
        self._msg_layout.addStretch(1)
        self._scroll.setWidget(self._msg_host)
        lay.addWidget(self._scroll, 1)

        self._empty = QFrame()
        self._empty.setObjectName("AnnotationCard")
        empty_lay = QVBoxLayout(self._empty)
        empty_lay.setContentsMargins(14, 12, 14, 12)
        empty_lay.setSpacing(6)
        self._empty_header = QLabel("ANNOTATION // QWEN2.5-CODER-7B")
        self._empty_header.setObjectName("AnnotationHeader")
        self._empty_body = QLabel(
            "Ask anything about your code, or describe an architectural RFC. "
            "Local weights are resident in VRAM (5037 MB, loaded in 0.2s)."
        )
        self._empty_body.setObjectName("AnnotationBody")
        self._empty_body.setWordWrap(True)
        empty_lay.addWidget(self._empty_header)
        empty_lay.addWidget(self._empty_body)
        self._msg_layout.insertWidget(0, self._empty)

        # Input row
        lay.addWidget(hline())
        input_host = QWidget()
        il = QVBoxLayout(input_host)
        il.setContentsMargins(Spacing.lg, Spacing.sm, Spacing.lg, Spacing.lg)
        il.setSpacing(Spacing.xs)

        # Agent Quick-Action & Undo Strip (/fix, /test, /run, /refactor, Undo)
        self._quick_bar = QWidget()
        qb_lay = QHBoxLayout(self._quick_bar)
        qb_lay.setContentsMargins(0, 0, 0, 2)
        qb_lay.setSpacing(4)
        for cmd_label, cmd_text, cmd_tip in (
            ("Fix Bug", "/fix", "Inspect active file & latest error and fix bugs on disk"),
            ("Run & Verify", "/run", "Ensure active file is complete, run it, and verify output"),
            ("Write Tests", "/test", "Generate and run unit tests for the active file"),
            ("Refactor", "/refactor", "Refactor active file for clean modular quality"),
        ):
            qbtn = QToolButton()
            qbtn.setObjectName("AgentQuickActionPill")
            qbtn.setText(cmd_label)
            qbtn.setToolTip(cmd_tip)
            qbtn.setCursor(Qt.PointingHandCursor)
            qbtn.clicked.connect(lambda _=False, c=cmd_text: self._trigger_quick_command(c))
            qb_lay.addWidget(qbtn)
        qb_lay.addStretch(1)
        self._undo_agent_btn = QToolButton()
        self._undo_agent_btn.setObjectName("AgentUndoPill")
        self._undo_agent_btn.setText("↶ Undo")
        self._undo_agent_btn.setToolTip("Revert the last file creation or edit made by the AI Agent")
        self._undo_agent_btn.setCursor(Qt.PointingHandCursor)
        self._undo_agent_btn.clicked.connect(self._on_undo_agent_clicked)
        qb_lay.addWidget(self._undo_agent_btn)
        il.addWidget(self._quick_bar)

        self._input = QPlainTextEdit()
        self._input.setPlaceholderText("Write an engineering prompt or specification...")
        self._input.setFixedHeight(84)
        self._input.installEventFilter(self)
        self._input.textChanged.connect(self._update_input_tokens)
        il.addWidget(self._input)

        # Usage footer: live input estimate + running session total (tokens only).
        self._usage_label = QLabel("")
        self._usage_label.setObjectName("UsageLabel")
        self._usage_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        il.addWidget(self._usage_label)

        btn_row = QHBoxLayout()
        self._regen_btn = TextButton("Regenerate", icon_name="refresh", tooltip="Regenerate the last AI response")
        self._regen_btn.clicked.connect(self._on_regenerate)
        self._regen_btn.setVisible(False)
        btn_row.addWidget(self._regen_btn)
        btn_row.addStretch(1)
        self._stop_btn = TextButton("Stop", icon_name="stop", tooltip="Stop AI response generation")
        self._stop_btn.clicked.connect(self._on_stop)
        self._stop_btn.setVisible(False)
        self._send_btn = TextButton("Run Agent" if self._mode == "agent" else "Send", icon_name="send", variant="primary", tooltip="Send prompt or run autonomous agent (Enter)")
        self._send_btn.setObjectName("AskGeminiBtn")
        self._send_btn.clicked.connect(self._on_send)
        btn_row.addWidget(self._stop_btn)
        btn_row.addWidget(self._send_btn)
        il.addLayout(btn_row)
        lay.addWidget(input_host)
        self._session_tokens = 0
        self._update_input_tokens()

        # Restore the remembered interaction mode and paint the pill/banner.
        self._mode_switch.set_mode(self._mode)
        self._apply_mode_placeholder()
        self._update_mode_banner()
        self._update_model_pill()

    # -- context / history panel construction --------------------------------
    def _build_context_panel(self) -> QWidget:
        box = QFrame()
        box.setObjectName("ContextPanel")
        v = QVBoxLayout(box)
        v.setContentsMargins(Spacing.lg, Spacing.sm, Spacing.lg, Spacing.sm)
        v.setSpacing(Spacing.xs)

        intro = QLabel("AI memory — files & notes shared with every chat so the "
                       "assistant has a recap of your work.")
        intro.setWordWrap(True)
        intro.setProperty("role", "muted")
        v.addWidget(intro)

        self._context_list = QListWidget()
        self._context_list.setObjectName("ContextList")
        self._context_list.setMaximumHeight(150)
        self._context_list.itemActivated.connect(self._on_context_item)
        v.addWidget(self._context_list)

        self._context_total = QLabel("No memory added yet.")
        self._context_total.setProperty("role", "muted")
        v.addWidget(self._context_total)

        row = QHBoxLayout()
        add_file = TextButton("Add file…", icon_name="file")
        add_file.clicked.connect(self._on_add_file)
        add_note = TextButton("Add note…", icon_name="edit")
        add_note.clicked.connect(self._on_add_note)
        reset = TextButton("Reset memory", icon_name="trash")
        reset.clicked.connect(self._on_reset_context)
        row.addWidget(add_file)
        row.addWidget(add_note)
        row.addStretch(1)
        row.addWidget(reset)
        v.addLayout(row)

        hint = QLabel("Tip: click an item to remove it. Reset clears everything "
                      "for a fresh, unrelated task.")
        hint.setWordWrap(True)
        hint.setObjectName("BubbleFooter")
        v.addWidget(hint)
        return box

    def _build_history_panel(self) -> QWidget:
        box = QFrame()
        box.setObjectName("HistoryPanel")
        v = QVBoxLayout(box)
        v.setContentsMargins(Spacing.lg, Spacing.sm, Spacing.lg, Spacing.sm)
        v.setSpacing(Spacing.xs)

        intro = QLabel("Past conversations — click to reopen. Right-click to "
                       "rename or delete.")
        intro.setWordWrap(True)
        intro.setProperty("role", "muted")
        v.addWidget(intro)

        self._history_list = QListWidget()
        self._history_list.setObjectName("HistoryList")
        self._history_list.setMaximumHeight(200)
        self._history_list.itemActivated.connect(self._on_history_activated)
        self._history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._history_list.customContextMenuRequested.connect(self._on_history_menu)
        v.addWidget(self._history_list)
        return box

    # -- chat engine wiring --------------------------------------------------
    def set_chat_engine(self, chat_engine):
        """Direct handle used for reading sessions/usage (mutations go via bus)."""
        self.chat_engine = chat_engine
        self._refresh_history()
        self._request_context()
        pending = self._pending_chat_messages
        self._pending_chat_messages = []
        for payload in pending:
            self._send_to_engine(payload)

    def _request_context(self):
        self._publish("ai_context_request", {})
        # If we have a direct handle, populate immediately too.
        engine = self.chat_engine
        if engine is not None and hasattr(engine, "context_store"):
            try:
                self._render_context(engine.context_store.summaries(),
                                     engine.context_store.total_tokens())
            except Exception:
                pass

    # -- toggles -------------------------------------------------------------
    def _toggle_context(self):
        vis = not self._context_panel.isVisible()
        self._context_panel.setVisible(vis)
        if vis:
            self._history_panel.setVisible(False)
            self._model_panel.setVisible(False)
            self._request_context()

    def _toggle_history(self):
        vis = not self._history_panel.isVisible()
        self._history_panel.setVisible(vis)
        if vis:
            self._context_panel.setVisible(False)
            self._model_panel.setVisible(False)
            self._refresh_history()

    def _toggle_model_panel(self):
        vis = not self._model_panel.isVisible()
        self._model_panel.setVisible(vis)
        if vis:
            self._context_panel.setVisible(False)
            self._history_panel.setVisible(False)

    # -- interaction mode (Chat / Edit / Agent) ------------------------------
    def _load_mode(self) -> str:
        try:
            if self._MODE_FILE.exists():
                data = json.loads(self._MODE_FILE.read_text(encoding="utf-8"))
                if data.get("agent_v44_initialized"):
                    m = data.get("mode")
                    if m in self._MODES:
                        return m
        except Exception:
            pass
        self._save_mode("agent")
        return "agent"

    def _save_mode(self, mode: str):
        try:
            self._MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
            self._MODE_FILE.write_text(
                json.dumps({"mode": mode, "agent_v44_initialized": True}),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _on_mode_changed(self, mode: str):
        if mode not in self._MODES:
            return
        self._mode = mode
        self._save_mode(mode)
        self._apply_mode_placeholder()
        self._update_mode_banner()
        # Tell the backend how much autonomy the user has granted. Chat is the
        # safe default; Edit asks for reviewable diffs; Agent is not live yet.
        self._publish("ai_mode_changed", {"mode": mode})

    def _apply_mode_placeholder(self):
        if hasattr(self, "_send_btn") and self._send_btn is not None:
            self._send_btn.setText("Run Agent" if self._mode == "agent" else "Send")
        if self._mode == "edit":
            self._input.setPlaceholderText(
                "Describe the change to make…  (changes open in a diff to review)")
        elif self._mode == "agent":
            self._input.setPlaceholderText(
                "Describe an engineering task…  (Creates/edits files directly in workspace & opens in editor)")
        else:
            self._input.setPlaceholderText(
                "Write an engineering prompt or question...")

    def _update_mode_banner(self):
        texts = {
            "edit": "Edit mode — file changes the assistant proposes open in a "
                    "diff for your approval before anything is written.",
            "agent": "Agent mode — autonomous multi-step planning, RepoMap AST context, "
                     "surgical SEARCH/REPLACE patching, and self-healing verification are active.",
        }
        t = texts.get(self._mode, "")
        self._mode_banner.setText(t)
        self._mode_banner.setVisible(bool(t))

    def _update_model_pill(self):
        """Reflect the active provider/model on the header pill."""
        provider = self._current_provider()
        model = self._model_combo.currentText()
        if not model or model in ("No models available", self._OTHER):
            self._model_pill.setText("Select model  ▾")
            self._model_pill.setToolTip("No model selected — click to choose")
            return
        label = model if len(model) <= 22 else model[:21] + "…"
        suffix = " · loading" if self._warming else ""
        self._model_pill.setText(f"{label}{suffix}  ▾")
        state = ("\nLoading into memory — the first reply will be slower."
                 if self._warming else
                 "\nLoaded and ready." if self._warm_ready else "")
        self._model_pill.setToolTip(
            f"{provider + ' · ' if provider else ''}{model}{state}"
            "\nClick to change provider/model")

    # -- warm-up -------------------------------------------------------------
    def _request_warm(self, reason: str):
        """Ask for the selected model to be loaded before it's needed.

        Cheap and fire-and-forget: the optimizer skips models that are already
        resident and never blocks the GUI thread on a load.
        """
        if self._streaming or not self.event_bus:
            return
        now = time.monotonic()
        if (now - self._last_warm_request) < self._WARM_MIN_INTERVAL_S:
            return
        model_id = self._current_model_id()
        if not model_id:
            return
        self._last_warm_request = now
        self._publish("ai_warm_request", {"model_id": model_id, "reason": reason})

    def _on_model_warming(self, data: dict):
        self._warming = True
        self._warm_ready = False
        self._update_model_pill()
        self._update_input_tokens()

    def _on_model_warm(self, data: dict):
        self._warming = False
        self._warm_ready = bool((data or {}).get("ready"))
        self._update_model_pill()
        self._update_input_tokens()
        estimate = (data or {}).get("estimate") or {}
        backend = estimate.get("backend", "unknown")
        size = estimate.get("model_size_gb", 0)
        load_time = (data or {}).get("load_seconds", 0)
        vram = estimate.get("vram_used_mb")
        details = f"{backend} · {size:.2f} GB · loaded in {load_time:.1f}s"
        if vram is not None:
            details += f" · VRAM {vram} MB"
        compute_mode = estimate.get("compute_mode")
        if compute_mode:
            details += f" · {compute_mode}"
        self._model_diagnostics = details
        self._update_input_tokens()
        self._model_pill.setToolTip(
            f"{self._current_provider()} · {self._model_combo.currentText()}\n"
            f"{details}\nClick to change provider/model")

    # -- context actions -----------------------------------------------------
    def _on_add_file(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add files to AI memory", "",
            "Text & code (*.txt *.md *.py *.js *.ts *.json *.yaml *.yml *.html "
            "*.css *.java *.c *.cpp *.h *.go *.rs *.rb *.sh);;All files (*.*)")
        for p in paths or []:
            self._publish("ai_context_add_file", {"path": p})
        if paths:
            QTimer.singleShot(120, self._request_context)

    def _on_add_note(self):
        text, ok = QInputDialog.getMultiLineText(
            self, "Add a note to AI memory",
            "Paste a recap, requirements, or anything the assistant should know:")
        if ok and text.strip():
            name, ok2 = QInputDialog.getText(
                self, "Name this note", "Short label:", QLineEdit.Normal, "note")
            self._publish("ai_context_add_note",
                          {"name": (name or "note") if ok2 else "note",
                           "content": text})
            QTimer.singleShot(120, self._request_context)

    def _on_reset_context(self):
        self._publish("ai_context_clear", {})
        QTimer.singleShot(120, self._request_context)

    def _on_context_item(self, item: QListWidgetItem):
        entry_id = item.data(Qt.UserRole)
        if entry_id:
            self._publish("ai_context_remove", {"entry_id": entry_id})
            QTimer.singleShot(120, self._request_context)

    def _render_context(self, entries: list, total_tokens: int):
        self._context_list.clear()
        for e in entries or []:
            label = f"{e.get('name', 'context')}  ·  ~{e.get('tokens', 0)} tok"
            it = QListWidgetItem(icon("file" if e.get("source") == "file" else "edit", 14), label)
            it.setData(Qt.UserRole, e.get("entry_id"))
            self._context_list.addItem(it)
        if entries:
            self._context_total.setText(
                f"{len(entries)} item(s) · ~{total_tokens} tokens shared with every chat.")
        else:
            self._context_total.setText("No memory added yet.")
        # keep the paperclip badge honest
        self._context_btn.setToolTip(
            f"AI memory / context ({len(entries or [])})")

    # -- history actions -----------------------------------------------------
    def _refresh_history(self):
        engine = self.chat_engine
        if engine is None or not hasattr(engine, "get_all_sessions"):
            return
        try:
            sessions = engine.get_all_sessions()
            current = engine.get_current_session() \
                if hasattr(engine, "get_current_session") else None
            current_id = getattr(current, "session_id", None)
        except Exception:
            return
        # pinned first, then most-recent activity
        try:
            sessions = sorted(
                sessions,
                key=lambda s: (not getattr(s, "is_pinned", False),
                               -getattr(s, "last_activity", None).timestamp()
                               if getattr(s, "last_activity", None) else 0))
        except Exception:
            pass
        self._history_list.clear()
        for s in sessions:
            n = len(getattr(s, "messages", []) or [])
            star = "★ " if getattr(s, "is_pinned", False) else ""
            label = f"{star}{getattr(s, 'title', 'Chat')}  ·  {n} msg"
            it = QListWidgetItem(icon("chat", 14), label)
            it.setData(Qt.UserRole, getattr(s, "session_id", None))
            if getattr(s, "session_id", None) == current_id:
                it.setSelected(True)
            self._history_list.addItem(it)

    def _on_history_activated(self, item: QListWidgetItem):
        session_id = item.data(Qt.UserRole)
        if session_id:
            self._publish("ai_chat_switch_session", {"session_id": session_id})

    def _on_history_menu(self, pos):
        item = self._history_list.itemAt(pos)
        if item is None:
            return
        session_id = item.data(Qt.UserRole)
        menu = QMenu(self)
        act_open = menu.addAction("Open")
        act_rename = menu.addAction("Rename…")
        act_pin = menu.addAction("Pin / Unpin")
        menu.addSeparator()
        act_delete = menu.addAction("Delete")
        chosen = menu.exec(self._history_list.mapToGlobal(pos))
        if chosen == act_open:
            self._publish("ai_chat_switch_session", {"session_id": session_id})
        elif chosen == act_rename:
            title, ok = QInputDialog.getText(self, "Rename chat", "New title:")
            if ok and title.strip():
                self._publish("ai_chat_rename_session",
                              {"session_id": session_id, "title": title.strip()})
        elif chosen == act_pin:
            pinned = self._session_is_pinned(session_id)
            self._publish("ai_chat_pin_session",
                          {"session_id": session_id, "pinned": not pinned})
        elif chosen == act_delete:
            self._publish("ai_chat_delete_session", {"session_id": session_id})

    def _session_is_pinned(self, session_id: str) -> bool:
        engine = self.chat_engine
        try:
            s = engine.get_session(session_id) if engine else None
            return bool(getattr(s, "is_pinned", False))
        except Exception:
            return False

    def _load_session_into_view(self, session_id: str):
        engine = self.chat_engine
        if engine is None or not hasattr(engine, "get_session"):
            return
        session = engine.get_session(session_id)
        if session is None:
            return
        self._clear_messages()
        for m in getattr(session, "messages", []) or []:
            role = getattr(m, "role", "assistant")
            if role == "system":
                continue
            bubble = self._add_bubble(role, getattr(m, "content", ""))
            if role == "assistant":
                bubble.finalize()
        # refresh running total from the engine
        try:
            usage = engine.get_session_usage(session_id)
            self._session_tokens = usage.get("total", 0)
        except Exception:
            self._session_tokens = 0
        self._update_input_tokens()

    # -- token footer --------------------------------------------------------
    def _update_input_tokens(self):
        try:
            draft = self._input.toPlainText()
        except Exception:
            draft = ""
        draft_tok = estimate_tokens(draft)
        if draft_tok:
            self._request_warm("typing")
        
        provider = self._current_provider() or "llama.cpp"
        model_str = str(self._model_combo.currentText() or "")
        size_str = "4.36 GB"
        if "7b" in model_str.lower():
            size_str = "4.36 GB"
        elif "8b" in model_str.lower():
            size_str = "4.92 GB"
        elif "1.5b" in model_str.lower():
            size_str = "1.12 GB"
            
        footer_text = f"session ~{self._session_tokens} tok · {provider} · {size_str}"
        self._usage_label.setText(footer_text)

    def _on_usage(self, data: dict):
        self._session_tokens = data.get("session_total_tokens", self._session_tokens)
        self._update_input_tokens()
        # annotate the just-finished assistant bubble, if any
        turn = data.get("turn_tokens")
        if self._current_assistant is not None and turn:
            speed = data.get("tokens_per_second", 0)
            speed_text = f" · {speed:.1f} tok/s" if speed else ""
            self._current_assistant.set_footer(
                f"~{data.get('completion_tokens', 0)} tok out · "
                f"~{data.get('prompt_tokens', 0)} tok in (est.){speed_text}")

    def _on_regenerate(self):
        if self._streaming:
            return
        self._publish("ai_chat_regenerate", {})

    def _on_context_changed_event(self, data: dict):
        self._render_context(data.get("entries", []), data.get("total_tokens", 0))

    def _on_context_error(self, data: dict):
        self._context_total.setText(data.get("error", "Could not add to memory."))

    def _on_session_switched(self, data: dict):
        sid = data.get("session_id")
        if sid:
            self._load_session_into_view(sid)
        self._refresh_history()

    def _on_session_list_changed(self, data: dict):
        self._refresh_history()



    # -- provider wiring -----------------------------------------------------
    def set_providers(self, provider_registry, provider_manager):
        self.provider_registry = provider_registry
        self.provider_manager = provider_manager
        self._reload_providers()
        self._ensure_models_discovered()

    # -- late model discovery ------------------------------------------------
    def _has_real_models(self) -> bool:
        """True when the model combo holds actual models, not just placeholders."""
        for i in range(self._model_combo.count()):
            text = self._model_combo.itemText(i)
            if text and text != self._OTHER and text != "No models available":
                return True
        return False

    def _ensure_models_discovered(self):
        """Retry discovery for a while when the current provider has no models.

        Ollama is frequently still starting when the IDE launches, so the very
        first /api/tags probe is refused and the list would otherwise stay empty
        until the next app restart.
        """
        if self._has_real_models():
            self._stop_discovery_retry()
            return
        provider = self._provider_obj(self._current_provider())
        # Cloud providers legitimately have no models until a key is entered —
        # retrying would just spam failures.
        if provider is None or self._provider_needs_key(provider):
            return
        if self._discovery_timer is None:
            self._discovery_timer = QTimer(self)
            self._discovery_timer.setInterval(self._DISCOVERY_RETRY_MS)
            self._discovery_timer.timeout.connect(self._retry_discovery)
        if not self._discovery_timer.isActive():
            self._discovery_retries = 0
            self._discovery_timer.start()

    def _stop_discovery_retry(self):
        if self._discovery_timer is not None and self._discovery_timer.isActive():
            self._discovery_timer.stop()

    def _retry_discovery(self):
        name = self._current_provider()
        provider = self._provider_obj(name)
        if provider is None:
            self._stop_discovery_retry()
            return
        if self._discovery_in_flight:
            return
        self._discovery_retries += 1
        if self._discovery_retries > self._DISCOVERY_MAX_RETRIES:
            self._stop_discovery_retry()
            return
        self._discovery_in_flight = True

        def discover():
            # Reconnecting is what actually repopulates the cache for local
            # servers; keep network I/O away from the Qt GUI thread.
            try:
                if not provider.is_connected():
                    provider.connect()
                models = self._discover_models(name)
            except Exception:
                models = []
            self._provider_models_arrived.emit(name, models)

        threading.Thread(target=discover, daemon=True).start()

    def _on_provider_models_event(self, data: dict):
        """Provider event handler — runs on a backend thread, so only signal."""
        payload = data or {}
        name = payload.get("provider", "")
        models = list(payload.get("models", []) or [])
        if name:
            self._provider_models_arrived.emit(name, models)

    def _apply_provider_models(self, provider_name: str, models: list):
        """Repopulate the model combo on the GUI thread, preserving selection."""
        self._discovery_in_flight = False
        if not provider_name or provider_name != self._current_provider():
            return                       # another provider woke up; ignore
        if not models:
            return
        previous = self._model_combo.currentText()
        engine_model = getattr(self.chat_engine, "_current_model", "") or ""
        engine_provider, separator, engine_bare = engine_model.partition(":")
        if separator and engine_provider == provider_name and engine_bare:
            previous = engine_bare
        elif not previous or previous in ("No models available", self._OTHER):
            provider = self._provider_obj(provider_name)
            cfg_default = getattr(getattr(provider, "config", None), "default_model", "") or ""
            if cfg_default:
                previous = cfg_default
            else:
                try:
                    from ui.settings_manager import get_settings_manager
                    dm = get_settings_manager().get_default_model() or ""
                    dp, dsep, dmodel = dm.partition(":")
                    if dsep and dp == provider_name and dmodel:
                        previous = dmodel
                except Exception:
                    pass
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        self._model_combo.addItems([str(m) for m in models])
        self._model_combo.addItem(self._OTHER)
        idx = self._model_combo.findText(previous)
        self._model_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._model_combo.blockSignals(False)
        self._stop_discovery_retry()
        if idx < 0:                      # selection changed, tell the backend
            self._emit_model_switch()
        self._update_model_pill()

    def _list_provider_names(self) -> list:
        reg = self.provider_registry
        if reg is None:
            return []
        try:
            if hasattr(reg, "get_loaded_providers"):
                return list(reg.get_loaded_providers() or [])
            if hasattr(reg, "get_all_providers"):
                return list((reg.get_all_providers() or {}).keys())
        except Exception:
            pass
        return []

    def _reload_providers(self):
        names = self._list_provider_names()
        # local providers first, then the rest alphabetically
        def _rank(n: str):
            low = n.lower()
            local = 0 if any(h in low for h in self._LOCAL_HINTS) else 1
            return (local, low)
        names = sorted(names, key=_rank)
        try:
            from ui.settings_manager import get_settings_manager
            default_model = get_settings_manager().get_default_model()
            preferred = default_model.split(":", 1)[0] if ":" in default_model else ""
        except Exception:
            preferred = "llama_cpp"

        self._provider_combo.blockSignals(True)
        self._provider_combo.clear()
        if names:
            self._provider_combo.addItems(names)
            preferred_index = self._provider_combo.findText(preferred)
            self._provider_combo.setCurrentIndex(preferred_index if preferred_index >= 0 else 0)
        else:
            self._provider_combo.addItem("No providers")
        self._provider_combo.blockSignals(False)

        self._on_provider_selected(self._current_provider(), emit=False)

        try:
            from ui.settings_manager import get_settings_manager
            default_model = get_settings_manager().get_default_model()
            provider, sep, model = default_model.partition(":")
            engine_model = getattr(self.chat_engine, "_current_model", "") or ""
            engine_provider, engine_sep, engine_model_name = engine_model.partition(":")
            if engine_sep and engine_provider == self._current_provider():
                model = engine_model_name
            if sep and provider == self._current_provider():
                model_index = self._model_combo.findText(model)
                if model_index >= 0:
                    self._select_model_index(model_index)
        except Exception:
            pass
        self._update_model_pill()

    def _provider_obj(self, name: str):
        try:
            reg = self.provider_registry
            if reg is not None and name and hasattr(reg, "get_provider"):
                return reg.get_provider(name)
        except Exception:
            pass
        return None

    def _provider_needs_key(self, provider) -> bool:
        """True when the provider authenticates with something other than 'none'."""
        if provider is None:
            return False
        try:
            auth = getattr(provider.config, "auth_type", None)
            val = getattr(auth, "value", auth)
            return str(val).lower() not in ("", "none")
        except Exception:
            return False
    def _on_provider_selected(self, name: str, emit: bool = True):
        """Sync the auth row + model list to the newly-selected provider."""
        provider = self._provider_obj(name)
        self._update_auth_row(provider)
        # local (no-key) providers can auto-discover; cloud providers wait for a key
        discover = provider is not None and not self._provider_needs_key(provider)
        self._reload_models_for(name, discover=False, emit=emit)
        if discover:
            self._ensure_models_discovered()

    def _update_auth_row(self, provider):
        needs_key = self._provider_needs_key(provider)
        self._auth_box.setVisible(needs_key)
        if not needs_key:
            return
        cfg = getattr(provider, "config", None)
        self._key_edit.blockSignals(True)
        self._url_edit.blockSignals(True)
        self._key_edit.setText(getattr(cfg, "api_key", "") or "")
        self._url_edit.setText(getattr(cfg, "endpoint", "") or "")
        self._key_edit.blockSignals(False)
        self._url_edit.blockSignals(False)
        if provider.is_connected():
            n = len(provider.get_models() or {})
            self._set_status(f"Connected · {n} model(s) available", ok=True)
        elif getattr(cfg, "api_key", ""):
            self._set_status("Key saved — click Connect to verify.", ok=None)
        else:
            self._set_status("Enter an API key to enable this provider.", ok=None)

    def _set_status(self, text: str, ok):
        c = get_design_system().colors
        color = c.text_muted
        if ok is True:
            color = getattr(c, "success", c.accent)
        elif ok is False:
            color = getattr(c, "error", c.text_primary)
        self._auth_status.setStyleSheet(f"color: {color}; font-size: {FontSize.tiny}px;")
        self._auth_status.setText(text)

    def _reload_models_for(self, provider_name: str, discover: bool = False,
                           emit: bool = True):
        provider = self._provider_obj(provider_name)
        models = []
        if provider is not None:
            try:
                models = list((provider.get_models() or {}).keys())
            except Exception:
                models = []
        preferred_model = ""
        if provider is not None:
            preferred_model = getattr(getattr(provider, "config", None), "default_model", "") or ""
        if not preferred_model:
            try:
                from ui.settings_manager import get_settings_manager
                dm = get_settings_manager().get_default_model() or ""
                dp, dsep, dmodel = dm.partition(":")
                if dsep and dp == provider_name and dmodel:
                    preferred_model = dmodel
            except Exception:
                pass
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        if models:
            self._model_combo.addItems(models)
        else:
            self._model_combo.addItem("No models available")
        self._model_combo.addItem(self._OTHER)   # manual entry escape hatch
        idx = self._model_combo.findText(preferred_model) if preferred_model else -1
        self._model_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._model_combo.blockSignals(False)
        if emit:
            self._emit_model_switch()
        self._update_model_pill()

    def _discover_models(self, provider_name: str) -> list:
        """Live-refresh a provider's models through the manager (best effort)."""
        mgr = self.provider_manager
        try:
            if mgr is not None and hasattr(mgr, "refresh_models"):
                result = mgr.refresh_models(provider_name) or {}
                ids = result.get(provider_name)
                if ids:
                    return list(ids)
        except Exception:
            pass
        # fall back to whatever landed in the cache after the refresh attempt
        provider = self._provider_obj(provider_name)
        if provider is not None:
            try:
                return list((provider.get_models() or {}).keys())
            except Exception:
                pass
        return []
    def _on_connect_clicked(self):
        """Apply the API key / base URL, connect the provider, and load its models."""
        name = self._current_provider()
        provider = self._provider_obj(name)
        if provider is None:
            self._set_status("Select a provider first.", ok=False)
            return
        key = self._key_edit.text().strip()
        base_url = self._url_edit.text().strip()
        if self._provider_needs_key(provider) and not key:
            self._set_status("An API key is required for this provider.", ok=False)
            return

        # Push the new settings onto the provider config.
        try:
            provider.config.api_key = key or provider.config.api_key
            if base_url:
                provider.config.endpoint = base_url
            provider.config.enabled = True
        except Exception as exc:
            self._set_status(f"Could not update settings: {exc}", ok=False)
            return

        # Persist (writes config.to_dict() back to config/providers/<name>.json).
        try:
            reg = self.provider_registry
            if reg is not None and hasattr(reg, "enable_provider"):
                reg.enable_provider(name)
        except Exception:
            pass

        self._set_status("Connecting…", ok=None)
        self._connect_btn.setEnabled(False)
        try:
            ok = False
            try:
                ok = bool(provider.connect())
            except Exception as exc:
                self._set_status(f"Connection failed: {exc}", ok=False)
                return
            if not ok:
                err = getattr(provider.config, "connection_status", None)
                self._set_status(
                    f"Connection failed ({getattr(err, 'value', err)}). Check the key/URL.",
                    ok=False)
                return
            # Connected — discover models and select the first one.
            self._reload_models_for(name, discover=True, emit=True)
            n = len(provider.get_models() or {})
            self._set_status(f"Connected · {n} model(s) available", ok=True)
        finally:
            self._connect_btn.setEnabled(True)

    # -- selection helpers ---------------------------------------------------
    def _current_provider(self) -> str:
        text = self._provider_combo.currentText()
        return "" if text in ("", "No providers") else text

    def _current_model_id(self) -> str:
        provider = self._current_provider()
        model = self._model_combo.currentText()
        if not model or model in ("No models available", self._OTHER):
            return ""
        return f"{provider}:{model}" if provider else model

    def _emit_model_switch(self):
        model_id = self._current_model_id()
        if model_id and model_id != self._last_emitted_model:
            self._last_emitted_model = model_id
            self._publish("ai_chat_switch_model", {"model_id": model_id})
        self._update_model_pill()

    # -- event bus -----------------------------------------------------------
    def _subscribe(self):
        if not self.event_bus:
            return
        self.event_bus.subscribe("ai_chat_streaming_started", self._on_stream_started)
        self.event_bus.subscribe("ai_chat_chunk", self._on_chunk)
        self.event_bus.subscribe("ai_chat_streaming_complete", self._on_stream_complete)
        self.event_bus.subscribe("ai_chat_error", self._on_error)
        self.event_bus.subscribe("ai_model_auto_selected", self._on_model_auto_selected)
        # Model warm-up progress, so "loading the model" doesn't look like a hang.
        self.event_bus.subscribe("ai_model_warming", self._on_model_warming)
        self.event_bus.subscribe("ai_model_warm", self._on_model_warm)
        # A provider that comes online later (Ollama started after the app, or a
        # cloud key was accepted) must be able to fill the model list without a
        # restart. Both events are handled the same way.
        self.event_bus.subscribe("provider_models_refreshed", self._on_provider_models_event)
        self.event_bus.subscribe("models_refreshed", self._on_provider_models_event)
        self.event_bus.subscribe("provider_connected", self._on_provider_models_event)
        # AI memory / usage / history
        self.event_bus.subscribe("ai_context_changed", self._on_context_changed_event)
        self.event_bus.subscribe("ai_context_error", self._on_context_error)
        self.event_bus.subscribe("ai_chat_usage", self._on_usage)
        self.event_bus.subscribe("ai_chat_session_switched", self._on_session_switched)
        self.event_bus.subscribe("ai_chat_session_created", self._on_session_list_changed)
        self.event_bus.subscribe("ai_chat_session_deleted", self._on_session_list_changed)
        self.event_bus.subscribe("ai_chat_session_renamed", self._on_session_list_changed)
        self.event_bus.subscribe("ai_chat_session_pinned", self._on_session_list_changed)
        self.event_bus.subscribe("ai_agent_operations_applied", self._on_agent_operations_applied)
        self.event_bus.subscribe("ai_agent_undo_completed", self._on_agent_undo_completed)
        self.event_bus.subscribe("ai_code_block_run_completed", self._on_code_block_run_completed)
        self.event_bus.subscribe("ai_agent_process_update", self._on_agent_process_update)
        self.event_bus.subscribe("ai_agent_summary_ready", self._on_agent_summary_ready)

    def _publish(self, topic: str, payload: dict):
        if self.event_bus:
            self.event_bus.publish(topic, payload)

    def _trigger_quick_command(self, cmd_text: str):
        if self._streaming:
            return
        existing = self._input.toPlainText().strip()
        full_cmd = f"{cmd_text} {existing}".strip() if existing and not existing.startswith("/") else cmd_text
        self._input.setPlainText(full_cmd)
        self._on_send()

    def _on_undo_agent_clicked(self):
        self._publish("ai_agent_undo", {})

    def _on_agent_operations_applied(self, data: dict):
        ops = list((data or {}).get("operations", []) or [])
        if not ops:
            return
        files_desc = ", ".join(f"{it.get('action', 'Updated')} {it.get('rel_path', '')}" for it in ops[:3])
        def _upd():
            try:
                self._mode_banner.setText(f"✓ Agent executed on workspace: {files_desc} (opened in editor)")
                self._mode_banner.setVisible(True)
            except Exception:
                pass
        QTimer.singleShot(0, _upd)

    def _on_agent_undo_completed(self, data: dict):
        restored = list((data or {}).get("restored", []) or [])
        msg = (
            f"↶ Reverted Agent changes: {', '.join(restored[:3])}"
            if restored else "No previous Agent workspace actions to undo."
        )
        def _upd():
            try:
                self._mode_banner.setText(msg)
                self._mode_banner.setVisible(True)
            except Exception:
                pass
        QTimer.singleShot(0, _upd)

    def _on_code_block_run_completed(self, data: dict):
        d = data or {}
        fname = d.get("file", "file")
        ok = d.get("success", False)
        out = (d.get("stdout") or d.get("stderr") or d.get("error") or "").strip().splitlines()
        first_line = out[0][:80] if out else ("exit 0" if ok else "failed")
        status = f"▶ Ran {fname}: {first_line}" if ok else f"⚠ Run {fname} failed: {first_line}"
        def _upd():
            try:
                self._mode_banner.setText(status)
                self._mode_banner.setVisible(True)
            except Exception:
                pass
        QTimer.singleShot(0, _upd)
    # -- actions -------------------------------------------------------------
    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self._input:
            if event.type() == QEvent.FocusIn:
                # Clicking into the box is the earliest reliable signal that a
                # message is coming — start loading the model now.
                self._request_warm("input_focus")
            elif event.type() == QEvent.KeyPress:
                if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
                    self._on_send()
                    return True
        return super().eventFilter(obj, event)

    def _on_send(self):
        text = self._input.toPlainText().strip()
        if not text or self._streaming:
            return
        self._add_bubble("user", text)
        self._input.clear()
        payload = {"message": text, "mode": self._mode}
        model = self._current_model_id()
        if model:
            payload["model_id"] = model
        # The chat engine is already wired directly by startup. Calling it
        # here avoids waiting on a queued EventBus delivery after the user
        # bubble is shown, which could leave a message visible with no reply.
        # Keep the event fallback for the short startup window before wiring.
        if self.chat_engine is None:
            self._pending_chat_messages.append(payload)
            return
        self._send_to_engine(payload)

    def _send_to_engine(self, payload: dict):
        try:
            self.chat_engine.send_message(
                payload["message"],
                model_id=payload.get("model_id"),
                mode=payload.get("mode", self._mode),
            )
        except Exception as exc:
            logger.error("Chat send failed before generation started: %s",
                         exc, exc_info=True)
            self._on_error({"error": f"Could not start the AI reply: {exc}"})

    def _on_stop(self):
        self._publish("ai_chat_cancel", {})
        self._set_streaming(False)

    def _on_new_chat(self):
        self._publish("ai_chat_new_session", {})
        self._clear_messages()
        self._session_tokens = 0
        self._regen_btn.setVisible(False)
        self._update_input_tokens()
        QTimer.singleShot(120, self._refresh_history)

    def _on_model_changed(self, text: str):
        if text == self._OTHER:
            self._prompt_custom_model()
            return
        if text and text != "No models available":
            self._emit_model_switch()

    def _on_provider_changed(self, text: str):
        if text and text != "No providers":
            self._on_provider_selected(text, emit=True)

    def _auto_detect(self):
        self._reload_models_for(self._current_provider(), discover=False, emit=False)
        self._discovery_retries = 0
        self._retry_discovery()

    def _prompt_custom_model(self):
        text, ok = QInputDialog.getText(
            self, "Custom Model", "Enter a model id (e.g. llama3.1:8b):")
        text = (text or "").strip()
        if ok and text:
            idx = self._model_combo.findText(text)
            if idx < 0:
                self._model_combo.blockSignals(True)
                # insert before the trailing "Other model…" sentinel
                self._model_combo.insertItem(max(0, self._model_combo.count() - 1), text)
                self._model_combo.blockSignals(False)
                idx = self._model_combo.findText(text)
            self._select_model_index(idx)
            self._emit_model_switch()
        else:
            self._select_model_index(0)   # revert off the sentinel

    def _select_model_index(self, idx: int):
        if idx is None or idx < 0:
            return
        self._model_combo.blockSignals(True)
        self._model_combo.setCurrentIndex(idx)
        self._model_combo.blockSignals(False)
    # -- streaming handlers --------------------------------------------------
    def _on_stream_started(self, data: dict):
        self._set_streaming(True)
        self._current_assistant = self._add_bubble("assistant", "")
        if self._mode == "agent" and self._current_assistant is not None:
            self._current_assistant.set_live_process(
                "Planning implementation",
                "Analyzing workspace context and requirements…",
            )

    def _on_agent_process_update(self, data: dict):
        headline = str((data or {}).get("headline") or "Working…")
        detail = str((data or {}).get("detail") or "")
        def _upd():
            try:
                if self._current_assistant is None:
                    self._current_assistant = self._add_bubble("assistant", "")
                self._current_assistant.set_live_process(headline, detail)
                self._mode_banner.setText(f"⚡ {headline} — {detail}" if detail else f"⚡ {headline}")
                self._mode_banner.setVisible(True)
                self._scroll_to_bottom()
            except Exception:
                pass
        QTimer.singleShot(0, _upd)

    def _on_agent_summary_ready(self, data: dict):
        summary_md = str((data or {}).get("summary_markdown") or "")
        target_bubble = self._current_assistant or getattr(self, "_last_assistant_bubble", None)
        def _upd():
            try:
                b = target_bubble or self._current_assistant or getattr(self, "_last_assistant_bubble", None)
                if b is not None and summary_md:
                    b.set_summary_markdown(summary_md)
                    self._scroll_to_bottom()
            except Exception:
                pass
        QTimer.singleShot(0, _upd)

    def _on_chunk(self, data: dict):
        chunk = data.get("chunk", "")
        if self._current_assistant is None:
            self._current_assistant = self._add_bubble("assistant", "")
        self._current_assistant.append(chunk)
        self._scroll_to_bottom()

    def _on_stream_complete(self, data: dict):
        self._set_streaming(False)
        summary_md = str((data or {}).get("summary_markdown") or "")
        if self._current_assistant is not None:
            self._last_assistant_bubble = self._current_assistant
            if summary_md:
                self._current_assistant.set_summary_markdown(summary_md)
            elif self._current_assistant.text().strip():
                self._current_assistant.finalize()
        self._current_assistant = None
        self._regen_btn.setVisible(True)

    def _on_error(self, data: dict):
        self._set_streaming(False)
        self._add_bubble("assistant", f"⚠ {data.get('error', 'An error occurred.')}")
        self._current_assistant = None

    def _on_model_auto_selected(self, data: dict):
        model_id = data.get("model_id", "")
        if not model_id:
            return
        provider, sep, model = model_id.partition(":")
        if not sep:                       # bare model name, no provider prefix
            provider, model = "", model_id
        # sync the provider combo when a prefix was supplied
        if provider:
            pi = self._provider_combo.findText(provider)
            if pi >= 0:
                self._provider_combo.blockSignals(True)
                self._provider_combo.setCurrentIndex(pi)
                self._provider_combo.blockSignals(False)
                self._update_auth_row(self._provider_obj(provider))
                self._reload_models_for(provider, emit=False)
        # ensure the model exists in the list, then select it (no re-emit)
        mi = self._model_combo.findText(model)
        if mi < 0:
            self._model_combo.blockSignals(True)
            self._model_combo.insertItem(max(0, self._model_combo.count() - 1), model)
            self._model_combo.blockSignals(False)
            mi = self._model_combo.findText(model)
        self._select_model_index(mi)
        self._update_model_pill()

    # -- message helpers -----------------------------------------------------
    def _add_bubble(self, role: str, text: str) -> _Bubble:
        if self._empty.isVisible():
            self._empty.hide()
        bubble = _Bubble(role, text)
        self._msg_layout.insertWidget(self._msg_layout.count() - 1, bubble)
        self._scroll_to_bottom()
        return bubble

    def _clear_messages(self):
        while self._msg_layout.count() > 1:
            item = self._msg_layout.takeAt(0)
            w = item.widget()
            if w and w is not self._empty:
                w.deleteLater()
        self._empty.show()
        self._msg_layout.insertWidget(0, self._empty)

    def _scroll_to_bottom(self):
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _set_streaming(self, streaming: bool):
        self._streaming = streaming
        self._send_btn.setVisible(not streaming)
        self._stop_btn.setVisible(streaming)
        if streaming:
            self._regen_btn.setVisible(False)

    # -- style ---------------------------------------------------------------
    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #AIWorkspace {{ background: {c.surface}; border-left: 1px solid {c.border_subtle}; }}
            #AuthBox {{ background: {c.surface_raised}; }}
            #AuthStatus {{ color: {c.text_muted}; font-size: {FontSize.tiny}px; }}
            #ModelPill {{
                background: {c.surface_inset};
                color: {c.text_secondary};
                border: 1px solid {c.border};
                border-radius: {Radius.pill}px;
                padding: 2px 12px;
                font-size: {FontSize.tiny}px;
                font-weight: {FontWeight.medium};
            }}
            #ModelPill:hover {{ color: {c.text_primary}; border-color: {c.border_strong}; }}
            #ModelPanel {{ background: {c.surface_raised}; border-bottom: 1px solid {c.border_subtle}; }}
            #ModeBanner {{
                background: {c.surface_raised};
                color: {c.text_muted};
                border-bottom: 1px solid {c.border_subtle};
                padding: 4px 12px;
                font-size: {FontSize.tiny}px;
            }}
            #AnnotationCard {{
                background: {c.surface_raised};
                border: 1px solid {c.border};
                border-radius: {Radius.md}px;
            }}
            #AnnotationHeader {{
                color: {c.accent};
                font-family: "JetBrains Mono", "Cascadia Code", Consolas, monospace;
                font-size: {FontSize.micro}px;
                font-weight: {FontWeight.semibold};
                letter-spacing: 0.6px;
            }}
            #AnnotationBody {{
                color: {c.text_primary};
                font-size: {FontSize.small}px;
            }}
            #UserBubble {{
                background: {c.accent_muted};
                border: 1px solid {c.accent_border};
                border-radius: {Radius.lg}px;
            }}
            #AssistantBubble {{
                background: {c.surface_raised};
                border: 1px solid {c.border_subtle};
                border-radius: {Radius.lg}px;
            }}
            #BubbleRole {{ color: {c.text_muted}; font-size: {FontSize.tiny}px; font-weight: 600; }}
            #BubbleFooter {{ color: {c.text_muted}; font-size: {FontSize.micro}px; }}
            #UsageLabel {{ color: {c.text_muted}; font-size: {FontSize.tiny}px; padding: 2px 2px 0 2px; }}
            #ContextPanel, #HistoryPanel {{
                background: {c.surface_raised};
                border-bottom: 1px solid {c.border_subtle};
            }}
            #ContextList, #HistoryList {{
                background: {c.surface_inset};
                border: 1px solid {c.border_subtle};
                border-radius: {Radius.md}px;
            }}
            QScrollArea {{ background: {c.surface}; }}
            QLineEdit {{
                background: {c.surface_inset};
                border: 1px solid {c.border};
                border-radius: {Radius.md}px;
                padding: 4px 6px;
            }}
            QPlainTextEdit {{
                background: {c.surface_inset};
                border: 1px solid {c.border};
                border-radius: {Radius.md}px;
            }}
        """)

    def refresh_theme(self):
        self._apply_style()
        try:
            self._mode_switch.refresh_theme()
        except Exception:
            pass






