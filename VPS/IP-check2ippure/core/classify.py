"""节点结果数据类、机房启发式、IPPure JSON 映射。"""
from dataclasses import dataclass
from typing import Optional

DATACENTER_KEYWORDS = (
    "vultr", "digitalocean", "linode", "amazon", "aws", "google", "ovh",
    "hetzner", "choopa", "constant", "cloudflare", "microsoft", "azure",
    "oracle", "tencent", "alibaba", "gcore", "leaseweb", "datacamp", "m247",
    "cogent", "level3", "akamai", "contabo", "scaleway", "bandwagon",
)


@dataclass
class NodeResult:
    name: str
    status: str = "ok"
    ip: str = ""
    asn: Optional[int] = None
    org: str = ""
    country: str = ""
    country_code: str = ""
    city: str = ""
    fraud_score: Optional[int] = None
    is_residential: Optional[bool] = None
    delay_ms: Optional[int] = None
    error: str = ""


def is_datacenter(is_residential: Optional[bool], org: str) -> bool:
    if is_residential:
        return False
    o = (org or "").lower()
    return any(k in o for k in DATACENTER_KEYWORDS)


def from_ippure_json(name: str, data: dict, delay_ms: Optional[int] = None) -> NodeResult:
    return NodeResult(
        name=name,
        status="ok",
        ip=data.get("ip", "") or "",
        asn=data.get("asn"),
        org=data.get("asOrganization", "") or "",
        country=data.get("country", "") or "",
        country_code=data.get("countryCode", "") or "",
        city=data.get("city", "") or "",
        fraud_score=data.get("fraudScore"),
        is_residential=data.get("isResidential"),
        delay_ms=delay_ms,
    )
