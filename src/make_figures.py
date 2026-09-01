"""
make_figures.py
---------------
Builds the eight recommended dissertation figures from the computed results.

Medium: STATIC figures for a Word/PDF dissertation on A4. So there is no hover
layer and no dark mode — but print-safety matters, because an assessor may read
this in greyscale. Every figure therefore carries identity in position or a
direct label, never in colour alone.

Palette: the validated reference palette, light surface only. Validated with
scripts/validate_palette.js before any chart code was written:
  - 5-slot set (bump chart, a LINE form -> adjacent pairlist): ALL PASS,
    with a contrast WARN on three slots -> relief required, satisfied by
    direct labels at both ends of every line.
  - 2-slot set (grouped bars, dumbbell): ALL PASS under --pairs all.
Six of the eight figures use a SINGLE colour, which sidesteps CVD entirely.

Output: outputs/figures/*.png at 300 dpi (for Word) and *.pdf (vector).

NO API CALLS. Reads outputs/analysis/ and results/.

Run:  PYTHONPATH=src ./venv/bin/python src/make_figures.py
"""

import itertools
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning)

ROOT = Path(__file__).resolve().parent.parent
ANA = ROOT / "outputs" / "analysis"
OUT = ROOT / "outputs" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Design tokens — the validated reference palette, light surface
# ---------------------------------------------------------------------------
SURFACE = "#fcfcfb"
INK = "#0b0b0b"          # primary
INK2 = "#52514e"         # secondary
MUTED = "#898781"        # axis / labels
GRID = "#e1e0d9"         # hairline gridline
BASELINE = "#c3c2b7"     # axis rule

# categorical slots, fixed order, never cycled
S1, S2, S3, S4, S5 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
CAT5 = [S1, S2, S3, S4, S5]
DIM = "#d8d7d0"          # de-emphasised bars in the emphasis pattern

MODELS = ["claude-sonnet-5", "deepseek-v4-pro", "gemini-3.1-pro",
          "gpt-5.6-terra", "llama-3.3-70b"]
LABEL = {"claude-sonnet-5": "Claude Sonnet 5", "deepseek-v4-pro": "DeepSeek V4-Pro",
         "gemini-3.1-pro": "Gemini 3.1 Pro", "gpt-5.6-terra": "GPT-5.6 Terra",
         "llama-3.3-70b": "Llama 3.3 70B"}
SHORT = {"claude-sonnet-5": "Claude", "deepseek-v4-pro": "DeepSeek",
         "gemini-3.1-pro": "Gemini", "gpt-5.6-terra": "GPT", "llama-3.3-70b": "Llama"}
# Colour follows the ENTITY, never its rank — fixed for the whole figure set.
MCOLOUR = dict(zip(MODELS, CAT5))

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 8.5,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.edgecolor": BASELINE,
    "axes.linewidth": 0.8,
    "axes.labelcolor": INK2,
    "axes.titlecolor": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "grid.color": GRID,
    "grid.linewidth": 0.7,
    "legend.frameon": False,
    "legend.fontsize": 8,
})

A4_TEXT_W = 6.3          # inches of usable text width on A4 with 25 mm margins


# ---------------------------------------------------------------------------
def load():
    d = {}
    d["cost"] = pd.read_csv(ANA / "cost_by_model_task.csv")
    d["ext_head"] = pd.read_csv(ROOT / "results/full_scores_v2.csv").set_index("model")
    d["ext_cat"] = pd.read_csv(ANA / "extraction_per_category.csv")
    d["ext_item"] = pd.read_csv(ANA / "extraction_per_item.csv")
    d["qa_item"] = pd.read_csv(ANA / "qa_per_item.csv")
    d["judge"] = pd.read_csv(ANA / "judge_items.csv")
    d["cov"] = pd.read_csv(ROOT / "results/coverage_cuad/coverage_by_model.csv").set_index("model")
    d["cov_detail"] = pd.read_csv(ROOT / "results/coverage_cuad/coverage_detail.csv")
    d["absent"] = pd.read_csv(ANA / "absent_clause_behaviour.csv").set_index("model")
    return d


def style_axes(ax, xgrid=False, ygrid=True):
    """Recessive chrome: hairline grid on one axis only, two spines removed."""
    ax.set_axisbelow(True)
    ax.grid(axis="y" if ygrid else "x", visible=ygrid or xgrid, linestyle="-")
    if xgrid:
        ax.grid(axis="x", visible=True, linestyle="-")
        ax.grid(axis="y", visible=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)


def finish(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=300, bbox_inches="tight",
                    pad_inches=0.12)
    plt.close(fig)
    print(f"  wrote {name}.png / .pdf")


def titles(ax, title, subtitle):
    """Title states what it is; subtitle states the finding.

    Offsets are in POINTS, not axes fractions, so the gap between the two
    lines stays constant whatever the figure's height. Axes-fraction offsets
    collapsed into an overlap on the shorter figures.
    """
    for text, dy, size, weight, colour in (
            (subtitle, 9, 8.5, "normal", INK2),
            (title, 24, 10.5, "bold", INK)):
        ax.annotate(text, xy=(0, 1), xycoords="axes fraction",
                    xytext=(0, dy), textcoords="offset points",
                    ha="left", va="bottom", fontsize=size,
                    fontweight=weight, color=colour, annotation_clip=False)


# ---------------------------------------------------------------------------
# Quality measures used consistently across figures 1 and 2
# ---------------------------------------------------------------------------
def quality_and_cost(d):
    cp = d["cost"].pivot(index="model", columns="task", values="cost_per_contract")
    q = {}
    for m in MODELS:
        q[m] = {
            "extraction": (cp.loc[m, "extraction"], d["ext_head"].loc[m, "span_f1"]),
            "qa": (cp.loc[m, "qa"],
                   d["qa_item"][d["qa_item"].model == m].correct.mean()),
            "summarisation": (cp.loc[m, "summarisation"], d["cov"].loc[m, "coverage_all"]),
        }
    return q


TASK_TITLE = {"extraction": "Clause extraction",
              "qa": "Long-document Q&A",
              "summarisation": "Summarisation"}
TASK_YLAB = {"extraction": "Span F1 vs expert-annotated clauses",
             "qa": "Answer accuracy",
             "summarisation": "Share of expert-annotated clauses mentioned"}


# ===========================================================================
def fig1_cost_vs_quality(d):
    """Small multiples. One series, direct-labelled — colour is not the
    identity channel, so the 5-point all-pairs CVD problem does not arise."""
    q = quality_and_cost(d)
    fig, axes = plt.subplots(1, 3, figsize=(A4_TEXT_W, 2.9), sharey=True)
    # SHARED y across panels. All three measures are 0-1 quality proportions,
    # so independent axes would make the Q&A panel's 0.05 spread look as large
    # as extraction's 0.22 — inventing a difference that is not there.
    for i, (ax, task) in enumerate(zip(axes, ["extraction", "qa", "summarisation"])):
        xs = [q[m][task][0] for m in MODELS]
        ys = [q[m][task][1] for m in MODELS]
        best = min(MODELS, key=lambda m: q[m][task][0] / max(q[m][task][1], 1e-9))
        order = sorted(range(5), key=lambda k: ys[k])
        for k in order:
            m, x, y = MODELS[k], xs[k], ys[k]
            hero = (m == best)
            ax.scatter([x], [y], s=54 if hero else 34,
                       color=S1 if hero else MUTED,
                       zorder=3, linewidths=1.3,
                       edgecolors=SURFACE)   # surface ring on overlap
            # Alternate label side when two points sit close vertically.
            near = [j for j in range(5) if j != k and abs(ys[j] - y) < 0.035
                    and abs(xs[j] - x) < max(xs) * 0.28]
            dy = 9 if (not near or x <= min(xs[j] for j in near)) else -13
            ax.annotate(SHORT[m], (x, y), textcoords="offset points",
                        xytext=(0, dy), ha="center", fontsize=7.2,
                        color=INK if hero else INK2,
                        fontweight="bold" if hero else "normal")
        style_axes(ax)
        ax.set_xlim(left=0, right=max(xs) * 1.30)
        ax.set_ylim(0.15, 0.92)
        ax.set_yticks([0.2, 0.4, 0.6, 0.8])
        ax.set_xlabel("US$ per contract", fontsize=8, color=INK2)
        ax.set_title(TASK_TITLE[task], loc="left", fontsize=9,
                     fontweight="bold", color=INK, pad=13)
        ax.text(0, 1.015, TASK_YLAB[task], transform=ax.transAxes,
                fontsize=6.8, color=MUTED, va="bottom")
    axes[0].set_ylabel("Quality (shared scale)", fontsize=8, color=INK2)
    fig.text(0, 1.14, "Cost buys less quality than expected",
             fontsize=10.5, fontweight="bold", color=INK)
    fig.text(0, 1.06,
             "Better is up and to the left. All three panels share one vertical "
             "scale, so the spreads are comparable.",
             fontsize=8.5, color=INK2)
    finish(fig, "fig1_cost_vs_quality")


# ===========================================================================
def fig2_rank_reordering(d):
    """Bump chart. A LINE form, so the adjacent pairlist applies and the
    5-slot palette validates. Contrast WARN relieved by labels at BOTH ends."""
    q = quality_and_cost(d)
    tasks = ["extraction", "qa", "summarisation"]

    # DOCUMENTED TIE. gpt .649 and claude .646 on summarisation gold coverage
    # SWAP places under high-confidence detectors (claude .689, gpt .667), so
    # the project's standing constraint is that they are tied with an unstable
    # order. Drawing them at distinct ranks would assert exactly the thing the
    # constraint forbids, so they share an averaged rank and a tie marker.
    TIES = {"summarisation": {"gpt-5.6-terra", "claude-sonnet-5"}}

    ranks = {}
    for t in tasks:
        order = sorted(MODELS, key=lambda m: -q[m][t][1])
        tied = TIES.get(t, set())
        positions = {m: i for i, m in enumerate(order, 1)}
        if tied:
            avg = sum(positions[m] for m in tied) / len(tied)
            for m in tied:
                positions[m] = avg
        for m in MODELS:
            ranks.setdefault(m, {})[t] = positions[m]

    # Nudge tied models apart vertically so both markers and labels are legible
    # while still sitting at the same rank value.
    NUDGE = {}
    for t, tied in TIES.items():
        for k, m in enumerate(sorted(tied)):
            NUDGE[(m, t)] = (-0.10 if k == 0 else 0.10)

    # A bump chart's lines CROSS, so any two can end up adjacent — the
    # all-pairs pairlist applies, and the 5-slot palette FAILS the
    # normal-vision floor there (verified with the validator). So: emphasis
    # pattern. Two highlighted entities carry validated slots 1 and 2; the
    # rest are muted. Every line is labelled at both ends, so identity never
    # rests on colour at all.
    HERO = ["claude-sonnet-5", "llama-3.3-70b"]
    HCOL = {"claude-sonnet-5": S1, "llama-3.3-70b": S2}

    fig, ax = plt.subplots(figsize=(A4_TEXT_W, 3.1))
    xs = np.arange(len(tasks))
    for m in MODELS:
        ys = [ranks[m][t] + NUDGE.get((m, t), 0.0) for t in tasks]
        hero = m in HERO
        ax.plot(xs, ys, "-o", color=HCOL.get(m, "#cbcac3"),
                linewidth=2.4 if hero else 1.6, markersize=9 if hero else 7,
                markeredgecolor=SURFACE, markeredgewidth=1.6,
                zorder=4 if hero else 2)
        for xi, ha, off in ((xs[0], "right", -9), (xs[-1], "left", 9)):
            t = tasks[0] if xi == xs[0] else tasks[-1]
            if m in TIES.get(t, set()):
                continue          # tied models share one combined label below
            yi = ys[0] if xi == xs[0] else ys[-1]
            ax.annotate(SHORT[m], (xi, yi), textcoords="offset points",
                        xytext=(off, 0), ha=ha, va="center", fontsize=8,
                        color=INK if hero else INK2,
                        fontweight="bold" if hero else "normal")

    # Tie marker: a bracket spanning the two nudged positions, labelled.
    for t, tied in TIES.items():
        xi = xs[tasks.index(t)]
        lo = min(ranks[m][t] + NUDGE.get((m, t), 0.0) for m in tied)
        hi = max(ranks[m][t] + NUDGE.get((m, t), 0.0) for m in tied)
        bx = xi + 0.055
        ax.plot([bx, bx], [lo, hi], color=INK2, linewidth=1.0, zorder=5)
        for yy in (lo, hi):
            ax.plot([bx - 0.022, bx], [yy, yy], color=INK2, linewidth=1.0,
                    zorder=5)
        names = " & ".join(sorted(SHORT[m] for m in tied))
        ax.annotate(f"{names} — tied", (bx, (lo + hi) / 2),
                    textcoords="offset points", xytext=(6, 0), ha="left",
                    va="center", fontsize=8, color=INK, fontweight="bold")
    ax.set_xticks(xs)
    ax.set_xticklabels([TASK_TITLE[t] for t in tasks], fontsize=8.5, color=INK2)
    ax.set_yticks(range(1, 6))
    ax.set_yticklabels([str(i) for i in range(1, 6)])
    ax.set_ylabel("Rank on quality (1 = best)", fontsize=8, color=INK2)
    ax.invert_yaxis()
    ax.set_xlim(-0.72, len(tasks) - 1 + 0.86)
    style_axes(ax, ygrid=True)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True, linestyle="-")
    for s in ("left",):
        ax.spines[s].set_visible(False)
    # Subtitle states ONLY what this chart's own measures show. An earlier
    # draft said "Llama is second at Q&A" — a transcription slip that was
    # true under NEITHER metric: on the pooled item accuracy plotted here
    # Llama ranks third (.808 behind DeepSeek's .817), and on the headline
    # Yes/No balanced accuracy it ranks FIRST (.803). Metric choice changes
    # the ranking (limitation L18), so the caption must match the plotted
    # statistic.
    titles(ax, "There is no single best model",
           "Claude falls from 3rd at extraction to last at Q&A; Llama rises "
           "from last to 3rd.")
    finish(fig, "fig2_rank_reordering")


# ===========================================================================
def _error_distribution(df, key_cols):
    """Observed vs independence-expected counts of items by number of models
    wrong. Exact Poisson-binomial, not a simulation."""
    w = df.pivot_table(index=key_cols, columns="model", values="correct").dropna()
    err = (w == 0)
    n = len(w)
    p = [err[m].mean() for m in MODELS]
    exp = [0.0] * 6
    for bits in itertools.product([0, 1], repeat=5):
        prob = 1.0
        for pi, b in zip(p, bits):
            prob *= pi if b else (1 - pi)
        exp[sum(bits)] += prob
    obs = err.sum(axis=1).value_counts().reindex(range(6), fill_value=0)
    return obs.values, np.array(exp) * n, n


def fig3_correlated_errors(d):
    ei = d["ext_item"].copy()
    ei["correct"] = (ei.tp == ei.n_gold) & (ei.n_pred == ei.n_gold)
    obs_e, exp_e, n_e = _error_distribution(ei, ["contract", "category"])
    obs_q, exp_q, n_q = _error_distribution(d["qa_item"], ["contract", "category"])

    fig, axes = plt.subplots(1, 2, figsize=(A4_TEXT_W, 2.9), sharey=False)
    for ax, (obs, exp, n, name, unit) in zip(axes, [
            (obs_e, exp_e, n_e, "Clause extraction", "clause lookups"),
            (obs_q, exp_q, n_q, "Long-document Q&A", "questions")]):
        x = np.arange(6)
        wdt = 0.38
        ax.bar(x - wdt / 2, obs, wdt, color=S1, label="Observed", zorder=3)
        ax.bar(x + wdt / 2, exp, wdt, color=S2,
               label="If model errors were independent", zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels([str(i) for i in x])
        ax.set_xlabel("Number of models wrong (of 5)", fontsize=8, color=INK2)
        ax.set_title(f"{name}  ({n} {unit})", loc="left", fontsize=9,
                     fontweight="bold", color=INK, pad=6)
        style_axes(ax)
        ax.set_ylim(0, max(obs.max(), exp.max()) * 1.16)
        # Direct-label only the bars that carry the finding.
        ax.annotate(f"{int(obs[5])}", (5 - wdt / 2, obs[5]),
                    textcoords="offset points", xytext=(0, 4), ha="center",
                    fontsize=8, fontweight="bold", color=INK)
        ax.annotate(f"{exp[5]:.1f}" if exp[5] >= 0.05 else "~0",
                    (5 + wdt / 2, exp[5]), textcoords="offset points",
                    xytext=(3, 4), ha="left", fontsize=8, color=INK2)
    axes[0].set_ylabel("Items", fontsize=8, color=INK2)
    # Legend ABOVE the plots, not inside them — an earlier draft placed it
    # over the leftmost bars.
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower left", bbox_to_anchor=(0.0, 0.99), ncols=2,
               handlelength=1.1, labelcolor=INK2, frameon=False)
    fig.text(0, 1.18, "When one model is wrong, the others usually are too",
             fontsize=10.5, fontweight="bold", color=INK)
    fig.text(0, 1.11,
             "Observed errors cluster at both ends; independent errors would "
             "form a single central peak.",
             fontsize=8.5, color=INK2)
    finish(fig, "fig3_correlated_errors")


# ===========================================================================
def fig4_silence_rate(d):
    """One series -> one colour for every bar (never a value-ramp)."""
    s = d["absent"].loc[MODELS, "silence_rate"].sort_values()
    inv = d["absent"].loc[s.index, "spans_invented_on_absent"]
    fig, ax = plt.subplots(figsize=(A4_TEXT_W, 2.6))
    y = np.arange(len(s))
    ax.barh(y, s.values, height=0.5, color=S1, zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels([LABEL[m] for m in s.index], fontsize=8.5, color=INK)
    ax.set_xlim(0, 1.0)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel("Lookups where the clause does not exist and the model "
                  "correctly returned nothing", fontsize=8, color=INK2)
    style_axes(ax, xgrid=True, ygrid=False)
    for yi, (m, v) in enumerate(s.items()):
        ax.annotate(f"{v:.1%}   ({int(inv[m])} clauses invented)",
                    (v, yi), textcoords="offset points", xytext=(6, 0),
                    va="center", fontsize=7.8, color=INK2)
    titles(ax, "Does the model know when to say nothing?",
           "Across 119 clause lookups where the contract contains no such "
           "clause.")
    finish(fig, "fig4_silence_rate")


# ===========================================================================
def fig5_inverted_risk(d):
    """Emphasis pattern: highlight the two bars that carry the finding,
    de-emphasise the rest. Not a value-ramp."""
    ct = (d["cov_detail"].groupby("clause")
          .agg(rate=("mentioned", "mean"), checks=("mentioned", "size"))
          .sort_values("rate"))
    HERO = {"Uncapped Liability", "Cap On Liability"}
    fig, ax = plt.subplots(figsize=(A4_TEXT_W, 4.5))
    y = np.arange(len(ct))
    cols = [S1 if c in HERO else DIM for c in ct.index]
    ax.barh(y, ct.rate.values, height=0.6, color=cols, zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(
        [f"{c}" for c in ct.index], fontsize=7.6,
        color=INK)
    for lbl, c in zip(ax.get_yticklabels(), ct.index):
        if c in HERO:
            lbl.set_fontweight("bold")
    ax.set_xlim(0, 1.0)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel("Share of contracts where the clause exists and the brief "
                  "mentions it", fontsize=8, color=INK2)
    style_axes(ax, xgrid=True, ygrid=False)
    for yi, (c, r) in enumerate(zip(ct.index, ct.rate.values)):
        ax.annotate(f"{r:.1%}", (r, yi), textcoords="offset points",
                    xytext=(6, 0), va="center", fontsize=7.4,
                    fontweight="bold" if c in HERO else "normal",
                    color=INK if c in HERO else MUTED)
    iu = list(ct.index).index("Uncapped Liability")
    ic = list(ct.index).index("Cap On Liability")
    ax.annotate("", xy=(0.66, ic), xytext=(0.66, iu),
                arrowprops=dict(arrowstyle="<->", color=INK2, linewidth=1.0))
    ax.text(0.68, (ic + iu) / 2,
            "reported 7.4×\nmore often when\nliability is CAPPED",
            fontsize=8, color=INK, va="center", fontweight="bold")
    titles(ax, "Risk is reported the wrong way round",
           "All five models pooled. Uncapped liability is the largest "
           "exposure a firm can carry.")
    finish(fig, "fig5_inverted_risk")


# ===========================================================================
def fig6_judge_blindness(d):
    """Dumbbell — the GAP is the story, so encode it as length."""
    jc = (d["judge"][d["judge"].dim == "coverage"]
          .groupby("model").passed.mean())
    gold = d["cov"]["coverage_all"]
    order = sorted(MODELS, key=lambda m: -gold[m])
    fig, ax = plt.subplots(figsize=(A4_TEXT_W, 2.9))
    y = np.arange(len(order))
    for yi, m in enumerate(order):
        ax.plot([gold[m], jc[m]], [yi, yi], color=BASELINE, linewidth=2.2,
                zorder=2, solid_capstyle="round")
        ax.scatter([gold[m]], [yi], s=64, color=S1, zorder=3,
                   edgecolors=SURFACE, linewidths=1.4)
        ax.scatter([jc[m]], [yi], s=64, color=S2, zorder=3,
                   edgecolors=SURFACE, linewidths=1.4)
        ax.annotate(f"gap {jc[m]-gold[m]:.2f}", ((gold[m] + jc[m]) / 2, yi),
                    textcoords="offset points", xytext=(0, 7), ha="center",
                    fontsize=7.4, color=INK2)
    ax.set_yticks(y)
    ax.set_yticklabels([LABEL[m] for m in order], fontsize=8.5, color=INK)
    ax.set_xlim(0, 1.06)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_ylim(len(order) - 0.4, -0.75)   # headroom so the top gap label fits
    ax.set_xlabel("Share of clause types present in the contract",
                  fontsize=8, color=INK2)
    style_axes(ax, xgrid=True, ygrid=False)
    h1 = plt.Line2D([], [], marker="o", linestyle="", color=S1, markersize=7,
                    label="Actually covered (expert annotation)")
    h2 = plt.Line2D([], [], marker="o", linestyle="", color=S2, markersize=7,
                    label="Judged as covered (AI judge)")
    # Legend BELOW the plot — an earlier draft placed it over the Llama row.
    ax.legend(handles=[h1, h2], loc="upper left", bbox_to_anchor=(0.0, -0.20),
              ncols=2, labelcolor=INK2, handletextpad=0.3, columnspacing=1.6)
    titles(ax, "The AI judge cannot see what is missing",
           "It passed coverage at 97–100% on briefs omitting a third to "
           "three-quarters of the clauses.")
    finish(fig, "fig6_judge_blindness")


# ===========================================================================
def fig7_clause_difficulty(d):
    """Range plot: the between-category spread dwarfs the between-model
    spread, so encode category range as length and models as dots."""
    piv = d["ext_cat"].pivot(index="category", columns="model", values="F1")
    piv = piv.loc[piv.max(axis=1).sort_values().index]
    fig, ax = plt.subplots(figsize=(A4_TEXT_W, 3.0))
    y = np.arange(len(piv))
    # A dot plot is an ALL-PAIRS case: any two model dots can land beside each
    # other. The 5-slot palette FAILS the normal-vision floor under --pairs all
    # (worst pair ΔE 12.9, below the 15 floor), and secondary encoding does not
    # excuse that check. Since this figure's claim is about the spread BETWEEN
    # clause types, model identity is not the message — so every dot takes one
    # colour and the CVD problem disappears. Per-model values are in the
    # appendix table and in Figures 1 and 2.
    for yi, cat in enumerate(piv.index):
        vals = piv.loc[cat]
        ax.plot([vals.min(), vals.max()], [yi, yi], color=BASELINE,
                linewidth=2.4, zorder=2, solid_capstyle="round")
        for m in MODELS:
            ax.scatter([vals[m]], [yi], s=32, color=S1, zorder=3,
                       edgecolors=SURFACE, linewidths=1.2)
        ax.annotate(f"{vals.max()-vals.min():.2f} spread",
                    (vals.max(), yi), textcoords="offset points",
                    xytext=(9, 0), va="center", fontsize=7.2, color=MUTED)
    ax.set_yticks(y)
    ax.set_yticklabels(piv.index, fontsize=8.5, color=INK)
    ax.set_xlim(0, 1.16)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xlabel("Span F1 against expert-annotated clauses  "
                  "(one dot per model)", fontsize=8, color=INK2)
    style_axes(ax, xgrid=True, ygrid=False)
    titles(ax, "Which clause you are looking for matters more than which model",
           "Best achievable F1 ranges 0.65 across clause types; the widest "
           "spread between models within one clause type is 0.36.")
    finish(fig, "fig7_clause_difficulty")


# ===========================================================================
def fig8_review_burden(d):
    ratio = (d["ext_head"].loc[MODELS, "span_pred"] /
             d["ext_head"].loc[MODELS, "span_gold"]).sort_values()
    fig, ax = plt.subplots(figsize=(A4_TEXT_W, 2.5))
    y = np.arange(len(ratio))
    ax.barh(y, ratio.values, height=0.5, color=S1, zorder=3)
    ax.axvline(1.0, color=INK2, linewidth=1.0, zorder=4)
    # Headroom above the top bar so the reference-line note is inside the axes;
    # an earlier draft placed it above the ylim and it never rendered.
    ax.set_ylim(-0.65, len(ratio) - 0.15)
    ax.annotate("one returned clause for each that exists",
                (1.0, len(ratio) - 0.38), textcoords="offset points",
                xytext=(6, 0), fontsize=7.4, color=INK2, va="center")
    ax.set_yticks(y)
    ax.set_yticklabels([LABEL[m] for m in ratio.index], fontsize=8.5, color=INK)
    ax.set_xlim(0, 2.0)
    ax.set_xlabel("Clauses returned for every clause that actually exists",
                  fontsize=8, color=INK2)
    style_axes(ax, xgrid=True, ygrid=False)
    for yi, v in enumerate(ratio.values):
        ax.annotate(f"{v:.2f}×", (v, yi), textcoords="offset points",
                    xytext=(6, 0), va="center", fontsize=7.8,
                    fontweight="bold", color=INK)
    titles(ax, "How much material a fee-earner has to review",
           "Everything to the right of the line is material a solicitor must read "
           "and reject.")
    finish(fig, "fig8_review_burden")


def main():
    d = load()
    print("Building figures ->", OUT.relative_to(ROOT))
    fig1_cost_vs_quality(d)
    fig2_rank_reordering(d)
    fig3_correlated_errors(d)
    fig4_silence_rate(d)
    fig5_inverted_risk(d)
    fig6_judge_blindness(d)
    fig7_clause_difficulty(d)
    fig8_review_burden(d)
    print("done")


if __name__ == "__main__":
    main()
