"""Test rubric and gate logic."""

from pathlib import Path

from app.judge.rubric import Rubric


def test_rubric_loads():
    """Rubric should load from default config."""
    config_path = Path(__file__).parent.parent / "configs" / "rubric.default.json"
    rubric = Rubric(config_path)

    assert len(rubric.dimensions) == 5
    assert rubric.gates["avg_threshold"] == 4.2  # Updated to match current rubric


def test_gates_pass():
    """Scores above thresholds should pass gates."""
    config_path = Path(__file__).parent.parent / "configs" / "rubric.default.json"
    rubric = Rubric(config_path)

    scores = {
        "coverage": 5,
        "factuality": 5,
        "actionability": 5,
        "structure_brevity": 5,
        "safety_compliance": 5,
    }

    assert rubric.check_gates(scores, []) is True


def test_gates_fail_low_avg():
    """Low average should fail gates."""
    config_path = Path(__file__).parent.parent / "configs" / "rubric.default.json"
    rubric = Rubric(config_path)

    scores = {
        "coverage": 3,
        "factuality": 3,
        "actionability": 3,
        "structure_brevity": 3,
        "safety_compliance": 3,
    }

    assert rubric.check_gates(scores, []) is False


def test_gates_fail_hallucination():
    """Hallucination flags should fail gates."""
    config_path = Path(__file__).parent.parent / "configs" / "rubric.default.json"
    rubric = Rubric(config_path)

    scores = {
        "coverage": 5,
        "factuality": 5,
        "actionability": 5,
        "structure_brevity": 5,
        "safety_compliance": 5,
    }

    assert rubric.check_gates(scores, ["Hallucinated claim ID"]) is False
