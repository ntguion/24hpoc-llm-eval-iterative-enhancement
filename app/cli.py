#!/usr/bin/env python3
"""CLI for Call Summary Copilot."""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env in the project root
# Must be done BEFORE importing app modules (which may access os.getenv)
# ruff: noqa: E402
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

from app.audit import AuditLogger
from app.config import ModelRegistry, Settings
from app.cost import compute_cost
from app.generate.runner import DatasetGenerator
from app.judge.runner import JudgeRunner
from app.provider.anthropic import AnthropicProvider
from app.provider.google import GoogleProvider
from app.provider.mock import MockProvider  # noqa: F401 - Used by test suite
from app.provider.openai import OpenAIProvider
from app.report.aggregate import generate_report
from app.summarize.runner import SummarizeRunner
from app.tune.heuristics import format_diff, suggest_prompt_changes


def get_provider(
    provider_name: str, model_size: str, settings: Settings, registry: ModelRegistry
):
    """Factory function to create provider instances."""
    model_id = registry.get_model_id(provider_name, model_size)

    if provider_name == "openai":
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")
        return OpenAIProvider(api_key, model_id)

    elif provider_name == "anthropic":
        api_key = settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")
        return AnthropicProvider(api_key, model_id)

    elif provider_name == "google":
        api_key = settings.google_api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set in environment")
        return GoogleProvider(api_key, model_id)

    else:
        raise ValueError(f"Unknown provider: {provider_name}")


def cmd_generate(args, settings: Settings, registry: ModelRegistry, run_dir: Path):
    """Generate synthetic dataset."""
    n = args.N or settings.default_n
    data_dir = Path("data")
    transcripts_file = data_dir / "transcripts.jsonl"

    provider = get_provider(args.provider, args.model, settings, registry)
    generator = DatasetGenerator(provider, data_dir)

    # Check if dataset already exists
    if transcripts_file.exists():
        # Count existing transcripts
        import json

        existing_count = 0
        try:
            with open(transcripts_file) as f:
                for line in f:
                    if line.strip():
                        existing_count += 1
        except Exception:
            existing_count = 0

        if args.regenerate:
            print(
                f"[generate] Regenerating dataset (replacing {existing_count} existing transcripts)"
            )
            transcripts_file.unlink()
            transcripts = generator.generate(n=n, workers=args.workers)
            generator.save(transcripts)
            print(f"[generate] ✓ Generated {len(transcripts)} new transcripts")
        elif existing_count >= n:
            print(
                f"[generate] Dataset already has {existing_count} transcripts (target: {n})"
            )
            print("[generate] Use --regenerate to replace existing dataset")
            return
        else:
            # Generate delta to reach target
            delta = n - existing_count
            print(
                f"[generate] Found {existing_count} existing transcripts, generating {delta} more to reach {n}"
            )
            new_transcripts = generator.generate(n=delta, workers=args.workers)

            # Load existing and append
            existing = []
            with open(transcripts_file) as f:
                for line in f:
                    if line.strip():
                        existing.append(json.loads(line))

            # Re-number all transcripts sequentially with new timestamp-based IDs
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            all_transcripts = existing + new_transcripts
            for idx, t in enumerate(all_transcripts, 1):
                t["call_id"] = f"TRA-{timestamp}-{idx:03d}"

            generator.save(all_transcripts)
            print(
                f"[generate] ✓ Added {delta} transcripts (total: {len(all_transcripts)})"
            )
    else:
        transcripts = generator.generate(n=n, workers=args.workers)
        generator.save(transcripts)
        print(f"[generate] ✓ Generated {len(transcripts)} transcripts")


def cmd_summarize(args, settings: Settings, registry: ModelRegistry, run_dir: Path):
    """Summarize transcripts."""
    data_dir = Path("data")
    transcripts_file = data_dir / "transcripts.jsonl"

    if not transcripts_file.exists():
        print("[error] No transcripts found. Run 'generate' first.")
        sys.exit(1)

    # Load transcripts
    transcripts = []
    with open(transcripts_file) as f:
        for line in f:
            transcripts.append(json.loads(line))

    print(f"[summarize] Loading {len(transcripts)} transcripts...")

    provider = get_provider(args.provider, args.model, settings, registry)
    prompts_dir = Path("configs/prompts")

    # Set up audit logger and cost calculator
    audit_logger = AuditLogger(run_dir)
    model_pricing = registry.get_pricing(args.provider, args.model)

    runner = SummarizeRunner(
        provider,
        prompts_dir,
        run_dir,
        audit_logger=audit_logger,
        cost_calculator=compute_cost,
        model_pricing=model_pricing,
        temperature=settings.temperature,
        seed=settings.seed,
    )
    summaries = runner.run(transcripts, workers=args.workers)

    # Save summaries to file
    output_file = run_dir / "summaries.jsonl"
    with open(output_file, "w") as f:
        for s in summaries:
            f.write(json.dumps(s) + "\n")

    print(f"[summarize] ✓ Summarized {len(summaries)} transcripts")
    print(f"[summarize] ✓ Saved {len(summaries)} summaries to {output_file}")


def cmd_judge(args, settings: Settings, registry: ModelRegistry, run_dir: Path):
    """Evaluate summaries."""
    data_dir = Path("data")
    transcripts_file = data_dir / "transcripts.jsonl"
    summaries_file = run_dir / "summaries.jsonl"

    if not summaries_file.exists():
        print("[error] No summaries found. Run 'summarize' first.")
        sys.exit(1)

    # Load summaries first to know which call_ids we need
    summaries = []
    with open(summaries_file) as f:
        for line in f:
            summaries.append(json.loads(line))

    # Load only the transcripts that match the summaries (by call_id)
    summary_call_ids = {s["call_id"] for s in summaries}
    transcripts = []
    with open(transcripts_file) as f:
        for line in f:
            transcript = json.loads(line)
            if transcript["call_id"] in summary_call_ids:
                transcripts.append(transcript)

    # Ensure transcripts and summaries are in the same order
    transcript_dict = {t["call_id"]: t for t in transcripts}
    transcripts = [
        transcript_dict[s["call_id"]]
        for s in summaries
        if s["call_id"] in transcript_dict
    ]

    print(f"[judge] Evaluating {len(summaries)} summaries...")

    provider = get_provider(args.provider, args.model, settings, registry)
    prompts_dir = Path("configs/prompts")
    rubric_path = Path("configs/rubric.default.json")

    # Set up audit logger and cost calculator
    audit_logger = AuditLogger(run_dir)
    model_pricing = registry.get_pricing(args.provider, args.model)

    runner = JudgeRunner(
        provider,
        prompts_dir,
        rubric_path,
        run_dir,
        audit_logger=audit_logger,
        cost_calculator=compute_cost,
        model_pricing=model_pricing,
        temperature=settings.temperature,
        seed=settings.seed,
    )
    evaluations = runner.run(transcripts, summaries, workers=args.workers)

    # Save evaluations to file
    output_file = run_dir / "evaluations.jsonl"
    with open(output_file, "w") as f:
        for e in evaluations:
            f.write(json.dumps(e) + "\n")

    print(f"[judge] ✓ Evaluated {len(evaluations)} summaries")
    print(f"[judge] ✓ Saved {len(evaluations)} evaluations to {output_file}")


def cmd_tune(args, settings: Settings, registry: ModelRegistry, run_dir: Path):
    """Generate prompt tuning suggestions."""
    evaluations_file = run_dir / "evaluations.jsonl"

    if not evaluations_file.exists():
        print("[error] No evaluations found. Run 'judge' first.")
        sys.exit(1)

    # Load evaluations
    evaluations = []
    with open(evaluations_file) as f:
        for line in f:
            evaluations.append(json.loads(line))

    print(f"[tune] Analyzing {len(evaluations)} evaluations...")

    # Choose tuning method
    if getattr(args, "use_llm", False):
        # LLM-assisted tuning
        print(
            f"[tune] Using LLM-assisted tuning (provider: {args.provider or 'openai'}, model: {args.model or 'small'})"
        )

        provider = get_provider(
            args.provider or "openai", args.model or "small", settings, registry
        )

        # Load current prompt
        prompt_system = Path("configs/prompts/summarizer.system.txt")
        prompt_user = Path("configs/prompts/summarizer.user.txt")

        if not prompt_system.exists():
            print("[error] Summarizer prompt file not found")
            sys.exit(1)

        with open(prompt_system) as f:
            system_prompt = f.read()
        with open(prompt_user) as f:
            user_prompt = f.read()

        current_prompt = f"SYSTEM:\n{system_prompt}\n\nUSER TEMPLATE:\n{user_prompt}"

        from app.tune.llm_assistant import llm_suggest_changes

        suggestions, metadata = llm_suggest_changes(
            provider, current_prompt, evaluations
        )

        # Log usage for tuner call
        if metadata.get("usage"):
            usage = metadata["usage"]
            cost_usd = None
            if usage:
                model_pricing = registry.get_pricing(
                    args.provider or "openai", provider.model_id
                )
                if model_pricing:
                    cost_usd = compute_cost(
                        type("Usage", (), usage)(), model_pricing
                    )  # Mock usage object

            print(
                f"[tune] LLM tuner: {usage.get('total_tokens', 0)} tokens"
                + (f", ${cost_usd:.4f}" if cost_usd else "")
            )

    else:
        # Heuristic-based tuning
        print("[tune] Using heuristic-based tuning")
        suggestions = suggest_prompt_changes(evaluations)

    diff_text = format_diff(suggestions)

    # Save diff
    diff_file = run_dir / "prompts.diff.md"
    with open(diff_file, "w") as f:
        f.write(diff_text)

    print(f"[tune] ✓ Saved prompt suggestions to {diff_file}")
    print("\nSuggestions:")
    for s in suggestions:
        print(f"  {s}")

    # Apply suggestions if requested
    if getattr(args, "apply", False):
        from app.tune.apply import apply_suggestions_interactive

        prompt_file = Path("configs/prompts/summarizer.system.txt")
        applied = apply_suggestions_interactive(
            prompt_file, suggestions, auto_apply=getattr(args, "auto_apply", False)
        )
        if applied:
            print(
                "\n[tune] ⚠️  Prompt has been modified. Re-run summarize → judge to see improvements."
            )


def cmd_report(args, settings: Settings, registry: ModelRegistry, run_dir: Path):
    """Generate final report."""
    evaluations_file = run_dir / "evaluations.jsonl"
    calls_file = run_dir / "calls.jsonl"

    if not evaluations_file.exists():
        print("[error] No evaluations found. Run 'judge' first.")
        sys.exit(1)

    # Load evaluations
    evaluations = []
    with open(evaluations_file) as f:
        for line in f:
            evaluations.append(json.loads(line))

    print(f"[report] Generating report for {len(evaluations)} evaluations...")

    report_file = run_dir / "report.md"
    generate_report(evaluations, calls_file, report_file)

    print(f"[report] ✓ Report saved to {report_file}")

    # Print summary
    print("\n" + "=" * 60)
    with open(report_file) as f:
        print(f.read())
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        prog="call-summary-copilot", description="Eval-first LLM Copilot"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_gen = sub.add_parser("generate", help="Generate synthetic dataset")
    p_gen.add_argument(
        "--provider", required=True, choices=["openai", "anthropic", "google"]
    )
    p_gen.add_argument("--model", required=True, choices=["small", "large"])
    p_gen.add_argument(
        "--dataset-only", action="store_true", help="Only generate dataset"
    )
    p_gen.add_argument(
        "--dataset-append", action="store_true", help="Append to existing dataset"
    )
    p_gen.add_argument(
        "--regenerate", action="store_true", help="Delete and regenerate entire dataset"
    )
    p_gen.add_argument("--N", type=int, help="Number of samples to generate")
    p_gen.add_argument("--M", type=int, help="Number of samples to append")
    p_gen.add_argument(
        "--workers", type=int, default=5, help="Number of concurrent workers"
    )

    p_sum = sub.add_parser("summarize", help="Generate summaries")
    p_sum.add_argument(
        "--provider", required=True, choices=["openai", "anthropic", "google"]
    )
    p_sum.add_argument("--model", required=True, choices=["small", "large"])
    p_sum.add_argument(
        "--workers", type=int, default=5, help="Number of concurrent workers"
    )

    p_judge = sub.add_parser("judge", help="Evaluate summaries")
    p_judge.add_argument(
        "--provider", required=True, choices=["openai", "anthropic", "google"]
    )
    p_judge.add_argument("--model", required=True, choices=["small", "large"])
    p_judge.add_argument(
        "--workers", type=int, default=5, help="Number of concurrent workers"
    )

    p_tune = sub.add_parser("tune", help="Generate prompt tuning suggestions")
    p_tune.add_argument(
        "--use-llm", action="store_true", help="Use LLM-assisted tuning"
    )
    p_tune.add_argument("--provider", choices=["openai", "anthropic", "google"])
    p_tune.add_argument("--model", choices=["small", "large"])
    p_tune.add_argument(
        "--apply", action="store_true", help="Interactively apply suggestions to prompt"
    )
    p_tune.add_argument(
        "--auto-apply",
        action="store_true",
        help="Auto-apply without confirmation (use with --apply)",
    )

    _ = sub.add_parser(
        "report", help="Generate final report"
    )  # No additional args needed

    args = parser.parse_args()

    # Load settings and model registry
    settings = Settings.from_env()
    registry_path = Path("configs/models.yaml")
    registry = ModelRegistry(registry_path)

    # Determine run directory
    # For generate: always create new
    # For other commands: use latest run if exists
    runs_root = Path("runs")
    if args.cmd == "generate":
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = runs_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        print(f"[cli] Run ID: {run_id}")
        print(f"[cli] Run directory: {run_dir}\n")
    else:
        # Use latest run directory with relevant artifacts
        if runs_root.exists():
            run_dirs = sorted(
                [d for d in runs_root.iterdir() if d.is_dir()], reverse=True
            )
            # For summarize/judge/tune/report, find run with summaries if needed
            if args.cmd in ["judge", "tune", "report"]:
                # Need summaries
                run_dir = None
                for d in run_dirs:
                    if (d / "summaries.jsonl").exists():
                        run_dir = d
                        break
                if not run_dir:
                    print("[error] No run with summaries found. Run 'summarize' first.")
                    sys.exit(1)
            else:
                # summarize just needs latest
                if run_dirs:
                    run_dir = run_dirs[0]
                else:
                    print("[error] No run directory found. Run 'generate' first.")
                    sys.exit(1)
            print(f"[cli] Using run: {run_dir.name}\n")
        else:
            print("[error] No runs directory found. Run 'generate' first.")
            sys.exit(1)

    # Dispatch to command handlers
    if args.cmd == "generate":
        cmd_generate(args, settings, registry, run_dir)
    elif args.cmd == "summarize":
        cmd_summarize(args, settings, registry, run_dir)
    elif args.cmd == "judge":
        cmd_judge(args, settings, registry, run_dir)
    elif args.cmd == "tune":
        cmd_tune(args, settings, registry, run_dir)
    elif args.cmd == "report":
        cmd_report(args, settings, registry, run_dir)


if __name__ == "__main__":
    main()
