"""
judge_summaries.py
------------------
Judges structured contract briefs (from run_summarisation.py) with the FULL
CONTRACT in the judge's context — the faithfulness dimension requires it
(user ruling 2, 19 Aug 2026: a fabricated obligation is a liability event for
a legal SME, so hallucination measurement is the point of this task).

Judge: Qwen3.6-Plus via Together (outside all five candidate families —
self-preference mitigation, locked 17 Aug 2026). Streaming required.

Rubric (user rulings 3 & 4): TWELVE BINARY items across three dimensions —
pass/fail each, no Likert. Every item verdict + one-sentence reason is logged
per (model, contract) to results/summarisation/judgements.jsonl, so failure
modes are analysable per model (e.g. "fabricates obligations" vs "omits the
term"), not just aggregate rates.

Decision rule stated to the judge: an item FAILS if it cannot be verified
from the contract text — uncertainty is never a pass.

Usage:
    ./venv/bin/python src/judge_summaries.py --pilot          # estimate + queue
    ./venv/bin/python src/judge_summaries.py --pilot --run    # judge pilot briefs
    ./venv/bin/python src/judge_summaries.py --run            # judge full-run briefs
    (aggregate tables print after every invocation, from all judgements on file)
"""

import argparse
import datetime
import glob
import json
from pathlib import Path

import pandas as pd

from model_config import MODELS, cost_usd
from llm_client import call_model
from parsing import extract_first_json

ROOT = Path(__file__).resolve().parent.parent
SUM_DIR = ROOT / "results" / "summarisation"
JUDGE_FILE = SUM_DIR / "judgements.jsonl"
JUDGE_MODEL = "qwen3.6-plus-judge"

# ---------------------------------------------------------------------------
# The checklist. Item codes are stable identifiers — they appear in the
# judgement log, the per-item failure matrix, and (eventually) the appendix.
# Wording is the operative rubric: keep changes versioned in git, never edit
# silently after scoring has started.
# ---------------------------------------------------------------------------
CHECKLIST = {
    "faithfulness": {
        "F1": "Every party named in the brief appears in the contract — no "
              "invented or misnamed parties.",
        "F2": "Every obligation in the brief is traceable to the contract — "
              "no invented obligations, and none attributed to the wrong party.",
        "F3": "The term stated in the brief is consistent with the contract; "
              "'not specified' is claimed only if the contract truly states "
              "no term.",
        "F4": "Every risk in the brief is traceable to the contract — no "
              "invented caps, amounts, rights or restrictions.",
    },
    "coverage": {
        "C1": "All contracting parties are identified in the brief.",
        "C2": "The stated purpose correctly reflects the type and subject "
              "matter of the agreement.",
        "C3": "Material obligations of EACH party are represented — not just "
              "one side's.",
        "C4": "The term/expiration/renewal arrangements are captured, or "
              "correctly reported as not specified.",
        "C5": "The contract's most material risk allocations (e.g. liability "
              "caps, indemnities, unilateral termination rights, IP transfer, "
              "exclusivity) are mentioned where the contract contains them.",
    },
    "usability": {
        "U1": "The brief is self-contained: a reader who has not seen the "
              "contract can understand it without further context.",
        "U2": "The brief is a digest, not a dump: no long verbatim clause "
              "pasting, fields are concise.",
        "U3": "Statements are specific: obligations and risks say who owes "
              "what; no vacuous boilerplate (e.g. 'parties must comply with "
              "their obligations').",
    },
}
ALL_ITEMS = {code: text for dim in CHECKLIST.values() for code, text in dim.items()}
DIM_OF = {code: dim for dim, items in CHECKLIST.items() for code in items}

SYSTEM_PROMPT = (
    "You are an impartial evaluator of contract briefing notes prepared by "
    "an AI assistant for a solicitor. You are given the full contract and the "
    "briefing note, and you grade the note against a fixed binary checklist. "
    "Your only evidence is the contract text: if an item cannot be verified "
    "from the contract, it FAILS. You respond ONLY with a JSON object."
)

USER_TEMPLATE = """Below is the full text of a contract, then a briefing note
about it, then a checklist.

<contract>
{contract_text}
</contract>

<briefing_note>
{brief_json}
</briefing_note>

Grade the briefing note on each checklist item. Every item is strictly
pass/fail — if you cannot verify an item from the contract text, it fails.

Checklist:
{checklist_lines}

Respond with ONLY this JSON object (no markdown fences, no commentary),
with one entry per item code:
{{"F1": {{"pass": true, "reason": "<one sentence>"}}, "F2": {{...}}, ...}}
"""


def checklist_lines() -> str:
    return "\n".join(f"- {code}: {text}" for code, text in ALL_ITEMS.items())


def already_judged(run: str) -> set:
    """Pairs already judged FOR THIS RUN TYPE.

    The run type is part of the key because the pilot and the full run are
    different API calls that produced different brief text for the same
    (model, contract). Keying on (model, contract) alone made a 20 Aug pilot
    verdict count as coverage of a 25 Aug full-run brief the judge had never
    seen — 23 of 59 records were affected before this was caught. Records
    written before this fix carry no "run" field and are all pilot verdicts,
    so they are treated as such.
    """
    done = set()
    if JUDGE_FILE.exists():
        for line in JUDGE_FILE.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("run", "pilot") == run:
                done.add((r["model_under_test"], r["contract"]))
    return done


def load_briefs(pilot: bool) -> pd.DataFrame:
    """All successfully parsed briefs across models, with contract paths."""
    prefix = "pilot_briefs" if pilot else "briefs"
    manifest = pd.read_csv(ROOT / "results" / "sample_manifest.csv")
    paths = manifest.set_index("txt_name")["txt_path"]
    frames = []
    for f in sorted(glob.glob(str(SUM_DIR / f"{prefix}__*.csv"))):
        model = Path(f).stem.replace(f"{prefix}__", "")
        df = pd.read_csv(f)
        df = df[df.call_error.isna() & df.brief_json.notna()].copy()
        df["model"] = model
        df["txt_path"] = df["contract"].map(paths)
        frames.append(df)
    return pd.concat(frames).reset_index(drop=True) if frames else pd.DataFrame()


def estimate(todo: pd.DataFrame) -> float:
    """Judge cost estimate: contract + brief + rubric in, ~700 tokens out
    (12 reasons + reasoning-model overhead is billed as output on Qwen)."""
    tokens_in = int(todo["word_count"].sum() * 1.39) + (450 + 400) * len(todo)
    return cost_usd(JUDGE_MODEL, tokens_in, 700 * len(todo))


def print_tables() -> None:
    """Aggregates from ALL judgements on file: per-dimension pass rates and
    the per-item matrix (user ruling 4 — failure modes, not just rates)."""
    if not JUDGE_FILE.exists():
        return
    rows = []
    for line in JUDGE_FILE.read_text().splitlines():
        r = json.loads(line)
        for code, v in r["items"].items():
            rows.append({"model": r["model_under_test"], "item": code,
                         "dim": DIM_OF.get(code, "?"),
                         "passed": bool(v.get("pass"))})
    df = pd.DataFrame(rows)
    print("\nPer-dimension pass rates (item-level):")
    print(df.pivot_table(index="model", columns="dim", values="passed",
                         aggfunc="mean").round(3).to_string())
    print("\nPer-item pass rates:")
    print(df.pivot_table(index="model", columns="item", values="passed",
                         aggfunc="mean").round(2).to_string())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()

    briefs = load_briefs(args.pilot)
    if briefs.empty:
        print("No briefs found to judge.")
        return
    run_type = "pilot" if args.pilot else "full"
    done = already_judged(run_type)
    todo = briefs[~briefs.apply(lambda r: (r["model"], r["contract"]) in done,
                                axis=1)]
    print(f"{len(todo)} briefs to judge ({len(done)} already judged). "
          f"Estimated judge cost: ${estimate(todo):.2f}" if len(todo)
          else f"0 briefs to judge ({len(done)} already judged).")
    if not args.run:
        print_tables()
        return

    for i, (_, r) in enumerate(todo.iterrows(), 1):
        tag = (f"summary-judge__{r['model']}"
               f"__{r['contract'][:35].replace(' ', '_')}")
        # Error-tolerant like the task runners: a dead call is printed and
        # skipped (it stays unjudged, so the next invocation retries it).
        try:
            out = call_model(
                JUDGE_MODEL,
                system=SYSTEM_PROMPT,
                user=USER_TEMPLATE.format(
                    contract_text=Path(r["txt_path"]).read_text(errors="ignore"),
                    brief_json=r["brief_json"],
                    checklist_lines=checklist_lines()),
                call_tag=tag,
                max_tokens=8192,     # thinking headroom
                stream=True,          # required by this model
            )
        except Exception as e:
            print(f"  CALL ERROR on {tag}: {type(e).__name__}: {str(e)[:200]}")
            continue
        # Parse the 12 verdicts. Missing/extra items or unparseable output are
        # recorded as judge_error — surfaced, never silently scored.
        items, judge_error = None, None
        try:
            parsed = extract_first_json(out["text"])
            items = {code: {"pass": bool(parsed[code]["pass"]),
                            "reason": str(parsed[code].get("reason", ""))}
                     for code in ALL_ITEMS}
        except Exception as e:
            judge_error = f"{type(e).__name__}: {e}"

        record = {
            "ts_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "task": "summarisation",
            "judge_model": JUDGE_MODEL,
            "model_under_test": r["model"],
            "contract": r["contract"],
            "run": run_type,      # pilot vs full: part of the resume key
            "items": items,
            "judge_error": judge_error,
            "judge_tokens_in": out["tokens_in"],
            "judge_tokens_out": out["tokens_out"],
            "judge_cost_usd": (round(out["cost_usd"], 6)
                               if out["cost_usd"] is not None else None),
            "raw_path": Path(out["raw_path"]).relative_to(ROOT).as_posix(),
        }
        if judge_error:
            print(f"  JUDGE ERROR on {tag}: {judge_error}")
            # not appended as a judgement — it stays in todo for a retry
        else:
            with open(JUDGE_FILE, "a") as f:
                f.write(json.dumps(record) + "\n")
        if i % 5 == 0:
            print(f"  {i}/{len(todo)}")

    print_tables()


if __name__ == "__main__":
    main()
