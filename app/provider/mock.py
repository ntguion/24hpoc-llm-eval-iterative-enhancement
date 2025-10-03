"""Mock provider for testing without real API calls."""

import json
import time

from .base import BaseProvider, LLMResponse, Message, Usage


class MockProvider(BaseProvider):
    """Mock provider that returns deterministic responses."""

    def __init__(self, api_key: str = "mock", model_id: str = "mock-model"):
        super().__init__(api_key, model_id)

    def generate(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        seed: int | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Return a mock response based on message content."""
        time.sleep(0.1)  # Simulate latency

        # Detect what kind of response is needed
        user_content = next((m.content for m in messages if m.role == "user"), "")
        system_content = next((m.content for m in messages if m.role == "system"), "")

        if "generate" in system_content.lower() or ("lob" in user_content.lower() and "metadata" in user_content.lower()):
            # Transcript generation request
            response_text = json.dumps(
                {
                    "call_id": "MOCK-001",
                    "lob": "Benefits",
                    "segments": [
                        {"t": "00:00", "speaker": "agent", "text": "Mock agent greeting"},
                        {"t": "00:05", "speaker": "caller", "text": "Mock member response"},
                        {"t": "00:10", "speaker": "agent", "text": "Mock agent follow-up"},
                    ],
                    "metadata": {"duration_s": 180},
                }
            )
        elif "schema" in user_content.lower() or "transcript" in user_content.lower():
            # Summarizer request
            response_text = json.dumps(
                {
                    "call_id": "MOCK-001",
                    "intent": "Mock intent",
                    "resolution": "Mock resolution",
                    "next_steps": "Mock next steps",
                }
            )
        elif "rubric" in user_content.lower() or "evaluate" in user_content.lower():
            # Judge request
            response_text = json.dumps(
                {
                    "scores": {
                        "coverage": 4,
                        "factuality": 5,
                        "actionability": 4,
                        "structure_brevity": 5,
                        "safety_compliance": 5,
                    },
                    "rationales": {
                        "coverage": "Mock coverage rationale",
                        "factuality": "Mock factuality rationale",
                        "actionability": "Mock actionability rationale",
                        "structure_brevity": "Mock structure rationale",
                        "safety_compliance": "Mock safety rationale",
                    },
                    "hallucination_flags": [],
                    "overall_pass": True,
                    "suggested_prompt_changes": [],
                }
            )
        else:
            # Generic response
            response_text = "Mock LLM response"

        # Estimate tokens
        prompt_tokens = sum(self.estimate_tokens(m.content) for m in messages)
        completion_tokens = self.estimate_tokens(response_text)

        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            usage_available=True,
            estimated=False,  # Mock provider returns "actuals"
        )

        return LLMResponse(
            text=response_text,
            usage=usage,
            request_id=f"mock-{int(time.time())}",
            latency_ms=100.0,
        )
