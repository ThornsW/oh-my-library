"""生成 mihomo 配置。输出用 json.dumps —— JSON 是合法 YAML，mihomo 直接可读。"""
import json

GROUP_NAME = "T"
PROVIDER_NAME = "airport"


def build_config(sub_url: str, mixed_port: int, ctrl_port: int, secret: str,
                 user_agent: str = "mihomo") -> dict:
    return {
        "mixed-port": mixed_port,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "warning",
        "external-controller": f"127.0.0.1:{ctrl_port}",
        "secret": secret,
        "dns": {
            "enable": True,
            "ipv6": False,
            "nameserver": ["1.1.1.1", "8.8.8.8"],
        },
        "proxy-providers": {
            PROVIDER_NAME: {
                "type": "http",
                "url": sub_url,
                "interval": 86400,
                "path": f"./{PROVIDER_NAME}-provider.yaml",
                "health-check": {
                    "enable": False,
                    "url": "http://www.gstatic.com/generate_204",
                    "interval": 0,
                },
                "header": {"User-Agent": [user_agent]},
            }
        },
        "proxy-groups": [
            {"name": GROUP_NAME, "type": "select", "use": [PROVIDER_NAME]}
        ],
        "rules": [f"MATCH,{GROUP_NAME}"],
    }


def dump_config(cfg: dict) -> str:
    return json.dumps(cfg, ensure_ascii=False, indent=2)
