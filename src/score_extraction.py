"""
score_extraction.py
-------------------
Scores extraction outputs against CUAD ground truth.

Span categories (all six):
  Token-level Jaccard overlap between predicted and gold spans.
  A predicted span is a true positive if its best Jaccard against any gold
  span meets the threshold; each gold span can be claimed by at most one
  prediction (greedy best-first matching). Precision and recall reported
  SEPARATELY — they answer different procurement questions (is the model
  wrong when it speaks, vs does it miss things) — F1 alongside.

Yes/No categories (Termination For Convenience, Cap On Liability,
Ip Ownership Assignment, Non-Compete):
  Presence prediction = (model extracted >= 1 span). Compared against the
  CUAD "-Answer" column. Headline metric: balanced accuracy, with
  positive-class precision/recall alongside; raw accuracy logged, not
  headlined (class imbalance: always-"No" scores ~80% raw).

Threshold: run with --sensitivity to print the match table at several
thresholds. The primary threshold and its justification live in the logbook.

Usage:
    ./venv/bin/python src/score_extraction.py --pilot                 # scores all pilot CSVs
    ./venv/bin/python src/score_extraction.py --pilot --sensitivity   # threshold sweep
"""

import argparse
import ast
import glob
import json
from pathlib import Path

import pandas as pd

from parsing import extract_first_json, normalise

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "results" / "sample_manifest.csv"

YES_NO_CATS = ["Termination For Convenience", "Cap On Liability",
               "Ip Ownership Assignment", "Non-Compete"]
ALL_CATS = ["Governing Law", "Expiration Date"] + YES_NO_CATS

PRIMARY_THRESHOLD = 0.25   # chosen from pilot borderline inspection — see logbook Day 4


def jaccard(a: str, b: str) -> float:
    """Token-level Jaccard: overlap of whitespace-token sets, normalised text."""
    ta, tb = set(normalise(a).split()), set(normalise(b).split())
    if not ta and not tb:
        return 1.0
    return len(ta & tb) / len(ta | tb)


def match_spans(pred: list, gold: list, threshold: float):
    """Greedy best-first matching. Returns (n_tp, n_pred, n_gold).

    Each gold span can be claimed by at most one prediction, so a model
    can't inflate precision by returning the same clause repeatedly.
    """
    pairs = sorted(
        ((jaccard(p, g), i, j) for i, p in enumerate(pred) for j, g in enumerate(gold)),
        reverse=True,
    )
    used_p, used_g = set(), set()
    tp = 0
    for score, i, j in pairs:
        if score < threshold:
            break
        if i in used_p or j in used_g:
            continue
        used_p.add(i); used_g.add(j)
        tp += 1
    return tp, len(pred), len(gold)


def load_gold(manifest: pd.DataFrame, contract: str, category: str) -> list:
    """Gold spans for one contract x category from the CUAD master clauses."""
    row = manifest[manifest.txt_name == contract].iloc[0]
    val = row[category]
    if pd.isna(val):
        return []
    spans = ast.literal_eval(val)
    return [s for s in spans if str(s).strip()]


def load_predictions(summary_csv: Path) -> pd.DataFrame:
    """Re-parse predictions from the RAW files (source of truth, survives
    parser upgrades), keyed by contract x category."""
    df = pd.read_csv(summary_csv)
    preds = []
    for _, r in df.iterrows():
        try:
            spans = extract_first_json(Path(ROOT / r["raw_path"]).read_text())["spans"]
        except Exception:
            spans = None   # unparseable = model failed this item
        preds.append(spans)
    df["pred_spans"] = preds
    return df


def score_model(summary_csv: Path, manifest: pd.DataFrame, threshold: float) -> dict:
    df = load_predictions(summary_csv)

    # --- span-level P/R/F1 over all six categories pooled ---
    tp = np_ = ng = 0
    per_cat = {}
    for _, r in df.iterrows():
        gold = load_gold(manifest, r["contract"], r["category"])
        pred = r["pred_spans"] if r["pred_spans"] is not None else []
        t, p, g = match_spans(pred, gold, threshold)
        tp += t; np_ += p; ng += g
        c = per_cat.setdefault(r["category"], [0, 0, 0])
        c[0] += t; c[1] += p; c[2] += g

    precision = tp / np_ if np_ else float("nan")
    recall = tp / ng if ng else float("nan")
    f1 = (2 * precision * recall / (precision + recall)
          if precision + recall > 0 else 0.0)

    # --- Yes/No presence scoring ---
    yn = df[df.category.isin(YES_NO_CATS)].copy()
    yn["pred_yes"] = yn.pred_spans.map(lambda s: bool(s))
    gold_yes = []
    for _, r in yn.iterrows():
        ans = manifest[manifest.txt_name == r["contract"]].iloc[0][f"{r['category']}-Answer"]
        gold_yes.append(str(ans).strip().lower() == "yes")
    yn["gold_yes"] = gold_yes

    tp_y = int(((yn.pred_yes) & (yn.gold_yes)).sum())
    fp_y = int(((yn.pred_yes) & (~yn.gold_yes)).sum())
    fn_y = int((~yn.pred_yes & yn.gold_yes).sum())
    tn_y = int((~yn.pred_yes & ~yn.gold_yes).sum())
    tpr = tp_y / (tp_y + fn_y) if (tp_y + fn_y) else float("nan")
    tnr = tn_y / (tn_y + fp_y) if (tn_y + fp_y) else float("nan")

    return {
        "span_precision": round(precision, 3),
        "span_recall": round(recall, 3),
        "span_f1": round(f1, 3),
        "span_tp": tp, "span_pred": np_, "span_gold": ng,
        "yn_balanced_acc": round((tpr + tnr) / 2, 3),
        "yn_pos_precision": round(tp_y / (tp_y + fp_y), 3) if (tp_y + fp_y) else float("nan"),
        "yn_pos_recall": round(tpr, 3),
        "yn_raw_acc": round((tp_y + tn_y) / len(yn), 3),   # logged, not headlined
        "per_category": per_cat,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--full", action="store_true",
                    help="score the 40-contract run (extraction_full__*.csv)")
    ap.add_argument("--cond", default="v2", choices=["v1", "v2"],
                    help="prompt condition directory (results/prompt_<cond>/)")
    ap.add_argument("--sensitivity", action="store_true")
    ap.add_argument("--threshold", type=float, default=PRIMARY_THRESHOLD)
    args = ap.parse_args()

    manifest = pd.read_csv(MANIFEST)
    cond_dir = ROOT / "results" / f"prompt_{args.cond}"
    pattern = "extraction_full__*.csv" if args.full else "pilot_extraction_summary__*.csv"
    prefix = "extraction_full__" if args.full else "pilot_extraction_summary__"
    csvs = {Path(f).stem.replace(prefix, ""): Path(f)
            for f in glob.glob(str(cond_dir / pattern))}

    if args.sensitivity:
        print("Threshold sensitivity (span precision/recall, all models pooled):")
        for th in (0.15, 0.30, 0.50, 0.70):
            agg_tp = agg_p = agg_g = 0
            for model, f in sorted(csvs.items()):
                s = score_model(f, manifest, th)
                agg_tp += s["span_tp"]; agg_p += s["span_pred"]; agg_g += s["span_gold"]
            print(f"  tau={th:.2f}:  P={agg_tp/agg_p:.3f}  R={agg_tp/agg_g:.3f}  "
                  f"(TP={agg_tp}, pred={agg_p}, gold={agg_g})")
        print()

    rows = []
    for model, f in sorted(csvs.items()):
        s = score_model(f, manifest, args.threshold)
        s.pop("per_category")
        rows.append({"model": model, **s})
    out = pd.DataFrame(rows)
    print(f"Scores at tau={args.threshold} (prompt condition: {args.cond}):")
    print(out.to_string(index=False))
    name = "full_scores" if args.full else "pilot_scores"
    outpath = ROOT / "results" / f"{name}_{args.cond}.csv"
    out.to_csv(outpath, index=False)
    print(f"\nsaved {outpath}")

    if args.full:
        # per-stratum span P/R/F1 (length-degradation view)
        strata_rows = []
        for model, f in sorted(csvs.items()):
            df = load_predictions(f)
            for stratum in ("short", "medium", "long"):
                sub = df[df.stratum == stratum]
                tp = np_ = ng = 0
                for _, r in sub.iterrows():
                    gold = load_gold(manifest, r["contract"], r["category"])
                    pred = r["pred_spans"] if r["pred_spans"] is not None else []
                    t, pn, g = match_spans(pred, gold, args.threshold)
                    tp += t; np_ += pn; ng += g
                P = tp / np_ if np_ else float("nan")
                R = tp / ng if ng else float("nan")
                F = 2*P*R/(P+R) if (P+R) > 0 else 0.0
                strata_rows.append({"model": model, "stratum": stratum,
                                    "P": round(P, 3), "R": round(R, 3),
                                    "F1": round(F, 3), "gold": ng, "pred": np_})
        sdf = pd.DataFrame(strata_rows)
        print("\nPer-stratum span scores:")
        print(sdf.pivot(index="model", columns="stratum",
                        values=["P", "R", "F1"]).to_string())
        sdf.to_csv(ROOT / "results" / f"full_scores_by_stratum_{args.cond}.csv", index=False)


if __name__ == "__main__":
    main()
