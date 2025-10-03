"""Dataset generator: create synthetic transcripts via LLM (verbose, simple, robust)."""

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from ..provider.base import BaseProvider, Message

# Expanded, more realistic few-shot examples (longer segments + richer flow).
FEW_SHOT_EXAMPLES = r"""
Example 1:
{
  "call_id": "AEP-2025-000001",
  "lob": "Benefits",
  "segments": [
    {"t": "00:00", "speaker": "caller", "text": "Hi there—I'm trying to add my spouse after our wedding and I'm not sure which forms I need."},
    {"t": "00:05", "speaker": "agent", "text": "Congrats! I can help with that. This call may be recorded. Can I confirm your member ID suffix and full name?"},
    {"t": "00:12", "speaker": "caller", "text": "Sure, the ID ends in 4321 and the name on file should be Jamie Rivera."},
    {"t": "00:20", "speaker": "agent", "text": "Thank you, Jamie. I’m pulling up your plan now—one moment."},
    {"t": "00:28", "speaker": "agent", "text": "Okay, I see you’re on the PPO Silver plan. For a qualifying life event like marriage, you have a 30-day window to add a spouse."},
    {"t": "00:38", "speaker": "caller", "text": "Got it. We were married last Friday, so I should be within that window."},
    {"t": "00:45", "speaker": "agent", "text": "Perfect timing. You’ll need a marriage certificate and a dependent add form—both can be uploaded in your member portal."},
    {"t": "00:56", "speaker": "caller", "text": "Do I need the certified copy, or will a scan work?"},
    {"t": "01:01", "speaker": "agent", "text": "A clear scan is fine for submission; if anything else is required, our team will follow up."},
    {"t": "01:09", "speaker": "caller", "text": "What about the effective date and any payroll changes?"},
    {"t": "01:15", "speaker": "agent", "text": "Once approved, coverage is effective the date of the event. Payroll adjustments occur on the next cycle; I’ll include that note in your summary."},
    {"t": "01:26", "speaker": "caller", "text": "Thanks. And ballpark, what will premiums look like when adding a spouse?"},
    {"t": "01:32", "speaker": "agent", "text": "It depends on employer contribution, but your plan’s spouse-add typically increases by a fixed tier amount. I’ll attach the current rate sheet in the portal."},
    {"t": "01:43", "speaker": "caller", "text": "Okay, that helps. Anything else I should know before I submit?"},
    {"t": "01:48", "speaker": "agent", "text": "Just ensure you submit within 30 days and keep an eye on portal messages in case we request clarification."},
    {"t": "01:56", "speaker": "caller", "text": "Sounds good. I appreciate the clear steps."},
    {"t": "02:00", "speaker": "agent", "text": "My pleasure, Jamie. I’m sending a checklist and the upload link now. Anything else today?"},
    {"t": "02:07", "speaker": "caller", "text": "No, that covers it—thanks so much."},
    {"t": "02:11", "speaker": "agent", "text": "You’re all set. Have a great day!"}
  ],
  "metadata": {"duration_s": 131}
}

Example 2:
{
  "call_id": "AEP-2025-000002",
  "lob": "Claims",
  "segments": [
    {"t": "00:00", "speaker": "caller", "text": "Hi, I’m following up on claim number XYZ789. The Explanation of Benefits confused me."},
    {"t": "00:05", "speaker": "agent", "text": "Happy to help. This call may be recorded. Can I verify your full name and date of service noted on the EOB?"},
    {"t": "00:13", "speaker": "caller", "text": "Sure—Alex Chen, and the visit was on June 12th."},
    {"t": "00:19", "speaker": "agent", "text": "Thanks, Alex. One moment while I pull that up…"},
    {"t": "00:25", "speaker": "agent", "text": "I see the claim is pending because the provider’s billing code requires additional documentation."},
    {"t": "00:33", "speaker": "caller", "text": "Does that mean I’ll be billed more? The EOB shows something under 'member responsibility'."},
    {"t": "00:40", "speaker": "agent", "text": "Not necessarily. EOBs aren’t bills. The 'member responsibility' line reflects what could apply after processing—deductible, copay, or coinsurance."},
    {"t": "00:52", "speaker": "caller", "text": "Okay. What happens next?"},
    {"t": "00:55", "speaker": "agent", "text": "We’ve requested notes from the provider to support the code. Once received, the claim finalizes in 7–10 business days."},
    {"t": "01:05", "speaker": "caller", "text": "Can I do anything to speed that up?"},
    {"t": "01:08", "speaker": "agent", "text": "You can call the provider and mention our request; sometimes that nudges things along. I’ll also place a courtesy follow-up on our side."},
    {"t": "01:18", "speaker": "caller", "text": "Appreciate that. If it denies, how do appeals work?"},
    {"t": "01:22", "speaker": "agent", "text": "You’ll get a denial letter with reasons and instructions. Appeals generally allow 180 days from the decision."},
    {"t": "01:31", "speaker": "caller", "text": "Got it. Please add a note that I called today."},
    {"t": "01:34", "speaker": "agent", "text": "Already done—timestamped. We’ll message you when the provider responds."},
    {"t": "01:40", "speaker": "caller", "text": "Thanks for clarifying—super helpful."},
    {"t": "01:43", "speaker": "agent", "text": "Anytime. Anything else I can help with today?"},
    {"t": "01:47", "speaker": "caller", "text": "No, that’s everything."},
    {"t": "01:50", "speaker": "agent", "text": "Have a great day, Alex!"}
  ],
  "metadata": {"duration_s": 110}
}
"""


# --- Constants kept minimal for clarity ---
_ALLOWED_LOBS: tuple[str, ...] = ("Benefits", "Claims", "Pharmacy")
_ALLOWED_SPEAKERS: tuple[str, ...] = ("caller", "agent")
_CALL_ID_PREFIX = "AEP-2025-"
_CALL_ID_WIDTH = 6
_MAX_PER_BATCH = 1  # Generate 1 transcript per LLM call for reliability


class DatasetGenerator:
    """Generate synthetic, verbose transcripts using an LLM."""

    def __init__(self, provider: BaseProvider, output_dir: Path):
        self.provider = provider
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # -------------------- Public API --------------------

    def generate(self, n: int = 50, workers: int = 5) -> list[dict]:
        """Generate N synthetic transcripts (LLM-only; no fallbacks) with concurrent workers."""
        print(f"[generate] Generating {n} synthetic transcripts with {workers} workers...")
        results: list[dict[str, Any]] = []
        completed_count = 0

        def generate_one(idx: int) -> dict[str, Any]:
            """Generate a single transcript."""
            batch = self._call_llm_and_parse(1)
            return batch[0]

        # Use ThreadPoolExecutor for concurrent API calls
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all tasks
            futures = {executor.submit(generate_one, i): i for i in range(n)}

            # Collect results as they complete
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    transcript = future.result()
                    results.append(transcript)
                    completed_count += 1
                    print(f"[generate] Progress: {completed_count}/{n} transcripts completed", flush=True)
                except Exception as e:
                    print(f"[generate] Warning: Failed to generate transcript {idx+1}: {e}", file=sys.stderr)

        # Normalize all transcripts with sequential IDs
        normalized_results = []
        for seq, t in enumerate(results, 1):
            normalized_results.append(self._normalize(t, seq))

        return normalized_results

    def save(self, transcripts: list[dict]):
        """Save transcripts to JSONL and CSV."""
        jsonl_path = self.output_dir / "transcripts.jsonl"
        csv_path = self.output_dir / "transcripts.csv"

        with open(jsonl_path, "w") as f:
            for t in transcripts:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")

        # Flatten for CSV
        import pandas as pd

        df = pd.DataFrame(
            [
                {
                    "call_id": t["call_id"],
                    "lob": t["lob"],
                    "segments_json": json.dumps(t["segments"], ensure_ascii=False),
                    "duration_s": int(t["metadata"]["duration_s"]),
                }
                for t in transcripts
            ]
        )
        df.to_csv(csv_path, index=False)

        print(f"[generate] Saved {len(transcripts)} transcripts to {jsonl_path} and {csv_path}")

    # -------------------- LLM glue --------------------

    def _call_llm_and_parse(self, k: int) -> list[dict[str, Any]]:
        """Ask the LLM for k transcripts; return list of raw dicts. Raises on failure."""
        prompt = self._build_prompt(k)
        messages = [
            Message(
                role="system",
                content=(
                    "You generate realistic, lengthy call-center transcripts for training. "
                    "Honor the JSON schema exactly. Avoid PHI/PII; use placeholders where needed."
                ),
            ),
            Message(role="user", content=prompt),
        ]

        resp = self.provider.generate(messages, max_tokens=8192, temperature=0.8)
        raw_text = getattr(resp, "text", None) or getattr(resp, "content", "")
        if not raw_text or not isinstance(raw_text, str):
            raise RuntimeError("Empty or invalid LLM response")

        json_str = self._extract_json(raw_text, k)
        data = json.loads(json_str)

        # Handle single object (k=1) or array
        if k == 1 and isinstance(data, dict):
            # Single transcript returned as object
            if isinstance(data.get("segments"), list):
                return [data]
            else:
                raise RuntimeError("LLM returned invalid transcript (missing segments)")

        # Allow {"transcripts": [...]} wrapper
        if isinstance(data, dict) and "transcripts" in data and isinstance(data["transcripts"], list):
            data = data["transcripts"]

        if not isinstance(data, list):
            raise RuntimeError("LLM did not return a JSON array of transcripts")

        # Light shape check
        cleaned = [t for t in data if isinstance(t, dict) and isinstance(t.get("segments"), list)]
        if not cleaned:
            raise RuntimeError("LLM returned no valid transcripts")
        return cleaned

    def _build_prompt(self, k: int) -> str:
        """Keep it simple: mirror few-shot length/structure; enforce schema."""
        if k == 1:
            return f"""Generate 1 unique, realistic call-center transcript as a JSON object (no extra text, no array).
The transcript MUST match this schema:
- "call_id": string "AEP-2025-NNNNNN" (unique per transcript; we will normalize later)
- "lob": one of {list(_ALLOWED_LOBS)}
- "segments": array of objects with:
    - "t": strictly increasing "MM:SS" or "HH:MM:SS", starting at "00:00"
    - "speaker": "caller" or "agent"
    - "text": natural utterance (professional tone; light disfluencies ok; no PHI)
- "metadata": {{"duration_s": integer total seconds consistent with last segment}}

STYLE & LENGTH:
- Mirror the examples below for length and detail (≈ 12–20 segments; ~100–150 seconds). ±25% is fine.
- Include greetings, brief verification (use placeholders), explanation of policy/coverage, clarifying Q&A, and a clean wrap-up.
- No markdown fences, no comments, valid JSON only.

Examples to mirror:
{FEW_SHOT_EXAMPLES}
"""

    # -------------------- Normalization --------------------

    def _normalize(self, t: dict[str, Any], seq_num: int) -> dict[str, Any]:
        """Coerce to exact schema, fix timestamps, enforce allowed values, assign call_id."""
        lob = str(t.get("lob", "")).strip().title()
        if lob not in _ALLOWED_LOBS:
            lob = _ALLOWED_LOBS[seq_num % len(_ALLOWED_LOBS)]

        # Normalize segments
        norm_segments = []
        last_s = -1
        for seg in t.get("segments", []):
            if not isinstance(seg, dict):
                continue
            ts = self._parse_ts(seg.get("t", "00:00"))
            if ts <= last_s:
                ts = last_s + 1
            spk = str(seg.get("speaker", "agent")).lower()
            if spk not in _ALLOWED_SPEAKERS:
                spk = _ALLOWED_SPEAKERS[len(norm_segments) % 2]
            text = str(seg.get("text", "")).strip() or "..."
            norm_segments.append({"t": self._fmt_ts(ts), "speaker": spk, "text": text})
            last_s = ts

        if not norm_segments:
            # If the LLM somehow returns zero segments, fail fast—no hidden fallback.
            raise RuntimeError("Transcript had no usable segments after normalization")

        # Duration reconciliation
        last_ts = self._parse_ts(norm_segments[-1]["t"])
        meta = t.get("metadata", {}) if isinstance(t.get("metadata"), dict) else {}
        duration_s = meta.get("duration_s")
        if not isinstance(duration_s, int) or duration_s < last_ts:
            duration_s = last_ts

        # Assign normalized call_id with timestamp
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        call_id = f"TRA-{timestamp}-{seq_num:03d}"

        return {
            "call_id": call_id,
            "lob": lob,
            "segments": norm_segments,
            "metadata": {"duration_s": int(duration_s)},
        }

    # -------------------- Helpers --------------------

    def _extract_json(self, text: str, k: int) -> str:
        """Extract top-level JSON (object for k=1, array for k>1) from messy model output."""
        s = text.strip()
        # Strip markdown fences if present
        s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.IGNORECASE | re.MULTILINE)

        if k == 1:
            # For single transcript, prefer object
            a, b = s.find("{"), s.rfind("}")
            if a != -1 and b != -1 and b > a:
                return s[a : b + 1]

        # For multiple, prefer array
        a, b = s.find("["), s.rfind("]")
        if a != -1 and b != -1 and b > a:
            return s[a : b + 1]

        # Or object with transcripts wrapper
        m = re.search(r'\{[^{}]*"transcripts"\s*:\s*\[.*\}\s*$', s, flags=re.DOTALL)
        if m:
            return m.group(0)

        raise RuntimeError("No JSON payload found in LLM response")

    def _parse_ts(self, ts: str) -> int:
        ts = str(ts).strip()
        parts = ts.split(":")
        try:
            if len(parts) == 2:  # MM:SS
                m, s = int(parts[0]), int(parts[1])
                return m * 60 + s
            if len(parts) == 3:  # HH:MM:SS
                h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
                return h * 3600 + m * 60 + s
        except Exception:
            pass
        return 0

    def _fmt_ts(self, seconds: int) -> str:
        if seconds < 3600:
            m, s = divmod(max(seconds, 0), 60)
            return f"{m:02d}:{s:02d}"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
