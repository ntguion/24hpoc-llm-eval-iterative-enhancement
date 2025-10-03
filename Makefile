.PHONY: help install generate summarize judge tune report pipeline clean test

help:
	@echo "Call Summary Copilot - Make Targets"
	@echo ""
	@echo "  install     Install dependencies"
	@echo "  generate    Generate synthetic transcripts (default N=10)"
	@echo "  summarize   Generate summaries"
	@echo "  judge       Evaluate summaries"
	@echo "  tune        Generate prompt improvements"
	@echo "  report      Generate evaluation report"
	@echo "  pipeline    Run full pipeline (generate → summarize → judge → tune → report)"
	@echo "  clean       Remove runs directory"
	@echo "  test        Run test suite"
	@echo ""
	@echo "Example: make generate N=20"

install:
	pip install -e .

generate:
	python -m app.cli generate --provider openai --model small --N $(or $(N),10)

summarize:
	python -m app.cli summarize --provider openai --model small

judge:
	python -m app.cli judge --provider openai --model small

tune:
	python -m app.cli tune --use-llm

report:
	python -m app.cli report

pipeline: generate summarize judge tune report
	@echo "✅ Pipeline complete!"

clean:
	rm -rf runs/
	rm -f data/transcripts.jsonl
	@echo "✅ Cleaned runs and transcripts"

test:
	pytest tests/ -v


