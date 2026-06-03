"""下载、校验、固定 mihomo 静态二进制（trust-on-first-use + SHA 固定）。"""
import gzip
import hashlib
import json
import os
import re
import stat
import urllib.request
from typing import List

RELEASES_API = "https://api.github.com/repos/MetaCubeX/mihomo/releases/latest"
_ASSET_PATTERNS = [
    r"^mihomo-linux-amd64-compatible-v[\d.]+\.gz$",
    r"^mihomo-linux-amd64-v[\d.]+\.gz$",
]


def pick_asset(assets: List[dict]) -> dict:
    for pat in _ASSET_PATTERNS:
        for a in assets:
            if re.match(pat, a["name"]):
                return a
    raise RuntimeError("GitHub release 里找不到 linux-amd64 的 .gz 资产")


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
    os.makedirs(bin_dir, exist_ok=True)
    release = json.loads(_fetch(RELEASES_API, timeout=30))
    asset = pick_asset(release.get("assets", []))
    print(f"[binary] 下载 {asset['name']} ...")
    data = gzip.decompress(_fetch(asset["browser_download_url"], timeout=180))
    with open(path, "wb") as f:
        f.write(data)
    _make_executable(path)
    digest = sha256_file(path)
    with open(sha_path, "w") as f:
        f.write(digest)
    print(f"[binary] 已固定 SHA256={digest}")
    return path
