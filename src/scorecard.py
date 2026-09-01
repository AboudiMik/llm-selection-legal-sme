"""
scorecard.py
------------
RO4 artefact: the procurement scorecard computation.

Supervised ruling (28 Aug 2026): weighting is PROFILE-BASED (Option B).
A single universal weight vector is not defensible for a heterogeneous SME
population, so the framework publishes three named buyer profiles and shows
that they discriminate.

Method, in the order it is applied:

  1. FIVE DIMENSIONS, defined once and mapped to a task-specific measure.
     The dimensions mean the same thing in every task; only the instrument
     that measures them changes. That mapping IS the RO2 contribution.

  2. DIRECTION ADJUSTMENT — cost and latency are inverted so that, on every
     dimension, higher is better.

  3. DOMINANCE ELIMINATION FIRST, before any weighting. Model A dominates B
     if A is >= B on all five dimensions and > on at least one. A dominated
     model is removed from the shortlist without any weighting argument, so
     the result does not depend on contested weights.

  4. NORMALISATION — min-max within each task across ALL FIVE models (not
     just the surviving ones), so a profile's feasibility filter cannot
     change the scale and thereby the scores.

  5. PROFILE WEIGHTS applied to the normalised, non-dominated set.

Discrimination check: if two profiles return the same model on every task the
script says so LOUDLY. Weights are never tuned to manufacture separation —
an identical result is a finding about the framework, not a bug to fix.

NO API CALLS. Reads results/ and outputs/analysis/; writes outputs/scorecard/.

Run:  PYTHONPATH=src ./venv/bin/python src/scorecard.py
"""

import itertools
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ANA = ROOT / "outputs" / "analysis"
OUT = ROOT / "outputs" / "scorecard"
OUT.mkdir(parents=True, exist_ok=True)

MODELS = ["claude-sonnet-5", "deepseek-v4-pro", "gemini-3.1-pro",
          "gpt-5.6-terra", "llama-3.3-70b"]
SHORT = {"claude-sonnet-5": "claude", "deepseek-v4-pro": "deepseek",
         "gemini-3.1-pro": "gemini", "gpt-5.6-terra": "gpt",
         "llama-3.3-70b": "llama"}

# Deployment route. Both open-weight models are used VIA API in this study —
# no self-hosting was in scope — so "open-weight" here means the weights are
# obtainable and a firm COULD move the workload in-house or to a UK/EU host
# later. It is a procurement-optionality property, not a measured one.
OPEN_WEIGHT = {"deepseek-v4-pro", "llama-3.3-70b"}

TASKS = ["extraction", "qa", "summarisation"]

# ---------------------------------------------------------------------------
# The five dimensions, and what measures them in each task.
# ---------------------------------------------------------------------------
DIMENSIONS = ["D1_completeness", "D2_trustworthiness", "D3_cost",
              "D4_speed", "D5_operational_reliability"]

DIMENSION_MEANING = {
    "D1_completeness": "Does it find what is there? (recall-shaped)",
    "D2_trustworthiness": "Is it right when it speaks? (precision / no fabrication)",
    "D3_cost": "US$ per contract for this task (inverted)",
    "D4_speed": "Mean seconds per call (inverted)",
    "D5_operational_reliability": "Format adherence x calls completed",
}

MEASURE_USED = {
    "extraction": {
        "D1_completeness": "span recall @ tau=0.25 vs CUAD gold spans",
        "D2_trustworthiness": "mean(span precision, absent-clause silence rate)",
        "D3_cost": "US$/contract, 6 calls",
        "D4_speed": "mean latency per call",
        "D5_operational_reliability": "strict-JSON rate x (calls ok / attempted)",
    },
    "qa": {
        "D1_completeness": "overall item accuracy over 120 items",
        "D2_trustworthiness": "Yes/No positive-class precision",
        "D3_cost": "US$/contract, 3 calls",
        "D4_speed": "mean latency per call",
        "D5_operational_reliability": "calls ok / attempted",
    },
    "summarisation": {
        "D1_completeness": "CUAD gold clause-type coverage (expert annotation)",
        "D2_trustworthiness": "LLM-judge faithfulness item pass rate",
        "D3_cost": "US$/contract, 1 call",
        "D4_speed": "mean latency per call",
        "D5_operational_reliability": "fields_ok x (briefs parsed / attempted)",
    },
}

# ---------------------------------------------------------------------------
# Profile weight vectors. These are the numbers to state in the dissertation.
# Traced to the OECD SME adoption-barrier categories: cost of adoption,
# trust/assurance, and skills/integration capacity.
# ---------------------------------------------------------------------------
PROFILES = {
    "cost-constrained": {
        "weights": {"D1_completeness": 0.20, "D2_trustworthiness": 0.15,
                    "D3_cost": 0.50, "D4_speed": 0.10,
                    "D5_operational_reliability": 0.05},
        "feasible": lambda m: True,
        "rationale": "Cost-adjusted quality dominates. The firm will accept a "
                     "quality decrement it can mitigate with review time, but "
                     "cannot accept a per-matter cost it cannot recover.",
    },
    "confidentiality-constrained": {
        "weights": {"D1_completeness": 0.15, "D2_trustworthiness": 0.25,
                    "D3_cost": 0.10, "D4_speed": 0.10,
                    "D5_operational_reliability": 0.40},
        "feasible": lambda m: m in OPEN_WEIGHT,
        "rationale": "Client confidentiality or a data-residency undertaking "
                     "restricts the feasible set to open-weight models the firm "
                     "could relocate in-house or to a controlled host. Within "
                     "that set, operational reliability and trustworthiness "
                     "dominate, because a self-managed route removes the "
                     "vendor's operational safety net.",
    },
    "quality-critical": {
        "weights": {"D1_completeness": 0.25, "D2_trustworthiness": 0.50,
                    "D3_cost": 0.05, "D4_speed": 0.05,
                    "D5_operational_reliability": 0.15},
        "feasible": lambda m: True,
        "rationale": "Output informs advice to a client. Fabrication is a "
                     "liability event, so trustworthiness carries half the "
                     "weight and cost is close to irrelevant at these absolute "
                     "price levels.",
    },
}

LOWER_IS_BETTER = {"D3_cost", "D4_speed"}


# ---------------------------------------------------------------------------
# Assemble the raw dimension matrix from the empirical results
# ---------------------------------------------------------------------------
def build_raw():
    cost = pd.read_csv(ANA / "cost_by_model_task.csv")
    ext_head = pd.read_csv(ROOT / "results/full_scores_v2.csv").set_index("model")
    qa_head = pd.read_csv(ROOT / "results/qa_scores.csv").set_index("model")
    qa_item = pd.read_csv(ANA / "qa_per_item.csv")
    cov = pd.read_csv(ROOT / "results/coverage_cuad/coverage_by_model.csv").set_index("model")
    judge = pd.read_csv(ANA / "judge_items.csv")
    absent = pd.read_csv(ANA / "absent_clause_behaviour.csv").set_index("model")
    ext_item = pd.read_csv(ANA / "extraction_per_item.csv")

    rows = []
    for m in MODELS:
        c = cost[cost.model == m].set_index("task")
        # --- extraction ---
        strict = ext_item[ext_item.model == m].strict_json_ok.mean()
        comp_e = c.loc["extraction", "calls_ok"] / c.loc["extraction", "calls_attempted"]
        rows.append({
            "task": "extraction", "model": m,
            "D1_completeness": ext_head.loc[m, "span_recall"],
            "D2_trustworthiness": round(
                (ext_head.loc[m, "span_precision"] + absent.loc[m, "silence_rate"]) / 2, 4),
            "D3_cost": c.loc["extraction", "cost_per_contract"],
            "D4_speed": c.loc["extraction", "mean_latency_s"],
            "D5_operational_reliability": round(strict * comp_e, 4),
        })
        # --- qa ---
        comp_q = c.loc["qa", "calls_ok"] / c.loc["qa", "calls_attempted"]
        rows.append({
            "task": "qa", "model": m,
            "D1_completeness": round(qa_item[qa_item.model == m].correct.mean(), 4),
            "D2_trustworthiness": qa_head.loc[m, "yn_pos_precision"],
            "D3_cost": c.loc["qa", "cost_per_contract"],
            "D4_speed": c.loc["qa", "mean_latency_s"],
            "D5_operational_reliability": round(comp_q, 4),
        })
        # --- summarisation ---
        jf = judge[(judge.model == m) & (judge.dim == "faithfulness")]
        briefs = pd.read_csv(ROOT / f"results/summarisation/briefs__{m}.csv")
        ok = briefs[briefs.call_error.isna()]
        fields_ok = ok.fields_ok.mean() if "fields_ok" in ok else 1.0
        comp_s = len(ok) / 40
        rows.append({
            "task": "summarisation", "model": m,
            "D1_completeness": cov.loc[m, "coverage_all"],
            "D2_trustworthiness": round(jf.passed.mean(), 4),
            "D3_cost": c.loc["summarisation", "cost_per_contract"],
            "D4_speed": c.loc["summarisation", "mean_latency_s"],
            "D5_operational_reliability": round(float(fields_ok) * comp_s, 4),
        })
    return pd.DataFrame(rows)


def orient(df):
    """Direction-adjust so higher is better on every dimension."""
    d = df.copy()
    for col in LOWER_IS_BETTER:
        d[col] = -d[col]
    return d


def dominance(oriented_task_df):
    """Return (dominated_models, explanation_rows) for one task.

    A dominates B iff A >= B on all five oriented dimensions and A > B on at
    least one. No weights involved — this is why it is applied first.
    """
    dominated, why = {}, []
    idx = oriented_task_df.set_index("model")[DIMENSIONS]
    for a, b in itertools.permutations(MODELS, 2):
        va, vb = idx.loc[a], idx.loc[b]
        if (va >= vb).all() and (va > vb).any():
            dominated.setdefault(b, []).append(a)
            why.append({"dominated": b, "dominated_by": a,
                        "margins": {k: round(va[k] - vb[k], 4) for k in DIMENSIONS}})
    return dominated, why


def normalise(oriented_task_df):
    """Min-max to [0,1] per dimension, across ALL FIVE models."""
    d = oriented_task_df.copy()
    for col in DIMENSIONS:
        lo, hi = d[col].min(), d[col].max()
        d[col] = 1.0 if hi == lo else (d[col] - lo) / (hi - lo)
    return d


def main():
    raw = build_raw()
    raw.to_csv(OUT / "raw_dimensions.csv", index=False)

    print("=" * 78)
    print("THE FIVE DIMENSIONS")
    print("=" * 78)
    for d in DIMENSIONS:
        print(f"  {d:28s} {DIMENSION_MEANING[d]}")
    print("\nMeasure used per task:")
    for t in TASKS:
        print(f"\n  [{t}]")
        for d in DIMENSIONS:
            print(f"    {d:28s} {MEASURE_USED[t][d]}")

    print("\n" + "=" * 78)
    print("RAW DIMENSION VALUES (before orientation or normalisation)")
    print("=" * 78)
    for t in TASKS:
        print(f"\n[{t}]")
        sub = raw[raw.task == t].set_index("model")[DIMENSIONS]
        sub.index = [SHORT[m] for m in sub.index]
        print(sub.to_string())

    print("\n" + "=" * 78)
    print("STEP 1 — DOMINANCE ELIMINATION (applied BEFORE any weighting)")
    print("=" * 78)
    survivors = {}
    dom_records = []
    for t in TASKS:
        o = orient(raw[raw.task == t])
        dominated, why = dominance(o)
        survivors[t] = [m for m in MODELS if m not in dominated]
        print(f"\n[{t}]")
        if not dominated:
            print("  no model is dominated — every model wins on at least one "
                  "dimension, so the choice genuinely requires weights.")
        for b, bys in dominated.items():
            print(f"  ELIMINATED {SHORT[b]:9s} dominated by "
                  f"{', '.join(SHORT[x] for x in bys)}")
        for w in why:
            dom_records.append({"task": t, **{k: v for k, v in w.items()
                                              if k != "margins"},
                                **{f"margin_{k}": v for k, v in w["margins"].items()}})
        print(f"  surviving shortlist: {[SHORT[m] for m in survivors[t]]}")
    pd.DataFrame(dom_records).to_csv(OUT / "dominance.csv", index=False)

    print("\n" + "=" * 78)
    print("STEP 2 — NORMALISED SCORES (min-max within task, across all 5 models)")
    print("=" * 78)
    norm = {}
    for t in TASKS:
        n = normalise(orient(raw[raw.task == t]))
        norm[t] = n
        print(f"\n[{t}]")
        s = n.set_index("model")[DIMENSIONS].round(3)
        s.index = [SHORT[m] for m in s.index]
        print(s.to_string())
    pd.concat(norm.values()).to_csv(OUT / "normalised_dimensions.csv", index=False)

    print("\n" + "=" * 78)
    print("STEP 3 — PROFILE WEIGHT VECTORS (state these verbatim in the write-up)")
    print("=" * 78)
    wv = pd.DataFrame({p: PROFILES[p]["weights"] for p in PROFILES}).T
    wv["SUM"] = wv.sum(axis=1)
    print(wv.to_string())
    wv.to_csv(OUT / "weight_vectors.csv")
    for p, cfg in PROFILES.items():
        print(f"\n  {p}: {cfg['rationale']}")

    print("\n" + "=" * 78)
    print("STEP 4 — RECOMMENDATION PER PROFILE PER TASK")
    print("=" * 78)
    results, recs = [], {}
    for p, cfg in PROFILES.items():
        recs[p] = {}
        print(f"\n### {p}")
        for t in TASKS:
            n = norm[t]
            feasible = [m for m in survivors[t] if cfg["feasible"](m)]
            excluded_by_filter = [m for m in MODELS
                                  if not cfg["feasible"](m)]
            sub = n[n.model.isin(feasible)].copy()
            sub["score"] = sum(sub[d] * cfg["weights"][d] for d in DIMENSIONS)
            sub = sub.sort_values("score", ascending=False)
            winner = sub.iloc[0]["model"]
            recs[p][t] = winner
            for _, r in sub.iterrows():
                results.append({"profile": p, "task": t, "model": r["model"],
                                "score": round(r["score"], 4)})
            note = ""
            if excluded_by_filter:
                note = (f"  [feasibility filter removed: "
                        f"{', '.join(SHORT[m] for m in excluded_by_filter)}]")
            ladder = "  ".join(f"{SHORT[r.model]}={r.score:.3f}"
                               for _, r in sub.iterrows())
            print(f"  {t:14s} -> {SHORT[winner]:9s}  ({ladder}){note}")
    pd.DataFrame(results).to_csv(OUT / "profile_scores.csv", index=False)

    print("\n" + "=" * 78)
    print("STEP 5 — DISCRIMINATION CHECK (the RO4 demonstration)")
    print("=" * 78)
    table = pd.DataFrame(recs).T[TASKS].map(lambda m: SHORT[m])
    print(table.to_string())
    identical = []
    for a, b in itertools.combinations(PROFILES, 2):
        if all(recs[a][t] == recs[b][t] for t in TASKS):
            identical.append((a, b))
    print()
    if identical:
        print("!" * 78)
        print("FLAG: PROFILES DO NOT DISCRIMINATE")
        for a, b in identical:
            print(f"  '{a}' and '{b}' return IDENTICAL recommendations on all "
                  f"three tasks.")
        print("  This is reported as-is. Weights have NOT been adjusted to")
        print("  manufacture separation — doing so would make the RO4")
        print("  demonstration circular.")
        print("!" * 78)
    else:
        print("All three profiles are distinguishable: no two profiles return "
              "the same model on every task.")
        n_distinct = len({tuple(recs[p][t] for t in TASKS) for p in PROFILES})
        print(f"Distinct recommendation vectors: {n_distinct} of {len(PROFILES)}.")
        for t in TASKS:
            picks = {recs[p][t] for p in PROFILES}
            print(f"  {t:14s}: {len(picks)} distinct pick(s) across profiles "
                  f"-> {', '.join(sorted(SHORT[m] for m in picks))}")

    table.to_csv(OUT / "recommendations.csv")
    print(f"\nWritten to {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
