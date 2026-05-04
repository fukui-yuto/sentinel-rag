"""Base interface for LLM and Embedding providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class EmbeddingResponse:
    embeddings: list[list[float]]
    model: str
    provider: str
    dimensions: int = 0


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    provider_name: str = ""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> LLMResponse:
        ...

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> AsyncGenerator[str, None]:
        ...


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    provider_name: str = ""

    @abstractmethod
    async def embed(
        self,
        texts: list[str],
        model: Optional[str] = None,
    ) -> EmbeddingResponse:
        ...
