"""Test provider contract compliance."""

from app.provider.base import Message
from app.provider.mock import MockProvider


def test_mock_provider_returns_response():
    """Mock provider should return a valid LLMResponse."""
    provider = MockProvider()
    messages = [
        Message(role="system", content="You are helpful."),
        Message(role="user", content="Hello"),
    ]

    response = provider.generate(messages)

    assert response.text is not None
    assert response.usage is not None
    assert response.usage.prompt_tokens > 0
    assert response.usage.completion_tokens > 0
    assert response.usage.usage_available is True


def test_mock_provider_summarizer_response():
    """Mock provider should return JSON for summarizer requests."""
    provider = MockProvider()
    messages = [
        Message(role="system", content="Generate summary"),
        Message(role="user", content="transcript schema"),
    ]

    response = provider.generate(messages)

    import json

    data = json.loads(response.text)
    assert "call_id" in data


def test_mock_provider_judge_response():
    """Mock provider should return JSON for judge requests."""
    provider = MockProvider()
    messages = [
        Message(role="system", content="Evaluate"),
        Message(role="user", content="rubric evaluate"),
    ]

    response = provider.generate(messages)

    import json

    data = json.loads(response.text)
    assert "scores" in data
    assert "rationales" in data
