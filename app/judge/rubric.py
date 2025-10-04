"""Rubric management and gate evaluation."""

import json
from pathlib import Path


class Rubric:
    """Load and manage evaluation rubric."""

    def __init__(self, config_path: Path):
        with open(config_path) as f:
            self.config = json.load(f)

        self.dimensions = self.config["dimensions"]
        self.gates = self.config["gates"]

    def check_gates(self, scores: dict[str, float], hallucination_flags: list[str]) -> bool:
        """Check if scores pass gate thresholds."""
        # Compute weighted average
        total_weight = sum(d["weight"] for d in self.dimensions)
        weighted_sum = sum(scores.get(d["name"], 0) * d["weight"] for d in self.dimensions)
        avg_score = weighted_sum / total_weight if total_weight > 0 else 0

        # Check avg threshold
        if avg_score < self.gates["avg_threshold"]:
            return False

        # Check per-dimension minimums
        for dim in self.dimensions:
            if scores.get(dim["name"], 0) < dim["min_threshold"]:
                return False

        # Check hallucination flags
        if self.gates["no_critical_failures"] and hallucination_flags:
            return False

        return True
