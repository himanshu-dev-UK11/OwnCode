"""
Consolidated Module: agent.execution_and_verification

Combines: ai.execution.execution_events, ai.execution.execution_metrics, ai.execution.execution_report, ai.execution.execution_queue, ai.execution.execution_monitor, ai.execution.task_scheduler, ai.execution.task_executor, ai.verification.verification_task, ai.verification.verification_report, ai.verification.error_classifier, ai.verification.success_validator, ai.verification.retry_manager, ai.verification.build_runner, ai.verification.test_runner, ai.verification.linter_runner, ai.verification.formatter_runner, ai.verification.verification_engine, ai.execution.execution_engine, ai.engine.engineering_workflow_coordinator
"""
from __future__ import annotations
import sys as _sys
import core
for _alias in ['ai.execution.execution_events', 'ai.execution.execution_metrics', 'ai.execution.execution_report', 'ai.execution.execution_queue', 'ai.execution.execution_monitor', 'ai.execution.task_scheduler', 'ai.execution.task_executor', 'ai.verification.verification_task', 'ai.verification.verification_report', 'ai.verification.error_classifier', 'ai.verification.success_validator', 'ai.verification.retry_manager', 'ai.verification.build_runner', 'ai.verification.test_runner', 'ai.verification.linter_runner', 'ai.verification.formatter_runner', 'ai.verification.verification_engine', 'ai.execution.execution_engine', 'ai.engine.engineering_workflow_coordinator']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ai.execution.execution_events (ai/execution/execution_events.py)
# ============================================================================
"""
ExecutionEvents — event definitions for UI integration.

Defines all events published by the ExecutionEngine for UI
integration. UI components subscribe to these events to
update in real-time without polling.

Event Categories:
- Task lifecycle: creation, scheduling, execution, completion
- Progress updates: step progress, model selection, tool execution
- Errors and warnings: failures, cancellations, timeouts
- Status updates: overall engine status

Usage:
    # In UI code
    event_bus.subscribe(ExecutionEvents.TASK_CREATED, on_task_created)
    event_bus.subscribe(ExecutionEvents.TASK_COMPLETED, on_task_completed)
    event_bus.subscribe(ExecutionEvents.STATUS_UPDATE, on_status_update)
"""

from typing import Dict, Any


class ExecutionEvents:
    """
    Event names for ExecutionEngine events.
    
    All events follow the pattern: execution_<category>_<action>
    """
    
    # ── Task lifecycle events ──────────────────────────────────────────────────
    
    TASK_CREATED = "execution_task_created"
    """
    Fired when a new task is created.
    
    Payload:
        task_id:    Task ID
        prompt:     User prompt
        priority:   Task priority
    """
    
    TASK_PLAN_SET = "execution_task_plan_set"
    """
    Fired when a task's plan is set.
    
    Payload:
        task_id: Task ID
        steps:   Number of steps in plan
    """
    
    TASK_STARTED = "execution_task_started"
    """
    Fired when a task starts execution.
    
    Payload:
        task_id:   Task ID
        started_at: Timestamp (ISO format)
    """
    
    TASK_COMPLETED = "execution_task_completed"
    """
    Fired when a task completes successfully.
    
    Payload:
        task_id:      Task ID
        completed_at: Timestamp (ISO format)
        results_count: Number of step results
    """
    
    TASK_FAILED = "execution_task_failed"
    """
    Fired when a task fails.
    
    Payload:
        task_id: Task ID
        error:   Error message
    """
    
    TASK_CANCELLED = "execution_task_cancelled"
    """
    Fired when a task is cancelled.
    
    Payload:
        task_id:      Task ID
        cancelled_by: User who cancelled
    """
    
    TASK_PAUSED = "execution_task_paused"
    """
    Fired when a task is paused.
    
    Payload:
        task_id: Task ID
    """
    
    TASK_RESUMED = "execution_task_resumed"
    """
    Fired when a task is resumed.
    
    Payload:
        task_id: Task ID
    """
    
    TASK_STATE_CHANGED = "execution_task_state_changed"
    """
    Fired when a task's state changes.
    
    Payload:
        task_id:   Task ID
        old_state: Previous state
        new_state: New state
    """
    
    # ── Step execution events ──────────────────────────────────────────────────
    
    STEP_STARTED = "execution_step_started"
    """
    Fired when a step starts.
    
    Payload:
        task_id:   Task ID
        step_index: Step index
        step_text:  Step description
    """
    
    STEP_COMPLETED = "execution_step_completed"
    """
    Fired when a step completes.
    
    Payload:
        task_id:  Task ID
        step_index: Step index
        output:   Step output
        duration_ms: Duration in milliseconds
    """
    
    STEP_FAILED = "execution_step_failed"
    """
    Fired when a step fails.
    
    Payload:
        task_id:   Task ID
        step_index: Step index
        error:     Error message
        attempts:   Number of attempts
    """
    
    # ── Model and tool events ──────────────────────────────────────────────────
    
    MODEL_SELECTED = "execution_model_selected"
    """
    Fired when a model is selected for execution.
    
    Payload:
        task_id:  Task ID
        model:    Model name
        reason:   Reason for selection
    """
    
    MODEL_EXECUTING = "execution_model_executing"
    """
    Fired when a model is executing.
    
    Payload:
        task_id:  Task ID
        model:    Model name
        context_size: Token count
    """
    
    MODEL_RESPONSE_RECEIVED = "execution_model_response_received"
    """
    Fired when a model response is received.
    
    Payload:
        task_id:  Task ID
        model:    Model name
        response_length: Response length
        latency_ms:    Latency in milliseconds
    """
    
    TOOL_EXECUTING = "execution_tool_executing"
    """
    Fired when a tool starts executing.
    
    Payload:
        task_id: Task ID
        tool:    Tool name
        action:  Action being performed
    """
    
    TOOL_COMPLETED = "execution_tool_completed"
    """
    Fired when a tool completes.
    
    Payload:
        task_id:  Task ID
        tool:     Tool name
        output:   Tool output
        duration_ms: Duration in milliseconds
    """
    
    # ── Verification events ────────────────────────────────────────────────────
    
    VERIFICATION_STARTED = "execution_verification_started"
    """
    Fired when verification starts.
    
    Payload:
        task_id: Task ID
        verifiers: List of verifiers to run
    """
    
    VERIFICATION_COMPLETE = "execution_verification_complete"
    """
    Fired when verification completes.
    
    Payload:
        task_id:   Task ID
        success:   True if all verifiers passed
        report:    Verification report
    """
    
    # ── Progress and metrics events ────────────────────────────────────────────
    
    PROGRESS_UPDATE = "execution_progress_update"
    """
    Fired periodically with progress updates.
    
    Payload:
        task_id:      Task ID
        progress:     Progress percentage (0-100)
        current_step: Current step index
        total_steps:  Total steps
    """
    
    STATUS_UPDATE = "execution_status_update"
    """
    Fired with engine-wide status updates.
    
    Payload:
        active_tasks:   Number of active tasks
        pending_tasks:  Number of pending tasks
        running_tasks:  Number of running tasks
        completed_tasks: Number of completed tasks
        failed_tasks:   Number of failed tasks
        executor_stats: Executor statistics
        queue_stats:    Queue statistics
    """
    
    METRICS_UPDATE = "execution_metrics_update"
    """
    Fired with metrics updates.
    
    Payload:
        tasks_executed:    Total tasks executed
        success_rate:      Success rate (0-100)
        avg_execution_time: Average execution time in ms
        retry_rate:        Retry rate (0-100)
    """
    
    # ── Error and warning events ───────────────────────────────────────────────
    
    ERROR_OCCURRED = "execution_error_occurred"
    """
    Fired when an error occurs.
    
    Payload:
        task_id: Task ID
        error:   Error message
        level:   Error level (warning/error/critical)
    """
    
    WARNING_OCCURRED = "execution_warning_occurred"
    """
    Fired when a warning occurs.
    
    Payload:
        task_id: Task ID
        warning: Warning message
    """
    
    # ── Utility methods ────────────────────────────────────────────────────────
    
    @classmethod
    def get_all_events(cls) -> list[str]:
        """Return all event names."""
        return [
            attr for attr in dir(cls)
            if attr.isupper()
            and not attr.startswith("_")
            and isinstance(getattr(cls, attr), str)
        ]
    
    @classmethod
    def get_event_description(cls, event_name: str) -> str:
        """
        Get description for an event.
        
        Args:
            event_name: Event name
            
        Returns:
            Event description, or "Unknown event" if not found
        """
        attr = getattr(cls, event_name, None)
        if attr is None:
            return "Unknown event"
        
        doc = getattr(cls, event_name).__doc__
        return doc or "No description available"


# Event payload type hints
EventPayload = Dict[str, Any]

# Type alias for event handlers (Python 3.9+ compatible)
try:
    from typing import Callable
    EventCallback = Callable[[EventPayload], None]
except ImportError:
    EventCallback = callable


def setup_logger(name: str):
    """Simple logger setup for this module."""
    import logging
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ============================================================================
# SECTION: ai.execution.execution_metrics (ai/execution/execution_metrics.py)
# ============================================================================
"""
ExecutionMetrics — performance metrics tracking.

Tracks and aggregates execution metrics including:
- Average task execution time
- Average verification time
- Average context build time
- Average model execution time
- Average apply time
- Success rate
- Failure rate
- Retry rate

Metrics are used for:
- Performance monitoring
- Capacity planning
- Optimization opportunities
- SLA tracking

Usage:
    metrics = ExecutionMetrics()
    
    # Record task completion
    metrics.record_task_success(task)
    
    # Record task failure
    metrics.record_task_failure(task)
    
    # Get metrics
    stats = metrics.get_metrics()
"""

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ai.execution.execution_task import ExecutionTask
from ai.execution.task_state import TaskState


@dataclass
class MetricSnapshot:
    """
    Snapshot of all metrics at a point in time.
    
    Attributes:
        timestamp:         When snapshot was taken
        tasks_executed:    Total tasks executed
        success_count:     Successful tasks
        failure_count:     Failed tasks
        cancel_count:      Cancelled tasks
        success_rate:      Success rate (0-100)
        failure_rate:      Failure rate (0-100)
        retry_count:       Total retries
        retry_rate:        Retry rate (0-100)
        avg_task_time_ms:  Average task execution time
        avg_verification_time_ms: Average verification time
        avg_context_time_ms: Average context build time
        avg_model_time_ms: Average model execution time
        avg_apply_time_ms: Average apply time
    """
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tasks_executed: int = 0
    success_count: int = 0
    failure_count: int = 0
    cancel_count: int = 0
    success_rate: float = 0.0
    failure_rate: float = 0.0
    retry_count: int = 0
    retry_rate: float = 0.0
    avg_task_time_ms: float = 0.0
    avg_verification_time_ms: float = 0.0
    avg_context_time_ms: float = 0.0
    avg_model_time_ms: float = 0.0
    avg_apply_time_ms: float = 0.0


class ExecutionMetrics:
    """
    Performance metrics tracking for execution engine.
    
    Maintains running averages and counts for all execution metrics.
    
    Usage:
        metrics = ExecutionMetrics()
        
        # Record completions
        metrics.record_task_success(task)
        metrics.record_task_failure(task)
        
        # Get current metrics
        stats = metrics.get_metrics()
        
        # Get historical metrics
        history = metrics.get_history(limit=10)
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        
        # Counters
        self._tasks_executed = 0
        self._success_count = 0
        self._failure_count = 0
        self._cancel_count = 0
        self._retry_count = 0
        
        # Timing storage (for running average)
        self._task_times: List[float] = []
        self._verification_times: List[float] = []
        self._context_times: List[float] = []
        self._model_times: List[float] = []
        self._apply_times: List[float] = []
        
        # Historical snapshots
        self._history: List[MetricSnapshot] = []
        self._max_history = 1000
        
        logger = setup_logger(__name__)
        logger.info("ExecutionMetrics initialized")
    
    # ── Public API ──────────────────────────────────────────────────────────────
    
    def record_task_success(self, task: ExecutionTask) -> None:
        """
        Record a successful task completion.
        
        Args:
            task: Completed task
        """
        with self._lock:
            self._tasks_executed += 1
            self._success_count += 1
            
            # Record task time
            if task.stats.total_duration_ms > 0:
                self._task_times.append(task.stats.total_duration_ms)
                # Keep only last 1000 for moving average
                if len(self._task_times) > 1000:
                    self._task_times = self._task_times[-1000:]
            
            # Record verification time if available
            if task.stats.verification_time_ms > 0:
                self._verification_times.append(task.stats.verification_time_ms)
                if len(self._verification_times) > 1000:
                    self._verification_times = self._verification_times[-1000:]
            
            # Record context time if available
            if task.stats.context_time_ms > 0:
                self._context_times.append(task.stats.context_time_ms)
                if len(self._context_times) > 1000:
                    self._context_times = self._context_times[-1000:]
            
            # Record retry count
            self._retry_count += task.stats.retry_count
            
            # Update history
            self._take_snapshot()
    
    def record_task_failure(self, task: ExecutionTask) -> None:
        """
        Record a failed task completion.
        
        Args:
            task: Failed task
        """
        with self._lock:
            self._tasks_executed += 1
            self._failure_count += 1
            
            # Record retry count
            self._retry_count += task.stats.retry_count
            
            # Update history
            self._take_snapshot()
    
    def record_task_cancelled(self, task: ExecutionTask) -> None:
        """
        Record a cancelled task.
        
        Args:
            task: Cancelled task
        """
        with self._lock:
            self._tasks_executed += 1
            self._cancel_count += 1
            
            # Update history
            self._take_snapshot()
    
    def record_verification_time(self, duration_ms: float) -> None:
        """
        Record a verification execution time.
        
        Args:
            duration_ms: Duration in milliseconds
        """
        with self._lock:
            self._verification_times.append(duration_ms)
            if len(self._verification_times) > 1000:
                self._verification_times = self._verification_times[-1000:]
    
    def record_context_build_time(self, duration_ms: float) -> None:
        """
        Record a context build time.
        
        Args:
            duration_ms: Duration in milliseconds
        """
        with self._lock:
            self._context_times.append(duration_ms)
            if len(self._context_times) > 1000:
                self._context_times = self._context_times[-1000:]
    
    def record_model_execution_time(self, duration_ms: float) -> None:
        """
        Record a model execution time.
        
        Args:
            duration_ms: Duration in milliseconds
        """
        with self._lock:
            self._model_times.append(duration_ms)
            if len(self._model_times) > 1000:
                self._model_times = self._model_times[-1000:]
    
    def record_apply_time(self, duration_ms: float) -> None:
        """
        Record a change apply time.
        
        Args:
            duration_ms: Duration in milliseconds
        """
        with self._lock:
            self._apply_times.append(duration_ms)
            if len(self._apply_times) > 1000:
                self._apply_times = self._apply_times[-1000:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics as a dictionary.
        
        Returns:
            Metrics dictionary
        """
        with self._lock:
            total = self._tasks_executed or 1
            
            return {
                "tasks_executed": self._tasks_executed,
                "success_count": self._success_count,
                "failure_count": self._failure_count,
                "cancel_count": self._cancel_count,
                "success_rate": round((self._success_count / total) * 100, 2),
                "failure_rate": round((self._failure_count / total) * 100, 2),
                "retry_count": self._retry_count,
                "retry_rate": round((self._retry_count / self._tasks_executed) * 100, 2) if self._tasks_executed > 0 else 0.0,
                "avg_task_time_ms": self._avg(self._task_times),
                "avg_verification_time_ms": self._avg(self._verification_times),
                "avg_context_time_ms": self._avg(self._context_times),
                "avg_model_time_ms": self._avg(self._model_times),
                "avg_apply_time_ms": self._avg(self._apply_times),
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    def get_history(self, limit: int = 10) -> List[MetricSnapshot]:
        """
        Get historical metrics snapshots.
        
        Args:
            limit: Maximum number of snapshots
            
        Returns:
            List of snapshots (newest first)
        """
        with self._lock:
            return list(reversed(self._history[-limit:]))
    
    def clear_history(self) -> None:
        """Clear historical snapshots."""
        with self._lock:
            self._history.clear()
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._tasks_executed = 0
            self._success_count = 0
            self._failure_count = 0
            self._cancel_count = 0
            self._retry_count = 0
            self._task_times.clear()
            self._verification_times.clear()
            self._context_times.clear()
            self._model_times.clear()
            self._apply_times.clear()
            self._history.clear()
    
    # ── Private helpers ─────────────────────────────────────────────────────────
    
    def _avg(self, values: List[float]) -> float:
        """Calculate average of values."""
        if not values:
            return 0.0
        return sum(values) / len(values)
    
    def _take_snapshot(self) -> None:
        """Take a metrics snapshot."""
        total = self._tasks_executed or 1
        
        snapshot = MetricSnapshot(
            tasks_executed=self._tasks_executed,
            success_count=self._success_count,
            failure_count=self._failure_count,
            cancel_count=self._cancel_count,
            success_rate=(self._success_count / total) * 100,
            failure_rate=(self._failure_count / total) * 100,
            retry_count=self._retry_count,
            retry_rate=(self._retry_count / self._tasks_executed) * 100 if self._tasks_executed > 0 else 0.0,
            avg_task_time_ms=self._avg(self._task_times),
            avg_verification_time_ms=self._avg(self._verification_times),
            avg_context_time_ms=self._avg(self._context_times),
            avg_model_time_ms=self._avg(self._model_times),
            avg_apply_time_ms=self._avg(self._apply_times),
        )
        
        self._history.append(snapshot)
        
        # Trim history
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]


def setup_logger(name: str):
    """Simple logger setup for this module."""
    import logging
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ============================================================================
# SECTION: ai.execution.execution_report (ai/execution/execution_report.py)
# ============================================================================
"""
ExecutionReportGenerator — human-readable execution reports.

Generates detailed execution reports for tasks including:
- Execution time
- Files modified/created/deleted
- Verification results
- Retry count
- Errors/warnings
- Risk assessment
- Rollback information

Reports are used for:
- User feedback
- Audit trails
- Debugging
- Analytics

Usage:
    reporter = ExecutionReportGenerator()
    report = reporter.generate(task)
    print(report)
"""

import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai.execution.execution_task import ExecutionTask, ExecutionResult
from ai.execution.task_state import TaskState


@dataclass
class ExecutionReport:
    """
    Generated execution report.
    
    Attributes:
        task_id:          Task ID
        title:            Task title
        status:           Final status
        start_time:       When execution started
        end_time:         When execution completed
        total_duration_ms: Total execution time
        steps_executed:   Number of steps executed
        files_modified:   List of modified files
        files_created:    List of created files
        files_deleted:    List of deleted files
        errors:           List of errors
        warnings:         List of warnings
        risk_level:       Risk level (low/medium/high/critical)
        rollback_id:      Rollback point ID (if applicable)
        retry_count:      Number of retries
        model_used:       Primary model used
        verification:     Verification summary
        step_details:     Detailed per-step information
    """
    task_id: str
    title: str
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_duration_ms: float = 0.0
    steps_executed: int = 0
    files_modified: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    files_deleted: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    risk_level: str = "low"
    rollback_id: Optional[str] = None
    retry_count: int = 0
    model_used: Optional[str] = None
    verification: Optional[Dict[str, Any]] = None
    step_details: List[Dict[str, Any]] = field(default_factory=list)


class ExecutionReportGenerator:
    """
    Generates human-readable execution reports.
    
    Usage:
        reporter = ExecutionReportGenerator()
        
        # Generate report for a task
        report = reporter.generate(task)
        
        # Format as text
        text = reporter.format_text(report)
        
        # Format as markdown
        markdown = reporter.format_markdown(report)
    """
    
    def __init__(self) -> None:
        self._logger = setup_logger(__name__)
    
    # ── Public API ──────────────────────────────────────────────────────────────
    
    def generate(self, task: ExecutionTask) -> ExecutionReport:
        """
        Generate a report for a task.
        
        Args:
            task: Task to report on
            
        Returns:
            ExecutionReport
        """
        report = ExecutionReport(
            task_id=task.id,
            title=task.task.title or task.task.original_prompt[:50],
            status=task.state.value,
            start_time=task.started_time,
            end_time=task.completed_time,
            total_duration_ms=task.stats.total_duration_ms,
            steps_executed=task.stats.steps_executed,
            files_modified=task.stats.files_modified,
            files_created=task.stats.files_created,
            files_deleted=task.stats.files_deleted,
            errors=[task.error] if task.error else [],
            retry_count=task.stats.retry_count,
            model_used=self._extract_model(task),
            verification=self._extract_verification(task),
            step_details=self._extract_step_details(task),
        )
        
        # Calculate risk level
        report.risk_level = self._calculate_risk(report)
        
        # Generate rollback ID for successful tasks
        if task.state == TaskState.SUCCESS:
            import uuid
            report.rollback_id = str(uuid.uuid4())[:8]
        
        return report
    
    def format_text(self, report: ExecutionReport) -> str:
        """
        Format report as plain text.
        
        Args:
            report: Report to format
            
        Returns:
            Formatted text string
        """
        lines = []
        
        # Header
        lines.append("=" * 60)
        lines.append(f"EXECUTION REPORT - Task {report.task_id[:8]}")
        lines.append("=" * 60)
        lines.append("")
        
        # Status
        lines.append(f"Status:       {report.status.upper()}")
        lines.append(f"Title:        {report.title}")
        lines.append(f"Risk Level:   {report.risk_level.upper()}")
        lines.append("")
        
        # Timing
        if report.start_time:
            lines.append(f"Started:      {report.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if report.end_time:
            lines.append(f"Completed:    {report.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Duration:     {report.total_duration_ms:.1f} ms")
        lines.append("")
        
        # Execution stats
        lines.append(f"Steps:        {report.steps_executed}")
        lines.append(f"Retries:      {report.retry_count}")
        if report.model_used:
            lines.append(f"Model:        {report.model_used}")
        if report.rollback_id:
            lines.append(f"Rollback ID:  {report.rollback_id}")
        lines.append("")
        
        # Files
        if report.files_modified:
            lines.append("Modified:")
            for f in report.files_modified:
                lines.append(f"  - {f}")
        
        if report.files_created:
            lines.append("Created:")
            for f in report.files_created:
                lines.append(f"  + {f}")
        
        if report.files_deleted:
            lines.append("Deleted:")
            for f in report.files_deleted:
                lines.append(f"  x {f}")
        lines.append("")
        
        # Errors
        if report.errors:
            lines.append("Errors:")
            for error in report.errors:
                lines.append(f"  ❌ {error}")
            lines.append("")
        
        # Warnings
        if report.warnings:
            lines.append("Warnings:")
            for warning in report.warnings:
                lines.append(f"  ⚠️  {warning}")
            lines.append("")
        
        # Step details
        if report.step_details:
            lines.append("Step Details:")
            for step in report.step_details:
                status = "✓" if step.get("success") else "✗"
                lines.append(f"  {status} Step {step.get('index', '?')}: {step.get('text', 'Unknown')}")
            lines.append("")
        
        # Footer
        lines.append("=" * 60)
        lines.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def format_markdown(self, report: ExecutionReport) -> str:
        """
        Format report as Markdown.
        
        Args:
            report: Report to format
            
        Returns:
            Formatted Markdown string
        """
        lines = []
        
        lines.append(f"# Execution Report: {report.title}")
        lines.append("")
        
        lines.append("## Summary")
        lines.append("")
        lines.append(f"| Property | Value |")
        lines.append(f"|----------|-------|")
        lines.append(f"| Task ID | `{report.task_id}` |")
        lines.append(f"| Status | {self._status_emoji(report.status)} `{report.status.upper()}` |")
        lines.append(f"| Risk Level | {self._risk_emoji(report.risk_level)} `{report.risk_level.upper()}` |")
        lines.append(f"| Duration | {report.total_duration_ms:.1f} ms |")
        lines.append(f"| Steps | {report.steps_executed} |")
        lines.append(f"| Retries | {report.retry_count} |")
        if report.model_used:
            lines.append(f"| Model | `{report.model_used}` |")
        lines.append("")
        
        # Timing
        lines.append("## Timing")
        lines.append("")
        if report.start_time:
            lines.append(f"- **Started:** {report.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if report.end_time:
            lines.append(f"- **Completed:** {report.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Files
        lines.append("## Files Changed")
        lines.append("")
        
        if report.files_created:
            lines.append("### Created")
            for f in report.files_created:
                lines.append(f"- ✅ `{f}`")
            lines.append("")
        
        if report.files_modified:
            lines.append("### Modified")
            for f in report.files_modified:
                lines.append(f"- 📝 `{f}`")
            lines.append("")
        
        if report.files_deleted:
            lines.append("### Deleted")
            for f in report.files_deleted:
                lines.append(f"- ❌ `{f}`")
            lines.append("")
        
        # Errors and warnings
        if report.errors or report.warnings:
            lines.append("## Issues")
            lines.append("")
            
            if report.errors:
                lines.append("### Errors")
                for error in report.errors:
                    lines.append(f"- ❌ {error}")
                lines.append("")
            
            if report.warnings:
                lines.append("### Warnings")
                for warning in report.warnings:
                    lines.append(f"- ⚠️  {warning}")
                lines.append("")
        
        # Verification
        if report.verification:
            lines.append("## Verification")
            lines.append("")
            
            if report.verification.get("success"):
                lines.append("✅ **Verification passed**")
            else:
                lines.append("❌ **Verification failed**")
            
            if report.verification.get("report"):
                lines.append("")
                lines.append("```")
                lines.append(report.verification["report"][:500])
                lines.append("```")
            lines.append("")
        
        # Step details
        if report.step_details:
            lines.append("## Step Details")
            lines.append("")
            
            for step in report.step_details:
                status = "✅" if step.get("success") else "❌"
                lines.append(f"### {status} Step {step.get('index', '?')}")
                lines.append(f"- {step.get('text', 'Unknown')}")
                
                if step.get("duration_ms"):
                    lines.append(f"- Duration: {step['duration_ms']:.1f} ms")
                
                if step.get("model_used"):
                    lines.append(f"- Model: `{step['model_used']}`")
                
                if step.get("tools_used"):
                    lines.append(f"- Tools: {', '.join(step['tools_used'])}")
                lines.append("")
        
        # Footer
        lines.append("---")
        lines.append(f"*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return "\n".join(lines)
    
    # ── Private helpers ─────────────────────────────────────────────────────────
    
    def _extract_model(self, task: ExecutionTask) -> Optional[str]:
        """Extract the primary model used from task results."""
        for result in task.results:
            if result.model_used:
                return result.model_used
        return None
    
    def _extract_verification(self, task: ExecutionTask) -> Optional[Dict[str, Any]]:
        """Extract verification info from task."""
        # In production, this would extract from task.metadata
        # for now, return None
        return None
    
    def _extract_step_details(self, task: ExecutionTask) -> List[Dict[str, Any]]:
        """Extract step details from task results."""
        details = []
        for i, result in enumerate(task.results):
            details.append({
                "index": result.step_index,
                "text": result.step_text,
                "success": result.success,
                "duration_ms": result.duration_ms,
                "model_used": result.model_used,
                "tools_used": result.tools_used,
            })
        return details
    
    def _calculate_risk(self, report: ExecutionReport) -> str:
        """Calculate risk level based on report content."""
        # Start with low risk
        risk = "low"
        
        # Check file operations
        if len(report.files_deleted) > 5:
            risk = "high"
        elif len(report.files_deleted) > 0:
            risk = "medium"
        
        if len(report.files_modified) > 10:
            risk = "high"
        elif len(report.files_modified) > 3:
            risk = "medium"
        
        # Check errors
        if len(report.errors) > 0:
            risk = "high"
        
        # Check verification
        if report.verification and not report.verification.get("success"):
            risk = "high"
        
        return risk
    
    def _status_emoji(self, status: str) -> str:
        """Return emoji for status."""
        emojis = {
            "success": "✅",
            "failed": "❌",
            "cancelled": "🛑",
            "pending": "⏳",
            "running": "🚀",
        }
        return emojis.get(status, "❓")
    
    def _risk_emoji(self, risk: str) -> str:
        """Return emoji for risk level."""
        emojis = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🟠",
            "critical": "🔴",
        }
        return emojis.get(risk, "❓")


def setup_logger(name: str):
    """Simple logger setup for this module."""
    import logging
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ============================================================================
# SECTION: ai.execution.execution_queue (ai/execution/execution_queue.py)
# ============================================================================
"""
ExecutionQueue — priority queue with persistence support.

Manages a priority queue of ExecutionTasks for the TaskScheduler.
Supports:
- Priority-based ordering
- Task groups for parallel execution
- Persistence to disk for application restarts
- Thread-safe operations

Tasks are ordered by:
1. Priority (higher = first)
2. Created time (earlier = first)
3. Task ID (alphabetically for stability)

This queue survives application restarts by serializing
its state to a JSON file in the config directory.
"""

import json
import threading
import time
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from uuid import uuid4

from ai.execution.execution_task import ExecutionTask, ExecutionConfig
from ai.execution.task_state import TaskState, StateTransition


class QueuePriority(int, Enum):
    """Priority levels for task queuing."""
    CRITICAL = 100
    URGENT   = 90
    HIGH     = 80
    MEDIUM   = 50
    LOW      = 20
    IDLE     = 10


class ExecutionQueue:
    """
    Thread-safe priority queue for ExecutionTasks.
    
    Features:
    - Priority-based ordering (higher priority = dequeued first)
    - Task groups for related tasks
    - Persistence to disk for restarts
    - Thread-safe operations via lock
    - Statistics tracking
    
    Usage:
        queue = ExecutionQueue(config_dir="/path/to/config")
        
        # Add task
        queue.enqueue(task)
        
        # Dequeue highest priority task
        task = queue.dequeue()
        
        # Save to disk
        queue.save()
        
        # Load from disk
        queue.load()
    """
    
    def __init__(
        self,
        config_dir: str,
        name: str = "default",
    ) -> None:
        self._config_dir = Path(config_dir)
        self._queue_file = self._config_dir / f"execution_queue_{name}.json"
        self._lock = threading.RLock()
        
        # Internal data structures
        self._tasks: Dict[str, ExecutionTask] = {}  # id → task
        self._priority_heap: List[tuple] = []       # (-priority, created_time, id)
        
        # Statistics
        self._total_enqueued = 0
        self._total_dequeued = 0
        self._total_requeued = 0
        
        logger = setup_logger(__name__)
        logger.info(f"ExecutionQueue initialized (file={self._queue_file.name})")
    
    # ── Public API ──────────────────────────────────────────────────────────────
    
    def enqueue(self, task: ExecutionTask) -> None:
        """
        Add a task to the queue.
        
        Args:
            task: Task to enqueue
        
        Raises:
            ValueError: If task is already terminal
        """
        if task.state_history.is_terminal:
            raise ValueError(f"Cannot enqueue terminal task: {task.id}")
        
        with self._lock:
            if task.id in self._tasks:
                # Already in queue, update and reheap
                self._tasks[task.id] = task
                self._rebuild_heap()
            else:
                self._tasks[task.id] = task
                self._push_to_heap(task)
                self._total_enqueued += 1
            
            # Update state
            task.state_history.add_transition(
                StateTransition(
                    from_state=task.state,
                    to_state=TaskState.SCHEDULED,
                    timestamp=datetime.utcnow(),
                    reason="Task enqueued",
                )
            )
        
        self._maybe_save()
    
    def dequeue(self) -> Optional[ExecutionTask]:
        """
        Remove and return the highest priority task.
        
        Returns:
            Highest priority task, or None if queue empty
        """
        with self._lock:
            if not self._priority_heap:
                return None
            
            _, _, task_id = self._priority_heap.pop(0)
            task = self._tasks.pop(task_id, None)
            
            if task:
                self._total_dequeued += 1
                task.state_history.add_transition(
                    StateTransition(
                        from_state=task.state,
                        to_state=TaskState.RUNNING,
                        timestamp=datetime.utcnow(),
                        reason="Task dequeued for execution",
                    )
                )
            
            return task
    
    def peek(self) -> Optional[ExecutionTask]:
        """Return highest priority task without removing it."""
        with self._lock:
            if not self._priority_heap:
                return None
            _, _, task_id = self._priority_heap[0]
            return self._tasks.get(task_id)
    
    def remove(self, task_id: str) -> bool:
        """
        Remove a specific task from the queue.
        
        Args:
            task_id: ID of task to remove
            
        Returns:
            True if task was removed, False if not found
        """
        with self._lock:
            if task_id not in self._tasks:
                return False
            
            del self._tasks[task_id]
            self._rebuild_heap()
            return True
    
    def contains(self, task_id: str) -> bool:
        """Check if a task is in the queue."""
        with self._lock:
            return task_id in self._tasks
    
    def get_task(self, task_id: str) -> Optional[ExecutionTask]:
        """Get a task by ID without removing it."""
        with self._lock:
            return self._tasks.get(task_id)
    
    def list_tasks(self) -> List[ExecutionTask]:
        """Return all tasks in priority order."""
        with self._lock:
            return [self._tasks[tid] for _, _, tid in sorted(self._priority_heap)]
    
    def count(self) -> int:
        """Return number of tasks in queue."""
        with self._lock:
            return len(self._tasks)
    
    def clear(self) -> None:
        """Remove all tasks from queue."""
        with self._lock:
            self._tasks.clear()
            self._priority_heap.clear()
    
    def get_by_group(self, group: str) -> List[ExecutionTask]:
        """Get all tasks in a group."""
        with self._lock:
            return [
                t for t in self._tasks.values()
                if t.config.group == group
            ]
    
    def get_pending_for_group(self, group: str) -> List[ExecutionTask]:
        """Get pending tasks in a group (waiting for dependencies)."""
        with self._lock:
            return [
                t for t in self._tasks.values()
                if t.config.group == group and t.state == TaskState.PENDING
            ]
    
    # ── Persistence ─────────────────────────────────────────────────────────────
    
    def save(self) -> None:
        """Save queue state to disk."""
        with self._lock:
            self._maybe_save()
    
    def load(self) -> int:
        """
        Load queue state from disk.
        
        Returns:
            Number of tasks loaded
        """
        if not self._queue_file.exists():
            return 0
        
        with self._lock:
            try:
                with open(self._queue_file, 'r') as f:
                    data = json.load(f)
                
                loaded = 0
                for task_data in data.get("tasks", []):
                    task = self._deserialize_task(task_data)
                    if task and not task.state_history.is_terminal:
                        self._tasks[task.id] = task
                        self._push_to_heap(task)
                        loaded += 1
                
                self._total_enqueued = data.get("total_enqueued", 0)
                self._total_dequeued = data.get("total_dequeued", 0)
                
                return loaded
                
            except Exception as e:
                logger = setup_logger(__name__)
                logger.error(f"Failed to load queue: {e}")
                return 0
    
    # ── Statistics ──────────────────────────────────────────────────────────────
    
    def stats(self) -> dict:
        """Return queue statistics."""
        with self._lock:
            return {
                "size": len(self._tasks),
                "total_enqueued": self._total_enqueued,
                "total_dequeued": self._total_dequeued,
                "total_requeued": self._total_requeued,
            }
    
    def stats_by_priority(self) -> Dict[str, int]:
        """Return task count grouped by priority."""
        with self._lock:
            counts: Dict[str, int] = {}
            for task in self._tasks.values():
                priority = task.config.priority or 50
                if priority >= 90:
                    key = "high"
                elif priority >= 50:
                    key = "medium"
                else:
                    key = "low"
                counts[key] = counts.get(key, 0) + 1
            return counts
    
    # ── Private helpers ─────────────────────────────────────────────────────────
    
    def _push_to_heap(self, task: ExecutionTask) -> None:
        """Add task to priority heap."""
        priority = task.config.priority or 50
        created = task.created_time
        # Use negative priority for max-heap behavior (heapq is min-heap)
        entry = (-priority, created, task.id)
        self._priority_heap.append(entry)
        self._priority_heap.sort()  # Re-sort after insert
    
    def _rebuild_heap(self) -> None:
        """Rebuild heap from scratch."""
        self._priority_heap.clear()
        for task in self._tasks.values():
            self._push_to_heap(task)
    
    def _maybe_save(self) -> None:
        """Save to disk if not already saved recently."""
        # Don't save on every enqueue - only periodically
        # For simplicity, we save here. In production, use a timer.
        self._save()
    
    def _save(self) -> None:
        """Actually save to disk."""
        try:
            self._queue_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "version": "1.0",
                "saved_at": datetime.utcnow().isoformat(),
                "total_enqueued": self._total_enqueued,
                "total_dequeued": self._total_dequeued,
                "tasks": [
                    self._serialize_task(task)
                    for task in self._tasks.values()
                ],
            }
            
            with open(self._queue_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger = setup_logger(__name__)
            logger.error(f"Failed to save queue: {e}")
    
    def _serialize_task(self, task: ExecutionTask) -> dict:
        """Serialize task to dict."""
        return {
            "id": task.id,
            "prompt": task.task.original_prompt,
            "title": task.task.title,
            "status": task.status.value,
            "state": task.state.value,
            "created_time": task.created_time.isoformat(),
            "config": {
                "mode": task.config.mode.value,
                "max_retries": task.config.max_retries,
                "retry_strategy": task.config.retry_strategy.value,
                "timeout_secs": task.config.timeout_secs,
                "priority": task.config.priority,
                "group": task.config.group,
                "cancel_on_error": task.config.cancel_on_error,
                "depends_on": task.config.depends_on,
            },
        }
    
    def _deserialize_task(self, data: dict) -> Optional[ExecutionTask]:
        """Deserialize task from dict."""
        try:
            from ai.engine.task import Task as BaseTask, TaskStatus as BaseStatus
            
            base_task = BaseTask(
                original_prompt=data["prompt"],
                title=data.get("title", ""),
            )
            base_task.status = BaseStatus(data.get("status", "pending"))
            
            config_data = data.get("config", {})
            config = ExecutionConfig(
                mode=ExecutionMode(config_data.get("mode", "background")),
                max_retries=config_data.get("max_retries", 2),
                retry_strategy=RetryStrategy(config_data.get("retry_strategy", "exponential")),
                timeout_secs=config_data.get("timeout_secs"),
                priority=config_data.get("priority"),
                group=config_data.get("group"),
                cancel_on_error=config_data.get("cancel_on_error", True),
                depends_on=config_data.get("depends_on", []),
            )
            
            task = ExecutionTask(
                task=base_task,
                config=config,
            )
            
            # Restore timing
            task.created_time = datetime.fromisoformat(data["created_time"])
            
            # Restore state
            state = TaskState(data.get("state", "pending"))
            if not task.state_history.transitions:
                task.state_history.add_transition(
                    StateTransition(
                        from_state=None,
                        to_state=state,
                        timestamp=task.created_time,
                        reason="Task restored from queue",
                    )
                )
            else:
                task.state_history.transitions[-1].to_state = state
            
            return task
            
        except Exception as e:
            logger = setup_logger(__name__)
            logger.error(f"Failed to deserialize task: {e}")
            return None


def setup_logger(name: str):
    """Simple logger setup for this module."""
    import logging
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ============================================================================
# SECTION: ai.execution.execution_monitor (ai/execution/execution_monitor.py)
# ============================================================================
"""
ExecutionMonitor — real-time monitoring of execution metrics.

Monitors running tasks and collects metrics for:
- Current step
- Current tool
- Current model
- Execution time
- Progress
- Memory usage
- CPU usage
- Errors and warnings

Provides a unified view of execution state for the UI and
other monitoring systems.

Usage:
    monitor = ExecutionMonitor(engine)
    monitor.start()
    
    # Get current status
    status = monitor.get_status()
    
    # Subscribe to updates
    monitor.on_status_change(lambda status: print(status))
"""

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ai.execution.execution_task import ExecutionTask, ExecutionResult
from ai.execution.task_state import TaskState
from core.logger import setup_logger


@dataclass
class MonitorStatus:
    """
    Current monitoring status.
    
    Attributes:
        timestamp:      When this status was captured
        active_task:    Currently executing task (if any)
        task_progress:  Progress percentage (0-100)
        current_step:   Current step index
        current_tool:   Currently executing tool (if any)
        current_model:  Currently selected model (if any)
        elapsed_time_ms: Total execution time so far
        estimated_total_ms: Estimated total time
        estimated_remaining_ms: Estimated remaining time
        memory_usage_mb: Current memory usage
        cpu_usage_percent: Current CPU usage
        errors:         Recent errors
        warnings:       Recent warnings
    """
    timestamp: datetime = field(default_factory=datetime.utcnow)
    active_task: Optional[str] = None
    task_progress: float = 0.0
    current_step: int = 0
    current_tool: Optional[str] = None
    current_model: Optional[str] = None
    elapsed_time_ms: float = 0.0
    estimated_total_ms: float = 0.0
    estimated_remaining_ms: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ExecutionMonitor:
    """
    Real-time execution monitor.
    
    Continuously monitors running tasks and provides
    up-to-date status information.
    
    Usage:
        monitor = ExecutionMonitor(engine)
        monitor.start()
        
        # Get current status
        while monitor.is_running():
            status = monitor.get_status()
            print(status)
            time.sleep(1.0)
        
        monitor.stop()
    """
    
    def __init__(self, engine: Any) -> None:
        self._engine = engine
        self._lock = threading.RLock()
        self._shutdown = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Status storage
        self._status: MonitorStatus = MonitorStatus()
        self._status_listeners: List[Callable[[MonitorStatus], None]] = []
        
        # Recent history for trending
        self._history: List[MonitorStatus] = []
        self._max_history = 100
        
        logger = setup_logger(__name__)
        logger.info("ExecutionMonitor initialized")
    
    # ── Public API ──────────────────────────────────────────────────────────────
    
    def start(self) -> None:
        """Start monitoring."""
        if self._monitor_thread:
            return
        
        self._shutdown = False
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ExecutionMonitor",
        )
        self._monitor_thread.start()
        
        logger = setup_logger(__name__)
        logger.info("ExecutionMonitor started")
    
    def stop(self) -> None:
        """Stop monitoring."""
        self._shutdown = True
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
            self._monitor_thread = None
        
        logger = setup_logger(__name__)
        logger.info("ExecutionMonitor stopped")
    
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._monitor_thread is not None and not self._shutdown
    
    def get_status(self) -> MonitorStatus:
        """
        Get current monitoring status.
        
        Returns:
            Current MonitorStatus
        """
        with self._lock:
            return self._update_status()
    
    def get_status_for_task(self, task_id: str) -> Optional[MonitorStatus]:
        """Get status for a specific task."""
        with self._lock:
            task = self._engine.get_task(task_id)
            if not task:
                return None
            
            # Build status for this task
            status = MonitorStatus()
            
            if task.started_time:
                elapsed = (datetime.utcnow() - task.started_time).total_seconds() * 1000
                status.elapsed_time_ms = elapsed
            
            if task.completed_time:
                total = (task.completed_time - task.started_time).total_seconds() * 1000 if task.started_time else 0
                status.estimated_total_ms = total
                status.task_progress = 100.0
            elif task.started_time:
                # Estimate based on completed steps
                completed = sum(1 for r in task.results if r.success)
                total_steps = len(task.task.plan) or 1
                status.task_progress = (completed / total_steps) * 100
                
                # Estimate remaining
                if completed > 0:
                    avg_step_time = elapsed / completed
                    remaining = (total_steps - completed) * avg_step_time
                    status.estimated_remaining_ms = remaining
                    status.estimated_total_ms = elapsed + remaining
            
            status.active_task = task_id
            status.errors = [task.error] if task.error else []
            
            return status
    
    def on_status_change(self, callback: Callable[[MonitorStatus], None]) -> None:
        """
        Register a callback for status changes.
        
        Args:
            callback: Function that takes MonitorStatus
        """
        with self._lock:
            self._status_listeners.append(callback)
    
    def get_history(self, limit: int = 10) -> List[MonitorStatus]:
        """
        Get recent status history.
        
        Args:
            limit: Maximum number of history items
            
        Returns:
            List of recent MonitorStatus (newest first)
        """
        with self._lock:
            return list(reversed(self._history[-limit:]))
    
    def clear_history(self) -> None:
        """Clear status history."""
        with self._lock:
            self._history.clear()
    
    # ── Private helpers ─────────────────────────────────────────────────────────
    
    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while not self._shutdown:
            try:
                status = self._update_status()
                
                with self._lock:
                    self._status = status
                    self._history.append(status)
                    
                    # Trim history
                    if len(self._history) > self._max_history:
                        self._history = self._history[-self._max_history:]
                    
                    # Notify listeners
                    for listener in self._status_listeners[:]:
                        try:
                            listener(status)
                        except Exception as e:
                            logger = setup_logger(__name__)
                            logger.error(f"Status listener error: {e}")
                
                # Small delay
                time.sleep(0.5)
                
            except Exception as e:
                logger = setup_logger(__name__)
                logger.error(f"Monitor loop error: {e}")
                time.sleep(1.0)
    
    def _update_status(self) -> MonitorStatus:
        """Update and return current status."""
        now = datetime.utcnow()
        
        # Get active task
        active_tasks = self._engine.get_running_tasks()
        active_task = active_tasks[0] if active_tasks else None
        
        status = MonitorStatus(timestamp=now)
        
        if active_task:
            status.active_task = active_task.id
            
            # Calculate progress
            completed = sum(1 for r in active_task.results if r.success)
            total_steps = len(active_task.task.plan) or 1
            status.task_progress = (completed / total_steps) * 100
            status.current_step = completed
            
            # Get current step details
            if active_task.results:
                last_result = active_task.results[-1]
                status.current_tool = last_result.tools_used[0] if last_result.tools_used else None
                status.current_model = last_result.model_used
            
            # Calculate timing
            if active_task.started_time:
                elapsed = (now - active_task.started_time).total_seconds() * 1000
                status.elapsed_time_ms = elapsed
                
                # Estimate remaining
                if completed > 0:
                    avg_step_time = elapsed / completed
                    remaining = (total_steps - completed) * avg_step_time
                    status.estimated_remaining_ms = remaining
                    status.estimated_total_ms = elapsed + remaining
            
            # Error/warning collection
            if active_task.error:
                status.errors.append(active_task.error)
        
        # Collect status from all tasks
        all_tasks = self._engine.get_all_tasks()
        errors = []
        warnings = []
        
        for task in all_tasks:
            if task.error:
                errors.append(f"Task {task.id[:8]}: {task.error}")
            
            # Check for warnings in results
            for result in task.results:
                if not result.success:
                    warnings.append(f"Step {result.step_index}: {result.error}")
        
        status.errors = errors
        status.warnings = warnings
        
        # Mock resource usage (in production, gather from OS)
        status.memory_usage_mb = 100.0 + len(all_tasks) * 10
        status.cpu_usage_percent = min(50.0 + len(active_tasks) * 10, 100.0)
        
        return status


def setup_logger(name: str):
    """Simple logger setup for this module."""
    import logging
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ============================================================================
# SECTION: ai.execution.task_scheduler (ai/execution/task_scheduler.py)
# ============================================================================
"""
TaskScheduler — task scheduling with dependencies and groups.

Manages task scheduling for the ExecutionEngine with support for:
- Sequential execution (default)
- Parallel execution (tasks in same group)
- Dependencies between tasks (depends_on field)
- Priority ordering
- Task groups for related tasks

The scheduler uses a two-phase approach:
1. Dependency resolution: Build DAG, detect cycles, topological sort
2. Schedule execution: Determine execution order based on priorities and dependencies
"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from ai.execution.execution_task import ExecutionTask, ExecutionConfig, ExecutionMode
from ai.execution.task_state import TaskState, TaskStateHistory, StateTransition
from ai.execution.execution_queue import ExecutionQueue


class DependencyStatus(Enum):
    """Status of a task's dependencies."""
    WAITING    = "waiting"    # Some dependencies not completed
    BLOCKED    = "blocked"    # A dependency failed/cancelled
    READY      = "ready"      # All dependencies satisfied
    NO_DEPS    = "no_deps"    # No dependencies defined


@dataclass
class ScheduleResult:
    """
    Result of scheduling operation.
    
    Attributes:
        scheduled:   List of tasks scheduled for execution
        waiting:     List of tasks waiting for dependencies
        blocked:     List of tasks blocked by failed dependencies
        errors:      List of error messages
    """
    scheduled: List[str] = field(default_factory=list)
    waiting:   List[str] = field(default_factory=list)
    blocked:   List[str] = field(default_factory=list)
    errors:    List[str] = field(default_factory=list)


class TaskScheduler:
    """
    Task scheduler with dependency and group support.
    
    The scheduler maintains a dependency graph and uses it to
    determine which tasks are ready to execute.
    
    Key behaviors:
    - Tasks with no dependencies are scheduled first
    - Tasks in the same group can run in parallel
    - Tasks with unsatisfied dependencies wait
    - Tasks with failed dependencies are blocked
    
    Usage:
        scheduler = TaskScheduler(queue, config_dir)
        scheduler.add_task(task)
        ready, waiting = scheduler.get_ready_tasks()
        scheduler.mark_completed(task_id)
    """
    
    def __init__(
        self,
        queue: ExecutionQueue,
        config_dir: str,
    ) -> None:
        self._queue = queue
        self._config_dir = Path(config_dir)
        self._dependency_graph: Dict[str, Set[str]] = {}  # task_id → dependencies
        self._dependents: Dict[str, Set[str]] = {}        # task_id → dependents
        self._lock = threading.RLock()
        self._grouped_tasks: Dict[str, List[str]] = defaultdict(list)  # group → task_ids
        
        logger = setup_logger(__name__)
        logger.info("TaskScheduler initialized")
    
    # ── Public API ──────────────────────────────────────────────────────────────
    
    def add_task(self, task: ExecutionTask) -> bool:
        """
        Add a task to the scheduler.
        
        Args:
            task: Task to add
            
        Returns:
            True if added successfully
        """
        with self._lock:
            task_id = task.id
            
            # Register dependencies
            deps = set(task.config.depends_on)
            self._dependency_graph[task_id] = deps
            self._dependents[task_id] = set()
            
            # Update reverse dependency mapping
            for dep_id in deps:
                if dep_id in self._dependents:
                    self._dependents[dep_id].add(task_id)
            
            # Register group
            if task.config.group:
                self._grouped_tasks[task.config.group].append(task_id)
            
            # Update task state
            task.state_history.add_transition(
                StateTransition(
                    from_state=task.state,
                    to_state=TaskState.SCHEDULED,
                    timestamp=datetime.utcnow(),
                    reason="Task scheduled",
                )
            )
            
            return True
    
    def remove_task(self, task_id: str) -> bool:
        """
        Remove a task from the scheduler.
        
        Args:
            task_id: ID of task to remove
            
        Returns:
            True if removed
        """
        with self._lock:
            if task_id not in self._dependency_graph:
                return False
            
            # Remove from dependency graph
            deps = self._dependency_graph.pop(task_id)
            for dep_id in deps:
                if dep_id in self._dependents:
                    self._dependents[dep_id].discard(task_id)
            
            # Remove dependents
            self._dependents.pop(task_id, None)
            
            # Remove from groups
            for group, task_ids in self._grouped_tasks.items():
                if task_id in task_ids:
                    task_ids.remove(task_id)
            
            return True
    
    def get_ready_tasks(self) -> List[ExecutionTask]:
        """
        Get all tasks that are ready to execute.
        
        A task is ready if:
        - All its dependencies are completed successfully
        - No dependency failed/cancelled
        - Task itself is in PENDING or SCHEDULED state
        
        Returns:
            List of ready tasks, ordered by priority
        """
        with self._lock:
            ready = []
            
            for task_id, deps in self._dependency_graph.items():
                task = self._queue.get_task(task_id)
                if not task:
                    continue
                
                # Skip if not in pending/scheduled state
                if task.state not in (TaskState.PENDING, TaskState.SCHEDULED):
                    continue
                
                # Check dependencies
                status = self._check_dependencies(deps)
                
                if status == DependencyStatus.READY or status == DependencyStatus.NO_DEPS:
                    ready.append(task)
            
            # Sort by priority (higher first)
            ready.sort(key=lambda t: t.config.priority or 50, reverse=True)
            
            return ready
    
    def get_group_ready_tasks(self, group: str) -> List[ExecutionTask]:
        """
        Get all ready tasks in a group.
        
        Args:
            group: Group name
            
        Returns:
            List of ready tasks in group
        """
        with self._lock:
            group_tasks = self._grouped_tasks.get(group, [])
            ready = []
            
            for task_id in group_tasks:
                task = self._queue.get_task(task_id)
                if not task:
                    continue
                
                if task.state not in (TaskState.PENDING, TaskState.SCHEDULED):
                    continue
                
                deps = self._dependency_graph.get(task_id, set())
                status = self._check_dependencies(deps)
                
                if status == DependencyStatus.READY or status == DependencyStatus.NO_DEPS:
                    ready.append(task)
            
            ready.sort(key=lambda t: t.config.priority or 50, reverse=True)
            return ready
    
    def get_dependents(self, task_id: str) -> List[ExecutionTask]:
        """
        Get all tasks that depend on this task.
        
        Args:
            task_id: Task ID
            
        Returns:
            List of dependent tasks
        """
        with self._lock:
            dependent_ids = self._dependents.get(task_id, set())
            return [
                self._queue.get_task(tid)
                for tid in dependent_ids
                if self._queue.get_task(tid)
            ]
    
    def mark_completed(self, task_id: str, success: bool = True) -> List[str]:
        """
        Mark a task as completed and update dependents.
        
        Args:
            task_id: Completed task ID
            success: True if task succeeded
            
        Returns:
            List of task IDs that are now ready due to this completion
        """
        with self._lock:
            now_ready = []
            
            # Update dependents
            for dep_id in self._dependents.get(task_id, set()):
                task = self._queue.get_task(dep_id)
                if not task:
                    continue
                
                if task.state in (TaskState.PENDING, TaskState.SCHEDULED):
                    status = self._check_dependencies(self._dependency_graph.get(dep_id, set()))
                    
                    if status == DependencyStatus.READY:
                        now_ready.append(dep_id)
                    elif status == DependencyStatus.BLOCKED and success:
                        # Task was waiting but now unblocked
                        now_ready.append(dep_id)
            
            return now_ready
    
    def mark_failed(self, task_id: str) -> List[str]:
        """
        Mark a task as failed and block dependents.
        
        Args:
            task_id: Failed task ID
            
        Returns:
            List of blocked task IDs
        """
        with self._lock:
            blocked = []
            
            for dep_id in self._dependents.get(task_id, set()):
                task = self._queue.get_task(dep_id)
                if task and task.state == TaskState.PENDING:
                    task.state_history.add_transition(
                        StateTransition(
                            from_state=task.state,
                            to_state=TaskState.PENDING,
                            timestamp=datetime.utcnow(),
                            reason=f"Dependent task {task_id[:8]} failed",
                        )
                    )
                    blocked.append(dep_id)
            
            return blocked
    
    def detect_cycles(self) -> List[List[str]]:
        """
        Detect cycles in the dependency graph.
        
        Returns:
            List of cycles (each cycle is a list of task IDs)
        """
        with self._lock:
            cycles = []
            visited = set()
            rec_stack = set()
            path = []
            
            def dfs(node: str) -> None:
                visited.add(node)
                rec_stack.add(node)
                path.append(node)
                
                for dep in self._dependency_graph.get(node, set()):
                    if dep not in visited:
                        dfs(dep)
                    elif dep in rec_stack:
                        # Found cycle
                        cycle_start = path.index(dep)
                        cycle = path[cycle_start:] + [dep]
                        cycles.append(cycle)
                
                path.pop()
                rec_stack.remove(node)
            
            for node in self._dependency_graph:
                if node not in visited:
                    dfs(node)
            
            return cycles
    
    # ── Private helpers ─────────────────────────────────────────────────────────
    
    def _check_dependencies(self, deps: Set[str]) -> DependencyStatus:
        """Check dependency status for a task."""
        if not deps:
            return DependencyStatus.NO_DEPS
        
        all_completed = True
        any_failed = False
        
        for dep_id in deps:
            task = self._queue.get_task(dep_id)
            if not task:
                all_completed = False
                continue
            
            if task.state_history.is_terminal:
                if not task.success:
                    any_failed = True
            else:
                all_completed = False
        
        if any_failed:
            return DependencyStatus.BLOCKED
        if all_completed:
            return DependencyStatus.READY
        return DependencyStatus.WAITING


def setup_logger(name: str):
    """Simple logger setup for this module."""
    import logging
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ============================================================================
# SECTION: ai.execution.task_executor (ai/execution/task_executor.py)
# ============================================================================
"""
TaskExecutor — thread pool executor with retry logic.

Executes tasks from the queue using a configurable thread pool.
Handles retries, timeouts, and failure recovery.

Features:
- Configurable thread pool size
- Per-task timeout
- Retry with configurable strategy (fixed, exponential, jittered)
- Statistics tracking
- Error handling and recovery

Usage:
    executor = TaskExecutor(
        pool_size=4,
        max_retries=2,
        default_timeout=300  # seconds
    )
    executor.start()
    executor.submit(task)
    # ... later ...
    executor.shutdown()
"""

import threading
import time
import traceback
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from ai.execution.execution_task import ExecutionTask, ExecutionConfig, ExecutionMode, ExecutionResult
from ai.execution.task_state import TaskState, StateTransition
from ai.execution.execution_queue import ExecutionQueue


class RetryStrategy(Enum):
    """Retry strategy for failed tasks."""
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    JITTERED = "jittered"


@dataclass
class ExecutorConfig:
    """
    Configuration for TaskExecutor.
    
    Attributes:
        pool_size:      Number of worker threads
        max_retries:    Maximum retry attempts per task
        default_timeout: Default timeout in seconds for tasks without one
        retry_delay:    Base delay between retries (seconds)
        on_task_start:  Callback when task starts
        on_task_complete: Callback when task completes
        on_task_error:  Callback when task errors
    """
    pool_size:      int = 4
    max_retries:    int = 2
    default_timeout: Optional[int] = None
    retry_delay:    float = 1.0
    on_task_start:  Optional[Callable[[ExecutionTask], None]] = None
    on_task_complete: Optional[Callable[[ExecutionTask, bool], None]] = None
    on_task_error:  Optional[Callable[[ExecutionTask, Exception], None]] = None


class TaskExecutor:
    """
    Thread pool executor for ExecutionTasks.
    
    Manages a pool of worker threads that consume tasks from
    the execution queue and execute them.
    
    Usage:
        executor = TaskExecutor(config)
        executor.start()
        
        while not shutdown:
            task = queue.dequeue()
            if task:
                executor.submit(task)
        
        executor.shutdown()
    """
    
    def __init__(self, config: ExecutorConfig) -> None:
        self._config = config
        self._executor = ThreadPoolExecutor(
            max_workers=config.pool_size,
            thread_name_prefix="TaskExecutor"
        )
        self._shutdown = False
        self._lock = threading.Lock()
        
        # Statistics
        self._tasks_submitted = 0
        self._tasks_completed = 0
        self._tasks_failed = 0
        self._total_execution_time = 0.0
        
        # Active tasks tracking
        self._active_tasks: Dict[str, ExecutionTask] = {}
        self._active_futures: Dict[str, Future] = {}
        
        logger = setup_logger(__name__)
        logger.info(f"TaskExecutor initialized (pool_size={config.pool_size}, max_retries={config.max_retries})")
    
    # ── Public API ──────────────────────────────────────────────────────────────
    
    def start(self) -> None:
        """Start the executor (no-op, ThreadPoolExecutor starts automatically)."""
        with self._lock:
            self._shutdown = False
        logger = setup_logger(__name__)
        logger.info("TaskExecutor started")
    
    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the executor.
        
        Args:
            wait: If True, wait for all tasks to complete
        """
        with self._lock:
            self._shutdown = True
        
        self._executor.shutdown(wait=wait)
        
        logger = setup_logger(__name__)
        logger.info("TaskExecutor shutdown complete")
    
    def submit(self, task: ExecutionTask) -> None:
        """
        Submit a task for execution.
        
        Args:
            task: Task to execute
        """
        with self._lock:
            self._tasks_submitted += 1
            self._active_tasks[task.id] = task
        
        # Update state
        task.state_history.add_transition(
            StateTransition(
                from_state=task.state,
                to_state=TaskState.RUNNING,
                timestamp=datetime.utcnow(),
                reason="Task started execution",
            )
        )
        
        # Notify start callback
        if self._config.on_task_start:
            try:
                self._config.on_task_start(task)
            except Exception as e:
                logger = setup_logger(__name__)
                logger.error(f"Task start callback failed: {e}")
        
        # Schedule execution
        future = self._executor.submit(self._execute_task, task)
        
        with self._lock:
            self._active_futures[task.id] = future
        
        # Add callback for completion
        future.add_done_callback(lambda f: self._handle_completion(task, f))
    
    def cancel(self, task_id: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: Task ID to cancel
            
        Returns:
            True if cancelled
        """
        with self._lock:
            future = self._active_futures.get(task_id)
            if not future:
                return False
            
            # Cancel the future
            if future.cancel():
                task = self._active_tasks.get(task_id)
                if task:
                    task.state_history.add_transition(
                        StateTransition(
                            from_state=task.state,
                            to_state=TaskState.CANCELLED,
                            timestamp=datetime.utcnow(),
                            reason="Task cancelled by user",
                        )
                    )
                return True
            
            return False
    
    def get_active_tasks(self) -> List[ExecutionTask]:
        """Get all currently executing tasks."""
        with self._lock:
            return list(self._active_tasks.values())
    
    def get_active_count(self) -> int:
        """Get number of currently executing tasks."""
        with self._lock:
            return len(self._active_tasks)
    
    def get_stats(self) -> dict:
        """Get executor statistics."""
        with self._lock:
            avg_time = (
                self._total_execution_time / self._tasks_completed
                if self._tasks_completed > 0
                else 0.0
            )
            
            return {
                "active": len(self._active_tasks),
                "submitted": self._tasks_submitted,
                "completed": self._tasks_completed,
                "failed": self._tasks_failed,
                "avg_execution_time_ms": avg_time * 1000,
            }
    
    # ── Internal execution ���─────────────────────────────────────────────────────
    
    def _execute_task(self, task: ExecutionTask) -> None:
        """
        Execute a single task.
        
        This method runs in a worker thread.
        """
        start_time = time.time()
        
        try:
            # Check for cancellation
            if self._shutdown:
                raise Exception("Executor shutting down")
            
            # Execute the task's plan
            self._execute_plan(task)
            
            # Mark as success
            task.state_history.add_transition(
                StateTransition(
                    from_state=task.state,
                    to_state=TaskState.SUCCESS,
                    timestamp=datetime.utcnow(),
                    reason="Task completed successfully",
                )
            )
            
        except Exception as e:
            # Check if we can retry
            if self._can_retry(task):
                self._retry_task(task, e)
            else:
                task.state_history.add_transition(
                    StateTransition(
                        from_state=task.state,
                        to_state=TaskState.FAILED,
                        timestamp=datetime.utcnow(),
                        reason=str(e),
                    )
                )
                task.error = str(e)
        
        finally:
            execution_time = time.time() - start_time
            
            with self._lock:
                self._total_execution_time += execution_time
                if task.state == TaskState.SUCCESS:
                    self._tasks_completed += 1
                else:
                    self._tasks_failed += 1
                
                # Clean up
                self._active_tasks.pop(task.id, None)
                self._active_futures.pop(task.id, None)
            
            # Notify completion callback
            if self._config.on_task_complete:
                try:
                    self._config.on_task_complete(task, task.state == TaskState.SUCCESS)
                except Exception as e:
                    logger = setup_logger(__name__)
                    logger.error(f"Task completion callback failed: {e}")
    
    # ── Chat engine injection ──────────────────────────────────────────────────

    _chat_engine = None   # class-level slot; set by ExecutionEngine after init

    @classmethod
    def set_chat_engine(cls, engine) -> None:
        """Inject the AIChatEngine so executor can call it for AI generation."""
        cls._chat_engine = engine

    # ── Plan execution ─────────────────────────────────────────────────────────

    def _execute_plan(self, task: ExecutionTask) -> None:
        """
        Execute the task's plan by calling the AI chat engine for each step.

        Each step description is sent as a prompt.  Responses accumulate
        in task.results.  If no chat engine is available we still record
        a result so the UI sees progress.
        """
        logger = setup_logger(__name__)
        steps = task.task.plan if task.task.plan else [task.task.original_prompt]

        for index, step_text in enumerate(steps):
            if self._shutdown:
                raise Exception("Executor shutting down")

            step_start = time.time()
            output = ""
            success = True

            try:
                engine = self.__class__._chat_engine
                if engine:
                    # Build a focused prompt for this step
                    prompt = (
                        f"[Engineering task step {index + 1}/{len(steps)}]\n"
                        f"{step_text}\n\n"
                        "Provide a concise technical response or code change."
                    )

                    # Collect the full response via on_complete callback
                    result_holder: list = []

                    def _on_complete(response: str, _holder=result_holder):
                        _holder.append(response)

                    engine.send_message(
                        message=prompt,
                        model_id=engine.get_current_model(),
                        on_chunk=None,
                        on_complete=_on_complete,
                    )

                    # Wait (blocking — we are on a worker thread)
                    deadline = time.time() + 300   # 5 min max per step
                    while not result_holder and time.time() < deadline:
                        time.sleep(0.1)

                    output = result_holder[0] if result_holder else "[no response]"
                else:
                    # No engine available — record a placeholder so the UI
                    # still tracks progress correctly.
                    output = (
                        f"[Step {index + 1}] {step_text}\n"
                        "(AI engine not available — connect a provider in Settings)"
                    )

            except Exception as exc:
                success = False
                output = str(exc)
                logger.error(f"TaskExecutor step {index + 1} failed: {exc}", exc_info=True)

            duration_ms = (time.time() - step_start) * 1000

            result = ExecutionResult(
                step_index=index,
                step_text=step_text,
                success=success,
                output=output,
                duration_ms=duration_ms,
                attempt=1,
            )

            task.results.append(result)
            task.stats.steps_executed += 1

            if not success:
                raise Exception(f"Step {index + 1} failed: {output}")

        task.stats.total_duration_ms = (
            (time.time() - task.started_time.timestamp()) * 1000
            if task.started_time else 0.0
        )
    
    def _can_retry(self, task: ExecutionTask) -> bool:
        """Check if task can be retried."""
        config = task.config
        max_retries = config.max_retries if config.max_retries >= 0 else self._config.max_retries
        
        current_attempts = sum(1 for r in task.results if not r.success)
        return current_attempts < max_retries
    
    def _retry_task(self, task: ExecutionTask, error: Exception) -> None:
        """
        Schedule a retry for a failed task.
        """
        config = task.config
        strategy = config.retry_strategy if config.retry_strategy != RetryStrategy.NONE else self._config.retry_strategy
        base_delay = config.retry_delay if config.retry_delay else self._config.retry_delay
        
        # Calculate delay
        current_retries = task.stats.retry_count
        if strategy == RetryStrategy.EXPONENTIAL:
            delay = base_delay * (2 ** current_retries)
        elif strategy == RetryStrategy.JITTERED:
            import random
            delay = base_delay * (2 ** current_retries) * (0.5 + random.random())
        else:  # FIXED
            delay = base_delay
        
        task.stats.retry_count += 1
        
        # Re-queue the task
        task.state_history.add_transition(
            StateTransition(
                from_state=task.state,
                to_state=TaskState.SCHEDULED,
                timestamp=datetime.utcnow(),
                reason=f"Retry #{task.stats.retry_count}",
            )
        )
        
        # Schedule retry
        def schedule_retry():
            time.sleep(delay)
            # In production, re-enqueue to queue
            pass
        
        threading.Thread(target=schedule_retry, daemon=True).start()
    
    def _handle_completion(self, task: ExecutionTask, future: Future) -> None:
        """Handle task completion callback."""
        try:
            # Get any exception from the future
            exception = future.exception()
            
            if exception:
                # Already handled in _execute_task
                pass
            
        except Exception as e:
            logger = setup_logger(__name__)
            logger.error(f"Future completion handler error: {e}")


def setup_logger(name: str):
    """Simple logger setup for this module."""
    import logging
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ============================================================================
# SECTION: ai.verification.verification_task (ai/verification/verification_task.py)
# ============================================================================
"""
verification_task.py — Task dataclass for verification operations.

Represents a single verification run with all its components:
- Edit results to verify
- Verifier configurations
- Execution status and results
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional


class VerifierType(Enum):
    """Types of verifiers that can be run."""
    BUILD = "build"
    TEST = "test"
    FORMAT = "format"
    LINT = "lint"
    ANALYSIS = "analysis"


class VerifierStatus(Enum):
    """Status of a verifier execution."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass(frozen=True)
class VerifierConfig:
    """
    Configuration for a single verifier.

    Attributes:
        type:         Verifier type (build, test, format, lint, analysis)
        enabled:      Whether this verifier is active
        command:      Command to execute (can be None if auto-detected)
        options:      Additional command-line options
        timeout:      Max execution time in seconds
        retry_count:  Number of retries on failure
    """
    type:         VerifierType
    enabled:      bool = True
    command:      Optional[str] = None
    options:      List[str] = field(default_factory=list)
    timeout:      int = 60
    retry_count:  int = 0


@dataclass
class VerifierResult:
    """
    Result of a single verifier execution.

    Attributes:
        verifier_type:   Type of verifier that ran
        command:         Command that was executed
        status:          Success/failure status
        stdout:          Standard output from execution
        stderr:          Standard error from execution
        exit_code:       Process exit code
        duration_ms:     Execution time in milliseconds
        diagnostics:     List of structured diagnostics (warnings/errors)
        files_changed:   Number of files modified by this verifier
    """
    verifier_type:   VerifierType
    command:         str
    status:          VerifierStatus
    stdout:          str
    stderr:          str
    exit_code:       int
    duration_ms:     float
    diagnostics:     List[Dict[str, Any]] = field(default_factory=list)
    files_changed:   int = 0


@dataclass
class VerificationTask:
    """
    A complete verification task.

    Attributes:
        task_id:         Unique identifier for this task
        edit_request_id: ID of the edit being verified
        user_prompt:     Original user request
        files_modified:  List of modified file paths
        timestamp:       When the task was created
        status:          Overall task status
        config:          Verifier configurations
        results:         Results from each verifier
        retry_count:     Number of retry attempts
        max_retries:     Maximum allowed retries
        error_count:     Total number of errors across all verifiers
        risk_level:      Estimated risk of the changes (low/medium/high)
    """
    task_id:          str
    edit_request_id:  str
    user_prompt:      str
    files_modified:   List[str]
    timestamp:        datetime
    status:           str  # pending, running, completed, failed
    config:           Dict[VerifierType, VerifierConfig]
    results:          Dict[VerifierType, VerifierResult] = field(default_factory=dict)
    retry_count:      int = 0
    max_retries:      int = 3
    error_count:      int = 0
    risk_level:       str = "low"

    @classmethod
    def create(
        cls,
        edit_request_id: str,
        user_prompt: str,
        files_modified: List[str],
        config: Optional[Dict[VerifierType, VerifierConfig]] = None,
        max_retries: int = 3,
    ) -> VerificationTask:
        """Create a new verification task."""
        return cls(
            task_id=f"ver_{uuid.uuid4().hex[:12]}",
            edit_request_id=edit_request_id,
            user_prompt=user_prompt,
            files_modified=files_modified,
            timestamp=datetime.now(),
            status="pending",
            config=config or {},
            results={},
            retry_count=0,
            max_retries=max_retries,
            error_count=0,
            risk_level="low",
        )

    def add_result(self, result: VerifierResult) -> None:
        """Add a verifier result to this task."""
        self.results[result.verifier_type] = result
        if result.status == VerifierStatus.FAILED:
            self.error_count += 1

    def is_complete(self) -> bool:
        """Check if all enabled verifiers have completed."""
        for vtype, result in self.results.items():
            if self.config.get(vtype, VerifierConfig(type=vtype)).enabled:
                if result.status not in (VerifierStatus.PASSED, VerifierStatus.FAILED):
                    return False
        return True

    def get_overall_status(self) -> str:
        """Determine overall verification status."""
        if not self.results:
            return "pending"

        all_passed = all(
            r.status == VerifierStatus.PASSED
            for r in self.results.values()
            if self.config.get(r.verifier_type, VerifierConfig(type=r.verifier_type)).enabled
        )
        return "success" if all_passed else "failed"

    def get_failed_verifiers(self) -> List[VerifierType]:
        """Return list of verifier types that failed."""
        return [
            vtype for vtype, result in self.results.items()
            if self.config.get(vtype, VerifierConfig(type=vtype)).enabled
            and result.status == VerifierStatus.FAILED
        ]

    def get_passed_verifiers(self) -> List[VerifierType]:
        """Return list of verifier types that passed."""
        return [
            vtype for vtype, result in self.results.items()
            if self.config.get(vtype, VerifierConfig(type=vtype)).enabled
            and result.status == VerifierStatus.PASSED
        ]

    def needs_retry(self) -> bool:
        """Check if this task should be retried."""
        return (
            self.retry_count < self.max_retries
            and self.get_overall_status() == "failed"
        )


def create_default_task_config() -> Dict[VerifierType, VerifierConfig]:
    """Create default verifier configurations."""
    return {
        VerifierType.FORMAT: VerifierConfig(
            type=VerifierType.FORMAT,
            enabled=True,
            timeout=30,
            retry_count=0,
        ),
        VerifierType.LINT: VerifierConfig(
            type=VerifierType.LINT,
            enabled=True,
            timeout=60,
            retry_count=0,
        ),
        VerifierType.BUILD: VerifierConfig(
            type=VerifierType.BUILD,
            enabled=True,
            timeout=120,
            retry_count=1,
        ),
        VerifierType.TEST: VerifierConfig(
            type=VerifierType.TEST,
            enabled=True,
            timeout=180,
            retry_count=0,
        ),
        VerifierType.ANALYSIS: VerifierConfig(
            type=VerifierType.ANALYSIS,
            enabled=False,
            timeout=60,
            retry_count=0,
        ),
    }

# ============================================================================
# SECTION: ai.verification.verification_report (ai/verification/verification_report.py)
# ============================================================================
"""
verification_report.py — Generate verification reports.

Generates comprehensive reports including:
  - Build status
  - Test results
  - Warnings
  - Errors
  - Execution time
  - Retries
  - Files changed
  - Risk level
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from ai.verification.verification_task import VerificationTask, VerifierType, VerifierStatus


@dataclass
class ReportSection:
    """A section of the verification report."""
    title:    str
    content:  List[str]
    status:   str  # success, warning, error, info


class VerificationReportGenerator:
    """
    Generates human-readable verification reports.

    Usage:
        generator = VerificationReportGenerator()
        report = generator.generate(task, execution_time_ms)
    """

    def __init__(self) -> None:
        self._max_lines = 100  # Limit output lines

    # ── Public API ─────────────────────────────────────────────────────────

    def generate(
        self,
        task: VerificationTask,
        execution_time_ms: float,
    ) -> str:
        """
        Generate a verification report.

        Args:
            task:             The verification task.
            execution_time_ms: Total execution time in milliseconds.

        Returns:
            Human-readable report string.
        """
        sections = []

        # Header
        sections.append(self._generate_header(task, execution_time_ms))

        # Per-verifier results
        sections.append(self._generate_verifier_summary(task))

        # Verifier details
        for vtype, result in task.results.items():
            sections.append(self._generate_verifier_detail(vtype, result))

        # Summary
        sections.append(self._generate_summary(task, execution_time_ms))

        return "\n\n".join(sections)

    # ── Report sections ─────────────────────────────────────────────────────

    def _generate_header(
        self,
        task: VerificationTask,
        execution_time_ms: float,
    ) -> str:
        """Generate report header."""
        status_emoji = "✅" if task.get_overall_status() == "success" else "❌"
        status_text = "VERIFIED" if task.get_overall_status() == "success" else "FAILED"

        lines = [
            f"{status_emoji} {status_text} Verification Report",
            f"Task ID: {task.task_id}",
            f"Edit Request: {task.edit_request_id}",
            f"Prompt: {task.user_prompt[:80]}{'...' if len(task.user_prompt) > 80 else ''}",
            f"Files Modified: {len(task.files_modified)}",
            f"Executed In: {execution_time_ms:.0f}ms",
            f"Retry Count: {task.retry_count}/{task.max_retries}",
        ]

        return "\n".join(lines)

    def _generate_verifier_summary(self, task: VerificationTask) -> str:
        """Generate summary of all verifiers."""
        lines = [
            "## Verifier Summary",
            "",
        ]

        passed = []
        failed = []
        skipped = []
        errored = []

        for vtype in [VerifierType.FORMAT, VerifierType.LINT, VerifierType.BUILD, VerifierType.TEST]:
            result = task.results.get(vtype)
            if not result:
                skipped.append(vtype)
                continue

            if result.status == VerifierStatus.PASSED:
                passed.append(vtype)
            elif result.status == VerifierStatus.FAILED:
                failed.append(vtype)
            elif result.status == VerifierStatus.ERROR:
                errored.append(vtype)
            else:
                skipped.append(vtype)

        # Passed
        if passed:
            lines.append(f"✅ **Passed** ({len(passed)}): {', '.join(v.value for v in passed)}")
        else:
            lines.append("✅ **Passed**: None")

        # Failed
        if failed:
            lines.append(f"❌ **Failed** ({len(failed)}): {', '.join(v.value for v in failed)}")
        else:
            lines.append("❌ **Failed**: None")

        # Skipped
        if skipped:
            lines.append(f"⏭️ **Skipped** ({len(skipped)}): {', '.join(v.value for v in skipped)}")
        else:
            lines.append("⏭️ **Skipped**: None")

        # Errored
        if errored:
            lines.append(f"🔥 **Errored** ({len(errored)}): {', '.join(v.value for v in errored)}")
        else:
            lines.append("🔥 **Errored**: None")

        return "\n".join(lines)

    def _generate_verifier_detail(
        self,
        vtype: VerifierType,
        result,
    ) -> str:
        """Generate detailed output for a verifier."""
        if not result:
            return f"## {vtype.value.upper()}\nNot executed"

        status_emoji = {
            VerifierStatus.PASSED: "✅",
            VerifierStatus.FAILED: "❌",
            VerifierStatus.ERROR: "🔥",
            VerifierStatus.SKIPPED: "⏭️",
            VerifierStatus.TIMEOUT: "⏱️",
        }.get(result.status, "❓")

        lines = [
            f"## {status_emoji} {vtype.value.upper()}",
            "",
            f"Command: `{result.command}`",
            f"Duration: {result.duration_ms:.0f}ms",
            f"Exit Code: {result.exit_code}",
        ]

        # Output (truncated)
        if result.stdout:
            stdout_lines = result.stdout.splitlines()[:self._max_lines]
            lines.append("")
            lines.append("### Output:")
            lines.append("```")
            lines.extend(stdout_lines[:20])  # Limit stdout lines
            if len(stdout_lines) > 20:
                lines.append(f"... ({len(stdout_lines) - 20} more lines) ...")
            lines.append("```")

        if result.stderr:
            stderr_lines = result.stderr.splitlines()[:self._max_lines]
            lines.append("")
            lines.append("### Errors/Warnings:")
            lines.append("```")
            lines.extend(stderr_lines[:20])
            if len(stderr_lines) > 20:
                lines.append(f"... ({len(stderr_lines) - 20} more lines) ...")
            lines.append("```")

        return "\n".join(lines)

    def _generate_summary(
        self,
        task: VerificationTask,
        execution_time_ms: float,
    ) -> str:
        """Generate final summary."""
        status = task.get_overall_status()
        risk = self._determine_risk(task)

        lines = [
            "",
            "## Summary",
            "",
            f"Status: **{status.upper()}**",
            f"Risk Level: **{risk.upper()}**",
            f"Execution Time: {execution_time_ms:.0f}ms",
            f"Total Errors: {task.error_count}",
            f"Files Changed: {len(task.files_modified)}",
        ]

        if task.get_failed_verifiers():
            lines.append("")
            lines.append("⚠️  **Failed verifiers:**")
            for vtype in task.get_failed_verifiers():
                lines.append(f"   - {vtype.value}")

        if task.get_passed_verifiers():
            lines.append("")
            lines.append("✅ **Passed verifiers:**")
            for vtype in task.get_passed_verifiers():
                lines.append(f"   - {vtype.value}")

        return "\n".join(lines)

    def _determine_risk(self, task: VerificationTask) -> str:
        """Determine risk level based on verification results."""
        # Check for critical errors
        for result in task.results.values():
            if result.status == VerifierStatus.ERROR:
                return "high"

        failed_count = len(task.get_failed_verifiers())

        if failed_count == 0:
            return "low"
        elif failed_count == 1:
            return "medium"
        else:
            return "high"


# Convenience function

def generate_report(
    task: VerificationTask,
    execution_time_ms: float,
) -> str:
    """Convenience function to generate report."""
    generator = VerificationReportGenerator()
    return generator.generate(task, execution_time_ms)

# ============================================================================
# SECTION: ai.verification.error_classifier (ai/verification/error_classifier.py)
# ============================================================================
"""
error_classifier.py — Categorize and classify verification errors.

Categorizes errors into types:
  - Syntax Error
  - Import Error
  - Build Failure
  - Test Failure
  - Dependency Failure
  - Formatting Error
  - Runtime Error
  - Unknown

Assigns severity levels:
  - critical: blocks progress
  - high: must fix before merge
  - medium: should fix soon
  - low: nice to fix
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class ErrorType(Enum):
    """Types of verification errors."""
    SYNTAX = "syntax"
    IMPORT = "import"
    BUILD = "build"
    TEST = "test"
    DEPENDENCY = "dependency"
    FORMATTING = "formatting"
    LINT = "lint"
    RUNTIME = "runtime"
    UNKNOWN = "unknown"


class Severity(Enum):
    """Severity levels for errors."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ErrorClassification:
    """
    Classification of a single error.

    Attributes:
        error_type:  Categorized error type
        severity:    Impact level
        message:     Original error message
        file:        File path where error occurred (if applicable)
        line:        Line number where error occurred (if applicable)
        suggestion:  Suggested fix (if known)
    """
    error_type:  ErrorType
    severity:    Severity
    message:     str
    file:        Optional[str] = None
    line:        Optional[int] = None
    suggestion:  Optional[str] = None


class ErrorClassifier:
    """
    Classifies errors from verification runs.

    Usage:
        classifier = ErrorClassifier()
        classification = classifier.classify(error_message, file_path)
    """

    def __init__(self) -> None:
        self._patterns = self._build_patterns()
        self._suggestions = self._build_suggestions()

    # ── Public API ─────────────────────────────────────────────────────────

    def classify(
        self,
        error_message: str,
        file_path: Optional[str] = None,
    ) -> ErrorClassification:
        """
        Classify an error message.

        Args:
            error_message: The error message to classify.
            file_path:     Optional file path where error occurred.

        Returns:
            ErrorClassification with type, severity, and suggestion.
        """
        error_lower = error_message.lower()

        # Check each pattern
        for error_type, (pattern, severity, suggestion_key) in self._patterns.items():
            if re.search(pattern, error_lower):
                return ErrorClassification(
                    error_type=error_type,
                    severity=severity,
                    message=error_message,
                    file=file_path,
                    line=self._extract_line_number(error_message),
                    suggestion=self._suggestions.get(suggestion_key, None),
                )

        # Default to unknown
        return ErrorClassification(
            error_type=ErrorType.UNKNOWN,
            severity=Severity.MEDIUM,
            message=error_message,
            file=file_path,
            line=self._extract_line_number(error_message),
            suggestion="Review the error message and check documentation.",
        )

    def classify_batch(
        self,
        output: str,
        file_path: Optional[str] = None,
    ) -> List[ErrorClassification]:
        """
        Classify all errors in a multi-line output.

        Args:
            output:      Multi-line output containing errors.
            file_path:   Optional file path where errors occurred.

        Returns:
            List of classifications for each error found.
        """
        classifications = []
        lines = output.splitlines()

        for line in lines:
            line = line.strip()
            if not line:
                continue

            classification = self.classify(line, file_path)
            classifications.append(classification)

        return classifications

    # ── Pattern building ────────────────────────────────────────────────────

    def _build_patterns(self) -> Dict[ErrorType, tuple]:
        """Build regex patterns for error classification."""
        return {
            ErrorType.SYNTAX: (
                r"(\bsyntax\s+error|unexpected\s+\w+|invalid\s+syntax)",
                Severity.HIGH,
                "syntax_error",
            ),
            ErrorType.IMPORT: (
                r"(\bimport\s+error|module\s+not\s+found|cannot\s+import)",
                Severity.HIGH,
                "import_error",
            ),
            ErrorType.BUILD: (
                r"(\bbuild\s+failed|compile\s+error|link\s+error)",
                Severity.CRITICAL,
                "build_error",
            ),
            ErrorType.TEST: (
                r"(\btest\s+failed|assertion\s+error|test\s+error)",
                Severity.MEDIUM,
                "test_error",
            ),
            ErrorType.DEPENDENCY: (
                r"(\bdependency\s+error|package\s+not\s+found|pip\s+install)",
                Severity.HIGH,
                "dependency_error",
            ),
            ErrorType.FORMATTING: (
                r"(\bformat\s+error|black|prettier|clang-format)",
                Severity.LOW,
                "format_error",
            ),
            ErrorType.LINT: (
                r"(\blint\s+error|flake8|ruff|pylint|eslint)",
                Severity.MEDIUM,
                "lint_error",
            ),
            ErrorType.RUNTIME: (
                r"(\bruntime\s+error|exception|traceback|crash)",
                Severity.CRITICAL,
                "runtime_error",
            ),
        }

    def _build_suggestions(self) -> Dict[str, Optional[str]]:
        """Build error-specific suggestions."""
        return {
            "syntax_error": "Check for missing colons, parentheses, or quotes.",
            "import_error": "Ensure the module is installed and in the Python path.",
            "build_error": "Check build configuration files and dependencies.",
            "test_error": "Review test expectations and implementation.",
            "dependency_error": "Update requirements.txt or package.json.",
            "format_error": "Run the formatter (black, prettier, etc.).",
            "lint_error": "Fix linting issues or update lint config.",
            "runtime_error": "Check input data and exception handling.",
        }

    def _extract_line_number(self, message: str) -> Optional[int]:
        """Extract line number from error message if present."""
        patterns = [
            r":(\d+):",        # :123: format
            r"line\s+(\d+)",   # line 123 format
            r"at\s+(\d+)",     # at 123 format
        ]

        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue

        return None

    def get_severity_color(self, severity: Severity) -> str:
        """Get color code for severity level."""
        return {
            Severity.CRITICAL: "#EF4444",  # Red
            Severity.HIGH: "#F97316",      # Orange
            Severity.MEDIUM: "#F59E0B",    # Amber
            Severity.LOW: "#10B981",       # Green
        }.get(severity, "#52525C")


# Convenience functions

def classify_error(
    error_message: str,
    file_path: Optional[str] = None,
) -> ErrorClassification:
    """Convenience function to classify an error."""
    classifier = ErrorClassifier()
    return classifier.classify(error_message, file_path)


def classify_batch(output: str, file_path: Optional[str] = None) -> List[ErrorClassification]:
    """Convenience function to classify multiple errors."""
    classifier = ErrorClassifier()
    return classifier.classify_batch(output, file_path)

# ============================================================================
# SECTION: ai.verification.success_validator (ai/verification/success_validator.py)
# ============================================================================
"""
success_validator.py — Determine if verification is successful.

Only marks task complete if ALL conditions are met:
  - Formatting passed
  - Lint passed
  - Build passed
  - Tests passed
  - No critical errors remain
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from ai.verification.verification_task import (
    VerificationTask, VerifierType, VerifierStatus, VerifierConfig
)


@dataclass
class ValidationResult:
    """
    Result of success validation.

    Attributes:
        is_success:        True if task passed all checks
        passed_verifiers:  List of verifier types that passed
        failed_verifiers:  List of verifier types that failed
        missing_verifiers: List of verifier types that weren't run
        errors:            List of error messages
        warnings:          List of warning messages
    """
    is_success:        bool
    passed_verifiers:  List[VerifierType]
    failed_verifiers:  List[VerifierType]
    missing_verifiers: List[VerifierType]
    errors:            List[str]
    warnings:          List[str]


class SuccessValidator:
    """
    Validates that all verification checks have passed.

    Usage:
        validator = SuccessValidator()
        result = validator.validate(task)
    """

    def __init__(self) -> None:
        # Verifiers that must pass for success
        self._required_verifiers = [
            VerifierType.FORMAT,
            VerifierType.LINT,
            VerifierType.BUILD,
            VerifierType.TEST,
        ]

    # ── Public API ─────────────────────────────────────────────────────────

    def validate(
        self,
        task: VerificationTask,
    ) -> ValidationResult:
        """
        Validate that a verification task succeeded.

        Args:
            task: The verification task to validate.

        Returns:
            ValidationResult with success status and details.
        """
        errors: List[str] = []
        warnings: List[str] = []
        passed: List[VerifierType] = []
        failed: List[VerifierType] = []
        missing: List[VerifierType] = []

        # Check each required verifier
        for vtype in self._required_verifiers:
            config = task.config.get(vtype, VerifierConfig(type=vtype, enabled=True))
            result = task.results.get(vtype)

            if not config.enabled:
                # Not enabled, skip
                continue

            if not result:
                missing.append(vtype)
                errors.append(f"Missing result for {vtype.value} verifier")
                continue

            if result.status == VerifierStatus.PASSED:
                passed.append(vtype)
            else:
                failed.append(vtype)
                errors.append(
                    f"{vtype.value} failed: {result.stderr[:100] if result.stderr else 'unknown error'}"
                )

        # Check for critical errors
        for vtype, result in task.results.items():
            if result.status == VerifierStatus.ERROR:
                errors.append(f"Critical error in {vtype.value}: {result.stderr}")

        # Determine overall success
        is_success = (
            len(failed) == 0
            and len(errors) == 0
            and len(passed) > 0  # At least one verifier must have run
        )

        return ValidationResult(
            is_success=is_success,
            passed_verifiers=passed,
            failed_verifiers=failed,
            missing_verifiers=missing,
            errors=errors,
            warnings=warnings,
        )

    def validate_with_optional(
        self,
        task: VerificationTask,
        optional_verifiers: List[VerifierType] = None,
    ) -> ValidationResult:
        """
        Validate with additional optional verifiers.

        Args:
            task:             The verification task.
            optional_verifiers: Additional verifiers to include.

        Returns:
            ValidationResult with success status.
        """
        all_required = self._required_verifiers + (optional_verifiers or [])
        # We need to update task config to mark these as required
        # For simplicity, just call the main validate method
        return self.validate(task)

    def can_proceed(self, task: VerificationTask) -> bool:
        """
        Quick check if task can proceed to the next stage.

        Args:
            task: The verification task.

        Returns:
            True if task passed all required checks.
        """
        result = self.validate(task)
        return result.is_success

    def get_failure_reason(self, task: VerificationTask) -> str:
        """
        Get human-readable reason for failure.

        Args:
            task: The verification task.

        Returns:
            Description of why verification failed.
        """
        result = self.validate(task)

        if result.is_success:
            return "Verification succeeded"

        if result.errors:
            return "; ".join(result.errors[:3])  # Limit to first 3 errors

        if result.missing_verifiers:
            return f"Missing verifiers: {', '.join(v.value for v in result.missing_verifiers)}"

        if result.failed_verifiers:
            return f"Failed verifiers: {', '.join(v.value for v in result.failed_verifiers)}"

        return "Unknown verification failure"


# Convenience functions

def validate_success(task: VerificationTask) -> ValidationResult:
    """Convenience function to validate task success."""
    validator = SuccessValidator()
    return validator.validate(task)


def can_proceed(task: VerificationTask) -> bool:
    """Convenience function to check if task can proceed."""
    validator = SuccessValidator()
    return validator.can_proceed(task)

# ============================================================================
# SECTION: ai.verification.retry_manager (ai/verification/retry_manager.py)
# ============================================================================
"""
retry_manager.py — Retry logic for failed verifications.

Handles retry behavior:
  - Generate retry tasks with exponential backoff
  - Limit maximum retry attempts
  - Escalate when maximum attempts reached
"""

import time
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from core.logger import setup_logger

from ai.verification.verification_task import VerificationTask, VerifierType, VerifierStatus

logger = setup_logger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries:      int = 3
    base_delay_ms:    int = 1000    # 1 second
    backoff_multiplier: float = 2.0  # Exponential backoff
    max_delay_ms:     int = 30000   # 30 seconds
    retry_on:         List[VerifierStatus] = None

    def __post_init__(self):
        if self.retry_on is None:
            self.retry_on = [VerifierStatus.FAILED, VerifierStatus.ERROR, VerifierStatus.TIMEOUT]


class RetryManager:
    """
    Manages retry logic for verification tasks.

    Features:
      - Exponential backoff between retries
      - Configurable retry limits
      - Retry history tracking
      - Escalation on failure

    Usage:
        manager = RetryManager(max_retries=3)
        should_retry, delay = manager.should_retry(task)
    """

    def __init__(self, config: Optional[RetryConfig] = None) -> None:
        self._config = config or RetryConfig()
        self._lock = threading.Lock()
        self._retry_history: Dict[str, List[datetime]] = {}
        logger.debug(f"RetryManager initialized (max_retries={self._config.max_retries}).")

    # ── Public API ─────────────────────────────────────────────────────────

    def should_retry(self, task: VerificationTask) -> tuple[bool, float]:
        """
        Determine if a task should be retried.

        Args:
            task: The verification task to check.

        Returns:
            Tuple of (should_retry, delay_ms).
        """
        with self._lock:
            # Check retry count
            if task.retry_count >= self._config.max_retries:
                logger.info(
                    f"RetryManager: max retries reached for task {task.task_id[:8]}"
                )
                return False, 0.0

            # Check if any verifiers failed
            failed_verifiers = task.get_failed_verifiers()
            if not failed_verifiers:
                return False, 0.0

            # Check if failure type should be retried
            should = False
            for vtype in failed_verifiers:
                result = task.results.get(vtype)
                if result and result.status in self._config.retry_on:
                    should = True
                    break

            if not should:
                return False, 0.0

            # Calculate delay with exponential backoff
            delay_ms = self._calculate_delay(task.retry_count)

            logger.info(
                f"RetryManager: task {task.task_id[:8]} should retry "
                f"in {delay_ms:.0f}ms (attempt {task.retry_count + 1}/{self._config.max_retries})"
            )
            return True, delay_ms

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given retry attempt.

        Args:
            attempt: The retry attempt number (0-indexed).

        Returns:
            Delay in milliseconds.
        """
        delay = self._config.base_delay_ms * (
            self._config.backoff_multiplier ** attempt
        )
        return min(delay, self._config.max_delay_ms)

    def record_retry(self, task_id: str) -> None:
        """Record a retry attempt for tracking."""
        with self._lock:
            if task_id not in self._retry_history:
                self._retry_history[task_id] = []
            self._retry_history[task_id].append(datetime.now())

    def get_retry_history(self, task_id: str) -> List[datetime]:
        """Get retry history for a task."""
        return self._retry_history.get(task_id, [])

    def reset_history(self, task_id: Optional[str] = None) -> None:
        """Reset retry history."""
        with self._lock:
            if task_id:
                self._retry_history.pop(task_id, None)
            else:
                self._retry_history.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Return retry manager statistics."""
        with self._lock:
            total_retries = sum(len(history) for history in self._retry_history.values())
            return {
                "max_retries": self._config.max_retries,
                "base_delay_ms": self._config.base_delay_ms,
                "backoff_multiplier": self._config.backoff_multiplier,
                "max_delay_ms": self._config.max_delay_ms,
                "retry_on": [s.value for s in self._config.retry_on],
                "total_retries": total_retries,
                "tracked_tasks": len(self._retry_history),
            }

    # ── Retry task generation ───────────────────────────────────────────────

    def create_retry_task(
        self,
        original: VerificationTask,
        new_task_id: Optional[str] = None,
    ) -> VerificationTask:
        """
        Create a new task for retry.

        Args:
            original:    The original verification task.
            new_task_id: Optional new task ID (auto-generated if not provided).

        Returns:
            New VerificationTask for retry.
        """
        retry_id = new_task_id or f"ver_{original.task_id[:8]}_retry{original.retry_count + 1}"

        # Create new task with same parameters
        new_task = VerificationTask.create(
            edit_request_id=original.edit_request_id,
            user_prompt=original.user_prompt,
            files_modified=original.files_modified,
            config=original.config,
            max_retries=self._config.max_retries,
        )
        new_task.task_id = retry_id
        new_task.retry_count = original.retry_count + 1

        logger.info(
            f"RetryManager: created retry task {retry_id[:8]} "
            f"for original {original.task_id[:8]}"
        )
        return new_task

    # ── Escalation handling ─────────────────────────────────────────────────

    def should_escalate(self, task: VerificationTask) -> bool:
        """
        Check if a failed task should be escalated (e.g., to human review).

        Args:
            task: The verification task to check.

        Returns:
            True if escalation is recommended.
        """
        # Escalate if max retries reached
        if task.retry_count >= self._config.max_retries:
            return True

        # Escalate if critical errors persist
        for result in task.results.values():
            if result.status == VerifierStatus.ERROR:
                return True

        return False

    def get_escalation_message(self, task: VerificationTask) -> str:
        """Generate escalation message for a task."""
        messages = []

        if task.retry_count >= self._config.max_retries:
            messages.append(f"Max retries ({task.retry_count}) reached")

        failed_verifiers = task.get_failed_verifiers()
        if failed_verifiers:
            messages.append(f"Failed verifiers: {', '.join(v.value for v in failed_verifiers)}")

        return "; ".join(messages) if messages else "Unknown failure"


# Convenience function

def should_retry_task(
    task: VerificationTask,
    max_retries: int = 3,
) -> tuple[bool, float]:
    """Convenience function to check if task should be retried."""
    manager = RetryManager(RetryConfig(max_retries=max_retries))
    return manager.should_retry(task)

# ============================================================================
# SECTION: ai.verification.build_runner (ai/verification/build_runner.py)
# ============================================================================
"""
build_runner.py — Automated build system detection and execution.

Detects the project's build system and executes it safely:
  - Python: pip install -e ., python setup.py build
  - Node.js: npm install, npm run build
  - Flutter: flutter pub get, flutter build
  - Rust: cargo build
  - Go: go build ./...
  - Java/CMake: cmake, make
"""

import subprocess
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.logger import setup_logger

from ai.verification.verification_task import VerificationTask, VerifierResult, VerifierStatus, VerifierType

logger = setup_logger(__name__)


@dataclass
class BuildSystem:
    """Detected build system information."""
    name:       str
    command:    str
    args:       List[str]
    lock_file:  str
    output_dir: str


class BuildRunner:
    """
    Runs automated builds for different project types.

    Features:
      - Automatic build system detection
      - Safe subprocess execution with timeout
      - stdout/stderr capture
      - Build status reporting

    Usage:
        runner = BuildRunner(project_root)
        result = runner.run(task, timeout=120)
    """

    def __init__(self, project_root: str) -> None:
        self._root = Path(project_root)
        self._detected: Optional[BuildSystem] = None
        logger.debug(f"BuildRunner initialized (root='{self._root.name}').")

    # ── Public API ─────────────────────────────────────────────────────────

    def run(
        self,
        task: VerificationTask,
        timeout: int = 120,
    ) -> VerifierResult:
        """
        Run the build for the project.

        Args:
            task:    The verification task containing project info.
            timeout: Max execution time in seconds.

        Returns:
            VerifierResult with build outcome.
        """
        build_system = self._detect_build_system()
        if not build_system:
            logger.info("BuildRunner: no build system detected, skipping build")
            return VerifierResult(
                verifier_type=VerifierType.BUILD,
                command="none",
                status=VerifierStatus.SKIPPED,
                stdout="No build system detected",
                stderr="",
                exit_code=0,
                duration_ms=0.0,
                diagnostics=[],
                files_changed=0,
            )

        self._detected = build_system
        logger.info(f"BuildRunner: detected {build_system.name} build system")

        start = datetime.now()
        command = [build_system.command] + build_system.args

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=str(self._root),
                timeout=timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            elapsed = (datetime.now() - start).total_seconds() * 1000

            # Classify result
            diagnostics = self._classify_diagnostics(result.stdout + result.stderr)

            status = (
                VerifierStatus.PASSED
                if result.returncode == 0
                else VerifierStatus.FAILED
            )

            return VerifierResult(
                verifier_type=VerifierType.BUILD,
                command=" ".join(command),
                status=status,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                duration_ms=round(elapsed, 1),
                diagnostics=diagnostics,
                files_changed=self._count_build_artifacts(build_system.output_dir),
            )

        except subprocess.TimeoutExpired:
            elapsed = (datetime.now() - start).total_seconds() * 1000
            return VerifierResult(
                verifier_type=VerifierType.BUILD,
                command=" ".join(command),
                status=VerifierStatus.TIMEOUT,
                stdout="",
                stderr=f"Build timeout after {timeout}s",
                exit_code=124,
                duration_ms=round(elapsed, 1),
                diagnostics=[],
                files_changed=0,
            )
        except Exception as exc:
            elapsed = (datetime.now() - start).total_seconds() * 1000
            return VerifierResult(
                verifier_type=VerifierType.BUILD,
                command=" ".join(command),
                status=VerifierStatus.ERROR,
                stdout="",
                stderr=str(exc),
                exit_code=1,
                duration_ms=round(elapsed, 1),
                diagnostics=[],
                files_changed=0,
            )

    # ── Build system detection ──────────────────────────────────────────────

    def _detect_build_system(self) -> Optional[BuildSystem]:
        """Detect the project's build system by scanning for configuration files."""
        # Check each build system in priority order
        checks = [
            ("CMake", self._check_cmake),
            ("Rust", self._check_rust),
            ("Go", self._check_go),
            ("Python", self._check_python),
            ("Node.js", self._check_node),
            ("Flutter", self._check_flutter),
            ("Java/CMake", self._check_java_cmake),
            ("Java/Maven", self._check_java_maven),
            ("Java/Gradle", self._check_java_gradle),
        ]

        for name, check_func in checks:
            result = check_func()
            if result:
                logger.debug(f"BuildRunner: detected {name}")
                return result

        return None

    def _check_cmake(self) -> Optional[BuildSystem]:
        """Check for CMake build system."""
        if (self._root / "CMakeLists.txt").exists():
            return BuildSystem(
                name="CMake",
                command="cmake",
                args=["-B", "build", "-S", "."],
                lock_file="CMakeLists.txt",
                output_dir="build",
            )
        return None

    def _check_rust(self) -> Optional[BuildSystem]:
        """Check for Rust/Cargo build system."""
        if (self._root / "Cargo.toml").exists():
            return BuildSystem(
                name="Rust",
                command="cargo",
                args=["build"],
                lock_file="Cargo.toml",
                output_dir="target",
            )
        return None

    def _check_go(self) -> Optional[BuildSystem]:
        """Check for Go build system."""
        if (self._root / "go.mod").exists():
            return BuildSystem(
                name="Go",
                command="go",
                args=["build", "./..."],
                lock_file="go.mod",
                output_dir="",
            )
        return None

    def _check_python(self) -> Optional[BuildSystem]:
        """Check for Python build system."""
        if (self._root / "setup.py").exists() or (self._root / "pyproject.toml").exists():
            return BuildSystem(
                name="Python",
                command="python",
                args=["setup.py", "build"],
                lock_file="setup.py",
                output_dir="build",
            )
        return None

    def _check_node(self) -> Optional[BuildSystem]:
        """Check for Node.js build system."""
        if (self._root / "package.json").exists():
            # Check for build script
            package_json = self._root / "package.json"
            if package_json.exists():
                import json
                try:
                    data = json.loads(package_json.read_text())
                    if "scripts" in data and "build" in data["scripts"]:
                        return BuildSystem(
                            name="Node.js",
                            command="npm",
                            args=["run", "build"],
                            lock_file="package.json",
                            output_dir="dist",
                        )
                except json.JSONDecodeError:
                    pass
        return None

    def _check_flutter(self) -> Optional[BuildSystem]:
        """Check for Flutter build system."""
        if (self._root / "pubspec.yaml").exists():
            return BuildSystem(
                name="Flutter",
                command="flutter",
                args=["build"],
                lock_file="pubspec.yaml",
                output_dir="build",
            )
        return None

    def _check_java_cmake(self) -> Optional[BuildSystem]:
        """Check for Java/CMake build system."""
        if (self._root / "CMakeLists.txt").exists() and self._has_java_files():
            return BuildSystem(
                name="Java/CMake",
                command="cmake",
                args=["-B", "build", "-S", "."],
                lock_file="CMakeLists.txt",
                output_dir="build",
            )
        return None

    def _check_java_maven(self) -> Optional[BuildSystem]:
        """Check for Java/Maven build system."""
        if (self._root / "pom.xml").exists():
            return BuildSystem(
                name="Maven",
                command="mvn",
                args=["compile"],
                lock_file="pom.xml",
                output_dir="target",
            )
        return None

    def _check_java_gradle(self) -> Optional[BuildSystem]:
        """Check for Java/Gradle build system."""
        if (self._root / "build.gradle").exists() or (self._root / "build.gradle.kts").exists():
            return BuildSystem(
                name="Gradle",
                command="gradle",
                args=["build"],
                lock_file="build.gradle",
                output_dir="build",
            )
        return None

    def _has_java_files(self) -> bool:
        """Check if project has Java source files."""
        return bool(list(self._root.rglob("*.java")))

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _classify_diagnostics(self, output: str) -> List[Dict]:
        """Parse build output for diagnostics."""
        diagnostics = []
        lines = output.splitlines()

        for i, line in enumerate(lines):
            line_lower = line.lower()
            if "error" in line_lower or "failed" in line_lower:
                diagnostics.append({
                    "severity": "error",
                    "message": line.strip(),
                    "line": i + 1,
                    "source": "build",
                })
            elif "warning" in line_lower:
                diagnostics.append({
                    "severity": "warning",
                    "message": line.strip(),
                    "line": i + 1,
                    "source": "build",
                })

        return diagnostics

    def _count_build_artifacts(self, output_dir: str) -> int:
        """Count files in build output directory."""
        if not output_dir:
            return 0

        dir_path = self._root / output_dir
        if not dir_path.exists():
            return 0

        try:
            return sum(1 for _ in dir_path.rglob("*") if _.is_file())
        except OSError:
            return 0

# ============================================================================
# SECTION: ai.verification.test_runner (ai/verification/test_runner.py)
# ============================================================================
"""
test_runner.py — Automated test framework detection and execution.

Detects testing frameworks and runs tests:
  - Python: pytest, unittest
  - Node.js: jest, mocha
  - Flutter: flutter test
  - Rust: cargo test
  - Java: mvn test, gradle test
"""

import subprocess
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.logger import setup_logger

from ai.verification.verification_task import VerificationTask, VerifierResult, VerifierStatus, VerifierType

logger = setup_logger(__name__)


@dataclass
class TestFramework:
    """Detected test framework information."""
    name:         str
    command:      str
    args:         List[str]
    config_file:  str


class TestRunner:
    """
    Runs automated tests for different frameworks.

    Features:
      - Automatic test framework detection
      - Test summary parsing (passed/failed/skipped)
      - Timeout handling
      - Test result reporting

    Usage:
        runner = TestRunner(project_root)
        result = runner.run(task, timeout=180)
    """

    def __init__(self, project_root: str) -> None:
        self._root = Path(project_root)
        self._detected: Optional[TestFramework] = None
        logger.debug(f"TestRunner initialized (root='{self._root.name}').")

    # ── Public API ─────────────────────────────────────────────────────────

    def run(
        self,
        task: VerificationTask,
        timeout: int = 180,
    ) -> VerifierResult:
        """
        Run tests for the project.

        Args:
            task:    The verification task containing project info.
            timeout: Max execution time in seconds.

        Returns:
            VerifierResult with test outcome.
        """
        framework = self._detect_test_framework()
        if not framework:
            logger.info("TestRunner: no test framework detected, skipping tests")
            return VerifierResult(
                verifier_type=VerifierType.TEST,
                command="none",
                status=VerifierStatus.SKIPPED,
                stdout="No test framework detected",
                stderr="",
                exit_code=0,
                duration_ms=0.0,
                diagnostics=[],
                files_changed=0,
            )

        self._detected = framework
        logger.info(f"TestRunner: detected {framework.name} testing framework")

        start = datetime.now()
        command = [framework.command] + framework.args

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=str(self._root),
                timeout=timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            elapsed = (datetime.now() - start).total_seconds() * 1000

            # Parse test results
            test_stats = self._parse_test_output(result.stdout)

            # Classify result
            diagnostics = self._classify_diagnostics(
                result.stdout + result.stderr,
                test_stats
            )

            status = (
                VerifierStatus.PASSED
                if result.returncode == 0 and test_stats.get("failed", 0) == 0
                else VerifierStatus.FAILED
            )

            return VerifierResult(
                verifier_type=VerifierType.TEST,
                command=" ".join(command),
                status=status,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                duration_ms=round(elapsed, 1),
                diagnostics=diagnostics,
                files_changed=test_stats.get("test_count", 0),
            )

        except subprocess.TimeoutExpired:
            elapsed = (datetime.now() - start).total_seconds() * 1000
            return VerifierResult(
                verifier_type=VerifierType.TEST,
                command=" ".join(command),
                status=VerifierStatus.TIMEOUT,
                stdout="",
                stderr=f"Tests timeout after {timeout}s",
                exit_code=124,
                duration_ms=round(elapsed, 1),
                diagnostics=[],
                files_changed=0,
            )
        except Exception as exc:
            elapsed = (datetime.now() - start).total_seconds() * 1000
            return VerifierResult(
                verifier_type=VerifierType.TEST,
                command=" ".join(command),
                status=VerifierStatus.ERROR,
                stdout="",
                stderr=str(exc),
                exit_code=1,
                duration_ms=round(elapsed, 1),
                diagnostics=[],
                files_changed=0,
            )

    # ── Test framework detection ────────────────────────────────────────────

    def _detect_test_framework(self) -> Optional[TestFramework]:
        """Detect the project's testing framework."""
        # Check each framework in priority order
        checks = [
            ("pytest", self._check_pytest),
            ("unittest", self._check_unittest),
            ("Jest", self._check_jest),
            ("Mocha", self._check_mocha),
            ("Flutter", self._check_flutter),
            ("Rust", self._check_rust),
            ("Maven", self._check_maven),
            ("Gradle", self._check_gradle),
        ]

        for name, check_func in checks:
            result = check_func()
            if result:
                logger.debug(f"TestRunner: detected {name}")
                return result

        return None

    def _check_pytest(self) -> Optional[TestFramework]:
        """Check for pytest framework."""
        # Check for pytest config or test files
        pytest_configs = ["pytest.ini", "pyproject.toml", "setup.cfg"]
        if any((self._root / cfg).exists() for cfg in pytest_configs):
            return TestFramework(
                name="pytest",
                command="pytest",
                args=["-v"],
                config_file="pytest.ini",
            )

        # Check for test directory
        test_dirs = ["tests", "test", "tests/unit", "tests/integration"]
        if any((self._root / d).is_dir() for d in test_dirs):
            return TestFramework(
                name="pytest",
                command="pytest",
                args=["-v"],
                config_file="tests/",
            )

        return None

    def _check_unittest(self) -> Optional[TestFramework]:
        """Check for Python unittest framework."""
        if any((self._root / f).exists() for f in ["test_*.py", "*_test.py"]):
            return TestFramework(
                name="unittest",
                command="python",
                args=["-m", "unittest", "discover"],
                config_file="test_*.py",
            )
        return None

    def _check_jest(self) -> Optional[TestFramework]:
        """Check for Jest framework."""
        package_json = self._root / "package.json"
        if package_json.exists():
            import json
            try:
                data = json.loads(package_json.read_text())
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                if "jest" in deps:
                    return TestFramework(
                        name="Jest",
                        command="npx",
                        args=["jest"],
                        config_file="jest.config.js",
                    )
            except json.JSONDecodeError:
                pass
        return None

    def _check_mocha(self) -> Optional[TestFramework]:
        """Check for Mocha framework."""
        package_json = self._root / "package.json"
        if package_json.exists():
            import json
            try:
                data = json.loads(package_json.read_text())
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                if "mocha" in deps:
                    return TestFramework(
                        name="Mocha",
                        command="npx",
                        args=["mocha"],
                        config_file="test/",
                    )
            except json.JSONDecodeError:
                pass
        return None

    def _check_flutter(self) -> Optional[TestFramework]:
        """Check for Flutter testing."""
        if (self._root / "pubspec.yaml").exists():
            return TestFramework(
                name="Flutter",
                command="flutter",
                args=["test"],
                config_file="pubspec.yaml",
            )
        return None

    def _check_rust(self) -> Optional[TestFramework]:
        """Check for Rust testing."""
        if (self._root / "Cargo.toml").exists():
            return TestFramework(
                name="Rust",
                command="cargo",
                args=["test"],
                config_file="Cargo.toml",
            )
        return None

    def _check_maven(self) -> Optional[TestFramework]:
        """Check for Maven testing."""
        if (self._root / "pom.xml").exists():
            return TestFramework(
                name="Maven",
                command="mvn",
                args=["test"],
                config_file="pom.xml",
            )
        return None

    def _check_gradle(self) -> Optional[TestFramework]:
        """Check for Gradle testing."""
        if (self._root / "build.gradle").exists() or (self._root / "build.gradle.kts").exists():
            return TestFramework(
                name="Gradle",
                command="gradle",
                args=["test"],
                config_file="build.gradle",
            )
        return None

    # ── Test output parsing ──────────────────────────────────────────────────

    def _parse_test_output(self, output: str) -> Dict[str, int]:
        """Parse test output for statistics."""
        stats = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "test_count": 0,
        }

        # Pytest pattern
        pytest_match = re.search(r"(\d+) passed(?:,)?\s*(\d+) failed(?:,)?\s*(\d+) skipped", output)
        if pytest_match:
            stats["passed"] = int(pytest_match.group(1))
            stats["failed"] = int(pytest_match.group(2))
            stats["skipped"] = int(pytest_match.group(3))
            stats["total"] = stats["passed"] + stats["failed"] + stats["skipped"]
            return stats

        # Jest pattern
        jest_match = re.search(r"Tests:\s+(\d+) passed", output)
        if jest_match:
            stats["passed"] = int(jest_match.group(1))
            stats["total"] = stats["passed"]
            return stats

        # Generic pattern for test count
        test_count = len(re.findall(r"(?i)(test\s+(?:\w+.*?pass|✓|✓))", output))
        stats["test_count"] = test_count
        stats["total"] = test_count

        return stats

    def _classify_diagnostics(self, output: str, stats: Dict[str, int]) -> List[Dict]:
        """Parse test output for diagnostics."""
        diagnostics = []

        # Look for failure messages
        failure_patterns = [
            (r"FAILED\s+(\S+)", "error"),
            (r"(?i)(test\s+failed)", "error"),
            (r"(?i)(AssertionError)", "error"),
            (r"(?i)(Error:)", "error"),
            (r"(?i)(Warning:)", "warning"),
        ]

        lines = output.splitlines()
        for i, line in enumerate(lines):
            for pattern, severity in failure_patterns:
                if re.search(pattern, line):
                    diagnostics.append({
                        "severity": severity,
                        "message": line.strip(),
                        "line": i + 1,
                        "source": "test",
                    })
                    break

        # Add summary diagnostics
        if stats["failed"] > 0:
            diagnostics.append({
                "severity": "error",
                "message": f"{stats['failed']} test(s) failed",
                "line": 0,
                "source": "test_summary",
            })

        if stats["skipped"] > 0:
            diagnostics.append({
                "severity": "warning",
                "message": f"{stats['skipped']} test(s) skipped",
                "line": 0,
                "source": "test_summary",
            })

        return diagnostics

# ============================================================================
# SECTION: ai.verification.linter_runner (ai/verification/linter_runner.py)
# ============================================================================
"""
linter_runner.py — Linter execution (plugin-agnostic).

Supports multiple linters through a plugin architecture:
  - Ruff (Python)
  - flake8 (Python)
  - pylint (Python)
  - ESLint (JS/TS)
  - Dart analyze (Dart)
  - Clang-tidy (C/C++)
"""

import subprocess
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.logger import setup_logger

from ai.verification.verification_task import VerificationTask, VerifierResult, VerifierStatus, VerifierType

logger = setup_logger(__name__)


@dataclass
class LinterConfig:
    """Configuration for a linter."""
    name:        str
    command:     str
    extensions:  List[str]
    options:     List[str]
    output_format: str  # "line", "json", "auto"


class LinterRunner:
    """
    Runs linters on modified files.

    Features:
      - Plugin-agnostic design (configs are configurable)
      - Only lints modified files
      - Parses structured diagnostics
      - Non-blocking if linter not available

    Usage:
        runner = LinterRunner(project_root)
        result = runner.run(task, timeout=60)
    """

    def __init__(
        self,
        project_root: str,
        configs: Optional[List[LinterConfig]] = None,
    ) -> None:
        self._root = Path(project_root)
        self._configs = configs or self._default_configs()
        self._available_linters = self._find_available_linters()
        logger.debug(f"LinterRunner initialized ({len(self._available_linters)} available).")

    # ── Public API ─────────────────────────────────────────────────────────

    def run(
        self,
        task: VerificationTask,
        timeout: int = 60,
    ) -> VerifierResult:
        """
        Run linters on modified files.

        Args:
            task:    The verification task containing modified files.
            timeout: Max execution time per linter in seconds.

        Returns:
            VerifierResult with linting outcome.
        """
        if not task.files_modified:
            logger.info("LinterRunner: no files to lint")
            return self._skip_result("No files to lint")

        # Find relevant linters for the files
        relevant_linters = self._find_relevant_linters(task.files_modified)

        if not relevant_linters:
            logger.info("LinterRunner: no suitable linter found")
            return self._skip_result("No suitable linter found")

        start = datetime.now()
        diagnostics: List[Dict] = []
        stdout = ""
        stderr = ""

        for linter in relevant_linters:
            # Filter files matching this linter's extensions
            matching_files = [
                f for f in task.files_modified
                if Path(f).suffix in linter.extensions
            ]

            if not matching_files:
                continue

            result = self._lint_files(matching_files, linter, timeout)
            stdout += f"{linter.name} output:\n{result.stdout}\n"
            stderr += result.stderr + "\n"

            # Parse diagnostics based on output format
            if linter.output_format == "json":
                parsed = self._parse_json_diagnostics(result.stdout)
            else:
                parsed = self._parse_line_diagnostics(result.stdout, linter.name)

            diagnostics.extend(parsed)

        elapsed = (datetime.now() - start).total_seconds() * 1000

        # Classify result based on diagnostics
        error_count = sum(1 for d in diagnostics if d.get("severity") == "error")
        status = (
            VerifierStatus.PASSED
            if error_count == 0
            else VerifierStatus.FAILED
        )

        return VerifierResult(
            verifier_type=VerifierType.LINT,
            command=" | ".join(l.command for l in relevant_linters),
            status=status,
            stdout=stdout,
            stderr=stderr,
            exit_code=error_count,
            duration_ms=round(elapsed, 1),
            diagnostics=diagnostics,
            files_changed=0,
        )

    # ── Helper methods ──────────────────────────────────────────────────────

    def _lint_files(
        self,
        files: List[str],
        linter: LinterConfig,
        timeout: int,
    ) -> VerifierResult:
        """Lint a list of files."""
        command = [linter.command] + linter.options + files

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=str(self._root),
                timeout=timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return VerifierResult(
                verifier_type=VerifierType.LINT,
                command=" ".join(command),
                status=(
                    VerifierStatus.PASSED
                    if result.returncode == 0
                    else VerifierStatus.FAILED
                ),
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                duration_ms=0.0,
                diagnostics=[],
                files_changed=0,
            )
        except subprocess.TimeoutExpired:
            return VerifierResult(
                verifier_type=VerifierType.LINT,
                command=" ".join(command),
                status=VerifierStatus.TIMEOUT,
                stdout="",
                stderr=f"Linting timeout after {timeout}s",
                exit_code=124,
                duration_ms=0.0,
                diagnostics=[],
                files_changed=0,
            )
        except Exception as exc:
            return VerifierResult(
                verifier_type=VerifierType.LINT,
                command=" ".join(command),
                status=VerifierStatus.ERROR,
                stdout="",
                stderr=str(exc),
                exit_code=1,
                duration_ms=0.0,
                diagnostics=[],
                files_changed=0,
            )

    def _skip_result(self, reason: str) -> VerifierResult:
        """Return a skip result with the given reason."""
        return VerifierResult(
            verifier_type=VerifierType.LINT,
            command="none",
            status=VerifierStatus.SKIPPED,
            stdout=reason,
            stderr="",
            exit_code=0,
            duration_ms=0.0,
            diagnostics=[],
            files_changed=0,
        )

    # ── Linter detection ────────────────────────────────────────────────────

    def _default_configs(self) -> List[LinterConfig]:
        """Return default linter configurations."""
        return [
            LinterConfig(
                name="Ruff",
                command="ruff",
                extensions=[".py"],
                options=["check"],
                output_format="auto",
            ),
            LinterConfig(
                name="flake8",
                command="flake8",
                extensions=[".py"],
                options=["."],
                output_format="line",
            ),
            LinterConfig(
                name="pylint",
                command="pylint",
                extensions=[".py"],
                options=["--output-format=text"],
                output_format="line",
            ),
            LinterConfig(
                name="ESLint",
                command="eslint",
                extensions=[".js", ".ts", ".jsx", ".tsx"],
                options=["--format", "unix"],
                output_format="line",
            ),
            LinterConfig(
                name="Dart analyze",
                command="dart",
                extensions=[".dart"],
                options=["analyze"],
                output_format="auto",
            ),
            LinterConfig(
                name="Clang-tidy",
                command="clang-tidy",
                extensions=[".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".java"],
                options=["-p", "."],
                output_format="auto",
            ),
        ]

    def _find_available_linters(self) -> List[LinterConfig]:
        """Return list of linters that are installed and available."""
        import shutil
        available = []
        for config in self._configs:
            if shutil.which(config.command):
                available.append(config)
        return available

    def _find_relevant_linters(
        self,
        files: List[str],
    ) -> List[LinterConfig]:
        """Return linters relevant for the given files."""
        relevant = set()

        for file_path in files:
            ext = Path(file_path).suffix.lower()
            for linter in self._available_linters:
                if ext in linter.extensions:
                    relevant.add(linter)

        return list(relevant)

    # ── Diagnostic parsing ──────────────────────────────────────────────────

    def _parse_json_diagnostics(self, output: str) -> List[Dict]:
        """Parse JSON-format lint output."""
        diagnostics = []
        try:
            data = json.loads(output)
            if isinstance(data, list):
                for item in data:
                    diagnostics.append({
                        "severity": item.get("severity", "warning"),
                        "message": item.get("message", ""),
                        "line": item.get("line", 0),
                        "column": item.get("column", 0),
                        "source": item.get("source", "lint"),
                    })
        except json.JSONDecodeError:
            pass
        return diagnostics

    def _parse_line_diagnostics(self, output: str, linter_name: str) -> List[Dict]:
        """Parse line-format lint output."""
        diagnostics = []
        lines = output.splitlines()

        for i, line in enumerate(lines):
            if not line.strip():
                continue

            # Common patterns for lint diagnostics
            patterns = [
                # file:line:column: severity: message
                (r"([^:]+):(\d+):(\d+):(\w+):\s*(.+)", True),
                # file.py:line: message
                (r"([^:]+):(\d+):\s*(.+)", False),
                # ERROR: message (at file:line)
                (r"(ERROR|WARNING|FATAL):\s*(.+)", False),
            ]

            for pattern, has_column in patterns:
                match = re.match(pattern, line)
                if match:
                    groups = match.groups()

                    if has_column:
                        file_path, line_num, col, severity, message = groups
                    else:
                        file_path = ""
                        line_num = groups[1] if len(groups) > 1 else "0"
                        message = groups[-1]

                    diagnostics.append({
                        "severity": severity.lower() if severity.lower() in ("error", "warning") else "warning",
                        "message": message.strip(),
                        "line": int(line_num) if line_num.isdigit() else 0,
                        "column": int(groups[2]) if has_column and groups[2].isdigit() else 0,
                        "source": linter_name,
                    })
                    break

        return diagnostics

    def is_linter_available(self, name: str) -> bool:
        """Check if a specific linter is available."""
        return any(l.name == name for l in self._available_linters)

    def get_available_linters(self) -> List[LinterConfig]:
        """Return list of available linters."""
        return self._available_linters

# ============================================================================
# SECTION: ai.verification.formatter_runner (ai/verification/formatter_runner.py)
# ============================================================================
"""
formatter_runner.py — Code formatter execution (plugin-agnostic).

Supports multiple formatters through a plugin architecture:
  - Black (Python)
  - isort (Python imports)
  - dart format (Dart)
  - prettier (JS/TS)
  - clang-format (C/C++/Java)
  - rustfmt (Rust)
"""

import subprocess
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.logger import setup_logger

from ai.verification.verification_task import VerificationTask, VerifierResult, VerifierStatus, VerifierType

logger = setup_logger(__name__)


@dataclass
class FormatterConfig:
    """Configuration for a formatter."""
    name:        str
    command:     str
    extensions:  List[str]
    options:     List[str]


class FormatterRunner:
    """
    Runs code formatters on modified files.

    Features:
      - Plugin-agnostic design (configs are configurable)
      - Only formats modified files
      - Reports formatting changes
      - Non-blocking if formatter not available

    Usage:
        runner = FormatterRunner(project_root)
        result = runner.run(task, timeout=30)
    """

    def __init__(
        self,
        project_root: str,
        configs: Optional[List[FormatterConfig]] = None,
    ) -> None:
        self._root = Path(project_root)
        self._configs = configs or self._default_configs()
        self._available_formatters = self._find_available_formatters()
        logger.debug(f"FormatterRunner initialized ({len(self._available_formatters)} available).")

    # ── Public API ─────────────────────────────────────────────────────────

    def run(
        self,
        task: VerificationTask,
        timeout: int = 30,
    ) -> VerifierResult:
        """
        Run formatters on modified files.

        Args:
            task:    The verification task containing modified files.
            timeout: Max execution time per formatter in seconds.

        Returns:
            VerifierResult with formatting outcome.
        """
        if not task.files_modified:
            logger.info("FormatterRunner: no files to format")
            return self._skip_result("No files to format")

        # Find relevant formatters for the files
        relevant_formatters = self._find_relevant_formatters(task.files_modified)

        if not relevant_formatters:
            logger.info("FormatterRunner: no suitable formatter found")
            return self._skip_result("No suitable formatter found")

        start = datetime.now()
        files_formatted = 0
        stdout = ""
        stderr = ""

        for formatter in relevant_formatters:
            # Filter files matching this formatter's extensions
            matching_files = [
                f for f in task.files_modified
                if Path(f).suffix in formatter.extensions
            ]

            if not matching_files:
                continue

            # Run formatter on each file
            for file_path in matching_files:
                result = self._format_file(file_path, formatter, timeout)

                stdout += f"Formatted: {file_path}\n"
                stdout += result.stdout + "\n"
                stderr += result.stderr + "\n"

                if result.exit_code == 0:
                    files_formatted += 1

        elapsed = (datetime.now() - start).total_seconds() * 1000

        # If files were formatted, status is PASS; otherwise SKIP
        status = (
            VerifierStatus.PASSED
            if files_formatted > 0
            else VerifierStatus.SKIPPED
        )

        return VerifierResult(
            verifier_type=VerifierType.FORMAT,
            command=" | ".join(f.command for f in relevant_formatters),
            status=status,
            stdout=stdout,
            stderr=stderr,
            exit_code=0 if files_formatted > 0 else 1,
            duration_ms=round(elapsed, 1),
            diagnostics=[],
            files_changed=files_formatted,
        )

    # ── Helper methods ──────────────────────────────────────────────────────

    def _format_file(
        self,
        file_path: str,
        formatter: FormatterConfig,
        timeout: int,
    ) -> VerifierResult:
        """Format a single file."""
        command = [formatter.command] + formatter.options + [file_path]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=str(self._root),
                timeout=timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return VerifierResult(
                verifier_type=VerifierType.FORMAT,
                command=" ".join(command),
                status=(
                    VerifierStatus.PASSED
                    if result.returncode == 0
                    else VerifierStatus.FAILED
                ),
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                duration_ms=0.0,
                diagnostics=[],
                files_changed=0,
            )
        except subprocess.TimeoutExpired:
            return VerifierResult(
                verifier_type=VerifierType.FORMAT,
                command=" ".join(command),
                status=VerifierStatus.TIMEOUT,
                stdout="",
                stderr=f"Formatting timeout after {timeout}s",
                exit_code=124,
                duration_ms=0.0,
                diagnostics=[],
                files_changed=0,
            )
        except Exception as exc:
            return VerifierResult(
                verifier_type=VerifierType.FORMAT,
                command=" ".join(command),
                status=VerifierStatus.ERROR,
                stdout="",
                stderr=str(exc),
                exit_code=1,
                duration_ms=0.0,
                diagnostics=[],
                files_changed=0,
            )

    def _skip_result(self, reason: str) -> VerifierResult:
        """Return a skip result with the given reason."""
        return VerifierResult(
            verifier_type=VerifierType.FORMAT,
            command="none",
            status=VerifierStatus.SKIPPED,
            stdout=reason,
            stderr="",
            exit_code=0,
            duration_ms=0.0,
            diagnostics=[],
            files_changed=0,
        )

    # ── Formatter detection ──────────────────────────────────────────────────

    def _default_configs(self) -> List[FormatterConfig]:
        """Return default formatter configurations."""
        return [
            FormatterConfig(
                name="Black",
                command="black",
                extensions=[".py"],
                options=["--quiet"],
            ),
            FormatterConfig(
                name="isort",
                command="isort",
                extensions=[".py"],
                options=["--profile", "black"],
            ),
            FormatterConfig(
                name="dart format",
                command="dart",
                extensions=[".dart"],
                options=["format"],
            ),
            FormatterConfig(
                name="prettier",
                command="prettier",
                extensions=[".js", ".ts", ".jsx", ".tsx", ".json", ".md"],
                options=["--write"],
            ),
            FormatterConfig(
                name="clang-format",
                command="clang-format",
                extensions=[".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".java"],
                options=["-i"],
            ),
            FormatterConfig(
                name="rustfmt",
                command="rustfmt",
                extensions=[".rs"],
                options=["--emit", "stdout"],
            ),
        ]

    def _find_available_formatters(self) -> List[FormatterConfig]:
        """Return list of formatters that are installed and available."""
        available = []
        for config in self._configs:
            if shutil.which(config.command):
                available.append(config)
        return available

    def _find_relevant_formatters(
        self,
        files: List[str],
    ) -> List[FormatterConfig]:
        """Return formatters relevant for the given files."""
        relevant = set()

        for file_path in files:
            ext = Path(file_path).suffix.lower()
            for formatter in self._available_formatters:
                if ext in formatter.extensions:
                    relevant.add(formatter)

        return list(relevant)

    def is_formatter_available(self, name: str) -> bool:
        """Check if a specific formatter is available."""
        return any(f.name == name for f in self._available_formatters)

    def get_available_formatters(self) -> List[FormatterConfig]:
        """Return list of available formatters."""
        return self._available_formatters

# ============================================================================
# SECTION: ai.verification.verification_engine (ai/verification/verification_engine.py)
# ============================================================================
"""
verification_engine.py — Main coordinator for verification operations.

Orchestrates the entire verification pipeline:
  1. Execute all configured verifiers
  2. Collect and aggregate results
  3. Determine success/failure
  4. Handle retries
  5. Generate verification reports
"""

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from core.logger import setup_logger
from core.event_bus import EventBus

from ai.editing.change_request import ChangeRequest, ChangeStatus
from ai.editing.rollback_manager import RollbackManager
from ai.verification.verification_task import (
    VerificationTask, VerifierType, VerifierResult, VerifierStatus, VerifierConfig
)
from ai.verification.build_runner import BuildRunner
from ai.verification.test_runner import TestRunner
from ai.verification.formatter_runner import FormatterRunner
from ai.verification.linter_runner import LinterRunner
from ai.verification.error_classifier import ErrorClassifier
from ai.verification.retry_manager import RetryManager
from ai.verification.success_validator import SuccessValidator
from ai.verification.verification_report import VerificationReportGenerator

logger = setup_logger(__name__)


@dataclass
class VerificationResult:
    """
    Final result of the verification engine.

    Attributes:
        task_id:           ID of the verification task
        success:           True if all verifiers passed
        total_verifiers:   Number of verifiers executed
        passed_verifiers:  Number that passed
        failed_verifiers:  Number that failed
        total_errors:      Total error count
        total_warnings:    Total warning count
        execution_time_ms: Total execution time
        report:            Generated verification report
    """
    task_id:           str
    success:           bool
    total_verifiers:   int
    passed_verifiers:  int
    failed_verifiers:  int
    total_errors:      int
    total_warnings:    int
    execution_time_ms: float
    report:            str


class VerificationEngine:
    """
    Main coordinator for AI code verification.

    Manages a pool of verifiers that run in sequence or parallel
    depending on configuration.

    Usage:
        engine = VerificationEngine(event_bus, project_root)
        result = engine.verify(task)
    """

    def __init__(
        self,
        event_bus: EventBus,
        project_root: str,
        config: Optional[Dict[VerifierType, VerifierConfig]] = None,
    ) -> None:
        self.event_bus = event_bus
        self._root = Path(project_root)
        self._config = config or create_default_config()

        # Initialize runner instances
        self._build_runner = BuildRunner(project_root)
        self._test_runner = TestRunner(project_root)
        self._formatter_runner = FormatterRunner(project_root)
        self._linter_runner = LinterRunner(project_root)
        self._error_classifier = ErrorClassifier()
        self._retry_manager = RetryManager()
        self._success_validator = SuccessValidator()
        self._report_generator = VerificationReportGenerator()

        # State management
        self._lock = threading.Lock()
        self._current_task: Optional[VerificationTask] = None

        logger.info(
            f"VerificationEngine initialized (root='{self._root.name}', "
            f"config={len(self._config)} verifiers)"
        )

    # ── Public API ─────────────────────────────────────────────────────────

    def verify(
        self,
        task: VerificationTask,
    ) -> VerificationResult:
        """
        Execute the verification pipeline for a task.

        Args:
            task: The VerificationTask to run.

        Returns:
            VerificationResult with overall success/failure.
        """
        with self._lock:
            self._current_task = task

        logger.info(
            f"VerificationEngine.verify(): task={task.task_id[:8]}, "
            f"files={len(task.files_modified)}, prompt='{task.user_prompt[:40]}...'"
        )
        self._publish("verification_started", {"task_id": task.task_id})

        start_time = time.perf_counter()

        try:
            # Execute each enabled verifier
            for vtype, verifer_config in self._config.items():
                if not verifer_config.enabled:
                    logger.debug(f"Verification: skipping {vtype.value} (disabled)")
                    continue

                result = self._run_verifier(task, vtype)
                task.add_result(result)

                # Publish progress
                self._publish("verification_progress", {
                    "task_id": task.task_id,
                    "verifier": vtype.value,
                    "status": result.status.value,
                    "duration_ms": result.duration_ms,
                })

                # Check if we should stop on critical failure
                if result.status == VerifierStatus.ERROR:
                    logger.warning(f"Verification: critical error in {vtype.value}")
                    break

            # Determine overall status
            task.status = task.get_overall_status()
            task.error_count = len(task.get_failed_verifiers())

            # Calculate execution time
            execution_time_ms = (time.perf_counter() - start_time) * 1000

            # Generate report
            report = self._report_generator.generate(task, execution_time_ms)

            # Publish completion
            self._publish("verification_complete", {
                "task_id": task.task_id,
                "success": task.get_overall_status() == "success",
                "report": report,
            })

            return VerificationResult(
                task_id=task.task_id,
                success=task.get_overall_status() == "success",
                total_verifiers=len(task.results),
                passed_verifiers=len(task.get_passed_verifiers()),
                failed_verifiers=len(task.get_failed_verifiers()),
                total_errors=task.error_count,
                total_warnings=sum(
                    len(r.diagnostics) for r in task.results.values()
                    if r.status == VerifierStatus.FAILED
                ),
                execution_time_ms=execution_time_ms,
                report=report,
            )

        except Exception as exc:
            logger.error(f"VerificationEngine: unexpected error: {exc}")
            self._publish("verification_error", {
                "task_id": task.task_id,
                "error": str(exc),
            })
            raise

    def verify_edit(
        self,
        edit_request: ChangeRequest,
        files_modified: List[str],
    ) -> VerificationResult:
        """
        Convenience method: Create and run verification for an edit request.

        Args:
            edit_request: The ChangeRequest to verify.
            files_modified: List of files that were modified.

        Returns:
            VerificationResult with success/failure.
        """
        task = VerificationTask.create(
            edit_request_id=edit_request.request_id,
            user_prompt=edit_request.user_prompt,
            files_modified=files_modified,
            config=self._config,
            max_retries=self._retry_manager.max_retries,
        )
        return self.verify(task)

    def retry_failed(self, task: VerificationTask) -> Optional[VerificationTask]:
        """
        Create a retry task if verification failed and retries remain.

        Args:
            task: The failed VerificationTask.

        Returns:
            New VerificationTask for retry, or None if no retries remain.
        """
        if not task.needs_retry():
            return None

        task.retry_count += 1
        logger.info(
            f"VerificationEngine: retry #{task.retry_count}/{task.max_retries} "
            f"for task {task.task_id[:8]}"
        )

        # Create new task with same parameters
        new_task = VerificationTask.create(
            edit_request_id=task.edit_request_id,
            user_prompt=task.user_prompt,
            files_modified=task.files_modified,
            config=task.config,
            max_retries=task.max_retries,
        )
        new_task.retry_count = task.retry_count

        return new_task

    def get_status(self) -> Dict[str, Any]:
        """Return engine status for UI display."""
        return {
            "running": self._current_task is not None,
            "current_task": self._current_task.task_id if self._current_task else None,
            "config": {
                vtype.value: {
                    "enabled": config.enabled,
                    "timeout": config.timeout,
                    "retry_count": config.retry_count,
                }
                for vtype, config in self._config.items()
            },
        }

    # ── Verifier execution ──────────────────────────────────────────────────

    def _run_verifier(
        self,
        task: VerificationTask,
        vtype: VerifierType,
    ) -> VerifierResult:
        """Run a single verifier and return result."""
        command = self._config[vtype].command
        timeout = self._config[vtype].timeout
        options = self._config[vtype].options

        logger.info(f"VerificationEngine: running {vtype.value} verifier")

        try:
            if vtype == VerifierType.BUILD:
                return self._build_runner.run(task, timeout)
            elif vtype == VerifierType.TEST:
                return self._test_runner.run(task, timeout)
            elif vtype == VerifierType.FORMAT:
                return self._formatter_runner.run(task, timeout)
            elif vtype == VerifierType.LINT:
                return self._linter_runner.run(task, timeout)
            elif vtype == VerifierType.ANALYSIS:
                # Analysis not yet implemented
                return VerifierResult(
                    verifier_type=vtype,
                    command="analysis (not implemented)",
                    status=VerifierStatus.SKIPPED,
                    stdout="Analysis not yet implemented",
                    stderr="",
                    exit_code=0,
                    duration_ms=0.0,
                    diagnostics=[],
                    files_changed=0,
                )
            else:
                return VerifierResult(
                    verifier_type=vtype,
                    command="unknown",
                    status=VerifierStatus.ERROR,
                    stdout="",
                    stderr=f"Unknown verifier type: {vtype}",
                    exit_code=1,
                    duration_ms=0.0,
                    diagnostics=[],
                    files_changed=0,
                )

        except Exception as exc:
            logger.error(f"VerificationEngine: {vtype.value} error: {exc}")
            return VerifierResult(
                verifier_type=vtype,
                command=str(command or "unknown"),
                status=VerifierStatus.ERROR,
                stdout="",
                stderr=str(exc),
                exit_code=1,
                duration_ms=0.0,
                diagnostics=[],
                files_changed=0,
            )

    # ── EventBus publishing ────────────────────────────────────────────────

    def _publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish an event to the EventBus."""
        try:
            self.event_bus.publish(event_type, data)
        except Exception as exc:
            logger.debug(f"VerificationEngine: publish failed ({event_type}): {exc}")


def create_default_config() -> Dict[VerifierType, VerifierConfig]:
    """Create default verifier configurations."""
    return {
        VerifierType.FORMAT: VerifierConfig(
            type=VerifierType.FORMAT,
            enabled=True,
            timeout=30,
            retry_count=0,
        ),
        VerifierType.LINT: VerifierConfig(
            type=VerifierType.LINT,
            enabled=True,
            timeout=60,
            retry_count=0,
        ),
        VerifierType.BUILD: VerifierConfig(
            type=VerifierType.BUILD,
            enabled=True,
            timeout=120,
            retry_count=1,
        ),
        VerifierType.TEST: VerifierConfig(
            type=VerifierType.TEST,
            enabled=True,
            timeout=180,
            retry_count=0,
        ),
        VerifierType.ANALYSIS: VerifierConfig(
            type=VerifierType.ANALYSIS,
            enabled=False,
            timeout=60,
            retry_count=0,
        ),
    }

# ============================================================================
# SECTION: ai.execution.execution_engine (ai/execution/execution_engine.py)
# ============================================================================
"""
ExecutionEngine — main orchestrator for AI execution.

Coordinates all AI actions in OwnCode. Does NOT contain
any LLM-specific code. It only manages execution:

- Creating tasks from user prompts
- Scheduling tasks (priority, dependencies, groups)
- Tracking task state and lifecycle
- Pausing, stopping, cancelling tasks
- Monitoring execution
- Generating reports and metrics

The engine is the central hub that ties together:
- Task creation (from Planner, user prompts)
- Task scheduling (TaskScheduler)
- Task execution (TaskExecutor)
- Task monitoring (ExecutionMonitor)
- Task storage (ExecutionQueue)

Usage:
    engine = ExecutionEngine(event_bus, config_dir, project_root)
    
    # Submit a task
    task = engine.submit_task("Add logging to every agent")
    
    # Monitor progress
    engine.start_monitoring()
    
    # Cancel a task
    engine.cancel_task(task.id)
    
    # Generate report
    report = engine.get_execution_report(task.id)
"""

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from core.event_bus import EventBus
from core.logger import setup_logger

from ai.engine.task import Task as BaseTask, TaskStatus
from ai.context.context_engine import ContextEngine, ContextPackage
from ai.models.model_manager import ModelManager
from ai.editing.change_applier import ChangeApplier
from ai.verification.verification_engine import VerificationEngine

from ai.execution.execution_task import ExecutionTask, ExecutionConfig, ExecutionMode, RetryStrategy
from ai.execution.execution_queue import ExecutionQueue
from ai.execution.task_scheduler import TaskScheduler
from ai.execution.task_executor import TaskExecutor, ExecutorConfig
from ai.execution.execution_monitor import ExecutionMonitor
from ai.execution.execution_report import ExecutionReportGenerator
from ai.execution.execution_metrics import ExecutionMetrics
from ai.execution.task_state import TaskState
from ai.engine.engineering_task import EngineeringTask


@dataclass
class ExecutionEngineConfig:
    """
    Configuration for ExecutionEngine.
    
    Attributes:
        max_concurrent:  Maximum concurrent tasks
        max_retries:     Default retry attempts
        default_timeout: Default task timeout in seconds
        config_dir:      Directory for queue persistence
        project_root:    Project root directory
    """
    max_concurrent: int = 4
    max_retries: int = 2
    default_timeout: Optional[int] = 300
    config_dir: str = "config"
    project_root: Optional[str] = None


class ExecutionEngine:
    """
    Central orchestrator for AI execution in OwnCode.
    
    This is the main entry point for all AI execution. It:
    - Accepts user prompts and creates ExecutionTasks
    - Schedules tasks using priority, dependencies, and groups
    - Executes tasks using a thread pool
    - Monitors execution and reports status
    - Integrates with all other engine components
    
    Key principles:
    - NO LLM code here - pure orchestration
    - All UI updates via EventBus
    - Non-blocking execution
    - Full cancellation support
    
    Usage:
        engine = ExecutionEngine(event_bus, config)
        
        # Submit tasks
        task1 = engine.submit_task("Add logging")
        task2 = engine.submit_task("Refactor database", priority=100)
        
        # Monitor
        engine.start_monitoring()
        
        # Cancel if needed
        engine.cancel_task(task1.id)
        
        # Get report
        report = engine.get_execution_report(task2.id)
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        config: ExecutionEngineConfig,
    ) -> None:
        self._event_bus = event_bus
        self._config = config
        self._config_dir = Path(config.config_dir)
        
        # Initialize components
        self._queue = ExecutionQueue(
            config_dir=str(self._config_dir),
            name="main",
        )
        
        self._scheduler = TaskScheduler(self._queue, str(self._config_dir))
        
        self._executor_config = ExecutorConfig(
            pool_size=config.max_concurrent,
            max_retries=config.max_retries,
            default_timeout=config.default_timeout,
        )
        self._executor = TaskExecutor(self._executor_config)
        
        self._monitor = ExecutionMonitor(self)
        self._reporter = ExecutionReportGenerator()
        self._metrics = ExecutionMetrics()
        
        # Integration components
        self._context_engine: Optional[ContextEngine] = None
        self._model_manager: Optional[ModelManager] = None
        self._change_applier: Optional[ChangeApplier] = None
        self._verification_engine: Optional[VerificationEngine] = None
        
        # Task tracking
        self._tasks: Dict[str, ExecutionTask] = {}
        self._shutdown = False
        
        # Setup callbacks
        self._executor_config.on_task_start = self._on_task_start
        self._executor_config.on_task_complete = self._on_task_complete
        self._executor_config.on_task_error = self._on_task_error
        
        # Monitoring thread
        self._monitor_thread: Optional[threading.Thread] = None
        
        logger = setup_logger(__name__)
        logger.info("ExecutionEngine initialized")
    
    # ── Public API ──────────────────────────────────────────────────────────────
    
    def submit_task(
        self,
        prompt: str,
        config: Optional[ExecutionConfig] = None,
    ) -> ExecutionTask:
        """
        Submit a new task for execution.
        
        Args:
            prompt: User prompt text
            config: Optional execution configuration
            
        Returns:
            New ExecutionTask
        """
        task = ExecutionTask(
            task=BaseTask(original_prompt=prompt),
            config=config or ExecutionConfig(),
        )
        
        # Add to queue
        self._queue.enqueue(task)
        
        # Add to scheduler
        self._scheduler.add_task(task)
        
        # Track task
        self._tasks[task.id] = task
        
        # Publish event
        self._publish("execution_task_created", {
            "task_id": task.id,
            "prompt": prompt,
            "priority": task.config.priority,
        })
        
        logger = setup_logger(__name__)
        logger.info(f"Task submitted: {task.id[:8]} - {prompt[:40]}...")
        
        return task
    
    def submit_with_plan(
        self,
        prompt: str,
        plan: List[str],
        config: Optional[ExecutionConfig] = None,
    ) -> ExecutionTask:
        """
        Submit a task with a pre-defined plan.
        
        Args:
            prompt: User prompt text
            plan: Ordered list of step descriptions
            config: Optional execution configuration
            
        Returns:
            New ExecutionTask
        """
        task = self.submit_task(prompt, config)
        task.task.plan = plan
        
        # Update event
        self._publish("execution_task_plan_set", {
            "task_id": task.id,
            "steps": len(plan),
        })
        
        return task
        
    def submit_engineering_tasks(self, tasks: List[EngineeringTask]) -> None:
        """Submit multiple pre-decomposed EngineeringTasks."""
        # Group independent tasks for parallel execution
        groups = {}
        for t in tasks:
            if not t.dependencies:
                # No dependencies - can run immediately
                if "parallel_batch" not in groups:
                    groups["parallel_batch"] = []
                groups["parallel_batch"].append(t)
            else:
                # Has dependencies - sequential
                groups[f"seq_{t.id[:8]}"] = [t]
        
        # Submit tasks with proper execution config
        for group_name, group_tasks in groups.items():
            for t in group_tasks:
                # Convert EngineeringTask to ExecutionTask
                exec_task = ExecutionTask(
                    task=BaseTask(
                        original_prompt=t.description,
                        title=t.title,
                        id=t.id
                    ),
                    config=ExecutionConfig(
                        mode=ExecutionMode.BACKGROUND,
                        max_retries=2,
                        retry_strategy=RetryStrategy.EXPONENTIAL,
                        depends_on=t.dependencies,
                        group=group_name if len(group_tasks) > 1 else None,
                        cancel_on_error=True
                    )
                )
                
                # Copy engineering-specific attributes
                exec_task.engineering_metadata = {
                    "estimated_duration": t.estimated_duration,
                    "actual_duration": t.actual_duration,
                    "assigned_model": t.assigned_model,
                    "verification_state": t.verification_state,
                    "affected_files": t.affected_files,
                    "retry_count": t.retry_count,
                    "logs": t.logs
                }
                
                # Add to queue
                self._queue.enqueue(exec_task)
                # Add to scheduler
                self._scheduler.add_task(exec_task)
                # Track task
                self._tasks[exec_task.id] = exec_task
                
                self._publish("execution_task_created", {
                    "task_id": exec_task.id,
                    "title": t.title,
                    "priority": t.priority.value if hasattr(t.priority, 'value') else str(t.priority),
                    "group": group_name,
                    "dependencies": t.dependencies,
                    "estimated_duration": t.estimated_duration
                })
            
        logger = setup_logger(__name__)
        logger.info(f"Submitted {len(tasks)} engineering tasks in {len(groups)} execution groups.")
        self.start_monitoring()
    
    def start_monitoring(self) -> None:
        """Start background monitoring."""
        if self._monitor_thread:
            return
        
        self._shutdown = False
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ExecutionMonitor"
        )
        self._monitor_thread.start()
        
        logger = setup_logger(__name__)
        logger.info("Execution monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._shutdown = True
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
            self._monitor_thread = None
        
        logger = setup_logger(__name__)
        logger.info("Execution monitoring stopped")
    
    def cancel_task(self, task_id: str, by_user: str = "user") -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: Task ID to cancel
            by_user: User who cancelled (for audit)
            
        Returns:
            True if cancelled
        """
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        # Stop executor if running
        self._executor.cancel(task_id)
        
        # Update state
        task.state_history.add_transition(
            StateTransition(
                from_state=task.state,
                to_state=TaskState.CANCELLED,
                timestamp=datetime.utcnow(),
                reason=f"Cancelled by {by_user}",
            )
        )
        
        # Update task
        task.cancelled_by = by_user
        
        # Publish event
        self._publish("execution_task_cancelled", {
            "task_id": task_id,
            "cancelled_by": by_user,
        })
        
        logger = setup_logger(__name__)
        logger.info(f"Task cancelled: {task_id[:8]}")
        
        return True
    
    def pause_task(self, task_id: str) -> bool:
        """Pause a running task."""
        # In production, this would pause the executor
        # For now, we just mark it as paused
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        task.state_history.add_transition(
            StateTransition(
                from_state=task.state,
                to_state=TaskState.PAUSED,
                timestamp=datetime.utcnow(),
                reason="Task paused",
            )
        )
        
        self._publish("execution_task_paused", {"task_id": task_id})
        
        return True
    
    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        task.state_history.add_transition(
            StateTransition(
                from_state=task.state,
                to_state=TaskState.RUNNING,
                timestamp=datetime.utcnow(),
                reason="Task resumed",
            )
        )
        
        # Re-submit to executor
        self._executor.submit(task)
        
        self._publish("execution_task_resumed", {"task_id": task_id})
        
        return True
    
    def get_task(self, task_id: str) -> Optional[ExecutionTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[ExecutionTask]:
        """Get all tasks."""
        return list(self._tasks.values())
    
    def get_pending_tasks(self) -> List[ExecutionTask]:
        """Get all pending tasks."""
        return [t for t in self._tasks.values() if t.state == TaskState.PENDING]
    
    def get_running_tasks(self) -> List[ExecutionTask]:
        """Get all running tasks."""
        return [t for t in self._tasks.values() if t.state == TaskState.RUNNING]
    
    def get_completed_tasks(self) -> List[ExecutionTask]:
        """Get all completed tasks."""
        return [t for t in self._tasks.values() if t.state == TaskState.SUCCESS]
    
    def get_failed_tasks(self) -> List[ExecutionTask]:
        """Get all failed tasks."""
        return [t for t in self._tasks.values() if t.state == TaskState.FAILED]
    
    def get_execution_report(self, task_id: str) -> Optional[dict]:
        """Get a detailed execution report for a task."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        return self._reporter.generate(task)
    
    def get_metrics(self) -> dict:
        """Get execution metrics."""
        return self._metrics.get_metrics()
    
    def get_status(self) -> dict:
        """Get engine status."""
        return {
            "active_tasks": self._executor.get_active_count(),
            "pending_tasks": len(self.get_pending_tasks()),
            "running_tasks": len(self.get_running_tasks()),
            "completed_tasks": len(self.get_completed_tasks()),
            "failed_tasks": len(self.get_failed_tasks()),
            "executor_stats": self._executor.get_stats(),
            "queue_stats": self._queue.stats(),
        }
    
    # ── Integration points ──────────────────────────────────────────────────────
    
    def attach_context_engine(self, engine: ContextEngine) -> None:
        """Attach ContextEngine for context building."""
        self._context_engine = engine
    
    def attach_model_manager(self, manager: ModelManager) -> None:
        """Attach ModelManager for model execution."""
        self._model_manager = manager
    
    def attach_change_applier(self, applier: ChangeApplier) -> None:
        """Attach ChangeApplier for code changes."""
        self._change_applier = applier
    
    def attach_verification_engine(self, engine: VerificationEngine) -> None:
        """Attach VerificationEngine for quality checks."""
        self._verification_engine = engine
    
    # ── Private helpers ─────────────────────────────────────────────────────────
    
    def _on_task_start(self, task: ExecutionTask) -> None:
        """Handle task start event."""
        task.started_time = datetime.utcnow()
        
        self._publish("execution_task_started", {
            "task_id": task.id,
            "started_at": task.started_time.isoformat(),
        })
    
    def _on_task_complete(self, task: ExecutionTask, success: bool) -> None:
        """Handle task completion event."""
        task.completed_time = datetime.utcnow()
        
        if success:
            task.state_history.add_transition(
                StateTransition(
                    from_state=task.state,
                    to_state=TaskState.SUCCESS,
                    timestamp=datetime.utcnow(),
                    reason="Task completed successfully",
                )
            )
            
            self._metrics.record_task_success(task)
            
            self._publish("execution_task_completed", {
                "task_id": task.id,
                "completed_at": task.completed_time.isoformat(),
                "results_count": len(task.results),
            })
            
            # Run verification if attached
            if self._verification_engine:
                self._run_verification(task)
            
            # Apply changes if attached
            if self._change_applier:
                self._apply_changes(task)
            
        else:
            task.state_history.add_transition(
                StateTransition(
                    from_state=task.state,
                    to_state=TaskState.FAILED,
                    timestamp=datetime.utcnow(),
                    reason="Task failed",
                )
            )
            
            self._metrics.record_task_failure(task)
    
    def _on_task_error(self, task: ExecutionTask, error: Exception) -> None:
        """Handle task error event."""
        self._publish("execution_task_error", {
            "task_id": task.id,
            "error": str(error),
        })
    
    def _run_verification(self, task: ExecutionTask) -> None:
        """Run verification on completed task via VerificationEngine."""
        if not self._verification_engine:
            return
        try:
            from ai.verification.verification_task import VerificationTask
            from ai.editing.change_request import ChangeRequest, ChangeStatus

            # Collect modified files from task results
            files: list = []
            for r in task.results:
                # Results may embed file paths in output as "FILE: <path>"
                for line in (r.output or "").splitlines():
                    if line.startswith("FILE:"):
                        files.append(line[5:].strip())

            if not files:
                return   # nothing to verify

            cr = ChangeRequest(
                request_id=task.id,
                user_prompt=task.task.original_prompt,
                status=ChangeStatus.PENDING,
            )
            vtask = VerificationTask.create(
                edit_request_id=cr.request_id,
                user_prompt=cr.user_prompt,
                files_modified=files,
                config=self._verification_engine._config,
                max_retries=1,
            )
            result = self._verification_engine.verify(vtask)
            logger = setup_logger(__name__)
            logger.info(
                f"Verification for task {task.id[:8]}: "
                f"success={result.success}, "
                f"errors={result.total_errors}"
            )
        except Exception as e:
            logger = setup_logger(__name__)
            logger.error(f"Verification failed for task {task.id[:8]}: {e}")

    def _apply_changes(self, task: ExecutionTask) -> None:
        """Apply code changes produced by the task via ChangeApplier."""
        if not self._change_applier:
            return
        try:
            from ai.editing.change_set import ChangeSet, ChangeOperation, OperationType
            from ai.editing.change_request import ChangeRequest, ChangeStatus

            from ai.editing.smart_patch_engine import SmartPatchEngine

            operations = []
            project_root = getattr(self._config, "project_root", None)
            for r in task.results:
                raw_out = r.output or ""
                extracted = SmartPatchEngine.extract_operations_from_llm_response(
                    raw_out, workspace_root=project_root
                )
                if extracted:
                    operations.extend(extracted)

            if not operations:
                return

            cs = ChangeSet(operations=operations)
            cr = ChangeRequest(
                request_id=task.id,
                user_prompt=task.task.original_prompt,
                status=ChangeStatus.PENDING,
            )
            result = self._change_applier.apply(cs, cr)
            logger = setup_logger(__name__)
            logger.info(
                f"ChangeApplier for task {task.id[:8]}: "
                f"applied={result.applied_count}, failed={result.failed_count}"
            )
        except Exception as e:
            logger = setup_logger(__name__)
            logger.error(f"ChangeApplier failed for task {task.id[:8]}: {e}")
    
    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while not self._shutdown:
            try:
                # Get ready tasks from scheduler
                ready_tasks = self._scheduler.get_ready_tasks()
                
                for task in ready_tasks:
                    if task.state == TaskState.SCHEDULED:
                        # Dequeue and execute
                        self._queue.dequeue()
                        self._executor.submit(task)
                        
                        # Publish detailed event
                        self._publish("execution_task_dispatched", {
                            "task_id": task.id,
                            "title": getattr(task, 'title', task.task.title if hasattr(task, 'task') else 'Unknown'),
                            "state": task.state.value
                        })
                
                # Update monitor
                status = self.get_status()
                self._publish("execution_status_update", status)
                
                # Publish individual task updates for UI
                for task_id, task in self._tasks.items():
                    if not task.is_terminal:
                        self._publish("execution_task_update", {
                            "task_id": task_id,
                            "title": getattr(task, 'title', task.task.title if hasattr(task, 'task') else 'Unknown'),
                            "state": task.state.value,
                            "status": task.status.value if hasattr(task, 'status') else task.state.value,
                            "progress": len(task.results) if hasattr(task, 'results') else 0
                        })
                
                # Small delay to avoid tight loop
                time.sleep(0.1)
                
            except Exception as e:
                logger = setup_logger(__name__)
                logger.error(f"Monitor loop error: {e}")
                time.sleep(1.0)
    
    def _publish(self, event_type: str, data: dict) -> None:
        """Publish event to EventBus."""
        try:
            self._event_bus.publish(event_type, data)
        except Exception as e:
            logger = setup_logger(__name__)
            logger.error(f"Failed to publish event: {e}")


# Convenience factory function
def create_execution_engine(
    event_bus: EventBus,
    config_dir: str = "config",
    project_root: Optional[str] = None,
    max_concurrent: int = 4,
    max_retries: int = 2,
) -> ExecutionEngine:
    """
    Factory function to create and configure an ExecutionEngine.
    
    Args:
        event_bus: EventBus instance
        config_dir: Directory for queue persistence
        project_root: Project root directory
        max_concurrent: Maximum concurrent tasks
        max_retries: Default retry attempts
        
    Returns:
        Configured ExecutionEngine
    """
    config = ExecutionEngineConfig(
        config_dir=config_dir,
        project_root=project_root,
        max_concurrent=max_concurrent,
        max_retries=max_retries,
    )
    
    return ExecutionEngine(event_bus, config)


# ============================================================================
# SECTION: ai.engine.engineering_workflow_coordinator (ai/engine/engineering_workflow_coordinator.py)
# ============================================================================
"""
EngineeringWorkflowCoordinator — Version 1.8.7
Coordinates the end-to-end AI software engineering workflow, connecting:
Project Intelligence -> Context Engine -> Model Router -> AI Engine -> Editing/Verification.
Executes asynchronously on a worker thread to keep the UI unblocked.
"""

import threading
from typing import Dict, Any, Optional

from core.logger import setup_logger
from core.event_bus import EventBus
from ai.intelligence.project_analyzer import ProjectAnalyzer
from ai.context.context_engine import ContextEngine
from ai.models.router import ModelRouter, TaskType
from ai.chat.ai_chat_engine import AIChatEngine
from ai.editing.change_applier import ChangeApplier
from ai.verification.verification_engine import VerificationEngine
from ai.memory.project_memory import ProjectMemory
from ai.memory.decision_memory import DecisionMemory
from ai.engine.task_analyzer import TaskAnalyzer
from ai.planning.task_decomposer import TaskDecomposer
from ai.execution.execution_engine import ExecutionEngine

logger = setup_logger(__name__)


class EngineeringWorkflowCoordinator:
    """
    Orchestrates the entire AI engineering pipeline:
    1. Task Analysis
    2. Project Intelligence (architecture, health)
    3. Context Assembly
    4. Model Selection
    5. Execution Plan / Generation
    6. Verification & Patch Proposal
    7. Memory Update
    """

    def __init__(
        self,
        event_bus: EventBus,
        project_analyzer: Optional[ProjectAnalyzer] = None,
        context_engine: Optional[ContextEngine] = None,
        model_router: Optional[ModelRouter] = None,
        chat_engine: Optional[AIChatEngine] = None,
        patch_engine: Optional[ChangeApplier] = None,
        verification_engine: Optional[VerificationEngine] = None,
        project_memory: Optional[ProjectMemory] = None,
        decision_memory: Optional[DecisionMemory] = None,
        execution_engine: Optional[ExecutionEngine] = None,
    ):
        self.event_bus = event_bus
        self.project_analyzer = project_analyzer
        self.context_engine = context_engine
        self.model_router = model_router
        self.chat_engine = chat_engine
        self.patch_engine = patch_engine
        self.verification_engine = verification_engine
        self.project_memory = project_memory or ProjectMemory()
        self.decision_memory = decision_memory or DecisionMemory()
        self.execution_engine = execution_engine
        
        self.task_analyzer = TaskAnalyzer()
        self.task_decomposer = TaskDecomposer()

        # Maps an in-flight engineering-task id -> (decision_id, affected_files)
        # so we can close the memory loop when the task finally succeeds/fails.
        self._active_decisions: Dict[str, Any] = {}

        # Subscribe to AI requests
        self.event_bus.subscribe("user_ai_request", self._on_user_request)

        # Subscribe to user workflow controls (v1.8.8)
        self.event_bus.subscribe("workflow_action_pause", self._on_pause_request)
        self.event_bus.subscribe("workflow_action_resume", self._on_resume_request)
        self.event_bus.subscribe("workflow_action_cancel", self._on_cancel_request)

        # Close the memory loop on task outcome (v1.9.1)
        self.event_bus.subscribe("execution_task_completed", self._on_task_outcome_success)
        self.event_bus.subscribe("execution_task_error", self._on_task_outcome_failure)
        self.event_bus.subscribe("verification_complete", self._on_verification_complete)

        logger.info("EngineeringWorkflowCoordinator initialized.")

    def _on_user_request(self, payload: Dict[str, Any]):
        """Triggered by the UI when a user submits a prompt."""
        prompt = payload.get("prompt", "")
        current_file = payload.get("current_file")
        open_tabs = payload.get("open_tabs", [])
        
        if not prompt:
            return

        # Start background workflow
        thread = threading.Thread(
            target=self._run_workflow,
            args=(prompt, current_file, open_tabs),
            daemon=True
        )
        thread.start()

    def _run_workflow(self, prompt: str, current_file: Optional[str], open_tabs: list):
        """Executes the pipeline sequentially in a background thread."""
        logger.info("Engineering Workflow Started.")
        self.event_bus.publish("workflow_started", {"prompt": prompt})

        # --- PHASE 1: Task Analysis ---
        self.event_bus.publish("workflow_stage_changed", {"stage": "Task Analysis"})
        task = self.task_analyzer.analyze(prompt)

        # --- PHASE 2: Project Intelligence ---
        self.event_bus.publish("workflow_stage_changed", {"stage": "Project Intelligence"})
        if self.project_analyzer and hasattr(self.project_analyzer, "analyze"):
            try:
                self.project_analyzer.analyze()
            except Exception as e:
                logger.warning(f"ProjectAnalyzer error: {e}")

        # --- PHASE 3: Context Assembly ---
        self.event_bus.publish("workflow_stage_changed", {"stage": "Context Assembly"})
        context_package = None
        if self.context_engine:
            try:
                context_package = self.context_engine.build(
                    prompt=prompt,
                    current_file=current_file,
                    open_tabs=open_tabs or [],
                )
                self.event_bus.publish("workflow_context_ready", {
                    "token_estimate": context_package.token_estimate,
                    "files_included": len(context_package.selected_files),
                })
                logger.info(
                    f"Context built: {len(context_package.selected_files)} files, "
                    f"~{context_package.token_estimate} tokens"
                )
            except Exception as e:
                logger.warning(f"Context Engine failed: {e}")
        else:
            logger.info("Context Engine not available — skipping context assembly")

        # --- PHASE 4: Model Selection ---
        self.event_bus.publish("workflow_stage_changed", {"stage": "Model Selection"})
        best_model = None
        task_type = self._resolve_task_type(task)
        if self.model_router:
            try:
                best_model = self.model_router.select_best_model(task_type=task_type)
                if best_model:
                    # best_model is a string model ID
                    self.event_bus.publish("workflow_model_selected", {
                        "model": best_model,
                        "task_type": task_type.value,
                    })
                    logger.info(f"Model selected: {best_model} (route={task_type.value})")
                else:
                    self.event_bus.publish("workflow_model_selected", {"model": "automatic"})
            except Exception as e:
                logger.warning(f"Model selection failed: {e}")

        # --- PHASE 5: Decomposition & Execution ---
        self.event_bus.publish("workflow_stage_changed", {"stage": "Decomposition & Execution"})
        try:
            engineering_tasks = self.task_decomposer.decompose(task, context_package)
            logger.info(f"Decomposed into {len(engineering_tasks)} engineering tasks")
        except Exception as e:
            logger.error(f"Task decomposition failed: {e}")
            self.event_bus.publish("workflow_failed", {"error": f"Decomposition failed: {e}"})
            return

        if self.execution_engine:
            try:
                self.execution_engine.submit_engineering_tasks(engineering_tasks)
                self.event_bus.publish("workflow_generation_started", {
                    "task_count": len(engineering_tasks),
                })
                logger.info("Engineering tasks dispatched to ExecutionEngine")

                # --- PHASE 6: Record decision in memory ---
                try:
                    self._record_decisions(
                        prompt=prompt,
                        task=task,
                        engineering_tasks=engineering_tasks,
                        best_model=best_model,
                    )
                except Exception as me:
                    logger.debug(f"Memory update skipped: {me}")

            except Exception as e:
                logger.error(f"ExecutionEngine submission failed: {e}")
                self.event_bus.publish("workflow_failed", {"error": str(e)})
        else:
            self.event_bus.publish("workflow_failed", {"error": "No execution engine available"})
    
    # ── Routing ─────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_task_type(task) -> TaskType:
        """Turn the analyzer's routing hint into a real router TaskType.

        Previously this only ever chose between CODING and SIMPLE_CHAT, so the
        router's ARCHITECTURE / DOCUMENTATION / HEAVY_REASONING / LARGE_CONTEXT
        scoring branches were unreachable. Now planning-ish prompts can reach a
        stronger model while cheap edits stay on a fast local one.
        """
        hint = getattr(task, "routing_task_type", "") or ""
        try:
            return TaskType(hint)
        except ValueError:
            pass
        return TaskType.CODING if getattr(task, "requires_code_changes", False) else TaskType.SIMPLE_CHAT

    # ── Memory loop (v1.9.1) ────────────────────────────────────────────────

    def _record_decisions(self, prompt: str, task, engineering_tasks: list,
                          best_model: Optional[str]) -> None:
        """Record one decision per dispatched engineering task.

        Recording per-task (rather than once per prompt) is what lets us later
        mark the *specific* decision success/failure when its task finishes,
        and feed the changed files back into ProjectMemory.
        """
        if not self.decision_memory:
            return

        complexity = getattr(getattr(task, "estimated_complexity", None), "value", "unknown")
        reasoning = (
            f"complexity={complexity}, model={best_model or 'automatic'}, "
            f"decomposed_into={len(engineering_tasks)}"
        )

        for et in engineering_tasks:
            et_id = getattr(et, "id", "") or ""
            affected = list(getattr(et, "affected_files", []) or [])
            decision = self.decision_memory.record(
                task_id=et_id,
                prompt=prompt,
                choice=f"{getattr(et, 'title', 'task')}: {getattr(et, 'description', '')[:200]}",
                reasoning=reasoning,
                model_used=str(best_model or ""),
                metadata={"affected_files": affected},
            )
            if et_id:
                self._active_decisions[et_id] = {
                    "decision_id": decision.decision_id,
                    "affected_files": affected,
                    "prompt": prompt,
                }

        if self.project_memory:
            self.project_memory.remember(
                category="general",
                content=f"Ran '{prompt[:80]}' as {len(engineering_tasks)} task(s) "
                        f"using {best_model or 'automatic'}",
                source="workflow_coordinator",
            )

    def _close_decision(self, task_id: str, outcome: str, detail: str = "") -> None:
        """Mark a recorded decision success/failure and teach ProjectMemory."""
        entry = self._active_decisions.pop(task_id, None)
        if not entry:
            return
        try:
            if self.decision_memory:
                self.decision_memory.update_outcome(entry["decision_id"], outcome)
            if self.project_memory:
                # This is the call that was previously never made anywhere.
                self.project_memory.update_from_task(
                    task_id=task_id,
                    outcome=outcome,
                    files_changed=entry.get("affected_files", []),
                )
                if outcome == "failure" and detail:
                    self.project_memory.remember(
                        category="issue",
                        content=f"Task '{entry.get('prompt', '')[:60]}' failed: {detail[:200]}",
                        source="workflow_coordinator",
                        confidence=0.9,
                    )
        except Exception as e:
            logger.debug(f"Could not close decision for {task_id}: {e}")

    def _on_task_outcome_success(self, payload: Dict[str, Any]) -> None:
        self._close_decision(payload.get("task_id", ""), "success")

    def _on_task_outcome_failure(self, payload: Dict[str, Any]) -> None:
        self._close_decision(payload.get("task_id", ""),
                             "failure", payload.get("error", ""))

    def _on_verification_complete(self, payload: Dict[str, Any]) -> None:
        """Verification is the stronger signal — let it override the outcome."""
        task_id = payload.get("task_id", "")
        if not task_id or task_id not in self._active_decisions:
            return
        passed = payload.get("passed", payload.get("success"))
        if passed is None:
            return
        self._close_decision(task_id, "success" if passed else "failure",
                             str(payload.get("summary", "verification failed")))

    def _on_pause_request(self, payload: Dict[str, Any]):
        """Handle workflow pause request from UI."""
        if self.execution_engine:
            # Pause all running tasks
            running = self.execution_engine.get_running_tasks()
            for task in running:
                self.execution_engine.pause_task(task.id)
            logger.info(f"Paused {len(running)} running tasks")
            self.event_bus.publish("workflow_paused", {"count": len(running)})
    
    def _on_resume_request(self, payload: Dict[str, Any]):
        """Handle workflow resume request from UI."""
        if self.execution_engine:
            # Resume all paused tasks
            paused = [t for t in self.execution_engine.get_all_tasks() if t.state.value == "paused"]
            for task in paused:
                self.execution_engine.resume_task(task.id)
            logger.info(f"Resumed {len(paused)} paused tasks")
            self.event_bus.publish("workflow_resumed", {"count": len(paused)})
    
    def _on_cancel_request(self, payload: Dict[str, Any]):
        """Handle workflow cancel request from UI."""
        if self.execution_engine:
            # Cancel all non-terminal tasks
            all_tasks = self.execution_engine.get_all_tasks()
            cancelled_count = 0
            for task in all_tasks:
                if not task.is_terminal:
                    self.execution_engine.cancel_task(task.id, by_user="UI")
                    cancelled_count += 1
            logger.info(f"Cancelled {cancelled_count} tasks")
            self.event_bus.publish("workflow_cancelled", {"count": cancelled_count})



from agent.code_editing import SmartPatchEngine, ShadowWorkspaceSandbox, FIMCompletionEngine, NextEditPredictor
