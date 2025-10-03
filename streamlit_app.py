import json
import subprocess
import time
from html import escape as html_escape
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from streamlit.components.v1 import html as components_html

# Paths relative to project root
BASE_DIR = Path(__file__).resolve().parent
RUNS_DIR = BASE_DIR / "runs"
DATA_DIR = BASE_DIR / "data"


def safe_load_jsonl(path: Path, limit: int = 2):
    items = []
    if not path.exists():
        return items
    try:
        with path.open() as f:
            for line in f:
                if line.strip():
                    items.append(json.loads(line))
                if len(items) >= limit:
                    break
    except Exception:
        return []
    return items


def load_sample_transcripts(runs_dir: Path, limit: int = 2):
    # Always load from the main data directory (the source of truth)
    backup = DATA_DIR / "transcripts.jsonl"
    if backup.exists():
        # Load all items first to sort them
        all_items = []
        with backup.open() as f:
            for line in f:
                if line.strip():
                    all_items.append(json.loads(line))
        # Sort by call_id to ensure consistent order
        all_items.sort(key=lambda x: x.get("call_id", ""))
        return all_items[:limit]
    return []


def load_sample_summaries(runs_dir: Path, limit: int = 2):
    if not runs_dir.exists():
        return []

    # Load current transcript IDs
    transcript_file = DATA_DIR / "transcripts.jsonl"
    if not transcript_file.exists():
        return []

    current_transcript_ids = set()
    with open(transcript_file) as f:
        for line in f:
            if line.strip():
                t = json.loads(line)
                current_transcript_ids.add(t.get("call_id"))

    # Find the most recent run with summaries that match EXACTLY the current transcripts
    latest = sorted(runs_dir.glob("*/summaries.jsonl"), reverse=True)
    for file_path in latest:
        all_items = []
        with file_path.open() as f:
            for line in f:
                if line.strip():
                    all_items.append(json.loads(line))

        # Check if ALL summary transcript_ids match current transcripts
        summary_transcript_ids = {s.get("transcript_id", s.get("call_id")) for s in all_items}

        # Only show if there's perfect alignment (same IDs, same count)
        if summary_transcript_ids == current_transcript_ids:
            # Sort by transcript_id to match transcript order
            all_items.sort(key=lambda x: x.get("transcript_id", x.get("call_id", "")))
            return all_items[:limit]

    # No matching run found - return empty to force user to run summarize
    return []


def load_sample_evals(runs_dir: Path, limit: int = 2):
    if not RUNS_DIR.exists():
        return []

    # Load current transcript IDs
    transcript_file = DATA_DIR / "transcripts.jsonl"
    if not transcript_file.exists():
        return []

    current_transcript_ids = set()
    with open(transcript_file) as f:
        for line in f:
            if line.strip():
                t = json.loads(line)
                current_transcript_ids.add(t.get("call_id"))

    # Find the most recent run with evaluations that match EXACTLY the current transcripts
    latest = sorted(RUNS_DIR.glob("*/evaluations.jsonl"), reverse=True)
    for file_path in latest:
        all_items = []
        with file_path.open() as f:
            for line in f:
                if line.strip():
                    all_items.append(json.loads(line))

        # Check if ALL evaluation transcript_ids match current transcripts
        eval_transcript_ids = {e.get("transcript_id", e.get("call_id")) for e in all_items}

        # Only show if there's perfect alignment (same IDs, same count)
        if eval_transcript_ids == current_transcript_ids:
            # Sort by transcript_id to match transcript order
            all_items.sort(key=lambda x: x.get("transcript_id", x.get("call_id", "")))
            return all_items[:limit]

    # No matching run found - return empty to force user to run judge
    return []


# Import our modules
from app.ui.styles import CUSTOM_CSS

# Page config
st.set_page_config(
    page_title="Summary Eval & Iteration Demo", page_icon="📞", layout="wide", initial_sidebar_state="expanded"
)

# Apply custom styling
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Header
st.markdown(
    """
<div style='text-align: center; padding: 2rem 0 1rem 0;'>
    <h1 style='font-size: 3rem; margin-bottom: 0; background: linear-gradient(135deg, #22d3ee 0%, #6366f1 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
    Summary Eval and Iterative Prompt Enahcement
</h1>
    <p style='color: rgba(226, 232, 240, 0.8); font-size: 1.15rem; margin-top: 0.5rem; font-weight: 500;'>
    Generate | Evaluate | Iterate
</p>
</div>
""",
    unsafe_allow_html=True,
)

st.divider()

# Initialize session state
if "session_totals" not in st.session_state:
    st.session_state.session_totals = {"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0}
if "pipeline_running" not in st.session_state:
    st.session_state.pipeline_running = False
if "last_run_dir" not in st.session_state:
    st.session_state.last_run_dir = None
if "run_log" not in st.session_state:
    st.session_state.run_log = []
if "live_samples" not in st.session_state:
    st.session_state.live_samples = {"transcripts": [], "summaries": [], "evaluations": []}

# Sidebar
with st.sidebar:
    st.markdown("### 🔑 API Keys")

    # Load existing API keys from .env if available
    env_file = Path(".env")
    existing_keys = {}
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, val = line.strip().split("=", 1)
                    existing_keys[key] = val

    openai_default = existing_keys.get("OPENAI_API_KEY", "")
    anthropic_default = existing_keys.get("ANTHROPIC_API_KEY", "")
    google_default = existing_keys.get("GOOGLE_API_KEY", "")

    openai_key = st.text_input(
        "OpenAI API Key",
        value=openai_default[:8] + "..." if openai_default else "",
        type="password",
        key="openai_key",
        help="Enter your OpenAI API key",
    )
    anthropic_key = st.text_input(
        "Anthropic API Key",
        value=anthropic_default[:8] + "..." if anthropic_default else "",
        type="password",
        key="anthropic_key",
        help="Enter your Anthropic API key",
    )
    google_key = st.text_input(
        "Google API Key",
        value=google_default[:8] + "..." if google_default else "",
        type="password",
        key="google_key",
        help="Enter your Google API key",
    )

    # Show which providers are active
    active_providers = []
    if openai_default or openai_key:
        active_providers.append("🟢 OpenAI")
    if anthropic_default or anthropic_key:
        active_providers.append("🟢 Anthropic")
    if google_default or google_key:
        active_providers.append("🟢 Google")

    if active_providers:
        st.success(f"Active: {', '.join(active_providers)}")
    else:
        st.warning("⚠️ No API keys configured")

    st.divider()
    st.markdown("### 📊 Session Totals")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Input Tokens", f"{st.session_state.session_totals['input_tokens']:,}", delta=None)
    with col2:
        st.metric("Output Tokens", f"{st.session_state.session_totals['output_tokens']:,}", delta=None)

    st.metric("💰 Total Cost", f"${st.session_state.session_totals['total_cost']:.4f}", delta=None)

    if st.session_state.session_totals["total_cost"] > 0:
        if st.button("🔄 Reset Session", type="secondary", use_container_width=True):
            st.session_state.session_totals = {"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0}
            st.rerun()


# Helper utilities
def append_run_log(message: str) -> None:
    if message is None:
        return
    if isinstance(message, str) and message.strip() == "":
        st.session_state.run_log.append("")
    else:
        st.session_state.run_log.append(message)
    # Trim the log to avoid unbounded growth
    if len(st.session_state.run_log) > 800:
        st.session_state.run_log = st.session_state.run_log[-800:]


def run_cli_command(label: str, args: list[str]) -> bool:
    append_run_log("")
    append_run_log(f"▶ {label}")
    append_run_log(f"$ {' '.join(args)}")

    result = subprocess.run(args, capture_output=True, text=True, cwd=str(BASE_DIR))

    if result.stdout:
        append_run_log(result.stdout.rstrip())
    if result.stderr:
        append_run_log(result.stderr.rstrip())

    if result.returncode == 0:
        append_run_log(f"✓ {label} completed successfully")
        return True
    append_run_log(f"✗ {label} failed (exit code {result.returncode})")
    return False


# ---------- Unified, compact one-page layout helpers ----------
def update_session_totals_from_calls(run_dir: Path) -> None:
    try:
        calls_path = run_dir / "calls.jsonl"
        if not calls_path.exists():
            return
        if "accounted_offsets" not in st.session_state:
            st.session_state.accounted_offsets = {}
        offsets: dict[str, int] = st.session_state.accounted_offsets
        run_id = run_dir.name
        start_idx = int(offsets.get(run_id, 0))
        processed = 0
        add_in = 0
        add_out = 0
        add_cost = 0.0
        with calls_path.open() as f:
            for i, line in enumerate(f):
                if i < start_idx:
                    continue
                if not line.strip():
                    continue
                processed += 1
                try:
                    rec = json.loads(line)
                    usage = rec.get("usage") or {}
                    add_in += int(usage.get("prompt_tokens") or 0)
                    add_out += int(usage.get("completion_tokens") or 0)
                    c = rec.get("cost_usd")
                    if isinstance(c, (int, float)):
                        add_cost += float(c)
                except Exception:
                    continue
        if processed:
            st.session_state.session_totals["input_tokens"] += add_in
            st.session_state.session_totals["output_tokens"] += add_out
            st.session_state.session_totals["total_cost"] += add_cost
            offsets[run_id] = start_idx + processed
    except Exception:
        pass


def get_latest_run_dir(required_files: list[str] | None = None) -> Path | None:
    required_files = required_files or []
    if not RUNS_DIR.exists():
        return None
    for run_path in sorted(RUNS_DIR.iterdir(), reverse=True):
        if not run_path.is_dir():
            continue
        ok = True
        for name in required_files:
            if not (run_path / name).exists():
                ok = False
                break
        if ok:
            return run_path
    return None


def load_evaluations_df(run_dir: Path) -> pd.DataFrame | None:
    try:
        evals_path = run_dir / "evaluations.jsonl"
        if not evals_path.exists():
            return None

        # Load current transcript IDs to verify alignment
        transcript_file = DATA_DIR / "transcripts.jsonl"
        if not transcript_file.exists():
            return None

        current_transcript_ids = set()
        with open(transcript_file) as f:
            for line in f:
                if line.strip():
                    t = json.loads(line)
                    current_transcript_ids.add(t.get("call_id"))

        # Load evaluations
        rows = []
        with evals_path.open() as f:
            for line in f:
                if not line.strip():
                    continue
                rows.append(json.loads(line))

        if not rows:
            return None

        # Verify all evaluations match current transcripts
        eval_transcript_ids = {e.get("transcript_id", e.get("call_id")) for e in rows}
        if eval_transcript_ids != current_transcript_ids:
            # Misalignment detected - return None to hide stale data
            return None

        # Normalize to rows of dimensions
        data = []
        for e in rows:
            call_id = e.get("call_id")
            scores = e.get("scores", {})
            for dim, score in scores.items():
                data.append({"call_id": call_id, "dimension": dim, "score": score})
        return pd.DataFrame(data)
    except Exception:
        return None


# ---------- Unified, compact one-page layout ----------
st.markdown("## ✨ Unified Evaluation & Feedback Loop")
st.markdown(
    "*An end-to-end pipeline demonstrating production-grade eval infrastructure: deterministic sampling, concurrent execution, structured outputs, LLM-as-judge scoring, and automated prompt optimization. Each step produces versioned, auditable artifacts that integrate into training feedback loops.*"
)
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# Compact settings row (one place for per-phase selections)
col_cfg1, col_cfg2 = st.columns([1, 2])
with col_cfg1:
    st.markdown("**🔧 Provider & Model (applies to all steps)**")
    provider_all = st.selectbox("Provider", ["openai", "anthropic", "google"], key="u_provider_all")
    model_all = st.selectbox("Model", ["small", "large"], key="u_model_all")
    workers_all = st.number_input(
        "Workers", min_value=1, max_value=32, value=5, step=1, help="Concurrent API calls per step"
    )
with col_cfg2:
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

st.divider()

# 1) Generate
with st.container():
    st.markdown("### 1️⃣ Generate (Transcripts)")
    st.markdown(
        "*Synthetic data generation through LLM-powered simulation. Enables rapid iteration on evaluation harnesses without dependencies on production systems or sensitive user data. Reproducibility comes from seeded sampling and versioned prompt templates—critical for tracking model behavior changes over time.*"
    )
    c1, c2 = st.columns([1, 3])
    with c1:
        n_samples = st.number_input("# Samples", min_value=1, max_value=200, value=10, step=5, key="u_n")
        regenerate_mode = st.checkbox("Regenerate (delete & replace)", value=False, key="u_regen")
        if st.button("Run Generate", key="u_btn_gen", type="primary", use_container_width=True):
            gen_args = [
                "python",
                "-m",
                "app.cli",
                "generate",
                "--provider",
                provider_all,
                "--model",
                model_all,
                "--N",
                str(n_samples),
            ]
            if regenerate_mode:
                gen_args.append("--regenerate")
            with st.status(
                f"Generating transcripts with {int(workers_all)} concurrent workers...", expanded=True
            ) as status:
                # Live progress (re-use existing logic)
                append_run_log("")
                append_run_log("▶ 1️⃣ Generate")
                append_run_log(f"$ {' '.join(gen_args)}")
                import re

                progress_ph = st.empty()
                progress_ph.text(f"Progress: 0/{n_samples}")
                gen_args += ["--workers", str(int(workers_all))]
                proc = subprocess.Popen(
                    gen_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(BASE_DIR), bufsize=1
                )
                for line in iter(proc.stdout.readline, ""):
                    if not line:
                        break
                    append_run_log(line.rstrip())
                    if "Progress:" in line or "already has" in line:
                        m = re.search(r"Progress: (\d+)/(\d+)", line)
                        if m:
                            progress_ph.text(f"Progress: {m.group(1)}/{m.group(2)} transcripts")
                        m2 = re.search(r"already has (\d+) transcripts \(target: (\d+)\)", line)
                        if m2:
                            progress_ph.text(f"Progress: {m2.group(1)}/{m2.group(2)} transcripts (already exists)")
                try:
                    proc.wait(timeout=900)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    append_run_log("[error] Generate timed out after 900s")
                err = proc.stderr.read()
                if err:
                    append_run_log(err.rstrip())
                ok = proc.returncode == 0
                if ok:
                    st.success("✅ Generation complete!")
                    status.update(label="✅ Generation complete!", state="complete")
                    latest = get_latest_run_dir([])
                    if latest:
                        update_session_totals_from_calls(latest)
                    time.sleep(0.5)
                    st.rerun()
                else:
                    last_err = "\n".join((err or "").splitlines()[-10:])
                    st.error("❌ Generation failed\n" + last_err)
                    status.update(label="❌ Failed", state="error")
    with c2:
        st.markdown("**Live Samples: Transcripts**")
        st.markdown("<div style='margin-top:6px'></div>", unsafe_allow_html=True)
        samples = load_sample_transcripts(RUNS_DIR, limit=2)
        if samples:
            for t in samples:
                transcript_id = t.get("call_id", "unknown")
                with st.expander(f"📞 {transcript_id}"):
                    st.caption(f"**LOB:** {t.get('lob', 'N/A')}")
                    if "transcript" in t and t["transcript"]:
                        st.text(t["transcript"])
                    elif "segments" in t:
                        for s in t["segments"][:12]:
                            st.markdown(f"**{s.get('speaker','?').title()}:** {s.get('text','')}")
        else:
            st.caption("Run Generate to populate transcripts.")

st.divider()

# 2) Summarize
with st.container():
    st.markdown("### 2️⃣ Summarize")
    st.markdown(
        "*The task being evaluated: structured extraction from conversational transcripts. Concurrent workers enable throughput scaling while maintaining deterministic outputs via temperature and seed control. Each summary links to its source transcript through traceable IDs—essential for debugging failure modes and understanding distribution shifts.*"
    )
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("Run Summarize", key="u_btn_sum", type="primary", use_container_width=True):
            with st.status(
                f"Generating summaries with {int(workers_all)} concurrent workers...", expanded=True
            ) as status:
                append_run_log("")
                append_run_log("▶ 2️⃣ Summarize")
                sum_args = [
                    "python",
                    "-m",
                    "app.cli",
                    "summarize",
                    "--provider",
                    provider_all,
                    "--model",
                    model_all,
                    "--workers",
                    str(int(workers_all)),
                ]
                append_run_log(f"$ {' '.join(sum_args)}")
                import re

                ph = st.empty()
                ph.text("Progress: 0/? summaries")
                p = subprocess.Popen(
                    sum_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(BASE_DIR), bufsize=1
                )
                for line in iter(p.stdout.readline, ""):
                    if not line:
                        break
                    append_run_log(line.rstrip())
                    if "Progress:" in line:
                        m = re.search(r"Progress: (\d+)/(\d+)", line)
                        if m:
                            ph.text(f"Progress: {m.group(1)}/{m.group(2)} summaries")
                try:
                    p.wait(timeout=1200)
                except subprocess.TimeoutExpired:
                    p.kill()
                    append_run_log("[error] Summarize timed out after 1200s")
                err = p.stderr.read()
                if err:
                    append_run_log(err.rstrip())
                ok = p.returncode == 0
                if ok:
                    st.success("✅ Summarization complete!")
                    status.update(label="✅ Summarization complete!", state="complete")
                    latest = get_latest_run_dir(["summaries.jsonl"]) or get_latest_run_dir([])
                    if latest:
                        update_session_totals_from_calls(latest)
                    time.sleep(0.5)
                    st.rerun()
                else:
                    last_err = "\n".join((err or "").splitlines()[-10:])
                    st.error("❌ Summarization failed\n" + last_err)
                    status.update(label="❌ Failed", state="error")
    with c2:
        st.markdown("**Live Samples: Summaries**")
        st.markdown("<div style='margin-top:6px'></div>", unsafe_allow_html=True)
        smps = load_sample_summaries(RUNS_DIR, limit=2)
        if smps:
            for s in smps:
                summary_id = s.get("summary_id", s.get("call_id", "unknown"))
                transcript_id = s.get("transcript_id", s.get("call_id", "unknown"))
                with st.expander(f"📝 {summary_id}"):
                    st.caption(f"**From Transcript:** {transcript_id}")
                    if "intent" in s:
                        st.markdown(f"**Intent:** {s.get('intent','—')}")
                    if "resolution" in s:
                        st.markdown(f"**Resolution:** {s.get('resolution','—')}")
                    if "next_steps" in s:
                        st.markdown(f"**Next Steps:** {s.get('next_steps','—')}")
                    if "sentiment" in s:
                        st.markdown(f"**Sentiment:** {s.get('sentiment','—')}")
        else:
            st.caption("Run Summarize to populate summaries.")

st.divider()

# 3) Judge
with st.container():
    st.markdown("### 3️⃣ Judge")
    st.markdown(
        "*LLM-as-judge evaluation with multi-dimensional rubrics and structured rationales. Transforms subjective quality into defensible, reproducible signals. Rationales enable root-cause analysis and inform targeted prompt improvements—the feedback loop that drives model behavior refinement.*"
    )
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("Run Judge", key="u_btn_judge", type="primary", use_container_width=True):
            with st.status(
                f"Evaluating summaries with {int(workers_all)} concurrent workers...", expanded=True
            ) as status:
                append_run_log("")
                append_run_log("▶ 3️⃣ Judge")
                judge_args = [
                    "python",
                    "-m",
                    "app.cli",
                    "judge",
                    "--provider",
                    provider_all,
                    "--model",
                    model_all,
                    "--workers",
                    str(int(workers_all)),
                ]
                append_run_log(f"$ {' '.join(judge_args)}")
                import re

                ph = st.empty()
                ph.text("Progress: 0/? evaluations")
                p = subprocess.Popen(
                    judge_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(BASE_DIR), bufsize=1
                )
                for line in iter(p.stdout.readline, ""):
                    if not line:
                        break
                    append_run_log(line.rstrip())
                    if "Progress:" in line:
                        m = re.search(r"Progress: (\d+)/(\d+)", line)
                        if m:
                            ph.text(f"Progress: {m.group(1)}/{m.group(2)} evaluations")
                try:
                    p.wait(timeout=1800)
                except subprocess.TimeoutExpired:
                    p.kill()
                    append_run_log("[error] Judge timed out after 1800s")
                err = p.stderr.read()
                if err:
                    append_run_log(err.rstrip())
                ok = p.returncode == 0
                if ok:
                    st.success("✅ Evaluation complete!")
                    status.update(label="✅ Evaluation complete!", state="complete")
                    latest = get_latest_run_dir(["evaluations.jsonl"]) or get_latest_run_dir([])
                    if latest:
                        update_session_totals_from_calls(latest)
                    time.sleep(0.5)
                    st.rerun()
                else:
                    last_err = "\n".join((err or "").splitlines()[-10:])
                    st.error("❌ Evaluation failed\n" + last_err)
                    status.update(label="❌ Failed", state="error")
    with c2:
        st.markdown("**Live Samples: Evaluations**")
        st.markdown("<div style='margin-top:6px'></div>", unsafe_allow_html=True)
        evs = load_sample_evals(RUNS_DIR, limit=2)
        if evs:
            for e in evs:
                evaluation_id = e.get("evaluation_id", e.get("call_id", "unknown"))
                summary_id = e.get("summary_id", "N/A")
                transcript_id = e.get("transcript_id", e.get("call_id", "unknown"))
                with st.expander(f"⚖️ {evaluation_id}"):
                    st.caption(f"**Summary:** {summary_id} → **Transcript:** {transcript_id}")
                    st.write("**Overall Pass:**", "✅" if e.get("overall_pass") else "❌")
                    if e.get("scores"):
                        st.json(e["scores"])
        else:
            st.caption("Run Judge to populate evaluations.")

st.divider()

# 4) Improve & Report (graph left, prompt + diff right)
st.markdown("### 4️⃣ Improve & Report")
st.markdown(
    "*Closing the loop: aggregate metrics reveal system-level performance while LLM-assisted prompt tuning generates targeted improvements from judge rationales. Visual distribution analysis surfaces outliers and edge cases. Apply suggested changes and re-run to measure lift—the compounding cycle that systematically raises quality bars.*"
)
left, right = st.columns([2, 2])
with left:
    run_for_chart = get_latest_run_dir(["evaluations.jsonl"]) or get_latest_run_dir([])
    df = load_evaluations_df(run_for_chart) if run_for_chart else None
    if df is not None and not df.empty:
        st.markdown("**Evaluation Distribution (latest run)**")
        chart = (
            alt.Chart(df)
            .mark_boxplot(size=40, median={"color": "#ffffff"})
            .encode(
                x=alt.X("dimension:N", title="Dimension"), y=alt.Y("score:Q", title="Score"), color=alt.value("#ffffff")
            )
            .properties(height=520)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.caption("Run Judge to populate the chart.")

with right:
    st.markdown("**Summarizer Prompt & Suggested Diff**")
    st.markdown("<div style='margin-top:6px'></div>", unsafe_allow_html=True)
    prompt_path = Path("configs/prompts/summarizer.system.txt")
    diff_path = get_latest_run_dir(["prompts.diff.md"]) or get_latest_run_dir([])
    diff_file = diff_path / "prompts.diff.md" if diff_path else None
    if prompt_path.exists():
        with open(prompt_path) as f:
            prompt_content = f.read()
        with st.expander("Current Prompt", expanded=False):
            st.code(prompt_content, language="text")
    if diff_file and diff_file.exists():
        st.markdown("**💡 Suggested Changes:**")
        diff_content = diff_file.read_text()
        # Parse and render the diff with proper HTML formatting
        diff_lines = diff_content.split("\n")
        formatted_diff = []
        for line in diff_lines:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("Rationale:"):
                continue
            # Handle lines with <span> tags already
            if "<span style=" in line:
                # Extract the content between tags
                if "color:green" in line:
                    import re

                    match = re.search(r"<span[^>]*>(.*?)</span>", line)
                    if match:
                        content = match.group(1).replace("+ ", "")
                        formatted_diff.append(
                            f'<div style="padding: 6px 10px; margin: 4px 0; background: rgba(34, 197, 94, 0.15); border-left: 3px solid #22c55e; border-radius: 4px; color: #86efac;"><strong>+</strong> {content}</div>'
                        )
                elif "color:red" in line:
                    import re

                    match = re.search(r"<span[^>]*>(.*?)</span>", line)
                    if match:
                        content = match.group(1).replace("- ", "")
                        formatted_diff.append(
                            f'<div style="padding: 6px 10px; margin: 4px 0; background: rgba(239, 68, 68, 0.15); border-left: 3px solid #ef4444; border-radius: 4px; color: #fca5a5;"><strong>−</strong> {content}</div>'
                        )
            elif line.startswith("+ "):
                content = line[2:]
                formatted_diff.append(
                    f'<div style="padding: 6px 10px; margin: 4px 0; background: rgba(34, 197, 94, 0.15); border-left: 3px solid #22c55e; border-radius: 4px; color: #86efac;"><strong>+</strong> {content}</div>'
                )
            elif line.startswith("- "):
                content = line[2:]
                formatted_diff.append(
                    f'<div style="padding: 6px 10px; margin: 4px 0; background: rgba(239, 68, 68, 0.15); border-left: 3px solid #ef4444; border-radius: 4px; color: #fca5a5;"><strong>−</strong> {content}</div>'
                )

        if formatted_diff:
            st.markdown(
                f"""
            <div style='background: rgba(15,23,42,0.9); border: 1px solid rgba(148,163,184,0.25); border-radius: 10px; padding: 16px; max-height: 400px; overflow-y: auto;'>
                {''.join(formatted_diff)}
            </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            st.code(diff_content, language="diff")
    else:
        st.caption("Run Tune to generate suggested diffs.")
    if st.button("✅ Apply Diff and Re-run Pipeline", type="primary"):
        with st.status("Applying prompt changes and re-running summarize → judge → report...", expanded=True) as status:
            # 1) Tune with auto-apply
            tune_args = [
                "python",
                "-m",
                "app.cli",
                "tune",
                "--use-llm",
                "--apply",
                "--auto-apply",
                "--provider",
                provider_all,
                "--model",
                model_all,
            ]
            ok1 = run_cli_command("Tune (auto-apply)", tune_args)
            # 2) Summarize
            ok2 = (
                run_cli_command(
                    "Summarize",
                    [
                        "python",
                        "-m",
                        "app.cli",
                        "summarize",
                        "--provider",
                        provider_all,
                        "--model",
                        model_all,
                        "--workers",
                        str(int(workers_all)),
                    ],
                )
                if ok1
                else False
            )
            # 3) Judge
            ok3 = (
                run_cli_command(
                    "Judge",
                    [
                        "python",
                        "-m",
                        "app.cli",
                        "judge",
                        "--provider",
                        provider_all,
                        "--model",
                        model_all,
                        "--workers",
                        str(int(workers_all)),
                    ],
                )
                if ok2
                else False
            )
            # 4) Report
            ok4 = run_cli_command("Report", ["python", "-m", "app.cli", "report"]) if ok3 else False
            if ok4:
                st.success("✅ Applied and re-ran successfully!")
                status.update(label="✅ Completed", state="complete")
                latest = get_latest_run_dir(["evaluations.jsonl"]) or get_latest_run_dir([])
                if latest:
                    update_session_totals_from_calls(latest)
            else:
                st.error("❌ One of the steps failed. See terminal feed below.")
                status.update(label="❌ Failed", state="error")

st.divider()

# Terminal Feed (single, consolidated)
st.markdown("#### 🖥️ Terminal Feed")
log_output = "\n".join(st.session_state.run_log).strip()
if not log_output:
    log_output = "⚡ Output will appear here once you run a step."
components_html(
    f"""
    <div id='cli-log' style='height: 360px; overflow-y: auto; background: rgba(15,23,42,0.92); border-radius: 14px; border: 1px solid rgba(148,163,184,0.25); padding: 16px; font-family: "SFMono-Regular", "Fira Code", monospace; font-size: 13px; color: #e5e7eb; white-space: pre-wrap;'>
        {html_escape(log_output)}
    </div>
    <script>
        const log = document.getElementById('cli-log');
        if (log) {{ log.scrollTop = log.scrollHeight; }}
    </script>
    """,
    height=380,
)

# End of unified layout

st.divider()
st.markdown(
    """
<div style='text-align: center; padding: 1rem; color: #6b7280;'>
    <p style='margin: 0; font-size: 0.85rem;'>Open Source • MIT License • Built with Streamlit</p>
</div>
""",
    unsafe_allow_html=True,
)
