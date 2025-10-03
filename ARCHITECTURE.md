# Architecture Deep-Dive

## System Overview

This is a production-grade LLM evaluation pipeline implementing the complete feedback loop: Generate → Evaluate → Improve → Measure → Repeat.

---

## Core Components

### 1. Provider Abstraction (`app/provider/`)

**Design Pattern:** Strategy pattern for multi-provider support

```python
class BaseProvider(ABC):
    @abstractmethod
    def generate(self, messages: List[Message], ...) -> LLMResponse:
        """Unified interface for all LLM providers"""
```

**Implementations:**
- `OpenAIProvider` - Uses OpenAI's chat completions API
- `AnthropicProvider` - Uses Anthropic's messages API  
- `GoogleProvider` - Uses Google's Gemini API
- `MockProvider` - For testing without API calls

**Key Design Decisions:**
- Native SDKs (not LangChain) for maximum control
- Unified `Message` and `LLMResponse` types for portability
- Per-call usage tracking built-in
- Provider-specific error handling

---

### 2. Data Generation (`app/generate/`)

**Purpose:** Create synthetic evaluation datasets without production dependencies

**Architecture:**
```
DatasetGenerator
  ├─ _build_prompt()     # Few-shot examples + schema
  ├─ _call_llm_and_parse() # LLM call + JSON extraction
  ├─ _normalize()         # Enforce schema, assign IDs
  └─ generate()           # Concurrent generation with workers
```

**Key Features:**
- Generates 1 transcript per API call (reliability > efficiency)
- Concurrent workers (default: 5) for throughput
- Robust JSON extraction (handles markdown fences, malformed output)
- Timestamp-based IDs: `TRA-YYYYMMDD_HHMMSS-NNN`
- Normalization ensures schema compliance

**Why Synthetic Data?**
- No PII/PHI concerns
- Rapid iteration (no approval processes)
- Reproducible with seeding
- Can target specific edge cases

---

### 3. Summarization (`app/summarize/`)

**Purpose:** The task being evaluated (structured extraction)

**Architecture:**
```
SummarizeRunner
  ├─ Loads prompts (system + user templates)
  ├─ Injects transcript + schema into user prompt
  ├─ Calls provider.generate()
  ├─ Parses JSON response
  ├─ Adds summary_id + transcript_id for lineage
  └─ Logs to audit trail
```

**Concurrent Execution:**
- ThreadPoolExecutor with configurable workers
- Progress tracking: `[summarize] Progress: X/Y summaries completed`
- Per-summary cost/token tracking
- Robust error handling (returns stub on failure, continues processing)

**Output:**
```json
{
  "summary_id": "SUM-001",
  "transcript_id": "TRA-20251002_125416-001",
  "call_id": "TRA-20251002_125416-001",
  "intent": "...",
  "resolution": "...",
  "next_steps": "...",
  "sentiment": "..."
}
```

---

### 4. Evaluation (`app/judge/`)

**Purpose:** LLM-as-judge with multi-dimensional scoring

**Rubric System:**
```python
class Rubric:
    dimensions: List[Dimension]  # Name, weight, min_threshold, description
    gates: Dict  # avg_threshold, no_hallucination_flags
    
    def check_gates() -> bool:
        # Enforce quality thresholds
```

**Judge Architecture:**
```
JudgeRunner
  ├─ Loads rubric + prompts
  ├─ For each (transcript, summary) pair:
  │   ├─ Inject into judge prompt
  │   ├─ Call provider.generate()
  │   ├─ Parse JSON response
  │   ├─ Normalize scores (handle nested formats)
  │   ├─ Check gates (pass/fail)
  │   └─ Add evaluation_id + lineage IDs
  └─ Return evaluations with rationales
```

**Key Features:**
- **Strict criteria** - 5 should be rare, most summaries 3-4
- **Detailed rationales** - One sentence per dimension citing specific gaps
- **Hallucination detection** - Zero tolerance, must quote hallucinated text
- **Actionable suggestions** - Concrete rules to add to summarizer prompt
- **Concurrent processing** - Same pattern as summarizer

**Scoring Philosophy:**
```
5 = Exceptional (no improvements needed)
4 = Good (minor gaps)
3 = Adequate (missing key details)
2 = Poor (significant gaps)
1 = Failed (unusable)
```

---

### 5. Prompt Tuning (`app/tune/`)

**Two Approaches:**

#### A. Heuristic Tuning (`heuristics.py`)
- Rule-based suggestions from aggregate statistics
- Example: "If avg(coverage) < 4.0 → suggest 'Include all verification details'"

#### B. LLM-Assisted Tuning (`llm_assistant.py`)
- Feeds judge rationales to an LLM
- Asks: "Based on these failures, suggest 1-3 rules to add"
- Returns actionable bullet points, not meta-instructions

**Output Format:**
```
- Always include verification details such as member ID and date of birth
- Specify exact timeframes for actions (e.g., '3-5 business days', not 'soon')
- Include specific medication names, pharmacy names, and plan codes when mentioned
```

**Apply Logic (`apply.py`):**
- Parses diff-style suggestions
- Shows unified diff preview
- Applies changes to prompt file
- Creates backup

---

### 6. Audit & Cost Tracking (`app/audit.py`, `app/cost.py`)

**Audit Trail (`calls.jsonl`):**
```json
{
  "ts": "2025-10-02T12:15:00.000Z",
  "run_id": "20251002_121500",
  "phase": "summarize",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "temperature": 0.7,
  "seed": null,
  "request_id": "chatcmpl-...",
  "latency_ms": 1234.5,
  "messages_digest_in": "sha256...",
  "response_digest_out": "sha256...",
  "usage": {
    "prompt_tokens": 500,
    "completion_tokens": 100,
    "total_tokens": 600
  },
  "cost_usd": 0.0012,
  "status": "ok"
}
```

**Cost Calculator:**
- Provider-specific pricing from `configs/models.yaml`
- Formula: `(prompt_tokens * price_per_1k_in + completion_tokens * price_per_1k_out) / 1000`
- Session totals aggregated in UI

---

### 7. Data Consistency (`streamlit_app.py`)

**Problem:** After regenerating transcripts, old summaries/evals shouldn't display

**Solution:** ID-based alignment checking

```python
def load_sample_summaries():
    # Load current transcript IDs
    current_ids = {t['call_id'] for t in transcripts}
    
    # For each run with summaries:
    summary_ids = {s['transcript_id'] for s in summaries}
    
    # Only show if perfect match
    if summary_ids == current_ids:
        return summaries
    else:
        return []  # Force user to re-run
```

**Applied to:**
- Sample summaries display
- Sample evaluations display
- Chart/report data loading

**Result:** Guaranteed data consistency, no stale artifacts

---

## CLI Design

**Command Pattern with Run Management:**

```bash
# Generate creates a new run
python -m app.cli generate --provider openai --model small --N 10
# → Creates runs/20251002_121500/

# Subsequent commands use latest run
python -m app.cli summarize --provider openai --model small
# → Writes to runs/20251002_121500/summaries.jsonl

python -m app.cli judge --provider openai --model small
# → Writes to runs/20251002_121500/evaluations.jsonl

python -m app.cli tune --use-llm
# → Writes to runs/20251002_121500/prompts.diff.md
```

**Run Directory Structure:**
```
runs/20251002_121500/
├── calls.jsonl          # Audit trail
├── summaries.jsonl      # Task outputs
├── evaluations.jsonl    # Judge outputs
├── prompts.diff.md      # Suggested changes
└── report.md            # Aggregate stats
```

---

## Streamlit UI Architecture

**Single-Page Design:**
- All pipeline steps visible at once
- Live progress tracking via subprocess parsing
- Real-time terminal output in "command log"
- Session state for cost/token tracking

**State Management:**
```python
st.session_state.session_totals = {
    'input_tokens': 0,
    'output_tokens': 0,
    'total_cost': 0.0
}
```

**Subprocess Pattern:**
```python
proc = subprocess.Popen(
    ["python", "-m", "app.cli", "summarize", ...],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

for line in iter(proc.stdout.readline, ''):
    # Parse progress: "Progress: X/Y summaries completed"
    # Update UI in real-time
```

---

## Concurrency Model

**Pattern:** ThreadPoolExecutor for I/O-bound LLM calls

```python
with ThreadPoolExecutor(max_workers=workers) as executor:
    futures = {executor.submit(process_one, item): item for item in items}
    
    for future in as_completed(futures):
        result = future.result()
        # Handle result, update progress
```

**Benefits:**
- Simple to understand
- Works within Python's GIL (I/O-bound)
- Easy error handling per-item
- Progress tracking straightforward

**Typical Performance:**
- 5 workers: ~60 summaries/min (limited by API latency)
- Scales linearly up to provider rate limits

---

## Error Handling Strategy

**Graceful Degradation:**
1. **Provider errors** → Log, return stub, continue
2. **JSON parse errors** → Robust extraction with regex fallbacks
3. **Missing data** → Return empty, show instructive message
4. **API rate limits** → (Future) Exponential backoff

**Audit Trail:**
- Every call logged, even failures
- Status field: "ok" | "error"
- Error message captured
- Enables post-mortem analysis

---

## Key Design Decisions

### 1. Native SDKs over LangChain
**Why:** Maximum control, minimal abstraction overhead, easier debugging

### 2. JSONL for All Data
**Why:** Streamable, append-friendly, git-friendly, human-readable

### 3. Timestamp-based Run IDs
**Why:** Natural sorting, no collisions, encodes temporal information

### 4. Concurrent by Default
**Why:** LLM calls are I/O-bound, parallelism is essential for reasonable throughput

### 5. Strict ID Lineage
**Why:** Prevents data consistency bugs, enables debugging, supports reproducibility

### 6. Prompts in Plain Text Files
**Why:** Git-friendly, easy to diff, no code changes needed for iteration

### 7. Single-Page UI
**Why:** See entire pipeline at once, understand narrative flow

---

## Future Enhancements

### Short-term
- [x] Add Anthropic/Google provider implementations
- [ ] Token estimation when usage unavailable
- [ ] Configurable retry logic for rate limits
- [ ] Export reports as PDF

### Medium-term
- [ ] Multi-run comparison charts
- [ ] A/B test framework for prompts
- [ ] Custom rubric editor in UI
- [ ] Word-specific heuristic adjustments (i.e. auto-apply term subs for increased emphasis)
- [ ] Batch API support for cost savings

### Long-term
- [ ] Integration with training pipelines (RL feedback)
- [ ] Real-time human labeling interface
- [ ] Disagreement analysis (multiple judges)
- [ ] Auto-discovery of failure modes

---

## Performance Characteristics

**Typical Run (10 samples):**
```
Generate:   ~15s  (5 workers, ~3s/sample)
Summarize:  ~8s  (5 workers, ~2s/sample)
Judge:      ~20s  (5 workers, ~4s/sample)
Total:      ~45s  (~4s/sample end-to-end)
Cost:       ~$0.005 (per sample using gpt-4o-mini)
```

**Scalability:**
- Linear scaling with worker count (up to rate limits)
- Cost scales linearly with sample count
- Storage is minial: ~100KB per run (10 samples)

---

## Testing Strategy

**Unit Tests:**
- Provider contract tests (mock responses)
- Rubric gate logic
- Cost calculation accuracy

**Integration Tests:**
- End-to-end pipeline with mocked provider
- Verifies all phases run without errors
- Checks output file structure

**Manual Testing:**
- Full pipeline with real API keys
- UI walkthrough
- Prompt iteration cycle

---

## Security Considerations

- **API Keys:** Never committed, loaded from `.env`
- **PII/PHI:** Synthetic data only, no real transcripts
- **Audit Trail:** Digests instead of full message content
- **Dependencies:** Pinned versions, regular updates

---

## Monitoring & Observability

**What We Track:**
- Per-call latency
- Token counts (input/output)
- Cost per call and per run
- Success/failure rates
- Score distributions

**Where:**
- `calls.jsonl` - Complete audit trail
- Terminal output - Real-time progress
- UI metrics - Session aggregates
- Reports - Run summaries
