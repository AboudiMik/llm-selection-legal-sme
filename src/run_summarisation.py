"""
run_summarisation.py
--------------------
Task 3 of 3: structured contract brief (summarisation), one call per contract.

Design locked 19 Aug 2026 (user rulings):
  1. STRUCTURED BRIEF, not free-form prose — five fields: parties, purpose,
     key_obligations, term, risks. Rationale: scoring reliability against
     structured fields beats holistic prose quality; it is the realistic SME
     task (an actionable briefing note); free-form would duplicate Q&A.
  2. Judged on three dimensions (faithfulness / coverage / usability) by
     judge_summaries.py — see that file for the checklist.
  3. Binary checklist items, not Likert.
  4. Per-item failures logged per model (failure-mode analysis).

Mechanics mirror run_extraction.py exactly:
  - RESUMABLE: contracts with a successful row in the output CSV are skipped.
  - ERROR-TOLERANT: a failed call records an error row and moves on; error
    rows are retried on the next invocation (drop them first, as with
    extraction, to avoid duplicate rows).
  - Cost estimate printed BEFORE any spend (working rule 4).
  - Raw responses and per-call tokens/latency/cost land in results/raw/ and
    results/call_log.jsonl via call_model() — nothing new here.

Usage:
    ./venv/bin/python src/run_summarisation.py --model llama-3.3-70b --pilot        # estimate only
    ./venv/bin/python src/run_summarisation.py --model llama-3.3-70b --pilot --run  # 5 contracts
    ./venv/bin/python src/run_summarisation.py --model llama-3.3-70b --run          # full 40
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from model_config import MODELS
from llm_client import call_model
from parsing import extract_first_json
from pilot_extraction import pick_pilot_contracts   # same 5 deterministic pilot contracts

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "results" / "sample_manifest.csv"
OUT_DIR = ROOT / "results" / "summarisation"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# The five brief fields, in scorecard order. A brief must contain exactly
# these keys; presence/non-emptiness is the auto-checked formatting metric
# (the judge never scores formatting — that would waste faithfulness budget).
FIELDS = ["parties", "purpose", "key_obligations", "term", "risks"]

SYSTEM_PROMPT = (
    "You are a legal assistant preparing briefing notes on contracts for a "
    "solicitor at a small law firm. You respond ONLY with a JSON object, "
    "no other text."
)

USER_TEMPLATE = """Below is the full text of a contract, followed by a task.

<contract>
{contract_text}
</contract>

Task: prepare a structured briefing note on this contract with exactly these
five fields:

- "parties": list of the contracting parties, each entry naming the party and
  its role in the agreement (e.g. "Acme Ltd (licensor)").
- "purpose": one or two sentences stating what the agreement is for.
- "key_obligations": list of the main obligations, each entry stating WHICH
  party owes the obligation and what it is.
- "term": the duration, expiration and any renewal arrangements, as a short
  string; use "not specified" if the contract does not state them.
- "risks": list of notable risk allocations a client should be aware of
  (e.g. liability caps, indemnities, unilateral termination rights, IP
  transfers, exclusivity or non-compete restrictions); empty list if none.

Respond with ONLY this JSON object (no markdown fences, no commentary):
{{"parties": ["..."], "purpose": "...", "key_obligations": ["..."], "term": "...", "risks": ["..."]}}

Rules:
- Base every statement solely on the contract text above. Do not invent
  parties, obligations, dates, amounts or rights that are not in the text.
- Summarise in your own words; do not paste long verbatim passages.
"""


def out_path(model_key: str, pilot: bool) -> Path:
    prefix = "pilot_briefs" if pilot else "briefs"
    return OUT_DIR / f"{prefix}__{model_key}.csv"


def load_done(path: Path) -> set:
    """Contracts already briefed successfully (error rows don't count)."""
    if not path.exists():
        return set()
    df = pd.read_csv(path)
    ok = df[df["call_error"].isna()] if "call_error" in df else df
    return set(ok["contract"])


def estimate_cost(contracts: pd.DataFrame, model_key: str) -> float:
    """Pre-run estimate. Input: observed calibration tokens_in = 1.39*words
    + 294/call. Output: a structured brief is longer than an extraction span
    list — assume 450 output tokens/call (to be recalibrated after pilot)."""
    cfg = MODELS[model_key]
    tokens_in = int(contracts["word_count"].sum() * 1.39) + 294 * len(contracts)
    tokens_out = len(contracts) * 450
    return (tokens_in / 1e6) * cfg["usd_per_m_in"] + (tokens_out / 1e6) * cfg["usd_per_m_out"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=list(MODELS.keys()))
    ap.add_argument("--pilot", action="store_true", help="5 pilot contracts only")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    model_key = args.model

    contracts = pick_pilot_contracts() if args.pilot else pd.read_csv(MANIFEST)
    outfile = out_path(model_key, args.pilot)
    done = load_done(outfile)
    todo = [r for _, r in contracts.iterrows() if r["txt_name"] not in done]

    est = estimate_cost(pd.DataFrame([dict(r) for r in todo]) if todo else contracts.head(0),
                        model_key) if todo else 0.0
    print(f"[{model_key}] summarisation: {len(todo)} calls to do "
          f"({len(done)} already done). Estimated cost: ${est:.3f}")
    if not args.run:
        print("Dry run only. Re-run with --run to execute.")
        return

    header_needed = not outfile.exists()
    for i, row in enumerate(todo, 1):
        tag = (f"summary__{model_key}__{row['txt_name'][:40].replace(' ', '_')}")
        rec = {"contract": row["txt_name"], "stratum": row["stratum"],
               "word_count": row["word_count"]}
        try:
            out = call_model(
                model_key,
                system=SYSTEM_PROMPT,
                user=USER_TEMPLATE.format(
                    contract_text=Path(row["txt_path"]).read_text(errors="ignore")),
                call_tag=tag,
                max_tokens=2048,   # thinking models get 8192 headroom in the client
            )
            # strict_json_ok: same instruction-adherence metric as extraction.
            strict_ok = True
            try:
                json.loads(out["text"].strip())
            except Exception:
                strict_ok = False
            # Robust parse + formatting check: all five fields present.
            parsed, parse_error = None, None
            try:
                parsed = extract_first_json(out["text"])
                assert isinstance(parsed, dict)
            except Exception as e:
                parse_error = f"{type(e).__name__}: {e}"
            fields_ok = bool(parsed) and all(
                f in parsed and (parsed[f] or parsed[f] == []) for f in FIELDS)
            rec.update({
                "strict_json_ok": strict_ok, "parse_error": parse_error,
                "fields_ok": fields_ok,
                # The brief itself is re-serialised into the CSV so the judge
                # reads a canonical form; raw response stays in results/raw/.
                "brief_json": json.dumps(parsed) if parsed else None,
                "call_error": None,
                "tokens_in": out["tokens_in"], "tokens_out": out["tokens_out"],
                "finish_reason": out["finish_reason"],
                "latency_s": round(out["latency_s"], 2),
                "cost_usd": round(out["cost_usd"], 5) if out["cost_usd"] is not None else None,
                "raw_path": Path(out["raw_path"]).relative_to(ROOT).as_posix(),
            })
        except Exception as e:
            rec.update({"strict_json_ok": None, "parse_error": None,
                        "fields_ok": None, "brief_json": None,
                        "call_error": f"{type(e).__name__}: {str(e)[:200]}",
                        "tokens_in": None, "tokens_out": None,
                        "finish_reason": None, "latency_s": None,
                        "cost_usd": None, "raw_path": None})
            print(f"  [{model_key}] CALL ERROR on {tag}: {rec['call_error']}")

        pd.DataFrame([rec]).to_csv(outfile, mode="a", header=header_needed, index=False)
        header_needed = False
        if i % 10 == 0:
            print(f"  [{model_key}] {i}/{len(todo)} done")

    df = pd.read_csv(outfile)
    ok = df["call_error"].isna().sum()
    print(f"[{model_key}] COMPLETE: {ok}/{len(df)} calls ok, "
          f"fields ok {int(df['fields_ok'].fillna(False).sum())}, "
          f"cost ${df['cost_usd'].sum():.3f} -> {outfile}")


if __name__ == "__main__":
    main()
