"""
make_recall_checks.py
---------------------
Builds the FAITHFULNESS-RECALL worksheet — the pre-registered test proposed in
the logbook on 27 Aug and never run.

The problem it closes
---------------------
The judge's faithfulness PRECISION is on record: 13 flagged failures, 13
researcher verdicts of "agree". Its RECALL is unmeasured — nobody has checked
whether it MISSES fabrications in briefs it passed. Two misses are already
known (the FAB-02 brief also omitted the real restriction; DEP-09 shows GPT and
DeepSeek asserting contradictory Works-transfer triggers with both briefs
passed on all 12 items), so recall is known to be below 1 but not quantified.

Sampling frame: briefs where the judge passed ALL TWELVE items in the full run.

TWO DESIGNS ARE BUILT. Both are 15 briefs, balanced 5 models x 3 length strata,
seed 42. They differ in how many distinct CONTRACTS the researcher must read,
and the choice between them is a real methodological trade-off that has NOT
been made here (CLAUDE.md working rule 6).

  design "spread"  — draw each (model, stratum) cell independently. Lands on
      ~7 distinct contracts, ~227k words to read. Briefs are spread over more
      documents, so the false-negative rate is less dependent on the quirks of
      any one contract.

  design "shared"  — pick ONE contract per stratum from the 27 contracts where
      ALL FIVE models passed all 12 items, and take all five briefs of it.
      Still 15 briefs, but only 3 contracts (~3-50k words) to read. It also
      enables CONTRADICTION DETECTION: five briefs on one contract, so where
      two models assert incompatible facts at least one is wrong and the judge
      passed both. That is exactly how the known DEP-09 miss was found.
      COST: the 15 briefs are clustered in 3 documents, so they are not 15
      independent observations and the rate has a wide, document-driven
      interval.

Neither is generated as "the" instrument. Pick one, record the choice, and do
not switch after classification starts.

TWO ANTI-CONTAMINATION RULES, both learned the hard way in this project
-----------------------------------------------------------------------
1. NO MACHINE VERDICTS. This script writes NO suggested answer, no pre-pass,
   no "llm_suggested_verdict" column. The single human-validation instrument in
   this project was contaminated once by an LLM verdict written into a
   researcher column, and once by the assistant offering the researcher a
   ready-made phrasing before they answered. Neither can happen here because
   there is nothing to copy from.
2. NO OVERWRITING HAND-ENTERED WORK. If a worksheet already exists with any
   researcher cell filled, the script refuses to run rather than regenerate.

The `locator` column is a NAVIGATION AID ONLY — a lexical guess at where in the
contract to look. It is explicitly not evidence, and it has been wrong before
(a previous guide pointed at a table of contents). Read the operative clause.

Run:  PYTHONPATH=src ./venv/bin/python src/make_recall_checks.py
"""

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SUM = ROOT / "results" / "summarisation"
OUTDIR = ROOT / "results" / "spot_checks"


def sheets(design: str):
    return (OUTDIR / f"recall_checks__{design}.csv",
            OUTDIR / f"recall_checks_claims__{design}.csv")

SEED = 42
STRATA = ["short", "medium", "long"]
MODELS = ["claude-sonnet-5", "deepseek-v4-pro", "gemini-3.1-pro",
          "gpt-5.6-terra", "llama-3.3-70b"]

# Researcher-owned columns. Their presence with any value blocks regeneration.
BRIEF_RESEARCHER_COLS = [
    "researcher_any_error_found_yes_no",
    "researcher_n_errors",
    "researcher_route",          # how the check was done, recorded AT THE TIME
    "researcher_minutes_spent",
    "notes",
]
CLAIM_RESEARCHER_COLS = [
    "claim_verdict_ok_error_unverifiable",
    "error_mode_invention_misattribution_redaction_conflation",
    "evidence_quote_from_contract",
    "claim_notes",
]

MANIFEST = pd.read_csv(ROOT / "results" / "sample_manifest.csv")
PATHS = MANIFEST.set_index("txt_name")["txt_path"].to_dict()
WORDS = MANIFEST.set_index("txt_name")["word_count"].to_dict()
STRATUM = MANIFEST.set_index("txt_name")["stratum"].to_dict()


def load_clean_passes() -> pd.DataFrame:
    """Full-run briefs where every one of the 12 checklist items passed."""
    rows = []
    for line in (SUM / "judgements.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("run") != "full" or not r.get("items"):
            continue
        items = r["items"]
        if len(items) != 12:
            continue
        if all(bool(v.get("pass")) for v in items.values()):
            rows.append({"model": r["model_under_test"], "contract": r["contract"],
                         "words": WORDS.get(r["contract"]),
                         "stratum": STRATUM.get(r["contract"])})
    return pd.DataFrame(rows)


def load_brief(model: str, contract: str) -> dict:
    """The successful brief for this (model, contract).

    gemini's briefs file holds 45 rows, not 40: the five contracts killed by
    credit depletion (F12) are retained as error rows and their successful
    retries appended, so the same contract appears twice. Filter to the row
    that actually produced a brief.
    """
    df = pd.read_csv(SUM / f"briefs__{model}.csv")
    row = df[(df.contract == contract) & df.brief_json.notna()].iloc[0]
    return json.loads(row.brief_json)


def locator(claim: str) -> str:
    """Lexical navigation hint: the most distinctive token in the claim.

    Preference order: a money figure, then a number with a unit, then the
    longest capitalised word (party names and defined terms), then the longest
    word. NOT evidence — a hint about where to start reading.
    """
    money = re.findall(r"\$[\d,]+(?:\.\d+)?|\b\d+(?:\.\d+)?\s?%", claim)
    if money:
        return money[0]
    caps = [w for w in re.findall(r"\b[A-Z][A-Za-z&\.\-]{3,}\b", claim)
            if w.lower() not in {"the", "this", "agreement", "company", "party",
                                 "parties", "contract", "section"}]
    if caps:
        return max(caps, key=len)
    words = [w for w in re.findall(r"\b[a-zA-Z\-]{6,}\b", claim)]
    return max(words, key=len) if words else ""


def claims_from_brief(b: dict):
    """Flatten a five-field brief into individually checkable factual claims."""
    out = []
    for p in (b.get("parties") or []):
        out.append(("parties", str(p)))
    if b.get("term"):
        out.append(("term", str(b["term"])))
    for o in (b.get("key_obligations") or []):
        out.append(("key_obligations", str(o)))
    for r in (b.get("risks") or []):
        out.append(("risks", str(r)))
    return out


def refuse_if_work_exists(design: str):
    bs, cs = sheets(design)
    for path, cols in [(bs, BRIEF_RESEARCHER_COLS), (cs, CLAIM_RESEARCHER_COLS)]:
        if not path.exists():
            continue
        d = pd.read_csv(path)
        present = [c for c in cols if c in d.columns]
        if present and d[present].notna().any().any():
            raise SystemExit(
                f"REFUSING TO REGENERATE: {path.name} already contains "
                f"hand-entered work. Move or rename it first if you really "
                f"intend to start over.")


def draw_spread(clean):
    """One independently drawn brief per (model, stratum) cell."""
    picks = []
    for m in MODELS:
        for s in STRATA:
            cell = clean[(clean.model == m) & (clean.stratum == s)]
            if cell.empty:
                print(f"  !! no eligible brief for {m} / {s} — cell left empty")
                continue
            picks.append(cell.sample(1, random_state=SEED).iloc[0])
    return pd.DataFrame(picks).reset_index(drop=True)


def draw_shared(clean):
    """One contract per stratum on which ALL FIVE models passed cleanly;
    take all five briefs of it."""
    wide = clean.assign(ok=True).pivot_table(index="contract", columns="model",
                                             values="ok", aggfunc="any")
    wide = wide.reindex(columns=MODELS).fillna(False).astype(bool)
    all_clean = wide[wide.all(axis=1)].index.tolist()
    picks = []
    for s in STRATA:
        cands = sorted(c for c in all_clean if STRATUM.get(c) == s)
        if not cands:
            print(f"  !! no all-clean contract in stratum {s}")
            continue
        chosen = pd.Series(cands).sample(1, random_state=SEED).iloc[0]
        for m in MODELS:
            picks.append({"model": m, "contract": chosen,
                          "words": WORDS.get(chosen), "stratum": s})
    return pd.DataFrame(picks).reset_index(drop=True)


def build(design: str, clean: pd.DataFrame):
    refuse_if_work_exists(design)
    print(f"\n{'-'*70}\nDESIGN: {design}\n{'-'*70}")
    sample = draw_spread(clean) if design == "spread" else draw_shared(clean)
    print(f"Drawn: {len(sample)} briefs over "
          f"{sample.contract.nunique()} distinct contracts "
          f"({sample.drop_duplicates('contract').words.sum():,} words to read)")

    brief_rows, claim_rows = [], []
    for i, r in sample.iterrows():
        cid = f"REC-{i+1:02d}"
        b = load_brief(r.model, r.contract)
        cl = claims_from_brief(b)
        brief_rows.append({
            "check_id": cid, "model": r.model, "contract": r.contract,
            "words": r.words, "stratum": r.stratum,
            "contract_path": PATHS.get(r.contract),
            "judge_verdict": "PASSED all 12 items",
            "n_claims_to_check": len(cl),
            "purpose_field": str(b.get("purpose", ""))[:400],
            **{c: "" for c in BRIEF_RESEARCHER_COLS},
        })
        for j, (field, text) in enumerate(cl, 1):
            claim_rows.append({
                "check_id": cid, "claim_id": f"{cid}.{j:02d}",
                "model": r.model, "contract": r.contract, "stratum": r.stratum,
                "field": field, "claim": text, "locator": locator(text),
                **{c: "" for c in CLAIM_RESEARCHER_COLS},
            })

    bs, cs = sheets(design)
    pd.DataFrame(brief_rows).to_csv(bs, index=False)
    cdf = pd.DataFrame(claim_rows)
    cdf.to_csv(cs, index=False)

    print(f"  {bs.relative_to(ROOT)}   ({len(brief_rows)} briefs)")
    print(f"  {cs.relative_to(ROOT)}   ({len(cdf)} claims, "
          f"median {int(cdf.groupby('check_id').size().median())} per brief)")
    print("  contracts to read:")
    for c, g in sample.groupby("contract"):
        print(f"    {WORDS.get(c):>6,} w  {g.stratum.iloc[0]:6s}  "
              f"{len(g)} brief(s)  {c[:62]}")
    return len(cdf), sample.drop_duplicates("contract").words.sum()


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    clean = load_clean_passes()
    print(f"Eligible frame: {len(clean)} briefs passed all 12 items "
          f"(of 199 judged).")
    print(clean.pivot_table(index="model", columns="stratum", values="contract",
                            aggfunc="count", fill_value=0)[STRATA].to_string())

    summary = {}
    for design in ("spread", "shared"):
        summary[design] = build(design, clean)

    print("\n" + "=" * 70)
    print("WORKLOAD COMPARISON — the choice is the researcher's")
    print("=" * 70)
    print(f"{'design':10s} {'claims':>8s} {'contract words to read':>24s}")
    for d, (n_claims, n_words) in summary.items():
        print(f"{d:10s} {n_claims:>8d} {n_words:>24,}")
    print("""
Both are 15 briefs and identically balanced (5 models x 3 strata), so the
headline denominator is the same either way.

  spread  — more document diversity; the rate is less hostage to three
            particular contracts. Costs far more reading.
  shared  — five briefs per contract, so contradictions between models on the
            same clause become visible; that is a second, cheaper route to
            catching a judge miss. But 15 briefs clustered in 3 documents are
            not 15 independent observations, and the interval is wide.

DECIDE BEFORE STARTING, record the decision in the logbook, and delete the
design you are not using so it cannot be confused for data later.""")


if __name__ == "__main__":
    main()
