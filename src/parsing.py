"""
parsing.py
----------
Response parsing shared by all task runners.

Pilot finding (17 Aug 2026): models sometimes append explanatory prose after
a valid JSON object despite instructions not to (1/30 pilot responses).
extract_first_json() therefore parses the FIRST balanced {...} object and
ignores anything after it, and tolerates markdown code fences.
"""

import json
import re


def extract_first_json(text: str) -> dict:
    """Parse the first balanced JSON object in a model response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].removeprefix("json").strip()
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object found in response")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("unbalanced JSON object in response")


def normalise(s: str) -> str:
    """Whitespace-collapse + lowercase, for span/answer comparison."""
    return re.sub(r"\s+", " ", s).strip().lower()
