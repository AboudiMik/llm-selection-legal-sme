"""
Build the 20 human spot-check worksheets (Day 8, researcher-specified design).

Two instruments, written to results/spot_checks/:

  A. fabrication_checks.csv  (n=2)
     The two F-item failures found at n=40. The researcher verifies each
     against the source contract and records agree / disagree with the judge.
     This is the reliability check on a judge with a very high pass rate.

  B. depth_checks.csv  (n=18)
     Paired SAME-CONTRACT comparisons between the deepest and shallowest
     models (claude-sonnet-5 vs llama-3.3-70b). For each pair the researcher
     classifies every obligation the deep brief has that the shallow one does
     not as: material / minor / padding.

     This is what resolves "depth is not quality" on a sample: if the extra
     obligations are mostly material, depth is genuine coverage the binary
     rubric cannot see; if mostly padding, depth is verbosity and the ceiling
     is the honest reading.

Sampling is stratified (6 short / 6 medium / 6 long) and seeded, so the
selection is reproducible and not cherry-picked.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SUMM = ROOT / "results" / "summarisation"
OUT = ROOT / "results" / "spot_checks"
SEED = 42                      # same seed used across the project
# Pairing chosen 25 Aug AFTER the full judge run completed, and deliberately
# NOT deepest-vs-shallowest. The original pairing (claude vs llama) is now a
# settled question: the judge gave Llama 15 of the 21 failures, so no human
# work is needed to establish that it is weaker.
#
# The LIVE procurement question is between two models the rubric certifies as
# equally adequate but which differ 4x in cost:
#     gpt-5.6-terra   10.4 obligations, 0 failures, $1.50 per 40 contracts
#     deepseek-v4-pro  7.2 obligations, 3 failures, $0.38 per 40 contracts
# If GPT's extra ~3 obligations per brief are material, a firm should pay 4x.
# If they are padding, DeepSeek wins outright. That is what these checks decide.
DEEP, SHALLOW = "gpt-5.6-terra", "deepseek-v4-pro"
PER_STRATUM = 6                # 6 x 3 strata = 18 depth checks


def load_briefs(model: str) -> pd.DataFrame:
    """Read one model's briefs, keep only successful calls, parse the JSON."""
    df = pd.read_csv(SUMM / f"briefs__{model}.csv")
    df = df[df["call_error"].isna()] if "call_error" in df else df
    rows = []
    for _, r in df.iterrows():
        try:
            brief = json.loads(r["brief_json"])
        except Exception:
            continue                      # unparseable brief cannot be compared
        if not isinstance(brief, dict):
            continue
        rows.append({
            "contract": r["contract"],
            "stratum": r["stratum"],
            "word_count": r["word_count"],
            "obligations": brief.get("key_obligations") or [],
            "risks": brief.get("risks") or [],
        })
    return pd.DataFrame(rows)


def _preserve_researcher_columns(fresh: pd.DataFrame, path: Path) -> pd.DataFrame:
    """Carry hand-entered columns from an existing worksheet onto a fresh one.

    Regeneration must never destroy human work. Any column in the existing file
    that is not produced by this script (verdicts, evidence quotes, notes, and
    the llm_suggested_verdict provenance column) is merged back on check_id.
    Non-empty existing values always win over blanks in the fresh frame.
    """
    if not path.exists():
        return fresh
    old = pd.read_csv(path)
    if "check_id" not in old.columns:
        return fresh
    carry = [c for c in old.columns
             if c not in fresh.columns or fresh[c].isna().all() or (fresh[c] == "").all()]
    carry = [c for c in carry if c != "check_id"]
    if not carry:
        return fresh
    merged = fresh.merge(old[["check_id"] + carry], on="check_id",
                         how="left", suffixes=("", "_old"))
    for c in carry:
        oldcol = f"{c}_old" if f"{c}_old" in merged else c
        if c in fresh.columns and oldcol != c:
            # keep existing non-empty value, else the freshly generated one
            merged[c] = merged[oldcol].where(merged[oldcol].notna(), merged[c])
            merged.drop(columns=[oldcol], inplace=True)
    kept = sum(int(merged[c].notna().sum()) for c in carry if c in merged)
    print(f"  preserved {kept} existing researcher/provenance values across {len(carry)} column(s)")
    return merged


def build_fabrication_checks() -> pd.DataFrame:
    """Pull every judged F-item failure straight from the judgements log."""
    rows = []
    path = SUMM / "judgements.jsonl"
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("judge_error") or isinstance(rec.get("items"), str):
            continue
        # Full-run verdicts only. Pilot verdicts (20-23 Aug) judged DIFFERENT
        # brief text for the same (model, contract) — see judge_summaries.py
        # already_judged() — so including them would attach a verdict to a
        # brief it never saw.
        if rec.get("run", "pilot") != "full":
            continue
        for code, verdict in rec["items"].items():
            # Faithfulness items only — these are the fabrication claims.
            if code.startswith("F") and verdict.get("pass") is not True:
                rows.append({
                    "check_id": f"FAB-{len(rows) + 1:02d}",
                    "model": rec["model_under_test"],
                    "contract": rec["contract"],
                    "item": code,
                    "judge_claim": verdict.get("reason", ""),
                    # blank columns for the researcher to complete
                    "researcher_verdict_agree_disagree": "",
                    "evidence_quote_from_contract": "",
                    "notes": "",
                })
    return pd.DataFrame(rows)


def build_depth_checks() -> pd.DataFrame:
    """Stratified paired sample: deepest vs shallowest brief per contract."""
    deep, shallow = load_briefs(DEEP), load_briefs(SHALLOW)
    merged = deep.merge(shallow, on=["contract", "stratum", "word_count"],
                        suffixes=("_deep", "_shallow"))
    # Only pairs where the deep brief actually has more to classify.
    merged["extra"] = merged.apply(
        lambda r: len(r["obligations_deep"]) - len(r["obligations_shallow"]), axis=1)
    merged = merged[merged["extra"] > 0]

    rng = random.Random(SEED)
    picked = []
    for stratum in ["short", "medium", "long"]:
        pool = merged[merged["stratum"] == stratum]["contract"].tolist()
        pool.sort()                                   # deterministic before sampling
        take = min(PER_STRATUM, len(pool))
        picked += rng.sample(pool, take)
        if take < PER_STRATUM:
            print(f"  ! only {take} eligible pairs in '{stratum}' (wanted {PER_STRATUM})")

    rows = []
    for i, contract in enumerate(picked, 1):
        r = merged[merged["contract"] == contract].iloc[0]
        rows.append({
            "check_id": f"DEP-{i:02d}",
            "contract": contract,
            "stratum": r["stratum"],
            "word_count": r["word_count"],
            "n_obl_deep": len(r["obligations_deep"]),
            "n_obl_shallow": len(r["obligations_shallow"]),
            "extra_obligations": r["extra"],
            f"{DEEP}_obligations": " | ".join(map(str, r["obligations_deep"])),
            f"{SHALLOW}_obligations": " | ".join(map(str, r["obligations_shallow"])),
            # Researcher fills these. EVERY deep-brief obligation gets exactly
            # ONE label, so the four columns sum to n_obl_deep — a number that
            # is known and printed, unlike `extra_obligations`.
            #
            # `extra_obligations` (n_deep - n_shallow) is ARITHMETIC ONLY and is
            # not the count of unmatched items: where the shallow brief bundles
            # two deep items into one line, the arithmetic overstates the gap.
            # It is kept as a rough sort key, not as a target to sum to.
            "n_matched": "",    # a shallow item covers this ground (1:1 or bundled)
            "n_material": "",   # unmatched AND a solicitor would need it
            "n_minor": "",      # unmatched but administrative
            "n_padding": "",    # unmatched and vacuous/duplicative/ungrounded
            "notes": "",
        })
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    fab = build_fabrication_checks()
    # DO NOT clobber researcher work. This script is designed to be re-run as
    # the judge finds more failures, but by 26 Aug the worksheet also carried
    # hand-entered verdicts, evidence quotes and notes. A plain to_csv() wiped
    # them. Merge any human-entered columns from the existing file back on.
    fab = _preserve_researcher_columns(fab, OUT / "fabrication_checks.csv")
    fab.to_csv(OUT / "fabrication_checks.csv", index=False)
    print(f"fabrication checks: {len(fab)} -> {OUT / 'fabrication_checks.csv'}")

    dep = build_depth_checks()
    dep.to_csv(OUT / "depth_checks.csv", index=False)
    print(f"depth checks:       {len(dep)} -> {OUT / 'depth_checks.csv'}")
    print(f"TOTAL spot-checks:  {len(fab) + len(dep)}")
    if len(fab) + len(dep) != 20:
        print("  NOTE: total != 20. Fabrication count grows as the judge run "
              "completes; re-run this script when judging finishes.")


if __name__ == "__main__":
    main()
