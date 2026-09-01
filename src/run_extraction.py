"""
run_extraction.py
-----------------
FULL extraction run: one model x 40 contracts x 6 categories = 240 calls.
Prompt v2 (CUAD-official definitions + two exclusions — locked 18 Aug 2026).

Reuses the pilot's prompt/categories verbatim (imported, not copied, so the
two can never drift). Adds what a 240-call run needs over a 30-call pilot:
  - RESUMABLE: existing (contract, category) rows in the output CSV are
    skipped, so a crashed run continues where it stopped.
  - ERROR-TOLERANT: a failed call records an error row and moves on; it
    never kills the run. Failed rows are retried on the next invocation
    (they are not counted as done).

Usage:
    ./venv/bin/python src/run_extraction.py --model llama-3.3-70b --run
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from model_config import MODELS
from llm_client import call_model
from parsing import extract_first_json
from pilot_extraction import CATEGORIES, EXCLUSIONS, SYSTEM_PROMPT, USER_TEMPLATE, PROMPT_VERSION

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "results" / "sample_manifest.csv"


def out_path(model_key: str) -> Path:
    return ROOT / "results" / f"prompt_{PROMPT_VERSION}" / f"extraction_full__{model_key}.csv"


def load_done(path: Path) -> set:
    """(contract, category) pairs already completed successfully."""
    if not path.exists():
        return set()
    df = pd.read_csv(path)
    ok = df[df["call_error"].isna()] if "call_error" in df else df
    return set(zip(ok["contract"], ok["category"]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=list(MODELS.keys()))
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    model_key = args.model

    contracts = pd.read_csv(MANIFEST)
    outfile = out_path(model_key)
    done = load_done(outfile)
    todo = [(r, cat) for _, r in contracts.iterrows() for cat in CATEGORIES
            if (r["txt_name"], cat) not in done]

    cfg = MODELS[model_key]
    est_in = int(contracts["word_count"].sum() * 1.39) * len(CATEGORIES) + 294 * len(todo)
    est = (est_in / 1e6) * cfg["usd_per_m_in"] + (len(todo) * 70 / 1e6) * cfg["usd_per_m_out"]
    print(f"[{model_key}] {len(todo)} calls to do ({len(done)} already done). "
          f"Estimated cost: ${est:.2f}")
    if not args.run:
        return

    # incremental append so progress survives crashes
    header_needed = not outfile.exists()
    for i, (row, cat) in enumerate(todo, 1):
        tag = (f"extraction-{PROMPT_VERSION}__{model_key}"
               f"__{row['txt_name'][:40].replace(' ', '_')}__{cat.replace(' ', '-')}")
        rec = {"contract": row["txt_name"], "category": cat,
               "stratum": row["stratum"], "word_count": row["word_count"]}
        try:
            out = call_model(
                model_key,
                system=SYSTEM_PROMPT,
                user=USER_TEMPLATE.format(
                    contract_text=Path(row["txt_path"]).read_text(errors="ignore"),
                    category_definition=CATEGORIES[cat],
                    exclusion=EXCLUSIONS.get(cat, "")),
                call_tag=tag,
                max_tokens=2048,
            )
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
            rec.update({
                "n_spans": len(parsed["spans"]) if parsed else None,
                "strict_json_ok": strict_ok, "parse_error": parse_error,
                "call_error": None,
                "tokens_in": out["tokens_in"], "tokens_out": out["tokens_out"],
                "finish_reason": out["finish_reason"],
                "latency_s": round(out["latency_s"], 2),
                "cost_usd": round(out["cost_usd"], 5),
                "raw_path": Path(out["raw_path"]).relative_to(ROOT).as_posix(),
            })
        except Exception as e:
            rec.update({"n_spans": None, "strict_json_ok": None,
                        "parse_error": None,
                        "call_error": f"{type(e).__name__}: {str(e)[:200]}",
                        "tokens_in": None, "tokens_out": None,
                        "finish_reason": None, "latency_s": None,
                        "cost_usd": None, "raw_path": None})
            print(f"  [{model_key}] CALL ERROR on {tag}: {rec['call_error']}")

        pd.DataFrame([rec]).to_csv(outfile, mode="a", header=header_needed, index=False)
        header_needed = False
        if i % 24 == 0:
            print(f"  [{model_key}] {i}/{len(todo)} done")

    df = pd.read_csv(outfile)
    ok = df["call_error"].isna().sum()
    print(f"[{model_key}] COMPLETE: {ok}/{len(df)} calls ok, "
          f"parse ok {(df['parse_error'].isna() & df['call_error'].isna()).sum()}, "
          f"cost ${df['cost_usd'].sum():.2f}")


if __name__ == "__main__":
    main()
