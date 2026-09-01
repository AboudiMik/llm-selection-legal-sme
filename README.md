# An LLM Selection Framework for Legal SMEs

Research repository accompanying an MSc Applied AI for Business dissertation
(INMR78, Henley Business School, University of Reading, 2026).

The study benchmarks five large language models on three operational legal
tasks — clause extraction, long-document Q&A, and contract summarisation —
over 40 commercial contracts from the CUAD dataset, and synthesises the
results into a procurement framework for small UK legal firms. The
methodology is Design Science Research.

**This repository is the audit trail.** Every number in the dissertation is
computed by a script in `src/` from data in `results/`, and every raw API
response is retained, so any reported figure can be traced from the final
table back to the call that produced it.

## Repository map

| Path | Contents |
|---|---|
| `src/` | All Python code: the API harness, task runners, scorers, the LLM-judge, analysis scripts, and the scorecard computation. Every file carries a docstring explaining what it does and why. |
| `data/cuad/` | The CUAD v1 dataset (see *Data and licence* below): expert clause annotations (`master_clauses.csv`) and 200 plain-text contracts. |
| `results/` | All empirical outputs. `raw/` holds every raw API response (2,622 calls) saved **before** any parsing; `call_log.jsonl` logs tokens, latency and cost per call; scored CSVs sit beside the run that produced them. `.bak` files are deliberate — they preserve pre-correction states referenced in the logbook's audit trail. |
| `results/spot_checks/` | Human-validation worksheets: the 13 researcher-verified fabrication checks, the depth-comparison instrument, and the (unrun) faithfulness-recall worksheets with their pre-registered protocol. |
| `outputs/analysis/` | Recomputed pattern-analysis tables (cost, quality-per-dollar, correlated errors, absent-clause behaviour). |
| `outputs/figures/` | The eight dissertation figures (300 dpi PNG + vector PDF) and their captions. |
| `outputs/tables/` | The six main-text tables as CSV + formatted Markdown. |
| `outputs/scorecard/` | The RO4 scorecard computation: raw and normalised dimension matrices, dominance analysis, profile scores, weight vectors, and sensitivity results. |
| `notes/` | The research logbook — the day-by-day record that forms the dissertation's audit-trail appendix. |
| `CLAUDE.md` | Working rules for the AI coding assistant used during the build (see *AI assistance* below). The logbook's process-correction entries reference these rules. |

## Key artefacts for a reader short on time

1. `notes/logbook.md` — the day-by-day research record, including every
   correction, defect, and provenance flag. Findings that were later refuted
   are retained and marked, not deleted.
2. `outputs/tables/TABLES.md` — the six main-text tables with captions.
3. `outputs/scorecard/` — the procurement scorecard computation, including
   the result that the three buyer profiles fail to discriminate and the
   Pareto/weight-simplex analysis showing why.
4. `outputs/analysis/` and `results/` — every intermediate table and raw
   response needed to trace any reported number to the call that produced it.

## Reproducing the analysis

Everything downstream of the API calls is reproducible offline from the
committed data — no API keys and no spend required:

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Re-score the tasks from the committed raw responses
PYTHONPATH=src python src/score_extraction.py --full        # extraction, tau=0.25
PYTHONPATH=src python src/score_qa.py --with-judge          # Q&A hybrid scoring
PYTHONPATH=src python src/score_coverage_cuad.py            # gold-label coverage

# Pattern analysis, scorecard, figures, tables
PYTHONPATH=src python src/analysis_patterns.py
PYTHONPATH=src python src/analysis_patterns2.py
PYTHONPATH=src python src/analysis_patterns3.py
PYTHONPATH=src python src/scorecard.py
PYTHONPATH=src python src/scorecard_sensitivity.py
PYTHONPATH=src python src/make_figures.py
PYTHONPATH=src python src/make_tables.py
```

Re-running the **model calls themselves** requires API keys for five
providers (copy `.env.example` to `.env`) and costs real money — the full
empirical run cost ≈ US$56. Prices, model availability, and behaviour are
demonstrably volatile on a timescale of weeks (findings F1, F7, F8 in the
logbook), so re-run results will differ from the committed ones; that
volatility is itself a finding of the study.

Random seeds are fixed (`random_state=42` throughout). The sample manifest
(`results/sample_manifest.csv`) pins the exact 40 contracts used.

One portability note: the manifest's `txt_path` column records absolute paths
from the research machine and is retained unmodified as a research record.
The offline scoring scripts above do not use it — they resolve contracts by
filename against `data/cuad/` and raw responses by relative path — so it does
not affect reproduction.

## Data and licence

- **CUAD v1** — The Contract Understanding Atticus Dataset, © The Atticus
  Project, Inc., licensed **CC BY 4.0**, redistributed here under that
  licence with attribution. Source: <https://huggingface.co/datasets/theatticusproject/cuad>
  and Hendrycks et al. (2021), *CUAD: An Expert-Annotated NLP Dataset for
  Legal Contract Review*, arXiv:2103.06268. The dataset's own README and
  datasheet are included unmodified in `data/cuad/CUAD_v1/`.
- **Code** in this repository is released under the MIT License (`LICENSE`).
- **Raw model outputs** in `results/raw/` are retained verbatim as research
  data. They are machine-generated responses to CUAD contract text.

## Ethics

The study uses only public, SEC-filed commercial contracts from CUAD
(CC BY 4.0). No human participants were recruited, no personal data was
processed, and no ethics application was required under the programme's
research ethics procedure.

## AI assistance

An AI coding assistant (Anthropic's Claude) was used to build the harness and
analysis code and to maintain the logbook, under the working rules recorded
in `CLAUDE.md`. All methodological decisions, human validations, and verdicts
are the researcher's; the logbook records assistant-attributed actions
explicitly, including two process failures and their corrections. One model
under test (Claude Sonnet 5) shares a vendor with the assistant; the
LLM-as-judge was therefore drawn from a sixth model family (Qwen3.6-Plus) and
the self-preference mitigations are documented in the logbook and the
research design.
