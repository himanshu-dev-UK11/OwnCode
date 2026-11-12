"""
Consolidated Module: ui.widgets_and_icons

Combines: ui.widgets.icons, ui.widgets.controls, ui.widgets.diff_view, ui.widgets.native_dialogs
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['ui.widgets.icons', 'ui.widgets.controls', 'ui.widgets.diff_view', 'ui.widgets.native_dialogs']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ui.widgets.icons (ui/widgets/icons.py)
# ============================================================================
"""
Icons — v2.2

Crisp, theme-aware line icons drawn with QPainter (no image assets, no font
dependency). Each icon is a stroke path on a 24x24 canvas, scaled to request.
"""

from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QPainterPath
from PySide6.QtCore import Qt, QRectF, QPointF

from ui.design_system import get_design_system


def _pen(painter: QPainter, color: QColor, width: float = 1.8):
    p = QPen(color)
    p.setWidthF(width)
    p.setCapStyle(Qt.RoundCap)
    p.setJoinStyle(Qt.RoundJoin)
    painter.setPen(p)
    painter.setBrush(Qt.NoBrush)


def _files(p, c):
    _pen(p, c)
    p.drawRoundedRect(QRectF(5, 3, 11, 15), 1.5, 1.5)
    p.drawLine(QPointF(8, 8), QPointF(13, 8))
    p.drawLine(QPointF(8, 11), QPointF(13, 11))
    p.drawLine(QPointF(8, 14), QPointF(11, 14))


def _search(p, c):
    _pen(p, c)
    p.drawEllipse(QRectF(4, 4, 11, 11))
    p.drawLine(QPointF(13.5, 13.5), QPointF(20, 20))


def _git(p, c):
    _pen(p, c)
    p.drawEllipse(QRectF(4, 4, 5, 5))
    p.drawEllipse(QRectF(4, 15, 5, 5))
    p.drawEllipse(QRectF(15, 9.5, 5, 5))
    p.drawLine(QPointF(6.5, 9), QPointF(6.5, 15))
    path = QPainterPath(QPointF(6.5, 9))
    path.cubicTo(6.5, 12, 9, 12, 15, 12)
    p.drawPath(path)


def _debug(p, c):
    _pen(p, c)
    p.drawEllipse(QRectF(7, 7, 10, 10))
    p.drawLine(QPointF(12, 3.5), QPointF(12, 7))
    for a, b in [(4, 9), (4, 15), (20, 9), (20, 15)]:
        p.drawLine(QPointF(a, b), QPointF(a + (4 if a < 12 else -4), b))


def _flask(p, c):
    """Lab flask / beaker icon for Program & Terminal Tests."""
    _pen(p, c)
    p.drawLine(QPointF(9, 4), QPointF(15, 4))
    path = QPainterPath(QPointF(10, 4))
    path.lineTo(10, 9)
    path.lineTo(5, 18.5)
    path.cubicTo(4.5, 19.5, 5.2, 20, 6.5, 20)
    path.lineTo(17.5, 20)
    path.cubicTo(18.8, 20, 19.5, 19.5, 19, 18.5)
    path.lineTo(14, 9)
    path.lineTo(14, 4)
    p.drawPath(path)
    p.drawLine(QPointF(7.5, 15), QPointF(16.5, 15))


def _extensions(p, c):
    _pen(p, c)
    p.drawRect(QRectF(4, 4, 7, 7))
    p.drawRect(QRectF(13, 4, 7, 7))
    p.drawRect(QRectF(4, 13, 7, 7))
    p.drawRect(QRectF(13, 13, 7, 7))


def _memory(p, c):
    _pen(p, c)
    path = QPainterPath()
    path.addEllipse(QRectF(5, 4, 14, 13))
    p.drawPath(path)
    p.drawLine(QPointF(12, 6), QPointF(12, 15))
    p.drawLine(QPointF(9, 9), QPointF(15, 9))
    p.drawLine(QPointF(9, 12), QPointF(15, 12))


def _tasks(p, c):
    _pen(p, c)
    p.drawRoundedRect(QRectF(4, 4, 16, 16), 2, 2)
    p.drawPolyline([QPointF(8, 12), QPointF(11, 15), QPointF(16, 9)])


def _settings(p, c):
    _pen(p, c, 1.7)
    p.drawEllipse(QRectF(9, 9, 6, 6))
    import math
    cx, cy = 12, 12
    for i in range(8):
        ang = i * math.pi / 4
        x1 = cx + 7 * math.cos(ang)
        y1 = cy + 7 * math.sin(ang)
        x2 = cx + 9.5 * math.cos(ang)
        y2 = cy + 9.5 * math.sin(ang)
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))


def _run(p, c):
    _pen(p, c)
    path = QPainterPath(QPointF(7, 5))
    path.lineTo(19, 12)
    path.lineTo(7, 19)
    path.closeSubpath()
    p.fillPath(path, c)
    p.drawPath(path)


def _stop(p, c):
    _pen(p, c)
    p.fillRect(QRectF(6, 6, 12, 12), c)


def _chat(p, c):
    _pen(p, c)
    path = QPainterPath()
    path.addRoundedRect(QRectF(4, 4, 16, 12), 3, 3)
    p.drawPath(path)
    p.drawPolyline([QPointF(8, 16), QPointF(8, 19), QPointF(12, 16)])


def _model(p, c):
    _pen(p, c)
    p.drawRoundedRect(QRectF(6, 6, 12, 12), 2, 2)
    for x in (9, 12, 15):
        p.drawLine(QPointF(x, 3.5), QPointF(x, 6))
        p.drawLine(QPointF(x, 18), QPointF(x, 20.5))
    for y in (9, 12, 15):
        p.drawLine(QPointF(3.5, y), QPointF(6, y))
        p.drawLine(QPointF(18, y), QPointF(20.5, y))


def _close(p, c):
    _pen(p, c)
    p.drawLine(QPointF(6, 6), QPointF(18, 18))
    p.drawLine(QPointF(18, 6), QPointF(6, 18))


def _minimize(p, c):
    _pen(p, c)
    p.drawLine(QPointF(6, 12), QPointF(18, 12))


def _maximize(p, c):
    _pen(p, c)
    p.drawRect(QRectF(6, 6, 12, 12))


def _restore(p, c):
    _pen(p, c)
    p.drawRect(QRectF(6, 8, 10, 10))
    p.drawPolyline([QPointF(9, 8), QPointF(9, 5), QPointF(19, 5), QPointF(19, 15), QPointF(16, 15)])


def _chevron_down(p, c):
    _pen(p, c)
    p.drawPolyline([QPointF(7, 10), QPointF(12, 15), QPointF(17, 10)])


def _chevron_right(p, c):
    _pen(p, c)
    p.drawPolyline([QPointF(10, 7), QPointF(15, 12), QPointF(10, 17)])


def _chevron_left(p, c):
    """Double left chevron («) for collapsing the left sidebar."""
    _pen(p, c)
    p.drawPolyline([QPointF(13, 7), QPointF(8, 12), QPointF(13, 17)])
    p.drawPolyline([QPointF(18, 7), QPointF(13, 12), QPointF(18, 17)])


def _folder_collapse(p, c):
    """Collapse-all folders icon (upward chevron inside a folder)."""
    _pen(p, c)
    path = QPainterPath(QPointF(4, 7))
    path.lineTo(9, 7)
    path.lineTo(11, 9)
    path.lineTo(20, 9)
    path.lineTo(20, 18)
    path.lineTo(4, 18)
    path.closeSubpath()
    p.drawPath(path)
    p.drawPolyline([QPointF(9, 15), QPointF(12, 12), QPointF(15, 15)])


def _plus(p, c):
    _pen(p, c)
    p.drawLine(QPointF(12, 6), QPointF(12, 18))
    p.drawLine(QPointF(6, 12), QPointF(18, 12))


def _folder(p, c):
    _pen(p, c)
    path = QPainterPath(QPointF(4, 7))
    path.lineTo(9, 7)
    path.lineTo(11, 9)
    path.lineTo(20, 9)
    path.lineTo(20, 18)
    path.lineTo(4, 18)
    path.closeSubpath()
    p.drawPath(path)


def _file(p, c):
    _pen(p, c)
    path = QPainterPath(QPointF(6, 3))
    path.lineTo(14, 3)
    path.lineTo(18, 7)
    path.lineTo(18, 21)
    path.lineTo(6, 21)
    path.closeSubpath()
    p.drawPath(path)
    p.drawPolyline([QPointF(14, 3), QPointF(14, 7), QPointF(18, 7)])


def _terminal(p, c):
    _pen(p, c)
    p.drawRoundedRect(QRectF(4, 5, 16, 14), 2, 2)
    p.drawPolyline([QPointF(7, 9), QPointF(11, 12), QPointF(7, 15)])
    p.drawLine(QPointF(13, 15), QPointF(17, 15))


def _ai(p, c):
    _pen(p, c)
    import math
    cx, cy = 12, 12
    path = QPainterPath()
    for i in range(4):
        ang = i * math.pi / 2
        path.moveTo(cx, cy)
        path.lineTo(cx + 8 * math.cos(ang), cy + 8 * math.sin(ang))
    p.drawPath(path)
    p.drawEllipse(QRectF(10, 10, 4, 4))


def _menu(p, c):
    _pen(p, c)
    for y in (7, 12, 17):
        p.drawLine(QPointF(5, y), QPointF(19, y))


def _bell(p, c):
    _pen(p, c)
    path = QPainterPath(QPointF(7, 16))
    path.lineTo(7, 11)
    path.cubicTo(7, 7, 17, 7, 17, 11)
    path.lineTo(17, 16)
    p.drawPath(path)
    p.drawLine(QPointF(5, 16), QPointF(19, 16))
    p.drawArc(QRectF(10, 16, 4, 4), 0, -180 * 16)


def _more(p, c):
    _pen(p, c, 2.2)
    for x in (6, 12, 18):
        p.drawPoint(QPointF(x, 12))


def _split(p, c):
    _pen(p, c)
    p.drawRoundedRect(QRectF(4, 5, 16, 14), 2, 2)
    p.drawLine(QPointF(12, 5), QPointF(12, 19))


def _refresh(p, c):
    _pen(p, c)
    p.drawArc(QRectF(5, 5, 14, 14), 40 * 16, 280 * 16)
    p.drawPolyline([QPointF(18, 4), QPointF(19, 8), QPointF(15, 8)])


def _collapse(p, c):
    _pen(p, c)
    p.drawRoundedRect(QRectF(4, 5, 16, 14), 2, 2)
    p.drawLine(QPointF(9, 5), QPointF(9, 19))


def _palette(p, c):
    _pen(p, c)
    p.drawEllipse(QRectF(4, 4, 16, 16))
    p.setBrush(c)
    for cx, cy in ((9, 8), (14, 9), (15, 14)):
        p.drawEllipse(QRectF(cx - 1.2, cy - 1.2, 2.4, 2.4))
    p.setBrush(Qt.NoBrush)


def _keyboard(p, c):
    _pen(p, c)
    p.drawRoundedRect(QRectF(3, 7, 18, 11), 2, 2)
    for x in (6, 9, 12, 15):
        p.drawLine(QPointF(x, 11), QPointF(x, 11))
        p.drawPoint(QPointF(x, 11))
    p.drawLine(QPointF(8, 15), QPointF(16, 15))


def _plug(p, c):
    _pen(p, c)
    p.drawLine(QPointF(12, 3), QPointF(12, 7))
    p.drawRoundedRect(QRectF(7, 7, 10, 7), 2, 2)
    p.drawLine(QPointF(9.5, 14), QPointF(9.5, 17))
    p.drawLine(QPointF(14.5, 14), QPointF(14.5, 17))
    p.drawArc(QRectF(8, 15, 8, 6), 180 * 16, 180 * 16)


def _wrench(p, c):
    _pen(p, c)
    p.drawLine(QPointF(7, 17), QPointF(14, 10))
    p.drawArc(QRectF(11, 3, 9, 9), 120 * 16, 240 * 16)
    p.drawEllipse(QRectF(5, 15, 4, 4))


def _code(p, c):
    _pen(p, c)
    p.drawPolyline([QPointF(8, 8), QPointF(4, 12), QPointF(8, 16)])
    p.drawPolyline([QPointF(16, 8), QPointF(20, 12), QPointF(16, 16)])
    p.drawLine(QPointF(13, 6), QPointF(11, 18))


def _type(p, c):
    _pen(p, c)
    p.drawLine(QPointF(5, 6), QPointF(19, 6))
    p.drawLine(QPointF(12, 6), QPointF(12, 18))
    p.drawLine(QPointF(9, 18), QPointF(15, 18))


def _play(p, c):
    _pen(p, c)
    path = QPainterPath(QPointF(7, 5))
    path.lineTo(19, 12)
    path.lineTo(7, 19)
    path.closeSubpath()
    p.drawPath(path)


def _square(p, c):
    _pen(p, c)
    p.drawRoundedRect(QRectF(6, 6, 12, 12), 1.5, 1.5)


def _star(p, c):
    _pen(p, c)
    import math
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        r = 8 if i % 2 == 0 else 3.4
        pts.append(QPointF(12 + r * math.cos(ang), 12 + r * math.sin(ang)))
    path = QPainterPath(pts[0])
    for pt in pts[1:]:
        path.lineTo(pt)
    path.closeSubpath()
    p.drawPath(path)


def _edit(p, c):
    _pen(p, c)
    p.drawPolyline([QPointF(5, 19), QPointF(5, 15), QPointF(15, 5),
                    QPointF(19, 9), QPointF(9, 19), QPointF(5, 19)])
    p.drawLine(QPointF(13, 7), QPointF(17, 11))


def _trash(p, c):
    _pen(p, c)
    p.drawLine(QPointF(5, 7), QPointF(19, 7))
    p.drawLine(QPointF(9, 7), QPointF(9, 5))
    p.drawLine(QPointF(15, 7), QPointF(15, 5))
    p.drawPolyline([QPointF(6.5, 7), QPointF(7.5, 19), QPointF(16.5, 19),
                    QPointF(17.5, 7)])
    p.drawLine(QPointF(12, 10), QPointF(12, 16))


def _check(p, c):
    _pen(p, c)
    p.drawPolyline([QPointF(5, 12), QPointF(10, 17), QPointF(19, 6)])


def _copy(p, c):
    _pen(p, c)
    p.drawRoundedRect(QRectF(8, 8, 11, 11), 1.5, 1.5)
    path = QPainterPath(QPointF(8, 5))
    path.lineTo(5, 5)
    path.lineTo(5, 16)
    p.drawPath(path)


def _history(p, c):
    _pen(p, c)
    p.drawArc(QRectF(5, 5, 14, 14), 60 * 16, 300 * 16)
    p.drawPolyline([QPointF(5, 5), QPointF(5, 9), QPointF(9, 9)])
    p.drawPolyline([QPointF(12, 8), QPointF(12, 12), QPointF(15, 14)])


def _paperclip(p, c):
    _pen(p, c)
    path = QPainterPath(QPointF(16, 8))
    path.lineTo(8.5, 15.5)
    path.cubicTo(7, 17, 7, 19.5, 9, 19.5)
    path.cubicTo(11, 19.5, 11.5, 18, 13, 16.5)
    path.lineTo(17, 12.5)
    path.cubicTo(19, 10.5, 19, 6.5, 15.5, 6.5)
    path.cubicTo(12, 6.5, 11, 9, 9, 11)
    p.drawPath(path)


_DRAWERS = {
    "code": _code, "type": _type, "play": _play, "square": _square,
    "star": _star, "edit": _edit, "trash": _trash, "check": _check,
    "copy": _copy, "history": _history, "paperclip": _paperclip,
    "files": _files, "explorer": _files, "search": _search, "git": _git,
    "debug": _debug, "flask": _flask, "test": _flask, "extensions": _extensions,
    "memory": _memory, "tasks": _tasks, "settings": _settings, "run": _run,
    "stop": _stop, "chat": _chat, "model": _model, "close": _close,
    "minimize": _minimize, "maximize": _maximize, "restore": _restore,
    "chevron-down": _chevron_down, "chevron-right": _chevron_right,
    "chevron-left": _chevron_left, "sidebar-hide": _chevron_left,
    "folder-collapse": _folder_collapse,
    "plus": _plus, "folder": _folder, "file": _file, "terminal": _terminal,
    "ai": _ai, "menu": _menu, "bell": _bell, "more": _more, "split": _split,
    "refresh": _refresh, "collapse": _collapse, "palette": _palette,
    "keyboard": _keyboard, "plug": _plug, "wrench": _wrench, "window": _maximize,
}


def icon(name: str, size: int = 20, color: str | None = None) -> QIcon:
    """Return a QIcon for `name`, drawn in `color` (defaults to text_secondary)."""
    if color is None:
        color = get_design_system().colors.text_secondary
    qcolor = QColor(color)
    drawer = _DRAWERS.get(name)
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    if drawer is not None:
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.scale(size / 24.0, size / 24.0)
        drawer(painter, qcolor)
        painter.end()
    return QIcon(pm)


def available_icons() -> list:
    return sorted(_DRAWERS.keys())


# ============================================================================
# SECTION: ui.widgets.controls (ui/widgets/controls.py)
# ============================================================================
"""
Shared widgets — v3.0

Small, consistent building blocks used across the shell and panels so geometry,
spacing, hover states, and descriptive hover tooltips ("hints") stay consistent
everywhere.
"""

import re

from PySide6.QtWidgets import (
    QAbstractButton, QPushButton, QToolButton, QCheckBox, QComboBox,
    QSpinBox, QDoubleSpinBox, QLineEdit, QTabWidget, QTabBar, QWidget,
    QHBoxLayout, QVBoxLayout, QLabel, QFrame, QSizePolicy,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QColor

from ui.design_system import get_design_system, Spacing, Radius, FontSize, Sidebar as SB
from ui.widgets.icons import icon


_DEFAULT_ICON_TOOLTIPS = {
    "menu": "Main Menu & Commands (Ctrl+Shift+P)",
    "collapse": "Toggle Left Sidebar (Ctrl+B)",
    "chevron-left": "Hide Left Sidebar (Ctrl+B)",
    "sidebar-hide": "Hide Left Sidebar (Ctrl+B)",
    "chevron-right": "Expand / Push",
    "chevron-down": "Expand / Pull",
    "folder": "Open Folder (Ctrl+O)",
    "folder-collapse": "Collapse All Folders",
    "plus": "Create New / Add",
    "file": "Save File (Ctrl+S)",
    "run": "Run Current File (F5)",
    "play": "Run Program (F5)",
    "flask": "Quick Test Program (F6)",
    "stop": "Stop Running Process",
    "square": "Stop Running Process",
    "terminal": "Toggle Terminal Panel (Ctrl+`)",
    "bell": "Notifications",
    "ai": "Toggle AI Workspace (Ctrl+Shift+A)",
    "settings": "Open Settings (Ctrl+,)",
    "refresh": "Refresh",
    "trash": "Clear / Delete",
    "close": "Close",
    "copy": "Copy to Clipboard",
    "edit": "Edit",
    "check": "Apply / Confirm",
    "code": "Use Regular Expression",
    "type": "Match Case",
    "search": "Search in Workspace (Ctrl+Shift+F)",
    "git": "GitHub / Git Source Control (Ctrl+Shift+G)",
    "debug": "Run & Debug",
    "tasks": "Workspace Tasks",
    "memory": "AI Project Memory",
    "explorer": "File Explorer (Ctrl+Shift+E)",
    "star": "Pin / Unpin Item",
    "history": "View Chat History",
    "paperclip": "Manage Context & Attachments",
    "chat": "Send Message (Enter)",
}


def _humanize_identifier(raw: str) -> str:
    """Turn an objectName or icon key like 'TerminalKillBtn' into 'Terminal Kill'."""
    if not raw:
        return ""
    cleaned = re.sub(r"(?:Btn|Button|Widget|Row|Bar|Panel)$", "", raw)
    cleaned = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", cleaned)
    cleaned = cleaned.replace("_", " ").replace("-", " ").strip()
    return cleaned.title() if cleaned else ""


class IconButton(QToolButton):
    """A flat, square icon button with a consistent hover fill and guaranteed tooltip."""

    def __init__(self, name: str, tooltip: str = "", size: int = 32,
                 icon_size: int = 18, checkable: bool = False, parent=None):
        super().__init__(parent)
        self._name = name
        self._icon_px = icon_size
        self._icon_color: str | None = None
        self.setCheckable(checkable)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(size, size)
        self.setIconSize(QSize(icon_size, icon_size))
        effective_tip = (tooltip or "").strip() or _DEFAULT_ICON_TOOLTIPS.get(
            name, _humanize_identifier(name) or "Action"
        )
        self.setToolTip(effective_tip)
        self.setAutoRaise(True)
        self.refresh_icon()

    def refresh_icon(self, color: str | None = None):
        if color is not None:
            self._icon_color = color
        self.setIcon(icon(self._name, size=self._icon_px, color=self._icon_color))

    def set_icon_name(self, name: str, color: str | None = None):
        self._name = name
        self.refresh_icon(color)

    def refresh_theme(self):
        self.refresh_icon()


class TextButton(QPushButton):
    """A labelled button with an optional leading icon, design-system variant, and automatic tooltip."""

    def __init__(self, text: str = "", icon_name: str | None = None,
                 variant: str = "default", tooltip: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(0)
        self._icon_name = icon_name
        self._variant = variant
        self._custom_tooltip = bool(tooltip)
        if variant and variant != "default":
            self.setProperty("variant", variant)
        if tooltip:
            self.setToolTip(tooltip)
        elif text and text.strip():
            self.setToolTip(text.strip())
        elif icon_name:
            self.setToolTip(_DEFAULT_ICON_TOOLTIPS.get(icon_name, _humanize_identifier(icon_name)))
        if icon_name:
            self.setIconSize(QSize(15, 15))
            self.refresh_icon()

    def setText(self, text: str):
        self._label_text = text
        try:
            super().setText(text)
        except Exception:
            pass

    def text(self) -> str:
        try:
            val = super().text()
            if isinstance(val, str):
                return val.strip()
        except Exception:
            pass
        return getattr(self, "_label_text", "")
        if not self._custom_tooltip and text and text.strip():
            self.setToolTip(text.strip())

    def refresh_icon(self):
        if not self._icon_name:
            return
        col = (get_design_system().colors.text_on_accent
               if self._variant == "primary" else None)
        self.setIcon(icon(self._icon_name, size=15, color=col))

    def refresh_theme(self):
        self.refresh_icon()


class Card(QFrame):
    """A raised, rounded container. Use .body layout to add children."""

    def __init__(self, parent=None, padding: int = Spacing.xl):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setProperty("card", "true")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(padding, padding, padding, padding)
        self.body.setSpacing(Spacing.md)


class Divider(QFrame):
    def __init__(self, horizontal: bool = True, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setProperty("divider", "true")
        if horizontal:
            self.setFixedHeight(1)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        else:
            self.setFixedWidth(1)
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)


class SectionHeader(QFrame):
    """A small uppercase section title with an optional trailing action row and subtle bottom border."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("SectionHeader")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(SB.HEADER_HEIGHT)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(Spacing.md, Spacing.xs, Spacing.sm, Spacing.xs)
        lay.setSpacing(2)
        self._label = QLabel(title.upper())
        self._label.setProperty("role", "subheading")
        self._label.setMinimumWidth(0)
        self._label.setToolTip(f"{title} Section")
        lay.addWidget(self._label, 1)
        self.actions = lay
        self._apply_style()

    def add_action(self, widget: QWidget):
        self.actions.addWidget(widget)

    def set_title(self, title: str):
        self._label.setText(title.upper())
        self._label.setToolTip(f"{title} Section")

    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(
            f"#SectionHeader {{ background: {c.surface}; border-bottom: 1px solid {c.border_subtle}; }}"
        )

    def refresh_theme(self):
        self._apply_style()


class Pill(QLabel):
    """A small rounded status chip."""

    def __init__(self, text: str = "", tone: str = "muted", parent=None):
        super().__init__(text, parent)
        self._tone = tone
        self.set_tone(tone)
        self.setAlignment(Qt.AlignCenter)
        if text:
            self.setToolTip(f"Status: {text}")

    def setText(self, text: str):
        super().setText(text)
        if text:
            self.setToolTip(f"Status: {text}")

    def set_tone(self, tone: str):
        self._tone = tone
        c = get_design_system().colors
        mapping = {
            "accent": (c.accent_muted, c.accent),
            "success": (c.success_muted, c.success),
            "warning": (c.warning_muted, c.warning),
            "error": (c.error_muted, c.error),
            "info": (c.info_muted, c.info),
            "muted": (c.surface_overlay, c.text_muted),
        }
        bg, fg = mapping.get(tone, mapping["muted"])
        self.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:{Radius.sm}px;"
            f" padding:1px 7px; font-size:{FontSize.tiny}px; font-weight:600;"
        )

    def refresh_theme(self):
        self.set_tone(self._tone)


def ensure_tooltips(root: QWidget):
    """
    Guarantee that every button, tab, input field, combo box, and spinbox under
    `root` has a helpful hover tooltip ("hint") showing its name or purpose.
    """
    if root is None:
        return

    for btn in root.findChildren(QAbstractButton):
        if not btn.toolTip():
            raw_text = (btn.text() or "").strip()
            if raw_text in ("×", "✕", "✖"):
                btn.setToolTip("Close / Dismiss")
            elif raw_text in ("+", "＋"):
                btn.setToolTip("Add / Create New")
            elif raw_text in ("-", "−"):
                btn.setToolTip("Remove / Unstage")
            elif raw_text:
                clean = re.sub(r"^[▶■↻⌫✓✕!•\s]+", "", raw_text).strip() or raw_text
                btn.setToolTip(clean)
            else:
                fallback = btn.accessibleName() or _humanize_identifier(btn.objectName())
                if fallback:
                    btn.setToolTip(fallback)

    for combo in root.findChildren(QComboBox):
        if not combo.toolTip():
            hint = _humanize_identifier(combo.objectName()) or "Select option"
            cur = (combo.currentText() or "").strip()
            combo.setToolTip(f"{hint} ({cur})" if cur else hint)

    for spin in root.findChildren((QSpinBox, QDoubleSpinBox)):
        if not spin.toolTip():
            hint = _humanize_identifier(spin.objectName()) or "Adjust numeric value"
            spin.setToolTip(hint)

    for edit in root.findChildren(QLineEdit):
        if not edit.toolTip():
            ph = (edit.placeholderText() or "").strip()
            if ph:
                edit.setToolTip(ph)
            else:
                hint = _humanize_identifier(edit.objectName())
                if hint:
                    edit.setToolTip(hint)

    for tab_bar in root.findChildren(QTabBar):
        for i in range(tab_bar.count()):
            if not tab_bar.tabToolTip(i):
                txt = (tab_bar.tabText(i) or "").strip()
                if txt:
                    tab_bar.setTabToolTip(i, f"{txt} Tab")


def restyle_atoms(root: QWidget):
    """Repaint every palette-baked atom under `root` after a theme change and ensure tooltips."""
    if root is None:
        return
    for widget in root.findChildren(QWidget):
        if isinstance(widget, (IconButton, TextButton, Pill, SectionHeader)):
            try:
                widget.refresh_theme()
            except Exception:
                pass
    try:
        ensure_tooltips(root)
    except Exception:
        pass


def apply_shadow(widget: QWidget, blur: int = 24, y: int = 6, alpha: int = 90):
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setXOffset(0)
    eff.setYOffset(y)
    eff.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(eff)
    return eff


def hline() -> Divider:
    return Divider(horizontal=True)


def vline() -> Divider:
    return Divider(horizontal=False)


# ============================================================================
# SECTION: ui.widgets.diff_view (ui/widgets/diff_view.py)
# ============================================================================
"""
diff_view.py — Reusable side-by-side diff widget.

Renders two versions of a file as an aligned, colour-coded two-column view.
Shared by the Git panel (view a file's working-tree diff) and the AI
change-preview / review flow (see :mod:`ui.dialogs.change_review_dialog`).

Design notes
------------
The view is a single ``QTextBrowser`` containing an HTML table with four
columns: old line-number, old text, new line-number, new text. Using one widget
(rather than two synced editors) makes horizontal/vertical scrolling and row
alignment trivially correct, and lets us colour each side independently:

    equal    → neutral
    delete   → red-tinted on the left, empty filler on the right
    insert   → empty filler on the left, green-tinted on the right
    replace  → red-tinted left + green-tinted right, side by side

Line alignment is computed with :class:`difflib.SequenceMatcher`, so it matches
what developers expect from git/VS Code rather than a naive zip.
"""

import difflib
import html
from typing import List, Optional, Tuple

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser
from PySide6.QtCore import Qt

from ui.design_system import get_design_system, Spacing, FontSize


# One aligned display row: (tag, old_no, old_text, new_no, new_text)
_Row = Tuple[str, Optional[int], str, Optional[int], str]


def build_rows(old_text: Optional[str], new_text: Optional[str]) -> List[_Row]:
    """Align two texts into side-by-side rows using difflib."""
    old_lines = (old_text or "").splitlines()
    new_lines = (new_text or "").splitlines()
    sm = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    rows: List[_Row] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for off in range(i2 - i1):
                rows.append(("equal", i1 + off + 1, old_lines[i1 + off],
                             j1 + off + 1, new_lines[j1 + off]))
        elif tag == "delete":
            for off in range(i2 - i1):
                rows.append(("delete", i1 + off + 1, old_lines[i1 + off], None, ""))
        elif tag == "insert":
            for off in range(j2 - j1):
                rows.append(("insert", None, "", j1 + off + 1, new_lines[j1 + off]))
        elif tag == "replace":
            left = i2 - i1
            right = j2 - j1
            for off in range(max(left, right)):
                o_no = i1 + off + 1 if off < left else None
                o_tx = old_lines[i1 + off] if off < left else ""
                n_no = j1 + off + 1 if off < right else None
                n_tx = new_lines[j1 + off] if off < right else ""
                rows.append(("replace", o_no, o_tx, n_no, n_tx))
    return rows


class DiffView(QWidget):
    """A read-only side-by-side diff viewer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DiffView")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._browser = QTextBrowser(self)
        self._browser.setOpenExternalLinks(False)
        self._browser.setLineWrapMode(QTextBrowser.NoWrap)
        lay.addWidget(self._browser)
        self._old = ""
        self._new = ""
        self._apply_style()

    # ── public API ─────────────────────────────────────────────────────────────
    def set_texts(self, old_text: Optional[str], new_text: Optional[str]) -> None:
        """Show a diff between ``old_text`` (left) and ``new_text`` (right)."""
        self._old = old_text or ""
        self._new = new_text or ""
        self._render(build_rows(old_text, new_text))

    def set_unified(self, unified_text: str) -> None:
        """Render a unified-diff string by reconstructing left/right columns.

        Used by the Git panel, whose service returns unified-diff text.
        """
        old_lines, new_lines = self._split_unified(unified_text)
        self.set_texts("\n".join(old_lines), "\n".join(new_lines))

    def clear(self) -> None:
        self._browser.clear()

    # ── rendering ──────────────────────────────────────────────────────────────
    def _render(self, rows: List[_Row]) -> None:
        c = get_design_system().colors
        add_bg = getattr(c, "success_muted", "#183d18")
        del_bg = getattr(c, "error_muted", "#3d1818")
        gutter = getattr(c, "text_muted", "#888")
        cells = []
        for tag, o_no, o_tx, n_no, n_tx in rows:
            left_bg = del_bg if tag in ("delete", "replace") and o_no is not None else "transparent"
            right_bg = add_bg if tag in ("insert", "replace") and n_no is not None else "transparent"
            cells.append(
                f"<tr>"
                f"<td class='ln' style='color:{gutter}'>{o_no if o_no else ''}</td>"
                f"<td class='src' style='background:{left_bg}'>{self._esc(o_tx)}</td>"
                f"<td class='ln' style='color:{gutter}'>{n_no if n_no else ''}</td>"
                f"<td class='src' style='background:{right_bg}'>{self._esc(n_tx)}</td>"
                f"</tr>"
            )
        table = (
            "<table cellspacing='0' cellpadding='0' style='width:100%'>"
            + "".join(cells) + "</table>"
        )
        self._browser.setHtml(table)

    @staticmethod
    def _esc(text: str) -> str:
        if text == "":
            return "&nbsp;"
        return html.escape(text).replace(" ", "&nbsp;").replace("\t", "&nbsp;" * 4)

    @staticmethod
    def _split_unified(unified: str) -> Tuple[List[str], List[str]]:
        old: List[str] = []
        new: List[str] = []
        for line in unified.splitlines():
            if line.startswith(("+++", "---", "diff ", "index ", "@@")):
                continue
            if line.startswith("+"):
                new.append(line[1:])
            elif line.startswith("-"):
                old.append(line[1:])
            else:
                body = line[1:] if line.startswith(" ") else line
                old.append(body)
                new.append(body)
        return old, new

    def _apply_style(self):
        c = get_design_system().colors
        self._browser.setStyleSheet(
            f"QTextBrowser {{ background:{c.surface}; color:{c.text_primary};"
            f" border:none; font-family:'Cascadia Code','Consolas',monospace;"
            f" font-size:{FontSize.small}px; }}"
        )

    def refresh_theme(self):
        self._apply_style()
        self.set_texts(self._old, self._new)


# ============================================================================
# SECTION: ui.widgets.native_dialogs (ui/widgets/native_dialogs.py)
# ============================================================================
"""
Native Dialogs — v2.0

Helpers that surface the *operating system's own* file picker rather than Qt's
fallback widget dialog.

Why this exists: ``QFileDialog.getExistingDirectory`` only draws a native dialog
when a Qt platform-theme integration is installed (KDE's ``plasma-integration``,
a GTK plugin, or ``xdg-desktop-portal``). On a bare setup Qt silently falls back
to its generic widget dialog. To guarantee users get their desktop's real file
manager dialog (Dolphin on KDE/CachyOS, Files/Nautilus on GNOME, Explorer on
Windows, Finder on macOS), we invoke the desktop's native picker directly on
Linux and rely on Qt's genuinely-native dialog everywhere else.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

from PySide6.QtWidgets import QFileDialog


def select_existing_directory(parent=None, title: str = "Open Folder",
                              start_dir: str = "") -> str:
    """Return an absolute directory path, or "" if the user cancelled."""
    start_dir = start_dir or str(Path.home())

    if sys.platform.startswith("linux"):
        result = _linux_native(title, start_dir, directory=True)
        if result is not None:          # a native tool handled it (path or cancel)
            return result

    # Windows / macOS: Qt's dialog is genuinely native here.
    # Linux fallback: portal-backed native dialog if available, else Qt's widget.
    return QFileDialog.getExistingDirectory(parent, title, start_dir) or ""


def select_existing_file(parent=None, title: str = "Open File",
                         start_dir: str = "") -> str:
    """Return an absolute file path, or "" if the user cancelled."""
    start_dir = start_dir or str(Path.home())

    if sys.platform.startswith("linux"):
        result = _linux_native(title, start_dir, directory=False)
        if result is not None:
            return result

    path, _ = QFileDialog.getOpenFileName(parent, title, start_dir)
    return path or ""


def select_save_file(parent=None, title: str = "Save File",
                     start_dir: str = "", suggested_name: str = "") -> str:
    """Ask where to *write* a file. Returns an absolute path, or "" if cancelled.

    Used by Save As and by the first save of an untitled buffer. Unlike the open
    helpers the target need not exist yet, so the native tools get their
    save-mode flags (``kdialog --getsavefilename`` / ``zenity --save``) and Qt
    falls back to ``getSaveFileName``.
    """
    start_dir = start_dir or str(Path.home())
    initial = os.path.join(start_dir, suggested_name) if suggested_name else \
        os.path.join(start_dir, "")

    if sys.platform.startswith("linux"):
        result = _linux_save(title, initial)
        if result is not None:
            return result

    path, _ = QFileDialog.getSaveFileName(parent, title, initial)
    return path or ""


# ── Linux native pickers ──────────────────────────────────────────────────
def _linux_save(title: str, initial: str) -> str | None:
    """Native save-as picker. Path, "" on cancel, or None if unrunnable."""
    kdialog = shutil.which("kdialog")
    zenity = shutil.which("zenity")
    order = [kdialog, zenity] if (_is_kde() and kdialog) else [zenity, kdialog]

    for tool in order:
        if not tool:
            continue
        if tool.endswith("kdialog"):
            cmd = [tool, "--title", title, "--getsavefilename", initial]
        else:  # zenity
            cmd = [tool, "--file-selection", "--save",
                   "--confirm-overwrite", "--title", title,
                   "--filename", initial]
        result = _run_picker(cmd)
        if result is not None:
            return result
    return None


def _linux_native(title: str, start_dir: str, directory: bool) -> str | None:
    """Try the desktop's own file/folder picker.

    Returns the chosen path, "" on user cancel, or None if no native tool
    could be launched (so the caller can fall back to Qt).
    """
    kdialog = shutil.which("kdialog")
    zenity = shutil.which("zenity")

    if _is_kde() and kdialog:
        order = [kdialog, zenity]
    elif zenity:
        order = [zenity, kdialog]
    else:
        order = [kdialog, zenity]

    for tool in order:
        if not tool:
            continue
        if tool.endswith("kdialog"):
            flag = "--getexistingdirectory" if directory else "--getopenfilename"
            cmd = [tool, "--title", title, flag, start_dir]
        else:  # zenity
            cmd = [tool, "--file-selection", "--title", title,
                   "--filename", os.path.join(start_dir, "")]
            if directory:
                cmd.append("--directory")
        result = _run_picker(cmd)
        if result is not None:
            return result
    return None


def _run_picker(cmd: list[str]) -> str | None:
    """Run a native picker. Path on success, "" on cancel, None if unrunnable."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except Exception:
        return None
    if proc.returncode == 0:
        return proc.stdout.strip()
    return ""  # non-zero from these tools means the user cancelled


def _is_kde() -> bool:
    desktop = (os.environ.get("XDG_CURRENT_DESKTOP", "") + " " +
               os.environ.get("XDG_SESSION_DESKTOP", "")).lower()
    if "kde" in desktop or "plasma" in desktop:
        return True
    return bool(os.environ.get("KDE_FULL_SESSION"))

