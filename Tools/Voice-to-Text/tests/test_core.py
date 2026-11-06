"""A few checks of pure logic (no microphone, network or X11 needed).

Run: python -B -m unittest discover -s tests
"""

import json
import os
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from voice_to_text import asr  # noqa: E402
from voice_to_text import plugins as pg  # noqa: E402
from voice_to_text import polish as pl  # noqa: E402
from voice_to_text.errors import StageError  # noqa: E402
from voice_to_text.audio import wav_bytes  # noqa: E402
from voice_to_text.log import redact, register_secret  # noqa: E402
from voice_to_text.postprocess import clean  # noqa: E402

PROVIDER = {"model": "m", "base_url": "https://example.com/v1/", "api_key": "sk-secret123456",
            "extra_json": '{"asr_options": {"enable_itn": true}}'}


class RedactTest(unittest.TestCase):
    def test_masks_key_bearer_and_audio(self):
        register_secret("my-private-key-xyz")
        text = redact('key=my-private-key-xyz Authorization: Bearer abc.def sk-abcdefgh '
                      '"data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEA"')
        self.assertNotIn("my-private-key-xyz", text)
        self.assertNotIn("abc.def", text)
        self.assertNotIn("sk-abcdefgh", text)
        self.assertNotIn("UklGRiQAAABX", text)


class RequestTest(unittest.TestCase):
    wav = wav_bytes(b"\0\0" * 160)

    def test_chat_audio_body(self):
        req = asr.build_openai_chat_audio(PROVIDER, self.wav, "zh", "Claude, Codex")
        body = json.loads(req.body)
        self.assertEqual(req.url, "https://example.com/v1/chat/completions")
        self.assertEqual(req.headers["Authorization"], "Bearer sk-secret123456")
        self.assertEqual(body["messages"][0]["role"], "system")
        audio = body["messages"][1]["content"][0]["input_audio"]["data"]
        self.assertTrue(audio.startswith("data:audio/wav;base64,"))
        # extra_json is merged, not overwritten
        self.assertEqual(body["asr_options"], {"language": "zh", "enable_itn": True})

    def test_transcriptions_multipart(self):
        req = asr.build_openai_transcriptions(PROVIDER, self.wav, "", "Claude")
        self.assertTrue(req.url.endswith("/audio/transcriptions"))
        self.assertIn(b'name="prompt"\r\n\r\nClaude', req.body)
        self.assertIn(b'filename="audio.wav"', req.body)

    def test_parsers(self):
        self.assertEqual(asr.parse_openai_chat_audio(
            {"choices": [{"message": {"content": "你好 Claude"}}]}), "你好 Claude")
        self.assertEqual(asr.parse_openai_chat_audio(
            {"choices": [{"message": {"content": [{"type": "text", "text": "a"}, {"text": "b"}]}}]}), "ab")
        self.assertEqual(asr.parse_dashscope_native(
            {"output": {"choices": [{"message": {"content": [{"text": "打开 Codex"}]}}]}}), "打开 Codex")
        self.assertEqual(asr.parse_openai_transcriptions({"text": "hi"}), "hi")


class CleanTest(unittest.TestCase):
    def test_newlines_rules_period(self):
        out = clean(" 打开 cloud code\n看一下。 ", "cloud code => Claude Code", strip_trailing_period=True)
        self.assertEqual(out, "打开 Claude Code 看一下")


POLISH = {"polish_reuse_provider": False, "polish_base_url": "https://text.example.com/v1",
          "polish_api_key": "sk-polish", "polish_model": "small", "polish_prompt": "",
          "polish_extra_json": '{"enable_thinking": false}'}


class PolishTest(unittest.TestCase):
    def test_resolve_reuse_own_and_native(self):
        chat = {**PROVIDER, "protocol": "openai_chat_audio"}
        s = pl.resolve_service({**POLISH, "polish_reuse_provider": True}, chat)
        self.assertEqual((s["base_url"], s["api_key"], s["model"]), ("https://example.com/v1/", "sk-secret123456", "small"))
        self.assertEqual(s["prompt"], pl.DEFAULT_PROMPT)  # "" means the built-in prompt
        s = pl.resolve_service({**POLISH, "polish_prompt": "只删重复"}, chat)
        self.assertEqual((s["base_url"], s["api_key"], s["prompt"]), ("https://text.example.com/v1", "sk-polish", "只删重复"))
        with self.assertRaises(StageError):
            pl.resolve_service({**POLISH, "polish_reuse_provider": True}, {**PROVIDER, "protocol": "dashscope_native"})
        with self.assertRaises(StageError):
            pl.resolve_service({**POLISH, "polish_model": " "}, chat)

    def test_request_body(self):
        req = pl.build_request(pl.resolve_service(POLISH, None), "那个帮我看看", "Claude Code")
        body = json.loads(req.body)
        self.assertEqual(req.url, "https://text.example.com/v1/chat/completions")
        self.assertEqual(req.headers["Authorization"], "Bearer sk-polish")
        self.assertEqual(body["model"], "small")
        self.assertEqual(body["messages"][0], {"role": "system", "content": pl.DEFAULT_PROMPT})
        self.assertIn("Claude Code", body["messages"][1]["content"])
        self.assertTrue(body["messages"][1]["content"].endswith("<原话>那个帮我看看</原话>"))
        self.assertIs(body["enable_thinking"], False)  # extra_json merged

    def test_accept(self):
        raw = "嗯那个就是帮我帮我看一下这个这个 bug"
        self.assertEqual(pl.accept(raw, "帮我看一下这个 bug"), "帮我看一下这个 bug")
        self.assertEqual(pl.accept(raw, "<think>想一想</think>\n“<原话>帮我看一下\n这个 bug</原话>”"),
                         "帮我看一下 这个 bug")
        self.assertIsNone(pl.accept(raw, "  "))
        self.assertIsNone(pl.accept("写个函数", "好的，下面是一个计算斐波那契数列的 Python 函数：def fib(n): ..."))


class PluginTest(unittest.TestCase):
    def test_parse(self):
        rules, errors = pg.parse("# 注释\n\n嗯+ =>\n， => \", \"\n没有箭头\n( => x\na => \\q\n(b) => [\\g<1>]")
        self.assertEqual([r.line for r in rules], [3, 4, 8])
        self.assertEqual(rules[0].repl, "")  # empty replacement deletes
        self.assertEqual(rules[1].repl, ", ")  # quotes keep the spaces
        self.assertEqual([e.split("：")[0] for e in errors], ["第 5 行", "第 6 行", "第 7 行"])
        out = pg.apply("嗯嗯好，abc\n", [pg.Plugin("t", Path("t"), rules)])
        self.assertEqual(out, "好, a[b]c")

    def test_builtin_halfwidth(self):
        rules, errors = pg.parse(pg.BUILTIN["标点半角"])
        self.assertEqual(errors, [])
        out = pg.apply("嗯，对。你看一下「设置」页面（第二个）里的选项？好的！比如：A、B；C……", [pg.Plugin("p", Path("p"), rules)])
        self.assertEqual(out, '嗯,对.你看一下"设置"页面(第二个)里的选项?好的!比如:A,B;C...')
        self.assertIsNone(re.search(r"[，。？！：；、（）“”「」…]", out))

    def test_plugin_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "plugins"
            ps = pg.PluginSet(d)
            ps.ensure_builtin()
            (d / "0-口头禅.rules").write_text("那个 =>\n", encoding="utf-8")
            self.assertEqual([p.name for p in ps.all()], ["0-口头禅", "标点半角"])  # file-name order
            self.assertEqual(ps.apply("那个，好", []), "那个，好")  # nothing enabled
            self.assertEqual(ps.apply("那个，好", ["0-口头禅", "标点半角"]), ",好")
            f = d / "0-口头禅.rules"
            f.write_text("那个 => 这个\n", encoding="utf-8")
            os.utime(f, (time.time() + 5, time.time() + 5))  # edited file is read again
            self.assertEqual(ps.apply("那个", ["0-口头禅"]), "这个")
            (d / "标点半角.rules").unlink()
            ps.ensure_builtin()  # folder exists: a deleted built-in stays deleted
            self.assertEqual([p.name for p in ps.all()], ["0-口头禅"])


if __name__ == "__main__":
    unittest.main()
