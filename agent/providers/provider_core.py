"""
Consolidated Module: agent.providers.provider_core

Combines: ai.providers.base_provider, ai.providers.secret_store, ai.providers.api_token_manager, ai.providers.provider_discovery, ai.providers.provider_health, ai.providers.provider_factory, ai.providers.provider_registry, ai.providers.provider_router, ai.providers.provider_manager
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['ai.providers.base_provider', 'ai.providers.secret_store', 'ai.providers.api_token_manager', 'ai.providers.provider_discovery', 'ai.providers.provider_health', 'ai.providers.provider_factory', 'ai.providers.provider_registry', 'ai.providers.provider_router', 'ai.providers.provider_manager']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ai.providers.base_provider (ai/providers/base_provider.py)
# ============================================================================
"""
Base Provider Interface.

Defines the contract all AI providers must implement.
"""

import asyncio
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from core.logger import setup_logger
from enum import Enum

class AuthenticationType(Enum):
    """Supported authentication methods."""
    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    OAUTH = "oauth"
    CUSTOM = "custom"

class ProviderStatus(Enum):
    """Provider connection status."""
    UNKNOWN = "unknown"
    UNINITIALIZED = "uninitialized"
    CONNECTING = "connecting"
    CHECKING = "checking"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    AUTHENTICATION_FAILED = "authentication_failed"
    API_MISSING = "api_missing"
    OFFLINE = "offline"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"
    ERROR = "error"

@dataclass
class ProviderConfig:
    """Configuration for a provider instance."""
    provider_name: str
    endpoint: str
    auth_type: AuthenticationType
    api_key: Optional[str] = None
    enabled: bool = True
    priority: int = 0
    default_model: str = ""
    connection_status: ProviderStatus = ProviderStatus.UNINITIALIZED
    timeout_seconds: int = 30
    retry_count: int = 3
    supports_streaming: bool = False
    supports_tool_calling: bool = False
    supports_vision: bool = False
    supports_function_calling: bool = False
    options: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for JSON serialization."""
        return {
            "provider_name": self.provider_name,
            "endpoint": self.endpoint,
            "auth_type": self.auth_type.value,
            "api_key": self.api_key,
            "enabled": self.enabled,
            "priority": self.priority,
            "default_model": self.default_model,
            "connection_status": self.connection_status.value,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "supports_streaming": self.supports_streaming,
            "supports_tool_calling": self.supports_tool_calling,
            "supports_vision": self.supports_vision,
            "supports_function_calling": self.supports_function_calling,
            "options": self.options,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProviderConfig":
        """Create config from dictionary."""
        return cls(
            provider_name=data.get("provider_name", ""),
            endpoint=data.get("endpoint", ""),
            auth_type=AuthenticationType(data.get("auth_type", "none")),
            api_key=data.get("api_key"),
            enabled=data.get("enabled", True),
            priority=data.get("priority", 0),
            default_model=data.get("default_model", ""),
            connection_status=ProviderStatus(data.get("connection_status", "uninitialized")),
            timeout_seconds=data.get("timeout_seconds", 30),
            retry_count=data.get("retry_count", 3),
            supports_streaming=data.get("supports_streaming", False),
            supports_tool_calling=data.get("supports_tool_calling", False),
            supports_vision=data.get("supports_vision", False),
            supports_function_calling=data.get("supports_function_calling", False),
            options=dict(data.get("options", {})),
        )


class ProviderEvent:
    """Event fired by provider state changes."""
    
    def __init__(
        self,
        provider_name: str,
        event_type: str,
        status: Optional[ProviderStatus] = None,
        error: Optional[str] = None,
        models_refreshed: Optional[List[str]] = None,
    ):
        self.provider_name = provider_name
        self.event_type = event_type
        self.status = status
        self.error = error
        self.models_refreshed = models_refreshed or []


class BaseProvider(ABC):
    """
    Abstract base class for all AI providers.
    
    Ensures uniform interface across all providers and handles:
    - API key management
    - Retry logic
    - Connection status tracking
    - Background thread management
    """
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.logger = setup_logger(f"provider.{config.provider_name}")
        self._models: Dict[str, Dict[str, Any]] = {}
        self._event_callbacks: List[Callable[[ProviderEvent], None]] = []
        self._lock = threading.Lock()

    # ─────────────────────────────────────────────────────────────────────────────
    # Core Methods
    # ─────────────────────────────────────────────────────────────────────────────

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the provider.
        
        Returns True if connection successful, False otherwise.
        Should be implemented using background thread for network operations.
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the provider."""
        pass

    @abstractmethod
    def generate_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate a response from the provider.
        
        Args:
            prompt: The user prompt
            model_id: Model to use (uses default if not specified)
            system_prompt: Optional system prompt
            **kwargs: Additional provider-specific parameters
            
        Returns:
            The generated response string
        """
        pass

    @abstractmethod
    def stream_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> str:
        """
        Stream a response from the provider.
        
        Args:
            prompt: The user prompt
            model_id: Model to use (uses default if not specified)
            system_prompt: Optional system prompt
            on_chunk: Callback for each chunk
            **kwargs: Additional provider-specific parameters
            
        Returns:
            The complete generated response string
        """
        pass

    # ─────────────────────────────────────────────────────────────────────────────
    # Model Management
    # ─────────────────────────────────────────────────────────────────────────────

    @abstractmethod
    def refresh_models(self) -> List[Dict[str, Any]]:
        """
        Fetch available models from the provider.
        
        Returns:
            List of model descriptions with id, name, context_window, etc.
        """
        pass

    def get_models(self) -> Dict[str, Dict[str, Any]]:
        """Get cached models."""
        with self._lock:
            return dict(self._models)

    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific model by ID."""
        with self._lock:
            return self._models.get(model_id)

    def _set_models(self, models: List[Dict[str, Any]]) -> None:
        """Set models from provider refresh (internal use)."""
        with self._lock:
            self._models = {m.get("id", m.get("name", "")): m for m in models}

    # ─────────────────────────────────────────────────────────────────────────────
    # Health & Status
    # ─────────────────────────────────────────────────────────────────────────────

    def get_status(self) -> ProviderStatus:
        """Get current connection status."""
        return self.config.connection_status

    def is_connected(self) -> bool:
        """Check if provider is connected."""
        return self.config.connection_status == ProviderStatus.CONNECTED

    def is_available(self) -> bool:
        """Check if provider is enabled and connected."""
        return self.config.enabled and self.is_connected()

    def test_connection(self) -> bool:
        """
        Test provider connectivity.
        
        Should be implemented efficiently without full connection setup.
        """
        try:
            if self.is_connected():
                return True
            if self.connect():
                self.disconnect()
                return True
            return False
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────────────────
    # Capabilities
    # ─────────────────────────────────────────────────────────────────────────────

    def supports_streaming(self) -> bool:
        """Check if provider supports streaming responses."""
        return self.config.supports_streaming

    def supports_tool_calling(self) -> bool:
        """Check if provider supports tool/function calling."""
        return self.config.supports_tool_calling

    def supports_vision(self) -> bool:
        """Check if provider supports image input."""
        return self.config.supports_vision

    def supports_function_calling(self) -> bool:
        """Check if provider supports function calling."""
        return self.config.supports_function_calling

    # ─────────────────────────────────────────────────────────────────────────────
    # Event System
    # ─────────────────────────────────────────────────────────────────────────────

    def on_event(self, callback: Callable[[ProviderEvent], None]) -> None:
        """Register an event callback."""
        self._event_callbacks.append(callback)

    def _fire_event(self, event: ProviderEvent) -> None:
        """Fire an event to all registered callbacks."""
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"Event callback failed: {e}")

    def _update_status(self, status: ProviderStatus, error: Optional[str] = None) -> None:
        """Update provider status and fire event."""
        self.config.connection_status = status
        self._fire_event(ProviderEvent(
            provider_name=self.config.provider_name,
            event_type="status_changed",
            status=status,
            error=error,
        ))

    # ─────────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────────

    def _get_model_id(self, model_id: Optional[str] = None) -> str:
        """Get model ID, using default if not specified."""
        if model_id:
            return model_id
        if self.config.default_model:
            return self.config.default_model
        models = self.get_models()
        if models:
            return list(models.keys())[0]
        raise ValueError(f"No model specified and no default for {self.config.provider_name}")

    def _run_async(self, coro) -> Any:
        """Run async coroutine in a thread-safe manner."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.config.provider_name}, status={self.config.connection_status.value})"


# ============================================================================
# SECTION: ai.providers.secret_store (ai/providers/secret_store.py)
# ============================================================================
"""
Secret Store — v2.0

Secure storage for provider API keys. Keeps secrets OUT of the plaintext
``config/providers/*.json`` files.

Backend selection (best available wins, all degrade gracefully):

  1. ``keyring``      — the OS credential vault (macOS Keychain, Windows
                        Credential Manager, Freedesktop Secret Service).
                        Preferred: secrets never touch the project directory.
  2. ``cryptography`` — a Fernet-encrypted blob at ``config/providers/.secrets.enc``
                        with the key file ``config/providers/.secretkey`` (0600).
                        Used when keyring is not importable (e.g. headless CI,
                        this sandbox). Secrets are encrypted at rest.
  3. plaintext        — last-resort fallback when neither library is present.
                        In this mode the store reports ``secure == False`` and
                        callers keep writing the key into the provider JSON as
                        before, so nothing breaks.

The public API is identical regardless of backend, so callers never branch on
which one is active — they only consult ``.secure`` to decide whether the JSON
copy of the key should be stripped.
"""

import json
import os
import stat
import threading
from pathlib import Path
from typing import Optional

from core.logger import setup_logger

logger = setup_logger(__name__)

_SERVICE_NAME = "owncode"

# ── Detect available backends once, at import ────────────────────────────────
try:  # pragma: no cover - depends on host
    import keyring as _keyring  # type: ignore
    # A keyring with no usable backend raises at get/set time; probe lazily.
    _HAS_KEYRING = True
except Exception:  # noqa: BLE001
    _keyring = None
    _HAS_KEYRING = False

try:
    from cryptography.fernet import Fernet as _Fernet  # type: ignore
    _HAS_FERNET = True
except Exception:  # noqa: BLE001
    _Fernet = None
    _HAS_FERNET = False


class SecretStore:
    """Backend-agnostic secret storage for provider API keys."""

    BACKEND_KEYRING = "keyring"
    BACKEND_ENCRYPTED = "encrypted-file"
    BACKEND_PLAINTEXT = "plaintext"

    def __init__(self, storage_dir: str = "config/providers"):
        self._dir = Path(storage_dir)
        self._lock = threading.RLock()
        self._enc_file = self._dir / ".secrets.enc"
        self._key_file = self._dir / ".secretkey"
        self._cipher = None
        self._keyring_ok = False

        # Pick the strongest backend that actually works on this host.
        if _HAS_KEYRING and self._probe_keyring():
            self.backend = self.BACKEND_KEYRING
            self._keyring_ok = True
        elif _HAS_FERNET:
            self.backend = self.BACKEND_ENCRYPTED
            self._init_cipher()
        else:
            self.backend = self.BACKEND_PLAINTEXT

        logger.info("SecretStore backend: %s", self.backend)

    # ── properties ───────────────────────────────────────────────────────────
    @property
    def secure(self) -> bool:
        """True when secrets are stored outside the plaintext provider JSON."""
        return self.backend != self.BACKEND_PLAINTEXT

    # ── backend probing / init ─────────────────────────────────────────────────
    def _probe_keyring(self) -> bool:
        """A keyring import can succeed while having no usable backend."""
        try:
            from keyring.errors import NoKeyringError  # type: ignore
        except Exception:  # noqa: BLE001
            NoKeyringError = Exception  # type: ignore
        try:
            backend = _keyring.get_keyring()
            name = backend.__class__.__name__.lower()
            # The "fail"/"null" backends are placeholders that raise on use.
            if "fail" in name or "null" in name:
                return False
            return True
        except NoKeyringError:
            return False
        except Exception as e:  # noqa: BLE001
            logger.debug("keyring probe failed: %s", e)
            return False

    def _init_cipher(self) -> None:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            if self._key_file.exists():
                key = self._key_file.read_bytes()
            else:
                key = _Fernet.generate_key()
                self._key_file.write_bytes(key)
                self._chmod_600(self._key_file)
            self._cipher = _Fernet(key)
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to init encrypted secret backend: %s", e)
            self.backend = self.BACKEND_PLAINTEXT

    @staticmethod
    def _chmod_600(path: Path) -> None:
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:  # noqa: BLE001 - best effort (e.g. Windows)
            pass

    # ── encrypted-file helpers ─────────────────────────────────────────────────
    def _read_enc(self) -> dict:
        if not self._enc_file.exists() or self._cipher is None:
            return {}
        try:
            raw = self._cipher.decrypt(self._enc_file.read_bytes())
            return json.loads(raw.decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to read encrypted secrets: %s", e)
            return {}

    def _write_enc(self, data: dict) -> None:
        if self._cipher is None:
            return
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            blob = self._cipher.encrypt(json.dumps(data).encode("utf-8"))
            self._enc_file.write_bytes(blob)
            self._chmod_600(self._enc_file)
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to write encrypted secrets: %s", e)

    # ── public API ─────────────────────────────────────────────────────────────
    def get_secret(self, provider_name: str) -> Optional[str]:
        with self._lock:
            if self.backend == self.BACKEND_KEYRING:
                try:
                    return _keyring.get_password(_SERVICE_NAME, provider_name)
                except Exception as e:  # noqa: BLE001
                    logger.error("keyring get failed for %s: %s", provider_name, e)
                    return None
            if self.backend == self.BACKEND_ENCRYPTED:
                return self._read_enc().get(provider_name)
            return None  # plaintext backend keeps the key in the JSON, not here

    def set_secret(self, provider_name: str, api_key: str) -> bool:
        if not api_key:
            return self.delete_secret(provider_name)
        with self._lock:
            if self.backend == self.BACKEND_KEYRING:
                try:
                    _keyring.set_password(_SERVICE_NAME, provider_name, api_key)
                    return True
                except Exception as e:  # noqa: BLE001
                    logger.error("keyring set failed for %s: %s", provider_name, e)
                    return False
            if self.backend == self.BACKEND_ENCRYPTED:
                data = self._read_enc()
                data[provider_name] = api_key
                self._write_enc(data)
                return True
            return False  # plaintext: caller persists into JSON instead

    def delete_secret(self, provider_name: str) -> bool:
        with self._lock:
            if self.backend == self.BACKEND_KEYRING:
                try:
                    _keyring.delete_password(_SERVICE_NAME, provider_name)
                except Exception:  # noqa: BLE001 - absent is fine
                    pass
                return True
            if self.backend == self.BACKEND_ENCRYPTED:
                data = self._read_enc()
                if provider_name in data:
                    del data[provider_name]
                    self._write_enc(data)
                return True
            return False

    def has_secret(self, provider_name: str) -> bool:
        return bool(self.get_secret(provider_name))


_store: Optional[SecretStore] = None
_store_lock = threading.Lock()


def get_secret_store(storage_dir: str = "config/providers") -> SecretStore:
    """Return the process-wide SecretStore singleton."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = SecretStore(storage_dir)
    return _store


# ============================================================================
# SECTION: ai.providers.api_token_manager (ai/providers/api_token_manager.py)
# ============================================================================
"""
API Token Manager.

Secure storage and management of API keys for AI providers.
"""

import json
import os
import secrets
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from cryptography.fernet import Fernet
from core.logger import setup_logger
from core.exceptions import ConfigurationError


logger = setup_logger(__name__)


@dataclass
class StoredToken:
    """Stored API token with metadata."""
    provider_name: str
    token_hash: str  # Hashed token for verification
    display_name: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_used: str = ""
    models: List[str] = field(default_factory=list)
    endpoint: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoredToken":
        """Create from dictionary."""
        return cls(
            provider_name=data.get("provider_name", ""),
            token_hash=data.get("token_hash", ""),
            display_name=data.get("display_name", ""),
            created_at=data.get("created_at", ""),
            last_used=data.get("last_used", ""),
            models=data.get("models", []),
            endpoint=data.get("endpoint", ""),
        )


class APITokenManager:
    """
    Manages API tokens for AI providers with secure storage.
    
    Features:
    - Secure token storage using encryption
    - Token hashing for verification
    - Provider connection tracking
    - Model list caching
    """
    
    def __init__(self, storage_dir: str = "config/api_tokens"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or generate encryption key
        self._key_file = self.storage_dir / ".key"
        self._encryption_key = self._load_or_generate_key()
        self._cipher = Fernet(self._encryption_key)
        
        # In-memory token cache
        self._tokens: Dict[str, StoredToken] = {}
        self._loaded = False
        
        logger.info(f"APITokenManager initialized with storage: {self.storage_dir}")
    
    def _load_or_generate_key(self) -> bytes:
        """Load encryption key from file or generate new one."""
        if self._key_file.exists():
            try:
                with open(self._key_file, 'rb') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to load encryption key: {e}")
        
        # Generate new key
        key = Fernet.generate_key()
        with open(self._key_file, 'wb') as f:
            f.write(key)
        logger.info("Generated new encryption key")
        return key
    
    def _encrypt_token(self, token: str) -> str:
        """Encrypt API token for storage."""
        return self._cipher.encrypt(token.encode()).decode()
    
    def _decrypt_token(self, encrypted: str) -> str:
        """Decrypt API token from storage."""
        try:
            return self._cipher.decrypt(encrypted.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt token: {e}")
            return ""
    
    def _hash_token(self, token: str) -> str:
        """Create hash of token for verification."""
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()[:16]
    
    def load_tokens(self) -> Dict[str, StoredToken]:
        """Load all stored tokens."""
        if self._loaded:
            return self._tokens
        
        tokens_file = self.storage_dir / "tokens.json"
        if not tokens_file.exists():
            logger.info("No stored tokens found")
            return {}
        
        try:
            with open(tokens_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for provider_name, token_data in data.items():
                token = StoredToken.from_dict(token_data)
                self._tokens[provider_name] = token
            
            self._loaded = True
            logger.info(f"Loaded {len(self._tokens)} stored tokens")
            
        except Exception as e:
            logger.error(f"Failed to load tokens: {e}")
        
        return self._tokens
    
    def save_tokens(self) -> bool:
        """Save all tokens to storage."""
        try:
            tokens_file = self.storage_dir / "tokens.json"
            data = {}
            
            for provider_name, token in self._tokens.items():
                data[provider_name] = token.to_dict()
            
            with open(tokens_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
            return False
    
    def store_token(self, provider_name: str, api_key: str, display_name: str = "",
                   endpoint: str = "", models: List[str] = None) -> bool:
        """
        Store API token securely.
        
        Args:
            provider_name: Unique provider identifier
            api_key: The API key to store
            display_name: Human-readable name
            endpoint: Provider endpoint URL
            models: List of available models
            
        Returns:
            True if stored successfully
        """
        token_hash = self._hash_token(api_key)
        
        token = StoredToken(
            provider_name=provider_name,
            token_hash=token_hash,
            display_name=display_name or provider_name,
            endpoint=endpoint,
            models=models or [],
        )
        
        self._tokens[provider_name] = token
        self.save_tokens()
        
        logger.info(f"Stored token for provider: {provider_name}")
        return True
    
    def get_token(self, provider_name: str) -> Optional[str]:
        """
        Get decrypted API token for provider.
        
        Args:
            provider_name: Provider identifier
            
        Returns:
            Decrypted API key or None if not found
        """
        token = self._tokens.get(provider_name)
        if not token:
            return None
        
        # Note: In production, you'd want to store the encrypted token
        # and decrypt it here. For now, we only have the hash.
        # This is a limitation - the actual token is not stored.
        # Users will need to re-enter API keys on each app start.
        # For better UX, consider storing encrypted tokens.
        
        logger.warning("Token encryption not fully implemented - API key not stored")
        return None
    
    def verify_token(self, provider_name: str, api_key: str) -> bool:
        """
        Verify an API key matches the stored token.
        
        Args:
            provider_name: Provider identifier
            api_key: API key to verify
            
        Returns:
            True if key matches stored token
        """
        token = self._tokens.get(provider_name)
        if not token:
            return False
        
        return self._hash_token(api_key) == token.token_hash
    
    def remove_token(self, provider_name: str) -> bool:
        """
        Remove stored token for provider.
        
        Args:
            provider_name: Provider identifier
            
        Returns:
            True if removed successfully
        """
        if provider_name in self._tokens:
            del self._tokens[provider_name]
            return self.save_tokens()
        return False
    
    def get_all_providers(self) -> Dict[str, StoredToken]:
        """Get all stored provider tokens."""
        return self._tokens.copy()
    
    def is_provider_connected(self, provider_name: str) -> bool:
        """
        Check if provider has a stored token.
        
        Args:
            provider_name: Provider identifier
            
        Returns:
            True if provider has stored token
        """
        return provider_name in self._tokens
    
    def update_last_used(self, provider_name: str) -> bool:
        """
        Update last used timestamp for provider.
        
        Args:
            provider_name: Provider identifier
            
        Returns:
            True if updated successfully
        """
        if provider_name in self._tokens:
            self._tokens[provider_name].last_used = datetime.utcnow().isoformat()
            return self.save_tokens()
        return False
    
    def get_connected_providers(self) -> List[str]:
        """Get list of provider names with stored tokens."""
        return list(self._tokens.keys())
    
    def clear_all_tokens(self) -> bool:
        """Remove all stored tokens."""
        self._tokens.clear()
        return self.save_tokens()

# ============================================================================
# SECTION: ai.providers.provider_discovery (ai/providers/provider_discovery.py)
# ============================================================================
"""
Provider Discovery.

Automatically detects available local and cloud providers using fast non-blocking
TCP socket probes before making HTTP requests.
"""

import os
import socket
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
from core.logger import setup_logger

from ai.providers.base_provider import AuthenticationType


logger = setup_logger(__name__)


def _is_local_port_open(url_or_host: str, default_port: int = 80, timeout: float = 0.15) -> bool:
    """Fast TCP probe to 127.0.0.1 so closed local ports fail in <150ms instead of 4-5s."""
    try:
        if "://" in url_or_host:
            parsed = urlparse(url_or_host)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or default_port
        else:
            host, port = url_or_host, default_port
        if host.lower() == "localhost":
            host = "127.0.0.1"
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


class ProviderDiscovery:
    """
    Discovers available AI providers on the local system and network.
    """
    
    def __init__(self):
        self.logger = logger
        self._detected_providers: Dict[str, Dict[str, Any]] = {}

    def discover_all(self) -> Dict[str, Dict[str, Any]]:
        """Run all discovery methods quickly without multi-second stalls on closed ports."""
        self._detected_providers = {}
        
        self._discover_ollama()
        self._discover_lm_studio()
        self._discover_llama_cpp()
        self._discover_vllm()
        self._discover_openai_compatible_servers()
        
        self.logger.info(f"Discovered {len(self._detected_providers)} providers")
        return dict(self._detected_providers)
    
    def discover_ollama(self) -> Optional[Dict[str, Any]]:
        return self._discover_ollama()
    
    def discover_lm_studio(self) -> Optional[Dict[str, Any]]:
        return self._discover_lm_studio()
    
    def discover_llama_cpp(self) -> Optional[Dict[str, Any]]:
        return self._discover_llama_cpp()
    
    def discover_vllm(self) -> Optional[Dict[str, Any]]:
        return self._discover_vllm()

    def _discover_ollama(self) -> Optional[Dict[str, Any]]:
        """Discover Ollama running locally."""
        ollama = {
            "name": "ollama",
            "display_name": "Ollama",
            "endpoint": "http://127.0.0.1:11434",
            "auth_type": AuthenticationType.NONE.value,
            "priority": 10,
            "supports_streaming": True,
            "supports_tool_calling": False,
            "supports_vision": False,
            "supports_function_calling": False,
            "detected_at": datetime.utcnow().isoformat(),
            "detection_method": "http_check",
            "detected": False,
        }
        if not _is_local_port_open("127.0.0.1", 11434):
            self._detected_providers["ollama"] = ollama
            return ollama
        
        try:
            import urllib.request
            req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
            req.add_header("User-Agent", "OwnCode/0.4")
            with urllib.request.urlopen(req, timeout=1.5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    models = data.get("models", [])
                    ollama["detected"] = True
                    ollama["models_count"] = len(models)
                    ollama["default_model"] = models[0].get("name", "") if models else ""
                    ollama["version"] = "unknown"
                    self._detected_providers["ollama"] = ollama
                    return ollama
        except Exception as e:
            self.logger.debug(f"Ollama detection failed: {e}")
        
        self._detected_providers["ollama"] = ollama
        return ollama

    def _discover_lm_studio(self) -> Optional[Dict[str, Any]]:
        """Discover LM Studio running locally."""
        lm_studio = {
            "name": "lm_studio",
            "display_name": "LM Studio",
            "endpoint": "http://127.0.0.1:1234",
            "auth_type": AuthenticationType.NONE.value,
            "priority": 8,
            "supports_streaming": True,
            "supports_tool_calling": True,
            "supports_vision": False,
            "supports_function_calling": False,
            "detected_at": datetime.utcnow().isoformat(),
            "detection_method": "http_check",
            "detected": False,
        }
        if not _is_local_port_open("127.0.0.1", 1234):
            self._detected_providers["lm_studio"] = lm_studio
            return lm_studio
        
        try:
            import urllib.request
            req = urllib.request.Request("http://127.0.0.1:1234/v1/models")
            req.add_header("User-Agent", "OwnCode/0.4")
            with urllib.request.urlopen(req, timeout=1.5) as response:
                if response.status == 200:
                    lm_studio["detected"] = True
                    data = json.loads(response.read().decode())
                    lm_studio["models_count"] = len(data.get("data", []))
                    self._detected_providers["lm_studio"] = lm_studio
                    return lm_studio
        except Exception as e:
            self.logger.debug(f"LM Studio detection failed: {e}")
        
        self._detected_providers["lm_studio"] = lm_studio
        return lm_studio

    def _discover_llama_cpp(self) -> Optional[Dict[str, Any]]:
        """Discover llama.cpp server running locally."""
        llama_cpp = {
            "name": "llama_cpp",
            "display_name": "llama.cpp",
            "endpoint": "http://127.0.0.1:8080",
            "auth_type": AuthenticationType.NONE.value,
            "priority": 7,
            "supports_streaming": True,
            "supports_tool_calling": True,
            "supports_vision": False,
            "supports_function_calling": False,
            "detected_at": datetime.utcnow().isoformat(),
            "detection_method": "http_check",
            "detected": False,
        }
        if not _is_local_port_open("127.0.0.1", 8080):
            self._detected_providers["llama_cpp"] = llama_cpp
            return llama_cpp
        
        try:
            import urllib.request
            req = urllib.request.Request("http://127.0.0.1:8080/v1/models")
            req.add_header("User-Agent", "OwnCode/0.4")
            with urllib.request.urlopen(req, timeout=1.5) as response:
                if response.status == 200:
                    llama_cpp["detected"] = True
                    self._detected_providers["llama_cpp"] = llama_cpp
                    return llama_cpp
        except Exception as e:
            self.logger.debug(f"llama.cpp detection failed: {e}")
        
        self._detected_providers["llama_cpp"] = llama_cpp
        return llama_cpp

    def _discover_vllm(self) -> Optional[Dict[str, Any]]:
        """Discover vLLM server running locally."""
        vllm = {
            "name": "vllm",
            "display_name": "vLLM",
            "endpoint": "http://127.0.0.1:8000",
            "auth_type": AuthenticationType.NONE.value,
            "priority": 9,
            "supports_streaming": True,
            "supports_tool_calling": True,
            "supports_vision": False,
            "supports_function_calling": True,
            "detected_at": datetime.utcnow().isoformat(),
            "detection_method": "http_check",
            "detected": False,
        }
        if not _is_local_port_open("127.0.0.1", 8000):
            self._detected_providers["vllm"] = vllm
            return vllm
        
        try:
            import urllib.request
            req = urllib.request.Request("http://127.0.0.1:8000/v1/models")
            req.add_header("User-Agent", "OwnCode/0.4")
            with urllib.request.urlopen(req, timeout=1.5) as response:
                if response.status == 200:
                    vllm["detected"] = True
                    self._detected_providers["vllm"] = vllm
                    return vllm
        except Exception as e:
            self.logger.debug(f"vLLM detection failed: {e}")
        
        self._detected_providers["vllm"] = vllm
        return vllm

    def _discover_openai_compatible_servers(self) -> List[Dict[str, Any]]:
        """Discover OpenAI-compatible servers on the network."""
        results = []
        common_endpoints = [
            ("http://127.0.0.1:3000", 3000, "vLLM"),
            ("http://127.0.0.1:9000", 9000, "Text Generation WebUI"),
        ]
        
        for endpoint, port, name in common_endpoints:
            provider = {
                "name": name.lower().replace(" ", "_"),
                "display_name": name,
                "endpoint": endpoint,
                "auth_type": AuthenticationType.API_KEY.value,
                "priority": 5,
                "supports_streaming": True,
                "supports_tool_calling": True,
                "supports_vision": False,
                "supports_function_calling": False,
                "detected_at": datetime.utcnow().isoformat(),
                "detection_method": "http_check",
                "compatible_with": "openai",
                "detected": False,
            }
            if not _is_local_port_open("127.0.0.1", port):
                self._detected_providers[provider["name"]] = provider
                continue
            try:
                import urllib.request
                req = urllib.request.Request(f"{endpoint}/v1/models")
                req.add_header("User-Agent", "OwnCode/0.4")
                with urllib.request.urlopen(req, timeout=1.5) as response:
                    if response.status == 200:
                        provider["detected"] = True
                        provider["detected_at"] = datetime.utcnow().isoformat()
                        self._detected_providers[provider["name"]] = provider
                        results.append(provider)
            except Exception:
                self._detected_providers[provider["name"]] = provider
        
        return results

    def get_discovered_providers(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._detected_providers)

    def is_provider_detected(self, provider_name: str) -> bool:
        return self._detected_providers.get(provider_name, {}).get("detected", False)

    def get_detection_details(self, provider_name: str) -> Optional[Dict[str, Any]]:
        return self._detected_providers.get(provider_name)

    def clear_cache(self) -> None:
        self._detected_providers.clear()
        self.logger.info("Discovery cache cleared")


# ============================================================================
# SECTION: ai.providers.provider_health (ai/providers/provider_health.py)
# ============================================================================
"""
Provider Health.

Tracks operational status and reliability of providers,
including Health Score calculation (Part 16).
"""

import threading
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from core.logger import setup_logger

from ai.providers.base_provider import ProviderStatus


logger = setup_logger(__name__)


@dataclass
class ProviderHealthMetrics:
    """
    Health metrics for a single provider, including health score (Part 16).
    """
    provider_name: str
    status: ProviderStatus = ProviderStatus.UNKNOWN
    last_tested: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    last_ping: Optional[datetime] = None
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    total_timeouts: int = 0
    average_latency_ms: float = 0.0
    current_availability: float = 1.0  # 1.0 = 100% available
    available_models_count: int = 0
    is_streaming_available: bool = True
    recent_errors: List[str] = field(default_factory=list)
    cached_models: Optional[List[Dict[str, Any]]] = None
    cached_valid_api_key: bool = False
    last_config_change: Optional[datetime] = None
    last_sync: Optional[datetime] = None
    requests_today: int = 0
    failures_today: int = 0
    
    def record_request(self, success: bool, latency_ms: float = 0.0, is_timeout: bool = False) -> None:
        """Record a request result."""
        self.total_requests += 1
        self.requests_today += 1
        self.last_tested = datetime.utcnow()
        
        if success:
            self.successful_requests += 1
            self.last_success = self.last_tested
            self.consecutive_failures = 0
            self.current_availability = min(1.0, self.current_availability + 0.05)
            
            # Update moving average latency
            if self.average_latency_ms == 0.0:
                self.average_latency_ms = latency_ms
            else:
                self.average_latency_ms = (self.average_latency_ms * 0.9) + (latency_ms * 0.1)
        else:
            self.failed_requests += 1
            self.failures_today +=1
            self.last_failure = self.last_tested
            self.consecutive_failures += 1
            
            if is_timeout:
                self.total_timeouts += 1
            
            # Decrease availability on failures
            self.current_availability = max(0.0, self.current_availability - 0.1)
            
            # Mark as offline after 3 consecutive failures
            if self.consecutive_failures >= 3:
                self.current_availability = 0.0

    def get_availability_score(self) -> float:
        """Calculate availability score (0.0 to 1.0)."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    def calculate_health_score(self) -> int:
        """
        Calculate overall health percentage (0-100) (Part 16).
        Considers:
        - Connection status
        - Authentication/API key validity
        - Latency (lower is better)
        - Successful requests ratio
        - Consecutive failures
        - Available models
        """
        score = 100
        
        # Factor 1: Status
        if self.status in [
            ProviderStatus.DISCONNECTED,
            ProviderStatus.OFFLINE,
            ProviderStatus.API_MISSING,
            ProviderStatus.AUTHENTICATION_FAILED,
            ProviderStatus.UNAVAILABLE
        ]:
            score -= 60
        elif self.status in [ProviderStatus.CHECKING, ProviderStatus.CONNECTING]:
            score -= 30
        
        # Factor 2: API key
        if not self.cached_valid_api_key:
            score -= 30
        
        # Factor3: Consecutive failures
        if self.consecutive_failures > 0:
            score -= min(self.consecutive_failures * 10, 40)
        
        # Factor4: Latency (penalize >500ms)
        if self.average_latency_ms > 500:
            score -= min((self.average_latency_ms / 100), 30)
        
        # Factor5: Availability score
        score *= self.get_availability_score()
        
        # Cap between 0-100, integer
        return max(0, min(100, int(score)))
    
    def get_health_info(self) -> Dict[str, Any]:
        """Get health info as dict for display (Part16, Part21)"""
        return {
            "status": self.status.value,
            "health_score": self.calculate_health_score(),
            "latency_ms": round(self.average_latency_ms, 1),
            "last_ping": self.last_ping.isoformat() if self.last_ping else None,
            "available_models": self.available_models_count,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "requests_today": self.requests_today,
            "failures_today": self.failures_today,
            "recent_errors": self.recent_errors[-5:],
        }


class ProviderHealth:
    """
    Monitors health of all providers.
    
    Tracks:
    - Connection status
    - Request success/failure rates
    - Latency metrics
    - Automatic reconnection triggers
    """
    
    def __init__(self, registry: Any):
        self.registry = registry
        self._metrics: Dict[str, ProviderHealthMetrics] = {}
        self._last_reconnect: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        logger.info("ProviderHealth initialized")

    def get_metrics(self, provider_name: str) -> Optional[ProviderHealthMetrics]:
        """Get health metrics for a provider."""
        return self._metrics.get(provider_name)

    def get_all_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Get health status for all providers.
        
        Returns:
            Dict mapping provider names to health info
        """
        result = {}
        for name, metrics in self._metrics.items():
            result[name] = {
                "status": metrics.status.value,
                "last_tested": metrics.last_tested.isoformat() if metrics.last_tested else None,
                "last_success": metrics.last_success.isoformat() if metrics.last_success else None,
                "last_failure": metrics.last_failure.isoformat() if metrics.last_failure else None,
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "consecutive_failures": metrics.consecutive_failures,
                "total_timeouts": metrics.total_timeouts,
                "average_latency_ms": round(metrics.average_latency_ms, 2),
                "current_availability": round(metrics.current_availability, 2),
                "availability_score": round(metrics.get_availability_score(), 2),
            }
        return result

    def record_status(self, provider_name: str, status: ProviderStatus) -> None:
        """Record provider status change."""
        with self._lock:
            if provider_name not in self._metrics:
                self._metrics[provider_name] = ProviderHealthMetrics(provider_name=provider_name)
            
            self._metrics[provider_name].status = status
    
    def record_request(
        self,
        provider_name: str,
        success: bool,
        latency_ms: float = 0.0,
        is_timeout: bool = False
    ) -> None:
        """Record a request result."""
        with self._lock:
            if provider_name not in self._metrics:
                self._metrics[provider_name] = ProviderHealthMetrics(provider_name=provider_name)
            
            self._metrics[provider_name].record_request(success, latency_ms, is_timeout)

    def record_attempt(self, provider_name: str) -> None:
        """Record a reconnection attempt."""
        with self._lock:
            self._last_reconnect[provider_name] = datetime.utcnow()

    def get_last_attempt(self, provider_name: str) -> Optional[datetime]:
        """Get last reconnection attempt time."""
        return self._last_reconnect.get(provider_name)

    def get_unavailable_providers(self) -> List[str]:
        """Get list of unavailable providers."""
        unavailable = []
        for name, metrics in self._metrics.items():
            if metrics.current_availability <= 0.0:
                unavailable.append(name)
        return unavailable

    def get_recommended_provider(self) -> Optional[str]:
        """
        Get the recommended provider based on health metrics.
        
        Returns:
            Provider name with best availability score, or None
        """
        best_provider = None
        best_score = -1.0
        
        for name, metrics in self._metrics.items():
            score = metrics.get_availability_score()
            if score > best_score:
                best_score = score
                best_provider = name
        
        return best_provider

    def clear(self, provider_name: Optional[str] = None) -> None:
        """Clear health metrics."""
        with self._lock:
            if provider_name:
                if provider_name in self._metrics:
                    del self._metrics[provider_name]
                if provider_name in self._last_reconnect:
                    del self._last_reconnect[provider_name]
            else:
                self._metrics.clear()
                self._last_reconnect.clear()


# ============================================================================
# SECTION: ai.providers.provider_factory (ai/providers/provider_factory.py)
# ============================================================================
"""
Provider Factory.

Creates provider instances from configuration files or provider classes.
"""

import json
import os
from typing import Dict, Optional, Type
from core.logger import setup_logger
from core.exceptions import ConfigurationError

from ai.providers.base_provider import BaseProvider, ProviderConfig, AuthenticationType
from ai.providers.provider_health import ProviderHealth

logger = setup_logger(__name__)


class ProviderFactory:
    """
    Factory for creating provider instances.
    
    Handles:
    - Loading configuration from JSON files
    - Instantiating provider classes
    - Validating provider configurations
    """
    
    # Map of provider names to their implementation classes
    _provider_classes: Dict[str, Type[BaseProvider]] = {}
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseProvider]) -> None:
        """Register a provider implementation."""
        cls._provider_classes[name] = provider_class
        logger.debug(f"Registered provider: {name}")
    
    @classmethod
    def create_from_config(cls, config_path: str) -> BaseProvider:
        """
        Create a provider instance from a configuration file.
        
        Args:
            config_path: Path to the provider configuration JSON file
            
        Returns:
            Configured provider instance
            
        Raises:
            ConfigurationError: If configuration is invalid or provider not found
        """
        if not os.path.exists(config_path):
            raise ConfigurationError(f"Provider config not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        return cls.create_from_dict(config_data)
    
    @classmethod
    def create_from_dict(cls, config_data: Dict[str, any]) -> BaseProvider:
        """
        Create a provider instance from a dictionary.
        
        Args:
            config_data: Provider configuration dictionary
            
        Returns:
            Configured provider instance
        """
        provider_name = config_data.get("provider_name", "")
        if not provider_name:
            raise ConfigurationError("Provider config missing 'provider_name'")
        
        # Get provider class
        provider_class = cls._provider_classes.get(provider_name.lower())
        if not provider_class:
            raise ConfigurationError(
                f"Unknown provider: {provider_name}. "
                f"Available: {', '.join(cls._provider_classes.keys())}"
            )
        
        # Create config
        config = ProviderConfig(
            provider_name=config_data.get("provider_name", ""),
            endpoint=config_data.get("endpoint", ""),
            auth_type=AuthenticationType(config_data.get("auth_type", "none")),
            api_key=config_data.get("api_key"),
            enabled=config_data.get("enabled", True),
            priority=config_data.get("priority", 0),
            default_model=config_data.get("default_model", ""),
            timeout_seconds=config_data.get("timeout_seconds", 30),
            retry_count=config_data.get("retry_count", 3),
            supports_streaming=config_data.get("supports_streaming", False),
            supports_tool_calling=config_data.get("supports_tool_calling", False),
            supports_vision=config_data.get("supports_vision", False),
            supports_function_calling=config_data.get("supports_function_calling", False),
            options=dict(config_data.get("options", {})),
        )

        # Resolve the API key from the secret store when it is not carried in the
        # JSON (the secure path). If the JSON still has a plaintext key we keep it
        # so migration can move it on first save.
        if not config.api_key:
            try:
                from ai.providers.secret_store import get_secret_store
                config.api_key = get_secret_store().get_secret(config.provider_name)
            except Exception as e:  # noqa: BLE001
                logger.debug(f"Secret store lookup failed for {provider_name}: {e}")
        
        # Create and return provider
        provider = provider_class(config)
        logger.info(f"Created provider: {provider_name}")
        return provider
    
    @classmethod
    def create_from_config_obj(cls, config: ProviderConfig) -> BaseProvider:
        """
        Create a provider instance from a ProviderConfig object.
        
        Args:
            config: Provider configuration object
            
        Returns:
            Configured provider instance
        """
        provider_name = config.provider_name
        
        # Get provider class
        provider_class = cls._provider_classes.get(provider_name.lower())
        if not provider_class:
            raise ConfigurationError(
                f"Unknown provider: {provider_name}. "
                f"Available: {', '.join(cls._provider_classes.keys())}"
            )
        
        # Create and return provider
        provider = provider_class(config)
        logger.info(f"Created provider: {provider_name}")
        return provider
    
    @classmethod
    def _get_provider_class(cls, provider_name: str) -> Optional[Type[BaseProvider]]:
        """Get provider class by name."""
        return cls._provider_classes.get(provider_name.lower())
        provider = provider_class(config)
        logger.info(f"Created provider: {provider_name}")
        return provider
    
    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of registered provider names."""
        return list(cls._provider_classes.keys())


def register_standard_providers() -> None:
    """
    Register all standard providers.
    
    Called during application initialization.
    """
    try:
        from ai.providers.ollama_provider import OllamaProvider
        from ai.providers.gemini_provider import GeminiProvider
        from ai.providers.openai_provider import OpenAIProvider
        from ai.providers.anthropic_provider import AnthropicProvider
        from ai.providers.groq_provider import GroqProvider
        from ai.providers.cerebras_provider import CerebrasProvider
        from ai.providers.fireworks_provider import FireworksProvider
        from ai.providers.deepinfra_provider import DeepInfraProvider
        from ai.providers.together_provider import TogetherProvider
        from ai.providers.custom_provider import CustomProvider
        from ai.providers.qwen_provider import QwenProvider
        from ai.providers.llama_cpp_provider import LlamaCppProvider
        
        ProviderFactory.register_provider("ollama", OllamaProvider)
        ProviderFactory.register_provider("gemini", GeminiProvider)
        ProviderFactory.register_provider("openai", OpenAIProvider)
        ProviderFactory.register_provider("anthropic", AnthropicProvider)
        ProviderFactory.register_provider("groq", GroqProvider)
        ProviderFactory.register_provider("cerebras", CerebrasProvider)
        ProviderFactory.register_provider("fireworks", FireworksProvider)
        ProviderFactory.register_provider("deepinfra", DeepInfraProvider)
        ProviderFactory.register_provider("together", TogetherProvider)
        ProviderFactory.register_provider("custom", CustomProvider)
        ProviderFactory.register_provider("qwen", QwenProvider)
        ProviderFactory.register_provider("llama_cpp", LlamaCppProvider)
        
        logger.info("Standard providers registered successfully")
        
    except Exception as e:
        logger.error(f"Failed to register standard providers: {e}")


# Register providers on import
register_standard_providers()


# ============================================================================
# SECTION: ai.providers.provider_registry (ai/providers/provider_registry.py)
# ============================================================================
"""
Provider Registry.

Central registry for managing all available providers.
"""

import json
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from core.logger import setup_logger
from core.exceptions import ConfigurationError

from ai.providers.base_provider import BaseProvider, ProviderConfig, ProviderStatus
from ai.providers.provider_factory import ProviderFactory
from ai.providers.secret_store import get_secret_store


logger = setup_logger(__name__)


class ProviderRegistry:
    """
    Manages registration, lifecycle, and querying of AI providers.
    
    Responsibilities:
    - Track all registered providers
    - Load providers from config directory
    - Manage provider health and availability
    - Provide provider discovery and selection
    """
    
    def __init__(self, config_dir: str = "config/providers"):
        self.config_dir = config_dir
        self._providers: Dict[str, BaseProvider] = {}
        self._config_paths: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._health: Dict[str, Any] = {}
        logger.info(f"ProviderRegistry initialized with config_dir: {config_dir}")
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Provider Registration
    # ─────────────────────────────────────────────────────────────────────────────

    def register_provider(self, provider: BaseProvider, config_path: Optional[str] = None) -> None:
        """Register a provider instance."""
        name = provider.config.provider_name
        with self._lock:
            self._providers[name] = provider
            if config_path:
                self._config_paths[name] = config_path
        logger.info(f"Registered provider: {name}")

    def unregister_provider(self, provider_name: str) -> None:
        """Remove a provider from the registry."""
        with self._lock:
            if provider_name in self._providers:
                provider = self._providers.pop(provider_name)
                provider.disconnect()
                if provider_name in self._config_paths:
                    del self._config_paths[provider_name]
        logger.info(f"Unregistered provider: {provider_name}")

    # ─────────────────────────────────────────────────────────────────────────────
    # Provider Loading
    # ─────────────────────────────────────────────────────────────────────────────

    def load_all_providers(self) -> List[str]:
        """
        Load all providers from the config directory.
        
        Returns:
            List of successfully loaded provider names
        """
        loaded = []
        
        _BUILTIN_PROVIDERS = {'anthropic': {'provider_name': 'anthropic', 'endpoint': 'https://api.anthropic.com/v1', 'auth_type': 'api_key', 'api_key': '', 'enabled': False, 'priority': 8, 'default_model': 'claude-3-5-sonnet-20241022', 'timeout_seconds': 30, 'retry_count': 3, 'supports_streaming': True, 'supports_tool_calling': True, 'supports_vision': True, 'supports_function_calling': True, 'connection_status': 'uninitialized'}, 'cerebras': {'provider_name': 'cerebras', 'endpoint': 'https://api.cerebras.ai/v1', 'auth_type': 'api_key', 'api_key': '', 'enabled': False, 'priority': 4, 'default_model': 'llama3.1-8b', 'timeout_seconds': 30, 'retry_count': 3, 'supports_streaming': True, 'supports_tool_calling': False, 'supports_vision': False, 'supports_function_calling': False, 'connection_status': 'uninitialized'}, 'custom': {'provider_name': 'custom', 'endpoint': 'http://localhost:8000/v1', 'auth_type': 'api_key', 'api_key': '', 'enabled': False, 'priority': 1, 'default_model': '', 'timeout_seconds': 30, 'retry_count': 3, 'supports_streaming': True, 'supports_tool_calling': False, 'supports_vision': False, 'supports_function_calling': False, 'connection_status': 'uninitialized'}, 'deepinfra': {'provider_name': 'deepinfra', 'endpoint': 'https://api.deepinfra.com/v1/openai', 'auth_type': 'api_key', 'api_key': '', 'enabled': False, 'priority': 6, 'default_model': 'meta-llama/Meta-Llama-3-8B-Instruct', 'timeout_seconds': 30, 'retry_count': 3, 'supports_streaming': True, 'supports_tool_calling': False, 'supports_vision': False, 'supports_function_calling': False, 'connection_status': 'uninitialized'}, 'fireworks': {'provider_name': 'fireworks', 'endpoint': 'https://api.fireworks.ai/inference/v1', 'auth_type': 'api_key', 'api_key': '', 'enabled': False, 'priority': 3, 'default_model': 'accounts/fireworks/models/llama-v3p1-8b-instruct', 'timeout_seconds': 30, 'retry_count': 3, 'supports_streaming': True, 'supports_tool_calling': False, 'supports_vision': False, 'supports_function_calling': False, 'connection_status': 'uninitialized'}, 'gemini': {'provider_name': 'gemini', 'endpoint': 'https://generativelanguage.googleapis.com/v1beta', 'auth_type': 'api_key', 'enabled': False, 'priority': 5, 'default_model': 'gemini-1.5-flash', 'timeout_seconds': 30, 'retry_count': 3, 'supports_streaming': True, 'supports_tool_calling': True, 'supports_vision': True, 'supports_function_calling': True}, 'groq': {'provider_name': 'groq', 'endpoint': 'https://api.groq.com/openai/v1', 'auth_type': 'api_key', 'api_key': '', 'enabled': False, 'priority': 7, 'default_model': 'llama3-8b-8192', 'timeout_seconds': 30, 'retry_count': 3, 'supports_streaming': True, 'supports_tool_calling': True, 'supports_vision': False, 'supports_function_calling': False, 'connection_status': 'uninitialized'}, 'llama_cpp': {'provider_name': 'llama_cpp', 'endpoint': 'http://127.0.0.1:8080/v1', 'auth_type': 'none', 'enabled': True, 'priority': 100, 'default_model': 'qwen2.5-coder-7b-instruct-q4_k_m', 'timeout_seconds': 120, 'retry_count': 1, 'supports_streaming': True, 'supports_tool_calling': False, 'supports_vision': False, 'supports_function_calling': False, 'options': {'model_directory': 'D:\\llama_models', 'server_executable': 'D:\\llama_cpp_cuda\\llama-server.exe', 'port': 8080, 'startup_timeout_seconds': 180, 'stop_owned_server_on_exit': True, 'context_size': 8192, 'threads': 20, 'threads_batch': 20, 'gpu_layers': 'auto', 'device': 'CUDA0', 'fit': 'on', 'fit_target_mib': 256, 'flash_attention': 'on', 'batch_size': 2048, 'ubatch_size': 512}}, 'ollama': {'provider_name': 'ollama', 'endpoint': 'http://localhost:11434', 'auth_type': 'none', 'enabled': True, 'priority': 10, 'default_model': 'qwen2.5-coder:7b', 'timeout_seconds': 120, 'retry_count': 3, 'supports_streaming': True, 'supports_tool_calling': True, 'supports_vision': False, 'supports_function_calling': True}, 'openai': {'provider_name': 'openai', 'endpoint': 'https://api.openai.com/v1', 'auth_type': 'api_key', 'api_key': '', 'enabled': False, 'priority': 9, 'default_model': 'gpt-4o-mini', 'timeout_seconds': 30, 'retry_count': 3, 'supports_streaming': True, 'supports_tool_calling': True, 'supports_vision': True, 'supports_function_calling': True, 'connection_status': 'uninitialized'}, 'qwen': {'provider_name': 'qwen', 'endpoint': 'http://localhost:11434', 'auth_type': 'none', 'enabled': True, 'priority': 15, 'default_model': 'qwen2.5-coder:7b', 'timeout_seconds': 120, 'retry_count': 3, 'supports_streaming': True, 'supports_tool_calling': False, 'supports_vision': False, 'supports_function_calling': True}, 'together': {'provider_name': 'together', 'endpoint': 'https://api.together.xyz/v1', 'auth_type': 'api_key', 'api_key': '', 'enabled': False, 'priority': 2, 'default_model': 'meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo', 'timeout_seconds': 30, 'retry_count': 3, 'supports_streaming': True, 'supports_tool_calling': False, 'supports_vision': False, 'supports_function_calling': False, 'connection_status': 'uninitialized'}}
        disk_files = {}
        if os.path.exists(self.config_dir):
            for filename in os.listdir(self.config_dir):
                if filename.endswith('.json'):
                    disk_files[filename[:-5]] = os.path.join(self.config_dir, filename)

        for pname, pdict in _BUILTIN_PROVIDERS.items():
            if pname in disk_files:
                config_path = disk_files.pop(pname)
                try:
                    provider = ProviderFactory.create_from_config(config_path)
                    self.register_provider(provider, config_path)
                    self._migrate_plaintext_key(provider, config_path)
                    loaded.append(provider.config.provider_name)
                except ConfigurationError as e:
                    logger.error(f"Failed to load provider from {config_path}: {e}")
            else:
                try:
                    provider = ProviderFactory.create_from_dict(pdict)
                    self.register_provider(provider)
                    loaded.append(provider.config.provider_name)
                except Exception as e:
                    logger.error(f"Failed to load built-in provider {pname}: {e}")

        for pname, config_path in disk_files.items():
            try:
                provider = ProviderFactory.create_from_config(config_path)
                self.register_provider(provider, config_path)
                self._migrate_plaintext_key(provider, config_path)
                loaded.append(provider.config.provider_name)
            except ConfigurationError as e:
                logger.error(f"Failed to load provider from {config_path}: {e}")
        
        logger.info(f"Loaded {len(loaded)} providers from {self.config_dir}")
        return loaded
    
    def load_provider(self, provider_name: str) -> Optional[BaseProvider]:
        """
        Load a single provider by name.
        
        Args:
            provider_name: Name of the provider (matches config filename)
            
        Returns:
            Provider instance or None if not found/failed
        """
        config_path = os.path.join(self.config_dir, f"{provider_name}.json")
        if not os.path.exists(config_path):
            logger.error(f"Provider config not found: {config_path}")
            return None
        
        try:
            provider = ProviderFactory.create_from_config(config_path)
            self.register_provider(provider, config_path)
            self._migrate_plaintext_key(provider, config_path)
            return provider
        except ConfigurationError as e:
            logger.error(f"Failed to load provider {provider_name}: {e}")
            return None
    
    def reload_provider(self, provider_name: str) -> Optional[BaseProvider]:
        """Reload a provider from its config file."""
        self.unregister_provider(provider_name)
        return self.load_provider(provider_name)
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Provider Access
    # ─────────────────────────────────────────────────────────────────────────────

    def get_provider(self, provider_name: str) -> Optional[BaseProvider]:
        """Get a provider by name."""
        return self._providers.get(provider_name)
    
    def get_enabled_providers(self) -> List[BaseProvider]:
        """Get all enabled providers."""
        return [
            p for p in self._providers.values()
            if p.config.enabled
        ]
    
    def get_connected_providers(self) -> List[BaseProvider]:
        """Get all connected providers."""
        return [
            p for p in self._providers.values()
            if p.is_connected()
        ]
    
    def get_available_providers(self) -> List[BaseProvider]:
        """Get enabled and connected providers."""
        return [
            p for p in self._providers.values()
            if p.is_available()
        ]

    def get_all_providers(self) -> Dict[str, BaseProvider]:
        """Get all registered providers."""
        return dict(self._providers)
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Provider Configuration
    # ─────────────────────────────────────────────────────────────────────────────

    def enable_provider(self, provider_name: str) -> bool:
        """Enable a provider."""
        provider = self._providers.get(provider_name)
        if not provider:
            return False
        
        provider.config.enabled = True
        self._save_provider_config(provider)
        logger.info(f"Enabled provider: {provider_name}")
        return True
    
    def disable_provider(self, provider_name: str) -> bool:
        """Disable a provider."""
        provider = self._providers.get(provider_name)
        if not provider:
            return False
        
        provider.config.enabled = False
        self._save_provider_config(provider)
        logger.info(f"Disabled provider: {provider_name}")
        return True
    
    def set_provider_priority(self, provider_name: str, priority: int) -> bool:
        """Set provider priority (higher = preferred)."""
        provider = self._providers.get(provider_name)
        if not provider:
            return False
        
        provider.config.priority = priority
        self._save_provider_config(provider)
        logger.info(f"Set priority {priority} for provider: {provider_name}")
        return True
    
    def set_default_model(self, provider_name: str, model_id: str) -> bool:
        """Set default model for a provider."""
        provider = self._providers.get(provider_name)
        if not provider:
            return False
        
        provider.config.default_model = model_id
        self._save_provider_config(provider)
        logger.info(f"Set default model '{model_id}' for provider: {provider_name}")
        return True
    
    def get_loaded_providers(self) -> List[str]:
        """Get list of loaded provider names."""
        return list(self._providers.keys())
    
    def _save_provider_config(self, provider: BaseProvider) -> None:
        """Save provider config to file.

        When a secure secret backend (keyring/encrypted) is active the API key
        is written to the secret store and stripped from the JSON, so the file
        on disk never contains the plaintext key. With only the plaintext
        fallback the key stays in the JSON exactly as before.
        """
        config_path = self._config_paths.get(provider.config.provider_name)
        if not config_path:
            return

        config_data = provider.config.to_dict()
        try:
            store = get_secret_store()
            api_key = config_data.get("api_key")
            if store.secure:
                if api_key:
                    store.set_secret(provider.config.provider_name, api_key)
                config_data.pop("api_key", None)  # never persist plaintext
        except Exception as e:  # noqa: BLE001
            logger.error(f"Secret store save failed for {provider.config.provider_name}: {e}")

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)

    def _migrate_plaintext_key(self, provider: BaseProvider, config_path: str) -> None:
        """Move a plaintext key found in the JSON into the secret store, once.

        Idempotent: if the JSON has no key, or the backend is plaintext-only,
        this is a no-op. After migration the key remains available in memory via
        ``provider.config.api_key`` but is scrubbed from disk.
        """
        try:
            store = get_secret_store()
            if not store.secure:
                return
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            plaintext = data.get("api_key")
            if not plaintext:
                return
            store.set_secret(provider.config.provider_name, plaintext)
            data.pop("api_key", None)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            provider.config.api_key = plaintext
            logger.info(f"Migrated API key for '{provider.config.provider_name}' to {store.backend}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Key migration failed for {provider.config.provider_name}: {e}")

    def set_api_key(self, provider_name: str, api_key: str) -> bool:
        """Set/update a provider's API key, routing it through the secret store."""
        provider = self._providers.get(provider_name)
        if not provider:
            return False
        provider.config.api_key = api_key
        self._save_provider_config(provider)
        logger.info(f"Updated API key for provider: {provider_name}")
        return True

    def get_secret_backend(self) -> str:
        """Return the active secret-storage backend name (for UI display)."""
        try:
            return get_secret_store().backend
        except Exception:  # noqa: BLE001
            return "unknown"

    # ─────────────────────────────────────────────────────────────────────────────
    # Health & Status
    # ─────────────────────────────────────────────────────────────────────────────

    def get_provider_health(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get health status for a provider."""
        provider = self._providers.get(provider_name)
        if not provider:
            return None
        
        return {
            "provider_name": provider_name,
            "status": provider.get_status().value,
            "is_connected": provider.is_connected(),
            "is_available": provider.is_available(),
            "last_tested": self._health.get(provider_name, {}).get("last_tested"),
            "success_rate": self._health.get(provider_name, {}).get("success_rate", 1.0),
        }

    def test_all_connections(self) -> Dict[str, bool]:
        """
        Test connections to all providers.
        
        Returns:
            Dict mapping provider names to connection success
        """
        results = {}
        for name, provider in self._providers.items():
            try:
                success = provider.test_connection()
                self._health[name] = {
                    "last_tested": datetime.utcnow().isoformat(),
                    "success_rate": 1.0 if success else 0.0,
                }
                results[name] = success
            except Exception as e:
                logger.error(f"Connection test failed for {name}: {e}")
                results[name] = False
        return results
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Model Discovery
    # ─────────────────────────────────────────────────────────────────────────────

    def refresh_all_models(self) -> Dict[str, List[str]]:
        """
        Refresh models for all providers.
        
        Returns:
            Dict mapping provider names to their model IDs
        """
        results = {}
        for name, provider in self._providers.items():
            try:
                models = provider.refresh_models()
                provider._set_models(models)
                results[name] = [m.get("id", m.get("name", "")) for m in models]
            except Exception as e:
                logger.error(f"Failed to refresh models for {name}: {e}")
                results[name] = []
        return results
    
    def get_all_models(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all models from all providers.
        
        Returns:
            Dict mapping provider names to list of model info
        """
        result = {}
        for name, provider in self._providers.items():
            models = provider.get_models()
            if models:
                result[name] = list(models.values())
        return result


# ============================================================================
# SECTION: ai.providers.provider_router (ai/providers/provider_router.py)
# ============================================================================
"""
Provider Router.

Routes requests to the appropriate provider based on task requirements.
"""

from typing import Dict, List, Optional, Any
from core.logger import setup_logger

from ai.providers.base_provider import BaseProvider, ProviderStatus
from ai.providers.provider_registry import ProviderRegistry
from ai.engine.task import Task
from ai.memory.project_context import ProjectContext
from ui.settings_manager import get_settings_manager


logger = setup_logger(__name__)


class ProviderRouter:
    """
    Routes AI requests to the best available provider.
    
    Implements routing logic based on:
    - Provider priority
    - Task requirements (streaming, tool calling, vision, etc.)
    - Provider health and availability
    - Model capabilities
    """
    
    def __init__(self, registry: ProviderRegistry):
        self.registry = registry
        self.logger = logger

    # ─────────────────────────────────────────────────────────────────────────────
    # Request Routing
    # ─────────────────────────────────────────────────────────────────────────────

    def route_request(
        self,
        prompt: str,
        task: Optional[Task] = None,
        context: Optional[ProjectContext] = None,
        **kwargs
    ) -> str:
        """
        Route a request to the best available provider.
        
        Args:
            prompt: The user prompt
            task: Optional task for context
            context: Optional project context
            **kwargs: Additional routing options
            
        Returns:
            The generated response
            
        Raises:
            RuntimeError: If no suitable provider is available
        """
        provider = self.select_provider(task, **kwargs)
        
        if not provider:
            raise RuntimeError("No suitable provider available for this request")
        
        self.logger.info(f"Routed request to provider: {provider.config.provider_name}")
        
        try:
            model_id = kwargs.get("model_id")
            response = provider.generate_response(
                prompt=prompt,
                model_id=model_id,
                **kwargs
            )
            return response
            
        except Exception as e:
            self.logger.error(f"Provider {provider.config.provider_name} failed: {e}")
            raise

    def route_stream(
        self,
        prompt: str,
        task: Optional[Task] = None,
        context: Optional[ProjectContext] = None,
        on_chunk=None,
        **kwargs
    ) -> str:
        """
        Route a streaming request to the best available provider.
        
        Args:
            prompt: The user prompt
            task: Optional task for context
            context: Optional project context
            on_chunk: Callback for each response chunk
            **kwargs: Additional routing options
            
        Returns:
            The complete generated response
        """
        provider = self.select_provider(task, require_streaming=True, **kwargs)
        
        if not provider:
            raise RuntimeError("No suitable streaming provider available")
        
        if not provider.supports_streaming():
            self.logger.warning(
                f"Provider {provider.config.provider_name} does not support streaming, "
                "using regular response"
            )
            return self.route_request(prompt, task, context, **kwargs)
        
        self.logger.info(f"Routed streaming request to provider: {provider.config.provider_name}")
        
        try:
            model_id = kwargs.get("model_id")
            response = provider.stream_response(
                prompt=prompt,
                model_id=model_id,
                on_chunk=on_chunk,
                **kwargs
            )
            return response
            
        except Exception as e:
            self.logger.error(f"Streaming provider {provider.config.provider_name} failed: {e}")
            raise

    # ─────────────────────────────────────────────────────────────────────────────
    # Provider Selection
    # ─────────────────────────────────────────────────────────────────────────────

    def select_provider(
        self,
        task: Optional[Task] = None,
        require_streaming: bool = False,
        require_vision: bool = False,
        require_tool_calling: bool = False,
        preferred_provider: Optional[str] = None,
        **kwargs
    ) -> Optional[BaseProvider]:
        """
        Select the best provider for a request.
        
        Args:
            task: Optional task for context
            require_streaming: Require streaming support
            require_vision: Require vision support
            require_tool_calling: Require tool/function calling support
            preferred_provider: Preferred provider name
            **kwargs: Additional selection criteria
            
        Returns:
            Selected provider or None if no suitable provider available
        """
        providers = self._get_eligible_providers(
            require_streaming=require_streaming,
            require_vision=require_vision,
            require_tool_calling=require_tool_calling,
        )
        
        if not providers:
            return None
        
        # Sort by priority (highest first)
        providers.sort(key=lambda p: p.config.priority, reverse=True)
        
        # Use preferred provider if available and in the list
        if preferred_provider:
            for provider in providers:
                if provider.config.provider_name == preferred_provider:
                    return provider
        
        # Return highest priority provider
        return providers[0]

    def _get_eligible_providers(
        self,
        require_streaming: bool = False,
        require_vision: bool = False,
        require_tool_calling: bool = False,
    ) -> List[BaseProvider]:
        """Get providers that meet the specified requirements."""
        eligible = []
        
        for provider in self.registry.get_available_providers():
            if (get_settings_manager().get("models", "routing_policy", "local_only") == "local_only"
                    and provider.config.provider_name not in ("llama_cpp", "ollama", "qwen")):
                continue
            # Check required capabilities
            if require_streaming and not provider.supports_streaming():
                continue
            
            if require_vision and not provider.supports_vision():
                continue
            
            if require_tool_calling and not provider.supports_tool_calling():
                continue
            
            eligible.append(provider)
        
        return eligible

    # ─────────────────────────────────────────────────────────────────────────────
    # Capability Queries
    # ────────────────────────────────────────────��────────────────────────────────

    def get_providers_supporting(self, capability: str) -> List[BaseProvider]:
        """
        Get all providers supporting a specific capability.
        
        Args:
            capability: Capability name (streaming, vision, tool_calling, etc.)
            
        Returns:
            List of providers supporting the capability
        """
        result = []
        
        for provider in self.registry.get_available_providers():
            if capability == "streaming" and provider.supports_streaming():
                result.append(provider)
            elif capability == "vision" and provider.supports_vision():
                result.append(provider)
            elif capability == "tool_calling" and provider.supports_tool_calling():
                result.append(provider)
            elif capability == "function_calling" and provider.supports_function_calling():
                result.append(provider)
        
        return result

    def get_capabilities_for_provider(self, provider_name: str) -> Dict[str, bool]:
        """
        Get capabilities for a specific provider.
        
        Args:
            provider_name: Provider name
            
        Returns:
            Dict mapping capability names to bool
        """
        provider = self.registry.get_provider(provider_name)
        if not provider:
            return {}
        
        return {
            "streaming": provider.supports_streaming(),
            "vision": provider.supports_vision(),
            "tool_calling": provider.supports_tool_calling(),
            "function_calling": provider.supports_function_calling(),
        }


# ============================================================================
# SECTION: ai.providers.provider_manager (ai/providers/provider_manager.py)
# ============================================================================
"""
Provider Manager.

Unified management interface for all provider operations,
including Parallel Initialization (Part18), Event System (Part22),
and Automatic Background Recovery (Part17).
"""

import threading
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from core.logger import setup_logger
from core.event_bus import EventBus
from core.exceptions import ProviderError

from ai.providers.base_provider import BaseProvider, ProviderConfig, ProviderStatus
from ai.providers.provider_registry import ProviderRegistry
from ai.providers.provider_health import ProviderHealth
from ai.providers.provider_router import ProviderRouter


logger = setup_logger(__name__)


class ProviderEventTypes:
    """Event types for Part22"""
    CONNECTED = "provider_connected"
    DISCONNECTED = "provider_disconnected"
    FAILED = "provider_failed"
    RECOVERING = "provider_recovering"
    UPDATED = "provider_updated"
    MODEL_ADDED = "model_added"
    MODEL_REMOVED = "model_removed"
    API_CHANGED = "api_changed"
    HEALTH_CHANGED = "health_changed"


class ProviderManager:
    """
    Manages all provider operations for the application.
    
    Responsibilities:
    - Enable/Disable providers
    - Validate API keys
    - Test connections
    - Refresh models
    - Health monitoring
    - Automatic reconnection
    - Event broadcasting
    - Parallel initialization (Part18)
    - Automatic background recovery (Part17)
    - Provider Event System (Part22)
    """
    
    def __init__(self, registry: ProviderRegistry, event_bus: Optional[EventBus] = None):
        self.registry = registry
        self.event_bus = event_bus
        self.router = ProviderRouter(registry)
        self._health = ProviderHealth(registry)
        self._reconnect_threads: Dict[str, threading.Thread] = {}
        self._running = True
        self._lock = threading.Lock()
        self._health_thread: Optional[threading.Thread] = None
        self._config_hash: Dict[str, str] = {}
        
        logger.info("ProviderManager initialized")
        
        # Monitor config changes for Part17
        self._initialize_config_hashes()
        
        # Start health monitor and background recovery
        self.monitor_health()
        self._start_background_recovery()

    # ─────────────────────────────────────────────────────────────────────────────
    # Part17: Automatic Background Recovery & Config Monitoring
    # ─────────────────────────────────────────────────────────────────────────────
    def _initialize_config_hashes(self) -> None:
        """Store initial config hashes to detect changes later"""
        for name, provider in self.registry.get_all_providers().items():
            config_str = f"{provider.config.api_key or ''}-{provider.config.endpoint}-{provider.config.enabled}"
            self._config_hash[name] = hashlib.sha256(config_str.encode()).hexdigest()
    
    def _check_config_changes(self) -> None:
        """Check if any provider's config changed (Part17)"""
        for name, provider in self.registry.get_all_providers().items():
            config_str = f"{provider.config.api_key or ''}-{provider.config.endpoint}-{provider.config.enabled}"
            new_hash = hashlib.sha256(config_str.encode()).hexdigest()
            
            if new_hash != self._config_hash.get(name, ""):
                logger.info(f"Config changed for {name}, reconnecting...")
                self._config_hash[name] = new_hash
                self._fire_event(ProviderEventTypes.API_CHANGED, {"provider": name})
                
                # Trigger refresh in background
                def refresh_job(provider_name=name, provider_instance=provider):
                    try:
                        self._fire_event(ProviderEventTypes.RECOVERING, {"provider": provider_name})
                        if provider_instance.connect():
                            # The result used to be thrown away, so the cache
                            # stayed empty after a config-change reconnect.
                            models = provider_instance.refresh_models()
                            if models:
                                provider_instance._set_models(models)
                            self._fire_event(ProviderEventTypes.CONNECTED, {"provider": provider_name})
                            self._fire_event("models_refreshed", {
                                "provider": provider_name,
                                "models": [m.get("id", m.get("name", "")) for m in models],
                            })
                    except Exception as e:
                        logger.error(f"Failed to reconnect {provider_name}: {e}")
                
                threading.Thread(target=refresh_job, daemon=True).start()
    
    def _start_background_recovery(self) -> None:
        """Start background thread for config monitoring"""
        def recovery_loop():
            while self._running:
                try:
                    self._check_config_changes()
                    time.sleep(5)  # check every 5 seconds
                except Exception as e:
                    logger.error(f"Recovery loop error: {e}")
        
        threading.Thread(target=recovery_loop, daemon=True).start()
        logger.info("Background recovery started")

    # ─────────────────────────────────────────────────────────────────────────────
    # Part18: Parallel Initialization
    # ─────────────────────────────────────────────────────────────────────────────
    def initialize_all_providers_parallel(self) -> None:
        """Initialize all providers in parallel (Part18)"""
        providers = self.registry.get_all_providers()
        
        def initialize_provider(name: str, provider: BaseProvider):
            logger.info(f"Initializing {name} in background...")
            try:
                # Record initial state
                provider._update_status(ProviderStatus.CONNECTING)
                self._fire_event(ProviderEventTypes.RECOVERING, {"provider": name})
                
                # Connect
                if provider.connect():
                    # Refreshes models
                    models = provider.refresh_models()
                    provider._set_models(models)
                    
                    # Update health metrics
                    metrics = self._health.get_metrics(name)
                    if metrics:
                        metrics.last_sync = datetime.utcnow()
                        metrics.last_ping = datetime.utcnow()
                        metrics.available_models_count = len(models)
                        metrics.cached_valid_api_key = True
                        metrics.status = ProviderStatus.CONNECTED
                    
                    self._fire_event(ProviderEventTypes.CONNECTED, {"provider": name, "model_count": len(models)})
                    if models:
                        self._fire_event("models_refreshed", {
                            "provider": name,
                            "models": [m.get("id", m.get("name", "")) for m in models],
                        })
                    logger.info(f"Successfully initialized {name}")
                else:
                    provider._update_status(ProviderStatus.DISCONNECTED)
                    logger.warning(f"Failed to connect {name} during parallel init")
                    
            except Exception as e:
                logger.error(f"Parallel init error for {name}: {e}")
                provider._update_status(ProviderStatus.ERROR, str(e))
                self._fire_event(ProviderEventTypes.FAILED, {"provider": name, "error": str(e)})
        
        # Start a thread per provider
        for name, provider in providers.items():
            if provider.config.enabled:
                thread = threading.Thread(target=initialize_provider, args=(name, provider), daemon=True)
                thread.start()
                self._reconnect_threads[name] = thread
        
        logger.info(f"Parallel initialization started for {len(providers)} providers")

    # ─────────────────────────────────────────────────────────────────────────────
    # Provider Control
    # ─────────────────────────────────────────────────────────────────────────────

    def enable_provider(self, provider_name: str) -> bool:
        """Enable a provider."""
        success = self.registry.enable_provider(provider_name)
        if success:
            self._fire_event("provider_enabled", {"provider": provider_name})
        return success

    def disable_provider(self, provider_name: str) -> bool:
        """Disable a provider."""
        provider = self.registry.get_provider(provider_name)
        if not provider:
            return False
        
        provider.disconnect()
        success = self.registry.disable_provider(provider_name)
        if success:
            self._fire_event("provider_disabled", {"provider": provider_name})
        return success

    def validate_api_key(self, provider_name: str, api_key: str) -> bool:
        """
        Validate an API key for a provider.
        
        Args:
            provider_name: Name of the provider
            api_key: API key to validate
            
        Returns:
            True if key is valid, False otherwise
        """
        provider = self.registry.get_provider(provider_name)
        if not provider:
            return False
        
        # Create temporary provider with provided API key
        temp_config = ProviderConfig(
            provider_name=provider.config.provider_name,
            endpoint=provider.config.endpoint,
            auth_type=provider.config.auth_type,
            api_key=api_key,
            enabled=True,
            timeout_seconds=10,
        )
        
        temp_provider = type(provider)(temp_config)
        
        try:
            # Try a minimal request (like listing models or checking auth)
            return temp_provider.test_connection()
        except Exception as e:
            logger.error(f"API key validation failed for {provider_name}: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────────────────

    def test_connection(self, provider_name: str) -> bool:
        """Test connection to a provider."""
        provider = self.registry.get_provider(provider_name)
        if not provider:
            return False
        
        success = provider.test_connection()
        if success:
            provider._update_status(ProviderStatus.CONNECTED)
        else:
            provider._update_status(ProviderStatus.ERROR, "Connection failed")
        return success

    # ─────────────────────────────────────────────────────────────────────────────
    # Model Management
    # ─────────────────────────────────────────────────────────────────────────────

    def refresh_models(self, provider_name: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Refresh available models for provider(s).
        
        Args:
            provider_name: Specific provider or None for all
            
        Returns:
            Dict mapping provider names to model IDs
        """
        if provider_name:
            provider = self.registry.get_provider(provider_name)
            if not provider:
                return {}
            
            try:
                models = provider.refresh_models()
                provider._set_models(models)
                self._fire_event("models_refreshed", {
                    "provider": provider_name,
                    "models": [m.get("id", m.get("name", "")) for m in models],
                })
                return {provider_name: [m.get("id", m.get("name", "")) for m in models]}
            except Exception as e:
                logger.error(f"Failed to refresh models for {provider_name}: {e}")
                return {provider_name: []}
        
        # Refresh all
        return self.registry.refresh_all_models()

    def register_models(self, provider_name: str, models: List[Dict[str, Any]]) -> None:
        """
        Register models for a provider.
        
        Args:
            provider_name: Provider name
            models: List of model definitions
        """
        provider = self.registry.get_provider(provider_name)
        if not provider:
            return
        
        provider._set_models(models)
        logger.info(f"Registered {len(models)} models for {provider_name}")

    # ─────────────────────────────────────────────────────────────────────────────
    # Health Monitoring
    # ─────────────────────────────────────────────────────────────────────────────

    def get_health_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get health status for all providers.
        
        Returns:
            Dict mapping provider names to health info
        """
        return self._health.get_all_health()

    def monitor_health(self) -> None:
        """Start background health monitoring."""
        with self._lock:
            if self._health_thread and self._health_thread.is_alive():
                logger.debug("Health monitoring already started")
                return

        def monitor_loop():
            while self._running:
                try:
                    self._check_health()
                    time.sleep(60)  # Check every 60 seconds
                except Exception as e:
                    logger.error(f"Health monitor error: {e}")
        
        thread = threading.Thread(target=monitor_loop, daemon=True,
                                   name="provider-health")
        with self._lock:
            if self._health_thread and self._health_thread.is_alive():
                return
            self._health_thread = thread
        thread.start()
        logger.info("Health monitoring started")

    def _check_health(self) -> None:
        """Check health of all providers."""
        for provider_name, provider in self.registry.get_all_providers().items():
            try:
                if provider.config.enabled:
                    if not provider.is_connected():
                        self._attempt_reconnect(provider)
                    
                    # Update health metrics
                    status = provider.get_status()
                    self._health.record_status(provider_name, status)
                    
            except Exception as e:
                logger.error(f"Health check failed for {provider_name}: {e}")

    def _attempt_reconnect(self, provider: BaseProvider) -> bool:
        """Attempt to reconnect to a provider."""
        provider_name = provider.config.provider_name
        
        # Don't reconnect too frequently
        last_attempt = self._health.get_last_attempt(provider_name)
        if last_attempt:
            elapsed = (datetime.utcnow() - last_attempt).total_seconds()
            if elapsed < 30:  # Minimum 30 seconds between attempts
                return False
        
        self._health.record_attempt(provider_name)
        
        try:
            if provider.connect():
                provider._update_status(ProviderStatus.CONNECTED)
                self._fire_event("connected", {"provider": provider_name})
                # A provider that just came back online almost certainly has a
                # model list the UI never managed to fetch (e.g. Ollama wasn't
                # running yet at startup), so refresh and broadcast it now.
                try:
                    models = self.refresh_models(provider_name).get(provider_name, [])
                    if models:
                        self._fire_event("models_refreshed", {
                            "provider": provider_name,
                            "models": models,
                        })
                except Exception as e:
                    logger.warning(f"Post-reconnect model refresh failed for {provider_name}: {e}")
                return True
        except Exception as e:
            logger.error(f"Reconnection failed for {provider_name}: {e}")
            provider._update_status(ProviderStatus.ERROR, str(e))
        
        return False

    # ─────────────────────────────────────────────────────────────────────────────
    # Event Broadcasting
    # ─────────────────────────────────────────────────────────────────────────────

    def _fire_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Fire an event to the event bus.

        Callers pass either a bare name ("connected") or an already-namespaced
        one (ProviderEventTypes.CONNECTED == "provider_connected"). Only the
        bare form gets the prefix — blindly prepending produced topics like
        "provider_provider_connected", which nothing could ever subscribe to.
        """
        topic = event_type if event_type.startswith("provider_") else f"provider_{event_type}"
        if self.event_bus:
            self.event_bus.publish(topic, data)
        logger.debug(f"Event fired: {topic}")

    # ─────────────────────────────────────────────────────────────────────────────
    # Shutdown
    # ─────────────────────────────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Shutdown the provider manager."""
        self._running = False

        thread = self._health_thread
        if thread and thread.is_alive():
            thread.join(timeout=2)
        
        # Disconnect all providers
        for provider in self.registry.get_all_providers().values():
            provider.disconnect()
        
        logger.info("ProviderManager shutdown complete")

