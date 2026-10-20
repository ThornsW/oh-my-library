"""读取程序目录下的 .env（KEY=VALUE），只补充尚未设置的环境变量。纯标准库。

支持空行、# 开头的注释行、可选的 export 前缀、成对的单/双引号。
不支持行尾注释：订阅 URL 里可能带 #，整行 = 之后的内容都算作值。
"""
import os
from typing import Dict, MutableMapping


def parse_env_file(path: str) -> Dict[str, str]:
    values: Dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        return values
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, sep, value = line.partition("=")
        if not sep or not key.strip():
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def load_env_file(path: str, environ: MutableMapping[str, str] = os.environ) -> None:
    """已存在的环境变量优先，.env 只补空缺。"""
    for key, value in parse_env_file(path).items():
        environ.setdefault(key, value)
