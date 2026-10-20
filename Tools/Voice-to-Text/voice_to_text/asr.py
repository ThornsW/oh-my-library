"""Cloud speech recognition. One adapter per protocol; models of the same
protocol only differ by the model name in settings."""

from __future__ import annotations

import base64
import json
import socket
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass

from .errors import Stage, StageError
from .log import log, redact


@dataclass
class AsrRequest:
    url: str
    headers: dict
    body: bytes


def _merge(base: dict, extra: dict) -> dict:
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
    return base


def _extra(provider: dict) -> dict:
    raw = (provider.get("extra_json") or "").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as e:
        raise StageError(Stage.CONFIG, "「附加参数」不是合法的 JSON", str(e))
    if not isinstance(value, dict):
        raise StageError(Stage.CONFIG, "「附加参数」必须是 JSON 对象 {...}")
    return value


def _auth(provider: dict) -> dict:
    key = (provider.get("api_key") or "").strip()
    return {"Authorization": f"Bearer {key}"} if key else {}


def _data_uri(wav: bytes) -> str:
    return "data:audio/wav;base64," + base64.b64encode(wav).decode("ascii")


# ---------- request builders ----------

def build_openai_chat_audio(provider: dict, wav: bytes, language: str, context: str) -> AsrRequest:
    if provider.get("audio_format") == "base64":  # OpenAI's own format
        audio = {"data": base64.b64encode(wav).decode("ascii"), "format": "wav"}
    else:  # DashScope / Qwen style
        audio = {"data": _data_uri(wav)}
    messages = []
    if context:
        messages.append({"role": "system", "content": [{"type": "text", "text": context}]})
    messages.append({"role": "user", "content": [{"type": "input_audio", "input_audio": audio}]})
    body: dict = {"model": provider["model"], "messages": messages, "stream": False}
    if language:
        body["asr_options"] = {"language": language}
    _merge(body, _extra(provider))
    url = provider["base_url"].rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json", **_auth(provider)}
    return AsrRequest(url, headers, json.dumps(body, ensure_ascii=False).encode("utf-8"))


def build_dashscope_native(provider: dict, wav: bytes, language: str, context: str) -> AsrRequest:
    messages = []
    if context:
        messages.append({"role": "system", "content": [{"text": context}]})
    messages.append({"role": "user", "content": [{"audio": _data_uri(wav)}]})
    body: dict = {"model": provider["model"], "input": {"messages": messages}, "parameters": {}}
    if language:
        body["parameters"]["asr_options"] = {"language": language}
    _merge(body, _extra(provider))
    url = provider["base_url"].rstrip("/") + "/services/aigc/multimodal-generation/generation"
    headers = {"Content-Type": "application/json", **_auth(provider)}
    return AsrRequest(url, headers, json.dumps(body, ensure_ascii=False).encode("utf-8"))


def build_openai_transcriptions(provider: dict, wav: bytes, language: str, context: str) -> AsrRequest:
    fields = {"model": provider["model"], "response_format": "json"}
    if language:
        fields["language"] = language
    if context:
        fields["prompt"] = context
    for k, v in _extra(provider).items():
        fields[k] = v if isinstance(v, str) else json.dumps(v)
    boundary = "vtt-" + uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio.wav"\r\n'
        f"Content-Type: audio/wav\r\n\r\n".encode() + wav + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    url = provider["base_url"].rstrip("/") + "/audio/transcriptions"
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}", **_auth(provider)}
    return AsrRequest(url, headers, b"".join(parts))


# ---------- response parsers ----------

def _text_of(content) -> str:
    """content may be a string or a list of {text}/{type:text,text} parts."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return ""


def parse_openai_chat_audio(data: dict) -> str:
    return _text_of(data["choices"][0]["message"]["content"])


def parse_dashscope_native(data: dict) -> str:
    return _text_of(data["output"]["choices"][0]["message"]["content"])


def parse_openai_transcriptions(data: dict) -> str:
    return data["text"]


BUILDERS = {
    "openai_chat_audio": (build_openai_chat_audio, parse_openai_chat_audio),
    "dashscope_native": (build_dashscope_native, parse_dashscope_native),
    "openai_transcriptions": (build_openai_transcriptions, parse_openai_transcriptions),
}


# ---------- HTTP ----------

_STATUS_REASONS = {
    400: "请求被服务端拒绝",
    401: "API Key 无效或未填写",
    403: "没有权限（检查 Key 权限、模型是否已开通、账户余额）",
    404: "接口地址或模型名不存在（检查地址、模型名、接口类型）",
    413: "音频太大，请缩短单次录音",
    429: "请求太频繁或额度不足",
}


def _server_message(body: str) -> str:
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return body[:200]
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict):
            return str(err.get("message") or err.get("code") or "")
        if isinstance(err, str):
            return err
        return str(data.get("message") or data.get("code") or "")
    return ""


def transcribe(provider: dict, wav: bytes, language: str = "", context: str = "",
               timeout: float = 30, allow_empty: bool = False) -> str:
    protocol = provider.get("protocol")
    if protocol not in BUILDERS:
        raise StageError(Stage.CONFIG, f"未知的接口类型：{protocol}")
    for field in ("base_url", "model"):
        if not (provider.get(field) or "").strip():
            raise StageError(Stage.CONFIG, f"识别服务缺少「{'接口地址' if field == 'base_url' else '模型'}」")
    build, parse = BUILDERS[protocol]
    req = build(provider, wav, language, context)
    t0 = time.monotonic()
    log.info("asr: POST %s model=%s protocol=%s audio=%d bytes", req.url, provider["model"],
             protocol, len(wav))
    http_req = urllib.request.Request(req.url, data=req.body, headers=req.headers, method="POST")
    try:
        with urllib.request.urlopen(http_req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        msg = _server_message(body)
        reason = _STATUS_REASONS.get(e.code, "服务端错误" if e.code >= 500 else "请求失败")
        detail = redact(f"HTTP {e.code} {req.url}\n{body[:800]}")
        log.warning("asr: %s", detail)
        raise StageError(Stage.ASR, f"HTTP {e.code} {reason}" + (f"：{redact(msg)}" if msg else ""), detail)
    except (socket.timeout, TimeoutError):
        raise StageError(Stage.ASR, f"请求超时（{timeout:.0f} 秒没有响应）", req.url)
    except urllib.error.URLError as e:
        reason = e.reason
        if isinstance(reason, (socket.timeout, TimeoutError)):
            raise StageError(Stage.ASR, f"请求超时（{timeout:.0f} 秒没有响应）", req.url)
        raise StageError(Stage.ASR, "无法连接识别服务（检查网络和接口地址）", redact(f"{req.url}\n{reason}"))
    elapsed = (time.monotonic() - t0) * 1000
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        if protocol == "openai_transcriptions" and raw.strip():
            return raw.strip()  # some servers answer plain text
        raise StageError(Stage.ASR, "返回内容不是 JSON（接口类型可能选错了）", redact(raw[:800]))
    try:
        text = parse(data)
    except (KeyError, IndexError, TypeError):
        raise StageError(Stage.ASR, "返回格式无法识别（接口类型可能选错了）", redact(raw[:800]))
    text = (text or "").strip()
    log.info("asr: ok in %.0f ms, %d chars", elapsed, len(text))
    if not text and not allow_empty:
        raise StageError(Stage.ASR, "识别结果为空（可能没说话或声音太小）")
    return text
