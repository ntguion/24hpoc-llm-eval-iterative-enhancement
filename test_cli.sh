#!/bin/bash
# Quick test script for CLI (uses stub data, not real API calls)

set -e

echo "Testing CLI commands..."
echo

# Test help
echo "1. Testing --help"
python -m app.cli --help
echo

# Note: To test with real OpenAI calls, set OPENAI_API_KEY and run:
# python -m app.cli generate --provider openai --model small --N 5
# python -m app.cli summarize --provider openai --model small
# python -m app.cli judge --provider openai --model small
# python -m app.cli tune
# python -m app.cli report

echo "✓ CLI structure OK. Set OPENAI_API_KEY to test real API calls."

