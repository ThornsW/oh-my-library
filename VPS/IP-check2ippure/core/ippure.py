"""查询 IPPure /v1/info（经代理或直连）。"""
from typing import Optional
from core.netutil import api_get

IPPURE_URL = "https://my.ippure.com/v1/info"


def query_via_proxy(proxy_port: int, timeout: float = 8) -> dict:
    return api_get(IPPURE_URL, timeout=timeout, proxy=f"http://127.0.0.1:{proxy_port}")


def query_direct(timeout: float = 8) -> dict:
    return api_get(IPPURE_URL, timeout=timeout, proxy=None)
