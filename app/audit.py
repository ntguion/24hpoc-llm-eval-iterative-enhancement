"""Audit trail logger for LLM API calls."""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from .provider.base import LLMResponse, Message


class AuditLogger:
    """Log every LLM API call with usage and cost."""

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.calls_file = run_dir / "calls.jsonl"
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def log_call(
        self,
        phase: str,
        provider: str,
        model: str,
        messages: list[Message],
        response: LLMResponse | None,
        temperature: float,
        seed: int | None,
        cost_usd: float | None,
        status: str = "ok",
        error: str | None = None,
    ):
        """Append a call record to calls.jsonl."""
        messages_str = json.dumps([{"role": m.role, "content": m.content} for m in messages])
        messages_digest = hashlib.sha256(messages_str.encode()).hexdigest()
        response_digest = hashlib.sha256(response.text.encode()).hexdigest() if response else None

        record = {
            "ts": datetime.utcnow().isoformat(),
            "run_id": self.run_dir.name,
            "phase": phase,
            "provider": provider,
            "model": model,
            "temperature": temperature,
            "seed": seed,
            "request_id": response.request_id if response else None,
            "latency_ms": response.latency_ms if response else 0,
            "messages_digest_in": messages_digest,
            "response_digest_out": response_digest,
            "usage": (
                {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
                if response and response.usage
                else None
            ),
            "usage_available": response.usage.usage_available if response and response.usage else False,
            "estimated": response.usage.estimated if response and response.usage else False,
            "cost_usd": cost_usd,
            "status": status,
            "error": error,
        }

        with open(self.calls_file, "a") as f:
            f.write(json.dumps(record) + "\n")
