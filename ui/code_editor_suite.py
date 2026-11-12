"""
Consolidated Module: ui.code_editor_suite

Combines: ui.panels.editor.language_support, ui.panels.editor.bracket_matcher, ui.panels.editor.syntax_highlighter, ui.panels.editor.tree_sitter_highlighter, ui.panels.editor.completion_popup, ui.panels.editor.symbol_outline, ui.panels.editor.breadcrumb, ui.panels.editor.code_editor, ui.panels.editor.editor_tabs, ui.panels.dashboard, ui.panels.center
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['ui.panels.editor.language_support', 'ui.panels.editor.bracket_matcher', 'ui.panels.editor.syntax_highlighter', 'ui.panels.editor.tree_sitter_highlighter', 'ui.panels.editor.completion_popup', 'ui.panels.editor.symbol_outline', 'ui.panels.editor.breadcrumb', 'ui.panels.editor.code_editor', 'ui.panels.editor.editor_tabs', 'ui.panels.dashboard', 'ui.panels.center']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ui.panels.editor.language_support (ui/panels/editor/language_support.py)
# ============================================================================
"""
Language Support — v1.6

Comprehensive language detection and metadata.
Supports 30+ programming languages with automatic detection from file extension.
"""
from pathlib import Path
from typing import Optional, Dict, List


class LanguageInfo:
    """Metadata about a programming language."""
    def __init__(
        self,
        name: str,
        extensions: List[str],
        line_comment: str = "",
        block_comment_start: str = "",
        block_comment_end: str = "",
        keywords: List[str] = None,
        file_icon: str = "",
        color: str = "#8E8E98"
    ):
        self.name = name
        self.extensions = extensions
        self.line_comment = line_comment
        self.block_comment_start = block_comment_start
        self.block_comment_end = block_comment_end
        self.keywords = keywords or []
        self.file_icon = file_icon
        self.color = color


# Language Database
LANGUAGES: Dict[str, LanguageInfo] = {
    "python": LanguageInfo(
        name="Python",
        extensions=[".py", ".pyw", ".pyi"],
        line_comment="#",
        keywords=[
            "and", "as", "assert", "async", "await", "break", "class", "continue",
            "def", "del", "elif", "else", "except", "False", "finally", "for",
            "from", "global", "if", "import", "in", "is", "lambda", "None",
            "nonlocal", "not", "or", "pass", "raise", "return", "True",
            "try", "while", "with", "yield", "self"
        ],
        file_icon="🐍",
        color="#3776AB"
    ),
    
    "javascript": LanguageInfo(
        name="JavaScript",
        extensions=[".js", ".mjs", ".cjs"],
        line_comment="//",
        block_comment_start="/*",
        block_comment_end="*/",
        keywords=[
            "abstract", "await", "boolean", "break", "byte", "case", "catch",
            "char", "class", "const", "continue", "debugger", "default",
            "delete", "do", "double", "else", "enum", "export", "extends",
            "false", "final", "finally", "float", "for", "function", "goto",
            "if", "implements", "import", "in", "instanceof", "int", "interface",
            "let", "long", "native", "new", "null", "package", "private",
            "protected", "public", "return", "short", "static", "super",
            "switch", "synchronized", "this", "throw", "throws", "transient",
            "true", "try", "typeof", "var", "void", "volatile", "while", "with", "yield"
        ],
        file_icon="📜",
        color="#F7DF1E"
    ),
    
    "typescript": LanguageInfo(
        name="TypeScript",
        extensions=[".ts", ".tsx"],
        line_comment="//",
        block_comment_start="/*",
        block_comment_end="*/",
        keywords=[
            "abstract", "any", "as", "async", "await", "boolean", "break", "case",
            "catch", "class", "const", "constructor", "continue", "debugger",
            "declare", "default", "delete", "do", "else", "enum", "export",
            "extends", "false", "finally", "for", "from", "function", "get",
            "if", "implements", "import", "in", "instanceof", "interface",
            "is", "keyof", "let", "module", "namespace", "never", "new",
            "null", "number", "of", "package", "private", "protected", "public",
            "readonly", "require", "return", "set", "static", "string", "super",
            "switch", "symbol", "this", "throw", "true", "try", "type", "typeof",
            "undefined", "unique", "unknown", "var", "void", "while", "with", "yield"
        ],
        file_icon="TS",
        color="#3178C6"
    ),
    
    "c": LanguageInfo(
        name="C",
        extensions=[".c", ".h"],
        line_comment="//",
        block_comment_start="/*",
        block_comment_end="*/",
        keywords=[
            "auto", "break", "case", "char", "const", "continue", "default",
            "do", "double", "else", "enum", "extern", "float", "for", "goto",
            "if", "inline", "int", "long", "register", "restrict", "return",
            "short", "signed", "sizeof", "static", "struct", "switch", "typedef",
            "union", "unsigned", "void", "volatile", "while", "_Bool", "_Complex",
            "_Imaginary"
        ],
        file_icon="C",
        color="#A8B9CC"
    ),
    
    "cpp": LanguageInfo(
        name="C++",
        extensions=[".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"],
        line_comment="//",
        block_comment_start="/*",
        block_comment_end="*/",
        keywords=[
            "alignas", "alignof", "and", "and_eq", "asm", "auto", "bitand", "bitor",
            "bool", "break", "case", "catch", "char", "char16_t", "char32_t", "class",
            "compl", "concept", "const", "constexpr", "const_cast", "continue",
            "decltype", "default", "delete", "do", "double", "dynamic_cast", "else",
            "enum", "explicit", "export", "extern", "false", "float", "for", "friend",
            "goto", "if", "inline", "int", "long", "mutable", "namespace", "new",
            "noexcept", "not", "not_eq", "nullptr", "operator", "or", "or_eq",
            "private", "protected", "public", "register", "reinterpret_cast",
            "requires", "return", "short", "signed", "sizeof", "static", "static_assert",
            "static_cast", "struct", "switch", "template", "this", "thread_local",
            "throw", "true", "try", "typedef", "typeid", "typename", "union",
            "unsigned", "using", "virtual", "void", "volatile", "wchar_t", "while",
            "xor", "xor_eq"
        ],
        file_icon="C++",
        color="#00599C"
    ),
    
    "csharp": LanguageInfo(
        name="C#",
        extensions=[".cs"],
        line_comment="//",
        block_comment_start="/*",
        block_comment_end="*/",
        keywords=[
            "abstract", "as", "base", "bool", "break", "byte", "case", "catch",
            "char", "checked", "class", "const", "continue", "decimal", "default",
            "delegate", "do", "double", "else", "enum", "event", "explicit",
            "extern", "false", "finally", "fixed", "float", "for", "foreach",
            "goto", "if", "implicit", "in", "int", "interface", "internal", "is",
            "lock", "long", "namespace", "new", "null", "object", "operator", "out",
            "override", "params", "private", "protected", "public", "readonly",
            "ref", "return", "sbyte", "sealed", "short", "sizeof", "stackalloc",
            "static", "string", "struct", "switch", "this", "throw", "true", "try",
            "typeof", "uint", "ulong", "unchecked", "unsafe", "ushort", "using",
            "var", "virtual", "void", "volatile", "while"
        ],
        file_icon="C#",
        color="#239120"
    ),
    
    "java": LanguageInfo(
        name="Java",
        extensions=[".java"],
        line_comment="//",
        block_comment_start="/*",
        block_comment_end="*/",
        keywords=[
            "abstract", "assert", "boolean", "break", "byte", "case", "catch",
            "char", "class", "const", "continue", "default", "do", "double",
            "else", "enum", "extends", "final", "finally", "float", "for",
            "goto", "if", "implements", "import", "instanceof", "int", "interface",
            "long", "native", "new", "package", "private", "protected", "public",
            "return", "short", "static", "strictfp", "super", "switch", "synchronized",
            "this", "throw", "throws", "transient", "try", "void", "volatile", "while"
        ],
        file_icon="☕",
        color="#007396"
    ),
    
    "kotlin": LanguageInfo(
        name="Kotlin",
        extensions=[".kt", ".kts"],
        line_comment="//",
        block_comment_start="/*",
        block_comment_end="*/",
        keywords=[
            "abstract", "actual", "annotation", "as", "break", "by", "catch", "class",
            "companion", "const", "constructor", "continue", "crossinline", "data",
            "delegate", "do", "dynamic", "else", "enum", "expect", "external", "false",
            "field", "file", "final", "finally", "for", "fun", "get", "if", "import",
            "in", "infix", "init", "inline", "inner", "interface", "internal", "is",
            "it", "lateinit", "noinline", "null", "object", "open", "operator", "out",
            "override", "package", "param", "private", "property", "protected", "public",
            "receiver", "reified", "return", "sealed", "set", "setparam", "super",
            "suspend", "tailrec", "this", "throw", "true", "try", "typealias", "typeof",
            "val", "var", "vararg", "when", "where", "while"
        ],
        file_icon="KT",
        color="#7F52FF"
    ),
    
    "rust": LanguageInfo(
        name="Rust",
        extensions=[".rs"],
        line_comment="//",
        block_comment_start="/*",
        block_comment_end="*/",
        keywords=[
            "as", "async", "await", "break", "const", "continue", "crate", "dyn",
            "else", "enum", "extern", "false", "fn", "for", "if", "impl", "in",
            "let", "loop", "match", "mod", "move", "mut", "pub", "ref", "return",
            "self", "Self", "static", "struct", "super", "trait", "true", "type",
            "unsafe", "use", "where", "while", "abstract", "become", "box", "do",
            "final", "macro", "override", "priv", "try", "typeof", "unsized",
            "virtual", "yield"
        ],
        file_icon="🦀",
        color="#CE422B"
    ),
    
    "go": LanguageInfo(
        name="Go",
        extensions=[".go"],
        line_comment="//",
        block_comment_start="/*",
        block_comment_end="*/",
        keywords=[
            "break", "case", "chan", "const", "continue", "default", "defer",
            "else", "fallthrough", "for", "func", "go", "goto", "if", "import",
            "interface", "map", "package", "range", "return", "select", "struct",
            "switch", "type", "var"
        ],
        file_icon="Go",
        color="#00ADD8"
    ),
    
    "dart": LanguageInfo(
        name="Dart",
        extensions=[".dart"],
        line_comment="//",
        block_comment_start="/*",
        block_comment_end="*/",
        keywords=[
            "abstract", "as", "assert", "async", "await", "break", "case", "catch",
            "class", "const", "continue", "covariant", "default", "deferred", "do",
            "dynamic", "else", "enum", "export", "extends", "extension", "external",
            "factory", "false", "final", "finally", "for", "Function", "get", "hide",
            "if", "implements", "import", "in", "interface", "is", "late", "library",
            "mixin", "new", "null", "on", "operator", "part", "required", "rethrow",
            "return", "set", "show", "static", "super", "switch", "sync", "this",
            "throw", "true", "try", "typedef", "var", "void", "while", "with", "yield"
        ],
        file_icon="🎯",
        color="#0175C2"
    ),
    
    "php": LanguageInfo(
        name="PHP",
        extensions=[".php", ".phtml"],
        line_comment="//",
        block_comment_start="/*",
        block_comment_end="*/",
        keywords=[
            "abstract", "and", "array", "as", "break", "callable", "case", "catch",
            "class", "clone", "const", "continue", "declare", "default", "die", "do",
            "echo", "else", "elseif", "empty", "enddeclare", "endfor", "endforeach",
            "endif", "endswitch", "endwhile", "eval", "exit", "extends", "final",
            "finally", "for", "foreach", "function", "global", "goto", "if",
            "implements", "include", "include_once", "instanceof", "insteadof",
            "interface", "isset", "list", "namespace", "new", "or", "print", "private",
            "protected", "public", "require", "require_once", "return", "static",
            "switch", "throw", "trait", "try", "unset", "use", "var", "while", "xor",
            "yield"
        ],
        file_icon="🐘",
        color="#777BB4"
    ),
    
    "swift": LanguageInfo(
        name="Swift",
        extensions=[".swift"],
        line_comment="//",
        block_comment_start="/*",
        block_comment_end="*/",
        keywords=[
            "associatedtype", "class", "deinit", "enum", "extension", "fileprivate",
            "func", "import", "init", "inout", "internal", "let", "open", "operator",
            "private", "protocol", "public", "rethrows", "static", "struct",
            "subscript", "typealias", "var", "break", "case", "continue", "default",
            "defer", "do", "else", "fallthrough", "for", "guard", "if", "in", "repeat",
            "return", "switch", "where", "while", "as", "Any", "catch", "false", "is",
            "nil", "super", "self", "Self", "throw", "throws", "true", "try"
        ],
        file_icon="🍎",
        color="#FA7343"
    ),
    
    "sql": LanguageInfo(
        name="SQL",
        extensions=[".sql"],
        line_comment="--",
        block_comment_start="/*",
        block_comment_end="*/",
        keywords=[
            "ADD", "ALL", "ALTER", "AND", "AS", "ASC", "BACKUP", "BETWEEN", "BY",
            "CASE", "CHECK", "COLUMN", "CONSTRAINT", "CREATE", "DATABASE", "DEFAULT",
            "DELETE", "DESC", "DISTINCT", "DROP", "EXEC", "EXISTS", "FOREIGN", "FROM",
            "FULL", "GROUP", "HAVING", "IN", "INDEX", "INNER", "INSERT", "INTO", "IS",
            "JOIN", "KEY", "LEFT", "LIKE", "LIMIT", "NOT", "NULL", "OR", "ORDER",
            "OUTER", "PRIMARY", "PROCEDURE", "RIGHT", "ROWNUM", "SELECT", "SET",
            "TABLE", "TOP", "TRUNCATE", "UNION", "UNIQUE", "UPDATE", "VALUES", "VIEW",
            "WHERE"
        ],
        file_icon="🗄️",
        color="#CC2927"
    ),
    
    "ruby": LanguageInfo(
        name="Ruby",
        extensions=[".rb", ".rake", ".gemspec"],
        line_comment="#",
        keywords=[
            "alias", "and", "begin", "break", "case", "class", "def", "defined?",
            "do", "else", "elsif", "end", "ensure", "false", "for", "if", "in",
            "module", "next", "nil", "not", "or", "redo", "rescue", "retry",
            "return", "self", "super", "then", "true", "undef", "unless", "until",
            "when", "while", "yield"
        ],
        file_icon="💎",
        color="#CC342D"
    ),
    
    "html": LanguageInfo(
        name="HTML",
        extensions=[".html", ".htm"],
        block_comment_start="<!--",
        block_comment_end="-->",
        file_icon="🌐",
        color="#E34F26"
    ),
    
    "css": LanguageInfo(
        name="CSS",
        extensions=[".css"],
        block_comment_start="/*",
        block_comment_end="*/",
        file_icon="🎨",
        color="#1572B6"
    ),
    
    "scss": LanguageInfo(
        name="SCSS",
        extensions=[".scss"],
        line_comment="//",
        block_comment_start="/*",
        block_comment_end="*/",
        file_icon="🎨",
        color="#CC6699"
    ),
    
    "json": LanguageInfo(
        name="JSON",
        extensions=[".json"],
        file_icon="📋",
        color="#FBBF24"
    ),
    
    "yaml": LanguageInfo(
        name="YAML",
        extensions=[".yaml", ".yml"],
        line_comment="#",
        file_icon="📄",
        color="#CB171E"
    ),
    
    "xml": LanguageInfo(
        name="XML",
        extensions=[".xml", ".xsd", ".xsl"],
        block_comment_start="<!--",
        block_comment_end="-->",
        file_icon="📄",
        color="#FF6600"
    ),
    
    "markdown": LanguageInfo(
        name="Markdown",
        extensions=[".md", ".markdown"],
        file_icon="📝",
        color="#083FA1"
    ),
    
    "shell": LanguageInfo(
        name="Shell",
        extensions=[".sh", ".bash", ".zsh"],
        line_comment="#",
        keywords=[
            "if", "then", "else", "elif", "fi", "case", "esac", "for", "while",
            "until", "do", "done", "function", "select", "time", "in", "return"
        ],
        file_icon="🐚",
        color="#89E051"
    ),
    
    "powershell": LanguageInfo(
        name="PowerShell",
        extensions=[".ps1", ".psm1", ".psd1"],
        line_comment="#",
        block_comment_start="<#",
        block_comment_end="#>",
        file_icon="PS",
        color="#012456"
    ),
    
    "batch": LanguageInfo(
        name="Batch",
        extensions=[".bat", ".cmd"],
        line_comment="REM",
        file_icon="⚙️",
        color="#C1F12E"
    ),
    
    "dockerfile": LanguageInfo(
        name="Docker",
        extensions=["Dockerfile", ".dockerfile"],
        line_comment="#",
        keywords=[
            "FROM", "RUN", "CMD", "LABEL", "MAINTAINER", "EXPOSE", "ENV", "ADD",
            "COPY", "ENTRYPOINT", "VOLUME", "USER", "WORKDIR", "ARG", "ONBUILD",
            "STOPSIGNAL", "HEALTHCHECK", "SHELL"
        ],
        file_icon="🐳",
        color="#2496ED"
    ),
    
    "makefile": LanguageInfo(
        name="Makefile",
        extensions=["Makefile", ".make", ".mk"],
        line_comment="#",
        file_icon="🔨",
        color="#427819"
    ),
    
    "lua": LanguageInfo(
        name="Lua",
        extensions=[".lua"],
        line_comment="--",
        block_comment_start="--[[",
        block_comment_end="]]",
        keywords=[
            "and", "break", "do", "else", "elseif", "end", "false", "for", "function",
            "goto", "if", "in", "local", "nil", "not", "or", "repeat", "return",
            "then", "true", "until", "while"
        ],
        file_icon="🌙",
        color="#000080"
    ),
    
    "r": LanguageInfo(
        name="R",
        extensions=[".r", ".R"],
        line_comment="#",
        keywords=[
            "if", "else", "repeat", "while", "function", "for", "in", "next", "break",
            "TRUE", "FALSE", "NULL", "Inf", "NaN", "NA", "NA_integer_", "NA_real_",
            "NA_complex_", "NA_character_"
        ],
        file_icon="📊",
        color="#276DC3"
    ),
    
    "toml": LanguageInfo(
        name="TOML",
        extensions=[".toml"],
        line_comment="#",
        file_icon="⚙️",
        color="#9C4221"
    ),
    
    "ini": LanguageInfo(
        name="INI",
        extensions=[".ini", ".cfg", ".conf"],
        line_comment=";",
        file_icon="⚙️",
        color="#6D9CBE"
    ),
    
    "plaintext": LanguageInfo(
        name="Plain Text",
        extensions=[".txt", ".text", ".log"],
        file_icon="📄",
        color="#8E8E98"
    ),
}


def detect_language(file_path: Path) -> LanguageInfo:
    """Detect language from file path."""
    ext = file_path.suffix.lower()
    name = file_path.name
    
    # Check exact filename matches (Dockerfile, Makefile)
    for lang_id, lang_info in LANGUAGES.items():
        if name in lang_info.extensions:
            return lang_info
    
    # Check extension matches
    for lang_id, lang_info in LANGUAGES.items():
        if ext in lang_info.extensions:
            return lang_info
    
    # Default to plaintext
    return LANGUAGES["plaintext"]


def get_language_by_name(name: str) -> Optional[LanguageInfo]:
    """Get language info by name."""
    return LANGUAGES.get(name.lower())


def get_all_languages() -> List[LanguageInfo]:
    """Get list of all supported languages."""
    return list(LANGUAGES.values())


def get_language_id_for_file(file_path: Path) -> str:
    """Detect language ID from file path."""
    ext = file_path.suffix.lower()
    name = file_path.name
    
    # Check exact filename matches (Dockerfile, Makefile)
    for lang_id, lang_info in LANGUAGES.items():
        if name in lang_info.extensions:
            return lang_id
    
    # Check extension matches
    for lang_id, lang_info in LANGUAGES.items():
        if ext in lang_info.extensions:
            return lang_id
    
    # Default to plaintext
    return "plaintext"


# ============================================================================
# SECTION: ui.panels.editor.bracket_matcher (ui/panels/editor/bracket_matcher.py)
# ============================================================================
"""
Bracket Matcher — v1.0

Highlight matching brackets: (), [], {}, <>
Supports all common bracket types with visual feedback.
"""

from PySide6.QtWidgets import QPlainTextEdit, QTextEdit
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QTextCursor, QTextCharFormat, QColor

from ui.design_system import get_design_system


class BracketMatcher(QObject):
    """Matches and highlights bracket pairs."""

    brackets_changed = Signal()

    def __init__(self, editor: QPlainTextEdit, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.bracket_pairs = {
            '(': ')',
            '[': ']',
            '{': '}',
            '<': '>'
        }

        # Brackets by direction
        self.open_brackets = set(self.bracket_pairs.keys())
        self.close_brackets = set(self.bracket_pairs.values())

        self.highlight_format = QTextCharFormat()
        self._build_format()

    def _build_format(self):
        """Palette-driven bracket highlight.

        This used to be a hardcoded QColor built from a CSS-style colour string,
        which QColor cannot parse — it produced an *invalid* colour that Qt
        painted as an opaque block that ignored the theme entirely.
        """
        c = get_design_system().colors
        tint = QColor(c.syn_bracket if c.syn_bracket else c.accent)
        tint.setAlpha(90)
        self.highlight_format = QTextCharFormat()
        self.highlight_format.setBackground(tint)
        self.highlight_format.setForeground(QColor(c.text_primary))

    def refresh_theme(self):
        """Rebuild the highlight colour and repaint the current match."""
        self._build_format()
        try:
            self.highlight_matching_brackets()
        except Exception:
            pass
        
    def set_bracket_pairs(self, pairs: dict):
        """Set custom bracket pairs."""
        self.bracket_pairs = pairs
        self.open_brackets = set(pairs.keys())
        self.close_brackets = set(pairs.values())
        
    def find_matching_bracket(self, cursor: QTextCursor):
        """Find position of matching bracket."""
        pos = cursor.position()
        char = cursor.document().characterAt(pos)
        
        if char in self.open_brackets:
            return self._find_matching_close(cursor, char)
        elif char in self.close_brackets:
            return self._find_matching_open(cursor, char)
            
        return -1
        
    def _find_matching_close(self, cursor, open_char):
        """Find matching closing bracket."""
        close_char = self.bracket_pairs[open_char]
        depth = 1
        pos = cursor.position()
        
        while pos < cursor.document().characterCount() - 1:
            pos += 1
            ch = cursor.document().characterAt(pos)
            
            if ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    return pos
                    
        return -1
        
    def _find_matching_open(self, cursor, close_char):
        """Find matching opening bracket."""
        open_char = None
        for k, v in self.bracket_pairs.items():
            if v == close_char:
                open_char = k
                break
                
        if not open_char:
            return -1
            
        depth = 1
        pos = cursor.position()
        
        while pos > 0:
            pos -= 1
            ch = cursor.document().characterAt(pos)
            
            if ch == close_char:
                depth += 1
            elif ch == open_char:
                depth -= 1
                if depth == 0:
                    return pos
                    
        return -1
        
    def highlight_matching_brackets(self):
        """Highlight matching brackets around cursor."""
        cursor = self.editor.textCursor()
        pos = cursor.position()
        
        # Get current character
        char = cursor.document().characterAt(pos)
        
        if char not in self.open_brackets and char not in self.close_brackets:
            # Try previous position
            if pos > 0:
                char = cursor.document().characterAt(pos - 1)
                if char not in self.open_brackets and char not in self.close_brackets:
                    if hasattr(self.editor, "set_bracket_highlights"):
                        self.editor.set_bracket_highlights([])
                    else:
                        self.editor.setExtraSelections([])
                    return
                    
        selections = []
        
        # Highlight current bracket
        if char in self.open_brackets or char in self.close_brackets:
            selection1 = QTextEdit.ExtraSelection()
            selection1.cursor = QTextCursor(cursor)
            selection1.cursor.setPosition(pos)
            selection1.cursor.setPosition(pos + 1, QTextCursor.KeepAnchor)
            selection1.format = self.highlight_format
            selections.append(selection1)
            
            # Find and highlight matching bracket
            match_pos = self.find_matching_bracket(cursor)
            if match_pos >= 0:
                selection2 = QTextEdit.ExtraSelection()
                selection2.cursor = QTextCursor(cursor)
                selection2.cursor.setPosition(match_pos)
                selection2.cursor.setPosition(match_pos + 1, QTextCursor.KeepAnchor)
                selection2.format = self.highlight_format
                selections.append(selection2)
                
        if hasattr(self.editor, "set_bracket_highlights"):
            self.editor.set_bracket_highlights(selections)
        else:
            self.editor.setExtraSelections(selections)
        
    def get_bracket_at_position(self, pos: int):
        """Get bracket character at position, if any."""
        cursor = self.editor.textCursor()
        cursor.setPosition(pos)
        char = cursor.document().characterAt(pos)
        
        if char in self.open_brackets or char in self.close_brackets:
            return char
        return None
        
    def is_bracket_at_cursor(self):
        """Check if cursor is at a bracket position."""
        cursor = self.editor.textCursor()
        pos = cursor.position()
        char = cursor.document().characterAt(pos)
        
        if char in self.open_brackets or char in self.close_brackets:
            return True
            
        # Check previous position
        if pos > 0:
            char = cursor.document().characterAt(pos - 1)
            return char in self.open_brackets or char in self.close_brackets
            
        return False


# ============================================================================
# SECTION: ui.panels.editor.syntax_highlighter (ui/panels/editor/syntax_highlighter.py)
# ============================================================================
"""
Enhanced Syntax Highlighter — v1.7

Comprehensive syntax highlighting for 30+ languages.
Uses language_support.py for language detection and keywords.
"""
import re
from pathlib import Path
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PySide6.QtCore import QRegularExpression
from ui.panels.editor.language_support import detect_language, get_language_by_name


class SyntaxHighlighter(QSyntaxHighlighter):
    """
    Advanced syntax highlighter with support for multiple languages.
    """
    def __init__(self, document, language_or_path):
        super().__init__(document)
        
        # Detect language
        if isinstance(language_or_path, str):
            if '.' in language_or_path or '/' in language_or_path or '\\' in language_or_path:
                # It's a file path
                self.lang_info = detect_language(Path(language_or_path))
            else:
                # It's a language name
                self.lang_info = get_language_by_name(language_or_path)
                if not self.lang_info:
                    from ui.panels.editor.language_support import LANGUAGES
                    self.lang_info = LANGUAGES["plaintext"]
        elif isinstance(language_or_path, Path):
            self.lang_info = detect_language(language_or_path)
        else:
            from ui.panels.editor.language_support import LANGUAGES
            self.lang_info = LANGUAGES["plaintext"]
            
        self.rules = []
        self.setup_formats()
        self.setup_rules()

    def refresh_theme(self):
        """Rebuild every text format from the active palette and repaint.

        The formats capture palette colours at construction time, so a theme
        switch has to come back through here or the code keeps the old colours.
        """
        self.setup_formats()
        self.setup_rules()
        self.rehighlight()

    def setup_formats(self):
        """Setup text formats for different syntax elements (theme-driven)."""
        from ui.design_system import get_design_system
        c = get_design_system().colors

        self.fmt_keyword = QTextCharFormat()
        self.fmt_keyword.setForeground(QColor(c.syn_keyword))
        self.fmt_keyword.setFontWeight(QFont.Bold)

        self.fmt_string = QTextCharFormat()
        self.fmt_string.setForeground(QColor(c.syn_string))

        self.fmt_comment = QTextCharFormat()
        self.fmt_comment.setForeground(QColor(c.syn_comment))
        self.fmt_comment.setFontItalic(True)

        self.fmt_number = QTextCharFormat()
        self.fmt_number.setForeground(QColor(c.syn_number))

        self.fmt_function = QTextCharFormat()
        self.fmt_function.setForeground(QColor(c.syn_function))

        self.fmt_class = QTextCharFormat()
        self.fmt_class.setForeground(QColor(c.syn_class))

        self.fmt_operator = QTextCharFormat()
        self.fmt_operator.setForeground(QColor(c.syn_operator))

        self.fmt_bracket = QTextCharFormat()
        self.fmt_bracket.setForeground(QColor(c.syn_bracket))

    def setup_rules(self):
        """Setup highlighting rules based on language."""
        # Rebuilt from scratch: refresh_theme() calls this again on every theme
        # change, and without the reset the list (and the stale formats in it)
        # grew on each switch.
        self.rules = []

        # Keywords
        for kw in self.lang_info.keywords:
            pattern = QRegularExpression(rf"\b{kw}\b")
            self.rules.append((pattern, self.fmt_keyword))

        # Numbers (integers, hex, floats)
        self.rules.append((QRegularExpression(r"\b\d+\.?\d*([eE][+-]?\d+)?\b"), self.fmt_number))
        self.rules.append((QRegularExpression(r"\b0[xX][0-9a-fA-F]+\b"), self.fmt_number))
        self.rules.append((QRegularExpression(r"\b0[bB][01]+\b"), self.fmt_number))
        self.rules.append((QRegularExpression(r"\b0[oO][0-7]+\b"), self.fmt_number))

        # Strings (double quotes)
        self.rules.append((QRegularExpression(r'"(?:[^"\\]|\\.)*"'), self.fmt_string))
        # Strings (single quotes)
        self.rules.append((QRegularExpression(r"'(?:[^'\\]|\\.)*'"), self.fmt_string))
        # Template literals (for JS/TS)
        if self.lang_info.name in ["JavaScript", "TypeScript"]:
            self.rules.append((QRegularExpression(r"`(?:[^`\\]|\\.)*`"), self.fmt_string))

        # Functions (name followed by opening paren)
        self.rules.append((QRegularExpression(r"\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\()"), self.fmt_function))

        # Classes/Types (CamelCase words)
        self.rules.append((QRegularExpression(r"\b[A-Z][A-Za-z0-9_]*\b"), self.fmt_class))

        # Operators
        operators = [
            r"\+", r"-", r"\*", r"/", r"%", r"=", r"==", r"!=", r"<", r">",
            r"<=", r">=", r"&&", r"\|\|", r"!", r"&", r"\|", r"\^", r"~",
            r"<<", r">>", r"\+=", r"-=", r"\*=", r"/=", r"%=", r"&=", r"\|=",
            r"\^=", r"<<=", r">>=", r"\+\+", r"--", r"->", r"::", r"\?", r":"
        ]
        for op in operators:
            self.rules.append((QRegularExpression(op), self.fmt_operator))

        # Brackets
        brackets = [r"\(", r"\)", r"\[", r"\]", r"\{", r"\}"]
        for br in brackets:
            self.rules.append((QRegularExpression(br), self.fmt_bracket))

        # Comments - handled separately in highlightBlock for multi-line support

    def highlightBlock(self, text):
        """Highlight a single block of text."""
        # Apply all regex rules
        for pattern, fmt in self.rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

        # Handle comments after other rules to override them
        self._highlight_comments(text)

    def _highlight_comments(self, text):
        """Highlight single-line and multi-line comments."""
        # Single-line comments
        if self.lang_info.line_comment:
            comment_start = text.find(self.lang_info.line_comment)
            if comment_start >= 0:
                # Check it's not inside a string (basic check)
                self.setFormat(comment_start, len(text) - comment_start, self.fmt_comment)

        # Multi-line comments (basic support)
        if self.lang_info.block_comment_start and self.lang_info.block_comment_end:
            start_pattern = QRegularExpression(re.escape(self.lang_info.block_comment_start))
            end_pattern   = QRegularExpression(re.escape(self.lang_info.block_comment_end))

            start_match = start_pattern.match(text)
            if start_match.hasMatch():
                start_index = start_match.capturedStart()
                end_match = end_pattern.match(
                    text, start_index + len(self.lang_info.block_comment_start)
                )
                if end_match.hasMatch():
                    length = end_match.capturedEnd() - start_index
                    self.setFormat(start_index, length, self.fmt_comment)
                else:
                    self.setFormat(start_index, len(text) - start_index, self.fmt_comment)


# ============================================================================
# SECTION: ui.panels.editor.tree_sitter_highlighter (ui/panels/editor/tree_sitter_highlighter.py)
# ============================================================================
"""
tree_sitter_highlighter.py — Structural syntax highlighting (Phase 2 item 8).

Replaces the regex :class:`SyntaxHighlighter` with a real parse tree when the
optional `tree-sitter` / `tree-sitter-languages` packages are installed. A parse
tree is accurate where regexes guess: it never mistakes a keyword inside a
string for a keyword, colours nested constructs correctly, and lays the
groundwork for structural features (folding, breadcrumbs, semantic selection).

Graceful degradation
--------------------
Both packages are optional. :func:`create_highlighter` returns a
:class:`TreeSitterHighlighter` only when tree-sitter is importable *and* a
grammar exists for the file's language; otherwise it falls back to the regex
highlighter, so highlighting always works. :data:`TREE_SITTER_AVAILABLE`
records which path is active.

Highlighting model
------------------
QSyntaxHighlighter drives highlighting per text block (line). We parse the whole
document once per document revision and pre-compute, for every row, the coloured
spans on that row (``row -> [(col_start, col_end, fmt_key)]``). ``highlightBlock``
then just applies the spans for the current row. Column offsets follow
tree-sitter's convention (UTF-8 byte offset within the line), which equals the
character offset for ASCII source — the common case for code.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

from ui.panels.editor.language_support import detect_language, get_language_by_name

try:  # pragma: no cover - import guard
    from tree_sitter_languages import get_parser as _ts_get_parser
    TREE_SITTER_AVAILABLE = True
except Exception:
    _ts_get_parser = None
    TREE_SITTER_AVAILABLE = False


# Our language names → tree-sitter grammar names (tree_sitter_languages keys).
_TS_LANG_NAMES = {
    "Python": "python",
    "JavaScript": "javascript",
    "TypeScript": "typescript",
    "TSX": "tsx",
    "C": "c",
    "C++": "cpp",
    "C#": "c_sharp",
    "Java": "java",
    "Go": "go",
    "Rust": "rust",
    "Ruby": "ruby",
    "PHP": "php",
    "HTML": "html",
    "CSS": "css",
    "JSON": "json",
    "Bash": "bash",
    "YAML": "yaml",
    "TOML": "toml",
    "SQL": "sql",
}

# tree-sitter node types → our format keys. Grammars are broadly consistent on
# these leaf/wrapper node names; anything unmatched is left unstyled.
_COMMENT_TYPES = {"comment", "line_comment", "block_comment"}
_STRING_TYPES = {
    "string", "string_literal", "interpreted_string_literal", "raw_string_literal",
    "char_literal", "template_string", "string_content", "quoted_string",
}
_NUMBER_TYPES = {
    "integer", "float", "number", "int_literal", "float_literal",
    "numeric_literal", "decimal_integer_literal",
}


def _language_name(language_or_path) -> str:
    """Resolve the incoming language/path spec to a language display name."""
    try:
        if isinstance(language_or_path, Path):
            info = detect_language(language_or_path)
        elif isinstance(language_or_path, str) and (
                "." in language_or_path or "/" in language_or_path
                or "\\" in language_or_path):
            info = detect_language(Path(language_or_path))
        else:
            info = get_language_by_name(str(language_or_path))
        return info.name if info else "plaintext"
    except Exception:
        return "plaintext"


def create_highlighter(document, language_or_path):
    """Return the best available highlighter for a document.

    Tree-sitter when its grammar is installed for the language; otherwise the
    regex :class:`SyntaxHighlighter`. Callers use this instead of constructing a
    highlighter directly so the fallback is automatic and centralised.
    """
    name = _language_name(language_or_path)
    if TREE_SITTER_AVAILABLE and name in _TS_LANG_NAMES:
        try:
            return TreeSitterHighlighter(document, name)
        except Exception:
            pass
    from ui.panels.editor.syntax_highlighter import SyntaxHighlighter
    return SyntaxHighlighter(document, language_or_path)


class TreeSitterHighlighter(QSyntaxHighlighter):
    """Parse-tree-driven highlighter for one document."""

    def __init__(self, document, language_name: str):
        super().__init__(document)
        self._lang_name = language_name
        self._parser = _ts_get_parser(_TS_LANG_NAMES[language_name])
        # Keyword sets come from our language metadata so keyword colouring
        # matches the regex highlighter's vocabulary.
        info = get_language_by_name(language_name)
        self._keywords = set(getattr(info, "keywords", []) or [])
        self._formats: Dict[str, QTextCharFormat] = {}
        self._spans: Dict[int, List[Tuple[int, int, str]]] = {}
        self._revision = -1
        self.setup_formats()

    # ── theming ────────────────────────────────────────────────────────────
    def setup_formats(self) -> None:
        from ui.design_system import get_design_system
        c = get_design_system().colors

        def fmt(color, *, bold=False, italic=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Bold)
            if italic:
                f.setFontItalic(True)
            return f

        self._formats = {
            "keyword":  fmt(c.syn_keyword, bold=True),
            "string":   fmt(c.syn_string),
            "comment":  fmt(c.syn_comment, italic=True),
            "number":   fmt(c.syn_number),
            "function": fmt(c.syn_function),
            "class":    fmt(c.syn_class),
            "operator": fmt(c.syn_operator),
        }

    def refresh_theme(self) -> None:
        self.setup_formats()
        self.rehighlight()

    # ── parsing ───────────────────────────────────────────────────────────
    def _reparse(self) -> None:
        source = self.document().toPlainText()
        try:
            tree = self._parser.parse(source.encode("utf-8"))
        except Exception:
            self._spans = {}
            return
        spans: Dict[int, List[Tuple[int, int, str]]] = {}
        self._walk(tree.root_node, spans)
        self._spans = spans

    def _walk(self, node, spans: Dict[int, List[Tuple[int, int, str]]]) -> None:
        """Depth-first classify each node and record per-row coloured spans."""
        key = self._classify(node)
        if key is not None:
            self._emit_span(node, key, spans)
            # Leaf-style categories (strings/comments) shouldn't be overwritten
            # by their children, so stop descending.
            if key in ("string", "comment"):
                return
        for child in node.children:
            self._walk(child, spans)

    def _classify(self, node) -> Optional[str]:
        t = node.type
        if t in _COMMENT_TYPES:
            return "comment"
        if t in _STRING_TYPES:
            return "string"
        if t in _NUMBER_TYPES:
            return "number"
        if node.child_count == 0:
            text = node.text.decode("utf-8", "replace") if node.text else ""
            if text in self._keywords:
                return "keyword"
            if t == "identifier":
                parent = node.parent
                pt = parent.type if parent is not None else ""
                if pt in ("call", "call_expression", "function_call"):
                    return "function"
                if pt in ("function_definition", "function_declaration",
                          "method_definition"):
                    return "function"
                if pt in ("class_definition", "class_declaration"):
                    return "class"
                if text[:1].isupper():
                    return "class"
        return None

    @staticmethod
    def _emit_span(node, key: str,
                   spans: Dict[int, List[Tuple[int, int, str]]]) -> None:
        sr, sc = node.start_point
        er, ec = node.end_point
        if sr == er:
            spans.setdefault(sr, []).append((sc, ec, key))
        else:
            # Multi-line node (block comment / triple-quoted string): colour the
            # first row from its column to end, whole middle rows, last row up to
            # its end column. A large sentinel end covers "to end of line".
            spans.setdefault(sr, []).append((sc, 1_000_000, key))
            for row in range(sr + 1, er):
                spans.setdefault(row, []).append((0, 1_000_000, key))
            spans.setdefault(er, []).append((0, ec, key))

    # ── QSyntaxHighlighter hook ─────────────────────────────────────────────
    def highlightBlock(self, text: str) -> None:
        rev = self.document().revision()
        if rev != self._revision:
            self._reparse()
            self._revision = rev
        row = self.currentBlock().blockNumber()
        length = len(text)
        for col_start, col_end, key in self._spans.get(row, ()):  # noqa: E501
            fmt = self._formats.get(key)
            if fmt is None:
                continue
            start = max(0, min(col_start, length))
            end = max(0, min(col_end, length))
            if end > start:
                self.setFormat(start, end - start, fmt)



# ============================================================================
# SECTION: ui.panels.editor.completion_popup (ui/panels/editor/completion_popup.py)
# ============================================================================
"""
completion_popup.py — Autocomplete + signature-help popups for the editor.

Two small frameless widgets that float over :class:`CodeEditor`:

  * :class:`CompletionPopup` — a keyboard-navigable list of candidates. The
    editor feeds it items (from the jedi provider), positions it under the
    caret, and forwards Up/Down/Enter/Esc while it is visible. Choosing an item
    emits :data:`chosen` with the text to insert.
  * :class:`SignatureTip` — a one-line tool-tip-styled label showing the active
    call signature, with the current parameter emphasised.

Both are theme-aware and Qt-only (no backend imports), so they stay reusable and
cheap to construct.
"""

from typing import List

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QLabel, QFrame
from PySide6.QtCore import Qt, Signal

from ui.design_system import get_design_system, FontSize


class CompletionPopup(QListWidget):
    """A floating, keyboard-driven completion list."""

    chosen = Signal(str)   # insert_text of the accepted item

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CompletionPopup")
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setFocusPolicy(Qt.NoFocus)
        self.setUniformItemSizes(True)
        self.setMouseTracking(True)
        self.itemClicked.connect(self._accept_item)
        self._apply_style()

    # ── population ────────────────────────────────────────────────────────────
    def set_items(self, items: List) -> bool:
        """Fill the list from Completion objects. Returns True if non-empty."""
        self.clear()
        for comp in items:
            label = getattr(comp, "label", str(comp))
            kind = getattr(comp, "kind", "")
            text = f"{label}    {kind}" if kind else label
            it = QListWidgetItem(text)
            it.setData(Qt.UserRole, getattr(comp, "insert_text", "") or label)
            detail = getattr(comp, "detail", "")
            if detail:
                it.setToolTip(detail)
            self.addItem(it)
        if self.count():
            self.setCurrentRow(0)
        return self.count() > 0

    # ── keyboard driving (called by the editor while visible) ─────────────────
    def move_selection(self, delta: int) -> None:
        if not self.count():
            return
        row = (self.currentRow() + delta) % self.count()
        self.setCurrentRow(row)

    def accept_current(self) -> bool:
        """Emit the current item's insert text. Returns False if empty."""
        it = self.currentItem()
        if it is None:
            return False
        self._accept_item(it)
        return True

    def _accept_item(self, item: QListWidgetItem) -> None:
        self.chosen.emit(item.data(Qt.UserRole) or item.text())
        self.hide()

    # ── style ─────────────────────────────────────────────────────────────────
    def _apply_style(self) -> None:
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #CompletionPopup {{
                background: {c.surface_overlay};
                color: {c.text_primary};
                border: 1px solid {c.border};
                border-radius: 4px;
                font-family: 'Cascadia Code','Consolas',monospace;
                font-size: {FontSize.small}px;
                outline: none;
            }}
            #CompletionPopup::item {{ padding: 2px 8px; }}
            #CompletionPopup::item:selected {{
                background: {c.selection}; color: {c.text_primary};
            }}
        """)

    def refresh_theme(self) -> None:
        self._apply_style()


class SignatureTip(QLabel):
    """A floating one-line label showing the active call signature."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SignatureTip")
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setTextFormat(Qt.RichText)
        self._apply_style()

    def show_signature(self, signature) -> None:
        """Render a Signature, bolding the active parameter."""
        params = list(getattr(signature, "parameters", []) or [])
        active = getattr(signature, "active_parameter", 0) or 0
        if params:
            shown = []
            for i, p in enumerate(params):
                shown.append(f"<b>{p}</b>" if i == active else p)
            body = ", ".join(shown)
            label = getattr(signature, "label", "")
            name = label.split("(")[0] if "(" in label else label
            self.setText(f"{name}({body})")
        else:
            self.setText(getattr(signature, "label", ""))
        self.adjustSize()

    def _apply_style(self) -> None:
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #SignatureTip {{
                background: {c.surface_overlay};
                color: {c.text_secondary};
                border: 1px solid {c.border};
                border-radius: 4px;
                padding: 3px 8px;
                font-family: 'Cascadia Code','Consolas',monospace;
                font-size: {FontSize.small}px;
            }}
        """)

    def refresh_theme(self) -> None:
        self._apply_style()


# ============================================================================
# SECTION: ui.panels.editor.symbol_outline (ui/panels/editor/symbol_outline.py)
# ============================================================================
"""
symbol_outline.py — Lightweight structural outline from the tree-sitter parse.

The breadcrumb bar wants to answer one question cheaply: *which definition
encloses the caret right now?* Tree-sitter already parses every open document
for highlighting, so we reuse the same grammars here rather than bolt on a
second parser. When tree-sitter isn't installed (or has no grammar for the
language) every function degrades to an empty result and the breadcrumb simply
shows the file path with no symbol tail — no errors, no hard dependency.

The public surface is two functions:

* :func:`extract_definitions` — parse source once and return a flat list of
  :class:`Definition` (name, kind, start row, end row), nesting included.
* :func:`enclosing_symbols` — given that list and a 0-based row, return the
  nested chain of definitions containing the row, outermost first.

Rows follow tree-sitter's convention (0-based). Callers cache the definition
list per document revision and only re-run :func:`enclosing_symbols` on cursor
moves, which is a cheap in-memory scan.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from ui.panels.editor.language_support import detect_language, get_language_by_name

try:  # Reuse the highlighter's grammar loader so we never parse twice differently.
    from ui.panels.editor.tree_sitter_highlighter import (
        _ts_get_parser, TREE_SITTER_AVAILABLE, _TS_LANG_NAMES,
    )
except Exception:  # pragma: no cover - defensive
    _ts_get_parser = None
    TREE_SITTER_AVAILABLE = False
    _TS_LANG_NAMES = {}


# tree-sitter definition node types → a short human kind. Grammars diverge a
# little on names, so we cast a wide net; anything not listed is ignored.
_DEF_KINDS = {
    # Python
    "function_definition": "def",
    "class_definition": "class",
    # JavaScript / TypeScript
    "function_declaration": "def",
    "generator_function_declaration": "def",
    "method_definition": "def",
    "class_declaration": "class",
    "interface_declaration": "interface",
    "abstract_class_declaration": "class",
    # C / C++
    "class_specifier": "class",
    "struct_specifier": "struct",
    "namespace_definition": "namespace",
    # Java / C#
    "method_declaration": "def",
    "constructor_declaration": "def",
    "enum_declaration": "enum",
    "struct_declaration": "struct",
    "record_declaration": "record",
    # Go
    "type_declaration": "type",
    # Rust
    "function_item": "def",
    "impl_item": "impl",
    "struct_item": "struct",
    "enum_item": "enum",
    "trait_item": "trait",
    "mod_item": "mod",
    # Ruby
    "method": "def",
    "singleton_method": "def",
    "module": "module",
    # PHP
    "function_definition_statement": "def",
}

# Node types that carry a usable identifier when we can't find a `name` field.
_NAME_NODE_TYPES = {
    "identifier", "field_identifier", "type_identifier", "constant",
    "name", "word", "scoped_identifier", "property_identifier",
    "namespace_identifier",
}


@dataclass(frozen=True)
class Definition:
    name: str
    kind: str
    start_row: int   # 0-based, inclusive
    end_row: int     # 0-based, inclusive


def language_name_for(path: str) -> str:
    """Display language name (e.g. ``"Python"``) for a path, or ``"plaintext"``."""
    try:
        info = detect_language(Path(path)) if path else None
        return info.name if info else "plaintext"
    except Exception:
        return "plaintext"


def supports(language_name: str) -> bool:
    """True when a tree-sitter grammar is available for this language."""
    return bool(TREE_SITTER_AVAILABLE and language_name in _TS_LANG_NAMES)


def extract_definitions(text: str, language_name: str) -> List[Definition]:
    """Return every function/class/etc. definition in ``text``, nesting included.

    Empty when tree-sitter or the grammar is unavailable, the source is huge
    (a guard against pathological files), or parsing fails for any reason.
    """
    if not text or not supports(language_name):
        return []
    if len(text) > 2_000_000:            # ~2 MB: skip rather than stall the UI
        return []
    try:
        parser = _ts_get_parser(_TS_LANG_NAMES[language_name])
        tree = parser.parse(text.encode("utf-8"))
    except Exception:
        return []
    out: List[Definition] = []
    _collect(tree.root_node, out)
    return out


def enclosing_symbols(defs: List[Definition], row: int) -> List[Definition]:
    """Definitions whose row range contains ``row``, outermost → innermost.

    Definitions that contain the same row are necessarily nested (siblings have
    disjoint ranges), so sorting the matches by span gives the ancestor chain.
    """
    hits = [d for d in defs if d.start_row <= row <= d.end_row]
    hits.sort(key=lambda d: (d.start_row, -(d.end_row - d.start_row)))
    return hits


# ── internals ────────────────────────────────────────────────────────────────
def _collect(node, out: List[Definition]) -> None:
    kind = _DEF_KINDS.get(node.type)
    if kind is not None:
        name = _name_of(node)
        if name:
            sr, _ = node.start_point
            er, _ = node.end_point
            out.append(Definition(name, kind, sr, er))
    for child in node.children:
        _collect(child, out)


def _name_of(node) -> Optional[str]:
    """Best-effort identifier for a definition node across grammars."""
    # Most grammars expose the declared name via the ``name`` field.
    try:
        named = node.child_by_field_name("name")
    except Exception:
        named = None
    if named is not None:
        txt = _text(named)
        if txt:
            return txt
    # C/C++ hide the name inside a (function_)declarator; follow that field.
    for field in ("declarator", "type"):
        try:
            sub = node.child_by_field_name(field)
        except Exception:
            sub = None
        if sub is not None:
            found = _first_identifier(sub, depth=4)
            if found:
                return found
    # Fall back to a shallow search of immediate children.
    return _first_identifier(node, depth=2)


def _first_identifier(node, depth: int) -> Optional[str]:
    """Shallow depth-first hunt for the first identifier-like descendant."""
    if depth < 0:
        return None
    if node.type in _NAME_NODE_TYPES:
        txt = _text(node)
        if txt:
            return txt
    for child in node.children:
        found = _first_identifier(child, depth - 1)
        if found:
            return found
    return None


def _text(node) -> str:
    try:
        raw = node.text
        return raw.decode("utf-8", "replace").strip() if raw else ""
    except Exception:
        return ""


# ============================================================================
# SECTION: ui.panels.editor.breadcrumb (ui/panels/editor/breadcrumb.py)
# ============================================================================
"""
breadcrumb.py — The path + symbol strip above the editor.

A thin bar that sits between the tab strip and the editor and answers "where am
I?" at a glance: the workspace-relative folder trail, the file, and — when
tree-sitter can tell us — the enclosing class/function chain at the caret.

Every segment is live. Clicking a folder or the file reveals it in the Explorer
(``path_activated``); clicking a symbol jumps the caret to its definition
(``symbol_activated``). The bar is backend-agnostic: it only emits Qt signals,
and the CenterPanel/MainWindow translate them into reveal/goto actions.

It renders nothing until a file is open, so the dashboard stays clean.
"""

from pathlib import Path
from typing import List, Tuple

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal

from ui.design_system import get_design_system, Spacing, Radius, FontSize


class _Crumb(QLabel):
    """A single clickable segment (folder, file, or symbol)."""

    clicked = Signal()

    def __init__(self, text: str, object_name: str, tooltip: str = "",
                 clickable: bool = True, parent=None):
        super().__init__(text, parent)
        self.setObjectName(object_name)
        self.kind_tag = object_name          # stable id for styling/introspection
        if tooltip:
            self.setToolTip(tooltip)
        if clickable:
            self.setCursor(Qt.PointingHandCursor)
        self._clickable = clickable

    def mousePressEvent(self, event):
        if self._clickable and event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class Breadcrumb(QWidget):
    """Path + symbol trail for the active editor."""

    path_activated = Signal(str)     # filesystem path of a clicked path segment
    symbol_activated = Signal(int)   # 0-based row of a clicked symbol

    # Deep paths collapse the middle so the bar never runs off the edge.
    _MAX_PATH_SEGMENTS = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Breadcrumb")
        self.setFixedHeight(26)
        self._root: str = ""
        self._path: str = ""
        self._symbols: List[Tuple[str, str, int]] = []   # (name, kind, row)
        self._crumbs: List[_Crumb] = []                  # live segments, in order

        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(Spacing.md, 0, Spacing.md, 0)
        self._lay.setSpacing(Spacing.xxs)

        self._apply_style()
        self.hide()

    # ── public API ──────────────────────────────────────────────────────────
    def set_context(self, root: str, path: str):
        """Set the workspace root and the active file path, then re-render."""
        self._root = str(root or "")
        self._path = str(path or "")
        self._symbols = []          # stale until the next cursor update
        self._render()

    def set_symbols(self, symbols: List[Tuple[str, str, int]]):
        """Set the enclosing-symbol chain (outermost → innermost) and re-render."""
        self._symbols = list(symbols or [])
        self._render()

    def clear(self):
        self._path = ""
        self._symbols = []
        self._clear_row()
        self.hide()

    def refresh_theme(self):
        self._apply_style()
        self._render()

    # ── rendering ────────────────────────────────────────────────────────────
    def _clear_row(self):
        while self._lay.count():
            item = self._lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._crumbs = []

    def _render(self):
        self._clear_row()
        if not self._path:
            self.hide()
            return

        for i, (label, fs, is_file) in enumerate(self._path_segments()):
            if i > 0:
                self._add_separator()
            if fs is None:                       # the elision placeholder
                self._add(_Crumb("…", "CrumbSep", clickable=False))
                continue
            name = "CrumbFile" if is_file else "Crumb"
            crumb = _Crumb(label, name, tooltip=fs)
            crumb.clicked.connect(lambda f=fs: self.path_activated.emit(f))
            self._add(crumb)

        for name, kind, row in self._symbols:
            self._add_separator()
            crumb = _Crumb(name, "CrumbSym", tooltip=f"{kind} {name}")
            crumb.clicked.connect(lambda r=row: self.symbol_activated.emit(r))
            self._add(crumb)

        self._lay.addStretch(1)
        self.show()

    def _add(self, crumb: "_Crumb"):
        self._crumbs.append(crumb)
        self._lay.addWidget(crumb)

    def _add_separator(self):
        self._add(_Crumb("›", "CrumbSep", clickable=False))

    def _path_segments(self) -> List[Tuple[str, object, bool]]:
        """Yield ``(label, fs_path_or_None, is_file)`` for the path trail.

        Segments are workspace-relative when the file sits under the root; the
        root folder itself leads the trail. A very deep trail collapses its
        middle to a single non-clickable ellipsis so the bar stays one line.
        """
        path = Path(self._path)
        root = Path(self._root) if self._root else None

        rel_parts: List[str]
        base: Path
        if root is not None:
            try:
                rel = path.relative_to(root)
                rel_parts = list(rel.parts)
                base = root
                # Lead with the workspace folder name for orientation.
                segments = [(root.name or str(root), str(root), False)]
            except ValueError:
                rel_parts = list(path.parts)
                base = Path(path.anchor or "")
                segments = []
        else:
            rel_parts = list(path.parts)
            base = Path(path.anchor or "")
            segments = []

        acc = base
        for idx, part in enumerate(rel_parts):
            acc = acc / part
            is_file = idx == len(rel_parts) - 1
            segments.append((part, str(acc), is_file))

        return self._elide(segments)

    def _elide(self, segments: List[Tuple[str, str, bool]]
               ) -> List[Tuple[str, object, bool]]:
        """Collapse the middle of an over-long trail to ``root › … › tail``."""
        if len(segments) <= self._MAX_PATH_SEGMENTS:
            return [(lbl, fs, isf) for (lbl, fs, isf) in segments]
        head = segments[:1]
        tail = segments[-(self._MAX_PATH_SEGMENTS - 2):]
        out: List[Tuple[str, object, bool]] = list(head)
        out.append(("…", None, False))
        out.extend(tail)
        return out

    # ── styling ──────────────────────────────────────────────────────────────
    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #Breadcrumb {{
                background: {c.surface};
                border-bottom: 1px solid {c.border_subtle};
            }}
            #Breadcrumb QLabel {{
                font-size: {FontSize.small}px;
                padding: 2px 5px;
                border-radius: {Radius.sm}px;
            }}
            #Crumb {{ color: {c.text_muted}; }}
            #Crumb:hover {{ background: {c.surface_overlay}; color: {c.text_primary}; }}
            #CrumbFile {{ color: {c.text_secondary}; font-weight: 600; }}
            #CrumbFile:hover {{ background: {c.surface_overlay}; color: {c.text_primary}; }}
            #CrumbSym {{ color: {c.accent}; }}
            #CrumbSym:hover {{ background: {c.surface_overlay}; }}
            #CrumbSep {{ color: {c.text_faint}; padding: 2px 1px; }}
        """)


# ============================================================================
# SECTION: ui.panels.editor.code_editor (ui/panels/editor/code_editor.py)
# ============================================================================
"""
Code Editor — v2.0

A clean, self-contained editor built on QPlainTextEdit:
  - gutter with line numbers
  - current-line highlight
  - theme-driven syntax highlighting (ported SyntaxHighlighter)
  - bracket matching (ported BracketMatcher)
  - LSP diagnostics underlines (via LSPManager.diagnostics_received)
  - auto-indent, tab-as-spaces, cursor/modified signals

The widget is backend-agnostic: it exposes signals the EditorTabs/MainWindow
translate into EventBus traffic.
"""

from PySide6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from PySide6.QtCore import Qt, QRect, QSize, Signal
from PySide6.QtGui import (
    QColor, QPainter, QTextFormat, QFont, QTextCursor, QTextOption,
)

from ui.design_system import get_design_system, FontFamily
from ui.panels.editor.syntax_highlighter import SyntaxHighlighter
from ui.panels.editor.tree_sitter_highlighter import create_highlighter
from ui.panels.editor.bracket_matcher import BracketMatcher
from ui.panels.editor.completion_popup import CompletionPopup, SignatureTip
from ui.settings_manager import get_settings_manager


def _editor_setting(category: str, key: str, fallback):
    try:
        return get_settings_manager().get(category, key, fallback)
    except Exception:
        return fallback


def _current_line_color():
    """A current-line wash that works on light *and* dark palettes.

    A raised-surface token was used before, which is invisible on some themes
    and far too bright on the light ones. A low-alpha accent tint tracks every
    palette.
    """
    c = get_design_system().colors
    tint = QColor(c.accent)
    tint.setAlpha(28 if c.is_dark else 20)
    return tint


class _Gutter(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QSize(self._editor.gutter_width(), 0)

    def paintEvent(self, event):
        self._editor.paint_gutter(event)


class CodeEditor(QPlainTextEdit):

    modified_state_changed = Signal(bool)
    cursor_moved = Signal(int, int)          # (line, col)
    save_requested = Signal()
    # Language-intelligence outcomes the tabs/MainWindow route onward.
    definition_found = Signal(str, int, int)   # (path, line, column) 0-based
    references_found = Signal(str, list)       # (symbol, [Location])
    rename_requested = Signal(object)          # ChangeSet to review

    def __init__(self, file_path: str | None = None, event_bus=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.event_bus = event_bus
        self.lsp_manager = None
        self.diagnostics = []
        self._diag_selections = []
        self._current_line_selection = []
        self._bracket_selections = []
        self._tab_size = 4
        self._insert_spaces = True

        self._gutter = _Gutter(self)
        self._completion = None      # lazily built CompletionPopup
        self._sig_tip = None         # lazily built SignatureTip
        self._setup_ui()
        self._setup_connections()

        self._highlighter = create_highlighter(self.document(), file_path or "plaintext")
        self._bracket = BracketMatcher(self)

        self._update_gutter_width()
        self._highlight_current_line()

    # -- setup ---------------------------------------------------------------
    def _setup_ui(self):
        self.setCursorWidth(2)
        self.apply_editor_settings()
        self._apply_style()

    def apply_editor_settings(self):
        """Apply the editor/appearance settings categories to this widget."""
        family = str(_editor_setting("terminal", "font_family", FontFamily.mono))
        size = int(_editor_setting("appearance", "font_size", 12))
        font = QFont(family.split(",")[0].strip('"\' '), max(8, size))
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        self.setFont(font)

        tab = int(_editor_setting("editor", "tab_size", 4))
        self._tab_size = max(1, tab)
        self._insert_spaces = bool(_editor_setting("editor", "insert_spaces", True))
        self.setTabStopDistance(
            self.fontMetrics().horizontalAdvance(" ") * self._tab_size)

        wrap = bool(_editor_setting("appearance", "word_wrap", False))
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth if wrap
                             else QPlainTextEdit.NoWrap)
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere if wrap
                             else QTextOption.NoWrap)

        opts = self.document().defaultTextOption()
        show_ws = str(_editor_setting("editor", "render_whitespace", "none"))
        flags = opts.flags()
        if show_ws in ("all", "boundary", "selection", "trailing"):
            flags |= QTextOption.ShowTabsAndSpaces
        else:
            flags &= ~QTextOption.ShowTabsAndSpaces
        opts.setFlags(flags)
        self.document().setDefaultTextOption(opts)

        self._update_gutter_width()

    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {c.surface_inset};
                color: {c.text_primary};
                border: none;
                selection-background-color: {c.selection};
                selection-color: {c.text_primary};
                padding-left: 6px;
            }}
            QScrollBar:vertical, QScrollBar:horizontal {{
                background: transparent; width: 10px; height: 10px; margin: 0;
            }}
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
                background: {c.scrollbar}; border-radius: 5px; min-height: 24px;
            }}
            QScrollBar::handle:hover {{ background: {c.scrollbar_hover}; }}
            QScrollBar::add-line, QScrollBar::sub-line {{
                width: 0; height: 0; background: transparent;
            }}
        """)

    def refresh_theme(self):
        """Re-skin the editor, its gutter, brackets and syntax colours.

        Every colour in here is read from the palette at build time, so without
        this the editor kept the theme it was opened under while the rest of the
        window switched.
        """
        self._apply_style()
        fn = getattr(self._highlighter, "refresh_theme", None)
        if callable(fn):
            fn()
        else:                                  # older highlighter: rebuild it
            self._highlighter = create_highlighter(
                self.document(), self.file_path or "plaintext")
            self._highlighter.rehighlight()
        fn = getattr(self._bracket, "refresh_theme", None)
        if callable(fn):
            try:
                fn()
            except Exception:
                pass
        self._highlight_current_line()
        self._rebuild_diag_selections()
        self._gutter.update()
        self.viewport().update()

    def _setup_connections(self):
        self.blockCountChanged.connect(lambda _: self._update_gutter_width())
        self.updateRequest.connect(self._on_update_request)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self.cursorPositionChanged.connect(self._emit_cursor)
        self.cursorPositionChanged.connect(self._on_cursor_brackets)
        self.modificationChanged.connect(self.modified_state_changed.emit)

    # -- file ----------------------------------------------------------------
    def load_text(self, content: str):
        self.setPlainText(content)
        self.document().setModified(False)

    def text(self) -> str:
        return self.toPlainText()

    def set_language(self, language_or_path: str):
        self._highlighter = create_highlighter(self.document(), language_or_path)
        self._highlighter.rehighlight()

    # -- gutter --------------------------------------------------------------
    def gutter_width(self) -> int:
        digits = max(3, len(str(max(1, self.blockCount()))))
        return 16 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_gutter_width(self):
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)

    def _on_update_request(self, rect: QRect, dy: int):
        if dy:
            self._gutter.scroll(0, dy)
        else:
            self._gutter.update(0, rect.y(), self._gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_gutter_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._gutter.setGeometry(QRect(cr.left(), cr.top(), self.gutter_width(), cr.height()))

    def paint_gutter(self, event):
        c = get_design_system().colors
        painter = QPainter(self._gutter)
        painter.fillRect(event.rect(), QColor(c.surface))
        # Hairline between gutter and code, so the two surfaces read as one
        # themed unit instead of a floating strip.
        painter.setPen(QColor(c.border_subtle))
        painter.drawLine(self._gutter.width() - 1, event.rect().top(),
                         self._gutter.width() - 1, event.rect().bottom())
        block = self.firstVisibleBlock()
        num = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        cur_line = self.textCursor().blockNumber()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                is_cur = (num == cur_line)
                painter.setPen(QColor(c.accent if is_cur else c.text_faint))
                painter.drawText(
                    0, int(top), self._gutter.width() - 8,
                    self.fontMetrics().height(),
                    Qt.AlignRight | Qt.AlignVCenter, str(num + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            num += 1
        painter.end()

    # -- highlights ----------------------------------------------------------
    def _highlight_current_line(self):
        sel = QTextEdit.ExtraSelection()
        sel.format.setBackground(_current_line_color())
        sel.format.setProperty(QTextFormat.FullWidthSelection, True)
        sel.cursor = self.textCursor()
        sel.cursor.clearSelection()
        self._current_line_selection = [sel]
        self._refresh_selections()

    def set_bracket_highlights(self, selections):
        self._bracket_selections = selections or []
        self._refresh_selections()

    def _on_cursor_brackets(self):
        try:
            self._bracket.highlight_matching_brackets()
        except Exception:
            pass

    def _refresh_selections(self):
        self.setExtraSelections(
            self._current_line_selection
            + self._bracket_selections
            + self._diag_selections
        )

    # -- editing behaviour ---------------------------------------------------
    def keyPressEvent(self, event):
        # While the completion popup is open, it owns navigation keys.
        if self._completion is not None and self._completion.isVisible():
            if event.key() in (Qt.Key_Up, Qt.Key_Down):
                self._completion.move_selection(1 if event.key() == Qt.Key_Down else -1)
                return
            if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
                if self._completion.accept_current():
                    return
            if event.key() == Qt.Key_Escape:
                self._completion.hide()
                return
        # Ctrl+Space → trigger completion.
        if (event.key() == Qt.Key_Space
                and event.modifiers() & Qt.ControlModifier):
            self.request_completion()
            return
        # F12 go-to-definition, Shift+F12 find-references, F2 rename.
        if event.key() == Qt.Key_F12:
            if event.modifiers() & Qt.ShiftModifier:
                self.request_references()
            else:
                self.request_definition()
            return
        if event.key() == Qt.Key_F2:
            self.request_rename()
            return
        if event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
            self.save_requested.emit()
            return
        if event.key() == Qt.Key_Tab and not (event.modifiers() & Qt.ShiftModifier):
            if getattr(self, "_insert_spaces", True):
                self.insertPlainText(" " * getattr(self, "_tab_size", 4))
            else:
                self.insertPlainText("\t")
            return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._auto_indent()
            return
        super().keyPressEvent(event)
        # After inserting a character, keep the signature tip and popup fresh.
        text = event.text()
        if text == "(":
            self.request_signature()
        elif text == ")":
            self._hide_signature()
        elif (self._completion is not None and self._completion.isVisible()
              and (text.isalnum() or text == "_")):
            self.request_completion()

    def _auto_indent(self):
        cursor = self.textCursor()
        block_text = cursor.block().text()
        indent = len(block_text) - len(block_text.lstrip(" "))
        step = getattr(self, "_tab_size", 4)
        extra = step if block_text.rstrip().endswith((":", "{", "(", "[")) else 0
        cursor.insertText("\n" + " " * (indent + extra))
        self.setTextCursor(cursor)

    def _emit_cursor(self):
        cur = self.textCursor()
        self.cursor_moved.emit(cur.blockNumber() + 1, cur.columnNumber() + 1)

    # -- LSP -----------------------------------------------------------------
    def set_lsp_manager(self, lsp_manager):
        self.lsp_manager = lsp_manager
        if lsp_manager is not None:
            try:
                lsp_manager.diagnostics_received.connect(self._on_diagnostics)
            except Exception:
                pass

    # -- language intelligence (jedi via LSPManager) -------------------------
    def _provider(self):
        """The in-process provider for this file, or None if unavailable."""
        mgr = self.lsp_manager
        if mgr is None or not self.file_path:
            return None
        try:
            if not mgr.supports_inprocess(self.file_path):
                return None
            prov = mgr.python_intelligence()
            return prov if prov.available else None
        except Exception:
            return None

    def _cursor_pos(self):
        """Current caret as (0-based line, 0-based column)."""
        cur = self.textCursor()
        return cur.blockNumber(), cur.columnNumber()

    def _word_under_cursor(self) -> str:
        cur = self.textCursor()
        cur.select(QTextCursor.WordUnderCursor)
        return cur.selectedText()

    def request_completion(self) -> None:
        prov = self._provider()
        if prov is None:
            return
        line, col = self._cursor_pos()
        items = prov.complete(self.toPlainText(), str(self.file_path), line, col)
        if not items:
            self._hide_completion()
            return
        popup = self._ensure_completion()
        if popup.set_items(items):
            self._place_popup(popup)
            popup.show()

    def _insert_completion(self, insert_text: str) -> None:
        cur = self.textCursor()
        cur.select(QTextCursor.WordUnderCursor)
        # jedi returns the full name; replace the partial word under the caret.
        cur.insertText(insert_text)
        self.setTextCursor(cur)

    def request_signature(self) -> None:
        prov = self._provider()
        if prov is None:
            return
        line, col = self._cursor_pos()
        sigs = prov.signatures(self.toPlainText(), str(self.file_path), line, col)
        if not sigs:
            self._hide_signature()
            return
        tip = self._ensure_sig_tip()
        tip.show_signature(sigs[0])
        self._place_tip(tip)
        tip.show()

    def request_definition(self) -> None:
        prov = self._provider()
        if prov is None:
            return
        line, col = self._cursor_pos()
        locs = prov.definition(self.toPlainText(), str(self.file_path), line, col)
        if not locs:
            return
        loc = locs[0]
        if loc.path and loc.path == str(self.file_path):
            self.goto_line_column(loc.line, loc.column)
        else:
            self.definition_found.emit(loc.path, loc.line, loc.column)

    def request_references(self) -> None:
        prov = self._provider()
        if prov is None:
            return
        line, col = self._cursor_pos()
        locs = prov.references(self.toPlainText(), str(self.file_path), line, col)
        if locs:
            self.references_found.emit(self._word_under_cursor(), locs)

    def request_rename(self) -> None:
        """Gather reference sites and hand a ChangeSet to the review flow."""
        prov = self._provider()
        if prov is None:
            return
        old_name = self._word_under_cursor()
        if not old_name:
            return
        new_name = self._prompt_new_name(old_name)
        if not new_name or new_name == old_name:
            return
        line, col = self._cursor_pos()
        locs = prov.references(self.toPlainText(), str(self.file_path), line, col)
        change_set = self._build_rename_change_set(locs, old_name, new_name)
        if change_set is not None and change_set.operations:
            self.rename_requested.emit(change_set)

    def _prompt_new_name(self, old_name: str) -> str:
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(
            self, "Rename symbol", f"Rename '{old_name}' to:", text=old_name)
        return text.strip() if ok else ""

    def _build_rename_change_set(self, locs, old_name: str, new_name: str):
        """Turn reference locations into a multi-file MODIFY ChangeSet.

        References are grouped by file; within each file we rewrite the symbol on
        every referenced line and emit one hunk per changed line. The current
        buffer is used for this file so unsaved edits are respected; other files
        are read from disk.
        """
        try:
            from ai.editing.change_set import ChangeSet, ChangeOperation, Hunk
        except Exception:
            return None
        from pathlib import Path as _P
        by_file: dict = {}
        for loc in locs:
            if loc.path:
                by_file.setdefault(loc.path, []).append(loc)
        ops = []
        for path, file_locs in by_file.items():
            if path == str(self.file_path):
                source = self.toPlainText()
            else:
                try:
                    source = _P(path).read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
            lines = source.splitlines(keepends=True)
            hunks = []
            seen = set()
            for loc in file_locs:
                if loc.line in seen or loc.line >= len(lines):
                    continue
                seen.add(loc.line)
                old_line = lines[loc.line]
                new_line = self._replace_identifier(old_line, old_name, new_name)
                if new_line == old_line:
                    continue
                hunks.append(Hunk(
                    old_start=loc.line + 1, old_lines=1,
                    new_start=loc.line + 1, new_lines=1,
                    old_text=old_line, new_text=new_line))
            if hunks:
                ops.append(ChangeOperation.modify_file(
                    path, hunks, reason=f"Rename '{old_name}' → '{new_name}'"))
        if not ops:
            return None
        return ChangeSet.from_operations(ops)

    @staticmethod
    def _replace_identifier(line: str, old: str, new: str) -> str:
        """Replace whole-word occurrences of ``old`` with ``new`` on a line."""
        import re
        return re.sub(rf"\b{re.escape(old)}\b", new, line)

    def goto_line_column(self, line: int, column: int) -> None:
        """Move the caret to a 0-based line/column and centre it."""
        block = self.document().findBlockByNumber(max(0, line))
        if not block.isValid():
            return
        cur = QTextCursor(block)
        cur.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor,
                         max(0, column))
        self.setTextCursor(cur)
        self.centerCursor()
        self.setFocus()

    # -- popup helpers -------------------------------------------------------
    def _ensure_completion(self) -> CompletionPopup:
        if self._completion is None:
            self._completion = CompletionPopup(self)
            self._completion.chosen.connect(self._insert_completion)
        return self._completion

    def _ensure_sig_tip(self) -> SignatureTip:
        if self._sig_tip is None:
            self._sig_tip = SignatureTip(self)
        return self._sig_tip

    def _hide_completion(self) -> None:
        if self._completion is not None:
            self._completion.hide()

    def _hide_signature(self) -> None:
        if self._sig_tip is not None:
            self._sig_tip.hide()

    def _place_popup(self, popup) -> None:
        rect = self.cursorRect()
        pt = self.viewport().mapToGlobal(rect.bottomLeft())
        popup.move(pt)
        popup.setFixedWidth(320)
        popup.setMaximumHeight(220)

    def _place_tip(self, tip) -> None:
        rect = self.cursorRect()
        pt = self.viewport().mapToGlobal(rect.topLeft())
        tip.move(pt.x(), pt.y() - tip.height() - 4)


    def _on_diagnostics(self, file_path: str, diagnostics: list):
        if not self.file_path or file_path != str(self.file_path):
            return
        self.diagnostics = diagnostics or []
        self._rebuild_diag_selections()

    def _rebuild_diag_selections(self):
        c = get_design_system().colors
        sels = []
        for diag in self.diagnostics:
            try:
                line = int(diag.get("line", diag.get("range", {}).get("start", {}).get("line", 0)))
                severity = diag.get("severity", 1)
            except Exception:
                continue
            sel = QTextEdit.ExtraSelection()
            color = QColor(c.error if severity == 1 else c.warning)
            color.setAlpha(40)
            sel.format.setBackground(color)
            sel.format.setProperty(QTextFormat.FullWidthSelection, True)
            block = self.document().findBlockByNumber(line)
            if block.isValid():
                cur = QTextCursor(block)
                sel.cursor = cur
                sels.append(sel)
        self._diag_selections = sels
        self._refresh_selections()


# ============================================================================
# SECTION: ui.panels.editor.editor_tabs (ui/panels/editor/editor_tabs.py)
# ============================================================================
"""
Editor Tabs — v2.0

A tabbed container of CodeEditors. Backend-agnostic: it emits Qt signals that
MainWindow maps to EventBus traffic (open/save/close). Provides the exact
`force_close_tab(path)` entry point main.py depends on.
"""

from pathlib import Path

from PySide6.QtWidgets import QTabWidget, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from ui.design_system import get_design_system, Editor, FontSize, Radius
from ui.panels.editor.code_editor import CodeEditor
from ui.panels.editor.language_support import detect_language


class EditorTabs(QTabWidget):

    save_requested = Signal(str)          # path
    close_requested = Signal(str)         # path
    current_file_changed = Signal(str)    # path ("" if none)
    modified_changed = Signal(str, bool)  # path, modified
    cursor_moved = Signal(int, int)       # line, col
    language_changed = Signal(str)        # language name
    empty = Signal()                      # last tab closed
    definition_found = Signal(str, int, int)   # (path, line, column) 0-based
    references_found = Signal(str, list)       # (symbol, [Location])
    rename_requested = Signal(object)          # ChangeSet to review

    def __init__(self, event_bus=None, parent=None):
        super().__init__(parent)
        self.event_bus = event_bus
        self.lsp_manager = None
        self._editors: dict[str, CodeEditor] = {}
        # Key of the tab opened as a single-click preview, if any. Only one
        # preview tab exists at a time; it is replaced rather than added to, so
        # browsing the tree does not flood the tab bar.
        self._preview_key: str = ""
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)
        self.setElideMode(Qt.ElideRight)
        self.tabCloseRequested.connect(self._on_tab_close_requested)
        self.currentChanged.connect(self._on_current_changed)
        self._apply_style()

    # -- public API ----------------------------------------------------------
    def open_file(self, path: str, content: str = "", encoding: str = "utf-8",
                  read_only: bool = False, preview: bool = False,
                  force_reload: bool = False):
        key = self._key(path)
        if key in self._editors:
            existing = self._editors[key]
            if force_reload and content is not None:
                try:
                    existing.load_text(content)
                except Exception:
                    pass
            self.setCurrentWidget(existing)
            if not preview and self._preview_key == key:
                self._promote_preview()      # a real open pins the preview tab
            return existing

        if preview:
            self._discard_preview(keep=key)

        editor = CodeEditor(file_path=path, event_bus=self.event_bus)
        editor.load_text(content)
        editor.setReadOnly(read_only)
        if self.lsp_manager is not None:
            editor.set_lsp_manager(self.lsp_manager)

        # These lambdas resolve the key from the editor rather than closing over
        # the key captured at open time, so a Save As (which re-keys the tab via
        # `retarget`) keeps its dirty-marker and save wiring intact.
        editor.save_requested.connect(
            lambda e=editor: self.save_requested.emit(e.file_path or ""))
        editor.modified_state_changed.connect(
            lambda m, e=editor: self._on_editor_modified(
                self._key(e.file_path or ""), m))
        editor.cursor_moved.connect(self.cursor_moved.emit)
        editor.definition_found.connect(self.definition_found.emit)
        editor.references_found.connect(self.references_found.emit)
        editor.rename_requested.connect(self.rename_requested.emit)

        name = Path(path).name if path else "untitled"
        idx = self.addTab(editor, name)
        ro = "  (read-only)" if read_only else ""
        self.setTabToolTip(idx, f"{path}{ro}")
        self._editors[key] = editor
        self.setCurrentIndex(idx)
        self._preview_key = key if preview else self._preview_key
        if preview:
            self._mark_preview(idx)
        return editor

    # -- preview tab ---------------------------------------------------------
    def _mark_preview(self, idx: int):
        """Grey the preview tab so it reads as provisional."""
        bar = self.tabBar()
        bar.setTabTextColor(idx, QColor(get_design_system().colors.text_muted))
        try:
            bar.setTabData(idx, "preview")
        except Exception:
            pass

    def _promote_preview(self):
        """Turn the preview tab into a normal one (double-click, or an edit)."""
        key, self._preview_key = self._preview_key, ""
        idx = self._index_for(key)
        if idx >= 0:
            self.tabBar().setTabTextColor(
                idx, QColor(get_design_system().colors.text_primary))

    def _discard_preview(self, keep: str = ""):
        """Close the current preview tab unless it was edited or is `keep`."""
        key = self._preview_key
        if not key or key == keep:
            return
        editor = self._editors.get(key)
        if editor is None:
            self._preview_key = ""
            return
        if editor.document().isModified():
            self._promote_preview()          # never discard unsaved work
            return
        self._preview_key = ""
        self.force_close_tab(editor.file_path or key)

    def force_close_tab(self, path: str):
        """Close a tab without emitting a close request (backend already closed)."""
        key = self._key(path)
        editor = self._editors.get(key)
        if editor is None:
            return
        idx = self.indexOf(editor)
        if idx >= 0:
            self.removeTab(idx)
        editor.deleteLater()
        self._editors.pop(key, None)
        if self._preview_key == key:
            self._preview_key = ""
        if self.count() == 0:
            self.empty.emit()

    def open_diff(self, title: str, unified_text: str = "",
                  old_text: str = None, new_text: str = None):
        """Open a read-only side-by-side diff as its own tab.

        Accepts either a unified-diff string (``unified_text``) or an explicit
        pair of old/new file contents. Re-opening a diff with the same title
        reuses the existing tab. Diff tabs are not tracked in ``_editors`` (they
        hold no file), so close/refresh handle them via widget-type checks.
        """
        from ui.widgets.diff_view import DiffView
        # Reuse a diff tab with the same title if present.
        for idx in range(self.count()):
            w = self.widget(idx)
            if isinstance(w, DiffView) and self.tabText(idx) == title:
                self.setCurrentIndex(idx)
                view = w
                break
        else:
            view = DiffView()
            idx = self.addTab(view, title)
            self.setTabToolTip(idx, title)
            self.setCurrentIndex(idx)
        if old_text is not None or new_text is not None:
            view.set_texts(old_text, new_text)
        else:
            view.set_unified(unified_text)
        return view

    def current_editor(self) -> CodeEditor | None:
        w = self.currentWidget()
        return w if isinstance(w, CodeEditor) else None

    def current_path(self) -> str:
        ed = self.current_editor()
        return ed.file_path if ed else ""

    def open_paths(self) -> list:
        """Paths of all currently open editors (for the command palette index)."""
        return [ed.file_path for ed in self._editors.values() if ed.file_path]

    def next_untitled_name(self) -> str:
        """An unused ``untitled-N`` label, so New File can be pressed twice."""
        used = {Path(ed.file_path or "").name for ed in self._editors.values()}
        i = 1
        while f"untitled-{i}" in used:
            i += 1
        return f"untitled-{i}"

    def set_lsp_manager(self, lsp_manager):
        self.lsp_manager = lsp_manager
        for editor in self._editors.values():
            editor.set_lsp_manager(lsp_manager)

    def mark_saved(self, path: str):
        ed = self._editors.get(self._key(path))
        if ed:
            ed.document().setModified(False)

    def retarget(self, editor, new_path: str) -> str:
        """Point an open editor at a different file path (Save As).

        Re-keys the ``_editors`` map, renames the tab, and re-derives the syntax
        highlighter from the new extension — an untitled buffer saved as
        ``foo.py`` should start colouring as Python immediately. Returns the new
        key, or "" if nothing was retargeted.
        """
        if editor is None or not new_path:
            return ""
        old_key = next((k for k, ed in self._editors.items() if ed is editor), None)
        new_key = self._key(new_path)
        if old_key is not None:
            self._editors.pop(old_key, None)
            if self._preview_key == old_key:
                self._preview_key = ""
        self._editors[new_key] = editor
        editor.file_path = str(new_path)
        idx = self.indexOf(editor)
        if idx >= 0:
            name = Path(new_path).name or str(new_path)
            self.setTabText(idx, name)
            self.setTabToolTip(idx, str(new_path))
        try:
            editor.set_language(str(new_path))
        except Exception:
            pass
        if self.currentWidget() is editor:
            self._on_current_changed(idx)
        return new_key

    def retarget_path(self, old_path: str, new_path: str) -> bool:
        """Retarget an open editor whose file was renamed outside the tabs."""
        editor = self._editors.get(self._key(old_path))
        if editor is None:
            return False
        self.retarget(editor, new_path)
        return True

    # -- internals -----------------------------------------------------------
    def _key(self, path: str) -> str:
        try:
            return str(Path(path).resolve())
        except Exception:
            return str(path)

    def _on_tab_close_requested(self, index: int):
        editor = self.widget(index)
        if isinstance(editor, CodeEditor):
            self.close_requested.emit(editor.file_path or "")
        else:
            # Non-editor tabs (e.g. read-only diff views) hold no backend file,
            # so close them directly rather than routing through the manager.
            self.removeTab(index)
            editor.deleteLater()
            if self.count() == 0:
                self.empty.emit()

    def _on_current_changed(self, index: int):
        editor = self.widget(index)
        if isinstance(editor, CodeEditor):
            path = editor.file_path or ""
            self.current_file_changed.emit(path)
            lang = detect_language(Path(path)) if path else None
            self.language_changed.emit(lang.name if lang else "Plain Text")
        else:
            self.current_file_changed.emit("")

    def _on_editor_modified(self, path: str, modified: bool):
        if modified and path == self._preview_key:
            self._promote_preview()   # editing a preview keeps it around
        idx = self._index_for(path)
        if idx >= 0:
            name = Path(path).name if path else "untitled"
            self.setTabText(idx, f"● {name}" if modified else name)
        self.modified_changed.emit(path, modified)

    def _index_for(self, key: str) -> int:
        ed = self._editors.get(key)
        return self.indexOf(ed) if ed else -1

    def _apply_style(self):
        c = get_design_system().colors
        idle, hover = self._close_button_icons()
        if idle and hover:
            # Faint at rest so the X recedes into the palette, brighter with a
            # soft chip on hover — reads as "muted, shows on hover".
            close_qss = f"""
            QTabBar::close-button {{
                image: url("{idle}");
                subcontrol-position: right;
                margin-left: 6px;
                padding: 2px;
                border-radius: {Radius.sm}px;
            }}
            QTabBar::close-button:hover {{
                image: url("{hover}");
                background: {c.surface_overlay};
            }}"""
        else:
            close_qss = "QTabBar::close-button { subcontrol-position: right; }"
        self.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: {c.surface_inset}; }}
            QTabBar::tab {{
                background: {c.surface};
                color: {c.text_muted};
                padding: 8px 16px;
                border: none;
                border-right: 1px solid {c.border_subtle};
                max-width: 220px;
                height: {Editor.TAB_HEIGHT - 16}px;
            }}
            QTabBar::tab:selected {{
                background: {c.surface_inset};
                color: {c.text_primary};
                border-top: 2px solid {c.accent};
            }}
            QTabBar::tab:hover:!selected {{ background: {c.surface_raised}; }}
            {close_qss}
        """)

    def _close_button_icons(self):
        """Return (idle, hover) file paths for the tab close glyph, themed.

        Qt paints a native close button whose colour we can't reach from QSS —
        only its ``image`` can be swapped. So we render the design-system
        ``close`` icon (faint at rest, ``text_secondary`` on hover) to two tiny
        cached PNGs and let the tab bar point at them. This is what mutes the
        stock bright-X so it stops clashing with the muted palette.

        On any failure we return ``("", "")`` and the caller falls back to the
        native button — closing tabs is never put at risk by the cosmetics.
        """
        try:
            import os
            import tempfile
            from ui.widgets.icons import icon

            ds = get_design_system()
            c = ds.colors
            cache = os.path.join(tempfile.gettempdir(), "mcm_tab_icons")
            os.makedirs(cache, exist_ok=True)
            paths = []
            for state, col in (("idle", c.text_faint),
                               ("hover", c.text_secondary)):
                p = os.path.join(cache, f"close_{ds.theme}_{state}.png")
                icon("close", size=16, color=col).pixmap(16, 16).save(p, "PNG")
                paths.append(p.replace("\\", "/"))
            return paths[0], paths[1]
        except Exception:
            return "", ""

    def refresh_theme(self):
        """Restyle the tab bar and every open editor.

        This used to restyle only the tab bar, which is why the code area kept
        the palette it was opened under after a theme switch.
        """
        self._apply_style()
        self._fan_out("refresh_theme")
        # tab text colours are palette-derived too
        c = get_design_system().colors
        bar = self.tabBar()
        for idx in range(self.count()):
            editor = self.widget(idx)
            key = self._key(getattr(editor, "file_path", "") or "")
            bar.setTabTextColor(
                idx, QColor(c.text_muted if key == self._preview_key
                            else c.text_primary))

    def apply_editor_settings(self):
        """Push an editor/appearance settings change into every open editor."""
        self._fan_out("apply_editor_settings")

    def _fan_out(self, method: str):
        for editor in list(self._editors.values()):
            fn = getattr(editor, method, None)
            if callable(fn):
                try:
                    fn()
                except Exception:
                    pass


# ============================================================================
# SECTION: ui.panels.dashboard (ui/panels/dashboard.py)
# ============================================================================
"""
Dashboard — v2.0

The welcome surface shown when no file is open. Presents quick actions and a
recent-projects list. Emits `open_recent_requested(path)` (wired by MainWindow
to open a workspace) and accepts the manager setters main.py-adjacent code
provides.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QGridLayout,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal

from ui.design_system import get_design_system, Spacing, Radius, FontSize
from ui.widgets.controls import TextButton, Card, hline


class _RecentItem(QWidget):
    clicked = Signal(str)

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self._path = path
        self.setObjectName("RecentItem")
        self.setCursor(Qt.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(Spacing.lg, Spacing.md, Spacing.lg, Spacing.md)
        lay.setSpacing(Spacing.md)
        name = QLabel(Path(path).name or path)
        name.setObjectName("RecentName")
        loc = QLabel(str(Path(path).parent))
        loc.setObjectName("RecentPath")
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(name)
        col.addWidget(loc)
        lay.addLayout(col)
        lay.addStretch(1)
        open_lbl = QLabel("Open →")
        open_lbl.setObjectName("RecentOpenAction")
        lay.addWidget(open_lbl)

    def mousePressEvent(self, event):
        self.clicked.emit(self._path)


class Dashboard(QScrollArea):

    open_recent_requested = Signal(str)
    open_folder_requested = Signal()
    new_file_requested = Signal()
    clone_repo_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_analyzer = None
        self.workspace_manager = None
        self.provider_manager = None
        self._recent_container = None
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self._build()
        self._apply_style()

    def _build(self):
        root = QWidget()
        root.setObjectName("DashboardRoot")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch(1)

        center = QWidget()
        center.setMaximumWidth(720)
        center.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        lay = QVBoxLayout(center)
        lay.setContentsMargins(Spacing.huge, Spacing.huge, Spacing.huge, Spacing.huge)
        lay.setSpacing(Spacing.xl)

        overline = QLabel("CALM LOCAL COMPUTING")
        overline.setObjectName("HeroOverline")
        title = QLabel("OwnCode")
        title.setObjectName("HeroTitle")
        subtitle = QLabel(
            "An AI-native coding workspace designed for deep reading and high-precision systems programming."
        )
        subtitle.setObjectName("HeroSubtitle")
        subtitle.setWordWrap(True)
        lay.addWidget(overline)
        lay.addWidget(title)
        lay.addWidget(subtitle)
        lay.addWidget(hline())

        # Quick actions
        actions = QHBoxLayout()
        actions.setSpacing(Spacing.md)
        open_btn = TextButton("Open Folder", icon_name="folder", variant="primary", tooltip="Open an existing project folder (Ctrl+O)")
        open_btn.clicked.connect(self.open_folder_requested.emit)
        new_btn = TextButton("New File", icon_name="plus", tooltip="Create a new untitled file (Ctrl+N)")
        new_btn.clicked.connect(self.new_file_requested.emit)
        clone_btn = TextButton("Clone Repository", icon_name="git", tooltip="Clone a Git repository from URL")
        clone_btn.clicked.connect(self.clone_repo_requested.emit)
        for b in (open_btn, new_btn, clone_btn):
            actions.addWidget(b)
        actions.addStretch(1)
        lay.addLayout(actions)

        # Recent
        recent_label = QLabel("RECENT")
        recent_label.setProperty("role", "subheading")
        lay.addWidget(recent_label)

        self._recent_card = Card(padding=Spacing.xs)
        self._recent_container = self._recent_card.body
        self._empty_label = QLabel("No recent projects yet — open a folder to get started.")
        self._empty_label.setProperty("role", "muted")
        self._empty_label.setContentsMargins(Spacing.lg, Spacing.md, Spacing.lg, Spacing.md)
        self._recent_container.addWidget(self._empty_label)
        lay.addWidget(self._recent_card)

        wrap = QHBoxLayout()
        wrap.addStretch(1)
        wrap.addWidget(center)
        wrap.addStretch(1)
        outer.addLayout(wrap)
        outer.addStretch(1)
        self.setWidget(root)

    # -- data ----------------------------------------------------------------
    def set_recent_projects(self, projects: list):
        # clear
        while self._recent_container.count():
            item = self._recent_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        if not projects:
            self._empty_label = QLabel("No recent projects yet — open a folder to get started.")
            self._empty_label.setProperty("role", "muted")
            self._empty_label.setContentsMargins(Spacing.lg, Spacing.md, Spacing.lg, Spacing.md)
            self._recent_container.addWidget(self._empty_label)
            return
        for i, path in enumerate(projects[:12]):
            item = _RecentItem(path)
            item.clicked.connect(self.open_recent_requested.emit)
            self._recent_container.addWidget(item)
            if i < len(projects) - 1:
                self._recent_container.addWidget(hline())

    # -- manager setters (provided by app) -----------------------------------
    def set_project_analyzer(self, analyzer):
        self.project_analyzer = analyzer

    def set_workspace_manager(self, manager):
        self.workspace_manager = manager

    def set_provider_manager(self, manager):
        self.provider_manager = manager

    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #DashboardRoot {{ background: {c.surface}; }}
            #HeroTitle {{ font-size: {FontSize.xxl}px; font-weight: 700; color: {c.text_primary}; }}
            #HeroSubtitle {{ font-size: {FontSize.lg}px; color: {c.text_muted}; }}
            #RecentItem {{ border-radius: {Radius.sm}px; }}
            #RecentItem:hover {{ background: {c.surface_overlay}; }}
            #RecentName {{ color: {c.text_primary}; font-weight: 600; }}
            #RecentPath {{ color: {c.text_faint}; font-size: {FontSize.tiny}px; }}
        """)

    def refresh_theme(self):
        self._apply_style()


# ============================================================================
# SECTION: ui.panels.center (ui/panels/center.py)
# ============================================================================
"""
Center Panel — v2.1

Stacked central area that flips between the Dashboard (no file open) and the
EditorTabs (one or more files open). A Breadcrumb bar sits above the stack and
is shown only while an editor is visible. Exposes `.editor_tabs` and
`.dashboard` exactly as main.py-adjacent code expects
(`window.center.editor_tabs...`, `window.center.dashboard.open_recent_requested`).
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget
from PySide6.QtCore import Signal

from ui.panels.dashboard import Dashboard
from ui.panels.editor.editor_tabs import EditorTabs
from ui.panels.editor.breadcrumb import Breadcrumb
from ui.panels.editor import symbol_outline


class CenterPanel(QWidget):

    # Re-emitted from the breadcrumb: a path segment was clicked and should be
    # revealed in the Explorer. MainWindow owns the Explorer, so it wires this.
    reveal_requested = Signal(str)

    def __init__(self, event_bus=None, parent=None):
        super().__init__(parent)
        self.event_bus = event_bus
        self._workspace_root = ""
        self._current_path = ""
        self._last_chain = None          # dedupe symbol re-renders on cursor move
        self._sym_cache: dict = {}       # id(editor) -> (revision, [Definition])

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.breadcrumb = Breadcrumb()
        self.breadcrumb.path_activated.connect(self.reveal_requested.emit)
        self.breadcrumb.symbol_activated.connect(self._on_symbol_activated)
        lay.addWidget(self.breadcrumb)

        self._stack = QStackedWidget()
        self.dashboard = Dashboard()
        self.editor_tabs = EditorTabs(event_bus=event_bus)

        self._stack.addWidget(self.dashboard)     # index 0
        self._stack.addWidget(self.editor_tabs)   # index 1
        lay.addWidget(self._stack)

        self.editor_tabs.empty.connect(self.show_dashboard)
        self.editor_tabs.cursor_moved.connect(self._on_cursor_moved)

    def open_file(self, path: str, content: str = "", encoding: str = "utf-8",
                  read_only: bool = False, preview: bool = False):
        self.editor_tabs.open_file(path, content, encoding, read_only,
                                   preview=preview)
        self.show_editor()

    def open_diff(self, title: str, unified_text: str = "",
                  old_text: str = None, new_text: str = None):
        """Open a side-by-side diff tab (Git or AI change preview)."""
        view = self.editor_tabs.open_diff(title, unified_text,
                                          old_text=old_text, new_text=new_text)
        self.show_editor()
        return view

    def show_dashboard(self):
        self._stack.setCurrentIndex(0)
        self.breadcrumb.hide()

    def show_editor(self):
        self._stack.setCurrentIndex(1)
        self.breadcrumb.setVisible(bool(self._current_path))

    # ── breadcrumb ────────────────────────────────────────────────────────────
    def set_workspace_root(self, root: str):
        """Remember the workspace root so path crumbs are shown relative to it."""
        self._workspace_root = str(root or "")
        if self._current_path:
            self.breadcrumb.set_context(self._workspace_root, self._current_path)
            self._last_chain = None
            self._update_symbols()

    def set_breadcrumb(self, path: str):
        """Point the breadcrumb at ``path`` (or clear it when empty)."""
        self._current_path = str(path or "")
        if not self._current_path:
            self.breadcrumb.clear()
            self._last_chain = None
            return
        self.breadcrumb.set_context(self._workspace_root, self._current_path)
        self._last_chain = None
        self._update_symbols()

    def _on_cursor_moved(self, _line: int, _col: int):
        if self._current_path:
            self._update_symbols()

    def _on_symbol_activated(self, row: int):
        ed = self.editor_tabs.current_editor()
        if ed is not None:
            try:
                ed.goto_line_column(int(row), 0)
            except Exception:
                pass

    def _update_symbols(self):
        """Recompute the enclosing-symbol chain for the caret and push it up.

        Cheap on cursor moves: the parse is cached per document revision, and an
        unchanged chain skips the re-render entirely.
        """
        ed = self.editor_tabs.current_editor()
        if ed is None:
            self._set_chain([])
            return
        lang = symbol_outline.language_name_for(self._current_path)
        if not symbol_outline.supports(lang):
            self._set_chain([])
            return
        try:
            text = ed.toPlainText()
            row = ed.textCursor().blockNumber()
        except Exception:
            self._set_chain([])
            return
        defs = self._defs_for(ed, text, lang)
        chain = symbol_outline.enclosing_symbols(defs, row)[-2:]  # innermost two
        self._set_chain([(d.name, d.kind, d.start_row) for d in chain])

    def _set_chain(self, chain: list):
        if chain == self._last_chain:
            return
        self._last_chain = chain
        self.breadcrumb.set_symbols(chain)

    def _defs_for(self, ed, text: str, lang: str) -> list:
        try:
            rev = ed.document().revision()
        except Exception:
            rev = -1
        key = id(ed)
        cached = self._sym_cache.get(key)
        if cached is not None and cached[0] == rev:
            return cached[1]
        if len(self._sym_cache) > 12:        # keep the cache from growing forever
            self._sym_cache.clear()
        defs = symbol_outline.extract_definitions(text, lang)
        self._sym_cache[key] = (rev, defs)
        return defs

    def refresh_theme(self):
        self.dashboard.refresh_theme()
        self.editor_tabs.refresh_theme()
        self.breadcrumb.refresh_theme()

    def apply_editor_settings(self):
        """Forward an editor/appearance settings change to the open editors."""
        fn = getattr(self.editor_tabs, "apply_editor_settings", None)
        if callable(fn):
            fn()



    def get_buffer_text(self, file_path: str) -> Optional[str]:
        """Return unsaved in-memory buffer text if the file is open in an editor tab."""
        norm_target = os.path.normcase(os.path.abspath(file_path))
        for i in range(self.count()):
            w = self.widget(i)
            w_path = getattr(w, "file_path", None)
            if w_path and os.path.normcase(os.path.abspath(str(w_path))) == norm_target:
                return w.toPlainText()
        return None

    def update_buffer_text(self, file_path: str, new_content: str, save_to_disk: bool = True) -> bool:
        """Synchronize an agent file edit directly into the open editor tab or disk."""
        norm_target = os.path.normcase(os.path.abspath(file_path))
        updated_tab = False
        for i in range(self.count()):
            w = self.widget(i)
            w_path = getattr(w, "file_path", None)
            if w_path and os.path.normcase(os.path.abspath(str(w_path))) == norm_target:
                cursor = w.textCursor()
                pos = cursor.position()
                w.setPlainText(new_content)
                cursor.setPosition(min(pos, len(new_content)))
                w.setTextCursor(cursor)
                updated_tab = True
                if save_to_disk and hasattr(w, "document"):
                    w.document().setModified(False)
                break
        if save_to_disk:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            Path(file_path).write_text(new_content, encoding="utf-8")
        return updated_tab
