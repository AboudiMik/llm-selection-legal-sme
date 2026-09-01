# Figure captions — paste these under the figures

Each entry gives a **caption** (goes under the figure, Harvard-style numbering)
and a **practitioner takeaway** (the business-reader sentence required by the
28 Aug supervised ruling S3). Where a figure carries a caveat, the caveat is in
the caption, not a footnote — it must travel with the image.

Files: `outputs/figures/*.png` (300 dpi, for Word) and `*.pdf` (vector).
All figures are sized to 6.3 in — the usable text width of A4 with 25 mm
margins — so insert at 100%, do not rescale.

Regenerate with `PYTHONPATH=src ./venv/bin/python src/make_figures.py`.

---

## Figure 1 — Cost against quality, by task
`fig1_cost_vs_quality`

**Caption.** Cost per contract (US$) against task quality for five models on
40 CUAD contracts. Quality is span F1 against expert-annotated clauses
(extraction), answer accuracy over 120 items (Q&A), and share of
expert-annotated clause types mentioned (summarisation). Better is up and to
the left. Prices are DeepSeek first-party off-peak, OpenAI, Anthropic, Google
and Together official rates, accessed 17 August 2026.

**Takeaway.** On these three tasks the cheapest model tested was also the most
accurate at finding clauses, so a price premium has to be justified task by
task rather than assumed.

**Caveat to carry.** DeepSeek's figures are specific to its first-party API run
off-peak; the same model served by a third party scored precision .474 against
.833 on identical prompts the same day.

---

## Figure 2 — Model rank reorders across tasks
`fig2_rank_reordering`

**Caption.** Rank on quality (1 = best) for each model on each of the three
tasks, using the quality measures defined in Figure 1. Claude and Llama are
highlighted because they exchange places; the other three are shown in grey.
All five lines are labelled at both ends. GPT and Claude are statistically
tied on summarisation coverage and share an averaged rank, marked with a tie
bracket; the order between them is not meaningful.

**Takeaway.** "Which is the best LLM" has no answer — Claude ranks third at
pulling clauses out of a contract and last at answering questions about one,
so procurement has to be decided per task.

**Caveat to carry.** Two, and both must appear. (i) GPT (.649) and Claude
(.646) are tied on summarisation coverage and their order reverses under
high-confidence detectors (.667 vs .689); they are drawn at a shared rank for
that reason and neither may be named the winner. (ii) Ranks here use pooled
item accuracy for Q&A. On the alternative headline statistic (Yes/No balanced
accuracy) Llama ranks first rather than third. The choice of statistic changes
the ranking, which is itself worth stating (limitation L18).

---

## Figure 3 — Models fail together
`fig3_correlated_errors`

**Caption.** Distribution of items by the number of models answering
incorrectly, observed against the distribution expected if model errors were
statistically independent (exact Poisson-binomial, computed from each model's
own error rate). 240 clause lookups and 120 questions. All five models were
wrong on 37 extraction items against 0.7 expected (×50), and on 10 Q&A items
against 0.03 expected (×289).

**Takeaway.** Running a second model as a check is close to worthless — on
roughly a quarter of the items where anything went wrong, every model got it
wrong, so only the contract settles it.

**Caveat to carry.** The mechanism is item-difficulty heterogeneity — some
clause lookups are hard for every model — rather than a demonstrated shared
bias. The consequence for a verification workflow is the same either way.

---

## Figure 4 — Behaviour when the clause is not there
`fig4_silence_rate`

**Caption.** Across the 119 contract × clause-category lookups where CUAD's
expert annotation records no such clause, the share on which each model
correctly returned nothing, with the number of clauses it produced instead.
Scored against expert annotation; no LLM judge is involved in this measure.

**Takeaway.** Ask not only whether a tool finds the clause but whether it stays
quiet when the clause is absent — one model tested produced text on nearly half
the clauses that did not exist.

**Caveat to carry.** "Absent" means absent from CUAD's fixed 41-category
taxonomy, so a small share of apparent inventions may be real clauses the
dataset does not label. This affects all five models equally and does not
change the ordering.

---

## Figure 5 — Risk is reported the wrong way round
`fig5_inverted_risk`

**Caption.** For each clause type, the share of contracts where CUAD's expert
annotation records the clause present and the model brief mentions it, pooled
across all five models (1,589 checks, 24 clause types, 37 contracts). Liability
clauses highlighted.

**Takeaway.** Every model tested flagged liability when it was capped and
stayed silent when it was unlimited, so an explicit uncapped-liability check
has to be a mandatory human step whichever tool a firm buys.

**Caveat to carry — important.** Low rates for several clause types are partly
an artefact of the brief schema, which asks for five fields and never requests
governing law, audit rights or covenants not to sue. The
capped-versus-uncapped contrast is not affected, because both are risk
allocations the prompt did request. Per-category rates must not be read as
model deficiencies in isolation.

---

## Figure 6 — What the AI judge could not see
`fig6_judge_blindness`

**Caption.** For each model, the share of clause types actually covered by its
briefs (measured against CUAD expert annotation) against the share the LLM
judge scored as covered, over the same 199 briefs. The gap widens as model
quality falls.

**Takeaway.** An AI that grades another AI will report a summary as complete
while a third of the important clauses are missing — completeness has to be
checked against a list of what should be there.

**Note for the Discussion.** This is the study's central methodological result:
an LLM judge is adequate for faithfulness, a closed question answerable from
the document in front of it, and inadequate for coverage, an open question
requiring an external reference standard.

---

## Figure 7 — Clause type matters more than model choice
`fig7_clause_difficulty`

**Caption.** Span F1 against expert-annotated clauses for each of the six
clause categories, with one dot per model and the bar spanning worst to best.
Categories ordered by best achieved score. Dots are deliberately undifferentiated
by model: the comparison here is between clause types, and per-model
per-category values are given in the appendix table.

**Takeaway.** Automate the clause types that are close to solved — governing
law, dates — and keep the judgement-heavy ones as human work with AI
assistance, because no model choice rescues the hard categories.

**Caveat to carry.** Non-Compete's low scores are substantially a taxonomy
artefact rather than model failure: CUAD's Non-Compete definition covers
territory restrictions that the dataset files separately under Exclusivity, so
models are penalised for clauses the gold standard assigns elsewhere. This
single category generates 42% of all false positives recorded in the study.

---

## Figure 8 — How much material a fee-earner must review
`fig8_review_burden`

**Caption.** Clauses returned for every clause that actually exists, across
240 extraction calls per model. The reference line marks one returned clause
per clause present; everything to its right is text a reviewer must read and
reject.

**Takeaway.** A tool that returns more is not being thorough — the models that
return most create review work that has to be paid for in fee-earner time, and
that cost does not appear on any invoice.

---

# Design notes (for the methodology appendix, if asked)

- **Palette.** A validated categorical palette, checked with an automated
  colour-vision-deficiency validator before any chart was drawn: lightness
  band, chroma floor, adjacent-pair CVD separation (ΔE ≥ 8, OKLab ×100),
  normal-vision floor (ΔE ≥ 15) and surface contrast. Six of the eight figures
  use a single colour, so colour never carries identity in those.
- **Print safety.** Where more than one series appears, identity is also
  carried by position or a direct label, so the figures survive greyscale
  printing.
- **No dual-axis charts** and no value-ramps on unordered categories; a single
  series is drawn in a single colour throughout.
- **Emphasis rather than decoration.** Figures 1 and 5 grey out the
  non-essential marks and highlight the ones carrying the finding.
