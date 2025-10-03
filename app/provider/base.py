"""Base provider interface for LLM API calls."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class Message:
    """Standard message format."""

    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class Usage:
    """Token usage tracking."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    usage_available: bool = True
    estimated: bool = False


@dataclass
class LLMResponse:
    """Standardized LLM response."""

    text: str
    usage: Usage
    request_id: str | None = None
    latency_ms: float = 0.0
    raw_response: dict[str, Any] | None = None


class ProviderError(Exception):
    """Base exception for provider errors."""

    pass


class BaseProvider(ABC):
    """Base class for all LLM providers."""

    def __init__(self, api_key: str, model_id: str):
        self.api_key = api_key
        self.model_id = model_id

    @abstractmethod
    def generate(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        seed: int | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a completion from messages."""
        pass

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (4 chars ≈ 1 token)."""
        return len(text) // 4
