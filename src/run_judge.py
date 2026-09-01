"""
run_judge.py
------------
Adjudicates Q&A answers the auto-matcher could not decide (results/judge_queue.csv).

Judge: Qwen3.6-Plus via Together — outside all five candidate families
(locked 17 Aug 2026, self-preference mitigation #1). Requires streaming.

Every adjudication is appended to results/judge_adjudications.jsonl WITH the
judge's reasoning — the record feeds (a) the dissertation appendix, (b) the
self-preference analysis (mitigation #2), (c) judge-human agreement on the
20 human spot-checks (mitigation #3).

Usage:
    ./venv/bin/python src/run_judge.py --run
"""

import argparse
import datetime
import json
from pathlib import Path

import pandas as pd

from llm_client import call_model
from parsing import extract_first_json

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "results" / "judge_queue.csv"
OUT = ROOT / "results" / "judge_adjudications.jsonl"
JUDGE_MODEL = "qwen3.6-plus-judge"

SYSTEM_PROMPT = (
    "You are an impartial grader of answers to questions about legal "
    "contracts. You compare a model's answer to a gold reference answer and "
    "decide whether the model's answer is substantively correct. Judge "
    "meaning, not wording. You respond ONLY with a JSON object."
)

USER_TEMPLATE = """Question category: {category}
Gold reference answer: "{gold}"
Model's answer: "{answer}"

Is the model's answer substantively correct — does it convey the same fact as
the gold answer? Notes:
- "not specified" is correct ONLY if the gold answer is also empty/not specified.
- Different formats of the same date are correct.
- A jurisdiction is correct if it names the same governing law
  (e.g. "New York" vs "State of New York, USA").
- Extra hedging or brief elaboration does not make a correct answer wrong.

Respond with ONLY this JSON object:
{{"verdict": "correct" or "incorrect", "reasoning": "<one or two sentences>"}}
"""


def already_judged() -> set:
    done = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            r = json.loads(line)
            done.add((r["model_under_test"], r["contract"], r["category"]))
    return done


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()

    queue = pd.read_csv(QUEUE)
    done = already_judged()
    todo = [r for _, r in queue.iterrows()
            if (r.model_under_test, r.contract, r.category) not in done]
    print(f"{len(todo)} adjudications to run ({len(done)} already done)")
    if not args.run:
        return

    for i, r in enumerate(todo, 1):
        gold = r.gold if isinstance(r.gold, str) and r.gold.strip() else "not specified"
        tag = (f"judge__{r.model_under_test}__{str(r.contract)[:35].replace(' ', '_')}"
               f"__{r.category.replace(' ', '-')}")
        out = call_model(
            JUDGE_MODEL,
            system=SYSTEM_PROMPT,
            user=USER_TEMPLATE.format(category=r.category, gold=gold,
                                      answer=r.answer),
            call_tag=tag,
            max_tokens=8192,     # thinking headroom; Qwen3.6-Plus reasons
            stream=True,          # required by this model
        )
        try:
            parsed = extract_first_json(out["text"])
            verdict = parsed["verdict"]
            reasoning = parsed.get("reasoning", "")
            assert verdict in ("correct", "incorrect")
        except Exception as e:
            verdict, reasoning = "unparseable", f"{type(e).__name__}: {e}"

        record = {
            "ts_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "task": "qa",
            "judge_model": JUDGE_MODEL,
            "model_under_test": r.model_under_test,
            "contract": r.contract,
            "category": r.category,
            "gold": gold,
            "answer": r.answer,
            "verdict": verdict,
            "reasoning": reasoning,
            "judge_tokens_in": out["tokens_in"],
            "judge_tokens_out": out["tokens_out"],
            "judge_cost_usd": (round(out["cost_usd"], 6)
                               if out["cost_usd"] is not None else None),
            "raw_path": Path(out["raw_path"]).relative_to(ROOT).as_posix(),
        }
        with open(OUT, "a") as f:
            f.write(json.dumps(record) + "\n")
        if i % 10 == 0:
            print(f"  {i}/{len(todo)}")

    print(f"done -> {OUT}")


if __name__ == "__main__":
    main()
