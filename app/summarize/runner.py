"""Summarize runner: generate summaries from transcripts."""

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from ..provider.base import BaseProvider, Message, ProviderError
from .schema import CallSummary


class SummarizeRunner:
    """Run summarization over a dataset."""

    def __init__(
        self,
        provider: BaseProvider,
        prompts_dir: Path,
        output_dir: Path,
        audit_logger=None,
        cost_calculator=None,
        model_pricing: dict | None = None,
        temperature: float = 0.7,
        seed: int | None = None,
    ):
        self.provider = provider
        self.prompts_dir = prompts_dir
        self.output_dir = output_dir
        self.audit_logger = audit_logger
        self.cost_calculator = cost_calculator
        self.model_pricing = model_pricing or {}
        self.temperature = temperature
        self.seed = seed

        # Load prompts
        with open(prompts_dir / "summarizer.system.txt") as f:
            self.system_prompt = f.read().strip()
        with open(prompts_dir / "summarizer.user.txt") as f:
            self.user_template = f.read().strip()

        # Session tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

    def run(self, transcripts: list[dict], workers: int = 5) -> list[dict]:
        """Generate summaries for all transcripts with concurrent workers."""
        print(f"[summarize] Summarizing {len(transcripts)} transcripts with {workers} workers...")
        summaries = []
        completed_count = 0

        def summarize_one(transcript: dict) -> dict | None:
            """Summarize a single transcript."""
            user_prompt = self.user_template.format(
                transcript_json=json.dumps(transcript, indent=2),
                schema=CallSummary.schema_text(),
                example=CallSummary.example_summary()
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
                    max_tokens=1024,
                )

                # Parse response - extract JSON from potential markdown fences
                raw_text = response.text.strip()

                # Try to extract JSON from markdown code blocks
                json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Try to find JSON object directly
                    json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                    else:
                        json_str = raw_text

                summary = json.loads(json_str)

                # Add summary_id and transcript_id for traceability
                # Extract the sequence number from transcript ID (e.g., TRA-20251002_122258-001 -> 001)
                transcript_id = transcript["call_id"]
                seq_num = transcript_id.split("-")[-1] if "-" in transcript_id else "000"
                summary_id = f"SUM-{seq_num}"
                summary["summary_id"] = summary_id
                summary["transcript_id"] = transcript_id

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
                        phase="summarize",
                        provider=self.provider.__class__.__name__.replace("Provider", "").lower(),
                        model=self.provider.model_id,
                        messages=messages,
                        response=response,
                        temperature=self.temperature,
                        seed=self.seed,
                        cost_usd=cost,
                        status="ok",
                    )

                return {
                    "summary": summary,
                    "call_id": transcript["call_id"],
                    "tokens": response.usage.total_tokens if response.usage else 0,
                    "cost": cost,
                    "error": None,
                }

            except (ProviderError, json.JSONDecodeError) as e:
                # Log error
                if self.audit_logger:
                    self.audit_logger.log_call(
                        phase="summarize",
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
                return {"summary": None, "call_id": transcript["call_id"], "tokens": 0, "cost": None, "error": str(e)}

        # Use ThreadPoolExecutor for concurrent processing
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all tasks
            futures = {executor.submit(summarize_one, transcript): transcript for transcript in transcripts}

            # Collect results as they complete
            for future in as_completed(futures):
                transcript = futures[future]
                try:
                    result = future.result()
                    completed_count += 1

                    if result["error"]:
                        print(
                            f"  [{completed_count}/{len(transcripts)}] {result['call_id']} → ERROR: {result['error']}",
                            flush=True,
                        )
                    else:
                        cost_str = f"${result['cost']:.4f}" if result["cost"] else "$0.0000"
                        print(
                            f"  [{completed_count}/{len(transcripts)}] {result['call_id']} → {result['tokens']} tokens, {cost_str}",
                            flush=True,
                        )
                        summaries.append(result["summary"])

                    # Print progress message for UI
                    print(f"[summarize] Progress: {completed_count}/{len(transcripts)} summaries completed", flush=True)

                except Exception as e:
                    completed_count += 1
                    print(
                        f"  [{completed_count}/{len(transcripts)}] {transcript['call_id']} → ERROR: {e}",
                        file=sys.stderr,
                        flush=True,
                    )

        return summaries

    def save(self, summaries: list[dict], run_dir: Path):
        """Save summaries to output files."""
        out_file = run_dir / "summaries.jsonl"
        with open(out_file, "w") as f:
            for summary in summaries:
                f.write(json.dumps(summary, ensure_ascii=False) + "\n")
        print(f"[summarize] ✓ Saved {len(summaries)} summaries to {out_file}")

        # Print cost summary
        print(f"[summarize] Total cost: ${self.total_cost:.4f}")
        print(
            f"[summarize] Total tokens: {self.total_input_tokens + self.total_output_tokens} "
            f"(in: {self.total_input_tokens}, out: {self.total_output_tokens})"
        )
