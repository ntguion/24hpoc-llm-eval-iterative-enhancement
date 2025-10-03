# 📞 LLM Eval & Iterative Prompt Enhancement Demo

> **Production-grade evaluation infrastructure demonstrating the complete feedback loop:** synthetic data generation, LLM-as-judge scoring, automated prompt optimization, and measurable quality improvements.

Built to showcase eval-driven development methodologies for LLM applications—the kind of systematic, data-driven approach used by Applied AI teams at companies like OpenAI.

---

## 🎯 What This Demonstrates

This is a **fully functional eval pipeline** that shows:

1. **Synthetic Data Generation** - LLM-powered transcript generation with reproducible seeding
2. **Structured Evaluation** - Multi-dimensional rubrics with detailed rationales
3. **LLM-as-Judge** - Rigorous scoring against production-grade quality standards
4. **Automated Prompt Tuning** - AI-suggested improvements based on failure analysis
5. **Measurable Iteration** - Quantified lift from prompt changes (+0.08 avg improvement demonstrated)
6. **Data Consistency** - Strict ID-based lineage tracking across all artifacts
7. **Production Patterns** - Concurrent execution, cost tracking, audit trails, versioned outputs

**Key Result:** Demonstrated +0.08 average score improvement (3.98 → 4.06) through two iteration cycles, with some samples improving by +0.4 points.

---

## 🚀 Quick Start (< 5 Minutes)

### Prerequisites
- Python 3.10+
- At least one API key (OpenAI recommended)

### Setup

```bash
# 1. Clone and install
git clone <your-repo-url>
cd call-summary-copilot
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .

# 2. Configure API keys
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Launch the UI
streamlit run streamlit_app.py
```

**That's it!** Open http://localhost:8501 and click through the pipeline.

---

## 💡 Key Features

### For Recruiters & Hiring Managers

- **Complete Eval Loop** - Not just a demo, but a working system showing eval → feedback → improvement
- **Production Patterns** - Concurrent processing, cost tracking, audit trails, error handling
- **Measurable Results** - Every change is quantified with before/after metrics
- **Clean Architecture** - Modular design, type hints, proper abstractions
- **Ready to Run** - No complex setup, works out of the box

### For Engineers

- **Multi-Provider Support** - OpenAI, Anthropic, Google Gemini with native SDKs
- **Configurable Rubrics** - JSON-based evaluation criteria with weighted dimensions
- **LLM-Assisted Tuning** - Automatically generates actionable prompt improvements
- **Artifact Versioning** - Every run produces versioned, traceable outputs
- **Diff Visualization** - Side-by-side prompt comparisons with apply/reject workflow
- **Session Tracking** - Real-time token/cost monitoring across pipeline steps

---

## 🏗️ Architecture

```
┌─────────────┐
│  Generate   │  Synthetic call transcripts (LLM-powered)
│ Transcripts │  → TRA-YYYYMMDD_HHMMSS-001
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Summarize  │  Extract structured data from transcripts
│   (Task)    │  → SUM-001 (links to TRA-001)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Judge    │  LLM-as-judge multi-dimensional scoring
│  (Evaluate) │  → EVA-001 (links to SUM-001 + TRA-001)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Improve   │  AI-suggested prompt improvements
│  & Report   │  → Apply → Re-run → Measure lift
└─────────────┘
```

### Data Flow

1. **Transcripts** have ID: `TRA-20251002_125416-001`
2. **Summaries** have ID: `SUM-001` + `transcript_id` link
3. **Evaluations** have ID: `EVA-001` + `summary_id` + `transcript_id` links

**Strict Consistency:** UI only shows data when IDs perfectly align—no stale results ever displayed.

---

## 📊 Example Workflow

### Iteration 1: Baseline
```bash
$ python -m app.cli generate --provider openai --model small --N 10
$ python -m app.cli summarize --provider openai --model small
$ python -m app.cli judge --provider openai --model small
```

**Result:** avg=3.98 (failing 4.2 threshold)

**Judge Feedback:**
```
- Always include verification details such as member ID and date of birth
- Specify exact timeframes for actions (e.g., '3-5 business days', not 'soon')
- Include specific medication names, pharmacy names, and plan codes when mentioned
```

### Iteration 2: After Applying Improvements
Apply suggestions → Re-run pipeline

**Result:** avg=4.06 (+0.08 improvement, some samples +0.4!)

**This demonstrates the compounding feedback loop that drives quality improvements.**

---

## 🎨 UI Features

- **Unified Pipeline View** - All steps on one page with live progress
- **Interactive Samples** - See transcripts, summaries, and evaluations side-by-side
- **Visual Diff** - Green/red highlighting for prompt changes
- **Live Metrics** - Real-time token counts and cost tracking
- **Distribution Charts** - Score breakdowns across eval dimensions
- **One-Click Apply** - Apply AI-suggested improvements and re-run

---

## 🔧 Configuration

### Rubric (`configs/rubric.default.json`)
```json
{
  "dimensions": [
    {"name": "coverage", "weight": 0.25, "min_threshold": 4.5},
    {"name": "factuality", "weight": 0.30, "min_threshold": 5.0},
    ...
  ],
  "gates": {
    "avg_threshold": 4.2,
    "no_hallucination_flags": true
  }
}
```

### Prompts (`configs/prompts/`)
- `summarizer.system.txt` - Instructions for the task being evaluated
- `judge.system.txt` - Scoring philosophy and criteria
- `judge.user.txt` - Rubric application and output format

---

## 📈 Technical Highlights

### For OpenAI Applied Evals Role

✅ **Eval Design** - Multi-dimensional rubrics with weighted scoring  
✅ **LLM-as-Judge** - Production-grade evaluation with detailed rationales  
✅ **Feedback Loops** - Automated prompt tuning from eval signals  
✅ **Reproducibility** - Seeded sampling, versioned artifacts, audit trails  
✅ **Scalability** - Concurrent workers (5-32x parallelism)  
✅ **Cost Management** - Per-call tracking with provider-specific pricing  
✅ **Data Integrity** - Strict lineage tracking prevents stale results  
✅ **Quantified Impact** - Every change measured with before/after metrics

### Code Quality

- Type hints throughout
- Modular architecture (provider abstraction, pluggable runners)
- Comprehensive error handling
- Clean separation of concerns (CLI, UI, core logic)
- Docstrings and inline comments
- Git-friendly (proper .gitignore, no secrets committed)

---

## 📚 Documentation

- **This README** - Quick start and overview
- **ARCHITECTURE.md** - Deep technical dive (coming soon)
- **CLEANUP_DELTA.md** - Development journey and cleanup plan
- **Inline code comments** - Explanation of complex logic

---

## 🧪 Testing

```bash
# Run tests
pytest

# Run end-to-end test (mocked)
pytest tests/test_end_to_end.py -v
```

---

## 🤝 Contributing

This is a portfolio demo project. Feel free to fork, adapt, or use as inspiration for your own eval infrastructure!

---

## 📜 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🎓 Learning Resources

This demo embodies concepts from:
- OpenAI's [Evals framework](https://github.com/openai/evals)
- Anthropic's [Constitutional AI](https://www.anthropic.com/constitutional.pdf)
- Google's [RLHF methodology](https://arxiv.org/abs/2009.01325)

---

## 🔗 Connect

Built by Nathan [Your Last Name]  
📧 [nathanguion1@gmail.com](mailto:nathanguion1@gmail.com)  
💼 [LinkedIn](https://linkedin.com/in/nathanguion/)
🐙 [GitHub](https://github.com/ntguion)

---

**⭐ If you found this useful, consider starring the repo!**
