"""Summary schema definition."""

from pydantic import BaseModel


class CallSummary(BaseModel):
    """Schema for call summaries."""

    call_id: str
    intent: str
    resolution: str
    next_steps: str | None = None
    sentiment: str | None = None

    @classmethod
    def schema_text(cls) -> str:
        """Return schema as text for prompting."""
        return """
{
  "call_id": "string (from transcript)",
  "intent": "string (caller's primary intent)",
  "resolution": "string (what was resolved or outcome)",
  "next_steps": "string or null (follow-up actions)",
  "sentiment": "string or null (overall tone: positive/neutral/negative)"
}
"""
