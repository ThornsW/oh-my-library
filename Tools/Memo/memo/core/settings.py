"""User preferences persisted to ``settings.json``."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from memo.core import paths

DEFAULT_HOTKEY = "<ctrl>+<shift>+m"


@dataclass
class Settings:
    always_on_top: bool = False
    autostart: bool = False
    global_hotkey: str = DEFAULT_HOTKEY
    window_geometry: str = ""        # base64 of QByteArray
    splitter_horizontal: str = ""    # base64 of QByteArray (sidebar | main)
    splitter_vertical: str = ""      # base64 of QByteArray (list | detail)
    selected_tag_id: int | None = None
    filter: str = "active"           # 'all' | 'active' | 'done'

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        target = path if path is not None else paths.settings_path()
        if not target.exists():
            return cls()
        try:
            raw: dict[str, Any] = json.loads(target.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()
        # Drop unknown keys, keep defaults for missing ones.
        known = {f.name for f in fields(cls)}
        clean = {k: v for k, v in raw.items() if k in known}
        return cls(**clean)

    def save(self, path: Path | None = None) -> None:
        target = path if path is not None else paths.settings_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
