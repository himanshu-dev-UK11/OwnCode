"""
Consolidated Module: agent.context_and_memory

Combines: ai.memory.project_memory, ai.memory.decision_memory, ai.memory.project_context, ai.context.token_estimator, ai.context.symbol_index, ai.context.file_import_graph, ai.context.dependency_resolver, ai.context.context_cache, ai.context.context_selector, ai.context.context_ranker, ai.context.context_builder, ai.context.ai_context_store, ai.context.context_engine
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['ai.memory.project_memory', 'ai.memory.decision_memory', 'ai.memory.project_context', 'ai.context.token_estimator', 'ai.context.symbol_index', 'ai.context.file_import_graph', 'ai.context.dependency_resolver', 'ai.context.context_cache', 'ai.context.context_selector', 'ai.context.context_ranker', 'ai.context.context_builder', 'ai.context.ai_context_store', 'ai.context.context_engine']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ai.memory.project_memory (ai/memory/project_memory.py)
# ============================================================================
"""
ProjectMemory — persists project-level AI knowledge across sessions.

Stores high-level findings about the open workspace: architecture
decisions, known issues, key files, and summaries from past scans.
This lets the AI "remember" the project without re-scanning on every
request.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import setup_logger

logger = setup_logger(__name__)

_STORAGE_FILE = Path("config/project_memory.json")


@dataclass
class ProjectFact:
    """A single piece of remembered knowledge about the project."""
    fact_id:    str
    category:   str          # "architecture" | "issue" | "convention" | "file" | "general"
    content:    str
    confidence: float = 1.0  # 0-1
    source:     str = ""     # where this fact came from
    timestamp:  str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata:   Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ProjectFact":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class ProjectMemory:
    """
    In-memory + disk-backed store of project knowledge.

    Usage:
        memory = ProjectMemory()
        memory.remember(category="architecture", content="Uses MVC pattern")
        memory.remember(category="issue", content="main.py is too large (1200 lines)")
        ctx = memory.build_context_string()  # inject into AI prompt
    """

    def __init__(self, storage_file: Optional[str] = None) -> None:
        self._file = Path(storage_file) if storage_file else _STORAGE_FILE
        self._facts: List[ProjectFact] = []
        self._project_name: str = ""
        self._project_root: str = ""
        self._load()
        logger.info(f"ProjectMemory initialized ({len(self._facts)} facts)")

    # ── Public API ─────────────────────────────────────────────────────────

    def set_project(self, name: str, root: str) -> None:
        """Set the active project. Clears memory if the project changed."""
        if self._project_root and self._project_root != root:
            logger.info(f"ProjectMemory: project changed — clearing old facts")
            self._facts.clear()
        self._project_name = name
        self._project_root = root
        self._save()

    def remember(
        self,
        category: str,
        content:  str,
        confidence: float = 1.0,
        source:   str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProjectFact:
        """Store a new fact about the project."""
        import uuid
        fact = ProjectFact(
            fact_id=str(uuid.uuid4())[:8],
            category=category,
            content=content[:500],
            confidence=confidence,
            source=source,
            metadata=metadata or {},
        )
        # Avoid exact duplicates
        existing = [f for f in self._facts if f.content == content]
        if not existing:
            self._facts.append(fact)
            self._save()
            logger.debug(f"ProjectMemory: remembered [{category}] {content[:60]}")
        return fact

    def update_from_task(self, task_id: str, outcome: str, files_changed: List[str]) -> None:
        """Update memory after a task completes."""
        if files_changed:
            self.remember(
                category="file",
                content=f"Task {task_id[:8]} ({outcome}) modified: {', '.join(files_changed[:5])}",
                source="task_executor",
            )

    def get_by_category(self, category: str) -> List[ProjectFact]:
        """Return all facts in a category."""
        return [f for f in self._facts if f.category == category]

    def get_all(self) -> List[ProjectFact]:
        return list(self._facts)

    def forget(self, fact_id: str) -> bool:
        """Delete a single fact by id. Returns True if one was removed."""
        before = len(self._facts)
        self._facts = [f for f in self._facts if f.fact_id != fact_id]
        removed = len(self._facts) != before
        if removed:
            self._save()
        return removed

    def set_pinned(self, fact_id: str, pinned: bool = True) -> bool:
        """Pin/unpin a fact (stored in its metadata). Returns True if found.

        Pinned facts are surfaced first and are never trimmed by the 300-fact
        cap because callers can filter on `metadata['pinned']`.
        """
        for f in self._facts:
            if f.fact_id == fact_id:
                f.metadata["pinned"] = bool(pinned)
                self._save()
                return True
        return False

    def update_content(self, fact_id: str, content: str) -> bool:
        """Edit the text of an existing fact. Returns True if found."""
        for f in self._facts:
            if f.fact_id == fact_id:
                f.content = content[:500]
                self._save()
                return True
        return False

    def build_context_string(self, max_facts: int = 15) -> str:
        """Build a compact string suitable for injection into AI prompts."""
        if not self._facts:
            return ""
        selected = sorted(
            self._facts, key=lambda f: f.confidence, reverse=True
        )[:max_facts]
        lines = [f"Project memory for '{self._project_name}':"]
        for f in selected:
            lines.append(f"  [{f.category}] {f.content}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all stored facts."""
        self._facts.clear()
        self._save()
        logger.info("ProjectMemory cleared")

    # ── Persistence ────────────────────────────────────────────────────────

    def _load(self) -> None:
        try:
            if self._file.exists():
                data = json.loads(self._file.read_text(encoding="utf-8"))
                self._project_name = data.get("project_name", "")
                self._project_root = data.get("project_root", "")
                self._facts = [ProjectFact.from_dict(f) for f in data.get("facts", [])]
        except Exception as e:
            logger.warning(f"ProjectMemory: could not load from disk: {e}")
            self._facts = []

    def _save(self) -> None:
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "project_name": self._project_name,
                "project_root": self._project_root,
                "facts": [f.to_dict() for f in self._facts[-300:]],
            }
            self._file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"ProjectMemory: could not save to disk: {e}")


# ============================================================================
# SECTION: ai.memory.decision_memory (ai/memory/decision_memory.py)
# ============================================================================
"""
DecisionMemory — persists AI decisions across sessions.

Stores every significant decision made during task execution so the AI
can reference past choices, avoid repeating mistakes, and explain its
reasoning to the user.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import setup_logger

logger = setup_logger(__name__)

_DECISION_STORAGE_FILE = Path("config/decision_memory.json")


@dataclass
class Decision:
    """A single recorded AI decision."""
    decision_id:  str
    task_id:      str
    prompt:       str
    choice:       str          # what the AI chose to do
    reasoning:    str          # why it made that choice
    outcome:      str = ""     # "success" | "failure" | "unknown"
    model_used:   str = ""
    timestamp:    str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata:     Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Decision":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class DecisionMemory:
    """
    In-memory + disk-backed store of AI decisions.

    Usage:
        memory = DecisionMemory()
        memory.record(task_id="abc", prompt="...", choice="...", reasoning="...")
        recent = memory.get_recent(limit=10)
    """

    def __init__(self, storage_file: Optional[str] = None) -> None:
        self._file = Path(storage_file) if storage_file else _DECISION_STORAGE_FILE
        self._decisions: List[Decision] = []
        self._load()
        logger.info(f"DecisionMemory initialized ({len(self._decisions)} past decisions)")

    # ── Public API ─────────────────────────────────────────────────────────

    def record(
        self,
        task_id:   str,
        prompt:    str,
        choice:    str,
        reasoning: str,
        outcome:   str = "unknown",
        model_used: str = "",
        metadata:  Optional[Dict[str, Any]] = None,
    ) -> Decision:
        """Record a new decision and persist to disk."""
        import uuid
        decision = Decision(
            decision_id=str(uuid.uuid4())[:8],
            task_id=task_id,
            prompt=prompt[:200],
            choice=choice[:500],
            reasoning=reasoning[:1000],
            outcome=outcome,
            model_used=model_used,
            metadata=metadata or {},
        )
        self._decisions.append(decision)
        self._save()
        logger.debug(f"Decision recorded: {decision.decision_id} (task={task_id[:8]})")
        return decision

    def update_outcome(self, decision_id: str, outcome: str) -> bool:
        """Update the outcome of a previously recorded decision."""
        for d in self._decisions:
            if d.decision_id == decision_id:
                d.outcome = outcome
                self._save()
                return True
        return False

    def get_recent(self, limit: int = 20) -> List[Decision]:
        """Return the most recent N decisions."""
        return list(reversed(self._decisions))[:limit]

    def get_for_task(self, task_id: str) -> List[Decision]:
        """Return all decisions for a specific task."""
        return [d for d in self._decisions if d.task_id == task_id]

    def get_failures(self) -> List[Decision]:
        """Return all decisions that resulted in failure."""
        return [d for d in self._decisions if d.outcome == "failure"]

    def summary_for_prompt(self, limit: int = 5) -> str:
        """Return a compact summary for injection into AI prompts."""
        recent = self.get_recent(limit)
        if not recent:
            return "No past decisions recorded."
        lines = ["Recent decisions:"]
        for d in recent:
            lines.append(
                f"  [{d.timestamp[:10]}] {d.choice[:80]} "
                f"(outcome={d.outcome})"
            )
        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all decisions (e.g. on new project open)."""
        self._decisions.clear()
        self._save()
        logger.info("DecisionMemory cleared")

    # ── Persistence ────────────────────────────────────────────────────────

    def _load(self) -> None:
        try:
            if self._file.exists():
                data = json.loads(self._file.read_text(encoding="utf-8"))
                self._decisions = [Decision.from_dict(d) for d in data.get("decisions", [])]
        except Exception as e:
            logger.warning(f"DecisionMemory: could not load from disk: {e}")
            self._decisions = []

    def _save(self) -> None:
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            payload = {"decisions": [d.to_dict() for d in self._decisions[-500:]]}
            self._file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"DecisionMemory: could not save to disk: {e}")


# ============================================================================
# SECTION: ai.memory.project_context (ai/memory/project_context.py)
# ============================================================================
"""
ProjectContext — single source of truth describing a scanned workspace.

This dataclass holds every piece of structural information that
OwnCode needs to understand a user's project before any
planning, routing, or coding begins. It is populated exclusively
by ProjectScanner and consumed by the AI pipeline components.

Persisting this object in memory means the filesystem only needs
to be walked once per session.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    # Avoid circular imports at runtime; used only for type annotations.
    from ai.tools.tree_builder import TreeNode
    from ai.tools.framework_detector import FrameworkResult
    from ai.tools.dependency_analyzer import DependencyInfo
    from ai.tools.language_detector import LanguageBreakdown


@dataclass
class ProjectContext:
    """
    A complete structural snapshot of a user's workspace.

    This is the object the entire AI pipeline consumes.
    It is built once by ProjectScanner and stored in ProjectMemory
    so it can be injected into any agent prompt without re-scanning.

    Attributes:
        project_name:       Inferred from the root directory name.
        root_path:          Absolute path to the workspace root.
        framework:          Detected framework result (name + confidence).
        languages:          Language breakdown (percentages per language).
        dependencies:       Parsed dependency info (libraries + versions).
        tree:               Root TreeNode of the complete in-memory folder tree.
        important_files:    Absolute paths to high-value files
                            (main entry points, config files, etc.).
        entry_points:       Likely application entry-point file paths.
        config_files:       Configuration file paths found in the workspace.
        total_files:        Total number of non-ignored files in the workspace.
        total_folders:      Total number of non-ignored directories.
        total_size_bytes:   Sum of all file sizes in bytes.
        detected_pkg_manager: The package manager string (e.g. "pip", "npm").
        detected_build_system: Build system if detected (e.g. "gradle", "cmake").
        created_time:       UTC timestamp when this context object was created.
        last_scan_time:     UTC timestamp of the most recent scan that populated it.
        scan_duration_ms:   How long the last scan took in milliseconds.
        metadata:           Arbitrary extra key-value pairs for future use.
    """

    # ── Identity ─────────────────────────────────────────────────────────
    project_name: str
    root_path:    Path

    # ── Framework & Languages ─────────────────────────────────────────────
    framework:    Optional["FrameworkResult"]  = None
    languages:    Optional["LanguageBreakdown"] = None
    dependencies: Optional["DependencyInfo"]  = None

    # ── File System Structure ─────────────────────────────────────────────
    tree:          Optional["TreeNode"] = field(default=None, repr=False)
    important_files: List[str]          = field(default_factory=list)
    entry_points:    List[str]          = field(default_factory=list)
    config_files:    List[str]          = field(default_factory=list)

    # ── Statistics ────────────────────────────────────────────────────────
    total_files:           int   = 0
    total_folders:         int   = 0
    total_size_bytes:      int   = 0
    detected_pkg_manager:  str   = ""
    detected_build_system: str   = ""

    # ── Timing ───────────────────────────────────────────────────────────
    created_time:     datetime = field(default_factory=datetime.utcnow)
    last_scan_time:   Optional[datetime] = None
    scan_duration_ms: float              = 0.0

    # ── Extensibility ─────────────────────────────────────────────────────
    metadata: Dict[str, object] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def framework_name(self) -> str:
        """Return the detected framework name string, or 'Unknown'."""
        return self.framework.framework.value if self.framework else "Unknown"

    @property
    def primary_language(self) -> str:
        """Return the dominant language name, or 'Unknown'."""
        if self.languages and self.languages.primary_language:
            return self.languages.primary_language
        return "Unknown"

    @property
    def total_size_kb(self) -> float:
        """Project size in kilobytes (rounded to 2 dp)."""
        return round(self.total_size_bytes / 1024, 2)

    @property
    def total_size_mb(self) -> float:
        """Project size in megabytes (rounded to 2 dp)."""
        return round(self.total_size_bytes / (1024 * 1024), 2)

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def summary(self) -> str:
        """
        Return a human-readable one-paragraph summary of the project context.

        This is the string that gets injected into AI model prompts so
        every agent immediately understands the project without re-scanning.
        """
        lang_lines = ""
        if self.languages:
            top = self.languages.languages[:5]
            lang_lines = ", ".join(f"{ls.language} ({ls.percentage}%)" for ls in top)

        dep_count = (
            len(self.dependencies.all_dependencies) if self.dependencies else 0
        )

        return (
            f"Project: {self.project_name}\n"
            f"Path: {self.root_path}\n"
            f"Framework: {self.framework_name}"
            + (f" (confidence: {self.framework.confidence:.0%})" if self.framework else "")
            + f"\nPrimary Language: {self.primary_language}\n"
            f"Languages: {lang_lines or 'N/A'}\n"
            f"Dependencies: {dep_count} packages "
            f"(manager: {self.detected_pkg_manager or 'unknown'})\n"
            f"Files: {self.total_files} | Folders: {self.total_folders} "
            f"| Size: {self.total_size_kb} KB\n"
            f"Entry Points: {', '.join(self.entry_points) or 'None detected'}\n"
            f"Last Scanned: {self.last_scan_time or 'Never'}"
        )

    def to_dict(self) -> Dict[str, object]:
        """
        Return a JSON-serializable dictionary of the context.

        The tree node is excluded as it is not serializable.
        """
        return {
            "project_name":          self.project_name,
            "root_path":             str(self.root_path),
            "framework":             self.framework_name,
            "framework_confidence":  self.framework.confidence if self.framework else 0,
            "primary_language":      self.primary_language,
            "languages":             [
                {"language": ls.language, "percentage": ls.percentage}
                for ls in (self.languages.languages if self.languages else [])
            ],
            "dependency_count":      len(self.dependencies.all_dependencies) if self.dependencies else 0,
            "package_manager":       self.detected_pkg_manager,
            "build_system":          self.detected_build_system,
            "total_files":           self.total_files,
            "total_folders":         self.total_folders,
            "total_size_bytes":      self.total_size_bytes,
            "entry_points":          self.entry_points,
            "config_files":          self.config_files,
            "important_files":       self.important_files,
            "last_scan_time":        str(self.last_scan_time),
            "scan_duration_ms":      self.scan_duration_ms,
        }

    def __repr__(self) -> str:
        return (
            f"ProjectContext(name={self.project_name!r}, "
            f"framework={self.framework_name!r}, "
            f"language={self.primary_language!r}, "
            f"files={self.total_files})"
        )


# ============================================================================
# SECTION: ai.context.token_estimator (ai/context/token_estimator.py)
# ============================================================================
"""
token_estimator.py — Token budget management.

Estimates how many LLM tokens a given piece of text or an entire
ContextPackage will require, enforces model limits, and suggests
which files to drop when the budget is exceeded.

The estimator uses a characters-per-token heuristic (default 4) which
is accurate enough for budget planning without requiring a real tokenizer.
"""

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Tuple

from core.logger import setup_logger

if TYPE_CHECKING:
    from ai.context.context_engine import ContextPackage

logger = setup_logger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────
DEFAULT_CHARS_PER_TOKEN: int = 4
DEFAULT_MODEL_LIMIT:     int = 128_000   # Conservative default (128 K tokens)
PROMPT_OVERHEAD_TOKENS:  int = 512       # System prompt + formatting overhead


@dataclass
class BudgetReport:
    """Result of a budget check against a specific model limit."""
    total_tokens:   int
    model_limit:    int
    fits:           bool
    excess_tokens:  int          # 0 when fits=True
    utilisation_pct: float       # 0-100


class TokenEstimator:
    """
    Lightweight token estimator using character count heuristics.

    Args:
        chars_per_token: Average characters per token for the target
                         tokenizer family (GPT/Gemini ≈ 4, LLaMA ≈ 3.5).
    """

    def __init__(self, chars_per_token: int = DEFAULT_CHARS_PER_TOKEN) -> None:
        self._cpt = chars_per_token
        logger.debug(f"TokenEstimator initialised (chars_per_token={chars_per_token}).")

    # ── Core estimates ─────────────────────────────────────────────────────

    def estimate(self, text: str) -> int:
        """Return estimated token count for an arbitrary string."""
        if not text:
            return 0
        return math.ceil(len(text) / self._cpt)

    def estimate_file(self, path: str, content: str) -> int:
        """Estimate tokens for a single file (path header + content)."""
        header = f"# File: {path}\n"
        return self.estimate(header + content)

    def estimate_package(self, package: "ContextPackage") -> int:
        """
        Estimate total tokens for an entire ContextPackage.

        Accounts for:
          - The user prompt
          - All selected file contents
          - Symbol summaries
          - Formatting overhead
        """
        total = PROMPT_OVERHEAD_TOKENS
        total += self.estimate(package.prompt)

        for sf in package.selected_files:
            total += self.estimate_file(sf.path, sf.content)

        # Symbol summaries are terse; count only their names
        if package.symbols:
            symbol_text = "\n".join(
                f"{s.kind} {s.name} @ {s.file}:{s.line}"
                for s in package.symbols
            )
            total += self.estimate(symbol_text)

        return total

    # ── Budget enforcement ─────────────────────────────────────────────────

    def check_budget(
        self,
        package: "ContextPackage",
        model_limit: int = DEFAULT_MODEL_LIMIT,
    ) -> BudgetReport:
        """
        Check whether a ContextPackage fits within the model's token limit.

        Returns a BudgetReport describing utilisation and any excess.
        """
        total = self.estimate_package(package)
        fits  = total <= model_limit
        excess = max(0, total - model_limit)
        utilisation = round(total / model_limit * 100, 1) if model_limit else 0.0

        logger.debug(
            f"Budget check: {total} / {model_limit} tokens "
            f"({utilisation}%) — {'OK' if fits else 'EXCEEDS'}"
        )
        return BudgetReport(
            total_tokens=total,
            model_limit=model_limit,
            fits=fits,
            excess_tokens=excess,
            utilisation_pct=utilisation,
        )

    def suggest_reduction(
        self,
        package: "ContextPackage",
        model_limit: int = DEFAULT_MODEL_LIMIT,
    ) -> List[str]:
        """
        Suggest which files to remove when the package exceeds the budget.

        Strategy: drop lowest-scored files first until budget is satisfied.
        Returns a list of file paths that should be excluded.
        """
        report = self.check_budget(package, model_limit)
        if report.fits:
            return []

        # Sort by score ascending (drop cheapest-value files first)
        sorted_files = sorted(package.selected_files, key=lambda f: f.score)
        to_drop: List[str] = []
        saved_tokens = 0
        needed = report.excess_tokens

        for sf in sorted_files:
            if saved_tokens >= needed:
                break
            file_tokens = self.estimate_file(sf.path, sf.content)
            to_drop.append(sf.path)
            saved_tokens += file_tokens
            logger.debug(f"Suggest dropping '{sf.path}' (−{file_tokens} tokens).")

        return to_drop


# ============================================================================
# SECTION: ai.context.symbol_index (ai/context/symbol_index.py)
# ============================================================================
"""
symbol_index.py — Per-file and per-project symbol indexing.

Indexes every class, function, method, variable, and constant in a
project so the Context Engine can surface relevant symbols alongside
selected files.

Python files are parsed with the built-in `ast` module for accuracy.
Other languages (JS, TS, Java, C#, C++) fall back to fast regex
patterns that cover the most common declaration forms.

Thread safety: SymbolIndex is stateless — each call is independent.
"""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from core.logger import setup_logger

logger = setup_logger(__name__)


# ── Data contract ──────────────────────────────────────────────────────────

@dataclass
class SymbolEntry:
    """
    One indexed symbol in the project.

    Attributes:
        name:       Symbol identifier (e.g. "login", "AuthManager").
        kind:       One of "class", "function", "method", "variable",
                    "constant", "interface", "enum".
        file:       Absolute path to the source file.
        line:       1-based line number of the definition.
        parent:     Enclosing class name (for methods), else "".
        references: File paths where this symbol is referenced (populated
                    lazily by DependencyResolver when needed).
    """
    name:       str
    kind:       str
    file:       str
    line:       int
    parent:     str = ""
    references: List[str] = field(default_factory=list)

    def __repr__(self) -> str:  # noqa: D105
        parent_str = f".{self.parent}" if self.parent else ""
        return f"<Symbol {self.kind} {parent_str}{self.name} @ {Path(self.file).name}:{self.line}>"


# ── Language-specific regex patterns ──────────────────────────────────────

# JS/TS — covers function declarations, arrow functions, classes, const/let/var
_JS_PATTERNS: List[tuple[str, str]] = [
    (r"^\s*(?:export\s+)?(?:default\s+)?class\s+(\w+)",        "class"),
    (r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)",       "function"),
    (r"^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(", "function"),  # arrow
    (r"^\s*(?:export\s+)?const\s+(\w+)\s*=",                   "constant"),
    (r"^\s*(?:export\s+)?(?:let|var)\s+(\w+)\s*=",             "variable"),
    (r"^\s*interface\s+(\w+)",                                  "interface"),
    (r"^\s*enum\s+(\w+)",                                       "enum"),
]

# Java/C# — classes, methods, interfaces, enums
_JAVA_PATTERNS: List[tuple[str, str]] = [
    (r"^\s*(?:public|private|protected|internal|static|abstract|sealed)?\s*class\s+(\w+)",     "class"),
    (r"^\s*(?:public|private|protected|internal|static|abstract|override|virtual)?\s*(?:void|int|str|bool|String|List|Dict|[A-Z]\w*)\s+(\w+)\s*\(",  "function"),
    (r"^\s*interface\s+(\w+)",                                                                   "interface"),
    (r"^\s*enum\s+(\w+)",                                                                        "enum"),
]

# C++ — functions, classes, structs, enums
_CPP_PATTERNS: List[tuple[str, str]] = [
    (r"^\s*class\s+(\w+)",      "class"),
    (r"^\s*struct\s+(\w+)",     "class"),
    (r"^\s*enum\s+(?:class\s+)?(\w+)", "enum"),
    (r"^(?:\w[\w\s\*&<>:,]+)\s+(\w+)\s*\(",  "function"),
]

_EXTENSION_PATTERNS: Dict[str, List[tuple[str, str]]] = {
    ".js":   _JS_PATTERNS,
    ".jsx":  _JS_PATTERNS,
    ".ts":   _JS_PATTERNS,
    ".tsx":  _JS_PATTERNS,
    ".java": _JAVA_PATTERNS,
    ".cs":   _JAVA_PATTERNS,
    ".cpp":  _CPP_PATTERNS,
    ".cc":   _CPP_PATTERNS,
    ".cxx":  _CPP_PATTERNS,
    ".h":    _CPP_PATTERNS,
    ".hpp":  _CPP_PATTERNS,
}


class SymbolIndex:
    """
    Indexes symbols in individual files or entire project trees.

    Usage::

        index = SymbolIndex()
        symbols = index.index_file("/path/to/auth.py")
        project_index = index.index_project("/path/to/project")
    """

    # ── Public API ─────────────────────────────────────────────────────────

    def index_file(self, path: str) -> List[SymbolEntry]:
        """
        Return all symbols found in a single file.

        Chooses the best parser for the file's extension.
        Returns an empty list on parse errors (never raises).
        """
        p = Path(path)
        if not p.is_file():
            return []

        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning(f"SymbolIndex: cannot read {path}: {exc}")
            return []

        ext = p.suffix.lower()

        if ext == ".py":
            return self._index_python(path, content)
        elif ext in _EXTENSION_PATTERNS:
            return self._index_regex(path, content, _EXTENSION_PATTERNS[ext])
        else:
            return []

    def index_project(self, root: str) -> Dict[str, List[SymbolEntry]]:
        """
        Walk *root* and index every supported source file.

        Returns a dict: absolute_path → list of SymbolEntry.
        Ignores hidden dirs, __pycache__, node_modules, build/, dist/.
        """
        root_path = Path(root)
        result: Dict[str, List[SymbolEntry]] = {}

        _SKIP_DIRS = {
            "__pycache__", ".git", "node_modules",
            "build", "dist", ".venv", "venv", "env",
            ".mypy_cache", ".pytest_cache",
        }
        _SUPPORTED_EXTS = {".py", ".js", ".jsx", ".ts", ".tsx",
                           ".java", ".cs", ".cpp", ".cc", ".cxx", ".h", ".hpp"}

        for p in root_path.rglob("*"):
            if any(part in _SKIP_DIRS for part in p.parts):
                continue
            if p.suffix.lower() not in _SUPPORTED_EXTS:
                continue
            if not p.is_file():
                continue

            symbols = self.index_file(str(p))
            if symbols:
                result[str(p)] = symbols

        total = sum(len(v) for v in result.values())
        logger.debug(
            f"SymbolIndex.index_project: {len(result)} files, "
            f"{total} symbols in '{root_path.name}'."
        )
        return result

    def search(
        self,
        project_index: Dict[str, List[SymbolEntry]],
        query: str,
        kinds: Optional[List[str]] = None,
    ) -> List[SymbolEntry]:
        """
        Search the project index for symbols whose name contains *query*.

        Args:
            project_index: Output of :meth:`index_project`.
            query:         Case-insensitive substring to match.
            kinds:         If provided, restrict to these symbol kinds.
        """
        q = query.lower()
        results: List[SymbolEntry] = []

        for symbols in project_index.values():
            for sym in symbols:
                if kinds and sym.kind not in kinds:
                    continue
                if q in sym.name.lower():
                    results.append(sym)

        return sorted(results, key=lambda s: s.name.lower())

    # ── Python parser (AST) ────────────────────────────────────────────────

    def _index_python(self, path: str, content: str) -> List[SymbolEntry]:
        """Parse Python source with ast for accurate symbol extraction."""
        try:
            tree = ast.parse(content, filename=path)
        except SyntaxError as exc:
            logger.debug(f"SymbolIndex: AST parse error in {path}: {exc}")
            return []

        symbols: List[SymbolEntry] = []
        self._walk_python_node(tree, path, symbols, parent_class="")
        return symbols

    def _walk_python_node(
        self,
        node: ast.AST,
        path: str,
        out: List[SymbolEntry],
        parent_class: str,
    ) -> None:
        """Recursively visit AST nodes and collect symbol definitions."""
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                out.append(SymbolEntry(
                    name=child.name, kind="class",
                    file=path, line=child.lineno, parent=parent_class,
                ))
                # Recurse into class body to capture methods
                self._walk_python_node(child, path, out, parent_class=child.name)

            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                kind = "method" if parent_class else "function"
                out.append(SymbolEntry(
                    name=child.name, kind=kind,
                    file=path, line=child.lineno, parent=parent_class,
                ))
                # Do NOT recurse further into function bodies (too noisy)

            elif isinstance(child, ast.Assign) and not parent_class:
                # Module-level assignments: constants and variables
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        kind = "constant" if target.id.isupper() else "variable"
                        out.append(SymbolEntry(
                            name=target.id, kind=kind,
                            file=path, line=child.lineno, parent="",
                        ))

            elif isinstance(child, ast.AnnAssign) and not parent_class:
                # Module-level annotated assignments
                if isinstance(child.target, ast.Name):
                    out.append(SymbolEntry(
                        name=child.target.id, kind="variable",
                        file=path, line=child.lineno, parent="",
                    ))

    # ── Regex parser (non-Python) ──────────────────────────────────────────

    def _index_regex(
        self,
        path: str,
        content: str,
        patterns: List[tuple[str, str]],
    ) -> List[SymbolEntry]:
        """Apply a list of (pattern, kind) pairs line-by-line."""
        compiled = [(re.compile(pat), kind) for pat, kind in patterns]
        symbols: List[SymbolEntry] = []

        for lineno, line in enumerate(content.splitlines(), start=1):
            for regex, kind in compiled:
                m = regex.match(line)
                if m:
                    name = m.group(1)
                    # Skip short/generic names
                    if len(name) > 1:
                        symbols.append(SymbolEntry(
                            name=name, kind=kind,
                            file=path, line=lineno,
                        ))
                    break  # First matching pattern wins

        return symbols


# ============================================================================
# SECTION: ai.context.file_import_graph (ai/context/file_import_graph.py)
# ============================================================================
"""
file_import_graph.py — Project-wide file import graph.

Builds a directed graph where every node is a source file and every
edge represents an import relationship:

    A → B  means file A imports from file B.

The graph answers two questions efficiently:
    1. "What does this file depend on?" (forward edges — imports)
    2. "What would break if I change this file?" (reverse edges — imported_by)

Currently supports Python (ast-based) with regex fallback for
JS/TS (import/require statements).

This graph is used by DependencyResolver to follow import chains
and by the Context Engine for future impact-analysis features.
"""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from core.logger import setup_logger

logger = setup_logger(__name__)

# Directories to skip when building the graph
_SKIP_DIRS: Set[str] = {
    "__pycache__", ".git", "node_modules",
    "build", "dist", ".venv", "venv", "env",
    ".mypy_cache", ".pytest_cache", "migrations",
}

# JS/TS import patterns
_JS_IMPORT_RE = re.compile(
    r"""
    (?:import\s+.*?\s+from\s+['"](.+?)['"])   # ES6 import ... from '...'
    |
    (?:require\s*\(\s*['"](.+?)['"]\s*\))      # require('...')
    """,
    re.VERBOSE,
)


@dataclass
class GraphStats:
    """Summary statistics for the import graph."""
    total_files:    int
    total_edges:    int
    most_imported:  Optional[str]   # file imported by the most others
    most_importing: Optional[str]   # file that imports the most others


class FileImportGraph:
    """
    Directed import graph for an entire project.

    Attributes:
        imports:     file → set of files it imports (forward edges).
        imported_by: file → set of files that import it (reverse edges).
    """

    def __init__(self) -> None:
        self.imports:     Dict[str, Set[str]] = {}
        self.imported_by: Dict[str, Set[str]] = {}
        self._root: Optional[Path] = None

    # ── Builder ────────────────────────────────────────────────────────────

    @classmethod
    def build(cls, root_path: str) -> "FileImportGraph":
        """
        Walk *root_path* and build the full import graph.

        Returns a populated FileImportGraph. Errors in individual files
        are silently skipped so the overall graph is always returned.
        """
        graph = cls()
        root  = Path(root_path)
        graph._root = root

        # Collect all supported source files
        py_files  = list(_iter_files(root, {".py"}))
        js_files  = list(_iter_files(root, {".js", ".jsx", ".ts", ".tsx"}))

        logger.debug(
            f"FileImportGraph: scanning {len(py_files)} .py and "
            f"{len(js_files)} JS/TS files in '{root.name}'."
        )

        for p in py_files:
            graph._process_python(p, root)

        for p in js_files:
            graph._process_js(p, root)

        total_edges = sum(len(v) for v in graph.imports.values())
        logger.debug(
            f"FileImportGraph built: {len(graph.imports)} nodes, "
            f"{total_edges} edges."
        )
        return graph

    # ── Query API ──────────────────────────────────────────────────────────

    def get_imports(self, file_path: str) -> Set[str]:
        """Return the set of files that *file_path* imports."""
        return self.imports.get(str(Path(file_path)), set())

    def get_imported_by(self, file_path: str) -> Set[str]:
        """Return the set of files that import *file_path*."""
        return self.imported_by.get(str(Path(file_path)), set())

    def all_files(self) -> List[str]:
        """Return all files in the graph (nodes with at least one edge)."""
        return list(self.imports.keys())

    def stats(self) -> GraphStats:
        """Return summary statistics about the graph."""
        total_edges = sum(len(v) for v in self.imports.values())

        most_imported = None
        if self.imported_by:
            most_imported = max(
                self.imported_by, key=lambda k: len(self.imported_by[k])
            )

        most_importing = None
        if self.imports:
            most_importing = max(self.imports, key=lambda k: len(self.imports[k]))

        return GraphStats(
            total_files=len(self.imports),
            total_edges=total_edges,
            most_imported=most_imported,
            most_importing=most_importing,
        )

    # ── Python import resolver ─────────────────────────────────────────────

    def _process_python(self, path: Path, root: Path) -> None:
        """Parse Python imports and add edges to the graph."""
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            tree    = ast.parse(content, filename=str(path))
        except (OSError, SyntaxError) as exc:
            logger.debug(f"FileImportGraph: skipping {path.name}: {exc}")
            return

        file_key = str(path)
        if file_key not in self.imports:
            self.imports[file_key] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    resolved = self._resolve_python_module(alias.name, root)
                    if resolved:
                        self._add_edge(file_key, resolved)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    resolved = self._resolve_python_module(node.module, root)
                    if resolved:
                        self._add_edge(file_key, resolved)

    def _resolve_python_module(self, module_name: str, root: Path) -> Optional[str]:
        """
        Convert a Python module name to an absolute file path.

        Only resolves modules that exist *within* the project root.
        Third-party and stdlib modules are ignored (return None).
        """
        # Convert dotted module name to path components
        parts = module_name.replace("-", "_").split(".")

        # Try as a package file: a/b/c.py
        candidate = root.joinpath(*parts).with_suffix(".py")
        if candidate.is_file():
            return str(candidate)

        # Try as a package init: a/b/c/__init__.py
        init_candidate = root.joinpath(*parts, "__init__.py")
        if init_candidate.is_file():
            return str(init_candidate)

        return None  # external / stdlib module

    # ── JS/TS import resolver ──────────────────────────────────────────────

    def _process_js(self, path: Path, root: Path) -> None:
        """Parse JS/TS import statements and add edges to the graph."""
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.debug(f"FileImportGraph: skipping {path.name}: {exc}")
            return

        file_key = str(path)
        if file_key not in self.imports:
            self.imports[file_key] = set()

        for match in _JS_IMPORT_RE.finditer(content):
            specifier = match.group(1) or match.group(2)
            if not specifier or not specifier.startswith("."):
                continue  # skip third-party / absolute imports

            resolved = self._resolve_js_specifier(specifier, path, root)
            if resolved:
                self._add_edge(file_key, resolved)

    def _resolve_js_specifier(
        self, specifier: str, importer: Path, root: Path
    ) -> Optional[str]:
        """Resolve a relative JS/TS import specifier to an absolute path."""
        base  = importer.parent
        target = (base / specifier).resolve()

        # Try exact path, then with extensions
        for suffix in ("", ".js", ".jsx", ".ts", ".tsx"):
            candidate = target.with_suffix(suffix) if suffix else target
            if candidate.is_file() and str(candidate).startswith(str(root)):
                return str(candidate)

        # Try as index file
        for suffix in ("/index.js", "/index.ts", "/index.jsx", "/index.tsx"):
            candidate = Path(str(target) + suffix)
            if candidate.is_file() and str(candidate).startswith(str(root)):
                return str(candidate)

        return None

    # ── Graph edge management ──────────────────────────────────────────────

    def _add_edge(self, source: str, target: str) -> None:
        """Add a directed edge source → target and update the reverse index."""
        if source == target:
            return  # No self-loops

        self.imports.setdefault(source, set()).add(target)
        self.imported_by.setdefault(target, set()).add(source)


# ── Helper ─────────────────────────────────────────────────────────────────

def _iter_files(root: Path, extensions: Set[str]):
    """Yield all files under *root* with the given extensions, skipping ignored dirs."""
    for p in root.rglob("*"):
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in extensions and p.is_file():
            yield p


# ============================================================================
# SECTION: ai.context.dependency_resolver (ai/context/dependency_resolver.py)
# ============================================================================
"""
dependency_resolver.py — Recursive import-chain follower.

Given a set of "seed" files (the files the Context Engine has
already decided are relevant), DependencyResolver walks the
FileImportGraph to collect every file those seeds depend on,
up to a configurable depth.

This prevents the common failure mode where the AI receives
"login.py" but not the "auth.py" and "user.py" it imports,
causing the model to hallucinate implementations for those symbols.

Depth semantics:
    depth 0 → seed files only (no resolution)
    depth 1 → direct imports of seeds
    depth 2 → imports of imports
    depth 3 → (default) three levels deep
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from core.logger import setup_logger
from ai.context.file_import_graph import FileImportGraph

logger = setup_logger(__name__)

DEFAULT_MAX_DEPTH = 3


@dataclass
class ResolvedChain:
    """
    The full dependency chain built from a set of seed files.

    Attributes:
        files:         All resolved file paths (seeds + dependencies),
                       ordered by discovery (BFS).
        depth_map:     file_path → depth at which it was discovered.
        seed_files:    The original input seeds.
        max_depth:     The depth cap that was applied.
    """
    files:      List[str]
    depth_map:  Dict[str, int]
    seed_files: List[str]
    max_depth:  int

    def at_depth(self, depth: int) -> List[str]:
        """Return files discovered at a specific depth."""
        return [f for f, d in self.depth_map.items() if d == depth]


class DependencyResolver:
    """
    Follows import chains from a set of seed files using a BFS strategy.

    Args:
        import_graph: A pre-built FileImportGraph for the project.
        max_depth:    Maximum number of hops from any seed file.
    """

    def __init__(
        self,
        import_graph: FileImportGraph,
        max_depth: int = DEFAULT_MAX_DEPTH,
    ) -> None:
        self._graph     = import_graph
        self._max_depth = max_depth
        logger.debug(
            f"DependencyResolver initialised (max_depth={max_depth})."
        )

    # ── Public API ─────────────────────────────────────────────────────────

    def resolve(
        self,
        seed_files: List[str],
        max_depth: Optional[int] = None,
    ) -> ResolvedChain:
        """
        Resolve all dependencies reachable from *seed_files*.

        Uses a breadth-first search so shallower dependencies are
        discovered first and the depth_map is accurate.

        Args:
            seed_files: Files the Context Engine already selected.
            max_depth:  Override the instance default for this call.

        Returns:
            ResolvedChain with all discovered paths and their depths.
        """
        depth_limit = max_depth if max_depth is not None else self._max_depth

        visited:   Dict[str, int] = {}   # path → discovery depth
        queue:     List[tuple[str, int]] = []

        # Initialise BFS with seeds at depth 0
        for seed in seed_files:
            if seed not in visited:
                visited[seed] = 0
                queue.append((seed, 0))

        # BFS
        head = 0
        while head < len(queue):
            current, depth = queue[head]
            head += 1

            if depth >= depth_limit:
                continue  # Respect depth cap — don't enqueue children

            children = self._graph.get_imports(current)
            for child in children:
                if child not in visited:
                    visited[child] = depth + 1
                    queue.append((child, depth + 1))
                    logger.debug(
                        f"Dependency resolved: depth={depth+1} "
                        f"{self._short(current)} → {self._short(child)}"
                    )

        # Build ordered output list (BFS order = discovery order)
        ordered = [path for path, _ in queue]

        chain = ResolvedChain(
            files=ordered,
            depth_map=visited,
            seed_files=list(seed_files),
            max_depth=depth_limit,
        )

        dep_count = len(ordered) - len(seed_files)
        logger.info(
            f"DependencyResolver: {len(seed_files)} seeds → "
            f"{dep_count} dependencies found (depth ≤ {depth_limit})."
        )
        return chain

    def reverse_resolve(
        self,
        file_path: str,
        max_depth: int = 1,
    ) -> List[str]:
        """
        Find files that *import* the given file (impact analysis).

        Useful for answering "what would break if I change this file?"
        Returns the set of files that directly or transitively
        import *file_path*, up to *max_depth* hops.
        """
        visited: Set[str] = set()
        queue:   List[tuple[str, int]] = [(file_path, 0)]
        results: List[str] = []

        while queue:
            current, depth = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            if current != file_path:
                results.append(current)

            if depth < max_depth:
                for parent in self._graph.get_imported_by(current):
                    if parent not in visited:
                        queue.append((parent, depth + 1))

        return results

    # ── Internals ──────────────────────────────────────────────────────────

    @staticmethod
    def _short(path: str) -> str:
        """Return a short display name (last 2 path components)."""
        from pathlib import Path
        p = Path(path)
        return str(p.parent.name + "/" + p.name)


# ============================================================================
# SECTION: ai.context.context_cache (ai/context/context_cache.py)
# ============================================================================
"""
context_cache.py — Thread-safe LRU cache for ContextPackage objects.

Caches previously built context packages and reuses them when an
identical (prompt + file + mtime fingerprint) request arrives.
Invalidation is file-level: any cached package that included a
changed file is evicted immediately.

Design decisions:
  - Uses collections.OrderedDict for O(1) LRU eviction.
  - All public methods acquire a threading.Lock for thread safety.
  - Cache key is a stable SHA-256 hash of the cache fingerprint string.
  - max_size defaults to 50 packages (tunable at construction time).
"""

import hashlib
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

from core.logger import setup_logger

if TYPE_CHECKING:
    from ai.context.context_engine import ContextPackage

logger = setup_logger(__name__)

DEFAULT_CACHE_SIZE = 50


@dataclass
class CacheEntry:
    """One slot in the LRU cache."""
    package:    "ContextPackage"
    key:        str
    created_at: datetime = field(default_factory=datetime.utcnow)
    hit_count:  int = 0
    file_paths: List[str] = field(default_factory=list)  # files used to build it


@dataclass
class CacheStats:
    """Snapshot of cache health metrics."""
    size:        int
    max_size:    int
    hits:        int
    misses:      int
    evictions:   int
    hit_rate_pct: float


class ContextCache:
    """
    Thread-safe LRU cache for ContextPackage objects.

    Args:
        max_size: Maximum number of packages to store before evicting
                  the least-recently-used entry.
    """

    def __init__(self, max_size: int = DEFAULT_CACHE_SIZE) -> None:
        self._max_size   = max_size
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock       = threading.Lock()

        # Stats (read without lock is acceptable for monitoring)
        self._hits      = 0
        self._misses    = 0
        self._evictions = 0

        logger.debug(f"ContextCache initialised (max_size={max_size}).")

    # ── Cache key generation ───────────────────────────────────────────────

    @staticmethod
    def make_key(
        prompt:       str,
        current_file: str,
        file_mtimes:  Dict[str, float],
    ) -> str:
        """
        Build a stable SHA-256 cache key.

        The key incorporates the prompt, current file, and the modification
        timestamps of every file in the candidate set so that any file change
        immediately yields a cache miss.
        """
        mtime_part = "|".join(
            f"{p}:{t}"
            for p, t in sorted(file_mtimes.items())
        )
        raw = f"{prompt}::{current_file}::{mtime_part}"
        return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()

    # ── Public API ─────────────────────────────────────────────────────────

    def get(self, key: str) -> Optional["ContextPackage"]:
        """
        Return the cached ContextPackage for *key*, or None on a miss.

        On a hit the entry is moved to the end of the LRU queue
        (most-recently-used).
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                logger.debug(f"Cache MISS — key={key[:12]}…")
                return None

            # Move to most-recently-used position
            self._store.move_to_end(key)
            entry.hit_count += 1
            self._hits += 1
            logger.debug(
                f"Cache HIT — key={key[:12]}… "
                f"(hit #{entry.hit_count}, age={self._age(entry)}s)"
            )
            return entry.package

    def put(
        self,
        key:      str,
        package:  "ContextPackage",
        file_paths: Optional[List[str]] = None,
    ) -> None:
        """
        Store *package* under *key*.

        If the cache is full, the least-recently-used entry is evicted first.
        """
        with self._lock:
            if key in self._store:
                # Update existing entry and move to end
                self._store.move_to_end(key)
                self._store[key].package    = package
                self._store[key].created_at = datetime.utcnow()
                self._store[key].file_paths = file_paths or []
            else:
                # Evict LRU if at capacity
                if len(self._store) >= self._max_size:
                    evicted_key, _ = self._store.popitem(last=False)
                    self._evictions += 1
                    logger.debug(f"Cache evict LRU — key={evicted_key[:12]}…")

                self._store[key] = CacheEntry(
                    package=package,
                    key=key,
                    file_paths=file_paths or [],
                )
                logger.debug(
                    f"Cache PUT — key={key[:12]}… "
                    f"(size now {len(self._store)}/{self._max_size})"
                )

    def invalidate_file(self, path: str) -> int:
        """
        Evict every cache entry that was built using *path*.

        Called when a file changes on disk so stale packages are
        never returned. Returns the number of entries evicted.
        """
        norm = str(Path(path))
        evicted = 0
        with self._lock:
            keys_to_remove = [
                k for k, e in self._store.items()
                if norm in (str(Path(p)) for p in e.file_paths)
            ]
            for k in keys_to_remove:
                del self._store[k]
                evicted += 1
                self._evictions += 1

        if evicted:
            logger.debug(
                f"Cache invalidated {evicted} entries for changed file: {path}"
            )
        return evicted

    def clear(self) -> None:
        """Remove all entries from the cache."""
        with self._lock:
            count = len(self._store)
            self._store.clear()
        logger.debug(f"Cache cleared ({count} entries removed).")

    def stats(self) -> CacheStats:
        """Return a snapshot of cache performance metrics."""
        total = self._hits + self._misses
        hit_rate = round(self._hits / total * 100, 1) if total else 0.0
        return CacheStats(
            size=len(self._store),
            max_size=self._max_size,
            hits=self._hits,
            misses=self._misses,
            evictions=self._evictions,
            hit_rate_pct=hit_rate,
        )

    # ── Internals ──────────────────────────────────────────────────────────

    @staticmethod
    def _age(entry: CacheEntry) -> int:
        """Age of an entry in whole seconds."""
        delta = datetime.utcnow() - entry.created_at
        return int(delta.total_seconds())


# ============================================================================
# SECTION: ai.context.context_selector (ai/context/context_selector.py)
# ============================================================================
"""
context_selector.py — Keyword-driven file relevance filter.

Chooses which files in the project are *candidates* for inclusion
in the context package, based on the user's prompt and the
currently open file.

Strategy
--------
1.  Extract intent keywords from the prompt (nouns, verbs, identifiers).
2.  Score every project file by how well its path/name matches those keywords.
3.  Always include the current file and its direct parents.
4.  Always exclude low-value directories (build artifacts, Docker, docs).
5.  Return the top N candidates for downstream ranking.

This is a purely heuristic, zero-AI filter — fast enough to run
synchronously on every keystroke if needed.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set

from core.logger import setup_logger

logger = setup_logger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────

# Directories whose contents are almost never relevant to AI coding tasks
_EXCLUDE_DIRS: Set[str] = {
    "__pycache__", ".git", ".svn", ".hg",
    "node_modules", "vendor", "third_party",
    "build", "dist", "out", "target", "bin", "obj",
    ".venv", "venv", "env", "site-packages",
    ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "migrations", ".terraform", "docker",
}

# File patterns that are almost never code-relevant for a coding task
_EXCLUDE_PATTERNS: Set[str] = {
    "readme.md", "changelog.md", "license", "license.md",
    "license.txt", "authors", "contributing.md", "code_of_conduct.md",
    ".gitignore", ".dockerignore", ".editorconfig",
    "dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example", ".env.sample",
}

# Extensions treated as "always exclude" (binary / generated)
_EXCLUDE_EXTS: Set[str] = {
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".mp3", ".mp4", ".avi", ".mov",
    ".zip", ".tar", ".gz", ".bz2",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".lock",  # package lock files are rarely useful for coding tasks
}

# Extensions treated as "config — include only when needed"
_CONFIG_EXTS: Set[str] = {
    ".toml", ".yaml", ".yml", ".json", ".ini", ".cfg",
    ".env", ".conf", ".config",
}

# Maximum number of candidates to return (before ranking)
DEFAULT_MAX_CANDIDATES = 30


@dataclass
class CandidateFile:
    """A file that passed the selection filter."""
    path:             str
    keyword_score:    float   # 0.0 → 1.0 — how well name matched prompt keywords
    is_current_file:  bool = False
    is_config_file:   bool = False
    reason:           str  = ""


class ContextSelector:
    """
    Selects a subset of project files as candidates for context inclusion.

    Args:
        max_candidates: Upper bound on the number of files returned.
    """

    def __init__(self, max_candidates: int = DEFAULT_MAX_CANDIDATES) -> None:
        self._max = max_candidates

    # ── Public API ─────────────────────────────────────────────────────────

    def select(
        self,
        prompt:        str,
        all_files:     List[str],
        current_file:  Optional[str] = None,
        config_files:  Optional[List[str]] = None,
    ) -> List[CandidateFile]:
        """
        Choose candidate files from *all_files* relevant to *prompt*.

        Args:
            prompt:       The raw user prompt.
            all_files:    Absolute paths of all project files.
            current_file: The file currently open in the editor (always included).
            config_files: Known config files (always included if budget allows).

        Returns:
            List of CandidateFile, sorted by keyword_score descending.
        """
        keywords = self._extract_keywords(prompt)
        logger.debug(
            f"ContextSelector: {len(all_files)} files, "
            f"keywords={keywords!r}"
        )

        current_norm = str(Path(current_file)) if current_file else ""
        config_norm  = {str(Path(c)) for c in (config_files or [])}
        candidates:  List[CandidateFile] = []

        for raw_path in all_files:
            p = Path(raw_path)
            norm = str(p)

            # ── Hard excludes ──────────────────────────────────────────
            if self._is_excluded(p):
                continue

            is_current = (norm == current_norm)
            is_config  = (norm in config_norm or p.suffix.lower() in _CONFIG_EXTS)

            # ── Keyword scoring ────────────────────────────────────────
            score = self._score_path(p, keywords)

            # Always include current file (score bump)
            if is_current:
                score = max(score, 1.0)
                reason = "current file"
            elif score == 0.0 and not is_config:
                continue  # No keyword match and not a config — skip
            elif is_config:
                reason = "config file"
                score  = max(score, 0.1)  # baseline so it passes threshold
            else:
                reason = f"keyword match ({score:.2f})"

            candidates.append(CandidateFile(
                path=norm,
                keyword_score=round(score, 3),
                is_current_file=is_current,
                is_config_file=is_config,
                reason=reason,
            ))

        # Sort by score descending, cap at max
        candidates.sort(key=lambda c: (c.is_current_file, c.keyword_score), reverse=True)
        result = candidates[:self._max]

        logger.info(
            f"ContextSelector: {len(all_files)} files → "
            f"{len(result)} candidates selected."
        )
        return result

    # ── Keyword extraction ─────────────────────────────────────────────────

    @staticmethod
    def _extract_keywords(prompt: str) -> List[str]:
        """
        Extract meaningful keywords from the user prompt.

        Splits on whitespace/punctuation, lower-cases everything, and
        removes very common English stop words that carry no file-name signal.
        """
        _STOP_WORDS = {
            "a", "an", "the", "in", "on", "at", "to", "for", "of", "and",
            "or", "but", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "can", "that", "this", "these", "those",
            "it", "its", "my", "your", "our", "their", "how", "what", "why",
            "when", "where", "which", "who",
            "fix", "add", "update", "change", "make", "create", "delete",
            "remove", "refactor", "improve", "implement", "write", "use",
        }

        tokens = re.findall(r"[a-zA-Z_]\w*", prompt.lower())
        return [t for t in tokens if t not in _STOP_WORDS and len(t) >= 3]

    # ── Scoring ────────────────────────────────────────────────────────────

    @staticmethod
    def _score_path(path: Path, keywords: List[str]) -> float:
        """
        Score a file path against a list of keywords.

        Checks the stem and parent directory names (case-insensitive).
        A full stem match scores higher than a partial substring match.
        """
        if not keywords:
            return 0.0

        # Parts to check: file stem and each parent dir name
        check_parts = [path.stem.lower()]
        check_parts += [p.lower() for p in path.parts[:-1]]

        total   = 0.0
        matched = 0

        for kw in keywords:
            kw_l = kw.lower()
            for part in check_parts:
                if part == kw_l:
                    total += 1.0   # Exact match
                    matched += 1
                    break
                elif kw_l in part or part in kw_l:
                    total += 0.5   # Partial match
                    matched += 1
                    break

        if matched == 0:
            return 0.0

        # Normalise to [0, 1]
        return min(1.0, total / len(keywords))

    # ── Exclusion logic ────────────────────────────────────────────────────

    @staticmethod
    def _is_excluded(path: Path) -> bool:
        """
        Return True if the file should be unconditionally excluded.

        Checks:
          - Any path component is a known exclude directory.
          - The file name (lower-cased) is in the exclude patterns set.
          - The file extension is a binary/generated type.
        """
        # Check each component (not just leaf)
        for part in path.parts:
            if part.lower() in _EXCLUDE_DIRS:
                return True

        # Check file name
        if path.name.lower() in _EXCLUDE_PATTERNS:
            return True

        # Check extension
        if path.suffix.lower() in _EXCLUDE_EXTS:
            return True

        return False


# ============================================================================
# SECTION: ai.context.context_ranker (ai/context/context_ranker.py)
# ============================================================================
"""
context_ranker.py — Multi-factor file relevance scorer.

Takes the candidate files from ContextSelector and assigns each one
a composite relevance score. The top-N files are forwarded to the
context builder for inclusion.

Scoring factors (weights sum to 1.0)
-------------------------------------
  current_file    0.30  — the file the user has open right now
  keyword_match   0.25  — how well the file name matched prompt keywords
  dependency      0.20  — is this file in the resolved dependency chain?
  git_modified    0.15  — was this file modified in the current git session?
  recently_opened 0.10  — does the user have it open in another tab?

The weights are designed so that the current file always wins, but
dependency files beat recently-opened files because they are structurally
necessary, not just convenient.
"""

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

from core.logger import setup_logger
from ai.context.context_selector import CandidateFile

logger = setup_logger(__name__)

# ── Weight constants ───────────────────────────────────────────────────────
W_CURRENT_FILE    = 0.30
W_KEYWORD_MATCH   = 0.25
W_DEPENDENCY      = 0.20
W_GIT_MODIFIED    = 0.15
W_RECENTLY_OPENED = 0.10

# Number of ranked files to return by default
DEFAULT_TOP_N = 15


@dataclass
class RankedFile:
    """
    A file that has been scored for context inclusion.

    Attributes:
        path:          Absolute file path.
        score:         Composite relevance score in [0, 1].
        reasons:       Human-readable explanations for why this file was included.
        is_dependency: True if the file was pulled in by the dependency resolver.
        dep_depth:     Import chain depth from a seed file (0 = seed itself).
    """
    path:          str
    score:         float
    reasons:       List[str]
    is_dependency: bool = False
    dep_depth:     int  = 0


class ContextRanker:
    """
    Multi-factor ranker for context file candidates.

    Args:
        top_n: Maximum number of files to return after ranking.
    """

    def __init__(self, top_n: int = DEFAULT_TOP_N) -> None:
        self._top_n = top_n

    # ── Public API ─────────────────────────────────────────────────────────

    def rank(
        self,
        candidates:       List[CandidateFile],
        dependency_files: Optional[List[str]] = None,
        dep_depth_map:    Optional[Dict[str, int]] = None,
        git_modified:     Optional[Set[str]] = None,
        open_tabs:        Optional[List[str]] = None,
        current_file:     Optional[str] = None,
    ) -> List[RankedFile]:
        """
        Score and sort candidate files by composite relevance.

        Args:
            candidates:       Output of ContextSelector.select().
            dependency_files: Files discovered by DependencyResolver.
            dep_depth_map:    Map of file → discovery depth from seed.
            git_modified:     Paths of files changed in git working tree.
            open_tabs:        Paths of files open in the editor's tab bar.
            current_file:     Path of the file currently focused in editor.

        Returns:
            List of RankedFile, sorted by score descending, capped at top_n.
        """
        dep_set   = set(dependency_files or [])
        depth_map = dep_depth_map or {}
        git_set   = {str(Path(p)) for p in (git_modified or [])}
        tabs_set  = {str(Path(p)) for p in (open_tabs or [])}
        current   = str(Path(current_file)) if current_file else ""

        ranked: List[RankedFile] = []

        for candidate in candidates:
            norm = str(Path(candidate.path))
            score, reasons = self._compute_score(
                norm, candidate, dep_set, depth_map,
                git_set, tabs_set, current,
            )

            is_dep   = norm in dep_set
            dep_depth = depth_map.get(norm, 0)

            ranked.append(RankedFile(
                path=norm,
                score=round(score, 4),
                reasons=reasons,
                is_dependency=is_dep,
                dep_depth=dep_depth,
            ))

        # Also rank dependency files that weren't in the original candidates
        for dep_path in dep_set:
            norm = str(Path(dep_path))
            if not any(r.path == norm for r in ranked):
                dep_depth = depth_map.get(norm, 1)
                dep_score = self._dependency_score(dep_depth)
                reasons   = [f"dependency (depth {dep_depth})"]

                if norm in git_set:
                    dep_score += W_GIT_MODIFIED * 0.5
                    reasons.append("git modified")

                ranked.append(RankedFile(
                    path=norm,
                    score=round(dep_score, 4),
                    reasons=reasons,
                    is_dependency=True,
                    dep_depth=dep_depth,
                ))

        ranked.sort(key=lambda r: r.score, reverse=True)
        result = ranked[:self._top_n]

        logger.info(
            f"ContextRanker: {len(ranked)} files ranked → "
            f"top {len(result)} selected "
            f"(highest score: {result[0].score if result else 0:.3f})."
        )
        return result

    # ── Scoring internals ──────────────────────────────────────────────────

    def _compute_score(
        self,
        norm:       str,
        candidate:  CandidateFile,
        dep_set:    Set[str],
        depth_map:  Dict[str, int],
        git_set:    Set[str],
        tabs_set:   Set[str],
        current:    str,
    ) -> tuple[float, List[str]]:
        """Compute composite score and build reason list for one file."""
        score   = 0.0
        reasons: List[str] = []

        # ── Factor: current file ───────────────────────────────────────
        if norm == current:
            score += W_CURRENT_FILE
            reasons.append("current file")

        # ── Factor: keyword match ──────────────────────────────────────
        if candidate.keyword_score > 0.0:
            kw_contribution = W_KEYWORD_MATCH * candidate.keyword_score
            score += kw_contribution
            reasons.append(f"keyword match ({candidate.keyword_score:.2f})")

        # ── Factor: dependency chain ───────────────────────────────────
        if norm in dep_set:
            dep_depth = depth_map.get(norm, 1)
            dep_contribution = self._dependency_score(dep_depth)
            score += dep_contribution
            reasons.append(f"dependency (depth {dep_depth})")

        # ── Factor: git modified ───────────────────────────────────────
        if norm in git_set:
            score += W_GIT_MODIFIED
            reasons.append("git modified")

        # ── Factor: open in tab ────────────────────────────────────────
        if norm in tabs_set:
            score += W_RECENTLY_OPENED
            reasons.append("open in editor tab")

        return score, reasons

    @staticmethod
    def _dependency_score(depth: int) -> float:
        """
        Return a dependency weight that decays with import depth.

        depth 0 → W_DEPENDENCY (seed file itself)
        depth 1 → W_DEPENDENCY * 0.8
        depth 2 → W_DEPENDENCY * 0.6
        depth 3 → W_DEPENDENCY * 0.4
        """
        decay = max(0.4, 1.0 - (depth * 0.2))
        return W_DEPENDENCY * decay


# ============================================================================
# SECTION: ai.context.context_builder (ai/context/context_builder.py)
# ============================================================================
"""
context_builder.py — Raw context material collector.

The ContextBuilder is the first stage of the Context Engine pipeline.
It does not rank or filter — it simply gathers every raw piece of
information that the engine might want to include:

  • All project files (paths only)
  • Currently open editor tabs
  • Git-modified files in the working tree
  • Config files and entry points from ProjectContext
  • Known documentation / knowledge files
  • File modification times (for cache fingerprinting)

All I/O is lazy: file contents are NOT read here. They are read only
for the files that survive ranking, inside ContextEngine.build().
"""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, TYPE_CHECKING

from core.logger import setup_logger

if TYPE_CHECKING:
    from ai.memory.project_context import ProjectContext

logger = setup_logger(__name__)

# Directories whose files are never collected as raw candidates
_SKIP_DIRS: Set[str] = {
    "__pycache__", ".git", ".svn", "node_modules", "vendor",
    "build", "dist", "out", "target", "bin", "obj",
    ".venv", "venv", "env", ".mypy_cache", ".pytest_cache",
    ".terraform", "docker",
}

# Extensions that are worth collecting as candidate source files
_SOURCE_EXTS: Set[str] = {
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".java", ".kt", ".cs", ".cpp", ".cc", ".c", ".h", ".hpp",
    ".go", ".rs", ".rb", ".php", ".swift", ".dart", ".scala",
    ".toml", ".yaml", ".yml", ".json", ".ini", ".cfg", ".env",
    ".md", ".txt",
}


@dataclass
class BuilderResult:
    """
    Raw context materials returned by ContextBuilder.

    Attributes:
        all_files:    Paths of all scannable files in the project.
        open_tabs:    Paths of files currently open in the editor.
        git_modified: Paths of files changed in the git working tree.
        config_files: Config/entry-point files from ProjectContext.
        doc_files:    Documentation / knowledge markdown files.
        file_mtimes:  path → mtime (float) for cache fingerprinting.
    """
    all_files:    List[str]              = field(default_factory=list)
    open_tabs:    List[str]              = field(default_factory=list)
    git_modified: List[str]             = field(default_factory=list)
    config_files: List[str]             = field(default_factory=list)
    doc_files:    List[str]             = field(default_factory=list)
    file_mtimes:  Dict[str, float]      = field(default_factory=dict)


class ContextBuilder:
    """
    Collects raw context materials for a project.

    Args:
        project_root: Absolute path to the workspace root directory.
    """

    def __init__(self, project_root: str) -> None:
        self._root = Path(project_root)
        logger.debug(f"ContextBuilder initialised (root='{self._root.name}').")

    # ── Public API ─────────────────────────────────────────────────────────

    def collect(
        self,
        project_context: Optional["ProjectContext"] = None,
        open_tabs:       Optional[List[str]] = None,
    ) -> BuilderResult:
        """
        Gather all raw context materials from the project.

        Args:
            project_context: ProjectContext from the last scan (may be None).
            open_tabs:       Paths currently open in the editor tab bar.

        Returns:
            BuilderResult with all gathered paths and mtimes.
        """
        result = BuilderResult()

        # ── 1. All source files ────────────────────────────────────────
        result.all_files = self._scan_files()
        logger.debug(f"ContextBuilder: {len(result.all_files)} source files collected.")

        # ── 2. File modification times ─────────────────────────────────
        result.file_mtimes = self._collect_mtimes(result.all_files)

        # ── 3. Open editor tabs ────────────────────────────────────────
        result.open_tabs = [str(Path(t)) for t in (open_tabs or [])]

        # ── 4. Git-modified files ──────────────────────────────────────
        result.git_modified = self._git_modified_files()

        # ── 5. Config + entry points from ProjectContext ───────────────
        if project_context:
            result.config_files = list(
                project_context.config_files + project_context.entry_points
            )
        else:
            result.config_files = self._find_config_files()

        # ── 6. Documentation files ─────────────────────────────────────
        result.doc_files = self._find_doc_files()

        return result

    # ── File scanning ──────────────────────────────────────────────────────

    def _scan_files(self) -> List[str]:
        """Walk the project tree and return paths of all source files."""
        found: List[str] = []

        for p in self._root.rglob("*"):
            if not p.is_file():
                continue
            if any(part in _SKIP_DIRS for part in p.parts):
                continue
            if p.suffix.lower() in _SOURCE_EXTS or not p.suffix:
                found.append(str(p))

        return sorted(found)

    @staticmethod
    def _collect_mtimes(paths: List[str]) -> Dict[str, float]:
        """Return a mapping of path → last-modified timestamp (st_mtime)."""
        mtimes: Dict[str, float] = {}
        for raw in paths:
            try:
                mtimes[raw] = Path(raw).stat().st_mtime
            except OSError:
                mtimes[raw] = 0.0
        return mtimes

    def _find_config_files(self) -> List[str]:
        """Fallback config detection when no ProjectContext is available."""
        _CONFIG_NAMES = {
            "pyproject.toml", "setup.cfg", "setup.py",
            "package.json", "tsconfig.json", "webpack.config.js",
            "Cargo.toml", "pom.xml", "build.gradle",
            ".env", "config.yaml", "config.yml", "config.toml",
            "settings.py", "settings.yaml",
        }
        found: List[str] = []
        for name in _CONFIG_NAMES:
            candidate = self._root / name
            if candidate.is_file():
                found.append(str(candidate))
        return found

    def _find_doc_files(self) -> List[str]:
        """Locate markdown / text documentation files at the project root."""
        _DOC_NAMES = {
            "README.md", "ARCHITECTURE.md", "CONTRIBUTING.md",
            "PROJECT_BLUEPRINT.md", "PROGRESS_TRACKER.md",
            "API.md", "DESIGN.md", "NOTES.md",
        }
        found: List[str] = []
        for name in _DOC_NAMES:
            candidate = self._root / name
            if candidate.is_file():
                found.append(str(candidate))
        return found

    # ── Git integration ────────────────────────────────────────────────────

    def _git_modified_files(self) -> List[str]:
        """
        Return absolute paths of files changed in the git working tree.

        Runs 'git status --porcelain' which is always fast.
        Returns an empty list if git is unavailable or the project is
        not a git repository.
        """
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True,
                cwd=str(self._root), timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode != 0:
                return []

            modified: List[str] = []
            for line in result.stdout.splitlines():
                if len(line) < 4:
                    continue
                relative = line[3:].strip()
                # Handle rename notation "old -> new"
                if " -> " in relative:
                    relative = relative.split(" -> ")[-1]
                abs_path = str(self._root / relative)
                if Path(abs_path).is_file():
                    modified.append(abs_path)

            logger.debug(
                f"ContextBuilder: {len(modified)} git-modified files detected."
            )
            return modified

        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            logger.debug(f"ContextBuilder: git status unavailable ({exc}).")
            return []


# ============================================================================
# SECTION: ai.context.ai_context_store (ai/context/ai_context_store.py)
# ============================================================================
"""
AI Context Store — v1.0

A small, project-global store of "memory" the user hands to the assistant: files
they upload or notes they paste so the AI gets a quick recap of prior work. The
stored text is injected as a prefix into every chat prompt (see AIChatEngine),
which is how the memory stays "connected" to whatever model is in use.

It is deliberately global (shared across chats/models) but fully resettable — the
user can clear it with one action when starting a completely different task, which
is exactly the workflow requested.

Persisted to config/ai_context.json. No Qt / GUI dependencies so it can be unit
tested headlessly and reused anywhere in the backend.
"""

import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any


# Rough client-side token estimate. Real tokenizers vary by model; ~4 chars per
# token is the widely-used heuristic. We also floor at the word count so very
# short/no-space text isn't undercounted. Clearly an *estimate*.
def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max((len(text) + 3) // 4, len(text.split()))


# Guard rails so a giant paste/file can't blow up the prompt silently.
_MAX_ENTRY_CHARS = 200_000
_MAX_TOTAL_CHARS = 600_000


@dataclass
class ContextEntry:
    entry_id: str
    name: str
    content: str
    source: str = "note"          # "note" | "file"
    added_at: float = field(default_factory=time.time)

    @property
    def chars(self) -> int:
        return len(self.content)

    @property
    def tokens(self) -> int:
        return estimate_tokens(self.content)

    def summary(self) -> Dict[str, Any]:
        """Lightweight dict for the UI (no full content)."""
        return {
            "entry_id": self.entry_id,
            "name": self.name,
            "source": self.source,
            "added_at": self.added_at,
            "chars": self.chars,
            "tokens": self.tokens,
        }

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ContextEntry":
        return cls(
            entry_id=d.get("entry_id") or uuid.uuid4().hex[:8],
            name=d.get("name", "context"),
            content=d.get("content", ""),
            source=d.get("source", "note"),
            added_at=d.get("added_at", time.time()),
        )


class AIContextStore:
    """Disk-backed collection of context entries injected into AI prompts."""

    def __init__(self, storage_path: str = "config/ai_context.json"):
        self._path = Path(storage_path)
        self._entries: List[ContextEntry] = []
        self._load()

    # -- persistence ---------------------------------------------------------
    def _load(self) -> None:
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._entries = [ContextEntry.from_dict(e)
                                 for e in data.get("entries", [])]
        except Exception:
            self._entries = []

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"entries": [e.to_dict() for e in self._entries],
                       "saved_at": time.time()}
            self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    # -- mutation ------------------------------------------------------------
    def add_note(self, name: str, content: str) -> ContextEntry:
        entry = ContextEntry(
            entry_id=uuid.uuid4().hex[:8],
            name=(name or "note").strip()[:120] or "note",
            content=(content or "")[:_MAX_ENTRY_CHARS],
            source="note",
        )
        self._entries.append(entry)
        self._enforce_total_budget()
        self._save()
        return entry

    def add_file(self, path: str) -> ContextEntry:
        """Read a text file and store its contents. Raises on unreadable input."""
        p = Path(path)
        # Best-effort text read; ignore undecodable bytes rather than failing.
        content = p.read_text(encoding="utf-8", errors="ignore")
        entry = ContextEntry(
            entry_id=uuid.uuid4().hex[:8],
            name=p.name,
            content=content[:_MAX_ENTRY_CHARS],
            source="file",
        )
        self._entries.append(entry)
        self._enforce_total_budget()
        self._save()
        return entry

    def remove(self, entry_id: str) -> bool:
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.entry_id != entry_id]
        removed = len(self._entries) != before
        if removed:
            self._save()
        return removed

    def clear(self) -> int:
        """Reset all memory for a fresh, unrelated task. Returns count removed."""
        n = len(self._entries)
        self._entries = []
        self._save()
        return n

    def _enforce_total_budget(self) -> None:
        """Drop oldest entries if the combined size gets unreasonable."""
        total = sum(e.chars for e in self._entries)
        while total > _MAX_TOTAL_CHARS and len(self._entries) > 1:
            dropped = self._entries.pop(0)
            total -= dropped.chars

    # -- reads ---------------------------------------------------------------
    def entries(self) -> List[ContextEntry]:
        return list(self._entries)

    def summaries(self) -> List[Dict[str, Any]]:
        return [e.summary() for e in self._entries]

    def is_empty(self) -> bool:
        return not self._entries

    def total_chars(self) -> int:
        return sum(e.chars for e in self._entries)

    def total_tokens(self) -> int:
        return estimate_tokens(self.prompt_prefix()) if self._entries else 0

    def prompt_prefix(self) -> str:
        """The block prepended to a user prompt so the model has the recap.

        Returns "" when empty so callers can cheaply skip injection.
        """
        if not self._entries:
            return ""
        parts = [
            "You have been given the following project context and memory from "
            "the user. Use it to inform your answer when relevant.\n",
            "<project_context>",
        ]
        for e in self._entries:
            label = f"{e.name} ({e.source})"
            parts.append(f"\n### {label}\n{e.content}")
        parts.append("\n</project_context>\n")
        return "\n".join(parts)


# ============================================================================
# SECTION: ai.context.context_engine (ai/context/context_engine.py)
# ============================================================================
"""
context_engine.py — Intelligent Context Engine (v0.5).

The Context Engine is the mandatory gateway between the Planner and
the Model Manager. No AI model ever receives a prompt directly from
the Planner — every request must first pass through this engine.

Pipeline (all synchronous, runs in a background thread via EventBus):

    User Prompt + Current File + Cursor Position + ProjectContext
        ↓
    ContextBuilder.collect()         — gather raw project materials
        ↓
    FileImportGraph.build()          — build the import graph (cached)
        ↓
    ContextSelector.select()         — keyword-filter candidate files
        ↓
    DependencyResolver.resolve()     — follow import chains
        ↓
    ContextRanker.rank()             — score and sort by relevance
        ↓
    [Read file contents for top N]   — lazy I/O for survivors only
        ↓
    SymbolIndex.index_project()      — index symbols in selected files
        ↓
    TokenEstimator.estimate_package()— estimate token budget
        ↓
    ContextCache.put()               — store for reuse
        ↓
    EventBus.publish("context_ready")
        ↓
    ContextPackage  →  Model Manager

Public API:
    engine = ContextEngine(event_bus, project_root)
    package = engine.build(prompt, current_file, cursor_line, project_context)
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.logger import setup_logger
from core.event_bus import EventBus

from ai.context.context_builder    import ContextBuilder
from ai.context.context_selector   import ContextSelector
from ai.context.context_ranker     import ContextRanker, RankedFile
from ai.context.dependency_resolver import DependencyResolver
from ai.context.symbol_index       import SymbolIndex, SymbolEntry
from ai.context.file_import_graph  import FileImportGraph
from ai.context.token_estimator    import TokenEstimator
from ai.context.context_cache      import ContextCache

if TYPE_CHECKING:
    from ai.memory.project_context import ProjectContext

logger = setup_logger(__name__)


# ── Data contracts ─────────────────────────────────────────────────────────

@dataclass
class SelectedFile:
    """
    One file selected for inclusion in the context package.

    Attributes:
        path:    Absolute path to the file.
        content: Full text content of the file.
        score:   Composite relevance score from ContextRanker (0-1).
        reason:  Human-readable explanation of why this file was chosen.
        token_estimate: Estimated tokens for this file alone.
    """
    path:           str
    content:        str
    score:          float
    reason:         str
    token_estimate: int = 0


@dataclass
class ContextPackage:
    """
    Optimized context package delivered to the Model Manager.

    This is the complete, ranked, token-budgeted set of everything
    a model needs to process the user's request.

    Attributes:
        prompt:            The original user prompt.
        selected_files:    Files chosen for inclusion (ranked, contents loaded).
        symbols:           Symbol index entries for selected files.
        dependency_chain:  All file paths in the dependency graph, ordered.
        token_estimate:    Total estimated token count for the package.
        cache_hit:         True if this package was served from cache.
        build_duration_ms: Time taken to build the package.
        warnings:          Non-fatal issues encountered during building.
        metadata:          Arbitrary extra data for future use.
    """
    prompt:            str
    selected_files:    List[SelectedFile]    = field(default_factory=list)
    symbols:           List[SymbolEntry]     = field(default_factory=list)
    dependency_chain:  List[str]             = field(default_factory=list)
    token_estimate:    int                   = 0
    cache_hit:         bool                  = False
    build_duration_ms: float                 = 0.0
    warnings:          List[str]             = field(default_factory=list)
    metadata:          Dict[str, Any]        = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"<ContextPackage files={len(self.selected_files)} "
            f"tokens≈{self.token_estimate} "
            f"cache={'HIT' if self.cache_hit else 'MISS'}>"
        )


# ── Main engine ────────────────────────────────────────────────────────────

class ContextEngine:
    """
    Intelligent Context Engine — the gateway between Planner and Model Manager.

    Responsibilities:
      1. Collect all project files and metadata.
      2. Select and rank files relevant to the user's prompt.
      3. Follow import chains to pull in necessary dependencies.
      4. Estimate token usage and enforce model budget limits.
      5. Cache results and return optimized ContextPackage objects.
      6. Publish progress events to the EventBus for UI updates.

    Args:
        event_bus:    Application-wide EventBus for UI notifications.
        project_root: Absolute path to the open project directory.
        max_files:    Maximum number of files to include in one package.
        model_limit:  Token budget for the target model.
    """

    def __init__(
        self,
        event_bus:    EventBus,
        project_root: str,
        max_files:    int = 15,
        model_limit:  int = 128_000,
    ) -> None:
        self.event_bus    = event_bus
        self._root        = Path(project_root)
        self._max_files   = max_files
        self._model_limit = model_limit

        # Component instances (stateless or lazily populated)
        self._builder   = ContextBuilder(project_root)
        self._selector  = ContextSelector(max_candidates=max_files * 3)
        self._ranker    = ContextRanker(top_n=max_files)
        self._sym_index = SymbolIndex()
        self._estimator = TokenEstimator()
        self._cache     = ContextCache(max_size=50)

        # Import graph is built once per session (lazily, then cached)
        self._import_graph: Optional[FileImportGraph] = None

        logger.info(
            f"ContextEngine ready — root='{self._root.name}', "
            f"max_files={max_files}, model_limit={model_limit:,} tokens."
        )

    # ── Public API ─────────────────────────────────────────────────────────

    def build(
        self,
        prompt:          str,
        current_file:    Optional[str]       = None,
        cursor_line:     int                  = 0,
        project_context: Optional["ProjectContext"] = None,
        open_tabs:       Optional[List[str]] = None,
    ) -> ContextPackage:
        """
        Build an optimized ContextPackage for the given prompt.

        This is the single public method called by WorkflowPipeline.
        It runs the full pipeline and publishes EventBus events for
        the UI to display progress.

        Args:
            prompt:          Raw user prompt (e.g. "Fix the login page").
            current_file:    Absolute path of the focused editor file.
            cursor_line:     Cursor line number (1-based) in current_file.
            project_context: Most recent ProjectContext from the scanner.
            open_tabs:       Paths of all open editor tabs.

        Returns:
            ContextPackage ready for the Model Manager.
        """
        start = time.perf_counter()
        logger.info(f"ContextEngine.build(): prompt='{prompt[:60]}…'")
        self._publish("context_building", {
            "prompt_preview": prompt[:60],
        })

        # ── 1. Collect raw materials ───────────────────────────────────
        builder_result = self._builder.collect(
            project_context=project_context,
            open_tabs=open_tabs,
        )
        all_files = builder_result.all_files
        logger.info(f"Context: {len(all_files)} files in project.")

        # ── 2. Cache check ─────────────────────────────────────────────
        cache_key = ContextCache.make_key(
            prompt       = prompt,
            current_file = current_file or "",
            file_mtimes  = builder_result.file_mtimes,
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("ContextEngine: cache HIT — returning cached package.")
            cached.cache_hit = True
            self._publish_ready(cached)
            return cached

        # ── 3. Build / reuse import graph ──────────────────────────────
        graph = self._get_import_graph(project_context)

        # ── 4. Select keyword-matched candidates ───────────────────────
        candidates = self._selector.select(
            prompt       = prompt,
            all_files    = all_files,
            current_file = current_file,
            config_files = builder_result.config_files,
        )
        logger.info(f"Context: {len(candidates)} candidates after keyword selection.")

        # ── 5. Resolve dependency chains ───────────────────────────────
        seed_files = [c.path for c in candidates]
        resolver   = DependencyResolver(graph)
        dep_chain  = resolver.resolve(seed_files)
        logger.info(
            f"Context: dependency chain resolved — "
            f"{len(dep_chain.files)} total files."
        )

        # ── 6. Rank all candidates + dependencies ──────────────────────
        ranked = self._ranker.rank(
            candidates       = candidates,
            dependency_files = dep_chain.files,
            dep_depth_map    = dep_chain.depth_map,
            git_modified     = set(builder_result.git_modified),
            open_tabs        = open_tabs,
            current_file     = current_file,
        )

        # ── 7. Load file contents for top-ranked files ─────────────────
        selected_files = self._load_file_contents(ranked, builder_result.file_mtimes)

        # ── 8. Index symbols in selected files ─────────────────────────
        symbols = self._index_symbols(selected_files)

        # ── 9. Assemble package ────────────────────────────────────────
        package = ContextPackage(
            prompt           = prompt,
            selected_files   = selected_files,
            symbols          = symbols,
            dependency_chain = dep_chain.files,
            cache_hit        = False,
        )

        # ── 10. Estimate tokens, enforce budget ────────────────────────
        token_estimate = self._estimator.estimate_package(package)
        package.token_estimate = token_estimate

        budget = self._estimator.check_budget(package, self._model_limit)
        if not budget.fits:
            drop_paths = self._estimator.suggest_reduction(package, self._model_limit)
            package.warnings.append(
                f"Context exceeds model limit by {budget.excess_tokens:,} tokens. "
                f"Suggested: drop {len(drop_paths)} file(s)."
            )
            package.selected_files = [
                f for f in package.selected_files if f.path not in set(drop_paths)
            ]
            logger.warning(
                f"ContextEngine: budget exceeded — dropped {len(drop_paths)} files."
            )

        # ── 11. Final metadata ─────────────────────────────────────────
        elapsed = (time.perf_counter() - start) * 1000
        package.build_duration_ms = round(elapsed, 1)
        package.metadata.update({
            "cursor_line":       cursor_line,
            "current_file":      current_file or "",
            "project_root":      str(self._root),
            "cache_key":         cache_key[:12] + "…",
            "budget_utilisation": f"{budget.utilisation_pct}%",
        })

        # ── 12. Cache & publish ────────────────────────────────────────
        self._cache.put(
            cache_key,
            package,
            file_paths=[f.path for f in selected_files],
        )
        self._publish_ready(package)

        # ── 13. Log summary ────────────────────────────────────────────
        logger.info(
            f"ContextEngine DONE in {elapsed:.0f} ms:\n"
            f"  • {len(all_files)} files analyzed\n"
            f"  • {len(selected_files)} files selected\n"
            f"  • {len(dep_chain.files)} in dependency chain\n"
            f"  • {len(symbols)} symbols indexed\n"
            f"  • ~{token_estimate:,} tokens estimated\n"
            f"  • {budget.utilisation_pct}% of model context used\n"
            f"  • Cache: MISS → stored"
        )

        return package

    def notify_file_changed(self, file_path: str) -> None:
        """
        Call this when a file changes on disk.

        Invalidates the import graph (forcing a rebuild next call) and
        evicts any cache entries that used the changed file.
        """
        self._import_graph = None          # Force graph rebuild
        evicted = self._cache.invalidate_file(file_path)
        logger.debug(
            f"ContextEngine: file changed '{Path(file_path).name}' — "
            f"{evicted} cache entries evicted, graph reset."
        )

    def cache_stats(self) -> Dict[str, Any]:
        """Return a dict of cache health metrics for the UI."""
        s = self._cache.stats()
        return {
            "size":        s.size,
            "max_size":    s.max_size,
            "hits":        s.hits,
            "misses":      s.misses,
            "evictions":   s.evictions,
            "hit_rate":    f"{s.hit_rate_pct}%",
        }

    # ── Pipeline helpers ───────────────────────────────────────────────────

    def _get_import_graph(
        self, project_context: Optional["ProjectContext"]
    ) -> FileImportGraph:
        """Return the cached import graph, rebuilding if necessary."""
        if self._import_graph is None:
            root = str(self._root)
            logger.debug("ContextEngine: building FileImportGraph…")
            t0 = time.perf_counter()
            self._import_graph = FileImportGraph.build(root)
            elapsed = (time.perf_counter() - t0) * 1000
            stats = self._import_graph.stats()
            logger.info(
                f"FileImportGraph built in {elapsed:.0f} ms — "
                f"{stats.total_files} files, {stats.total_edges} edges."
            )
        return self._import_graph

    def _load_file_contents(
        self,
        ranked: List[RankedFile],
        mtimes: Dict[str, float],
    ) -> List[SelectedFile]:
        """Read the content of each ranked file. Skip unreadable files."""
        selected: List[SelectedFile] = []

        for ranked_file in ranked:
            p = Path(ranked_file.path)
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                logger.warning(f"ContextEngine: cannot read '{p.name}': {exc}")
                continue

            token_est = self._estimator.estimate_file(str(p), content)
            reason    = " | ".join(ranked_file.reasons) if ranked_file.reasons else "ranked"

            selected.append(SelectedFile(
                path           = str(p),
                content        = content,
                score          = ranked_file.score,
                reason         = reason,
                token_estimate = token_est,
            ))

        return selected

    def _index_symbols(self, files: List[SelectedFile]) -> List[SymbolEntry]:
        """Index symbols for all selected files."""
        symbols: List[SymbolEntry] = []
        for sf in files:
            try:
                file_symbols = self._sym_index.index_file(sf.path)
                symbols.extend(file_symbols)
            except Exception as exc:
                logger.debug(f"Symbol index error in '{sf.path}': {exc}")
        return symbols

    # ── EventBus publishing ────────────────────────────────────────────────

    def _publish(self, event_type: str, data: Dict[str, Any]) -> None:
        try:
            self.event_bus.publish(event_type, data)
        except Exception as exc:
            logger.debug(f"ContextEngine: publish failed ({event_type}): {exc}")

    def _publish_ready(self, package: ContextPackage) -> None:
        """Publish the context_ready event with key metrics for the UI."""
        self._publish("context_ready", {
            "selected_files":   [
                {"path": f.path, "reason": f.reason, "score": f.score}
                for f in package.selected_files
            ],
            "token_estimate":    package.token_estimate,
            "dependency_count":  len(package.dependency_chain),
            "cache_hit":         package.cache_hit,
            "duration_ms":       package.build_duration_ms,
            "file_count":        len(package.selected_files),
            "symbol_count":      len(package.symbols),
            "warnings":          package.warnings,
        })




# =====================================================================
# Phase 2 & 3 + v3.1 Lazy-Init Context & Memory Extensions
# =====================================================================
import math
import sqlite3
from collections import defaultdict


class ASTFileSlicer:
    """Extracts exact AST symbol slices + imports without loading full files into context."""

    @staticmethod
    def slice_symbol(file_path: Path, symbol_name: str) -> Optional[Dict[str, Any]]:
        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = source.splitlines()
            tree = ast.parse(source)
        except Exception:
            return None

        imports: List[str] = []
        target_node = None
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                s = getattr(node, "lineno", 1) - 1
                e = getattr(node, "end_lineno", s + 1)
                imports.append("\n".join(lines[s:e]))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name == symbol_name:
                    target_node = node
                    break
                if isinstance(node, ast.ClassDef):
                    for sub in node.body:
                        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                            sub.name == symbol_name or f"{node.name}.{sub.name}" == symbol_name
                        ):
                            target_node = sub
                            break

        if target_node is None:
            return None

        start_line = getattr(target_node, "lineno", 1)
        end_line = getattr(target_node, "end_lineno", start_line)
        body = "\n".join(lines[start_line - 1 : end_line])
        return {
            "file": str(file_path),
            "symbol": symbol_name,
            "start_line": start_line,
            "end_line": end_line,
            "imports": "\n".join(imports[:15]),
            "content": body,
        }


class RepoMapBuilder:
    """Builds a compact, relevance-ranked repository signature map under a strict token budget."""

    IGNORE_DIRS = {
        ".git", "__pycache__", "node_modules", ".venv", "venv", "env",
        "dist", "build", ".idea", ".vscode", ".owncode", ".owncode_shadow"
    }

    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root).resolve()

    def build_map(
        self,
        query: str = "",
        active_files: Optional[List[str]] = None,
        max_tokens: int = 1024,
    ) -> str:
        active_set = {str(Path(p)) for p in (active_files or [])}
        query_terms = [
            t.lower()
            for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", query or "")
        ]

        file_entries: List[Tuple[float, str, List[str]]] = []
        for root, dirs, files in os.walk(self.workspace_root):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS and not d.startswith(".")]
            for fname in files:
                if not fname.endswith((".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs")):
                    continue
                fpath = Path(root) / fname
                try:
                    rel_str = fpath.relative_to(self.workspace_root).as_posix()
                except ValueError:
                    rel_str = str(fpath)

                sigs = self._extract_signatures(fpath)
                if not sigs:
                    continue

                score = 1.0
                if rel_str in active_set or fpath.name in active_set:
                    score += 5.0
                joined_lower = (rel_str + " " + " ".join(sigs)).lower()
                for term in query_terms:
                    if term in rel_str.lower():
                        score += 3.0
                    elif term in joined_lower:
                        score += 1.5
                score += min(len(sigs) * 0.05, 1.0)
                file_entries.append((score, rel_str, sigs))

        file_entries.sort(key=lambda item: (-item[0], item[1]))
        max_chars = max(256, max_tokens * 4)
        lines_out = ["# Repository Map (Ranked AST Signatures)"]
        used_chars = len(lines_out[0])

        for score, rel_str, sigs in file_entries:
            block_lines = [f"## {rel_str}"] + [f"  {s}" for s in sigs[:25]]
            block = "\n".join(block_lines)
            if used_chars + len(block) + 2 > max_chars:
                break
            lines_out.append(block)
            used_chars += len(block) + 1

        return "\n".join(lines_out)

    def _extract_signatures(self, fpath: Path) -> List[str]:
        try:
            source = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []
        if fpath.suffix == ".py":
            try:
                tree = ast.parse(source)
                sigs: List[str] = []
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        bases = [getattr(b, "id", getattr(b, "attr", "")) for b in node.bases]
                        base_str = f"({', '.join(b for b in bases if b)})" if bases else ""
                        sigs.append(f"class {node.name}{base_str}: [L{node.lineno}]")
                        for sub in node.body:
                            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                args = [a.arg for a in sub.args.args]
                                sigs.append(f"  def {sub.name}({', '.join(args[:6])}) [L{sub.lineno}]")
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        args = [a.arg for a in node.args.args]
                        sigs.append(f"def {node.name}({', '.join(args[:6])}) [L{node.lineno}]")
                return sigs
            except Exception:
                pass
        sigs = []
        for idx, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith(("def ", "async def ", "class ", "function ", "export function ", "export class ")):
                sigs.append(f"{stripped[:80]} [L{idx}]")
        return sigs


class EpisodicMemoryStore:
    """Persistent cross-session episodic & semantic memory backed by SQLite FTS5 + BM25 fallback.
    Uses lazy table initialization so instantiating ProjectMemory during IDE startup touches zero disk I/O.
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._fts_enabled = False
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS episodic_memories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT NOT NULL,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        tags TEXT DEFAULT '',
                        workspace TEXT DEFAULT '',
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                try:
                    conn.execute(
                        """
                        CREATE VIRTUAL TABLE IF NOT EXISTS episodic_memories_fts
                        USING fts5(title, content, tags, category, content='episodic_memories', content_rowid='id')
                        """
                    )
                    self._fts_enabled = True
                except sqlite3.OperationalError:
                    self._fts_enabled = False
                conn.commit()
            self._initialized = True
        except Exception as exc:
            logger.warning(f"EpisodicMemoryStore init failed: {exc}")

    def record_episode(
        self,
        category: str,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        workspace: str = "",
    ) -> int:
        self._ensure_initialized()
        tag_str = ",".join(tags or [])
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO episodic_memories (category, title, content, tags, workspace) VALUES (?, ?, ?, ?, ?)",
                (category, title, content, tag_str, workspace),
            )
            rowid = int(cur.lastrowid or 0)
            if self._fts_enabled and rowid:
                try:
                    conn.execute(
                        "INSERT INTO episodic_memories_fts(rowid, title, content, tags, category) VALUES (?, ?, ?, ?, ?)",
                        (rowid, title, content, tag_str, category),
                    )
                except sqlite3.Error:
                    pass
            conn.commit()
            return rowid

    def search_memories(self, query: str, limit: int = 5, category: Optional[str] = None) -> List[Dict[str, Any]]:
        self._ensure_initialized()
        terms = [t.lower() for t in re.findall(r"[A-Za-z0-9_]+", query or "") if len(t) > 1]
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if category:
                rows = conn.execute(
                    "SELECT * FROM episodic_memories WHERE category = ? ORDER BY id DESC LIMIT 200",
                    (category,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM episodic_memories ORDER BY id DESC LIMIT 200"
                ).fetchall()

        if not rows:
            return []
        if not terms:
            return [dict(r) for r in rows[:limit]]

        scored: List[Tuple[float, Dict[str, Any]]] = []
        for r in rows:
            d = dict(r)
            haystack = f"{d.get('title', '')} {d.get('content', '')} {d.get('tags', '')}".lower()
            score = 0.0
            for t in terms:
                count = haystack.count(t)
                if count > 0:
                    score += 1.0 + math.log(1 + count)
                    if t in d.get("title", "").lower():
                        score += 1.5
                    if t in d.get("tags", "").lower():
                        score += 1.0
            if score > 0:
                d["relevance_score"] = round(score, 3)
                scored.append((score, d))

        scored.sort(key=lambda x: (-x[0], -x[1].get("id", 0)))
        return [item[1] for item in scored[:limit]]
