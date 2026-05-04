"""Anthropic (Claude) LLM provider."""

from collections.abc import AsyncGenerator
from typing import Optional

from src.providers.base import BaseLLMProvider, LLMResponse


class AnthropicProvider(BaseLLMProvider):
    provider_name = "anthropic"

    def __init__(self, api_key: str, proxy_url: Optional[str] = None):
        import anthropic

        kwargs = {"api_key": api_key}
        if proxy_url:
            import httpx

            kwargs["http_client"] = httpx.AsyncClient(proxy=proxy_url)
        self.client = anthropic.AsyncAnthropic(**kwargs)
        self.default_model = "claude-sonnet-4-20250514"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> LLMResponse:
        model = model or self.default_model
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = await self.client.messages.create(**kwargs)
        return LLMResponse(
            content=response.content[0].text,
            model=model,
            provider=self.provider_name,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
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
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
