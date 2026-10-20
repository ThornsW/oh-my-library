"""端口选择与 HTTP 帮助函数（纯标准库 urllib）。"""
import json
import socket
import urllib.request
from typing import Optional


def find_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _opener(proxy: Optional[str]):
    handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy} if proxy else {})
    return urllib.request.build_opener(handler)


def http_request(url: str, method: str = "GET", body=None, secret: Optional[str] = None,
                 timeout: float = 10, proxy: Optional[str] = None):
    headers = {"User-Agent": "ippure-checker"}
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with _opener(proxy).open(req, timeout=timeout) as resp:
        raw = resp.read().decode().strip()
        parsed = json.loads(raw) if raw else {}
        return resp.status, parsed


def api_get(url: str, secret: Optional[str] = None, timeout: float = 10, proxy: Optional[str] = None) -> dict:
    return http_request(url, "GET", None, secret, timeout, proxy)[1]


def api_put(url: str, body=None, secret: Optional[str] = None, timeout: float = 10) -> int:
    return http_request(url, "PUT", body, secret, timeout, None)[0]
