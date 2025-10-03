# 24h POCs — #002 Business-Aligned Agent Assist

**Evaluating non-deterministic LLM output with a business rubric**

## TL;DR

**Thesis.** Business teams adopt what they can evaluate. Non-deterministic LLM output needs a yardstick leaders recognize.
**Method.** Use an LLM as judge to fill the same rubric a human supervisor would. Iterate prompts against that rubric and measure the change.
**Result.** In 24 hours, factuality improved **+0.40** and actionability briefly improved **+0.20** before regressing under tighter structure. This is a **preliminary demo** of a method I have used successfully at ~10× larger scale in commercial settings (national health plan level). Small moves signal a system that can be steered.

---

## 1) Framing the problem

Business adoption of AI is not blocked by demos. It is blocked by trust and performance at scale. Leaders really want two things:

1. Will this consistently capture what matters for the workflow (resolution, action, context, compliance)?
2. Will this avoid harming end-user experience (hallucinations, missed steps, sloppy compliance)?

Traditional testing leaders know assumes determinism. They expect a single correct answer, which is not how LLMs behave. To bridge that gap, we evaluate outputs with **rubrics** that reflect business outcomes rather than academic benchmarks. Humans and the model apply the same rubric. That creates clarity and establishes a path to adoption.

---

## 2) The 24-hour POC

Goal: demonstrate the loop simply, show directional results, and mirror what works in practice—without pretending to be "production-grade."

**What I built**

* **Business rubric** with five dimensions: call resolution, action items, context preservation, compliance notes, quality indicators (weights and gates).
* **Human-mirrored judging.** The LLM judge fills the same rubric a supervisor would.
* **Parallel review cycles.** Calibrate the judge to match human SMEs, then let the judge run at scale.
* **Self-guided prompt improvement.** The judge provides short rationales. A model converts those rationales (plus transcripts and summaries) into **diff-ready** prompt edits. Re-run and measure the delta.

**Minimal model mix** (cost-aware for a POC)

* Generate transcripts: **gpt-4o-mini**
* Summarize and judge: **GPT-4.1**

---

## 3) What moved in a night

Small sample, fixed rubric, three iterations.

|                       Iteration |    Avg   | Factuality | Actionability | Notes                            |
| ------------------------------: | :------: | :--------: | :-----------: | -------------------------------- |
|                    0 (baseline) | **4.24** |  **3.80**  |    **3.80**   | simple 3-rule prompt             |
|                   1 (+evidence) |   4.24   |    4.00    |      4.00     | tighter support requirements     |
|        2 (+factuality controls) | **4.32** |  **4.20**  |    **4.20**   | best overall                     |
| 3 (+structured actions/context) |   4.24   |    4.20    |      3.80     | structure up, actionability down |

**Read:** Explicit evidence and outcome controls reliably lift factuality. Actionability is multi-factor; formatting alone is not enough. Costs stayed roughly **~$0.10 per iteration** for five samples—easy to defend for a POC.

---

## 4) How this earns adoption

* **Transparent scoring.** Leaders see the same rubric they use in QA.
* **Human-calibrated automation.** LLM judge scales review volume while staying aligned to SME standards.
* **Actionable feedback.** Rationales distill into concrete prompt edits, not vibes.
* **Measured iteration.** Re-run comparable sets and show the delta; expand data variety as confidence grows.

I have used this exact pattern with a national health plan: human + LLM reviews in parallel during AEP, prompt rules refined by model-generated diffs, and steady improvements to a summarization engine that ops teams accepted.

---

## 5) Run the demo

```bash
git clone https://github.com/ntguion/24hpoc-llm-eval-iterative-enhancement.git
cd 24hpoc-llm-eval-iterative-enhancement
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env        # add OPENAI_API_KEY (and others if you like)
streamlit run streamlit_app.py
```

Optional CLI:

```bash
python -m app.cli generate --provider openai --model small --N 10
python -m app.cli summarize --provider openai --model small
python -m app.cli judge --provider openai --model small
python -m app.cli tune --use-llm
```

---

## 6) A note on seeds, sets, and scale

For quick loops you can reuse a seed to make A/B deltas crisp. As you gain confidence, expand the set and diversify transcripts. In client work, the same approach scaled about an order of magnitude up and continued to deliver lift once the rubric was tuned with SMEs.

---

## 7) Appendix: the bits that matter

* **Rubric:** five dimensions with weights and a gate at average 4.2 and no critical failures.
* **Prompt evolution:**

  ```
  Iter 0: 3 simple rules
  Iter 1: + evidence requirements, + action item details
  Iter 2: + factuality controls, + outcome clarity
  Iter 3: + structured action items, + context coverage
  ```
* **Observed metrics (this POC):** factuality **+0.40** net; actionability **+0.20 then back to baseline**; coverage steady at **4.00**; structure **4.80 → 4.40**; safety steady.
* **Why evidence helps:** it pushes the model to anchor on transcript facts and reduces hallucination risk without heavy scaffolding.

---

---

# 🏗️ Technical Architecture & Implementation

*[Clear line between business case and technical implementation]*

## System Architecture

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

### Data Flow & Consistency

1. **Transcripts** have ID: `TRA-20251002_125416-001`
2. **Summaries** have ID: `SUM-001` + `transcript_id` link
3. **Evaluations** have ID: `EVA-001` + `summary_id` + `transcript_id` links

**Strict Consistency:** UI only shows data when IDs perfectly align—no stale results ever displayed.

## Core Components

### Multi-Provider Architecture
- **OpenAI** - Native SDK with GPT-4o-mini, GPT-4.1
- **Anthropic** - Claude 3.5 Haiku, Claude 3.5 Sonnet  
- **Google** - Gemini 2.0 Flash, Gemini 1.5 Pro
- **Mock** - For testing and development

### Business Rubric System
```json
{
  "dimensions": [
    {"name": "call_resolution", "weight": 0.25, "min_threshold": 4.0},
    {"name": "action_items", "weight": 0.25, "min_threshold": 4.0},
    {"name": "context_preservation", "weight": 0.20, "min_threshold": 4.0},
    {"name": "compliance_notes", "weight": 0.15, "min_threshold": 4.0},
    {"name": "quality_indicators", "weight": 0.15, "min_threshold": 4.0}
  ],
  "gates": {
    "avg_threshold": 4.2,
    "no_critical_failures": true
  }
}
```

### Cost-Optimized Model Selection
```yaml
openai:
  small:
    id: "gpt-4o-mini"        # $0.15/$0.60 per 1M tokens
    display_name: "GPT-4o Mini"
  large:
    id: "gpt-4.1"            # $1.50/$6.00 per 1M tokens
    display_name: "GPT-4.1"
```

## Production Patterns

### Concurrent Processing
- **ThreadPoolExecutor** for parallel API calls (5-32 workers)
- **Progress tracking** with real-time updates
- **Error handling** with graceful degradation

### Audit & Cost Tracking
- **Every API call logged** to `calls.jsonl` with usage, cost, latency
- **Session totals** tracked across pipeline steps
- **Provider-specific pricing** with real-time cost calculation

### Data Integrity
- **Strict ID-based lineage** prevents stale data display
- **Versioned artifacts** with timestamped run directories
- **Deterministic sampling** with temperature and seed control

## UI Features

### Streamlit Interface
- **Unified pipeline view** - All steps on one page with live progress
- **Interactive samples** - See transcripts, summaries, and evaluations side-by-side
- **Visual diff** - Green/red highlighting for prompt changes
- **Live metrics** - Real-time token counts and cost tracking
- **Distribution charts** - Score breakdowns across eval dimensions

### CLI Interface
```bash
# Complete pipeline
python -m app.cli generate --provider openai --model small --N 10
python -m app.cli summarize --provider openai --model large
python -m app.cli judge --provider openai --model large
python -m app.cli tune --use-llm --apply --auto-apply
python -m app.cli report
```

## Code Quality & Engineering

### Architecture Highlights
- **Type hints throughout** with Pydantic models
- **Modular design** with provider abstraction and pluggable runners
- **Clean separation** of concerns (CLI, UI, core logic)
- **Comprehensive error handling** with graceful fallbacks
- **Git-friendly** with proper .gitignore and no secrets committed

### Testing & Validation
```bash
# Run tests
pytest

# Run end-to-end test (mocked)
pytest tests/test_end_to_end.py -v
```

---

## 📚 Documentation

- **[ITERATION_REPORT.md](ITERATION_REPORT.md)** - Complete 3-iteration study with business-aligned rubrics
- **Inline code comments** - Explanation of complex logic

---

## 🤝 Contributing

This is a portfolio demo project. Feel free to fork, adapt, or use as inspiration for your own eval infrastructure!

---

## 📜 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🔗 Connect

Built by Nathan [Your Last Name]  
📧 [your.email@example.com](mailto:your.email@example.com)  
💼 [LinkedIn](https://linkedin.com/in/yourprofile)  
🐙 [GitHub](https://github.com/yourusername)

---

**⭐ If you found this useful, consider starring the repo!**