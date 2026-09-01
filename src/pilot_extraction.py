"""
pilot_extraction.py
-------------------
End-to-end pilot: clause extraction, ONE model, FIVE contracts, all six
clause categories (per-category prompting, as locked in the logbook).

Purpose: prove the pipeline — call, log, save raw, parse — before scaling to
5 models x 40 contracts. Prints a cost estimate before making any calls.

Usage:
    ./venv/bin/python src/pilot_extraction.py --model llama-3.3-70b          # estimate only
    ./venv/bin/python src/pilot_extraction.py --model claude-sonnet-5 --run  # estimate, then run
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from model_config import MODELS
from llm_client import call_model
from parsing import extract_first_json

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "results" / "sample_manifest.csv"
N_PER_STRATUM = {"short": 2, "medium": 2, "long": 1}   # 5 contracts total

PROMPT_VERSION = "v2"

# PROMPT V2 (18 Aug 2026): CUAD's official category descriptions VERBATIM
# (source: CUAD_v1_README.txt category table), plus two exclusions motivated
# by the v1 failure gallery (convergent false positives at category
# boundaries CUAD defines but v1's paraphrases did not).
# v1 (paraphrased one-liners) is preserved in git history and
# results/prompt_v1/ as an experimental condition.
CATEGORIES = {
    "Governing Law":
        "Which state/country's law governs the interpretation of the contract?",
    "Expiration Date":
        "On what date will the contract's initial term expire?",
    "Termination For Convenience":
        "Can a party terminate this contract without cause (solely by giving "
        "a notice and allowing a waiting period to expire)?",
    "Cap On Liability":
        "Does the contract include a cap on liability upon the breach of a "
        "party's obligation? This includes time limitation for the "
        "counterparty to bring claims or maximum amount for recovery.",
    "Ip Ownership Assignment":
        "Does intellectual property created by one party become the property "
        "of the counterparty, either per the terms of the contract or upon "
        "the occurrence of certain events?",
    "Non-Compete":
        "Is there a restriction on the ability of a party to compete with "
        "the counterparty or operate in a certain geography or business or "
        "technology sector?",
}

# Exclusions derived from v1 failure analysis — stated only for the two
# categories where convergent false positives demonstrated the boundary.
EXCLUSIONS = {
    "Termination For Convenience":
        "Do NOT include clauses that merely allow a party to give notice of "
        "non-renewal of an automatically renewing term — those are renewal "
        "notice clauses, not termination for convenience.",
    "Ip Ownership Assignment":
        "Do NOT include clauses in which a party merely retains ownership of "
        "its own pre-existing intellectual property — only clauses where IP "
        "created under the contract is assigned to, or becomes the property "
        "of, the other party.",
}

SYSTEM_PROMPT = (
    "You are a legal contract analyst. You extract clauses from contracts "
    "verbatim — exact text as it appears in the document, no paraphrasing. "
    "You respond ONLY with a JSON object, no other text."
)

USER_TEMPLATE = """Below is the full text of a contract, followed by a task.

<contract>
{contract_text}
</contract>

Task: find all clauses in this contract relevant to the following category
question: {category_definition}
{exclusion}

Respond with ONLY this JSON object (no markdown fences, no commentary):
{{"spans": ["<verbatim clause text 1>", "<verbatim clause text 2>", ...]}}

Rules:
- Each span must be copied VERBATIM from the contract text above.
- If the contract contains no such clause, respond with {{"spans": []}}.
"""


def pick_pilot_contracts() -> pd.DataFrame:
    """Deterministic pilot subset: first N of each stratum by word count."""
    m = pd.read_csv(MANIFEST)
    parts = [m[m["stratum"] == s].nsmallest(n, "word_count")
             for s, n in N_PER_STRATUM.items()]
    return pd.concat(parts).reset_index(drop=True)


def estimate_cost(contracts: pd.DataFrame, model_key: str) -> float:
    """Pre-run spend estimate (working rule: estimate before any run).
    Calibrated from pilot observation: tokens_in = 1.39*words + 294/call."""
    cfg = MODELS[model_key]
    n_calls = len(contracts) * len(CATEGORIES)
    tokens_in = int(contracts["word_count"].sum() * 1.39) * len(CATEGORIES) + 294 * n_calls
    tokens_out = len(contracts) * len(CATEGORIES) * 70    # observed pilot mean
    return (tokens_in / 1e6) * cfg["usd_per_m_in"] + (tokens_out / 1e6) * cfg["usd_per_m_out"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=list(MODELS.keys()))
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    model_key = args.model

    contracts = pick_pilot_contracts()
    n_calls = len(contracts) * len(CATEGORIES)
    est = estimate_cost(contracts, model_key)

    print(f"Pilot: {len(contracts)} contracts x {len(CATEGORIES)} categories "
          f"= {n_calls} calls on {model_key}")
    print(contracts[["txt_name", "word_count", "stratum"]].to_string(index=False))
    print(f"\nEstimated cost: ${est:.3f}")

    if not args.run:
        print("\nDry run only. Re-run with --run to execute.")
        return

    results = []
    for _, row in contracts.iterrows():
        contract_text = Path(row["txt_path"]).read_text(errors="ignore")
        short_name = row["txt_name"][:40].replace(" ", "_")
        for cat, definition in CATEGORIES.items():
            tag = f"extraction-{PROMPT_VERSION}__{model_key}__{short_name}__{cat.replace(' ', '-')}"
            print(f"  calling: {tag} ...", flush=True)
            out = call_model(
                model_key,
                system=SYSTEM_PROMPT,
                user=USER_TEMPLATE.format(contract_text=contract_text,
                                          category_definition=definition,
                                          exclusion=EXCLUSIONS.get(cat, "")),
                call_tag=tag,
                max_tokens=2048,
            )
            # Parse attempts — recorded, never fatal (raw is already on disk).
            # strict_json_ok: entire response is exactly one JSON object, as
            # instructed. A per-model behavioural metric (instruction
            # adherence -> integration friction for an SME).
            strict_ok = True
            try:
                json.loads(out["text"].strip())
            except Exception:
                strict_ok = False
            parsed, parse_error = None, None
            try:
                parsed = extract_first_json(out["text"])
                assert isinstance(parsed.get("spans"), list)
            except Exception as e:
                parse_error = f"{type(e).__name__}: {e}"

            results.append({
                "contract": row["txt_name"], "category": cat,
                "n_spans": len(parsed["spans"]) if parsed else None,
                "strict_json_ok": strict_ok,
                "parse_error": parse_error,
                "tokens_in": out["tokens_in"], "tokens_out": out["tokens_out"],
                "latency_s": round(out["latency_s"], 2),
                "cost_usd": round(out["cost_usd"], 5),
                "raw_path": out["raw_path"],
            })

    df = pd.DataFrame(results)
    outpath = ROOT / "results" / f"prompt_{PROMPT_VERSION}" / f"pilot_extraction_summary__{model_key}.csv"
    df.to_csv(outpath, index=False)

    n_ok = df["parse_error"].isna().sum()
    n_strict = df["strict_json_ok"].sum()
    print(f"\nDone. robust parse {n_ok}/{len(df)}; strict JSON compliance {n_strict}/{len(df)}.")
    print(f"Total actual cost: ${df['cost_usd'].sum():.4f}")
    print(f"Summary: {outpath}")
    if n_ok < len(df):
        print("\nParse failures:")
        print(df[df["parse_error"].notna()][["contract", "category", "parse_error"]].to_string(index=False))


if __name__ == "__main__":
    main()
