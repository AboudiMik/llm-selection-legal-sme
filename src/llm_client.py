"""
llm_client.py
-------------
One function — call_model() — that every task runner uses.

Guarantees, on every single API call:
  1. The raw, unmodified response text is saved to results/raw/ BEFORE any
     parsing happens (reproducibility rule: raw data survives parser bugs).
  2. Tokens in/out, latency, and cost are logged to results/call_log.jsonl.
     Cost-per-task is a core finding, so this is not optional telemetry.

Only OpenAI-compatible endpoints for now (Together, OpenAI, DeepSeek — and the
Qwen judge). Anthropic/Google adapters will slot in behind the same interface.
"""

import json
import os
import time
import datetime
from pathlib import Path

from openai import OpenAI

from model_config import MODELS, get_api_key, cost_usd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "results" / "raw"
CALL_LOG = ROOT / "results" / "call_log.jsonl"

RAW_DIR.mkdir(parents=True, exist_ok=True)


def _call_openai_compatible(cfg, model_key, system, user, max_tokens,
                            temperature, stream):
    """OpenAI-compatible chat completions (OpenAI, Together, DeepSeek).

    GPT-5.x quirks are handled by retrying once per adjustment:
      - newer OpenAI models take max_completion_tokens, not max_tokens
      - some reject non-default temperature (as Sonnet 5 does)
    Any adjustment is printed so the run log shows the exact request shape.
    """
    from openai import BadRequestError

    # timeout: reasoning models (Qwen judge, Gemini) can sit silent for
    # minutes while thinking before the first visible chunk arrives — the
    # default read timeout kills the stream mid-call (observed 20 Aug 2026,
    # summary judge with full contract in context). 20 min is generous but
    # a hung call still dies rather than blocking a run forever.
    client = OpenAI(api_key=get_api_key(model_key), base_url=cfg["base_url"],
                    timeout=1200)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    if cfg.get("thinking"):
        # thinking models spend the same budget on reasoning + answer
        max_tokens = max(max_tokens, 8192)
    kwargs = {"model": cfg["model_id"], "messages": messages,
              "max_tokens": max_tokens, "temperature": temperature}

    for _ in range(3):  # at most two adjustments, then give up
        try:
            if stream:
                # Some providers occasionally omit the final usage chunk
                # (observed: Together, 18 Aug 2026 — crashed the judge run).
                # Retry the whole call once; if usage is still missing, return
                # it as None and let the caller log nulls — never fabricate.
                for attempt in range(2):
                    chunks = client.chat.completions.create(
                        **kwargs, stream=True,
                        stream_options={"include_usage": True},
                    )
                    parts, usage, finish = [], None, None
                    try:
                        for c in chunks:
                            if c.choices and c.choices[0].delta.content:
                                parts.append(c.choices[0].delta.content)
                            if c.choices and c.choices[0].finish_reason:
                                finish = c.choices[0].finish_reason
                            if c.usage:      # final chunk carries usage
                                usage = c.usage
                    except Exception as e:
                        # Mid-stream network death (read timeout, connection
                        # reset). Retry the whole call once; then give up so
                        # the caller records a call_error, not a hang.
                        if "Timeout" not in type(e).__name__ or attempt == 1:
                            raise
                        print(f"    [{model_key}] stream died mid-call "
                              f"({type(e).__name__}) — retrying once")
                        continue
                    if usage is not None:
                        break
                    print(f"    [{model_key}] stream returned no usage chunk "
                          f"(attempt {attempt + 1}/2)")
                return "".join(parts), usage, finish
            resp = client.chat.completions.create(**kwargs)
            return (resp.choices[0].message.content or "", resp.usage,
                    resp.choices[0].finish_reason)
        except BadRequestError as e:
            msg = str(e)
            if "max_tokens" in msg and "max_completion_tokens" in msg:
                kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")
                print(f"    [{model_key}] adjusted: max_tokens -> max_completion_tokens")
            elif "temperature" in msg and "temperature" in kwargs:
                kwargs.pop("temperature")
                print(f"    [{model_key}] adjusted: temperature removed (provider default)")
            else:
                raise
    raise RuntimeError(f"{model_key}: request rejected after parameter adjustments")


def _call_anthropic(cfg, model_key, system, user, max_tokens):
    """Anthropic Messages API (Claude Sonnet 5).

    Provider defaults: adaptive thinking is on when `thinking` is omitted, and
    thinking tokens bill as output — deliberately kept, so logged cost is the
    out-of-the-box cost an SME would pay. Sonnet 5 rejects non-default
    temperature, so none is sent. max_tokens caps thinking + answer together,
    hence the generous floor below.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=get_api_key(model_key))
    resp = client.messages.create(
        model=cfg["model_id"],
        max_tokens=max(max_tokens, 8192),   # headroom for thinking + answer
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    if resp.stop_reason == "refusal":
        # Log-visible marker; raw file will contain it, parse will fail cleanly.
        return "[REFUSAL] model declined this request", resp.usage, "refusal"
    text = "".join(b.text for b in resp.content if b.type == "text")
    return text, resp.usage, resp.stop_reason


def call_model(model_key: str, system: str, user: str, call_tag: str,
               max_tokens: int = 1024, temperature: float = 0.0,
               stream: bool = False) -> dict:
    """
    Make one chat completion call and log everything.

    call_tag uniquely identifies the call for the raw-response filename,
    e.g. "extraction__llama-3.3-70b__CONTRACT__Governing-Law".

    stream=True is required by some models (e.g. the Qwen judge); the text is
    accumulated so callers see no difference. Latency for streamed calls is
    total wall time, and usage comes from the final chunk.

    Returns a dict: {text, tokens_in, tokens_out, latency_s, cost_usd, raw_path}
    """
    cfg = MODELS[model_key]

    # Peak-window guard (DeepSeek first-party): the logged cost assumes the
    # off-peak rate, so running in a peak window would silently understate
    # true spend by 2x. Refuse unless explicitly overridden.
    if cfg.get("peak_windows_utc"):
        hour = datetime.datetime.now(datetime.timezone.utc).hour
        in_peak = any(lo <= hour < hi for lo, hi in cfg["peak_windows_utc"])
        if in_peak and not os.getenv("DEEPSEEK_ALLOW_PEAK"):
            raise RuntimeError(
                f"{model_key}: current UTC hour {hour} is inside a peak pricing "
                f"window {cfg['peak_windows_utc']} — the logged off-peak rate "
                f"would understate cost 2x. Re-run off-peak, or set "
                f"DEEPSEEK_ALLOW_PEAK=1 to proceed at your own risk."
            )

    t0 = time.perf_counter()
    if cfg.get("provider") == "anthropic":
        text, usage, finish = _call_anthropic(cfg, model_key, system, user, max_tokens)
        tin, tout = usage.input_tokens, usage.output_tokens
    else:
        text, usage, finish = _call_openai_compatible(cfg, model_key, system, user,
                                                      max_tokens, temperature, stream)
        if usage is None:
            # Provider gave no token counts (rare streaming quirk): log nulls,
            # not zeros — a fabricated $0.00 would corrupt the cost findings.
            tin, tout = None, None
        else:
            tin, tout = usage.prompt_tokens, usage.completion_tokens
    latency = time.perf_counter() - t0
    cost = cost_usd(model_key, tin, tout) if tin is not None else None

    # 1. Save raw response first — before any parsing can fail.
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
    raw_path = RAW_DIR / f"{ts}__{call_tag}.txt"
    raw_path.write_text(text)

    # 2. Append structured record to the call log.
    record = {
        "ts_utc": ts,
        "call_tag": call_tag,
        "model_key": model_key,
        "model_id": cfg["model_id"],
        "tokens_in": tin,
        "tokens_out": tout,
        "finish_reason": finish,
        "latency_s": round(latency, 3),
        "cost_usd": round(cost, 6) if cost is not None else None,
        "raw_path": str(raw_path.relative_to(ROOT)),
    }
    with open(CALL_LOG, "a") as f:
        f.write(json.dumps(record) + "\n")

    return {"text": text, "tokens_in": tin, "tokens_out": tout,
            "finish_reason": finish, "latency_s": latency, "cost_usd": cost,
            "raw_path": str(raw_path)}
