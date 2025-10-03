"""Judge runner: evaluate summaries against transcripts."""

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from ..provider.base import BaseProvider, Message, ProviderError
from .rubric import Rubric


class JudgeRunner:
    """Run evaluation over summaries."""

    def __init__(
        self,
        provider: BaseProvider,
        prompts_dir: Path,
        rubric_path: Path,
        output_dir: Path,
        audit_logger=None,
        cost_calculator=None,
        model_pricing: dict | None = None,
        temperature: float = 0.7,
        seed: int | None = None,
    ):
        self.provider = provider
        self.prompts_dir = prompts_dir
        self.rubric = Rubric(rubric_path)
        self.output_dir = output_dir
        self.audit_logger = audit_logger
        self.cost_calculator = cost_calculator
        self.model_pricing = model_pricing or {}
        self.temperature = temperature
        self.seed = seed
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load prompts
        with open(prompts_dir / "judge.system.txt") as f:
            self.system_prompt = f.read().strip()
        with open(prompts_dir / "judge.user.txt") as f:
            self.user_template = f.read().strip()

        # Session tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

    def run(self, transcripts: list[dict], summaries: list[dict], workers: int = 5) -> list[dict]:
        """Evaluate summaries against transcripts with concurrent workers."""
        pairs = list(zip(transcripts, summaries))
        total_pairs = len(pairs)
        print(f"[judge] Evaluating {total_pairs} summaries with {workers} workers...")
        evaluations = []
        completed_count = 0

        def evaluate_one(transcript: dict, summary: dict) -> dict | None:
            """Evaluate a single summary."""
            user_prompt = self.user_template.format(
                rubric=json.dumps(self.rubric.config, indent=2),
                transcript_json=json.dumps(transcript, indent=2),
                summary_json=json.dumps(summary, indent=2),
            )

            messages = [
                Message(role="system", content=self.system_prompt),
                Message(role="user", content=user_prompt),
            ]

            try:
                # Call provider
                response = self.provider.generate(
                    messages,
                    temperature=self.temperature,
                    seed=self.seed,
                    max_tokens=2048,
                )

                # Parse response with robust JSON extraction
                raw_text = response.text.strip()
                
                # Try to extract JSON from markdown code blocks or find JSON object
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Try to find the JSON object (stop at first complete object)
                    json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                    else:
                        json_str = raw_text
                
                # Attempt to parse JSON with error handling
                try:
                    evaluation = json.loads(json_str)
                except json.JSONDecodeError as e:
                    # Try cleaning up common formatting issues
                    cleaned = re.sub(r'\s+', ' ', json_str)
                    try:
                        evaluation = json.loads(cleaned)
                    except json.JSONDecodeError:
                        # Log error and skip this evaluation by returning None
                        error_msg = f"JSON parse error: {str(e)[:100]}"
                        return None  # Skip this evaluation
                evaluation["call_id"] = summary["call_id"]

                # Add evaluation_id, summary_id, and transcript_id for traceability
                # Extract the sequence number from transcript ID (e.g., TRA-20251002_122258-001 -> 001)
                transcript_id = summary.get("transcript_id", transcript["call_id"])
                seq_num = transcript_id.split("-")[-1] if "-" in transcript_id else "000"
                evaluation_id = f"EVA-{seq_num}"
                evaluation["evaluation_id"] = evaluation_id
                evaluation["summary_id"] = summary.get("summary_id", f"SUM-{seq_num}")
                evaluation["transcript_id"] = transcript_id

                # Normalize scores (handle both flat and nested formats)
                scores = evaluation.get("scores", {})
                if scores and isinstance(list(scores.values())[0], dict):
                    # LLM returned {"coverage": {"score": 4, "rationale": "..."}} format
                    # Extract scores and rationales separately
                    normalized_scores = {}
                    normalized_rationales = {}
                    for dim, val in scores.items():
                        if isinstance(val, dict):
                            normalized_scores[dim] = val.get("score", 0)
                            if "rationale" in val:
                                normalized_rationales[dim] = val["rationale"]
                        elif isinstance(val, (int, float)):
                            normalized_scores[dim] = val
                        else:
                            normalized_scores[dim] = 0
                    evaluation["scores"] = normalized_scores
                    # Only add rationales if we extracted any
                    if normalized_rationales and "rationales" not in evaluation:
                        evaluation["rationales"] = normalized_rationales

                # Ensure rationales key exists (even if empty)
                if "rationales" not in evaluation:
                    evaluation["rationales"] = {}

                # Check gates
                evaluation["overall_pass"] = self.rubric.check_gates(
                    evaluation.get("scores", {}), evaluation.get("hallucination_flags", [])
                )

                # Track tokens and cost
                cost = None
                if response.usage:
                    self.total_input_tokens += response.usage.prompt_tokens
                    self.total_output_tokens += response.usage.completion_tokens

                    if self.cost_calculator and self.model_pricing:
                        cost = self.cost_calculator(response.usage, self.model_pricing)
                        if cost:
                            self.total_cost += cost

                # Log to audit trail
                if self.audit_logger:
                    self.audit_logger.log_call(
                        phase="judge",
                        provider=self.provider.__class__.__name__.replace("Provider", "").lower(),
                        model=self.provider.model_id,
                        messages=messages,
                        response=response,
                        temperature=self.temperature,
                        seed=self.seed,
                        cost_usd=cost,
                        status="ok",
                    )

                pass_emoji = "✓" if evaluation["overall_pass"] else "✗"
                avg_score = (
                    sum(evaluation["scores"].values()) / len(evaluation["scores"]) if evaluation.get("scores") else 0
                )

                return {
                    "evaluation": evaluation,
                    "call_id": summary["call_id"],
                    "pass_emoji": pass_emoji,
                    "avg_score": avg_score,
                    "tokens": response.usage.total_tokens if response.usage else 0,
                    "cost": cost,
                    "error": None,
                }

            except (ProviderError, json.JSONDecodeError) as e:
                # Log error
                if self.audit_logger:
                    self.audit_logger.log_call(
                        phase="judge",
                        provider=self.provider.__class__.__name__.replace("Provider", "").lower(),
                        model=self.provider.model_id,
                        messages=messages,
                        response=None,
                        temperature=self.temperature,
                        seed=self.seed,
                        cost_usd=None,
                        status="error",
                        error=str(e),
                    )

                # Create stub evaluation on error
                stub_evaluation = {
                    "call_id": summary["call_id"],
                    "scores": {
                        "coverage": 0,
                        "factuality": 0,
                        "actionability": 0,
                        "structure_brevity": 0,
                        "safety_compliance": 0,
                    },
                    "rationales": {
                        dim: f"ERROR: {str(e)}"
                        for dim in ["coverage", "factuality", "actionability", "structure_brevity", "safety_compliance"]
                    },
                    "hallucination_flags": [],
                    "overall_pass": False,
                    "suggested_prompt_changes": [],
                }

                return {
                    "evaluation": stub_evaluation,
                    "call_id": summary["call_id"],
                    "pass_emoji": "✗",
                    "avg_score": 0,
                    "tokens": 0,
                    "cost": None,
                    "error": str(e),
                }

        # Use ThreadPoolExecutor for concurrent processing
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(evaluate_one, transcript, summary): (transcript, summary)
                for transcript, summary in pairs
            }

            # Collect results as they complete
            for future in as_completed(futures):
                transcript, summary = futures[future]
                try:
                    result = future.result()
                    completed_count += 1

                    # Handle case where evaluate_one returns None (JSON parsing error)
                    if result is None:
                        print(
                            f"  [{completed_count}/{total_pairs}] {summary.get('call_id', 'unknown')} → ERROR: JSON parsing failed",
                            flush=True,
                        )
                        continue

                    if result["error"]:
                        print(
                            f"  [{completed_count}/{total_pairs}] {result['call_id']} → ERROR: {result['error']}",
                            flush=True,
                        )
                    else:
                        cost_str = f"${result['cost']:.4f}" if result["cost"] else "$0.0000"
                        print(
                            f"  [{completed_count}/{total_pairs}] {result['call_id']} → {result['pass_emoji']} avg={result['avg_score']:.1f}, {result['tokens']} tokens, {cost_str}",
                            flush=True,
                        )

                    if result is not None and "evaluation" in result:
                        evaluations.append(result["evaluation"])

                    # Print progress message for UI
                    print(f"[judge] Progress: {completed_count}/{total_pairs} evaluations completed", flush=True)

                except Exception as e:
                    completed_count += 1
                    print(
                        f"  [{completed_count}/{total_pairs}] {summary['call_id']} → ERROR: {e}",
                        file=sys.stderr,
                        flush=True,
                    )

        # Save evaluations
        output_file = self.output_dir / "evaluations.jsonl"
        with open(output_file, "w") as f:
            for e in evaluations:
                f.write(json.dumps(e) + "\n")

        print(f"\n[judge] ✓ Saved {len(evaluations)} evaluations to {output_file}")
        print(
            f"[judge] Session totals: {self.total_input_tokens} in + {self.total_output_tokens} out = "
            f"{self.total_input_tokens + self.total_output_tokens} tokens, ${self.total_cost:.4f}"
        )

        return evaluations
