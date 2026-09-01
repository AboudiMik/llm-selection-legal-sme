"""
score_qa.py
-----------
Hybrid Q&A scoring (locked 17 Aug 2026):

  1. Normalised auto-match first (cheap, objective):
     - Yes/No categories: normalise to yes/no; balanced accuracy headline.
     - Free-text (Governing Law, Expiration Date): normalised exact match,
       containment match ("Delaware" in "State of Delaware"), date-parse
       equivalence, and the "not specified" convention for empty gold.
  2. Anything unresolved on the free-text categories goes to the judge
     (run_judge.py) — the verdict file feeds back into this scorer.

Usage:
    ./venv/bin/python src/score_qa.py                # score, list judge queue
    ./venv/bin/python src/score_qa.py --with-judge   # include judge verdicts
"""

import argparse
import glob
import json
import re
from pathlib import Path

import pandas as pd
from dateutil import parser as dateparser

from parsing import normalise

ROOT = Path(__file__).resolve().parent.parent
YES_NO_CATS = {"Termination For Convenience", "Cap On Liability",
               "Ip Ownership Assignment"}
FREE_TEXT_CATS = {"Governing Law", "Expiration Date"}
JUDGE_FILE = ROOT / "results" / "judge_adjudications.jsonl"


def norm_yesno(s: str):
    s = normalise(str(s))
    if s.startswith("yes"):
        return "yes"
    if s.startswith("no") and not s.startswith("not specified"):
        return "no"
    return None


def dates_equal(a: str, b: str) -> bool:
    try:
        return dateparser.parse(a, fuzzy=True).date() == dateparser.parse(b, fuzzy=True).date()
    except Exception:
        return False


def auto_match_freetext(gold: str, ans: str):
    """True/False if auto-decidable, None if it needs the judge."""
    g = normalise(gold) if isinstance(gold, str) and gold.strip() else "not specified"
    a = normalise(ans) if isinstance(ans, str) else ""
    if not a:
        return None
    if g == a:
        return True
    if g == "not specified" or a == "not specified":
        return g == a               # one says not-specified, other doesn't -> mismatch is decisive? no:
    # containment for jurisdictions ("delaware" vs "state of delaware, usa")
    if g in a or a in g:
        return True
    if dates_equal(g, a):
        return True
    return None                      # disagreement -> judge decides


def load_judge_verdicts() -> dict:
    """(model, contract, category) -> verdict bool"""
    v = {}
    if JUDGE_FILE.exists():
        for line in JUDGE_FILE.read_text().splitlines():
            r = json.loads(line)
            v[(r["model_under_test"], r["contract"], r["category"])] = \
                (r["verdict"] == "correct")
    return v


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-judge", action="store_true")
    args = ap.parse_args()

    verdicts = load_judge_verdicts() if args.with_judge else {}
    needs_judge = []
    rows = []

    for f in sorted(glob.glob(str(ROOT / "results/prompt_v2/qa_full__*.csv"))):
        model = Path(f).stem.replace("qa_full__", "")
        df = pd.read_csv(f)
        df = df[df.call_error.isna()]

        # --- Yes/No tiers ---
        yn = df[df.category.isin(YES_NO_CATS)].copy()
        yn["pred"] = yn.model_answer.map(norm_yesno)
        yn["gold"] = yn.gold_answer.map(norm_yesno).fillna("no")  # empty gold = No
        tp = int(((yn.pred == "yes") & (yn.gold == "yes")).sum())
        fp = int(((yn.pred == "yes") & (yn.gold == "no")).sum())
        fn = int(((yn.pred != "yes") & (yn.gold == "yes")).sum())
        tn = int(((yn.pred != "yes") & (yn.gold == "no")).sum())
        tpr = tp / (tp + fn) if tp + fn else float("nan")
        tnr = tn / (tn + fp) if tn + fp else float("nan")

        # --- free-text tiers (hybrid) ---
        ft = df[df.category.isin(FREE_TEXT_CATS)]
        correct = wrong = pending = 0
        for _, r in ft.iterrows():
            m = auto_match_freetext(r.gold_answer, r.model_answer)
            if m is None:
                key = (model, r.contract, r.category)
                if key in verdicts:
                    m = verdicts[key]
                else:
                    pending += 1
                    needs_judge.append({
                        "model_under_test": model, "contract": r.contract,
                        "category": r.category,
                        "gold": r.gold_answer if isinstance(r.gold_answer, str) else "not specified",
                        "answer": r.model_answer})
                    continue
            correct += int(bool(m)); wrong += int(not m)

        rows.append({
            "model": model,
            "yn_balanced_acc": round((tpr + tnr) / 2, 3),
            "yn_pos_precision": round(tp / (tp + fp), 3) if tp + fp else float("nan"),
            "yn_pos_recall": round(tpr, 3),
            "yn_raw_acc": round((tp + tn) / len(yn), 3) if len(yn) else float("nan"),
            "ft_auto_correct": correct, "ft_wrong": wrong,
            "ft_pending_judge": pending,
            "ft_accuracy": round(correct / (correct + wrong), 3) if correct + wrong else float("nan"),
        })

    out = pd.DataFrame(rows)
    print(out.to_string(index=False))
    out.to_csv(ROOT / "results" / "qa_scores.csv", index=False)
    if needs_judge:
        q = ROOT / "results" / "judge_queue.csv"
        pd.DataFrame(needs_judge).to_csv(q, index=False)
        print(f"\n{len(needs_judge)} items queued for judge -> {q}")


if __name__ == "__main__":
    main()
