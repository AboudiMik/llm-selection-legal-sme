"""
score_coverage_cuad.py
----------------------
GROUND-TRUTH coverage scoring for the summarisation task.

WHY THIS EXISTS
---------------
The summarisation task has no gold standard for "material obligations", so it
was scored entirely by an LLM judge. That leaves the RO2 reliability argument
resting on one LLM assessing another. This script supplies an INDEPENDENT,
NON-LLM check by reusing CUAD's own expert clause annotations:

    for every clause type CUAD says IS PRESENT in a contract,
    does the model's brief actually mention it?

No API calls, no judge. Just the dataset's annotations versus the briefs.

WHAT IT MEASURES, AND WHAT IT DOES NOT
--------------------------------------
It measures CLAUSE-TYPE RECALL against expert annotation. It is NOT a
correctness score: a five-field brief cannot possibly mention all 20 clause
types in a dense contract, so a low absolute percentage is expected and is not
an error. The number is meaningful only COMPARATIVELY -- all five models face
the identical constraint on the identical contracts.

DESIGN DECISIONS (surfaced, not made silently)
----------------------------------------------
1. GOVERNING LAW IS EXCLUDED. The brief prompt asks for parties, purpose,
   key_obligations, term and risks. It never asks for governing law, so
   scoring it would penalise every model for something the prompt did not
   request. 30 of our contracts carry a Governing Law annotation; all are
   dropped. Every other category maps onto obligations, risks or term.
2. Only categories with >= MIN_OCCURRENCES gold-present contracts are scored,
   so no model is ranked on a category appearing once or twice.
3. Each detector carries a CONFIDENCE tier. Loose detectors (e.g. "minimum"
   for Minimum Commitment) produce false positives; the summary is reported
   both for all detectors and for HIGH-confidence detectors only, so the
   conclusion can be checked against the stricter subset.
4. A validation sample is emitted for human spot-checking, because the whole
   point of this script is to be more trustworthy than the LLM judge -- an
   unvalidated regex would not be.

OUTPUTS
-------
results/coverage_cuad/coverage_detail.csv    one row per (contract, clause, model)
results/coverage_cuad/coverage_by_model.csv  headline table
results/coverage_cuad/validation_sample.csv  30 rows for human detector checking

Usage:
    ./venv/bin/python src/score_coverage_cuad.py
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SUMM = ROOT / "results" / "summarisation"
OUT = ROOT / "results" / "coverage_cuad"
MASTER = ROOT / "data" / "cuad" / "CUAD_v1" / "master_clauses.csv"
MANIFEST = ROOT / "results" / "sample_manifest.csv"

SEED = 42
MIN_OCCURRENCES = 5      # skip clause types too rare to rank models on
VALIDATION_N = 30        # rows emitted for human detector checking

# Detectors. `conf` is the researcher-facing confidence in the pattern:
#   high   - the word is near-unambiguous in a contract brief
#   medium - usually right, but the term has other senses
#   low    - deliberately broad; reported separately, never on its own
DETECTORS = {
    "Anti-Assignment":                  (r"assign", "high"),
    # TIGHTENED 27 Aug after the validation sample exposed false positives.
    # The original r"liabilit|indemnif|cap\b" fired on "general LIABILITY
    # INSURANCE ($5m per occurrence)" -- insurance, not a cap -- giving an
    # implausible 97.4%. Cap language must now be explicit.
    "Cap On Liability":                 (r"cap(?:ped|s)? on liabilit|liabilit\w*[^.]{0,40}"
                                         r"(?:cap|limited to|not exceed|ceiling)|"
                                         r"limitation of liabilit|shall not exceed|"
                                         r"maximum liabilit|aggregate liabilit", "high"),
    "Uncapped Liability":               (r"uncapped|unlimited liabilit|no (?:liability )?cap|"
                                         r"no limitation of liabilit|without limitation of liabilit",
                                         "high"),
    # Original included r"\bterm\b", which appears in almost every brief.
    "Expiration Date":                  (r"expir|end date|ends? on|until \d|through \d{4}|"
                                         r"terminat\w+ date", "medium"),
    "Renewal Term":                     (r"renew|extend", "high"),
    # Original bare r"terminat" matched termination for BREACH as well, giving
    # a 100% hit rate. Convenience-specific language is now required.
    "Termination For Convenience":      (r"convenience|without cause|for any reason|at will|"
                                         r"unilateral\w*[^.]{0,30}terminat|"
                                         r"terminat\w*[^.]{0,30}unilateral", "high"),
    "License Grant":                    (r"licen[sc]", "high"),
    "Non-Transferable License":         (r"non-?transferab|not transferab", "high"),
    "Irrevocable Or Perpetual License": (r"perpetual|irrevocab", "high"),
    "Affiliate License-Licensee":       (r"affiliate", "medium"),
    "Audit Rights":                     (r"audit|inspect|examine .{0,30}record", "high"),
    "Insurance":                        (r"insur", "high"),
    "Exclusivity":                      (r"exclusiv", "high"),
    "Non-Compete":                      (r"compet", "high"),
    # r"waiv" dropped: waiver language is common and unrelated.
    "Covenant Not To Sue":              (r"not to sue|covenant not to|refrain from suing", "high"),
    "No-Solicit Of Employees":          (r"solicit|poach|hire .{0,30}employee", "high"),
    "Change Of Control":                (r"change of control|acquisition|merger|acquir", "low"),
    "Revenue/Profit Sharing":           (r"revenue shar|profit shar|royalt|commission", "high"),
    "Minimum Commitment":               (r"minimum|at least|no less than", "low"),
    # r"cap\b" and bare r"limit" dropped: both fired on unrelated cap/limit text.
    "Volume Restriction":               (r"volume|quantit|maximum (?:of|number|amount)", "low"),
    # r"survive" dropped: survival clauses are not post-termination services.
    "Post-Termination Services":        (r"post-?termination|transition|after termination|"
                                         r"wind.?down", "medium"),
    # bare r"ownership" dropped: matched share ownership, equity, etc.
    "Ip Ownership Assignment":          (r"intellectual property|work made for hire|"
                                         r"ip ownership|owns? (?:all )?(?:right|title)", "high"),
    "Warranty Duration":                (r"warrant", "high"),
    "Liquidated Damages":               (r"liquidated damages|penalt", "high"),
}


def gold_present(value) -> bool:
    """CUAD marks absence as blank, 'nan', '[]' or a literal 'No'."""
    s = str(value).strip()
    return s not in ("", "nan", "[]", "No", "no")


def load_briefs() -> dict:
    """(model, contract) -> lowercased brief text, for successful parseable calls."""
    out = {}
    for path in sorted(SUMM.glob("briefs__*.csv")):
        model = path.name[len("briefs__"):-len(".csv")]
        df = pd.read_csv(path)
        df = df[df["call_error"].isna()] if "call_error" in df else df
        for _, row in df.iterrows():
            try:
                brief = json.loads(row["brief_json"])
            except Exception:
                continue          # unparseable brief cannot be scored
            if not isinstance(brief, dict):
                continue
            # Score against the fields the prompt actually asked for.
            text = " ".join(str(brief.get(f, "")) for f in
                            ("purpose", "key_obligations", "term", "risks"))
            out[(model, row["contract"])] = text.lower()
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    man = pd.read_csv(MANIFEST)
    fn2txt = dict(zip(man["Filename"], man["txt_name"]))
    gold = pd.read_csv(MASTER)
    gold = gold[gold["Filename"].isin(man["Filename"])].set_index("Filename")
    briefs = load_briefs()
    models = sorted({m for m, _ in briefs})

    # Which categories clear the frequency floor?
    freq = {}
    for cat in DETECTORS:
        col = f"{cat}-Answer"
        if col in gold.columns:
            freq[cat] = int(gold[col].map(gold_present).sum())
    scored = {c: n for c, n in freq.items() if n >= MIN_OCCURRENCES}
    dropped = {c: n for c, n in freq.items() if n < MIN_OCCURRENCES}
    if dropped:
        print(f"skipped (fewer than {MIN_OCCURRENCES} gold-present contracts): "
              + ", ".join(f"{c}({n})" for c, n in sorted(dropped.items())))

    rows = []
    for fn, grow in gold.iterrows():
        contract = fn2txt.get(fn)
        for cat in scored:
            if not gold_present(grow[f"{cat}-Answer"]):
                continue
            pattern, conf = DETECTORS[cat]
            for model in models:
                text = briefs.get((model, contract))
                if text is None:
                    continue      # e.g. the one unparseable GPT brief
                rows.append({
                    "contract": contract,
                    "clause": cat,
                    "confidence": conf,
                    "model": model,
                    "mentioned": bool(re.search(pattern, text)),
                })
    detail = pd.DataFrame(rows)
    detail.to_csv(OUT / "coverage_detail.csv", index=False)

    print(f"\nclause types scored: {len(scored)}  |  checks: {len(detail)}"
          f"  |  contracts: {detail['contract'].nunique()}")

    # Headline: all detectors, then high-confidence only as a robustness check.
    allc = detail.groupby("model")["mentioned"].agg(["size", "mean"])
    hi = (detail[detail["confidence"] == "high"]
          .groupby("model")["mentioned"].agg(["size", "mean"]))
    table = pd.DataFrame({
        "checks": allc["size"], "coverage_all": allc["mean"].round(3),
        "checks_high_conf": hi["size"], "coverage_high_conf": hi["mean"].round(3),
    }).sort_values("coverage_all", ascending=False)
    table.to_csv(OUT / "coverage_by_model.csv")
    print("\n=== COVERAGE OF CUAD-GOLD CLAUSES (ground truth, no LLM) ===")
    print(table.to_string())

    print("\n=== BY CLAUSE TYPE (mean across models) ===")
    per = (detail.groupby(["clause", "confidence"])["mentioned"]
           .agg(["size", "mean"]).round(3).sort_values("mean"))
    print(per.to_string())

    # Validation sample: the detector is the weak link, so make it checkable.
    rng = random.Random(SEED)
    idx = rng.sample(range(len(detail)), min(VALIDATION_N, len(detail)))
    val = detail.iloc[sorted(idx)].copy()
    val["brief_excerpt"] = [
        (briefs.get((r["model"], r["contract"]), "")[:600] + "...")
        for _, r in val.iterrows()]
    val["detector_correct_y_n"] = ""      # researcher fills: did the brief really discuss it?
    val["notes"] = ""
    val.to_csv(OUT / "validation_sample.csv", index=False)
    print(f"\nvalidation sample ({len(val)} rows) -> {OUT / 'validation_sample.csv'}")
    print("Fill detector_correct_y_n to measure detector precision before reporting.")


if __name__ == "__main__":
    main()
