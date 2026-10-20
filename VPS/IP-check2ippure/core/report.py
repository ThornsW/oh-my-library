"""排序与报表渲染：文本表格 / CSV / Markdown。"""
import csv
from typing import List
from core.classify import NodeResult, is_datacenter

_COLUMNS = [
    ("#",        lambda i, r: str(i)),
    ("节点名",    lambda i, r: r.name),
    ("出口IP",    lambda i, r: r.ip or "-"),
    ("国家/城市", lambda i, r: _geo(r)),
    ("ASN/组织",  lambda i, r: _asn(r)),
    ("风险分",    lambda i, r: "-" if r.fraud_score is None else str(r.fraud_score)),
    ("原生",      lambda i, r: _tri(r.is_residential)),
    ("机房?",     lambda i, r: _dc(r)),
    ("延迟ms",    lambda i, r: "-" if r.delay_ms is None else str(r.delay_ms)),
    ("状态",      lambda i, r: r.status),
]


def _geo(r: NodeResult) -> str:
    if r.country_code and r.city:
        return f"{r.country_code}/{r.city}"
    return r.country_code or r.country or "-"


def _asn(r: NodeResult) -> str:
    if r.asn is None and not r.org:
        return "-"
    return f"AS{r.asn} {r.org}".strip()


def _tri(v) -> str:
    if v is None:
        return "-"
    return "是" if v else "否"


def _dc(r: NodeResult) -> str:
    if r.status != "ok":
        return "-"
    return "是" if is_datacenter(r.is_residential, r.org) else "否"


def sort_results(results: List[NodeResult]) -> List[NodeResult]:
    def key(r: NodeResult):
        ok = 0 if r.status == "ok" else 1
        fs = r.fraud_score if r.fraud_score is not None else 10_000
        return (ok, fs, r.name)
    return sorted(results, key=key)


def _disp_width(s: str) -> int:
    return sum(2 if ord(c) > 0x2E7F else 1 for c in s)


def _pad(s: str, width: int) -> str:
    return s + " " * max(0, width - _disp_width(s))


def render_table(results: List[NodeResult]) -> str:
    rows = [[col[1](i + 1, r) for col in _COLUMNS] for i, r in enumerate(results)]
    headers = [c[0] for c in _COLUMNS]
    widths = [_disp_width(h) for h in headers]
    for row in rows:
        for j, cell in enumerate(row):
            widths[j] = max(widths[j], _disp_width(cell))
    lines = ["  ".join(_pad(h, widths[j]) for j, h in enumerate(headers))]
    lines.append("  ".join("-" * widths[j] for j in range(len(headers))))
    for row in rows:
        lines.append("  ".join(_pad(c, widths[j]) for j, c in enumerate(row)))
    return "\n".join(lines)


_CSV_FIELDS = ["name", "status", "ip", "asn", "org", "country", "country_code",
               "city", "fraud_score", "is_residential", "is_datacenter", "delay_ms", "error"]


def write_csv(results: List[NodeResult], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
        w.writeheader()
        for r in results:
            w.writerow({
                "name": r.name, "status": r.status, "ip": r.ip, "asn": r.asn,
                "org": r.org, "country": r.country, "country_code": r.country_code,
                "city": r.city, "fraud_score": r.fraud_score,
                "is_residential": r.is_residential,
                "is_datacenter": is_datacenter(r.is_residential, r.org) if r.status == "ok" else "",
                "delay_ms": r.delay_ms, "error": r.error,
            })


def write_markdown(results: List[NodeResult], path: str, title: str = "机场节点 IPPure 质检") -> None:
    headers = [c[0] for c in _COLUMNS]
    lines = [f"# {title}", "", "| " + " | ".join(headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    for i, r in enumerate(results):
        cells = [col[1](i + 1, r) for col in _COLUMNS]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
