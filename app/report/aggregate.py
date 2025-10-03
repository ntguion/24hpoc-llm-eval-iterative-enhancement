"""Report aggregation and markdown generation."""

import json
from pathlib import Path


def generate_report(
    evaluations: list[dict],
    calls_file: Path,
    output_file: Path,
):
    """Generate a markdown report with pass-rate, dimension stats, and costs."""
    total = len(evaluations)
    passed = sum(1 for e in evaluations if e.get("overall_pass", False))
    pass_rate = (passed / total * 100) if total > 0 else 0

    # Dimension stats
    dim_scores = {}
    for eval in evaluations:
        for dim, score in eval.get("scores", {}).items():
            if dim not in dim_scores:
                dim_scores[dim] = []
            dim_scores[dim].append(score)

    dim_stats = {
        dim: {
            "avg": sum(scores) / len(scores),
            "min": min(scores),
            "max": max(scores),
        }
        for dim, scores in dim_scores.items()
    }

    # Cost stats from calls.jsonl
    total_cost = 0.0
    total_tokens = 0
    estimated_count = 0

    if calls_file.exists():
        with open(calls_file) as f:
            for line in f:
                call = json.loads(line)
                if call.get("cost_usd"):
                    total_cost += call["cost_usd"]
                if call.get("usage"):
                    total_tokens += call["usage"].get("total_tokens", 0)
                if call.get("estimated", False):
                    estimated_count += 1

    # Top failure modes
    failures = [e for e in evaluations if not e.get("overall_pass", False)]
    failure_modes = {}
    for fail in failures:
        for dim, score in fail.get("scores", {}).items():
            if score < 4.0:
                failure_modes[dim] = failure_modes.get(dim, 0) + 1

    # Write markdown report
    with open(output_file, "w") as f:
        f.write("# Evaluation Report\n\n")
        f.write(f"**Pass Rate:** {passed}/{total} ({pass_rate:.1f}%)\n\n")

        f.write("## Dimension Statistics\n\n")
        for dim, stats in dim_stats.items():
            f.write(f"- **{dim}:** avg={stats['avg']:.2f}, min={stats['min']}, max={stats['max']}\n")

        f.write("\n## Top Failure Modes\n\n")
        if failure_modes:
            for dim, count in sorted(failure_modes.items(), key=lambda x: -x[1]):
                f.write(f"- **{dim}:** {count} failures\n")
        else:
            f.write("No failures detected.\n")

        f.write("\n## Cost Summary\n\n")
        f.write(f"- **Total Cost:** ${total_cost:.4f}\n")
        f.write(f"- **Total Tokens:** {total_tokens:,}\n")
        if estimated_count > 0:
            f.write(f"- **Estimated Records:** {estimated_count} (verify with provider billing)\n")
        else:
            f.write("- All costs based on provider-reported usage.\n")

    print(f"[report] Generated report at {output_file}")
