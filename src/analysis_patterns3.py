"""
analysis_patterns3.py
---------------------
Stage 3: discriminators that had not been looked at anywhere in the project.

  G. Behaviour on ABSENT clauses — when the contract has no such clause, does
     the model correctly say nothing, or invent one? (the false-positive engine)
  H. Cost predictability — spend variance per contract, which is what an SME
     actually budgets against
  I. Wall-clock throughput for a 40-contract batch
  J. Where the judge's coverage blindness bites hardest, per contract
  K. Extraction recall vs precision trade at the item level: "flooders" vs
     "withholders" quantified as a single index

NO API CALLS. Writes only to outputs/analysis/.

Run:  PYTHONPATH=src ./venv/bin/python src/analysis_patterns3.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "analysis"

MODELS = ["claude-sonnet-5", "deepseek-v4-pro", "gemini-3.1-pro",
          "gpt-5.6-terra", "llama-3.3-70b"]
SHORT = {"claude-sonnet-5": "claude", "deepseek-v4-pro": "deepseek",
         "gemini-3.1-pro": "gemini", "gpt-5.6-terra": "gpt",
         "llama-3.3-70b": "llama"}

ext_item = pd.read_csv(OUT / "extraction_per_item.csv")
judge = pd.read_csv(OUT / "judge_items.csv")
cov_detail = pd.read_csv(ROOT / "results/coverage_cuad/coverage_detail.csv")


def section(t):
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


# ===========================================================================
section("G. BEHAVIOUR ON ABSENT CLAUSES — does the model know when to say nothing?")
# ===========================================================================
absent = ext_item[ext_item.n_gold == 0]
present = ext_item[ext_item.n_gold > 0]
print(f"Item pool: {len(absent)//5} contract x category items where CUAD records "
      f"NO clause, {len(present)//5} where it records at least one.\n")

rows = []
for m in MODELS:
    a = absent[absent.model == m]
    p = present[present.model == m]
    rows.append({
        "model": m,
        "absent_items": len(a),
        "correctly_silent": int((a.n_pred == 0).sum()),
        "silence_rate": round((a.n_pred == 0).mean(), 3),
        "spans_invented_on_absent": int(a.n_pred.sum()),
        "present_items": len(p),
        "found_something": round((p.n_pred > 0).mean(), 3),
    })
G = pd.DataFrame(rows)
G["invented_per_absent_item"] = (G.spans_invented_on_absent / G.absent_items).round(2)
print(G.to_string(index=False))
G.to_csv(OUT / "absent_clause_behaviour.csv", index=False)

print("""
This is the single cleanest 'hallucination' measure in the extraction data and
it uses expert ground truth, not a judge. 'silence_rate' is the share of
contract x category lookups where the clause genuinely does not exist and the
model correctly returned nothing.""")

print("\nSilence rate by category (all models pooled) — where absence is hardest:")
ab = absent.groupby("category").agg(
    absent_items=("n_pred", "size"),
    silent=("n_pred", lambda s: (s == 0).sum()))
ab["silence_rate"] = (ab.silent / ab.absent_items).round(3)
print(ab.sort_values("silence_rate").to_string())

print("\nSilence rate, model x category:")
piv = (absent.assign(silent=(absent.n_pred == 0))
       .pivot_table(index="category", columns="model", values="silent",
                    aggfunc="mean").round(3))
print(piv.to_string())


# ===========================================================================
section("H. COST PREDICTABILITY — what an SME actually budgets against")
# ===========================================================================
rows = []
for m in MODELS:
    per_contract = []
    for task, path in [("extraction", f"results/prompt_v2/extraction_full__{m}.csv"),
                       ("qa", f"results/prompt_v2/qa_full__{m}.csv"),
                       ("summarisation", f"results/summarisation/briefs__{m}.csv")]:
        d = pd.read_csv(ROOT / path)
        d = d[d.call_error.isna()]
        per_contract.append(d.groupby("contract").cost_usd.sum())
    tot = pd.concat(per_contract, axis=1).sum(axis=1)
    rows.append({
        "model": m,
        "mean_$_per_contract": round(tot.mean(), 4),
        "median": round(tot.median(), 4),
        "min": round(tot.min(), 4),
        "max": round(tot.max(), 4),
        "max/median": round(tot.max() / tot.median(), 1),
        "std": round(tot.std(), 4),
        "coef_of_variation": round(tot.std() / tot.mean(), 2),
    })
H = pd.DataFrame(rows)
print(H.to_string(index=False))
H.to_csv(OUT / "cost_predictability.csv", index=False)
print("""
'max/median' is the worst-case surprise: a firm quoting a fixed fee on a
median contract and then receiving the largest one in the sample.""")


# ===========================================================================
section("I. WALL-CLOCK THROUGHPUT for the whole 40-contract batch")
# ===========================================================================
rows = []
for m in MODELS:
    total_s = 0.0
    for path in [f"results/prompt_v2/extraction_full__{m}.csv",
                 f"results/prompt_v2/qa_full__{m}.csv",
                 f"results/summarisation/briefs__{m}.csv"]:
        d = pd.read_csv(ROOT / path)
        total_s += d[d.call_error.isna()].latency_s.sum()
    rows.append({"model": m, "serial_minutes_for_40_contracts": round(total_s / 60, 1),
                 "seconds_per_contract": round(total_s / 40, 1)})
I = pd.DataFrame(rows).sort_values("serial_minutes_for_40_contracts")
print(I.to_string(index=False))
print("\n(Serial, i.e. one call at a time — the way a small firm's script would "
      "run it without concurrency engineering.)")


# ===========================================================================
section("J. WHERE THE JUDGE'S COVERAGE BLINDNESS BITES HARDEST")
# ===========================================================================
jc = judge[judge.dim == "coverage"].groupby(["model", "contract"]).passed.mean()
gc = cov_detail.groupby(["model", "contract"]).mentioned.mean()
J = pd.concat([jc.rename("judge_coverage_pass"), gc.rename("cuad_gold_coverage")],
              axis=1).dropna().reset_index()
J["gap"] = (J.judge_coverage_pass - J.cuad_gold_coverage).round(3)
print("Per-model mean gap (judge says covered minus ground truth says covered):")
print(J.groupby("model").gap.agg(["mean", "max", "size"]).round(3).to_string())
print("\nThe 12 worst individual cases — judge passed coverage in full while "
      "the brief missed most gold clauses:")
print(J.sort_values("gap", ascending=False).head(12)
      [["model", "contract", "judge_coverage_pass", "cuad_gold_coverage", "gap"]]
      .to_string(index=False))
J.to_csv(OUT / "judge_vs_goldcoverage_per_contract.csv", index=False)


# ===========================================================================
section("K. FLOODER vs WITHHOLDER INDEX (extraction)")
# ===========================================================================
rows = []
for m in MODELS:
    d = ext_item[ext_item.model == m]
    over = d.n_pred - d.n_gold
    rows.append({
        "model": m,
        "net_over_prediction": int(over.sum()),
        "items_over": int((over > 0).sum()),
        "items_under": int((over < 0).sum()),
        "items_exact_count": int((over == 0).sum()),
        "flooder_index": round((over > 0).mean() - (over < 0).mean(), 3),
    })
K = pd.DataFrame(rows).sort_values("flooder_index")
print(K.to_string(index=False))
print("""
flooder_index = share of items where the model returned MORE spans than exist
minus the share where it returned fewer. +1 = always over-returns, -1 = always
under-returns, 0 = balanced. This is the behaviour that determines how much
review time the output costs a fee-earner, independent of F1.""")

print("\n\nDone.")
