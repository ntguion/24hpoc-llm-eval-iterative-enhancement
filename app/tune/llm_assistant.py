"""LLM-assisted prompt tuning (optional)."""

import json

from ..provider.base import BaseProvider, Message, ProviderError


def llm_suggest_changes(
    provider: BaseProvider,
    current_prompt: str,
    evaluations: list[dict],
) -> tuple[list[str], dict]:
    """Use an LLM to propose GENERIC prompt improvements based on evaluation patterns.

    Returns:
        (suggestions, metadata) where metadata includes usage/cost info
    """
    failure_summary = summarize_failures(evaluations)

    system_msg = """You are a prompt engineering expert. Your job is to improve prompts by identifying SYSTEMIC, GENERIC issues—not scenario-specific problems.

When analyzing evaluation failures:
- Look for PATTERNS across multiple evaluations
- Focus on STRUCTURAL weaknesses in the prompt itself
- Suggest changes that will help ALL future summaries, not just current examples

Output format: JSON object with:
{
  "suggestions": [
    {"type": "add", "text": "generic principle to add (e.g., 'Include verification details when present')"},
    {"type": "remove", "text": "text to remove from current prompt"},
    {"type": "replace", "old": "current text", "new": "improved text"}
  ],
  "rationale": "explanation focusing on WHY these generic improvements will help"
}

CRITICAL RULES:
- DO NOT suggest scenario-specific details (e.g., "include pharmacy name", "mention medication X")
- DO suggest generic patterns (e.g., "specify exact timeframes", "include verification details")
- Think: "What structural change prevents this TYPE of failure in ANY call?"
- Keep the prompt concise—remove redundant or overly specific rules
"""

    user_msg = f"""Current Summarization Prompt:
{current_prompt}

Evaluation Results Summary:
{failure_summary}

Analyze the PATTERN of failures. Propose 2-4 GENERIC improvements to the prompt structure.

Focus on:
1. Coverage: Are summaries missing categories of information systematically?
2. Actionability: Do summaries lack clear next steps in a consistent way?
3. Precision: Are summaries vague where they should be specific?
4. Redundancy: Can we simplify or consolidate existing rules?

Return ONLY generic, reusable improvements. Return JSON only, no markdown fences."""

    messages = [Message(role="system", content=system_msg), Message(role="user", content=user_msg)]

    try:
        response = provider.generate(messages, temperature=0.3, max_tokens=1024)

        # Parse response
        raw_text = response.text.strip()
        # Strip markdown fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        data = json.loads(raw_text)

        # Convert to diff-style strings
        suggestions = []
        for item in data.get("suggestions", []):
            item_type = item.get("type", "add")
            if item_type == "add":
                suggestions.append(f"+ {item.get('text', '')}")
            elif item_type == "remove":
                suggestions.append(f"- {item.get('text', '')}")
            elif item_type == "replace":
                suggestions.append(f"- {item.get('old', '')}")
                suggestions.append(f"+ {item.get('new', '')}")

        # Add rationale as plain text
        if data.get("rationale"):
            suggestions.append(f"\nRationale: {data['rationale']}")

        metadata = {
            "usage": (
                {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                }
                if response.usage
                else None
            ),
            "request_id": response.request_id,
            "latency_ms": response.latency_ms,
        }

        return suggestions, metadata

    except (ProviderError, json.JSONDecodeError, KeyError) as e:
        # Fall back to error message
        return [f"⚠️ LLM tuner error: {str(e)}"], {}


def summarize_failures(evaluations: list[dict]) -> str:
    """Summarize common failure patterns with dimension-level analysis."""
    failures = [e for e in evaluations if not e.get("overall_pass", True)]

    # Aggregate dimension scores across all evals
    dim_scores = {}
    dim_rationales = {}

    for eval in evaluations:
        for dim, score in eval.get("scores", {}).items():
            if dim not in dim_scores:
                dim_scores[dim] = []
                dim_rationales[dim] = []
            dim_scores[dim].append(score)

            # Collect rationales for low scores
            if score < 4.0:
                rationale = eval.get("rationales", {}).get(dim, "")
                if rationale:
                    dim_rationales[dim].append(f"{eval.get('call_id', 'unknown')}: {rationale}")

    # Build summary
    summary_lines = []

    if failures:
        summary_lines.append(f"Failed {len(failures)}/{len(evaluations)} evaluations")
    else:
        summary_lines.append(f"All {len(evaluations)} evaluations passed")

    summary_lines.append("\nDimension Performance:")
    for dim, scores in dim_scores.items():
        avg = sum(scores) / len(scores)
        min_score = min(scores)
        max_score = max(scores)
        fail_count = sum(1 for s in scores if s < 4.0)

        status = "✓" if avg >= 4.0 else "⚠️"
        summary_lines.append(f"  {status} {dim}: avg={avg:.1f} (range {min_score}-{max_score}, {fail_count} low)")

        # Add sample rationales for low-scoring dimensions
        if fail_count > 0 and dim_rationales.get(dim):
            for rationale in dim_rationales[dim][:2]:  # Show up to 2 examples
                summary_lines.append(f"     → {rationale}")

    # Hallucination flags
    hallucination_count = 0
    for e in evaluations:
        flags = e.get("hallucination_flags", [])
        if isinstance(flags, list):
            hallucination_count += len(flags)
        elif flags:  # If it's a bool and True
            hallucination_count += 1

    if hallucination_count > 0:
        summary_lines.append(f"\n⚠️ {hallucination_count} hallucination flags detected")

    return "\n".join(summary_lines)
