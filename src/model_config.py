"""
model_config.py
---------------
Single source of truth for model endpoints and pricing.

Pricing verified against OFFICIAL vendor pages, accessed 17 Aug 2026
(see notes/logbook.md for URLs). Prices are USD per million tokens.
Every cost figure the harness logs is derived from this table, so a price
change only ever needs correcting in one place.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load API keys from dissertation/.env (never committed — see .gitignore)
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


# Each entry: which API-key env var it needs, the base URL (OpenAI-compatible
# endpoints only for now — Anthropic and Google get their own adapters later),
# the provider's model ID string, and official per-million-token pricing.
MODELS = {
    # NOTE 17 Aug 2026: Llama 4 Maverick is no longer serverless on Together
    # (dedicated endpoints only — verified by API error + models endpoint).
    # Replaced by Llama 3.3 70B Instruct Turbo, pending user ratification of
    # the slate change. Pricing from Together's models API, accessed 17 Aug 2026.
    "llama-3.3-70b": {
        "env_key": "TOGETHER_API_KEY",
        "base_url": "https://api.together.xyz/v1",
        "model_id": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "usd_per_m_in": 1.04,
        "usd_per_m_out": 1.04,
    },
    "gpt-5.6-terra": {
        "env_key": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "model_id": "gpt-5.6-terra",
        "usd_per_m_in": 2.00,
        "usd_per_m_out": 12.00,
    },
    "claude-sonnet-5": {
        "provider": "anthropic",          # uses the Anthropic SDK, not OpenAI-compatible
        "env_key": "ANTHROPIC_API_KEY",
        "model_id": "claude-sonnet-5",
        "usd_per_m_in": 2.00,
        "usd_per_m_out": 10.00,
        # NOTE: Sonnet 5 runs adaptive thinking by default; thinking tokens are
        # billed as output tokens. We run provider defaults (see logbook,
        # "provider-default settings" rule) so logged cost reflects what an
        # SME would actually pay out of the box.
    },
    # DeepSeek FIRST-PARTY (reversed from Together routing, 18 Aug 2026 —
    # Together's flat $1.32/$3.96 equals DeepSeek's peak rate, 2x off-peak,
    # which would inflate the headline cost-per-task figure; see logbook).
    # Headline pricing = off-peak; runs are guarded against peak windows.
    "deepseek-v4-pro": {
        "env_key": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/v1",
        "model_id": "deepseek-chat",
        "usd_per_m_in": 0.66,     # off-peak (peak doubles: 1.32/3.96)
        "usd_per_m_out": 1.98,
        "thinking": True,          # V4-Pro reasons — same headroom rule as Gemini
        # Calls during these UTC windows are refused by llm_client unless
        # DEEPSEEK_ALLOW_PEAK=1 — protects the off-peak cost basis.
        "peak_windows_utc": [(1, 4), (6, 10)],
    },
    # Judge — outside the five candidate families (Alibaba). Not a candidate.
    "qwen3.6-plus-judge": {
        "env_key": "TOGETHER_API_KEY",
        "base_url": "https://api.together.xyz/v1",
        "model_id": "Qwen/Qwen3.6-Plus",
        "usd_per_m_in": 0.50,
        "usd_per_m_out": 3.00,
    },
    # Gemini via Google's OpenAI-compatible endpoint — one client path for
    # OpenAI/Together/DeepSeek/Google; only Anthropic needs its own SDK.
    # NOTE: Google serves the 3.1 Pro tier as a "-preview" SKU (verified on
    # the live models endpoint, 18 Aug 2026) — logged as a maturity flag.
    "gemini-3.1-pro": {
        "env_key": "GOOGLE_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model_id": "models/gemini-3.1-pro-preview",
        "usd_per_m_in": 2.00,
        "usd_per_m_out": 12.00,
        # Thinking model: max_tokens caps reasoning + answer together, so the
        # client must give headroom (pilot finding: finish_reason=length at
        # 2048 with only ~80 visible output tokens).
        "thinking": True,
    },
}


def get_api_key(model_key: str) -> str:
    """Return the API key for a model, or raise with a clear setup message."""
    env_key = MODELS[model_key]["env_key"]
    key = os.getenv(env_key)
    if not key:
        raise RuntimeError(
            f"{env_key} is not set. Add it to {ROOT / '.env'} as a line like:\n"
            f"  {env_key}=sk-...\n"
        )
    return key


def cost_usd(model_key: str, tokens_in: int, tokens_out: int) -> float:
    """Cost of a single call at official list prices."""
    m = MODELS[model_key]
    return (tokens_in / 1e6) * m["usd_per_m_in"] + (tokens_out / 1e6) * m["usd_per_m_out"]
