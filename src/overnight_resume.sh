#!/bin/zsh
# Overnight resume — waits for the Gemini quota window (~07:00 UTC 19 Aug),
# then: (1) Gemini extraction stragglers, (2) full Gemini QA run,
# (3) pending judge adjudications on Together, (4) rescore everything.
# Launched 18 Aug 2026 ~20:00 UTC; approved by user ("No need to wait for me").
set -u
cd "$(dirname "$0")/.."
PY=./venv/bin/python
LOG=results/run_logs/overnight.log

echo "[$(date -u +%FT%TZ)] overnight script started" >> $LOG

# --- wait until the target epoch (07:05 UTC, 19 Aug 2026) ---
TARGET_EPOCH=1787123100   # 2026-08-19 07:05:00 UTC (verified)
while [ "$(date -u +%s)" -lt "$TARGET_EPOCH" ]; do
  sleep 300
done
echo "[$(date -u +%FT%TZ)] window open — starting" >> $LOG

# --- 1. Gemini extraction stragglers (drop error rows, resume) ---
$PY - << 'EOF' >> $LOG 2>&1
import pandas as pd
f = "results/prompt_v2/extraction_full__gemini-3.1-pro.csv"
df = pd.read_csv(f)
keep = df[df.call_error.isna()]
print(f"gemini extraction: dropping {len(df)-len(keep)} error rows, {len(keep)} kept")
keep.to_csv(f, index=False)
EOF
$PY src/run_extraction.py --model gemini-3.1-pro --run >> $LOG 2>&1

# --- 2. Gemini QA (full 120) ---
$PY src/run_qa.py --model gemini-3.1-pro --run >> $LOG 2>&1

# --- 3. regenerate judge queue (includes any new Gemini escalations), judge, rescore ---
$PY src/score_qa.py >> $LOG 2>&1
$PY src/run_judge.py --run >> $LOG 2>&1
$PY src/score_qa.py --with-judge >> $LOG 2>&1

# --- 4. final extraction scores ---
$PY src/score_extraction.py --pilot --full --cond v2 >> $LOG 2>&1

echo "[$(date -u +%FT%TZ)] overnight script finished" >> $LOG
