"""Anthropic provider using native SDK."""

import time

from anthropic import Anthropic

from .base import BaseProvider, LLMResponse, Message, ProviderError, Usage


class AnthropicProvider(BaseProvider):
    """Anthropic provider via native SDK."""

    def __init__(self, api_key: str, model_id: str):
        super().__init__(api_key, model_id)
        self.client = Anthropic(api_key=api_key)

    def generate(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        seed: int | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Call Anthropic Messages API.

        Note: Anthropic requires system message to be passed separately from conversation messages.
        """
        start_time = time.time()

        try:
            # Extract system message separately (Anthropic API requirement)
            system_msg = next((m.content for m in messages if m.role == "system"), None)

            # Convert remaining messages (must be user/assistant alternating)
            conversation_msgs = [
                {"role": m.role, "content": m.content}
                for m in messages
                if m.role != "system"
            ]

            # Call Anthropic API
            response = self.client.messages.create(
                model=self.model_id,
                max_tokens=max_tokens or 4096,
                temperature=temperature,
                system=system_msg if system_msg else "",
                messages=conversation_msgs,
            )

            latency_ms = (time.time() - start_time) * 1000

            # Extract text from response
            text = response.content[0].text if response.content else ""

            # Build usage object
            usage = Usage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                usage_available=True,
                estimated=False,
            )

            return LLMResponse(
                text=text,
                usage=usage,
                request_id=response.id,
                latency_ms=latency_ms,
                raw_response=(
                    response.model_dump() if hasattr(response, "model_dump") else None
                ),
            )

        except Exception as e:
            raise ProviderError(f"Anthropic API error: {str(e)}") from e
