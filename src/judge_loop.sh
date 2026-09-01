#!/bin/bash
# Self-restarting wrapper for the summarisation judge.
#
# Why this exists: the judge process was repeatedly killed by an external
# signal after ~15 minutes (~13 judgements) with no Python traceback — the
# unbuffered log simply stops mid-run. Cause not identified; likely a process
# reaper outside this project. judge_summaries.py is resumable (it skips any
# (model, contract) pair already in judgements.jsonl), so restarting it is
# always safe and never re-spends on completed work.
#
# The loop re-invokes the judge until it reports nothing left to do, with a
# hard cap on passes so a genuine failure cannot spin forever.
cd "$(dirname "$0")/.." || exit 1

LOG=results/run_logs/judge_loop.log
MAX_PASSES=40

# Single-instance lock. Two concurrent loops once raced and wrote a duplicate
# judgement for the same (model, contract) — wasted spend and a corrupted
# append-only log. mkdir is atomic, so it works as a portable mutex on macOS.
LOCK=results/run_logs/.judge_loop.lock
# The lock records its owner's PID. A plain trap-based release is not enough:
# `trap ... EXIT INT TERM` does NOT fire on SIGKILL, and these runs were killed
# with `pkill -9` repeatedly on 25 Aug — every such kill left a lock directory
# behind that permanently blocked all later launches with "REFUSING TO START".
# So on startup we check whether the recorded PID is still alive and reclaim
# the lock if it is not.
if ! mkdir "$LOCK" 2>/dev/null; then
    owner=$(cat "$LOCK/pid" 2>/dev/null)
    if [ -n "$owner" ] && kill -0 "$owner" 2>/dev/null; then
        echo "[$(date -u +%H:%M:%S)] REFUSING TO START: live judge runner (pid $owner) holds $LOCK" >> "$LOG"
        echo "REFUSING TO START: live judge runner (pid $owner) holds $LOCK"
        exit 1
    fi
    echo "[$(date -u +%H:%M:%S)] reclaiming stale lock (owner '${owner:-unknown}' not running)" >> "$LOG"
    rm -rf "$LOCK"
    mkdir "$LOCK" || { echo "could not create $LOCK"; exit 1; }
fi
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK" 2>/dev/null' EXIT INT TERM

for pass in $(seq 1 $MAX_PASSES); do
    # Count remaining work WITHOUT spending: judge_summaries.py with no --run
    # prints "<N> briefs to judge" and exits before making any API call.
    remaining=$(./venv/bin/python -u src/judge_summaries.py 2>/dev/null \
                | grep -oE '^[0-9]+ briefs to judge' | grep -oE '^[0-9]+')

    echo "[$(date -u +%H:%M:%S)] pass $pass — remaining: ${remaining:-unknown}" >> "$LOG"

    # Empty or zero means the queue is clear: stop.
    if [ -z "$remaining" ] || [ "$remaining" -eq 0 ]; then
        echo "[$(date -u +%H:%M:%S)] COMPLETE after $((pass-1)) passes" >> "$LOG"
        break
    fi

    # One judging pass. If it is killed mid-way, completed judgements are
    # already durably appended to judgements.jsonl, so the next pass resumes.
    ./venv/bin/python -u src/judge_summaries.py --run >> "$LOG" 2>&1

    sleep 5
done
