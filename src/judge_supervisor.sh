#!/bin/zsh
# Supervisor for the summarisation judge (25 Aug 2026).
#
# WHY THIS EXISTS: the judge is being killed by macOS under memory pressure
# (swap ~8.1/9.2 GB used at launch time), not by a Python error — it dies with
# no traceback even with `python -u` and stderr merged. Three launches died
# after 1-13 judgements each. The judge itself is idempotent and resumable:
# every completed judgement is appended to judgements.jsonl and skipped on the
# next invocation, so simply restarting it makes forward progress.
#
# This wrapper restarts the judge until the queue is empty, with two guards so
# it cannot loop forever or spend without bound:
#   1. MAX_ATTEMPTS  — hard cap on relaunches.
#   2. stall detection — if an attempt adds ZERO judgements, count it; after
#      MAX_STALLS consecutive no-progress attempts, stop and report. This is
#      what prevents an infinite restart loop against a persistent failure
#      (e.g. an API outage) that a naive `until` loop would spin on forever.
#
# Progress and every attempt boundary are logged so the run is auditable.
set -u
cd "$(dirname "$0")/.."

PY=./venv/bin/python
JFILE=results/summarisation/judgements.jsonl
LOG=results/run_logs/judge_supervisor.log
MAX_ATTEMPTS=40
MAX_STALLS=3

# Single-writer mutex, SHARED with src/judge_loop.sh (same path deliberately).
# Two judge runners writing judgements.jsonl concurrently already produced a
# duplicate verdict for one (model, contract) pair on 25 Aug. Sharing one lock
# means this supervisor and judge_loop.sh exclude each other, not merely
# themselves. mkdir is atomic, so it is a portable mutex on macOS.
# The lock records its owner's PID, because `trap ... EXIT INT TERM` does NOT
# fire on SIGKILL: every `pkill -9` on 25 Aug left a lock behind that blocked
# all later launches. Reclaim the lock if its recorded owner is gone.
LOCK=results/run_logs/.judge_loop.lock
if ! mkdir "$LOCK" 2>/dev/null; then
  owner=$(cat "$LOCK/pid" 2>/dev/null)
  if [ -n "$owner" ] && kill -0 "$owner" 2>/dev/null; then
    echo "[$(date -u +%FT%TZ)] REFUSING TO START: live judge runner (pid $owner) holds $LOCK" >> $LOG
    echo "REFUSING TO START: live judge runner (pid $owner) holds $LOCK"
    exit 1
  fi
  echo "[$(date -u +%FT%TZ)] reclaiming stale lock (owner '${owner:-unknown}' not running)" >> $LOG
  rm -rf "$LOCK"
  mkdir "$LOCK" || { echo "could not create $LOCK"; exit 1; }
fi
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK" 2>/dev/null' EXIT INT TERM

count() { grep -c . "$JFILE" 2>/dev/null || echo 0; }

stalls=0
for attempt in $(seq 1 $MAX_ATTEMPTS); do
  before=$(count)

  # Queue empty? The judge prints "0 briefs to judge" on a dry run.
  if PYTHONPATH=src $PY src/judge_summaries.py 2>/dev/null | head -1 | grep -q '^0 briefs'; then
    echo "[$(date -u +%FT%TZ)] queue empty after $((attempt-1)) attempts, $before judgements" >> $LOG
    echo "DONE: queue empty, $before judgements on file"
    exit 0
  fi

  echo "[$(date -u +%FT%TZ)] attempt $attempt starting (judged=$before)" >> $LOG
  PYTHONPATH=src caffeinate -i $PY -u src/judge_summaries.py --run >> $LOG 2>&1
  rc=$?
  after=$(count)
  gained=$((after - before))
  echo "[$(date -u +%FT%TZ)] attempt $attempt ended rc=$rc, +$gained judgements (total $after)" >> $LOG
  echo "attempt $attempt: rc=$rc, +$gained (total $after)"

  if [ "$gained" -eq 0 ]; then
    stalls=$((stalls + 1))
    if [ "$stalls" -ge "$MAX_STALLS" ]; then
      echo "[$(date -u +%FT%TZ)] STOPPING: $MAX_STALLS consecutive attempts with no progress" >> $LOG
      echo "STOPPED: $MAX_STALLS consecutive no-progress attempts — not a memory kill, investigate the log"
      exit 1
    fi
    sleep 20          # brief backoff before retrying
  else
    stalls=0          # progress resets the stall counter
  fi
done

echo "[$(date -u +%FT%TZ)] STOPPING: hit MAX_ATTEMPTS=$MAX_ATTEMPTS ($(count) judged)" >> $LOG
echo "STOPPED: hit MAX_ATTEMPTS=$MAX_ATTEMPTS with $(count) judgements"
exit 1
