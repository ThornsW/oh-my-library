"""Entry point. Without options it starts the GUI; options run diagnostics."""

from __future__ import annotations

import argparse
import os
import sys
import time

from . import __version__
from .config import Config, resolve_config_dir
from .errors import StageError
from .log import log, redact, setup


def _diag_list_devices() -> int:
    from .audio import list_input_devices
    for name, desc in list_input_devices():
        print(f"{name}\t{desc}")
    return 0


def _diag_record(cfg: Config, seconds: float, out: str) -> int:
    from .audio import Recorder
    rec = Recorder(cfg["audio_device"])
    rec.start()
    time.sleep(seconds)
    r = rec.stop()
    with open(out, "wb") as f:
        f.write(r.wav())
    print(f"录音 {r.seconds:.1f}s，最大音量 {r.peak_db:.1f} dB -> {out}")
    return 0


def _diag_asr(cfg: Config, wav_path: str, provider_name: str | None) -> int:
    from .asr import transcribe
    from .postprocess import clean
    provider = cfg.provider(provider_name)
    with open(wav_path, "rb") as f:
        wav = f.read()
    t0 = time.monotonic()
    text = transcribe(provider, wav, cfg["language"], cfg["context"], cfg["request_timeout_s"])
    print(f"[{provider['name']}] {(time.monotonic() - t0) * 1000:.0f} ms")
    print("原始:", text)
    print("整理:", clean(text, cfg["replacements"], cfg["strip_trailing_period"]))
    return 0


def _diag_deliver(cfg: Config, text: str, window: int | None, enter: bool) -> int:
    from .deliver import DeliverySettings, deliver
    settings = DeliverySettings(cfg["paste_keys"], cfg["enter_keys"],
                                cfg["delay_before_paste_ms"], cfg["delay_before_enter_ms"])
    r = deliver(text, window or cfg["target_window"], settings, enter=enter, allowed=None)
    print("已粘贴" + ("并回车" if r.entered else "") + (f"（{r.note}）" if r.note else ""))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="voice-to-text", description="按住说话，识别后粘贴到终端")
    p.add_argument("--config-dir", help="配置/日志/缓存目录（默认：程序所在目录）")
    p.add_argument("--list-devices", action="store_true", help="列出录音设备")
    p.add_argument("--record", type=float, metavar="SECONDS", help="录一段音，配合 --out")
    p.add_argument("--out", default="vtt-record.wav", help="--record 的输出文件")
    p.add_argument("--test-asr", metavar="WAV", help="用一个 WAV 文件测试识别")
    p.add_argument("--provider", help="--test-asr 使用的服务名称（默认当前选中的）")
    p.add_argument("--test-deliver", metavar="TEXT", help="把文字投递到目标窗口")
    p.add_argument("--window", type=int, help="--test-deliver 的窗口 id（默认已绑定的）")
    p.add_argument("--enter", action="store_true", help="--test-deliver 后按回车")
    p.add_argument("--version", action="version", version=__version__)
    args = p.parse_args(argv)

    config_dir, warning = resolve_config_dir(args.config_dir)
    cfg = Config(config_dir).load()
    setup(cfg.log_dir)
    log.info("start v%s config=%s", __version__, cfg.path)

    try:
        if args.list_devices:
            return _diag_list_devices()
        if args.record:
            return _diag_record(cfg, args.record, args.out)
        if args.test_asr:
            return _diag_asr(cfg, args.test_asr, args.provider)
        if args.test_deliver:
            return _diag_deliver(cfg, args.test_deliver, args.window, args.enter)
    except StageError as e:
        print(f"失败 {e}", file=sys.stderr)
        if e.detail:
            print(redact(e.detail), file=sys.stderr)
        return 1

    if os.environ.get("XDG_SESSION_TYPE") == "wayland" or not os.environ.get("DISPLAY"):
        print("需要 X11 桌面会话（当前不是 X11，xdotool 无法工作）", file=sys.stderr)
        return 1
    try:
        from .ui.app import run_gui
    except (ImportError, ValueError) as e:
        print(f"需要系统自带的 GTK3 Python 接口：sudo apt install python3-gi gir1.2-gtk-3.0（{e}）",
              file=sys.stderr)
        return 1
    return run_gui(cfg, warning)


if __name__ == "__main__":
    sys.exit(main())
