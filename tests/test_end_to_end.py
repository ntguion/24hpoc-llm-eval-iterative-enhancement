"""End-to-end test with mocked providers."""

import tempfile
from pathlib import Path

from app.generate.runner import DatasetGenerator
from app.judge.runner import JudgeRunner
from app.provider.mock import MockProvider
from app.report.aggregate import generate_report
from app.summarize.runner import SummarizeRunner


def test_end_to_end_mocked():
    """Run full pipeline with mock provider on 2 samples."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        data_dir = tmp_path / "data"
        prompts_dir = Path(__file__).parent.parent / "configs" / "prompts"
        rubric_path = Path(__file__).parent.parent / "configs" / "rubric.default.json"
        run_dir = tmp_path / "runs" / "test-run"

        # Generate dataset
        provider = MockProvider()
        generator = DatasetGenerator(provider, data_dir)
        transcripts = generator.generate(n=2)
        generator.save(transcripts)

        assert len(transcripts) == 2
        assert (data_dir / "transcripts.jsonl").exists()

        # Summarize
        summarizer = SummarizeRunner(provider, prompts_dir, run_dir)
        summaries = summarizer.run(transcripts)

        assert len(summaries) == 2

        # Judge
        judge = JudgeRunner(provider, prompts_dir, rubric_path, run_dir)
        evaluations = judge.run(transcripts, summaries)

        assert len(evaluations) == 2
        assert all(e.get("overall_pass") is not None for e in evaluations)

        # Report
        calls_file = run_dir / "calls.jsonl"
        report_file = run_dir / "report.md"
        generate_report(evaluations, calls_file, report_file)

        assert report_file.exists()
        report_text = report_file.read_text()
        assert "Pass Rate" in report_text
        assert "Dimension Statistics" in report_text
