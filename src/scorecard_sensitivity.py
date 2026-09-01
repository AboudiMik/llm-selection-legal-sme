"""
scorecard_sensitivity.py
------------------------
How safe are the scorecard's recommendations?

Three checks, all deterministic (seeded), no API calls:

  1. MARGIN — winner minus runner-up, per profile per task. A margin inside
     the measurement noise is a coin toss dressed as a recommendation.
  2. WEIGHT PERTURBATION — jitter each stated weight vector 2,000 times and
     count how often the recommendation changes. This is the honest answer to
     "you chose those weights, didn't you?"
  3. WHY THE PROFILES COLLAPSE — is the non-discrimination a weighting
     artefact or a property of the model slate? Tested by checking Pareto
     optimality, which involves no weights at all.

Run:  PYTHONPATH=src ./venv/bin/python src/scorecard_sensitivity.py
"""

import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from scorecard import (MODELS, SHORT, TASKS, DIMENSIONS, PROFILES, OPEN_WEIGHT,
                       build_raw, orient, normalise, dominance, OUT)

RNG = np.random.default_rng(42)          # seeded — reproducible


def section(t):
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


raw = build_raw()
norm, survivors = {}, {}
for t in TASKS:
    o = orient(raw[raw.task == t])
    dominated, _ = dominance(o)
    survivors[t] = [m for m in MODELS if m not in dominated]
    norm[t] = normalise(o).set_index("model")


def score(t, model, weights):
    return sum(norm[t].loc[model, d] * weights[d] for d in DIMENSIONS)


# ---------------------------------------------------------------------------
section("1. MARGIN — winner vs runner-up")
# ---------------------------------------------------------------------------
rows = []
for p, cfg in PROFILES.items():
    for t in TASKS:
        feas = [m for m in survivors[t] if cfg["feasible"](m)]
        s = sorted(((score(t, m, cfg["weights"]), m) for m in feas), reverse=True)
        if len(s) == 1:
            rows.append({"profile": p, "task": t, "winner": SHORT[s[0][1]],
                         "runner_up": "— none —", "margin": None,
                         "verdict": "NO CHOICE: one feasible candidate"})
        else:
            margin = s[0][0] - s[1][0]
            rows.append({"profile": p, "task": t, "winner": SHORT[s[0][1]],
                         "runner_up": SHORT[s[1][1]], "margin": round(margin, 4),
                         "verdict": ("DECISIVE" if margin > 0.10 else
                                     "NARROW" if margin > 0.03 else
                                     "TOO CLOSE TO CALL")})
M = pd.DataFrame(rows)
print(M.to_string(index=False))
M.to_csv(OUT / "sensitivity_margins.csv", index=False)


# ---------------------------------------------------------------------------
section("2. WEIGHT PERTURBATION — 2,000 jittered draws per profile per task")
# ---------------------------------------------------------------------------
print("Each stated weight is perturbed by +/- 50% of its own value, then the")
print("vector is renormalised to sum to 1. Reports how often the stated")
print("winner survives.\n")

rows = []
N = 2000
for p, cfg in PROFILES.items():
    base = np.array([cfg["weights"][d] for d in DIMENSIONS])
    for t in TASKS:
        feas = [m for m in survivors[t] if cfg["feasible"](m)]
        stated = max(feas, key=lambda m: score(t, m, cfg["weights"]))
        if len(feas) == 1:
            rows.append({"profile": p, "task": t, "stated_winner": SHORT[stated],
                         "unchanged_pct": 100.0, "n_alternatives": 0,
                         "note": "single feasible candidate — weights inert"})
            continue
        mat = np.array([[norm[t].loc[m, d] for d in DIMENSIONS] for m in feas])
        wins = {}
        for _ in range(N):
            w = base * RNG.uniform(0.5, 1.5, size=len(base))
            w = w / w.sum()
            k = feas[int(np.argmax(mat @ w))]
            wins[k] = wins.get(k, 0) + 1
        rows.append({"profile": p, "task": t, "stated_winner": SHORT[stated],
                     "unchanged_pct": round(100 * wins.get(stated, 0) / N, 1),
                     "n_alternatives": len([k for k in wins if k != stated]),
                     "note": ", ".join(f"{SHORT[k]} {100*v/N:.0f}%"
                                       for k, v in sorted(wins.items(),
                                                          key=lambda x: -x[1]))})
S = pd.DataFrame(rows)
print(S.to_string(index=False))
S.to_csv(OUT / "sensitivity_weight_perturbation.csv", index=False)


# ---------------------------------------------------------------------------
section("3. WHY THE PROFILES COLLAPSE — Pareto analysis (no weights at all)")
# ---------------------------------------------------------------------------
print("If one model sits on the Pareto frontier alone, or dominates the whole")
print("feasible set, NO weight vector can pick anything else. That would make")
print("non-discrimination a property of the slate, not of the weights.\n")

for t in TASKS:
    o = orient(raw[raw.task == t]).set_index("model")[DIMENSIONS]
    print(f"[{t}]")
    frontier = []
    for m in MODELS:
        dominated_by_any = any(
            (o.loc[x] >= o.loc[m]).all() and (o.loc[x] > o.loc[m]).any()
            for x in MODELS if x != m)
        if not dominated_by_any:
            frontier.append(m)
    print(f"  Pareto frontier: {[SHORT[m] for m in frontier]}")
    # how many dimensions does each frontier model win outright?
    for m in frontier:
        best = [d for d in DIMENSIONS if o[d].max() == o.loc[m, d]]
        print(f"    {SHORT[m]:9s} is best-in-slate on "
              f"{len(best)}/5: {[d.split('_',1)[1] for d in best]}")
    ow = [m for m in frontier if m in OPEN_WEIGHT]
    print(f"  open-weight models on the frontier: {[SHORT[m] for m in ow]}")
    print()

print("Interpretation guide:")
print("  If deepseek is best-in-slate on 3+ of 5 dimensions in a task, every")
print("  profile that weights those dimensions at all will pick it, and the")
print("  profiles CANNOT separate no matter how the weights are set. That is")
print("  an empirical result about the 2026 model market, not a defect in the")
print("  framework — but it must be reported as such, and the framework's")
print("  discriminating power then has to be demonstrated some other way.")


# ---------------------------------------------------------------------------
section("4. WHAT WOULD IT TAKE TO SEPARATE THE PROFILES?")
# ---------------------------------------------------------------------------
print("Search: for each task, is there ANY weight vector on the 5 dimensions")
print("(simplex, 20,000 seeded draws) under which each model wins? A model")
print("that never wins under any weighting is unselectable by this framework.\n")

for t in TASKS:
    feas = survivors[t]
    mat = np.array([[norm[t].loc[m, d] for d in DIMENSIONS] for m in feas])
    W = RNG.dirichlet(np.ones(len(DIMENSIONS)), size=20000)
    winners = np.array(feas)[np.argmax(W @ mat.T, axis=1)]
    vc = pd.Series(winners).value_counts(normalize=True)
    print(f"[{t}] share of the weight simplex won by each surviving model:")
    for m in feas:
        share = vc.get(m, 0.0)
        print(f"    {SHORT[m]:9s} {share:6.1%}"
              + ("   <- never wins under any weighting" if share == 0 else ""))
    print()

print("Done.")
