"""Google Gemini provider using native SDK."""

import time

import google.generativeai as genai

from .base import BaseProvider, LLMResponse, Message, ProviderError, Usage


class GoogleProvider(BaseProvider):
    """Google Gemini provider via Google AI SDK."""

    def __init__(self, api_key: str, model_id: str):
        super().__init__(api_key, model_id)
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_id)

    def generate(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        seed: int | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Call Google Gemini API.

        Note: Gemini combines system and user messages into a single prompt.
        We prepend the system message to the conversation.
        """
        start_time = time.time()

        try:
            # Combine system message with first user message for Gemini
            system_msg = next((m.content for m in messages if m.role == "system"), None)
            user_msgs = [m for m in messages if m.role != "system"]

            # Build conversation history for Gemini
            if system_msg and user_msgs:
                # Prepend system message to first user message
                first_user_content = f"{system_msg}\n\n{user_msgs[0].content}"
                history = [{"role": "user", "parts": [first_user_content]}]

                # Add remaining messages if any
                for msg in user_msgs[1:]:
                    role = "model" if msg.role == "assistant" else "user"
                    history.append({"role": role, "parts": [msg.content]})

                # Use chat mode if we have history
                if len(history) > 1:
                    chat = self.model.start_chat(history=history[:-1])
                    response = chat.send_message(
                        history[-1]["parts"][0],
                        generation_config=genai.types.GenerationConfig(
                            temperature=temperature,
                            max_output_tokens=max_tokens or 8192,
                        ),
                    )
                else:
                    # Single turn
                    response = self.model.generate_content(
                        first_user_content,
                        generation_config=genai.types.GenerationConfig(
                            temperature=temperature,
                            max_output_tokens=max_tokens or 8192,
                        ),
                    )
            else:
                # No system message, just use user messages
                content = "\n\n".join([m.content for m in user_msgs])
                response = self.model.generate_content(
                    content,
                    generation_config=genai.types.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens or 8192,
                    ),
                )

            latency_ms = (time.time() - start_time) * 1000

            # Extract text from response
            text = response.text if hasattr(response, "text") else ""

            # Build usage object - Gemini provides usage metadata
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = Usage(
                    prompt_tokens=response.usage_metadata.prompt_token_count,
                    completion_tokens=response.usage_metadata.candidates_token_count,
                    total_tokens=response.usage_metadata.total_token_count,
                    usage_available=True,
                    estimated=False,
                )
            else:
                # Fallback to estimation if usage not available
                prompt_content = system_msg or ""
                for m in user_msgs:
                    prompt_content += m.content
                prompt_tokens = self.estimate_tokens(prompt_content)
                completion_tokens = self.estimate_tokens(text)
                usage = Usage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    usage_available=False,
                    estimated=True,
                )

            return LLMResponse(
                text=text,
                usage=usage,
                request_id=f"gemini-{int(time.time() * 1000)}",
                latency_ms=latency_ms,
                raw_response=None,  # Gemini response object is not easily serializable
            )

        except Exception as e:
            raise ProviderError(f"Google Gemini API error: {str(e)}") from e
