"""OpenAI provider using native SDK."""

import time

from openai import OpenAI

from .base import BaseProvider, LLMResponse, Message, ProviderError, Usage


class OpenAIProvider(BaseProvider):
    """OpenAI provider via native SDK (chat.completions.create)."""

    def __init__(self, api_key: str, model_id: str):
        super().__init__(api_key, model_id)
        self.client = OpenAI(api_key=api_key)

    def generate(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        seed: int | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Call OpenAI chat.completions.create API."""
        start_time = time.time()

        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=temperature,
                seed=seed,
                max_tokens=max_tokens or 4096,
            )

            latency_ms = (time.time() - start_time) * 1000

            # Extract usage from response
            usage = Usage(
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
                usage_available=response.usage is not None,
                estimated=False,
            )

            return LLMResponse(
                text=response.choices[0].message.content or "",
                usage=usage,
                request_id=response.id,
                latency_ms=latency_ms,
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
            )

        except Exception as e:
            raise ProviderError(f"OpenAI API error: {str(e)}") from e
