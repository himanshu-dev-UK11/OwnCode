"""
Consolidated Module: tools.explorer_and_files

Combines: safety.delete_guard, core.file_operations, core.file_watcher, ai.tools.tree_builder, ai.tools.language_detector, ai.tools.framework_detector, ai.tools.dependency_analyzer, ai.tools.project_scanner, ui.panels.explorer
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['safety.delete_guard', 'core.file_operations', 'core.file_watcher', 'ai.tools.tree_builder', 'ai.tools.language_detector', 'ai.tools.framework_detector', 'ai.tools.dependency_analyzer', 'ai.tools.project_scanner', 'ui.panels.explorer']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: safety.delete_guard (safety/delete_guard.py)
# ============================================================================
"""
Deletion confirmation and protection layer.
"""

from core.logger import setup_logger

logger = setup_logger(__name__)

class DeleteGuard:
    def __init__(self):
        logger.info("DeleteGuard initialized.")
        pass

# ============================================================================
# SECTION: core.file_operations (core/file_operations.py)
# ============================================================================
"""
File Operations Manager — v1.6

Safe file and folder operations with validation and error handling.
Supports: create, rename, delete, move, copy, duplicate
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from PySide6.QtWidgets import QMessageBox, QInputDialog, QWidget
from core.logger import setup_logger
from core.process_utils import hidden_subprocess_kwargs

logger = setup_logger(__name__)


class FileOperations:
    """
    Safe file and folder operations with user confirmation.
    """
    def __init__(self, event_bus, parent: Optional[QWidget] = None):
        self.event_bus = event_bus
        self.parent = parent
        
    def create_file(self, parent_dir: Path, filename: str = None) -> Optional[Path]:
        """Create a new file."""
        if filename is None:
            filename, ok = QInputDialog.getText(
                self.parent, "New File", "Enter file name:"
            )
            if not ok or not filename:
                return None
                
        file_path = parent_dir / filename
        
        if file_path.exists():
            QMessageBox.warning(
                self.parent, "File Exists", 
                f"File '{filename}' already exists."
            )
            return None
            
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch()
            logger.info(f"Created file: {file_path}")
            self.event_bus.publish("file_created", {"path": str(file_path)})
            return file_path
        except Exception as e:
            logger.error(f"Failed to create file: {e}")
            QMessageBox.critical(
                self.parent, "Error", 
                f"Failed to create file: {e}"
            )
            return None
            
    def create_folder(self, parent_dir: Path, folder_name: str = None) -> Optional[Path]:
        """Create a new folder."""
        if folder_name is None:
            folder_name, ok = QInputDialog.getText(
                self.parent, "New Folder", "Enter folder name:"
            )
            if not ok or not folder_name:
                return None
                
        folder_path = parent_dir / folder_name
        
        if folder_path.exists():
            QMessageBox.warning(
                self.parent, "Folder Exists",
                f"Folder '{folder_name}' already exists."
            )
            return None

            
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created folder: {folder_path}")
            self.event_bus.publish("folder_created", {"path": str(folder_path)})
            return folder_path
        except Exception as e:
            logger.error(f"Failed to create folder: {e}")
            QMessageBox.critical(
                self.parent, "Error",
                f"Failed to create folder: {e}"
            )
            return None
            
    def rename(self, old_path: Path, new_name: str = None) -> Optional[Path]:
        """Rename a file or folder."""
        if new_name is None:
            new_name, ok = QInputDialog.getText(
                self.parent, "Rename", 
                f"Rename '{old_path.name}' to:",
                text=old_path.name
            )
            if not ok or not new_name:
                return None
                
        new_path = old_path.parent / new_name
        
        if new_path.exists():
            QMessageBox.warning(
                self.parent, "Already Exists",
                f"'{new_name}' already exists."
            )
            return None
            
        try:
            old_path.rename(new_path)
            logger.info(f"Renamed: {old_path} -> {new_path}")
            self.event_bus.publish("file_renamed", {
                "old_path": str(old_path),
                "new_path": str(new_path)
            })
            return new_path
        except Exception as e:
            logger.error(f"Failed to rename: {e}")
            QMessageBox.critical(
                self.parent, "Error",
                f"Failed to rename: {e}"
            )
            return None

            
    def delete(self, path: Path, confirm: bool = True) -> bool:
        """Delete a file or folder with confirmation."""
        if confirm:
            is_dir = path.is_dir()
            item_type = "folder" if is_dir else "file"
            
            reply = QMessageBox.question(
                self.parent, "Confirm Delete",
                f"Are you sure you want to delete this {item_type}?\n\n{path.name}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return False
                
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            logger.info(f"Deleted: {path}")
            self.event_bus.publish("file_deleted", {"path": str(path)})
            return True
        except Exception as e:
            logger.error(f"Failed to delete: {e}")
            QMessageBox.critical(
                self.parent, "Error",
                f"Failed to delete: {e}"
            )
            return False
            
    def move(self, source: Path, destination: Path) -> Optional[Path]:
        """Move a file or folder."""
        if destination.exists():
            QMessageBox.warning(
                self.parent, "Already Exists",
                f"Destination already exists: {destination}"
            )
            return None
            
        try:
            shutil.move(str(source), str(destination))
            logger.info(f"Moved: {source} -> {destination}")
            self.event_bus.publish("file_moved", {
                "source": str(source),
                "destination": str(destination)
            })
            return destination
        except Exception as e:
            logger.error(f"Failed to move: {e}")
            QMessageBox.critical(
                self.parent, "Error",
                f"Failed to move: {e}"
            )
            return None

            
    def copy(self, source: Path, destination: Path) -> Optional[Path]:
        """Copy a file or folder."""
        if destination.exists():
            QMessageBox.warning(
                self.parent, "Already Exists",
                f"Destination already exists: {destination}"
            )
            return None
            
        try:
            if source.is_dir():
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)
            logger.info(f"Copied: {source} -> {destination}")
            self.event_bus.publish("file_copied", {
                "source": str(source),
                "destination": str(destination)
            })
            return destination
        except Exception as e:
            logger.error(f"Failed to copy: {e}")
            QMessageBox.critical(
                self.parent, "Error",
                f"Failed to copy: {e}"
            )
            return None
            
    def duplicate(self, path: Path) -> Optional[Path]:
        """Duplicate a file or folder."""
        if path.is_dir():
            new_name = f"{path.name}_copy"
        else:
            stem = path.stem
            suffix = path.suffix
            new_name = f"{stem}_copy{suffix}"
            
        new_path = path.parent / new_name
        
        counter = 2
        while new_path.exists():
            if path.is_dir():
                new_name = f"{path.name}_copy{counter}"
            else:
                new_name = f"{stem}_copy{counter}{suffix}"
            new_path = path.parent / new_name
            counter += 1
            
        return self.copy(path, new_path)
        
    def reveal_in_explorer(self, path: Path):
        """Open file location in system file explorer across Windows, macOS, and Linux."""
        try:
            target = path.parent if path.is_file() else path
            if hasattr(os, "startfile"):
                os.startfile(str(target))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(target)], **hidden_subprocess_kwargs())
            else:
                subprocess.Popen(["xdg-open", str(target)], **hidden_subprocess_kwargs())
        except Exception as e:
            logger.error(f"Failed to reveal in explorer: {e}")
            QMessageBox.critical(
                self.parent, "Error",
                f"Failed to open location: {e}"
            )

# ============================================================================
# SECTION: core.file_watcher (core/file_watcher.py)
# ============================================================================
"""
File System Watcher — v1.6

Monitors workspace for file changes and emits events.
Supports:
- File created
- File modified
- File deleted
- Directory created
- Directory deleted
"""
from pathlib import Path
from typing import Set, Optional
from PySide6.QtCore import QFileSystemWatcher, QObject, Signal
from core.logger import setup_logger

logger = setup_logger(__name__)


class FileWatcher(QObject):
    """
    Watches files and directories for changes.
    Emits events through EventBus.
    """
    file_created = Signal(str)  # path
    file_modified = Signal(str)  # path
    file_deleted = Signal(str)  # path
    directory_created = Signal(str)  # path
    directory_deleted = Signal(str)  # path

    def __init__(self, event_bus):
        super().__init__()
        self.event_bus = event_bus
        self.watcher = QFileSystemWatcher()
        self.watched_files: Set[str] = set()
        self.watched_dirs: Set[str] = set()
        
        # Connect signals
        self.watcher.fileChanged.connect(self._on_file_changed)
        self.watcher.directoryChanged.connect(self._on_directory_changed)
        
    def watch_directory(self, path: Path):
        """Add a directory to watch list."""
        path_str = str(path.resolve())
        if path_str not in self.watched_dirs:
            if self.watcher.addPath(path_str):
                self.watched_dirs.add(path_str)
                logger.debug(f"Watching directory: {path_str}")
            else:
                logger.warning(f"Failed to watch directory: {path_str}")
                
    def watch_file(self, path: Path):
        """Add a file to watch list."""
        path_str = str(path.resolve())
        if path_str not in self.watched_files:
            if self.watcher.addPath(path_str):
                self.watched_files.add(path_str)
                logger.debug(f"Watching file: {path_str}")
            else:
                logger.warning(f"Failed to watch file: {path_str}")
                
    def unwatch_file(self, path: Path):
        """Remove a file from watch list."""
        path_str = str(path.resolve())
        if path_str in self.watched_files:
            self.watcher.removePath(path_str)
            self.watched_files.remove(path_str)
            logger.debug(f"Stopped watching file: {path_str}")
            
    def unwatch_directory(self, path: Path):
        """Remove a directory from watch list."""
        path_str = str(path.resolve())
        if path_str in self.watched_dirs:
            self.watcher.removePath(path_str)
            self.watched_dirs.remove(path_str)
            logger.debug(f"Stopped watching directory: {path_str}")
            
    def clear_all(self):
        """Stop watching all files and directories."""
        for path in list(self.watched_files):
            self.watcher.removePath(path)
        for path in list(self.watched_dirs):
            self.watcher.removePath(path)
        self.watched_files.clear()
        self.watched_dirs.clear()
        
    def _on_file_changed(self, path: str):
        """Handle file change event."""
        p = Path(path)
        if p.exists():
            self.file_modified.emit(path)
            self.event_bus.publish("file_changed_externally", {"path": path})
        else:
            # File was deleted
            self.file_deleted.emit(path)
            self.event_bus.publish("file_deleted_externally", {"path": path})
            self.watched_files.discard(path)
            
    def _on_directory_changed(self, path: str):
        """Handle directory change event."""
        # Directory contents changed - could be file added, deleted, or modified
        self.event_bus.publish("directory_changed", {"path": path})

# ============================================================================
# SECTION: ai.tools.tree_builder (ai/tools/tree_builder.py)
# ============================================================================
"""
TreeNode and TreeBuilder — in-memory folder tree generator.

Walks a workspace directory and builds a complete in-memory
representation of every file and folder. The resulting tree
is the structural backbone of ProjectContext; all other scanners
receive it to avoid redundant filesystem walks.

No files are modified. This module is read-only.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from core.logger import setup_logger
from core.exceptions import OwnCodeError

logger = setup_logger(__name__)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class TreeBuildError(OwnCodeError):
    """Raised when the tree cannot be built from the given root path."""


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class TreeNode:
    """
    Represents a single file or directory in the project tree.

    Attributes:
        name:          Filename or directory name (not the full path).
        path:          Absolute path as a Path object.
        is_directory:  True if this node represents a directory.
        parent:        Reference to the parent TreeNode (None for root).
        children:      Ordered list of child TreeNodes (empty for files).
        extension:     Lowercased file extension including dot (e.g. ".py"),
                       or empty string for directories.
        size_bytes:    File size in bytes. 0 for directories.
        last_modified: UTC datetime of the last file modification.
    """

    name:          str
    path:          Path
    is_directory:  bool
    parent:        Optional[TreeNode]        = field(default=None,  repr=False)
    children:      List[TreeNode]            = field(default_factory=list, repr=False)
    extension:     str                       = ""
    size_bytes:    int                       = 0
    last_modified: Optional[datetime]        = None

    # Index populated by TreeBuilder for O(1) path lookups
    _path_index: Dict[str, TreeNode]         = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.is_directory:
            self.extension = self.path.suffix.lower()

    # ------------------------------------------------------------------
    # Tree traversal helpers
    # ------------------------------------------------------------------

    def walk(self) -> Iterator[TreeNode]:
        """Depth-first iterator over this node and all its descendants."""
        yield self
        for child in self.children:
            yield from child.walk()

    def files(self) -> Iterator[TreeNode]:
        """Iterator over all file nodes in the subtree (non-directories)."""
        return (n for n in self.walk() if not n.is_directory)

    def directories(self) -> Iterator[TreeNode]:
        """Iterator over all directory nodes in the subtree."""
        return (n for n in self.walk() if n.is_directory)

    def find_by_name(self, name: str) -> List[TreeNode]:
        """Return all nodes whose filename matches `name` (case-insensitive)."""
        return [n for n in self.walk() if n.name.lower() == name.lower()]

    def depth(self) -> int:
        """Return depth from this node to the root (root = 0)."""
        d = 0
        node = self
        while node.parent is not None:
            d += 1
            node = node.parent
        return d

    def relative_path(self, root: Path) -> Path:
        """Return this node's path relative to `root`."""
        return self.path.relative_to(root)

    def __repr__(self) -> str:
        kind = "Dir" if self.is_directory else "File"
        return f"TreeNode({kind}, {self.name!r})"


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

# Directories to skip during scanning
_IGNORED_DIRS: frozenset = frozenset({
    ".git",
    "node_modules",
    "build",
    "dist",
    "__pycache__",
    ".dart_tool",
    ".idea",
    ".vscode",
})


class TreeBuilder:
    """
    Builds a TreeNode tree from a workspace root directory.

    The tree is built once and cached in memory. The builder
    also maintains a path-keyed index for O(1) lookups by
    absolute path string.

    Usage:
        builder = TreeBuilder("/path/to/project")
        root    = builder.build()
        node    = builder.find("/path/to/project/main.py")

    Raises:
        TreeBuildError: If the root path does not exist or is not a directory.
    """

    def __init__(self, root_path: str | Path) -> None:
        self.root_path = Path(root_path).resolve()
        self._root_node: Optional[TreeNode] = None
        self._path_index: Dict[str, TreeNode] = {}
        logger.info(f"TreeBuilder initialized for: {self.root_path}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self) -> TreeNode:
        """
        Walk the filesystem and build the complete in-memory tree.

        Returns:
            The root TreeNode of the built tree.

        Raises:
            TreeBuildError: If root_path does not exist or is not a directory.
        """
        if not self.root_path.exists():
            raise TreeBuildError(f"Root path does not exist: {self.root_path}")
        if not self.root_path.is_dir():
            raise TreeBuildError(f"Root path is not a directory: {self.root_path}")

        logger.info(f"Building tree for: {self.root_path}")
        self._path_index.clear()
        self._root_node = self._build_node(self.root_path, parent=None)
        logger.info(
            f"Tree built — {self.total_files()} files, "
            f"{self.total_dirs()} directories."
        )
        return self._root_node

    def find(self, path: str | Path) -> Optional[TreeNode]:
        """
        Look up a node by its absolute path string (O(1)).

        Returns None if the path was not indexed (e.g. it was ignored).
        """
        return self._path_index.get(str(Path(path).resolve()))

    def total_files(self) -> int:
        """Return the total number of file nodes in the tree."""
        if self._root_node is None:
            return 0
        return sum(1 for _ in self._root_node.files())

    def total_dirs(self) -> int:
        """Return the total number of directory nodes (excluding root)."""
        if self._root_node is None:
            return 0
        return sum(1 for _ in self._root_node.directories()) - 1  # exclude root

    def total_size_bytes(self) -> int:
        """Return the sum of all file sizes in the tree."""
        if self._root_node is None:
            return 0
        return sum(n.size_bytes for n in self._root_node.files())

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_node(self, path: Path, parent: Optional[TreeNode]) -> TreeNode:
        """
        Recursively create a TreeNode for `path` and all its children.

        Directories in `_IGNORED_DIRS` are skipped entirely.
        """
        stat = path.stat()
        node = TreeNode(
            name          = path.name,
            path          = path,
            is_directory  = path.is_dir(),
            parent        = parent,
            size_bytes    = stat.st_size if path.is_file() else 0,
            last_modified = datetime.utcfromtimestamp(stat.st_mtime),
        )

        # Register in the path index
        self._path_index[str(path)] = node

        if path.is_dir():
            try:
                entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
            except PermissionError:
                logger.warning(f"Permission denied — skipping directory: {path}")
                return node

            for entry in entries:
                if entry.name in _IGNORED_DIRS:
                    logger.debug(f"Skipping ignored directory: {entry.name}")
                    continue
                try:
                    child = self._build_node(entry, parent=node)
                    node.children.append(child)
                except Exception as exc:
                    logger.warning(f"Could not index {entry}: {exc}")

        return node

    def render_ascii(self, node: Optional[TreeNode] = None, prefix: str = "") -> str:
        """
        Return an ASCII art representation of the tree (like the `tree` command).

        Args:
            node:   Starting node (defaults to root).
            prefix: Internal recursion prefix — do not set manually.
        """
        if node is None:
            node = self._root_node
        if node is None:
            return "(empty tree)"

        lines: List[str] = []
        if node.parent is None:
            lines.append(str(node.path))

        children = node.children
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{child.name}")
            if child.is_directory:
                extension = "    " if is_last else "│   "
                lines.append(self.render_ascii(child, prefix + extension))

        return "\n".join(filter(None, lines))

# ============================================================================
# SECTION: ai.tools.language_detector (ai/tools/language_detector.py)
# ============================================================================
"""
LanguageDetector — determine language composition of a project.

Walks the project tree, maps every file extension to a programming
language, and returns a breakdown of language usage as both raw file
counts and percentage of total code files.

No files are modified. This module is read-only.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from core.logger import setup_logger
from ai.tools.tree_builder import TreeNode

logger = setup_logger(__name__)


# ---------------------------------------------------------------------------
# Extension → Language mapping
# ---------------------------------------------------------------------------

_EXT_MAP: Dict[str, str] = {
    # Python
    ".py":    "Python",
    ".pyi":   "Python",
    ".pyw":   "Python",
    # JavaScript / TypeScript
    ".js":    "JavaScript",
    ".mjs":   "JavaScript",
    ".cjs":   "JavaScript",
    ".jsx":   "JavaScript",
    ".ts":    "TypeScript",
    ".tsx":   "TypeScript",
    # Dart / Flutter
    ".dart":  "Dart",
    # Rust
    ".rs":    "Rust",
    # Go
    ".go":    "Go",
    # Java
    ".java":  "Java",
    # Kotlin
    ".kt":    "Kotlin",
    ".kts":   "Kotlin",
    # C / C++
    ".c":     "C",
    ".h":     "C",
    ".cpp":   "C++",
    ".cxx":   "C++",
    ".cc":    "C++",
    ".hpp":   "C++",
    # C#
    ".cs":    "C#",
    # Ruby
    ".rb":    "Ruby",
    # PHP
    ".php":   "PHP",
    # Swift
    ".swift": "Swift",
    # Shell
    ".sh":    "Shell",
    ".bash":  "Shell",
    ".zsh":   "Shell",
    ".ps1":   "PowerShell",
    # Web
    ".html":  "HTML",
    ".htm":   "HTML",
    ".css":   "CSS",
    ".scss":  "CSS",
    ".sass":  "CSS",
    ".less":  "CSS",
    # Data / Config
    ".json":  "JSON",
    ".yaml":  "YAML",
    ".yml":   "YAML",
    ".toml":  "TOML",
    ".xml":   "XML",
    ".sql":   "SQL",
    ".env":   "Config",
    ".ini":   "Config",
    ".cfg":   "Config",
    ".conf":  "Config",
    # Documentation
    ".md":    "Markdown",
    ".rst":   "reStructuredText",
    ".txt":   "Text",
    # Other
    ".r":     "R",
    ".scala": "Scala",
    ".lua":   "Lua",
    ".proto": "Protobuf",
    ".graphql": "GraphQL",
    ".gql":   "GraphQL",
}

# These extensions are counted but treated as non-code for percentage purposes
_NON_CODE_LANGUAGES: frozenset = frozenset({
    "JSON", "YAML", "TOML", "XML", "Markdown",
    "reStructuredText", "Text", "Config",
})


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class LanguageStats:
    """
    Statistics for a single programming language.

    Attributes:
        language:    Language name (e.g. "Python", "Dart").
        file_count:  Number of files written in this language.
        percentage:  Percentage of total detected files (0.0–100.0).
        is_code:     False for config/data/doc formats (JSON, YAML, etc.).
    """
    language:   str
    file_count: int
    percentage: float
    is_code:    bool = True

    def __repr__(self) -> str:
        return f"LanguageStats({self.language!r}, {self.file_count} files, {self.percentage:.1f}%)"


@dataclass
class LanguageBreakdown:
    """
    Full language composition of a project.

    Attributes:
        languages:        Ordered list (descending by file count).
        total_files:      Total number of files analyzed.
        primary_language: The language with the highest file count.
    """
    languages:        List[LanguageStats]
    total_files:      int
    primary_language: Optional[str] = None

    def get(self, language: str) -> Optional[LanguageStats]:
        """Return stats for a specific language, or None if not detected."""
        name_lower = language.lower()
        return next(
            (ls for ls in self.languages if ls.language.lower() == name_lower),
            None,
        )

    def code_languages(self) -> List[LanguageStats]:
        """Return only languages that are considered source code."""
        return [ls for ls in self.languages if ls.is_code]

    def __repr__(self) -> str:
        top = self.languages[:3] if self.languages else []
        return f"LanguageBreakdown(primary={self.primary_language!r}, top={top})"


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

class LanguageDetector:
    """
    Determines the programming language composition of a project.

    Requires a pre-built TreeNode (from TreeBuilder) to avoid
    redundant filesystem walks.

    Usage:
        builder   = TreeBuilder(root)
        tree_root = builder.build()
        detector  = LanguageDetector()
        breakdown = detector.detect(tree_root)
        print(breakdown.primary_language)  # "Python"
    """

    def __init__(self) -> None:
        logger.info("LanguageDetector initialized.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, tree_root: TreeNode) -> LanguageBreakdown:
        """
        Walk the tree and calculate language percentages.

        Args:
            tree_root: Root TreeNode returned by TreeBuilder.build().

        Returns:
            LanguageBreakdown with per-language stats and a primary language.
        """
        logger.info("Detecting language composition...")
        counts: Dict[str, int] = {}

        for node in tree_root.files():
            lang = _EXT_MAP.get(node.extension)
            if lang:
                counts[lang] = counts.get(lang, 0) + 1

        total = sum(counts.values())
        if total == 0:
            logger.info("No recognized source files found.")
            return LanguageBreakdown(languages=[], total_files=0)

        stats: List[LanguageStats] = []
        for lang, count in sorted(counts.items(), key=lambda x: -x[1]):
            stats.append(LanguageStats(
                language   = lang,
                file_count = count,
                percentage = round(count / total * 100, 1),
                is_code    = lang not in _NON_CODE_LANGUAGES,
            ))

        primary = stats[0].language if stats else None
        logger.info(
            f"Language detection complete — {len(stats)} languages, "
            f"primary: {primary!r}, total files: {total}."
        )
        return LanguageBreakdown(
            languages        = stats,
            total_files      = total,
            primary_language = primary,
        )

    def detect_from_path(self, root_path: str | Path) -> LanguageBreakdown:
        """
        Convenience method: build a tree internally and detect languages.

        Use this when you do not already have a TreeNode available.
        """
        from ai.tools.tree_builder import TreeBuilder
        builder   = TreeBuilder(root_path)
        tree_root = builder.build()
        return self.detect(tree_root)

# ============================================================================
# SECTION: ai.tools.framework_detector (ai/tools/framework_detector.py)
# ============================================================================
"""
FrameworkDetector — automatically identify the project's framework.

Inspects well-known configuration and manifest files in the project
root to determine which framework (and language ecosystem) the user's
project belongs to. Returns a structured detection result with a
framework name, a confidence score, and the evidence that led to
the conclusion.

No files are written. This module is purely read-only analysis.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

from core.logger import setup_logger
from core.exceptions import OwnCodeError

logger = setup_logger(__name__)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class FrameworkDetectionError(OwnCodeError):
    """Raised when framework detection cannot run due to an I/O or parse error."""


# ---------------------------------------------------------------------------
# Supported frameworks
# ---------------------------------------------------------------------------

class Framework(str, Enum):
    """All frameworks the detector can identify."""
    FLUTTER     = "Flutter"
    DJANGO      = "Django"
    FASTAPI     = "FastAPI"
    FLASK       = "Flask"
    PYTHON      = "Python"           # Generic Python (no web framework)
    REACT       = "React"
    NEXTJS      = "Next.js"
    NODEJS      = "Node.js"          # Generic Node (no specific framework)
    JAVA        = "Java"             # Generic Java / Maven / Gradle
    SPRING_BOOT = "Spring Boot"
    RUST        = "Rust"
    GO          = "Go"
    CSHARP      = "C#"
    CPP         = "C++"
    UNKNOWN     = "Unknown"


# ---------------------------------------------------------------------------
# Detection result
# ---------------------------------------------------------------------------

@dataclass
class FrameworkResult:
    """
    The outcome of a single framework detection pass.

    Attributes:
        framework:   The detected Framework enum value.
        confidence:  A float between 0.0 and 1.0 (higher = more certain).
        reason:      Human-readable explanation of why this framework was chosen.
        evidence_files: List of file paths that contributed to the detection.
    """
    framework:       Framework
    confidence:      float
    reason:          str
    evidence_files:  List[str]

    def __repr__(self) -> str:
        return (
            f"FrameworkResult(framework={self.framework.value!r}, "
            f"confidence={self.confidence:.0%}, reason={self.reason!r})"
        )


# ---------------------------------------------------------------------------
# Detection rules
# Each rule is: (file_to_check, content_substring_or_None, framework, confidence, reason)
# If content_substring is None, mere existence of the file is enough.
# ---------------------------------------------------------------------------

@dataclass
class _DetectionRule:
    filename:         str
    content_hint:     Optional[str]   # substring to search for inside the file
    framework:        Framework
    confidence:       float
    reason:           str


_RULES: List[_DetectionRule] = [
    # --- Flutter ---
    _DetectionRule("pubspec.yaml",    "flutter:",         Framework.FLUTTER,     0.98, "pubspec.yaml contains 'flutter:' dependency"),
    _DetectionRule("pubspec.yaml",    None,               Framework.FLUTTER,     0.80, "pubspec.yaml present (likely Flutter/Dart)"),

    # --- Python web frameworks (checked before generic Python) ---
    _DetectionRule("requirements.txt", "django",          Framework.DJANGO,      0.90, "requirements.txt contains 'django'"),
    _DetectionRule("requirements.txt", "fastapi",         Framework.FASTAPI,     0.90, "requirements.txt contains 'fastapi'"),
    _DetectionRule("requirements.txt", "flask",           Framework.FLASK,       0.90, "requirements.txt contains 'flask'"),
    _DetectionRule("pyproject.toml",   "django",          Framework.DJANGO,      0.90, "pyproject.toml contains 'django'"),
    _DetectionRule("pyproject.toml",   "fastapi",         Framework.FASTAPI,     0.90, "pyproject.toml contains 'fastapi'"),
    _DetectionRule("pyproject.toml",   "flask",           Framework.FLASK,       0.90, "pyproject.toml contains 'flask'"),
    _DetectionRule("manage.py",        "django",          Framework.DJANGO,      0.95, "manage.py present with 'django' content"),
    _DetectionRule("manage.py",        None,              Framework.DJANGO,      0.85, "manage.py present (Django management script)"),

    # --- Generic Python ---
    _DetectionRule("requirements.txt", None,              Framework.PYTHON,      0.70, "requirements.txt present (Python project)"),
    _DetectionRule("pyproject.toml",   None,              Framework.PYTHON,      0.70, "pyproject.toml present (Python project)"),
    _DetectionRule("setup.py",         None,              Framework.PYTHON,      0.65, "setup.py present (Python package)"),

    # --- JavaScript / Node ---
    _DetectionRule("package.json",     '"next"',          Framework.NEXTJS,      0.95, "package.json contains 'next' dependency"),
    _DetectionRule("next.config.js",   None,              Framework.NEXTJS,      0.97, "next.config.js present"),
    _DetectionRule("next.config.mjs",  None,              Framework.NEXTJS,      0.97, "next.config.mjs present"),
    _DetectionRule("package.json",     '"react"',         Framework.REACT,       0.90, "package.json contains 'react' dependency"),
    _DetectionRule("package.json",     None,              Framework.NODEJS,      0.65, "package.json present (Node.js project)"),

    # --- Rust ---
    _DetectionRule("Cargo.toml",       None,              Framework.RUST,        0.98, "Cargo.toml present (Rust project)"),

    # --- Java / Spring Boot ---
    _DetectionRule("pom.xml",          "spring-boot",     Framework.SPRING_BOOT, 0.95, "pom.xml contains 'spring-boot'"),
    _DetectionRule("build.gradle",     "spring-boot",     Framework.SPRING_BOOT, 0.95, "build.gradle contains 'spring-boot'"),
    _DetectionRule("pom.xml",          None,              Framework.JAVA,        0.80, "pom.xml present (Maven/Java project)"),
    _DetectionRule("build.gradle",     None,              Framework.JAVA,        0.80, "build.gradle present (Gradle/Java project)"),

    # --- C# ---
    _DetectionRule("*.sln",            None,              Framework.CSHARP,      0.95, ".sln solution file present (C# project)"),

    # --- C++ ---
    _DetectionRule("CMakeLists.txt",   None,              Framework.CPP,         0.90, "CMakeLists.txt present (C++ CMake project)"),

    # --- Go ---
    _DetectionRule("go.mod",           None,              Framework.GO,          0.97, "go.mod present (Go module)"),
]


class FrameworkDetector:
    """
    Detects the dominant framework of a software project.

    Evaluates a prioritized list of file-based detection rules
    against the project root, returning the highest-confidence
    match as a FrameworkResult.

    If no rule matches, returns UNKNOWN with 0.0 confidence.

    Usage:
        detector = FrameworkDetector("/path/to/project")
        result   = detector.detect()
        print(result.framework.value, result.confidence)
    """

    def __init__(self, root_path: str | Path) -> None:
        self.root_path = Path(root_path).resolve()
        logger.info(f"FrameworkDetector initialized for: {self.root_path}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self) -> FrameworkResult:
        """
        Run all detection rules and return the best match.

        Returns:
            FrameworkResult with the detected framework, confidence, reason,
            and list of evidence file paths.

        Raises:
            FrameworkDetectionError: If an unexpected I/O error occurs.
        """
        logger.info("Starting framework detection...")
        best: Optional[FrameworkResult] = None

        for rule in _RULES:
            result = self._evaluate_rule(rule)
            if result is None:
                continue
            if best is None or result.confidence > best.confidence:
                best = result
                logger.debug(f"New best match: {best}")

        if best is None:
            logger.info("No framework detected — returning UNKNOWN.")
            return FrameworkResult(
                framework=Framework.UNKNOWN,
                confidence=0.0,
                reason="No recognizable configuration file found.",
                evidence_files=[],
            )

        logger.info(f"Framework detected: {best.framework.value} ({best.confidence:.0%})")
        return best

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _evaluate_rule(self, rule: _DetectionRule) -> Optional[FrameworkResult]:
        """
        Test a single detection rule against the filesystem.

        Handles glob patterns (e.g. "*.sln") and optional content checks.

        Returns a FrameworkResult if the rule matches, otherwise None.
        """
        # Resolve the target file(s) — support simple glob patterns
        if "*" in rule.filename:
            matches = list(self.root_path.glob(rule.filename))
        else:
            candidate = self.root_path / rule.filename
            matches = [candidate] if candidate.exists() else []

        if not matches:
            return None

        evidence = [str(p) for p in matches]

        # If a content check is required, verify at least one matching file
        if rule.content_hint is not None:
            content_match = False
            for filepath in matches:
                try:
                    text = filepath.read_text(encoding="utf-8", errors="ignore").lower()
                    if rule.content_hint.lower() in text:
                        content_match = True
                        break
                except Exception as exc:
                    logger.warning(f"Could not read {filepath}: {exc}")
            if not content_match:
                return None

        return FrameworkResult(
            framework=rule.framework,
            confidence=rule.confidence,
            reason=rule.reason,
            evidence_files=evidence,
        )

# ============================================================================
# SECTION: ai.tools.dependency_analyzer (ai/tools/dependency_analyzer.py)
# ============================================================================
"""
DependencyAnalyzer — extract libraries, versions, and package manager info.

Reads standard dependency manifest files and parses them into structured
DependencyInfo objects. This gives the AI context engine a precise view
of which external libraries the project relies on, enabling smarter
code suggestions and conflict detection.

No files are modified. This module is read-only.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from core.logger import setup_logger
from core.exceptions import OwnCodeError

logger = setup_logger(__name__)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class DependencyAnalysisError(OwnCodeError):
    """Raised when a dependency file is malformed or cannot be parsed."""


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Dependency:
    """
    A single library or package dependency.

    Attributes:
        name:            The package name (e.g. "django", "react").
        version:         The version constraint string (e.g. ">=4.0", "^18.0.0").
                         Empty string if no version is specified.
        is_dev:          True if this is a development-only dependency.
        source_file:     The manifest file this dependency was parsed from.
    """
    name:        str
    version:     str      = ""
    is_dev:      bool     = False
    source_file: str      = ""

    def __repr__(self) -> str:
        ver = f"@{self.version}" if self.version else ""
        return f"Dependency({self.name!r}{ver})"


@dataclass
class DependencyInfo:
    """
    Complete dependency picture for a project.

    Attributes:
        package_manager:    Detected package manager (e.g. "pip", "npm", "cargo").
        framework_version:  Version of the primary framework if detectable.
        dependencies:       List of all runtime dependencies.
        dev_dependencies:   List of development-only dependencies.
        source_files:       Manifest files that were read.
    """
    package_manager:    str
    framework_version:  str               = ""
    dependencies:       List[Dependency]  = field(default_factory=list)
    dev_dependencies:   List[Dependency]  = field(default_factory=list)
    source_files:       List[str]         = field(default_factory=list)

    @property
    def all_dependencies(self) -> List[Dependency]:
        """Combined list of runtime and dev dependencies."""
        return self.dependencies + self.dev_dependencies

    @property
    def dependency_names(self) -> List[str]:
        """Flat list of all dependency names."""
        return [d.name for d in self.all_dependencies]

    def __repr__(self) -> str:
        return (
            f"DependencyInfo(pm={self.package_manager!r}, "
            f"deps={len(self.dependencies)}, "
            f"dev_deps={len(self.dev_dependencies)})"
        )


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class DependencyAnalyzer:
    """
    Reads and parses project dependency manifests into DependencyInfo objects.

    Supports the following package managers / manifest formats:
      - pip       : requirements.txt
      - pip/pypa  : pyproject.toml (tool.poetry.dependencies or project.dependencies)
      - npm/yarn  : package.json
      - cargo     : Cargo.toml
      - maven     : pom.xml (partial — library name + version only)
      - gradle    : build.gradle (regex-based)
      - pubspec   : pubspec.yaml (Flutter/Dart)

    Usage:
        analyzer = DependencyAnalyzer("/path/to/project")
        info     = analyzer.analyze()
        print(info.package_manager, info.dependency_names)
    """

    def __init__(self, root_path: str | Path) -> None:
        self.root_path = Path(root_path).resolve()
        logger.info(f"DependencyAnalyzer initialized for: {self.root_path}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self) -> Optional[DependencyInfo]:
        """
        Detect the package manager and parse all available dependency files.

        Returns:
            DependencyInfo if at least one manifest was found, otherwise None.
        """
        logger.info("Analyzing project dependencies...")

        # Try each parser in priority order
        parsers = [
            ("requirements.txt",  self._parse_requirements_txt),
            ("pyproject.toml",    self._parse_pyproject_toml),
            ("package.json",      self._parse_package_json),
            ("Cargo.toml",        self._parse_cargo_toml),
            ("pom.xml",           self._parse_pom_xml),
            ("build.gradle",      self._parse_build_gradle),
            ("pubspec.yaml",      self._parse_pubspec_yaml),
        ]

        for filename, parser in parsers:
            path = self.root_path / filename
            if path.exists():
                try:
                    logger.info(f"Parsing dependency file: {filename}")
                    info = parser(path)
                    logger.info(
                        f"Found {len(info.dependencies)} runtime deps, "
                        f"{len(info.dev_dependencies)} dev deps via {filename}."
                    )
                    return info
                except Exception as exc:
                    logger.warning(f"Failed to parse {filename}: {exc}")

        logger.info("No dependency file found.")
        return None

    # ------------------------------------------------------------------
    # Parsers — one per manifest format
    # ------------------------------------------------------------------

    def _parse_requirements_txt(self, path: Path) -> DependencyInfo:
        """Parse a pip requirements.txt file."""
        deps: List[Dependency] = []
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()

        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            # e.g. django>=4.0,<5.0  or  requests==2.28.1
            match = re.match(r"^([A-Za-z0-9_.\-]+)\s*([><=!~^].+)?", line)
            if match:
                name    = match.group(1).lower()
                version = (match.group(2) or "").strip()
                deps.append(Dependency(name=name, version=version, source_file=str(path)))

        return DependencyInfo(
            package_manager="pip",
            dependencies=deps,
            source_files=[str(path)],
        )

    def _parse_pyproject_toml(self, path: Path) -> DependencyInfo:
        """Parse a pyproject.toml (PEP 517/518/621 or Poetry format)."""
        text = path.read_text(encoding="utf-8", errors="ignore")
        deps:     List[Dependency] = []
        dev_deps: List[Dependency] = []

        # PEP 621 project.dependencies
        pep621 = re.findall(r'dependencies\s*=\s*\[([^\]]+)\]', text, re.DOTALL)
        if pep621:
            for entry in re.findall(r'"([^"]+)"', pep621[0]):
                m = re.match(r"^([A-Za-z0-9_.\-]+)\s*([><=!~^].+)?", entry)
                if m:
                    deps.append(Dependency(name=m.group(1).lower(),
                                           version=(m.group(2) or "").strip(),
                                           source_file=str(path)))

        # Poetry [tool.poetry.dependencies]
        poetry_block = re.search(
            r'\[tool\.poetry\.dependencies\](.*?)(?=\[|$)', text, re.DOTALL
        )
        if poetry_block:
            for m in re.finditer(r'^([a-zA-Z][a-zA-Z0-9_\-]+)\s*=\s*"([^"]*)"',
                                  poetry_block.group(1), re.MULTILINE):
                if m.group(1).lower() != "python":
                    deps.append(Dependency(name=m.group(1).lower(),
                                           version=m.group(2),
                                           source_file=str(path)))

        # Poetry [tool.poetry.dev-dependencies]
        dev_block = re.search(
            r'\[tool\.poetry\.dev-dependencies\](.*?)(?=\[|$)', text, re.DOTALL
        )
        if dev_block:
            for m in re.finditer(r'^([a-zA-Z][a-zA-Z0-9_\-]+)\s*=\s*"([^"]*)"',
                                  dev_block.group(1), re.MULTILINE):
                dev_deps.append(Dependency(name=m.group(1).lower(),
                                           version=m.group(2),
                                           is_dev=True,
                                           source_file=str(path)))

        return DependencyInfo(
            package_manager="pip/poetry",
            dependencies=deps,
            dev_dependencies=dev_deps,
            source_files=[str(path)],
        )

    def _parse_package_json(self, path: Path) -> DependencyInfo:
        """Parse a Node.js package.json file using the standard json module."""
        import json
        data = json.loads(path.read_text(encoding="utf-8"))

        runtime_raw = data.get("dependencies", {})
        dev_raw     = data.get("devDependencies", {})

        deps     = [Dependency(name=k, version=v, source_file=str(path))
                    for k, v in runtime_raw.items()]
        dev_deps = [Dependency(name=k, version=v, is_dev=True, source_file=str(path))
                    for k, v in dev_raw.items()]

        # Detect yarn vs npm
        pm = "yarn" if (path.parent / "yarn.lock").exists() else "npm"

        return DependencyInfo(
            package_manager=pm,
            dependencies=deps,
            dev_dependencies=dev_deps,
            source_files=[str(path)],
        )

    def _parse_cargo_toml(self, path: Path) -> DependencyInfo:
        """Parse a Rust Cargo.toml file (TOML, parsed with regex)."""
        text = path.read_text(encoding="utf-8", errors="ignore")
        deps:     List[Dependency] = []
        dev_deps: List[Dependency] = []

        dep_block = re.search(r'\[dependencies\](.*?)(?=\[|$)', text, re.DOTALL)
        if dep_block:
            for m in re.finditer(r'^([a-z_\-]+)\s*=\s*"([^"]+)"',
                                  dep_block.group(1), re.MULTILINE):
                deps.append(Dependency(name=m.group(1), version=m.group(2),
                                       source_file=str(path)))

        dev_block = re.search(r'\[dev-dependencies\](.*?)(?=\[|$)', text, re.DOTALL)
        if dev_block:
            for m in re.finditer(r'^([a-z_\-]+)\s*=\s*"([^"]+)"',
                                  dev_block.group(1), re.MULTILINE):
                dev_deps.append(Dependency(name=m.group(1), version=m.group(2),
                                           is_dev=True, source_file=str(path)))

        return DependencyInfo(
            package_manager="cargo",
            dependencies=deps,
            dev_dependencies=dev_deps,
            source_files=[str(path)],
        )

    def _parse_pom_xml(self, path: Path) -> DependencyInfo:
        """Parse a Maven pom.xml file (regex-based, no external XML library)."""
        text = path.read_text(encoding="utf-8", errors="ignore")
        deps: List[Dependency] = []

        # Extract <dependency> blocks
        for block in re.finditer(r'<dependency>(.*?)</dependency>', text, re.DOTALL):
            content  = block.group(1)
            artifact = re.search(r'<artifactId>(.*?)</artifactId>', content)
            version  = re.search(r'<version>(.*?)</version>',      content)
            is_test  = bool(re.search(r'<scope>test</scope>',       content))
            if artifact:
                deps.append(Dependency(
                    name        = artifact.group(1).strip(),
                    version     = version.group(1).strip() if version else "",
                    is_dev      = is_test,
                    source_file = str(path),
                ))

        runtime = [d for d in deps if not d.is_dev]
        dev     = [d for d in deps if d.is_dev]

        return DependencyInfo(
            package_manager="maven",
            dependencies=runtime,
            dev_dependencies=dev,
            source_files=[str(path)],
        )

    def _parse_build_gradle(self, path: Path) -> DependencyInfo:
        """Parse a Gradle build.gradle file (regex-based)."""
        text = path.read_text(encoding="utf-8", errors="ignore")
        deps:     List[Dependency] = []
        dev_deps: List[Dependency] = []

        # e.g.  implementation 'com.example:library:1.0'
        #        testImplementation "junit:junit:4.13"
        for m in re.finditer(
            r"(implementation|api|compileOnly|testImplementation|runtimeOnly)"
            r"\s+['\"]([^'\"]+)['\"]",
            text
        ):
            scope, coord = m.group(1), m.group(2)
            parts   = coord.split(":")
            name    = parts[1] if len(parts) > 1 else coord
            version = parts[2] if len(parts) > 2 else ""
            is_dev  = scope.startswith("test")
            dep     = Dependency(name=name, version=version, is_dev=is_dev,
                                 source_file=str(path))
            (dev_deps if is_dev else deps).append(dep)

        return DependencyInfo(
            package_manager="gradle",
            dependencies=deps,
            dev_dependencies=dev_deps,
            source_files=[str(path)],
        )

    def _parse_pubspec_yaml(self, path: Path) -> DependencyInfo:
        """Parse a Flutter/Dart pubspec.yaml file (regex-based YAML parsing)."""
        text = path.read_text(encoding="utf-8", errors="ignore")
        deps:     List[Dependency] = []
        dev_deps: List[Dependency] = []

        dep_block = re.search(r'^dependencies:(.*?)(?=^\S|\Z)', text,
                               re.DOTALL | re.MULTILINE)
        if dep_block:
            for m in re.finditer(r'^\s{2}([a-z_]+):\s*(\^?[\d\.]+)?',
                                  dep_block.group(1), re.MULTILINE):
                if m.group(1) not in ("flutter", "sdk"):
                    deps.append(Dependency(name=m.group(1),
                                           version=m.group(2) or "",
                                           source_file=str(path)))

        dev_block = re.search(r'^dev_dependencies:(.*?)(?=^\S|\Z)', text,
                               re.DOTALL | re.MULTILINE)
        if dev_block:
            for m in re.finditer(r'^\s{2}([a-z_]+):\s*(\^?[\d\.]+)?',
                                  dev_block.group(1), re.MULTILINE):
                dev_deps.append(Dependency(name=m.group(1),
                                           version=m.group(2) or "",
                                           is_dev=True,
                                           source_file=str(path)))

        return DependencyInfo(
            package_manager="pub",
            dependencies=deps,
            dev_dependencies=dev_deps,
            source_files=[str(path)],
        )

# ============================================================================
# SECTION: ai.tools.project_scanner (ai/tools/project_scanner.py)
# ============================================================================
"""
ProjectScanner — the entry point for workspace analysis.

Before any AI model receives a prompt, OwnCode must completely
understand the user's project. ProjectScanner is the single component
responsible for that understanding.

It orchestrates all specialist analyzers, collects their output, and
assembles a single ProjectContext object that becomes the source of
truth for the entire AI pipeline session.

No files are modified. The scanner is entirely read-only.

Pipeline triggered by ProjectScanner.scan():

    TreeBuilder       — build in-memory folder tree
        ↓
    LanguageDetector  — calculate language percentages
        ↓
    FrameworkDetector — identify project framework
        ↓
    DependencyAnalyzer — parse manifest files
        ↓
    ProjectContext    — assembled and returned
"""

import time
from pathlib import Path
from typing import List, Optional

from core.logger import setup_logger
from core.exceptions import OwnCodeError
from ai.tools.tree_builder import TreeBuilder, TreeNode
from ai.tools.framework_detector import FrameworkDetector
from ai.tools.dependency_analyzer import DependencyAnalyzer
from ai.tools.language_detector import LanguageDetector

logger = setup_logger(__name__)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class ProjectScanError(OwnCodeError):
    """Raised when the project scan fails critically and cannot complete."""


# ---------------------------------------------------------------------------
# Known entry-point file names (checked in order during important-file scan)
# ---------------------------------------------------------------------------

_ENTRY_POINT_NAMES: List[str] = [
    "main.py", "app.py", "run.py", "server.py", "index.js",
    "index.ts", "main.js", "main.ts", "main.dart", "main.go",
    "main.rs", "Main.java", "Program.cs", "main.cpp",
]

_CONFIG_FILE_NAMES: List[str] = [
    ".env", ".env.example", "config.py", "settings.py", "settings.json",
    "config.json", "pyproject.toml", "package.json", "Cargo.toml",
    "pubspec.yaml", "pom.xml", "build.gradle", "CMakeLists.txt",
    "docker-compose.yml", "Dockerfile", ".gitignore", "go.mod",
]

_IMPORTANT_FILE_NAMES: List[str] = [
    "README.md", "README.rst", "CHANGELOG.md", "LICENSE",
    "CONTRIBUTING.md", ".github",
]


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

class ProjectScanner:
    """
    Orchestrates all workspace analysis tools and produces a ProjectContext.

    The scanner is the first component called when a user opens a
    workspace in OwnCode. The resulting ProjectContext is stored
    in memory and injected into every subsequent AI prompt so that
    agents always have complete structural awareness of the project.

    Args:
        workspace_root: Absolute path to the root of the project to analyze.

    Usage:
        scanner = ProjectScanner("/path/to/user/project")
        context = scanner.scan()
        print(context.summary())

    Raises:
        ProjectScanError: If the workspace_root does not exist or is not a directory.
    """

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        logger.info(f"ProjectScanner created for: {self.workspace_root}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(self) -> ProjectContext:
        """
        Run a full analysis of the workspace and return a ProjectContext.

        Calls all sub-analyzers in sequence. Each failure is logged and
        handled gracefully — no single analyzer failure will abort the
        entire scan. The resulting context will simply have None in that
        field and continue.

        Returns:
            A fully populated ProjectContext object.

        Raises:
            ProjectScanError: If the workspace root does not exist.
        """
        if not self.workspace_root.exists():
            raise ProjectScanError(
                f"Workspace does not exist: {self.workspace_root}"
            )
        if not self.workspace_root.is_dir():
            raise ProjectScanError(
                f"Workspace path is not a directory: {self.workspace_root}"
            )

        logger.info(f"Beginning project scan: {self.workspace_root}")
        scan_start = time.perf_counter()

        # ── Stage 1: Build tree ─────────────────────────────────────────
        tree_root = self._run_tree_builder()

        # ── Stage 2: Language detection ─────────────────────────────────
        language_breakdown = self._run_language_detector(tree_root)

        # ── Stage 3: Framework detection ────────────────────────────────
        framework_result = self._run_framework_detector()

        # ── Stage 4: Dependency analysis ────────────────────────────────
        dependency_info = self._run_dependency_analyzer()

        # ── Stage 5: Identify important files ───────────────────────────
        entry_points, config_files, important_files = self._find_important_files(tree_root)

        # ── Assemble context ─────────────────────────────────────────────
        elapsed_ms = (time.perf_counter() - scan_start) * 1000

        # Count stats from tree builder
        builder_tmp = TreeBuilder(self.workspace_root)
        # Re-use already built tree_root for stats
        total_files   = sum(1 for _ in tree_root.files()) if tree_root else 0
        total_folders = sum(1 for _ in tree_root.directories()) - 1 if tree_root else 0
        total_size    = sum(n.size_bytes for n in tree_root.files()) if tree_root else 0

        from datetime import datetime
        from ai.memory.project_context import ProjectContext
        context = ProjectContext(
            project_name          = self.workspace_root.name,
            root_path             = self.workspace_root,
            framework             = framework_result,
            languages             = language_breakdown,
            dependencies          = dependency_info,
            tree                  = tree_root,
            entry_points          = entry_points,
            config_files          = config_files,
            important_files       = important_files,
            total_files           = total_files,
            total_folders         = total_folders,
            total_size_bytes      = total_size,
            detected_pkg_manager  = dependency_info.package_manager if dependency_info else "",
            detected_build_system = self._detect_build_system(),
            last_scan_time        = datetime.utcnow(),
            scan_duration_ms      = round(elapsed_ms, 2),
        )

        logger.info(
            f"Scan complete in {elapsed_ms:.0f}ms — "
            f"{total_files} files, {total_folders} folders, "
            f"framework={context.framework_name!r}, "
            f"language={context.primary_language!r}."
        )
        return context

    # ------------------------------------------------------------------
    # Private — sub-analyzer wrappers
    # ------------------------------------------------------------------

    def _run_tree_builder(self) -> Optional[TreeNode]:
        """Build the in-memory folder tree. Returns None on failure."""
        try:
            builder = TreeBuilder(self.workspace_root)
            return builder.build()
        except Exception as exc:
            logger.error(f"TreeBuilder failed: {exc}", exc_info=True)
            return None

    def _run_language_detector(
        self, tree_root: Optional[TreeNode]
    ) -> Optional[object]:
        """Detect language composition from the tree. Returns None on failure."""
        if tree_root is None:
            logger.warning("Skipping language detection — tree not available.")
            return None
        try:
            detector = LanguageDetector()
            return detector.detect(tree_root)
        except Exception as exc:
            logger.error(f"LanguageDetector failed: {exc}", exc_info=True)
            return None

    def _run_framework_detector(self) -> Optional[object]:
        """Detect the project framework. Returns None on failure."""
        try:
            detector = FrameworkDetector(self.workspace_root)
            return detector.detect()
        except Exception as exc:
            logger.error(f"FrameworkDetector failed: {exc}", exc_info=True)
            return None

    def _run_dependency_analyzer(self) -> Optional[object]:
        """Parse dependency manifests. Returns None on failure."""
        try:
            analyzer = DependencyAnalyzer(self.workspace_root)
            return analyzer.analyze()
        except Exception as exc:
            logger.error(f"DependencyAnalyzer failed: {exc}", exc_info=True)
            return None

    def _find_important_files(
        self, tree_root: Optional[TreeNode]
    ) -> tuple[List[str], List[str], List[str]]:
        """
        Walk the tree to locate entry points, config files, and important docs.

        Returns:
            Tuple of (entry_points, config_files, important_files).
        """
        entry_points:    List[str] = []
        config_files:    List[str] = []
        important_files: List[str] = []

        if tree_root is None:
            return entry_points, config_files, important_files

        # Check root-level files by name
        root = self.workspace_root
        for name in _ENTRY_POINT_NAMES:
            p = root / name
            if p.exists():
                entry_points.append(str(p))

        for name in _CONFIG_FILE_NAMES:
            p = root / name
            if p.exists():
                config_files.append(str(p))

        for name in _IMPORTANT_FILE_NAMES:
            p = root / name
            if p.exists():
                important_files.append(str(p))

        return entry_points, config_files, important_files

    def _detect_build_system(self) -> str:
        """
        Detect the build system from the presence of known build files.

        Returns:
            Build system name string, or empty string if not detected.
        """
        checks = {
            "cmake":  ["CMakeLists.txt"],
            "gradle": ["build.gradle", "gradlew"],
            "maven":  ["pom.xml"],
            "cargo":  ["Cargo.toml"],
            "make":   ["Makefile", "GNUmakefile"],
            "meson":  ["meson.build"],
            "bazel":  ["BUILD", "WORKSPACE"],
            "npm":    ["package.json"],
        }
        root = self.workspace_root
        for system, files in checks.items():
            if any((root / f).exists() for f in files):
                return system
        return ""

# ============================================================================
# SECTION: ui.panels.explorer (ui/panels/explorer.py)
# ============================================================================
"""
Explorer — v2.2

Workspace file tree built on QFileSystemModel. Emits `file_activated(path)` when
a file is opened and exposes `set_root(path)`.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QFileSystemModel, QLabel,
    QStackedWidget, QScrollArea, QAbstractItemView, QInputDialog, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QDir, QModelIndex

from ui.design_system import get_design_system, Spacing, Radius, FontSize
from ui.widgets.controls import SectionHeader, TextButton, IconButton
from ui.settings_manager import get_settings_manager


class _RecentRow(QFrame):
    """A compact, clickable recent-project row for the Explorer empty state."""

    clicked = Signal(str)

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self._path = path
        self.setObjectName("RecentRow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(path)
        p = Path(path)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(Spacing.sm, Spacing.xs, Spacing.sm, Spacing.xs)
        lay.setSpacing(1)
        name = QLabel(p.name or str(p))
        name.setObjectName("RecentRowName")
        name.setMinimumWidth(0)
        loc = QLabel(str(p.parent))
        loc.setObjectName("RecentRowPath")
        loc.setMinimumWidth(0)
        lay.addWidget(name)
        lay.addWidget(loc)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._path)
            event.accept()
            return
        super().mousePressEvent(event)


class Explorer(QFrame):

    file_activated = Signal(str)
    file_previewed = Signal(str)
    open_folder_requested = Signal()
    open_recent_requested = Signal(str)
    clone_repo_requested = Signal()
    refresh_requested = Signal()
    file_renamed = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Explorer")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._root = None
        self._single_click = True
        self._preview = False
        self._model_initialized = False
        self._build()
        self.apply_workspace_settings()
        self._apply_style()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._header = SectionHeader("Explorer")
        self._open_btn = IconButton("folder", "Open Folder  (Ctrl+O)", size=24, icon_size=14)
        self._open_btn.clicked.connect(self.open_folder_requested.emit)
        self._refresh_btn = IconButton("refresh", "Refresh Explorer", size=24, icon_size=14)
        self._refresh_btn.clicked.connect(self.refresh_requested.emit)
        self._collapse_btn = IconButton("folder-collapse", "Collapse All Folders", size=24, icon_size=14)
        self._collapse_btn.clicked.connect(lambda: self._tree.collapseAll())
        self._header.add_action(self._open_btn)
        self._header.add_action(self._refresh_btn)
        self._header.add_action(self._collapse_btn)
        lay.addWidget(self._header)

        self._stack = QStackedWidget()

        # Empty state
        empty = QWidget()
        el = QVBoxLayout(empty)
        el.setContentsMargins(Spacing.md, Spacing.lg, Spacing.md, Spacing.md)
        el.setSpacing(Spacing.sm)

        msg = QLabel("No folder open yet.")
        msg.setProperty("role", "muted")
        msg.setWordWrap(True)
        el.addWidget(msg)

        open_btn = TextButton("Open Folder", icon_name="folder", variant="primary", tooltip="Open a project folder in the workspace (Ctrl+O)")
        open_btn.clicked.connect(self.open_folder_requested.emit)
        el.addWidget(open_btn)

        clone_btn = TextButton("Clone Repository", icon_name="git", tooltip="Clone a Git repository from GitHub or URL")
        clone_btn.clicked.connect(self.clone_repo_requested.emit)
        el.addWidget(clone_btn)

        el.addSpacing(Spacing.xs)

        recent_head = QLabel("RECENT")
        recent_head.setObjectName("RecentHeading")
        el.addWidget(recent_head)

        self._recent_scroll = QScrollArea()
        self._recent_scroll.setObjectName("RecentScroll")
        self._recent_scroll.setWidgetResizable(True)
        self._recent_scroll.setFrameShape(QScrollArea.NoFrame)
        self._recent_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        host = QWidget()
        self._recent_layout = QVBoxLayout(host)
        self._recent_layout.setContentsMargins(0, 0, 0, 0)
        self._recent_layout.setSpacing(Spacing.xxs)
        self._recent_scroll.setWidget(host)
        el.addWidget(self._recent_scroll, 1)

        self._recent: list = []
        self.set_recent_projects([])

        # Tree (lazily bound to filesystem root when set_root is called so startup is instant)
        self._model = QFileSystemModel(self)
        self._model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot | QDir.Hidden)

        tree_container = QWidget()
        tree_container.setObjectName("ExplorerTreeContainer")
        tcl = QVBoxLayout(tree_container)
        tcl.setContentsMargins(Spacing.xs, Spacing.xs, Spacing.xs, Spacing.xs)
        tcl.setSpacing(0)

        self._tree = QTreeView()
        self._tree.setObjectName("ExplorerTree")
        self._tree.setHeaderHidden(True)
        self._tree.setAnimated(True)
        self._tree.setIndentation(14)
        self._tree.setUniformRowHeights(True)
        self._tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._tree.clicked.connect(self._on_click)
        self._tree.doubleClicked.connect(self._on_double_click)
        tcl.addWidget(self._tree, 1)

        self._stack.addWidget(empty)           # 0
        self._stack.addWidget(tree_container)  # 1
        lay.addWidget(self._stack, 1)

    def _ensure_model_attached(self):
        if not self._model_initialized:
            self._model_initialized = True
            self._tree.setModel(self._model)
            for col in (1, 2, 3):
                self._tree.hideColumn(col)

    def has_tree_focus(self) -> bool:
        return self._tree.hasFocus()

    def rename_selected(self) -> bool:
        """Rename the selected file or folder and refresh the model."""
        index = self._tree.currentIndex()
        if not index.isValid():
            return False
        old_path = Path(self._model.filePath(index))
        if not old_path.exists():
            return False
        new_name, ok = QInputDialog.getText(
            self, "Rename", f"Rename '{old_path.name}' to:", text=old_path.name)
        new_name = new_name.strip()
        if not ok or not new_name or new_name == old_path.name:
            return False
        new_path = old_path.parent / new_name
        if new_path.exists():
            QMessageBox.warning(self, "Already Exists",
                                f"'{new_name}' already exists.")
            return False
        try:
            old_path.rename(new_path)
        except OSError as exc:
            QMessageBox.critical(self, "Rename Failed", str(exc))
            return False
        self.file_renamed.emit(str(old_path), str(new_path))
        self.set_root(self._root or str(old_path.parent))
        return True

    # ── settings ──────────────────────────────────────────────────────────
    def apply_workspace_settings(self):
        self._single_click = bool(self._setting("single_click_open", True))
        self._preview = bool(self._setting("preview_single_click", False))
        self._tree.setExpandsOnDoubleClick(not self._single_click)

    @staticmethod
    def _setting(key: str, fallback):
        try:
            return get_settings_manager().get("workspace", key, fallback)
        except Exception:
            return fallback

    def set_recent_projects(self, projects: list):
        self._recent = list(projects or [])
        lay = self._recent_layout
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        if not self._recent:
            placeholder = QLabel("No recent projects yet.")
            placeholder.setProperty("role", "muted")
            placeholder.setContentsMargins(Spacing.sm, Spacing.xs, Spacing.sm, 0)
            lay.addWidget(placeholder)
            lay.addStretch(1)
            return
        for path in self._recent[:8]:
            row = _RecentRow(path)
            row.clicked.connect(self.open_recent_requested.emit)
            lay.addWidget(row)
        lay.addStretch(1)

    def set_root(self, path: str):
        if not path or not Path(path).exists():
            self._stack.setCurrentIndex(0)
            return
        self._ensure_model_attached()
        self._root = str(path)
        idx = self._model.setRootPath(self._root)
        self._tree.setRootIndex(idx)
        root_path_obj = Path(self._root)
        self._header.set_title(root_path_obj.name or self._root)
        if hasattr(self, "_mc_name"):
            self._mc_name.setText(root_path_obj.name or "project")
            self._mc_path.setText(str(root_path_obj))
            try:
                c_h_files = len(list(root_path_obj.glob("*.c"))) + len(list(root_path_obj.glob("*.h")))
                if c_h_files > 0:
                    self._mc_stats.setText(f"{c_h_files} C/H files")
                else:
                    total_f = len([f for f in root_path_obj.iterdir() if f.is_file()])
                    self._mc_stats.setText(f"{total_f} files")
            except Exception:
                self._mc_stats.setText("active")
        self._stack.setCurrentIndex(1)

    def reveal(self, path: str, force: bool = False):
        if not path or not self._model_initialized:
            return
        if not force:
            try:
                if not bool(get_settings_manager().get(
                        "workspace", "reveal_active_file", True)):
                    return
            except Exception:
                pass
        index = self._model.index(str(path))
        if not index.isValid():
            return
        self._tree.setCurrentIndex(index)
        self._tree.scrollTo(index, QAbstractItemView.PositionAtCenter)

    def _on_click(self, index: QModelIndex):
        self._single_click = bool(self._setting("single_click_open", True))
        self._preview = bool(self._setting("preview_single_click", False))
        if not self._single_click:
            return
        if self._model.isDir(index):
            self._tree.setExpanded(index, not self._tree.isExpanded(index))
            return
        path = self._model.filePath(index)
        if not path:
            return
        if self._preview:
            self.file_previewed.emit(path)
        else:
            self.file_activated.emit(path)

    def _on_double_click(self, index: QModelIndex):
        path = self._model.filePath(index)
        if path and not self._model.isDir(index):
            self.file_activated.emit(path)

    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #Explorer, #ExplorerTreeContainer {{ background: {c.surface}; }}
            #RecentHeading {{
                color: {c.text_faint};
                font-size: {FontSize.micro}px;
                font-weight: 600;
                letter-spacing: 1px;
            }}
            #RecentScroll {{ background: transparent; border: none; }}
            #RecentRow {{ border-radius: {Radius.sm}px; }}
            #RecentRow:hover {{ background: {c.surface_overlay}; }}
            #RecentRowName {{ color: {c.text_secondary}; font-size: {FontSize.small}px; font-weight: 500; }}
            #RecentRowPath {{ color: {c.text_faint}; font-size: {FontSize.micro}px; }}
            #ExplorerTree {{
                background: {c.surface};
                color: {c.text_secondary};
                border: none;
                font-size: {FontSize.small}px;
                outline: none;
            }}
            #ExplorerTree::item {{
                padding: 4px 6px;
                margin: 1px 2px;
                border-radius: {Radius.sm}px;
                border-left: 2px solid transparent;
            }}
            #ExplorerTree::item:hover {{
                background: {c.surface_raised};
                color: {c.text_primary};
            }}
            #ExplorerTree::item:selected {{
                background: {c.selection};
                color: {c.text_primary};
                border-left: 2px solid {c.accent};
            }}
            QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
            QScrollBar::handle:vertical {{
                background: {c.scrollbar}; border-radius: 5px; min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {c.scrollbar_hover}; }}
            QScrollBar::add-line, QScrollBar::sub-line {{
                width: 0; height: 0; background: transparent;
            }}
        """)

    def refresh_theme(self):
        self._apply_style()
