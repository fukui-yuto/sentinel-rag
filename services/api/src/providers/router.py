"""LLM Router: provider selection, fallback, sensitivity-based routing."""

from typing import Optional

import structlog

from src.core.config import settings
from src.providers.base import BaseEmbeddingProvider, BaseLLMProvider

logger = structlog.get_logger()

# Sensitivity-based LLM routing rules
SENSITIVITY_ALLOWED_PROVIDERS: dict[str, set[str]] = {
    "public": {"anthropic", "openai", "google", "ollama"},
    "internal": {"anthropic", "openai", "google", "ollama"},
    "confidential": {"ollama"},
    "restricted": {"ollama"},
}


def get_llm_provider(
    provider_name: Optional[str] = None,
    sensitivity: str = "internal",
) -> BaseLLMProvider:
    """Get an LLM provider instance, respecting sensitivity constraints."""
    name = provider_name or settings.default_llm_provider
    allowed = SENSITIVITY_ALLOWED_PROVIDERS.get(sensitivity, {"ollama"})

    if name not in allowed:
        logger.warning(
            "provider_blocked_by_sensitivity",
            requested=name,
            sensitivity=sensitivity,
            fallback="ollama",
        )
        name = "ollama"

    return _create_llm_provider(name)


def get_embedding_provider(
    provider_name: Optional[str] = None,
) -> BaseEmbeddingProvider:
    """Get an embedding provider instance."""
    name = provider_name or settings.default_embedding_provider
    return _create_embedding_provider(name)


def _create_llm_provider(name: str) -> BaseLLMProvider:
    proxy = settings.https_proxy or settings.http_proxy or None

    if name == "anthropic":
        from src.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(api_key=settings.anthropic_api_key, proxy_url=proxy)
    elif name == "openai":
        from src.providers.openai_provider import OpenAIProvider

        return OpenAIProvider(api_key=settings.openai_api_key, proxy_url=proxy)
    elif name == "google":
        from src.providers.gemini_provider import GeminiProvider

        return GeminiProvider(api_key=settings.google_api_key, proxy_url=proxy)
    elif name == "ollama":
        from src.providers.ollama_provider import OllamaProvider

        return OllamaProvider(base_url=settings.ollama_host)
    else:
        raise ValueError(f"Unknown LLM provider: {name}")


def _create_embedding_provider(name: str) -> BaseEmbeddingProvider:
    proxy = settings.https_proxy or settings.http_proxy or None

    if name == "openai":
        from src.providers.openai_provider import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(api_key=settings.openai_api_key, proxy_url=proxy)
    elif name == "google":
        from src.providers.gemini_provider import GeminiEmbeddingProvider

        return GeminiEmbeddingProvider(api_key=settings.google_api_key, proxy_url=proxy)
    elif name == "ollama":
        from src.providers.ollama_provider import OllamaEmbeddingProvider

        return OllamaEmbeddingProvider(base_url=settings.ollama_host)
    else:
        raise ValueError(f"Unknown embedding provider: {name}")
