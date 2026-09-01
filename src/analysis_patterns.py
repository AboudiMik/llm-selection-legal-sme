"""
analysis_patterns.py
--------------------
Read-only pattern analysis over the completed empirical results.

Design rule: this script NEVER reimplements a scoring rule. It imports the
project's own scorers (score_extraction, score_qa) so every number it prints
is consistent with the published headline tables by construction. If a figure
here disagrees with results/full_scores_v2.csv or results/qa_scores.csv, that
is a bug to investigate, not a new result.

NO API CALLS. Writes only to outputs/analysis/.

Run:  PYTHONPATH=src ./venv/bin/python src/analysis_patterns.py
"""

import json
from pathlib import Path

import pandas as pd

from score_extraction import (load_predictions, load_gold, match_spans,
                              YES_NO_CATS as EXT_YN_CATS, PRIMARY_THRESHOLD)
from score_qa import (norm_yesno, auto_match_freetext, load_judge_verdicts,
                      YES_NO_CATS as QA_YN_CATS, FREE_TEXT_CATS)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "analysis"
OUT.mkdir(parents=True, exist_ok=True)

MODELS = ["claude-sonnet-5", "deepseek-v4-pro", "gemini-3.1-pro",
          "gpt-5.6-terra", "llama-3.3-70b"]
OPEN_WEIGHT = {"deepseek-v4-pro", "llama-3.3-70b"}

MANIFEST = pd.read_csv(ROOT / "results" / "sample_manifest.csv")
WORDS = MANIFEST.set_index("txt_name")["word_count"].to_dict()
STRATUM = MANIFEST.set_index("txt_name")["stratum"].to_dict()


def section(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# ---------------------------------------------------------------------------
# 1. COST AND LATENCY, per model per task
# ---------------------------------------------------------------------------
def cost_table():
    """Total cost / latency per model per task over the FULL runs only.

    Uses the per-run scored files, not call_log.jsonl: those files contain
    exactly the calls that were scored, so pilot calls, retries and abandoned
    calls are excluded by construction.
    """
    rows = []
    for m in MODELS:
        for task, path in [
            ("extraction", f"results/prompt_v2/extraction_full__{m}.csv"),
            ("qa", f"results/prompt_v2/qa_full__{m}.csv"),
            ("summarisation", f"results/summarisation/briefs__{m}.csv"),
        ]:
            d = pd.read_csv(ROOT / path)
            ok = d[d.call_error.isna()]
            rows.append({
                "model": m, "task": task,
                "calls_attempted": len(d), "calls_ok": len(ok),
                "cost_usd": round(ok.cost_usd.sum(), 4),
                "cost_per_contract": round(ok.cost_usd.sum() / 40, 4),
                "mean_latency_s": round(ok.latency_s.mean(), 2),
                "p95_latency_s": round(ok.latency_s.quantile(0.95), 2),
                "tokens_in": int(ok.tokens_in.sum()),
                "tokens_out": int(ok.tokens_out.sum()),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 2. EXTRACTION — per category and per item, using the project's own scorer
# ---------------------------------------------------------------------------
def extraction_detail(threshold=PRIMARY_THRESHOLD):
    per_cat, per_item = [], []
    for m in MODELS:
        df = load_predictions(ROOT / f"results/prompt_v2/extraction_full__{m}.csv")
        for _, r in df.iterrows():
            gold = load_gold(MANIFEST, r["contract"], r["category"])
            pred = r["pred_spans"] if r["pred_spans"] is not None else []
            tp, npred, ngold = match_spans(pred, gold, threshold)
            # Yes/No presence view (only defined for the four Y/N categories)
            gold_yes = pred_yes = None
            if r["category"] in EXT_YN_CATS:
                ans = MANIFEST[MANIFEST.txt_name == r["contract"]].iloc[0][
                    f"{r['category']}-Answer"]
                gold_yes = str(ans).strip().lower() == "yes"
                pred_yes = bool(pred)
            per_item.append({
                "model": m, "contract": r["contract"], "category": r["category"],
                "stratum": r["stratum"], "words": r["word_count"],
                "tp": tp, "n_pred": npred, "n_gold": ngold,
                "parse_ok": r["pred_spans"] is not None,
                "strict_json_ok": r.get("strict_json_ok"),
                "gold_yes": gold_yes, "pred_yes": pred_yes,
                "yn_correct": (None if gold_yes is None else gold_yes == pred_yes),
            })
    pi = pd.DataFrame(per_item)

    for (m, c), g in pi.groupby(["model", "category"]):
        tp, npred, ngold = g.tp.sum(), g.n_pred.sum(), g.n_gold.sum()
        P = tp / npred if npred else float("nan")
        R = tp / ngold if ngold else float("nan")
        row = {"model": m, "category": c, "tp": int(tp), "pred": int(npred),
               "gold": int(ngold), "P": round(P, 3), "R": round(R, 3),
               "F1": round(2 * P * R / (P + R), 3) if (P + R) > 0 else 0.0}
        if c in EXT_YN_CATS:
            tp_y = int(((g.pred_yes) & (g.gold_yes)).sum())
            fp_y = int(((g.pred_yes) & (~g.gold_yes)).sum())
            fn_y = int(((~g.pred_yes) & (g.gold_yes)).sum())
            tn_y = int(((~g.pred_yes) & (~g.gold_yes)).sum())
            tpr = tp_y / (tp_y + fn_y) if tp_y + fn_y else float("nan")
            tnr = tn_y / (tn_y + fp_y) if tn_y + fp_y else float("nan")
            row["yn_bal_acc"] = round((tpr + tnr) / 2, 3)
        per_cat.append(row)
    return pd.DataFrame(per_cat), pi


# ---------------------------------------------------------------------------
# 3. Q&A — per item, using the project's own hybrid matcher
# ---------------------------------------------------------------------------
def qa_detail():
    verdicts = load_judge_verdicts()
    rows = []
    for m in MODELS:
        df = pd.read_csv(ROOT / f"results/prompt_v2/qa_full__{m}.csv")
        df = df[df.call_error.isna()]
        for _, r in df.iterrows():
            cat = r.category
            if cat in QA_YN_CATS:
                pred = norm_yesno(r.model_answer)
                gold = norm_yesno(r.gold_answer) or "no"   # empty gold = No
                correct = (pred == "yes") == (gold == "yes")
                src = "auto-yn"
            else:
                v = auto_match_freetext(r.gold_answer, r.model_answer)
                if v is None:
                    v = verdicts.get((m, r.contract, cat))
                    src = "judge" if v is not None else "unresolved"
                    v = bool(v)
                else:
                    src = "auto-ft"
                correct = bool(v)
            rows.append({"model": m, "contract": r.contract, "tier": r.tier,
                         "category": cat, "stratum": r.stratum,
                         "words": r.word_count, "correct": bool(correct),
                         "source": src,
                         "gold": r.gold_answer, "answer": r.model_answer})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 4. SUMMARISATION — judge item verdicts (full run only)
# ---------------------------------------------------------------------------
def judge_detail():
    rows = []
    for line in (ROOT / "results/summarisation/judgements.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("run") != "full" or not r.get("items"):
            continue
        for code, v in r["items"].items():
            rows.append({"model": r["model_under_test"], "contract": r["contract"],
                         "item": code,
                         "dim": {"F": "faithfulness", "C": "coverage",
                                 "U": "usability"}[code[0]],
                         "passed": bool(v.get("pass")),
                         "reason": v.get("reason", ""),
                         "words": WORDS.get(r["contract"]),
                         "stratum": STRATUM.get(r["contract"])})
    return pd.DataFrame(rows)


def main():
    section("1. COST AND LATENCY BY MODEL AND TASK (full runs only)")
    ct = cost_table()
    ct.to_csv(OUT / "cost_by_model_task.csv", index=False)
    print(ct.to_string(index=False))
    piv = ct.pivot(index="model", columns="task", values="cost_usd")
    piv["TOTAL"] = piv.sum(axis=1)
    print("\nCost (USD) for the whole 40-contract sample, by task:")
    print(piv.round(3).to_string())

    section("2. EXTRACTION — PER CATEGORY")
    pc, pi = extraction_detail()
    pc.to_csv(OUT / "extraction_per_category.csv", index=False)
    pi.to_csv(OUT / "extraction_per_item.csv", index=False)
    print("Span F1 by category:")
    print(pc.pivot(index="category", columns="model", values="F1").to_string())
    print("\nSpan precision by category:")
    print(pc.pivot(index="category", columns="model", values="P").to_string())
    print("\nPredicted span volume by category (GOLD = ground-truth count):")
    vol = pc.pivot(index="category", columns="model", values="pred")
    vol.insert(0, "GOLD", pc.groupby("category")["gold"].max())
    print(vol.to_string())
    print("\nYes/No balanced accuracy by category:")
    print(pc[pc.yn_bal_acc.notna()].pivot(index="category", columns="model",
                                          values="yn_bal_acc").to_string())

    section("3. Q&A — PER TIER / CATEGORY / STRATUM")
    qi = qa_detail()
    qi.to_csv(OUT / "qa_per_item.csv", index=False)
    print("Accuracy by difficulty tier:")
    print(qi.pivot_table(index="tier", columns="model", values="correct",
                         aggfunc="mean").round(3).to_string())
    print("\nAccuracy by category:")
    print(qi.pivot_table(index="category", columns="model", values="correct",
                         aggfunc="mean").round(3).to_string())
    print("\nAccuracy by stratum:")
    print(qi.pivot_table(index="stratum", columns="model", values="correct",
                         aggfunc="mean").round(3).to_string())
    print("\nOverall per-model item accuracy (all 120 items):")
    print(qi.groupby("model").correct.mean().round(3).to_string())
    print("\nResolution source counts:")
    print(qi.groupby(["model", "source"]).size().unstack(fill_value=0).to_string())

    section("4. SUMMARISATION — JUDGE ITEMS")
    ji = judge_detail()
    ji.to_csv(OUT / "judge_items.csv", index=False)
    print("briefs judged per model:",
          ji.groupby("model")["contract"].nunique().to_dict())
    print("\nPass rate by dimension:")
    print(ji.pivot_table(index="model", columns="dim", values="passed",
                         aggfunc="mean").round(4).to_string())
    fails = ji[~ji.passed]
    print(f"\nTotal failed items: {len(fails)} of {len(ji)}")
    print("\nFailures by item code:")
    print(fails.pivot_table(index="model", columns="item", values="passed",
                            aggfunc="size", fill_value=0).to_string())
    print("\nEvery failure:")
    print(fails[["model", "item", "contract", "words", "stratum"]]
          .sort_values(["model", "item"]).to_string(index=False))

    print("\n\nIntermediate CSVs written to outputs/analysis/")


if __name__ == "__main__":
    main()
