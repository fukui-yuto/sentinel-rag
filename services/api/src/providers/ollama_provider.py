"""Ollama local LLM and Embedding provider."""

import json
from collections.abc import AsyncGenerator
from typing import Optional

import httpx

from src.providers.base import BaseEmbeddingProvider, BaseLLMProvider, EmbeddingResponse, LLMResponse


class OllamaProvider(BaseLLMProvider):
    provider_name = "ollama"

    def __init__(self, base_url: str = "http://ollama:11434"):
        self.base_url = base_url.rstrip("/")
        self.default_model = "qwen2.5:3b"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> LLMResponse:
        model = model or self.default_model
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()

        return LLMResponse(
            content=data.get("response", ""),
            model=model,
            provider=self.provider_name,
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
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
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST", f"{self.base_url}/api/generate", json=payload
            ) as resp:
                async for line in resp.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if token := data.get("response"):
                            yield token


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    provider_name = "ollama"

    def __init__(self, base_url: str = "http://ollama:11434"):
        self.base_url = base_url.rstrip("/")
        self.default_model = "nomic-embed-text"

    async def embed(
        self,
        texts: list[str],
        model: Optional[str] = None,
    ) -> EmbeddingResponse:
        model = model or self.default_model
        embeddings = []

        async with httpx.AsyncClient(timeout=120) as client:
            for text in texts:
                resp = await client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": model, "input": text},
                )
                resp.raise_for_status()
                data = resp.json()
                embeddings.append(data["embeddings"][0])

        dimensions = len(embeddings[0]) if embeddings else 0
        return EmbeddingResponse(
            embeddings=embeddings,
            model=model,
            provider=self.provider_name,
            dimensions=dimensions,
        )
