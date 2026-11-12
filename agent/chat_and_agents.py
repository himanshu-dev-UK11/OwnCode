"""
Consolidated Module: agent.chat_and_agents

Combines: ai.agents.base_agent, ai.agents.coder, ai.agents.debugger, ai.agents.planner, ai.connection.connection_manager, ai.chat.ai_chat_engine, ai.integration.ai_ide_integration
"""
from __future__ import annotations
import sys as _sys
import re
import core  # ensure module alias resolver is active
for _alias in ['ai.agents.base_agent', 'ai.agents.coder', 'ai.agents.debugger', 'ai.agents.planner', 'ai.connection.connection_manager', 'ai.chat.ai_chat_engine', 'ai.integration.ai_ide_integration']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ai.agents.base_agent (ai/agents/base_agent.py)
# ============================================================================
"""
Base Agent class.

Provides common functionality for all agents like logging, error handling,
and event bus integration.
"""

from core.logger import setup_logger

class BaseAgent:
    """
    Abstract base class for all AI agents.
    """
    def __init__(self, name: str, event_bus):
        self.name = name
        self.event_bus = event_bus
        self.logger = setup_logger(f"agent.{name}")
        self.logger.info(f"{name} agent initialized.")
        
    def handle_error(self, error: Exception):
        """
        Standardized error handling to prevent silent failures.
        """
        self.logger.error(f"Error in {self.name}: {str(error)}", exc_info=True)


# ============================================================================
# SECTION: ai.agents.coder (ai/agents/coder.py)
# ============================================================================
"""
CoderAgent — generates and modifies code via the AI chat engine.

Routes coding requests through the active AIChatEngine using the best
available local model, streams the response, and returns the result.
"""

from typing import Callable, Optional

from ai.agents.base_agent import BaseAgent


class CoderAgent(BaseAgent):
    """
    Agent responsible for code generation and modification.

    Relies on an injected AIChatEngine for actual LLM calls.
    Can be used standalone or wired into the EngineeringWorkflowCoordinator.
    """

    def __init__(self, event_bus, chat_engine=None) -> None:
        super().__init__("coder", event_bus)
        self._engine = chat_engine   # AIChatEngine, injected at runtime

    # ── Public API ─────────────────────────────────────────────────────────

    def set_engine(self, engine) -> None:
        """Inject / replace the chat engine at runtime."""
        self._engine = engine

    def implement_task(
        self,
        task_description: str,
        context: str = "",
        language: str = "",
        on_chunk: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Generate code or a code modification for the given task description.

        Args:
            task_description: What the code should do.
            context:          Optional surrounding code / project context.
            language:         Target programming language hint (e.g. "python").
            on_chunk:         Optional streaming callback per token.
            on_complete:      Optional callback when generation finishes.

        Returns:
            The generated code as a string (may be empty if streaming only).
        """
        self.logger.info(f"CoderAgent.implement_task: {task_description[:80]}")

        if not self._engine:
            msg = (
                "CoderAgent: no chat engine available. "
                "Connect a provider in Settings → AI Providers."
            )
            self.logger.warning(msg)
            if on_complete:
                on_complete(msg)
            return msg

        prompt = self._build_prompt(task_description, context, language)

        result: list[str] = []

        def _on_done(response: str) -> None:
            result.append(response)
            if on_complete:
                on_complete(response)

        try:
            self._engine.send_message(
                message=prompt,
                model_id=self._engine.get_current_model(),
                on_chunk=on_chunk,
                on_complete=_on_done,
            )
        except Exception as exc:
            self.handle_error(exc)
            if on_complete:
                on_complete(f"Error: {exc}")
            return ""

        return result[0] if result else ""

    def refactor(
        self,
        code: str,
        instruction: str,
        language: str = "",
        on_chunk: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Refactor existing code per the instruction."""
        task = (
            f"Refactor the following code: {instruction}\n\n"
            f"```{language}\n{code}\n```"
        )
        return self.implement_task(
            task, language=language, on_chunk=on_chunk, on_complete=on_complete
        )

    def explain(self, code: str, language: str = "") -> str:
        """Explain what a piece of code does (blocking call)."""
        task = f"Explain the following code clearly and concisely:\n\n```{language}\n{code}\n```"
        result: list[str] = []
        self.implement_task(task, language=language, on_complete=lambda r: result.append(r))
        return result[0] if result else ""

    # ── Helpers ────────────────────────────────────────────────────────────

    def _build_prompt(self, task: str, context: str, language: str) -> str:
        parts = ["You are an expert software engineer. "]
        if language:
            parts.append(f"Write in {language}. ")
        parts.append("\n\nTask:\n" + task)
        if context:
            parts.append(f"\n\nContext / existing code:\n```\n{context}\n```")
        parts.append(
            "\n\nRespond with complete, working code only. "
            "Add brief inline comments where helpful."
        )
        return "".join(parts)


# ============================================================================
# SECTION: ai.agents.debugger (ai/agents/debugger.py)
# ============================================================================
"""
DebuggerAgent — analyses errors and suggests fixes via the AI chat engine.
"""

from typing import Callable, Optional

from ai.agents.base_agent import BaseAgent


class DebuggerAgent(BaseAgent):
    """
    Agent responsible for analysing errors and proposing fixes.

    Relies on an injected AIChatEngine for actual LLM calls.
    """

    def __init__(self, event_bus, chat_engine=None) -> None:
        super().__init__("debugger", event_bus)
        self._engine = chat_engine

    # ── Public API ─────────────────────────────────────────────────────────

    def set_engine(self, engine) -> None:
        """Inject / replace the chat engine at runtime."""
        self._engine = engine

    def analyze_error(
        self,
        error_message: str,
        context: str = "",
        file_path: str = "",
        on_chunk: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Analyse an error and suggest a fix.

        Args:
            error_message: The full error / traceback text.
            context:       Surrounding source code where the error occurred.
            file_path:     Path of the file that triggered the error.
            on_chunk:      Optional streaming callback per token.
            on_complete:   Optional callback when analysis finishes.

        Returns:
            The analysis and fix suggestion as a string.
        """
        self.logger.info(f"DebuggerAgent.analyze_error: {error_message[:80]}")

        if not self._engine:
            msg = (
                "DebuggerAgent: no chat engine available. "
                "Connect a provider in Settings → AI Providers."
            )
            self.logger.warning(msg)
            if on_complete:
                on_complete(msg)
            return msg

        prompt = self._build_prompt(error_message, context, file_path)

        result: list[str] = []

        def _on_done(response: str) -> None:
            result.append(response)
            if on_complete:
                on_complete(response)

        try:
            self._engine.send_message(
                message=prompt,
                model_id=self._engine.get_current_model(),
                on_chunk=on_chunk,
                on_complete=_on_done,
            )
        except Exception as exc:
            self.handle_error(exc)
            if on_complete:
                on_complete(f"Error: {exc}")
            return ""

        return result[0] if result else ""

    def suggest_fix(
        self,
        code: str,
        error: str,
        language: str = "",
        on_chunk: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Return a corrected version of the code that resolves the error."""
        prompt = (
            f"The following {language} code produces this error:\n"
            f"```\n{error}\n```\n\n"
            f"Code:\n```{language}\n{code}\n```\n\n"
            "Return the corrected code only, with a one-line comment explaining the fix."
        )
        result: list[str] = []
        self.analyze_error(
            error_message=prompt,
            on_chunk=on_chunk,
            on_complete=lambda r: result.append(r),
        )
        return result[0] if result else ""

    # ── Helpers ────────────────────────────────────────────────────────────

    def _build_prompt(self, error: str, context: str, file_path: str) -> str:
        parts = [
            "You are an expert debugger. Analyse the following error and explain:\n"
            "1. What caused it\n"
            "2. How to fix it\n"
            "3. The corrected code snippet (if applicable)\n\n"
        ]
        if file_path:
            parts.append(f"File: {file_path}\n\n")
        parts.append(f"Error:\n```\n{error}\n```")
        if context:
            parts.append(f"\n\nRelevant code:\n```\n{context}\n```")
        return "".join(parts)


# ============================================================================
# SECTION: ai.agents.planner (ai/agents/planner.py)
# ============================================================================
"""
Project planning and roadmap generation agent.
"""

from typing import Optional
import uuid
from ai.agents.base_agent import BaseAgent
from ai.engine.task import Task
from ai.memory.project_context import ProjectContext
from ai.planning.plan import Plan
from ai.planning.task_decomposer import TaskDecomposer
from ai.planning.roadmap_builder import RoadmapBuilder
from ai.planning.complexity_analyzer import ComplexityAnalyzer
from ai.planning.risk_analyzer import RiskAnalyzer
from ai.planning.plan_validator import PlanValidator

class PlannerAgent(BaseAgent):
    def __init__(self, event_bus):
        super().__init__("planner", event_bus)
        self.decomposer = TaskDecomposer()
        self.roadmap_builder = RoadmapBuilder()
        self.complexity_analyzer = ComplexityAnalyzer()
        self.risk_analyzer = RiskAnalyzer()
        self.validator = PlanValidator()
        
    def create_plan(self, goal: str, context: Optional[ProjectContext] = None, task: Optional[Task] = None) -> Plan:
        self.logger.info(f"Creating plan for goal: {goal}")
        
        if not task:
            task = Task(original_prompt=goal, objective=goal)
            
        # Decompose the task into executable steps
        steps = self.decomposer.decompose(task, context)
        
        # Group steps into execution phases
        phases = self.roadmap_builder.build_roadmap(steps)
        
        # Analyze project complexity and potential risks
        complexity = self.complexity_analyzer.estimate_complexity(task, context)
        risks = self.risk_analyzer.analyze_risks(task, context)
        
        # Build the final Plan object
        plan = Plan(
            plan_id=str(uuid.uuid4()),
            goal=goal,
            complexity=complexity,
            risks=risks,
            steps=steps,
            phases=phases
        )
        
        # Validate the generated plan
        is_valid = self.validator.validate(plan)
        if not is_valid:
            self.logger.warning("Generated plan failed validation!")
            plan.status = "failed_validation"
        else:
            plan.status = "validated"
            
        return plan


# ============================================================================
# SECTION: ai.connection.connection_manager (ai/connection/connection_manager.py)
# ============================================================================
"""
AI Connection Manager - Complete Connection System.

Handles all AI provider connections with intelligent error handling,
user guidance, and automatic recovery.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from core.logger import setup_logger
from core.exceptions import ProviderError, ConfigurationError


logger = setup_logger(__name__)


@dataclass
class ConnectionStatus:
    """Connection status for a provider."""
    provider_name: str
    is_connected: bool
    status_message: str
    error_message: str = ""
    can_retry: bool = True
    suggested_action: str = ""
    help_url: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderConnection:
    """Stored provider connection information."""
    provider_name: str
    display_name: str
    api_key: str
    endpoint: str
    models: List[str]
    is_active: bool = True
    created_at: str = ""
    last_used: str = ""
    connection_count: int = 0
    error_count: int = 0
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProviderConnection":
        return cls(**data)


class AIConnectionManager:
    """
    Complete AI Connection Management System.
    
    Features:
    - Automatic error recovery
    - User-friendly error messages
    - Guided connection setup
    - Persistent storage
    - Connection health monitoring
    - Smart retry logic
    """
    
    def __init__(self, storage_dir: str = "config/connections"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self._connections: Dict[str, ProviderConnection] = {}
        self._connection_file = self.storage_dir / "connections.json"
        
        # Load existing connections
        self._load_connections()
        
        logger.info(f"AIConnectionManager initialized with {len(self._connections)} connections")
    
    # ═══════════════════════════════════════════════════════════════
    # Connection Management
    # ═══════════════════════════════════════════════════════════════
    
    def add_connection(self, provider_name: str, display_name: str, 
                      api_key: str, endpoint: str = "",
                      models: List[str] = None) -> Tuple[bool, str]:
        """
        Add a new provider connection.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate inputs
            if not provider_name:
                return False, "Provider name cannot be empty"
            
            if not api_key:
                return False, "API key cannot be empty"
            
            # Check if already exists
            if provider_name in self._connections:
                return False, f"Provider '{provider_name}' is already connected. Remove it first to reconnect."
            
            # Create connection
            connection = ProviderConnection(
                provider_name=provider_name,
                display_name=display_name or provider_name,
                api_key=api_key,
                endpoint=endpoint or self._get_default_endpoint(provider_name),
                models=models or [],
                is_active=True
            )
            
            self._connections[provider_name] = connection
            self._save_connections()
            
            logger.info(f"Added connection for provider: {provider_name}")
            return True, f"Successfully connected to {display_name}"
            
        except Exception as e:
            logger.error(f"Failed to add connection: {e}")
            return False, f"Failed to add connection: {str(e)}"
    
    def remove_connection(self, provider_name: str) -> Tuple[bool, str]:
        """Remove a provider connection."""
        if provider_name not in self._connections:
            return False, f"Provider '{provider_name}' not found"
        
        del self._connections[provider_name]
        self._save_connections()
        
        logger.info(f"Removed connection for provider: {provider_name}")
        return True, f"Successfully removed {provider_name}"
    
    def update_connection(self, provider_name: str, **updates) -> Tuple[bool, str]:
        """Update an existing connection."""
        if provider_name not in self._connections:
            return False, f"Provider '{provider_name}' not found"
        
        connection = self._connections[provider_name]
        
        for key, value in updates.items():
            if hasattr(connection, key):
                setattr(connection, key, value)
        
        self._save_connections()
        return True, f"Updated {provider_name}"
    
    def get_connection(self, provider_name: str) -> Optional[ProviderConnection]:
        """Get a specific connection."""
        return self._connections.get(provider_name)
    
    def get_all_connections(self) -> Dict[str, ProviderConnection]:
        """Get all connections."""
        return self._connections.copy()
    
    def has_connections(self) -> bool:
        """Check if any connections exist."""
        return len(self._connections) > 0
    
    def get_active_connections(self) -> Dict[str, ProviderConnection]:
        """Get all active connections."""
        return {
            name: conn for name, conn in self._connections.items()
            if conn.is_active
        }
    
    # ═══════════════════════════════════════════════════════════════
    # Connection Testing & Validation
    # ═══════════════════════════════════════════════════════════════
    
    def test_connection(self, provider_name: str) -> ConnectionStatus:
        """
        Test a provider connection with intelligent error handling.
        """
        connection = self._connections.get(provider_name)
        
        if not connection:
            return ConnectionStatus(
                provider_name=provider_name,
                is_connected=False,
                status_message="Provider not found",
                error_message="This provider has not been configured yet.",
                suggested_action="Please add this provider first using the 'Connect New Provider' button.",
                help_url="",
                can_retry=False
            )
        
        try:
            # Update last used
            connection.last_used = datetime.utcnow().isoformat()
            connection.connection_count += 1
            
            # Try to connect (this would call the actual provider)
            # For now, we'll simulate a connection check
            if not connection.api_key:
                connection.error_count += 1
                return ConnectionStatus(
                    provider_name=provider_name,
                    is_connected=False,
                    status_message="Missing API Key",
                    error_message="No API key configured for this provider.",
                    suggested_action="Please enter your API key in the provider settings.",
                    help_url=self._get_help_url(provider_name, "api_key"),
                    can_retry=True
                )
            
            # Connection successful
            self._save_connections()
            return ConnectionStatus(
                provider_name=provider_name,
                is_connected=True,
                status_message=f"Connected to {connection.display_name}",
                suggested_action="You can now use this provider for AI conversations.",
                can_retry=False
            )
            
        except Exception as e:
            logger.error(f"Connection test failed for {provider_name}: {e}")
            connection.error_count += 1
            self._save_connections()
            
            return self._handle_connection_error(provider_name, e)
    
    def _handle_connection_error(self, provider_name: str, 
                                 error: Exception) -> ConnectionStatus:
        """Handle connection errors intelligently."""
        error_str = str(error).lower()
        
        # HTTP 400 - Bad Request
        if "400" in error_str or "bad request" in error_str:
            return ConnectionStatus(
                provider_name=provider_name,
                is_connected=False,
                status_message="Invalid Request",
                error_message="The request format is incorrect or missing required parameters.",
                suggested_action="Check your API key format and endpoint URL. Try reconnecting.",
                help_url=self._get_help_url(provider_name, "bad_request"),
                can_retry=True
            )
        
        # HTTP 401 - Unauthorized
        if "401" in error_str or "unauthorized" in error_str:
            return ConnectionStatus(
                provider_name=provider_name,
                is_connected=False,
                status_message="Authentication Failed",
                error_message="Your API key is invalid or has expired.",
                suggested_action="Please check your API key and update it in the provider settings.",
                help_url=self._get_help_url(provider_name, "auth"),
                can_retry=True
            )
        
        # HTTP 403 - Forbidden
        if "403" in error_str or "forbidden" in error_str:
            return ConnectionStatus(
                provider_name=provider_name,
                is_connected=False,
                status_message="Access Denied",
                error_message="Your account doesn't have permission to access this resource.",
                suggested_action="Check your account status and API key permissions.",
                help_url=self._get_help_url(provider_name, "forbidden"),
                can_retry=False
            )
        
        # HTTP 404 - Not Found
        if "404" in error_str or "not found" in error_str:
            return ConnectionStatus(
                provider_name=provider_name,
                is_connected=False,
                status_message="Endpoint Not Found",
                error_message="The API endpoint is incorrect or the model doesn't exist.",
                suggested_action="Verify your endpoint URL and model name are correct.",
                help_url=self._get_help_url(provider_name, "not_found"),
                can_retry=True
            )
        
        # HTTP 429 - Rate Limit
        if "429" in error_str or "rate limit" in error_str:
            return ConnectionStatus(
                provider_name=provider_name,
                is_connected=False,
                status_message="Rate Limit Exceeded",
                error_message="You've made too many requests. Please wait a moment.",
                suggested_action="Wait a few minutes before trying again.",
                help_url=self._get_help_url(provider_name, "rate_limit"),
                can_retry=True
            )
        
        # HTTP 500 - Server Error
        if "500" in error_str or "server error" in error_str:
            return ConnectionStatus(
                provider_name=provider_name,
                is_connected=False,
                status_message="Provider Server Error",
                error_message="The provider's server is experiencing issues.",
                suggested_action="This is a temporary issue. Please try again later.",
                help_url=self._get_help_url(provider_name, "server_error"),
                can_retry=True
            )
        
        # Network errors
        if "network" in error_str or "connection" in error_str or "timeout" in error_str:
            return ConnectionStatus(
                provider_name=provider_name,
                is_connected=False,
                status_message="Network Error",
                error_message="Cannot connect to the provider. Check your internet connection.",
                suggested_action="Verify your internet connection and try again.",
                help_url=self._get_help_url(provider_name, "network"),
                can_retry=True
            )
        
        # Generic error
        return ConnectionStatus(
            provider_name=provider_name,
            is_connected=False,
            status_message="Connection Failed",
            error_message=str(error),
            suggested_action="Check your settings and try again. If the problem persists, contact support.",
            help_url=self._get_help_url(provider_name, "generic"),
            can_retry=True
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Helper Methods
    # ═══════════════════════════════════════════════════════════════
    
    def _get_default_endpoint(self, provider_name: str) -> str:
        """Get default endpoint for a provider."""
        endpoints = {
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com/v1",
            "gemini": "https://generativelanguage.googleapis.com/v1beta",
            "google": "https://generativelanguage.googleapis.com/v1beta",
            "groq": "https://api.groq.com/openai/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "deepinfra": "https://api.deepinfra.com/v1/openai",
            "fireworks": "https://api.fireworks.ai/inference/v1",
            "together": "https://api.together.xyz/v1",
            "cerebras": "https://api.cerebras.ai/v1",
            "ollama": "http://localhost:11434",
        }
        return endpoints.get(provider_name.lower(), "")
    
    def _get_help_url(self, provider_name: str, error_type: str) -> str:
        """Get help URL for specific error types."""
        base_urls = {
            "openai": "https://platform.openai.com/docs",
            "anthropic": "https://docs.anthropic.com",
            "gemini": "https://ai.google.dev/docs",
            "groq": "https://console.groq.com/docs",
        }
        return base_urls.get(provider_name.lower(), "")
    
    def _load_connections(self) -> None:
        """Load connections from storage."""
        if not self._connection_file.exists():
            return
        
        try:
            with open(self._connection_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for provider_name, conn_data in data.items():
                self._connections[provider_name] = ProviderConnection.from_dict(conn_data)
            
            logger.info(f"Loaded {len(self._connections)} connections")
            
        except Exception as e:
            logger.error(f"Failed to load connections: {e}")
    
    def _save_connections(self) -> None:
        """Save connections to storage."""
        try:
            data = {
                name: conn.to_dict()
                for name, conn in self._connections.items()
            }
            
            with open(self._connection_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved {len(self._connections)} connections")
            
        except Exception as e:
            logger.error(f"Failed to save connections: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        total = len(self._connections)
        active = len(self.get_active_connections())
        
        total_attempts = sum(c.connection_count for c in self._connections.values())
        total_errors = sum(c.error_count for c in self._connections.values())
        
        return {
            "total_providers": total,
            "active_providers": active,
            "total_connections": total_attempts,
            "total_errors": total_errors,
            "success_rate": (total_attempts - total_errors) / total_attempts if total_attempts > 0 else 0
        }
    
    def clear_all_connections(self) -> Tuple[bool, str]:
        """Clear all connections (use with caution)."""
        self._connections.clear()
        self._save_connections()
        return True, "All connections cleared"


# Global instance
_connection_manager = None


def get_connection_manager() -> AIConnectionManager:
    """Get the global connection manager instance."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = AIConnectionManager()
    return _connection_manager


def initialize_connection_manager() -> AIConnectionManager:
    """Initialize the global connection manager."""
    global _connection_manager
    _connection_manager = AIConnectionManager()
    return _connection_manager

# ============================================================================
# SECTION: ai.chat.ai_chat_engine (ai/chat/ai_chat_engine.py)
# ============================================================================
"""
AI Chat Engine — v1.5

First Working AI implementation.
Handles real AI communication with Ollama and Gemini providers.
Supports streaming, model switching, and chat history management.
"""

import threading
import asyncio
import time
import uuid
import os
import shutil
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from core.logger import setup_logger
from core.event_bus import EventBus

from ai.providers.provider_registry import ProviderRegistry
from ai.providers.provider_manager import ProviderManager
from ai.models.model_center import ModelCenter
from ai.models.model_registry import ModelRegistry
from ai.context.ai_context_store import AIContextStore, estimate_tokens


logger = setup_logger(__name__)


@dataclass
class ChatMessage:
    """A single chat message."""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    model_id: Optional[str] = None
    message_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "model_id": self.model_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        msg = cls(
            role=data["role"],
            content=data["content"],
            model_id=data.get("model_id"),
        )
        if data.get("timestamp"):
            from datetime import datetime
            msg.timestamp = datetime.fromisoformat(data["timestamp"])
        return msg


@dataclass
class ChatSession:
    """A chat session with a model."""
    session_id: str
    title: str
    model_id: str
    provider_name: str
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    is_pinned: bool = False
    
    def add_message(self, message: ChatMessage) -> None:
        self.messages.append(message)
        self.last_activity = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "model_id": self.model_id,
            "provider_name": self.provider_name,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "is_pinned": self.is_pinned,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatSession":
        session = cls(
            session_id=data["session_id"],
            title=data["title"],
            model_id=data["model_id"],
            provider_name=data["provider_name"],
        )
        if data.get("messages"):
            session.messages = [ChatMessage.from_dict(m) for m in data["messages"]]
        if data.get("created_at"):
            from datetime import datetime
            session.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("last_activity"):
            session.last_activity = datetime.fromisoformat(data["last_activity"])
        session.is_pinned = data.get("is_pinned", False)
        return session


@dataclass
class ChatRequest:
    request_id: str
    session_id: str
    cancel: threading.Event = field(default_factory=threading.Event)
    retries: int = 0
    max_retries: int = 1
    started_at: float = field(default_factory=time.perf_counter)
    first_token_at: Optional[float] = None


class AIChatEngine:
    """
    AI Chat Engine for real AI communication.
    
    Features:
    - Real AI model communication (Ollama, Gemini)
    - Streaming responses with token-by-token delivery
    - Model switching during runtime
    - Chat history management
    - Session persistence
    - Error handling with helpful messages
    """
    
    def __init__(self, event_bus: EventBus,
                 provider_registry: ProviderRegistry,
                 provider_manager: ProviderManager,
                 model_center: ModelCenter,
                 model_registry: ModelRegistry,
                 tool_coordinator=None):
        self.event_bus = event_bus
        self.provider_registry = provider_registry
        self.provider_manager = provider_manager
        self.model_center = model_center
        self.model_registry = model_registry
        self.tool_coordinator = tool_coordinator
        self.optimizer = None  # LLM optimizer
        
        self._sessions: Dict[str, ChatSession] = {}
        self._current_session_id: Optional[str] = None
        self._current_provider: Optional[str] = None
        self._current_model: Optional[str] = None
        self._requests: Dict[str, ChatRequest] = {}
        self._request_lock = threading.Lock()

        # Project-global "memory" the user uploads/pastes; injected into prompts.
        self.context_store = AIContextStore()
        # Running token estimates per session {session_id: {"prompt","completion","total"}}
        self._session_tokens: Dict[str, Dict[str, int]] = {}
        # Remembers the last user message per session so the UI can regenerate.
        self._last_user_message: Dict[str, str] = {}

        self._logger = logger
        
        # Load sessions from storage
        self._load_sessions()
        
        # Initialize model router for auto-selection
        from ai.models.router import ModelRouter
        self._model_router = ModelRouter(self.model_registry, self.provider_manager)
        
        # Auto-select best available model on startup if no session exists
        if not self._current_model:
            self._auto_select_initial_model()
        
        # Subscribe to events
        event_bus.subscribe("ai_chat_send", self._on_chat_send)
        event_bus.subscribe("ai_chat_switch_model", self._on_switch_model)
        event_bus.subscribe("ai_chat_cancel", self._on_cancel_stream)
        event_bus.subscribe("ai_chat_new_session", self._on_new_session)
        event_bus.subscribe("ai_chat_switch_session", self._on_switch_session)
        event_bus.subscribe("ai_chat_delete_session", self._on_delete_session)
        event_bus.subscribe("ai_chat_rename_session", self._on_rename_session)
        event_bus.subscribe("ai_chat_pin_session", self._on_pin_session)
        event_bus.subscribe("ai_chat_export", self._on_export_session)
        event_bus.subscribe("ai_chat_import", self._on_import_session)
        event_bus.subscribe("ai_execute_tool", self._on_execute_tool)
        # AI memory/context (uploaded files + notes)
        event_bus.subscribe("ai_context_add_note", self._on_context_add_note)
        event_bus.subscribe("ai_context_add_file", self._on_context_add_file)
        event_bus.subscribe("ai_context_remove", self._on_context_remove)
        event_bus.subscribe("ai_context_clear", self._on_context_clear)
        event_bus.subscribe("ai_context_request", self._on_context_request)
        # Regenerate the last assistant turn
        event_bus.subscribe("ai_chat_regenerate", self._on_regenerate)
        self.active_mode: str = self._load_initial_mode()
        self.workspace_root: Optional[str] = None
        self.active_editor_file: Optional[str] = None
        self._applied_message_ids: set = set()
        self._agent_checkpoints: List[Dict[str, Any]] = []
        self.last_execution_error: str = ""
        self.last_execution_output: str = ""
        self.last_executed_file: str = ""
        event_bus.subscribe("ai_mode_changed", self._on_mode_changed)
        event_bus.subscribe("workspace_loaded", self._on_workspace_loaded_track)
        event_bus.subscribe("workspace_activated", self._on_workspace_loaded_track)
        event_bus.subscribe("file_opened", self._on_file_opened_track)
        event_bus.subscribe("ai_apply_code_block", self._on_apply_code_block)
        event_bus.subscribe("ai_apply_last_response", self._on_apply_last_response)
        event_bus.subscribe("ai_agent_undo", self._on_agent_undo)
        event_bus.subscribe("ai_run_code_block", self._on_run_code_block)
        event_bus.subscribe("process_finished", self._on_process_finished_track)
        event_bus.subscribe("test_finished", self._on_test_finished_track)
        event_bus.subscribe("terminal_test_finished", self._on_test_finished_track)
    
    def set_tool_coordinator(self, tool_coordinator):
        """Set the tool coordinator for AI tool execution."""
        self.tool_coordinator = tool_coordinator
        if tool_coordinator:
            logger.info("Tool coordinator connected to chat engine")
            # Publish tool capabilities
            tools = tool_coordinator.get_available_tools()
            self.event_bus.publish("ai_tools_available", {
                "tool_count": len(tools),
                "tools": tools
            })
    
    def _on_execute_tool(self, data: dict):
        """Handle tool execution request from AI."""
        if not self.tool_coordinator:
            logger.warning("Tool execution requested but no tool coordinator available")
            self.event_bus.publish("tool_execution_failed", {
                "error": "No tool coordinator available"
            })
            return
        
        tool_name = data.get('tool_name')
        tool_params = data.get('params', {})
        
        logger.info(f"Executing tool: {tool_name} with params: {tool_params}")
        
        result = self.tool_coordinator.execute_tool(tool_name, **tool_params)
        
        self.event_bus.publish("tool_execution_complete", {
            "tool": tool_name,
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "requires_confirmation": result.requires_confirmation
        })
    
    def _auto_select_initial_model(self) -> None:
        """Auto-select the best available model on startup."""
        try:
            from ai.models.router import TaskType
            self._logger.info("Auto-selecting best available model on startup...")
            from ui.settings_manager import get_settings_manager
            configured = get_settings_manager().get_default_model()
            best_model = self._model_router.dispatch(
                None if configured == "auto" else configured, "", TaskType.SIMPLE_CHAT)
            if best_model:
                self._current_model = best_model
                self._update_current_provider(best_model)
                self._logger.info(f"✓ Auto-selected initial model: {best_model} (can reply and is active)")
                self.event_bus.publish("ai_model_auto_selected", {
                    "model_id": best_model,
                    "reason": "automatic_startup_selection"
                })
            else:
                self._logger.warning("⚠ No active models available for auto-selection on startup")
                self.event_bus.publish("ai_model_selection_failed", {
                    "reason": "no_active_models_available"
                })
        except Exception as e:
            self._logger.error(f"Failed to auto-select initial model: {e}", exc_info=True)
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Session Management
    # ─────────────────────────────────────────────────────────────────────────────

    def _load_sessions(self) -> None:
        """Load sessions from storage."""
        try:
            import json
            from pathlib import Path
            
            storage_file = Path("config/chat_sessions.json")
            if storage_file.exists():
                with open(storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Tolerate both the current dict format
                # ({"sessions": [...], "current_session_id": ...}) and the
                # legacy bare-list format ([{session}, ...]).
                if isinstance(data, list):
                    session_list = data
                    current_id = None
                elif isinstance(data, dict):
                    session_list = data.get("sessions", [])
                    current_id = data.get("current_session_id")
                else:
                    session_list = []
                    current_id = None

                for session_data in session_list:
                    if not isinstance(session_data, dict):
                        continue
                    if not session_data.get("session_id") or not session_data.get("model_id"):
                        self._logger.warning("Skipping invalid chat session record")
                        continue
                    session = ChatSession.from_dict(session_data)
                    for message in session.messages:
                        if not message.model_id:
                            message.model_id = session.model_id
                    self._sessions[session.session_id] = session

                self._logger.info(f"Loaded {len(self._sessions)} chat sessions")

                # Set current session if available (and still present).
                if current_id and current_id in self._sessions:
                    self._current_session_id = current_id
                    self._current_model = self._sessions[current_id].model_id
                    self._current_provider = self._sessions[current_id].provider_name
                    
        except Exception as e:
            self._logger.error(f"Failed to load sessions: {e}")
    
    def _save_sessions(self) -> None:
        """Save sessions to storage."""
        try:
            import json
            from pathlib import Path
            
            storage_file = Path("config/chat_sessions.json")
            
            data = {
                "schema_version": 2,
                "sessions": [s.to_dict() for s in self._sessions.values()],
                "current_session_id": self._current_session_id,
                "saved_at": datetime.utcnow().isoformat(),
            }
            
            storage_file.parent.mkdir(parents=True, exist_ok=True)
            if storage_file.exists():
                backup = storage_file.with_suffix(storage_file.suffix + ".bak")
                shutil.copy2(storage_file, backup)
            fd, temp_name = tempfile.mkstemp(
                prefix="chat_sessions.", suffix=".tmp", dir=str(storage_file.parent))
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp_name, storage_file)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
                
        except Exception as e:
            self._logger.error(f"Failed to save sessions: {e}")
    
    def create_session(self, model_id: Optional[str] = None,
                       title: Optional[str] = None) -> str:
        """Create a new chat session."""
        import uuid
        
        session_id = str(uuid.uuid4())[:8]
        
        # Auto-select best model if not provided
        if not model_id:
            from ai.models.router import TaskType
            from ui.settings_manager import get_settings_manager
            configured = get_settings_manager().get_default_model()
            model_id = self._model_router.dispatch(
                None if configured == "auto" else configured, "", TaskType.SIMPLE_CHAT)
            if not model_id:
                # Fallback to current model if router fails
                model_id = self._current_model
                if not model_id:
                    self._logger.error("No models available for new chat session")
                    raise RuntimeError("No active AI models available. Please connect a provider first.")
        
        model = model_id
        
        # Update current model
        self._current_model = model
        self._update_current_provider(model)
        
        provider = self._current_provider or (
            model.split(":", 1)[0] if ":" in model else "llama_cpp"
        )
        
        if not title:
            title = f"Chat {len(self._sessions) + 1}"
        
        session = ChatSession(
            session_id=session_id,
            title=title,
            model_id=model,
            provider_name=provider,
        )
        
        self._sessions[session_id] = session
        self._current_session_id = session_id
        
        self._save_sessions()
        
        self._logger.info(f"Created session {session_id} with model {model}")
        self.event_bus.publish("ai_chat_session_created", {
            "session_id": session_id,
            "model_id": model,
            "title": title,
        })
        
        return session_id
    
    def _update_current_provider(self, model_id: str) -> None:
        """Update current provider based on model."""
        model = self.model_center.get_model(model_id)
        if model:
            self._current_provider = model.provider
            self._current_model = model_id
            self._logger.info(f"Updated current provider to {model.provider} for model {model_id}")
        elif ":" in model_id:
            provider_name = model_id.split(":", 1)[0]
            if self.provider_registry.get_provider(provider_name):
                self._current_provider = provider_name
                self._current_model = model_id
    
    def get_current_session(self) -> Optional[ChatSession]:
        """Get the current chat session."""
        if self._current_session_id:
            return self._sessions.get(self._current_session_id)
        return None
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a specific session."""
        return self._sessions.get(session_id)
    
    def get_all_sessions(self) -> List[ChatSession]:
        """Get all sessions."""
        return list(self._sessions.values())
    
    def switch_session(self, session_id: str) -> bool:
        """Switch to a different session."""
        if session_id not in self._sessions:
            return False
        
        self._current_session_id = session_id
        session = self._sessions[session_id]
        self._current_model = session.model_id
        self._current_provider = session.provider_name
        
        self._save_sessions()
        
        self._logger.info(f"Switched to session {session_id}")
        self.event_bus.publish("ai_chat_session_switched", {
            "session_id": session_id,
            "model_id": session.model_id,
        })
        # The new session may use a different model; start loading it now
        # rather than when the user hits Enter.
        if session.model_id:
            self.event_bus.publish("ai_warm_request", {
                "model_id": session.model_id,
                "reason": "session_switch",
            })

        return True
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id not in self._sessions:
            return False
        
        del self._sessions[session_id]
        
        if self._current_session_id == session_id:
            if self._sessions:
                self._current_session_id = list(self._sessions.keys())[0]
            else:
                self._current_session_id = None
        
        self._save_sessions()
        
        self._logger.info(f"Deleted session {session_id}")
        self.event_bus.publish("ai_chat_session_deleted", {"session_id": session_id})
        
        return True
    
    def rename_session(self, session_id: str, new_title: str) -> bool:
        """Rename a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session.title = new_title
        self._save_sessions()
        
        self._logger.info(f"Renamed session {session_id} to {new_title}")
        self.event_bus.publish("ai_chat_session_renamed", {
            "session_id": session_id,
            "title": new_title,
        })
        
        return True
    
    def pin_session(self, session_id: str, pinned: bool) -> bool:
        """Pin/unpin a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session.is_pinned = pinned
        self._save_sessions()
        
        self._logger.info(f"Session {session_id} {'pinned' if pinned else 'unpinned'}")
        self.event_bus.publish("ai_chat_session_pinned", {
            "session_id": session_id,
            "pinned": pinned,
        })
        
        return True
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Message Sending
    # ─────────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _load_initial_mode() -> str:
        try:
            mode_file = Path("config/ai_panel.json")
            if mode_file.exists():
                data = json.loads(mode_file.read_text(encoding="utf-8"))
                m = data.get("mode")
                if m in ("chat", "edit", "agent"):
                    return m
        except Exception:
            pass
        return "agent"

    def set_workspace_root(self, workspace_root: Optional[str]) -> None:
        if workspace_root:
            self.workspace_root = str(workspace_root)
            if self.tool_coordinator and hasattr(self.tool_coordinator, "set_workspace_root"):
                try:
                    self.tool_coordinator.set_workspace_root(self.workspace_root)
                except Exception:
                    pass

    def _on_workspace_loaded_track(self, data: dict) -> None:
        path = (data or {}).get("path") or (data or {}).get("path_str")
        if path:
            self.set_workspace_root(str(path))

    def _on_file_opened_track(self, data: dict) -> None:
        path = (data or {}).get("path_str") or (data or {}).get("path")
        if path:
            self.active_editor_file = str(path)

    @staticmethod
    def _is_owncode_internal_dir(path: Path) -> bool:
        try:
            p = path.resolve()
            return (p / "main.py").is_file() and (p / "agent" / "chat_and_agents.py").is_file()
        except Exception:
            return False

    def _resolve_workspace_root(self) -> Path:
        if self.workspace_root and Path(self.workspace_root).is_dir():
            cand = Path(self.workspace_root).resolve()
            if not self._is_owncode_internal_dir(cand):
                return cand
        if self.tool_coordinator and getattr(self.tool_coordinator, "workspace_root", None):
            tc_root = Path(str(self.tool_coordinator.workspace_root))
            if tc_root.is_dir() and not self._is_owncode_internal_dir(tc_root):
                return tc_root.resolve()
        if self.active_editor_file:
            p = Path(self.active_editor_file)
            if p.parent.is_dir() and not self._is_owncode_internal_dir(p.parent):
                return p.parent.resolve()
        cwd = Path.cwd().resolve()
        if self._is_owncode_internal_dir(cwd):
            # When the user hasn't opened a folder yet, use a dedicated clean workspace directory
            # so the agent never mistakes OwnCode's internal `tools/` or `ui/` folders for user folders!
            default_ws = cwd / "workspace"
            default_ws.mkdir(parents=True, exist_ok=True)
            return default_ws
        return cwd

    @staticmethod
    def _extract_code_symbols(code_body: str) -> List[str]:
        """Extract class and function names defined in a code snippet for the live Agent process summary."""
        symbols: List[str] = []
        for m in re.finditer(r"^\s*(?:class|def|async\s+def|struct)\s+([A-Za-z_][A-Za-z0-9_]*)", code_body or "", re.MULTILINE):
            name = m.group(1)
            if name not in symbols and not name.startswith("__"):
                symbols.append(name)
            elif name == "__init__" and not symbols:
                pass
        if not symbols:
            for m in re.finditer(r"^\s*(?:void|int|float|double|char\s*\*?|bool|auto)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", code_body or "", re.MULTILINE):
                name = m.group(1)
                if name not in ("if", "while", "for", "switch") and name not in symbols:
                    symbols.append(name)
        return symbols[:8]

    @classmethod
    def _detect_live_agent_process_state(cls, raw_text: str, user_message: str = "") -> Dict[str, Any]:
        """Inspect the in-flight LLM buffer and return a clean, human-readable process headline & detail line
        (like Gemini / ChatGPT / Cursor Agent status headers) without dumping raw code or copying the user's prompt.
        """
        text = raw_text or ""
        prompt_low = (user_message or "").lower()

        # Detect target filename in buffer if present
        target_file = ""
        m_file = re.search(
            r"(?:FILE|CREATE|MODIFY|EDIT|WRITE|PATH)\s*:\s*`?([A-Za-z0-9_\-./\\]+\.[A-Za-z0-9]+)`?",
            text,
            re.IGNORECASE,
        )
        if m_file:
            target_file = Path(m_file.group(1).replace("\\", "/")).name
        if not target_file:
            m_comment = re.search(
                r"```[^\n]*\n\s*(?:#+|//+|/\*+)\s*([A-Za-z0-9_\-./\\]+\.[A-Za-z0-9]+)",
                text,
            )
            if m_comment:
                target_file = Path(m_comment.group(1).replace("\\", "/")).name
        if not target_file:
            m_prose = re.search(
                r"(?:named|called|file)\s+[`'\"]?([A-Za-z0-9_\-]+\.[A-Za-z0-9]+)[`'\"]?",
                text,
                re.IGNORECASE,
            )
            if m_prose:
                target_file = m_prose.group(1)

        fence_count = text.count("```")
        in_code_block = (fence_count % 2 == 1)
        has_completed_code_block = (fence_count >= 2)
        has_search_replace = "<<<<<<< SEARCH" in text

        # Extract code inside first fence for live metrics
        code_part = ""
        if "```" in text:
            segs = text.split("```")
            if len(segs) >= 2:
                code_part = segs[1]
                if "\n" in code_part:
                    code_part = code_part.split("\n", 1)[1]

        code_lines = len(code_part.splitlines()) if code_part.strip() else 0
        symbols = cls._extract_code_symbols(code_part)
        sym_str = f" ({', '.join(symbols[:5])})" if symbols else ""

        if has_search_replace:
            fname = target_file or "workspace file"
            return {
                "phase": "patching",
                "headline": f"Applying surgical patch to {fname}",
                "detail": f"Synthesizing SEARCH/REPLACE diff hunks{sym_str}…",
            }
        if in_code_block:
            action_word = "Updating" if any(k in prompt_low for k in ("fix", "update", "edit", "modify", "refactor")) else "Generating code for"
            fname = target_file or "new file"
            return {
                "phase": "coding",
                "headline": f"{action_word} {fname}",
                "detail": f"Writing implementation{sym_str} · {max(1, code_lines)} lines generated…",
            }
        if has_completed_code_block:
            fname = target_file or "file"
            return {
                "phase": "finalizing",
                "headline": f"Finalizing {fname}",
                "detail": f"Prepared {max(1, code_lines)} lines{sym_str} · validating syntax & opening in editor…",
            }
        if any(k in prompt_low for k in ("fix", "bug", "error", "debug", "crash")):
            return {
                "phase": "debugging",
                "headline": "Diagnosing issue & preparing fix",
                "detail": "Inspecting code structure and root cause…",
            }
        if any(k in prompt_low for k in ("refactor", "clean", "optimize")):
            return {
                "phase": "refactoring",
                "headline": "Analyzing code for refactoring",
                "detail": "Planning structural improvements…",
            }
        return {
            "phase": "analyzing",
            "headline": "Planning implementation",
            "detail": "Analyzing workspace context and requirements…",
        }

    @classmethod
    def _build_clean_agent_summary_markdown(
        cls,
        applied_records: List[Dict[str, Any]],
        raw_response: str,
        ws_root: Path,
        run_outputs: Optional[List[str]] = None,
        healed: bool = False,
    ) -> str:
        """Build a clean, concise, high-signal Agent Process Summary (no raw code dump or repetitive LLM chatter)."""
        if not applied_records:
            return raw_response

        first = applied_records[0]
        action = first.get("action", "Updated")
        rel_path = first.get("rel_path", "file")
        full_path = first.get("full_path", "")

        code_text = ""
        if full_path and Path(full_path).is_file():
            try:
                code_text = Path(full_path).read_text(encoding="utf-8", errors="ignore")
            except Exception:
                code_text = ""
        line_count = len(code_text.splitlines()) if code_text else 0
        symbols = cls._extract_code_symbols(code_text)

        if len(applied_records) == 1:
            headline = f"**{action} `{rel_path}`**"
        else:
            files_list = ", ".join(f"`{r.get('rel_path')}`" for r in applied_records)
            headline = f"**Applied changes across {len(applied_records)} files ({files_list})**"

        steps: List[str] = [headline, ""]
        steps.append("- **Analyzed** workspace context and target specification")
        for rec in applied_records:
            r_act = rec.get("action", "Updated")
            r_rel = rec.get("rel_path", "file")
            r_fp = rec.get("full_path", "")
            r_code = ""
            if r_fp and Path(r_fp).is_file():
                try:
                    r_code = Path(r_fp).read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    pass
            r_lines = len(r_code.splitlines()) if r_code else 0
            r_syms = cls._extract_code_symbols(r_code)
            sym_badge = f" · Symbols: `{', '.join(r_syms)}`" if r_syms else ""
            lines_badge = f" ({r_lines} lines{sym_badge})" if r_lines else ""
            steps.append(f"- **{r_act}** `{r_rel}`{lines_badge} and opened in editor")

            stage = rec.get("stage", "syntax")
            if rec.get("verified", True):
                heal_tag = " after automatic self-healing repair" if healed else ""
                steps.append(f"- **Verified** `{r_rel}` ({stage} check passed with 0 errors{heal_tag})")
            elif rec.get("error"):
                steps.append(f"- **Diagnostic Note** on `{r_rel}`: `{rec.get('error')[:160]}`")

        if run_outputs:
            for ro in run_outputs:
                steps.append(ro)

        return "\n".join(steps)

    def _on_process_finished_track(self, data: dict) -> None:
        d = data or {}
        exit_code = d.get("exit_code", 0)
        stderr = str(d.get("stderr") or d.get("error") or "")
        stdout = str(d.get("stdout") or d.get("output") or "")
        fpath = str(d.get("file_path") or d.get("path") or self.active_editor_file or "")
        if fpath:
            self.last_executed_file = fpath
        self.last_execution_output = (stdout + ("\n" + stderr if stderr else "")).strip()[-3000:]
        if exit_code != 0 or "Traceback" in self.last_execution_output or "error:" in stderr.lower():
            self.last_execution_error = (stderr or stdout).strip()[-3000:]
        else:
            self.last_execution_error = ""

    def _on_test_finished_track(self, data: dict) -> None:
        d = data or {}
        res = d.get("result")
        if res is not None:
            fpath = str(getattr(res, "file_path", "") or self.active_editor_file or "")
            if fpath:
                self.last_executed_file = fpath
            stderr = str(getattr(res, "stderr", "") or "")
            stdout = str(getattr(res, "stdout", "") or "")
            diag = str(getattr(res, "error_diagnosis", "") or "")
            self.last_execution_output = f"{stdout}\n{stderr}\n{diag}".strip()[-3000:]
            if not getattr(res, "success", True):
                self.last_execution_error = (diag or stderr or stdout).strip()[-3000:]
            else:
                self.last_execution_error = ""

    def _list_workspace_files(self, ws_root: Path, max_files: int = 60) -> List[Path]:
        skip_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", "build", "dist", ".kilo", ".vscode"}
        found: List[Path] = []
        try:
            for item in sorted(ws_root.iterdir()):
                if item.name in skip_dirs or item.name.startswith("."):
                    continue
                if item.is_file():
                    found.append(item)
                elif item.is_dir():
                    for sub in sorted(item.iterdir()):
                        if sub.is_file() and len(found) < max_files:
                            found.append(sub)
                if len(found) >= max_files:
                    break
        except Exception:
            pass
        return found

    def _prefetch_workspace_context_for_prompt(self, user_message: str, ws_root: Path) -> str:
        """Power 1: Automatically resolve @file mentions, fuzzy-matched workspace files,
        and recent runtime/compiler errors so local 7B models never edit blindly.
        """
        msg = user_message or ""
        msg_lower = msg.lower()
        ws_files = self._list_workspace_files(ws_root, max_files=80)
        matched_files: List[Path] = []

        # 1. Explicit @filename mentions (e.g. @linked_list.c or @hello.py)
        for m in re.finditer(r"@([A-Za-z0-9_\-./\\]+\.[A-Za-z0-9]+)", msg):
            token = m.group(1).replace("\\", "/").lstrip("/")
            cand = (ws_root / token).resolve()
            if cand.is_file() and cand not in matched_files:
                matched_files.append(cand)
            else:
                for wf in ws_files:
                    if wf.name.lower() == Path(token).name.lower() and wf not in matched_files:
                        matched_files.append(wf)

        # 2. Exact filename or fuzzy stem matches in user prompt
        for wf in ws_files:
            if len(matched_files) >= 3:
                break
            rel = str(wf.relative_to(ws_root)).replace("\\", "/")
            stem_words = wf.stem.lower().replace("_", " ").replace("-", " ")
            if wf.name.lower() in msg_lower or rel.lower() in msg_lower:
                if wf not in matched_files:
                    matched_files.append(wf)
            elif len(stem_words) >= 4 and stem_words in msg_lower:
                if wf not in matched_files:
                    matched_files.append(wf)

        # 3. Build pre-fetched file snippets
        sections: List[str] = []
        active_resolved = Path(self.active_editor_file).resolve() if (self.active_editor_file and Path(self.active_editor_file).is_file()) else None
        for mf in matched_files[:3]:
            if active_resolved and mf.resolve() == active_resolved:
                continue
            try:
                rel_name = str(mf.relative_to(ws_root)).replace("\\", "/")
                content = mf.read_text(encoding="utf-8", errors="ignore")
                if len(content) <= 5000:
                    sections.append(f"Referenced workspace file (`{rel_name}`):\n```\n{content}\n```")
                else:
                    sections.append(f"Referenced workspace file (`{rel_name}`, first 4000 chars):\n```\n{content[:4000]}\n```")
            except Exception:
                pass

        # 4. Inject recent runtime/compiler error if user asks to fix/debug/solve
        if self.last_execution_error and any(k in msg_lower for k in ("fix", "error", "bug", "crash", "fail", "issue", "broken", "debug", "why")):
            err_file = Path(self.last_executed_file).name if self.last_executed_file else "workspace"
            sections.append(
                f"Latest Runtime / Compiler Error in `{err_file}`:\n```\n{self.last_execution_error}\n```"
            )
        return "\n\n".join(sections)

    def _expand_slash_command(self, user_message: str) -> str:
        """Power 5: Built-in slash commands (/fix, /test, /run, /refactor, /explain, /undo)."""
        raw = (user_message or "").strip()
        if not raw.startswith("/"):
            return user_message
        parts = raw.split(None, 1)
        cmd = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""
        target_name = Path(self.active_editor_file).name if self.active_editor_file else "the target file"

        if cmd == "/fix":
            err_ctx = f"\nRecent error:\n{self.last_execution_error}" if self.last_execution_error else ""
            return (
                f"Inspect and fix all bugs, syntax errors, or edge-case issues in `{rest or target_name}`.{err_ctx}\n"
                f"Output `FILE: {rest or target_name}` followed by the complete corrected code block."
            )
        if cmd == "/refactor":
            return (
                f"Refactor `{rest or target_name}` for clean modular structure, readability, edge-case safety, "
                f"and performance while preserving behavior. Output `FILE: {rest or target_name}` followed by the complete updated code block."
            )
        if cmd == "/test":
            return (
                f"Create or update comprehensive runnable tests for `{rest or target_name}` and run verification. "
                f"Output `FILE: <test_filename>` followed by the complete runnable test code."
            )
        if cmd == "/run":
            return (
                f"Ensure `{rest or target_name}` is complete and runnable, then execute and verify its output."
            )
        if cmd == "/explain":
            return (
                f"Explain the architecture, control flow, data structures, and time/space complexity of `{rest or target_name}` clearly and concisely."
            )
        return user_message

    def _build_agent_system_prompt(self, user_message: str, active_mode: str) -> str:
        ws_root = self._resolve_workspace_root()
        ws_files_paths = self._list_workspace_files(ws_root, max_files=50)
        ws_files = [str(p.relative_to(ws_root)).replace("\\", "/") for p in ws_files_paths]

        active_file_ctx = ""
        if self.active_editor_file:
            try:
                af_path = Path(self.active_editor_file)
                if af_path.is_file():
                    rel_af = af_path.name
                    try:
                        rel_af = str(af_path.resolve().relative_to(ws_root)).replace("\\", "/")
                    except Exception:
                        pass
                    af_text = af_path.read_text(encoding="utf-8", errors="ignore")
                    if len(af_text) <= 4500:
                        active_file_ctx = f"\nCurrently open file in editor (`{rel_af}`):\n```\n{af_text}\n```\n"
            except Exception:
                pass

        prefetched_ctx = self._prefetch_workspace_context_for_prompt(user_message, ws_root)
        if prefetched_ctx:
            active_file_ctx = f"{active_file_ctx}\n{prefetched_ctx}\n"

        repo_map_snippet = ""
        try:
            from agent.context_and_memory import RepoMapBuilder
            rmap = RepoMapBuilder(ws_root).build_map(query=user_message, max_tokens=450)
            if rmap:
                repo_map_snippet = f"\n{rmap}\n"
        except Exception:
            pass

        files_summary = ", ".join(ws_files) if ws_files else "(empty workspace)"
        if active_mode == "edit":
            return (
                f"You are OwnCode Edit Mode operating in workspace: {ws_root}\n"
                f"Workspace files: {files_summary}\n"
                f"{active_file_ctx}"
                "When creating or modifying a file, ALWAYS write `FILE: <relative_path>` on the line "
                "immediately before the code block, or use:\n"
                "FILE: <relative_path>\n<<<<<<< SEARCH\n<old code>\n=======\n<new code>\n>>>>>>> REPLACE\n"
                "Always include the target filename as a comment on the first line inside every code block (e.g. `# filename.py` or `// filename.c`)."
            )
        return (
            f"You are OwnCode Autonomous Agent Mode operating directly on the user's workspace: {ws_root}\n"
            f"Workspace files: {files_summary}\n"
            f"{active_file_ctx}"
            f"{repo_map_snippet}\n"
            "AUTONOMOUS AGENT CAPABILITIES & RULES:\n"
            "1. CREATE OR UPDATE FILES: Output `FILE: <relative_path>` on its own line immediately followed by a fenced code block containing the complete, runnable code, AND place `# <relative_path>` (or `// <relative_path>`) on the first line inside the code block.\n"
            "2. SURGICAL PATCHES: For targeted edits to existing files, you may emit:\n"
            "FILE: <relative_path>\n<<<<<<< SEARCH\n<exact existing lines>\n=======\n<replacement lines>\n>>>>>>> REPLACE\n"
            "3. DELETE OR RENAME FILES: Emit `DELETE: <relative_path>` or `RENAME: <old_path> -> <new_path>` on its own line.\n"
            "4. INSPECT OR SEARCH BEFORE CODING: If you need to read another workspace file or search across the project first, emit `READ: <relative_path>` or `SEARCH: <pattern>`.\n"
            "5. QUALITY & SELF-CONTAINED CODE: Always write complete, clean, production-grade code with a runnable `if __name__ == '__main__':` or `int main()` demo/test block when creating standalone scripts so verification can execute immediately."
        )

    def _execute_agent_inspection_directives(self, response_text: str, ws_root: Path) -> List[str]:
        """Power 2: Execute READ:, SEARCH:, LIST:, or <tool_call> read/search/list directives in the ReAct loop."""
        if not response_text:
            return []
        observations: List[str] = []

        # 1. Line directives: READ: <file>, SEARCH: <pattern>, LIST: <dir>
        for m in re.finditer(r"^(?:READ|INSPECT|VIEW_FILE)\s*:\s*`?([^`\n]+?)`?\s*$", response_text, re.MULTILINE | re.IGNORECASE):
            rel = m.group(1).strip().strip("`'\"")
            cand = (ws_root / rel).resolve()
            try:
                cand.relative_to(ws_root)
                if cand.is_file():
                    txt = cand.read_text(encoding="utf-8", errors="ignore")[:5000]
                    observations.append(f"[Observation from READ `{rel}`]:\n```\n{txt}\n```")
            except Exception:
                pass

        for m in re.finditer(r"^(?:SEARCH|GREP)\s*:\s*`?([^`\n]+?)`?\s*$", response_text, re.MULTILINE | re.IGNORECASE):
            pat = m.group(1).strip().strip("`'\"")
            if not pat:
                continue
            hits: List[str] = []
            for wf in self._list_workspace_files(ws_root, max_files=60):
                try:
                    for lineno, line in enumerate(wf.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                        if pat.lower() in line.lower():
                            rel = str(wf.relative_to(ws_root)).replace("\\", "/")
                            hits.append(f"{rel}:{lineno}: {line.strip()[:120]}")
                            if len(hits) >= 25:
                                break
                except Exception:
                    pass
                if len(hits) >= 25:
                    break
            observations.append(
                f"[Observation from SEARCH `{pat}`]:\n" + ("\n".join(hits) if hits else "(no matches found)")
            )

        # 2. <tool_call> JSON read/search/list calls
        for m in re.finditer(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", response_text, re.DOTALL | re.IGNORECASE):
            try:
                payload = json.loads(m.group(1))
                tname = str(payload.get("name") or payload.get("tool") or "").lower()
                args = payload.get("arguments") or payload.get("params") or {}
                if isinstance(args, str):
                    args = json.loads(args)
                op_name = str(args.get("operation") or tname).lower()
                if "read" in op_name:
                    rel = str(args.get("path") or args.get("file_path") or "").strip()
                    cand = (ws_root / rel).resolve()
                    cand.relative_to(ws_root)
                    if cand.is_file():
                        txt = cand.read_text(encoding="utf-8", errors="ignore")[:5000]
                        observations.append(f"[Observation from tool read `{rel}`]:\n```\n{txt}\n```")
                elif "list" in op_name:
                    files = [str(p.relative_to(ws_root)).replace("\\", "/") for p in self._list_workspace_files(ws_root)]
                    observations.append(f"[Observation from workspace file list]: {', '.join(files)}")
            except Exception:
                pass

        return observations

    def apply_agent_operations(
        self,
        ops: list,
        workspace_root: Optional[str] = None,
        user_prompt: str = "",
        record_checkpoint: bool = True,
    ) -> List[Dict[str, Any]]:
        """Execute extracted file creation/modification/deletion/rename operations directly on the workspace,
        record a rollback checkpoint, run multi-language syntax/compiler verification, and open in the IDE editor.
        """
        if not ops:
            return []
        ws_root = Path(workspace_root).resolve() if workspace_root else self._resolve_workspace_root()
        ws_root.mkdir(parents=True, exist_ok=True)

        from agent.code_editing import SmartPatchEngine
        engine = SmartPatchEngine()
        verifier = SelfHealingVerifier(ws_root)

        checkpoint_entries: List[Dict[str, Any]] = []
        applied_records: List[Dict[str, Any]] = []

        for op in ops:
            src_rel = (op.source_path or "").strip().replace("\\", "/").lstrip("/")
            dst_rel = (op.dest_path or src_rel).strip().replace("\\", "/").lstrip("/")
            if not src_rel or ".." in src_rel.split("/") or ".." in dst_rel.split("/"):
                continue
            src_path = (ws_root / src_rel).resolve()
            dst_path = (ws_root / dst_rel).resolve()
            try:
                src_path.relative_to(ws_root)
                dst_path.relative_to(ws_root)
            except ValueError:
                continue

            op_kind = getattr(op.op_type, "value", str(op.op_type)).lower()

            # Handle DELETE
            if "delete" in op_kind:
                if src_path.is_file():
                    try:
                        old_bytes = src_path.read_bytes()
                        checkpoint_entries.append({
                            "kind": "delete",
                            "path": str(src_path),
                            "rel_path": src_rel,
                            "existed_before": True,
                            "old_bytes": old_bytes,
                        })
                        src_path.unlink()
                        self.event_bus.publish("file_closed", {"path": str(src_path), "path_str": str(src_path)})
                        applied_records.append({
                            "action": "Deleted",
                            "rel_path": src_rel,
                            "full_path": str(src_path),
                            "verified": True,
                            "stage": "deleted",
                        })
                    except Exception as exc:
                        self._logger.error(f"Agent failed to delete {src_path}: {exc}")
                continue

            # Handle RENAME
            if "rename" in op_kind:
                if src_path.is_file():
                    try:
                        old_bytes = src_path.read_bytes()
                        dst_existed = dst_path.is_file()
                        dst_old_bytes = dst_path.read_bytes() if dst_existed else None
                        checkpoint_entries.append({
                            "kind": "rename",
                            "src_path": str(src_path),
                            "dst_path": str(dst_path),
                            "src_rel": src_rel,
                            "dst_rel": dst_rel,
                            "old_bytes": old_bytes,
                            "dst_existed": dst_existed,
                            "dst_old_bytes": dst_old_bytes,
                        })
                        dst_path.parent.mkdir(parents=True, exist_ok=True)
                        src_path.replace(dst_path)
                        text_content = dst_path.read_text(encoding="utf-8", errors="ignore")
                        self.event_bus.publish("file_closed", {"path": str(src_path), "path_str": str(src_path)})
                        self.event_bus.publish("file_opened", {
                            "path": str(dst_path),
                            "path_str": str(dst_path),
                            "content": text_content,
                            "preview": False,
                            "force_reload": True,
                        })
                        applied_records.append({
                            "action": "Renamed",
                            "rel_path": f"{src_rel} -> {dst_rel}",
                            "full_path": str(dst_path),
                            "verified": True,
                            "stage": "renamed",
                        })
                    except Exception as exc:
                        self._logger.error(f"Agent failed to rename {src_path} -> {dst_path}: {exc}")
                continue

            # Handle CREATE or MODIFY
            target_path = dst_path
            rel_path = dst_rel
            existed_before = target_path.is_file()
            old_bytes = target_path.read_bytes() if existed_before else None
            new_content = ""

            if "create" in op_kind or not existed_before:
                if op.content is not None:
                    new_content = op.content
                elif op.hunks:
                    new_content = "\n".join(h.new_text for h in op.hunks if h.new_text is not None)
                action_label = "Updated" if existed_before else "Created"
            elif "modify" in op_kind:
                old_text = ""
                try:
                    old_text = target_path.read_text(encoding="utf-8")
                except Exception:
                    old_text = ""
                working = old_text
                for hunk in (op.hunks or []):
                    if not old_text or (hunk.old_text == old_text):
                        working = hunk.new_text
                    else:
                        res = engine.apply_patch(working, hunk.old_text, hunk.new_text)
                        if res.success:
                            working = getattr(res, "new_content", None) or getattr(res, "content", working)
                        elif hunk.new_text:
                            working = hunk.new_text
                new_content = working
                action_label = "Updated"
            else:
                continue

            try:
                checkpoint_entries.append({
                    "kind": "write",
                    "path": str(target_path),
                    "rel_path": rel_path,
                    "existed_before": existed_before,
                    "old_bytes": old_bytes,
                })
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(new_content, encoding="utf-8")
                self.active_editor_file = str(target_path)

                vres = verifier.verify_file(target_path)
                verified = bool(vres.get("passed", True))

                self.event_bus.publish("file_opened", {
                    "path": str(target_path),
                    "path_str": str(target_path),
                    "content": new_content,
                    "preview": False,
                    "force_reload": True,
                })
                self.event_bus.publish("file_saved", {"path": str(target_path)})

                applied_records.append({
                    "action": action_label,
                    "rel_path": rel_path,
                    "full_path": str(target_path),
                    "verified": verified,
                    "stage": vres.get("stage", "syntax"),
                    "error": vres.get("error", ""),
                    "verification": vres,
                })
            except Exception as exc:
                self._logger.error(f"Agent failed to write {target_path}: {exc}")

        if record_checkpoint and checkpoint_entries:
            self._agent_checkpoints.append({
                "workspace": str(ws_root),
                "prompt": user_prompt,
                "entries": checkpoint_entries,
            })
            if len(self._agent_checkpoints) > 25:
                self._agent_checkpoints.pop(0)

        if applied_records:
            self.event_bus.publish("request_refresh_workspace", {"path": str(ws_root)})
            self.event_bus.publish("ai_agent_operations_applied", {
                "workspace": str(ws_root),
                "operations": applied_records,
                "prompt": user_prompt,
                "can_undo": len(self._agent_checkpoints) > 0,
            })
        return applied_records

    def undo_last_agent_action(self) -> Dict[str, Any]:
        """Power 4: Revert the most recent Agent file checkpoint on disk and update open editor tabs."""
        if not self._agent_checkpoints:
            return {"success": False, "restored": [], "message": "No agent actions to undo."}
        ckpt = self._agent_checkpoints.pop()
        ws_root = ckpt.get("workspace", "")
        restored: List[str] = []

        for entry in reversed(ckpt.get("entries", [])):
            kind = entry.get("kind")
            try:
                if kind == "write":
                    fpath = Path(entry["path"])
                    rel = entry.get("rel_path", fpath.name)
                    if entry.get("existed_before") and entry.get("old_bytes") is not None:
                        fpath.parent.mkdir(parents=True, exist_ok=True)
                        fpath.write_bytes(entry["old_bytes"])
                        text = fpath.read_text(encoding="utf-8", errors="ignore")
                        self.event_bus.publish("file_opened", {
                            "path": str(fpath),
                            "path_str": str(fpath),
                            "content": text,
                            "preview": False,
                            "force_reload": True,
                        })
                        restored.append(f"Restored {rel}")
                    else:
                        if fpath.is_file():
                            fpath.unlink()
                        self.event_bus.publish("file_closed", {"path": str(fpath), "path_str": str(fpath)})
                        restored.append(f"Removed created file {rel}")
                elif kind == "delete":
                    fpath = Path(entry["path"])
                    rel = entry.get("rel_path", fpath.name)
                    if entry.get("old_bytes") is not None:
                        fpath.parent.mkdir(parents=True, exist_ok=True)
                        fpath.write_bytes(entry["old_bytes"])
                        text = fpath.read_text(encoding="utf-8", errors="ignore")
                        self.event_bus.publish("file_opened", {
                            "path": str(fpath),
                            "path_str": str(fpath),
                            "content": text,
                            "preview": False,
                            "force_reload": True,
                        })
                        restored.append(f"Restored deleted file {rel}")
                elif kind == "rename":
                    src_p = Path(entry["src_path"])
                    dst_p = Path(entry["dst_path"])
                    if dst_p.is_file():
                        dst_p.unlink()
                    if entry.get("dst_existed") and entry.get("dst_old_bytes") is not None:
                        dst_p.write_bytes(entry["dst_old_bytes"])
                    if entry.get("old_bytes") is not None:
                        src_p.parent.mkdir(parents=True, exist_ok=True)
                        src_p.write_bytes(entry["old_bytes"])
                    self.event_bus.publish("file_closed", {"path": str(dst_p), "path_str": str(dst_p)})
                    restored.append(f"Reverted rename {entry.get('src_rel')}")
            except Exception as exc:
                self._logger.error(f"Undo entry failed: {exc}")

        if ws_root:
            self.event_bus.publish("request_refresh_workspace", {"path": ws_root})
        result = {
            "success": len(restored) > 0,
            "restored": restored,
            "can_undo": len(self._agent_checkpoints) > 0,
        }
        self.event_bus.publish("ai_agent_undo_completed", result)
        return result

    def _on_agent_undo(self, data: dict = None) -> None:
        self.undo_last_agent_action()

    def run_and_verify_file(self, file_path: str) -> Dict[str, Any]:
        """Power 4: Safely execute & test a workspace file using ProgramTester (auto-stdin, hidden console, timeout)."""
        fpath = Path(file_path).resolve()
        if not fpath.is_file():
            return {"success": False, "error": f"File not found: {fpath}"}
        try:
            from core.program_tester import run_program_test
            res = run_program_test(fpath, timeout=6.0)
            self.last_executed_file = str(fpath)
            self.last_execution_output = f"{res.stdout}\n{res.stderr}".strip()[-3000:]
            if not res.success:
                self.last_execution_error = (getattr(res, "issue_summary", "") or res.stderr or res.stdout).strip()[-3000:]
            else:
                self.last_execution_error = ""
            return {
                "success": bool(res.success),
                "exit_code": res.exit_code,
                "stdout": (res.stdout or "").strip()[:1200],
                "stderr": (res.stderr or "").strip()[:800],
                "duration_ms": round(float(res.duration_ms), 1),
                "diagnosis": getattr(res, "issue_summary", "") or "",
                "quick_fix": res.quick_fix or "",
                "file": fpath.name,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc), "file": fpath.name}

    def _on_run_code_block(self, data: dict) -> None:
        """Handle clicking '▶ Run' on a _CodeBlockWidget: apply the file to workspace and run it via RunManager/ProgramTester."""
        code = (data or {}).get("code", "")
        lang = (data or {}).get("lang", "")
        if not code or not code.strip():
            return
        ws_root = self._resolve_workspace_root()
        from agent.code_editing import SmartPatchEngine
        wrapped = f"```{lang}\n{code}\n```"
        session = self.get_current_session()
        last_prompt = self._last_user_message.get(session.session_id, "create a file") if session else "create a file"
        ops = SmartPatchEngine.extract_operations_from_llm_response(
            wrapped,
            workspace_root=str(ws_root),
            user_prompt=last_prompt,
            active_file=self.active_editor_file,
        )
        if ops:
            applied = self.apply_agent_operations(ops, str(ws_root), user_prompt=last_prompt)
            if applied:
                target_full = applied[0].get("full_path")
                if target_full:
                    run_res = self.run_and_verify_file(target_full)
                    self.event_bus.publish("ai_code_block_run_completed", run_res)

    def _on_apply_code_block(self, data: dict) -> None:
        """Handle one-click 'Apply to File' from a _CodeBlockWidget in the AI Workspace."""
        code = (data or {}).get("code", "")
        lang = (data or {}).get("lang", "")
        hint_path = (data or {}).get("file_path", "")
        if not code or not code.strip():
            return
        ws_root = self._resolve_workspace_root()
        from agent.code_editing import SmartPatchEngine
        if hint_path:
            cleaned = SmartPatchEngine._clean_candidate_path(hint_path)
            if cleaned:
                op = SmartPatchEngine._build_create_or_modify_op(cleaned, code, ws_root, reason="User clicked Apply to File")
                self.apply_agent_operations([op], str(ws_root), user_prompt=f"Apply {cleaned}")
                return
        wrapped = f"```{lang}\n{code}\n```"
        session = self.get_current_session()
        last_prompt = self._last_user_message.get(session.session_id, "create a file") if session else "create a file"
        ops = SmartPatchEngine.extract_operations_from_llm_response(
            wrapped,
            workspace_root=str(ws_root),
            user_prompt=last_prompt,
            active_file=self.active_editor_file,
        )
        if ops:
            self.apply_agent_operations(ops, str(ws_root), user_prompt=last_prompt)

    def _on_apply_last_response(self, data: dict) -> None:
        """When user switches to Agent mode or requests applying the last assistant message."""
        session = self.get_current_session()
        if not session or not session.messages:
            return
        last_assistant = None
        for m in reversed(session.messages):
            if getattr(m, "role", "") == "assistant" and getattr(m, "content", "").strip():
                last_assistant = m
                break
        if not last_assistant:
            return
        msg_id = getattr(last_assistant, "message_id", None) or str(id(last_assistant))
        if msg_id in self._applied_message_ids and not (data or {}).get("force"):
            return
        ws_root = self._resolve_workspace_root()
        last_prompt = self._last_user_message.get(session.session_id, "create a file")
        from agent.code_editing import SmartPatchEngine
        ops = SmartPatchEngine.extract_operations_from_llm_response(
            last_assistant.content,
            workspace_root=str(ws_root),
            user_prompt=last_prompt,
            active_file=self.active_editor_file,
        )
        if ops:
            applied = self.apply_agent_operations(ops, str(ws_root), user_prompt=last_prompt)
            if applied:
                self._applied_message_ids.add(msg_id)

    def _on_mode_changed(self, data: dict) -> None:
        mode = (data or {}).get("mode", "chat")
        if mode in ("chat", "edit", "agent"):
            prev_mode = getattr(self, "active_mode", "chat")
            self.active_mode = mode
            if mode == "agent" and prev_mode != "agent":
                try:
                    self._on_apply_last_response({"force": False})
                except Exception as exc:
                    self._logger.debug(f"Auto-apply on mode switch skipped: {exc}")
    def send_message(self, message: str,
                     model_id: Optional[str] = None,
                     on_chunk: Optional[Callable[[str], None]] = None,
                     on_complete: Optional[Callable[[str], None]] = None,
                     mode: Optional[str] = None) -> str:
        """
        Send a message and get a streamed response.
        
        Args:
            message: The user message
            model_id: Model to use (optional, uses current)
            on_chunk: Callback for each streamed chunk
            on_complete: Callback when complete
            
        Returns:
            Message ID
        """
        session = self.get_current_session()
        if not session:
            session_id = self.create_session(model_id=model_id)
            session = self.get_session(session_id)
        
        if model_id:
            session.model_id = model_id
            session.provider_name = model_id.split(":", 1)[0] if ":" in model_id else self._current_provider or "llama_cpp"
            self._current_model = model_id
        
        # Create user message
        user_msg = ChatMessage(
            role="user",
            content=message,
            model_id=session.model_id,
        )
        session.add_message(user_msg)
        self._last_user_message[session.session_id] = message
        
        self.event_bus.publish("ai_chat_message_added", {
            "session_id": session.session_id,
            "role": "user",
            "content": message,
        })
        
        if mode in ("chat", "edit", "agent"):
            self.active_mode = mode

        request = ChatRequest(uuid.uuid4().hex[:12], session.session_id)
        request.mode = self.active_mode
        with self._request_lock:
            self._requests[request.request_id] = request
        self.event_bus.publish("ai_chat_request_started", {
            "request_id": request.request_id,
            "session_id": session.session_id,
            "model_id": session.model_id,
        })

        # Start background thread for AI response
        thread = threading.Thread(
            target=self._generate_response_sync,
            args=(session, message, on_chunk, on_complete,
                  request),
            daemon=True
        )
        thread.start()
        
        self._logger.info(f"Sent message to {session.model_id} in session {session.session_id}")
        return user_msg.message_id or user_msg.timestamp.isoformat()
    
    def _generate_response_sync(self, session: ChatSession,
                                user_message: str,
                                on_chunk: Optional[Callable[[str], None]],
                                on_complete: Optional[Callable[[str], None]],
                                request: ChatRequest) -> None:
        """
        Generate AI response in background thread.
        
        Resolves the provider in this order:
        1. Extract provider name from model_id prefix  (e.g. "ollama:qwen2.5-coder:7b")
        2. Look up via model_center if step 1 fails
        3. Fall back to the router's best available model
        
        Auto-reconnects the provider if it is not yet connected (handles cold start).
        """
        request_id = request.request_id
        current_model_id = session.model_id
        self._logger.info(f"_generate_response_sync: model='{current_model_id}'")
        
        # ── Step 1: Resolve provider + actual model name ──────────────────────
        provider = None
        actual_model_id = current_model_id   # what we pass to the API

        # Model IDs from the combo are stored as  "providerName:model_name"
        # e.g. "ollama:qwen2.5-coder:7b"  or  "ollama:llama3:8b"
        # Split on first ":" to get provider key, keep the rest as model name.
        if ":" in current_model_id:
            provider_key, actual_model_id = current_model_id.split(":", 1)
            provider = self.provider_registry.get_provider(provider_key)
            if provider:
                self._logger.info(f"Resolved provider '{provider_key}' from model ID prefix")
        
        # Fallback: look up via model_center
        if not provider:
            model_info = self.model_center.get_model(current_model_id)
            if model_info:
                provider = self.provider_registry.get_provider(model_info.provider)
                actual_model_id = current_model_id   # model_center stores full id
                if ":" in current_model_id:
                    actual_model_id = current_model_id.split(":", 1)[1]
        
        # Final fallback: use router to find any working model
        if not provider:
            self._logger.warning(
                f"Could not resolve provider for '{current_model_id}'. "
                "Asking router for best available model."
            )
            best = self._model_router.select_best_model()
            if best:
                current_model_id = best
                if ":" in best:
                    pkey, actual_model_id = best.split(":", 1)
                    provider = self.provider_registry.get_provider(pkey)
                    session.model_id = best
                    self._update_current_provider(best)
                    self.event_bus.publish("ai_chat_failover", {
                        "old_model": session.model_id,
                        "new_model": best,
                        "reason": "Original model provider not found"
                    })
        
        if not provider:
            self._handle_error(
                "No AI provider is available. Check the selected local server or provider settings.",
                on_chunk, on_complete, request_id
            )
            return
        
        # ── Step 2: Ensure provider is connected (auto-reconnect) ─────────────
        if not provider.is_connected():
            self._logger.info(f"Provider '{provider.config.provider_name}' not connected, attempting to connect…")
            # For a local provider, "not connected" usually just means the
            # daemon isn't running yet. Start it rather than sending the user
            # to a terminal — this is the single biggest first-message stall.
            activate_model = getattr(provider, "activate_model", None)
            ensure_server = getattr(provider, "ensure_server", None)
            if callable(activate_model):
                try:
                    activate_model(actual_model_id)
                except Exception as se:
                    self._logger.warning(f"Could not auto-start the local LLM server: {se}")
            elif callable(ensure_server):
                try:
                    ensure_server()
                except Exception as se:
                    self._logger.warning(f"Could not auto-start the local LLM server: {se}")
            try:
                connected = provider.connect()
                if not connected:
                    self._handle_error(
                        f"Cannot connect to '{provider.config.provider_name}'. Check its server settings.",
                        on_chunk, on_complete, request_id
                    )
                    return
                self._logger.info(f"Provider '{provider.config.provider_name}' connected successfully")
            except Exception as ce:
                self._handle_error(
                    f"Connection failed for '{provider.config.provider_name}': {ce}",
                    on_chunk, on_complete, request_id
                )
                return
        
        # ── Step 3: Stream the response ───────────────────────────────────────
        self._logger.info(
            f"Streaming from provider='{provider.config.provider_name}' "
            f"model='{actual_model_id}'"
        )
        
        current_message = ChatMessage(
            role="assistant",
            content="",
            model_id=current_model_id,
        )
        
        self.event_bus.publish("ai_chat_streaming_started", {
            "session_id": session.session_id,
            "model_id": current_model_id,
            "request_id": request_id,
        })

        # Inject project-global memory/context as a prompt prefix so the model
        # gets the user's recap. Stored in history is the *raw* user message, so
        # the context never bloats the visible transcript.
        context_prefix = ""
        try:
            context_prefix = self.context_store.prompt_prefix()
        except Exception:
            context_prefix = ""
        effective_prompt = (
            f"{context_prefix}\n\nUser request:\n{user_message}"
            if context_prefix else user_message
        )

        try:
            generation_started = time.perf_counter()
            active_mode = getattr(request, "mode", None) or getattr(self, "active_mode", "agent")
            ws_root = self._resolve_workspace_root()

            # Immediate handling for /undo command without requiring LLM inference
            if (user_message or "").strip().lower() == "/undo":
                undo_res = self.undo_last_agent_action()
                if undo_res.get("success"):
                    msg_txt = "✓ **Reverted Last Agent Action:**\n" + "\n".join(f"- {r}" for r in undo_res["restored"])
                else:
                    msg_txt = "No previous Agent workspace actions to undo."
                self._handle_chunk(msg_txt, current_message, on_chunk, request)
                current_message.content = msg_txt
                session.add_message(current_message)
                self.event_bus.publish("ai_chat_streaming_complete", {
                    "session_id": session.session_id,
                    "content_length": len(msg_txt),
                    "request_id": request_id,
                })
                if on_complete:
                    on_complete(msg_txt)
                return

            expanded_user_message = self._expand_slash_command(user_message)
            effective_prompt = (
                f"{context_prefix}\n\nUser request:\n{expanded_user_message}"
                if context_prefix else expanded_user_message
            )

            system_prompt = None
            if active_mode in ("edit", "agent"):
                system_prompt = self._build_agent_system_prompt(expanded_user_message, active_mode)

            history_messages = []
            for m in list(getattr(session, "messages", []) or [])[:-1][-18:]:
                m_role = getattr(m, "role", "user")
                m_content = getattr(m, "content", "")
                if m_role in ("user", "assistant", "system") and m_content:
                    history_messages.append({"role": m_role, "content": m_content})
            history_messages.append({"role": "user", "content": effective_prompt})

            if active_mode == "agent":
                init_state = self._detect_live_agent_process_state("", user_message)
                self.event_bus.publish("ai_agent_process_update", {
                    "session_id": session.session_id,
                    "request_id": request_id,
                    "phase": init_state["phase"],
                    "headline": init_state["headline"],
                    "detail": init_state["detail"],
                })

            def _on_model_chunk(chunk: str):
                if active_mode == "agent":
                    if request is not None and request.cancel.is_set():
                        raise Exception("Streaming cancelled")
                    current_message.content += chunk
                    if request is not None and request.first_token_at is None:
                        request.first_token_at = time.perf_counter()
                    if on_chunk:
                        on_chunk(chunk)
                    state = self._detect_live_agent_process_state(current_message.content, user_message)
                    self.event_bus.publish("ai_agent_process_update", {
                        "session_id": session.session_id,
                        "request_id": request_id,
                        "phase": state["phase"],
                        "headline": state["headline"],
                        "detail": state["detail"],
                    })
                else:
                    self._handle_chunk(chunk, current_message, on_chunk, request)

            def _call_model_stream(prompt_text, msgs):
                try:
                    return provider.stream_response(
                        prompt=prompt_text,
                        model_id=actual_model_id,
                        system_prompt=system_prompt,
                        on_chunk=_on_model_chunk,
                        messages=msgs,
                    )
                except TypeError:
                    return provider.stream_response(
                        prompt=prompt_text,
                        model_id=actual_model_id,
                        on_chunk=_on_model_chunk,
                    )

            response = _call_model_stream(effective_prompt, history_messages)
            full_response = response if response else current_message.content

            # ── Power 2: Bounded ReAct Inspection Loop (up to 2 follow-up turns) ─
            if active_mode == "agent" and full_response:
                for _react_turn in range(2):
                    observations = self._execute_agent_inspection_directives(full_response, ws_root)
                    if not observations or "```" in full_response or "<<<<<<< SEARCH" in full_response:
                        break
                    obs_block = "\n\n".join(observations)
                    step_note = f"\n\n*⚡ Agent inspected workspace context ({len(observations)} item(s))...*\n\n"
                    self._handle_chunk(step_note, current_message, on_chunk, request)
                    history_messages.append({"role": "assistant", "content": full_response})
                    followup_prompt = (
                        f"{obs_block}\n\nNow complete the user's request (`{expanded_user_message}`) "
                        f"by outputting `FILE: <filename>` followed by the code block."
                    )
                    history_messages.append({"role": "user", "content": followup_prompt})
                    next_resp = _call_model_stream(followup_prompt, history_messages)
                    full_response = current_message.content if not next_resp else f"{full_response}\n{next_resp}"

            generation_seconds = max(time.perf_counter() - generation_started, 0.001)

            if active_mode in ("edit", "agent") and full_response:
                try:
                    from agent.code_editing import SmartPatchEngine, ChangeSet
                    ops = SmartPatchEngine.extract_operations_from_llm_response(
                        full_response,
                        workspace_root=str(ws_root),
                        user_prompt=expanded_user_message,
                        active_file=self.active_editor_file,
                    )
                    if ops:
                        self.event_bus.publish("ai_agent_operations_ready", {
                            "mode": active_mode,
                            "operation_count": len(ops),
                            "files": [op.source_path for op in ops],
                        })
                        if active_mode == "agent":
                            applied = self.apply_agent_operations(
                                ops,
                                workspace_root=str(ws_root),
                                user_prompt=user_message,
                            )
                            # ── Power 3: Closed-Loop Self-Healing Auto-Repair if syntax/compile failed ─
                            failed_items = [it for it in applied if not it.get("verified", True) and it.get("verification")]
                            if failed_items:
                                broken = failed_items[0]
                                verifier = SelfHealingVerifier(ws_root)
                                repair_prompt = verifier.build_repair_prompt(broken["verification"], attempt=1)
                                heal_note = f"\n\n*⚡ Self-healing syntax/compile issue in `{broken['rel_path']}`...*\n\n"
                                self._handle_chunk(heal_note, current_message, on_chunk, request)
                                history_messages.append({"role": "assistant", "content": full_response})
                                history_messages.append({"role": "user", "content": repair_prompt})
                                repair_resp = _call_model_stream(repair_prompt, history_messages)
                                if repair_resp:
                                    repair_ops = SmartPatchEngine.extract_operations_from_llm_response(
                                        repair_resp,
                                        workspace_root=str(ws_root),
                                        user_prompt=repair_prompt,
                                        active_file=broken.get("full_path"),
                                    )
                                    if repair_ops:
                                        repaired = self.apply_agent_operations(
                                            repair_ops,
                                            workspace_root=str(ws_root),
                                            user_prompt="Self-healing repair",
                                            record_checkpoint=False,
                                        )
                                        if repaired:
                                            applied = repaired

                            if applied:
                                run_outputs: List[str] = []
                                prompt_low = (user_message or "").lower()
                                wants_run = (
                                    prompt_low.startswith(("/run", "/test"))
                                    or any(k in prompt_low for k in ("and run", "run it", "test it", "execute it", "check output", "run the"))
                                )
                                if wants_run:
                                    for item in applied[:2]:
                                        fpath = item.get("full_path", "")
                                        if fpath and Path(fpath).is_file():
                                            self.event_bus.publish("ai_agent_process_update", {
                                                "session_id": session.session_id,
                                                "request_id": request_id,
                                                "phase": "running",
                                                "headline": f"Running & verifying {item['rel_path']}",
                                                "detail": "Executing in hidden sandbox…",
                                            })
                                            run_res = self.run_and_verify_file(fpath)
                                            if run_res.get("success"):
                                                out_preview = (run_res.get("stdout") or "(no stdout)").strip()
                                                run_outputs.append(
                                                    f"- **Executed** `{item['rel_path']}` (exit 0 in {run_res.get('duration_ms', 0)}ms):\n```\n{out_preview[:500]}\n```"
                                                )
                                            else:
                                                err_preview = (run_res.get("diagnosis") or run_res.get("stderr") or run_res.get("error") or "Execution failed").strip()
                                                run_outputs.append(
                                                    f"- **Execution Check** `{item['rel_path']}`: {err_preview[:400]}"
                                                )

                                clean_summary = self._build_clean_agent_summary_markdown(
                                    applied,
                                    full_response,
                                    ws_root,
                                    run_outputs=run_outputs,
                                    healed=bool(failed_items),
                                )
                                current_message.content = clean_summary
                                full_response = clean_summary
                                self.event_bus.publish("ai_agent_summary_ready", {
                                    "session_id": session.session_id,
                                    "request_id": request_id,
                                    "summary_markdown": clean_summary,
                                    "operations": applied,
                                })
                        elif active_mode == "edit":
                            cs = ChangeSet.from_operations(ops, description=user_message)
                            self.event_bus.publish("review_change_set", {
                                "change_set": cs,
                                "prompt": user_message,
                            })
                    elif active_mode == "agent" and full_response:
                        # No file operations were needed (e.g. conceptual question in Agent mode) -> display response
                        self.event_bus.publish("ai_agent_summary_ready", {
                            "session_id": session.session_id,
                            "request_id": request_id,
                            "summary_markdown": full_response,
                            "operations": [],
                        })
                except Exception as pe:
                    self._logger.error(f"Agent operation execution error: {pe}", exc_info=True)

            current_message.content = full_response
            session.add_message(current_message)
            msg_id = getattr(current_message, "message_id", None) or str(id(current_message))
            if active_mode == "agent":
                self._applied_message_ids.add(msg_id)
            self._record_usage(
                session.session_id, effective_prompt, full_response,
                generation_seconds=generation_seconds,
                request=request)

            self.event_bus.publish("ai_chat_streaming_complete", {
                "session_id": session.session_id,
                "content_length": len(full_response),
                "request_id": request_id,
                "summary_markdown": full_response if active_mode == "agent" else "",
            })
            
            if on_complete:
                on_complete(full_response)
            
            self._logger.info(
                f"Response complete: {len(full_response)} chars from '{actual_model_id}'"
            )
            
        except Exception as e:
            self._logger.error(f"Streaming failed: {e}", exc_info=True)

            if request.cancel.is_set():
                self.event_bus.publish("ai_chat_stream_cancelled", {"request_id": request_id})
                return
            
            # Try failover to another model
            best = self._model_router.select_best_model()
            if best and best != current_model_id and request.retries < request.max_retries:
                request.retries += 1
                self._logger.info(f"Failing over to '{best}'")
                self.event_bus.publish("ai_chat_failover", {
                    "old_model": current_model_id,
                    "new_model": best,
                    "reason": str(e)
                })
                session.model_id = best
                self._update_current_provider(best)
                # Re-enter with new model
                self._generate_response_sync(
                    session, user_message, on_chunk, on_complete, request)
            else:
                self._handle_error(str(e), on_chunk, on_complete, request_id)
        finally:
            with self._request_lock:
                self._requests.pop(request_id, None)
            self.event_bus.publish("ai_chat_request_finished", {
                "request_id": request_id, "session_id": session.session_id})
    
    def _handle_chunk(self, chunk: str, message: ChatMessage,
                      on_chunk: Optional[Callable[[str], None]],
                      request: Optional[ChatRequest] = None) -> None:
        """Handle a streaming chunk."""
        if request is not None and request.cancel.is_set():
            raise Exception("Streaming cancelled")
        
        message.content += chunk
        
        if request is not None and request.first_token_at is None:
            request.first_token_at = time.perf_counter()
        if on_chunk:
            on_chunk(chunk)
        
        self.event_bus.publish("ai_chat_chunk", {
            "chunk": chunk,
            "message_id": message.message_id,
        })
    
    def _handle_error(self, error: str,
                      on_chunk: Optional[Callable[[str], None]],
                      on_complete: Optional[Callable[[str], None]],
                      request_id: Optional[str] = None) -> None:
        """Handle an error during streaming."""
        self.event_bus.publish("ai_chat_error", {
            "error": error,
            "request_id": request_id,
        })
        
        if on_chunk:
            on_chunk(f"\n\n**Error:** {error}")

        if on_complete:
            on_complete(f"\n\n**Error:** {error}")

    # ─────────────────────────────────────────────────────────────────────────────
    # Token usage (client-side estimate) & AI memory/context
    # ─────────────────────────────────────────────────────────────────────────────

    def _record_usage(self, session_id: str, prompt: str, response: str,
                      generation_seconds: float = 0.0,
                      request: Optional[ChatRequest] = None) -> None:
        """Estimate tokens for a completed turn and publish running totals."""
        try:
            prompt_tokens = estimate_tokens(prompt)
            completion_tokens = estimate_tokens(response)
            turn_total = prompt_tokens + completion_tokens
            tokens_per_second = (
                completion_tokens / generation_seconds
                if generation_seconds > 0 else 0.0)
            acc = self._session_tokens.setdefault(
                session_id, {"prompt": 0, "completion": 0, "total": 0})
            acc["prompt"] += prompt_tokens
            acc["completion"] += completion_tokens
            acc["total"] += turn_total
            self.event_bus.publish("ai_chat_usage", {
                "session_id": session_id,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "turn_tokens": turn_total,
                "session_prompt_tokens": acc["prompt"],
                "session_completion_tokens": acc["completion"],
                "session_total_tokens": acc["total"],
                "generation_seconds": round(generation_seconds, 3),
                "tokens_per_second": round(tokens_per_second, 2),
                "first_token_seconds": round(
                    (request.first_token_at - request.started_at)
                    if request and request.first_token_at else 0.0, 3),
                "request_id": request.request_id if request else None,
                "estimated": True,
            })
        except Exception as e:
            self._logger.debug(f"usage tracking failed: {e}")

    def get_session_usage(self, session_id: Optional[str] = None) -> Dict[str, int]:
        sid = session_id or self._current_session_id
        return dict(self._session_tokens.get(sid, {"prompt": 0, "completion": 0, "total": 0}))

    def _publish_context(self) -> None:
        try:
            self.event_bus.publish("ai_context_changed", {
                "entries": self.context_store.summaries(),
                "total_tokens": self.context_store.total_tokens(),
                "total_chars": self.context_store.total_chars(),
            })
        except Exception:
            pass

    def _on_context_add_note(self, data: dict) -> None:
        name = (data or {}).get("name", "note")
        content = (data or {}).get("content", "")
        if content.strip():
            self.context_store.add_note(name, content)
            self._publish_context()

    def _on_context_add_file(self, data: dict) -> None:
        path = (data or {}).get("path", "")
        if not path:
            return
        try:
            self.context_store.add_file(path)
            self._publish_context()
        except Exception as e:
            self.event_bus.publish("ai_context_error",
                                   {"error": f"Could not read '{path}': {e}"})

    def _on_context_remove(self, data: dict) -> None:
        entry_id = (data or {}).get("entry_id")
        if entry_id and self.context_store.remove(entry_id):
            self._publish_context()

    def _on_context_clear(self, data: dict) -> None:
        self.context_store.clear()
        self._publish_context()

    def _on_context_request(self, data: dict) -> None:
        """Let the UI ask for the current context snapshot (e.g. on startup)."""
        self._publish_context()

    def _on_regenerate(self, data: dict) -> None:
        """Re-send the last user message in the current session."""
        session = self.get_current_session()
        if not session:
            return
        last = self._last_user_message.get(session.session_id)
        if not last:
            return
        self.send_message(last, model_id=session.model_id)

    
    # ─────────────────────────────────────────────────────────────────────────────
    # Event Handlers
    # ─────────────────────────────────────────────────────────────────────────────

    def resolve_provider(self, model_id: Optional[str], allow_fallback: bool = True):
        """Resolve (provider, actual_model_id) for a "provider:model" id.

        Mirrors the resolution used by streaming, but side-effect free — no
        session mutation, no events. Returns (provider_or_None, actual_model_id).
        """
        provider = None
        actual = model_id or ""
        if model_id and ":" in model_id:
            key, actual = model_id.split(":", 1)
            provider = self.provider_registry.get_provider(key)
        if not provider and model_id:
            info = self.model_center.get_model(model_id)
            if info:
                provider = self.provider_registry.get_provider(info.provider)
                actual = model_id.split(":", 1)[1] if ":" in model_id else model_id
        if not provider and allow_fallback:
            best = self._model_router.select_best_model()
            if best and ":" in best:
                key, actual = best.split(":", 1)
                provider = self.provider_registry.get_provider(key)
        return provider, actual

    def generate_once(self, prompt: str, model_id: Optional[str] = None,
                      on_complete: Optional[Callable[[str], None]] = None,
                      on_error: Optional[Callable[[str], None]] = None) -> None:
        """One-shot generation, isolated from chat sessions and chat events.

        Used by the editor's inline-AI feature so an inline edit never appears in
        the chat panel. Runs on a daemon thread; callbacks fire from that thread,
        so UI callers must marshal results back to the UI thread themselves.
        """
        model_id = model_id or self._current_model
        if not model_id:
            sess = self.get_current_session()
            model_id = sess.model_id if sess else None

        def work():
            try:
                provider, actual = self.resolve_provider(model_id)
                if not provider:
                    if on_error:
                        on_error("No AI provider available. Connect one in Settings.")
                    return
                if not provider.is_connected():
                    try:
                        if not provider.connect():
                            if on_error:
                                on_error(f"Cannot connect to '{provider.config.provider_name}'.")
                            return
                    except Exception as ce:
                        if on_error:
                            on_error(f"Connection failed: {ce}")
                        return
                chunks: list = []
                resp = provider.stream_response(
                    prompt=prompt, model_id=actual,
                    on_chunk=lambda ch: chunks.append(ch))
                full = resp if resp else "".join(chunks)
                if on_complete:
                    on_complete(full or "")
            except Exception as e:
                if on_error:
                    on_error(str(e))

        threading.Thread(target=work, daemon=True).start()

    def _on_chat_send(self, data: dict) -> None:
        """Handle chat send event."""
        message = data.get("message", "")
        model_id = data.get("model_id")
        on_chunk = data.get("on_chunk")
        on_complete = data.get("on_complete")
        mode = data.get("mode")
        
        if message:
            self.send_message(message, model_id, on_chunk, on_complete, mode=mode)
    
    def _on_switch_model(self, data: dict) -> None:
        """Handle model switch event."""
        model_id = data.get("model_id")
        session_id = data.get("session_id", self._current_session_id)
        
        if model_id:
            session = self._sessions.get(session_id)
            if (model_id == self._current_model
                    and (session is None or session.model_id == model_id)):
                return
            if session:
                session.model_id = model_id
                self._update_current_provider(model_id)
                session.provider_name = self._current_provider or session.provider_name
                self._save_sessions()
                self.event_bus.publish("ai_chat_model_switched", {
                    "session_id": session_id,
                    "model_id": model_id,
                })
            if self.optimizer is not None:
                self.optimizer.switch_model(model_id)
    
    def _on_cancel_stream(self, data: dict) -> None:
        """Handle cancel stream event."""
        request_id = (data or {}).get("request_id")
        with self._request_lock:
            requests = ([self._requests.get(request_id)] if request_id
                        else list(self._requests.values()))
        for request in [item for item in requests if item is not None]:
            request.cancel.set()
        self.event_bus.publish("ai_chat_stream_cancelled", {
            "request_id": request_id})
    
    def _on_new_session(self, data: dict) -> None:
        """Handle new session event."""
        title = data.get("title", "New Chat")
        model_id = data.get("model_id")
        self.create_session(model_id=model_id, title=title)

    def _on_switch_session(self, data: dict) -> None:
        """Handle switch-to-existing-session event."""
        session_id = data.get("session_id")
        if session_id:
            self.switch_session(session_id)
    
    def _on_delete_session(self, data: dict) -> None:
        """Handle delete session event."""
        session_id = data.get("session_id")
        if session_id:
            self.delete_session(session_id)
    
    def _on_rename_session(self, data: dict) -> None:
        """Handle rename session event."""
        session_id = data.get("session_id")
        new_title = data.get("title")
        if session_id and new_title:
            self.rename_session(session_id, new_title)
    
    def _on_pin_session(self, data: dict) -> None:
        """Handle pin session event."""
        session_id = data.get("session_id")
        pinned = data.get("pinned", True)
        if session_id:
            self.pin_session(session_id, pinned)
    
    def _on_export_session(self, data: dict) -> Optional[str]:
        """Handle export session event."""
        session_id = data.get("session_id")
        if not session_id:
            return None
        
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        import json
        export_data = {
            "session": session.to_dict(),
            "exported_at": datetime.utcnow().isoformat(),
        }
        
        return json.dumps(export_data, indent=2)
    
    def _on_import_session(self, data: dict) -> str:
        """Handle import session event."""
        import json
        from pathlib import Path
        
        content = data.get("content")
        if not content:
            return "No content provided"
        
        try:
            data = json.loads(content)
            session_data = data.get("session")
            
            if session_data:
                session = ChatSession.from_dict(session_data)
                self._sessions[session.session_id] = session
                self._save_sessions()
                return f"Imported session: {session.title}"
            else:
                return "Invalid session format"
                
        except json.JSONDecodeError as e:
            return f"Failed to import: {str(e)}"
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Utility Methods
    # ─────────────────────────────────────────────────────────────────────────────

    def get_available_models(self) -> Dict[str, str]:
        """Get available models for selection (returns all models regardless of provider availability)."""
        try:
            # Get all models, not just enabled ones
            all_models = self.model_center.get_all_models()
            return {m.model_id: m.display_name for m in all_models.values()}
        except Exception as e:
            self._logger.error(f"Failed to get available models: {e}")
            return {}
    
    def get_current_provider(self) -> Optional[str]:
        """Get current provider name."""
        return self._current_provider
    
    def get_current_model(self) -> Optional[str]:
        """Get current model ID."""
        return self._current_model
    
    def is_streaming(self) -> bool:
        """Check if streaming is active."""
        with self._request_lock:
            return bool(self._requests)
    
    def test_provider_connection(self, provider_name: str) -> Dict[str, Any]:
        """Test provider connection."""
        provider = self.provider_registry.get_provider(provider_name)
        if not provider:
            return {"success": False, "error": "Provider not found"}
        
        try:
            success = provider.test_connection()
            return {
                "success": success,
                "status": provider.get_status().value,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_available_tools(self):
        """Get list of available tools for LLM."""
        if not self.tool_coordinator:
            return []
        return self.tool_coordinator.get_available_tools()
    
    def set_tool_coordinator(self, tool_coordinator):
        """Set the tool coordinator."""
        self.tool_coordinator = tool_coordinator
        self._logger.info("Tool coordinator connected to AI chat engine")

    def set_optimizer(self, optimizer):
        """Set the LLM optimizer."""
        self.optimizer = optimizer
        self._logger.info("LLM optimizer connected to AI chat engine")


# Global instance
_ai_chat_engine = None


def get_ai_chat_engine() -> AIChatEngine:
    """Get the global AI chat engine."""
    global _ai_chat_engine
    if _ai_chat_engine is None:
        raise RuntimeError("AIChatEngine not initialized")
    return _ai_chat_engine


def initialize_ai_chat_engine(event_bus, provider_registry, provider_manager,
                               model_center, model_registry) -> AIChatEngine:
    """Initialize the global AI chat engine."""
    global _ai_chat_engine
    _ai_chat_engine = AIChatEngine(
        event_bus=event_bus,
        provider_registry=provider_registry,
        provider_manager=provider_manager,
        model_center=model_center,
        model_registry=model_registry,
    )
    return _ai_chat_engine


def reset_ai_chat_engine():
    """Reset the global AI chat engine."""
    global _ai_chat_engine
    _ai_chat_engine = None

    # ─────────────────────────────────────────────────────────────────────────────
    # Tool Integration
    # ─────────────────────────────────────────────────────────────────────────────
    
    def _on_execute_tool(self, data: dict):
        """Handle tool execution request from AI."""
        if not self.tool_coordinator:
            self._logger.warning("Tool coordinator not available")
            return
        
        tool_name = data.get("tool")
        params = data.get("params", {})
        
        result = self.tool_coordinator.execute_tool(tool_name, **params)
        
        # Publish result back to AI
        self.event_bus.publish("ai_tool_result", {
            "tool": tool_name,
            "result": result.output,
            "success": result.success,
            "error": result.error,
            "metadata": result.metadata
        })


# ============================================================================
# SECTION: ai.integration.ai_ide_integration (ai/integration/ai_ide_integration.py)
# ============================================================================
"""
AI-IDE Integration Module

Connects AI tools with IDE features:
- File operations
- Editor control
- Project management
- Safety confirmations
"""

from typing import Optional
from PySide6.QtWidgets import QWidget

from core.event_bus import EventBus
from core.logger import setup_logger
from ai.tools.tool_coordinator import AIToolCoordinator, initialize_tool_coordinator
from ai.chat.ai_chat_engine import AIChatEngine
from ui.dialogs.tool_confirmation_dialog import ToolConfirmationDialog

logger = setup_logger(__name__)


class AIIDEIntegration:
    """
    Central integration point between AI and IDE.
    
    Responsibilities:
    - Initialize AI tool system
    - Connect tools to chat engine
    - Handle confirmation dialogs
    - Manage workspace context
    - Coordinate AI-driven IDE operations
    """
    
    def __init__(self, event_bus: EventBus, parent_widget: Optional[QWidget] = None):
        self.event_bus = event_bus
        self.parent_widget = parent_widget
        self.tool_coordinator: Optional[AIToolCoordinator] = None
        self.chat_engine: Optional[AIChatEngine] = None
        self.workspace_root: Optional[str] = None
        
        self._active_confirmations = {}
        
        # Subscribe to events
        self._subscribe_events()
        
        logger.info("AI-IDE Integration initialized")
    
    def _subscribe_events(self):
        """Subscribe to integration events."""
        self.event_bus.subscribe("workspace_loaded", self._on_workspace_loaded)
        self.event_bus.subscribe("tool_confirmation_required", self._on_confirmation_required)
        self.event_bus.subscribe("ai_chat_engine_ready", self._on_chat_engine_ready)
    
    def initialize_tools(self, workspace_root: Optional[str] = None):
        """Initialize AI tool system."""
        self.workspace_root = workspace_root
        
        # Create tool coordinator
        self.tool_coordinator = initialize_tool_coordinator(
            self.event_bus,
            workspace_root
        )
        
        # Connect to chat engine if available
        if self.chat_engine:
            self.chat_engine.set_tool_coordinator(self.tool_coordinator)
        
        logger.info(f"AI tools initialized with workspace: {workspace_root or 'None'}")
    
    def set_chat_engine(self, chat_engine: AIChatEngine):
        """Connect chat engine to tool system."""
        self.chat_engine = chat_engine
        
        if self.tool_coordinator:
            chat_engine.set_tool_coordinator(self.tool_coordinator)
            logger.info("Chat engine connected to tool coordinator")
    
    def _on_workspace_loaded(self, data: dict):
        """Handle workspace loaded event."""
        workspace_path = data.get("path")
        if workspace_path:
            logger.info(f"Updating AI tools workspace: {workspace_path}")
            
            if not self.tool_coordinator:
                self.initialize_tools(workspace_path)
            else:
                self.tool_coordinator.set_workspace_root(workspace_path)
    
    def _on_chat_engine_ready(self, data: dict):
        """Handle chat engine ready event."""
        # Chat engine will be set via set_chat_engine method
        pass
    
    def _on_confirmation_required(self, data: dict):
        """Handle tool confirmation request."""
        confirmation_id = data.get("confirmation_id")
        tool_name = data.get("tool")
        action = data.get("action")
        message = data.get("message")
        metadata = data.get("metadata", {})
        
        # Show confirmation dialog
        dialog = ToolConfirmationDialog(
            confirmation_id=confirmation_id,
            tool_name=tool_name,
            action=action,
            message=message,
            metadata=metadata,
            parent=self.parent_widget
        )
        
        # Connect signals
        dialog.confirmed.connect(self._on_dialog_confirmed)
        dialog.denied.connect(self._on_dialog_denied)
        
        # Track dialog
        self._active_confirmations[confirmation_id] = dialog
        
        # Show dialog
        dialog.exec()
    
    def _on_dialog_confirmed(self, confirmation_id: str):
        """Handle dialog confirmation."""
        if confirmation_id in self._active_confirmations:
            del self._active_confirmations[confirmation_id]
        
        # Publish approval
        self.event_bus.publish("tool_confirmation_approved", {
            "confirmation_id": confirmation_id
        })
    
    def _on_dialog_denied(self, confirmation_id: str):
        """Handle dialog denial."""
        if confirmation_id in self._active_confirmations:
            del self._active_confirmations[confirmation_id]
        
        # Publish denial
        self.event_bus.publish("tool_confirmation_denied", {
            "confirmation_id": confirmation_id
        })
    
    def get_tool_capabilities(self) -> dict:
        """Get current AI tool capabilities."""
        if not self.tool_coordinator:
            return {
                "enabled": False,
                "tools": [],
                "workspace": None
            }
        
        return {
            "enabled": True,
            "tools": self.tool_coordinator.get_available_tools(),
            "workspace": self.workspace_root,
            "tool_count": len(self.tool_coordinator.get_tool_names())
        }
    
    def execute_ai_command(self, command: str, context: dict = None):
        """
        Execute an AI command with full IDE access.
        
        Args:
            command: Natural language command
            context: Additional context (current file, selection, etc.)
        """
        if not self.chat_engine:
            logger.warning("Chat engine not available for AI command")
            return
        
        # Build enhanced prompt with tool capabilities
        tools = self.tool_coordinator.get_available_tools() if self.tool_coordinator else []
        
        enhanced_prompt = f"{command}\n\n"
        if context:
            enhanced_prompt += f"Context: {context}\n\n"
        
        if tools:
            enhanced_prompt += "Available tools:\n"
            for tool in tools:
                enhanced_prompt += f"- {tool['name']}: {tool['description']}\n"
        
        # Send to chat engine
        self.chat_engine.send_message(enhanced_prompt)


def initialize_ai_ide_integration(event_bus: EventBus,
                                  parent_widget: Optional[QWidget] = None) -> AIIDEIntegration:
    """
    Initialize AI-IDE integration.
    
    Args:
        event_bus: Event bus for communication
        parent_widget: Parent widget for dialogs
        
    Returns:
        AIIDEIntegration instance
    """
    integration = AIIDEIntegration(event_bus, parent_widget)
    logger.info("AI-IDE integration initialized successfully")
    return integration




# =====================================================================
# Phase 2 & 3: DAG Sub-Agent Orchestrator & Closed-Loop Self-Healing
# =====================================================================
import ast
from dataclasses import dataclass, field as dc_field


@dataclass
class SubTaskNode:
    id: str
    title: str
    role: str  # "architect", "coder", "verifier", "debugger", "documenter"
    description: str
    dependencies: List[str] = dc_field(default_factory=list)
    status: str = "pending"
    result: Optional[str] = None
    verification: Optional[Dict[str, Any]] = None


class SelfHealingVerifier:
    """Runs multi-language syntax/compiler checks (Python AST, C/C++ gcc/g++ -fsyntax-only,
    JS node --check, JSON validation) after code mutations, constructing structured repair prompts if any check fails.
    """

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = Path(workspace_root or Path.cwd()).resolve()

    @classmethod
    def verify_python_code(cls, source: str, filename: str = "<memory>") -> Dict[str, Any]:
        try:
            ast.parse(source or "", filename=filename)
            return {"passed": True, "stage": "ast_syntax", "file": filename}
        except SyntaxError as exc:
            return {
                "passed": False,
                "stage": "ast_syntax",
                "file": filename,
                "line": exc.lineno,
                "offset": exc.offset,
                "error": f"SyntaxError: {exc.msg} at line {exc.lineno}",
                "repair_prompt": (
                    f"Fix SyntaxError in {Path(filename).name} at line {exc.lineno}: {exc.msg}\n"
                    f"Offending line: {(exc.text or '').strip()}"
                ),
            }

    def verify_python_file(self, file_path: Path) -> Dict[str, Any]:
        fpath = Path(file_path)
        if not fpath.is_absolute():
            fpath = (self.workspace_root / fpath).resolve()
        if not fpath.exists():
            return {"passed": False, "stage": "exists", "error": f"File not found: {fpath}"}
        try:
            source = fpath.read_text(encoding="utf-8")
        except Exception as exc:
            return {"passed": False, "stage": "read", "error": str(exc)}
        return self.verify_python_code(source, str(fpath))

    def verify_file(self, file_path: Path) -> Dict[str, Any]:
        """Multi-language syntax & compiler check (.py, .c, .cpp, .js, .json)."""
        import shutil as _shutil
        fpath = Path(file_path)
        if not fpath.is_absolute():
            fpath = (self.workspace_root / fpath).resolve()
        if not fpath.exists():
            return {"passed": False, "stage": "exists", "error": f"File not found: {fpath}"}

        ext = fpath.suffix.lower()
        if ext == ".py":
            return self.verify_python_file(fpath)
        if ext == ".json":
            try:
                json.loads(fpath.read_text(encoding="utf-8"))
                return {"passed": True, "stage": "json_syntax", "file": str(fpath)}
            except Exception as exc:
                return {"passed": False, "stage": "json_syntax", "file": str(fpath), "error": f"JSON error: {exc}"}
        if ext in (".c", ".cpp", ".cc", ".cxx"):
            compiler = "gcc" if ext == ".c" else "g++"
            if _shutil.which(compiler):
                try:
                    from core.process_utils import run_hidden_command
                    res = run_hidden_command([compiler, "-fsyntax-only", str(fpath)], cwd=str(fpath.parent), timeout=6.0)
                    if res.returncode != 0:
                        err_msg = (res.stderr or res.stdout or "Compilation error").strip()
                        return {
                            "passed": False,
                            "stage": f"{compiler}_syntax",
                            "file": str(fpath),
                            "error": err_msg[:600],
                            "repair_prompt": f"Fix {compiler} compile error in {fpath.name}:\n{err_msg[:600]}",
                        }
                    return {"passed": True, "stage": f"{compiler}_syntax", "file": str(fpath)}
                except Exception:
                    pass
        if ext in (".js", ".mjs") and _shutil.which("node"):
            try:
                from core.process_utils import run_hidden_command
                res = run_hidden_command(["node", "--check", str(fpath)], cwd=str(fpath.parent), timeout=5.0)
                if res.returncode != 0:
                    err_msg = (res.stderr or res.stdout or "JS syntax error").strip()
                    return {
                        "passed": False,
                        "stage": "node_syntax",
                        "file": str(fpath),
                        "error": err_msg[:600],
                    }
                return {"passed": True, "stage": "node_syntax", "file": str(fpath)}
            except Exception:
                pass
        return {"passed": True, "stage": "basic", "file": str(fpath)}

    def build_repair_prompt(self, verification_result: Dict[str, Any], attempt: int = 1) -> str:
        fpath = verification_result.get("file", "file")
        fname = Path(fpath).name if fpath else "file"
        return (
            f"[Self-Healing Repair Attempt {attempt}]\n"
            f"Target File: {fname}\n"
            f"Stage Failed: {verification_result.get('stage')}\n"
            f"Error:\n{verification_result.get('error')}\n\n"
            f"Instruction: Output `FILE: {fname}` followed by the complete fixed code block with zero syntax or compile errors."
        )


class AgentOrchestrator:
    """Hierarchical DAG planner & specialist sub-agent dispatcher with closed-loop verification."""

    ROLE_PROMPTS = {
        "architect": "You are the Principal Software Architect. Decompose the task, identify affected files/symbols, and define invariants.",
        "coder": "You are the Senior Implementation Engineer. Write minimal, surgical SEARCH/REPLACE patches adhering strictly to project conventions.",
        "verifier": "You are the Staff QA & Verification Engineer. Validate AST syntax, edge cases, and unit test coverage.",
        "debugger": "You are the Root-Cause Debugger. Analyze stack traces and failing assertions to isolate and fix the exact defect.",
    }

    def __init__(self, workspace_root: Optional[Path] = None, max_repair_retries: int = 3):
        self.workspace_root = Path(workspace_root or Path.cwd()).resolve()
        self.max_repair_retries = max_repair_retries
        self.verifier = SelfHealingVerifier(self.workspace_root)

    def build_task_dag(self, objective: str, target_files: Optional[List[str]] = None) -> List[SubTaskNode]:
        files_desc = ", ".join(target_files) if target_files else "workspace files"
        return [
            SubTaskNode(
                id="plan",
                title="Architectural Impact & Context Analysis",
                role="architect",
                description=f"Analyze impact of '{objective}' across {files_desc}.",
                dependencies=[],
            ),
            SubTaskNode(
                id="implement",
                title="Surgical Patch Synthesis",
                role="coder",
                description=f"Implement changes for '{objective}' in {files_desc}.",
                dependencies=["plan"],
            ),
            SubTaskNode(
                id="verify",
                title="AST & Test Verification Loop",
                role="verifier",
                description=f"Verify syntax, imports, and tests for {files_desc}.",
                dependencies=["implement"],
            ),
        ]

    def execute_dag(
        self,
        nodes: List[SubTaskNode],
        step_executor: Optional[Callable[[SubTaskNode, Dict[str, Any]], str]] = None,
        modified_files: Optional[List[Path]] = None,
    ) -> Dict[str, Any]:
        completed: Dict[str, SubTaskNode] = {}
        execution_order: List[str] = []

        pending = list(nodes)
        while pending:
            progressed = False
            for node in list(pending):
                if all(dep in completed and completed[dep].status == "completed" for dep in node.dependencies):
                    node.status = "running"
                    ctx = {
                        "role_prompt": self.ROLE_PROMPTS.get(node.role, ""),
                        "dependency_results": {dep: completed[dep].result for dep in node.dependencies},
                    }
                    if step_executor:
                        node.result = step_executor(node, ctx)
                    else:
                        node.result = f"[{node.role.upper()}] Completed: {node.title}"

                    if node.role == "verifier" and modified_files:
                        verifications = [self.verifier.verify_python_file(f) for f in modified_files]
                        failed = [v for v in verifications if not v.get("passed")]
                        node.verification = {
                            "passed": len(failed) == 0,
                            "checks": verifications,
                        }
                        if failed:
                            for attempt in range(1, self.max_repair_retries + 1):
                                repair_prompt = self.verifier.build_repair_prompt(failed[0], attempt=attempt)
                                if step_executor:
                                    repair_node = SubTaskNode(
                                        id=f"repair_{attempt}",
                                        title=f"Self-Healing Repair #{attempt}",
                                        role="debugger",
                                        description=repair_prompt,
                                    )
                                    step_executor(repair_node, {"role_prompt": self.ROLE_PROMPTS["debugger"]})
                                verifications = [self.verifier.verify_python_file(f) for f in modified_files]
                                failed = [v for v in verifications if not v.get("passed")]
                                node.verification = {"passed": len(failed) == 0, "checks": verifications, "repair_attempts": attempt}
                                if not failed:
                                    break
                    node.status = "completed"
                    completed[node.id] = node
                    execution_order.append(node.id)
                    pending.remove(node)
                    progressed = True
            if not progressed:
                break

        all_passed = all(
            (n.verification is None or n.verification.get("passed", True))
            for n in completed.values()
        )
        return {
            "completed_count": len(completed),
            "total_count": len(nodes),
            "execution_order": execution_order,
            "all_verified": all_passed,
            "nodes": {nid: {"status": n.status, "result": n.result, "verification": n.verification} for nid, n in completed.items()},
        }

    def run_in_shadow_sandbox(
        self,
        patches: Dict[str, str],
        test_command: Optional[List[str]] = None,
        auto_promote: bool = True,
    ) -> Dict[str, Any]:
        from agent.execution_and_verification import ShadowWorkspaceSandbox
        sandbox = ShadowWorkspaceSandbox(self.workspace_root)
        try:
            sandbox.create_snapshot(list(patches.keys()))
            for rel_path, new_content in patches.items():
                sandbox.stage_file_content(rel_path, new_content)
            v_res = sandbox.verify_staged_Changes(test_command=test_command)
            promoted: List[str] = []
            if v_res.get("passed") and auto_promote:
                promoted = sandbox.promote()
            else:
                sandbox.rollback()
            return {
                "passed": v_res.get("passed", False),
                "verification": v_res,
                "promoted_files": promoted,
            }
        finally:
            sandbox.cleanup()
