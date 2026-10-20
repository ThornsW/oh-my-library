"""Settings stored as config.json next to the program (portable by default)."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

from .log import register_secret

def _app_dir() -> Path:
    """The folder that holds the program: the source checkout, or the folder
    containing the single-file build (where the package lives inside the file)."""
    here = Path(__file__).resolve().parent.parent
    return here.parent if here.is_file() else here


APP_DIR = _app_dir()

PROTOCOLS = {
    "openai_chat_audio": "OpenAI 兼容 · 聊天音频（同步）",
    "openai_transcriptions": "OpenAI 标准转写 /audio/transcriptions",
    "dashscope_native": "DashScope 原生 · 同步",
}

DEFAULT_PROVIDERS = [
    {
        "name": "千问 qwen3-asr-flash（OpenAI 兼容）",
        "protocol": "openai_chat_audio",
        "base_url": "https://maas.qianwenaiapi.com/compatible-mode/v1",
        "model": "qwen3-asr-flash",
        "api_key": "",
        "audio_format": "data_uri",
        "extra_json": '{"asr_options": {"enable_itn": false}}',
    },
    {
        "name": "千问 DashScope 原生（同步）",
        "protocol": "dashscope_native",
        "base_url": "https://maas.qianwenaiapi.com/api/v1",
        "model": "qwen3-asr-flash",
        "api_key": "",
        "audio_format": "data_uri",
        "extra_json": '{"parameters": {"asr_options": {"enable_itn": false}}}',
    },
    {
        "name": "OpenAI Whisper（标准转写）",
        "protocol": "openai_transcriptions",
        "base_url": "https://api.openai.com/v1",
        "model": "whisper-1",
        "api_key": "",
        "audio_format": "data_uri",
        "extra_json": "",
    },
]

DEFAULTS: dict = {
    "version": 1,
    "active_provider": DEFAULT_PROVIDERS[0]["name"],
    "providers": DEFAULT_PROVIDERS,
    # Recognition
    "language": "",  # "" = let the service detect; "zh", "en", ...
    "context": "Codex, Claude, Claude Code, Ubuntu, API, CLI, GitHub, Python",
    "replacements": "",  # one rule per line: wrong => right
    "strip_trailing_period": False,
    "request_timeout_s": 30,
    # Recording
    "audio_device": "",  # PipeWire node.name; "" = system default
    "min_seconds": 0.4,
    "tail_ms": 1000,  # keep recording this long after release so the last word is complete
    "max_seconds": 180,
    "silence_threshold_db": -50.0,
    # Delivery
    "auto_paste": True,
    "auto_enter": False,
    "paste_keys": "ctrl+shift+v",
    "enter_keys": "Return",
    "delay_before_paste_ms": 60,
    "delay_before_enter_ms": 300,
    "target_mode": "fixed",  # fixed | follow
    "target_window": 0,
    "target_title": "",
    # UI
    "floating_visible": True,
    "floating_pos": None,
    "main_on_top": False,
    "font_pt": 13,
}


def resolve_config_dir(override: str | None = None) -> tuple[Path, str | None]:
    """Return (directory, warning). Program directory unless overridden or read-only."""
    chosen = override or os.environ.get("VTT_CONFIG_DIR")
    if chosen:
        d = Path(chosen).expanduser().resolve()
        d.mkdir(parents=True, exist_ok=True)
        return d, None
    if os.access(APP_DIR, os.W_OK):
        return APP_DIR, None
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    d = base / "voice-to-text"
    d.mkdir(parents=True, exist_ok=True)
    return d, f"程序目录不可写，配置改存到 {d}"


class Config:
    def __init__(self, directory: Path):
        self.dir = directory
        self.path = directory / "config.json"
        self.data: dict = copy.deepcopy(DEFAULTS)

    @property
    def log_dir(self) -> Path:
        return self.dir / "logs"

    @property
    def cache_dir(self) -> Path:
        return self.dir / "cache"

    def load(self) -> "Config":
        if self.path.exists():
            with open(self.path, encoding="utf-8") as f:
                stored = json.load(f)
            for k, v in stored.items():
                self.data[k] = v
        else:
            self.save()
        for p in self.data.get("providers", []):
            register_secret(p.get("api_key"))
        return self

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.chmod(tmp, 0o600)  # holds API keys
        os.replace(tmp, self.path)
        for p in self.data.get("providers", []):
            register_secret(p.get("api_key"))

    def __getitem__(self, key: str):
        return self.data.get(key, DEFAULTS.get(key))

    def __setitem__(self, key: str, value) -> None:
        self.data[key] = value

    def provider(self, name: str | None = None) -> dict:
        providers = self.data.get("providers") or []
        want = name or self.data.get("active_provider")
        for p in providers:
            if p.get("name") == want:
                return p
        if not providers:
            raise LookupError("没有配置任何识别服务")
        if name:
            raise LookupError(f"找不到识别服务「{name}」")
        return providers[0]
