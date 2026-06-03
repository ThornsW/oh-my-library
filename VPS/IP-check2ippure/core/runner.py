"""核心检测循环：对每个节点 切换→延迟→查询→产出 NodeResult。"""
import time
from typing import Callable, List
from core.classify import NodeResult, from_ippure_json


def run_checks(controller, query: Callable[..., dict], proxy_port: int,
               gap: float = 0.3, timeout: float = 8,
               on_progress: Callable[[int, int, NodeResult], None] = None) -> List[NodeResult]:
    members = controller.list_group_members()
    total = len(members)
    results: List[NodeResult] = []
    for idx, node in enumerate(members, 1):
        controller.switch(node)
        delay_ms = controller.delay(node)
        try:
            data = query(proxy_port, timeout=timeout)
            r = from_ippure_json(node, data, delay_ms=delay_ms)
        except TimeoutError as e:
            r = NodeResult(name=node, status="timeout", delay_ms=delay_ms, error=str(e))
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            status = "ratelimit" if "429" in msg else "fail"
            r = NodeResult(name=node, status=status, delay_ms=delay_ms, error=msg)
        results.append(r)
        if on_progress:
            on_progress(idx, total, r)
        if gap and idx < total:
            time.sleep(gap)
    return results
