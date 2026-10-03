"""Model-independent language model contracts."""

from .provider import (
    FakeLLMProvider,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    OllamaProvider,
    OllamaProviderError,
)

__all__ = [
    "FakeLLMProvider", "LLMProvider", "LLMRequest", "LLMResponse",
    "OllamaProvider", "OllamaProviderError",
]
