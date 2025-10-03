"""Heuristic-based prompt tuning suggestions."""


def suggest_prompt_changes(evaluations: list[dict]) -> list[str]:
    """Analyze failure modes and suggest prompt changes."""
    suggestions = []

    # Aggregate low-scoring dimensions
    dim_scores = {}
    for eval in evaluations:
        for dim, score in eval.get("scores", {}).items():
            if dim not in dim_scores:
                dim_scores[dim] = []
            dim_scores[dim].append(score)

    # Compute averages
    dim_avgs = {dim: sum(scores) / len(scores) for dim, scores in dim_scores.items()}

    # Heuristic rules
    if dim_avgs.get("coverage", 5) < 4.0:
        suggestions.append("+ Add explicit instruction: 'Capture caller intent, completed actions, and pending items.'")

    if dim_avgs.get("factuality", 5) < 4.0:
        suggestions.append("+ Add constraint: 'Do not infer or assume information not present in the transcript.'")
        suggestions.append("- Remove any language encouraging interpretation")

    if dim_avgs.get("structure_brevity", 5) < 4.0:
        suggestions.append("+ Add limit: 'Max 100 words' (currently 120)")
        suggestions.append("+ Add structure requirement: 'Use bullet points for next_steps'")

    if dim_avgs.get("actionability", 5) < 4.0:
        suggestions.append("+ Add requirement: 'Explicitly list any follow-up actions or deadlines.'")

    if dim_avgs.get("safety_compliance", 5) < 4.0:
        suggestions.append("+ Add safety instruction: 'Flag any compliance concerns or sensitive data mentions.'")

    return suggestions if suggestions else ["No changes recommended; all dimensions meet thresholds."]


def format_diff(suggestions: list[str]) -> str:
    """Format suggestions as a diff-style markdown."""
    diff_lines = ["# Prompt Tuning Suggestions\n"]

    for suggestion in suggestions:
        if suggestion.startswith("+"):
            diff_lines.append(f"<span style='color:green'>{suggestion}</span>")
        elif suggestion.startswith("-"):
            diff_lines.append(f"<span style='color:red'>{suggestion}</span>")
        else:
            diff_lines.append(suggestion)

    return "\n".join(diff_lines)
