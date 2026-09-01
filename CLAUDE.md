# Dissertation Project — LLM Selection Framework for Legal SMEs

## Context

MSc Applied AI for Business dissertation (INMR78, Henley Business School).
**Deadline: 4 September 2026, 2pm. Zero slack.**

Building a practitioner-oriented framework that helps small UK legal firms choose
between LLMs for real operational tasks. Methodology is Design Science Research.
The headline artefact is a one-page procurement scorecard.

## Research objectives

- **RO1** — Identify recurring, comparable LLM tasks in legal professional services
- **RO2** — Develop an evaluation method measuring usefulness and enabling comparison
- **RO3** — Apply the method empirically
- **RO4** — Synthesise into a procurement framework; evaluate via informed argument
  (criteria traced to OECD SME barrier data) and summative artificial demonstration

## Locked scope — do not expand

- **Sector:** UK legal SMEs only (not accountancy)
- **Tasks:** 3 only — clause extraction, long-document Q&A, summarisation
- **Models:** 5 only — 3 commercial APIs, 2 open-source via API (no self-hosting)
- **Dataset:** CUAD only (`theatticusproject/cuad`, CC BY 4.0)
- **Sample:** ~30–50 contracts, 5–8 clause categories
- **No human participants.** No ethics application required.

If a change would expand scope, flag it and stop. Do not implement.

## Supervised decisions — 28 Aug 2026. HARD CONSTRAINTS.

Ruled by the supervisor at the 28 August supervision meeting. These are not
proposals and not inferred from files. They override any earlier plan, note or
logbook entry that conflicts with them. Full record: `notes/logbook.md`,
"SUPERVISED DECISIONS — supervision meeting, 28 August 2026".

1. **FinQA is CANCELLED. The study is SINGLE-DOMAIN LEGAL.** Do not add,
   propose, or build a second domain. No cross-domain generalisation claim.
2. **Word budget rebalances toward Results, Research Design and Discussion.**
   Literature review and background compress.
3. **Findings are framed for BUSINESS READERS**, with visualisations that
   matter to a law SME. Every figure carries a one-sentence practitioner
   takeaway; technical framing moves to methodology and appendix.
4. **A cost-to-benefit analysis is required.** Quality-per-dollar per task is a
   first-class result, not a footnote.
5. **Limitations must be EXHAUSTIVE, with a stated reason for every scoping
   choice** — not just what was excluded but why. See
   `notes/handoff_for_writing.md` §F (30 entries).
6. **Weighting is PROFILE-BASED (Option B).** A single universal weight vector
   is rejected. Three named buyer profiles with published weight vectors.
   **Never tune the weights to manufacture separation between profiles** — that
   would make the RO4 demonstration circular. If profiles fail to discriminate,
   report it.

## NO DISSERTATION TEXT IN THIS ENVIRONMENT

**Writing moved to a separate environment on 28 Aug 2026.** This environment
produces data, computation, instruments and handoff material **only**.

Do not draft, ghost-write, or "sketch" chapter prose, abstracts, chapter
introductions, discussion paragraphs, or scorecard copy here — not as an
example, not as a starting point, not because it would be quicker. If asked for
something that is really dissertation text, say so and stop.

**Permitted here:** analysis scripts, computed tables, worksheets and
instruments, logbook entries, and factual handoff notes that transcribe results
and definitions from source files.

The single source for the writing phase is `notes/handoff_for_writing.md`.

## Directory layout

```
dissertation/
├── data/cuad/      CUAD dataset (510 contracts, master clauses CSV)
├── src/            Python code
├── results/        Raw model outputs, scores
├── outputs/        Figures, tables, scorecard
└── notes/          Logbook (goes in dissertation appendix)
```

## Technical decisions already made

- Python venv at `./venv` — always activate before running
- Ground truth from CUAD master clauses CSV; join to contracts via filename
- Clause extraction scored automatically against ground truth (precision/recall/F1)
- Subjective tasks scored by LLM-as-judge + human spot-check on 20 outputs
- Log tokens, latency, and cost on every single API call — cost-per-task is a
  core finding, not an afterthought

## Working rules

1. **Explain all code.** Comment what each block does and why. I need to
   understand and modify it, not just run it.
2. **Small steps.** One working piece at a time. Verify before extending.
3. **Never fabricate results.** If something fails, say so. Fabricated numbers
   would end the degree.
4. **Cost awareness.** Estimate API spend before any full run. Budget ~£200–300 total.
5. **Reproducibility.** Set random seeds. Save raw responses before any processing.
6. **Don't make methodological choices silently.** Sample sizes, thresholds,
   prompt strategies, scoring rules — surface these for a decision, with the
   trade-offs, rather than picking one.
7. **"Before scaling" and "decision needed" are HARD GATES.** Any instruction,
   note, or logbook entry marked *before scaling*, *decision needed*, *open
   decision*, or *NOT decided here* blocks the work it gates. Do not run the
   gated step — not to save time, not because a deadline is close, not because
   the surrounding config says "locked". "Locked" describes a rubric or
   threshold that must not be edited; it does **not** mean the decision about
   whether to run it has been made. Stop and ask.
8. **On ambiguity between the logbook and conversation, stop and ask.** The
   logbook is a record of what happened, not standing authorisation for what
   happens next. If a file implies one thing and the conversation implies
   another — or if a session starts with no history and you are reconstructing
   intent from files — surface the conflict and wait. Reconstructed intent is a
   hypothesis, never an instruction. **Never treat "continue" as approval for
   spend or for a gated step.**

*Rules 7 and 8 were added on 25 Aug 2026 after a full 40-contract summarisation
run ($5.43) was executed from a reconstructed logbook state while the rubric
decision that explicitly gated scaling was still open.*

## Timeline gates

- **Day 4 (21 Aug):** harness produces scored output, 3 tasks × 5 models. If not,
  cut to 2 tasks and proceed.
- **Day 8 (25 Aug):** all empirical work stops. Unfinished work becomes a
  documented limitation, not a chase.

## Out of scope for this session

Chapter drafting, methodology argumentation, literature review, and scorecard
design happen elsewhere. This session is build and run only.
