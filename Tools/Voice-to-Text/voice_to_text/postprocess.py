"""Clean up recognized text before it is pasted."""

from __future__ import annotations

import re


def parse_rules(rules: str) -> list[tuple[str, str]]:
    """One rule per line, `wrong => right`. Lines starting with # are comments."""
    out = []
    for line in (rules or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=>" not in line:
            continue
        wrong, right = line.split("=>", 1)
        if wrong.strip():
            out.append((wrong.strip(), right.strip()))
    return out


def clean(text: str, rules: str = "", strip_trailing_period: bool = False) -> str:
    # A newline inside the text would act like Enter in some terminals.
    text = re.sub(r"\s*[\r\n]+\s*", " ", text or "").strip()
    for wrong, right in parse_rules(rules):
        text = re.sub(re.escape(wrong), lambda _m: right, text, flags=re.IGNORECASE)
    if strip_trailing_period:
        text = re.sub(r"[。.]+$", "", text)
    return text
