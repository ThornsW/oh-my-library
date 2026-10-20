"""File logging with secret redaction.

Every string that reaches the log file or the UI's error details goes through
redact(), so API keys, bearer tokens and base64 audio never leak.
"""

from __future__ import annotations

import logging
import re
import sys
import threading
from datetime import date
from pathlib import Path

_secrets: set[str] = set()
_lock = threading.Lock()

_BEARER = re.compile(r"(?i)(bearer\s+)[^\s\"',}]+")
_SK = re.compile(r"\bsk-[A-Za-z0-9_\-]{6,}")
_B64_AUDIO = re.compile(r"(base64,)[A-Za-z0-9+/=]{16,}")

log = logging.getLogger("vtt")


def register_secret(value: str | None) -> None:
    """Remember a secret so redact() masks it wherever it appears."""
    if value and len(value) >= 4:
        with _lock:
            _secrets.add(value)


def redact(text: str) -> str:
    if not text:
        return text
    with _lock:
        secrets = sorted(_secrets, key=len, reverse=True)
    for s in secrets:
        text = text.replace(s, "***")
    text = _BEARER.sub(r"\1***", text)
    text = _SK.sub("sk-***", text)
    text = _B64_AUDIO.sub(r"\1<音频数据已省略>", text)
    return text


class _RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


def setup(log_dir: Path, to_stderr: bool = True) -> Path:
    """Log to <log_dir>/vtt-YYYY-MM-DD.log (one file per start date)."""
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"vtt-{date.today():%Y-%m-%d}.log"
    fmt = _RedactingFormatter("%(asctime)s.%(msecs)03d %(levelname)s %(message)s", "%H:%M:%S")
    fh = logging.FileHandler(path, encoding="utf-8")
    fh.setFormatter(fmt)
    log.handlers.clear()
    log.addHandler(fh)
    if to_stderr:
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(fmt)
        log.addHandler(sh)
    log.setLevel(logging.INFO)
    log.propagate = False
    return path
