"""
sample_contracts.py
-------------------
Builds the 40-contract stratified sample that all subsequent experiments use.

Why stratified?  Document length is the primary driver of model cost and of
performance degradation on long-document Q&A.  Stratifying keeps all three
strata (short / medium / long) in the sample, so we can make statements like
"model X degrades on long contracts while model Y holds up" — which simple
random sampling cannot support.

Outputs
-------
results/sample_manifest.csv   — the 40 chosen rows with metadata
"""

import ast
import pandas as pd
from pathlib import Path


# ── 1. Paths ──────────────────────────────────────────────────────────────────

ROOT        = Path(__file__).resolve().parent.parent   # dissertation/
CUAD_DIR    = ROOT / "data" / "cuad" / "CUAD_v1"
CSV_PATH    = CUAD_DIR / "master_clauses.csv"
TXT_DIR     = CUAD_DIR / "full_contract_txt"
OUT_DIR     = ROOT / "results"
OUT_PATH    = OUT_DIR / "sample_manifest.csv"

OUT_DIR.mkdir(exist_ok=True)


# ── 2. Configuration ──────────────────────────────────────────────────────────

# These are the six categories we evaluate.  The names must match the exact
# column headers in master_clauses.csv (case-sensitive).
CLAUSE_COLS = [
    "Governing Law",
    "Expiration Date",
    "Termination For Convenience",
    "Cap On Liability",
    "Ip Ownership Assignment",
    "Non-Compete",
]

# Sampling parameters
N_TOTAL    = 40    # total contracts to sample
N_STRATA   = 3     # short / medium / long — must divide N_TOTAL evenly
RANDOM_STATE = 42  # fixed seed for reproducibility


# ── 3. Build the pool of 194 TXT-matched contracts ────────────────────────────

df = pd.read_csv(CSV_PATH)
print(f"CSV loaded: {len(df)} rows, {len(df.columns)} columns")

# Build a lookup from TXT filename → absolute path, ignoring Part_I/Part_II.
txt_by_name = {f.name: f for f in TXT_DIR.rglob("*.txt")}
print(f"TXT files on disk: {len(txt_by_name)}")

# The CSV Filename column ends '.pdf'; convert to '.txt' for matching.
df["txt_name"] = df["Filename"].str.replace(r"\.pdf$", ".txt", regex=True, case=False)
df["txt_path"] = df["txt_name"].map(txt_by_name)

# Keep only rows where we found the full text.
pool = df[df["txt_path"].notna()].copy()
print(f"Matched pool (CSV row + TXT file): {len(pool)} contracts")


# ── 4. Measure word count (proxy for token count) ─────────────────────────────
# We use word count here because it is instantaneous and free.  Token count
# would require calling a tokeniser; the correlation with word count is >0.99
# for plain-text contracts, so this is adequate for stratification.

def word_count(path: Path) -> int:
    return len(path.read_text(errors="ignore").split())

pool["word_count"] = pool["txt_path"].apply(word_count)
pool = pool.sort_values("word_count").reset_index(drop=True)

wc = pool["word_count"]
print(f"\nPool word counts  min={wc.min()}  median={int(wc.median())}  max={wc.max()}")


# ── 5. Assign strata ──────────────────────────────────────────────────────────
# pd.qcut splits on quantile boundaries, so each stratum has the same number
# of contracts in the pool before sampling.  Boundaries are logged so they
# can be reported in the methodology chapter.

pool["stratum"] = pd.qcut(
    pool["word_count"],
    q=N_STRATA,
    labels=["short", "medium", "long"],
)

for label in ["short", "medium", "long"]:
    subset = pool[pool["stratum"] == label]
    print(f"  {label:6s}: {len(subset):3d} contracts  "
          f"words {subset['word_count'].min()}–{subset['word_count'].max()}")


# ── 6. Stratified sample ──────────────────────────────────────────────────────
# Sample n_per_stratum from each group.  If a stratum is smaller than
# n_per_stratum, this will raise — but with 194 contracts and 3 strata of
# ~65 each, sampling 13 or 14 is always safe.

n_per_stratum = N_TOTAL // N_STRATA   # 13; remaining 1 goes to 'long' below

frames = []
for i, label in enumerate(["short", "medium", "long"]):
    n = n_per_stratum + (1 if i == N_STRATA - 1 else 0)  # long gets the extra 1
    subset = pool[pool["stratum"] == label]
    frames.append(
        subset.sample(n=n, random_state=RANDOM_STATE)
    )

sample = pd.concat(frames).sort_values("word_count").reset_index(drop=True)
print(f"\nSample size: {len(sample)} contracts  "
      f"(short={sum(sample['stratum']=='short')}, "
      f"medium={sum(sample['stratum']=='medium')}, "
      f"long={sum(sample['stratum']=='long')})")


# ── 7. Annotate with clause presence for the 6 target categories ─────────────
# For each category we record whether the ground-truth span list is non-empty
# (i.e., at least one positive example exists in the contract).  This is just
# a diagnostic — it tells us if the sample has a reasonable mix of positive
# and negative examples per clause.

for col in CLAUSE_COLS:
    def has_span(val):
        try:
            spans = ast.literal_eval(val) if isinstance(val, str) else []
            return len([s for s in spans if str(s).strip()]) > 0
        except Exception:
            return False
    sample[f"has_{col.lower().replace(' ', '_')}"] = sample[col].apply(has_span)

# Print prevalence table
print("\nPositive-example prevalence in the 40-contract sample:")
for col in CLAUSE_COLS:
    key = f"has_{col.lower().replace(' ', '_')}"
    n_pos = sample[key].sum()
    print(f"  {col:<30s} {n_pos:2d}/40")


# ── 8. Save manifest ──────────────────────────────────────────────────────────
# Keep the columns we'll actually use downstream, plus all six clause columns
# and their -Answer counterparts (ground truth).

keep_cols = (
    ["Filename", "txt_name", "txt_path", "word_count", "stratum"]
    + CLAUSE_COLS
    + [f"{c}-Answer" for c in CLAUSE_COLS]
)
sample[keep_cols].to_csv(OUT_PATH, index=False)
print(f"\nManifest saved to: {OUT_PATH}")
