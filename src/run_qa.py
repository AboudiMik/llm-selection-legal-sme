"""
run_qa.py
---------
Long-document Q&A task: 3 questions per contract, one per difficulty tier
(locked design, 18 Aug 2026):

  easy      Governing Law            OR  Expiration Date
  moderate  Termination For Convenience (always)
  hard      Cap On Liability         OR  Ip Ownership Assignment

Tier members alternate deterministically by manifest row parity (even rows:
Governing Law + Cap; odd rows: Expiration Date + IP), so both members of each
tier get coverage and the assignment is reproducible without a seed.

Questions use CUAD's official category descriptions verbatim. Gold answers
are the CUAD "-Answer" columns; empty gold means the correct answer is
"not specified" — a hallucination-refusal test, so models are told that
option explicitly.

Same operational guarantees as run_extraction.py: resumable, error-tolerant,
raw responses saved before parsing, everything logged.

Usage:
    ./venv/bin/python src/run_qa.py --model claude-sonnet-5 --run
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from model_config import MODELS
from llm_client import call_model
from parsing import extract_first_json
from pilot_extraction import CATEGORIES  # CUAD official wording (v2)

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "results" / "sample_manifest.csv"

TIERS = ["easy", "moderate", "hard"]

SYSTEM_PROMPT = (
    "You are a legal contract analyst. You answer questions about a contract "
    "with a short, direct answer. You respond ONLY with a JSON object, no "
    "other text."
)

USER_TEMPLATE = """Below is the full text of a contract, followed by a question.

<contract>
{contract_text}
</contract>

Question: {question}
{format_hint}

Respond with ONLY this JSON object (no markdown fences, no commentary):
{{"answer": "<short answer>"}}

Rules:
- Keep the answer short: a name, a date, Yes, or No — not a full clause.
- If the contract does not specify the answer, respond exactly with
  {{"answer": "not specified"}}.
"""

# Per-category answer-format hints, mirroring CUAD's "Answer Format" field.
FORMAT_HINTS = {
    "Governing Law": "Answer with the name of the governing state/country only.",
    "Expiration Date": "Answer with a date (mm/dd/yyyy) if determinable, or 'perpetual' if the term is perpetual.",
    "Termination For Convenience": "Answer Yes or No.",
    "Cap On Liability": "Answer Yes or No.",
    "Ip Ownership Assignment": "Answer Yes or No.",
}


def question_plan(manifest: pd.DataFrame) -> list:
    """(row, tier, category) triples — deterministic by row parity."""
    plan = []
    for i, (_, row) in enumerate(manifest.iterrows()):
        easy = "Governing Law" if i % 2 == 0 else "Expiration Date"
        hard = "Cap On Liability" if i % 2 == 0 else "Ip Ownership Assignment"
        for tier, cat in (("easy", easy),
                          ("moderate", "Termination For Convenience"),
                          ("hard", hard)):
            plan.append((row, tier, cat))
    return plan


def out_path(model_key: str) -> Path:
    return ROOT / "results" / "prompt_v2" / f"qa_full__{model_key}.csv"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=list(MODELS.keys()))
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    model_key = args.model

    manifest = pd.read_csv(MANIFEST)
    outfile = out_path(model_key)
    done = set()
    if outfile.exists():
        prev = pd.read_csv(outfile)
        ok = prev[prev["call_error"].isna()]
        done = set(zip(ok["contract"], ok["category"]))

    plan = [(r, t, c) for r, t, c in question_plan(manifest)
            if (r["txt_name"], c) not in done]

    cfg = MODELS[model_key]
    est_in = int(manifest["word_count"].sum() * 1.39 * 3 / len(manifest) * (len(plan) / 3)) + 294 * len(plan)
    est = (est_in / 1e6) * cfg["usd_per_m_in"] + (len(plan) * 40 / 1e6) * cfg["usd_per_m_out"]
    print(f"[{model_key}] QA: {len(plan)} calls to do ({len(done)} done). Estimated: ${est:.2f}")
    if not args.run:
        return

    header_needed = not outfile.exists()
    for i, (row, tier, cat) in enumerate(plan, 1):
        gold = row[f"{cat}-Answer"]
        tag = (f"qa-v2__{model_key}__{row['txt_name'][:40].replace(' ', '_')}"
               f"__{cat.replace(' ', '-')}")
        rec = {"contract": row["txt_name"], "tier": tier, "category": cat,
               "stratum": row["stratum"], "word_count": row["word_count"],
               "gold_answer": gold if isinstance(gold, str) else ""}
        try:
            out = call_model(
                model_key,
                system=SYSTEM_PROMPT,
                user=USER_TEMPLATE.format(
                    contract_text=Path(row["txt_path"]).read_text(errors="ignore"),
                    question=CATEGORIES[cat],
                    format_hint=FORMAT_HINTS[cat]),
                call_tag=tag,
                max_tokens=512,
            )
            answer, parse_error = None, None
            try:
                answer = extract_first_json(out["text"])["answer"]
            except Exception as e:
                parse_error = f"{type(e).__name__}: {e}"
            rec.update({
                "model_answer": answer, "parse_error": parse_error,
                "call_error": None,
                "tokens_in": out["tokens_in"], "tokens_out": out["tokens_out"],
                "finish_reason": out["finish_reason"],
                "latency_s": round(out["latency_s"], 2),
                "cost_usd": round(out["cost_usd"], 5),
                "raw_path": Path(out["raw_path"]).relative_to(ROOT).as_posix(),
            })
        except Exception as e:
            rec.update({"model_answer": None, "parse_error": None,
                        "call_error": f"{type(e).__name__}: {str(e)[:200]}",
                        "tokens_in": None, "tokens_out": None,
                        "finish_reason": None, "latency_s": None,
                        "cost_usd": None, "raw_path": None})
            print(f"  [{model_key}] CALL ERROR: {rec['call_error'][:120]}")

        pd.DataFrame([rec]).to_csv(outfile, mode="a", header=header_needed, index=False)
        header_needed = False
        if i % 24 == 0:
            print(f"  [{model_key}] {i}/{len(plan)}")

    df = pd.read_csv(outfile)
    print(f"[{model_key}] QA COMPLETE: {df['call_error'].isna().sum()}/{len(df)} ok, "
          f"cost ${df['cost_usd'].sum():.2f}")


if __name__ == "__main__":
    main()
