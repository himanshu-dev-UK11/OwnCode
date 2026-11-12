# AI Provider Platform

## Overview

The AI Provider Platform is a provider-based architecture that allows unlimited local or cloud providers to be added without modifying the IDE core. The platform follows SOLID principles and provides a clean separation between the IDE and AI provider implementations.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AI Workspace (IDE)                              │
│                         ↓                                               │
│                    Provider Router                                      │
│                         ↓                                               │
│                    Provider Manager                                     │
│                         ↓                                               │
│                    Provider Registry                                    │
│                         ↓                                               │
│           ┌─────────────┬─────────────┬─────────────┐                   │
│           │ Provider    │ Provider    │ Provider    │                   │
│           │ Ollama      │ Gemini      │ OpenAI      │                   │
│           └─────────────┴─────────────┴─────────────┘                   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### BaseProvider (`ai/providers/base_provider.py`)

Abstract base class for all AI providers. Defines the contract that all providers must implement:

```python
class BaseProvider(ABC):
    @abstractmethod
    def connect(self) -> bool: ...
    
    @abstractmethod
    def disconnect(self) -> None: ...
    
    @abstractmethod
    def generate_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        **kwargs
    ) -> str: ...
    
    @abstractmethod
    def stream_response(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        on_chunk: Optional[callable] = None,
        **kwargs
    ) -> str: ...
    
    @abstractmethod
    def refresh_models(self) -> List[Dict[str, Any]]: ...
```

### ProviderConfig

Configuration for a provider instance:

```python
@dataclass
class ProviderConfig:
    provider_name: str
    endpoint: str
    auth_type: AuthenticationType  # none, api_key, bearer_token, oauth, custom
    api_key: Optional[str]
    enabled: bool
    priority: int  # Higher = preferred
    default_model: str
    timeout_seconds: int
    retry_count: int
    supports_streaming: bool
    supports_tool_calling: bool
    supports_vision: bool
    supports_function_calling: bool
```

### ProviderRegistry (`ai/providers/provider_registry.py`)

Central registry for managing all providers:

```python
class ProviderRegistry:
    def register_provider(self, provider: BaseProvider) -> None
    def load_all_providers(self) -> List[str]
    def get_provider(self, provider_name: str) -> Optional[BaseProvider]
    def enable_provider(self, provider_name: str) -> bool
    def disable_provider(self, provider_name: str) -> bool
    def refresh_all_models(self) -> Dict[str, List[str]]
    def test_all_connections(self) -> Dict[str, bool]
```

### ProviderManager (`ai/providers/provider_manager.py`)

Unified management interface for all provider operations:

```python
class ProviderManager:
    def enable_provider(self, provider_name: str) -> bool
    def disable_provider(self, provider_name: str) -> bool
    def validate_api_key(self, provider_name: str, api_key: str) -> bool
    def test_connection(self, provider_name: str) -> bool
    def refresh_models(self, provider_name: Optional[str] = None)
    def get_health_status(self) -> Dict[str, Dict[str, Any]]
    def monitor_health(self) -> None  # Background monitoring
```

### ProviderRouter (`ai/providers/provider_router.py`)

Routes requests to the appropriate provider:

```python
class ProviderRouter:
    def route_request(self, prompt: str, **kwargs) -> str
    def route_stream(
        self,
        prompt: str,
        on_chunk: callable,
        **kwargs
    ) -> str
    def select_provider(
        self,
        task: Optional[Task] = None,
        require_streaming: bool = False,
        require_vision: bool = False,
        require_tool_calling: bool = False,
        **kwargs
    ) -> Optional[BaseProvider]
```

### ProviderHealth (`ai/providers/provider_health.py`)

Tracks operational status and reliability of providers:

```python
class ProviderHealth:
    def record_request(
        self,
        provider_name: str,
        success: bool,
        latency_ms: float = 0.0,
        is_timeout: bool = False
    ) -> None
    
    def get_all_health(self) -> Dict[str, Dict[str, Any]]
    def get_unavailable_providers(self) -> List[str]
    def get_recommended_provider(self) -> Optional[str]
```

### ProviderDiscovery (`ai/providers/provider_discovery.py`)

Automatically detects available local providers:

```python
class ProviderDiscovery:
    def discover_all(self) -> Dict[str, Dict[str, Any]]
    def discover_ollama(self) -> Optional[Dict[str, Any]]
    def discover_lm_studio(self) -> Optional[Dict[str, Any]]
    def discover_llama_cpp(self) -> Optional[Dict[str, Any]]
    def discover_vllm(self) -> Optional[Dict[str, Any]]
```

## Provider Implementations

### Local Providers

- **Ollama** (`ollama_provider.py`) - Local LLM server
- **Custom** (`custom_provider.py`) - Generic OpenAI-compatible server

### Cloud Providers

- **Gemini** (`gemini_provider.py`) - Google Gemini API
- **OpenAI** (`openai_provider.py`) - OpenAI API
- **Anthropic** (`anthropic_provider.py`) - Claude API
- **Groq** (`groq_provider.py`) - Groq cloud API
- **Cerebras** (`cerebras_provider.py`) - Cerebras GPT API
- **Fireworks** (`fireworks_provider.py`) - Fireworks AI API
- **DeepInfra** (`deepinfra_provider.py`) - DeepInfra API
- **Together** (`together_provider.py`) - Together AI API

## Configuration

### Provider Configuration

Each provider has its own configuration file in `config/providers/`:

```json
{
    "provider_name": "ollama",
    "endpoint": "http://localhost:11434",
    "auth_type": "none",
    "enabled": true,
    "priority": 10,
    "default_model": "llama3:8b",
    "timeout_seconds": 30,
    "retry_count": 3,
    "supports_streaming": true,
    "supports_tool_calling": false,
    "supports_vision": false,
    "supports_function_calling": false
}
```

### Model Configuration

Each model has its own configuration file in `config/models/`:

```json
{
    "display_name": "Qwen 3 Coder",
    "provider": "qwen",
    "model_id": "qwen3-coder",
    "context_window": 32768,
    "max_output_tokens": 8192,
    "type": "local",
    "supports_streaming": true,
    "supports_tool_calling": true,
    "supports_vision": false,
    "supports_function_calling": true,
    "license": "Apache 2.0",
    "cost_type": "free",
    "priority": 10,
    "version": "3.0",
    "tags": ["coding", "local", "fast"]
}
```

## Adding a New Provider

1. Create a new provider class extending `BaseProvider`:
```python
from ai.providers.base_provider import BaseProvider, ProviderConfig

class MyProvider(BaseProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
    
    def connect(self) -> bool:
        # Implement connection logic
        pass
    
    def disconnect(self) -> None:
        # Implement disconnection logic
        pass
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        # Implement response generation
        pass
    
    def stream_response(self, prompt: str, on_chunk: callable, **kwargs) -> str:
        # Implement streaming
        pass
    
    def refresh_models(self) -> List[Dict[str, Any]]:
        # Implement model listing
        pass
```

2. Register the provider in `provider_factory.py`:
```python
from ai.providers.my_provider import MyProvider
ProviderFactory.register_provider("my_provider", MyProvider)
```

3. Create a configuration file `config/providers/my_provider.json`

4. Restart the application

## Request Flow

```
User Prompt
    ↓
ModelManager.execute_request()
    ↓
ProviderRouter.select_provider()
    ↓
ProviderRouter.route_request()
    ↓
Provider.generate_response()
    ↓
Provider Health Recording
    ↓
Response
```

## Health Monitoring

The provider manager runs background health monitoring:
- Checks provider availability every 60 seconds
- Automatically attempts reconnection
- Tracks success/failure rates
- Calculates availability scores

## Event System

Providers fire events for state changes:
- `provider_enabled` - Provider enabled
- `provider_disabled` - Provider disabled
- `provider_connected` - Provider connected
- `provider_disconnected` - Provider disconnected
- `provider_status_changed` - Status changed

## Best Practices

1. **Never hardcode provider details** - Always use the provider platform
2. **Use background threads** for network operations
3. **Implement proper error handling** in provider implementations
4. **Track health metrics** for reliable provider selection
5. **Support streaming** when possible
6. **Implement model refresh** for dynamic model discovery
7. **Use configuration files** for all provider settings
8. **Test connection before use** to provide early feedback

## Migration from Old Model System

The old model system (`ai/models/`) has been replaced by the provider platform. Key changes:

- `ModelManager` now uses `ProviderManager` and `ProviderRouter`
- `ModelRouter` replaced by `ProviderRouter`
- `ModelRegistry` works with `ProviderRegistry`
- Models are now loaded from providers dynamically

## References

- Base Provider Interface: `ai/providers/base_provider.py`
- Provider Factory: `ai/providers/provider_factory.py`
- Provider Registry: `ai/providers/provider_registry.py`
- Provider Manager: `ai/providers/provider_manager.py`
- Provider Router: `ai/providers/provider_router.py`
- Provider Health: `ai/providers/provider_health.py`
- Provider Discovery: `ai/providers/provider_discovery.py`


---

# Qwen3 8B Provider Integration

## Overview

The Qwen provider enables integration with Qwen3 8B, a state-of-the-art local coding model optimized for code generation, completion, and understanding.

## Architecture

```
┌─────────────────────┐
│   UI Layer          │
│  QwenCodingPanel    │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│   Model Layer       │
│    QwenModel        │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Provider Layer     │
│   QwenProvider      │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│   Local Server      │
│  LM Studio/Ollama   │
│   (Qwen3 8B Model)  │
└─────────────────────┘
```

## Components

### 1. QwenProvider (`ai/providers/qwen_provider.py`)

**Responsibilities**:
- Manage connection to local Qwen3 server
- Handle OpenAI-compatible API communication
- Support streaming and non-streaming responses
- Provide specialized coding methods

**Key Features**:
- OpenAI-compatible API support
- Streaming response support
- Model discovery and management
- Connection health monitoring
- Retry logic with exponential backoff

**API Methods**:
```python
# Basic generation
generate_response(prompt, model_id, system_prompt, **kwargs) -> str

# Streaming generation
stream_response(prompt, model_id, system_prompt, on_chunk, **kwargs) -> str

# Code-specific methods
generate_code(task, language, context, **kwargs) -> str
explain_code(code, language, **kwargs) -> str
debug_code(code, error, language, **kwargs) -> str
refactor_code(code, goal, language, **kwargs) -> str

# Model management
refresh_models() -> List[Dict[str, Any]]
connect() -> bool
disconnect() -> None
```

### 2. QwenModel (`ai/models/qwen.py`)

**Responsibilities**:
- High-level interface for Qwen operations
- Lazy loading of provider
- Error handling and logging
- Code completion support

**Key Features**:
- Simplified API for common tasks
- Automatic provider initialization
- Connection management
- Fallback handling

**API Methods**:
```python
# Core methods
generate_response(prompt, system_prompt, **kwargs) -> str
generate_code(task, language, context, **kwargs) -> str
explain_code(code, language, **kwargs) -> str
debug_code(code, error, language, **kwargs) -> str
refactor_code(code, goal, language, **kwargs) -> str
complete_code(prefix, suffix, language, **kwargs) -> str
```

### 3. QwenCodingPanel (`ui/ai_workspace/qwen_coding_panel.py`)

**Responsibilities**:
- User interface for Qwen operations
- Operation mode selection
- Connection management UI
- Background thread execution
- Result display

**Key Features**:
- 6 operation modes (Generate, Explain, Debug, Refactor, Complete, Custom)
- Real-time connection status
- Language selector
- Async execution with progress feedback
- Copy to clipboard support

## Configuration

### Provider Config (`config/providers/qwen.json`)

```json
{
  "provider_name": "qwen",
  "endpoint": "http://localhost:1234/v1",
  "auth_type": "none",
  "enabled": true,
  "priority": 15,
  "default_model": "qwen3-8b",
  "timeout_seconds": 120,
  "retry_count": 3,
  "supports_streaming": true,
  "supports_tool_calling": false,
  "supports_vision": false,
  "supports_function_calling": true
}
```

### Key Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `endpoint` | `http://localhost:1234/v1` | Local server API endpoint |
| `priority` | `15` | Provider priority (higher = preferred) |
| `timeout_seconds` | `120` | Request timeout |
| `default_model` | `qwen3-8b` | Default model to use |
| `supports_streaming` | `true` | Enable streaming responses |
| `supports_function_calling` | `true` | Enable function calling |

## Usage Examples

### Basic Code Generation

```python
from ai.models.qwen import QwenModel

qwen = QwenModel(endpoint="http://localhost:1234/v1")

# Generate a function
code = qwen.generate_code(
    task="Create a function to validate email addresses",
    language="python",
    context="This is for a user registration system"
)
print(code)
```

### Code Explanation

```python
code_snippet = """
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)
"""

explanation = qwen.explain_code(code_snippet, language="python")
print(explanation)
```

### Debugging

```python
buggy_code = """
def divide_numbers(a, b):
    return a / b
"""

error_msg = "ZeroDivisionError: division by zero"

solution = qwen.debug_code(
    code=buggy_code,
    error=error_msg,
    language="python"
)
print(solution)
```

### Code Refactoring

```python
old_code = """
def get_user(user_id):
    conn = sqlite3.connect('db.sqlite')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ' + str(user_id))
    result = cursor.fetchone()
    conn.close()
    return result
"""

improved = qwen.refactor_code(
    code=old_code,
    goal="add error handling, use context manager, prevent SQL injection",
    language="python"
)
print(improved)
```

### Streaming Response

```python
from ai.providers.qwen_provider import QwenProvider
from ai.providers.base_provider import ProviderConfig, AuthenticationType

config = ProviderConfig(
    provider_name="qwen",
    endpoint="http://localhost:1234/v1",
    auth_type=AuthenticationType.NONE,
    enabled=True,
    supports_streaming=True
)

provider = QwenProvider(config)
provider.connect()

def on_chunk(text):
    print(text, end='', flush=True)

response = provider.stream_response(
    prompt="Explain async/await in Python",
    on_chunk=on_chunk
)
```

## Integration Points

### 1. Provider Registry

The Qwen provider is automatically registered in `provider_factory.py`:

```python
from ai.providers.qwen_provider import QwenProvider
ProviderFactory.register_provider("qwen", QwenProvider)
```

### 2. Model Registry

Qwen models are discovered and registered automatically:

```python
# Models are registered from provider discovery
model_registry.register_model_from_provider("qwen", model_info)
```

### 3. AI Workspace Panel

The Qwen coding panel is integrated into the AI Workspace:

```python
from ui.ai_workspace.qwen_coding_panel import QwenCodingPanel

# In AI Workspace initialization
qwen_panel = QwenCodingPanel()
qwen_section = Section("Qwen3 Coding Assistant", qwen_panel)
workspace_layout.addWidget(qwen_section)
```

## Performance Optimization

### 1. Request Parameters

Adjust generation parameters for better performance:

```python
# Faster, more deterministic (good for code)
qwen.generate_code(
    task=task,
    language=language,
    temperature=0.3,      # Lower temperature
    max_tokens=2048,      # Limit output length
    top_p=0.9
)

# More creative (good for explanations)
qwen.explain_code(
    code=code,
    language=language,
    temperature=0.7,      # Higher temperature
    max_tokens=4096
)
```

### 2. Model Quantization

Use appropriate quantization level:
- **Q4_K_M**: Fast, good quality (recommended)
- **Q5_K_M**: Better quality, slightly slower
- **Q8_0**: Best quality, slowest

### 3. Context Management

Optimize context window usage:

```python
# For long files, provide relevant excerpt only
context = extract_relevant_context(full_file, max_tokens=2000)
code = qwen.generate_code(task, language, context=context)
```

## Error Handling

### Connection Errors

```python
from ai.models.qwen import QwenModel

try:
    qwen = QwenModel(endpoint="http://localhost:1234/v1")
    response = qwen.generate_response("Hello")
except ConnectionError as e:
    print(f"Failed to connect to Qwen server: {e}")
    # Fallback to another provider or show error to user
```

### Timeout Handling

```python
# Increase timeout for complex requests
qwen.generate_code(
    task=complex_task,
    language="python",
    timeout_seconds=180  # 3 minutes
)
```

### Graceful Degradation

```python
def generate_with_fallback(task, language):
    try:
        # Try Qwen first
        return qwen.generate_code(task, language)
    except Exception as e:
        logger.warning(f"Qwen failed, trying fallback: {e}")
        # Fallback to another provider
        return openai.generate_code(task, language)
```

## Testing

### Unit Tests

```python
import unittest
from ai.providers.qwen_provider import QwenProvider
from ai.providers.base_provider import ProviderConfig, AuthenticationType

class TestQwenProvider(unittest.TestCase):
    def setUp(self):
        config = ProviderConfig(
            provider_name="qwen",
            endpoint="http://localhost:1234/v1",
            auth_type=AuthenticationType.NONE
        )
        self.provider = QwenProvider(config)
    
    def test_connection(self):
        success = self.provider.connect()
        self.assertTrue(success)
    
    def test_generate_code(self):
        code = self.provider.generate_code(
            task="Create a hello world function",
            language="python"
        )
        self.assertIn("def", code)
        self.assertIn("hello", code.lower())
```

### Integration Tests

```python
def test_end_to_end_code_generation():
    # Initialize
    qwen = QwenModel()
    
    # Generate code
    code = qwen.generate_code(
        task="Create a function to calculate factorial",
        language="python"
    )
    
    # Verify code is executable
    exec_globals = {}
    exec(code, exec_globals)
    
    # Test generated function
    assert 'factorial' in exec_globals
    assert exec_globals['factorial'](5) == 120
```

## Monitoring and Logging

### Connection Health

```python
from ai.providers.provider_manager import ProviderManager

manager = ProviderManager(registry, event_bus)
health = manager.get_health_status()

qwen_health = health.get('qwen', {})
print(f"Status: {qwen_health.get('status')}")
print(f"Last tested: {qwen_health.get('last_tested')}")
print(f"Success rate: {qwen_health.get('success_rate')}")
```

### Request Logging

```python
# Enable debug logging
import logging
logging.getLogger('provider.qwen').setLevel(logging.DEBUG)

# Logs will include:
# - Connection attempts
# - Request/response data
# - Error details
# - Performance metrics
```

## Security Considerations

1. **Local Execution**: All processing happens locally
2. **No Data Leaks**: Code never leaves your machine
3. **Authentication**: Optional API key support for secured local servers
4. **Code Review**: Always review AI-generated code before use

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Connection refused" | Ensure local server (LM Studio/Ollama) is running |
| Slow responses | Reduce max_tokens, use lower quantization |
| Out of memory | Use Q4_K_M quantization, close other apps |
| Poor code quality | Lower temperature (0.3-0.5), provide more context |
| Timeout errors | Increase timeout_seconds in config |

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# This will log:
# - All API requests/responses
# - Connection status changes
# - Error stack traces
```

## Future Enhancements

- [ ] Function calling support
- [ ] Code execution sandbox
- [ ] Multi-file context support
- [ ] Code diff generation
- [ ] Test generation
- [ ] Documentation generation
- [ ] Code review suggestions
- [ ] Performance profiling
- [ ] Security vulnerability scanning

## Contributing

When contributing to the Qwen integration:

1. Follow existing code style
2. Add unit tests for new features
3. Update documentation
4. Test with multiple quantization levels
5. Consider backward compatibility

## License

This integration follows the same license as the main OwnCode IDE project.

## References

- [Qwen2.5-Coder Official Repo](https://github.com/QwenLM/Qwen2.5-Coder)
- [LM Studio Documentation](https://lmstudio.ai/docs)
- [Ollama Documentation](https://ollama.com/docs)
- [OpenAI API Compatibility](https://platform.openai.com/docs/api-reference)
