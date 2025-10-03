# 24h POCs — #001 Business-Aligned Agent Assist

**Evaluating non-deterministic LLM output with a business rubric**

---

## TL;DR

**Thesis.** Business teams adopt what they can measure. Non-deterministic LLM output needs a yardstick leaders already trust.  
**Method.** Let an LLM act as judge, using the same rubric a human supervisor would. Iterate prompts against that rubric and track the change.  
**Result.** In 24 hours, factuality improved **+0.40**, and actionability bumped **+0.20** before dipping again under tighter structure. This is an early demo of a method I've also used at ~10× scale in commercial settings (national health plan level). Even small shifts show the system can be steered.

---

## 1) Framing the problem

AI adoption in business doesn't stall because of weak demos—it stalls because of missing trust and missing proof of performance at scale. Leaders want answers to two questions:

1. Will this consistently capture what matters for the workflow (resolution, action, context, compliance)?  
2. Will this avoid harming end-user experience (hallucinations, skipped steps, compliance gaps)?  

Most traditional testing assumes determinism: one right answer. LLMs don't behave that way. The bridge is evaluation with **rubrics** that mirror business outcomes. If humans and models both use the same rubric, results become clear, comparable, and adoption feels less like a leap of faith.

---

## 2) The 24-hour POC

**Goal:** Build a quick loop, show directional movement, and mirror what actually works in practice—without pretending this is "production-grade."

**What I built:**
- **Business rubric** with five dimensions: call resolution, action items, context preservation, compliance notes, quality indicators (weights + gates).
- **Human-mirrored judging.** The LLM judge fills the same rubric a supervisor would.
- **Parallel reviews.** Calibrate the judge with SME reviews, then let it scale.
- **Prompt edits guided by the model.** The judge explains itself in short rationales. Another model turns those rationales into **diff-ready** prompt edits. Rinse and repeat.

**Models (kept cost-aware for a POC):**
- Transcript generation: **gpt-4o-mini**
- Summarization + judging: **GPT-4.1**

---

## 3) What moved overnight

Three iterations, fixed rubric, small sample.

| Iteration                     |   Avg   | Factuality | Actionability | Notes                        |
| ------------------------------ | :-----: | :--------: | :-----------: | ---------------------------- |
| 0 (baseline)                   | **4.24** |   **3.80** |    **3.80**   | simple 3-rule prompt         |
| 1 (+evidence)                  |   4.24  |    4.00    |      4.00     | tighter support requirements |
| 2 (+factuality controls)       | **4.32** |   **4.20** |    **4.20**   | best overall                 |
| 3 (+structured actions/context)|   4.24  |   **4.20** |      3.80     | structure ↑, action ↓        |

**Read:** Explicit evidence and outcome controls reliably lift factuality. Actionability is trickier—formatting alone doesn't solve it. Costs ran ~**$0.10 per iteration** for five samples—plenty cheap for a POC.

---

## 4) Why this matters for adoption

- **Scoring feels familiar.** Leaders see the same rubric they already use in QA.
- **Scales without losing touch.** LLM judge can handle more volume while staying aligned with SMEs.
- **Feedback is practical.** Rationales translate into prompt edits, not just vibes.
- **Iteration is visible.** Comparable runs show clear deltas. Expand the data as confidence grows.

I've used this exact pattern with a national health plan: humans and models reviewed in parallel, prompt rules refined with model-generated diffs, and the summarization engine steadily improved until ops teams trusted it.

---

## 5) Run it yourself

```bash
git clone https://github.com/ntguion/24hpoc-llm-eval-iterative-enhancement.git
cd 24hpoc-llm-eval-iterative-enhancement
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env        # add OPENAI_API_KEY
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

## 6) Seeds, sets, and scale

For quick comparisons, reuse a seed to keep A/B deltas crisp. As confidence grows, expand the set and diversify transcripts. In client work, this approach scaled about 10× and still delivered measurable lift once rubrics were tuned with SMEs.

---

## 7) Appendix: details that matter

* **Rubric:** five weighted dimensions; gate at 4.2 average, no critical fails.
* **Prompt evolution:**

  ```
  Iter 0: 3 simple rules
  Iter 1: + evidence requirements, + action item details
  Iter 2: + factuality controls, + outcome clarity
  Iter 3: + structured actions, + context coverage
  ```
* **Metrics (this POC):** factuality **+0.40 net**; actionability **+0.20 then back to baseline**; coverage steady at **4.00**; structure **4.80 → 4.40**; safety steady.
* **Why evidence helps:** Anchors the model to transcript facts, trimming hallucination risk without heavy scaffolding.

---

# 🏗️ Technical Architecture & Implementation

*(Business case above. Implementation here.)*

## System Architecture

```
Generate → Summarize → Judge → Improve
```

IDs enforce strict lineage—no stale results.

## Core Components

* **Multi-provider stack:** OpenAI (GPT-4o mini, GPT-4.1), Anthropic (Claude), Google (Gemini), Mock.
* **Rubric system:** JSON, weighted, gated.
* **Cost-aware model mix:** small for generation, large for evaluation.

## Production Patterns

* **Concurrent API calls** with thread pools.
* **Audit + cost tracking** logged at each call.
* **Strict ID lineage** for clean data integrity.
* **Seeds + versioning** for reproducibility.

## UI & CLI

* **Streamlit UI:** pipeline view, interactive samples, visual diffs, live costs, score charts.
* **CLI:** orchestrates full pipeline with `--auto-apply`.

## Code Quality

* Strong typing with Pydantic.
* Modular design with provider abstraction.
* Clear separation of concerns.
* Tests + error handling baked in.

---

## 📚 Documentation

* **[ITERATION_REPORT.md](ITERATION_REPORT.md)** — full study with rubrics.
* Inline code comments for clarity.

---

## 🤝 Contributing

This is a demo project. Feel free to fork, adapt, extend.

---

## 📜 License

MIT — see [LICENSE](LICENSE) for details.

---

## 🔗 Connect

Built by Nathan Guion  
📧 [nathanguion1@gmail.com](mailto:nathanguion1@gmail.com)  
💼 [LinkedIn](https://linkedin.com/in/nathanguion)  
🐙 [GitHub](https://github.com/ntguion)

---

<<<<<<< HEAD
**⭐ If this helps, a star on the repo is always appreciated.**
=======
**⭐ If you found this useful, consider starring the repo!**
>>>>>>> 3ef8f55b85a9a3ce07f304135577e8016face3f5
