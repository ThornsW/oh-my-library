import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

import check_airport
from core.envfile import load_env_file, parse_env_file


def _fail(*_a, **_k):
    raise AssertionError("should not be called")


class _Stop(Exception):
    pass


class TestEnvFile(unittest.TestCase):
    def _write(self, text):
        fd, path = tempfile.mkstemp(suffix=".env")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        self.addCleanup(os.remove, path)
        return path

    def test_parses_quotes_export_comments_and_keeps_hash_in_value(self):
        path = self._write("# comment\n\nexport A='x y'\nB=\"q\"\nC=https://example.com/s?t=1#frag\nbad line\n")
        self.assertEqual(parse_env_file(path),
                         {"A": "x y", "B": "q", "C": "https://example.com/s?t=1#frag"})

    def test_missing_file_is_empty(self):
        self.assertEqual(parse_env_file("/nonexistent/.env"), {})

    def test_existing_variables_win(self):
        path = self._write("IPPURE_SUB_URL=https://example.com/from-file\n")
        env = {"IPPURE_SUB_URL": "https://example.com/from-env"}
        load_env_file(path, env)
        self.assertEqual(env["IPPURE_SUB_URL"], "https://example.com/from-env")


class TestResolveSubUrl(unittest.TestCase):
    def test_cli_beats_environment(self):
        env = {"IPPURE_SUB_URL": "https://example.com/env"}
        self.assertEqual(check_airport.resolve_sub_url("https://example.com/cli", env, _fail),
                         "https://example.com/cli")

    def test_environment_then_prompt(self):
        env = {"IPPURE_SUB_URL": " https://example.com/env "}
        self.assertEqual(check_airport.resolve_sub_url(None, env, _fail), "https://example.com/env")
        self.assertEqual(check_airport.resolve_sub_url(None, {}, lambda _p: "https://example.com/typed"),
                         "https://example.com/typed")

    def test_dotenv_fills_missing_environment(self):
        fd, path = tempfile.mkstemp(suffix=".env")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("IPPURE_SUB_URL=https://example.com/dotenv\n")
        self.addCleanup(os.remove, path)
        env = {}
        load_env_file(path, env)
        self.assertEqual(check_airport.resolve_sub_url(None, env, _fail), "https://example.com/dotenv")

    def test_empty_input_exits(self):
        with self.assertRaises(SystemExit):
            check_airport.resolve_sub_url(None, {}, lambda _p: "  ")


class TestResolveBinary(unittest.TestCase):
    def test_local_binary_skips_download(self):
        with tempfile.NamedTemporaryFile() as f:
            self.assertEqual(check_airport.resolve_binary(f.name, "/unused", _fail), f.name)

    def test_missing_local_binary_exits(self):
        with self.assertRaises(SystemExit):
            check_airport.resolve_binary("/nonexistent/mihomo", "/unused", _fail)

    def test_no_path_downloads(self):
        self.assertEqual(check_airport.resolve_binary(None, "/bin-dir", lambda d: d + "/mihomo"),
                         "/bin-dir/mihomo")


class TestConfirmProxyOff(unittest.TestCase):
    def test_yes_does_not_wait(self):
        with redirect_stdout(io.StringIO()):
            check_airport.confirm_proxy_off(True, ask=_fail)

    def test_default_waits_for_enter(self):
        calls = []
        with redirect_stdout(io.StringIO()):
            check_airport.confirm_proxy_off(False, ask=calls.append)
        self.assertEqual(len(calls), 1)


class TestMain(unittest.TestCase):
    def setUp(self):
        for target in ("check_airport.ensure_mihomo", "check_airport.os.makedirs",
                       "urllib.request.urlopen"):
            p = mock.patch(target, side_effect=AssertionError(f"{target} must not be called"))
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(check_airport, "ENV_PATH", "/nonexistent/.env")
        p.start()
        self.addCleanup(p.stop)

    def test_version_and_help_have_no_side_effects(self):
        for argv, expected in ((["--version"], check_airport.__version__), (["--help"], "--mihomo")):
            out = io.StringIO()
            with self.assertRaises(SystemExit) as cm, redirect_stdout(out), redirect_stderr(out):
                check_airport.main(argv)
            self.assertEqual(cm.exception.code, 0)
            self.assertIn(expected, out.getvalue())

    def test_mihomo_env_sets_default(self):
        with mock.patch.dict(os.environ, {"MIHOMO_BIN": "/opt/mihomo"}):
            self.assertEqual(check_airport.build_parser().parse_args([]).mihomo, "/opt/mihomo")

    def test_ua_and_local_binary_reach_config(self):
        seen = {}

        def fake_build_config(sub_url, mixed_port, ctrl_port, secret, user_agent="mihomo"):
            seen.update(sub_url=sub_url, user_agent=user_agent)
            raise _Stop

        with tempfile.NamedTemporaryFile() as binary, \
                mock.patch("check_airport.os.makedirs"), \
                mock.patch("check_airport.build_config", side_effect=fake_build_config), \
                redirect_stdout(io.StringIO()):
            with self.assertRaises(_Stop):
                check_airport.main(["https://example.com/sub", "--ua", "clash.meta",
                                    "--mihomo", binary.name])
        self.assertEqual(seen, {"sub_url": "https://example.com/sub", "user_agent": "clash.meta"})


if __name__ == "__main__":
    unittest.main()
