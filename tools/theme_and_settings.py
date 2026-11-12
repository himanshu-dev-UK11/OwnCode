"""
Consolidated Module: tools.theme_and_settings

Combines: ui.settings_manager, ui.design_system, ui.theme
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['ui.settings_manager', 'ui.design_system', 'ui.theme']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ui.settings_manager (ui/settings_manager.py)
# ============================================================================
"""
Settings Manager — v0.8

Handles application settings persistence and management.
Supports:
- General settings
- Appearance settings
- Editor settings
- Workspace settings
- Models settings
- AI settings
- Git settings
- Keyboard shortcuts

All settings are persisted to a JSON file.
"""

import json
import copy
from pathlib import Path
try:
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtCore import Qt, QLocale
except ImportError:
    QGuiApplication = None
    Qt = None
    QLocale = None


class SettingsManager:
    """
    Manages application settings with persistence.
    
    Settings are stored in config/settings.json
    """
    
    def __init__(self):
        self._config_dir = Path("config")
        self._config_file = self._config_dir / "settings.json"
        self._settings = {}
        self._default_settings = self._get_default_settings()
        self._load()
        
    def _get_default_settings(self) -> dict:
        """Get default settings."""
        return {
            "general": {
                "auto_save": False,
                "auto_save_delay": 3000,
                "restore_session": True,
                "show_welcome": True,
                "language": "en",
                "theme": "paper_ink"
            },
            "appearance": {
                "font_family": "Inter, Segoe UI, SF Pro Display, system-ui, sans-serif",
                "font_size": 12,
                "font_ligatures": True,
                "line_height": 1.5,
                "letter_spacing": 0,
                "word_wrap": True,
                "minimap": True,
                "scrollbar_size": 8
            },
            "editor": {
                "tab_size": 4,
                "insert_spaces": True,
                "render_whitespace": "none",
                "cursor_blinking": True,
                "cursor_style": "line",
                "word_based_suggestions": True,
                "automatic_completions": True,
                "format_on_type": True,
                "format_on_save": False
            },
            "workspace": {
                "single_click_open": True,
                "preview_single_click": False,
                "reveal_active_file": True,
                "auto_scan": True,
                "scan_delay": 1000,
                "follow_symlinks": False,
                "exclude_patterns": [
                    ".git",
                    "__pycache__",
                    "node_modules",
                    ".vscode",
                    ".idea"
                ]
            },
            "models": {
                "default_model": "llama_cpp:qwen2.5-coder-7b-instruct-q4_k_m",
                "routing_policy": "local_only",
                "banned_models": ["deepseek"],
                "models": {
                    "qwen3:8b": {
                        "name": "Qwen 3 8B",
                        "provider": "ollama",
                        "context_window": 32768,
                        "enabled": True
                    }
                }
            },
            "ai": {
                "auto_context": True,
                "max_context_files": 10,
                "context_window_size": 4096,
                "max_tokens": 4096,
                "temperature": 0.7,
                "streaming": True,
                "smart_suggestions": True,
                "auto_verify": True,
                "inline_ai_enabled": False,
                "inline_completions_enabled": False
            },
            "git": {
                "enabled": True,
                "auto_refresh": True,
                "refresh_interval": 5000,
                "commit_on_save": False,
                "push_on_close": False
            },
            "github": {
                "enabled": False,
                "token": "",
                "username": "",
                "default_branch": "main"
            },
            "keyboard": {
                "shortcuts": {
                    "command_palette": ["Ctrl+Shift+P"],
                    "new_file": ["Ctrl+N"],
                    "open_folder": ["Ctrl+K", "Ctrl+O"],
                    "save": ["Ctrl+S"],
                    "save_all": ["Ctrl+Shift+S"],
                    "close": ["Ctrl+W"],
                    "next_tab": ["Ctrl+Tab"],
                    "prev_tab": ["Ctrl+Shift+Tab"],
                    "run": ["F5"],
                    "stop": ["Shift+F5"],
                    "toggle_terminal": ["Ctrl+`"],
                    "toggle_explorer": ["Ctrl+B"],
                    "toggle_ai_panel": ["Ctrl+\\"] 
                }
            },
            "window": {
                "restore_layout": True,
                "remember_position": True,
                "remember_size": True,
                "remember_maximized": True
            },
            "terminal": {
                "font_family": "JetBrains Mono, Cascadia Code, Consolas",
                "font_size": 11,
                "cursor_shape": "block",
                "cursor_blink": True,
                "line_height": 1.5,
                "scrollback_size": 10000,
                "default_shell": "cmd",
                "default_working_dir": "",
                "copy_on_select": False,
                "confirm_before_close": True,
                "bell": False,
                "smooth_scrolling": True,
                "padding": 8
            }
        }
        
    def _load(self):
        """Load settings from file."""
        try:
            if self._config_file.exists():
                with open(self._config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Merge with defaults to ensure new settings exist
                    self._settings = self._deep_merge(self._default_settings, loaded)
            else:
                # deepcopy, else _settings and _default_settings would share the
                # same nested dicts and every set() would corrupt the defaults.
                self._settings = copy.deepcopy(self._default_settings)
                self._save()
        except Exception as e:
            print(f"Error loading settings: {e}")
            self._settings = copy.deepcopy(self._default_settings)
            
    def _save(self):
        """Save settings to file."""
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
            
    def _deep_merge(self, default: dict, loaded: dict) -> dict:
        """Deep merge loaded into default."""
        result = default.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
        
    def get(self, category: str, key: str, default=None):
        """Get a setting value."""
        category_data = self._settings.get(category, {})
        return category_data.get(key, default)
        
    def set(self, category: str, key: str, value):
        """Set a setting value."""
        if category not in self._settings:
            self._settings[category] = {}
        self._settings[category][key] = value
        self._save()
        
    def get_all(self, category: str) -> dict:
        """Get all settings for a category."""
        return self._settings.get(category, {})
        
    def set_all(self, category: str, settings: dict):
        """Set all settings for a category."""
        self._settings[category] = settings
        self._save()
        
    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        # deepcopy: a shallow copy would hand out the *same* nested dicts the
        # defaults are built from, so the next set() would rewrite them.
        self._settings = copy.deepcopy(self._default_settings)
        self._save()

    def reset_category(self, category: str):
        """Reset a category to defaults."""
        if category in self._default_settings:
            self._settings[category] = copy.deepcopy(self._default_settings[category])
            self._save()

    def get_default(self, category: str, key: str = None):
        """Factory default for a category, or for a single key inside it."""
        cat = self._default_settings.get(category, {})
        if key is None:
            return copy.deepcopy(cat)
        return copy.deepcopy(cat.get(key))

    def categories(self) -> list:
        """Names of all known setting categories."""
        return list(self._default_settings.keys())
            
    def get_theme(self) -> str:
        """Get current theme setting."""
        theme = self.get("general", "theme", "system")
        if theme == "system":
            # Detect system theme
            return self._detect_system_theme()
        return theme
        
    def _detect_system_theme(self) -> str:
        """Detect system theme (dark/light)."""
        # Try Qt's policy first
        if hasattr(QGuiApplication, 'styleHints'):
            color_scheme = QGuiApplication.styleHints().colorScheme()
            if color_scheme == Qt.ColorScheme.Dark:
                return "dark"
            elif color_scheme == Qt.ColorScheme.Light:
                return "light"
        
        # Fallback: check if any widget has dark background
        return "dark"  # Default to dark for now
        
    def get_font_family(self) -> str:
        """Get font family for UI."""
        return self.get("appearance", "font_family", "Inter, Segoe UI, sans-serif")
        
    def get_font_size(self) -> int:
        """Get font size for UI."""
        return self.get("appearance", "font_size", 12)
        
    def is_auto_save_enabled(self) -> bool:
        """Check if auto-save is enabled."""
        return self.get("general", "auto_save", False)
        
    def get_auto_save_delay(self) -> int:
        """Get auto-save delay in milliseconds."""
        return self.get("general", "auto_save_delay", 3000)
        
    def is_restore_session_enabled(self) -> bool:
        """Check if session restore is enabled."""
        return self.get("general", "restore_session", True)
        
    def is_show_welcome_enabled(self) -> bool:
        """Check if welcome screen should be shown."""
        return self.get("general", "show_welcome", True)
        
    def get_keyboard_shortcut(self, action: str) -> list:
        """Get keyboard shortcut for an action."""
        shortcuts = self.get("keyboard", "shortcuts", {})
        return shortcuts.get(action, [])
        
    def set_keyboard_shortcut(self, action: str, keys: list):
        """Set keyboard shortcut for an action."""
        shortcuts = self.get("keyboard", "shortcuts", {})
        shortcuts[action] = keys
        self.set("keyboard", "shortcuts", shortcuts)
        
    def is_git_enabled(self) -> bool:
        """Check if Git is enabled."""
        return self.get("git", "enabled", True)
        
    def is_github_enabled(self) -> bool:
        """Check if GitHub integration is enabled."""
        return self.get("github", "enabled", False)
        
    def get_exclude_patterns(self) -> list:
        """Get workspace exclude patterns."""
        return self.get("workspace", "exclude_patterns", [])
        
    def get_default_model(self) -> str:
        """Get default AI model."""
        return self.get("models", "default_model", "auto")


# Global instance
_settings_manager = None


def get_settings_manager() -> SettingsManager:
    """Get the global settings manager instance."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager


def reset_settings_manager():
    """Reset the global settings manager (for testing)."""
    global _settings_manager
    _settings_manager = None


# ============================================================================
# SECTION: ui.design_system (ui/design_system.py)
# ============================================================================
"""
Design System — v2.0 (Graphite Dark)

A single source of truth for the entire UI: colour tokens, spacing grid,
radius scale, type scale, motion, per-component geometry, and a QSS generator.

Design language:
  - Graphite dark: a 6-step neutral elevation ramp on a near-black canvas.
  - ONE saturated accent (clean blue) used sparingly for focus/selection/state.
  - Strict 4px spacing grid; 4-step radius scale; two chrome font sizes.

Public API (kept stable for main.py + panels):
  get_design_system() -> DesignSystem      (singleton)
  set_design_system_theme(name)            (switch palette)
  DesignSystem.get_stylesheet(component)   ("global" = whole-app QSS)
  Token classes: Spacing, Radius, FontFamily, FontSize, FontWeight, Duration,
                 Easing, Titlebar, Toolbar, ActivityBar, Sidebar, AIPanel,
                 StatusBar, Terminal, Editor
  ColorPalette dataclass + PALETTES registry
"""

from dataclasses import dataclass, field
from typing import Dict


# ─────────────────────────────────────────────────────────────────────────────
# Colour palette
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ColorPalette:
    name: str

    # Elevation ramp (darkest → lightest surface)
    canvas: str          # deepest background, behind everything
    surface: str         # default panel background
    surface_raised: str  # cards, inputs
    surface_overlay: str # menus, popovers, hover fills
    surface_high: str    # active/selected fills
    surface_inset: str   # wells, editors gutter

    # Borders
    border_subtle: str
    border: str
    border_strong: str
    border_focus: str

    # Text
    text_primary: str
    text_secondary: str
    text_muted: str
    text_faint: str
    text_on_accent: str

    # Accent (single hue)
    accent: str
    accent_hover: str
    accent_active: str
    accent_muted: str      # translucent fill
    accent_border: str

    # Semantic
    success: str
    warning: str
    error: str
    info: str
    success_muted: str
    warning_muted: str
    error_muted: str
    info_muted: str

    # Syntax (editor)
    syn_keyword: str
    syn_string: str
    syn_comment: str
    syn_number: str
    syn_function: str
    syn_class: str
    syn_operator: str
    syn_bracket: str

    # Scrollbar / misc
    scrollbar: str
    scrollbar_hover: str
    selection: str
    shadow: str

    # Light palettes need this to be False so components that branch on
    # brightness (icons, syntax fallbacks, QPalette) render correctly.
    # Defaulted so the existing dark palettes keep working unchanged.
    is_dark: bool = True

    def as_dict(self) -> Dict[str, str]:
        return {k: v for k, v in self.__dict__.items() if isinstance(v, str)}


GRAPHITE = ColorPalette(
    name="graphite",
    canvas="#0c0e10",
    surface="#131619",
    surface_raised="#1a1e22",
    surface_overlay="#22272d",
    surface_high="#2b3138",
    surface_inset="#0f1214",
    border_subtle="#20262c",
    border="#2c333a",
    border_strong="#3b444d",
    border_focus="#4c8fff",
    text_primary="#e6edf3",
    text_secondary="#adbac7",
    text_muted="#768390",
    text_faint="#545d68",
    text_on_accent="#ffffff",
    accent="#4c8fff",
    accent_hover="#6ba3ff",
    accent_active="#3b7ce6",
    accent_muted="rgba(76,143,255,0.14)",
    accent_border="rgba(76,143,255,0.45)",
    success="#3fb950",
    warning="#d29922",
    error="#f85149",
    info="#58a6ff",
    success_muted="rgba(63,185,80,0.15)",
    warning_muted="rgba(210,153,34,0.15)",
    error_muted="rgba(248,81,73,0.15)",
    info_muted="rgba(88,166,255,0.15)",
    syn_keyword="#c7a2ff",
    syn_string="#8ddb8c",
    syn_comment="#6a7481",
    syn_number="#f0a072",
    syn_function="#6cb6ff",
    syn_class="#f2cc60",
    syn_operator="#7ce0e6",
    syn_bracket="#e6a4d6",
    scrollbar="#2c333a",
    scrollbar_hover="#3b444d",
    selection="rgba(76,143,255,0.28)",
    shadow="rgba(0,0,0,0.45)",
)

# A slightly warmer alternative kept for parity with the old "clay" default.
SLATE = ColorPalette(
    name="slate",
    canvas="#0b0f14",
    surface="#111722",
    surface_raised="#18202c",
    surface_overlay="#202a38",
    surface_high="#2a3646",
    surface_inset="#0d131b",
    border_subtle="#1d2836",
    border="#293747",
    border_strong="#38495c",
    border_focus="#5ea0ff",
    text_primary="#e8eef6",
    text_secondary="#aebacb",
    text_muted="#74839a",
    text_faint="#515e72",
    text_on_accent="#ffffff",
    accent="#5ea0ff",
    accent_hover="#7db3ff",
    accent_active="#4a8ae6",
    accent_muted="rgba(94,160,255,0.14)",
    accent_border="rgba(94,160,255,0.45)",
    success="#40c463",
    warning="#e0a83a",
    error="#ff6b63",
    info="#69b0ff",
    success_muted="rgba(64,196,99,0.15)",
    warning_muted="rgba(224,168,58,0.15)",
    error_muted="rgba(255,107,99,0.15)",
    info_muted="rgba(105,176,255,0.15)",
    syn_keyword="#c7a2ff",
    syn_string="#8ddb8c",
    syn_comment="#63718a",
    syn_number="#f0a072",
    syn_function="#6cb6ff",
    syn_class="#f2cc60",
    syn_operator="#7ce0e6",
    syn_bracket="#e6a4d6",
    scrollbar="#293747",
    scrollbar_hover="#38495c",
    selection="rgba(94,160,255,0.28)",
    shadow="rgba(0,0,0,0.5)",
)

PALETTES: Dict[str, ColorPalette] = {
    "graphite": GRAPHITE,
    "slate": SLATE,
}

# ─────────────────────────────────────────────────────────────────────────────
# Palette factory
#
# A full palette is ~40 fields, most of which are mechanically derived from a
# handful of seeds (the surface ramp, the text ramp and one accent). Spelling
# every field out per theme would be ~400 lines of near-duplicate hex, so the
# themes below declare only what makes them distinct and inherit the rest.
# ─────────────────────────────────────────────────────────────────────────────
def _rgba(hex_color: str, alpha: float) -> str:
    """Convert '#rrggbb' + alpha into a QSS rgba() string."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


# Shared semantic + syntax defaults. Themes override only what they restyle.
_DARK_SEMANTIC = dict(success="#3fb950", warning="#d29922", error="#f85149", info="#58a6ff")
_LIGHT_SEMANTIC = dict(success="#1a7f37", warning="#9a6700", error="#cf222e", info="#0969da")

_DARK_SYNTAX = dict(
    syn_keyword="#c7a2ff", syn_string="#8ddb8c", syn_comment="#6a7481",
    syn_number="#f0a072", syn_function="#6cb6ff", syn_class="#f2cc60",
    syn_operator="#7ce0e6", syn_bracket="#e6a4d6",
)
_LIGHT_SYNTAX = dict(
    syn_keyword="#8250df", syn_string="#0a7c42", syn_comment="#8b949e",
    syn_number="#bc4c00", syn_function="#0550ae", syn_class="#953800",
    syn_operator="#1b7c83", syn_bracket="#a24aa2",
)


def make_palette(
    name: str,
    *,
    ramp: tuple,          # 6 surfaces: canvas, surface, raised, overlay, high, inset
    borders: tuple,       # 3 borders: subtle, base, strong
    text: tuple,          # 4 text tones: primary, secondary, muted, faint
    accent: str,
    accent_hover: str,
    accent_active: str,
    is_dark: bool = True,
    text_on_accent: str = "#ffffff",
    selection_alpha: float = 0.28,
    shadow_alpha: float = 0.45,
    **overrides,
) -> ColorPalette:
    """Build a full ColorPalette from its distinctive seeds.

    Translucent fills (accent_muted, selection, the *_muted semantics) are
    derived from their solid counterpart so every theme stays internally
    consistent; pass any field name in **overrides to opt out.
    """
    canvas, surface, raised, overlay, high, inset = ramp
    b_subtle, b_base, b_strong = borders
    t_primary, t_secondary, t_muted, t_faint = text
    semantic = dict(_DARK_SEMANTIC if is_dark else _LIGHT_SEMANTIC)
    syntax = dict(_DARK_SYNTAX if is_dark else _LIGHT_SYNTAX)

    fields = dict(
        name=name, is_dark=is_dark,
        canvas=canvas, surface=surface, surface_raised=raised,
        surface_overlay=overlay, surface_high=high, surface_inset=inset,
        border_subtle=b_subtle, border=b_base, border_strong=b_strong,
        border_focus=accent,
        text_primary=t_primary, text_secondary=t_secondary,
        text_muted=t_muted, text_faint=t_faint, text_on_accent=text_on_accent,
        accent=accent, accent_hover=accent_hover, accent_active=accent_active,
        accent_muted=_rgba(accent, 0.14), accent_border=_rgba(accent, 0.45),
        scrollbar=b_base, scrollbar_hover=b_strong,
        selection=_rgba(accent, selection_alpha),
        shadow=_rgba("#000000", shadow_alpha),
        **semantic, **syntax,
    )
    for key, solid in (("success_muted", fields["success"]),
                       ("warning_muted", fields["warning"]),
                       ("error_muted", fields["error"]),
                       ("info_muted", fields["info"])):
        fields[key] = _rgba(solid, 0.15)
    fields.update(overrides)
    return ColorPalette(**fields)


# ── Dark themes ──────────────────────────────────────────────────────────────

# Matte: no pure blacks and no glare. Desaturated charcoal with a soft steel
# accent and deliberately low contrast for long sessions in dim rooms.
MATTE = make_palette(
    "matte",
    ramp=("#1b1c1e", "#232427", "#2a2c30", "#33363b", "#3d4046", "#1f2022"),
    borders=("#2d2f33", "#393c41", "#4a4e55"),
    text=("#dcdee1", "#adb1b8", "#7f858e", "#5f656d"),
    accent="#8aa2b8", accent_hover="#9fb4c8", accent_active="#748ca2",
    selection_alpha=0.24, shadow_alpha=0.35,
    syn_keyword="#b3a6d1", syn_string="#a3c49a", syn_comment="#6f757e",
    syn_number="#d6a888", syn_function="#93b4d1", syn_class="#d8c58a",
)

# Clay: the warm, earthy, softly-rounded feel of Zen Browser. Brown-grey
# surfaces with a terracotta accent instead of the usual blue.
CLAY = make_palette(
    "clay",
    ramp=("#1a1614", "#221d1a", "#2b2521", "#352d28", "#413731", "#1d1917"),
    borders=("#2e2723", "#3b322c", "#4d423a"),
    text=("#f0e7e0", "#c8b8ad", "#96877d", "#6e625a"),
    accent="#d98b6a", accent_hover="#e6a184", accent_active="#c07454",
    selection_alpha=0.26, shadow_alpha=0.5,
    success="#7fa86b", warning="#d9a55c", error="#dc7a6b", info="#c99a7a",
    syn_keyword="#d9a0c0", syn_string="#a8bd82", syn_comment="#7a6c63",
    syn_number="#e0a06a", syn_function="#e2b48c", syn_class="#e8c98a",
    syn_operator="#c9a58a", syn_bracket="#d4a5b5",
)

# Mocha: coffee-dark with a creamy amber accent. Warmer than clay, deeper.
MOCHA = make_palette(
    "mocha",
    ramp=("#14100e", "#1c1714", "#241d19", "#2e2620", "#3a302a", "#171310"),
    borders=("#28211c", "#342b25", "#453930"),
    text=("#ede4d8", "#c2b3a2", "#8e8173", "#665c51"),
    accent="#e0a458", accent_hover="#ecb972", accent_active="#c78c43",
    syn_keyword="#c9a0dc", syn_string="#b5c98a", syn_comment="#75695d",
    syn_number="#e8a86a", syn_function="#e8c68a", syn_class="#f0d49a",
)

# Midnight: deep navy canvas, crisp cyan accent. High contrast, cool.
MIDNIGHT = make_palette(
    "midnight",
    ramp=("#080b14", "#0e1320", "#151c2c", "#1d2739", "#273349", "#0a0f1a"),
    borders=("#18202f", "#222d40", "#324158"),
    text=("#e4ecf7", "#a7b6cc", "#6f7f99", "#4d5a70"),
    accent="#4dd0e1", accent_hover="#6fdcea", accent_active="#3bb3c4",
    shadow_alpha=0.6,
    syn_keyword="#a5b4fc", syn_string="#7ee0c0", syn_comment="#5a6883",
    syn_number="#f0a8a0", syn_function="#7cc6ff", syn_class="#ffd88a",
)

# Nord: the arctic blue-grey palette, muted and even-toned.
NORD = make_palette(
    "nord",
    ramp=("#242933", "#2e3440", "#3b4252", "#434c5e", "#4c566a", "#292e39"),
    borders=("#3b4252", "#434c5e", "#4c566a"),
    text=("#eceff4", "#d8dee9", "#9aa5b4", "#717d8f"),
    accent="#88c0d0", accent_hover="#9fd0dd", accent_active="#6fa8ba",
    selection_alpha=0.3, shadow_alpha=0.35,
    success="#a3be8c", warning="#ebcb8b", error="#bf616a", info="#81a1c1",
    syn_keyword="#81a1c1", syn_string="#a3be8c", syn_comment="#697c8f",
    syn_number="#b48ead", syn_function="#88c0d0", syn_class="#ebcb8b",
    syn_operator="#8fbcbb", syn_bracket="#d08770",
)

# Forest: deep green-black with a fresh moss accent.
FOREST = make_palette(
    "forest",
    ramp=("#0a1210", "#111b18", "#182420", "#1f2e29", "#293b34", "#0c1513"),
    borders=("#1a2723", "#22322c", "#2f4239"),
    text=("#e3efe9", "#a8c2b6", "#75907f", "#546b5e"),
    accent="#5fc98a", accent_hover="#7dd8a0", accent_active="#48ad72",
    syn_keyword="#9fd6b0", syn_string="#c8e08a", syn_comment="#5e7568",
    syn_number="#e0b070", syn_function="#7fd0b8", syn_class="#e8d48a",
)

# Rosé: mauve-plum surfaces with a dusty pink accent.
ROSE = make_palette(
    "rose",
    ramp=("#16121b", "#1e1926", "#262030", "#302a3c", "#3c3449", "#191420"),
    borders=("#2a2333", "#352d40", "#463c54"),
    text=("#efe6f2", "#c3b3cc", "#8f8199", "#685c73"),
    accent="#e0879f", accent_hover="#eb9fb3", accent_active="#c86e87",
    syn_keyword="#c4a7e7", syn_string="#9ccfd8", syn_comment="#6e6480",
    syn_number="#f0a08a", syn_function="#ebbcba", syn_class="#f6c177",
)

# Contrast: maximum legibility — pure black, white text, thick visible borders.
# Intended for accessibility and bright rooms, not for looks.
CONTRAST = make_palette(
    "contrast",
    ramp=("#000000", "#0a0a0a", "#141414", "#1f1f1f", "#2e2e2e", "#000000"),
    borders=("#3d3d3d", "#5c5c5c", "#8a8a8a"),
    text=("#ffffff", "#ebebeb", "#c4c4c4", "#9e9e9e"),
    accent="#ffcc00", accent_hover="#ffd733", accent_active="#e6b800",
    text_on_accent="#000000", selection_alpha=0.35, shadow_alpha=0.7,
    success="#4ae168", warning="#ffcc00", error="#ff5c5c", info="#5cc8ff",
    syn_keyword="#ff9cf0", syn_string="#7dff9e", syn_comment="#a8a8a8",
    syn_number="#ffb86c", syn_function="#8ad4ff", syn_class="#ffe066",
)

# ── Light themes ─────────────────────────────────────────────────────────────


# Paper Ink: signature calm editorial computing aesthetic — warm archival
# manuscript paper (#FAF8F5 / #F4F1EA), deep charcoal ink (#181816),
# botanical forest green primary accent (#1B5E3A), and warm terracotta
# secondary/semantic highlight (#C85A32).
PAPER_INK = make_palette(
    "paper_ink",
    ramp=("#f4f1ea", "#faf8f5", "#f2efe7", "#eae5d9", "#dfd9ca", "#ffffff"),
    borders=("#e6e2d8", "#ddd8cc", "#c5beb0"),
    text=("#181816", "#3d3b36", "#6e6a61", "#9a958b"),
    accent="#1b5e3a",
    accent_hover="#237047",
    accent_active="#14492c",
    is_dark=False,
    selection_alpha=0.18,
    shadow_alpha=0.10,
    success="#1b5e3a",
    warning="#c85a32",
    error="#b93829",
    info="#2b5b84",
    syn_keyword="#1b5e3a",
    syn_string="#9e472a",
    syn_comment="#8a8479",
    syn_number="#c85a32",
    syn_function="#1e4d6b",
    syn_class="#7a3e1d",
    syn_operator="#4a554e",
    syn_bracket="#5c5346",
)

# Warm Parchment: classical scholar's vellum cream with oxblood & sepia ink.
PARCHMENT = make_palette(
    "parchment",
    ramp=("#efe9dc", "#f7f3e8", "#ede6d6", "#e4dcc8", "#d8ceb6", "#fdfbf6"),
    borders=("#e0d8c6", "#d2c8b2", "#b8ac94"),
    text=("#221d17", "#463d33", "#73685a", "#9c9080"),
    accent="#7c2d23",
    accent_hover="#94382c",
    accent_active="#63221a",
    is_dark=False,
    selection_alpha=0.16,
    shadow_alpha=0.12,
    success="#2d663b",
    warning="#b85d28",
    error="#a82929",
    info="#2b5878",
)

# Botanical Sage: soft sage-tinted paper with deep pine & amber ink.
SAGE_PAPER = make_palette(
    "sage_paper",
    ramp=("#eef2ed", "#f5f8f4", "#e8ede6", "#dee5dc", "#d0d9ce", "#fbfdfb"),
    borders=("#dce3da", "#ccd5c9", "#b2bfb0"),
    text=("#162019", "#344238", "#5f6f63", "#8b998e"),
    accent="#1f6342",
    accent_hover="#287851",
    accent_active="#174d33",
    is_dark=False,
    selection_alpha=0.18,
    shadow_alpha=0.10,
    success="#1f6342",
    warning="#c2622d",
    error="#b8372b",
    info="#275c7a",
)

# Carbon Ink: dark-mode counterpart to Paper Ink — warm pressroom carbon
# surfaces with botanical emerald and terracotta highlights.
INK_DARK = make_palette(
    "ink_dark",
    ramp=("#111210", "#171815", "#1f211c", "#282b24", "#33372e", "#141512"),
    borders=("#252822", "#31352d", "#43483d"),
    text=("#ece9e0", "#b8b4a8", "#858176", "#5e5b52"),
    accent="#2e8b57",
    accent_hover="#3ca168",
    accent_active="#246e45",
    is_dark=True,
    selection_alpha=0.26,
    shadow_alpha=0.48,
    success="#3ca168",
    warning="#d96b43",
    error="#e05a4f",
    info="#6ca0c9",
    syn_keyword="#68c490",
    syn_string="#e08b67",
    syn_comment="#757268",
    syn_number="#e69a5c",
    syn_function="#7db8da",
    syn_class="#e2c278",
    syn_operator="#9ec4b0",
    syn_bracket="#c9a892",
)

# Paper: neutral, clean, near-white. The default light option.
PAPER = make_palette(
    "paper",
    ramp=("#ffffff", "#f7f8fa", "#ffffff", "#eef1f5", "#e2e7ee", "#f1f3f6"),
    borders=("#e6e9ee", "#d5dae2", "#b9c1cc"),
    text=("#1c2128", "#414a56", "#69737f", "#98a1ac"),
    accent="#0969da", accent_hover="#2a7de1", accent_active="#0757b8",
    is_dark=False, selection_alpha=0.18, shadow_alpha=0.14,
)

# Dune: warm paper — cream surfaces, sand borders, easier on tired eyes than
# a pure-white light theme.
DUNE = make_palette(
    "dune",
    ramp=("#fdfaf4", "#f6f1e7", "#fffdf8", "#ede5d6", "#e0d5c1", "#f2ebdd"),
    borders=("#e8e0d0", "#d9cfba", "#c0b39b"),
    text=("#2a2318", "#4d4433", "#7a6f5b", "#a3987f"),
    accent="#b0651f", accent_hover="#c67a33", accent_active="#8f5015",
    is_dark=False, selection_alpha=0.16, shadow_alpha=0.12,
    success="#4f7a2f", warning="#a97612", error="#b3402c", info="#2b6a94",
)

# Mist: cool light grey-blue, low glare.
MIST = make_palette(
    "mist",
    ramp=("#f4f7fa", "#eaeff5", "#ffffff", "#dfe6ef", "#cfd9e5", "#e5ebf2"),
    borders=("#dde4ec", "#c8d2de", "#a9b6c6"),
    text=("#182430", "#3a4757", "#61707f", "#8e9caa"),
    accent="#2b7a9e", accent_hover="#3d90b5", accent_active="#1f6183",
    is_dark=False, selection_alpha=0.18, shadow_alpha=0.12,
)


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────
PALETTES.update({
    p.name: p for p in (
        MATTE, CLAY, MOCHA, MIDNIGHT, NORD, FOREST, ROSE, CONTRAST,
        PAPER_INK, PARCHMENT, SAGE_PAPER, INK_DARK, PAPER, DUNE, MIST,
    )
})

# Legacy aliases so older saved settings and main.py's apply_onyx()/apply_dark()
# never crash. NOTE: "clay" is now a real palette, not an alias for graphite.
_ALIASES = {"onyx": "graphite", "dark": "graphite", "light": "paper_ink",
            "system": "graphite"}
for _alias, _target in _ALIASES.items():
    PALETTES.setdefault(_alias, PALETTES[_target])


@dataclass(frozen=True)
class ThemeInfo:
    """Presentation metadata for the settings theme gallery."""
    name: str
    label: str
    group: str        # "Dark" | "Light"
    blurb: str


THEME_META: Dict[str, ThemeInfo] = {t.name: t for t in (
    ThemeInfo("graphite", "Graphite", "Dark", "Neutral near-black with a clean blue accent."),
    ThemeInfo("matte", "Matte", "Dark", "Soft desaturated charcoal — no pure black, no glare."),
    ThemeInfo("clay", "Clay", "Dark", "Warm earthy browns with terracotta, à la Zen Browser."),
    ThemeInfo("mocha", "Mocha", "Dark", "Coffee-dark surfaces with a creamy amber accent."),
    ThemeInfo("slate", "Slate", "Dark", "Cool blue-grey, slightly warmer than Graphite."),
    ThemeInfo("midnight", "Midnight", "Dark", "Deep navy canvas with a crisp cyan accent."),
    ThemeInfo("nord", "Nord", "Dark", "Muted arctic blue-grey, even-toned and calm."),
    ThemeInfo("forest", "Forest", "Dark", "Deep green-black with a fresh moss accent."),
    ThemeInfo("rose", "Rosé", "Dark", "Mauve-plum surfaces with a dusty pink accent."),
    ThemeInfo("contrast", "High Contrast", "Dark", "Pure black and white for maximum legibility."),
    ThemeInfo("paper_ink", "Paper Ink", "Light", "Warm editorial manuscript paper with forest green & terracotta ink."),
    ThemeInfo("parchment", "Warm Parchment", "Light", "Classical vellum cream with oxblood & sepia ink accents."),
    ThemeInfo("sage_paper", "Botanical Sage", "Light", "Soft sage archival paper with deep pine & amber ink."),
    ThemeInfo("ink_dark", "Carbon Ink", "Dark", "Warm pressroom carbon dark theme with emerald & terracotta ink."),
    ThemeInfo("paper", "Paper", "Light", "Clean neutral near-white. The default light theme."),
    ThemeInfo("dune", "Dune", "Light", "Warm cream and sand — softer than pure white."),
    ThemeInfo("mist", "Mist", "Light", "Cool grey-blue light theme with low glare."),
)}


def list_themes(group: str = "") -> list:
    """Theme metadata in display order, optionally filtered by group."""
    return [t for t in THEME_META.values() if not group or t.group == group]

# ─────────────────────────────────────────────────────────────────────────────
# Geometry & type tokens  (all spacing on a 4px grid)
# ─────────────────────────────────────────────────────────────────────────────
class Spacing:
    xxs = 2
    xs = 4
    sm = 6
    md = 8
    lg = 12
    xl = 16
    xxl = 20
    xxxl = 24
    huge = 32


class Radius:
    none = 0
    sm = 4
    md = 6
    lg = 10
    xl = 14
    pill = 999


class FontFamily:
    ui = '"Inter", "Segoe UI", "SF Pro Text", system-ui, sans-serif'
    mono = '"JetBrains Mono", "Cascadia Code", "SF Mono", Consolas, monospace'


class FontSize:
    micro = 10
    tiny = 11
    small = 12
    base = 13
    md = 14
    lg = 16
    xl = 20
    xxl = 26


class FontWeight:
    normal = 400
    medium = 500
    semibold = 600
    bold = 700


class LineHeight:
    tight = 1.25
    normal = 1.5
    relaxed = 1.7


class Duration:
    fast = 120
    base = 180
    slow = 260


class Easing:
    standard = "cubic-bezier(0.4, 0.0, 0.2, 1)"
    decelerate = "cubic-bezier(0.0, 0.0, 0.2, 1)"


# Per-component geometry (single source of truth for the shell)
class Titlebar:
    HEIGHT = 40


class Toolbar:
    HEIGHT = 44


class ActivityBar:
    WIDTH = 70          # wide enough for a caption under each icon
    ICON = 22
    BUTTON = 42         # bottom icon-only actions (AI, settings)
    RAIL_BUTTON = 52    # primary icon-over-label buttons


class Sidebar:
    MIN_WIDTH = 240
    DEFAULT_WIDTH = 300
    MAX_WIDTH = 520
    HEADER_HEIGHT = 36


class AIPanel:
    MIN_WIDTH = 340
    DEFAULT_WIDTH = 424
    MAX_WIDTH = 680


class StatusBar:
    HEIGHT = 26


class Terminal:
    MIN_HEIGHT = 120
    DEFAULT_HEIGHT = 224
    TAB_HEIGHT = 34


class Editor:
    TAB_HEIGHT = 36
    GUTTER_MIN = 48


# ─────────────────────────────────────────────────────────────────────────────
# Stylesheet generator
# ─────────────────────────────────────────────────────────────────────────────
class DesignSystem:
    """Holds the active palette and generates QSS for the app."""

    def __init__(self, theme: str = "graphite"):
        self.colors = PALETTES.get(theme, GRAPHITE)
        # Store the palette's own name, not the key used to look it up, so an
        # alias like "system"/"dark" reports as the real theme ("graphite") and
        # the settings gallery can highlight the matching card.
        self._theme = self.colors.name

    # -- palette control -----------------------------------------------------
    def set_theme(self, theme: str) -> None:
        self.colors = PALETTES.get(theme, GRAPHITE)
        self._theme = self.colors.name

    @property
    def theme(self) -> str:
        return self._theme

    @property
    def is_dark(self) -> bool:
        return self.colors.is_dark

    def color(self, token: str) -> str:
        return getattr(self.colors, token, "#ffffff")

    # -- stylesheet ----------------------------------------------------------
    def get_stylesheet(self, component: str = "global") -> str:
        if component == "global":
            return self._global_qss()
        # component-scoped stylesheets fall back to global tokens
        return self._global_qss()

    def _global_qss(self) -> str:
        c = self.colors
        return _GLOBAL_QSS_TEMPLATE.format(
            c=c,
            ui=FontFamily.ui,
            mono=FontFamily.mono,
            fs_base=FontSize.base,
            fs_small=FontSize.small,
            fs_tiny=FontSize.tiny,
            r_sm=Radius.sm,
            r_md=Radius.md,
            r_lg=Radius.lg,
            sp_xs=Spacing.xs,
            sp_sm=Spacing.sm,
            sp_md=Spacing.md,
            sp_lg=Spacing.lg,
        )


# The template references palette fields via {c.field}. Kept module-level so the
# f-string braces for QSS blocks are escaped once ({{ }}) and stay readable.
_GLOBAL_QSS_TEMPLATE = """
* {{
    font-family: {ui};
    font-size: {fs_base}px;
    color: {c.text_primary};
    outline: none;
}}
QWidget {{
    background-color: {c.surface};
    color: {c.text_primary};
}}
QMainWindow, QDialog {{
    background-color: {c.canvas};
}}
QToolTip {{
    background-color: {c.surface_overlay};
    color: {c.text_primary};
    border: 1px solid {c.border};
    border-radius: {r_sm}px;
    padding: 4px 8px;
    font-size: {fs_small}px;
}}

/* ── Labels ─────────────────────────────────────────── */
QLabel {{ background: transparent; }}
QLabel[role="heading"] {{ font-size: 16px; font-weight: 600; color: {c.text_primary}; }}
QLabel[role="subheading"] {{ font-size: {fs_small}px; font-weight: 600; color: {c.text_muted}; }}
QLabel[role="muted"] {{ color: {c.text_muted}; }}
QLabel[role="faint"] {{ color: {c.text_faint}; font-size: {fs_tiny}px; }}

/* ── Buttons ────────────────────────────────────────── */
QPushButton {{
    background-color: {c.surface_raised};
    color: {c.text_secondary};
    border: 1px solid {c.border};
    border-radius: {r_md}px;
    padding: 6px 14px;
    font-weight: 500;
}}
QPushButton:hover {{ background-color: {c.surface_overlay}; color: {c.text_primary}; border-color: {c.border_strong}; }}
QPushButton:pressed {{ background-color: {c.surface_high}; }}
QPushButton:disabled {{ color: {c.text_faint}; background-color: {c.surface}; border-color: {c.border_subtle}; }}
QPushButton[variant="primary"] {{
    background-color: {c.accent}; color: {c.text_on_accent};
    border: 1px solid {c.accent}; font-weight: 600;
}}
QPushButton[variant="primary"]:hover {{ background-color: {c.accent_hover}; border-color: {c.accent_hover}; }}
QPushButton[variant="primary"]:pressed {{ background-color: {c.accent_active}; }}
QPushButton[variant="ghost"] {{ background: transparent; border: 1px solid transparent; color: {c.text_muted}; }}
QPushButton[variant="ghost"]:hover {{ background-color: {c.surface_overlay}; color: {c.text_primary}; }}
QPushButton[variant="danger"] {{ background-color: {c.error}; color: #ffffff; border-color: {c.error}; }}

/* ── Inputs ─────────────────────────────────────────── */
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {c.surface_inset};
    color: {c.text_primary};
    border: 1px solid {c.border};
    border-radius: {r_md}px;
    padding: 6px 10px;
    selection-background-color: {c.selection};
    selection-color: {c.text_primary};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus {{
    border: 1px solid {c.border_focus};
}}
QLineEdit::placeholder {{ color: {c.text_faint}; }}

QComboBox {{
    background-color: {c.surface_raised};
    border: 1px solid {c.border};
    border-radius: {r_md}px;
    padding: 5px 10px;
    color: {c.text_primary};
    min-height: 20px;
}}
QComboBox:hover {{ border-color: {c.border_strong}; }}
QComboBox:focus {{ border-color: {c.border_focus}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background-color: {c.surface_overlay};
    border: 1px solid {c.border};
    border-radius: {r_md}px;
    selection-background-color: {c.accent_muted};
    selection-color: {c.text_primary};
    padding: 4px;
    outline: none;
}}

QCheckBox, QRadioButton {{ spacing: 8px; color: {c.text_secondary}; background: transparent; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {c.border_strong};
    border-radius: {r_sm}px;
    background: {c.surface_inset};
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background: {c.accent}; border-color: {c.accent};
}}
QRadioButton::indicator {{ border-radius: 8px; }}

/* ── Scrollbars ─────────────────────────────────────── */
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{
    background: {c.scrollbar}; border-radius: 6px; min-height: 32px; margin: 2px;
}}
QScrollBar::handle:vertical:hover {{ background: {c.scrollbar_hover}; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 0; }}
QScrollBar::handle:horizontal {{
    background: {c.scrollbar}; border-radius: 6px; min-width: 32px; margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{ background: {c.scrollbar_hover}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ── Tabs ───────────────────────────────────────────── */
QTabWidget::pane {{ border: none; background: {c.surface}; }}
QTabBar {{ background: transparent; qproperty-drawBase: 0; }}
QTabBar::tab {{
    background: transparent;
    color: {c.text_muted};
    padding: 7px 16px;
    border: none;
    border-right: 1px solid {c.border_subtle};
    border-top: 2px solid transparent;
}}
QTabBar::tab:selected {{
    background: {c.surface};
    color: {c.text_primary};
    border-top: 2px solid {c.accent};
}}
QTabBar::tab:hover:!selected {{ color: {c.text_secondary}; background: {c.surface_raised}; }}

/* ── Trees / Lists ──────────────────────────────────── */
QTreeView, QListView, QListWidget, QTreeWidget {{
    background: {c.surface};
    border: none;
    outline: none;
    show-decoration-selected: 1;
}}
QTreeView::item, QListView::item, QListWidget::item {{
    padding: 3px 6px; border-radius: {r_sm}px; color: {c.text_secondary};
}}
QTreeView::item:hover, QListView::item:hover, QListWidget::item:hover {{
    background: {c.surface_overlay};
}}
QTreeView::item:selected, QListView::item:selected, QListWidget::item:selected {{
    background: {c.accent_muted}; color: {c.text_primary};
}}
QTreeView::branch {{ background: transparent; }}
QHeaderView::section {{
    background: {c.surface};
    color: {c.text_muted};
    border: none;
    border-bottom: 1px solid {c.border_subtle};
    padding: 5px 8px;
    font-size: {fs_tiny}px;
    font-weight: 600;
}}

/* ── Menus ──────────────────────────────────────────── */
QMenu {{
    background: {c.surface_overlay};
    border: 1px solid {c.border};
    border-radius: {r_lg}px;
    padding: 6px;
}}
QMenu::item {{ padding: 6px 24px 6px 12px; border-radius: {r_sm}px; color: {c.text_secondary}; }}
QMenu::item:selected {{ background: {c.accent_muted}; color: {c.text_primary}; }}
QMenu::separator {{ height: 1px; background: {c.border_subtle}; margin: 5px 8px; }}
QMenuBar {{ background: {c.surface}; }}
QMenuBar::item {{ padding: 5px 10px; background: transparent; }}
QMenuBar::item:selected {{ background: {c.surface_overlay}; border-radius: {r_sm}px; }}

/* ── Splitter ───────────────────────────────────────── */
QSplitter::handle {{ background: {c.border}; }}
QSplitter::handle:hover {{ background: {c.accent}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}

/* ── Progress ───────────────────────────────────────── */
QProgressBar {{
    background: {c.surface_inset}; border: none; border-radius: {r_sm}px;
    height: 6px; text-align: center; color: {c.text_muted};
}}
QProgressBar::chunk {{ background: {c.accent}; border-radius: {r_sm}px; }}

/* ── Frames / cards via property ────────────────────── */
QFrame[card="true"] {{
    background: {c.surface_raised};
    border: 1px solid {c.border_subtle};
    border-radius: {r_lg}px;
}}
QFrame[divider="true"] {{ background: {c.border}; border: none; }}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Singleton accessors
# ─────────────────────────────────────────────────────────────────────────────
_design_system: "DesignSystem | None" = None


def get_design_system() -> DesignSystem:
    global _design_system
    if _design_system is None:
        _design_system = DesignSystem("graphite")
    return _design_system


def set_design_system_theme(theme: str) -> DesignSystem:
    ds = get_design_system()
    ds.set_theme(theme)
    return ds


def reset_design_system() -> None:
    global _design_system
    _design_system = None



# ============================================================================
# SECTION: ui.theme (ui/theme.py)
# ============================================================================
"""
Theme Manager — v2.0

Thin controller over the DesignSystem. Applies the generated global stylesheet
to the QApplication and lets the app switch palettes at runtime.

Kept API-compatible with the previous ThemeManager so main.py and the shell
never break: apply_theme(name), apply_clay(), toggle(), get_current_theme(),
colors (dict), is_dark, and per-theme apply_<name>() helpers.
"""

from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import QObject, Signal

from ui.design_system import get_design_system, PALETTES, THEME_META


class ThemeManager(QObject):
    """Applies design-system palettes to the running QApplication."""

    theme_changed = Signal(str)

    # Every real palette, in gallery order. Aliases (onyx/dark/light/system)
    # are deliberately excluded so the settings gallery shows no duplicates.
    THEMES = list(THEME_META.keys())

    # Curated subset for the titlebar swatch row — 13 swatches would not fit,
    # so the full set lives in Settings → Appearance.
    QUICK_THEMES = ["paper_ink", "ink_dark", "graphite", "clay", "midnight", "paper", "dune"]

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._ds = get_design_system()
        self._current = self._ds.theme or "graphite"

    # -- application ---------------------------------------------------------
    def apply_theme(self, name: str) -> None:
        if name not in PALETTES:
            name = "graphite"
        self._ds.set_theme(name)
        # Canonical name (aliases collapse to the real palette name)
        self._current = self._ds.theme
        self._apply_qpalette()
        if self._app is not None:
            try:
                f = self._app.font()
                if f.pointSize() <= 0:
                    f.setPointSize(10)
                    self._app.setFont(f)
            except Exception:
                pass
            self._app.setStyleSheet(self._ds.get_stylesheet("global"))
        self.theme_changed.emit(self._current)

    def _apply_qpalette(self) -> None:
        """Set a base QPalette so native-drawn bits match the QSS."""
        if self._app is None:
            return
        c = self._ds.colors
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(c.surface))
        pal.setColor(QPalette.WindowText, QColor(c.text_primary))
        pal.setColor(QPalette.Base, QColor(c.surface_inset))
        pal.setColor(QPalette.AlternateBase, QColor(c.surface_raised))
        pal.setColor(QPalette.Text, QColor(c.text_primary))
        pal.setColor(QPalette.Button, QColor(c.surface_raised))
        pal.setColor(QPalette.ButtonText, QColor(c.text_primary))
        pal.setColor(QPalette.Highlight, QColor(c.accent))
        pal.setColor(QPalette.HighlightedText, QColor(c.text_on_accent))
        pal.setColor(QPalette.ToolTipBase, QColor(c.surface_overlay))
        pal.setColor(QPalette.ToolTipText, QColor(c.text_primary))
        pal.setColor(QPalette.PlaceholderText, QColor(c.text_faint))
        self._app.setPalette(pal)

    # -- helpers -------------------------------------------------------------
    def toggle(self) -> None:
        """Cycle the quick-pick themes (the full list lives in Settings)."""
        order = self.QUICK_THEMES
        try:
            idx = order.index(self._current)
        except ValueError:
            idx = -1
        self.apply_theme(order[(idx + 1) % len(order)])

    def available_themes(self) -> list:
        """Metadata for every selectable theme, in gallery order."""
        return list(THEME_META.values())

    def get_current_theme(self) -> str:
        return self._current

    @property
    def is_dark(self) -> bool:
        return self._ds.is_dark

    @property
    def colors(self) -> dict:
        return self._ds.colors.as_dict()

    # Legacy per-theme entry points (main.py calls apply_clay()).
    def apply_clay(self):
        self.apply_theme("clay")

    def apply_graphite(self):
        self.apply_theme("graphite")

    def apply_slate(self):
        self.apply_theme("slate")

    def apply_onyx(self):
        self.apply_theme("graphite")

    def apply_dark(self):
        self.apply_theme("graphite")

    def __getattr__(self, item):
        """Synthesize apply_<theme>() for every registered palette.

        Saves 13 near-identical methods and keeps working if palettes are added.
        Only consulted for attributes that don't exist, so the explicit legacy
        methods above still win.
        """
        if item.startswith("apply_"):
            name = item[len("apply_"):]
            if name in PALETTES:
                return lambda: self.apply_theme(name)
        raise AttributeError(item)

