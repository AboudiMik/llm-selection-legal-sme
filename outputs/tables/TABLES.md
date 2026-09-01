# Main-text tables

Six tables for the main text. Everything per-category, per-stratum or per-metric-variant belongs in the appendix.

**Formatting standard, applied identically to all six.** Booktabs rules only — one above the header, one below it, one at the bottom; no vertical rules, no shading, no zebra striping. Numbers right-aligned at three decimals, text left-aligned. Units in the header, never repeated in cells. Bold marks the best value per column, and that is the only emphasis used. Caption above the table (figures take captions below), numbered sequentially, referenced in prose before the table appears. Footnote symbols bind caveats to the table, never to distant prose. One point below body size is acceptable if width demands it; never break a table across pages — shrink it or move it to the appendix.

**One deliberate deviation from the three-decimal rule.** Latency is reported to one decimal. Call latency is measured to roughly 10 ms, so "15.920 s" would assert a precision the instrument does not have. Quality and cost keep three decimals.

**Width warning on Table 1.** At ten columns it is the only table at risk of overrunning A4 portrait. If it does not fit at one point below body size, move the three latency columns to the appendix and keep quality and cost — latency is the least decision-relevant of the three, and Figure 1 already carries the cost-quality relationship.

Build with `PYTHONPATH=src ./venv/bin/python src/make_tables.py`.

---

## Table 1 — Consolidated results

**Table 1.** Headline quality, cost and latency for five models across the three tasks, 40 CUAD contracts. Quality is span F1 against expert-annotated clause spans (extraction), item accuracy over 120 questions (Q&A), and share of expert-annotated clause types mentioned (summarisation). Best value in each column is bold.

| Model | Extraction: F1 | Extraction: cost, US$/contract | Extraction: median latency, s | Q&A: accuracy | Q&A: cost, US$/contract | Q&A: median latency, s | Summarisation: coverage | Summarisation: cost, US$/contract | Summarisation: median latency, s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Claude Sonnet 5 | 0.648 | 0.262 | 3.4 | 0.775 | 0.125 | 2.2 | 0.646 | 0.056 | 15.9 |
| DeepSeek V4-Pro | **0.706** | **0.052** | **1.7** | 0.817 | **0.025** | 1.2 | 0.486 | **0.010** | **5.8** |
| Gemini 3.1 Pro | 0.684 | 0.162 | 8.2 | **0.825** | 0.078 | 5.6 | 0.436 | 0.031 | 19.9 |
| GPT-5.6 Terra | 0.585 | 0.168 | 3.1 | 0.792 | 0.077 | 1.9 | **0.649** | 0.038 | 13.9 |
| Llama 3.3 70B | 0.486 | 0.081 | 2.1 | 0.808 | 0.040 | **1.0** | 0.229 | 0.014 | 10.1 |

- Coverage is complete (240/240 extraction and 120/120 Q&A calls per model; 199 briefs judged, of which GPT contributes 39 because one brief was unparseable at generation).
- † GPT-5.6 Terra and Claude Sonnet 5 are statistically tied on summarisation coverage (.649 vs .646) and their order reverses under high-confidence detectors (.667 vs .689). The order shown is not meaningful.
- ‡ DeepSeek figures are for its first-party API run off-peak. The same model served by a third-party host scored span precision .474 against .833 on identical prompts the same day, and first-party pricing doubles inside two daily UTC windows.

---

## Table 2 — Evaluation dimensions and their instruments

**Table 2.** The evaluation dimensions and the instrument used to measure each, per task. The dimensions carry the same meaning in every task; only the instrument changes. Selecting the instrument that can actually measure a given dimension is the methodological contribution of RO2.

| Dimension | What it asks | Extraction | Q&A | Summarisation | Instrument class |
|---|---|---|---|---|---|
| D1 Completeness | Does it find what is there? | Span recall vs CUAD gold spans (τ = 0.25) | Item accuracy vs CUAD gold answers | CUAD gold clause-type coverage | Ground truth |
| D2 Trustworthiness | Is it right when it speaks? | Span precision + absent-clause silence rate | Yes/No positive-class precision | LLM-judge faithfulness pass rate | Ground truth (tasks 1–2); LLM judge (task 3) |
| D3 Cost | What does one contract cost? | US$/contract, 6 calls | US$/contract, 3 calls | US$/contract, 1 call | Metered |
| D4 Speed | How long does a reader wait? | Median seconds per call | Median seconds per call | Median seconds per call | Metered |
| D5 Operational reliability | Does it return usable output every time? | Strict-JSON rate × calls completed | Calls completed / attempted | Fields present × briefs parsed | Metered |

- Coverage for summarisation is measured against CUAD expert annotation rather than the LLM judge's own coverage items, because the judge passed coverage at 97–100% on briefs omitting 35–77% of the clause types the dataset records as present (Table 5, Figure 6).
- Depth (obligations per brief) is deliberately NOT a scored dimension: the classification instrument that would establish whether extra depth is material remains uncompleted, so treating more output as better would import an unvalidated assumption.
- Usability is judged by the LLM only and has no independent check of any kind; it is reported but not scored.

---

## Table 3 — Failure-mode taxonomy

**Table 3.** Failure mechanisms identified in the summarisation faithfulness failures, with the verification step each implies. Counts are instances across the 7 of 13 failures that carry a mechanism label; one failure exhibits two mechanisms, so instances exceed items.

| Mechanism | Definition | Instances | Workflow control it implies | Verified example |
|---|---|---|---|---|
| Misattribution | The clause exists and is quoted accurately, but the obligation or restriction is attached to the wrong party, or its direction is reversed. | 5 | Check who owes what to whom. | Dova §12.5: the tail payment applies solely where Dova terminates; the brief attributed it to Valeant's termination. |
| Invention | The clause does not exist in the contract at all. | 1 | Check the clause exists before relying on it. | Orbsat clause F: the brief asserts a restriction on AVDU assigning; the only assignment provision restricts UTK. |
| Redaction assertion | The clause and party are right, but the contract redacts the value and the model supplies one anyway. | 1 | Check a figure was actually stated, not inferred. | NETGEAR: the liability cap is redacted as “[*]”; the brief states a specific cap. |
| Conflation | Two unrelated provisions are spliced into a single claim. | 1 | Check provenance — which section did this come from? | Cardlytics: a source-code purchase trigger welded to a maintenance renewal term to assert an overall agreement term. |

- † 6 of the 13 faithfulness failures are not yet classified by mechanism, so NO share of the 13 is reported and none should be inferred. The counts are a floor.
- ‡ The researcher's verdicts confirm that the judge was correct to fail each item. They do not attest the mechanism labels, which were derived from verified source-text quotations but not independently classified.
- Misattribution is the most consequential mechanism because the output reads as competent legal analysis and can only be caught by returning to the contract — the work the brief was meant to save.

---

## Table 4 — Buyer profile weight vectors

**Table 4.** Weight vectors for the three buyer profiles. Weights are stated rather than fitted, and trace to the OECD SME technology-adoption barrier categories of cost, trust and assurance, and skills and integration capacity.

| Buyer profile | D1 Completeness | D2 Trustworthiness | D3 Cost | D4 Speed | D5 Operational reliability | Total |
|---|---|---|---|---|---|---|
| Cost-constrained | 0.200 | 0.150 | 0.500 | 0.100 | 0.050 | 1.000 |
| Confidentiality-constrained | 0.150 | 0.250 | 0.100 | 0.100 | 0.400 | 1.000 |
| Quality-critical | 0.250 | 0.500 | 0.050 | 0.050 | 0.150 | 1.000 |

- The confidentiality-constrained profile additionally applies a feasibility filter restricting the candidate set to open-weight models the firm could relocate in-house or to a controlled host.
- † Deployment route is a feasibility constraint, not a scored dimension: once the filter is applied every surviving candidate scores identically on it, so weighting it cannot change any outcome.
- Weights were NOT adjusted after seeing the recommendations. Tuning them to separate the profiles would make the RO4 demonstration circular (see Table 5).

---

## Table 5 — Dominance elimination and unselectability

**Table 5.** Dominance elimination and weight-simplex analysis per task. A model is dominated when another is at least as good on all five dimensions and better on at least one; dominated models leave the shortlist without any weighting argument. Simplex shares are from 20,000 seeded Dirichlet draws across the entire space of possible weightings.

| Task | Eliminated by dominance | Dominated by | Surviving shortlist | Share of weight simplex won | Cannot win under any weighting |
|---|---|---|---|---|---|
| Clause extraction | Llama | DeepSeek | DeepSeek, Claude, Gemini, GPT | DeepSeek 73.3%, Claude 26.7%, Gemini 0.0%, GPT 0.0% | Gemini, GPT |
| Long-document Q&A | Claude, GPT, Llama | DeepSeek, Llama | DeepSeek, Gemini | DeepSeek 98.9%, Gemini 1.1% | — |
| Summarisation | Llama | DeepSeek | DeepSeek, GPT, Claude, Gemini | DeepSeek 86.0%, GPT 7.3%, Claude 6.2%, Gemini 0.5% | — |

- Llama 3.3 70B is dominated on all three tasks and is therefore removable from any shortlist without a value judgement.
- On Q&A, Llama dominates Claude Sonnet 5 outright — it is better on every one of the five dimensions — while itself being dominated by DeepSeek. Dominance is a pairwise relation, so a model can eliminate another and still be eliminated in turn.
- † DeepSeek is best-in-slate on three or four of the five dimensions in every task, which is why no coherent buyer profile selects a different model. The failure of the profiles to discriminate is a property of the 2026 model slate, not of the chosen weights.
- ‡ Gemini and GPT never win clause extraction under any weighting of these five dimensions. A benchmark league table cannot produce that statement.

---

## Table 6 — Sampling chain and scope

**Table 6.** Sampling chain from the full CUAD corpus to the study sample, with the reason for each reduction. Length strata: short 109–2,909 words, medium 2,955–8,147, long 8,396–45,650.

| Step | Contracts | Reason for the reduction |
|---|---|---|
| CUAD v1, full corpus | 510 | — (starting point: the recognised expert-annotated benchmark for legal contract review, CC BY 4.0) |
| Available as plain text | 200 | The public repository ships plain text for 200 contracts only; the remaining 310 exist as PDF. Extracting text from PDFs would introduce an OCR error source into the ground truth itself. |
| Joins cleanly to the annotation file | 194 | Six filenames fail the join on punctuation differences. Hand-editing filenames to force a match would be an undocumented manipulation of the ground-truth link, and 194 already far exceeded the target. |
| Sampled for this study | 40 | Top of the pre-registered 30–50 range; balances statistical power against the API budget and the eight-day empirical window. Stratified by word count into three strata (13 short / 13 medium / 14 long), random_state = 42. |

- Contract-type skew was checked against the 194-contract pool: no agreement type exceeds three occurrences in any stratum and the sample mirrors the pool (Strategic Alliance 2/40 = 5% against 12/194 = 6%). No re-sampling was required.
- Six of CUAD's 41 clause categories were used, selected for a deliberate difficulty gradient and a mix of span and Yes/No scoring types.
- † CUAD comprises US commercial contracts filed with the SEC, while the framework targets UK legal SMEs. The tasks and clause types transfer; governing law and drafting conventions do not. This is the largest external-validity limitation in the study.

---
