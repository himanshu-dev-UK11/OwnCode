"""
Consolidated Module: agent.code_intelligence

Combines: ai.intelligence.symbol_indexer, ai.intelligence.reference_index, ai.intelligence.dependency_graph, ai.intelligence.language_statistics, ai.intelligence.entry_point_detector, ai.intelligence.architecture_detector, ai.intelligence.documentation_indexer, ai.intelligence.impact_analyzer, ai.intelligence.project_health, ai.intelligence.project_analyzer
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['ai.intelligence.symbol_indexer', 'ai.intelligence.reference_index', 'ai.intelligence.dependency_graph', 'ai.intelligence.language_statistics', 'ai.intelligence.entry_point_detector', 'ai.intelligence.architecture_detector', 'ai.intelligence.documentation_indexer', 'ai.intelligence.impact_analyzer', 'ai.intelligence.project_health', 'ai.intelligence.project_analyzer']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ai.intelligence.symbol_indexer (ai/intelligence/symbol_indexer.py)
# ============================================================================
"""
Symbol Indexer — indexes classes, functions, and variables in source code.

This module provides symbol indexing for multiple programming languages.
It extracts:
- Classes
- Functions/Methods
- Variables/Constants
- Interfaces/Enums
- Import statements

The index can be used for:
- Code navigation (go to definition)
- Finding usages
- Understanding code structure
"""

import os
import fnmatch
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from core.logger import setup_logger

logger = setup_logger(__name__)

# Directories to skip when indexing — they are noisy, slow, and often
# permission-restricted (e.g. node_modules on Windows).
_SKIP_DIRS = {
    "__pycache__", ".git", "node_modules", ".venv", "venv", "env",
    "build", "dist", ".mypy_cache", ".pytest_cache", ".tox",
    ".next", ".nuxt", "vendor", "target", "versions history",
}


class SymbolType(Enum):
    """Types of symbols that can be indexed."""
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    INTERFACE = "interface"
    ENUM = "enum"
    STRUCT = "struct"
    MODULE = "module"
    IMPORT = "import"
    DECORATOR = "decorator"
    ANNOTATION = "annotation"


@dataclass
class SymbolEntry:
    """Represents a symbol in the codebase."""
    name: str
    symbol_type: SymbolType
    path: str
    line_start: int
    line_end: int
    class_name: Optional[str] = None  # For methods
    module: Optional[str] = None
    signature: Optional[str] = None
    docstring: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    visibility: str = "public"  # public, private, protected
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "symbol_type": self.symbol_type.value,
            "path": self.path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "class_name": self.class_name,
            "module": self.module,
            "signature": self.signature,
            "docstring": self.docstring,
            "decorators": self.decorators,
            "visibility": self.visibility,
            "parameters": self.parameters,
            "return_type": self.return_type,
        }
        
    def get_full_name(self) -> str:
        """Get the fully qualified name of the symbol."""
        if self.class_name:
            return f"{self.class_name}.{self.name}"
        return self.name


class SymbolIndexer:
    """
    Indexes symbols across a project's source code.
    
    Supports multiple programming languages:
    - Python
    - JavaScript/TypeScript
    - Java
    - C/C++
    - Go
    - Rust
    - PHP
    - Ruby
    - C#
    
    The index can be queried for:
    - Symbols by name
    - Symbols by type
    - Symbols in a file
    - Symbol definitions and references
    """
    
    def __init__(self):
        self.index: Dict[str, List[SymbolEntry]] = {}  # file_path -> symbols
        self.name_index: Dict[str, List[SymbolEntry]] = {}  # symbol_name -> entries
        
    def index_project(self, project_path: str | Path, file_patterns: List[str] = None) -> List[SymbolEntry]:
        """
        Index all symbols in a project.
        
        Args:
            project_path: Path to the project root
            file_patterns: File patterns to include (default: common source patterns)
            
        Returns:
            List of all indexed symbols
        """
        project_path = Path(project_path).resolve()
        
        if file_patterns is None:
            file_patterns = [
                "*.py", "*.js", "*.ts", "*.jsx", "*.tsx",
                "*.java", "*.c", "*.cpp", "*.h", "*.hpp",
                "*.go", "*.rs", "*.php", "*.rb", "*.cs",
            ]
            
        logger.info(f"Indexing symbols in: {project_path}")
        
        all_symbols = []
        self.index.clear()
        self.name_index.clear()

        if project_path.is_dir():
            for root, dirs, files in os.walk(project_path, topdown=True):
                dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")]
                root_p = Path(root)
                for fname in files:
                    if not any(fnmatch.fnmatch(fname, pat) for pat in file_patterns):
                        continue
                    fpath = root_p / fname
                    if fpath.is_file():
                        symbols = self.index_file(str(fpath))
                        all_symbols.extend(symbols)

        logger.info(f"Indexed {len(all_symbols)} symbols in project")
        return all_symbols
    
    def index_file(self, file_path: str | Path) -> List[SymbolEntry]:
        """
        Index all symbols in a single file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of symbols found in the file
        """
        file_path = Path(file_path).resolve()
        symbols = []
        if not file_path.is_file():
            return symbols
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            ext = file_path.suffix.lower()
            
            if ext == '.py':
                symbols.extend(self._index_python(content, str(file_path)))
            elif ext in ['.js', '.ts', '.jsx', '.tsx']:
                symbols.extend(self._index_js(content, str(file_path)))
            elif ext == '.java':
                symbols.extend(self._index_java(content, str(file_path)))
            elif ext in ['.c', '.cpp', '.h', '.hpp']:
                symbols.extend(self._index_c(content, str(file_path)))
            elif ext == '.go':
                symbols.extend(self._index_go(content, str(file_path)))
            elif ext == '.rs':
                symbols.extend(self._index_rust(content, str(file_path)))
            elif ext == '.php':
                symbols.extend(self._index_php(content, str(file_path)))
            elif ext == '.rb':
                symbols.extend(self._index_ruby(content, str(file_path)))
            elif ext == '.cs':
                symbols.extend(self._index_csharp(content, str(file_path)))
                
        except Exception as e:
            logger.warning(f"Error indexing file {file_path}: {e}")

        self.index[str(file_path)] = symbols
        for sym in symbols:
            self.name_index.setdefault(sym.name, []).append(sym)
            
        return symbols
    
    def _index_python(self, content: str, file_path: str) -> List[SymbolEntry]:
        """Index Python symbols."""
        symbols = []
        lines = content.split('\n')
        current_class = None
        
        for i, line in enumerate(lines, 1):
            # Class definition
            class_match = re.match(r'^class\s+(\w+)(?:\(([^)]*)\))?:', line)
            if class_match:
                current_class = class_match.group(1)
                symbols.append(SymbolEntry(
                    name=current_class,
                    symbol_type=SymbolType.CLASS,
                    path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i),
                    signature=f"class {current_class}",
                ))
                continue
                
            # Function/method definition
            func_match = re.match(r'^\s*(async\s+)?def\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*([^:]+))?:', line)
            if func_match:
                is_async = bool(func_match.group(1))
                name = func_match.group(2)
                params = func_match.group(3)
                return_type = func_match.group(4)
                
                symbol_type = SymbolType.METHOD if current_class else SymbolType.FUNCTION
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=symbol_type,
                    path=file_path,
                    line_start=i,
                    line_end=self._find_block_end(lines, i),
                    class_name=current_class,
                    signature=f"{'async ' if is_async else ''}def {name}({params})",
                    parameters=self._parse_parameters(params),
                    return_type=return_type.strip() if return_type else None,
                ))
                continue
                
            # Decorator
            decorator_match = re.match(r'^\s*@(\w+)', line)
            if decorator_match:
                symbols.append(SymbolEntry(
                    name=decorator_match.group(1),
                    symbol_type=SymbolType.DECORATOR,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                ))
                
        return symbols
    
    def _index_js(self, content: str, file_path: str) -> List[SymbolEntry]:
        """Index JavaScript/TypeScript symbols."""
        symbols = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Function declaration
            func_match = re.match(r'\s*(export\s+)?(async\s+)?function\s+(\w+)\s*\(([^)]*)\)', line)
            if func_match:
                is_async = bool(func_match.group(2))
                name = func_match.group(3)
                params = func_match.group(4)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.FUNCTION,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"{'async ' if is_async else ''}function {name}({params})",
                    parameters=self._parse_parameters(params),
                ))
                continue
                
            # Arrow function
            arrow_match = re.match(r'\s*(export\s+)?(const|let|var)\s+(\w+)\s*=\s*(async\s+)?\(([^)]*)\)\s*=>', line)
            if arrow_match:
                name = arrow_match.group(3)
                is_async = bool(arrow_match.group(4))
                params = arrow_match.group(5)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.FUNCTION,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"const {name} = {'async ' if is_async else ''}({params}) =>",
                    parameters=self._parse_parameters(params),
                ))
                
            # Class definition
            class_match = re.match(r'\s*(export\s+)?class\s+(\w+)', line)
            if class_match:
                name = class_match.group(2)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.CLASS,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"{'export ' if class_match.group(1) else ''}class {name}",
                ))
                
            # Interface definition (TypeScript)
            interface_match = re.match(r'\s*(export\s+)?interface\s+(\w+)', line)
            if interface_match:
                name = interface_match.group(2)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.INTERFACE,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"{'export ' if interface_match.group(1) else ''}interface {name}",
                ))
                
            # Variable/constant
            var_match = re.match(r'\s*(export\s+)?(const|let|var)\s+(\w+)', line)
            if var_match:
                name = var_match.group(3)
                const = var_match.group(2) == 'const'
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.CONSTANT if const else SymbolType.VARIABLE,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"{var_match.group(1) or ''}{var_match.group(2)} {name}",
                ))
                
        return symbols
    
    def _index_java(self, content: str, file_path: str) -> List[SymbolEntry]:
        """Index Java symbols."""
        symbols = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Class definition
            class_match = re.match(r'^\s*(public|private|protected)?\s*(static\s+)?(final\s+)?class\s+(\w+)', line)
            if class_match:
                name = class_match.group(4)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.CLASS,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"class {name}",
                ))
                
            # Method definition
            method_match = re.match(r'^\s*(public|private|protected)?\s*(static\s+)?(final\s+)?(\w+)\s+(\w+)\s*\(([^)]*)\)', line)
            if method_match:
                return_type = method_match.group(4)
                name = method_match.group(5)
                params = method_match.group(6)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.METHOD,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"{return_type} {name}({params})",
                    parameters=self._parse_parameters(params),
                    return_type=return_type,
                ))
                
            # Interface definition
            interface_match = re.match(r'^\s*(public|private|protected)?\s*interface\s+(\w+)', line)
            if interface_match:
                name = interface_match.group(2)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.INTERFACE,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"interface {name}",
                ))
                
            # Variable definition
            var_match = re.match(r'^\s*(public|private|protected)?\s*(static\s+)?(final\s+)?(\w+)\s+(\w+)\s*=', line)
            if var_match:
                type_name = var_match.group(4)
                name = var_match.group(5)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.VARIABLE,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"{type_name} {name}",
                    parameters=[type_name],
                ))
                
        return symbols
    
    def _index_c(self, content: str, file_path: str) -> List[SymbolEntry]:
        """Index C/C++ symbols."""
        symbols = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Function definition
            func_match = re.match(r'^\s*(inline\s+)?(static\s+)?(const\s+)?(\w+)\s+(\w+)\s*\(([^)]*)\)', line)
            if func_match:
                return_type = func_match.group(4)
                name = func_match.group(5)
                params = func_match.group(6)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.FUNCTION,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"{return_type} {name}({params})",
                    parameters=self._parse_parameters(params),
                    return_type=return_type,
                ))
                
            # Class/struct definition
            class_match = re.match(r'^\s*(struct|class)\s+(\w+)', line)
            if class_match:
                type_name = class_match.group(1)
                name = class_match.group(2)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.STRUCT if type_name == 'struct' else SymbolType.CLASS,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"{type_name} {name}",
                ))
                
        return symbols
    
    def _index_go(self, content: str, file_path: str) -> List[SymbolEntry]:
        """Index Go symbols."""
        symbols = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Function definition
            func_match = re.match(r'^\s*func\s+(\w+)\s*\(([^)]*)\)', line)
            if func_match:
                name = func_match.group(1)
                params = func_match.group(2)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.FUNCTION,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"func {name}({params})",
                    parameters=self._parse_parameters(params),
                ))
                
            # Method definition
            method_match = re.match(r'^\s*func\s+\(([^)]+)\)\s+(\w+)\s*\(([^)]*)\)', line)
            if method_match:
                receiver = method_match.group(1)
                name = method_match.group(2)
                params = method_match.group(3)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.METHOD,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"func ({receiver}) {name}({params})",
                    parameters=self._parse_parameters(params),
                ))
                
            # Type definition
            type_match = re.match(r'^\s*type\s+(\w+)\s+', line)
            if type_match:
                name = type_match.group(1)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.STRUCT,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"type {name}",
                ))
                
        return symbols
    
    def _index_rust(self, content: str, file_path: str) -> List[SymbolEntry]:
        """Index Rust symbols."""
        symbols = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Function definition
            func_match = re.match(r'^\s*fn\s+(\w+)\s*\(([^)]*)\)', line)
            if func_match:
                name = func_match.group(1)
                params = func_match.group(2)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.FUNCTION,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"fn {name}({params})",
                    parameters=self._parse_parameters(params),
                ))
                
            # Method definition
            method_match = re.match(r'^\s*fn\s+(\w+)\s*\(([^)]*)\)', line)
            if method_match and '&self' in method_match.group(2):
                name = method_match.group(1)
                params = method_match.group(2)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.METHOD,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"fn {name}({params})",
                    parameters=self._parse_parameters(params),
                ))
                
            # Struct definition
            struct_match = re.match(r'^\s*struct\s+(\w+)', line)
            if struct_match:
                name = struct_match.group(1)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.STRUCT,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"struct {name}",
                ))
                
            # Enum definition
            enum_match = re.match(r'^\s*enum\s+(\w+)', line)
            if enum_match:
                name = enum_match.group(1)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.ENUM,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"enum {name}",
                ))
                
        return symbols
    
    def _index_php(self, content: str, file_path: str) -> List[SymbolEntry]:
        """Index PHP symbols."""
        symbols = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Class definition
            class_match = re.match(r'^\s*(abstract\s+)?(final\s+)?class\s+(\w+)', line)
            if class_match:
                name = class_match.group(3)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.CLASS,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"class {name}",
                ))
                
            # Function definition
            func_match = re.match(r'^\s*(public|private|protected)?\s*(static\s+)?function\s+(\w+)', line)
            if func_match:
                name = func_match.group(3)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.FUNCTION,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"function {name}",
                ))
                
        return symbols
    
    def _index_ruby(self, content: str, file_path: str) -> List[SymbolEntry]:
        """Index Ruby symbols."""
        symbols = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Class definition
            class_match = re.match(r'^\s*class\s+(\w+)', line)
            if class_match:
                name = class_match.group(1)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.CLASS,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"class {name}",
                ))
                
            # Method definition
            method_match = re.match(r'^\s*def\s+(\w+)', line)
            if method_match:
                name = method_match.group(1)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.METHOD,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"def {name}",
                ))
                
        return symbols
    
    def _index_csharp(self, content: str, file_path: str) -> List[SymbolEntry]:
        """Index C# symbols."""
        symbols = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Class definition
            class_match = re.match(r'^\s*(public|private|protected)?\s*(static\s+)?(abstract\s+)?class\s+(\w+)', line)
            if class_match:
                name = class_match.group(4)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.CLASS,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"class {name}",
                ))
                
            # Method definition
            method_match = re.match(r'^\s*(public|private|protected)?\s*(static\s+)?(async\s+)?(\w+)\s+(\w+)\s*\(([^)]*)\)', line)
            if method_match:
                return_type = method_match.group(4)
                name = method_match.group(5)
                params = method_match.group(6)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.METHOD,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"{return_type} {name}({params})",
                    parameters=self._parse_parameters(params),
                    return_type=return_type,
                ))
                
            # Interface definition
            interface_match = re.match(r'^\s*interface\s+(\w+)', line)
            if interface_match:
                name = interface_match.group(1)
                
                symbols.append(SymbolEntry(
                    name=name,
                    symbol_type=SymbolType.INTERFACE,
                    path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=f"interface {name}",
                ))
                
        return symbols
    
    def _find_block_end(self, lines: List[str], start_line: int) -> int:
        """Find the end of a code block (for Python)."""
        if start_line >= len(lines):
            return start_line
            
        base_indent = len(lines[start_line - 1]) - len(lines[start_line - 1].lstrip())
        
        for i in range(start_line, len(lines)):
            line = lines[i]
            if line.strip() and not line.startswith(' ' * (base_indent + 1)):
                return i
                
        return len(lines)
    
    def _parse_parameters(self, params: str) -> List[str]:
        """Parse function parameters into a list."""
        if not params:
            return []
            
        # Simple parsing - split by comma
        # This doesn't handle nested parentheses or complex types
        return [p.strip() for p in params.split(',')]
    
    def get_symbols_by_name(self, name: str) -> List[SymbolEntry]:
        """Get all symbols with a given name."""
        return self.name_index.get(name, [])
    
    def get_symbols_by_type(self, symbol_type: SymbolType) -> List[SymbolEntry]:
        """Get all symbols of a given type."""
        return [symbol for file_symbols in self.index.values() for symbol in file_symbols if symbol.symbol_type == symbol_type]
    
    def get_symbols_in_file(self, file_path: str) -> List[SymbolEntry]:
        """Get all symbols in a specific file."""
        return self.index.get(file_path, [])
    
    def find_definition(self, symbol_name: str, context_file: str = None) -> Optional[SymbolEntry]:
        """
        Find the definition of a symbol.
        
        Args:
            symbol_name: Name of the symbol to find
            context_file: Optional file path for context
            
        Returns:
            SymbolEntry if found, None otherwise
        """
        symbols = self.get_symbols_by_name(symbol_name)
        
        if not symbols:
            return None
            
        if len(symbols) == 1:
            return symbols[0]
            
        # If context file is provided, try to find in same file
        if context_file:
            for symbol in symbols:
                if symbol.path == context_file:
                    return symbol
                    
        # Return the first one
        return symbols[0]
    
    def find_usages(self, symbol: SymbolEntry) -> List[SymbolEntry]:
        """
        Find usages of a symbol in the codebase.
        
        Args:
            symbol: The symbol to find usages for
            
        Returns:
            List of SymbolEntry objects representing usages
        """
        usages = []
        
        for path, symbols in self.index.items():
            for s in symbols:
                # Check if this symbol references the given symbol
                # This is a simple implementation - could be improved
                if s.path == symbol.path:
                    continue
                    
                # Check if symbol name appears in the file
                try:
                    content = Path(s.path).read_text(encoding='utf-8', errors='ignore')
                    if symbol.name in content:
                        usages.append(s)
                except Exception:
                    pass
                    
        return usages
    
    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-serializable representation of the index."""
        return {
            "file_count": len(self.index),
            "total_symbols": sum(len(symbols) for symbols in self.index.values()),
            "symbols_by_type": {
                t.value: len([s for file_symbols in self.index.values() for s in file_symbols if s.symbol_type.value == t.value])
                for t in SymbolType
            },
        }

# ============================================================================
# SECTION: ai.intelligence.reference_index (ai/intelligence/reference_index.py)
# ============================================================================
"""
Reference Index — builds and queries symbol references.

This module builds an index of all symbol references (usages) in a project.
It complements SymbolIndexer by tracking where symbols are used rather than
where they are defined.

This enables features like:
- Find all usages of a function
- Find all implementations of an interface
- Cross-reference analysis
- Impact analysis
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass

from core.logger import setup_logger

logger = setup_logger(__name__)

_SKIP_DIRS = {
    "__pycache__", ".git", "node_modules", ".venv", "venv", "env",
    "build", "dist", ".mypy_cache", ".pytest_cache", ".tox",
    ".next", ".nuxt", "vendor", "target", "versions history",
}

_SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".java", ".c", ".cpp", ".h", ".hpp",
    ".go", ".rs", ".php", ".rb", ".cs",
}

_WORD_RE = re.compile(r"\b\w+\b")


@dataclass
class Reference:
    """Represents a reference to a symbol."""
    symbol_name: str
    file_path: str
    line_number: int
    column: int
    context: str  # Short code snippet around the reference
    
    def to_dict(self) -> Dict[str, object]:
        return {
            "symbol_name": self.symbol_name,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column": self.column,
            "context": self.context,
        }


class ReferenceIndex:
    """
    Indexes all references to symbols in a project.
    """
    
    def __init__(self):
        self.references: Dict[str, List[Reference]] = {}  # symbol_name -> references
        self.definitions: Dict[str, List[Reference]] = {}  # symbol_name -> definitions
        self.file_references: Dict[str, List[Reference]] = {}  # file_path -> references
        
    def build_index(self, project_path: str | Path, symbols: List) -> Dict[str, List[str]]:
        """Build a reference index for a project."""
        project_path = Path(project_path).resolve()
        
        logger.info(f"Building reference index for: {project_path}")
        
        # Reset index
        self.references = {}
        self.definitions = {}
        self.file_references = {}
        
        # Index all definitions first
        for symbol in symbols:
            self._add_definition(symbol)
            
        # Then index all references
        self._scan_files(project_path)
        
        logger.info(f"Reference index built: {len(self.references)} symbols referenced")
        
        # Return file paths for each symbol
        result = {}
        for symbol_name, refs in self.references.items():
            result[symbol_name] = list(set(r.file_path for r in refs))
            
        return result
    
    def _add_definition(self, symbol):
        """Add a symbol definition to the index."""
        ref = Reference(
            symbol_name=symbol.name,
            file_path=symbol.path,
            line_number=symbol.line_start,
            column=0,
            context=symbol.signature or "",
        )
        
        if symbol.symbol_type.value in ('class', 'function', 'method', 'variable', 'constant'):
            if symbol.name not in self.definitions:
                self.definitions[symbol.name] = []
            self.definitions[symbol.name].append(ref)
            
            if symbol.name not in self.references:
                self.references[symbol.name] = []
            self.references[symbol.name].append(ref)
            
            if symbol.path not in self.file_references:
                self.file_references[symbol.path] = []
            self.file_references[symbol.path].append(ref)
    
    def _scan_files(self, project_path: Path):
        """Scan all files for symbol references using pruned os.walk."""
        if not self.definitions or not project_path.is_dir():
            return

        for root, dirs, files in os.walk(project_path, topdown=True):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")]
            root_path = Path(root)
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in _SOURCE_EXTENSIONS:
                    continue
                file_path = root_path / fname
                if file_path.is_file():
                    self._scan_file(file_path, project_path)
                
    def _scan_file(self, file_path: Path, project_path: Optional[Path] = None):
        """Scan a single file for symbol references using O(1) token set lookup per line."""
        if not file_path.is_file():
            return
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            try:
                base = project_path if project_path is not None else file_path.parents[1]
                relative_path = str(file_path.relative_to(base))
            except Exception:
                relative_path = str(file_path)

            known_symbols = set(self.definitions.keys())
            if not known_symbols:
                return

            for line_num, line in enumerate(lines, 1):
                if not line:
                    continue
                tokens = set(_WORD_RE.findall(line))
                matched = tokens & known_symbols
                if not matched:
                    continue
                ctx = line.strip()
                for symbol_name in matched:
                    ref = Reference(
                        symbol_name=symbol_name,
                        file_path=relative_path,
                        line_number=line_num,
                        column=0,
                        context=ctx,
                    )
                    if symbol_name not in self.references:
                        self.references[symbol_name] = []
                    self.references[symbol_name].append(ref)

                    if relative_path not in self.file_references:
                        self.file_references[relative_path] = []
                    self.file_references[relative_path].append(ref)
                        
        except Exception as e:
            logger.warning(f"Error scanning file {file_path}: {e}")
    
    def _symbol_in_line(self, symbol_name: str, line: str) -> bool:
        """Check if a symbol name appears in a line (not as part of another identifier)."""
        pattern = r'\b' + re.escape(symbol_name) + r'\b'
        return bool(re.search(pattern, line))
    
    def get_references(self, symbol_name: str) -> List[Reference]:
        """Get all references to a symbol."""
        return self.references.get(symbol_name, [])
    
    def get_definitions(self, symbol_name: str) -> List[Reference]:
        """Get all definitions of a symbol."""
        return self.definitions.get(symbol_name, [])
    
    def get_file_references(self, file_path: str) -> List[Reference]:
        """Get all references in a specific file."""
        return self.file_references.get(file_path, [])
    
    def get_cross_references(self, symbol_name: str) -> Dict[str, List[Reference]]:
        """Get bidirectional references for a symbol."""
        return {
            "references": self.get_references(symbol_name),
            "definitions": self.get_definitions(symbol_name),
        }
    
    def find_callers(self, function_name: str) -> List[Reference]:
        """Find all calls to a function."""
        return [ref for ref in self.get_references(function_name) 
                if 'def' not in ref.context and '(' in ref.context]
    
    def find_implementations(self, interface_name: str) -> List[Reference]:
        """Find all implementations of an interface."""
        implementations = []
        for ref in self.get_references(interface_name):
            if 'class' in ref.context:
                implementations.append(ref)
        return implementations
    
    def get_call_graph(self, function_name: str, depth: int = 3) -> Dict:
        """Build a call graph for a function up to a certain depth."""
        def build_graph(name: str, current_depth: int, visited: Set[str]) -> Dict:
            if current_depth > depth or name in visited:
                return {"name": name, "depth": current_depth}
                
            visited.add(name)
            callers = self.find_callers(name)
            
            return {
                "name": name,
                "depth": current_depth,
                "callers": [
                    build_graph(c.symbol_name, current_depth + 1, visited.copy())
                    for c in callers
                    if c.symbol_name != name
                ],
            }
            
        return build_graph(function_name, 0, set())
    
    def get_impact_analysis(self, symbol_name: str) -> List[str]:
        """Get files that would be affected by changing a symbol."""
        affected_files = set()
        for ref in self.get_references(symbol_name):
            affected_files.add(ref.file_path)
        return list(affected_files)
    
    def get_top_referenced(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get the most referenced symbols in the project."""
        counts = [(name, len(refs)) for name, refs in self.references.items()]
        counts.sort(key=lambda x: x[1], reverse=True)
        return counts[:limit]
    
    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-serializable representation of the index."""
        return {
            "symbol_count": len(self.references),
            "definition_count": len(self.definitions),
            "file_count": len(self.file_references),
            "top_referenced": self.get_top_referenced(10),
        }

# ============================================================================
# SECTION: ai.intelligence.dependency_graph (ai/intelligence/dependency_graph.py)
# ============================================================================
"""
Dependency Graph — builds and queries dependency relationships.

This module builds a graph representing imports and dependencies
between files in a project. The graph is queryable to answer questions
like:
- What files does X import?
- What files import X?
- What files will be affected by changing X?
"""

import os
import fnmatch
import re
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field

from core.logger import setup_logger

logger = setup_logger(__name__)

_SKIP_DIRS = {
    "__pycache__", ".git", "node_modules", ".venv", "venv", "env",
    "build", "dist", ".mypy_cache", ".pytest_cache", ".tox",
    ".next", ".nuxt", "vendor", "target", "versions history",
}


@dataclass
class DependencyNode:
    """Represents a file in the dependency graph."""
    path: str
    imports: List[str] = field(default_factory=list)
    imported_by: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, object]:
        return {
            "path": self.path,
            "imports": self.imports,
            "imported_by": self.imported_by,
        }


@dataclass
class DependencyEdge:
    """Represents a dependency relationship between two files."""
    from_file: str
    to_file: str
    dependency_type: str = "import"  # import, extends, implements, call
    
    def to_dict(self) -> Dict[str, object]:
        return {
            "from_file": self.from_file,
            "to_file": self.to_file,
            "dependency_type": self.dependency_type,
        }


class DependencyGraph:
    """
    Builds and manages a dependency graph for a project.
    
    The graph is built by scanning import statements in source files.
    It supports queries like:
    - get_dependencies(path): What does this file import?
    - get_dependents(path): What files import this file?
    - get_impact(path): What files will be affected by changing this file?
    
    The graph is stored in memory and rebuilt when files change.
    """
    
    def __init__(self):
        self.nodes: Dict[str, DependencyNode] = {}
        self.edges: List[DependencyEdge] = []
        
    def build(self, project_path: str | Path, file_patterns: List[str] = None):
        """
        Build the dependency graph for a project.
        
        Args:
            project_path: Path to the project root
            file_patterns: File patterns to include (default: common source patterns)
        """
        project_path = Path(project_path).resolve()
        
        if file_patterns is None:
            file_patterns = [
                "*.py", "*.js", "*.ts", "*.jsx", "*.tsx",
                "*.java", "*.c", "*.cpp", "*.h", "*.hpp",
                "*.go", "*.rs", "*.php", "*.rb",
            ]
            
        logger.info(f"Building dependency graph for: {project_path}")
        
        # Reset graph
        self.nodes = {}
        self.edges = []
        
        # Find all source files
        source_files = self._find_source_files(project_path, file_patterns)
        logger.info(f"Found {len(source_files)} source files")
        
        # Build all nodes first. Reverse links are rebuilt in a second pass so
        # dependency results do not depend on filesystem traversal order.
        for file_path in source_files:
            self._process_file(file_path, project_path)

        for node in self.nodes.values():
            node.imported_by.clear()
        for edge in self.edges:
            target = self.nodes.get(edge.to_file)
            if target and edge.from_file not in target.imported_by:
                target.imported_by.append(edge.from_file)
            
        logger.info(f"Dependency graph built: {len(self.nodes)} nodes, {len(self.edges)} edges")
        
    def _find_source_files(self, project_path: Path, patterns: List[str]) -> List[Path]:
        """Find all source files matching patterns using pruned os.walk."""
        source_files = []
        if not project_path.is_dir():
            return source_files
        try:
            for root, dirs, files in os.walk(project_path, topdown=True):
                dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")]
                root_p = Path(root)
                for fname in files:
                    if any(fnmatch.fnmatch(fname, pat) for pat in patterns):
                        fpath = root_p / fname
                        if fpath.is_file():
                            source_files.append(fpath)
        except Exception as e:
            logger.warning(f"Error finding source files in {project_path}: {e}")
        return source_files
        
    def _process_file(self, file_path: Path, project_path: Path):
        """Process a single file to extract dependencies."""
        relative_path = file_path.relative_to(project_path).as_posix()
        
        # Create node
        node = DependencyNode(path=relative_path)
        
        # Parse imports based on file type
        imports = self._parse_imports(file_path, project_path)
        
        node.imports = imports
        self.nodes[relative_path] = node
        
        # Create edges
        for imp in imports:
            self.edges.append(DependencyEdge(
                from_file=relative_path,
                to_file=imp,
                dependency_type="import"
            ))
            # Reverse links are populated after every node has been parsed.
                
    def _parse_imports(self, file_path: Path, project_path: Path) -> List[str]:
        """Parse import statements from a file."""
        imports = []
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            ext = file_path.suffix.lower()
            
            # Python imports
            if ext == '.py':
                imports.extend(self._parse_python_imports(content, file_path, project_path))
                
            # JavaScript/TypeScript imports
            elif ext in ['.js', '.ts', '.jsx', '.tsx']:
                imports.extend(self._parse_js_imports(content, file_path, project_path))
                
            # Java imports
            elif ext == '.java':
                imports.extend(self._parse_java_imports(content, file_path, project_path))
                
            # C/C++ imports
            elif ext in ['.c', '.cpp', '.h', '.hpp']:
                imports.extend(self._parse_c_imports(content, file_path, project_path))
                
            # Go imports
            elif ext == '.go':
                imports.extend(self._parse_go_imports(content, file_path, project_path))
                
            # Rust imports
            elif ext == '.rs':
                imports.extend(self._parse_rust_imports(content, file_path, project_path))
                
            # PHP imports
            elif ext == '.php':
                imports.extend(self._parse_php_imports(content, file_path, project_path))
                
            # Ruby imports
            elif ext == '.rb':
                imports.extend(self._parse_ruby_imports(content, file_path, project_path))
                
        except Exception as e:
            logger.warning(f"Error parsing imports from {file_path}: {e}")
            
        return imports
        
    def _parse_python_imports(self, content: str, file_path: Path, project_path: Path) -> List[str]:
        """Parse Python import statements."""
        imports = []
        
        # Match: import x, from x import y, import x.y.z
        patterns = [
            r'^import\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'^from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import',
        ]
        
        for line in content.split('\n'):
            line = line.strip()
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    module = match.group(1)
                    # Try to resolve to relative path
                    resolved = self._resolve_python_module(module, file_path, project_path)
                    if resolved:
                        imports.append(resolved)
                        
        return imports
    
    def _resolve_python_module(self, module: str, file_path: Path, project_path: Path) -> Optional[str]:
        """Resolve a Python module name to a file path."""
        # Convert module path to file path
        parts = module.split('.')
        rel_dir = project_path / Path(*parts)
        
        # Check for module.py
        if (rel_dir.with_suffix('.py')).exists():
            return rel_dir.with_suffix('.py').relative_to(project_path).as_posix()
            
        # Check for module/__init__.py
        if (rel_dir / '__init__.py').exists():
            return (rel_dir / '__init__.py').relative_to(project_path).as_posix()
            
        return None
    
    def _parse_js_imports(self, content: str, file_path: Path, project_path: Path) -> List[str]:
        """Parse JavaScript/TypeScript import statements."""
        imports = []
        
        # Match: import x from 'y', import { x } from 'y', require('y')
        patterns = [
            r"import\s+(?:.*?\s+from\s+)?['\"]([^'\"]+)['\"]",
            r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
            r"import\s+type\s+.*?\s+from\s+['\"]([^'\"]+)['\"]",
        ]
        
        for line in content.split('\n'):
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    module = match.group(1)
                    resolved = self._resolve_js_module(module, file_path, project_path)
                    if resolved:
                        imports.append(resolved)
                        
        return imports
    
    def _resolve_js_module(self, module: str, file_path: Path, project_path: Path) -> Optional[str]:
        """Resolve a JavaScript module to a file path."""
        # Get the directory of the current file
        file_dir = file_path.parent
        
        # Check if module is relative
        if module.startswith('.'):
            resolved = (file_dir / module).resolve()
            if resolved.exists():
                return resolved.relative_to(project_path).as_posix()
                
        # Non-relative imports are harder to resolve
        # Try to find in common locations
        possible_paths = [
            file_dir / module,
            file_dir / f"{module}.js",
            file_dir / f"{module}.ts",
            file_dir / f"{module}.jsx",
            file_dir / f"{module}.tsx",
        ]
        
        for path in possible_paths:
            if path.exists():
                try:
                    return path.relative_to(project_path).as_posix()
                except ValueError:
                    # Path is not under project_path
                    pass
                    
        return None
    
    def _parse_java_imports(self, content: str, file_path: Path, project_path: Path) -> List[str]:
        """Parse Java import statements."""
        imports = []
        
        # Match: import package.Class;
        pattern = r'^import\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s*;'
        
        for line in content.split('\n'):
            line = line.strip()
            match = re.match(pattern, line)
            if match:
                module = match.group(1)
                # Convert to file path
                file_path_str = module.replace('.', '/') + '.java'
                resolved = project_path / file_path_str
                if resolved.exists():
                    imports.append(resolved.relative_to(project_path).as_posix())
                    
        return imports
    
    def _parse_c_imports(self, content: str, file_path: Path, project_path: Path) -> List[str]:
        """Parse C/C++ include statements."""
        imports = []
        
        # Match: #include <file> or #include "file"
        pattern = r'#include\s*[<"]([^>"]+)[>"]'
        
        for line in content.split('\n'):
            match = re.search(pattern, line)
            if match:
                header = match.group(1)
                # Try to resolve header file
                # For now, just return the header name
                # In a real implementation, this would search include paths
                imports.append(header)
                
        return imports
    
    def _parse_go_imports(self, content: str, file_path: Path, project_path: Path) -> List[str]:
        """Parse Go import statements."""
        imports = []
        
        # Match: import "path" or import ( ... )
        pattern = r'import\s+["\']([^"\']+)["\']'
        
        for line in content.split('\n'):
            match = re.search(pattern, line)
            if match:
                module = match.group(1)
                imports.append(module)
                
        return imports
    
    def _parse_rust_imports(self, content: str, file_path: Path, project_path: Path) -> List[str]:
        """Parse Rust import (use) statements."""
        imports = []
        
        # Match: use path::module;
        pattern = r'^use\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        
        for line in content.split('\n'):
            line = line.strip()
            match = re.match(pattern, line)
            if match:
                module = match.group(1)
                imports.append(module)
                
        return imports
    
    def _parse_php_imports(self, content: str, file_path: Path, project_path: Path) -> List[str]:
        """Parse PHP import statements."""
        imports = []
        
        # Match: use Namespace\Class;
        pattern = r'^use\s+([a-zA-Z_][a-zA-Z0-9_\\]*)'
        
        for line in content.split('\n'):
            line = line.strip()
            match = re.match(pattern, line)
            if match:
                module = match.group(1)
                imports.append(module)
                
        return imports
    
    def _parse_ruby_imports(self, content: str, file_path: Path, project_path: Path) -> List[str]:
        """Parse Ruby require statements."""
        imports = []
        
        # Match: require 'file' or require_relative 'file'
        pattern = r"require(?:_relative)?\s+['\"]([^'\"]+)['\"]"
        
        for line in content.split('\n'):
            match = re.search(pattern, line)
            if match:
                module = match.group(1)
                imports.append(module)
                
        return imports
    
    def get_dependencies(self, path: str) -> List[str]:
        """Get files that the given file depends on."""
        node = self.nodes.get(path)
        if node:
            return node.imports
        return []
    
    def get_dependents(self, path: str) -> List[str]:
        """Get files that depend on the given file."""
        node = self.nodes.get(path)
        if node:
            return node.imported_by
        return []
    
    def get_impact(self, path: str, include_transitive: bool = True) -> List[str]:
        """
        Get all files affected by changing the given file.
        
        Args:
            path: The file path to analyze
            include_transitive: Whether to include transitive dependencies
            
        Returns:
            List of affected file paths
        """
        affected = set()
        
        # Direct dependents
        dependents = self.get_dependents(path)
        affected.update(dependents)
        
        if include_transitive:
            # Recursively find transitive dependents
            to_process = list(dependents)
            processed = set()
            
            while to_process:
                current = to_process.pop(0)
                if current in processed:
                    continue
                processed.add(current)
                
                # Find files that depend on this one
                transitive = self.get_dependents(current)
                for t in transitive:
                    if t not in processed:
                        to_process.append(t)
                        affected.add(t)
                        
        return sorted(affected)

    def analyze_file_dependencies(self, path: str) -> Dict[str, object]:
        """Return dependency and impact information for one project file."""
        normalized = str(Path(path).as_posix())
        return {
            "path": normalized,
            "dependencies": sorted(self.get_dependencies(normalized)),
            "dependents": sorted(self.get_dependents(normalized)),
            "impact": self.get_impact(normalized, include_transitive=True),
            "cycles": [cycle for cycle in self.get_cycle_paths()
                       if normalized in cycle],
        }

    def get_impact_report(self, paths: List[str]) -> Dict[str, object]:
        """Summarize the files affected by a proposed multi-file change."""
        normalized = sorted({str(Path(path).as_posix()) for path in paths})
        affected = sorted({item for path in normalized
                           for item in self.get_impact(path)})
        return {
            "changed_files": normalized,
            "affected_files": affected,
            "affected_count": len(affected),
            "cycles": [cycle for cycle in self.get_cycle_paths()
                       if any(node in normalized for node in cycle)],
        }
    
    def get_cycle_paths(self) -> List[List[str]]:
        """Detect and return paths with circular dependencies."""
        cycles = []
        
        def dfs(node: str, visited: Set[str], path: List[str]) -> bool:
            if node in path:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return True
                
            if node in visited:
                return False
                
            visited.add(node)
            path.append(node)
            
            # Visit all dependencies
            for dep in self.nodes.get(node, DependencyNode(path="")).imports:
                if dep in self.nodes:
                    dfs(dep, visited, path)
                    
            path.pop()
            return False
            
        for node in self.nodes:
            dfs(node, set(), [])
            
        return cycles
    
    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-serializable representation of the graph."""
        return {
            "nodes": {
                path: node.to_dict()
                for path, node in self.nodes.items()
            },
            "edges": [edge.to_dict() for edge in self.edges],
            "summary": {
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
            },
        }

# ============================================================================
# SECTION: ai.intelligence.language_statistics (ai/intelligence/language_statistics.py)
# ============================================================================
"""
Language Statistics — calculates language breakdown for a project.

This module analyzes a project and calculates:
- Percentage of code per language
- Total lines of code per language
- File counts per language

This is used for:
- Project overview
- Resource allocation
- Language-specific optimizations
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from core.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class LanguageStats:
    """Statistics for a single language."""
    language: str
    file_count: int = 0
    line_count: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    percentage: float = 0.0
    
    def to_dict(self) -> Dict[str, object]:
        return {
            "language": self.language,
            "file_count": self.file_count,
            "line_count": self.line_count,
            "code_lines": self.code_lines,
            "comment_lines": self.comment_lines,
            "blank_lines": self.blank_lines,
            "percentage": self.percentage,
        }


class LanguageStatistics:
    """
    Calculates language statistics for a project.
    
    This class analyzes all source files in a project and calculates
    statistics for each programming language.
    """
    
    # Mapping of extensions to language names
    EXTENSION_MAP: Dict[str, str] = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.jsx': 'JavaScript',
        '.tsx': 'TypeScript',
        '.java': 'Java',
        '.c': 'C',
        '.cpp': 'C++',
        '.h': 'C',
        '.hpp': 'C++',
        '.go': 'Go',
        '.rs': 'Rust',
        '.php': 'PHP',
        '.rb': 'Ruby',
        '.cs': 'C#',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.scala': 'Scala',
        '.tsv': 'TSQL',
        '.pl': 'Perl',
        '.pm': 'Perl',
        '.r': 'R',
        '.R': 'R',
        '.m': 'Objective-C',
        '.mm': 'Objective-C',
        '.sh': 'Bash',
        '.bash': 'Bash',
        '.zsh': 'Zsh',
        '.fish': 'Fish',
        '.ps1': 'PowerShell',
        '.cmd': 'Batch',
        '.bat': 'Batch',
        '.html': 'HTML',
        '.htm': 'HTML',
        '.css': 'CSS',
        '.scss': 'SCSS',
        '.sass': 'Sass',
        '.less': 'Less',
        '.json': 'JSON',
        '.xml': 'XML',
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.md': 'Markdown',
        '.rst': 'reStructuredText',
        '.txt': 'Text',
        '.sql': 'SQL',
        '.graphql': 'GraphQL',
        '.proto': 'Protocol Buffers',
    }
    
    # Comment patterns for different languages
    COMMENT_PATTERNS: Dict[str, Tuple[str, str]] = {
        'Python': ('#', None),
        'JavaScript': ('//', '/* */'),
        'TypeScript': ('//', '/* */'),
        'Java': ('//', '/* */'),
        'C': ('//', '/* */'),
        'C++': ('//', '/* */'),
        'Go': ('//', '/* */'),
        'Rust': ('//', '/* */'),
        'PHP': ('//', '/* */'),
        'Ruby': ('#', None),
        'C#': ('//', '/* */'),
        'Swift': ('//', '/* */'),
        'Kotlin': ('//', '/* */'),
        'Scala': ('//', '/* */'),
        'Bash': ('#', None),
        'Zsh': ('#', None),
        'Fish': ('#', None),
        'PowerShell': ('#', None),
        'Batch': ('REM', None),
        'SQL': ('--', None),
    }
    
    # Blank line patterns
    BLANK_PATTERNS = ['', ' ', '\t']
    
    def __init__(self, project_path: str | Path):
        self.project_path = Path(project_path).resolve()
        self.language_stats: Dict[str, LanguageStats] = {}
        self.total_lines = 0
        self.total_files = 0
        
    def calculate(self) -> Dict[str, LanguageStats]:
        """
        Calculate language statistics for the project.
        
        Returns:
            Dictionary mapping language names to LanguageStats
        """
        logger.info(f"Calculating language statistics for: {self.project_path}")
        
        # Reset stats
        self.language_stats = {}
        self.total_lines = 0
        self.total_files = 0
        
        # Find all source files
        patterns = [
            "*.py", "*.js", "*.ts", "*.jsx", "*.tsx",
            "*.java", "*.c", "*.cpp", "*.h", "*.hpp",
            "*.go", "*.rs", "*.php", "*.rb", "*.cs",
            "*.swift", "*.kt", "*.scala",
            "*.sh", "*.bash", "*.zsh", "*.fish",
            "*.ps1", "*.cmd", "*.bat",
            "*.html", "*.css", "*.scss", "*.less",
            "*.json", "*.xml", "*.yaml", "*.yml",
            "*.md", "*.rst", "*.sql", "*.graphql",
            "*.proto",
        ]
        
        # Process each file
        for pattern in patterns:
            for file_path in self.project_path.rglob(pattern):
                self._process_file(file_path)
                
        # Calculate percentages
        self._calculate_percentages()
        
        logger.info(f"Language statistics calculated: {len(self.language_stats)} languages")
        
        return self.language_stats
    
    def _process_file(self, file_path: Path):
        """Process a single file to calculate language statistics."""
        ext = file_path.suffix.lower()
        language = self.EXTENSION_MAP.get(ext, "Unknown")
        
        # Initialize language stats if not exists
        if language not in self.language_stats:
            self.language_stats[language] = LanguageStats(language=language)
            
        stats = self.language_stats[language]
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            
            stats.file_count += 1
            stats.line_count += len(lines)
            self.total_lines += len(lines)
            self.total_files += 1
            
            # Analyze lines
            for line in lines:
                stripped = line.strip()
                
                if not stripped:
                    stats.blank_lines += 1
                elif self._is_comment(stripped, language):
                    stats.comment_lines += 1
                else:
                    stats.code_lines += 1
                    
        except Exception as e:
            logger.warning(f"Error processing file {file_path}: {e}")
            
    def _is_comment(self, line: str, language: str) -> bool:
        """Check if a line is a comment."""
        comment_start, comment_block = self.COMMENT_PATTERNS.get(language, ('#', None))
        
        if line.startswith(comment_start):
            return True
            
        if comment_block:
            if line.startswith(comment_block.split()[0]):
                return True
                
        return False
    
    def _calculate_percentages(self):
        """Calculate percentage for each language."""
        if self.total_lines == 0:
            return
            
        for stats in self.language_stats.values():
            stats.percentage = round((stats.line_count / self.total_lines) * 100, 2)
            
    def get_primary_language(self) -> Optional[str]:
        """Get the primary (most used) language."""
        if not self.language_stats:
            return None
            
        return max(self.language_stats.keys(), key=lambda x: self.language_stats[x].line_count)
    
    def get_language_percentages(self) -> Dict[str, float]:
        """Get language percentages as a dictionary."""
        return {lang: stats.percentage for lang, stats in self.language_stats.items()}
    
    def get_top_languages(self, limit: int = 5) -> List[Tuple[str, LanguageStats]]:
        """Get top N languages by line count."""
        sorted_langs = sorted(
            self.language_stats.items(),
            key=lambda x: x[1].line_count,
            reverse=True
        )
        return sorted_langs[:limit]
    
    def get_total_stats(self) -> Dict[str, int]:
        """Get total statistics."""
        return {
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "total_languages": len(self.language_stats),
        }
    
    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-serializable representation."""
        return {
            "project_path": str(self.project_path),
            "languages": {
                lang: stats.to_dict()
                for lang, stats in self.language_stats.items()
            },
            "total_lines": self.total_lines,
            "total_files": self.total_files,
            "primary_language": self.get_primary_language(),
        }

# ============================================================================
# SECTION: ai.intelligence.entry_point_detector (ai/intelligence/entry_point_detector.py)
# ============================================================================
"""
Entry Point Detector — automatically detects application entry points.

This module detects common entry point files for different frameworks
and technologies:
- Python: main.py, app.py, run.py, server.py
- JavaScript: index.js, server.js, app.js
- React/Next.js: index.tsx, app.tsx
- Flutter: main.dart
- Android: MainActivity.java, MainApplication.java
- iOS: main.m, AppDelegate.m
- C/C++: main.c, main.cpp, WinMain.c
- Java: Main.java
- C#: Program.cs
- Go: main.go
- Rust: main.rs
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from core.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class EntryPoint:
    """Represents a detected entry point."""
    path: str
    language: str
    framework: Optional[str] = None
    confidence: float = 0.0
    entry_type: str = "application"  # application, library, test, cli
    main_function: Optional[str] = None
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, object]:
        return {
            "path": self.path,
            "language": self.language,
            "framework": self.framework,
            "confidence": self.confidence,
            "entry_type": self.entry_type,
            "main_function": self.main_function,
            "description": self.description,
        }


class EntryPointDetector:
    """
    Detects entry points for different frameworks and technologies.
    
    This detector scans for common entry point patterns and analyzes
    the content to confirm and provide additional information about
    the entry point.
    """
    
    # Entry point patterns by language/framework
    ENTRY_PATTERNS: Dict[str, List[Dict]] = {
        "python": [
            {
                "files": ["main.py", "app.py", "run.py", "server.py", "wsgi.py"],
                "function_patterns": ["def main", "app = Flask", "app = FastAPI", "app = Django", "async def main"],
                "confidence": 0.9,
                "entry_type": "application",
            },
            {
                "files": ["__main__.py"],
                "function_patterns": ["if __name__ == '__main__'"],
                "confidence": 0.8,
                "entry_type": "application",
            },
            {
                "files": ["cli.py", "command.py"],
                "function_patterns": ["def main", "argparse", "click"],
                "confidence": 0.7,
                "entry_type": "cli",
            },
            {
                "files": ["test_*.py", "*_test.py"],
                "function_patterns": ["def test_", "pytest", "unittest"],
                "confidence": 0.5,
                "entry_type": "test",
            },
        ],
        "javascript": [
            {
                "files": ["index.js", "app.js", "server.js", "main.js"],
                "function_patterns": ["app.listen", "server.listen", "export default", "module.exports"],
                "confidence": 0.9,
                "entry_type": "application",
            },
            {
                "files": ["index.ts", "app.ts", "main.ts"],
                "function_patterns": ["app.listen", "server.listen", "export default", "module.exports"],
                "confidence": 0.8,
                "entry_type": "application",
            },
            {
                "files": ["test.js", "test.ts", "spec.js", "spec.ts"],
                "function_patterns": ["describe(", "it(", "test(", "jest"],
                "confidence": 0.7,
                "entry_type": "test",
            },
        ],
        "typescript": [
            {
                "files": ["index.ts", "app.ts", "main.ts"],
                "function_patterns": ["app.listen", "server.listen", "export default", "module.exports"],
                "confidence": 0.9,
                "entry_type": "application",
            },
        ],
        "react": [
            {
                "files": ["index.tsx", "app.tsx"],
                "function_patterns": ["ReactDOM.render", "createRoot", "export default"],
                "confidence": 0.9,
                "entry_type": "application",
            },
        ],
        "flutter": [
            {
                "files": ["main.dart"],
                "function_patterns": ["void main()", "runApp"],
                "confidence": 0.95,
                "entry_type": "application",
            },
        ],
        "android": [
            {
                "files": ["MainActivity.java", "MainActivity.kt"],
                "function_patterns": ["onCreate", "extends Activity", "class MainActivity"],
                "confidence": 0.8,
                "entry_type": "application",
            },
        ],
        "ios": [
            {
                "files": ["main.m", "main.swift"],
                "function_patterns": ["int main", "UIApplicationMain", "@main"],
                "confidence": 0.85,
                "entry_type": "application",
            },
        ],
        "c": [
            {
                "files": ["main.c"],
                "function_patterns": ["int main", "void main"],
                "confidence": 0.95,
                "entry_type": "application",
            },
        ],
        "cpp": [
            {
                "files": ["main.cpp", "WinMain.cpp"],
                "function_patterns": ["int main", "int WinMain"],
                "confidence": 0.95,
                "entry_type": "application",
            },
        ],
        "java": [
            {
                "files": ["Main.java"],
                "function_patterns": ["public static void main", "public static void main\\(String\\[\\]"],
                "confidence": 0.9,
                "entry_type": "application",
            },
        ],
        "csharp": [
            {
                "files": ["Program.cs"],
                "function_patterns": ["static void Main", "async Task Main", "var builder = WebApplication"],
                "confidence": 0.9,
                "entry_type": "application",
            },
        ],
        "go": [
            {
                "files": ["main.go"],
                "function_patterns": ["func main\\(\\)", "package main"],
                "confidence": 0.95,
                "entry_type": "application",
            },
        ],
        "rust": [
            {
                "files": ["main.rs"],
                "function_patterns": ["fn main\\(\\)", "#\\[tokio::main\\]"],
                "confidence": 0.95,
                "entry_type": "application",
            },
        ],
    }
    
    # Framework detection patterns
    FRAMEWORK_PATTERNS: Dict[str, List[Tuple[str, str]]] = {
        "flask": [
            ("*.py", "Flask\\("),
            ("*.py", "from flask import"),
        ],
        "django": [
            ("*.py", "from django"),
            ("*.py", "import django"),
            ("settings.py", None),
        ],
        "fastapi": [
            ("*.py", "FastAPI\\("),
            ("*.py", "from fastapi"),
        ],
        "express": [
            ("*.js", "express\\("),
            ("*.js", "const express ="),
        ],
        "next": [
            ("*.js", "next\\("),
            ("next.config.js", None),
        ],
        "react": [
            ("*.tsx", "React.createElement"),
            ("*.tsx", "import React"),
        ],
        "spring": [
            ("*.java", "@SpringBootApplication"),
            ("pom.xml", None),
        ],
        "fastapi": [
            ("*.py", "FastAPI\\("),
            ("*.py", "uvicorn.run"),
        ],
    }
    
    def __init__(self, project_path: str | Path):
        self.project_path = Path(project_path).resolve()
        self.detected_entries: List[EntryPoint] = []
        
    def detect(self) -> List[EntryPoint]:
        """
        Detect all entry points in the project.
        
        Returns:
            List of EntryPoint objects
        """
        logger.info(f"Detecting entry points for: {self.project_path}")
        
        # Reset entries
        self.detected_entries = []
        
        # Check all languages
        for language, patterns in self.ENTRY_PATTERNS.items():
            self._detect_language_entries(language, patterns)
            
        # Detect framework-specific entries
        self._detect_framework_entries()
        
        # Sort by confidence
        self.detected_entries.sort(key=lambda x: x.confidence, reverse=True)
        
        logger.info(f"Detected {len(self.detected_entries)} entry points")
        
        return self.detected_entries
    
    def _detect_language_entries(self, language: str, patterns: List[Dict]):
        """Detect entry points for a specific language."""
        for pattern in patterns:
            for file_pattern in pattern["files"]:
                for file_path in self.project_path.rglob(file_pattern):
                    entry = self._analyze_entry(file_path, language, pattern)
                    if entry:
                        self.detected_entries.append(entry)
                        
    def _analyze_entry(self, file_path: Path, language: str, pattern: Dict) -> Optional[EntryPoint]:
        """Analyze a file to confirm it's an entry point."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Check if any function pattern matches
            main_function = None
            for func_pattern in pattern["function_patterns"]:
                if re.search(func_pattern, content):
                    # Extract function name
                    match = re.search(r'(?:def|fun|func)\s+(\w+)\s*\(', content)
                    if match:
                        main_function = match.group(1)
                    break
                    
            # Determine entry type
            entry_type = pattern.get("entry_type", "application")
            
            # Detect framework
            framework = self._detect_framework_for_file(file_path)
            
            # Build description
            description = f"Entry point for {language} {entry_type} application"
            if framework:
                description += f" using {framework}"
                
            return EntryPoint(
                path=str(file_path.relative_to(self.project_path)),
                language=language,
                framework=framework,
                confidence=pattern["confidence"],
                entry_type=entry_type,
                main_function=main_function,
                description=description,
            )
            
        except Exception as e:
            logger.warning(f"Error analyzing {file_path}: {e}")
            return None
    
    def _detect_framework_for_file(self, file_path: Path) -> Optional[str]:
        """Detect framework for a specific file."""
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        for framework, patterns in self.FRAMEWORK_PATTERNS.items():
            for pattern_file, pattern_text in patterns:
                if pattern_file == "*" or file_path.name == pattern_file:
                    if pattern_text is None or re.search(pattern_text, content):
                        return framework
                        
        return None
    
    def _detect_framework_entries(self):
        """Detect framework-specific entry points."""
        # Check for common framework entry points
        framework_patterns = {
            "next": "app/page.tsx",
            "svelte": "src/main.js",
            "vue": "src/main.js",
            "angular": "src/main.ts",
        }
        
        for framework, entry_file in framework_patterns.items():
            entry_path = self.project_path / entry_file
            if entry_path.exists():
                entry = EntryPoint(
                    path=entry_file,
                    language=self._detect_language_for_file(entry_path),
                    framework=framework,
                    confidence=0.9,
                    entry_type="application",
                    description=f"Entry point for {framework} application",
                )
                self.detected_entries.append(entry)
                
    def _detect_language_for_file(self, file_path: Path) -> str:
        """Detect language for a file."""
        ext = file_path.suffix.lower()
        extension_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript',
            '.java': 'Java',
            '.kt': 'Kotlin',
            '.go': 'Go',
            '.rs': 'Rust',
        }
        return extension_map.get(ext, "Unknown")
    
    def get_primary_entry_point(self) -> Optional[EntryPoint]:
        """Get the primary (highest confidence) entry point."""
        if not self.detected_entries:
            return None
        return self.detected_entries[0]
    
    def get_entry_points_by_type(self, entry_type: str) -> List[EntryPoint]:
        """Get entry points of a specific type."""
        return [e for e in self.detected_entries if e.entry_type == entry_type]
    
    def get_entry_points_by_framework(self, framework: str) -> List[EntryPoint]:
        """Get entry points for a specific framework."""
        return [e for e in self.detected_entries if e.framework == framework]
    
    def get_entry_points_by_language(self, language: str) -> List[EntryPoint]:
        """Get entry points for a specific language."""
        return [e for e in self.detected_entries if e.language == language]
    
    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-serializable representation."""
        return {
            "project_path": str(self.project_path),
            "entry_points": [e.to_dict() for e in self.detected_entries],
            "primary_entry_point": self.get_primary_entry_point().to_dict() if self.get_primary_entry_point() else None,
        }

# ============================================================================
# SECTION: ai.intelligence.architecture_detector (ai/intelligence/architecture_detector.py)
# ============================================================================
"""
Architecture Detector — identifies project architecture patterns.

This analyzer examines the project structure, file organization,
and code patterns to determine the architectural design pattern
used by the project.

Return values:
- Clean Architecture
- MVC (Model-View-Controller)
- MVVM (Model-View-ViewModel)
- Feature First
- Layered (Three-tier)
- Hexagonal (Ports and Adapters)
- Event-Driven
- Microservices
- Unknown
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

from core.logger import setup_logger

logger = setup_logger(__name__)


class ArchitectureResult:
    """Result from architecture detection."""
    
    def __init__(self, architecture: str, confidence: float, evidence: List[str] = None):
        self.architecture = architecture
        self.confidence = confidence
        self.evidence = evidence or []
        
    def to_dict(self) -> Dict[str, object]:
        return {
            "architecture": self.architecture,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


class ArchitectureDetector:
    """
    Detects the architectural pattern of a project.
    
    This analyzer examines:
    - Folder structure and organization
    - File naming conventions
    - Import patterns
    - Configuration files
    - Framework-specific patterns
    
    Return a confidence score between 0.0 and 1.0.
    """
    
    def __init__(self):
        self._detection_rules = self._build_detection_rules()
        
    def _build_detection_rules(self) -> List[Dict]:
        """Build detection rules for different architectures."""
        return [
            {
                "name": "Clean Architecture",
                "folders": ["domain", "application", "infrastructure", "presentation"],
                "patterns": ["core/", "src/core/", "app/core/"],
                "confidence_weights": {"folders": 0.5, "patterns": 0.5},
            },
            {
                "name": "MVC",
                "folders": ["models", "views", "controllers", "controller"],
                "patterns": ["Controller.cs", "Controller.php", "controller.py"],
                "confidence_weights": {"folders": 0.4, "patterns": 0.6},
            },
            {
                "name": "MVVM",
                "folders": ["models", "views", "viewmodels", "view-models"],
                "patterns": ["ViewModel.cs", "ViewModel.ts", "view-model.ts"],
                "confidence_weights": {"folders": 0.4, "patterns": 0.6},
            },
            {
                "name": "Feature First",
                "folders": ["features", "modules", "features/"],
                "patterns": ["feature/", "module/"],
                "confidence_weights": {"folders": 0.6, "patterns": 0.4},
            },
            {
                "name": "Layered",
                "folders": ["layers", "layers/", "tier", "tier/"],
                "patterns": ["layer", "tier"],
                "confidence_weights": {"folders": 0.5, "patterns": 0.5},
            },
            {
                "name": "Hexagonal",
                "folders": ["ports", "adapters", "ports/", "adapters/"],
                "patterns": ["port", "adapter"],
                "confidence_weights": {"folders": 0.5, "patterns": 0.5},
            },
            {
                "name": "Event-Driven",
                "folders": ["events", "handlers", "events/", "handlers/"],
                "patterns": ["Event", "EventHandler", "EventListener"],
                "confidence_weights": {"folders": 0.4, "patterns": 0.6},
            },
            {
                "name": "Microservices",
                "folders": ["services", "microservices", "services/", "microservices/"],
                "patterns": ["service", "microservice"],
                "confidence_weights": {"folders": 0.5, "patterns": 0.5},
            },
        ]
        
    def detect(self, project_path: str | Path) -> Optional[ArchitectureResult]:
        """
        Detect the architecture pattern of a project.
        
        Args:
            project_path: Path to the project root
            
        Returns:
            ArchitectureResult with architecture name, confidence, and evidence
        """
        project_path = Path(project_path).resolve()
        
        if not project_path.exists():
            logger.error(f"Project path does not exist: {project_path}")
            return None
            
        logger.info(f"Detecting architecture for: {project_path}")
        
        # Collect evidence
        evidence = []
        scores = {}
        
        # Check folder structure
        folders = self._get_directories(project_path)
        
        # Check for config files that indicate frameworks
        config_files = self._find_config_files(project_path)
        
        # Check for architecture-specific patterns in code
        code_patterns = self._analyze_code_patterns(project_path)
        
        # Score each architecture
        for rule in self._detection_rules:
            rule_name = rule["name"]
            folder_score = self._score_folders(rule["folders"], folders)
            pattern_score = self._score_patterns(rule["patterns"], code_patterns)
            
            # Calculate weighted score
            weights = rule["confidence_weights"]
            total_score = (folder_score * weights["folders"] + 
                          pattern_score * weights["patterns"])
            
            scores[rule_name] = total_score
            
            if total_score > 0.3:
                rule_evidence = []
                if folder_score > 0:
                    rule_evidence.append(f"Found {folder_score:.0%} of expected folders")
                if pattern_score > 0:
                    rule_evidence.append(f"Found {pattern_score:.0%} of expected patterns")
                scores[rule_name] = max(scores[rule_name], 0.3)
                
        # Find best match
        if not scores:
            return ArchitectureResult("Unknown", 0.0, ["No patterns detected"])
            
        best_architecture = max(scores.keys(), key=lambda x: scores[x])
        best_score = scores[best_architecture]
        
        # Build evidence list
        for rule in self._detection_rules:
            if rule["name"] == best_architecture:
                evidence = rule.get("evidence", [])
                break
                
        if best_score < 0.4:
            evidence.append("Low confidence - architecture may be Unknown")
            
        logger.info(f"Detected architecture: {best_architecture} (confidence: {best_score:.0%})")
        
        return ArchitectureResult(best_architecture, best_score, evidence)
    
    def _get_directories(self, project_path: Path) -> List[str]:
        """Get list of directory names at project root."""
        directories = []
        try:
            for item in project_path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    directories.append(item.name.lower())
        except Exception as e:
            logger.error(f"Failed to read directories: {e}")
        return directories
    
    def _find_config_files(self, project_path: Path) -> List[str]:
        """Find framework config files."""
        config_patterns = {
            "django": ["settings.py", "manage.py"],
            "flask": ["app.py", "wsgi.py"],
            "fastapi": ["main.py", "app.py"],
            "spring": ["pom.xml", "build.gradle"],
            "django": ["models.py", "views.py"],
            "laravel": ["routes/web.php", "app/Http/Controllers"],
            "rails": ["Gemfile", "app/controllers"],
            "nextjs": ["next.config.js", "pages/"],
            "react": ["package.json", "src/"],
            "angular": ["angular.json", "src/app/"],
            "vue": ["vue.config.js", "src/"],
            "node": ["package.json", "server.js"],
        }
        
        found_configs = []
        for framework, patterns in config_patterns.items():
            for pattern in patterns:
                if (project_path / pattern).exists() or any(
                    (project_path / p).exists() for p in [pattern] if '/' not in pattern
                ):
                    found_configs.append(framework)
                    break
                    
        return found_configs
    
    def _analyze_code_patterns(self, project_path: Path) -> List[str]:
        """Analyze code files for architecture patterns."""
        patterns = []
        
        # Pattern files to check
        pattern_files = ["main.py", "app.py", "server.py", "App.java", "Main.cs"]
        
        for pattern_file in pattern_files:
            file_path = project_path / pattern_file
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    
                    # Check for controller patterns
                    if re.search(r'class.*[Cc]ontroller', content):
                        patterns.append("controller")
                        
                    # Check for viewmodel patterns
                    if re.search(r'class.*[Vv]iew[Mm]odel', content):
                        patterns.append("viewmodel")
                        
                    # Check for event patterns
                    if re.search(r'class.*[Ee]vent', content):
                        patterns.append("event")
                        
                    # Check for domain patterns
                    if re.search(r'class.*[Dd]omain', content):
                        patterns.append("domain")
                        
                    # Check for port/adapter patterns
                    if re.search(r'(port|adapter)', content, re.IGNORECASE):
                        patterns.append("hexagonal")
                        
                except Exception as e:
                    logger.debug(f"Could not read {pattern_file}: {e}")
                    
        return patterns
    
    def _score_folders(self, expected_folders: List[str], actual_folders: List[str]) -> float:
        """Score how well expected folders match actual folders."""
        if not expected_folders or not actual_folders:
            return 0.0
            
        matches = sum(1 for folder in expected_folders 
                     if any(folder in actual for actual in actual_folders))
        
        return matches / len(expected_folders)
    
    def _score_patterns(self, expected_patterns: List[str], actual_patterns: List[str]) -> float:
        """Score how well expected patterns match actual patterns."""
        if not expected_patterns or not actual_patterns:
            return 0.0
            
        matches = sum(1 for pattern in expected_patterns 
                     if any(pattern in actual for actual in actual_patterns))
        
        return matches / len(expected_patterns)

# ============================================================================
# SECTION: ai.intelligence.documentation_indexer (ai/intelligence/documentation_indexer.py)
# ============================================================================
"""
Documentation Indexer — automatically indexes project documentation.

This module indexes:
- README files
- Documentation in markdown files
- Code comments (docstrings)
- API documentation
- Architecture notes

The index can be used for:
- Context generation for AI prompts
- Documentation coverage analysis
- Auto-generated API docs
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from core.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class DocumentationEntry:
    """Represents a documentation entry."""
    path: str
    title: str
    content: str
    entry_type: str  # readme, doc, comment, api, architecture
    language: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, object]:
        return {
            "path": self.path,
            "title": self.title,
            "content": self.content,
            "entry_type": self.entry_type,
            "language": self.language,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "tags": self.tags,
        }


class DocumentationIndexer:
    """
    Indexes documentation across a project.
    
    This indexer scans for documentation in multiple formats:
    - README.md files
    - docs/ directory markdown files
    - Code comments (docstrings)
    - Architecture decision records
    """
    
    # README file names
    README_NAMES = [
        "README.md", "README.rst", "README.txt", "README",
        "readme.md", "readme.rst", "readme.txt",
    ]
    
    # Documentation patterns
    DOC_PATTERNS = [
        "docs/**/*.md",
        "docs/**/*.rst",
        "docs/**/*.txt",
        "doc/**/*.md",
        "doc/**/*.rst",
    ]
    
    # Architecture notes patterns
    ARCHITECTURE_NAMES = [
        "ARCHITECTURE.md", "ARCHITECTURE.rst",
        "ADR/**/*.md", "adr/**/*.md",
        "docs/decisions/**/*.md",
    ]
    
    def __init__(self, project_path: str | Path):
        self.project_path = Path(project_path).resolve()
        self.entries: List[DocumentationEntry] = []

    def index(self) -> List[DocumentationEntry]:
        """
        Index all documentation in the project.

        Returns:
            List of DocumentationEntry objects
        """
        logger.info(f"Indexing documentation for: {self.project_path}")

        # Reset index
        self.entries = []
        
        # Index README files
        self._index_readmes()
        
        # Index documentation files
        self._index_docs()
        
        # Index architecture notes
        self._index_architecture()
        
        # Index code comments (optional - can be slow)
        # self._index_comments()
        
        logger.info(f"Indexed {len(self.entries)} documentation entries")

        return self.entries
    
    def _index_readmes(self):
        """Index all README files."""
        for readme_name in self.README_NAMES:
            for readme_path in self.project_path.rglob(readme_name):
                self._index_readme(readme_path)
                
    def _index_readme(self, file_path: Path):
        """Index a single README file."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Extract title (first # heading)
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else file_path.name
            
            # Truncate long content
            truncated_content = self._truncate_content(content)
            
            entry = DocumentationEntry(
                path=str(file_path.relative_to(self.project_path)),
                title=title,
                content=truncated_content,
                entry_type="readme",
                language=self._detect_language_for_file(file_path),
                tags=["readme", "overview"],
            )
            
            self.entries.append(entry)
            
        except Exception as e:
            logger.warning(f"Error indexing README {file_path}: {e}")
    
    def _index_docs(self):
        """Index documentation files in docs directory."""
        for pattern in self.DOC_PATTERNS:
            for doc_path in self.project_path.rglob(pattern):
                # Skip if already indexed as README
                if doc_path.name in self.README_NAMES:
                    continue
                    
                self._index_doc(doc_path)
                
    def _index_doc(self, file_path: Path):
        """Index a single documentation file."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Extract title (first # heading or filename)
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else file_path.stem
            
            # Truncate content
            truncated_content = self._truncate_content(content)
            
            # Determine entry type based on path
            entry_type = "doc"
            if "architecture" in str(file_path).lower():
                entry_type = "architecture"
            elif "api" in str(file_path).lower():
                entry_type = "api"
                
            # Extract tags
            tags = [entry_type]
            if "tutorial" in str(file_path).lower():
                tags.append("tutorial")
            if "guide" in str(file_path).lower():
                tags.append("guide")
                
            entry = DocumentationEntry(
                path=str(file_path.relative_to(self.project_path)),
                title=title,
                content=truncated_content,
                entry_type=entry_type,
                language=self._detect_language_for_file(file_path),
                tags=tags,
            )
            
            self.entries.append(entry)
            
        except Exception as e:
            logger.warning(f"Error indexing doc {file_path}: {e}")
    
    def _index_architecture(self):
        """Index architecture decision records and notes."""
        for arch_name in self.ARCHITECTURE_NAMES:
            if "**" in arch_name:
                # Pattern with subdirectories
                base_dir = arch_name.split("**")[0].rstrip("/")
                for arch_path in self.project_path.rglob(base_dir + "*.md"):
                    self._index_architecture_file(arch_path)
            else:
                # Single file
                arch_path = self.project_path / arch_name
                if arch_path.exists():
                    self._index_architecture_file(arch_path)
                    
    def _index_architecture_file(self, file_path: Path):
        """Index a single architecture file."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Extract title
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else file_path.stem
            
            # Truncate content
            truncated_content = self._truncate_content(content)
            
            entry = DocumentationEntry(
                path=str(file_path.relative_to(self.project_path)),
                title=title,
                content=truncated_content,
                entry_type="architecture",
                language=self._detect_language_for_file(file_path),
                tags=["architecture", "adr"],
            )
            
            self.entries.append(entry)
            
        except Exception as e:
            logger.warning(f"Error indexing architecture {file_path}: {e}")
    
    def _index_comments(self):
        """Index code comments (optional - can be slow)."""
        # This is a simplified implementation
        # A full implementation would parse source files and extract docstrings
        
        patterns = ["*.py", "*.js", "*.ts", "*.java", "*.c", "*.cpp", "*.go", "*.rs", "*.php", "*.rb", "*.cs"]
        
        for pattern in patterns:
            for file_path in self.project_path.rglob(pattern):
                self._index_file_comments(file_path)
                
    def _index_file_comments(self, file_path: Path):
        """Index comments in a single file."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            
            # Detect comment style
            ext = file_path.suffix.lower()
            comment_prefix = self._get_comment_prefix(ext)
            
            for i, line in enumerate(lines, 1):
                if line.strip().startswith(comment_prefix):
                    # Extract comment content
                    comment = line.strip()[len(comment_prefix):].strip()
                    
                    if len(comment) > 10:  # Skip very short comments
                        entry = DocumentationEntry(
                            path=str(file_path.relative_to(self.project_path)),
                            title=f"Line {i}",
                            content=comment,
                            entry_type="comment",
                            language=self._detect_language_for_file(file_path),
                            line_start=i,
                            line_end=i,
                            tags=["comment"],
                        )
                        self.entries.append(entry)
                        
        except Exception as e:
            logger.warning(f"Error indexing comments {file_path}: {e}")
    
    def _get_comment_prefix(self, ext: str) -> str:
        """Get comment prefix for a file extension."""
        prefix_map = {
            '.py': '#',
            '.js': '//',
            '.ts': '//',
            '.java': '//',
            '.c': '//',
            '.cpp': '//',
            '.go': '//',
            '.rs': '//',
            '.php': '//',
            '.rb': '#',
            '.cs': '//',
            '.sh': '#',
            '.bash': '#',
        }
        return prefix_map.get(ext, '#')
    
    def _truncate_content(self, content: str, max_length: int = 5000) -> str:
        """Truncate content to a maximum length."""
        if len(content) <= max_length:
            return content
        return content[:max_length] + f"\n... [truncated, original length: {len(content)} characters]..."
    
    def _detect_language_for_file(self, file_path: Path) -> Optional[str]:
        """Detect language for a file."""
        ext = file_path.suffix.lower()
        extension_map = {
            '.md': 'Markdown',
            '.rst': 'reStructuredText',
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
        }
        return extension_map.get(ext)
    
    def get_readme(self) -> Optional[DocumentationEntry]:
        """Get the main README entry."""
        for entry in self.entries:
            if entry.entry_type == "readme":
                return entry
        return None
    
    def get_architecture_docs(self) -> List[DocumentationEntry]:
        """Get all architecture documentation."""
        return [e for e in self.entries if e.entry_type == "architecture"]
    
    def get_api_docs(self) -> List[DocumentationEntry]:
        """Get all API documentation."""
        return [e for e in self.entries if e.entry_type == "api"]
    
    def get_docs_by_tag(self, tag: str) -> List[DocumentationEntry]:
        """Get documentation entries with a specific tag."""
        return [e for e in self.entries if tag in e.tags]
    
    def search_docs(self, query: str) -> List[DocumentationEntry]:
        """Search documentation for a query."""
        query_lower = query.lower()
        results = []
        
        for entry in self.entries:
            if query_lower in entry.title.lower() or query_lower in entry.content.lower():
                results.append(entry)
                
        return results
    
    def get_coverage_stats(self) -> Dict[str, object]:
        """Get documentation coverage statistics."""
        readme_count = sum(1 for e in self.entries if e.entry_type == "readme")
        architecture_count = sum(1 for e in self.entries if e.entry_type == "architecture")
        doc_count = sum(1 for e in self.entries if e.entry_type == "doc")
        
        return {
            "total_entries": len(self.entries),
            "readmes": readme_count,
            "architecture_docs": architecture_count,
            "general_docs": doc_count,
            "languages": list(set(e.language for e in self.entries if e.language)),
        }
    
    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-serializable representation."""
        return {
            "project_path": str(self.project_path),
            "entries": [e.to_dict() for e in self.entries],
            "coverage": self.get_coverage_stats(),
        }

# ============================================================================
# SECTION: ai.intelligence.impact_analyzer (ai/intelligence/impact_analyzer.py)
# ============================================================================
"""
Impact Analyzer — calculates the impact of file changes.

This module analyzes how changes to a file will affect other files
in the project. It considers:
- Direct dependencies
- Import relationships
- Business logic dependencies
- Test dependencies

The impact analysis is used for:
- Risk assessment before changes
- Determining test scope
- Predicting merge conflicts
- Optimizing CI/CD pipelines
"""

import time
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field

from core.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class ImpactReport:
    """Report of the impact of changing a file."""
    file_path: str
    affected_files: List[str] = field(default_factory=list)
    affected_classes: List[str] = field(default_factory=list)
    affected_functions: List[str] = field(default_factory=list)
    risk_level: str = "low"  # low, medium, high, critical
    dependency_count: int = 0
    build_impact: List[str] = field(default_factory=list)
    test_impact: List[str] = field(default_factory=list)
    estimated_complexity: str = "simple"  # simple, moderate, complex, major
    
    def to_dict(self) -> Dict[str, object]:
        return {
            "file_path": self.file_path,
            "affected_files": self.affected_files,
            "affected_classes": self.affected_classes,
            "affected_functions": self.affected_functions,
            "risk_level": self.risk_level,
            "dependency_count": self.dependency_count,
            "build_impact": self.build_impact,
            "test_impact": self.test_impact,
            "estimated_complexity": self.estimated_complexity,
        }


class ImpactAnalyzer:
    """
    Analyzes the impact of file changes in a project.
    
    This analyzer considers:
    - Direct file dependencies (imports)
    - Reverse dependencies (who imports this file)
    - Class and function dependencies
    - Test file relationships
    - Build system dependencies
    
    The analysis is cached to avoid recomputing for the same file.
    """
    
    def __init__(self):
        self._cache: Dict[str, ImpactReport] = {}
        self._dependency_graph = None
        self._symbol_index = None
        
    def set_dependency_graph(self, graph):
        """Set the dependency graph for analysis."""
        self._dependency_graph = graph
        
    def set_symbol_index(self, index):
        """Set the symbol index for analysis."""
        self._symbol_index = index
        
    def analyze(self, file_path: str | Path, project_path: str | Path = None) -> ImpactReport:
        """
        Analyze the impact of changing a file.
        
        Args:
            file_path: Path to the file to analyze
            project_path: Optional project root (uses file_path's root if not provided)
            
        Returns:
            ImpactReport with all impact information
        """
        file_path = Path(file_path).resolve()
        
        if project_path:
            project_path = Path(project_path).resolve()
        else:
            project_path = file_path.parent
            
        # Check cache first
        cache_key = str(file_path)
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        logger.info(f"Analyzing impact for: {file_path}")
        start_time = time.perf_counter()
        
        # Build impact report
        report = ImpactReport(file_path=str(file_path))
        
        # 1. Find files that import this file
        if self._dependency_graph:
            dependents = self._dependency_graph.get_dependents(str(file_path.relative_to(project_path)))
            report.affected_files.extend(dependents)
            
            # 2. Find files this file depends on
            dependencies = self._dependency_graph.get_dependencies(str(file_path.relative_to(project_path)))
            report.dependency_count = len(dependencies)
            
        # 3. Find classes and functions defined in this file
        if self._symbol_index:
            symbols = self._symbol_index.get_symbols_in_file(str(file_path))
            for symbol in symbols:
                if symbol.symbol_type.value in ('class', 'function', 'method'):
                    if symbol.name not in report.affected_classes:
                        report.affected_classes.append(symbol.name)
                        
        # 4. Find test files for this file
        test_files = self._find_test_files(file_path, project_path)
        report.test_impact.extend(test_files)
        
        # 5. Check build system dependencies
        build_impact = self._analyze_build_impact(file_path, project_path)
        report.build_impact.extend(build_impact)
        
        # 6. Calculate risk level
        report.risk_level = self._calculate_risk_level(report)
        
        # 7. Estimate complexity
        report.estimated_complexity = self._estimate_complexity(report)
        
        # Cache the result
        self._cache[cache_key] = report
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(f"Impact analysis completed in {elapsed_ms:.0f}ms")
        
        return report
    
    def _find_test_files(self, file_path: Path, project_path: Path) -> List[str]:
        """Find test files related to a file."""
        test_patterns = [
            "test_*.py",
            "*_test.py",
            "tests/test_*.py",
            "tests/*_test.py",
            "spec_*.py",
            "*_spec.py",
        ]
        
        # Get the base name of the file
        stem = file_path.stem
        
        test_files = []
        for pattern in test_patterns:
            for test_file in project_path.rglob(pattern):
                # Check if the test file relates to our file
                if stem in test_file.name or test_file.name in stem:
                    test_files.append(str(test_file))
                    
        return test_files
    
    def _analyze_build_impact(self, file_path: Path, project_path: Path) -> List[str]:
        """Analyze build system dependencies."""
        impact = []
        
        # Check for common build/config files
        config_files = [
            "Makefile",
            "CMakeLists.txt",
            "build.gradle",
            "pom.xml",
            "package.json",
            "requirements.txt",
            "pyproject.toml",
            "Cargo.toml",
            "go.mod",
        ]
        
        for config in config_files:
            config_path = project_path / config
            if config_path.exists():
                # Check if the config references our file
                try:
                    content = config_path.read_text(encoding='utf-8', errors='ignore')
                    if str(file_path.relative_to(project_path)) in content:
                        impact.append(config)
                except Exception:
                    pass
                    
        return impact
    
    def _calculate_risk_level(self, report: ImpactReport) -> str:
        """Calculate the risk level of changing a file."""
        # Count factors that increase risk
        risk_factors = 0
        max_factors = 10
        
        # More affected files = higher risk
        if len(report.affected_files) > 50:
            risk_factors += 3
        elif len(report.affected_files) > 10:
            risk_factors += 2
        elif len(report.affected_files) > 3:
            risk_factors += 1
            
        # More dependencies = higher risk
        if report.dependency_count > 20:
            risk_factors += 2
        elif report.dependency_count > 10:
            risk_factors += 1
            
        # More test files = higher risk
        if len(report.test_impact) > 10:
            risk_factors += 2
            
        # More affected classes/functions = higher risk
        if len(report.affected_classes) > 10:
            risk_factors += 2
        elif len(report.affected_classes) > 3:
            risk_factors += 1
            
        # If file is in build system
        if report.build_impact:
            risk_factors += 1
            
        # Calculate risk level
        if risk_factors >= 7:
            return "critical"
        elif risk_factors >= 5:
            return "high"
        elif risk_factors >= 3:
            return "medium"
        else:
            return "low"
    
    def _estimate_complexity(self, report: ImpactReport) -> str:
        """Estimate the complexity of the change."""
        complexity_factors = 0
        
        # More affected files = more complex
        if len(report.affected_files) > 100:
            complexity_factors += 3
        elif len(report.affected_files) > 50:
            complexity_factors += 2
        elif len(report.affected_files) > 10:
            complexity_factors += 1
            
        # More affected functions/classes = more complex
        if len(report.affected_classes) > 20:
            complexity_factors += 2
        elif len(report.affected_classes) > 10:
            complexity_factors += 1
            
        # If test files are affected = more complex
        if report.test_impact:
            complexity_factors += 1
            
        if complexity_factors >= 5:
            return "major"
        elif complexity_factors >= 3:
            return "complex"
        elif complexity_factors >= 2:
            return "moderate"
        else:
            return "simple"
    
    def analyze_batch(self, file_paths: List[str | Path], project_path: str | Path) -> Dict[str, ImpactReport]:
        """
        Analyze multiple files at once.
        
        Args:
            file_paths: List of file paths to analyze
            project_path: Project root path
            
        Returns:
            Dictionary mapping file paths to impact reports
        """
        results = {}
        for file_path in file_paths:
            results[str(file_path)] = self.analyze(file_path, project_path)
        return results
    
    def get_high_impact_files(self, project_path: str | Path, threshold: str = "medium") -> List[str]:
        """
        Get all files with high or critical impact.
        
        Args:
            project_path: Project root path
            threshold: Minimum risk level ("low", "medium", "high", "critical")
            
        Returns:
            List of file paths with high impact
        """
        high_impact = []
        
        # Scan common source files
        patterns = ["*.py", "*.js", "*.ts", "*.java", "*.c", "*.cpp"]
        
        for pattern in patterns:
            for file_path in Path(project_path).rglob(pattern):
                report = self.analyze(file_path, project_path)
                
                if report.risk_level in ("high", "critical"):
                    high_impact.append(str(file_path))
                    
        return high_impact
    
    def clear_cache(self):
        """Clear the impact analysis cache."""
        self._cache = {}
        logger.info("Impact analysis cache cleared")
        
    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-serializable representation of the analyzer state."""
        return {
            "cache_size": len(self._cache),
            "has_dependency_graph": self._dependency_graph is not None,
            "has_symbol_index": self._symbol_index is not None,
        }

# ============================================================================
# SECTION: ai.intelligence.project_health (ai/intelligence/project_health.py)
# ============================================================================
"""
Project Health — calculates project health scores and recommendations.

This module analyzes a project for code quality issues and generates
a health score along with actionable recommendations.

Health factors considered:
- Dead code detection
- Large files
- Circular imports
- Duplicate code
- Long functions
- Unused imports
- Missing tests
- Large classes
- Architecture violations
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from core.logger import setup_logger

logger = setup_logger(__name__)


class HealthStatus(Enum):
    """Health status indicators."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class HealthRecommendation:
    """A recommendation for improving project health."""
    category: str  # code_quality, architecture, tests, documentation
    severity: str  # low, medium, high, critical
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suggested_fix: Optional[str] = None
    
    def to_dict(self) -> Dict[str, object]:
        return {
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "suggested_fix": self.suggested_fix,
        }


@dataclass
class HealthScore:
    """Health score for a project."""
    total_score: int  # 0-100
    status: HealthStatus
    breakdown: Dict[str, int] = field(default_factory=dict)
    recommendations: List[HealthRecommendation] = field(default_factory=list)
    scores: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, object]:
        return {
            "total_score": self.total_score,
            "status": self.status.value,
            "breakdown": self.breakdown,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "scores": self.scores,
        }


class ProjectHealth:
    """
    Analyzes project health and generates recommendations.
    
    This analyzer examines the codebase for common quality issues
    and assigns a health score from 0-100.
    
    Categories:
    - Code Quality (40 points)
    - Architecture (25 points)
    - Tests (20 points)
    - Documentation (15 points)
    """
    
    # File size thresholds (in KB)
    MAX_FILE_SIZE = 500  # KB
    LARGE_FILE_SIZE = 200  # KB
    
    # Class/Function thresholds
    MAX_CLASS_LINES = 500
    MAX_FUNCTION_LINES = 50
    MAX_PARAMETERS = 5
    
    # Dependency thresholds
    MAX_CIRCULAR_DEPENDENCIES = 3
    MAX_DEPENDENCIES_PER_FILE = 20
    
    def __init__(
        self,
        project_path: str | Path,
        symbols: List = None,
        dependency_graph = None,
        documentation: List = None,
    ):
        self.project_path = Path(project_path).resolve()
        self.symbols = symbols or []
        self.dependency_graph = dependency_graph
        self.documentation = documentation or []
        
        # Cache for analysis results
        self._large_files: List[str] = []
        self._circular_dependencies: List[List[str]] = []
        self._dead_code: List[str] = []
        self._unused_imports: List[str] = []
        self._long_functions: List[str] = []
        self._large_classes: List[str] = []
        self._duplicate_code: List[str] = []
        self._missing_tests: List[str] = []
        self._architecture_violations: List[str] = []
        
    def calculate(self) -> HealthScore:
        """
        Calculate the overall project health score.
        
        Returns:
            HealthScore with total score, status, and recommendations
        """
        logger.info(f"Calculating project health for: {self.project_path}")
        
        # Run all analyses
        self._analyze_large_files()
        self._analyze_circular_dependencies()
        self._analyze_dead_code()
        self._analyze_unused_imports()
        self._analyze_long_functions()
        self._analyze_large_classes()
        self._analyze_duplicate_code()
        self._analyze_missing_tests()
        self._analyze_architecture()
        
        # Calculate scores for each category
        code_quality_score = self._calculate_code_quality_score()
        architecture_score = self._calculate_architecture_score()
        tests_score = self._calculate_tests_score()
        documentation_score = self._calculate_documentation_score()
        
        # Weighted total
        total_score = (
            code_quality_score * 0.40 +
            architecture_score * 0.25 +
            tests_score * 0.20 +
            documentation_score * 0.15
        )
        
        # Determine status
        if total_score >= 90:
            status = HealthStatus.EXCELLENT
        elif total_score >= 75:
            status = HealthStatus.GOOD
        elif total_score >= 50:
            status = HealthStatus.FAIR
        elif total_score >= 25:
            status = HealthStatus.POOR
        else:
            status = HealthStatus.CRITICAL
            
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        # Build breakdown
        breakdown = {
            "code_quality": code_quality_score,
            "architecture": architecture_score,
            "tests": tests_score,
            "documentation": documentation_score,
        }
        
        scores = {
            "code_quality": code_quality_score,
            "architecture": architecture_score,
            "tests": tests_score,
            "documentation": documentation_score,
        }
        
        score = HealthScore(
            total_score=int(total_score),
            status=status,
            breakdown=breakdown,
            recommendations=recommendations,
            scores=scores,
        )
        
        logger.info(f"Project health score: {score.total_score}/100 ({score.status.value})")
        
        return score
    
    def _analyze_large_files(self):
        """Analyze file sizes."""
        self._large_files = []
        
        for file_path in self.project_path.rglob("*"):
            if file_path.is_file():
                try:
                    size_kb = file_path.stat().st_size / 1024
                    if size_kb > self.MAX_FILE_SIZE:
                        self._large_files.append(str(file_path))
                except Exception:
                    pass
                    
    def _analyze_circular_dependencies(self):
        """Detect circular dependencies."""
        self._circular_dependencies = []
        
        if self.dependency_graph:
            cycles = self.dependency_graph.get_cycle_paths()
            self._circular_dependencies = cycles
    
    def _analyze_dead_code(self):
        """Detect dead code (unused classes/functions)."""
        self._dead_code = []
        
        # Find classes and functions with no references
        for symbol in self.symbols:
            if symbol.symbol_type.value in ('class', 'function', 'method'):
                # Check if symbol has any references
                has_references = False
                for ref_symbol in self.symbols:
                    if ref_symbol.path != symbol.path:
                        # This is a simplified check
                        pass
                        
                if not has_references:
                    self._dead_code.append(symbol.get_full_name())
                    
    def _analyze_unused_imports(self):
        """Detect unused imports."""
        self._unused_imports = []
        
        # This would require more sophisticated analysis
        # For now, just mark that analysis exists
        pass
        
    def _analyze_long_functions(self):
        """Detect long functions."""
        self._long_functions = []
        
        for symbol in self.symbols:
            if symbol.symbol_type.value == 'function':
                line_count = symbol.line_end - symbol.line_start
                if line_count > self.MAX_FUNCTION_LINES:
                    self._long_functions.append(symbol.get_full_name())
                    
    def _analyze_large_classes(self):
        """Detect large classes."""
        self._large_classes = []
        
        for symbol in self.symbols:
            if symbol.symbol_type.value == 'class':
                line_count = symbol.line_end - symbol.line_start
                if line_count > self.MAX_CLASS_LINES:
                    self._large_classes.append(symbol.get_full_name())
                    
    def _analyze_duplicate_code(self):
        """Detect duplicate code blocks."""
        self._duplicate_code = []
        
        # This would require fuzzy matching of code blocks
        # For now, just mark that analysis exists
        pass
        
    def _analyze_missing_tests(self):
        """Detect files without tests."""
        self._missing_tests = []
        
        # Check for test file patterns
        test_patterns = [
            "test_*.py",
            "*_test.py",
            "tests/test_*.py",
        ]
        
        source_extensions = {'.py', '.js', '.ts', '.java', '.c', '.cpp'}
        test_extensions = {'.py', '.js', '.ts', '.java'}
        
        source_files = []
        test_files = []
        
        for file_path in self.project_path.rglob("*"):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                stem = file_path.stem
                
                if ext in source_extensions:
                    source_files.append(str(file_path))
                    
                if ext in test_extensions:
                    for pattern in test_patterns:
                        if pattern.replace('*', stem) in str(file_path):
                            test_files.append(str(file_path))
                            break
                            
        # Find source files without tests
        for source in source_files:
            has_test = False
            for test in test_files:
                if source.replace('/src/', '/tests/') in test or 'test' in test:
                    has_test = True
                    break
                    
            if not has_test:
                self._missing_tests.append(source)
                
    def _analyze_architecture(self):
        """Check for architecture violations."""
        self._architecture_violations = []
        
        # Check for common violations based on detected architecture
        # This would be more sophisticated with actual architecture detection
        
    def _calculate_code_quality_score(self) -> int:
        """Calculate code quality score."""
        score = 100
        
        # Large files penalty
        large_file_count = len(self._large_files)
        score -= min(large_file_count * 2, 20)
        
        # Circular dependencies penalty
        cycle_count = len(self._circular_dependencies)
        score -= min(cycle_count * 5, 25)
        
        # Dead code penalty
        dead_code_count = len(self._dead_code)
        score -= min(dead_code_count * 3, 15)
        
        # Long functions penalty
        long_func_count = len(self._long_functions)
        score -= min(long_func_count * 2, 10)
        
        # Large classes penalty
        large_class_count = len(self._large_classes)
        score -= min(large_class_count * 2, 10)
        
        return max(score, 0)
    
    def _calculate_architecture_score(self) -> int:
        """Calculate architecture score."""
        score = 100
        
        # Circular dependencies penalty
        cycle_count = len(self._circular_dependencies)
        score -= min(cycle_count * 10, 30)
        
        # Architecture violations penalty
        violation_count = len(self._architecture_violations)
        score -= min(violation_count * 5, 20)
        
        return max(score, 0)
    
    def _calculate_tests_score(self) -> int:
        """Calculate test coverage score."""
        score = 100
        
        # Missing tests penalty
        missing_count = len(self._missing_tests)
        if missing_count > 0:
            # Calculate percentage of files without tests
            total_source_files = len(self.symbols)  # Rough estimate
            percentage = missing_count / max(total_source_files, 1)
            penalty = int(percentage * 50)
            score -= penalty
            
        return max(score, 0)
    
    def _calculate_documentation_score(self) -> int:
        """Calculate documentation score."""
        score = 100
        
        # Check for README
        readme_count = sum(1 for f in self.documentation if 'readme' in f.path.lower())
        if readme_count == 0:
            score -= 10
            
        # Check for docstrings
        docstring_count = sum(1 for s in self.symbols if s.docstring)
        if docstring_count < len(self.symbols) * 0.5:
            score -= 20
            
        return max(score, 0)
    
    def _generate_recommendations(self) -> List[HealthRecommendation]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        # Large files
        if self._large_files:
            recommendations.append(HealthRecommendation(
                category="code_quality",
                severity="high",
                message=f"Found {len(self._large_files)} large files (>500KB)",
                suggested_fix="Consider splitting large files into smaller modules",
            ))
            
        # Circular dependencies
        if self._circular_dependencies:
            recommendations.append(HealthRecommendation(
                category="architecture",
                severity="critical",
                message=f"Found {len(self._circular_dependencies)} circular dependency paths",
                suggested_fix="Refactor to break circular dependencies using dependency injection",
            ))
            
        # Dead code
        if self._dead_code:
            recommendations.append(HealthRecommendation(
                category="code_quality",
                severity="medium",
                message=f"Found {len(self._dead_code)} potential dead code items",
                suggested_fix="Remove or comment out unused code",
            ))
            
        # Long functions
        if self._long_functions:
            recommendations.append(HealthRecommendation(
                category="code_quality",
                severity="medium",
                message=f"Found {len(self._long_functions)} long functions (>50 lines)",
                suggested_fix="Refactor long functions into smaller, focused functions",
            ))
            
        # Large classes
        if self._large_classes:
            recommendations.append(HealthRecommendation(
                category="code_quality",
                severity="medium",
                message=f"Found {len(self._large_classes)} large classes (>500 lines)",
                suggested_fix="Apply Single Responsibility Principle to split classes",
            ))
            
        # Missing tests
        if self._missing_tests:
            recommendations.append(HealthRecommendation(
                category="tests",
                severity="high",
                message=f"Found {len(self._missing_tests)} files without tests",
                suggested_fix="Add unit tests for uncovered code",
            ))
            
        # Architecture violations
        if self._architecture_violations:
            recommendations.append(HealthRecommendation(
                category="architecture",
                severity="high",
                message=f"Found {len(self._architecture_violations)} architecture violations",
                suggested_fix="Review and fix architecture violations",
            ))
            
        return recommendations
    
    def get_health_summary(self) -> Dict[str, object]:
        """Get a summary of project health."""
        score = self.calculate()
        
        return {
            "total_score": score.total_score,
            "status": score.status.value,
            "breakdown": score.breakdown,
            "recommendations_count": len(score.recommendations),
            "issues": {
                "large_files": len(self._large_files),
                "circular_dependencies": len(self._circular_dependencies),
                "dead_code": len(self._dead_code),
                "long_functions": len(self._long_functions),
                "large_classes": len(self._large_classes),
                "missing_tests": len(self._missing_tests),
            },
        }
    
    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-serializable representation."""
        return {
            "project_path": str(self.project_path),
            "large_files": self._large_files,
            "circular_dependencies": self._circular_dependencies,
            "dead_code": self._dead_code,
            "long_functions": self._long_functions,
            "large_classes": self._large_classes,
            "missing_tests": self._missing_tests,
        }

# ============================================================================
# SECTION: ai.intelligence.project_analyzer (ai/intelligence/project_analyzer.py)
# ============================================================================
"""
Project Analyzer — orchestrates the Project Intelligence Engine.

When a project is opened, this analyzer runs all sub-analyzers,
aggregates their results, and produces a comprehensive ProjectIntelligence
object that describes the project's structure, architecture, and health.

The analyzer is asynchronous and runs in the background to avoid UI freezes.
Results are cached and only re-scanned when files change.
"""

import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from core.logger import setup_logger
from core.event_bus import EventBus

# Sub-analyzers
from ai.intelligence.architecture_detector import ArchitectureDetector
from ai.intelligence.dependency_graph import DependencyGraph
from ai.intelligence.symbol_indexer import SymbolIndexer
from ai.intelligence.reference_index import ReferenceIndex
from ai.intelligence.impact_analyzer import ImpactAnalyzer
from ai.intelligence.project_health import ProjectHealth
from ai.intelligence.language_statistics import LanguageStatistics
from ai.intelligence.entry_point_detector import EntryPointDetector
from ai.intelligence.documentation_indexer import DocumentationIndexer

# Result types
from ai.intelligence.dependency_graph import DependencyNode
from ai.intelligence.symbol_indexer import SymbolEntry
from ai.intelligence.impact_analyzer import ImpactReport
from ai.intelligence.project_health import HealthScore, HealthRecommendation
from ai.intelligence.entry_point_detector import EntryPoint
from ai.intelligence.documentation_indexer import DocumentationEntry

logger = setup_logger(__name__)


class ProjectIntelligence:
    """
    Complete understanding of a project's structure, architecture, and health.
    
    This object is populated by ProjectAnalyzer and becomes the source
    of truth for all AI operations. It includes:
    - Architecture and design patterns
    - Dependency relationships
    - Symbol locations and references
    - Entry points and main modules
    - Health score and recommendations
    - Language statistics
    - Documentation coverage
    """
    
    def __init__(
        self,
        project_path: Path,
        architecture: Optional[str] = None,
        architecture_confidence: float = 0.0,
        dependency_graph: Optional[DependencyGraph] = None,
        symbols: List[SymbolEntry] = None,
        references: Dict[str, List[str]] = None,
        entry_points: List[EntryPoint] = None,
        health: Optional[HealthScore] = None,
        language_stats: Optional[LanguageStatistics] = None,
        documentation: List[DocumentationEntry] = None,
        impact_cache: Dict[str, ImpactReport] = None,
        scan_duration_ms: float = 0.0,
        last_scan_time: Optional[float] = None,
    ):
        self.project_path = project_path
        self.architecture = architecture
        self.architecture_confidence = architecture_confidence
        self.dependency_graph = dependency_graph or DependencyGraph()
        self.symbols = symbols or []
        self.references = references or {}
        self.entry_points = entry_points or []
        self.health = health
        self.language_stats = language_stats
        self.documentation = documentation or []
        self.impact_cache = impact_cache or {}
        self.scan_duration_ms = scan_duration_ms
        self.last_scan_time = last_scan_time or time.time()
        
    def get_summary(self) -> Dict[str, Any]:
        """Return a human-readable summary of project intelligence."""
        return {
            "project": str(self.project_path),
            "architecture": {
                "type": self.architecture,
                "confidence": f"{self.architecture_confidence:.0%}",
            },
            "dependency_graph": {
                "node_count": len(self.dependency_graph.nodes),
                "edge_count": len(self.dependency_graph.edges),
            },
            "symbols": len(self.symbols),
            "entry_points": [ep.path for ep in self.entry_points],
            "health": {
                "score": self.health.score if self.health else None,
                "status": self.health.status if self.health else None,
                "recommendations": [
                    rec.to_dict() for rec in (self.health.recommendations if self.health else [])
                ],
            },
            "language_stats": self.language_stats.to_dict() if self.language_stats else None,
            "documentation": {
                "indexed_files": len(self.documentation),
                "coverage": f"{len(self.documentation):,} entries",
            },
            "impact_cache_size": len(self.impact_cache),
            "scan_duration_ms": self.scan_duration_ms,
        }


class ProjectAnalyzer:
    """
    Orchestrates all sub-analyzers to build complete project intelligence.
    
    This is the main entry point for the Project Intelligence Engine.
    When a workspace is opened, this analyzer runs all sub-analyzers
    asynchronously and publishes results to the EventBus.
    
    Events published:
    - `project_intelligence_scan_started`: Scan beginning
    - `project_intelligence_scan_progress`: Progress updates
    - `project_intelligence_scan_completed`: Scan completed with results
    - `project_intelligence_scan_failed`: Scan failed with error
    
    Usage:
        analyzer = ProjectAnalyzer(event_bus)
        analyzer.analyze("/path/to/project")
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._current_task: Optional[str] = None
        self._canceled = False
        self._memory_cache: Dict[str, ProjectIntelligence] = {}
        
    def analyze(self, project_path: str | Path, callback: Callable[[ProjectIntelligence], None] = None):
        """
        Analyze a project and return comprehensive intelligence.
        
        This method runs asynchronously and publishes progress events.
        The final ProjectIntelligence object is passed to the callback
        if provided, or can be retrieved from the last scan completed event.
        
        Args:
            project_path: Path to the project to analyze
            callback: Optional callback to receive the results
        """
        project_path = Path(project_path).resolve()
        logger.info(f"Starting project analysis: {project_path}")
        
        # Publish scan started
        self.event_bus.publish("project_intelligence_scan_started", {
            "project_path": str(project_path),
        })
        
        # Start analysis in background thread
        thread = threading.Thread(
            target=self._analyze_async,
            args=(project_path, callback),
            daemon=True
        )
        thread.start()
        
    def _analyze_async(self, project_path: Path, callback: Callable[[ProjectIntelligence], None] = None):
        """Run analysis in background thread."""
        start_time = time.perf_counter()
        self._canceled = False
        
        try:
            # Initialize intelligence object
            intelligence = ProjectIntelligence(project_path=project_path)
            
            # Step 1: Architecture detection
            self._current_task = "Detecting architecture..."
            self.event_bus.publish("project_intelligence_scan_progress", {
                "task": self._current_task,
                "progress": 10,
            })
            
            arch_detector = ArchitectureDetector()
            arch_result = arch_detector.detect(project_path)
            if arch_result:
                intelligence.architecture = arch_result.architecture
                intelligence.architecture_confidence = arch_result.confidence
            
            # Step 2: Language statistics
            self._current_task = "Analyzing language statistics..."
            self.event_bus.publish("project_intelligence_scan_progress", {
                "task": self._current_task,
                "progress": 20,
            })
            
            lang_stats = LanguageStatistics(project_path)
            intelligence.language_stats = lang_stats
            
            # Step 3: Entry point detection
            self._current_task = "Detecting entry points..."
            self.event_bus.publish("project_intelligence_scan_progress", {
                "task": self._current_task,
                "progress": 30,
            })
            
            entry_detector = EntryPointDetector(project_path)
            intelligence.entry_points = entry_detector.detect()
            
            # Step 4: Dependency graph
            self._current_task = "Building dependency graph..."
            self.event_bus.publish("project_intelligence_scan_progress", {
                "task": self._current_task,
                "progress": 45,
            })
            
            dep_graph = DependencyGraph()
            dep_graph.build(project_path)
            intelligence.dependency_graph = dep_graph
            
            # Step 5: Symbol indexing
            self._current_task = "Indexing symbols..."
            self.event_bus.publish("project_intelligence_scan_progress", {
                "task": self._current_task,
                "progress": 60,
            })
            
            symbol_indexer = SymbolIndexer()
            intelligence.symbols = symbol_indexer.index_project(str(project_path))
            
            # Step 6: Reference index
            self._current_task = "Building reference index..."
            self.event_bus.publish("project_intelligence_scan_progress", {
                "task": self._current_task,
                "progress": 70,
            })
            
            ref_index = ReferenceIndex()
            intelligence.references = ref_index.build_index(str(project_path), intelligence.symbols)
            
            # Step 7: Documentation indexing
            self._current_task = "Indexing documentation..."
            self.event_bus.publish("project_intelligence_scan_progress", {
                "task": self._current_task,
                "progress": 80,
            })
            
            doc_indexer = DocumentationIndexer(project_path)
            intelligence.documentation = doc_indexer.index()
            
            # Step 8: Project health
            self._current_task = "Calculating project health..."
            self.event_bus.publish("project_intelligence_scan_progress", {
                "task": self._current_task,
                "progress": 90,
            })
            
            health = ProjectHealth(
                project_path=project_path,
                symbols=intelligence.symbols,
                dependency_graph=intelligence.dependency_graph,
                documentation=intelligence.documentation,
            )
            intelligence.health = health.calculate()
            
            # Calculate total duration
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            intelligence.scan_duration_ms = elapsed_ms
            intelligence.last_scan_time = time.time()
            
            # Publish completion
            logger.info(f"Project analysis completed in {elapsed_ms:.0f}ms")
            self.event_bus.publish("project_intelligence_scan_completed", {
                "project_path": str(project_path),
                "intelligence": intelligence,
                "duration_ms": elapsed_ms,
            })
            
            # Call callback if provided
            if callback:
                callback(intelligence)
                
        except Exception as e:
            logger.error(f"Project analysis failed: {e}", exc_info=True)
            self.event_bus.publish("project_intelligence_scan_failed", {
                "project_path": str(project_path),
                "error": str(e),
            })
    
    def get_intelligence(self, project_path: str | Path) -> Optional[ProjectIntelligence]:
        """
        Get cached intelligence for a project if available.
        
        This method checks if intelligence has been previously calculated
        for this project and returns it. Otherwise, returns None.
        
        Note: Currently this analyzer doesn't cache results. In the future,
        it could store intelligence in a file or database for persistence.
        
        Args:
            project_path: Path to the project
            
        Returns:
            ProjectIntelligence if previously analyzed, None otherwise
        """
        import json
        resolved = str(Path(project_path).resolve())
        if resolved in self._memory_cache:
            return self._memory_cache[resolved]
        cache_file = Path(resolved) / ".owncode" / "intelligence_cache.json"
        if cache_file.is_file():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                if hasattr(ProjectIntelligence, "from_dict"):
                    try:
                        intel = ProjectIntelligence.from_dict(data)
                        self._memory_cache[resolved] = intel
                        return intel
                    except Exception:
                        pass
                self._memory_cache[resolved] = data
                return data
            except Exception as exc:
                logger.debug(f"Failed to read intelligence cache from disk: {exc}")
        return None
    
    def cancel(self):
        """Cancel the current analysis if running."""
        self._canceled = True
        logger.info("Project analysis cancelled")
