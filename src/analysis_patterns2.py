"""
analysis_patterns2.py
---------------------
Stage 2 of the read-only pattern analysis. Depends on the CSVs written by
analysis_patterns.py (run that first).

Covers the questions stage 1 did not:
  A. quality per dollar, per task
  B. model "personality" — behavioural signature across tasks
  C. length-stratum performance, all three tasks on one scale
  D. failure concentration: category, contract, mechanism
  E. inter-model agreement and CORRELATED ERRORS at scale
  F. things not yet looked at: verbosity/over-prediction, parse cleanliness,
     cost efficiency of tokens, per-contract difficulty

NO API CALLS. Writes only to outputs/analysis/.

Run:  PYTHONPATH=src ./venv/bin/python src/analysis_patterns2.py
"""

import itertools
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "analysis"

MODELS = ["claude-sonnet-5", "deepseek-v4-pro", "gemini-3.1-pro",
          "gpt-5.6-terra", "llama-3.3-70b"]
SHORT = {"claude-sonnet-5": "claude", "deepseek-v4-pro": "deepseek",
         "gemini-3.1-pro": "gemini", "gpt-5.6-terra": "gpt",
         "llama-3.3-70b": "llama"}

MANIFEST = pd.read_csv(ROOT / "results" / "sample_manifest.csv")
WORDS = MANIFEST.set_index("txt_name")["word_count"].to_dict()
STRATUM = MANIFEST.set_index("txt_name")["stratum"].to_dict()

cost = pd.read_csv(OUT / "cost_by_model_task.csv")
ext_item = pd.read_csv(OUT / "extraction_per_item.csv")
qa_item = pd.read_csv(OUT / "qa_per_item.csv")
judge = pd.read_csv(OUT / "judge_items.csv")
depth = pd.read_csv(ROOT / "results/summarisation/brief_depth.csv")
cov = pd.read_csv(ROOT / "results/coverage_cuad/coverage_by_model.csv")
cov_detail = pd.read_csv(ROOT / "results/coverage_cuad/coverage_detail.csv")

ext_head = pd.read_csv(ROOT / "results/full_scores_v2.csv")
qa_head = pd.read_csv(ROOT / "results/qa_scores.csv")


def section(t):
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


def contract_type(name):
    """Coarse agreement type from the CUAD filename, for the failure-by-type
    view. Filenames encode the exhibit description after the last dash."""
    n = name.upper()
    for key, label in [
        ("DISTRIBUT", "Distribution"), ("DEVELOPMENT", "Development"),
        ("ENDORSEMENT", "Endorsement"), ("SPONSORSHIP", "Sponsorship"),
        ("HOSTING", "Hosting"), ("MAINTENANCE", "Maintenance/Support"),
        ("SUPPORT", "Maintenance/Support"), ("TRANSPORTATION", "Transportation"),
        ("SUPPLY", "Supply"), ("OUTSOURCING", "Outsourcing"),
        ("STRATEGIC ALLIANCE", "Strategic Alliance"), ("SERVICE", "Services"),
        ("SERV AGREE", "Services"), ("PROMOTION", "Promotion"),
        ("INTELLECTUAL PROPERTY", "IP"), ("TRADEMARK", "IP/Trademark"),
        ("LICENSE", "Licence"), ("AFFILIATE", "Affiliate"),
        ("JOINT FILING", "Joint Filing"),
    ]:
        if key in n:
            return label
    return "Other"


# ===========================================================================
section("A. QUALITY PER DOLLAR, PER TASK  (the supervisor's cost-benefit ratio)")
# ===========================================================================
cost_p = cost.pivot(index="model", columns="task", values="cost_usd")

qpd = []
for m in MODELS:
    e = ext_head[ext_head.model == m].iloc[0]
    q = qa_head[qa_head.model == m].iloc[0]
    c = cov[cov.model == m].iloc[0]
    jf = judge[judge.model == m]
    fail_rate = 1 - jf.passed.mean()
    # Q&A single quality number: mean of the two reported axes, which is how
    # the scorecard will have to combine them (stated, not hidden).
    qa_quality = (q.yn_balanced_acc + q.ft_accuracy) / 2
    qpd.append({
        "model": m,
        "ext_F1": e.span_f1, "ext_cost": cost_p.loc[m, "extraction"],
        "ext_F1_per_$": round(e.span_f1 / cost_p.loc[m, "extraction"], 3),
        "qa_quality": round(qa_quality, 3), "qa_cost": cost_p.loc[m, "qa"],
        "qa_qual_per_$": round(qa_quality / cost_p.loc[m, "qa"], 3),
        "sum_coverage": c.coverage_all, "sum_cost": cost_p.loc[m, "summarisation"],
        "sum_cov_per_$": round(c.coverage_all / cost_p.loc[m, "summarisation"], 3),
        "sum_item_pass": round(jf.passed.mean(), 4),
        "total_cost": round(cost_p.loc[m].sum(), 2),
    })
QPD = pd.DataFrame(qpd)
QPD.to_csv(OUT / "quality_per_dollar.csv", index=False)
print(QPD.to_string(index=False))

print("\nCost to run all three tasks over 40 contracts, and the quality bought:")
for _, r in QPD.sort_values("total_cost").iterrows():
    print(f"  {SHORT[r.model]:9s} ${r.total_cost:6.2f}   "
          f"ext F1 {r.ext_F1:.3f} | QA {r.qa_quality:.3f} | "
          f"summ coverage {r.sum_coverage:.3f} | judge pass {r.sum_item_pass:.4f}")

print("\nPremium paid over the cheapest model (deepseek), and what it buys:")
base = QPD[QPD.model == "deepseek-v4-pro"].iloc[0]
for _, r in QPD.iterrows():
    if r.model == "deepseek-v4-pro":
        continue
    print(f"  {SHORT[r.model]:9s} {r.total_cost/base.total_cost:4.1f}x cost  "
          f"ext F1 {r.ext_F1-base.ext_F1:+.3f}  QA {r.qa_quality-base.qa_quality:+.3f}  "
          f"coverage {r.sum_coverage-base.sum_coverage:+.3f}")


# ===========================================================================
section("B. MODEL PERSONALITY — behavioural signature across tasks")
# ===========================================================================
pers = []
for m in MODELS:
    e = ext_head[ext_head.model == m].iloc[0]
    d = depth[depth.model == m]
    ei = ext_item[ext_item.model == m]
    c = cov[cov.model == m].iloc[0]
    # over-prediction ratio: spans emitted per gold span
    pers.append({
        "model": m,
        "ext_pred/gold": round(e.span_pred / e.span_gold, 2),
        "ext_P": e.span_precision, "ext_R": e.span_recall,
        "P_minus_R": round(e.span_precision - e.span_recall, 3),
        "obligations/brief": round(d.obligations.mean(), 2),
        "risks/brief": round(d.risks.mean(), 2),
        "brief_scaling_short_to_long": None,
        "cuad_coverage": c.coverage_all,
        "strict_json_rate": round(ei.strict_json_ok.mean(), 3),
        "mean_lat_s": round(cost[(cost.model == m)].mean_latency_s.mean(), 2),
    })
P = pd.DataFrame(pers)
# how much the brief grows from short to long contracts
for i, m in enumerate(MODELS):
    d = depth[depth.model == m]
    s = d[d.stratum == "short"].obligations.mean()
    l = d[d.stratum == "long"].obligations.mean()
    P.loc[i, "brief_scaling_short_to_long"] = round(l / s, 2)
P.to_csv(OUT / "model_personality.csv", index=False)
print(P.to_string(index=False))

print("""
Reading:
  ext_pred/gold > 1      = over-predicts (floods); < 1 = withholds
  P_minus_R < 0          = recall-leaning (says a lot, some of it wrong)
  brief_scaling          = obligations on long contracts / on short contracts;
                           ~1.0 means a fixed-size brief regardless of input
""")

print("Depth by stratum (obligations per brief):")
print(depth.pivot_table(index="model", columns="stratum", values="obligations",
                        aggfunc="mean").round(2)[["short", "medium", "long"]].to_string())


# ===========================================================================
section("C. LENGTH STRATUM — all three tasks on one view")
# ===========================================================================
ext_str = pd.read_csv(ROOT / "results/full_scores_by_stratum_v2.csv")
print("Extraction span F1 by stratum:")
print(ext_str.pivot(index="model", columns="stratum",
                    values="F1")[["short", "medium", "long"]].to_string())
print("\nQ&A item accuracy by stratum:")
print(qa_item.pivot_table(index="model", columns="stratum", values="correct",
                          aggfunc="mean").round(3)[["short", "medium", "long"]].to_string())
print("\nSummarisation judge item pass rate by stratum:")
print(judge.pivot_table(index="model", columns="stratum", values="passed",
                        aggfunc="mean").round(4)[["short", "medium", "long"]].to_string())
print("\nCUAD gold coverage by stratum:")
cd = cov_detail.copy()
cd["stratum"] = cd["contract"].map(STRATUM) if "contract" in cd.columns else None
if "mentioned" in cd.columns and cd["stratum"].notna().any():
    print(cd.pivot_table(index="model", columns="stratum", values="mentioned",
                         aggfunc="mean").round(3).to_string())
else:
    print("  (coverage_detail columns:", cd.columns.tolist(), ")")


# ===========================================================================
section("D. FAILURE CONCENTRATION")
# ===========================================================================
print("D1. Extraction — which categories destroy precision (pooled all models):")
pc = pd.read_csv(OUT / "extraction_per_category.csv")
agg = pc.groupby("category").agg(gold=("gold", "max"), pred=("pred", "sum"),
                                 tp=("tp", "sum")).reset_index()
agg["false_positives"] = agg.pred - agg.tp
agg["FP_share_of_all"] = (agg.false_positives / agg.false_positives.sum()).round(3)
agg["pooled_P"] = (agg.tp / agg.pred).round(3)
agg["pooled_R"] = (agg.tp / (agg.gold * 5)).round(3)
print(agg.sort_values("false_positives", ascending=False).to_string(index=False))

print("\nD2. Summarisation — failures by contract (which documents break models):")
jf = judge[~judge.passed].copy()
jf["type"] = jf.contract.map(contract_type)
bycon = (jf.groupby(["contract", "words", "stratum"])
           .agg(n_failures=("item", "size"),
                models=("model", lambda s: ",".join(sorted(set(SHORT[x] for x in s)))),
                items=("item", lambda s: ",".join(sorted(set(s)))))
           .reset_index().sort_values("n_failures", ascending=False))
print(bycon.to_string(index=False))

print("\nD3. Failures by contract TYPE (n_failures / n_contracts of that type):")
MANIFEST["type"] = MANIFEST.txt_name.map(contract_type)
type_counts = MANIFEST["type"].value_counts()
tf = jf.groupby("type").size()
td = pd.DataFrame({"contracts_in_sample": type_counts,
                   "failures": tf}).fillna(0).astype(int)
td["failures_per_contract"] = (td.failures / td.contracts_in_sample).round(2)
print(td.sort_values("failures_per_contract", ascending=False).to_string())

print("\nD4. Failure mechanism (dimension) by stratum, pooled:")
print(jf.pivot_table(index="stratum", columns="dim", values="item",
                     aggfunc="size", fill_value=0).to_string())


# ===========================================================================
section("E. INTER-MODEL AGREEMENT AND CORRELATED ERRORS")
# ===========================================================================
def correlation_report(df, key_cols, label):
    """For a binary-correct item set: how often do models fail together,
    and is that more than independence predicts?"""
    w = df.pivot_table(index=key_cols, columns="model", values="correct")
    w = w.dropna()
    n = len(w)
    err = (w == 0)
    per_model_err = err.mean()
    print(f"\n{label}: {n} items x {len(MODELS)} models")
    print("  per-model error rate:",
          {SHORT[m]: round(per_model_err[m], 3) for m in MODELS})
    k = err.sum(axis=1)
    dist = k.value_counts().sort_index()
    # expected distribution under independence (Poisson-binomial, exact)
    p = [per_model_err[m] for m in MODELS]
    exp = [0.0] * 6
    for bits in itertools.product([0, 1], repeat=5):
        prob = 1.0
        for pi_, b in zip(p, bits):
            prob *= pi_ if b else (1 - pi_)
        exp[sum(bits)] += prob
    print("  items by number of models wrong (observed vs independence):")
    for j in range(6):
        print(f"    {j} wrong: observed {int(dist.get(j,0)):4d}   "
              f"expected {exp[j]*n:7.1f}")
    all_wrong = int(dist.get(5, 0))
    maj_wrong = int(sum(dist.get(j, 0) for j in (3, 4, 5)))
    print(f"  ALL FIVE wrong: {all_wrong} observed vs {exp[5]*n:.1f} expected "
          f"({'x%.1f' % (all_wrong/(exp[5]*n)) if exp[5]*n > 0 else 'n/a'})")
    print(f"  MAJORITY (3+) wrong: {maj_wrong} observed vs "
          f"{sum(exp[3:])*n:.1f} expected")
    # pairwise agreement on errors
    print("  pairwise: P(model B wrong | model A wrong), for a firm "
          "cross-checking A against B:")
    rows = []
    for a, b in itertools.combinations(MODELS, 2):
        both = int((err[a] & err[b]).sum())
        pa, pb = int(err[a].sum()), int(err[b].sum())
        rows.append({"pair": f"{SHORT[a]}+{SHORT[b]}",
                     "both_wrong": both,
                     "P(b|a)": round(both / pa, 3) if pa else float("nan"),
                     "indep_baseline": round(per_model_err[b], 3),
                     "lift": round((both / pa) / per_model_err[b], 2) if pa and per_model_err[b] else float("nan")})
    pr = pd.DataFrame(rows).sort_values("lift", ascending=False)
    print(pr.to_string(index=False))
    return w, k


# Extraction: an item is (contract, category); "correct" = model got the
# exact gold count with no false positives. Strict, but it is the definition
# a practitioner cares about: did this clause lookup come back right.
ei = ext_item.copy()
ei["correct"] = (ei.tp == ei.n_gold) & (ei.n_pred == ei.n_gold)
w_ext, k_ext = correlation_report(ei, ["contract", "category"],
                                  "EXTRACTION (item = contract x category)")

w_qa, k_qa = correlation_report(qa_item, ["contract", "category"],
                                "Q&A (item = contract x question)")

# Summarisation: an item is (contract, checklist item)
jj = judge.copy()
jj["correct"] = jj.passed.astype(int)
w_j, k_j = correlation_report(jj, ["contract", "item"],
                              "SUMMARISATION (item = contract x checklist item)")

print("\nE-SUMMARY — the cross-checking question:")
for label, k in [("extraction", k_ext), ("Q&A", k_qa), ("summarisation", k_j)]:
    wrong_items = (k > 0).sum()
    unan = (k == 5).sum()
    print(f"  {label:14s}: of {wrong_items} items where ANY model erred, "
          f"{unan} ({unan/wrong_items:.0%}) had ALL FIVE wrong — a second "
          f"model would not have caught them.")

# Which specific contracts defeat everyone on summarisation?
print("\nItems where ALL FIVE models failed the same checklist item:")
allfail = w_j[w_j.sum(axis=1) == 0]
print(allfail.index.tolist() if len(allfail) else "  none")

print("\nExtraction items where ALL FIVE models were wrong, by category:")
ext_all_wrong = w_ext[w_ext.sum(axis=1) == 0].reset_index()
print(ext_all_wrong.category.value_counts().to_string())


# ===========================================================================
section("F. NOT YET LOOKED AT — other discriminators")
# ===========================================================================
print("F1. Instruction adherence (strict JSON) — integration friction:")
print(ext_item.groupby("model").strict_json_ok.agg(["mean", "sum", "size"]).round(4).to_string())

print("\nF2. Output-token economy — how many output tokens each model spends:")
print(cost.pivot(index="model", columns="task", values="tokens_out").to_string())
print("\n  input tokens are near-identical across models (same contracts), so")
print("  output volume and per-token price explain the whole cost spread:")
tot = cost.groupby("model")[["tokens_in", "tokens_out"]].sum()
tot["cost"] = cost.groupby("model").cost_usd.sum().round(2)
tot["out/in %"] = (100 * tot.tokens_out / tot.tokens_in).round(2)
tot["$ per 1k out"] = (tot.cost / (tot.tokens_out / 1000)).round(4)
print(tot.to_string())

print("\nF3. Latency at the 95th percentile — the 'slowest document' experience:")
print(cost.pivot(index="model", columns="task", values="p95_latency_s").to_string())

print("\nF4. Per-contract difficulty — contracts ranked by how many models "
      "failed an extraction item on them:")
ei2 = ei.groupby("contract").correct.apply(lambda s: (~s).sum())
hard = pd.DataFrame({"items_failed_across_models": ei2,
                     "words": pd.Series(WORDS),
                     "stratum": pd.Series(STRATUM)}).dropna()
hard["type"] = hard.index.map(contract_type)
print(hard.sort_values("items_failed_across_models", ascending=False).head(12).to_string())

print("\nF5. Does contract length predict extraction error? "
      "(correlation of words with per-contract failed items, per model)")
for m in MODELS:
    g = ei[ei.model == m].groupby("contract").agg(
        fails=("correct", lambda s: (~s).sum()), words=("words", "max"))
    print(f"  {SHORT[m]:9s} pearson r = {g.fails.corr(g.words):+.3f}   "
          f"rank r = {g.fails.rank().corr(g.words.rank()):+.3f}")

print("\nF6. CUAD coverage per clause type, pooled across models "
      "(the shared-blind-spot view):")
if "clause" in cov_detail.columns and "mentioned" in cov_detail.columns:
    ct = (cov_detail.groupby("clause")
          .agg(checks=("mentioned", "size"), rate=("mentioned", "mean"))
          .sort_values("rate"))
    print(ct.round(3).to_string())
else:
    print("  coverage_detail columns:", cov_detail.columns.tolist())

print("\n\nDone.")
