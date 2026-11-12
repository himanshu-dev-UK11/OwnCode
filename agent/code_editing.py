"""
Consolidated Module: agent.code_editing

Combines: ai.editing.change_request, ai.editing.change_set, ai.editing.diff_generator, ai.editing.patch_builder, ai.editing.patch_validator, ai.editing.file_lock_manager, ai.editing.edit_history, ai.editing.rollback_manager, ai.editing.change_preview, ai.editing.change_applier, ai.editing.review_model
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['ai.editing.change_request', 'ai.editing.change_set', 'ai.editing.diff_generator', 'ai.editing.patch_builder', 'ai.editing.patch_validator', 'ai.editing.file_lock_manager', 'ai.editing.edit_history', 'ai.editing.rollback_manager', 'ai.editing.change_preview', 'ai.editing.change_applier', 'ai.editing.review_model', 'ai.editing.smart_patch_engine', 'ai.editing.shadow_sandbox', 'ai.editing.fim_and_next_edit']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ai.editing.change_request (ai/editing/change_request.py)
# ============================================================================
"""
change_request.py — Dataclass representing an AI code modification request.

This is the input contract that flows from Model Manager into the
editing pipeline. It captures what the AI wants to do, why, and
which files are affected.

All fields are immutable to ensure request integrity throughout
the pipeline. Once created, a ChangeRequest cannot be changed.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any


class ChangePriority(Enum):
    """Priority levels for code change requests."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ChangeStatus(Enum):
    """Status of a change request in the pipeline."""
    PENDING = "pending"
    VALIDATING = "validating"
    PREVIEW_READY = "preview_ready"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class ChangeRequest:
    """
    Represents a request from an AI model to modify files.

    Attributes:
        request_id:    Unique identifier for this request.
        user_prompt:   The original user request that triggered this change.
        files:         List of absolute file paths to be modified.
        changes:       Detailed change descriptions (diff hunks).
        reason:        Human-readable explanation of what is being changed.
        priority:      Importance level for scheduling.
        timestamp:     When this request was created.
        status:        Current state in the editing pipeline.
        metadata:      Arbitrary extra data (e.g., model name, confidence).
        rollback_id:   ID of the rollback point created before this change.
    """

    request_id:     str
    user_prompt:    str
    files:          List[str]
    changes:        List[Dict[str, Any]]
    reason:         str
    priority:       ChangePriority
    timestamp:      datetime
    status:         ChangeStatus
    metadata:       Dict[str, Any] = field(default_factory=dict)
    rollback_id:    Optional[str] = None

    # Class-level counter for sequential request IDs
    _counter: int = 0

    @classmethod
    def create(
        cls,
        user_prompt:  str,
        files:        List[str],
        changes:      List[Dict[str, Any]],
        reason:       str,
        priority:     ChangePriority = ChangePriority.NORMAL,
        metadata:     Optional[Dict[str, Any]] = None,
    ) -> ChangeRequest:
        """
        Create a new ChangeRequest with automatic ID generation.

        Args:
            user_prompt: The original user request.
            files:       List of affected file paths.
            changes:     List of change hunks (dicts with 'type', 'old', 'new').
            reason:      Explanation of the changes.
            priority:    Request priority (default: NORMAL).
            metadata:    Extra data for tracking (default: empty dict).
        """
        cls._counter += 1

        return cls(
            request_id=f"req_{cls._counter:06d}_{uuid.uuid4().hex[:8]}",
            user_prompt=user_prompt,
            files=files,
            changes=changes,
            reason=reason,
            priority=priority,
            timestamp=datetime.now(),
            status=ChangeStatus.PENDING,
            metadata=metadata or {},
            rollback_id=None,
        )

    def with_status(self, status: ChangeStatus) -> ChangeRequest:
        """Return a copy of this request with updated status."""
        return dataclasses_replace(
            self,
            status=status,
        )

    def with_metadata(self, key: str, value: Any) -> ChangeRequest:
        """Return a copy with an updated metadata entry."""
        new_metadata = dict(self.metadata)
        new_metadata[key] = value
        return dataclasses_replace(
            self,
            metadata=new_metadata,
        )

    def with_rollback_id(self, rollback_id: str) -> ChangeRequest:
        """Return a copy with the rollback ID set."""
        return dataclasses_replace(
            self,
            status=ChangeStatus.PREVIEW_READY,
            rollback_id=rollback_id,
        )


# Helper to replace dataclass fields immutably
def dataclasses_replace(instance, **changes):
    """Replacement for dataclasses.replace that works across Python versions."""
    import dataclasses
    return dataclasses.replace(instance, **changes)


def make_request_id() -> str:
    """Generate a unique request ID with timestamp."""
    import time
    ts = int(time.time() * 1000)
    return f"req_{ts:013d}_{uuid.uuid4().hex[:8]}"

# ============================================================================
# SECTION: ai.editing.change_set (ai/editing/change_set.py)
# ============================================================================
"""
change_set.py — Collection of file modification operations.

Represents all proposed changes as a set of atomic operations:
- Create new files
- Delete files
- Rename/move files
- Modify files (with specific line ranges)

This is the intermediate format between diff generation and
patch application. It's model-agnostic and serialization-ready.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any


class OperationType(Enum):
    """Types of file operations in a change set."""
    CREATE = "create"
    DELETE = "delete"
    RENAME = "rename"
    MOVE = "move"
    MODIFY = "modify"


@dataclass(frozen=True)
class Hunk:
    """
    A single change hunk for a modified file.

    For modified files, we support multiple hunks to represent
    disjoint changes within the same file.

    Attributes:
        old_start: Starting line number in original file (1-based).
        old_lines: Number of lines in original section.
        new_start: Starting line in new version.
        new_lines: Number of lines in new version.
        old_text:  Original text (before change).
        new_text:  New text (after change).
        context:   Context lines around the change.
    """
    old_start:  int
    old_lines:  int
    new_start:  int
    new_lines:  int
    old_text:   str
    new_text:   str
    context:    List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ChangeOperation:
    """
    One atomic operation in the change set.

    Attributes:
        op_type:     Type of operation (create, delete, rename, move, modify).
        source_path: Source file path (for rename/move/modify/delete).
        dest_path:   Destination file path (for create/rename/move).
        hunks:       List of Hunk objects (for MODIFY operations).
        content:     Full content for CREATE operations.
        reason:      Human-readable explanation.
    """
    op_type:    OperationType
    source_path: str
    dest_path:  Optional[str] = None
    hunks:      List[Hunk] = field(default_factory=list)
    content:    Optional[str] = None
    reason:     str = ""

    @classmethod
    def create_file(
        cls,
        path:   str,
        content: str,
        reason: str = "",
    ) -> ChangeOperation:
        """Create a CREATE operation."""
        return cls(
            op_type=OperationType.CREATE,
            source_path=path,
            dest_path=path,
            content=content,
            reason=reason,
        )

    @classmethod
    def delete_file(
        cls,
        path:   str,
        reason: str = "",
    ) -> ChangeOperation:
        """Create a DELETE operation."""
        return cls(
            op_type=OperationType.DELETE,
            source_path=path,
            reason=reason,
        )

    @classmethod
    def rename_file(
        cls,
        source: str,
        dest:   str,
        reason: str = "",
    ) -> ChangeOperation:
        """Create a RENAME operation."""
        return cls(
            op_type=OperationType.RENAME,
            source_path=source,
            dest_path=dest,
            reason=reason,
        )

    @classmethod
    def move_file(
        cls,
        source: str,
        dest:   str,
        reason: str = "",
    ) -> ChangeOperation:
        """Create a MOVE operation."""
        return cls(
            op_type=OperationType.MOVE,
            source_path=source,
            dest_path=dest,
            reason=reason,
        )

    @classmethod
    def modify_file(
        cls,
        path:   str,
        hunks:  List[Hunk],
        reason: str = "",
    ) -> ChangeOperation:
        """Create a MODIFY operation."""
        return cls(
            op_type=OperationType.MODIFY,
            source_path=path,
            hunks=hunks,
            reason=reason,
        )


@dataclass(frozen=True)
class ChangeSet:
    """
    Collection of all proposed file modifications.

    This is the output of DiffGenerator and the input to
    PatchBuilder. It's immutable and can be safely shared
    across threads.

    Attributes:
        operations: List of ChangeOperation objects.
        files:      Unique set of all affected file paths.
        total_hunks: Total number of hunks across all operations.
    """
    operations: List[ChangeOperation]
    files:      List[str]
    total_hunks: int

    @classmethod
    def from_operations(cls, operations: List[ChangeOperation]) -> ChangeSet:
        """Create a ChangeSet from a list of operations."""
        all_files = set()
        total_hunks = 0

        for op in operations:
            all_files.add(op.source_path)
            if op.dest_path:
                all_files.add(op.dest_path)
            total_hunks += len(op.hunks)

        return cls(
            operations=operations,
            files=sorted(all_files),
            total_hunks=total_hunks,
        )

    def is_empty(self) -> bool:
        """Return True if no operations are defined."""
        return len(self.operations) == 0

    def get_operations_by_type(self, op_type: OperationType) -> List[ChangeOperation]:
        """Return all operations of a specific type."""
        return [op for op in self.operations if op.op_type == op_type]

    def get_changes_by_file(self, path: str) -> List[ChangeOperation]:
        """Return all operations affecting a specific file."""
        path = str(Path(path))
        return [
            op for op in self.operations
            if op.source_path == path or op.dest_path == path
        ]

# ============================================================================
# SECTION: ai.editing.diff_generator (ai/editing/diff_generator.py)
# ============================================================================
"""
diff_generator.py — Professional diff generation from change requests.

Generates human-readable diffs that show exactly what changed:
- Line-by-line comparison
- Added/removed/modified markers
- Line numbers for easy reference
- File summary statistics

The output is designed to be displayed in a UI preview window
before the user approves changes.
"""

import difflib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from core.logger import setup_logger

from ai.editing.change_request import ChangeRequest, ChangeStatus
from ai.editing.change_set import ChangeSet, ChangeOperation, OperationType, Hunk

logger = setup_logger(__name__)


@dataclass
class DiffResult:
    """
    Complete diff output for a single file.

    Attributes:
        file_path:     Absolute path to the file.
        op_type:       Type of operation (create, delete, modify).
        old_content:   Original file content (None for create).
        new_content:   New file content (None for delete).
        hunks:         List of individual change hunks.
        summary:       File-level statistics.
    """
    file_path:     str
    op_type:       OperationType
    old_content:   str | None
    new_content:   str | None
    hunks:         List[Dict[str, Any]]
    summary:       Dict[str, int]


@dataclass
class DiffSummary:
    """
    Summary of all changes across the change set.

    Attributes:
        total_files:     Number of files affected.
        files_created:   Files being created.
        files_deleted:   Files being deleted.
        files_modified:  Files being modified.
        total_hunks:     Total number of change hunks.
        lines_added:     Total lines added.
        lines_removed:   Total lines removed.
    """
    total_files:    int
    files_created:  int
    files_deleted:  int
    files_modified: int
    total_hunks:    int
    lines_added:    int
    lines_removed:  int


class DiffGenerator:
    """
    Generates professional diffs from ChangeRequest objects.

    The generator supports:
      - Text-based file comparison using Python's difflib
      - Line-by-line diff with added/removed markers
      - Summary statistics for UI display

    Usage:
        generator = DiffGenerator()
        diff = generator.generate(request, change_set)
    """

    def __init__(self) -> None:
        logger.debug("DiffGenerator initialized.")

    # ── Public API ─────────────────────────────────────────────────────────

    def generate(
        self,
        request:  ChangeRequest,
        change_set: ChangeSet,
    ) -> List[DiffResult]:
        """
        Generate diff results for all operations in the change set.

        Args:
            request:  The ChangeRequest (original user prompt + AI changes).
            change_set: The ChangeSet with all proposed operations.

        Returns:
            List of DiffResult objects, one per file operation.
        """
        if change_set.is_empty():
            logger.warning("DiffGenerator: empty change set — no diffs generated.")
            return []

        diffs = []
        for op in change_set.operations:
            diff = self._generate_file_diff(op)
            if diff:
                diffs.append(diff)

        logger.info(
            f"DiffGenerator: {len(diffs)} files processed, "
            f"{change_set.total_hunks} hunks generated."
        )
        return diffs

    def generate_summary(self, diffs: List[DiffResult]) -> DiffSummary:
        """
        Create an overall summary from a list of diff results.

        Args:
            diffs: List of DiffResult objects from generate().

        Returns:
            DiffSummary with aggregate statistics.
        """
        files_created = 0
        files_deleted = 0
        files_modified = 0
        total_hunks = 0
        lines_added = 0
        lines_removed = 0

        for diff in diffs:
            if diff.op_type == OperationType.CREATE:
                files_created += 1
                if diff.new_content:
                    lines = diff.new_content.splitlines()
                    lines_added += len(lines)
                    total_hunks += 1
            elif diff.op_type == OperationType.DELETE:
                files_deleted += 1
                if diff.old_content:
                    lines = diff.old_content.splitlines()
                    lines_removed += len(lines)
                    total_hunks += 1
            elif diff.op_type == OperationType.MODIFY:
                files_modified += 1
                total_hunks += len(diff.hunks)
                for hunk in diff.hunks:
                    lines_added += hunk.get("added", 0)
                    lines_removed += hunk.get("removed", 0)

        total_files = files_created + files_deleted + files_modified

        return DiffSummary(
            total_files=total_files,
            files_created=files_created,
            files_deleted=files_deleted,
            files_modified=files_modified,
            total_hunks=total_hunks,
            lines_added=lines_added,
            lines_removed=lines_removed,
        )

    # ── File-level diff generation ──────────────────────────────────────────

    def _generate_file_diff(self, op: ChangeOperation) -> DiffResult | None:
        """Generate diff for a single operation."""
        if op.op_type == OperationType.CREATE:
            return self._generate_create_diff(op)
        elif op.op_type == OperationType.DELETE:
            return self._generate_delete_diff(op)
        elif op.op_type == OperationType.MODIFY:
            return self._generate_modify_diff(op)
        else:
            # Rename and move are logical — show as delete + create
            return None

    def _generate_create_diff(self, op: ChangeOperation) -> DiffResult:
        """Generate diff for a file creation operation."""
        path = op.source_path
        new_content = op.content or ""

        hunks = []
        if new_content:
            lines = new_content.splitlines()
            hunks.append({
                "type": "create",
                "added": len(lines),
                "removed": 0,
                "content": new_content[:500] + ("..." if len(new_content) > 500 else ""),
            })

        summary = {
            "lines_added": len(new_content.splitlines()),
            "lines_removed": 0,
            "file_size": len(new_content),
        }

        return DiffResult(
            file_path=path,
            op_type=op.op_type,
            old_content=None,
            new_content=new_content,
            hunks=hunks,
            summary=summary,
        )

    def _generate_delete_diff(self, op: ChangeOperation) -> DiffResult:
        """Generate diff for a file deletion operation."""
        path = op.source_path
        old_content = self._read_file(path)

        hunks = []
        if old_content:
            lines = old_content.splitlines()
            hunks.append({
                "type": "delete",
                "added": 0,
                "removed": len(lines),
                "content": old_content[:500] + ("..." if len(old_content) > 500 else ""),
            })

        summary = {
            "lines_added": 0,
            "lines_removed": len(old_content.splitlines()) if old_content else 0,
            "file_size": len(old_content) if old_content else 0,
        }

        return DiffResult(
            file_path=path,
            op_type=op.op_type,
            old_content=old_content,
            new_content=None,
            hunks=hunks,
            summary=summary,
        )

    def _generate_modify_diff(self, op: ChangeOperation) -> DiffResult:
        """Generate diff for a file modification operation."""
        path = op.source_path
        old_content = self._read_file(path)
        new_content = self._apply_hunks(old_content, op.hunks)

        if old_content is None:
            logger.warning(f"DiffGenerator: source file not found: {path}")
            return None

        # Generate unified diff
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff_lines = list(difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"a/{Path(path).name}",
            tofile=f"b/{Path(path).name}",
            lineterm="",
        ))

        # Parse diff into structured hunks
        hunks = self._parse_unified_diff(diff_lines, old_content, new_content)

        summary = {
            "lines_added": sum(h.get("added", 0) for h in hunks),
            "lines_removed": sum(h.get("removed", 0) for h in hunks),
            "file_size": len(new_content),
        }

        return DiffResult(
            file_path=path,
            op_type=op.op_type,
            old_content=old_content,
            new_content=new_content,
            hunks=hunks,
            summary=summary,
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _read_file(self, path: str) -> str | None:
        """Read file content, return None if not found."""
        try:
            return Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.debug(f"DiffGenerator: cannot read '{path}': {exc}")
            return None

    def _apply_hunks(self, content: str, hunks: List[Hunk]) -> str:
        """Apply hunks to content and return modified content."""
        if not hunks:
            return content

        lines = content.splitlines(keepends=True)
        result = lines.copy()

        # Process hunks in reverse order to maintain line indices
        for hunk in reversed(hunks):
            # Remove old lines
            if hunk.old_lines > 0:
                del result[hunk.old_start - 1:hunk.old_start - 1 + hunk.old_lines]

            # Insert new lines
            new_lines = hunk.new_text.splitlines(keepends=True)
            if new_lines or hunk.new_lines > 0:
                result[hunk.old_start - 1:hunk.old_start - 1] = new_lines

        return "".join(result)

    def _parse_unified_diff(
        self,
        diff_lines: List[str],
        old_content: str,
        new_content: str,
    ) -> List[Dict[str, Any]]:
        """
        Parse unified diff lines into structured hunks.

        Returns a list of dicts with:
          - added:   lines added count
          - removed: lines removed count
          - context: preview of the change
        """
        hunks = []
        current_hunk = None

        for line in diff_lines:
            if line.startswith("@@"):
                # New hunk header
                if current_hunk:
                    hunks.append(current_hunk)

                # Parse @@ -old_start,old_lines +new_start,new_lines @@
                import re
                match = re.match(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@", line)
                if match:
                    current_hunk = {
                        "old_start": int(match.group(1)),
                        "old_lines": int(match.group(2)),
                        "new_start": int(match.group(3)),
                        "new_lines": int(match.group(4)),
                        "added": 0,
                        "removed": 0,
                        "context": [],
                    }
            elif current_hunk:
                if line.startswith("+"):
                    current_hunk["added"] += 1
                    current_hunk["context"].append(("add", line[1:]))
                elif line.startswith("-"):
                    current_hunk["removed"] += 1
                    current_hunk["context"].append(("remove", line[1:]))
                elif line.startswith(" "):
                    current_hunk["context"].append(("context", line[1:]))

        if current_hunk:
            hunks.append(current_hunk)

        return hunks

# ============================================================================
# SECTION: ai.editing.patch_builder (ai/editing/patch_builder.py)
# ============================================================================
"""
patch_builder.py — Safe, incremental patch generation.

Builds patches that modify only necessary sections of files
instead of replacing entire files. This minimizes merge conflicts
and preserves unrelated content.

The patches are designed to be:
  - Atomic (all-or-nothing application)
  - Reversible (rollback support)
  - Incremental (only changed sections)
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

from core.logger import setup_logger

from ai.editing.change_set import ChangeSet, ChangeOperation, OperationType, Hunk


logger = setup_logger(__name__)


@dataclass
class Patch:
    """
    A single patch for applying changes to a file.

    Attributes:
        file_path:  Absolute path to the target file.
        op_type:    Type of operation (create, delete, modify).
        hunks:      List of Hunk objects with exact line ranges.
        checksum:   SHA-256 hash of original file content (for safety).
    """
    file_path:  str
    op_type:    OperationType
    hunks:      List[Hunk]
    checksum:   Optional[str] = None


@dataclass
class PatchSet:
    """
    Collection of patches for all operations in a change set.

    Attributes:
        patches:    List of Patch objects.
        total_size: Total characters that will be changed.
    """
    patches:    List[Patch]
    total_size: int


class PatchBuilder:
    """
    Builds safe, incremental patches from a ChangeSet.

    Usage:
        builder = PatchBuilder()
        patch_set = builder.build(change_set, project_root)
    """

    def __init__(self) -> None:
        logger.debug("PatchBuilder initialized.")

    # ── Public API ─────────────────────────────────────────────────────────

    def build(
        self,
        change_set: ChangeSet,
        project_root: str,
    ) -> PatchSet:
        """
        Build patches for all operations in the change set.

        Args:
            change_set:  The ChangeSet with all proposed operations.
            project_root: Absolute path to the project directory.

        Returns:
            PatchSet with all patches and total change size.
        """
        patches = []
        total_size = 0

        for op in change_set.operations:
            patch = self._build_patch(op, project_root)
            if patch:
                patches.append(patch)
                total_size += self._estimate_patch_size(patch)

        return PatchSet(patches=patches, total_size=total_size)

    # ── Patch construction ──────────────────────────────────────────────────

    def _build_patch(
        self,
        op: ChangeOperation,
        project_root: str,
    ) -> Optional[Patch]:
        """Build a patch for a single operation."""
        if op.op_type == OperationType.CREATE:
            return self._build_create_patch(op, project_root)
        elif op.op_type == OperationType.DELETE:
            return self._build_delete_patch(op, project_root)
        elif op.op_type == OperationType.MODIFY:
            return self._build_modify_patch(op, project_root)
        else:
            # Rename/move handled by apply_phase
            return None

    def _build_create_patch(
        self,
        op: ChangeOperation,
        project_root: str,
    ) -> Patch:
        """Build patch for file creation."""
        content = op.content or ""
        lines = content.splitlines(keepends=True)

        hunk = Hunk(
            old_start=1,
            old_lines=0,
            new_start=1,
            new_lines=len(lines),
            old_text="",
            new_text=content,
            context=lines[:10],
        )

        return Patch(
            file_path=op.source_path,
            op_type=OperationType.CREATE,
            hunks=[hunk],
            checksum=None,  # File doesn't exist yet
        )

    def _build_delete_patch(
        self,
        op: ChangeOperation,
        project_root: str,
    ) -> Patch:
        """Build patch for file deletion."""
        path = Path(project_root) / op.source_path
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            content = ""

        lines = content.splitlines(keepends=True)

        hunk = Hunk(
            old_start=1,
            old_lines=len(lines),
            new_start=1,
            new_lines=0,
            old_text=content,
            new_text="",
            context=lines[:10] if lines else [],
        )

        return Patch(
            file_path=op.source_path,
            op_type=OperationType.DELETE,
            hunks=[hunk],
            checksum=None,
        )

    def _build_modify_patch(
        self,
        op: ChangeOperation,
        project_root: str,
    ) -> Patch:
        """Build patch for file modification."""
        path = Path(project_root) / op.source_path

        # Read original content
        try:
            old_content = path.read_text(encoding="utf-8")
        except OSError:
            logger.warning(f"PatchBuilder: source file not found: {path}")
            return None

        # Use hunks from ChangeOperation
        hunks = op.hunks

        return Patch(
            file_path=op.source_path,
            op_type=OperationType.MODIFY,
            hunks=hunks,
            checksum=None,
        )

    def _estimate_patch_size(self, patch: Patch) -> int:
        """Estimate total characters that will be changed."""
        size = 0
        for hunk in patch.hunks:
            size += len(hunk.old_text) + len(hunk.new_text)
        return size

    # ── Smart patch generation ─────────────────────────────────────────────

    def generate_smart_hunks(
        self,
        old_content: str,
        new_content: str,
        context_lines: int = 3,
    ) -> List[Hunk]:
        """
        Generate optimal hunks by comparing old and new content.

        This method:
          1. Finds the longest common subsequence
          2. Groups changes into hunks
          3. Adds context lines before and after each hunk

        Args:
            old_content: Original file content.
            new_content: Target file content.
            context_lines: Number of unchanged lines surrounding each change.

        Returns:
            List of Hunk objects representing the changes.
        """
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()

        # Find differences using difflib
        import difflib
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

        hunks = []
        current_hunk_old_start = None
        current_hunk_new_start = None
        hunk_old_lines = []
        hunk_new_lines = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                # This section is unchanged
                if hunk_old_lines or hunk_new_lines:
                    # Close current hunk
                    hunks.append(Hunk(
                        old_start=current_hunk_old_start,
                        old_lines=len(hunk_old_lines),
                        new_start=current_hunk_new_start,
                        new_lines=len(hunk_new_lines),
                        old_text="\n".join(hunk_old_lines) + "\n",
                        new_text="\n".join(hunk_new_lines) + "\n",
                        context=[],
                    ))
                    hunk_old_lines = []
                    hunk_new_lines = []
                    current_hunk_old_start = None
                    current_hunk_new_start = None

                # Add context lines before next change
                context_start = max(0, i2 - context_lines)
                context_end = min(len(old_lines), i2 + context_lines)
                context = old_lines[context_start:context_end]

            elif tag in ("replace", "delete", "insert"):
                # This section has changes
                if current_hunk_old_start is None:
                    current_hunk_old_start = i1 + 1
                    current_hunk_new_start = j1 + 1

                # Collect changed lines
                if tag in ("replace", "delete"):
                    hunk_old_lines.extend(old_lines[i1:i2])
                if tag in ("replace", "insert"):
                    hunk_new_lines.extend(new_lines[j1:j2])

        # Close final hunk if pending
        if hunk_old_lines or hunk_new_lines:
            hunks.append(Hunk(
                old_start=current_hunk_old_start,
                old_lines=len(hunk_old_lines),
                new_start=current_hunk_new_start,
                new_lines=len(hunk_new_lines),
                old_text="\n".join(hunk_old_lines) + "\n",
                new_text="\n".join(hunk_new_lines) + "\n",
                context=[],
            ))

        return hunks


def build_patch_for_operation(
    op: ChangeOperation,
    project_root: str,
    smart: bool = True,
) -> Optional[Patch]:
    """
    Convenience function to build a single patch.

    Args:
        op:          The ChangeOperation to patch.
        project_root: Project directory path.
        smart:       Use smart hunk generation if True.

    Returns:
        Patch object or None on error.
    """
    builder = PatchBuilder()

    if smart and op.op_type == OperationType.MODIFY:
        # Read files and generate smart hunks
        path = Path(project_root) / op.source_path
        try:
            old_content = path.read_text(encoding="utf-8")
            new_content = old_content  # Start with original
            for hunk in op.hunks:
                new_content = apply_hunk_to_content(new_content, hunk)
            hunks = builder.generate_smart_hunks(old_content, new_content)
            return Patch(
                file_path=op.source_path,
                op_type=op.op_type,
                hunks=hunks,
            )
        except OSError:
            pass

    return builder._build_patch(op, project_root)


def apply_hunk_to_content(content: str, hunk: Hunk) -> str:
    """Apply a single hunk to content and return result."""
    lines = content.splitlines(keepends=True)

    # Remove old lines
    start_idx = hunk.old_start - 1
    end_idx = start_idx + hunk.old_lines
    del lines[start_idx:end_idx]

    # Insert new lines
    new_lines = hunk.new_text.splitlines(keepends=True)
    if new_lines:
        lines[start_idx:start_idx] = new_lines

    return "".join(lines)

# ============================================================================
# SECTION: ai.editing.patch_validator (ai/editing/patch_validator.py)
# ============================================================================
"""
patch_validator.py — Verification and safety checks for patches.

Validates that patches are safe to apply by checking for:
  - Syntax corruption (Python syntax validation)
  - Malformed patches (proper line ranges)
  - Duplicate edits (same section modified twice)
  - Overlapping edits (conflicting changes)

This is the final safety gate before showing changes to the user.
"""

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple, Any

from core.logger import setup_logger

from ai.editing.change_set import ChangeSet, ChangeOperation, Hunk
from ai.editing.patch_builder import Patch, PatchSet


logger = setup_logger(__name__)


@dataclass
class ValidationResult:
    """
    Result of validating a patch or change set.

    Attributes:
        is_valid:     True if all checks passed.
        warnings:     Non-blocking issues to show to user.
        errors:       Blocking issues that prevent application.
        safe_to_apply: True if patch can be safely applied.
    """
    is_valid:       bool
    warnings:       List[str]
    errors:         List[str]
    safe_to_apply:  bool


class PatchValidator:
    """
    Validates patches for safety and correctness.

    Performs multiple validation passes:
      1. Patch syntax validation (line ranges, etc.)
      2. Duplicate edit detection (same file, overlapping hunks)
      3. Overlap detection (conflicting changes)
      4. Syntax validation (for supported languages)
    """

    def __init__(self) -> None:
        logger.debug("PatchValidator initialized.")
        self._supported_syntax_langs = {".py", ".js", ".ts", ".jsx", ".tsx"}

    # ── Public API ─────────────────────────────────────────────────────────

    def validate_change_set(
        self,
        change_set: ChangeSet,
        project_root: str,
    ) -> ValidationResult:
        """
        Validate an entire change set.

        Args:
            change_set:  The ChangeSet to validate.
            project_root: Project directory path.

        Returns:
            ValidationResult with all findings.
        """
        warnings: List[str] = []
        errors: List[str] = []

        # Pass 1: Validate individual hunks
        for op in change_set.operations:
            hunk_results = self._validate_hunks(op.hunks, op.source_path)
            warnings.extend(hunk_results["warnings"])
            errors.extend(hunk_results["errors"])

        # Pass 2: Check for duplicate edits
        dup_results = self._check_duplicates(change_set)
        warnings.extend(dup_results["warnings"])
        errors.extend(dup_results["errors"])

        # Pass 3: Check for overlapping edits
        overlap_results = self._check_overlaps(change_set, project_root)
        warnings.extend(overlap_results["warnings"])
        errors.extend(overlap_results["errors"])

        # Pass 4: Syntax validation (for modified files)
        syntax_results = self._validate_syntax(change_set, project_root)
        warnings.extend(syntax_results["warnings"])
        errors.extend(syntax_results["errors"])

        is_valid = len(errors) == 0
        safe_to_apply = is_valid and len(warnings) < 3

        result = ValidationResult(
            is_valid=is_valid,
            warnings=warnings,
            errors=errors,
            safe_to_apply=safe_to_apply,
        )

        if is_valid:
            logger.info(
                f"PatchValidator: {len(change_set.operations)} operations "
                f"validated — safe to apply."
            )
        else:
            logger.warning(
                f"PatchValidator: {len(errors)} errors, {len(warnings)} warnings."
            )

        return result

    # ── Validation passes ───────────────────────────────────────────────────

    def _validate_hunks(
        self,
        hunks: List[Hunk],
        file_path: str,
    ) -> Dict[str, List[str]]:
        """Validate individual hunks for correctness."""
        warnings: List[str] = []
        errors: List[str] = []

        for i, hunk in enumerate(hunks):
            # Check line ranges are positive
            if hunk.old_start < 1:
                errors.append(f"Hunk {i+1}: old_start must be >= 1")
            if hunk.new_start < 1:
                errors.append(f"Hunk {i+1}: new_start must be >= 1")

            # Check line counts are non-negative
            if hunk.old_lines < 0:
                errors.append(f"Hunk {i+1}: old_lines must be >= 0")
            if hunk.new_lines < 0:
                errors.append(f"Hunk {i+1}: new_lines must be >= 0")

            # Check old and new content have same line count if specified
            if hunk.old_text and hunk.old_lines > 0:
                old_line_count = len(hunk.old_text.splitlines())
                if old_line_count != hunk.old_lines:
                    warnings.append(
                        f"Hunk {i+1}: old_lines count mismatch "
                        f"(expected {hunk.old_lines}, got {old_line_count})"
                    )

            if hunk.new_text and hunk.new_lines > 0:
                new_line_count = len(hunk.new_text.splitlines())
                if new_line_count != hunk.new_lines:
                    warnings.append(
                        f"Hunk {i+1}: new_lines count mismatch "
                        f"(expected {hunk.new_lines}, got {new_line_count})"
                    )

        return {"warnings": warnings, "errors": errors}

    def _check_duplicates(
        self,
        change_set: ChangeSet,
    ) -> Dict[str, List[str]]:
        """Check for duplicate edits of the same file."""
        warnings: List[str] = []
        errors: List[str] = []

        # Group operations by file
        file_ops: Dict[str, List[ChangeOperation]] = {}
        for op in change_set.operations:
            if op.op_type != OperationType.MODIFY:
                continue
            if op.source_path not in file_ops:
                file_ops[op.source_path] = []
            file_ops[op.source_path].append(op)

        # Check for multiple modifications to same file
        for path, ops in file_ops.items():
            if len(ops) > 1:
                warnings.append(
                    f"Multiple modifications to '{path}' — "
                    f"{len(ops)} operations detected"
                )

        return {"warnings": warnings, "errors": errors}

    def _check_overlaps(
        self,
        change_set: ChangeSet,
        project_root: str,
    ) -> Dict[str, List[str]]:
        """Check for overlapping changes within the same file."""
        warnings: List[str] = []
        errors: List[str] = []

        # Group hunks by file
        file_hunks: Dict[str, List[Tuple[int, int, Hunk]]] = {}
        for op in change_set.operations:
            if op.op_type != OperationType.MODIFY:
                continue

            # Build line ranges for each hunk
            ranges = []
            current_line = 1
            for hunk in op.hunks:
                old_end = hunk.old_start + hunk.old_lines - 1
                ranges.append((hunk.old_start, old_end, hunk))
                current_line = old_end + 1

            file_hunks[op.source_path] = ranges

        # Check for overlaps within each file
        for path, ranges in file_hunks.items():
            if len(ranges) < 2:
                continue

            for i in range(len(ranges)):
                for j in range(i + 1, len(ranges)):
                    start1, end1, _ = ranges[i]
                    start2, end2, _ = ranges[j]

                    # Check if ranges overlap
                    if start1 <= end2 and start2 <= end1:
                        warnings.append(
                            f"Overlapping changes in '{path}' at "
                            f"lines {start1}-{end1} and {start2}-{end2}"
                        )

        return {"warnings": warnings, "errors": errors}

    def _validate_syntax(
        self,
        change_set: ChangeSet,
        project_root: str,
    ) -> Dict[str, List[str]]:
        """Validate syntax for modified Python files."""
        warnings: List[str] = []
        errors: List[str] = []

        for op in change_set.operations:
            if op.op_type != OperationType.MODIFY:
                continue

            ext = Path(op.source_path).suffix.lower()
            if ext not in self._supported_syntax_langs:
                continue

            # Read current file content
            path = Path(project_root) / op.source_path
            try:
                original = path.read_text(encoding="utf-8")
            except OSError:
                warnings.append(
                    f"Cannot read '{op.source_path}' for syntax validation"
                )
                continue

            # Apply hunks to get new content
            new_content = original
            for hunk in op.hunks:
                new_content = self._apply_hunk(new_content, hunk)

            # Validate syntax
            try:
                if ext == ".py":
                    ast.parse(new_content, filename=op.source_path)
            except SyntaxError as e:
                errors.append(
                    f"Syntax error in '{op.source_path}' at line {e.lineno}: "
                    f"{e.msg}"
                )

        return {"warnings": warnings, "errors": errors}

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _apply_hunk(self, content: str, hunk: Hunk) -> str:
        """Apply a single hunk to content."""
        lines = content.splitlines(keepends=True)

        start_idx = hunk.old_start - 1
        end_idx = start_idx + hunk.old_lines

        if end_idx > len(lines):
            end_idx = len(lines)
        if start_idx > len(lines):
            start_idx = len(lines)

        del lines[start_idx:end_idx]

        new_lines = hunk.new_text.splitlines(keepends=True)
        if new_lines:
            lines[start_idx:start_idx] = new_lines

        return "".join(lines)


def validate_change_set(
    change_set: ChangeSet,
    project_root: str,
) -> ValidationResult:
    """
    Convenience function to validate a change set.

    Args:
        change_set:  The ChangeSet to validate.
        project_root: Project directory path.

    Returns:
        ValidationResult with validation results.
    """
    validator = PatchValidator()
    return validator.validate_change_set(change_set, project_root)

# ============================================================================
# SECTION: ai.editing.file_lock_manager (ai/editing/file_lock_manager.py)
# ============================================================================
"""
file_lock_manager.py — Concurrent edit prevention and queue management.

Prevents simultaneous edits of the same file by:
  - Locking files during editing
  - Queueing requests for locked files
  - Rejecting requests safely with informative messages

Thread-safe implementation with proper cleanup.
"""

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

from core.logger import setup_logger


logger = setup_logger(__name__)


class LockStatus(Enum):
    """Status of a file lock."""
    LOCKED = "locked"
    PENDING = "pending"
    REJECTED = "rejected"
    RELEASED = "released"


@dataclass
class FileLock:
    """
    A lock on a file.

    Attributes:
        lock_id:      Unique identifier for this lock.
        file_path:    Absolute path to the locked file.
        lock_time:    When the lock was acquired.
        expires_at:   When the lock will expire (for timeout).
        status:       Current status of the lock.
        request_id:   ID of the request holding the lock.
    """
    lock_id:     str
    file_path:   str
    lock_time:   datetime
    expires_at:  datetime
    status:      LockStatus
    request_id:  str


@dataclass
class LockRequest:
    """
    A request to lock a file.

    Attributes:
        request_id:   Unique identifier for this request.
        file_path:    File to lock.
        timestamp:    When the request was made.
        status:       Current status of the request.
        reason:       Human-readable reason for the lock.
    """
    request_id:  str
    file_path:   str
    timestamp:   datetime
    status:      LockStatus
    reason:      str


class FileLockManager:
    """
    Manages file locks to prevent concurrent edits.

    Features:
      - Per-file locking with configurable timeout
      - Request queuing for locked files
      - Automatic lock release on completion
      - Deadlock detection and timeout

    Usage:
        manager = FileLockManager(timeout_seconds=60)
        lock = manager.acquire(file_path, request_id)
        if lock:
            # Edit the file
            manager.release(file_path)
    """

    # Default timeout: 60 seconds
    DEFAULT_TIMEOUT = 60

    def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT) -> None:
        self._timeout = timedelta(seconds=timeout_seconds)
        self._locks: Dict[str, FileLock] = {}
        self._requests: Dict[str, LockRequest] = {}
        self._lock = threading.RLock()

        logger.debug(f"FileLockManager initialized (timeout={timeout_seconds}s).")

    # ── Public API ─────────────────────────────────────────────────────────

    def acquire(
        self,
        file_path: str,
        request_id: str,
        reason: str = "",
        timeout: Optional[float] = None,
    ) -> Optional[FileLock]:
        """
        Acquire a lock on a file.

        Args:
            file_path: Absolute path to the file.
            request_id: ID of the request requesting the lock.
            reason: Human-readable reason for the lock.
            timeout: Optional custom timeout in seconds.

        Returns:
            FileLock if acquired, None if file is locked by another request.
        """
        file_path = str(Path(file_path))
        timeout_delta = (
            timedelta(seconds=timeout)
            if timeout is not None
            else self._timeout
        )

        with self._lock:
            # Check if file is already locked
            existing = self._locks.get(file_path)
            if existing:
                # Check if lock is expired
                if datetime.now() > existing.expires_at:
                    # Lock expired, release it
                    self._release_lock(existing)
                else:
                    # Lock still valid, check if same request
                    if existing.request_id == request_id:
                        # Re-acquire own lock (extend timeout)
                        return self._create_lock(file_path, request_id, reason, timeout_delta)
                    else:
                        # File locked by another request
                        self._requests[request_id] = LockRequest(
                            request_id=request_id,
                            file_path=file_path,
                            timestamp=datetime.now(),
                            status=LockStatus.PENDING,
                            reason=reason,
                        )
                        logger.debug(
                            f"FileLockManager: '{Path(file_path).name}' locked by "
                            f"{existing.request_id[:8]}..."
                        )
                        return None

            # Create new lock
            lock = self._create_lock(file_path, request_id, reason, timeout_delta)
            self._locks[file_path] = lock
            self._requests[request_id] = LockRequest(
                request_id=request_id,
                file_path=file_path,
                timestamp=datetime.now(),
                status=LockStatus.LOCKED,
                reason=reason,
            )
            logger.debug(f"FileLockManager: lock acquired for '{Path(file_path).name}'.")
            return lock

    def release(
        self,
        file_path: str,
        request_id: Optional[str] = None,
    ) -> bool:
        """
        Release a lock on a file.

        Args:
            file_path: Absolute path to the file.
            request_id: Optional request ID to verify ownership.

        Returns:
            True if lock was released, False if lock wasn't held.
        """
        file_path = str(Path(file_path))

        with self._lock:
            lock = self._locks.get(file_path)
            if not lock:
                logger.debug(f"FileLockManager: no lock found for '{file_path}'.")
                return False

            if request_id and lock.request_id != request_id:
                logger.warning(
                    f"FileLockManager: attempt to release lock held by "
                    f"{lock.request_id[:8]}... (requested by {request_id[:8]}...)"
                )
                return False

            self._release_lock(lock)
            logger.debug(f"FileLockManager: lock released for '{file_path}'.")
            return True

    def release_all(self, request_id: str) -> int:
        """
        Release all locks held by a specific request.

        Args:
            request_id: ID of the request whose locks to release.

        Returns:
            Number of locks released.
        """
        released = 0
        with self._lock:
            locks_to_release = [
                lock for lock in self._locks.values()
                if lock.request_id == request_id
            ]
            for lock in locks_to_release:
                self._release_lock(lock)
                released += 1

        if released > 0:
            logger.info(
                f"FileLockManager: released {released} locks for request {request_id[:8]}..."
            )
        return released

    def is_locked(self, file_path: str) -> bool:
        """Check if a file is currently locked."""
        file_path = str(Path(file_path))

        with self._lock:
            lock = self._locks.get(file_path)
            if not lock:
                return False

            # Check if expired
            if datetime.now() > lock.expires_at:
                self._release_lock(lock)
                return False

            return True

    def get_lock(self, file_path: str) -> Optional[FileLock]:
        """Get the current lock on a file, if any."""
        file_path = str(Path(file_path))

        with self._lock:
            lock = self._locks.get(file_path)
            if lock and datetime.now() <= lock.expires_at:
                return lock
            elif lock:
                self._release_lock(lock)
            return None

    def queue_status(self) -> Dict[str, Any]:
        """Return the current queue status for all pending requests."""
        with self._lock:
            pending = [
                req for req in self._requests.values()
                if req.status == LockStatus.PENDING
            ]
            return {
                "total_pending": len(pending),
                "pending_files": list(set(req.file_path for req in pending)),
            }

    def cleanup_expired(self) -> int:
        """
        Remove all expired locks.

        Returns:
            Number of locks removed.
        """
        now = datetime.now()
        removed = 0

        with self._lock:
            expired = [
                lock for lock in self._locks.values()
                if now > lock.expires_at
            ]
            for lock in expired:
                self._release_lock(lock)
                removed += 1

        if removed > 0:
            logger.info(f"FileLockManager: cleaned up {removed} expired locks.")
        return removed

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _create_lock(
        self,
        file_path: str,
        request_id: str,
        reason: str,
        timeout_delta: timedelta,
    ) -> FileLock:
        """Create a new lock entry."""
        lock_id = f"lock_{uuid.uuid4().hex[:12]}"
        return FileLock(
            lock_id=lock_id,
            file_path=file_path,
            lock_time=datetime.now(),
            expires_at=datetime.now() + timeout_delta,
            status=LockStatus.LOCKED,
            request_id=request_id,
        )

    def _release_lock(self, lock: FileLock) -> None:
        """Release a lock and update state."""
        if lock.file_path in self._locks:
            del self._locks[lock.file_path]

        lock = lock.__class__(
            **{
                **lock.__dict__,
                "status": LockStatus.RELEASED,
            }
        )

# ============================================================================
# SECTION: ai.editing.edit_history (ai/editing/edit_history.py)
# ============================================================================
"""
edit_history.py — Comprehensive edit history tracking.

Stores every edit with metadata for:
  - Audit trail (who, what, when, why)
  - Undo/redo functionality
  - Impact analysis
  - Learning from past edits

Designed to be serialized for persistence.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

from core.logger import setup_logger


logger = setup_logger(__name__)


@dataclass
class EditEntry:
    """
    One edit entry in the history.

    Attributes:
        edit_id:         Unique identifier for this edit.
        timestamp:       When the edit occurred.
        request_id:      ID of the request that triggered the edit.
        user_prompt:     Original user prompt.
        model_name:      Name of the AI model that generated the edit.
        files:           List of affected file paths.
        rollback_id:     ID of the rollback checkpoint created before this edit.
        changes_summary: Brief summary of changes.
        metadata:        Extra data (confidence, tokens, etc.).
    """
    edit_id:        str
    timestamp:      datetime
    request_id:     str
    user_prompt:    str
    model_name:     Optional[str]
    files:          List[str]
    rollback_id:    str
    changes_summary: str
    metadata:       Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "edit_id": self.edit_id,
            "timestamp": self.timestamp.isoformat(),
            "request_id": self.request_id,
            "user_prompt": self.user_prompt,
            "model_name": self.model_name,
            "files": self.files,
            "rollback_id": self.rollback_id,
            "changes_summary": self.changes_summary,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EditEntry:
        """Create from dictionary."""
        return cls(
            edit_id=data["edit_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            request_id=data["request_id"],
            user_prompt=data["user_prompt"],
            model_name=data.get("model_name"),
            files=data.get("files", []),
            rollback_id=data["rollback_id"],
            changes_summary=data.get("changes_summary", ""),
            metadata=data.get("metadata", {}),
        )


class EditHistory:
    """
    Manages edit history with support for:
      - Long-term persistence
      - Undo/redo
      - Query by criteria
      - Impact analysis

    Usage:
        history = EditHistory(project_root)
        history.add_entry(edit_entry)
        entries = history.get_by_file(file_path)
        history.undo(last_n=1)
    """

    def __init__(self, project_root: str, max_entries: int = 1000) -> None:
        self._root = Path(project_root)
        self._history_file = self._root / ".ai_history" / "edits.json"
        self._history_file.parent.mkdir(exist_ok=True)

        self._entries: List[EditEntry] = []
        self._max_entries = max_entries

        self._load_history()
        logger.debug(f"EditHistory initialized (max_entries={max_entries}).")

    # ── Public API ─────────────────────────────────────────────────────────

    def add_entry(self, entry: EditEntry) -> None:
        """
        Add a new edit entry to history.

        Args:
            entry: The EditEntry to store.
        """
        self._entries.insert(0, entry)
        self._trim_entries()
        self._save_history()
        logger.info(
            f"EditHistory: added entry {entry.edit_id[:8]} for "
            f"{len(entry.files)} file(s)."
        )

    def get_all(self) -> List[EditEntry]:
        """Return all edit entries, newest first."""
        return list(self._entries)

    def get_by_request_id(self, request_id: str) -> List[EditEntry]:
        """Return entries matching a specific request ID."""
        return [e for e in self._entries if e.request_id == request_id]

    def get_by_file(self, file_path: str) -> List[EditEntry]:
        """Return entries that affected a specific file."""
        file_path = str(Path(file_path))
        return [e for e in self._entries if file_path in e.files]

    def get_by_model(self, model_name: str) -> List[EditEntry]:
        """Return entries generated by a specific model."""
        return [e for e in self._entries if e.model_name == model_name]

    def get_by_time_range(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[EditEntry]:
        """Return entries within a time range."""
        result = []
        for e in self._entries:
            if start and e.timestamp < start:
                continue
            if end and e.timestamp > end:
                continue
            result.append(e)
        return result

    def undo(self, last_n: int = 1) -> List[EditEntry]:
        """
        Undo the last N edits by rolling back to their checkpoints.

        Args:
            last_n: Number of recent edits to undo.

        Returns:
            List of entries that were undone.
        """
        undone = []
        for entry in self._entries[:last_n]:
            if entry.rollback_id:
                logger.info(
                    f"EditHistory: undoing edit {entry.edit_id[:8]}, "
                    f"rollback_id={entry.rollback_id[:8]}"
                )
                undone.append(entry)

        return undone

    def search(self, query: str, case_sensitive: bool = False) -> List[EditEntry]:
        """
        Search entries by prompt or file content.

        Args:
            query: Text to search for.
            case_sensitive: Whether to match case exactly.

        Returns:
            Matching entries.
        """
        if not case_sensitive:
            query = query.lower()

        results = []
        for e in self._entries:
            text = e.user_prompt if case_sensitive else e.user_prompt.lower()
            if query in text:
                results.append(e)
        return results

    def stats(self) -> Dict[str, Any]:
        """Return history statistics."""
        if not self._entries:
            return {
                "total_edits": 0,
                "files_edited": 0,
                "models_used": 0,
            }

        files = set()
        models = set()
        for e in self._entries:
            files.update(e.files)
            if e.model_name:
                models.add(e.model_name)

        return {
            "total_edits": len(self._entries),
            "files_edited": len(files),
            "models_used": len(models),
            "oldest": self._entries[-1].timestamp.isoformat() if self._entries else None,
            "newest": self._entries[0].timestamp.isoformat() if self._entries else None,
        }

    # ── Persistence ───────────────���──────────────────────────────────────────

    def _load_history(self) -> None:
        """Load history from disk."""
        if not self._history_file.exists():
            return

        try:
            data = json.loads(self._history_file.read_text(encoding="utf-8"))
            self._entries = [EditEntry.from_dict(d) for d in data]
        except (json.JSONDecodeError, KeyError) as exc:
            logger.error(f"EditHistory: failed to load history: {exc}")
            self._entries = []

    def _save_history(self) -> None:
        """Save history to disk."""
        data = [e.to_dict() for e in self._entries]
        self._history_file.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )

    def _trim_entries(self) -> None:
        """Remove old entries if over the limit."""
        if len(self._entries) > self._max_entries:
            removed = self._entries[self._max_entries:]
            self._entries = self._entries[:self._max_entries]
            logger.info(
                f"EditHistory: trimmed {len(removed)} old entries "
                f"(max={self._max_entries})."
            )


def load_edit_history(project_root: str, max_entries: int = 1000) -> EditHistory:
    """Convenience function to load edit history."""
    return EditHistory(project_root, max_entries)


def create_edit_entry(
    request_id: str,
    user_prompt: str,
    model_name: Optional[str],
    files: List[str],
    rollback_id: str,
    changes_summary: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> EditEntry:
    """Convenience function to create an edit entry."""
    return EditEntry(
        edit_id=f"edit_{uuid.uuid4().hex[:12]}",
        timestamp=datetime.now(),
        request_id=request_id,
        user_prompt=user_prompt,
        model_name=model_name,
        files=files,
        rollback_id=rollback_id,
        changes_summary=changes_summary,
        metadata=metadata or {},
    )

# ============================================================================
# SECTION: ai.editing.rollback_manager (ai/editing/rollback_manager.py)
# ============================================================================
"""
rollback_manager.py — Automatic backup and rollback system.

Before every edit, creates:
  - Git checkpoint (if git is available)
  - Internal rollback point (local backup)

Supports:
  - Undo (restore to previous state)
  - Restore (select specific checkpoint)
  - Recovery (revert to last known good state)
"""

import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

from core.logger import setup_logger


logger = setup_logger(__name__)


@dataclass
class Checkpoint:
    """
    A rollback checkpoint.

    Attributes:
        checkpoint_id: Unique identifier for this checkpoint.
        request_id:    ID of the request that triggered this checkpoint.
        user_prompt:   User prompt that triggered the edit.
        timestamp:     When the checkpoint was created.
        backup_paths:  Map of original path → backup path.
        git_commit:    Git commit hash (if available).
        files_affected: List of file paths that were backed up.
    """
    checkpoint_id:    str
    request_id:       Optional[str]
    user_prompt:      str
    timestamp:        datetime
    backup_paths:     Dict[str, str]
    git_commit:       Optional[str]
    files_affected:   List[str]


@dataclass
class RollbackResult:
    """
    Result of a rollback operation.

    Attributes:
        success:      True if rollback succeeded.
        restored:     Number of files restored.
        failed:       Number of files that failed to restore.
        errors:       List of error messages.
    """
    success:  bool
    restored: int
    failed:   int
    errors:   List[str]


class RollbackManager:
    """
    Manages automatic backups and rollback capabilities.

    Creates checkpoints before edits and supports restore operations.

    Usage:
        manager = RollbackManager(project_root)
        checkpoint = manager.create_checkpoint(change_set, request)
        manager.rollback(checkpoint.checkpoint_id)
    """

    def __init__(self, project_root: str) -> None:
        self._root = Path(project_root)
        self._backups_dir = Path(project_root) / ".ai_backups"
        self._backups_dir.mkdir(exist_ok=True)

        self._checkpoints: Dict[str, Checkpoint] = {}

        logger.debug(f"RollbackManager initialized (root='{self._root.name}').")

    # ── Public API ─────────────────────────────────────────────────────────

    def create_checkpoint(
        self,
        change_set: Optional[Any] = None,
        request_id: Optional[str] = None,
        user_prompt: Optional[str] = None,
    ) -> str:
        """
        Create a rollback checkpoint.

        Args:
            change_set:  The ChangeSet being modified (optional).
            request_id:  ID of the request triggering this checkpoint.
            user_prompt: User prompt that triggered the edit.

        Returns:
            Checkpoint ID for later rollback.
        """
        checkpoint_id = f"ckpt_{uuid.uuid4().hex[:12]}"

        # Get file list from change set if available
        files = []
        if change_set:
            files = change_set.files

        # Create backup for each file
        backup_paths: Dict[str, str] = {}
        for file_path in files:
            try:
                original = self._root / file_path
                if original.exists():
                    backup_name = f"{checkpoint_id}_{Path(file_path).name}"
                    backup_path = self._backups_dir / backup_name
                    backup_path.write_bytes(original.read_bytes())
                    backup_paths[file_path] = str(backup_path)
            except OSError as exc:
                logger.warning(
                    f"RollbackManager: failed to backup '{file_path}': {exc}"
                )

        # Get git commit hash if available
        git_commit = self._get_git_commit()

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            request_id=request_id,
            user_prompt=user_prompt or "",
            timestamp=datetime.now(),
            backup_paths=backup_paths,
            git_commit=git_commit,
            files_affected=files,
        )

        self._checkpoints[checkpoint_id] = checkpoint
        self._save_checkpoint(checkpoint)

        logger.info(
            f"RollbackManager: checkpoint {checkpoint_id[:8]} created "
            f"for {len(files)} files."
        )
        return checkpoint_id

    def rollback(self, checkpoint_id: str) -> RollbackResult:
        """
        Rollback to a specific checkpoint.

        Args:
            checkpoint_id: ID of the checkpoint to restore.

        Returns:
            RollbackResult with success/failure info.
        """
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint:
            logger.error(f"RollbackManager: checkpoint not found: {checkpoint_id}")
            return RollbackResult(
                success=False,
                restored=0,
                failed=0,
                errors=[f"Checkpoint not found: {checkpoint_id}"],
            )

        restored = 0
        failed = 0
        errors: List[str] = []

        logger.info(
            f"RollbackManager: restoring checkpoint {checkpoint_id[:8]} "
            f"for {len(checkpoint.files_affected)} files."
        )

        for original_path, backup_path in checkpoint.backup_paths.items():
            try:
                src = Path(backup_path)
                dst = self._root / original_path

                # Restore directory structure
                dst.parent.mkdir(parents=True, exist_ok=True)

                # Restore file
                dst.write_bytes(src.read_bytes())
                restored += 1

            except OSError as exc:
                failed += 1
                errors.append(f"Failed to restore '{original_path}': {exc}")
                logger.error(
                    f"RollbackManager: failed to restore '{original_path}': {exc}"
                )

        # Remove checkpoint after successful rollback
        if failed == 0:
            self._remove_checkpoint(checkpoint_id)
            logger.info(
                f"RollbackManager: checkpoint {checkpoint_id[:8]} restored successfully."
            )
        else:
            logger.warning(
                f"RollbackManager: checkpoint {checkpoint_id[:8]} partially restored "
                f"({restored} OK, {failed} failed)."
            )

        return RollbackResult(
            success=failed == 0,
            restored=restored,
            failed=failed,
            errors=errors,
        )

    def undo(self) -> RollbackResult:
        """
        Undo the most recent change by rolling back to the last checkpoint.

        Returns:
            RollbackResult with success/failure info.
        """
        if not self._checkpoints:
            return RollbackResult(
                success=False,
                restored=0,
                failed=0,
                errors=["No checkpoints available for undo."],
            )

        # Get most recent checkpoint
        most_recent = max(
            self._checkpoints.values(),
            key=lambda c: c.timestamp
        )

        return self.rollback(most_recent.checkpoint_id)

    def recover(self) -> RollbackResult:
        """
        Attempt to recover from the most recent successful checkpoint.

        This is similar to undo but doesn't remove the checkpoint,
        allowing multiple recovery attempts.

        Returns:
            RollbackResult with success/failure info.
        """
        return self.undo()

    def list_checkpoints(self) -> List[Checkpoint]:
        """Return all available checkpoints, sorted by timestamp."""
        return sorted(
            self._checkpoints.values(),
            key=lambda c: c.timestamp,
            reverse=True
        )

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Return a specific checkpoint by ID."""
        return self._checkpoints.get(checkpoint_id)

    def clear_all(self) -> int:
        """
        Remove all checkpoints and backup files.

        Returns:
            Number of checkpoints removed.
        """
        count = len(self._checkpoints)
        self._checkpoints.clear()

        # Also remove backup files
        if self._backups_dir.exists():
            for f in self._backups_dir.iterdir():
                if f.is_file():
                    f.unlink()

        logger.info(f"RollbackManager: cleared {count} checkpoints.")
        return count

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint metadata to disk."""
        metadata_path = self._backups_dir / f"{checkpoint.checkpoint_id}.json"
        import json
        data = {
            "checkpoint_id": checkpoint.checkpoint_id,
            "request_id": checkpoint.request_id,
            "user_prompt": checkpoint.user_prompt,
            "timestamp": checkpoint.timestamp.isoformat(),
            "backup_paths": checkpoint.backup_paths,
            "git_commit": checkpoint.git_commit,
            "files_affected": checkpoint.files_affected,
        }
        metadata_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _remove_checkpoint(self, checkpoint_id: str) -> None:
        """Remove a checkpoint and its metadata."""
        if checkpoint_id in self._checkpoints:
            del self._checkpoints[checkpoint_id]

        # Remove metadata file
        metadata_path = self._backups_dir / f"{checkpoint_id}.json"
        if metadata_path.exists():
            metadata_path.unlink()

    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash if available."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(self._root),
                timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
        return None

    def stats(self) -> Dict[str, Any]:
        """Return rollback manager statistics."""
        return {
            "total_checkpoints": len(self._checkpoints),
            "backups_dir": str(self._backups_dir),
            "backups_dir_exists": self._backups_dir.exists(),
        }


# Convenience functions

def create_checkpoint(
    project_root: str,
    change_set: Optional[Any] = None,
    request_id: Optional[str] = None,
    user_prompt: Optional[str] = None,
) -> str:
    """Convenience function to create a checkpoint."""
    manager = RollbackManager(project_root)
    return manager.create_checkpoint(change_set, request_id, user_prompt)


def rollback(project_root: str, checkpoint_id: str) -> RollbackResult:
    """Convenience function to rollback to a checkpoint."""
    manager = RollbackManager(project_root)
    return manager.rollback(checkpoint_id)

# ============================================================================
# SECTION: ai.editing.change_preview (ai/editing/change_preview.py)
# ============================================================================
"""
change_preview.py — Preview window for code changes.

Creates a visual preview showing:
  - Changed files list
  - Diff hunks with line numbers
  - Reason for each change
  - Affected functions
  - Estimated impact

User must approve changes before they are applied.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QTextEdit, QLabel, QPushButton, QFrame, QScrollArea, QSplitter,
    QTreeWidget, QTreeWidgetItem, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from core.logger import setup_logger

from ai.editing.change_request import ChangeRequest, ChangeStatus
from ai.editing.change_set import ChangeSet, OperationType
from ai.editing.diff_generator import DiffResult, DiffSummary


logger = setup_logger(__name__)


@dataclass
class PreviewResult:
    """Result from the preview window."""
    approved:  bool
    changes:   List[Dict[str, Any]]
    timestamp: datetime


class ChangePreview(QWidget):
    """
    Preview window showing proposed code changes.

    Displays:
      - Files changed list with icons
      - Diff view with line numbers
      - Reason and metadata
      - Apply/Reject buttons

    Usage:
        preview = ChangePreview(request, diff_results, summary)
        approved = preview.exec_()
    """

    approved = Signal()
    rejected = Signal()

    def __init__(
        self,
        request: ChangeRequest,
        diff_results: List[DiffResult],
        summary: DiffSummary,
    ):
        super().__init__()
        self.request = request
        self.diff_results = diff_results
        self.summary = summary
        self._user_approved = False

        self.setWindowTitle(f"Code Changes: {request.user_prompt[:50]}...")
        self.setMinimumSize(900, 700)

        logger.debug(
            f"ChangePreview initialized with {summary.total_files} files, "
            f"{summary.total_hunks} hunks."
        )

        self._setup_ui()
        self._populate_data()

    # ── UI Setup ─────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        """Build the preview window UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ── Header ─────────────────────────────────────
        header = self._create_header()
        main_layout.addWidget(header)

        # ── Splitter: Files | Diff ─────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setSizes([300, 600])

        # Files list
        files_widget = self._create_files_panel()
        splitter.addWidget(files_widget)

        # Diff view
        diff_widget = self._create_diff_panel()
        splitter.addWidget(diff_widget)

        main_layout.addWidget(splitter)

        # ── Footer: Buttons ────────────────────────────
        footer = self._create_footer()
        main_layout.addWidget(footer)

    def _create_header(self) -> QWidget:
        """Create the header with request info."""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #111113;
                border-bottom: 1px solid #252528;
            }
        """)
        widget.setFixedHeight(60)

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        # Prompt line
        prompt_label = QLabel(self.request.user_prompt)
        prompt_label.setStyleSheet("""
            color: #E2E2E6;
            font-size: 14px;
            font-weight: 600;
            background-color: transparent;
        """)
        prompt_label.setWordWrap(True)
        layout.addWidget(prompt_label)

        # Meta line
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(16)

        files_label = QLabel(f"{self.summary.total_files} file(s) changed")
        files_label.setStyleSheet("""
            color: #52525C;
            font-size: 11px;
            background-color: transparent;
        """)
        meta_layout.addWidget(files_label)

        added_label = QLabel(f"+{self.summary.lines_added} lines")
        added_label.setStyleSheet("""
            color: #22C55E;
            font-size: 11px;
            font-weight: 600;
            background-color: transparent;
        """)
        meta_layout.addWidget(added_label)

        removed_label = QLabel(f"-{self.summary.lines_removed} lines")
        removed_label.setStyleSheet("""
            color: #EF4444;
            font-size: 11px;
            font-weight: 600;
            background-color: transparent;
        """)
        meta_layout.addWidget(removed_label)

        layout.addLayout(meta_layout)

        return widget

    def _create_files_panel(self) -> QWidget:
        """Create the files changed list panel."""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #0D0D0F;
                border-right: 1px solid #252528;
            }
        """)

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title
        title = QLabel("CHANGED FILES")
        title.setStyleSheet("""
            color: #52525C;
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.7px;
            padding: 8px 16px;
            background-color: #111113;
            border-bottom: 1px solid #252528;
        """)
        layout.addWidget(title)

        # File list
        self._file_list = QListWidget()
        self._file_list.setStyleSheet("""
            QListWidget {
                background-color: #0D0D0F;
                border: none;
                padding: 8px;
            }
            QListWidget::item {
                padding: 8px 16px;
                min-height: 32px;
                border-radius: 2px;
            }
            QListWidget::item:hover {
                background-color: #161618;
            }
            QListWidget::item:selected {
                background-color: #1E3A5F;
            }
        """)
        self._file_list.itemSelectionChanged.connect(self._on_file_selected)
        layout.addWidget(self._file_list)

        # Summary stats
        stats_widget = QWidget()
        stats_widget.setStyleSheet("background-color: #111113;")
        stats_layout = QVBoxLayout(stats_widget)
        stats_layout.setContentsMargins(16, 12, 16, 12)
        stats_layout.setSpacing(8)

        # File type breakdown
        create_count = self.summary.files_created
        delete_count = self.summary.files_deleted
        modify_count = self.summary.files_modified

        if create_count > 0:
            create_label = QLabel(f"  + {create_count} new file(s)")
            create_label.setStyleSheet("""
                color: #22C55E;
                font-size: 11px;
                background-color: transparent;
            """)
            stats_layout.addWidget(create_label)

        if delete_count > 0:
            delete_label = QLabel(f"  × {delete_count} deleted file(s)")
            delete_label.setStyleSheet("""
                color: #EF4444;
                font-size: 11px;
                background-color: transparent;
            """)
            stats_layout.addWidget(delete_label)

        if modify_count > 0:
            modify_label = QLabel(f"  ∼ {modify_count} modified file(s)")
            modify_label.setStyleSheet("""
                color: #F59E0B;
                font-size: 11px;
                background-color: transparent;
            """)
            stats_layout.addWidget(modify_label)

        layout.addWidget(stats_widget)

        return widget

    def _create_diff_panel(self) -> QWidget:
        """Create the diff view panel."""
        widget = QWidget()
        widget.setStyleSheet("background-color: #0D0D0F;")

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Diff viewer (read-only text edit with monospace font)
        self._diff_view = QTextEdit()
        self._diff_view.setReadOnly(True)
        self._diff_view.setLineWrapMode(QTextEdit.NoWrap)
        self._diff_view.setFont(QFont("JetBrains Mono", 11))

        self._diff_view.setStyleSheet("""
            QTextEdit {
                background-color: #0D0D0F;
                color: #E2E2E6;
                border: none;
                padding: 16px;
            }
        """)

        layout.addWidget(self._diff_view)

        # Footer info
        info_widget = QWidget()
        info_widget.setStyleSheet("background-color: #111113;")
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(16, 8, 16, 8)
        info_layout.setSpacing(16)

        # Reason
        reason_label = QLabel(f"Reason: {self.request.reason}")
        reason_label.setStyleSheet("""
            color: #52525C;
            font-size: 10px;
            background-color: transparent;
        """)
        reason_label.setWordWrap(True)
        info_layout.addWidget(reason_label)

        # File count badge
        badge = QLabel(f"{self.summary.total_hunks} hunks")
        badge.setStyleSheet("""
            background-color: #1C1C1F;
            color: #52525C;
            font-size: 9px;
            padding: 2px 8px;
            border-radius: 2px;
            border: 1px solid #252528;
        """)
        info_layout.addWidget(badge)

        layout.addWidget(info_widget)

        return widget

    def _create_footer(self) -> QWidget:
        """Create the action buttons footer."""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #111113;
                border-top: 1px solid #252528;
            }
        """)
        widget.setFixedHeight(50)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        # Approve button
        approve_btn = QPushButton("Approve Changes")
        approve_btn.setFixedHeight(30)
        approve_btn.setStyleSheet("""
            QPushButton {
                background-color: #22C55E;
                color: #064E3B;
                font-size: 12px;
                font-weight: 600;
                border: none;
                border-radius: 4px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background-color: #16A34A;
            }
            QPushButton:pressed {
                background-color: #15803D;
            }
        """)
        approve_btn.clicked.connect(self._on_approve)
        layout.addWidget(approve_btn)

        # Reject button
        reject_btn = QPushButton("Reject")
        reject_btn.setFixedHeight(30)
        reject_btn.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: #7F1D1D;
                font-size: 12px;
                font-weight: 600;
                border: none;
                border-radius: 4px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background-color: #DC2626;
            }
            QPushButton:pressed {
                background-color: #B91C1C;
            }
        """)
        reject_btn.clicked.connect(self._on_reject)
        layout.addWidget(reject_btn)

        # Cancel button (for window close)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(30)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #E5E7EB;
                font-size: 12px;
                font-weight: 500;
                border: none;
                border-radius: 4px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)
        cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(cancel_btn)

        layout.addStretch()

        return widget

    # ── Data Population ──────────────────────────────────────────────────────

    def _populate_data(self) -> None:
        """Populate the UI with change data."""
        self._file_list.clear()

        for diff in self.diff_results:
            # Create list item
            item = QListWidgetItem(self._file_list)

            # Determine icon and text
            if diff.op_type == OperationType.CREATE:
                icon = "+"
                color = "#22C55E"
            elif diff.op_type == OperationType.DELETE:
                icon = "×"
                color = "#EF4444"
            elif diff.op_type == OperationType.MODIFY:
                icon = "∼"
                color = "#F59E0B"
            else:
                icon = "?"
                color = "#52525C"

            text = f"  {icon}  {Path(diff.file_path).name}"
            item.setText(text)
            item.setForeground(QColor(color))
            item.setData(Qt.UserRole, diff)
            item.setSizeHint(item.sizeHint())

            self._file_list.addItem(item)

        # Select first file automatically
        if self._file_list.count() > 0:
            self._file_list.setCurrentRow(0)

    def _on_file_selected(self) -> None:
        """Show diff for selected file."""
        current_item = self._file_list.currentItem()
        if not current_item:
            return

        diff = current_item.data(Qt.UserRole)
        if not diff:
            return

        # Generate diff text
        diff_text = self._generate_diff_text(diff)
        self._diff_view.setPlainText(diff_text)

    def _generate_diff_text(self, diff: DiffResult) -> str:
        """Generate formatted diff text for display."""
        lines = []

        # Header
        lines.append(f"File: {diff.file_path}")
        lines.append("-" * 60)
        lines.append(f"Operation: {diff.op_type.value.upper()}")
        lines.append(f"Lines: +{diff.summary.get('lines_added', 0)} "
                     f"-{diff.summary.get('lines_removed', 0)}")
        lines.append("")

        # Hunks
        for i, hunk in enumerate(diff.hunks):
            lines.append(f"Hunk {i + 1}")
            lines.append("-" * 40)

            if hunk["type"] == "create":
                lines.append(f"+ Added {hunk['added']} lines:")
                lines.append(hunk.get("content", "")[:1000])

            elif hunk["type"] == "delete":
                lines.append(f"- Removed {hunk['removed']} lines:")
                lines.append(hunk.get("content", "")[:1000])

            else:
                for status, text in hunk.get("context", []):
                    if status == "add":
                        lines.append(f"+ {text}")
                    elif status == "remove":
                        lines.append(f"- {text}")
                    else:
                        lines.append(f"  {text}")

            lines.append("")

        return "\n".join(lines)

    # ── Event Handlers ───────────────────────────────────────────────────────

    def _on_approve(self) -> None:
        """User approved the changes."""
        self._user_approved = True
        self.approved.emit()
        self.close()

    def _on_reject(self) -> None:
        """User rejected the changes."""
        self._user_approved = False
        self.rejected.emit()
        self.close()

    def _on_cancel(self) -> None:
        """User cancelled (closed window)."""
        self._user_approved = False
        self.close()

    def exec(self) -> bool:
        """Show the preview and return whether it was approved."""
        self.show()
        return self._user_approved

# ============================================================================
# SECTION: ai.editing.change_applier (ai/editing/change_applier.py)
# ============================================================================
"""
change_applier.py — Safe file modification and application.

Applies approved patches to files with support for:
  - Atomic operations (all-or-nothing)
  - Progress updates via EventBus
  - Failure recovery
  - Git checkpoint creation

This is the final step before changes are committed to the project.
"""

import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

from core.logger import setup_logger
from core.event_bus import EventBus

from ai.editing.change_request import ChangeRequest, ChangeStatus
from ai.editing.change_set import ChangeSet, ChangeOperation, OperationType, Hunk
from ai.editing.rollback_manager import RollbackManager
from ai.intelligence.dependency_graph import DependencyGraph


logger = setup_logger(__name__)


@dataclass
class ApplyResult:
    """
    Result of applying a change set.

    Attributes:
        success:        True if all operations succeeded.
        applied_count:  Number of operations successfully applied.
        failed_count:   Number of operations that failed.
        errors:         List of error messages.
        rollback_id:    ID of the rollback point created.
    """
    success:       bool
    applied_count: int
    failed_count:  int
    errors:        List[str]
    rollback_id:   Optional[str]


class ChangeApplier:
    """
    Applies approved patches to files safely.

    Features:
      - Creates rollback points before any changes
      - Processes operations in dependency order
      - Supports atomic operations (rollback on failure)
      - Publishes progress events to EventBus

    Usage:
        applier = ChangeApplier(event_bus, project_root)
        result = applier.apply(change_set, request)
    """

    def __init__(
        self,
        event_bus: EventBus,
        project_root: str,
    ) -> None:
        self.event_bus = event_bus
        self._root = Path(project_root)
        self._rollback_manager = RollbackManager(project_root)
        self._dependency_graph = DependencyGraph()
        self._dependency_graph_built = False
        self._pending_confirmations: Dict[str, tuple[ChangeSet, ChangeRequest]] = {}

        logger.debug(f"ChangeApplier initialized (root='{self._root.name}').")

    # ── Public API ─────────────────────────────────────────────────────────

    def apply(
        self,
        change_set: ChangeSet,
        request: ChangeRequest,
    ) -> ApplyResult:
        """
        Apply all operations in the change set.

        Args:
            change_set: The ChangeSet with all proposed operations.
            request:    The ChangeRequest being applied.

        Returns:
            ApplyResult with success/failure info.
        """
        if change_set.is_empty():
            logger.warning("ChangeApplier: empty change set — nothing to apply.")
            return ApplyResult(
                success=True,
                applied_count=0,
                failed_count=0,
                errors=[],
                rollback_id=None,
            )

        try:
            if not self._dependency_graph_built:
                self._dependency_graph.build(self._root)
                self._dependency_graph_built = True
            changed_files = [op.source_path for op in change_set.operations]
            impact = self._dependency_graph.get_impact_report(changed_files)
            self.event_bus.publish("change_impact_analyzed", {
                "request_id": request.request_id,
                **impact,
            })
        except Exception as exc:
            logger.warning("Dependency impact analysis skipped: %s", exc)

        # Sort operations by type and dependencies
        operations = self._sort_operations(change_set.operations)

        if self._has_unconfirmed_destructive_changes(operations, request):
            self._pending_confirmations[request.request_id] = (change_set, request)
            self._publish_confirmation_required(request, operations)
            return ApplyResult(
                success=False,
                applied_count=0,
                failed_count=len([op for op in operations if op.op_type == OperationType.DELETE]),
                errors=["Destructive file changes require confirmation before applying."],
                rollback_id=None,
            )

        # Create rollback checkpoint
        rollback_id = self._rollback_manager.create_checkpoint(
            change_set=change_set,
            request_id=request.request_id,
            user_prompt=request.user_prompt,
        )
        request = request.with_rollback_id(rollback_id)

        logger.info(
            f"ChangeApplier: applying {len(change_set.operations)} operations, "
            f"rollback_id={rollback_id[:8]}..."
        )
        self._publish_progress(request, 0, "Creating rollback checkpoint")

        # Apply operations
        applied = 0
        failed = 0
        errors: List[str] = []

        for i, op in enumerate(operations):
            try:
                self._apply_operation(op, request)
                applied += 1
                self._publish_progress(request, int((i + 1) / len(operations) * 100))
            except Exception as exc:
                failed += 1
                errors.append(f"{op.op_type.value.upper()} {op.source_path}: {exc}")
                logger.error(f"ChangeApplier: failed to apply {op.op_type.value} for {op.source_path}: {exc}")

                # Attempt rollback on first failure
                if failed == 1:
                    logger.warning("ChangeApplier: failure detected, initiating rollback.")
                    self._rollback_manager.rollback(rollback_id)
                    return ApplyResult(
                        success=False,
                        applied_count=applied,
                        failed_count=failed,
                        errors=errors,
                        rollback_id=rollback_id,
                    )

        # Update request status
        request = request.with_status(ChangeStatus.APPLIED)

        # Publish completion
        self._publish_progress(request, 100, "Application complete")
        self._publish_complete(request, change_set, applied, failed, errors)

        return ApplyResult(
            success=failed == 0,
            applied_count=applied,
            failed_count=failed,
            errors=errors,
            rollback_id=rollback_id,
        )

    def confirm_pending(self, request_id: str) -> Optional[ApplyResult]:
        """Apply a previously blocked destructive change request after user confirmation."""
        pending = self._pending_confirmations.pop(request_id, None)
        if not pending:
            return None

        change_set, request = pending
        confirmed_request = request.with_metadata("confirmed_destructive", True)
        return self.apply(change_set, confirmed_request)

    # ── Operation application ────────────────────────────────────────────────

    def _apply_operation(self, op: ChangeOperation, request: ChangeRequest) -> None:
        """Apply a single operation."""
        if op.op_type == OperationType.CREATE:
            self._apply_create(op)
        elif op.op_type == OperationType.DELETE:
            self._apply_delete(op, request)
        elif op.op_type == OperationType.MODIFY:
            self._apply_modify(op)
        elif op.op_type == OperationType.RENAME:
            self._apply_rename(op)
        elif op.op_type == OperationType.MOVE:
            self._apply_move(op)

    def _apply_create(self, op: ChangeOperation) -> None:
        """Create a new file."""
        path = self._root / op.source_path
        path.parent.mkdir(parents=True, exist_ok=True)
        content = op.content or ""
        path.write_text(content, encoding="utf-8")
        logger.info(f"ChangeApplier: created '{op.source_path}' ({len(content)} chars)")

    def _apply_delete(self, op: ChangeOperation, request: ChangeRequest) -> None:
        """Delete a file."""
        path = self._root / op.source_path
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            logger.info(f"ChangeApplier: deleted '{op.source_path}'")
        else:
            logger.warning(f"ChangeApplier: file not found for deletion: {op.source_path}")

    def _apply_modify(self, op: ChangeOperation) -> None:
        """Modify a file using hunks."""
        path = self._root / op.source_path
        content = path.read_text(encoding="utf-8")

        # Apply each hunk
        new_content = content
        for hunk in op.hunks:
            new_content = self._apply_hunk(new_content, hunk)

        path.write_text(new_content, encoding="utf-8")
        logger.info(
            f"ChangeApplier: modified '{op.source_path}', "
            f"{len(op.hunks)} hunks applied"
        )

    def _apply_rename(self, op: ChangeOperation) -> None:
        """Rename a file."""
        src = self._root / op.source_path
        dst = self._root / op.dest_path
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
            logger.info(f"ChangeApplier: renamed '{op.source_path}' → '{op.dest_path}'")
        else:
            raise FileNotFoundError(f"Source file not found: {op.source_path}")

    def _apply_move(self, op: ChangeOperation) -> None:
        """Move a file to a new location."""
        self._apply_rename(op)

    # ── Hunk application ─────────────────────────────────────────────────────

    def _apply_hunk(self, content: str, hunk: Hunk) -> str:
        """Apply a single hunk to content."""
        lines = content.splitlines(keepends=True)

        # Remove old lines
        start_idx = hunk.old_start - 1
        end_idx = start_idx + hunk.old_lines

        if start_idx < 0:
            start_idx = 0
        if end_idx > len(lines):
            end_idx = len(lines)

        if start_idx <= end_idx:
            del lines[start_idx:end_idx]

        # Insert new lines
        new_lines = hunk.new_text.splitlines(keepends=True)
        if new_lines:
            lines[start_idx:start_idx] = new_lines

        return "".join(lines)

    # ── Utilities ────────────────────────────────────────────────────────────

    def _sort_operations(self, operations: List[ChangeOperation]) -> List[ChangeOperation]:
        """
        Sort operations to handle dependencies correctly.

        Order: Creates → Deletes → Modifies → Renames → Moves
        """
        by_type: Dict[OperationType, List[ChangeOperation]] = {}

        for op in operations:
            if op.op_type not in by_type:
                by_type[op.op_type] = []
            by_type[op.op_type].append(op)

        # Apply order: create first, then deletes, then modifies
        order = [OperationType.CREATE, OperationType.DELETE, OperationType.MODIFY,
                 OperationType.RENAME, OperationType.MOVE]

        result = []
        for op_type in order:
            result.extend(by_type.get(op_type, []))

        return result

    def _publish_progress(
        self,
        request: ChangeRequest,
        percent: int,
        message: str = "",
    ) -> None:
        """Publish progress event to EventBus."""
        self.event_bus.publish("edit_progress", {
            "request_id": request.request_id,
            "percent": percent,
            "message": message,
            "status": request.status.value,
        })

    def _publish_complete(
        self,
        request: ChangeRequest,
        change_set: ChangeSet,
        applied: int,
        failed: int,
        errors: List[str],
    ) -> None:
        """Publish completion event to EventBus."""
        self.event_bus.publish("edit_complete", {
            "request_id": request.request_id,
            "success": failed == 0,
            "applied": applied,
            "failed": failed,
            "errors": errors,
            "files": change_set.files,
            "rollback_id": request.rollback_id,
        })

    def _has_unconfirmed_destructive_changes(self, operations: List[ChangeOperation], request: ChangeRequest) -> bool:
        """Block destructive changes until explicitly confirmed."""
        if request.metadata.get("confirmed_destructive", False):
            return False
        return any(op.op_type == OperationType.DELETE for op in operations)

    def _publish_confirmation_required(self, request: ChangeRequest, operations: List[ChangeOperation]) -> None:
        """Notify the UI that confirmation is required before destructive changes apply."""
        destructive_files = [op.source_path for op in operations if op.op_type == OperationType.DELETE]
        self.event_bus.publish("edit_confirmation_required", {
            "request_id": request.request_id,
            "reason": "Deleting files or folders requires confirmation.",
            "files": destructive_files,
            "operation_count": len(destructive_files),
        })

# ============================================================================
# SECTION: ai.editing.review_model (ai/editing/review_model.py)
# ============================================================================
"""
review_model.py — Selection state for the multi-file change review UI.

Qt-free so it can be unit-tested headlessly. Wraps a :class:`ChangeSet` and
tracks, per operation (and per hunk for MODIFY operations), whether the user has
accepted or rejected it. From that selection it can:

  * compute the *effective* new content of a file (only the accepted hunks
    applied on top of the on-disk original), for live diff preview, and
  * emit a filtered :class:`ChangeSet` containing only what the user accepted,
    ready to hand to :class:`ChangeApplier`.

The original on-disk file is the source of truth for MODIFY/DELETE; CREATE
carries its full content inline.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ai.editing.change_set import ChangeSet, ChangeOperation, OperationType, Hunk


class ReviewModel:
    """Tracks accept/reject state over a ChangeSet's operations and hunks."""

    def __init__(self, change_set: ChangeSet, project_root: str = "") -> None:
        self._ops: List[ChangeOperation] = list(change_set.operations)
        self._root = Path(project_root) if project_root else None
        self._op_selected: Dict[int, bool] = {i: True for i in range(len(self._ops))}
        # (op_index, hunk_index) -> accepted
        self._hunk_selected: Dict[Tuple[int, int], bool] = {}
        for i, op in enumerate(self._ops):
            for h in range(len(op.hunks)):
                self._hunk_selected[(i, h)] = True
        self._orig_cache: Dict[int, Optional[str]] = {}

    # ── enumeration ────────────────────────────────────────────────────────────
    def operations(self) -> List[ChangeOperation]:
        return list(self._ops)

    def operation(self, index: int) -> ChangeOperation:
        return self._ops[index]

    def count(self) -> int:
        return len(self._ops)

    # ── selection state ─────────────────────────────────────────────────────────
    def is_op_selected(self, index: int) -> bool:
        return self._op_selected.get(index, False)

    def set_op_selected(self, index: int, value: bool) -> None:
        if index in self._op_selected:
            self._op_selected[index] = bool(value)
            # Cascade to hunks so a rejected file rejects all its hunks.
            for (oi, hi) in list(self._hunk_selected):
                if oi == index:
                    self._hunk_selected[(oi, hi)] = bool(value)

    def is_hunk_selected(self, op_index: int, hunk_index: int) -> bool:
        return self._hunk_selected.get((op_index, hunk_index), False)

    def set_hunk_selected(self, op_index: int, hunk_index: int, value: bool) -> None:
        if (op_index, hunk_index) in self._hunk_selected:
            self._hunk_selected[(op_index, hunk_index)] = bool(value)
            # A file is "selected" if any of its hunks remain accepted.
            if value:
                self._op_selected[op_index] = True
            elif not self._any_hunk_selected(op_index):
                self._op_selected[op_index] = False

    def _any_hunk_selected(self, op_index: int) -> bool:
        hunks = [(oi, hi) for (oi, hi) in self._hunk_selected if oi == op_index]
        if not hunks:
            return self._op_selected.get(op_index, False)
        return any(self._hunk_selected[k] for k in hunks)

    # ── content resolution ───────────────────────────────────────────────────────
    def original_content(self, index: int) -> Optional[str]:
        """On-disk content of the operation's source file (None if absent/new)."""
        if index in self._orig_cache:
            return self._orig_cache[index]
        op = self._ops[index]
        content: Optional[str] = None
        if op.op_type in (OperationType.MODIFY, OperationType.DELETE,
                          OperationType.RENAME, OperationType.MOVE):
            path = Path(op.source_path)
            if self._root and not path.is_absolute():
                path = self._root / path
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                content = None
        self._orig_cache[index] = content
        return content

    def proposed_content(self, index: int) -> Optional[str]:
        """Full new content with ALL hunks applied (ignores selection)."""
        op = self._ops[index]
        if op.op_type == OperationType.CREATE:
            return op.content or ""
        if op.op_type == OperationType.DELETE:
            return None
        if op.op_type == OperationType.MODIFY:
            base = self.original_content(index) or ""
            return self._apply_hunks(base, list(op.hunks))
        return self.original_content(index)

    def effective_content(self, index: int) -> Optional[str]:
        """New content with only the ACCEPTED hunks applied — for live preview."""
        op = self._ops[index]
        if op.op_type == OperationType.CREATE:
            return op.content or "" if self.is_op_selected(index) else None
        if op.op_type == OperationType.DELETE:
            return None if self.is_op_selected(index) else self.original_content(index)
        if op.op_type == OperationType.MODIFY:
            base = self.original_content(index) or ""
            accepted = [h for hi, h in enumerate(op.hunks)
                        if self.is_hunk_selected(index, hi)]
            return self._apply_hunks(base, accepted)
        return self.original_content(index)

    @staticmethod
    def _apply_hunks(content: str, hunks: List[Hunk]) -> str:
        """Apply hunks to content (reverse order keeps line indices stable)."""
        if not hunks:
            return content
        lines = content.splitlines(keepends=True)
        result = lines.copy()
        for hunk in sorted(hunks, key=lambda h: h.old_start, reverse=True):
            if hunk.old_lines > 0:
                del result[hunk.old_start - 1:hunk.old_start - 1 + hunk.old_lines]
            new_lines = hunk.new_text.splitlines(keepends=True)
            if new_lines or hunk.new_lines > 0:
                result[hunk.old_start - 1:hunk.old_start - 1] = new_lines
        return "".join(result)

    # ── output ─────────────────────────────────────────────────────────────────
    def selected_change_set(self) -> ChangeSet:
        """Build a ChangeSet containing only the accepted operations/hunks."""
        ops: List[ChangeOperation] = []
        for i, op in enumerate(self._ops):
            if not self.is_op_selected(i):
                continue
            if op.op_type == OperationType.MODIFY:
                accepted = [h for hi, h in enumerate(op.hunks)
                            if self.is_hunk_selected(i, hi)]
                if not accepted:
                    continue
                ops.append(ChangeOperation.modify_file(
                    op.source_path, accepted, op.reason))
            else:
                ops.append(op)
        return ChangeSet.from_operations(ops)

    def stats(self) -> Dict[str, int]:
        """Counts over the currently-accepted selection."""
        cs = self.selected_change_set()
        created = len(cs.get_operations_by_type(OperationType.CREATE))
        deleted = len(cs.get_operations_by_type(OperationType.DELETE))
        modified = len(cs.get_operations_by_type(OperationType.MODIFY))
        return {
            "files": len(cs.operations),
            "created": created,
            "deleted": deleted,
            "modified": modified,
            "hunks": cs.total_hunks,
        }



# ============================================================================
# SECTION: ai.editing.smart_patch_engine (4-Stage Fuzzy & AST Patch Engine)
# ============================================================================
import ast as _ast
import difflib as _difflib
import os
import re as _re
import shutil as _sh_shutil
import tempfile as _sh_tempfile
from dataclasses import dataclass as _dataclass, field as _field
from typing import List as _List, Optional as _Optional, Tuple as _Tuple, Dict as _Dict, Any as _Any


@_dataclass
class SmartPatchResult:
    success: bool
    new_content: str = ""
    stage_used: str = ""
    matched_start_line: int = 0
    matched_end_line: int = 0
    confidence: float = 0.0
    replacements: int = 0
    hunk: _Optional[Hunk] = None
    error: _Optional[str] = None
    candidate_lines: _List[int] = _field(default_factory=list)


class SmartPatchEngine:
    def __init__(self, fuzzy_threshold: float = 0.90) -> None:
        self.fuzzy_threshold = fuzzy_threshold

    @staticmethod
    def _leading_indent(line: str) -> str:
        return line[: len(line) - len(line.lstrip(" \t"))]

    @classmethod
    def _reindent_block(cls, new_text: str, ref_old_indent: str, actual_file_indent: str) -> str:
        if ref_old_indent == actual_file_indent:
            return new_text
        new_lines = new_text.splitlines(keepends=True)
        adjusted: _List[str] = []
        for ln in new_lines:
            if not ln.strip():
                adjusted.append(ln)
                continue
            if ref_old_indent and ln.startswith(ref_old_indent):
                adjusted.append(actual_file_indent + ln[len(ref_old_indent):])
            elif not ref_old_indent:
                adjusted.append(actual_file_indent + ln)
            else:
                old_spaces = len(ref_old_indent.expandtabs(4))
                target_spaces = len(actual_file_indent.expandtabs(4))
                cur_indent = cls._leading_indent(ln)
                cur_spaces = len(cur_indent.expandtabs(4))
                new_spaces = max(0, cur_spaces + (target_spaces - old_spaces))
                adjusted.append((" " * new_spaces) + ln.lstrip(" \t"))
        return "".join(adjusted)

    @staticmethod
    def _find_ast_symbol_span(content: str, symbol_name: str) -> _Optional[_Tuple[int, int]]:
        if not symbol_name:
            return None
        target = symbol_name.split(".")[-1].strip()
        try:
            tree = _ast.parse(content)
            for node in _ast.walk(tree):
                if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
                    if node.name == target and hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                        start = max(0, int(node.lineno) - 1)
                        if getattr(node, "decorator_list", None):
                            first_dec = min(getattr(d, "lineno", node.lineno) for d in node.decorator_list)
                            start = max(0, int(first_dec) - 1)
                        end = int(node.end_lineno or node.lineno)
                        return (start, end)
        except Exception:
            pass
        return None

    def apply_patch(
        self,
        content: str,
        old_text: str,
        new_text: str,
        start_line: _Optional[int] = None,
        end_line: _Optional[int] = None,
        symbol_name: _Optional[str] = None,
        occurrence: _Optional[int] = None,
        replace_all: bool = False,
    ) -> SmartPatchResult:
        if old_text is None or new_text is None:
            return SmartPatchResult(success=False, error="Both old_text and new_text must be provided.")
        if old_text == "":
            return SmartPatchResult(success=False, error="old_text cannot be empty for patch replacement.")

        line_sep = "\r\n" if "\r\n" in content and content.count("\r\n") >= content.count("\n") // 2 else "\n"
        norm_content = content.replace("\r\n", "\n")
        norm_old = old_text.replace("\r\n", "\n")
        norm_new = new_text.replace("\r\n", "\n")

        file_lines = norm_content.splitlines(keepends=True)
        old_lines = norm_old.splitlines(keepends=True)
        n_file = len(file_lines)
        n_old = len(old_lines)

        win_start = 0
        win_end = n_file
        if symbol_name:
            span = self._find_ast_symbol_span(norm_content, symbol_name)
            if span:
                win_start = max(0, span[0] - 3)
                win_end = min(n_file, span[1] + 3)
        if start_line is not None and start_line > 0:
            win_start = max(0, start_line - 5)
        if end_line is not None and end_line > 0:
            win_end = min(n_file, end_line + 5)

        if norm_old in norm_content:
            offsets: _List[int] = []
            pos = 0
            while True:
                idx = norm_content.find(norm_old, pos)
                if idx == -1:
                    break
                offsets.append(idx)
                pos = idx + max(1, len(norm_old))

            line_starts = [norm_content.count("\n", 0, off) + 1 for off in offsets]

            if start_line is not None and len(offsets) > 1:
                upper = end_line if (end_line is not None and end_line >= start_line) else (start_line + n_old + 2)
                scoped = [
                    (off, ln) for off, ln in zip(offsets, line_starts)
                    if start_line <= ln <= upper
                ]
                if not scoped:
                    closest = min(zip(offsets, line_starts), key=lambda pair: abs(pair[1] - start_line))
                    scoped = [closest]
                offsets = [x[0] for x in scoped]
                line_starts = [x[1] for x in scoped]
            elif symbol_name is not None and len(offsets) > 1:
                filtered = [
                    (off, ln) for off, ln in zip(offsets, line_starts)
                    if (win_start + 1) <= ln <= max(win_end + 1, win_start + 1)
                ]
                if filtered:
                    offsets = [x[0] for x in filtered]
                    line_starts = [x[1] for x in filtered]

            if replace_all:
                updated = norm_content.replace(norm_old, norm_new)
                if line_sep == "\r\n":
                    updated = updated.replace("\n", "\r\n")
                first_ln = line_starts[0] if line_starts else 1
                hunk = Hunk(
                    old_start=first_ln,
                    old_lines=n_old,
                    new_start=first_ln,
                    new_lines=len(norm_new.splitlines()) or 1,
                    old_text=norm_old,
                    new_text=norm_new,
                )
                return SmartPatchResult(
                    success=True,
                    new_content=updated,
                    stage_used="exact_all",
                    matched_start_line=first_ln,
                    matched_end_line=first_ln + n_old - 1,
                    confidence=1.0,
                    replacements=len(offsets),
                    hunk=hunk,
                )

            if len(offsets) > 1 and occurrence is None:
                return SmartPatchResult(
                    success=False,
                    error=(
                        f"Ambiguous patch: old_text matches {len(offsets)} locations at lines "
                        f"{line_starts}. Provide more context lines or specify start_line."
                    ),
                    candidate_lines=line_starts,
                )

            chosen_idx = (occurrence - 1) if (occurrence is not None and 1 <= occurrence <= len(offsets)) else 0
            chosen_off = offsets[chosen_idx]
            chosen_ln = line_starts[chosen_idx]
            updated = norm_content[:chosen_off] + norm_new + norm_content[chosen_off + len(norm_old):]
            if line_sep == "\r\n":
                updated = updated.replace("\n", "\r\n")
            hunk = Hunk(
                old_start=chosen_ln,
                old_lines=n_old,
                new_start=chosen_ln,
                new_lines=len(norm_new.splitlines()) or 1,
                old_text=norm_old,
                new_text=norm_new,
            )
            return SmartPatchResult(
                success=True,
                new_content=updated,
                stage_used="exact",
                matched_start_line=chosen_ln,
                matched_end_line=chosen_ln + n_old - 1,
                confidence=1.0,
                replacements=1,
                hunk=hunk,
            )

        if n_old > 0 and n_old <= n_file:
            old_rstripped = [ln.rstrip(" \t\r\n") for ln in old_lines]
            file_rstripped = [ln.rstrip(" \t\r\n") for ln in file_lines]
            s2_matches: _List[int] = [
                i for i in range(win_start, max(win_start, win_end - n_old + 1))
                if file_rstripped[i : i + n_old] == old_rstripped
            ]
            if not s2_matches and (win_start > 0 or win_end < n_file):
                s2_matches = [
                    i for i in range(0, n_file - n_old + 1)
                    if file_rstripped[i : i + n_old] == old_rstripped
                ]
            if len(s2_matches) == 1 or (s2_matches and occurrence is not None):
                idx = s2_matches[(occurrence - 1) if occurrence else 0]
                replacement = norm_new
                if file_lines[idx + n_old - 1].endswith("\n") and not replacement.endswith("\n"):
                    replacement += "\n"
                new_file_lines = file_lines[:idx] + replacement.splitlines(keepends=True) + file_lines[idx + n_old:]
                updated = "".join(new_file_lines)
                if line_sep == "\r\n":
                    updated = updated.replace("\n", "\r\n")
                hunk = Hunk(
                    old_start=idx + 1,
                    old_lines=n_old,
                    new_start=idx + 1,
                    new_lines=len(replacement.splitlines()),
                    old_text="".join(file_lines[idx : idx + n_old]),
                    new_text=replacement,
                )
                return SmartPatchResult(
                    success=True,
                    new_content=updated,
                    stage_used="whitespace_normalized",
                    matched_start_line=idx + 1,
                    matched_end_line=idx + n_old,
                    confidence=0.98,
                    replacements=1,
                    hunk=hunk,
                )

        old_stripped = [ln.strip() for ln in old_lines]
        non_empty_old = [ln for ln in old_lines if ln.strip()]
        if non_empty_old and n_old <= n_file:
            file_stripped = [ln.strip() for ln in file_lines]
            s3_matches: _List[int] = [
                i for i in range(win_start, max(win_start, win_end - n_old + 1))
                if file_stripped[i : i + n_old] == old_stripped
            ]
            if not s3_matches and (win_start > 0 or win_end < n_file):
                s3_matches = [
                    i for i in range(0, n_file - n_old + 1)
                    if file_stripped[i : i + n_old] == old_stripped
                ]
            if len(s3_matches) == 1 or (s3_matches and occurrence is not None):
                idx = s3_matches[(occurrence - 1) if occurrence else 0]
                first_non_empty_offset = next(j for j, ln in enumerate(old_lines) if ln.strip())
                ref_old_indent = self._leading_indent(old_lines[first_non_empty_offset])
                actual_file_indent = self._leading_indent(file_lines[idx + first_non_empty_offset])
                reindented_new = self._reindent_block(norm_new, ref_old_indent, actual_file_indent)
                if file_lines[idx + n_old - 1].endswith("\n") and not reindented_new.endswith("\n"):
                    reindented_new += "\n"
                new_file_lines = file_lines[:idx] + reindented_new.splitlines(keepends=True) + file_lines[idx + n_old:]
                updated = "".join(new_file_lines)
                if line_sep == "\r\n":
                    updated = updated.replace("\n", "\r\n")
                hunk = Hunk(
                    old_start=idx + 1,
                    old_lines=n_old,
                    new_start=idx + 1,
                    new_lines=len(reindented_new.splitlines()),
                    old_text="".join(file_lines[idx : idx + n_old]),
                    new_text=reindented_new,
                )
                return SmartPatchResult(
                    success=True,
                    new_content=updated,
                    stage_used="indentation_relative",
                    matched_start_line=idx + 1,
                    matched_end_line=idx + n_old,
                    confidence=0.95,
                    replacements=1,
                    hunk=hunk,
                )

        if n_old >= 2 and n_old <= n_file:
            old_norm_block = "\n".join(ln.strip() for ln in old_lines if ln.strip())
            best_ratio = 0.0
            second_best = 0.0
            best_idx = -1
            search_start = win_start if (win_end - win_start) >= n_old else 0
            search_end = win_end if (win_end - win_start) >= n_old else n_file
            for i in range(search_start, max(search_start, search_end - n_old + 1)):
                cand_block = "\n".join(ln.strip() for ln in file_lines[i : i + n_old] if ln.strip())
                if not cand_block:
                    continue
                ratio = _difflib.SequenceMatcher(None, old_norm_block, cand_block).ratio()
                if ratio > best_ratio:
                    second_best = best_ratio
                    best_ratio = ratio
                    best_idx = i
                elif ratio > second_best:
                    second_best = ratio

            if best_idx >= 0 and best_ratio >= self.fuzzy_threshold and (best_ratio - second_best) >= 0.03:
                first_non_empty_offset = next((j for j, ln in enumerate(old_lines) if ln.strip()), 0)
                ref_old_indent = self._leading_indent(old_lines[first_non_empty_offset])
                actual_file_indent = self._leading_indent(file_lines[best_idx + first_non_empty_offset])
                reindented_new = self._reindent_block(norm_new, ref_old_indent, actual_file_indent)
                if file_lines[best_idx + n_old - 1].endswith("\n") and not reindented_new.endswith("\n"):
                    reindented_new += "\n"
                new_file_lines = file_lines[:best_idx] + reindented_new.splitlines(keepends=True) + file_lines[best_idx + n_old:]
                updated = "".join(new_file_lines)
                if line_sep == "\r\n":
                    updated = updated.replace("\n", "\r\n")
                hunk = Hunk(
                    old_start=best_idx + 1,
                    old_lines=n_old,
                    new_start=best_idx + 1,
                    new_lines=len(reindented_new.splitlines()),
                    old_text="".join(file_lines[best_idx : best_idx + n_old]),
                    new_text=reindented_new,
                )
                return SmartPatchResult(
                    success=True,
                    new_content=updated,
                    stage_used="fuzzy_ast_anchor",
                    matched_start_line=best_idx + 1,
                    matched_end_line=best_idx + n_old,
                    confidence=round(best_ratio, 4),
                    replacements=1,
                    hunk=hunk,
                )

        return SmartPatchResult(
            success=False,
            error=f"Text not found in file: {old_text[:80]!r}",
        )

    _VALID_FILE_EXTS = {
        ".py", ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".js", ".jsx",
        ".ts", ".tsx", ".java", ".rs", ".go", ".rb", ".php", ".cs", ".swift",
        ".kt", ".scala", ".html", ".htm", ".css", ".scss", ".json", ".yaml",
        ".yml", ".toml", ".ini", ".cfg", ".md", ".txt", ".sh", ".bash",
        ".bat", ".ps1", ".sql", ".xml", ".lua", ".r", ".dart", ".zig",
    }
    _SPECIAL_FILENAMES = {"makefile", "dockerfile", "cmakelists.txt", "requirements.txt", "readme.md"}
    _FALSE_POSITIVE_STEMS = {
        "self", "cls", "current", "node", "head", "next", "prev", "data",
        "list", "dict", "str", "int", "float", "os", "sys", "re", "json",
        "math", "time", "pathlib", "typing", "st", "np", "pd", "plt",
        "llama", "qwen", "ollama", "window", "app", "console", "document",
        "std", "stdio", "stdlib", "string", "vector", "iostream",
    }
    _LANG_TO_EXT = {
        "python": ".py", "py": ".py",
        "c": ".c", "cpp": ".cpp", "c++": ".cpp", "cxx": ".cpp", "h": ".h", "hpp": ".hpp",
        "javascript": ".js", "js": ".js", "jsx": ".jsx",
        "typescript": ".ts", "ts": ".ts", "tsx": ".tsx",
        "java": ".java", "rust": ".rs", "rs": ".rs",
        "go": ".go", "golang": ".go", "ruby": ".rb", "rb": ".rb",
        "php": ".php", "csharp": ".cs", "cs": ".cs",
        "html": ".html", "css": ".css", "json": ".json",
        "yaml": ".yaml", "yml": ".yml", "toml": ".toml",
        "sql": ".sql", "sh": ".sh", "bash": ".sh", "shell": ".sh",
        "markdown": ".md", "md": ".md", "text": ".txt", "txt": ".txt",
    }

    @classmethod
    def _clean_candidate_path(cls, raw_candidate: str) -> _Optional[str]:
        if not raw_candidate:
            return None
        cand = raw_candidate.strip().strip("`'\"").strip()
        cand = _re.sub(r"^[#*>\-\s]+", "", cand).strip()
        cand = _re.sub(r"^(?:file|filename|path|create|modify|edit|write|save\s+as)\s*:\s*", "", cand, flags=_re.IGNORECASE).strip()
        cand = cand.strip("`'\"()[]{}.,:;!?")
        if not cand or " " in cand or "\n" in cand or "\t" in cand:
            return None
        if cand.startswith(("http://", "https://", "file://", "/")):
            if cand.startswith("/") and cand.count("/") == 1:
                cand = cand.lstrip("/")
            else:
                return None
        norm = cand.replace("\\", "/")
        parts = [p for p in norm.split("/") if p and p != "."]
        if not parts or any(p == ".." for p in parts):
            return None
        basename = parts[-1]
        if basename.lower() in cls._SPECIAL_FILENAMES:
            return "/".join(parts)
        stem, ext = os.path.splitext(basename)
        if not stem or not ext:
            return None
        if ext.lower() not in cls._VALID_FILE_EXTS:
            return None
        if len(parts) == 1 and stem.lower() in cls._FALSE_POSITIVE_STEMS:
            return None
        if not _re.match(r"^[A-Za-z0-9_\-\.]+$", basename):
            return None
        if len(parts) == 2 and parts[0].lower() in ("tools", "ui", "agent", "core", "models"):
            return basename
        return "/".join(parts)

    @classmethod
    def _extract_first_line_filename_comment(cls, code_body: str) -> _Tuple[_Optional[str], str]:
        lines = (code_body or "").splitlines()
        for idx, line in enumerate(lines[:3]):
            s = line.strip()
            if not s:
                continue
            m = _re.match(
                r"^(?:#+|//+|/\*+|<!--+|--+)\s*(?:file(?:name)?\s*:\s*)?([A-Za-z0-9_\-./\\]+\.[A-Za-z0-9]+)\s*(?:\*+/|-->+)?$",
                s,
                _re.IGNORECASE,
            )
            if m:
                cleaned = cls._clean_candidate_path(m.group(1))
                if cleaned:
                    return cleaned, code_body
            break
        return None, code_body

    @classmethod
    def _infer_filename_from_prose(cls, prose_before: str, user_prompt: str = "") -> _Optional[str]:
        search_window = (prose_before or "")[-600:]
        patterns = [
            r"(?:FILE|CREATE|MODIFY|EDIT|WRITE|PATH)\s*:\s*`?([A-Za-z0-9_\-./\\]+\.[A-Za-z0-9]+)`?",
            r"#{1,4}\s*`?([A-Za-z0-9_\-./\\]+\.[A-Za-z0-9]+)`?",
            r"(?:named|called|file|create|save\s+as|into|in|to|update|edit)\s+[`'\"]?([A-Za-z0-9_\-./\\]+\.[A-Za-z0-9]+)[`'\"]?",
            r"\*\*([A-Za-z0-9_\-./\\]+\.[A-Za-z0-9]+)\*\*",
            r"`([A-Za-z0-9_\-./\\]+\.[A-Za-z0-9]+)`",
        ]
        for pat in patterns:
            matches = list(_re.finditer(pat, search_window, _re.IGNORECASE))
            for m in reversed(matches):
                cand = cls._clean_candidate_path(m.group(1))
                if cand:
                    return cand
        if user_prompt:
            for pat in patterns:
                matches = list(_re.finditer(pat, user_prompt, _re.IGNORECASE))
                for m in reversed(matches):
                    cand = cls._clean_candidate_path(m.group(1))
                    if cand:
                        return cand
        return None

    @classmethod
    def _infer_filename_from_code_and_prompt(
        cls,
        code_body: str,
        lang: str = "",
        user_prompt: str = "",
        workspace_root: _Optional[str] = None,
        active_file: _Optional[str] = None,
    ) -> _Optional[str]:
        prompt_lower = (user_prompt or "").lower()
        wants_create = any(
            kw in prompt_lower
            for kw in (
                "create a file", "create file", "new file", "make a file",
                "write a file", "generate a file", "add a file", "create a ",
                "implement ", "write a program", "write code",
            )
        )
        wants_edit_active = any(
            kw in prompt_lower
            for kw in (
                "this file", "current file", "open file", "fix this",
                "update this", "add to it", "in it", "modify this",
            )
        )
        if active_file and wants_edit_active and not wants_create:
            try:
                if workspace_root:
                    rel = os.path.relpath(active_file, workspace_root).replace("\\", "/")
                    if not rel.startswith(".."):
                        return rel
                return Path(active_file).name
            except Exception:
                return Path(active_file).name

        if not wants_create and not active_file:
            if not _re.search(r"\b(?:class|def|int\s+main|void\s+\w+|function\s+\w+|struct\s+\w+)\b", code_body or ""):
                return None

        ext = cls._LANG_TO_EXT.get((lang or "").strip().lower(), "")
        if not ext:
            if _re.search(r"#include\s*<", code_body):
                ext = ".cpp" if ("iostream" in code_body or "std::" in code_body) else ".c"
            elif _re.search(r"\b(?:def\s+\w+|class\s+\w+|import\s+\w+)\b", code_body):
                ext = ".py"
            elif _re.search(r"\b(?:function\s+\w+|const\s+\w+\s*=|console\.log)\b", code_body):
                ext = ".js"
            else:
                ext = ".py"

        stem = None
        m_class = _re.search(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)", code_body)
        if m_class:
            cname = m_class.group(1)
            if cname.lower() not in ("node", "solution", "main", "base", "item", "element"):
                stem = _re.sub(r"(?<!^)(?=[A-Z])", "_", cname).lower()
        if not stem:
            topic_match = _re.search(
                r"(?:add|for|with|implement|create)\s+(?:a\s+|an\s+)?([a-z][a-z0-9_]+(?:\s+[a-z][a-z0-9_]+)?)\s+(?:function|funiton|program|class|implementation|script|code|in\b|on\b)",
                prompt_lower,
            )
            if topic_match:
                raw_topic = topic_match.group(1).strip()
                words = [w for w in raw_topic.split() if w not in ("file", "new", "simple", "basic", "python", "c", "cpp", "the", "a", "an")]
                if words:
                    stem = "_".join(words[:3])
        if not stem:
            m_fn = _re.search(r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)", code_body)
            if m_fn and not m_fn.group(1).startswith("__"):
                stem = m_fn.group(1).lower()
        if not stem:
            stem = "main" if ext in (".c", ".cpp", ".rs", ".go") else "generated_module"

        candidate = f"{stem}{ext}"
        return cls._clean_candidate_path(candidate)

    @classmethod
    def _build_create_or_modify_op(
        cls,
        fpath: str,
        code_body: str,
        root: _Optional[Path],
        reason: str = "AI Agent file operation",
    ) -> ChangeOperation:
        if root is not None:
            cand = (root / fpath).resolve()
            if cand.is_file():
                try:
                    old_text = cand.read_text(encoding="utf-8")
                    hunk = Hunk(
                        old_start=1,
                        old_lines=max(1, len(old_text.splitlines())),
                        new_start=1,
                        new_lines=max(1, len(code_body.splitlines())),
                        old_text=old_text,
                        new_text=code_body,
                    )
                    return ChangeOperation.modify_file(fpath, [hunk], reason=reason)
                except Exception:
                    pass
        return ChangeOperation.create_file(fpath, code_body, reason=reason)

    @classmethod
    def extract_operations_from_llm_response(
        cls,
        response_text: str,
        workspace_root: _Optional[str] = None,
        user_prompt: str = "",
        active_file: _Optional[str] = None,
    ) -> _List[ChangeOperation]:
        if not response_text:
            return []
        operations: _List[ChangeOperation] = []
        root = Path(workspace_root).resolve() if workspace_root else None
        engine = cls()

        # ── 1. Extract SEARCH / REPLACE blocks ──────────────────────────────
        sr_pattern = _re.compile(
            r"(?:(?:FILE|MODIFY|EDIT|PATH|###\s*(?:FILE\s*:?)?)\s*:?\s*`?([^`\n]+?)`?\s*\n)?"
            r"<{5,9}\s*SEARCH\s*\n(.*?)\n={5,9}\s*\n(.*?)\n>{5,9}\s*REPLACE",
            _re.DOTALL | _re.IGNORECASE,
        )
        last_file_path: _Optional[str] = None
        hunks_by_file: _Dict[str, _List[Hunk]] = {}

        for match in sr_pattern.finditer(response_text):
            raw_header = (match.group(1) or "").strip()
            raw_path = cls._clean_candidate_path(raw_header) if raw_header else None
            if not raw_path:
                before_text = response_text[:match.start()]
                raw_path = cls._infer_filename_from_prose(before_text, user_prompt=user_prompt) or last_file_path
            old_block = match.group(2)
            new_block = match.group(3)

            if not raw_path and active_file:
                try:
                    raw_path = (
                        os.path.relpath(active_file, str(root)).replace("\\", "/")
                        if root else Path(active_file).name
                    )
                except Exception:
                    raw_path = Path(active_file).name
            if not raw_path and root and old_block.strip():
                for p in root.rglob("*"):
                    if p.is_file() and p.suffix.lower() in cls._VALID_FILE_EXTS:
                        try:
                            txt = p.read_text(encoding="utf-8", errors="ignore")
                            if old_block.strip() in txt:
                                raw_path = str(p.relative_to(root)).replace("\\", "/")
                                break
                        except Exception:
                            pass
            if not raw_path:
                continue
            last_file_path = raw_path
            file_content = ""
            if root:
                cand = (root / raw_path).resolve()
                if cand.is_file():
                    try:
                        file_content = cand.read_text(encoding="utf-8")
                    except Exception:
                        file_content = ""
            if file_content:
                patch_res = engine.apply_patch(file_content, old_block, new_block)
                if patch_res.success and patch_res.hunk:
                    hunks_by_file.setdefault(raw_path, []).append(patch_res.hunk)
                    continue
            hunks_by_file.setdefault(raw_path, []).append(
                Hunk(
                    old_start=1,
                    old_lines=max(1, len(old_block.splitlines())),
                    new_start=1,
                    new_lines=max(1, len(new_block.splitlines())),
                    old_text=old_block,
                    new_text=new_block,
                )
            )

        for fpath, hunks in hunks_by_file.items():
            operations.append(ChangeOperation.modify_file(fpath, hunks, reason="AI SEARCH/REPLACE patch"))

        # ── 2. Extract <tool_call> JSON write/create/edit operations ────────
        tc_pattern = _re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", _re.DOTALL | _re.IGNORECASE)
        for m in tc_pattern.finditer(response_text):
            try:
                payload = json.loads(m.group(1))
                tname = str(payload.get("name") or payload.get("tool") or "").lower()
                args = payload.get("arguments") or payload.get("params") or {}
                if isinstance(args, str):
                    args = json.loads(args)
                op_type = str(args.get("operation") or tname).lower()
                fpath = cls._clean_candidate_path(str(args.get("path") or args.get("file_path") or args.get("filename") or ""))
                content = args.get("content") or args.get("code") or args.get("new_content")
                if fpath and isinstance(content, str) and fpath not in hunks_by_file:
                    if any(k in op_type for k in ("write", "create", "edit", "save", "file")):
                        operations.append(cls._build_create_or_modify_op(fpath, content, root, reason="AI tool_call file write"))
                        hunks_by_file[fpath] = []
            except Exception:
                pass

        # ── 3. Extract explicit CREATE/FILE/WRITE headers before code fences ─
        create_pattern = _re.compile(
            r"(?:CREATE|FILE|WRITE|MODIFY|EDIT|PATH)\s*:\s*`?([^`\n]+?)`?\s*\n+```([^\n]*)\n(.*?)```",
            _re.DOTALL | _re.IGNORECASE,
        )
        for match in create_pattern.finditer(response_text):
            fpath = cls._clean_candidate_path(match.group(1))
            code_body = match.group(3)
            if not fpath or fpath in hunks_by_file:
                continue
            operations.append(cls._build_create_or_modify_op(fpath, code_body, root, reason="AI explicit file header"))
            hunks_by_file[fpath] = []

        # ── 4 & 5 & 6. Inspect all fenced code blocks for comment/prose/prompt filenames ─
        fence_pattern = _re.compile(r"```([^\n`]*)\n(.*?)```", _re.DOTALL)
        fence_matches = list(fence_pattern.finditer(response_text))
        for idx, match in enumerate(fence_matches):
            lang = (match.group(1) or "").strip()
            code_body = match.group(2)
            if not code_body or not code_body.strip():
                continue
            if "<<<<<<< SEARCH" in code_body:
                continue

            fpath, cleaned_code = cls._extract_first_line_filename_comment(code_body)

            if not fpath:
                prev_end = fence_matches[idx - 1].end() if idx > 0 else 0
                prose_before = response_text[prev_end:match.start()]
                fpath = cls._infer_filename_from_prose(
                    prose_before,
                    user_prompt=(user_prompt if len(fence_matches) == 1 else ""),
                )

            if not fpath and len(fence_matches) == 1 and not operations:
                fpath = cls._infer_filename_from_code_and_prompt(
                    code_body,
                    lang=lang,
                    user_prompt=user_prompt,
                    workspace_root=workspace_root,
                    active_file=active_file,
                )

            if fpath and fpath not in hunks_by_file:
                operations.append(cls._build_create_or_modify_op(fpath, cleaned_code, root, reason="AI code block extraction"))
                hunks_by_file[fpath] = []

        # ── 7. Extract explicit DELETE / REMOVE_FILE and RENAME / MOVE directives ─
        delete_pattern = _re.compile(
            r"^(?:DELETE|REMOVE_FILE|DELETE_FILE)\s*:\s*`?([^`\n]+?)`?\s*$",
            _re.MULTILINE | _re.IGNORECASE,
        )
        for m in delete_pattern.finditer(response_text):
            fpath = cls._clean_candidate_path(m.group(1))
            if fpath and fpath not in hunks_by_file:
                operations.append(ChangeOperation.delete_file(fpath, reason="AI file deletion"))
                hunks_by_file[fpath] = []

        rename_pattern = _re.compile(
            r"^(?:RENAME|MOVE|RENAME_FILE)\s*:\s*`?([^`\n\->]+?)`?\s*(?:->|=>|\s+to\s+)\s*`?([^`\n]+?)`?\s*$",
            _re.MULTILINE | _re.IGNORECASE,
        )
        for m in rename_pattern.finditer(response_text):
            src = cls._clean_candidate_path(m.group(1))
            dst = cls._clean_candidate_path(m.group(2))
            if src and dst and src != dst and src not in hunks_by_file:
                operations.append(ChangeOperation.rename_file(src, dst, reason="AI file rename"))
                hunks_by_file[src] = []

        return operations

class ShadowWorkspaceSandbox:
    _SKIP_DIRS = {
        ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
        "dist", "build", ".tox", ".mypy_cache", ".pytest_cache",
    }

    def __init__(self, workspace_root: str, event_bus=None, use_git_worktree: bool = True) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.event_bus = event_bus
        self.use_git_worktree = use_git_worktree
        self._shadow_dir: _Optional[Path] = None
        self._is_worktree = False
        self._baseline_snapshots: _Dict[str, bytes] = {}

    @property
    def shadow_root(self) -> Path:
        if self._shadow_dir is None:
            return self.enter()
        return self._shadow_dir

    def enter(self) -> Path:
        if self._shadow_dir is not None and self._shadow_dir.exists():
            return self._shadow_dir
        self._shadow_dir = Path(_sh_tempfile.mkdtemp(prefix="owncode_shadow_")).resolve()
        self._baseline_snapshots.clear()

        for dirpath, dirs, files in os.walk(str(self.workspace_root), topdown=True, followlinks=False):
            dirs[:] = [d for d in dirs if d not in self._SKIP_DIRS and not d.startswith(".git")]
            rel_dir = Path(dirpath).relative_to(self.workspace_root)
            target_dir = self._shadow_dir / rel_dir
            target_dir.mkdir(parents=True, exist_ok=True)
            for fname in files:
                src_file = Path(dirpath) / fname
                rel_file = str(rel_dir / fname) if str(rel_dir) != "." else fname
                dst_file = target_dir / fname
                try:
                    raw = src_file.read_bytes()
                    self._baseline_snapshots[rel_file.replace("\\", "/")] = raw
                    dst_file.write_bytes(raw)
                except OSError:
                    pass
        return self._shadow_dir

    def compute_change_set(self) -> ChangeSet:
        if self._shadow_dir is None or not self._shadow_dir.exists():
            return ChangeSet.from_operations([])
        shadow_files: _Dict[str, bytes] = {}
        for dirpath, dirs, files in os.walk(str(self._shadow_dir), topdown=True, followlinks=False):
            dirs[:] = [d for d in dirs if d not in self._SKIP_DIRS and not d.startswith(".git")]
            rel_dir = Path(dirpath).relative_to(self._shadow_dir)
            for fname in files:
                if fname.endswith(".bak"):
                    continue
                sf = Path(dirpath) / fname
                rel_file = (str(rel_dir / fname) if str(rel_dir) != "." else fname).replace("\\", "/")
                try:
                    shadow_files[rel_file] = sf.read_bytes()
                except OSError:
                    pass

        ops: _List[ChangeOperation] = []
        for rel_path, new_bytes in sorted(shadow_files.items()):
            if rel_path not in self._baseline_snapshots:
                try:
                    ops.append(ChangeOperation.create_file(rel_path, new_bytes.decode("utf-8"), reason="Created in shadow sandbox"))
                except UnicodeDecodeError:
                    pass
            elif new_bytes != self._baseline_snapshots[rel_path]:
                try:
                    old_text = self._baseline_snapshots[rel_path].decode("utf-8")
                    new_text = new_bytes.decode("utf-8")
                    hunk = Hunk(
                        old_start=1,
                        old_lines=max(1, len(old_text.splitlines())),
                        new_start=1,
                        new_lines=max(1, len(new_text.splitlines())),
                        old_text=old_text,
                        new_text=new_text,
                    )
                    ops.append(ChangeOperation.modify_file(rel_path, [hunk], reason="Modified in shadow sandbox"))
                except UnicodeDecodeError:
                    pass

        for rel_path in sorted(self._baseline_snapshots.keys()):
            if rel_path not in shadow_files:
                ops.append(ChangeOperation.delete_file(rel_path, reason="Deleted in shadow sandbox"))

        return ChangeSet.from_operations(ops)

    def promote_to_workspace(
        self,
        selected_files: _Optional[_List[str]] = None,
        user_prompt: str = "Promote shadow sandbox changes",
    ) -> ApplyResult:
        cs = self.compute_change_set()
        if selected_files is not None:
            allowed = {f.replace("\\", "/") for f in selected_files}
            filtered_ops = [op for op in cs.operations if op.source_path.replace("\\", "/") in allowed]
            cs = ChangeSet.from_operations(filtered_ops)
        bus = self.event_bus
        if bus is None:
            from core.event_bus import EventBus
            bus = EventBus()
        applier = ChangeApplier(bus, str(self.workspace_root))
        req = ChangeRequest.create(
            user_prompt=user_prompt,
            files=cs.files,
            changes=[],
            reason="Shadow sandbox promotion",
            metadata={"confirmed_destructive": True},
        )
        return applier.apply(cs, req)

    def cleanup(self) -> None:
        if self._shadow_dir is not None and self._shadow_dir.exists():
            _sh_shutil.rmtree(self._shadow_dir, ignore_errors=True)
        self._shadow_dir = None

    def __enter__(self) -> "ShadowWorkspaceSandbox":
        self.enter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()


class FIMCompletionEngine:
    _STOP_TOKENS = (
        "<|endoftext|>", "<|fim_pad|>", "<|file_sep|>", "<|im_end|>",
        "<EOT>", "<|eot_id|>", "</s>",
    )

    @classmethod
    def build_fim_prompt(
        cls,
        prefix: str,
        suffix: str,
        model_id: str = "",
        max_prefix_lines: int = 60,
        max_suffix_lines: int = 25,
    ) -> str:
        p_trimmed = "".join((prefix or "").splitlines(keepends=True)[-max_prefix_lines:])
        s_trimmed = "".join((suffix or "").splitlines(keepends=True)[:max_suffix_lines])
        if "codellama" in (model_id or "").lower():
            return f"<PRE> {p_trimmed} <SUF>{s_trimmed} <MID>"
        return f"<|fim_prefix|>{p_trimmed}<|fim_suffix|>{s_trimmed}<|fim_middle|>"

    @classmethod
    def clean_fim_completion(cls, raw_text: str, prefix: str = "", suffix: str = "") -> str:
        text = raw_text or ""
        for tok in cls._STOP_TOKENS:
            if tok in text:
                text = text.split(tok, 1)[0]
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        if suffix:
            first_suffix_line = next((ln.strip() for ln in suffix.splitlines() if ln.strip()), "")
            if first_suffix_line and text.rstrip().endswith(first_suffix_line):
                idx = text.rfind(first_suffix_line)
                if idx > 0:
                    text = text[:idx].rstrip()
        return text


class NextEditPredictor:
    @classmethod
    def predict_next_edits(
        cls,
        old_code: str,
        new_code: str,
        current_file: str = "current.py",
        workspace_root: _Optional[str] = None,
    ) -> _List[_Dict[str, _Any]]:
        predictions: _List[_Dict[str, _Any]] = []
        old_defs = cls._extract_python_defs(old_code)
        new_defs = cls._extract_python_defs(new_code)
        if not old_defs or not new_defs:
            return predictions

        removed_names = [name for name in old_defs if name not in new_defs]
        added_names = [name for name in new_defs if name not in old_defs]
        rename_map: _Dict[str, str] = {}
        if len(removed_names) == 1 and len(added_names) == 1:
            rename_map[removed_names[0]] = added_names[0]

        param_changes: _Dict[str, _Tuple[_List[str], _List[str]]] = {}
        for name, new_args in new_defs.items():
            if name in old_defs and old_defs[name] != new_args:
                param_changes[name] = (old_defs[name], new_args)

        files_to_scan: _List[_Tuple[str, str]] = [(current_file, new_code)]
        for fpath, text in files_to_scan:
            for lineno, line in enumerate(text.splitlines(), start=1):
                stripped = line.strip()
                if stripped.startswith(("def ", "async def ", "class ", "#")):
                    continue
                for old_name, new_name in rename_map.items():
                    if _re.search(rf"\b{_re.escape(old_name)}\s*\(", line):
                        suggested = _re.sub(rf"\b{_re.escape(old_name)}(?=\s*\()", new_name, line)
                        predictions.append({
                            "file": fpath,
                            "line": lineno,
                            "symbol": old_name,
                            "old_line_text": line,
                            "suggested_line_text": suggested,
                            "reason": f"Function '{old_name}' was renamed to '{new_name}'",
                        })
                for fn_name, (old_args, new_args) in param_changes.items():
                    m = _re.search(rf"\b{_re.escape(fn_name)}\s*\(([^)]*)\)", line)
                    if m:
                        call_args = [a.strip() for a in m.group(1).split(",") if a.strip()]
                        non_self_old = [a for a in old_args if a != "self"]
                        non_self_new = [a for a in new_args if a != "self"]
                        if len(non_self_new) > len(non_self_old) and len(call_args) == len(non_self_old):
                            added_params = non_self_new[len(non_self_old):]
                            placeholder_args = ", ".join(f"{p}=..." for p in added_params)
                            new_inside = f"{m.group(1)}, {placeholder_args}" if m.group(1).strip() else placeholder_args
                            suggested = line[:m.start(1)] + new_inside + line[m.end(1):]
                            predictions.append({
                                "file": fpath,
                                "line": lineno,
                                "symbol": fn_name,
                                "old_line_text": line,
                                "suggested_line_text": suggested,
                                "reason": f"Signature of '{fn_name}' added parameter(s): {', '.join(added_params)}",
                            })
        return predictions

    @staticmethod
    def _extract_python_defs(code: str) -> _Dict[str, _List[str]]:
        out: _Dict[str, _List[str]] = {}
        try:
            tree = _ast.parse(code or "")
            for node in _ast.walk(tree):
                if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                    out[node.name] = [a.arg for a in node.args.args]
        except Exception:
            pass
        return out
