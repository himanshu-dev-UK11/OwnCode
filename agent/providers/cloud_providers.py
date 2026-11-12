"""
Consolidated Module: agent.providers.cloud_providers

Combines: ai.providers.openai_provider, ai.providers.anthropic_provider, ai.providers.gemini_provider, ai.providers.groq_provider, ai.providers.cerebras_provider, ai.providers.deepinfra_provider, ai.providers.fireworks_provider, ai.providers.together_provider, ai.providers.custom_provider
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['ai.providers.openai_provider', 'ai.providers.anthropic_provider', 'ai.providers.gemini_provider', 'ai.providers.groq_provider', 'ai.providers.cerebras_provider', 'ai.providers.deepinfra_provider', 'ai.providers.fireworks_provider', 'ai.providers.together_provider', 'ai.providers.custom_provider']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ai.providers.openai_provider (ai/providers/openai_provider.py)
# ============================================================================
"""
OpenAI Provider.

OpenAI cloud API provider.
"""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from core.logger import setup_logger

from ai.providers.base_provider import BaseProvider, ProviderConfig, ProviderStatus


logger = setup_logger(__name__)


class OpenAIProvider(BaseProvider):
    """
    Provider implementation for OpenAI API.
    
    Supports:
    - Text generation
    - Streaming responses
    - Vision (GPT-4V)
    - Tool calling
    
    Requires:
    - API key from OpenAI
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        
        # Update config with defaults
        if not self.config.endpoint:
            self.config.endpoint = "https://api.openai.com/v1"
        if not self.config.supports_streaming:
            self.config.supports_streaming = True
        if not self.config.supports_tool_calling:
            self.config.supports_tool_calling = True
        if not self.config.supports_function_calling:
            self.config.supports_function_calling = True

    def connect(self) -> bool:
        """Connect to OpenAI API (validates API key)."""
        try:
            self._update_status(ProviderStatus.CONNECTING)
            
            if not self.config.api_key:
                self._update_status(ProviderStatus.ERROR, "API key not configured")
                return False
            
            # Test connection by listing models
            models = self.refresh_models()
            
            if models:
                self._set_connected()
                self.logger.info("Connected to OpenAI API")
                return True
            else:
                self._update_status(ProviderStatus.ERROR, "No models available")
                return False
                
        except urllib.error.HTTPError as e:
            if e.code == 401:
                self._update_status(ProviderStatus.ERROR, "Invalid API key")
            elif e.code == 403:
                self._update_status(ProviderStatus.ERROR, "API key lacks required permissions")
            elif e.code == 429:
                self._update_status(ProviderStatus.ERROR, "API quota exceeded")
            else:
                self._update_status(ProviderStatus.ERROR, f"HTTP {e.code}")
            self.logger.error(f"OpenAI connection failed: {e}")
            return False
        except Exception as e:
            self._update_status(ProviderStatus.ERROR, str(e))
            self.logger.error(f"Unexpected error connecting to OpenAI: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from OpenAI API."""
        self._update_status(ProviderStatus.DISCONNECTED)
        self.logger.info("Disconnected from OpenAI API")

    def generate_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response from OpenAI."""
        model = self._get_model_id(model_id)
        
        url = f"{self.config.endpoint}/chat/completions"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        
        if system_prompt:
            payload["messages"].insert(0, {"role": "system", "content": system_prompt})
        
        # Add any additional kwargs
        payload.update(kwargs)
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", f"Bearer {self.config.api_key}")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                # Extract text from response
                choices = result.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    return message.get("content", "")
                
                return ""
                
        except Exception as e:
            self.logger.error(f"OpenAI generation failed: {e}")
            raise

    def stream_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        on_chunk: Optional[callable] = None,
        **kwargs
    ) -> str:
        """Stream a response from OpenAI."""
        model = self._get_model_id(model_id)
        
        url = f"{self.config.endpoint}/chat/completions"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        
        if system_prompt:
            payload["messages"].insert(0, {"role": "system", "content": system_prompt})
        
        payload.update(kwargs)
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", f"Bearer {self.config.api_key}")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        full_response = ""
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                for line in response:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith("data:"):
                            try:
                                chunk = json.loads(line_str[5:])
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    full_response += content
                                    
                                    if on_chunk:
                                        on_chunk(content)
                                
                                if chunk.get("choices", [{}])[0].get("finish_reason") == "stop":
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            self.logger.error(f"OpenAI streaming failed: {e}")
            raise
        
        return full_response

    def refresh_models(self) -> List[Dict[str, Any]]:
        """Refresh available models from OpenAI API."""
        url = f"{self.config.endpoint}/models"
        
        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {self.config.api_key}")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                models = result.get("data", [])
                parsed_models = []
                
                for model in models:
                    model_info = {
                        "id": model.get("id", ""),
                        "name": model.get("id", "").replace("gpt-", "GPT-"),
                        "context_window": self._get_context_window(model.get("id", "")),
                        "max_output_tokens": 4096,
                        "supports_vision": "vision" in model.get("id", "").lower(),
                        "supports_tool_calling": True,
                        "capabilities": self._extract_capabilities(model.get("id", "")),
                    }
                    parsed_models.append(model_info)
                
                return parsed_models
                
        except Exception as e:
            self.logger.error(f"Failed to refresh OpenAI models: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────────────────────────────

    def _set_connected(self) -> None:
        """Set provider to connected status."""
        self._update_status(ProviderStatus.CONNECTED)

    def _get_context_window(self, model_id: str) -> int:
        """Get context window for a model."""
        if "gpt-4o" in model_id:
            return 128000
        elif "gpt-4-turbo" in model_id:
            return 128000
        elif "gpt-4" in model_id:
            return 32768
        elif "gpt-3.5-turbo" in model_id:
            return 16385
        return 4096

    def _extract_capabilities(self, model_id: str) -> List[str]:
        """Extract model capabilities."""
        capabilities = []
        
        model_id_lower = model_id.lower()
        if "vision" in model_id_lower:
            capabilities.append("vision")
        if "tool" in model_id_lower or "function" in model_id_lower:
            capabilities.append("tool_calling")
        
        return capabilities


# ============================================================================
# SECTION: ai.providers.anthropic_provider (ai/providers/anthropic_provider.py)
# ============================================================================
"""
Anthropic Provider.

Anthropic (Claude) cloud API provider.
"""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from core.logger import setup_logger

from ai.providers.base_provider import BaseProvider, ProviderConfig, ProviderStatus


logger = setup_logger(__name__)


class AnthropicProvider(BaseProvider):
    """
    Provider implementation for Anthropic API (Claude).
    
    Supports:
    - Text generation
    - Streaming responses
    - Vision (Claude 3+)
    - Tool calling (Claude 3.5+)
    
    Requires:
    - API key from Anthropic
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        
        # Update config with defaults
        if not self.config.endpoint:
            self.config.endpoint = "https://api.anthropic.com/v1"
        if not self.config.supports_streaming:
            self.config.supports_streaming = True
        if not self.config.supports_vision:
            self.config.supports_vision = True
        if not self.config.supports_tool_calling:
            self.config.supports_tool_calling = True

    def connect(self) -> bool:
        """Connect to Anthropic API (validates API key)."""
        try:
            self._update_status(ProviderStatus.CONNECTING)
            
            if not self.config.api_key:
                self._update_status(ProviderStatus.ERROR, "API key not configured")
                return False
            
            # Test connection by listing models
            models = self.refresh_models()
            
            if models:
                self._set_connected()
                self.logger.info("Connected to Anthropic API")
                return True
            else:
                self._update_status(ProviderStatus.ERROR, "No models available")
                return False
                
        except urllib.error.HTTPError as e:
            if e.code == 401:
                self._update_status(ProviderStatus.ERROR, "Invalid API key")
            elif e.code == 403:
                self._update_status(ProviderStatus.ERROR, "API key lacks required permissions")
            else:
                self._update_status(ProviderStatus.ERROR, f"HTTP {e.code}")
            self.logger.error(f"Anthropic connection failed: {e}")
            return False
        except Exception as e:
            self._update_status(ProviderStatus.ERROR, str(e))
            self.logger.error(f"Unexpected error connecting to Anthropic: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from Anthropic API."""
        self._update_status(ProviderStatus.DISCONNECTED)
        self.logger.info("Disconnected from Anthropic API")

    def generate_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response from Anthropic."""
        model = self._get_model_id(model_id)
        
        url = f"{self.config.endpoint}/messages"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        # Add any additional kwargs
        payload.update(kwargs)
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("x-api-key", self.config.api_key)
        request.add_header("anthropic-version", "2023-06-01")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                # Extract text from response
                content = result.get("content", [])
                if content:
                    for item in content:
                        if item.get("type") == "text":
                            return item.get("text", "")
                
                return ""
                
        except Exception as e:
            self.logger.error(f"Anthropic generation failed: {e}")
            raise

    def stream_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        on_chunk: Optional[callable] = None,
        **kwargs
    ) -> str:
        """Stream a response from Anthropic."""
        model = self._get_model_id(model_id)
        
        url = f"{self.config.endpoint}/messages"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        payload.update(kwargs)
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("x-api-key", self.config.api_key)
        request.add_header("anthropic-version", "2023-06-01")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        full_response = ""
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                for line in response:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith("data:"):
                            try:
                                chunk = json.loads(line_str[5:])
                                event = chunk.get("type", "")
                                
                                if event == "content_block_delta":
                                    delta = chunk.get("delta", {})
                                    text = delta.get("text", "")
                                    full_response += text
                                    
                                    if on_chunk:
                                        on_chunk(text)
                                
                                if event == "message_stop":
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            self.logger.error(f"Anthropic streaming failed: {e}")
            raise
        
        return full_response

    def refresh_models(self) -> List[Dict[str, Any]]:
        """Refresh available models from Anthropic API."""
        url = f"{self.config.endpoint}/models"
        
        request = urllib.request.Request(url)
        request.add_header("x-api-key", self.config.api_key)
        request.add_header("anthropic-version", "2023-06-01")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                models = result.get("data", [])
                parsed_models = []
                
                for model in models:
                    model_info = {
                        "id": model.get("id", ""),
                        "name": model.get("displayName", ""),
                        "context_window": self._get_context_window(model.get("id", "")),
                        "max_output_tokens": 8192,
                        "supports_vision": self._supports_vision(model.get("id", "")),
                        "supports_tool_calling": self._supports_tool_calling(model.get("id", "")),
                        "capabilities": self._extract_capabilities(model.get("id", "")),
                    }
                    parsed_models.append(model_info)
                
                return parsed_models
                
        except Exception as e:
            self.logger.error(f"Failed to refresh Anthropic models: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────────────────────────────

    def _set_connected(self) -> None:
        """Set provider to connected status."""
        self._update_status(ProviderStatus.CONNECTED)

    def _get_context_window(self, model_id: str) -> int:
        """Get context window for a model."""
        if "claude-3.5-sonnet" in model_id or "claude-3-opus" in model_id:
            return 200000
        elif "claude-3-sonnet" in model_id or "claude-3-haiku" in model_id:
            return 200000
        return 100000

    def _supports_vision(self, model_id: str) -> bool:
        """Check if model supports vision."""
        return "claude-3" in model_id.lower()

    def _supports_tool_calling(self, model_id: str) -> bool:
        """Check if model supports tool calling."""
        return "claude-3.5" in model_id.lower() or "claude-3-opus" in model_id.lower()

    def _extract_capabilities(self, model_id: str) -> List[str]:
        """Extract model capabilities."""
        capabilities = []
        
        if self._supports_vision(model_id):
            capabilities.append("vision")
        if self._supports_tool_calling(model_id):
            capabilities.append("tool_calling")
        
        return capabilities


# ============================================================================
# SECTION: ai.providers.gemini_provider (ai/providers/gemini_provider.py)
# ============================================================================
"""
Gemini Provider.

Google Gemini cloud API provider.
"""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from core.logger import setup_logger

from ai.providers.base_provider import BaseProvider, ProviderConfig, ProviderStatus, AuthenticationType


logger = setup_logger(__name__)


class GeminiProvider(BaseProvider):
    """
    Provider implementation for Google Gemini API.
    
    Supports:
    - Text generation
    - Streaming responses
    - Vision (multimodal)
    - Tool calling
    
    Requires:
    - API key from Google Cloud
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        
        # Update config with defaults
        if not self.config.endpoint:
            self.config.endpoint = "https://generativelanguage.googleapis.com/v1beta"
        if not self.config.supports_streaming:
            self.config.supports_streaming = True
        if not self.config.supports_vision:
            self.config.supports_vision = True
        if not self.config.supports_tool_calling:
            self.config.supports_tool_calling = True
        if not self.config.supports_function_calling:
            self.config.supports_function_calling = True

    def connect(self) -> bool:
        """Connect to Gemini API (validates API key)."""
        try:
            self._update_status(ProviderStatus.CONNECTING)
            
            if not self.config.api_key:
                self._update_status(ProviderStatus.ERROR, "API key not configured")
                return False
            
            # Test connection by listing models
            models = self.refresh_models()
            
            if models:
                self._set_connected()
                self.logger.info("Connected to Gemini API")
                return True
            else:
                self._update_status(ProviderStatus.ERROR, "No models available")
                return False
                
        except urllib.error.HTTPError as e:
            if e.code == 403:
                self._update_status(ProviderStatus.ERROR, "Invalid API key or insufficient permissions")
            elif e.code == 429:
                self._update_status(ProviderStatus.ERROR, "API quota exceeded")
            else:
                self._update_status(ProviderStatus.ERROR, f"HTTP {e.code}")
            self.logger.error(f"Gemini connection failed: {e}")
            return False
        except Exception as e:
            self._update_status(ProviderStatus.ERROR, str(e))
            self.logger.error(f"Unexpected error connecting to Gemini: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from Gemini API."""
        self._update_status(ProviderStatus.DISCONNECTED)
        self.logger.info("Disconnected from Gemini API")

    def generate_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response from Gemini."""
        model = self._get_model_id(model_id)
        
        url = f"{self.config.endpoint}/models/{model}:generateContent?key={self.config.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
        }
        
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }
        
        # Add any additional kwargs
        payload.update(kwargs)
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                # Extract text from response
                candidates = result.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
                
                return ""
                
        except Exception as e:
            self.logger.error(f"Gemini generation failed: {e}")
            raise

    def stream_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        on_chunk: Optional[callable] = None,
        **kwargs
    ) -> str:
        """Stream a response from Gemini."""
        model = self._get_model_id(model_id)
        
        url = f"{self.config.endpoint}/models/{model}:streamGenerateContent?key={self.config.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "stream": True,
        }
        
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }
        
        payload.update(kwargs)
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        full_response = ""
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                for line in response:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith("data:"):
                            try:
                                chunk = json.loads(line_str[5:])
                                candidates = chunk.get("candidates", [])
                                if candidates:
                                    content = candidates[0].get("content", {})
                                    parts = content.get("parts", [])
                                    if parts:
                                        text = parts[0].get("text", "")
                                        full_response += text
                                        
                                        if on_chunk:
                                            on_chunk(text)
                                
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            self.logger.error(f"Gemini streaming failed: {e}")
            raise
        
        return full_response

    def refresh_models(self) -> List[Dict[str, Any]]:
        """Refresh available models from Gemini API."""
        url = f"{self.config.endpoint}/models?key={self.config.api_key}"
        request = urllib.request.Request(url)
        request.add_header("User-Agent", "OwnCode/0.4")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                models = result.get("models", [])
                parsed_models = []
                
                for model in models:
                    model_info = {
                        "id": model.get("name", "").replace("models/", ""),
                        "name": model.get("displayName", ""),
                        "context_window": self._parse_context_window(model),
                        "max_output_tokens": self._parse_max_output(model),
                        "supports_vision": self._supports_vision(model),
                        "supports_tool_calling": self._supports_tool_calling(model),
                        "capabilities": self._extract_capabilities(model),
                    }
                    parsed_models.append(model_info)
                
                return parsed_models
                
        except Exception as e:
            self.logger.error(f"Failed to refresh Gemini models: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────────────────────────────

    def _set_connected(self) -> None:
        """Set provider to connected status."""
        self._update_status(ProviderStatus.CONNECTED)

    def _parse_context_window(self, model: Dict[str, Any]) -> int:
        """Parse context window from model info."""
        params = model.get("supportedGenerationMethods", {})
        return int(params.get("promptTokenCount", 32000))

    def _parse_max_output(self, model: Dict[str, Any]) -> int:
        """Parse max output tokens from model info."""
        params = model.get("supportedGenerationMethods", {})
        return int(params.get("maxTokenCount", 8192))

    def _supports_vision(self, model: Dict[str, Any]) -> bool:
        """Check if model supports vision."""
        methods = model.get("supportedGenerationMethods", {})
        return "uploadContent" in methods or "multimodal" in str(model.get("metadata", {}))

    def _supports_tool_calling(self, model: Dict[str, Any]) -> bool:
        """Check if model supports tool calling."""
        methods = model.get("supportedGenerationMethods", {})
        return "executableCode" in methods or "generateContent" in str(model.get("metadata", {}))

    def _extract_capabilities(self, model: Dict[str, Any]) -> List[str]:
        """Extract model capabilities."""
        capabilities = []
        
        if self._supports_vision(model):
            capabilities.append("vision")
        if self._supports_tool_calling(model):
            capabilities.append("tool_calling")
        
        return capabilities


# ============================================================================
# SECTION: ai.providers.groq_provider (ai/providers/groq_provider.py)
# ============================================================================
"""
Groq Provider.

Groq cloud API provider (using OpenAI-compatible interface).
"""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from core.logger import setup_logger

from ai.providers.base_provider import BaseProvider, ProviderConfig, ProviderStatus


logger = setup_logger(__name__)


class GroqProvider(BaseProvider):
    """
    Provider implementation for Groq API.
    
    Groq provides fast inference using their LPU (Liquid Processing Unit) hardware.
    Supports OpenAI-compatible API format.
    
    Requires:
    - API key from Groq
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        
        # Update config with defaults
        if not self.config.endpoint:
            self.config.endpoint = "https://api.groq.com/openai/v1"
        if not self.config.supports_streaming:
            self.config.supports_streaming = True
        if not self.config.supports_tool_calling:
            self.config.supports_tool_calling = True

    def connect(self) -> bool:
        """Connect to Groq API (validates API key)."""
        try:
            self._update_status(ProviderStatus.CONNECTING)
            
            if not self.config.api_key:
                self._update_status(ProviderStatus.ERROR, "API key not configured")
                return False
            
            # Test connection by listing models
            models = self.refresh_models()
            
            if models:
                self._set_connected()
                self.logger.info("Connected to Groq API")
                return True
            else:
                self._update_status(ProviderStatus.ERROR, "No models available")
                return False
                
        except urllib.error.HTTPError as e:
            if e.code == 401:
                self._update_status(ProviderStatus.ERROR, "Invalid API key")
            elif e.code == 403:
                self._update_status(ProviderStatus.ERROR, "API key lacks required permissions")
            else:
                self._update_status(ProviderStatus.ERROR, f"HTTP {e.code}")
            self.logger.error(f"Groq connection failed: {e}")
            return False
        except Exception as e:
            self._update_status(ProviderStatus.ERROR, str(e))
            self.logger.error(f"Unexpected error connecting to Groq: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from Groq API."""
        self._update_status(ProviderStatus.DISCONNECTED)
        self.logger.info("Disconnected from Groq API")

    def generate_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response from Groq."""
        model = self._get_model_id(model_id)
        
        url = f"{self.config.endpoint}/chat/completions"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        
        if system_prompt:
            payload["messages"].insert(0, {"role": "system", "content": system_prompt})
        
        payload.update(kwargs)
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", f"Bearer {self.config.api_key}")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                choices = result.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    return message.get("content", "")
                
                return ""
                
        except Exception as e:
            self.logger.error(f"Groq generation failed: {e}")
            raise

    def stream_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        on_chunk: Optional[callable] = None,
        **kwargs
    ) -> str:
        """Stream a response from Groq."""
        model = self._get_model_id(model_id)
        
        url = f"{self.config.endpoint}/chat/completions"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        
        if system_prompt:
            payload["messages"].insert(0, {"role": "system", "content": system_prompt})
        
        payload.update(kwargs)
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", f"Bearer {self.config.api_key}")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        full_response = ""
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                for line in response:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith("data:"):
                            try:
                                chunk = json.loads(line_str[5:])
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    full_response += content
                                    
                                    if on_chunk:
                                        on_chunk(content)
                                
                                if chunk.get("choices", [{}])[0].get("finish_reason") == "stop":
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            self.logger.error(f"Groq streaming failed: {e}")
            raise
        
        return full_response

    def refresh_models(self) -> List[Dict[str, Any]]:
        """Refresh available models from Groq API."""
        url = f"{self.config.endpoint}/models"
        
        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {self.config.api_key}")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                models = result.get("data", [])
                parsed_models = []
                
                for model in models:
                    model_info = {
                        "id": model.get("id", ""),
                        "name": model.get("id", "").replace("llama3-", "Llama 3 "),
                        "context_window": self._get_context_window(model.get("id", "")),
                        "max_output_tokens": 8192,
                        "supports_streaming": True,
                        "supports_tool_calling": "tool" in model.get("id", "").lower(),
                        "capabilities": self._extract_capabilities(model.get("id", "")),
                    }
                    parsed_models.append(model_info)
                
                return parsed_models
                
        except Exception as e:
            self.logger.error(f"Failed to refresh Groq models: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────────────────────────────

    def _set_connected(self) -> None:
        """Set provider to connected status."""
        self._update_status(ProviderStatus.CONNECTED)

    def _get_context_window(self, model_id: str) -> int:
        """Get context window for a model."""
        if "llama-3" in model_id or "llama3" in model_id:
            return 8192
        elif "mixtral" in model_id:
            return 32768
        elif "gemma" in model_id:
            return 8192
        return 4096

    def _extract_capabilities(self, model_id: str) -> List[str]:
        """Extract model capabilities."""
        capabilities = []
        
        if "tool" in model_id.lower():
            capabilities.append("tool_calling")
        
        return capabilities


# ============================================================================
# SECTION: ai.providers.cerebras_provider (ai/providers/cerebras_provider.py)
# ============================================================================
"""
Cerebras Provider.

Cerebras cloud API provider (using OpenAI-compatible interface).
"""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from core.logger import setup_logger

from ai.providers.base_provider import BaseProvider, ProviderConfig, ProviderStatus


logger = setup_logger(__name__)


class CerebrasProvider(BaseProvider):
    """
    Provider implementation for Cerebras API.
    
    Cerebras provides fast inference using their Cerebras GPT models.
    Supports OpenAI-compatible API format.
    
    Requires:
    - API key from Cerebras
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        
        # Update config with defaults
        if not self.config.endpoint:
            self.config.endpoint = "https://api.cerebras.ai/v1"
        if not self.config.supports_streaming:
            self.config.supports_streaming = True
        if not self.config.supports_tool_calling:
            self.config.supports_tool_calling = False

    def connect(self) -> bool:
        """Connect to Cerebras API (validates API key)."""
        try:
            self._update_status(ProviderStatus.CONNECTING)
            
            if not self.config.api_key:
                self._update_status(ProviderStatus.ERROR, "API key not configured")
                return False
            
            # Test connection by listing models
            models = self.refresh_models()
            
            if models:
                self._set_connected()
                self.logger.info("Connected to Cerebras API")
                return True
            else:
                self._update_status(ProviderStatus.ERROR, "No models available")
                return False
                
        except urllib.error.HTTPError as e:
            if e.code == 401:
                self._update_status(ProviderStatus.ERROR, "Invalid API key")
            elif e.code == 403:
                self._update_status(ProviderStatus.ERROR, "API key lacks required permissions")
            else:
                self._update_status(ProviderStatus.ERROR, f"HTTP {e.code}")
            self.logger.error(f"Cerebras connection failed: {e}")
            return False
        except Exception as e:
            self._update_status(ProviderStatus.ERROR, str(e))
            self.logger.error(f"Unexpected error connecting to Cerebras: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from Cerebras API."""
        self._update_status(ProviderStatus.DISCONNECTED)
        self.logger.info("Disconnected from Cerebras API")

    def generate_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response from Cerebras."""
        model = self._get_model_id(model_id)
        
        url = f"{self.config.endpoint}/chat/completions"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        
        if system_prompt:
            payload["messages"].insert(0, {"role": "system", "content": system_prompt})
        
        payload.update(kwargs)
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", f"Bearer {self.config.api_key}")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                choices = result.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    return message.get("content", "")
                
                return ""
                
        except Exception as e:
            self.logger.error(f"Cerebras generation failed: {e}")
            raise

    def stream_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        on_chunk: Optional[callable] = None,
        **kwargs
    ) -> str:
        """Stream a response from Cerebras."""
        model = self._get_model_id(model_id)
        
        url = f"{self.config.endpoint}/chat/completions"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        
        if system_prompt:
            payload["messages"].insert(0, {"role": "system", "content": system_prompt})
        
        payload.update(kwargs)
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", f"Bearer {self.config.api_key}")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        full_response = ""
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                for line in response:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith("data:"):
                            try:
                                chunk = json.loads(line_str[5:])
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    full_response += content
                                    
                                    if on_chunk:
                                        on_chunk(content)
                                
                                if chunk.get("choices", [{}])[0].get("finish_reason") == "stop":
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            self.logger.error(f"Cerebras streaming failed: {e}")
            raise
        
        return full_response

    def refresh_models(self) -> List[Dict[str, Any]]:
        """Refresh available models from Cerebras API."""
        url = f"{self.config.endpoint}/models"
        
        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {self.config.api_key}")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                models = result.get("data", [])
                parsed_models = []
                
                for model in models:
                    model_info = {
                        "id": model.get("id", ""),
                        "name": model.get("id", "").replace("cerebras-", "Cerebras "),
                        "context_window": self._get_context_window(model.get("id", "")),
                        "max_output_tokens": 8192,
                        "supports_streaming": True,
                        "supports_tool_calling": False,
                        "capabilities": [],
                    }
                    parsed_models.append(model_info)
                
                return parsed_models
                
        except Exception as e:
            self.logger.error(f"Failed to refresh Cerebras models: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────────────────────────────

    def _set_connected(self) -> None:
        """Set provider to connected status."""
        self._update_status(ProviderStatus.CONNECTED)

    def _get_context_window(self, model_id: str) -> int:
        """Get context window for a model."""
        if "llama3" in model_id:
            return 8192
        elif "mixtral" in model_id:
            return 32768
        return 4096


# ============================================================================
# SECTION: ai.providers.deepinfra_provider (ai/providers/deepinfra_provider.py)
# ============================================================================
"""
DeepInfra Provider.

DeepInfra cloud API provider (using OpenAI-compatible interface).
"""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from core.logger import setup_logger

from ai.providers.base_provider import BaseProvider, ProviderConfig, ProviderStatus


logger = setup_logger(__name__)


class DeepInfraProvider(BaseProvider):
    """
    Provider implementation for DeepInfra API.
    
    DeepInfra provides fast inference for various open models.
    Supports OpenAI-compatible API format.
    
    Requires:
    - API key from DeepInfra
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        
        # Update config with defaults
        if not self.config.endpoint:
            self.config.endpoint = "https://api.deepinfra.com/v1/openai"
        if not self.config.supports_streaming:
            self.config.supports_streaming = True
        if not self.config.supports_tool_calling:
            self.config.supports_tool_calling = False

    def connect(self) -> bool:
        """Connect to DeepInfra API (validates API key)."""
        try:
            self._update_status(ProviderStatus.CONNECTING)
            
            if not self.config.api_key:
                self._update_status(ProviderStatus.ERROR, "API key not configured")
                return False
            
            # Test connection by listing models
            models = self.refresh_models()
            
            if models:
                self._set_connected()
                self.logger.info("Connected to DeepInfra API")
                return True
            else:
                self._update_status(ProviderStatus.ERROR, "No models available")
                return False
                
        except urllib.error.HTTPError as e:
            if e.code == 401:
                self._update_status(ProviderStatus.ERROR, "Invalid API key")
            elif e.code == 403:
                self._update_status(ProviderStatus.ERROR, "API key lacks required permissions")
            else:
                self._update_status(ProviderStatus.ERROR, f"HTTP {e.code}")
            self.logger.error(f"DeepInfra connection failed: {e}")
            return False
        except Exception as e:
            self._update_status(ProviderStatus.ERROR, str(e))
            self.logger.error(f"Unexpected error connecting to DeepInfra: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from DeepInfra API."""
        self._update_status(ProviderStatus.DISCONNECTED)
        self.logger.info("Disconnected from DeepInfra API")

    def generate_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response from DeepInfra."""
        model = self._get_model_id(model_id)
        
        url = f"{self.config.endpoint}/chat/completions"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        
        if system_prompt:
            payload["messages"].insert(0, {"role": "system", "content": system_prompt})
        
        payload.update(kwargs)
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", f"Bearer {self.config.api_key}")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                choices = result.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    return message.get("content", "")
                
                return ""
                
        except Exception as e:
            self.logger.error(f"DeepInfra generation failed: {e}")
            raise

    def stream_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        on_chunk: Optional[callable] = None,
        **kwargs
    ) -> str:
        """Stream a response from DeepInfra."""
        model = self._get_model_id(model_id)
        
        url = f"{self.config.endpoint}/chat/completions"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        
        if system_prompt:
            payload["messages"].insert(0, {"role": "system", "content": system_prompt})
        
        payload.update(kwargs)
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", f"Bearer {self.config.api_key}")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        full_response = ""
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                for line in response:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith("data:"):
                            try:
                                chunk = json.loads(line_str[5:])
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    full_response += content
                                    
                                    if on_chunk:
                                        on_chunk(content)
                                
                                if chunk.get("choices", [{}])[0].get("finish_reason") == "stop":
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            self.logger.error(f"DeepInfra streaming failed: {e}")
            raise
        
        return full_response

    def refresh_models(self) -> List[Dict[str, Any]]:
        """Refresh available models from DeepInfra API."""
        url = f"{self.config.endpoint}/models"
        
        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {self.config.api_key}")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                models = result.get("data", [])
                parsed_models = []
                
                for model in models:
                    model_info = {
                        "id": model.get("id", ""),
                        "name": model.get("id", ""),
                        "context_window": self._get_context_window(model.get("id", "")),
                        "max_output_tokens": 4096,
                        "supports_streaming": True,
                        "supports_tool_calling": False,
                        "capabilities": [],
                    }
                    parsed_models.append(model_info)
                
                return parsed_models
                
        except Exception as e:
            self.logger.error(f"Failed to refresh DeepInfra models: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────────────────────────────

    def _set_connected(self) -> None:
        """Set provider to connected status."""
        self._update_status(ProviderStatus.CONNECTED)

    def _get_context_window(self, model_id: str) -> int:
        """Get context window for a model."""
        if "llama-3" in model_id:
            return 8192
        elif "mistral" in model_id:
            return 32768
        elif "mixtral" in model_id:
            return 32768
        elif "gemma" in model_id:
            return 8192
        return 4096


# ============================================================================
# SECTION: ai.providers.fireworks_provider (ai/providers/fireworks_provider.py)
# ============================================================================
"""
Fireworks Provider.

Fireworks AI cloud API provider (using OpenAI-compatible interface).
"""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from core.logger import setup_logger

from ai.providers.base_provider import BaseProvider, ProviderConfig, ProviderStatus


logger = setup_logger(__name__)


class FireworksProvider(BaseProvider):
    """
    Provider implementation for Fireworks AI API.
    
    Fireworks provides fast inference for various open models.
    Supports OpenAI-compatible API format.
    
    Requires:
    - API key from Fireworks
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        
        # Update config with defaults
        if not self.config.endpoint:
            self.config.endpoint = "https://api.fireworks.ai/inference/v1"
        if not self.config.supports_streaming:
            self.config.supports_streaming = True
        if not self.config.supports_tool_calling:
            self.config.supports_tool_calling = True

    def connect(self) -> bool:
        """Connect to Fireworks API (validates API key)."""
        try:
            self._update_status(ProviderStatus.CONNECTING)
            
            if not self.config.api_key:
                self._update_status(ProviderStatus.ERROR, "API key not configured")
                return False
            
            # Test connection by listing models
            models = self.refresh_models()
            
            if models:
                self._set_connected()
                self.logger.info("Connected to Fireworks API")
                return True
            else:
                self._update_status(ProviderStatus.ERROR, "No models available")
                return False
                
        except urllib.error.HTTPError as e:
            if e.code == 401:
                self._update_status(ProviderStatus.ERROR, "Invalid API key")
            elif e.code == 403:
                self._update_status(ProviderStatus.ERROR, "API key lacks required permissions")
            else:
                self._update_status(ProviderStatus.ERROR, f"HTTP {e.code}")
            self.logger.error(f"Fireworks connection failed: {e}")
            return False
        except Exception as e:
            self._update_status(ProviderStatus.ERROR, str(e))
            self.logger.error(f"Unexpected error connecting to Fireworks: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from Fireworks API."""
        self._update_status(ProviderStatus.DISCONNECTED)
        self.logger.info("Disconnected from Fireworks API")

    def generate_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response from Fireworks."""
        model = self._get_model_id(model_id)
        
        url = f"{self.config.endpoint}/chat/completions"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        
        if system_prompt:
            payload["messages"].insert(0, {"role": "system", "content": system_prompt})
        
        payload.update(kwargs)
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", f"Bearer {self.config.api_key}")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                choices = result.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    return message.get("content", "")
                
                return ""
                
        except Exception as e:
            self.logger.error(f"Fireworks generation failed: {e}")
            raise

    def stream_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        on_chunk: Optional[callable] = None,
        **kwargs
    ) -> str:
        """Stream a response from Fireworks."""
        model = self._get_model_id(model_id)
        
        url = f"{self.config.endpoint}/chat/completions"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        
        if system_prompt:
            payload["messages"].insert(0, {"role": "system", "content": system_prompt})
        
        payload.update(kwargs)
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", f"Bearer {self.config.api_key}")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        full_response = ""
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                for line in response:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith("data:"):
                            try:
                                chunk = json.loads(line_str[5:])
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    full_response += content
                                    
                                    if on_chunk:
                                        on_chunk(content)
                                
                                if chunk.get("choices", [{}])[0].get("finish_reason") == "stop":
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            self.logger.error(f"Fireworks streaming failed: {e}")
            raise
        
        return full_response

    def refresh_models(self) -> List[Dict[str, Any]]:
        """Refresh available models from Fireworks API."""
        url = f"{self.config.endpoint}/models"
        
        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {self.config.api_key}")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                models = result.get("data", [])
                parsed_models = []
                
                for model in models:
                    model_info = {
                        "id": model.get("id", ""),
                        "name": model.get("id", "").replace("accounts/fireworks/models/", ""),
                        "context_window": self._get_context_window(model.get("id", "")),
                        "max_output_tokens": 4096,
                        "supports_streaming": True,
                        "supports_tool_calling": "firefunction" in model.get("id", "").lower(),
                        "capabilities": self._extract_capabilities(model.get("id", "")),
                    }
                    parsed_models.append(model_info)
                
                return parsed_models
                
        except Exception as e:
            self.logger.error(f"Failed to refresh Fireworks models: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────────────────────────────

    def _set_connected(self) -> None:
        """Set provider to connected status."""
        self._update_status(ProviderStatus.CONNECTED)

    def _get_context_window(self, model_id: str) -> int:
        """Get context window for a model."""
        if "llama-3" in model_id:
            return 8192
        elif "mixtral" in model_id:
            return 32768
        elif "nemotron" in model_id:
            return 8192
        return 4096

    def _extract_capabilities(self, model_id: str) -> List[str]:
        """Extract model capabilities."""
        capabilities = []
        
        if "firefunction" in model_id.lower():
            capabilities.append("tool_calling")
        
        return capabilities


# ============================================================================
# SECTION: ai.providers.together_provider (ai/providers/together_provider.py)
# ============================================================================
"""
Together Provider.

Together AI cloud API provider (using OpenAI-compatible interface).
"""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from core.logger import setup_logger

from ai.providers.base_provider import BaseProvider, ProviderConfig, ProviderStatus


logger = setup_logger(__name__)


class TogetherProvider(BaseProvider):
    """
    Provider implementation for Together AI API.
    
    Together provides fast inference for various open models.
    Supports OpenAI-compatible API format.
    
    Requires:
    - API key from Together
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        
        # Update config with defaults
        if not self.config.endpoint:
            self.config.endpoint = "https://api.together.xyz/v1"
        if not self.config.supports_streaming:
            self.config.supports_streaming = True
        if not self.config.supports_tool_calling:
            self.config.supports_tool_calling = True

    def connect(self) -> bool:
        """Connect to Together API (validates API key)."""
        try:
            self._update_status(ProviderStatus.CONNECTING)
            
            if not self.config.api_key:
                self._update_status(ProviderStatus.ERROR, "API key not configured")
                return False
            
            # Test connection by listing models
            models = self.refresh_models()
            
            if models:
                self._set_connected()
                self.logger.info("Connected to Together API")
                return True
            else:
                self._update_status(ProviderStatus.ERROR, "No models available")
                return False
                
        except urllib.error.HTTPError as e:
            if e.code == 401:
                self._update_status(ProviderStatus.ERROR, "Invalid API key")
            elif e.code == 403:
                self._update_status(ProviderStatus.ERROR, "API key lacks required permissions")
            else:
                self._update_status(ProviderStatus.ERROR, f"HTTP {e.code}")
            self.logger.error(f"Together connection failed: {e}")
            return False
        except Exception as e:
            self._update_status(ProviderStatus.ERROR, str(e))
            self.logger.error(f"Unexpected error connecting to Together: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from Together API."""
        self._update_status(ProviderStatus.DISCONNECTED)
        self.logger.info("Disconnected from Together API")

    def generate_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response from Together."""
        model = self._get_model_id(model_id)
        
        url = f"{self.config.endpoint}/chat/completions"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        
        if system_prompt:
            payload["messages"].insert(0, {"role": "system", "content": system_prompt})
        
        payload.update(kwargs)
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", f"Bearer {self.config.api_key}")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                choices = result.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    return message.get("content", "")
                
                return ""
                
        except Exception as e:
            self.logger.error(f"Together generation failed: {e}")
            raise

    def stream_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        on_chunk: Optional[callable] = None,
        **kwargs
    ) -> str:
        """Stream a response from Together."""
        model = self._get_model_id(model_id)
        
        url = f"{self.config.endpoint}/chat/completions"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        
        if system_prompt:
            payload["messages"].insert(0, {"role": "system", "content": system_prompt})
        
        payload.update(kwargs)
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", f"Bearer {self.config.api_key}")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        full_response = ""
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                for line in response:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith("data:"):
                            try:
                                chunk = json.loads(line_str[5:])
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    full_response += content
                                    
                                    if on_chunk:
                                        on_chunk(content)
                                
                                if chunk.get("choices", [{}])[0].get("finish_reason") == "stop":
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            self.logger.error(f"Together streaming failed: {e}")
            raise
        
        return full_response

    def refresh_models(self) -> List[Dict[str, Any]]:
        """Refresh available models from Together API."""
        url = f"{self.config.endpoint}/models"
        
        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {self.config.api_key}")
        request.add_header("User-Agent", "OwnCode/0.4")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                models = result.get("data", [])
                parsed_models = []
                
                for model in models:
                    model_info = {
                        "id": model.get("id", ""),
                        "name": model.get("display_name", model.get("id", "")),
                        "context_window": self._get_context_window(model.get("id", "")),
                        "max_output_tokens": 4096,
                        "supports_streaming": True,
                        "supports_tool_calling": "tool" in model.get("id", "").lower(),
                        "capabilities": self._extract_capabilities(model.get("id", "")),
                    }
                    parsed_models.append(model_info)
                
                return parsed_models
                
        except Exception as e:
            self.logger.error(f"Failed to refresh Together models: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────────────────────────────

    def _set_connected(self) -> None:
        """Set provider to connected status."""
        self._update_status(ProviderStatus.CONNECTED)

    def _get_context_window(self, model_id: str) -> int:
        """Get context window for a model."""
        if "llama-3" in model_id:
            return 8192
        elif "mistral" in model_id:
            return 32768
        elif "mixtral" in model_id:
            return 32768
        return 4096

    def _extract_capabilities(self, model_id: str) -> List[str]:
        """Extract model capabilities."""
        capabilities = []
        
        if "tool" in model_id.lower():
            capabilities.append("tool_calling")
        
        return capabilities


# ============================================================================
# SECTION: ai.providers.custom_provider (ai/providers/custom_provider.py)
# ============================================================================
"""
Custom Provider.

Generic provider for any OpenAI-compatible API endpoint.
"""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from core.logger import setup_logger

from ai.providers.base_provider import BaseProvider, ProviderConfig, ProviderStatus, AuthenticationType


logger = setup_logger(__name__)


class CustomProvider(BaseProvider):
    """
    Generic provider for any OpenAI-compatible API endpoint.
    
    This provider can be used with:
    - Self-hosted OpenAI-compatible servers
    - Local LLM servers (vLLM, llama.cpp, etc.)
    - Any service implementing OpenAI API format
    
    Supports:
    - Text generation
    - Streaming responses
    - Configurable authentication
    
    Configuration:
    The provider is configured via JSON file with:
    - endpoint: API endpoint URL
    - auth_type: none, api_key, bearer_token, or custom
    - api_key: For API key authentication
    - headers: Additional headers to include
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        
        # Update config with defaults
        if not self.config.endpoint:
            self.config.endpoint = "http://localhost:8000/v1"
        if not self.config.supports_streaming:
            self.config.supports_streaming = True
        if not self.config.supports_tool_calling:
            self.config.supports_tool_calling = False

    def connect(self) -> bool:
        """Connect to custom API endpoint."""
        try:
            self._update_status(ProviderStatus.CONNECTING)
            
            # Test connection by listing models
            models = self.refresh_models()
            
            if models is not None:
                self._set_connected()
                self.logger.info(f"Connected to custom provider at {self.config.endpoint}")
                return True
            else:
                self._update_status(ProviderStatus.ERROR, "Failed to list models")
                return False
                
        except Exception as e:
            self._update_status(ProviderStatus.ERROR, str(e))
            self.logger.error(f"Failed to connect to custom provider: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from custom API endpoint."""
        self._update_status(ProviderStatus.DISCONNECTED)
        self.logger.info(f"Disconnected from custom provider at {self.config.endpoint}")

    def generate_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response from the custom endpoint."""
        model = self._get_model_id(model_id)
        
        url = f"{self.config.endpoint}/chat/completions"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        
        if system_prompt:
            payload["messages"].insert(0, {"role": "system", "content": system_prompt})
        
        payload.update(kwargs)
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        
        # Add authentication header
        if self.config.auth_type == AuthenticationType.API_KEY:
            request.add_header("Authorization", f"Bearer {self.config.api_key}")
        elif self.config.auth_type == AuthenticationType.BEARER_TOKEN:
            request.add_header("Authorization", f"Bearer {self.config.api_key}")
        
        request.add_header("User-Agent", "OwnCode/0.4")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                choices = result.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    return message.get("content", "")
                
                return ""
                
        except Exception as e:
            self.logger.error(f"Custom provider generation failed: {e}")
            raise

    def stream_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        on_chunk: Optional[callable] = None,
        **kwargs
    ) -> str:
        """Stream a response from the custom endpoint."""
        model = self._get_model_id(model_id)
        
        url = f"{self.config.endpoint}/chat/completions"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        
        if system_prompt:
            payload["messages"].insert(0, {"role": "system", "content": system_prompt})
        
        payload.update(kwargs)
        
        data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(url, data=data)
        request.add_header("Content-Type", "application/json")
        
        # Add authentication header
        if self.config.auth_type == AuthenticationType.API_KEY:
            request.add_header("Authorization", f"Bearer {self.config.api_key}")
        elif self.config.auth_type == AuthenticationType.BEARER_TOKEN:
            request.add_header("Authorization", f"Bearer {self.config.api_key}")
        
        request.add_header("User-Agent", "OwnCode/0.4")
        
        full_response = ""
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                for line in response:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith("data:"):
                            try:
                                chunk = json.loads(line_str[5:])
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    full_response += content
                                    
                                    if on_chunk:
                                        on_chunk(content)
                                
                                if chunk.get("choices", [{}])[0].get("finish_reason") == "stop":
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            self.logger.error(f"Custom provider streaming failed: {e}")
            raise
        
        return full_response

    def refresh_models(self) -> List[Dict[str, Any]]:
        """Refresh available models from the custom endpoint."""
        url = f"{self.config.endpoint}/models"
        
        request = urllib.request.Request(url)
        
        # Add authentication header
        if self.config.auth_type == AuthenticationType.API_KEY:
            request.add_header("Authorization", f"Bearer {self.config.api_key}")
        elif self.config.auth_type == AuthenticationType.BEARER_TOKEN:
            request.add_header("Authorization", f"Bearer {self.config.api_key}")
        
        request.add_header("User-Agent", "OwnCode/0.4")
        
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                models = result.get("data", [])
                parsed_models = []
                
                for model in models:
                    model_info = {
                        "id": model.get("id", ""),
                        "name": model.get("id", ""),
                        "context_window": self._get_context_window(model.get("id", "")),
                        "max_output_tokens": 4096,
                        "supports_streaming": True,
                        "supports_tool_calling": False,
                        "capabilities": [],
                    }
                    parsed_models.append(model_info)
                
                return parsed_models
                
        except Exception as e:
            self.logger.error(f"Failed to refresh custom provider models: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────────────────────────────

    def _set_connected(self) -> None:
        """Set provider to connected status."""
        self._update_status(ProviderStatus.CONNECTED)

    def _get_context_window(self, model_id: str) -> int:
        """Get context window for a model (generic estimate)."""
        return 4096

