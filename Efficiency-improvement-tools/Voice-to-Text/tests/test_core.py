"""A few checks of pure logic (no microphone, network or X11 needed).

Run: python -B -m unittest discover -s tests
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from voice_to_text import asr  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
