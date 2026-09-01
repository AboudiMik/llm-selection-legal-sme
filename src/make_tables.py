"""
make_tables.py
--------------
Builds the six main-text tables.

Every cell is computed from the result files or transcribed from a named
source document — nothing is retyped from memory. Emits, for each table:
  outputs/tables/tableN_*.csv   machine-readable, for programmatic docx build
  outputs/tables/TABLES.md      formatted, with captions and footnotes

FORMATTING STANDARD (identical across all six — inconsistency is what makes
tables look amateur):
  - Booktabs rules only: one above the header, one below it, one at the
    bottom. No vertical rules, no shading, no zebra striping.
  - Numbers right-aligned at three decimals; text left-aligned.
  - Units in the header ("Cost, US$/contract"), never repeated in cells.
  - Bold marks the best value per column; a single caption note says so.
    That is the only emphasis used.
  - Caption ABOVE the table (figures take captions below), numbered
    sequentially, referenced in prose before the table appears.
  - Footnotes attach to the table by symbol, never float in distant prose.

NO API CALLS.  Run:  PYTHONPATH=src ./venv/bin/python src/make_tables.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ANA = ROOT / "outputs" / "analysis"
SC = ROOT / "outputs" / "scorecard"
OUT = ROOT / "outputs" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

MODELS = ["claude-sonnet-5", "deepseek-v4-pro", "gemini-3.1-pro",
          "gpt-5.6-terra", "llama-3.3-70b"]
LABEL = {"claude-sonnet-5": "Claude Sonnet 5", "deepseek-v4-pro": "DeepSeek V4-Pro",
         "gemini-3.1-pro": "Gemini 3.1 Pro", "gpt-5.6-terra": "GPT-5.6 Terra",
         "llama-3.3-70b": "Llama 3.3 70B"}
SHORT = {"claude-sonnet-5": "Claude", "deepseek-v4-pro": "DeepSeek",
         "gemini-3.1-pro": "Gemini", "gpt-5.6-terra": "GPT",
         "llama-3.3-70b": "Llama"}

BLOCKS = []          # (number, title, caption, dataframe, footnotes, bold_spec)


def median_latency(model, task):
    path = {"extraction": f"results/prompt_v2/extraction_full__{model}.csv",
            "qa": f"results/prompt_v2/qa_full__{model}.csv",
            "summarisation": f"results/summarisation/briefs__{model}.csv"}[task]
    d = pd.read_csv(ROOT / path)
    return d[d.call_error.isna()].latency_s.median()


# ===========================================================================
# TABLE 1 — consolidated results
# ===========================================================================
def table1():
    cost = pd.read_csv(ANA / "cost_by_model_task.csv")
    cp = cost.pivot(index="model", columns="task", values="cost_per_contract")
    ext = pd.read_csv(ROOT / "results/full_scores_v2.csv").set_index("model")
    qa_item = pd.read_csv(ANA / "qa_per_item.csv")
    cov = pd.read_csv(ROOT / "results/coverage_cuad/coverage_by_model.csv").set_index("model")

    rows = []
    for m in MODELS:
        rows.append({
            "Model": LABEL[m],
            "Extraction: F1": round(ext.loc[m, "span_f1"], 3),
            "Extraction: cost, US$/contract": round(cp.loc[m, "extraction"], 3),
            "Extraction: median latency, s": round(median_latency(m, "extraction"), 2),
            "Q&A: accuracy": round(qa_item[qa_item.model == m].correct.mean(), 3),
            "Q&A: cost, US$/contract": round(cp.loc[m, "qa"], 3),
            "Q&A: median latency, s": round(median_latency(m, "qa"), 2),
            "Summarisation: coverage": round(cov.loc[m, "coverage_all"], 3),
            "Summarisation: cost, US$/contract": round(cp.loc[m, "summarisation"], 3),
            "Summarisation: median latency, s": round(median_latency(m, "summarisation"), 2),
        })
    df = pd.DataFrame(rows)
    bold = {c: ("max" if ("F1" in c or "accuracy" in c or "coverage" in c)
                else "min") for c in df.columns if c != "Model"}
    caption = ("Headline quality, cost and latency for five models across the "
               "three tasks, 40 CUAD contracts. Quality is span F1 against "
               "expert-annotated clause spans (extraction), item accuracy over "
               "120 questions (Q&A), and share of expert-annotated clause types "
               "mentioned (summarisation). Best value in each column is bold.")
    notes = [
        "Coverage is complete (240/240 extraction and 120/120 Q&A calls per "
        "model; 199 briefs judged, of which GPT contributes 39 because one "
        "brief was unparseable at generation).",
        "† GPT-5.6 Terra and Claude Sonnet 5 are statistically tied on "
        "summarisation coverage (.649 vs .646) and their order reverses under "
        "high-confidence detectors (.667 vs .689). The order shown is not "
        "meaningful.",
        "‡ DeepSeek figures are for its first-party API run off-peak. The "
        "same model served by a third-party host scored span precision .474 "
        "against .833 on identical prompts the same day, and first-party "
        "pricing doubles inside two daily UTC windows.",
    ]
    BLOCKS.append((1, "Consolidated results", caption, df, notes, bold))


# ===========================================================================
# TABLE 2 — dimension-to-instrument map (the RO2 contribution)
# ===========================================================================
def table2():
    rows = [
        {"Dimension": "D1 Completeness",
         "What it asks": "Does it find what is there?",
         "Extraction": "Span recall vs CUAD gold spans (τ = 0.25)",
         "Q&A": "Item accuracy vs CUAD gold answers",
         "Summarisation": "CUAD gold clause-type coverage",
         "Instrument class": "Ground truth"},
        {"Dimension": "D2 Trustworthiness",
         "What it asks": "Is it right when it speaks?",
         "Extraction": "Span precision + absent-clause silence rate",
         "Q&A": "Yes/No positive-class precision",
         "Summarisation": "LLM-judge faithfulness pass rate",
         "Instrument class": "Ground truth (tasks 1–2); LLM judge (task 3)"},
        {"Dimension": "D3 Cost",
         "What it asks": "What does one contract cost?",
         "Extraction": "US$/contract, 6 calls",
         "Q&A": "US$/contract, 3 calls",
         "Summarisation": "US$/contract, 1 call",
         "Instrument class": "Metered"},
        {"Dimension": "D4 Speed",
         "What it asks": "How long does a reader wait?",
         "Extraction": "Median seconds per call",
         "Q&A": "Median seconds per call",
         "Summarisation": "Median seconds per call",
         "Instrument class": "Metered"},
        {"Dimension": "D5 Operational reliability",
         "What it asks": "Does it return usable output every time?",
         "Extraction": "Strict-JSON rate × calls completed",
         "Q&A": "Calls completed / attempted",
         "Summarisation": "Fields present × briefs parsed",
         "Instrument class": "Metered"},
    ]
    df = pd.DataFrame(rows)
    caption = ("The evaluation dimensions and the instrument used to measure "
               "each, per task. The dimensions carry the same meaning in every "
               "task; only the instrument changes. Selecting the instrument "
               "that can actually measure a given dimension is the "
               "methodological contribution of RO2.")
    notes = [
        "Coverage for summarisation is measured against CUAD expert "
        "annotation rather than the LLM judge's own coverage items, because "
        "the judge passed coverage at 97–100% on briefs omitting 35–77% "
        "of the clause types the dataset records as present (Table 5, Figure 6).",
        "Depth (obligations per brief) is deliberately NOT a scored dimension: "
        "the classification instrument that would establish whether extra "
        "depth is material remains uncompleted, so treating more output as "
        "better would import an unvalidated assumption.",
        "Usability is judged by the LLM only and has no independent check of "
        "any kind; it is reported but not scored.",
    ]
    BLOCKS.append((2, "Evaluation dimensions and their instruments", caption,
                   df, notes, {}))


# ===========================================================================
# TABLE 3 — failure-mode taxonomy
# ===========================================================================
def table3():
    fab = pd.read_csv(ROOT / "results/spot_checks/fabrication_checks.csv")
    classified = fab[~fab.failure_mode.str.contains("not classified", na=False)]
    modes = {}
    for v in classified.failure_mode:
        for part in [p.strip() for p in str(v).split("+")]:
            modes[part] = modes.get(part, 0) + 1

    spec = [
        ("Misattribution",
         "The clause exists and is quoted accurately, but the obligation or "
         "restriction is attached to the wrong party, or its direction is "
         "reversed.",
         "Check who owes what to whom.",
         "Dova §12.5: the tail payment applies solely where Dova "
         "terminates; the brief attributed it to Valeant's termination."),
        ("Invention",
         "The clause does not exist in the contract at all.",
         "Check the clause exists before relying on it.",
         "Orbsat clause F: the brief asserts a restriction on AVDU assigning; "
         "the only assignment provision restricts UTK."),
        ("Redaction assertion",
         "The clause and party are right, but the contract redacts the value "
         "and the model supplies one anyway.",
         "Check a figure was actually stated, not inferred.",
         "NETGEAR: the liability cap is redacted as “[*]”; the brief "
         "states a specific cap."),
        ("Conflation",
         "Two unrelated provisions are spliced into a single claim.",
         "Check provenance — which section did this come from?",
         "Cardlytics: a source-code purchase trigger welded to a maintenance "
         "renewal term to assert an overall agreement term."),
    ]
    rows = []
    for name, definition, control, example in spec:
        rows.append({
            "Mechanism": name,
            "Definition": definition,
            "Instances": modes.get(name.lower(), modes.get(name, 0)),
            "Workflow control it implies": control,
            "Verified example": example,
        })
    df = pd.DataFrame(rows)
    n_class = len(classified)
    caption = (f"Failure mechanisms identified in the summarisation "
               f"faithfulness failures, with the verification step each "
               f"implies. Counts are instances across the {n_class} of 13 "
               f"failures that carry a mechanism label; one failure exhibits "
               f"two mechanisms, so instances exceed items.")
    notes = [
        f"† {13 - n_class} of the 13 faithfulness failures are not yet "
        "classified by mechanism, so NO share of the 13 is reported and none "
        "should be inferred. The counts are a floor.",
        "‡ The researcher's verdicts confirm that the judge was correct "
        "to fail each item. They do not attest the mechanism labels, which "
        "were derived from verified source-text quotations but not "
        "independently classified.",
        "Misattribution is the most consequential mechanism because the "
        "output reads as competent legal analysis and can only be caught by "
        "returning to the contract — the work the brief was meant to save.",
    ]
    BLOCKS.append((3, "Failure-mode taxonomy", caption, df, notes, {}))


# ===========================================================================
# TABLE 4 — profile weight vectors
# ===========================================================================
def table4():
    w = pd.read_csv(SC / "weight_vectors.csv", index_col=0)
    pretty = {"D1_completeness": "D1 Completeness",
              "D2_trustworthiness": "D2 Trustworthiness",
              "D3_cost": "D3 Cost", "D4_speed": "D4 Speed",
              "D5_operational_reliability": "D5 Operational reliability"}
    name = {"cost-constrained": "Cost-constrained",
            "confidentiality-constrained": "Confidentiality-constrained",
            "quality-critical": "Quality-critical"}
    df = w.rename(columns=pretty, index=name).reset_index()
    df = df.rename(columns={"index": "Buyer profile", "SUM": "Total"})
    caption = ("Weight vectors for the three buyer profiles. Weights are "
               "stated rather than fitted, and trace to the OECD SME "
               "technology-adoption barrier categories of cost, trust and "
               "assurance, and skills and integration capacity.")
    notes = [
        "The confidentiality-constrained profile additionally applies a "
        "feasibility filter restricting the candidate set to open-weight "
        "models the firm could relocate in-house or to a controlled host.",
        "† Deployment route is a feasibility constraint, not a scored "
        "dimension: once the filter is applied every surviving candidate "
        "scores identically on it, so weighting it cannot change any outcome.",
        "Weights were NOT adjusted after seeing the recommendations. Tuning "
        "them to separate the profiles would make the RO4 demonstration "
        "circular (see Table 5).",
    ]
    BLOCKS.append((4, "Buyer profile weight vectors", caption, df, notes, {}))


# ===========================================================================
# TABLE 5 — dominance and unselectability (the RO4 evidence table)
# ===========================================================================
def table5():
    dom = pd.read_csv(SC / "dominance.csv")
    # Simplex shares from scorecard_sensitivity.py, 20,000 seeded Dirichlet draws
    SIMPLEX = {
        "extraction": {"deepseek-v4-pro": 73.3, "claude-sonnet-5": 26.7,
                       "gemini-3.1-pro": 0.0, "gpt-5.6-terra": 0.0},
        "qa": {"deepseek-v4-pro": 98.9, "gemini-3.1-pro": 1.1},
        "summarisation": {"deepseek-v4-pro": 86.0, "gpt-5.6-terra": 7.3,
                          "claude-sonnet-5": 6.2, "gemini-3.1-pro": 0.5},
    }
    TASKN = {"extraction": "Clause extraction", "qa": "Long-document Q&A",
             "summarisation": "Summarisation"}
    rows = []
    for t in ["extraction", "qa", "summarisation"]:
        sub = dom[dom.task == t]
        elim = sorted(set(sub.dominated))
        by = sorted(set(sub.dominated_by))
        survivors = SIMPLEX[t]
        share = ", ".join(f"{SHORT[m]} {v:.1f}%"
                          for m, v in sorted(survivors.items(),
                                             key=lambda x: -x[1]))
        never = [SHORT[m] for m, v in survivors.items() if v == 0.0]
        rows.append({
            "Task": TASKN[t],
            "Eliminated by dominance": ", ".join(SHORT[m] for m in elim) or "—",
            "Dominated by": ", ".join(SHORT[m] for m in by) or "—",
            "Surviving shortlist": ", ".join(SHORT[m] for m in survivors),
            "Share of weight simplex won": share,
            "Cannot win under any weighting": ", ".join(never) or "—",
        })
    df = pd.DataFrame(rows)
    caption = ("Dominance elimination and weight-simplex analysis per task. "
               "A model is dominated when another is at least as good on all "
               "five dimensions and better on at least one; dominated models "
               "leave the shortlist without any weighting argument. Simplex "
               "shares are from 20,000 seeded Dirichlet draws across the "
               "entire space of possible weightings.")
    notes = [
        "Llama 3.3 70B is dominated on all three tasks and is therefore "
        "removable from any shortlist without a value judgement.",
        "On Q&A, Llama dominates Claude Sonnet 5 outright — it is better on "
        "every one of the five dimensions — while itself being dominated by "
        "DeepSeek. Dominance is a pairwise relation, so a model can eliminate "
        "another and still be eliminated in turn.",
        "† DeepSeek is best-in-slate on three or four of the five "
        "dimensions in every task, which is why no coherent buyer profile "
        "selects a different model. The failure of the profiles to "
        "discriminate is a property of the 2026 model slate, not of the "
        "chosen weights.",
        "‡ Gemini and GPT never win clause extraction under any weighting "
        "of these five dimensions. A benchmark league table cannot produce "
        "that statement.",
    ]
    BLOCKS.append((5, "Dominance elimination and unselectability", caption,
                   df, notes, {}))


# ===========================================================================
# TABLE 6 — sampling and scope
# ===========================================================================
def table6():
    rows = [
        {"Step": "CUAD v1, full corpus", "Contracts": 510,
         "Reason for the reduction": "— (starting point: the recognised "
         "expert-annotated benchmark for legal contract review, CC BY 4.0)"},
        {"Step": "Available as plain text", "Contracts": 200,
         "Reason for the reduction": "The public repository ships plain text "
         "for 200 contracts only; the remaining 310 exist as PDF. Extracting "
         "text from PDFs would introduce an OCR error source into the ground "
         "truth itself."},
        {"Step": "Joins cleanly to the annotation file", "Contracts": 194,
         "Reason for the reduction": "Six filenames fail the join on "
         "punctuation differences. Hand-editing filenames to force a match "
         "would be an undocumented manipulation of the ground-truth link, and "
         "194 already far exceeded the target."},
        {"Step": "Sampled for this study", "Contracts": 40,
         "Reason for the reduction": "Top of the pre-registered 30–50 "
         "range; balances statistical power against the API budget and the "
         "eight-day empirical window. Stratified by word count into three "
         "strata (13 short / 13 medium / 14 long), random_state = 42."},
    ]
    df = pd.DataFrame(rows)
    caption = ("Sampling chain from the full CUAD corpus to the study sample, "
               "with the reason for each reduction. Length strata: short "
               "109–2,909 words, medium 2,955–8,147, long "
               "8,396–45,650.")
    notes = [
        "Contract-type skew was checked against the 194-contract pool: no "
        "agreement type exceeds three occurrences in any stratum and the "
        "sample mirrors the pool (Strategic Alliance 2/40 = 5% against 12/194 "
        "= 6%). No re-sampling was required.",
        "Six of CUAD's 41 clause categories were used, selected for a "
        "deliberate difficulty gradient and a mix of span and Yes/No scoring "
        "types.",
        "† CUAD comprises US commercial contracts filed with the SEC, "
        "while the framework targets UK legal SMEs. The tasks and clause "
        "types transfer; governing law and drafting conventions do not. This "
        "is the largest external-validity limitation in the study.",
    ]
    BLOCKS.append((6, "Sampling chain and scope", caption, df, notes, {}))


# ===========================================================================
def fmt(v, col=""):
    """Three decimals throughout, per the house standard — EXCEPT latency in
    seconds, which is measured to roughly 10 ms and would assert false
    precision at 3 dp. The deviation is stated in the formatting note."""
    if isinstance(v, float):
        if "latency" in col.lower():
            return f"{v:.1f}"
        return f"{v:.3f}" if abs(v) < 100 else f"{v:,.0f}"
    return str(v)


def render_md():
    lines = ["# Main-text tables",
             "",
             "Six tables for the main text. Everything per-category, "
             "per-stratum or per-metric-variant belongs in the appendix.",
             "",
             "**Formatting standard, applied identically to all six.** "
             "Booktabs rules only — one above the header, one below it, "
             "one at the bottom; no vertical rules, no shading, no zebra "
             "striping. Numbers right-aligned at three decimals, text "
             "left-aligned. Units in the header, never repeated in cells. "
             "Bold marks the best value per column, and that is the only "
             "emphasis used. Caption above the table (figures take captions "
             "below), numbered sequentially, referenced in prose before the "
             "table appears. Footnote symbols bind caveats to the table, "
             "never to distant prose. One point below body size is acceptable "
             "if width demands it; never break a table across pages — "
             "shrink it or move it to the appendix.",
             "",
             "**One deliberate deviation from the three-decimal rule.** "
             "Latency is reported to one decimal. Call latency is measured to "
             "roughly 10 ms, so \"15.920 s\" would assert a precision the "
             "instrument does not have. Quality and cost keep three decimals.",
             "",
             "**Width warning on Table 1.** At ten columns it is the only "
             "table at risk of overrunning A4 portrait. If it does not fit at "
             "one point below body size, move the three latency columns to the "
             "appendix and keep quality and cost — latency is the least "
             "decision-relevant of the three, and Figure 1 already carries the "
             "cost-quality relationship.",
             "",
             "Build with `PYTHONPATH=src ./venv/bin/python src/make_tables.py`.",
             "", "---", ""]
    for num, title, caption, df, notes, bold in BLOCKS:
        lines.append(f"## Table {num} — {title}")
        lines.append("")
        lines.append(f"**Table {num}.** {caption}")
        lines.append("")
        show = df.copy()
        for col, how in bold.items():
            vals = pd.to_numeric(show[col], errors="coerce")
            target = vals.max() if how == "max" else vals.min()
            show[col] = [f"**{fmt(v, col)}**" if v == target else fmt(v, col)
                         for v in vals]
        for col in show.columns:
            if col not in bold:
                show[col] = show[col].map(lambda v, c=col: fmt(v, c))
        lines.append("| " + " | ".join(show.columns) + " |")
        lines.append("|" + "|".join(
            ["---:" if c in bold else "---" for c in show.columns]) + "|")
        for _, r in show.iterrows():
            lines.append("| " + " | ".join(str(r[c]) for c in show.columns) + " |")
        lines.append("")
        for n in notes:
            lines.append(f"- {n}")
        lines.append("")
        lines.append("---")
        lines.append("")
    (OUT / "TABLES.md").write_text("\n".join(lines))


def main():
    table1(); table2(); table3(); table4(); table5(); table6()
    for num, title, caption, df, notes, bold in BLOCKS:
        slug = title.lower().replace(" ", "_").replace("—", "").replace(",", "")
        df.to_csv(OUT / f"table{num}_{slug}.csv", index=False)
        print(f"  table{num}: {title}  ({len(df)} rows x {len(df.columns)} cols)")
    render_md()
    print(f"\nWritten to {OUT.relative_to(ROOT)}/  (+ TABLES.md)")


if __name__ == "__main__":
    main()
