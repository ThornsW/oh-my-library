"""管理 mihomo 子进程并通过 external-controller API 操作。"""
import os
import subprocess
import time
import urllib.parse
from typing import List, Optional
from core.netutil import api_get, api_put
from core.config_gen import GROUP_NAME, PROVIDER_NAME

_SPECIAL = {"DIRECT", "REJECT", "REJECT-DROP", "PASS", "COMPATIBLE", GROUP_NAME}


class MihomoController:
    def __init__(self, binary: str, run_dir: str, config_path: str, ctrl_port: int, secret: str):
        self.binary = binary
        self.run_dir = run_dir
        self.config_path = config_path
        self.base = f"http://127.0.0.1:{ctrl_port}"
        self.secret = secret
        self.proc: Optional[subprocess.Popen] = None

    def start(self) -> None:
        log = open(os.path.join(self.run_dir, "mihomo.log"), "w")
        self.proc = subprocess.Popen(
            [self.binary, "-d", self.run_dir, "-f", self.config_path],
            stdout=log, stderr=subprocess.STDOUT,
        )

    def wait_ready(self, timeout: float = 30) -> None:
        deadline = time.time() + timeout
        last = ""
        while time.time() < deadline:
            if self.proc and self.proc.poll() is not None:
                raise RuntimeError(f"mihomo 进程已退出(code={self.proc.returncode})，查看 run/mihomo.log")
            try:
                api_get(self.base + "/version", secret=self.secret, timeout=2)
                return
            except Exception as e:  # noqa: BLE001
                last = str(e)
                time.sleep(0.5)
        raise RuntimeError(f"mihomo 控制器 30s 内未就绪：{last}")

    def list_group_members(self, group: str = GROUP_NAME) -> List[str]:
        try:
            data = api_get(self.base + "/proxies/" + urllib.parse.quote(group),
                           secret=self.secret, timeout=5)
        except Exception:  # noqa: BLE001
            return []
        return [m for m in data.get("all", []) if m not in _SPECIAL]

    def wait_provider(self, group: str = GROUP_NAME, timeout: float = 60) -> List[str]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            members = self.list_group_members(group)
            if members:
                return members
            try:
                api_put(self.base + "/providers/proxies/" + PROVIDER_NAME, None, secret=self.secret, timeout=10)
            except Exception:  # noqa: BLE001
                pass
            time.sleep(1.5)
        raise RuntimeError(
            "60s 内订阅节点列表为空：① 确认透明/系统代理（如 PassWall）已关闭（多数机场拒绝代理 IP 拉取订阅，"
            "会返回“请关闭网络代理后再获取订阅”）；② 订阅 URL 是否有效；③ UA 是否需调整（--ua）")

    def switch(self, node: str, group: str = GROUP_NAME) -> None:
        api_put(self.base + "/proxies/" + urllib.parse.quote(group), {"name": node}, secret=self.secret, timeout=5)

    def delay(self, node: str, url: str = "http://www.gstatic.com/generate_204", timeout_ms: int = 5000) -> Optional[int]:
        q = urllib.parse.urlencode({"url": url, "timeout": timeout_ms})
        try:
            data = api_get(self.base + "/proxies/" + urllib.parse.quote(node) + "/delay?" + q,
                           secret=self.secret, timeout=timeout_ms / 1000 + 3)
            return data.get("delay")
        except Exception:  # noqa: BLE001
            return None

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
