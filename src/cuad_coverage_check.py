"""VERIFICATION SCRIPT — not (yet) an adopted project measure.

Purpose: independently reproduce the claim that summarisation briefs can be
scored against CUAD's expert gold labels, giving a ground-truth coverage
ranking with NO LLM in the loop.

Why it exists: that analysis was originally run ad hoc and left no script or
output file, so its numbers could not be re-derived — a reproducibility
failure under the project's own rules. This file makes the computation
inspectable, re-runnable, and auditable.

Method (deliberately simple, so its weaknesses are visible):
  1. Join the 40-contract sample to CUAD master_clauses.csv.
  2. For each clause category with a NON-EMPTY gold span, the contract is
     treated as genuinely containing that clause.
  3. Ask whether the model's brief mentions it, by matching any of a small
     set of hand-written lexical signatures against the brief text.
  4. Coverage = mentioned / present, pooled across contracts.

KNOWN LIMITATIONS (these are why this is a verification, not a result):
  - Detection is KEYWORD-BASED. "assign" matches unrelated uses of the word,
    so false positives are certain. Needs human spot-checking before it could
    be reported.
  - CUAD labels clause PRESENCE, not what a five-field digest ought to
    contain. A brief cannot mention 20 clause types. The absolute percentage
    is therefore NOT a correctness score; only the BETWEEN-MODEL comparison is
    meaningful, since every model faced an identical constraint.
  - Only categories with reasonably clean lexical signatures are tested.

Run:  ./venv/bin/python src/cuad_coverage_check.py
"""
import ast
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

# Hand-written lexical signatures. Kept deliberately narrow and explicit so a
# reader can judge each one; a category is "mentioned" if ANY phrase appears.
SIGNATURES = {
    "Anti-Assignment":            ["assign", "assignment", "transfer of this agreement"],
    "Cap On Liability":           ["liability", "liable", "damages", "cap on"],
    "Governing Law":              ["governing law", "governed by", "jurisdiction", "laws of"],
    "Exclusivity":                ["exclusiv", "sole and exclusive"],
    "Non-Compete":                ["non-compete", "not compete", "noncompete", "compete"],
    "Ip Ownership Assignment":    ["intellectual property", "ip ownership", "ownership of",
                                   "work made for hire", "patent", "copyright"],
    "License Grant":              ["licen"],           # licence / license / licensing
    "Termination For Convenience": ["terminat"],
    "Insurance":                  ["insurance", "insured"],
    "Audit Rights":               ["audit", "inspect"],
    "Covenant Not To Sue":        ["covenant not to sue", "not to sue", "refrain from suing"],
    "Warranty Duration":          ["warrant"],
}


def gold_present(cell) -> bool:
    """CUAD span columns hold a stringified list; non-empty means present."""
    try:
        return bool(isinstance(cell, str) and ast.literal_eval(cell))
    except Exception:
        return False


def brief_text(brief_json: str) -> str:
    """Flatten a brief's fields into one lowercase string for matching."""
    try:
        b = json.loads(brief_json)
    except Exception:
        return ""
    parts = []
    for v in b.values():
        if isinstance(v, list):
            parts.extend(str(x) for x in v)
        else:
            parts.append(str(v))
    return " ".join(parts).lower()


def main() -> None:
    mc = pd.read_csv(ROOT / "data/cuad/CUAD_v1/master_clauses.csv")
    man = pd.read_csv(ROOT / "results/sample_manifest.csv")
    mc["key"] = mc["Filename"].str.rsplit(".", n=1).str[0].str.strip().str.lower()
    man["key"] = man["txt_name"].str.rsplit(".", n=1).str[0].str.strip().str.lower()
    gold = man[["key", "txt_name"]].merge(mc, on="key", how="left").set_index("txt_name")

    cats = [c for c in SIGNATURES if c in gold.columns]
    rows = []
    for f in sorted((ROOT / "results/summarisation").glob("briefs__*.csv")):
        model = f.stem.replace("briefs__", "")
        df = pd.read_csv(f)
        df = df[df.call_error.isna() & df.brief_json.notna()]
        for _, r in df.iterrows():
            text = brief_text(r.brief_json)
            for cat in cats:
                if not gold_present(gold.loc[r.contract, cat]):
                    continue                      # clause absent -> not a test
                hit = any(p in text for p in SIGNATURES[cat])
                rows.append({"model": model, "contract": r.contract,
                             "category": cat, "mentioned": hit})

    d = pd.DataFrame(rows)
    out = ROOT / "results/summarisation/cuad_coverage_check.csv"
    d.to_csv(out, index=False)

    print(f"gold-present clause instances tested: {len(d)}  "
          f"(categories: {len(cats)})\n")
    per_model = (d.groupby("model")["mentioned"].agg(["mean", "size"])
                   .sort_values("mean", ascending=False))
    per_model["pct"] = (per_model["mean"] * 100).round(1)
    print("coverage of CUAD gold-labelled clauses, by model:")
    print(per_model[["pct", "size"]].to_string())

    print("\nby category (all models pooled) — low values = shared blind spots:")
    per_cat = (d.groupby("category")["mentioned"].agg(["mean", "size"])
                 .sort_values("mean"))
    per_cat["pct"] = (per_cat["mean"] * 100).round(1)
    print(per_cat[["pct", "size"]].to_string())
    print(f"\nwritten: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
