"""
Consolidated Module: agent.models.model_catalog_and_router

Combines: ai.models.base_model, ai.models.model_capabilities, ai.models.model_profile, ai.models.model_context, ai.models.model_catalog, ai.models.model_health, ai.models.model_registry, ai.models.model_selector, ai.models.model_manager, ai.models.router, ai.performance.llm_optimizer
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['ai.models.base_model', 'ai.models.model_capabilities', 'ai.models.model_profile', 'ai.models.model_context', 'ai.models.model_catalog', 'ai.models.model_health', 'ai.models.model_registry', 'ai.models.model_selector', 'ai.models.model_manager', 'ai.models.router', 'ai.performance.llm_optimizer']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ai.models.base_model (ai/models/base_model.py)
# ============================================================================
"""
Base Model interface.

Ensures all models implement standard methods and uniform error handling.
"""

from core.logger import setup_logger
from core.exceptions import ModelTimeoutError

class BaseModel:
    """
    Abstract base class for AI models.
    """
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.logger = setup_logger(f"model.{provider_name}")
        
    def generate_response(self, prompt: str) -> str:
        raise NotImplementedError("Subclasses must implement generate_response")


# ============================================================================
# SECTION: ai.models.model_capabilities (ai/models/model_capabilities.py)
# ============================================================================
"""
Model Capabilities definitions.

Standardizes capability tags and maps them to known models,
including icons for each capability (Part 15).
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class CapabilityInfo:
    """Info about a single capability, including its icon (Part 15)."""
    name: str
    icon: str

class ModelCapabilities:
    """
    Constants for ALL standard model capabilities, with icons (Part 15).
    """
    # Core capabilities (Part 15)
    CODING = "Coding"
    GENERAL_CHAT = "General Chat"
    REASONING = "Reasoning"
    VISION = "Vision"
    IMAGE_GENERATION = "Image Generation"
    AUDIO = "Audio"
    SPEECH_TO_TEXT = "Speech-to-Text"
    TEXT_TO_SPEECH = "Text-to-Speech"
    VIDEO = "Video"
    TOOL_CALLING = "Tool Calling"
    FUNCTION_CALLING = "Function Calling"
    JSON_MODE = "JSON Mode"
    STRUCTURED_OUTPUT = "Structured Output"
    STREAMING = "Streaming"
    EMBEDDINGS = "Embeddings"
    LONG_CONTEXT = "Long Context"
    THINKING_MODE = "Thinking Mode"
    MULTI_MODAL = "Multi-modal"
    OFFLINE = "Offline"
    
    @classmethod
    def get_icon(cls, capability: str) -> str:
        """Get the icon for a capability (Part 15)."""
        icon_map = {
            cls.CODING: "💻",
            cls.GENERAL_CHAT: "💬",
            cls.REASONING: "🧠",
            cls.VISION: "👁",
            cls.IMAGE_GENERATION: "🖼",
            cls.AUDIO: "🎵",
            cls.SPEECH_TO_TEXT: "🎤",
            cls.TEXT_TO_SPEECH: "🔊",
            cls.VIDEO: "🎬",
            cls.TOOL_CALLING: "🛠",
            cls.FUNCTION_CALLING: "⚙",
            cls.JSON_MODE: "📄",
            cls.STRUCTURED_OUTPUT: "📋",
            cls.STREAMING: "⚡",
            cls.EMBEDDINGS: "🔍",
            cls.LONG_CONTEXT: "📚",
            cls.THINKING_MODE: "🤔",
            cls.MULTI_MODAL: "📷",
            cls.OFFLINE: "🔌",
        }
        return icon_map.get(capability, "❓")

# Pre-defined capability mappings (Heuristics)
DEFAULT_CAPABILITIES = {
    "gemini": [
        ModelCapabilities.CODING,
        ModelCapabilities.GENERAL_CHAT,
        ModelCapabilities.REASONING,
        ModelCapabilities.VISION,
        ModelCapabilities.LONG_CONTEXT,
        ModelCapabilities.MULTI_MODAL,
        ModelCapabilities.STREAMING,
    ],
    "qwen": [
        ModelCapabilities.CODING,
        ModelCapabilities.GENERAL_CHAT,
        ModelCapabilities.REASONING,
        ModelCapabilities.OFFLINE,
        ModelCapabilities.LONG_CONTEXT,
        ModelCapabilities.STREAMING,
    ],
    "deepseek": [
        ModelCapabilities.CODING,
        ModelCapabilities.REASONING,
        ModelCapabilities.THINKING_MODE,
        ModelCapabilities.LONG_CONTEXT,
        ModelCapabilities.STREAMING,
    ],
    "claude": [
        ModelCapabilities.CODING,
        ModelCapabilities.REASONING,
        ModelCapabilities.VISION,
        ModelCapabilities.TOOL_CALLING,
        ModelCapabilities.LONG_CONTEXT,
        ModelCapabilities.STREAMING,
    ],
    "llama": [
        ModelCapabilities.GENERAL_CHAT,
        ModelCapabilities.REASONING,
        ModelCapabilities.LONG_CONTEXT,
        ModelCapabilities.STREAMING,
    ]
}


# ============================================================================
# SECTION: ai.models.model_profile (ai/models/model_profile.py)
# ============================================================================
"""
Model Profile dataclass.

Describes the specifications and abilities of an AI model,
including full capabilities (Part 15), quality profile (Part 23).
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class ModelQualityProfile:
    """Model quality scores for Part 23: displays stars for Coding/Reasoning/Speed/Creativity"""
    coding: int = 5  # 1-5 stars
    reasoning: int = 5  # 1-5 stars
    speed: int = 5  # 1-5 stars
    creativity: int = 5  # 1-5 stars
    
    def to_stars(self, score: int) -> str:
        """Convert a 1-5 score to star string for display"""
        full = "★" * score
        empty = "☆" * (5 - score)
        return full + empty

@dataclass
class ModelProfile:
    """
    Metadata and capabilities of a specific AI model.
    """
    name: str
    provider: str
    version: str
    is_local: bool
    context_window: int
    max_output_tokens: int
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    supported_languages: List[str] = field(default_factory=list)
    coding_ability: int = 1  # 1 to 10 (for scoring)
    reasoning_ability: int = 1  # 1 to 10 (for scoring)
    cost_per_1k_tokens: float = 0.0
    average_response_time_ms: float = 0.0
    availability_score: float = 1.0  # 0.0 to 1.0
    
    # --- Capabilities (Part 15) ---
    supports_streaming: bool = True
    supports_vision: bool = False
    supports_tool_calling: bool = False
    supports_function_calling: bool = False
    supports_json_mode: bool = False
    supports_structured_output: bool = False
    supports_embeddings: bool = False
    supports_image_generation: bool = False
    supports_audio: bool = False
    supports_speech_to_text: bool = False
    supports_text_to_speech: bool = False
    supports_video: bool = False
    supports_thinking_mode: bool = False
    supports_multi_modal: bool = False
    capabilities: List[str] = field(default_factory=list)  # for icon display
    
    # --- Quality Profile (Part 23) ---
    quality: ModelQualityProfile = field(default_factory=ModelQualityProfile)
    
    # --- Cache Info (Part 19) ---
    last_verified: Optional[datetime] = None


# ============================================================================
# SECTION: ai.models.model_context (ai/models/model_context.py)
# ============================================================================
"""
Model Context Manager.

Determines if a task's context fits within a model's limits.
"""

from ai.models.model_profile import ModelProfile
from ai.memory.project_context import ProjectContext
from ai.engine.task import Task

class ModelContextManager:
    """
    Estimates token usage and validates context constraints.
    """
    def estimate_tokens(self, text: str) -> int:
        """Rough estimation: 1 token ~= 4 characters."""
        if not text:
            return 0
        return len(text) // 4

    def fits_in_context(self, task: Task, context: ProjectContext, profile: ModelProfile) -> bool:
        """
        Check if the required context fits within the model's window.
        """
        prompt_tokens = self.estimate_tokens(task.original_prompt) if task else 0
        
        # Estimate context overhead based on project stats
        files_to_retrieve = min(10, context.total_files) if context else 0
        estimated_file_tokens = files_to_retrieve * 500  # Assume 500 tokens per file retrieved
        
        total_estimated = prompt_tokens + estimated_file_tokens
        
        # Keep 20% margin for generation and safety
        return total_estimated < (profile.context_window * 0.8)


# ============================================================================
# SECTION: ai.models.model_catalog (ai/models/model_catalog.py)
# ============================================================================
"""
Model Catalog.

Permanent catalog of ALL officially supported models in OwnCode.
Each model has a profile, provider, and metadata, with
capabilities (Part15) and quality profiles (Part23).
"""

from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from core.logger import setup_logger
from ai.models.model_profile import ModelProfile, ModelQualityProfile
from ai.models.model_capabilities import ModelCapabilities

logger = setup_logger(__name__)


class ModelState(Enum):
    """All possible model states."""
    READY = "Ready"
    CONNECTED = "Connected"
    INSTALLED = "Installed"
    API_REQUIRED = "API Required"
    API_MISSING = "API Missing"
    AUTH_FAILED = "Authentication Failed"
    OFFLINE = "Offline"
    DISCONNECTED = "Disconnected"
    DOWNLOADING = "Downloading"
    DISABLED = "Disabled"
    UNSUPPORTED = "Unsupported"
    UNKNOWN = "Unknown"
    
    @classmethod
    def get_icon(cls, state: 'ModelState') -> str:
        """Get status icon for model state (Part7)"""
        icon_map = {
            cls.READY: "✅",
            cls.CONNECTED: "🔵",
            cls.API_REQUIRED: "🟡",
            cls.API_MISSING: "🟡",
            cls.DISCONNECTED: "🟠",
            cls.OFFLINE: "🔴",
            cls.UNSUPPORTED: "⚫",
            cls.DOWNLOADING: "⏳",
            cls.AUTH_FAILED: "🔴",
        }
        return icon_map.get(state, "❓")


@dataclass
class CatalogEntry:
    """Single entry in the model catalog."""
    profile: ModelProfile
    state: ModelState = ModelState.UNKNOWN
    is_officially_supported: bool = True


class ModelCatalog:
    """
    Permanent catalog of all supported models.
    
    Separates the concept of:
    1. Officially supported models (always in catalog)
    2. Currently available models (state depends on connectivity/config)
    """
    
    def __init__(self):
        self._catalog: Dict[str, CatalogEntry] = {}
        self._load_official_models()
        logger.info("ModelCatalog initialized with official models")
        
    def _load_official_models(self):
        """
        Dynamically loads models from providers. 
        Hardcoded model lists have been removed per architecture guidelines.
        """
        # Providers will populate the catalog at runtime during discovery.
        logger.info(f"Loaded {len(self._catalog)} official models into catalog")
        
    def get_entry(self, model_name: str) -> Optional[CatalogEntry]:
        """Get a catalog entry by model name."""
        return self._catalog.get(model_name)
        
    def get_all_entries(self) -> List[CatalogEntry]:
        """Get all catalog entries."""
        return list(self._catalog.values())
        
    def get_entries_by_provider(self, provider_name: str) -> List[CatalogEntry]:
        """Get all entries for a specific provider."""
        return [e for e in self._catalog.values() if e.profile.provider == provider_name]
        
    def update_model_state(self, model_name: str, state: ModelState):
        """Update the state of a model."""
        if model_name in self._catalog:
            self._catalog[model_name].state = state
            logger.debug(f"Updated model state: {model_name} -> {state.value}")
            
    def add_custom_model(self, profile: ModelProfile) -> str:
        """Add a custom user-defined model to the catalog."""
        entry = CatalogEntry(
            profile=profile,
            state=ModelState.UNKNOWN,
            is_officially_supported=False
        )
        self._catalog[profile.name] = entry
        logger.info(f"Added custom model to catalog: {profile.name}")
        return profile.name


# ============================================================================
# SECTION: ai.models.model_health (ai/models/model_health.py)
# ============================================================================
"""
Model Health monitoring.

Tracks the operational status and reliability of models.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class ModelHealth:
    """
    Health metrics for a single model.
    """
    model_name: str
    is_online: bool = True
    average_latency_ms: float = 0.0
    last_successful_request: Optional[datetime] = None
    consecutive_failures: int = 0
    current_availability: float = 1.0  # 1.0 = healthy, 0.0 = offline

    def record_success(self, latency_ms: float):
        """Record a successful execution."""
        self.is_online = True
        self.consecutive_failures = 0
        self.last_successful_request = datetime.utcnow()
        if self.average_latency_ms == 0.0:
            self.average_latency_ms = latency_ms
        else:
            self.average_latency_ms = (self.average_latency_ms * 0.9) + (latency_ms * 0.1)
        self.current_availability = 1.0

    def record_failure(self):
        """Record a failed execution."""
        self.consecutive_failures += 1
        if self.consecutive_failures >= 3:
            self.is_online = False
            self.current_availability = 0.0
        else:
            self.current_availability = max(0.0, 1.0 - (self.consecutive_failures * 0.3))


# ============================================================================
# SECTION: ai.models.model_registry (ai/models/model_registry.py)
# ============================================================================
"""
Model Registry.

Central registry for managing all available models in the system.

The Model Registry now works in conjunction with the Provider Registry and Model Catalog to:
- Load models from catalog and provider configurations
- Track model health and availability
- Support model-specific routing
- Track model states
"""

from typing import Dict, List, Optional, Any
from core.logger import setup_logger
from ai.models.model_profile import ModelProfile
from ai.models.model_health import ModelHealth
from ai.models.model_catalog import ModelCatalog, ModelState
from ai.providers.provider_registry import ProviderRegistry
from ai.providers.base_provider import ProviderConfig

logger = setup_logger(__name__)

class ModelRegistry:
    """
    Manages registration, lifecycle, and querying of AI models.
    
    The model registry now works with the provider platform to:
    - Load models from catalog and provider configurations
    - Map providers to their available models
    - Track model-specific health metrics
    - Track model states
    """
    def __init__(self, provider_registry: Optional[ProviderRegistry] = None):
        self.provider_registry = provider_registry
        self.catalog = ModelCatalog()
        self._health: Dict[str, ModelHealth] = {}
        self._enabled: Dict[str, bool] = {}
        self._provider_models: Dict[str, List[str]] = {}  # provider -> list of model IDs
        
        logger.info("ModelRegistry initialized with catalog")

    def register_model(self, profile: ModelProfile, enabled: bool = True):
        """Register a new model to the system."""
        if profile.name not in self.catalog._catalog:
            self.catalog.add_custom_model(profile)
        self._health[profile.name] = ModelHealth(model_name=profile.name)
        self._enabled[profile.name] = enabled
        
        # Link to provider if available
        provider_name = profile.provider
        if provider_name:
            if provider_name not in self._provider_models:
                self._provider_models[provider_name] = []
            if profile.name not in self._provider_models[provider_name]:
                self._provider_models[provider_name].append(profile.name)
        
        logger.info(f"Registered model: {profile.name}")

    def register_model_from_provider(self, provider_name: str, model_info: Dict[str, Any]):
        """
        Register a model from provider discovery results.
        
        Args:
            provider_name: Name of the provider
            model_info: Model information from provider
        """
        model_id = model_info.get("id", model_info.get("name", ""))
        model_name = f"{provider_name}:{model_id}"
        
        # Check if model is already in catalog first
        catalog_entry = self.catalog.get_entry(model_name)
        if catalog_entry:
            profile = catalog_entry.profile
        else:
            profile = ModelProfile(
                name=model_name,
                provider=provider_name,
                version=model_info.get("version", "1.0"),
                is_local=model_info.get("type", "cloud") == "local",
                context_window=model_info.get("context_window", 4096),
                max_output_tokens=model_info.get("max_output_tokens", 4096),
                strengths=model_info.get("capabilities", []),
                weaknesses=[],
                supported_languages=model_info.get("supported_languages", ["*"]),
                coding_ability=5,
                reasoning_ability=5,
                cost_per_1k_tokens=0.0,
                average_response_time_ms=0.0,
                availability_score=1.0,
            )
        
        self.register_model(profile, enabled=True)

    def load_models_from_provider(self, provider_name: str) -> List[str]:
        """
        Load all models from a specific provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            List of registered model names
        """
        models = []
        provider = self.provider_registry.get_provider(provider_name) if self.provider_registry else None
        
        # First, get all catalog entries for this provider
        catalog_entries = self.catalog.get_entries_by_provider(provider_name)
        for entry in catalog_entries:
            self.register_model(entry.profile, enabled=True)
            models.append(entry.profile.name)
        
        # Then add any provider-discovered models
        if provider:
            provider_models = provider.get_models()
            for model_id, model_info in provider_models.items():
                model_name = f"{provider_name}:{model_id}"
                if self.catalog.get_entry(model_name) is None:
                    self.register_model_from_provider(provider_name, model_info)
                    models.append(model_name)
        
        return models

    def enable_model(self, model_name: str):
        if model_name in self.catalog._catalog:
            self._enabled[model_name] = True
            self.catalog.update_model_state(model_name, ModelState.READY)

    def disable_model(self, model_name: str):
        if model_name in self.catalog._catalog:
            self._enabled[model_name] = False
            self.catalog.update_model_state(model_name, ModelState.DISABLED)

    def get_profile(self, model_name: str) -> Optional[ModelProfile]:
        entry = self.catalog.get_entry(model_name)
        return entry.profile if entry else None

    def get_health(self, model_name: str) -> Optional[ModelHealth]:
        return self._health.get(model_name)

    def get_all_catalog_models(self) -> List[str]:
        """Return all models in the catalog."""
        return [entry.profile.name for entry in self.catalog.get_all_entries()]

    def get_available_models(self) -> List[str]:
        """Return a list of enabled and healthy models."""
        available = []
        for name in self.get_all_catalog_models():
            entry = self.catalog.get_entry(name)
            if entry and entry.state in [ModelState.READY, ModelState.CONNECTED, ModelState.INSTALLED]:
                available.append(name)
        return available

    def get_models_for_provider(self, provider_name: str) -> List[str]:
        """Get all models in catalog for a specific provider."""
        entries = self.catalog.get_entries_by_provider(provider_name)
        return [e.profile.name for e in entries]

    def get_provider_for_model(self, model_name: str) -> Optional[str]:
        """Get the provider name for a specific model."""
        entry = self.catalog.get_entry(model_name)
        return entry.profile.provider if entry else None
        
    def update_model_state(self, model_name: str, state: ModelState):
        """Update the state of a model in catalog."""
        self.catalog.update_model_state(model_name, state)


# ============================================================================
# SECTION: ai.models.model_selector (ai/models/model_selector.py)
# ============================================================================
"""
Intelligent Model Selector.

Determines the best model for a given task and context.
"""

from typing import Tuple, Dict, Any
from core.logger import setup_logger
from ai.models.model_registry import ModelRegistry
from ai.models.model_context import ModelContextManager
from ai.models.model_profile import ModelProfile
from ai.memory.project_context import ProjectContext
from ai.engine.task import Task

logger = setup_logger(__name__)

class ModelSelector:
    """
    Scores and selects the best model for a task.
    """
    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self.context_manager = ModelContextManager()

    def select_best_model(self, task: Task, plan: Any, context: ProjectContext, require_local: bool = False) -> Tuple[str, str]:
        """
        Evaluate all available models and select the best one based on weighted scores.
        Returns: (selected_model_name, reason_for_selection)
        """
        available = self.registry.get_available_models()
        if not available:
            return "none", "No available models in registry."
            
        best_model = None
        best_score = -1.0
        reason = ""

        for model_name in available:
            profile = self.registry.get_profile(model_name)
            health = self.registry.get_health(model_name)
            
            if not profile or not health:
                continue
                
            if require_local and not profile.is_local:
                continue

            if not self.context_manager.fits_in_context(task, context, profile):
                continue

            score = self._calculate_score(task, profile, health)
            
            if score > best_score:
                best_score = score
                best_model = model_name
                reason = self._generate_reason(task, profile)

        if not best_model:
            # Fallback to the first available if all else fails
            fallback = available[0]
            logger.warning(f"No optimal model found. Falling back to {fallback}.")
            return fallback, "Fallback selected due to constraints."

        logger.info(f"Selected model: {best_model} (Score: {best_score})")
        return best_model, reason

    def _calculate_score(self, task: Task, profile: ModelProfile, health: Any) -> float:
        """
        Compute a weighted score based on task complexity, model ability, and health.
        """
        score = 0.0
        
        # Coding vs Reasoning weighting
        if task and task.estimated_complexity.value in ("complex", "expert"):
            score += profile.reasoning_ability * 2.0
        else:
            score += profile.coding_ability * 1.5

        # Health penalty
        score *= health.current_availability
        
        return score

    def _generate_reason(self, task: Task, profile: ModelProfile) -> str:
        return f"Selected {profile.name} for its {profile.coding_ability}/10 coding ability and health status."


# ============================================================================
# SECTION: ai.models.model_manager (ai/models/model_manager.py)
# ============================================================================
"""
Model Manager.

Unified interface for all model interactions through the provider platform.

Uses the provider architecture to route requests to appropriate providers
based on task requirements, provider capabilities, and health status.
"""

from typing import Any, Optional
from core.logger import setup_logger
from ai.models.model_registry import ModelRegistry
from ai.models.model_selector import ModelSelector
from ai.engine.task import Task
from ai.memory.project_context import ProjectContext
from ai.providers.provider_router import ProviderRouter
from ai.providers.provider_manager import ProviderManager
from ai.providers.provider_registry import ProviderRegistry

logger = setup_logger(__name__)

class ModelManager:
    """
    Coordinates model selection, routing, and execution through the provider platform.
    
    The ModelManager now uses the ProviderRouter and ProviderManager to:
    - Select the best provider based on task requirements
    - Route requests to appropriate providers
    - Handle provider health and reconnection
    - Support streaming, tool calling, and other capabilities
    """
    def __init__(
        self,
        provider_registry: ProviderRegistry,
        provider_manager: ProviderManager,
        model_registry: ModelRegistry,
        event_bus: Any
    ):
        self.provider_registry = provider_registry
        self.provider_manager = provider_manager
        self.model_registry = model_registry
        self.event_bus = event_bus
        self.selector = ModelSelector(model_registry)
        self.router = ProviderRouter(provider_registry)

    def execute_request(
        self,
        prompt: str,
        task: Task,
        context: ProjectContext,
        plan: Any = None,
        preferred_provider: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Selects the best provider and executes the request, handling fallbacks.
        
        Args:
            prompt: The user prompt
            task: The task being executed
            context: Project context
            plan: Optional execution plan
            preferred_provider: Preferred provider name (optional)
            **kwargs: Additional provider-specific parameters
            
        Returns:
            The generated response
        """
        # Step 1: Select Provider based on task requirements
        provider = self.router.select_provider(
            task=task,
            require_streaming=kwargs.get("streaming", False),
            require_vision=kwargs.get("require_vision", False),
            require_tool_calling=kwargs.get("require_tool_calling", False),
            preferred_provider=preferred_provider,
        )
        
        if not provider:
            raise RuntimeError("No suitable provider available to execute the request.")

        provider_name = provider.config.provider_name
        logger.info(f"ModelManager: Selected provider {provider_name}")
        
        # Step 2: Execute with retries
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                # Generate response through the provider
                response = provider.generate_response(
                    prompt=prompt,
                    **kwargs
                )
                
                # Record health
                self.provider_manager._health.record_request(provider_name, success=True)
                logger.info(f"ModelManager: Successfully executed request with {provider_name}")
                
                return response
                
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed on attempt {attempt + 1}: {e}")
                self.provider_manager._health.record_request(provider_name, success=False)
                
                # If provider goes offline, re-select
                if not provider.is_connected():
                    logger.info("Provider went offline. Attempting to select a fallback provider.")
                    provider = self.router.select_provider(
                        task=task,
                        require_streaming=kwargs.get("streaming", False),
                        require_vision=kwargs.get("require_vision", False),
                        require_tool_calling=kwargs.get("require_tool_calling", False),
                        preferred_provider=preferred_provider,
                    )
                    if not provider:
                        raise RuntimeError("All providers exhausted.")

        raise RuntimeError(f"Failed to execute request after {max_retries} retries.")


# ============================================================================
# SECTION: ai.models.router (ai/models/router.py)
# ============================================================================
"""
Smart Model Router.

Selects the best model for the task from available ones,
never selects an unusable model, falls back gracefully.
"""

from typing import Optional, List
from enum import Enum
from core.logger import setup_logger
from ai.models.model_registry import ModelRegistry
from ai.models.model_catalog import ModelState, CatalogEntry
from ai.providers.provider_registry import ProviderRegistry
from ai.providers.provider_manager import ProviderManager
from ui.settings_manager import get_settings_manager

logger = setup_logger(__name__)


class TaskType(Enum):
    """Types of tasks the router can optimize for."""
    SIMPLE_CHAT = "simple_chat"
    CODING = "coding"
    HEAVY_REASONING = "heavy_reasoning"
    DOCUMENTATION = "documentation"
    ARCHITECTURE = "architecture"
    LARGE_CONTEXT = "large_context"
    DEBUGGING = "debugging"
    TOOL_EXECUTION = "tool_execution"
    FIM_COMPLETION = "fim_completion"


class RoutingTier(Enum):
    """5-Tier Local-First Execution Hierarchy (Phase 1 Upgrade)."""
    TIER_0_FIM = "tier_0_fim"
    TIER_1_FAST_CONTEXT = "tier_1_fast_context"
    TIER_2_SINGLE_FILE_EDIT = "tier_2_single_file_edit"
    TIER_3_MULTI_FILE_AGENT = "tier_3_multi_file_agent"
    TIER_4_DEEP_ARCHITECTURE = "tier_4_deep_architecture"


@dataclass
class RoutingDecision:
    """Structured per-turn routing decision produced by UnifiedModelRouter."""
    tier: RoutingTier
    task_type: TaskType
    selected_model: Optional[str] = None
    requires_tools: bool = False
    recommended_temperature: float = 0.3
    max_context_budget_ratio: float = 0.70
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier.value,
            "task_type": self.task_type.value,
            "selected_model": self.selected_model,
            "requires_tools": self.requires_tools,
            "recommended_temperature": self.recommended_temperature,
            "max_context_budget_ratio": self.max_context_budget_ratio,
            "reasoning": self.reasoning,
        }


class IntentClassifier:
    """Fast (<1ms) deterministic + structural classifier for per-turn model routing."""

    _DEBUG_KEYWORDS = (
        "traceback (most recent call last)", "exception:", "error:", "syntaxerror",
        "typeerror", "valueerror", "attributeerror", "indexerror", "keyerror",
        "segfault", "crash", "bug", "fix the error", "why is this failing", "stack trace",
    )
    _ARCH_KEYWORDS = (
        "architecture", "design pattern", "system design", "scalability", "refactor entire",
        "migrate", "roadmap", "3-phase", "blueprint", "microservice", "database schema",
    )
    _AGENT_KEYWORDS = (
        "across all files", "search the project", "find all references", "run tests",
        "create a new module", "update all callers", "implement phase", "build a complete",
    )
    _CODE_KEYWORDS = (
        "def ", "class ", "import ", "function", "implement", "refactor", "write code",
        "optimize", "patch", "modify", "update ", "add a method", "```",
    )
    _DOC_KEYWORDS = (
        "docstring", "readme", "documentation", "explain", "summarize", "comment",
    )

    @classmethod
    def classify(
        cls,
        prompt: str,
        mode: str = "chat",
        has_selection: bool = False,
        file_count: int = 0,
    ) -> RoutingDecision:
        text = (prompt or "").strip()
        lower = text.lower()
        mode_norm = (mode or "chat").strip().lower()

        if mode_norm == "fim":
            return RoutingDecision(
                tier=RoutingTier.TIER_0_FIM,
                task_type=TaskType.FIM_COMPLETION,
                requires_tools=False,
                recommended_temperature=0.1,
                max_context_budget_ratio=0.35,
                reasoning="Inline FIM completion mode",
            )

        if mode_norm == "agent":
            is_deep = any(k in lower for k in cls._ARCH_KEYWORDS) or any(k in lower for k in cls._DEBUG_KEYWORDS)
            return RoutingDecision(
                tier=RoutingTier.TIER_4_DEEP_ARCHITECTURE if is_deep else RoutingTier.TIER_3_MULTI_FILE_AGENT,
                task_type=TaskType.DEBUGGING if any(k in lower for k in cls._DEBUG_KEYWORDS) else TaskType.TOOL_EXECUTION,
                requires_tools=True,
                recommended_temperature=0.2,
                max_context_budget_ratio=0.80,
                reasoning="Autonomous Agent mode with ReAct tool execution",
            )

        if mode_norm == "edit":
            if file_count > 1 or any(k in lower for k in cls._AGENT_KEYWORDS):
                return RoutingDecision(
                    tier=RoutingTier.TIER_3_MULTI_FILE_AGENT,
                    task_type=TaskType.CODING,
                    requires_tools=True,
                    recommended_temperature=0.2,
                    max_context_budget_ratio=0.75,
                    reasoning="Multi-file Edit mode request",
                )
            return RoutingDecision(
                tier=RoutingTier.TIER_2_SINGLE_FILE_EDIT,
                task_type=TaskType.CODING,
                requires_tools=False,
                recommended_temperature=0.2,
                max_context_budget_ratio=0.70,
                reasoning="Scoped Edit mode request",
            )

        if any(k in lower for k in cls._DEBUG_KEYWORDS):
            return RoutingDecision(
                tier=RoutingTier.TIER_4_DEEP_ARCHITECTURE,
                task_type=TaskType.DEBUGGING,
                requires_tools=False,
                recommended_temperature=0.2,
                max_context_budget_ratio=0.75,
                reasoning="Detected traceback/error debugging intent",
            )

        if any(k in lower for k in cls._ARCH_KEYWORDS) or len(text) > 3500:
            return RoutingDecision(
                tier=RoutingTier.TIER_4_DEEP_ARCHITECTURE,
                task_type=TaskType.ARCHITECTURE if len(text) <= 6000 else TaskType.LARGE_CONTEXT,
                requires_tools=False,
                recommended_temperature=0.3,
                max_context_budget_ratio=0.80,
                reasoning="Detected architectural/large-context reasoning intent",
            )

        if any(k in lower for k in cls._AGENT_KEYWORDS) or file_count > 2:
            return RoutingDecision(
                tier=RoutingTier.TIER_3_MULTI_FILE_AGENT,
                task_type=TaskType.TOOL_EXECUTION,
                requires_tools=True,
                recommended_temperature=0.25,
                max_context_budget_ratio=0.75,
                reasoning="Detected multi-file workspace operation intent",
            )

        if has_selection or any(k in lower for k in cls._CODE_KEYWORDS):
            return RoutingDecision(
                tier=RoutingTier.TIER_2_SINGLE_FILE_EDIT,
                task_type=TaskType.CODING,
                requires_tools=False,
                recommended_temperature=0.25,
                max_context_budget_ratio=0.70,
                reasoning="Detected code generation or modification intent",
            )

        if any(k in lower for k in cls._DOC_KEYWORDS):
            return RoutingDecision(
                tier=RoutingTier.TIER_1_FAST_CONTEXT,
                task_type=TaskType.DOCUMENTATION,
                requires_tools=False,
                recommended_temperature=0.4,
                max_context_budget_ratio=0.60,
                reasoning="Detected documentation or explanation intent",
            )

        return RoutingDecision(
            tier=RoutingTier.TIER_1_FAST_CONTEXT,
            task_type=TaskType.SIMPLE_CHAT,
            requires_tools=False,
            recommended_temperature=0.5,
            max_context_budget_ratio=0.60,
            reasoning="Standard conversational query",
        )


class ModelRouter:
    """
    Smart model router that selects the appropriate model for the task.
    """
    def __init__(self, model_registry: ModelRegistry, provider_manager: ProviderManager):
        self.model_registry = model_registry
        self.provider_manager = provider_manager
        logger.info("ModelRouter (Smart) initialized.")
        
    def _is_provider_healthy(self, provider_name: str) -> bool:
        """Check if a provider is healthy, available, and connected"""
        provider = self.provider_manager.registry.get_provider(provider_name)
        if not provider:
            return False
        if not provider.config.enabled:
            return False
        return provider.is_available()
        
    def _get_healthy_models(self) -> List[CatalogEntry]:
        """Get all models from healthy, available providers"""
        all_entries = self.model_registry.catalog.get_all_entries()
        healthy = []
        
        for entry in all_entries:
            if not entry:
                continue
            if self._is_provider_healthy(entry.profile.provider):
                healthy.append(entry)
        
        return healthy

    def _routing_policy(self) -> str:
        return str(get_settings_manager().get("models", "routing_policy", "local_only"))

    def _is_local(self, entry: CatalogEntry) -> bool:
        return bool(entry.profile.is_local or entry.profile.provider in ("llama_cpp", "ollama", "qwen"))

    def select_best_model(self, task_type: TaskType = TaskType.SIMPLE_CHAT) -> Optional[str]:
        """
        Select the best available model for the given task type.
        Never returns an unusable model.
        Prioritizes local models first, then highest quality available.
        EXCLUDES deepseek per user request.
        ONLY selects models that can reply (are connected and healthy).
        """
        healthy_entries = self._get_healthy_models()
        if not healthy_entries:
            logger.warning("No healthy models available")
            return None
            
        # Score models based on task type and preferences (Part 8)
        scored = []
        for entry in healthy_entries:
            profile = entry.profile
            score = 0

            if self._routing_policy() == "local_only" and not self._is_local(entry):
                continue
            
            # 0. User requested to ban deepseek from auto-selection
            if "deepseek" in profile.name.lower():
                logger.info(f"Skipping deepseek model {profile.name} per user request")
                continue

            # 0.5 Check if model can actually reply - get provider and verify connection
            provider = self.provider_manager.registry.get_provider(profile.provider)
            if not provider:
                logger.info(f"Skipping {profile.name} - provider {profile.provider} not found")
                continue
            if not provider.is_connected():
                logger.info(f"Skipping {profile.name} - provider {profile.provider} not connected")
                continue
            if not provider.is_available():
                logger.info(f"Skipping {profile.name} - provider {profile.provider} not available")
                continue
            
            # 1. Highest priority: local models (Part 5)
            if profile.is_local:
                score += 10000

            if profile.provider == "llama_cpp":
                score += 20000
                
            # 1.5 Model specific health check
            model_health = self.model_registry._health.get(profile.name)
            if model_health:
                if not model_health.is_online:
                    logger.info(f"Skipping {profile.name} - model health shows offline")
                    continue  # Skip models that are known to fail/not reply
                score += model_health.current_availability * 500
                
            # 2. Availability and provider health
            health_metrics = self.provider_manager._health.get_metrics(profile.provider)
            if health_metrics:
                score += health_metrics.current_availability * 100
                # Lower latency is better
                if health_metrics.average_latency_ms > 0:
                    score += 500 - min(health_metrics.average_latency_ms / 10, 400)
                
            # 3. Context window
            score += profile.context_window // 1000
                
            # 4. Task-specific optimization
            if task_type == TaskType.SIMPLE_CHAT:
                score += 50
                if "fast" in profile.strengths:
                    score += 150
                if profile.supports_streaming:
                    score += 50
            elif task_type == TaskType.CODING:
                score += profile.coding_ability * 100
                if "coding" in profile.strengths:
                    score += 300
                if profile.supports_tool_calling:
                    score += 100
                if profile.supports_function_calling:
                    score += 100
            elif task_type in (TaskType.HEAVY_REASONING, TaskType.ARCHITECTURE):
                score += profile.reasoning_ability * 100
                if "reasoning" in profile.strengths:
                    score += 300
                if "architecture" in profile.strengths or "coding" in profile.strengths:
                    score += 150
            elif task_type == TaskType.DEBUGGING:
                score += (profile.coding_ability + profile.reasoning_ability) * 75
                if "coding" in profile.strengths or "debugging" in profile.strengths:
                    score += 300
            elif task_type == TaskType.TOOL_EXECUTION:
                score += profile.coding_ability * 100
                if profile.supports_tool_calling or profile.supports_function_calling:
                    score += 350
                if "coding" in profile.strengths:
                    score += 200
            elif task_type == TaskType.DOCUMENTATION:
                score += profile.reasoning_ability * 60
                if "fast" in profile.strengths:
                    score += 100
            elif task_type == TaskType.FIM_COMPLETION:
                score += profile.coding_ability * 80
                if "fast" in profile.strengths or "coding" in profile.strengths:
                    score += 250
            elif task_type == TaskType.LARGE_CONTEXT:
                score += profile.context_window // 500
                
            # 5. Cost preference (cheaper is better)
            score += (1.0 - min(profile.cost_per_1k_tokens / 3.0, 1.0)) * 100
                
            scored.append((score, profile.name))
            
        if not scored:
            logger.warning("No models passed health and availability checks")
            return None
            
        # Sort by score, descending
        scored.sort(reverse=True, key=lambda x: x[0])
        best_model = scored[0][1]
        logger.info(
            f"Automatic Router: Selected {best_model} "
            f"(Score: {scored[0][0]:.0f}, "
            f"Task: {task_type.value}, "
            f"Can reply: Yes, "
            f"Active: Yes)"
        )
        
        # Log reasoning
        if scored:
            logger.debug("Top 5 candidates:")
            for i, (score, name) in enumerate(scored[:5]):
                logger.debug(f"  {i+1}. {name} - score: {score}")
                
        return best_model
        
    def dispatch(self, model_name: Optional[str], prompt: str, task_type: TaskType = TaskType.SIMPLE_CHAT) -> Optional[str]:
        """
        Dispatch request: if model_name is provided, use it (if available).
        Otherwise, select the best model automatically.
        """
        if model_name:
            # Verify model is available
            entry = self.model_registry.catalog.get_entry(model_name)
            if entry and self._is_provider_healthy(entry.profile.provider):
                logger.info(f"Using explicitly requested model: {model_name}")
                return model_name
            else:
                logger.warning(f"Model {model_name} not available, selecting best alternative")
        
        # Select best available model automatically
        model_name = self.select_best_model(task_type)
        
        if not model_name:
            logger.error("No healthy models available")
            return None
            
        logger.info(f"Dispatching request to model: {model_name}")
        return model_name

    def classify_intent(
        self,
        prompt: str,
        mode: str = "chat",
        has_selection: bool = False,
        file_count: int = 0,
    ) -> RoutingDecision:
        return IntentClassifier.classify(
            prompt=prompt,
            mode=mode,
            has_selection=has_selection,
            file_count=file_count,
        )

    def route_for_turn(
        self,
        prompt: str,
        requested_model: Optional[str] = None,
        mode: str = "chat",
        has_selection: bool = False,
        file_count: int = 0,
    ) -> RoutingDecision:
        decision = self.classify_intent(
            prompt=prompt,
            mode=mode,
            has_selection=has_selection,
            file_count=file_count,
        )
        explicit = None if (not requested_model or requested_model == "auto") else requested_model
        decision.selected_model = self.dispatch(explicit, prompt, decision.task_type)
        return decision
        
    def get_recommendation(self, unavailable_model: Optional[str] = None, task_type: TaskType = TaskType.SIMPLE_CHAT) -> Optional[dict]:
        """
        Get a smart recommendation for the best available model (Part20),
        explaining why the original was unavailable and recommending the alternative.
        """
        from ai.models.model_catalog import ModelState
        
        recommendation = {
            "original_model": unavailable_model,
            "available": False,
            "reason": "",
            "recommended_model": None,
            "recommended_display_name": None,
            "score": 0
        }
        
        if unavailable_model:
            entry = self.model_registry.catalog.get_entry(unavailable_model)
            if not entry:
                recommendation["reason"] = f"Model '{unavailable_model}' not found in catalog"
            elif not self._is_provider_healthy(entry.profile.provider):
                provider = self.provider_manager.registry.get_provider(entry.profile.provider)
                if not provider:
                    recommendation["reason"] = f"Provider '{entry.profile.provider}' not found"
                elif not provider.config.enabled:
                    recommendation["reason"] = f"Provider '{entry.profile.provider}' is disabled"
                elif not provider.is_connected():
                    recommendation["reason"] = f"Provider '{entry.profile.provider}' not connected"
                else:
                    recommendation["reason"] = f"Provider '{entry.profile.provider}' unavailable"
        
        # Get best available model
        best_name = self.select_best_model(task_type)
        if best_name:
            entry = self.model_registry.catalog.get_entry(best_name)
            if entry:
                recommendation["available"] = True
                recommendation["recommended_model"] = best_name
                recommendation["recommended_display_name"] = entry.profile.name
        
        return recommendation


UnifiedModelRouter = ModelRouter


# ============================================================================
# SECTION: ai.performance.llm_optimizer (ai/performance/llm_optimizer.py)
# ============================================================================
"""
LLM Performance Optimizer

Reduces latency and improves response times for local LLMs (Ollama, etc.):
1. Model preloading and keep-alive
2. Context window optimization
3. Response caching
4. Parallel processing
5. Smart batching
"""

import json
import time
import threading
import subprocess
from typing import Dict, Optional, Any, List
from pathlib import Path
from datetime import datetime, timedelta
from collections import OrderedDict

from core.logger import setup_logger
from core.event_bus import EventBus
from core.process_utils import hidden_subprocess_kwargs

logger = setup_logger(__name__)

# Model ids in this app are "<provider>:<model>" — but a bare Ollama tag also
# contains a colon ("qwen2.5-coder:7b"), so a leading segment is only a provider
# prefix when it actually names one. These are the names the factory registers,
# kept here so a prefix is still recognised before the registry has loaded.
_PROVIDER_KEYS = frozenset({
    "ollama", "openai", "anthropic", "gemini", "google", "groq", "cerebras",
    "fireworks", "deepinfra", "together", "custom", "qwen", "azure",
    "mistral", "openrouter", "deepseek", "lmstudio", "local", "llama_cpp",
})


class ResponseCache:
    """
    LRU cache for LLM responses.
    
    Caches responses based on (prompt, model, context) tuple.
    Significantly speeds up repeated or similar queries.
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
    
    def _make_key(self, prompt: str, model_id: str, context: str = "") -> str:
        """Create cache key from prompt, model, and context."""
        import hashlib
        content = f"{model_id}:{prompt}:{context}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, prompt: str, model_id: str, context: str = "") -> Optional[str]:
        """Get cached response if available and not expired."""
        with self._lock:
            key = self._make_key(prompt, model_id, context)
            
            if key in self._cache:
                entry = self._cache[key]
                
                # Check if expired
                if datetime.now() - entry['timestamp'] > timedelta(seconds=self.ttl_seconds):
                    del self._cache[key]
                    self._misses += 1
                    return None
                
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                self._hits += 1
                logger.debug(f"Cache HIT for prompt hash: {key[:8]}")
                return entry['response']
            
            self._misses += 1
            return None
    
    def set(self, prompt: str, model_id: str, response: str, context: str = ""):
        """Cache a response."""
        with self._lock:
            key = self._make_key(prompt, model_id, context)
            
            # Remove oldest if at capacity
            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            
            self._cache[key] = {
                'response': response,
                'timestamp': datetime.now()
            }
            logger.debug(f"Cached response for prompt hash: {key[:8]}")
    
    def clear(self):
        """Clear all cached responses."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            logger.info("Response cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            'hits': self._hits,
            'misses': self._misses,
            'total_queries': total,
            'hit_rate_percent': round(hit_rate, 2),
            'cache_size': len(self._cache),
            'max_size': self.max_size
        }


class ModelPreloader:
    """
    Preloads the model the user is about to talk to, so the first message
    doesn't pay for loading weights off disk.

    Ollama unloads models after inactivity; a periodic heartbeat keeps the
    active one resident for as long as the IDE is open.
    """

    def __init__(self, provider, keep_alive_minutes: int = 30):
        self.provider = provider
        self.keep_alive_minutes = keep_alive_minutes
        self._preloaded_models: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        self._keep_alive_thread = None
        self._running = False
        self._wake = threading.Event()
        # Bare model name (no "provider:" prefix) currently selected in the UI.
        self._active_model: Optional[str] = None

    @property
    def keep_alive(self) -> str:
        """Ollama keep_alive string; -1 means "never unload"."""
        if self.keep_alive_minutes < 0:
            return "-1"
        return f"{self.keep_alive_minutes}m"

    def set_active_model(self, model_id: Optional[str]):
        """Remember which model the heartbeat should keep resident."""
        with self._lock:
            self._active_model = model_id or None

    def preload_model(self, model_id: str, force: bool = False) -> bool:
        """Load a model into memory. Returns True if it is resident after."""
        if not model_id or self.provider is None:
            return False
        try:
            # The provider knows the cheap way: an empty prompt loads the
            # weights and generates nothing. Fall back to a 1-token
            # generation for providers that don't implement warm_model.
            warm = getattr(self.provider, "warm_model", None)
            if callable(warm):
                ok = bool(warm(model_id, keep_alive=self.keep_alive, force=force))
            else:
                self.provider.generate_response(
                    prompt="Hi", model_id=model_id,
                    num_predict=1, keep_alive=self.keep_alive)
                ok = True

            if ok:
                with self._lock:
                    self._preloaded_models[model_id] = datetime.now()
                logger.info(f"✓ Model preloaded: {model_id}")
            return ok

        except Exception as e:
            logger.error(f"Failed to preload model {model_id}: {e}")
            return False

    def start_keep_alive(self, models: Optional[List[str]] = None):
        """Start the heartbeat thread that keeps warm models warm."""
        if self._running:
            return
        self._running = True
        self._wake.clear()
        self._keep_alive_thread = threading.Thread(
            target=self._keep_alive_loop,
            args=(list(models or []),),
            daemon=True,
        )
        self._keep_alive_thread.start()
        logger.info("Keep-alive heartbeat started")

    def stop_keep_alive(self):
        """Stop keep-alive thread."""
        self._running = False
        self._wake.set()          # interrupt the sleep instead of waiting it out
        if self._keep_alive_thread:
            self._keep_alive_thread.join(timeout=5)
        logger.info("Keep-alive stopped")

    def _keep_alive_loop(self, extra_models: List[str]):
        """Re-assert keep_alive before Ollama's timer can expire.

        keep_alive is only refreshed by real traffic, so an idle session used to
        go cold in the background and the next message paid a full reload.
        """
        minutes = self.keep_alive_minutes
        if minutes < 0:
            return  # keep_alive=-1 never expires; no heartbeat needed
        interval = max(60.0, 60.0 * (minutes / 2.0))

        while self._running:
            if self._wake.wait(timeout=interval):
                break  # stop_keep_alive() was called
            if not self._running:
                break
            with self._lock:
                targets = [m for m in ([self._active_model] + extra_models) if m]
            seen = set()
            for model_id in targets:
                if not self._running:
                    break
                if model_id in seen:
                    continue
                seen.add(model_id)
                try:
                    self.preload_model(model_id)
                    logger.debug(f"Keep-alive ping: {model_id}")
                except Exception as e:
                    logger.warning(f"Keep-alive failed for {model_id}: {e}")


class ContextOptimizer:
    """
    Holds the context window size used for inference.

    Deliberately *stable*: Ollama keys a loaded model by its runner options, so
    growing num_ctx as a conversation gets longer evicts the model and reloads
    it mid-conversation — a multi-second stall exactly when the user is engaged.
    One size is picked up front and reused.
    """

    def __init__(self, default_ctx: int = 8192):
        self.default_ctx = default_ctx
        self._model_contexts: Dict[str, int] = {}

    def get_optimal_context(self, conversation_length: int, model_id: str) -> int:
        """The context size to request. Same value every time, on purpose."""
        return self.get_model_context(model_id)

    def set_model_context(self, model_id: str, context_size: int):
        """Set preferred context for a model."""
        self._model_contexts[model_id] = context_size
        logger.info(f"Set context for {model_id}: {context_size}")

    def get_model_context(self, model_id: str) -> int:
        """Get preferred context for a model."""
        return self._model_contexts.get(model_id, self.default_ctx)


class LLMOptimizer:
    """
    Main LLM performance optimizer.
    
    Combines all optimization techniques:
    - Response caching
    - Model preloading
    - Context optimization
    - Configuration tuning
    """
    
    def __init__(self, event_bus: EventBus, provider=None, provider_registry=None):
        self.event_bus = event_bus
        self.provider = provider
        self.provider_registry = provider_registry

        # Settings first — the components below are sized from them.
        self.settings = self._load_settings()

        # Components
        self.cache = ResponseCache(
            max_size=int(self.settings['cache_max_size']),
            ttl_seconds=int(self.settings['cache_ttl_seconds']),
        )
        self.preloader = ModelPreloader(
            provider, keep_alive_minutes=int(self.settings['keep_alive_minutes'])
        ) if provider else None
        self.context_optimizer = ContextOptimizer(
            default_ctx=int(self.settings['default_context_size'])
        )

        # Warm-up bookkeeping
        self._warm_lock = threading.Lock()
        self._warming: set = set()          # models with a warm in flight
        self._warmed_at: Dict[str, float] = {}
        self._active_model_id: Optional[str] = None   # full "provider:model"
        self._switch_generation = 0
        self._active_provider_name = ""
        self._vram_info: Dict[str, Any] = {}

        # Stats
        self._total_queries = 0
        self._cache_hits = 0
        self._avg_response_time = 0.0

        self._push_runner_defaults()
        self._subscribe()

        logger.info("LLM Optimizer initialized")

    def _push_runner_defaults(self):
        """Teach the provider the context/keep_alive we warm with.

        Warm-up and real requests have to agree on these or Ollama reloads the
        model on the first real message and the warm-up bought nothing.
        """
        if self.provider is None:
            return
        try:
            self.provider.default_num_ctx = int(self.settings['default_context_size'])
            minutes = int(self.settings['keep_alive_minutes'])
            self.provider.default_keep_alive = "-1" if minutes < 0 else f"{minutes}m"
        except Exception as e:
            logger.debug(f"Provider does not take runner defaults: {e}")

    def _subscribe(self):
        """Warm whenever we learn which model the user is about to use."""
        try:
            self.event_bus.subscribe("ai_model_auto_selected", self._on_model_selected)
            self.event_bus.subscribe("ai_chat_model_switched", self._on_model_selected)
            self.event_bus.subscribe("ai_warm_request", self._on_warm_request)
        except Exception as e:
            logger.warning(f"Could not subscribe optimizer to warm events: {e}")

    # ── Warm-up ─────────────────────────────────────────────────────────────

    def _on_model_selected(self, data: dict):
        model_id = (data or {}).get("model_id")
        if not model_id:
            return
        self._active_model_id = model_id
        # Do not spawn llama-server or warm multi-GB GGUF weights on initial startup selection;
        # wait until the user focuses the chat box, starts typing, or switches models manually.
        if (data or {}).get("reason") == "automatic_startup_selection" and not self.settings.get("warm_on_startup", False):
            return
        self.warm(model_id, reason="model_selected")

    def _on_warm_request(self, data: dict):
        model_id = (data or {}).get("model_id") or self._active_model_id
        self.warm(model_id, reason=(data or {}).get("reason", "request"))

    def switch_model(self, model_id: str) -> bool:
        """Make one model switch authoritative and warm it once in background."""
        model_id = (model_id or "").strip()
        if not model_id:
            return False
        with self._warm_lock:
            if model_id == self._active_model_id:
                return False
            prev_model_id = self._active_model_id
            self._active_model_id = model_id
            provider, _ = self._resolve(model_id)
            self._active_provider_name = getattr(
                getattr(provider, "config", None), "provider_name", "")
            self._switch_generation += 1
        # Unload the previous provider's model from VRAM before warming the
        # new one. On a 6 GB card two 4+ GB models cannot coexist.
        if prev_model_id and prev_model_id != model_id:
            threading.Thread(
                target=self._unload_other_providers,
                args=(model_id,),
                daemon=True,
                name="unload-prev-provider",
            ).start()
        self.warm(model_id, reason="model_switched", force=True)
        return True

    def _unload_other_providers(self, active_model_id: str) -> None:
        """Evict models from every provider that is NOT serving active_model_id.

        Called in a daemon thread after a model switch so the UI is never
        blocked. On a machine with limited VRAM (e.g. 6 GB RTX 3050) two
        4+ GB models cannot coexist — one must be evicted before the new
        one loads or both run at reduced speed due to VRAM paging.
        """
        if not active_model_id:
            return
        active_provider_name = active_model_id.split(":", 1)[0] if ":" in active_model_id else ""

        if self.provider_registry is None:
            # No registry — try the single provider if it differs
            if (self.provider is not None
                    and getattr(getattr(self.provider, "config", None),
                                "provider_name", "") != active_provider_name):
                self._evict_provider(self.provider)
            return

        for pname in ("ollama", "llama_cpp", "qwen"):
            if pname == active_provider_name:
                continue
            try:
                p = self.provider_registry.get_provider(pname)
                if p is None:
                    continue
                self._evict_provider(p)
            except Exception as exc:
                logger.debug(f"Could not evict provider '{pname}': {exc}")

    def _evict_provider(self, provider) -> None:
        """Tell a provider to free its models from VRAM."""
        pname = getattr(getattr(provider, "config", None), "provider_name", "?")
        try:
            # Ollama: send keep_alive=0 for every loaded model
            unload = getattr(provider, "unload_models", None)
            if callable(unload):
                n = unload()
                if n:
                    logger.info(f"Unloaded {n} model(s) from {pname}")
                return
            # llama.cpp: stop the owned server process entirely
            stop = getattr(provider, "stop", None)
            if callable(stop):
                stop()
                logger.info(f"Stopped {pname} server to free VRAM")
        except Exception as exc:
            logger.warning(f"Failed to evict {pname}: {exc}")

    def get_model_estimate(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """Return conservative model size and VRAM information for the UI."""
        provider, bare = self._resolve(model_id or self._active_model_id)
        info = {"model_id": model_id or self._active_model_id or "",
                "provider": self._active_provider_name, "model_bytes": 0,
                "model_size_gb": 0.0, "vram_used_mb": None,
                "vram_total_mb": None, "backend": "unknown"}
        if provider is not None:
            info["provider"] = getattr(getattr(provider, "config", None),
                                        "provider_name", info["provider"])
            info["backend"] = ("CUDA/Ollama" if info["provider"] == "ollama"
                               else "llama.cpp" if info["provider"] == "llama_cpp"
                               else info["provider"])
            loader = getattr(provider, "loader", None)
            if loader is not None and bare:
                try:
                    path = loader.model_path(bare)
                    info["model_bytes"] = path.stat().st_size
                except (OSError, ValueError, RuntimeError):
                    pass
            try:
                models = provider.get_models() or {}
                model_info = models.get(bare, {})
                info["model_bytes"] = info["model_bytes"] or int(model_info.get("size", 0))
            except (AttributeError, TypeError, ValueError):
                pass
        info["model_size_gb"] = round(info["model_bytes"] / (1024 ** 3), 2)
        now_mono = time.monotonic()
        cached_smi = getattr(self, "_smi_cache", None)
        if cached_smi and (now_mono - cached_smi[0]) < 10.0:
            info.update(cached_smi[1])
        else:
            smi_data = {}
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used,memory.total",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=1, check=False,
                    **hidden_subprocess_kwargs())
                used, total = result.stdout.strip().splitlines()[0].split(",")
                smi_data["vram_used_mb"] = int(used.strip())
                smi_data["vram_total_mb"] = int(total.strip())
                smi_data["compute_mode"] = "GPU"
            except (OSError, subprocess.SubprocessError, IndexError, ValueError):
                smi_data["compute_mode"] = "CPU/unknown"
            self._smi_cache = (now_mono, smi_data)
            info.update(smi_data)
        return info

    def diagnostics(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """Return the latest local inference diagnostics."""
        info = self.get_model_estimate(model_id)
        info.update(self._vram_info)
        info["active_model"] = self._active_model_id
        info["warming"] = bool(self._warming)
        return info

    def _provider_named(self, name: str):
        """The loaded provider registered under `name`, or None."""
        if not name:
            return None
        if self.provider_registry is not None:
            try:
                found = self.provider_registry.get_provider(name)
            except Exception:
                found = None
            if found is not None:
                return found
        if self.provider is not None:
            try:
                own = self.provider.config.provider_name
            except Exception:
                own = "ollama"
            if name.lower() == (own or "").lower():
                return self.provider
        return None

    def _resolve(self, model_id: Optional[str]):
        """(provider, bare model name) for a model id.

        Ids from the UI look like "ollama:qwen2.5-coder:7b", but a plain Ollama
        tag — "qwen2.5-coder:7b" — has a colon in it too. Splitting blindly on
        the first colon turned that tag into the model "7b" and warmed nothing,
        so the prefix is only stripped when the leading segment really names a
        provider.
        """
        if not model_id:
            return self.provider, None
        model_id = model_id.strip()
        key, sep, rest = model_id.partition(":")
        if not sep:                       # no colon at all — already bare
            return self.provider, key

        provider = self._provider_named(key)
        if provider is not None:
            return provider, rest
        if key.lower() in _PROVIDER_KEYS:
            # A provider prefix we can't serve (that provider isn't loaded).
            # Better to do nothing than to warm the wrong provider's model.
            return None, rest
        # Not a prefix: the whole string is the model tag.
        return self.provider, model_id

    def warm(self, model_id: Optional[str] = None, reason: str = "",
             force: bool = False) -> None:
        """Load a model in the background so the next message replies at once.

        Cheap to call often: warms are de-duplicated, skipped when the model is
        already resident, and always run off the caller's thread (event dispatch
        happens on the GUI thread, which must never block on a model load).
        """
        if not self.settings.get('preload_enabled', True):
            return
        model_id = model_id or self._active_model_id
        provider, bare = self._resolve(model_id)
        if provider is None or not bare:
            return
        if not hasattr(provider, "warm_model") and not hasattr(provider, "generate_response"):
            return

        now = time.time()
        with self._warm_lock:
            if bare in self._warming:
                return
            if not force and (now - self._warmed_at.get(bare, 0.0)) < self._warm_cooldown:
                return
            self._warming.add(bare)
            generation = self._switch_generation

        def work():
            ok = False
            load_started = time.perf_counter()
            try:
                with self._warm_lock:
                    if generation != self._switch_generation and reason == "model_switched":
                        return
                estimate = self.get_model_estimate(model_id)
                self.event_bus.publish("ai_model_warming",
                                       {"model_id": model_id, "reason": reason,
                                        "estimate": estimate})
                if self.settings.get('auto_start_server', True):
                    ensure = getattr(provider, "ensure_server", None)
                    if callable(ensure):
                        ensure()
                if self.preloader is not None and provider is self.provider:
                    ok = self.preloader.preload_model(bare, force=force)
                    self.preloader.set_active_model(bare)
                else:
                    warm = getattr(provider, "warm_model", None)
                    ok = bool(warm(bare, force=force)) if callable(warm) else False
            except Exception as e:
                logger.warning(f"Warm-up failed for {model_id}: {e}")
            finally:
                with self._warm_lock:
                    self._warming.discard(bare)
                    if ok:
                        self._warmed_at[bare] = time.time()
                self.event_bus.publish("ai_model_warm",
                                       {"model_id": model_id, "ready": ok,
                                        "reason": reason,
                                        "load_seconds": round(time.perf_counter() - load_started, 3),
                                        "estimate": self.get_model_estimate(model_id)})

        threading.Thread(target=work, daemon=True,
                         name=f"warm-{bare}").start()

    @property
    def _warm_cooldown(self) -> float:
        """Don't re-warm the same model more often than this (seconds)."""
        minutes = int(self.settings.get('keep_alive_minutes', 30))
        if minutes < 0:
            return 3600.0
        return max(30.0, 60.0 * minutes / 3.0)

    def _load_settings(self) -> Dict[str, Any]:
        """Load optimizer settings."""
        settings_file = Path("config/llm_optimizer.json")

        default_settings = {
            "cache_enabled": True,
            "cache_ttl_seconds": 3600,
            "cache_max_size": 100,
            "preload_enabled": True,
            # Ollama only refreshes keep_alive on real traffic; the heartbeat
            # below re-asserts it. -1 means "never unload".
            "keep_alive_minutes": 30,
            # One stable value: changing it mid-session reloads the model.
            "default_context_size": 8192,
            "optimize_context": True,
            "preferred_models": [],   # extra models to keep warm alongside the active one
            "max_preload_models": 1,  # more than one thrashes VRAM on most machines
            "auto_start_server": False,  # start server on-demand (input focus / first message)
            "warm_on_startup": False,    # do not thrash disk/VRAM during IDE launch
            "warm_on_typing": True,      # re-warm as soon as the user starts typing
            "unload_on_exit": False,     # keeping it resident is why the next launch is fast
            "performance_mode": "balanced"  # "fast", "balanced", "quality"
        }

        try:
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    loaded = json.load(f)
                    default_settings.update(loaded)
        except Exception as e:
            logger.warning(f"Failed to load optimizer settings: {e}")

        # The user-facing AI setting is the source of truth for the Ollama
        # context size. Keep the optimizer file as a fallback for older setups.
        try:
            app_settings_file = Path("config/settings.json")
            if app_settings_file.exists():
                with open(app_settings_file, 'r') as f:
                    app_settings = json.load(f)
                context_size = app_settings.get("ai", {}).get("context_window_size")
                if context_size is not None:
                    default_settings["default_context_size"] = max(512, int(context_size))
        except (OSError, TypeError, ValueError) as e:
            logger.warning(f"Failed to load AI context window setting: {e}")

        return default_settings
    
    def save_settings(self):
        """Save current settings."""
        settings_file = Path("config/llm_optimizer.json")
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            logger.info("Optimizer settings saved")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
    
    def optimize_request(self, prompt: str, model_id: str, 
                        conversation_length: int = 0, **kwargs) -> Dict[str, Any]:
        """
        Optimize request parameters before sending to LLM.
        
        Returns optimized parameters to pass to provider.
        """
        optimized = kwargs.copy()
        
        # 1. Context optimization
        if self.settings['optimize_context'] and 'num_ctx' not in optimized:
            optimal_ctx = self.context_optimizer.get_optimal_context(
                conversation_length, model_id
            )
            optimized['num_ctx'] = optimal_ctx
            logger.debug(f"Optimized context: {optimal_ctx}")
        
        # 2. Keep-alive
        if self.settings['preload_enabled']:
            minutes = int(self.settings['keep_alive_minutes'])
            optimized['keep_alive'] = "-1" if minutes < 0 else f"{minutes}m"
        
        # 3. Performance mode adjustments
        mode = self.settings['performance_mode']
        if mode == "fast":
            optimized.setdefault('temperature', 0.7)
            optimized.setdefault('top_p', 0.9)
            optimized.setdefault('top_k', 40)
        elif mode == "quality":
            optimized.setdefault('temperature', 0.8)
            optimized.setdefault('top_p', 0.95)
            optimized.setdefault('top_k', 100)
        else:  # balanced
            optimized.setdefault('temperature', 0.7)
            optimized.setdefault('top_p', 0.9)
            optimized.setdefault('top_k', 40)
        
        return optimized
    
    def get_cached_response(self, prompt: str, model_id: str, context: str = "") -> Optional[str]:
        """Check if response is cached."""
        if not self.settings['cache_enabled']:
            return None
        
        return self.cache.get(prompt, model_id, context)
    
    def cache_response(self, prompt: str, model_id: str, response: str, context: str = ""):
        """Cache a response."""
        if self.settings['cache_enabled']:
            self.cache.set(prompt, model_id, response, context)
    
    def preload_preferred_models(self):
        """Bring the local LLM stack up to speed, in the background.

        Order matters: the daemon has to exist before anything can be loaded,
        and the *active* model is warmed first because it is the one the user
        will actually message. `preferred_models` is a fallback for the case
        where no model has been selected yet.
        """
        if not self.settings['preload_enabled'] or not self.preloader:
            return

        # 0. Evict models from providers that are NOT the active one so they
        #    don't share VRAM. On a 6 GB card two 4+ GB models cannot coexist.
        if self._active_model_id:
            threading.Thread(
                target=self._unload_other_providers,
                args=(self._active_model_id,),
                daemon=True,
                name="startup-evict",
            ).start()

        # 1. The server itself — otherwise every warm below just fails.
        if self.settings.get('auto_start_server', True) and self.provider is not None:
            ensure = getattr(self.provider, "ensure_server", None)
            if callable(ensure):
                try:
                    ensure()
                except Exception as e:
                    logger.warning(f"Could not ensure the Ollama server: {e}")

        # 2. The model. Loading several at once thrashes VRAM and each load
        #    can evict the previous one, so only `max_preload_models` are warmed.
        if self.settings.get('warm_on_startup', True):
            cap = 1  # one resident model avoids VRAM thrashing on this GPU
            targets: List[str] = []
            if self._active_model_id:
                _, bare = self._resolve(self._active_model_id)
                if bare:
                    targets.append(bare)
            for m in self.settings.get('preferred_models') or []:
                # Config entries are plain local tags ("qwen2.5-coder:7b"), so
                # they are used as-is rather than parsed for a provider prefix.
                m = (m or "").strip()
                if m and m not in targets:
                    targets.append(m)
            targets = targets[:cap]

            if targets:
                logger.info(f"Warming {len(targets)} model(s): {targets}")
                for model_id in targets:
                    self.preloader.preload_model(model_id)
                self.preloader.set_active_model(targets[0])
            else:
                logger.info("No model to warm yet — will warm on selection")

        # 3. Keep it warm for as long as the IDE is open. Only the active model
        #    gets the heartbeat — pinging several would keep evicting each other.
        self.preloader.start_keep_alive()

    def stop(self):
        """Stop background warm-up work (called on shutdown)."""
        if self.preloader:
            try:
                self.preloader.stop_keep_alive()
            except Exception:
                pass

    @property
    def unload_on_exit(self) -> bool:
        """Whether local models should be evicted when the IDE closes."""
        return bool(self.settings.get('unload_on_exit', False))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get optimizer statistics."""
        cache_stats = self.cache.get_stats()
        
        return {
            'cache': cache_stats,
            'settings': self.settings,
            'total_queries': self._total_queries,
            'average_response_time_ms': round(self._avg_response_time * 1000, 2),
        }
    
    def set_performance_mode(self, mode: str):
        """
        Set performance mode.
        
        Args:
            mode: "fast", "balanced", or "quality"
        """
        if mode not in ["fast", "balanced", "quality"]:
            raise ValueError(f"Invalid mode: {mode}")
        
        self.settings['performance_mode'] = mode
        self.save_settings()
        logger.info(f"Performance mode set to: {mode}")
        
        # Publish event
        self.event_bus.publish("llm_performance_mode_changed", {"mode": mode})
    
    def enable_cache(self, enabled: bool = True):
        """Enable or disable response caching."""
        self.settings['cache_enabled'] = enabled
        if not enabled:
            self.cache.clear()
        self.save_settings()
        logger.info(f"Cache {'enabled' if enabled else 'disabled'}")
    
    def enable_preload(self, enabled: bool = True):
        """Enable or disable model preloading."""
        self.settings['preload_enabled'] = enabled
        if not enabled and self.preloader:
            self.preloader.stop_keep_alive()
        self.save_settings()
        logger.info(f"Preload {'enabled' if enabled else 'disabled'}")
    
    def add_preferred_model(self, model_id: str):
        """Add a model to preload on startup."""
        if model_id not in self.settings['preferred_models']:
            self.settings['preferred_models'].append(model_id)
            self.save_settings()

            # Warm it now — off-thread, so a UI caller never blocks on a load.
            if self.settings['preload_enabled']:
                self.warm(model_id, reason="preferred_added")

            logger.info(f"Added preferred model: {model_id}")
    
    def remove_preferred_model(self, model_id: str):
        """Remove a model from preload list."""
        if model_id in self.settings['preferred_models']:
            self.settings['preferred_models'].remove(model_id)
            self.save_settings()
            logger.info(f"Removed preferred model: {model_id}")
    
    def clear_cache(self):
        """Clear response cache."""
        self.cache.clear()
        logger.info("Response cache cleared")


def initialize_llm_optimizer(event_bus: EventBus, provider=None,
                             provider_registry=None) -> LLMOptimizer:
    """
    Initialize LLM optimizer.

    Args:
        event_bus: Event bus for communication
        provider: local LLM provider to warm (Ollama)
        provider_registry: registry used to resolve "provider:model" ids

    Returns:
        LLMOptimizer instance
    """
    optimizer = LLMOptimizer(event_bus, provider, provider_registry)

    # Start the server and warm the model in the background — this can take
    # tens of seconds on a cold machine and must never block startup.
    if optimizer.settings['preload_enabled']:
        threading.Thread(
            target=optimizer.preload_preferred_models,
            daemon=True,
            name="llm-warmup",
        ).start()

    logger.info("LLM Optimizer initialized and ready")
    return optimizer

