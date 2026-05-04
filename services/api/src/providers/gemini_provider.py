"""Google Gemini LLM and Embedding provider."""

from collections.abc import AsyncGenerator
from typing import Optional

from src.providers.base import BaseEmbeddingProvider, BaseLLMProvider, EmbeddingResponse, LLMResponse


class GeminiProvider(BaseLLMProvider):
    provider_name = "google"

    def __init__(self, api_key: str, proxy_url: Optional[str] = None):
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self.genai = genai
        self.default_model = "gemini-1.5-pro"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> LLMResponse:
        model_name = model or self.default_model
        gen_model = self.genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt,
        )
        response = await gen_model.generate_content_async(
            prompt,
            generation_config=self.genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )
        return LLMResponse(
            content=response.text,
            model=model_name,
            provider=self.provider_name,
            input_tokens=response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
            output_tokens=response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
        )

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> AsyncGenerator[str, None]:
        model_name = model or self.default_model
        gen_model = self.genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt,
        )
        response = await gen_model.generate_content_async(
            prompt,
            generation_config=self.genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
            stream=True,
        )
        async for chunk in response:
            if chunk.text:
                yield chunk.text


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    provider_name = "google"

    def __init__(self, api_key: str, proxy_url: Optional[str] = None):
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self.genai = genai
        self.default_model = "models/text-embedding-004"

    async def embed(
        self,
        texts: list[str],
        model: Optional[str] = None,
    ) -> EmbeddingResponse:
        model_name = model or self.default_model
        result = self.genai.embed_content(
            model=model_name,
            content=texts,
        )
        embeddings = result["embedding"]
        if isinstance(embeddings[0], float):
            embeddings = [embeddings]
        dimensions = len(embeddings[0]) if embeddings else 0
        return EmbeddingResponse(
            embeddings=embeddings,
            model=model_name,
            provider=self.provider_name,
            dimensions=dimensions,
        )
