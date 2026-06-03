"""下载、校验、固定 mihomo 静态二进制（trust-on-first-use + SHA 固定）。

自动按当前操作系统/CPU 架构选择 mihomo 官方构建：
支持 Linux / macOS 的 amd64 与 arm64。原生 Windows 请在 WSL 下运行。
"""
import gzip
import hashlib
import json
import os
import platform
import re
import stat
import sys
import urllib.request
from typing import List, Tuple

RELEASES_API = "https://api.github.com/repos/MetaCubeX/mihomo/releases/latest"


def detect_platform() -> Tuple[str, str]:
    """返回 (os_tag, arch)；不支持的平台抛出明确错误。"""
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        arch = "amd64"
    elif machine in ("aarch64", "arm64"):
        arch = "arm64"
    else:
        raise RuntimeError(f"不支持的 CPU 架构：{machine}（mihomo 无对应预编译构建）")
    if sys.platform.startswith("linux"):
        return "linux", arch
    if sys.platform == "darwin":
        return "darwin", arch
    if sys.platform.startswith("win"):
        raise RuntimeError("暂不支持原生 Windows，请在 WSL（Windows 上的 Linux 子系统）下运行本工具。")
    raise RuntimeError(f"不支持的操作系统：{sys.platform}")


def _candidate_patterns(os_tag: str, arch: str) -> List[str]:
    """按优先级返回可接受的资产名正则。amd64 优先 compatible（兼容老 CPU）。"""
    pats = []
    if arch == "amd64":
        pats.append(rf"^mihomo-{os_tag}-amd64-compatible-v[\d.]+\.gz$")
    pats.append(rf"^mihomo-{os_tag}-{arch}-v[\d.]+\.gz$")
    return pats


def pick_asset(assets: List[dict], os_tag: str, arch: str) -> dict:
    for pat in _candidate_patterns(os_tag, arch):
        for a in assets:
            if re.match(pat, a["name"]):
                return a
    raise RuntimeError(f"GitHub release 里找不到 {os_tag}-{arch} 的 mihomo .gz 资产")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _make_executable(path: str) -> None:
    mode = os.stat(path).st_mode
    os.chmod(path, mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def _fetch(url: str, timeout: float) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "ippure-checker"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def ensure_mihomo(bin_dir: str) -> str:
    path = os.path.join(bin_dir, "mihomo")
    sha_path = path + ".sha256"
    if os.path.exists(path) and os.access(path, os.X_OK) and os.path.exists(sha_path):
        with open(sha_path) as f:
            pinned = f.read().strip()
        if sha256_file(path) == pinned:
            return path
    os_tag, arch = detect_platform()
    os.makedirs(bin_dir, exist_ok=True)
    release = json.loads(_fetch(RELEASES_API, timeout=30))
    asset = pick_asset(release.get("assets", []), os_tag, arch)
    print(f"[binary] 下载 {asset['name']}（{os_tag}-{arch}）...")
    data = gzip.decompress(_fetch(asset["browser_download_url"], timeout=180))
    with open(path, "wb") as f:
        f.write(data)
    _make_executable(path)
    digest = sha256_file(path)
    with open(sha_path, "w") as f:
        f.write(digest)
    print(f"[binary] 已固定 SHA256={digest}")
    return path
