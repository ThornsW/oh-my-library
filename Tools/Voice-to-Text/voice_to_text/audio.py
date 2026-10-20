"""Microphone capture through PipeWire's pw-record (16 kHz, mono, 16-bit)."""

from __future__ import annotations

import io
import json
import math
import signal
import subprocess
import threading
import time
import wave
from array import array
from dataclasses import dataclass
from typing import Callable

from .errors import Stage, StageError

RATE = 16000
SAMPLE_WIDTH = 2
BYTES_PER_SECOND = RATE * SAMPLE_WIDTH
CHUNK = BYTES_PER_SECOND // 10  # 100 ms


def rms_db(pcm: bytes) -> float:
    samples = array("h")
    samples.frombytes(pcm[: len(pcm) // 2 * 2])
    if not samples:
        return -120.0
    mean_square = sum(s * s for s in samples) / len(samples)
    if mean_square <= 0:
        return -120.0
    return 10 * math.log10(mean_square / (32768.0 * 32768.0))


def wav_bytes(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(SAMPLE_WIDTH)
        w.setframerate(RATE)
        w.writeframes(pcm)
    return buf.getvalue()


def list_input_devices() -> list[tuple[str, str]]:
    """Return [(node.name, description)] for PipeWire audio sources."""
    try:
        out = subprocess.run(["pw-dump"], capture_output=True, text=True, timeout=5)
    except FileNotFoundError:
        raise StageError(Stage.RECORD, "找不到 pw-dump，需要 PipeWire（pipewire-bin）")
    except subprocess.TimeoutExpired:
        raise StageError(Stage.RECORD, "列出录音设备超时")
    try:
        objects = json.loads(out.stdout or "[]")
    except json.JSONDecodeError as e:
        raise StageError(Stage.RECORD, "无法解析录音设备列表", str(e))
    devices = []
    for obj in objects:
        if obj.get("type") != "PipeWire:Interface:Node":
            continue
        props = (obj.get("info") or {}).get("props") or {}
        if props.get("media.class") in ("Audio/Source", "Audio/Source/Virtual"):
            name = props.get("node.name")
            if name:
                devices.append((name, props.get("node.description") or name))
    return devices


@dataclass
class Recording:
    pcm: bytes
    peak_db: float  # loudest 100 ms window

    @property
    def seconds(self) -> float:
        return len(self.pcm) / BYTES_PER_SECOND

    def wav(self) -> bytes:
        return wav_bytes(self.pcm)


class Recorder:
    """One recording session: start() spawns pw-record, stop() returns the audio."""

    def __init__(self, device: str = "", on_level: Callable[[float], None] | None = None):
        self.device = device
        self.on_level = on_level
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._buf = bytearray()
        self._peak_db = -120.0
        self.started_at = 0.0

    def start(self) -> None:
        cmd = ["pw-record", "--rate", str(RATE), "--channels", "1", "--format", "s16"]
        if self.device:
            cmd += ["--target", self.device]
        cmd.append("-")
        try:
            self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except FileNotFoundError:
            raise StageError(Stage.RECORD, "找不到 pw-record，需要 PipeWire（pipewire-bin）")
        self.started_at = time.monotonic()
        self._thread = threading.Thread(target=self._read, args=(self._proc.stdout,), daemon=True)
        self._thread.start()

    def _read(self, stdout) -> None:
        # Reads until pw-record exits, so the audio captured right before stop() is kept.
        while True:
            chunk = stdout.read(CHUNK)
            if not chunk:
                break
            self._buf += chunk
            db = rms_db(chunk)
            if db > self._peak_db:
                self._peak_db = db
            if self.on_level:
                self.on_level(db)

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.started_at if self.started_at else 0.0

    def stop(self) -> Recording:
        proc = self._proc
        if proc is None:
            raise StageError(Stage.RECORD, "录音没有开始")
        self._proc = None
        if proc.poll() is None:
            proc.send_signal(signal.SIGINT)
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
        if self._thread:
            self._thread.join(timeout=2)
        stderr = proc.stderr.read().decode("utf-8", "replace").strip() if proc.stderr else ""
        if not self._buf:
            raise StageError(Stage.RECORD, "没有拿到任何音频数据（录音设备可能不可用）", stderr)
        return Recording(pcm=bytes(self._buf), peak_db=self._peak_db)

    def abort(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.kill()
        self._proc = None
