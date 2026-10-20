"""Put text into a target X11 window: clipboard (xclip) + paste keystroke (xdotool).

The clipboard is owned by a separate xclip process, not by this program, so the
terminal's paste request is answered even while we are sleeping before Enter.
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass

from .errors import ForegroundChanged, Stage, StageError
from .log import log


def _run(cmd: list[str], timeout: float = 3.0, stage: str = Stage.TARGET) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        raise StageError(stage, f"找不到 {cmd[0]}，请先安装（sudo apt install {cmd[0]}）")
    except subprocess.TimeoutExpired:
        raise StageError(stage, f"{cmd[0]} 执行超时", " ".join(cmd))


def active_window() -> int | None:
    r = _run(["xdotool", "getactivewindow"], stage=Stage.FOCUS)
    try:
        return int(r.stdout.strip()) if r.returncode == 0 else None
    except ValueError:
        return None


def window_exists(wid: int) -> bool:
    return bool(wid) and _run(["xdotool", "getwindowname", str(wid)]).returncode == 0


def window_title(wid: int | None) -> str:
    if not wid:
        return ""
    r = _run(["xdotool", "getwindowname", str(wid)])
    return r.stdout.decode("utf-8", "replace").strip() if r.returncode == 0 else ""


def select_window(timeout: float = 30.0) -> int:
    """Let the user click a window; returns its id."""
    r = _run(["xdotool", "selectwindow"], timeout=timeout)
    try:
        return int(r.stdout.strip())
    except ValueError:
        raise StageError(Stage.TARGET, "没有选中窗口", r.stderr.decode("utf-8", "replace"))


def set_clipboard(text: str) -> None:
    data = text.encode("utf-8")
    # No captured pipes here: the forked xclip owner would hold them open and block us.
    try:
        rc = subprocess.run(["xclip", "-selection", "clipboard", "-i"], input=data, timeout=3,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
    except FileNotFoundError:
        raise StageError(Stage.CLIPBOARD, "找不到 xclip，请先安装（sudo apt install xclip）")
    except subprocess.TimeoutExpired:
        raise StageError(Stage.CLIPBOARD, "xclip 执行超时")
    if rc != 0:
        raise StageError(Stage.CLIPBOARD, f"写入剪贴板失败（xclip 退出码 {rc}）")
    # xclip forks a background owner; confirm the terminal will get *this* text, not an old one.
    for _ in range(10):
        got = _run(["xclip", "-selection", "clipboard", "-o"], stage=Stage.CLIPBOARD)
        if got.returncode == 0 and got.stdout == data:
            return
        time.sleep(0.03)
    raise StageError(Stage.CLIPBOARD, "剪贴板内容校验失败（可能被其他程序改写）")


def target_is_active(target: int) -> bool:
    current = active_window()
    return current is not None and is_same_window(current, target)


def activate(wid: int) -> None:
    if target_is_active(wid):
        return
    _run(["xdotool", "windowactivate", "--sync", str(wid)], timeout=3, stage=Stage.FOCUS)
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        if target_is_active(wid):
            return
        time.sleep(0.03)
    raise StageError(Stage.FOCUS, "无法把目标窗口切到前台")


def press(keys: str, stage: str) -> None:
    r = _run(["xdotool", "key", "--clearmodifiers", *keys.split()], stage=stage)
    if r.returncode != 0:
        raise StageError(stage, f"发送按键 {keys} 失败", r.stderr.decode("utf-8", "replace"))


@dataclass
class DeliverySettings:
    paste_keys: str = "ctrl+shift+v"
    enter_keys: str = "Return"
    delay_before_paste_ms: int = 60
    delay_before_enter_ms: int = 300


@dataclass
class DeliveryResult:
    entered: bool
    note: str = ""


def check_target(target: int | None) -> int:
    if not target:
        raise StageError(Stage.TARGET, "还没有绑定目标窗口，请点「绑定窗口」")
    if not window_exists(target):
        raise StageError(Stage.TARGET, "绑定的窗口已关闭，请重新绑定")
    return target


def window_pid(wid: int) -> int | None:
    r = _run(["xdotool", "getwindowpid", str(wid)], stage=Stage.FOCUS)
    try:
        return int(r.stdout.strip()) if r.returncode == 0 else None
    except ValueError:
        return None


def child_windows(wid: int) -> set[int]:
    """Direct children of a window. Window managers such as GNOME's
    mutter-x11-frames wrap each app window in a separate frame window."""
    r = _run(["xwininfo", "-children", "-id", str(wid)], stage=Stage.FOCUS)
    ids = set()
    for line in r.stdout.decode("utf-8", "replace").splitlines():
        token = line.strip().split(" ", 1)[0]
        if token.startswith("0x"):
            try:
                ids.add(int(token, 16))
            except ValueError:
                pass
    ids.discard(wid)
    return ids


def is_own_window(wid: int, own_ids: set[int]) -> bool:
    if wid in own_ids or window_pid(wid) == os.getpid():
        return True
    return bool(child_windows(wid) & own_ids)


def is_same_window(wid: int, target: int) -> bool:
    return wid == target or target in child_windows(wid)


def check_foreground(target: int, allowed: set[int]) -> None:
    """Refuse when the user is working in some unrelated window."""
    current = active_window()
    if current is None or is_same_window(current, target) or is_own_window(current, allowed):
        return
    log.info("foreground check: blocked current=0x%x pid=%s target=0x%x own=%s", current,
             window_pid(current), target, [hex(i) for i in sorted(allowed)])
    raise ForegroundChanged(window_title(current))


def deliver(text: str, target: int | None, settings: DeliverySettings, enter: bool,
            allowed: set[int] | None = None) -> DeliveryResult:
    """Paste text into target, then optionally press Enter.

    allowed: our own window ids. Pass None to skip the foreground check
    (used when the user explicitly asks to send).
    """
    t0 = time.monotonic()
    target = check_target(target)
    if allowed is not None:
        check_foreground(target, allowed)
    set_clipboard(text)
    activate(target)
    time.sleep(settings.delay_before_paste_ms / 1000)
    if not target_is_active(target):
        raise StageError(Stage.PASTE, "粘贴前目标窗口失去焦点，已停止")
    press(settings.paste_keys, Stage.PASTE)
    log.info("delivery: pasted %d chars into %s (%.0f ms)", len(text), target,
             (time.monotonic() - t0) * 1000)
    if not enter:
        return DeliveryResult(entered=False)
    time.sleep(settings.delay_before_enter_ms / 1000)
    if not target_is_active(target):
        log.info("delivery: enter skipped, focus left %s", target)
        return DeliveryResult(entered=False, note="已粘贴，但焦点已变，没有按回车")
    press(settings.enter_keys, Stage.ENTER)
    log.info("delivery: enter sent to %s", target)
    return DeliveryResult(entered=True)


def press_enter(target: int | None, settings: DeliverySettings) -> None:
    target = check_target(target)
    activate(target)
    time.sleep(settings.delay_before_paste_ms / 1000)
    press(settings.enter_keys, Stage.ENTER)
