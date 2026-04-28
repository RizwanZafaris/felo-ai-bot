"""Multi-provider LLM adapter. Same async API for Anthropic, OpenAI, Gemini, DeepSeek."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional

from config import settings
from cost_model import calculate_cost


@dataclass
class CompletionResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    model: str = ""
    cost_usd: float = 0.0


class BaseProvider(ABC):
    name: str = ""

    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        system_prompt: str,
        model: str,
        stream: bool = False,
    ) -> CompletionResult | AsyncGenerator[str, None]: ...


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self) -> None:
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def complete(self, messages, system_prompt, model, stream=False):
        sys_block = [{
            "type": "text", "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }]
        if stream:
            return self._stream(messages, sys_block, model)
        resp = await self.client.messages.create(
            model=model, max_tokens=1024, system=sys_block, messages=messages,
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        u = resp.usage
        return CompletionResult(
            text=text,
            input_tokens=u.input_tokens,
            output_tokens=u.output_tokens,
            cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
            cache_write_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
            model=model,
            cost_usd=calculate_cost(
                model, u.input_tokens, u.output_tokens,
                getattr(u, "cache_creation_input_tokens", 0) or 0,
                getattr(u, "cache_read_input_tokens", 0) or 0,
            ),
        )

    async def _stream(self, messages, sys_block, model):
        async with self.client.messages.stream(
            model=model, max_tokens=1024, system=sys_block, messages=messages,
        ) as s:
            async for delta in s.text_stream:
                yield delta


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None) -> None:
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=api_key or settings.OPENAI_API_KEY,
            base_url=base_url,
        )

    async def complete(self, messages, system_prompt, model, stream=False):
        full = [{"role": "system", "content": system_prompt}, *messages]
        if stream:
            return self._stream(full, model)
        resp = await self.client.chat.completions.create(model=model, messages=full, max_tokens=1024)
        text = resp.choices[0].message.content or ""
        u = resp.usage
        return CompletionResult(
            text=text,
            input_tokens=u.prompt_tokens, output_tokens=u.completion_tokens,
            model=model,
            cost_usd=calculate_cost(model, u.prompt_tokens, u.completion_tokens),
        )

    async def _stream(self, full, model):
        s = await self.client.chat.completions.create(
            model=model, messages=full, max_tokens=1024, stream=True,
        )
        async for chunk in s:
            tok = chunk.choices[0].delta.content
            if tok:
                yield tok


class DeepSeekProvider(OpenAIProvider):
    name = "deepseek"

    def __init__(self) -> None:
        super().__init__(base_url="https://api.deepseek.com", api_key=settings.DEEPSEEK_API_KEY)


class GeminiProvider(BaseProvider):
    name = "gemini"

    def __init__(self) -> None:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.genai = genai

    async def complete(self, messages, system_prompt, model, stream=False):
        m = self.genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
        contents = [{"role": "user" if x["role"] == "user" else "model", "parts": [x["content"]]} for x in messages]
        if stream:
            return self._stream(m, contents)
        resp = await m.generate_content_async(contents)
        text = resp.text or ""
        u = getattr(resp, "usage_metadata", None)
        in_tok = getattr(u, "prompt_token_count", 0) if u else 0
        out_tok = getattr(u, "candidates_token_count", 0) if u else 0
        return CompletionResult(
            text=text, input_tokens=in_tok, output_tokens=out_tok, model=model,
            cost_usd=calculate_cost(model, in_tok, out_tok),
        )

    async def _stream(self, m, contents):
        resp = await m.generate_content_async(contents, stream=True)
        async for chunk in resp:
            if chunk.text:
                yield chunk.text


PROVIDER_REGISTRY: dict[str, type[BaseProvider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "deepseek": DeepSeekProvider,
}

_cache: dict[str, BaseProvider] = {}


def get_provider(provider_name: str) -> BaseProvider:
    if provider_name not in PROVIDER_REGISTRY:
        raise ValueError(f"Unknown provider: {provider_name}")
    if provider_name not in _cache:
        _cache[provider_name] = PROVIDER_REGISTRY[provider_name]()
    return _cache[provider_name]


AVAILABLE_MODELS = [
    {"provider": "anthropic", "model": "claude-sonnet-4-6"},
    {"provider": "anthropic", "model": "claude-haiku-4-5"},
    {"provider": "anthropic", "model": "claude-opus-4-7"},
    {"provider": "openai",    "model": "gpt-4o"},
    {"provider": "openai",    "model": "gpt-4o-mini"},
    {"provider": "gemini",    "model": "gemini-1.5-pro"},
    {"provider": "deepseek",  "model": "deepseek-chat"},
]
