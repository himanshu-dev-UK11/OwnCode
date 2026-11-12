"""
Consolidated Module: agent.planning_engine

Combines: ai.engine.task, ai.engine.engineering_task, ai.engine.task_analyzer, ai.planning.plan_step, ai.planning.plan, ai.planning.dependency_graph, ai.planning.complexity_analyzer, ai.planning.risk_analyzer, ai.planning.plan_validator, ai.planning.task_decomposer, ai.planning.roadmap_builder, ai.execution.task_state, ai.execution.execution_task
"""
from __future__ import annotations
import sys as _sys
import core
for _alias in ['ai.engine.task', 'ai.engine.engineering_task', 'ai.engine.task_analyzer', 'ai.planning.plan_step', 'ai.planning.plan', 'ai.planning.dependency_graph', 'ai.planning.complexity_analyzer', 'ai.planning.risk_analyzer', 'ai.planning.plan_validator', 'ai.planning.task_decomposer', 'ai.planning.roadmap_builder', 'ai.execution.task_state', 'ai.execution.execution_task']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ai.engine.task (ai/engine/task.py)
# ============================================================================
"""
Task dataclass — the universal unit of work.

Every user request is converted into a Task object.
This object is the standard format passed between all engine
components: TaskAnalyzer → Planner → ExecutionManager → Memory.

By centralizing the task definition here, every component works
on the same well-typed, serializable structure rather than raw
dictionaries or loose strings.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class TaskStatus(str, Enum):
    """Lifecycle states a Task can occupy."""
    PENDING    = "pending"     # Just created, not yet analyzed
    ANALYZING  = "analyzing"   # TaskAnalyzer is working
    PLANNING   = "planning"    # PlannerAgent is working
    EXECUTING  = "executing"   # ExecutionManager is running steps
    COMPLETED  = "completed"   # Finished successfully
    FAILED     = "failed"      # Stopped due to an unrecoverable error
    CANCELLED  = "cancelled"   # Stopped by the user


class TaskPriority(str, Enum):
    """Execution priority levels."""
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"
    URGENT = "urgent"


class TaskComplexity(str, Enum):
    """Estimated complexity levels assigned by TaskAnalyzer."""
    SIMPLE   = "simple"    # Single-file edits, trivial commands
    MODERATE = "moderate"  # Multi-file changes, single-agent tasks
    COMPLEX  = "complex"   # Multi-agent, multi-step workflows
    EXPERT   = "expert"    # Requires planning, internet, and iteration


@dataclass
class Task:
    """
    The universal unit of work in OwnCode.

    A Task is created from a raw user prompt by the TaskAnalyzer
    and is enriched as it passes through the pipeline. All engine
    components communicate by reading and writing to this object.

    Attributes:
        id:                   Unique identifier (UUID4 string).
        title:                Short human-readable label for the task.
        original_prompt:      The exact text the user typed.
        objective:            Cleaned, clarified goal extracted from the prompt.
        status:               Current lifecycle state of the task.
        priority:             Execution priority assigned during analysis.
        estimated_complexity: Complexity level assigned during analysis.
        required_tools:       Names of tools the task will need (e.g. "file", "terminal").
        required_models:      Model identifiers needed (e.g. "gemini", "qwen").
        created_time:         UTC timestamp when the Task was instantiated.
        completed_time:       UTC timestamp when the Task reached a terminal state.
        plan:                 Ordered list of step strings set by PlannerAgent.
        metadata:             Arbitrary key-value pairs for future extensibility.
    """

    # --- Core Identity ---
    original_prompt: str
    title: str = ""
    objective: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # --- State ---
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    estimated_complexity: TaskComplexity = TaskComplexity.SIMPLE

    # --- Requirements (populated by TaskAnalyzer) ---
    required_tools: List[str]  = field(default_factory=list)
    required_models: List[str] = field(default_factory=list)

    # Routing hint for ai/models/router.TaskType (value string, e.g. "coding").
    # Set by TaskAnalyzer.classify_task_type().
    routing_task_type: str = "simple_chat"

    # --- Detected Context (populated by TaskAnalyzer) ---
    detected_language:  Optional[str] = None
    detected_framework: Optional[str] = None
    detected_project_type: Optional[str] = None
    needs_planning:    bool = False
    needs_internet:    bool = False
    needs_terminal:    bool = False
    needs_file_write:  bool = False

    @property
    def requires_code_changes(self) -> bool:
        """True when the task implies writing or modifying source files."""
        return self.needs_file_write or self.estimated_complexity in (
            TaskComplexity.MODERATE, TaskComplexity.COMPLEX, TaskComplexity.EXPERT
        )

    # --- Timing ---
    created_time: datetime   = field(default_factory=datetime.utcnow)
    completed_time: Optional[datetime] = None

    # --- Execution Artefacts ---
    plan: List[str]            = field(default_factory=list)
    metadata: dict             = field(default_factory=dict)

    def mark_completed(self) -> None:
        """Mark the task as successfully completed and record the timestamp."""
        self.status = TaskStatus.COMPLETED
        self.completed_time = datetime.utcnow()

    def mark_failed(self) -> None:
        """Mark the task as failed and record the timestamp."""
        self.status = TaskStatus.FAILED
        self.completed_time = datetime.utcnow()

    def is_terminal(self) -> bool:
        """Return True if the Task has reached a final, non-resumable state."""
        return self.status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}

    def __repr__(self) -> str:
        return (
            f"Task(id={self.id[:8]}..., title={self.title!r}, "
            f"status={self.status.value}, priority={self.priority.value})"
        )


# ============================================================================
# SECTION: ai.engine.engineering_task (ai/engine/engineering_task.py)
# ============================================================================
"""
EngineeringTask — Autonomous Engineering Task definition.

Extends the base Task/ExecutionTask concept to provide granular
details required for an autonomous engineering workflow. 
Each engineering task represents a specific sub-step in a larger plan.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ai.engine.task import TaskPriority, TaskStatus


class EngineeringTaskStatus(str, Enum):
    PENDING    = "pending"
    RUNNING    = "running"
    COMPLETED  = "completed"
    FAILED     = "failed"
    CANCELLED  = "cancelled"
    RETRYING   = "retrying"


@dataclass
class EngineeringTask:
    """
    An autonomous engineering task representing a single step in a plan.

    Attributes:
        id:                 Unique identifier.
        title:              Short title of the task.
        description:        Detailed description of what needs to be done.
        priority:           Priority of this specific task.
        status:             Current execution status.
        dependencies:       List of task IDs this task depends on.
        affected_files:     List of files this task is expected to modify.
        estimated_duration: Estimated duration in seconds.
        actual_duration:    Actual duration in seconds.
        assigned_model:     The AI model assigned to execute this task.
        verification_state: Status of the verification (e.g. 'unverified', 'passed', 'failed').
        retry_count:        Number of times this task has been retried.
        logs:               List of specific engineering logs (reasoning summary, files changed, tool calls, etc).
    """

    id:                 str = field(default_factory=lambda: str(uuid.uuid4()))
    title:              str = ""
    description:        str = ""
    priority:           TaskPriority = TaskPriority.MEDIUM
    status:             EngineeringTaskStatus = EngineeringTaskStatus.PENDING
    dependencies:       List[str] = field(default_factory=list)
    affected_files:     List[str] = field(default_factory=list)
    estimated_duration: Optional[int] = None
    actual_duration:    Optional[int] = None
    assigned_model:     Optional[str] = None
    verification_state: str = "unverified"
    retry_count:        int = 0
    logs:               List[Dict[str, Any]] = field(default_factory=list)

    def add_log(self, reasoning: str = "", files_changed: List[str] = None, 
                tool_calls: List[str] = None, verification_result: str = "", 
                execution_time_ms: float = 0.0):
        """Append an engineering-specific log entry."""
        self.logs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "reasoning_summary": reasoning,
            "files_changed": files_changed or [],
            "tool_calls": tool_calls or [],
            "verification_result": verification_result,
            "execution_time_ms": execution_time_ms
        })



# ============================================================================
# SECTION: ai.engine.task_analyzer (ai/engine/task_analyzer.py)
# ============================================================================
"""
TaskAnalyzer — rule-based prompt intelligence.

Converts a raw user prompt into a fully populated Task object using
deterministic, keyword-based rules. No AI models are called here.

This is the first stage of the pipeline. By separating prompt
analysis from actual AI reasoning, we can cheaply pre-classify
tasks, assign priorities, and detect required tooling — making
the system faster and more predictable for simple tasks.
"""

import re
from typing import Dict, List, Set

from core.logger import setup_logger
from ai.engine.task import Task, TaskComplexity, TaskPriority, TaskStatus

logger = setup_logger(__name__)


# ---------------------------------------------------------------------------
# Detection rule tables — extend these as the project grows.
# ---------------------------------------------------------------------------

_LANGUAGE_KEYWORDS: Dict[str, List[str]] = {
    "python":     ["python", ".py", "pip", "django", "flask", "fastapi"],
    "javascript": ["javascript", "js", "node", "npm", "react", "vue", "typescript", "ts"],
    "rust":       ["rust", "cargo", "crate"],
    "go":         ["golang", " go ", "goroutine"],
    "java":       ["java", "maven", "gradle", "spring"],
    "cpp":        ["c++", "cpp", "cmake"],
}

_FRAMEWORK_KEYWORDS: Dict[str, List[str]] = {
    "django":   ["django", "wsgi"],
    "flask":    ["flask", "blueprint"],
    "fastapi":  ["fastapi", "uvicorn", "pydantic"],
    "react":    ["react", "jsx", "tsx", "next.js", "nextjs"],
    "vue":      ["vue", "nuxt"],
    "express":  ["express", "middleware"],
    "pytorch":  ["pytorch", "torch", "tensor"],
    "sklearn":  ["sklearn", "scikit", "scikit-learn"],
}

_PROJECT_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "web_app":    ["website", "web app", "frontend", "backend", "api", "rest"],
    "cli_tool":   ["cli", "command line", "terminal tool", "script"],
    "desktop_app":["desktop", "gui", "tkinter", "pyqt", "wxpython"],
    "ml_model":   ["machine learning", "train", "model", "dataset", "neural"],
    "data_pipeline": ["pipeline", "etl", "dataframe", "pandas", "spark"],
}

_TOOL_INDICATORS: Dict[str, List[str]] = {
    "terminal": ["run", "execute", "install", "compile", "build", "test", "command"],
    "file":     ["create file", "write file", "read file", "modify", "edit file", "delete file"],
    "git":      ["git", "commit", "branch", "push", "pull", "merge"],
    "browser":  ["search", "web", "internet", "google", "look up", "documentation"],
}

_COMPLEXITY_HIGH_INDICATORS: List[str] = [
    "architecture", "refactor", "entire", "whole project", "system",
    "multi", "complex", "integrate", "pipeline", "deploy", "migrate",
]

_PRIORITY_URGENT_INDICATORS: List[str] = [
    "urgent", "asap", "immediately", "critical", "broken", "crash", "error", "bug", "fix",
]

_PRIORITY_HIGH_INDICATORS: List[str] = [
    "important", "high priority", "must", "required", "blocker",
]

# Maps a prompt to the routing task-type consumed by ai/models/router.TaskType.
# Kept as plain strings so this module stays import-light (no circular import
# with the model layer). First match wins, evaluated top-down.
_TASK_TYPE_INDICATORS: List[tuple] = [
    ("architecture", ["architecture", "architect", "design the", "system design",
                      "restructure", "migrate", "refactor the whole"]),
    ("documentation", ["document", "documentation", "docstring", "readme",
                       "explain", "comment", "write docs"]),
    ("heavy_reasoning", ["why", "root cause", "debug", "diagnose", "investigate",
                         "trace", "analyze", "figure out", "reason"]),
    ("large_context", ["entire", "whole project", "all files", "across the",
                       "every file", "codebase-wide", "project-wide"]),
    ("coding", ["implement", "write", "create", "add", "fix", "refactor",
                "rename", "code", "function", "class", "test"]),
]


class TaskAnalyzer:
    """
    Rule-based prompt analyzer.

    Analyzes an incoming user prompt and produces a fully populated
    Task object with detected context and requirements.

    No AI models are invoked here. All decisions are deterministic
    and based on keyword matching.

    Usage:
        analyzer = TaskAnalyzer()
        task = analyzer.analyze("Build a Flask REST API with auth")
    """

    def __init__(self) -> None:
        logger.info("TaskAnalyzer initialized.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, prompt: str) -> Task:
        """
        Analyze a raw user prompt and return a Task object.

        Args:
            prompt: The exact text the user submitted.

        Returns:
            A Task instance populated with all detected context.
        """
        logger.info(f"Analyzing prompt: {prompt[:80]!r}...")

        task = Task(original_prompt=prompt)
        task.status = TaskStatus.ANALYZING

        normalized = prompt.lower()

        # Run all detectors in order
        task.detected_language    = self._detect_language(normalized)
        task.detected_framework   = self._detect_framework(normalized)
        task.detected_project_type = self._detect_project_type(normalized)
        task.required_tools       = self._detect_required_tools(normalized)
        task.needs_planning       = self._detect_needs_planning(normalized)
        task.needs_internet       = "browser" in task.required_tools
        task.needs_terminal       = "terminal" in task.required_tools
        task.needs_file_write     = "file" in task.required_tools
        task.estimated_complexity = self._estimate_complexity(normalized, task.required_tools)
        task.priority             = self._assign_priority(normalized)
        task.required_models      = self._select_required_models(task)
        task.routing_task_type    = self.classify_task_type(normalized, task)
        task.title                = self._generate_title(prompt)
        task.objective            = prompt.strip()

        logger.info(
            f"Task analyzed — language={task.detected_language}, "
            f"complexity={task.estimated_complexity.value}, "
            f"priority={task.priority.value}, "
            f"route={task.routing_task_type}, "
            f"tools={task.required_tools}"
        )
        return task

    def classify_task_type(self, text: str, task: Task) -> str:
        """Classify the prompt into a routing task type for the ModelRouter.

        Returns one of the ai.models.router.TaskType *values*:
        "architecture" | "documentation" | "heavy_reasoning" |
        "large_context" | "coding" | "simple_chat".

        This is what lets the router send planning/architecture work to a
        strong model and cheap edits to a fast local one, instead of the old
        behaviour of only ever choosing between CODING and SIMPLE_CHAT.
        """
        for task_type, keywords in _TASK_TYPE_INDICATORS:
            if any(kw in text for kw in keywords):
                # An EXPERT-complexity "coding" prompt is really architecture work.
                if task_type == "coding" and task.estimated_complexity == TaskComplexity.EXPERT:
                    return "architecture"
                return task_type

        # No keyword hit — fall back to structural signals.
        if task.needs_planning:
            return "architecture"
        if task.requires_code_changes:
            return "coding"
        return "simple_chat"

    # ------------------------------------------------------------------
    # Private detectors
    # ------------------------------------------------------------------

    def _detect_language(self, text: str) -> str | None:
        """Return the first matched programming language, or None."""
        for lang, keywords in _LANGUAGE_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return lang
        return None

    def _detect_framework(self, text: str) -> str | None:
        """Return the first matched framework, or None."""
        for framework, keywords in _FRAMEWORK_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return framework
        return None

    def _detect_project_type(self, text: str) -> str | None:
        """Return the first matched project type, or None."""
        for ptype, keywords in _PROJECT_TYPE_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return ptype
        return None

    def _detect_required_tools(self, text: str) -> List[str]:
        """Return a list of tool names that the prompt implies are needed."""
        needed: Set[str] = set()
        for tool, keywords in _TOOL_INDICATORS.items():
            if any(kw in text for kw in keywords):
                needed.add(tool)
        return sorted(needed)

    def _detect_needs_planning(self, text: str) -> bool:
        """
        Return True if the prompt implies multi-step planning is needed.

        Heuristics: multi-step words, large scope, or high complexity indicators.
        """
        planning_keywords = ["plan", "design", "architect", "step by step", "milestone"] + _COMPLEXITY_HIGH_INDICATORS
        return any(kw in text for kw in planning_keywords)

    def _estimate_complexity(self, text: str, required_tools: List[str]) -> TaskComplexity:
        """
        Estimate task complexity from keywords and tool count.

        Rules (evaluated top-down, first match wins):
        - EXPERT   → high-complexity keywords found
        - COMPLEX  → needs planning OR 3+ tools
        - MODERATE → 2 tools, or framework detected
        - SIMPLE   → default
        """
        if any(kw in text for kw in _COMPLEXITY_HIGH_INDICATORS):
            return TaskComplexity.EXPERT
        if self._detect_needs_planning(text) or len(required_tools) >= 3:
            return TaskComplexity.COMPLEX
        if len(required_tools) >= 2:
            return TaskComplexity.MODERATE
        return TaskComplexity.SIMPLE

    def _assign_priority(self, text: str) -> TaskPriority:
        """
        Assign priority based on urgency / importance keywords.

        Rules (evaluated top-down):
        - URGENT → crash / error / urgent words
        - HIGH   → importance words
        - MEDIUM → default
        """
        if any(kw in text for kw in _PRIORITY_URGENT_INDICATORS):
            return TaskPriority.URGENT
        if any(kw in text for kw in _PRIORITY_HIGH_INDICATORS):
            return TaskPriority.HIGH
        return TaskPriority.MEDIUM

    def _select_required_models(self, task: Task) -> List[str]:
        """Capability hints for this task, consumed by the ModelRouter as a bias.

        These are capability *tags* (matched against a model profile's
        `strengths`), not hardcoded vendor names — the actual model choice is
        made by ai/models/router.py::select_best_model() against whatever
        providers are genuinely connected.
        """
        hints: List[str] = []
        if task.estimated_complexity in {TaskComplexity.EXPERT, TaskComplexity.COMPLEX}:
            hints.append("reasoning")
        if task.requires_code_changes:
            hints.append("coding")
        if not hints:
            hints.append("fast")
        return hints

    def _generate_title(self, prompt: str) -> str:
        """
        Create a short title from the first sentence of the prompt.
        Truncates at 60 characters.
        """
        first_sentence = re.split(r'[.\n]', prompt.strip())[0]
        title = first_sentence.strip()
        return title if len(title) <= 60 else title[:57] + "..."


# ============================================================================
# SECTION: ai.planning.plan_step (ai/planning/plan_step.py)
# ============================================================================
"""
PlanStep dataclass.

Represents a single atomic step within a larger Plan.
"""

from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class PlanStep:
    """
    A single step in the execution plan.
    """
    step_id: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    estimated_time_minutes: float = 0.0
    required_tool: Optional[str] = None
    required_model: Optional[str] = None
    expected_output: str = ""
    status: str = "pending"


# ============================================================================
# SECTION: ai.planning.plan (ai/planning/plan.py)
# ============================================================================
"""
Plan dataclass.

Represents the complete, validated execution plan for a Task.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from ai.planning.plan_step import PlanStep

@dataclass
class Plan:
    """
    Complete execution plan containing all steps, risks, and metadata.
    """
    plan_id: str
    goal: str
    status: str = "pending"
    estimated_time_minutes: float = 0.0
    estimated_tokens: int = 0
    complexity: str = "easy"
    risks: List[Dict[str, str]] = field(default_factory=list)
    required_models: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    steps: List[PlanStep] = field(default_factory=list)
    phases: Dict[str, List[str]] = field(default_factory=dict)


# ============================================================================
# SECTION: ai.planning.dependency_graph (ai/planning/dependency_graph.py)
# ============================================================================
"""
DependencyGraph module.

Builds a dependency graph to ensure correct step execution order
and to identify related files.
"""

from typing import List, Dict, Set
from ai.planning.plan_step import PlanStep

class DependencyGraph:
    """
    Manages relationships between execution steps and project files.
    """
    def __init__(self):
        self.step_dependencies: Dict[str, List[str]] = {}
        self.file_dependencies: Dict[str, List[str]] = {}
        
    def build_step_graph(self, steps: List[PlanStep]) -> None:
        """
        Build a directed graph of step dependencies.
        """
        for step in steps:
            self.step_dependencies[step.step_id] = step.dependencies
            
    def analyze_file_dependencies(self, files: List[str]) -> None:
        """
        Placeholder for file-level dependency analysis.
        e.g. login.dart -> auth_service.dart -> user_model.dart
        """
        pass
        
    def has_cycles(self) -> bool:
        """
        Check if the step dependency graph contains cyclic dependencies.
        """
        visited: Set[str] = set()
        path: Set[str] = set()
        
        def visit(node: str) -> bool:
            if node in path:
                return True
            if node in visited:
                return False
                
            visited.add(node)
            path.add(node)
            
            for neighbor in self.step_dependencies.get(node, []):
                if visit(neighbor):
                    return True
                    
            path.remove(node)
            return False
            
        for node in self.step_dependencies:
            if visit(node):
                return True
                
        return False


# ============================================================================
# SECTION: ai.planning.complexity_analyzer (ai/planning/complexity_analyzer.py)
# ============================================================================
"""
ComplexityAnalyzer module.

Estimates the project's overall difficulty level.
"""

from ai.memory.project_context import ProjectContext
from ai.engine.task import Task

class ComplexityAnalyzer:
    """
    Assigns an estimated complexity rating to a task.
    """
    def estimate_complexity(self, task: Task, context: ProjectContext) -> str:
        """
        Return Easy, Medium, Hard, or Very Hard based on context size and task type.
        """
        if not context:
            return "Easy"
            
        if context.total_files < 10:
            return "Easy"
        elif context.total_files < 50:
            return "Medium"
        elif context.total_files < 200:
            return "Hard"
        else:
            return "Very Hard"


# ============================================================================
# SECTION: ai.planning.risk_analyzer (ai/planning/risk_analyzer.py)
# ============================================================================
"""
RiskAnalyzer module.

Predicts possible implementation risks.
"""

from typing import List, Dict
from ai.memory.project_context import ProjectContext
from ai.engine.task import Task

class RiskAnalyzer:
    """
    Identifies potential risks like circular imports, breaking changes, etc.
    """
    def analyze_risks(self, task: Task, context: ProjectContext) -> List[Dict[str, str]]:
        """
        Return a list of identified risks with their severity levels.
        Assigns Low, Medium, or High.
        """
        risks = []
        
        objective = task.objective.lower() if task and task.objective else ""
        
        if "refactor" in objective:
            risks.append({"risk": "Large refactor", "severity": "High"})
        if "delete" in objective:
            risks.append({"risk": "Dangerous delete", "severity": "High"})
            
        if context and context.total_files > 100:
            risks.append({"risk": "Missing dependencies or broken imports", "severity": "Medium"})
            
        if not risks:
            risks.append({"risk": "General implementation issues", "severity": "Low"})
            
        return risks


# ============================================================================
# SECTION: ai.planning.plan_validator (ai/planning/plan_validator.py)
# ============================================================================
"""
PlanValidator module.

Verifies the generated plan to prevent invalid execution sequences.
"""

from ai.planning.plan import Plan
from ai.planning.dependency_graph import DependencyGraph

class PlanValidator:
    """
    Runs safety and structural checks on the proposed Plan.
    """
    def validate(self, plan: Plan) -> bool:
        """
        Check for missing steps, duplicate work, invalid order, missing dependencies.
        """
        if not plan.steps:
            return False
            
        step_ids = [step.step_id for step in plan.steps]
        
        # Check for duplicate step IDs
        if len(step_ids) != len(set(step_ids)):
            return False
            
        # Check for missing dependencies
        graph = DependencyGraph()
        graph.build_step_graph(plan.steps)
        
        for step in plan.steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    return False
                    
        # Check for cyclic dependencies
        if graph.has_cycles():
            return False
            
        return True


# ============================================================================
# SECTION: ai.planning.task_decomposer (ai/planning/task_decomposer.py)
# ============================================================================
"""
TaskDecomposer — intelligent task decomposition.

Converts a Task into a list of actionable EngineeringTasks.
Adapts the number and type of steps to task complexity.
"""

from typing import List, Optional
import uuid
from core.logger import setup_logger
from ai.engine.task import Task, TaskComplexity
from ai.engine.engineering_task import EngineeringTask
from ai.engine.task import TaskPriority as EngineeringTaskPriority  # alias

logger = setup_logger(__name__)


class TaskDecomposer:
    """
    Breaks down a high-level Task into actionable EngineeringTasks.

    Decomposition strategy:
    - SIMPLE    → 1 step: direct execution
    - MODERATE  → 2 steps: analyse + implement
    - COMPLEX   → 3 steps: analyse + implement + verify
    - EXPERT    → 4 steps: analyse + plan + implement + verify
    """

    def decompose(self, task: Task, context=None) -> List[EngineeringTask]:
        """
        Convert task into an ordered list of EngineeringTasks.

        Args:
            task:    The analyzed Task object from TaskAnalyzer.
            context: Optional ContextPackage (may be None early in pipeline).

        Returns:
            Ordered list of EngineeringTasks with dependency chains set.
        """
        complexity = getattr(task, "estimated_complexity", TaskComplexity.SIMPLE)
        prompt     = getattr(task, "original_prompt", "Complete task")
        objective  = getattr(task, "objective", prompt) or prompt
        lang       = getattr(task, "detected_language", None)
        tools      = getattr(task, "required_tools", [])

        logger.info(
            f"TaskDecomposer: decomposing '{objective[:60]}' "
            f"(complexity={complexity.value})"
        )

        steps: List[EngineeringTask] = []

        # ── SIMPLE: one direct execution step ────────────────────────────
        if complexity == TaskComplexity.SIMPLE:
            step = EngineeringTask(
                id=str(uuid.uuid4()),
                title="Execute task",
                description=objective,
                estimated_duration=30,
                priority=EngineeringTaskPriority.MEDIUM,
            )
            steps.append(step)

        # ── MODERATE: analyse + implement ───────────────────────────────
        elif complexity == TaskComplexity.MODERATE:
            s1 = EngineeringTask(
                id=str(uuid.uuid4()),
                title="Analyse context",
                description=(
                    f"Read relevant files{' (' + lang + ')' if lang else ''} "
                    "and understand the current state."
                ),
                estimated_duration=20,
                priority=EngineeringTaskPriority.HIGH,
            )
            s2 = EngineeringTask(
                id=str(uuid.uuid4()),
                title=f"Implement: {objective[:50]}",
                description=objective,
                dependencies=[s1.id],
                estimated_duration=90,
                priority=EngineeringTaskPriority.HIGH,
            )
            steps.extend([s1, s2])

        # ── COMPLEX: analyse + implement + verify ────────────────────────
        elif complexity == TaskComplexity.COMPLEX:
            s1 = EngineeringTask(
                id=str(uuid.uuid4()),
                title="Analyse project and gather context",
                description=(
                    "Locate entry points, config files, and relevant modules. "
                    f"Tools needed: {', '.join(tools) or 'none'}."
                ),
                estimated_duration=25,
                priority=EngineeringTaskPriority.HIGH,
            )
            s2 = EngineeringTask(
                id=str(uuid.uuid4()),
                title=f"Implement: {objective[:50]}",
                description=(
                    f"{objective}\n\nApply changes to the identified files, "
                    "following the project's existing patterns."
                ),
                dependencies=[s1.id],
                estimated_duration=120,
                priority=EngineeringTaskPriority.HIGH,
            )
            s3 = EngineeringTask(
                id=str(uuid.uuid4()),
                title="Verify and validate changes",
                description=(
                    "Run linters and tests on modified files. "
                    "Confirm changes are consistent and correct."
                ),
                dependencies=[s2.id],
                estimated_duration=40,
                priority=EngineeringTaskPriority.MEDIUM,
            )
            steps.extend([s1, s2, s3])

        # ── EXPERT: analyse + plan + implement + verify ──────────────────
        else:
            s1 = EngineeringTask(
                id=str(uuid.uuid4()),
                title="Deep project analysis",
                description=(
                    "Scan project architecture, dependencies, and identify all "
                    "affected components for this change."
                ),
                estimated_duration=30,
                priority=EngineeringTaskPriority.URGENT,
            )
            s2 = EngineeringTask(
                id=str(uuid.uuid4()),
                title="Plan implementation strategy",
                description=(
                    f"Design the approach for: {objective[:80]}. "
                    "Break down into safe, reversible sub-changes."
                ),
                dependencies=[s1.id],
                estimated_duration=30,
                priority=EngineeringTaskPriority.URGENT,
            )
            s3 = EngineeringTask(
                id=str(uuid.uuid4()),
                title=f"Implement: {objective[:50]}",
                description=(
                    f"{objective}\n\nFollow the plan from step 2. "
                    "Make atomic, focused changes per file."
                ),
                dependencies=[s2.id],
                estimated_duration=180,
                priority=EngineeringTaskPriority.HIGH,
            )
            s4 = EngineeringTask(
                id=str(uuid.uuid4()),
                title="Verify, test, and generate diff",
                description=(
                    "Run full verification suite. Generate a diff summary "
                    "of all changes for user review."
                ),
                dependencies=[s3.id],
                estimated_duration=60,
                priority=EngineeringTaskPriority.HIGH,
            )
            steps.extend([s1, s2, s3, s4])

        logger.info(
            f"TaskDecomposer: produced {len(steps)} steps "
            f"for complexity={complexity.value}"
        )
        return steps


# ============================================================================
# SECTION: ai.planning.roadmap_builder (ai/planning/roadmap_builder.py)
# ============================================================================
"""
RoadmapBuilder module.

Groups PlanSteps into sequential execution phases.
"""

from typing import List, Dict
from ai.planning.plan_step import PlanStep

class RoadmapBuilder:
    """
    Generates execution phases from a list of steps.
    """
    def build_roadmap(self, steps: List[PlanStep]) -> Dict[str, List[str]]:
        """
        Groups step IDs into logical phases.
        """
        phases = {
            "Phase 1: Preparation": [],
            "Phase 2: Implementation": [],
            "Phase 3: Testing and Verification": []
        }
        
        for i, step in enumerate(steps):
            if i == 0:
                phases["Phase 1: Preparation"].append(step.step_id)
            elif i == len(steps) - 1:
                phases["Phase 3: Testing and Verification"].append(step.step_id)
            else:
                phases["Phase 2: Implementation"].append(step.step_id)
                
        return phases


# ============================================================================
# SECTION: ai.execution.task_state (ai/execution/task_state.py)
# ============================================================================
"""
TaskState — task lifecycle state machine.

Defines the complete lifecycle states for ExecutionTasks and
provides state transition rules to prevent invalid state changes.

This is a state machine pattern implementation to ensure
tasks can only transition between valid states.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Set


class TaskState(Enum):
    """
    Lifecycle states for ExecutionTask.
    
    States follow a directed acyclic graph:
    
    PENDING → SCHEDULED → RUNNING → [SUCCESS/FAILED/CANCELLED]
                 ↘→ PAUSED → RUNNING (loop)
    
    Terminal states: SUCCESS, FAILED, CANCELLED, EXPIRED
    """
    # ── Non-started states ─────────────────────────────────────────────────
    PENDING     = "pending"      # Just created, not yet scheduled
    SCHEDULED   = "scheduled"    # Queued, waiting for executor availability
    
    # ── Active execution states ──────────────────────────────────────────
    RUNNING     = "running"      # Currently executing
    PAUSED      = "paused"       # Execution temporarily suspended
    
    # ── Terminal states ──────────────────────────────────────────────────
    SUCCESS     = "success"      # Completed successfully
    FAILED      = "failed"       # Execution failed (after all retries)
    CANCELLED   = "cancelled"    # Stopped by user
    EXPIRED     = "expired"      # Timeout reached


@dataclass
class StateTransition:
    """
    Records a single state transition with timing.
    
    Used for audit trail and debugging execution flow.
    
    Attributes:
        from_state: Previous state (None for initial state)
        to_state:   New state
        timestamp:  When transition occurred
        reason:     Human-readable reason for transition
        metadata:   Arbitrary data associated with transition
    """
    from_state: Optional[TaskState]
    to_state:   TaskState
    timestamp:  datetime
    reason:     str = ""
    metadata:   dict = field(default_factory=dict)
    
    def __repr__(self) -> str:
        from_str = f"→ {self.from_state.value}" if self.from_state else "START"
        return f"{from_str} → {self.to_state.value} ({self.timestamp:%H:%M:%S.%f})"


@dataclass
class TaskStateHistory:
    """
    Complete history of state transitions for a task.
    
    Provides methods to query the state machine:
    - Get current state
    - Get all transitions
    - Check if state is terminal
    - Calculate time in each state
    """
    transitions: list[StateTransition] = field(default_factory=list)
    
    @property
    def current_state(self) -> TaskState:
        """Return the current (most recent) state."""
        if not self.transitions:
            return TaskState.PENDING
        return self.transitions[-1].to_state
    
    @property
    def is_terminal(self) -> bool:
        """Return True if the task has reached a terminal state."""
        return self.current_state in {
            TaskState.SUCCESS, TaskState.FAILED, 
            TaskState.CANCELLED, TaskState.EXPIRED
        }
    
    def get_transitions(self) -> list[StateTransition]:
        """Return all state transitions in order."""
        return list(self.transitions)
    
    def get_transitions_by_state(self, state: TaskState) -> list[StateTransition]:
        """Return all transitions TO a specific state."""
        return [t for t in self.transitions if t.to_state == state]
    
    def get_time_in_state(self, state: TaskState) -> Optional[float]:
        """
        Calculate total time spent in a state (in seconds).
        Returns None if task never entered that state.
        """
        state_transitions = self.get_transitions_by_state(state)
        if not state_transitions:
            return None
        
        total = 0.0
        for i, trans in enumerate(state_transitions):
            # Find next transition
            next_trans = None
            for t in self.transitions:
                if t.timestamp > trans.timestamp:
                    next_trans = t
                    break
            
            # Calculate duration
            if next_trans:
                total += (next_trans.timestamp - trans.timestamp).total_seconds()
            else:
                # Still in this state (if not terminal) or ended here
                if not self.is_terminal or trans.to_state == self.current_state:
                    total += (datetime.utcnow() - trans.timestamp).total_seconds()
        
        return total
    
    def add_transition(self, transition: StateTransition) -> None:
        """Add a new state transition to history."""
        self.transitions.append(transition)


# ── Valid state transitions ───────────────────────────────────────────────────

VALID_TRANSITIONS: dict[TaskState, Set[TaskState]] = {
    TaskState.PENDING:   {TaskState.SCHEDULED, TaskState.CANCELLED},
    TaskState.SCHEDULED: {TaskState.RUNNING, TaskState.PAUSED, TaskState.CANCELLED},
    TaskState.RUNNING:   {TaskState.SUCCESS, TaskState.FAILED, TaskState.PAUSED, 
                          TaskState.CANCELLED, TaskState.EXPIRED},
    TaskState.PAUSED:    {TaskState.RUNNING, TaskState.CANCELLED},
    TaskState.SUCCESS:   set(),  # Terminal - no outgoing
    TaskState.FAILED:    set(),  # Terminal - no outgoing
    TaskState.CANCELLED: set(),  # Terminal - no outgoing
    TaskState.EXPIRED:   set(),  # Terminal - no outgoing
}


def can_transition(from_state: TaskState, to_state: TaskState) -> bool:
    """
    Check if a state transition is valid.
    
    Args:
        from_state: Current state
        to_state:   Target state
        
    Returns:
        True if the transition is allowed
    """
    return to_state in VALID_TRANSITIONS.get(from_state, set())


def validate_transition(from_state: TaskState, to_state: TaskState) -> None:
    """
    Validate a state transition, raising ValueError if invalid.
    
    Args:
        from_state: Current state
        to_state:   Target state
        
    Raises:
        ValueError: If the transition is not allowed
    """
    if not can_transition(from_state, to_state):
        raise ValueError(
            f"Invalid transition: {from_state.value} → {to_state.value}. "
            f"Valid transitions from {from_state.value}: "
            f"{[s.value for s in VALID_TRANSITIONS.get(from_state, set())]}"
        )


# ============================================================================
# SECTION: ai.execution.execution_task (ai/execution/execution_task.py)
# ============================================================================
"""
ExecutionTask — extended task dataclass with execution metadata.

Extends the base Task dataclass with execution-specific fields
needed by the Execution Engine. Maintains compatibility with
existing Task while adding monitoring and reporting features.

All execution tasks flow through the ExecutionEngine and
are tracked by the ExecutionMonitor.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ai.engine.task import Task, TaskStatus, TaskPriority, TaskComplexity
from ai.execution.task_state import TaskState, TaskStateHistory, StateTransition
from ai.execution.task_state import TaskState, TaskStateHistory


class ExecutionMode(str, Enum):
    """Execution mode for a task."""
    FOREGROUND   = "foreground"   # Blocks calling thread
    BACKGROUND   = "background"   # Runs in executor pool
    MONITOR_ONLY = "monitor_only" # Only monitor, no execution


class RetryStrategy(str, Enum):
    """Strategy for handling task retries."""
    FIXED      = "fixed"       # Fixed delay between retries
    EXPONENTIAL = "exponential" # Exponential backoff
    JITTERED   = "jittered"    # Exponential + random jitter
    NONE       = "none"        # No retries


@dataclass
class ExecutionConfig:
    """
    Execution configuration for a task.
    
    Attributes:
        mode:           Execution mode (foreground/background/monitor_only)
        max_retries:    Maximum retry attempts
        retry_strategy: Strategy for timing between retries
        timeout_secs:   Maximum execution time before timeout
        priority:       Execution priority (overrides Task.priority)
        depends_on:     IDs of tasks this depends on
        group:          Task group name for parallel execution
        cancel_on_error: Stop entire group on error
    """
    mode:           ExecutionMode  = ExecutionMode.BACKGROUND
    max_retries:    int            = 2
    retry_strategy: RetryStrategy  = RetryStrategy.EXPONENTIAL
    timeout_secs:   Optional[int]  = None
    priority:       Optional[int]  = None  # None = use Task.priority
    depends_on:     List[str]      = field(default_factory=list)
    group:          Optional[str]  = None
    cancel_on_error: bool          = True


@dataclass
class ExecutionResult:
    """
    Result of a single execution attempt.
    
    Attributes:
        step_index:    Index of step in plan
        step_text:     Original step description
        success:       True if step succeeded
        output:        Step output data
        error:         Error message if failed
        duration_ms:   Execution time
        attempt:       Attempt number (1 = first)
        model_used:    Model used for this step
        tools_used:    Tools called during step
        verification:  Verification result if applicable
    """
    step_index:   int
    step_text:    str
    success:      bool
    output:       Any = None
    error:        Optional[str] = None
    duration_ms:  float = 0.0
    attempt:      int = 1
    model_used:   Optional[str] = None
    tools_used:   List[str] = field(default_factory=list)
    verification: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionStats:
    """
    Execution statistics for a task.
    
    Attributes:
        total_duration_ms:   Full execution time
        model_time_ms:       Total time waiting for model responses
        context_time_ms:     Total time building context
        verification_time_ms: Total time for verification
        tool_time_ms:        Total time spent in tools
        retry_count:         Number of retries performed
        steps_executed:      Number of steps actually executed
        files_modified:      List of modified file paths
        files_created:       List of created file paths
        files_deleted:       List of deleted file paths
    """
    total_duration_ms:   float = 0.0
    model_time_ms:       float = 0.0
    context_time_ms:     float = 0.0
    verification_time_ms: float = 0.0
    tool_time_ms:        float = 0.0
    retry_count:         int = 0
    steps_executed:      int = 0
    files_modified:      List[str] = field(default_factory=list)
    files_created:       List[str] = field(default_factory=list)
    files_deleted:       List[str] = field(default_factory=list)


@dataclass
class ExecutionTask:
    """
    Extended task with execution engine metadata.
    
    Wraps a base Task and adds:
    - State machine tracking
    - Execution configuration
    - Execution history
    - Performance metrics
    - Audit trail
    
    This is the unit of work that flows through the
    ExecutionEngine, TaskScheduler, and TaskExecutor.
    
    Attributes:
        task:          Base Task object (for compatibility)
        state_history: State machine history
        config:        Execution configuration
        results:       Step-by-step execution results
        stats:         Aggregated statistics
        created_time:  When task was created
        scheduled_time: When task entered SCHEDULED state
        started_time:  When task entered RUNNING state
        completed_time: When task reached terminal state
        error:         Final error message (if failed)
        cancelled_by:  User who cancelled (if cancelled)
    """
    # ── Wrapped task (for compatibility) ─────────────────────────────────────
    task: Task
    
    # ── State machine ────────────────────────────────────────────────────────
    state_history: TaskStateHistory = field(default_factory=TaskStateHistory)
    
    # ── Configuration ────────────────────────────────────────────────────────
    config: ExecutionConfig = field(default_factory=ExecutionConfig)
    
    # ── Execution history ────────────────────────────────────────────────────
    results: List[ExecutionResult] = field(default_factory=list)
    
    # ── Statistics ───────────────────────────────────────────────────────────
    stats: ExecutionStats = field(default_factory=ExecutionStats)
    
    # ── Timing ───────────────────────────────────────────────────────────────
    created_time:    datetime = field(default_factory=datetime.utcnow)
    scheduled_time:  Optional[datetime] = None
    started_time:    Optional[datetime] = None
    completed_time:  Optional[datetime] = None
    
    # ── Terminal state info ──────────────────────────────────────────────────
    error:         Optional[str] = None
    cancelled_by:  Optional[str] = None
    
    @property
    def id(self) -> str:
        """Return task ID (from wrapped task)."""
        return self.task.id
    
    @property
    def state(self) -> TaskState:
        """Return current state (from state history)."""
        return self.state_history.current_state
    
    @property
    def is_terminal(self) -> bool:
        """Return True if task has reached a terminal state."""
        return self.state_history.is_terminal
    
    @property
    def success(self) -> bool:
        """Return True if task succeeded."""
        return self.state == TaskState.SUCCESS
    
    @property
    def status(self) -> TaskStatus:
        """Return TaskStatus enum for compatibility."""
        mapping = {
            TaskState.PENDING:    TaskStatus.PENDING,
            TaskState.SCHEDULED:  TaskStatus.PENDING,
            TaskState.RUNNING:    TaskStatus.EXECUTING,
            TaskState.PAUSED:     TaskStatus.PENDING,
            TaskState.SUCCESS:    TaskStatus.COMPLETED,
            TaskState.FAILED:     TaskStatus.FAILED,
            TaskState.CANCELLED:  TaskStatus.CANCELLED,
            TaskState.EXPIRED:    TaskStatus.FAILED,
        }
        return mapping.get(self.state, TaskStatus.PENDING)
    
    def to_dict(self) -> dict:
        """Convert to serializable dict."""
        return {
            "id": self.id,
            "title": self.task.title,
            "status": self.status.value,
            "state": self.state.value,
            "created_time": self.created_time.isoformat(),
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "started_time": self.started_time.isoformat() if self.started_time else None,
            "completed_time": self.completed_time.isoformat() if self.completed_time else None,
            "config": {
                "mode": self.config.mode.value,
                "max_retries": self.config.max_retries,
                "retry_strategy": self.config.retry_strategy.value,
                "timeout_secs": self.config.timeout_secs,
                "priority": self.config.priority,
                "group": self.config.group,
                "cancel_on_error": self.config.cancel_on_error,
            },
            "stats": {
                "total_duration_ms": self.stats.total_duration_ms,
                "model_time_ms": self.stats.model_time_ms,
                "retry_count": self.stats.retry_count,
                "steps_executed": self.stats.steps_executed,
            },
            "results_count": len(self.results),
        }
    
    def __repr__(self) -> str:
        return (
            f"ExecutionTask(id={self.id[:8]}..., title={self.task.title!r}, "
            f"state={self.state.value}, status={self.status.value})"
        )


def create_execution_task(prompt: str, config: Optional[ExecutionConfig] = None) -> ExecutionTask:
    """
    Factory function to create a new ExecutionTask.
    
    Args:
        prompt: User prompt text
        config: Optional execution configuration
        
    Returns:
        New ExecutionTask with PENDING state
    """
    base_task = Task(original_prompt=prompt)
    task = ExecutionTask(task=base_task, config=config or ExecutionConfig())
    
    # Initial state transition
    task.state_history.add_transition(
        StateTransition(
            from_state=None,
            to_state=TaskState.PENDING,
            timestamp=datetime.utcnow(),
            reason="Task created",
        )
    )
    
    return task

