"""OpenAI LLM and Embedding provider."""

from collections.abc import AsyncGenerator
from typing import Optional

from src.providers.base import BaseEmbeddingProvider, BaseLLMProvider, EmbeddingResponse, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    provider_name = "openai"

    def __init__(self, api_key: str, proxy_url: Optional[str] = None):
        from openai import AsyncOpenAI

        kwargs = {"api_key": api_key}
        if proxy_url:
            import httpx

            kwargs["http_client"] = httpx.AsyncClient(proxy=proxy_url)
        self.client = AsyncOpenAI(**kwargs)
        self.default_model = "gpt-4o"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> LLMResponse:
        model = model or self.default_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        choice = response.choices[0]
        usage = response.usage
        return LLMResponse(
            content=choice.message.content or "",
            model=model,
            provider=self.provider_name,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> AsyncGenerator[str, None]:
        model = model or self.default_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    provider_name = "openai"

    def __init__(self, api_key: str, proxy_url: Optional[str] = None):
        from openai import AsyncOpenAI

        kwargs = {"api_key": api_key}
        if proxy_url:
            import httpx

            kwargs["http_client"] = httpx.AsyncClient(proxy=proxy_url)
        self.client = AsyncOpenAI(**kwargs)
        self.default_model = "text-embedding-3-small"

    async def embed(
        self,
        texts: list[str],
        model: Optional[str] = None,
    ) -> EmbeddingResponse:
        model = model or self.default_model
        response = await self.client.embeddings.create(model=model, input=texts)
        embeddings = [item.embedding for item in response.data]
        dimensions = len(embeddings[0]) if embeddings else 0
        return EmbeddingResponse(
            embeddings=embeddings,
            model=model,
            provider=self.provider_name,
            dimensions=dimensions,
        )
