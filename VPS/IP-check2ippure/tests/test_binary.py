import gzip
import io
import os
import stat
import tempfile
import unittest
import zipfile
from core.binary import (pick_asset, sha256_file, ensure_mihomo, detect_platform,
                         binary_name, _extract_binary)


class TestBinary(unittest.TestCase):
    def test_pick_asset_prefers_compatible_amd64(self):
        assets = [
            {"name": "mihomo-linux-amd64-v1.19.0.gz", "browser_download_url": "u1"},
            {"name": "mihomo-linux-amd64-compatible-v1.19.0.gz", "browser_download_url": "u2"},
            {"name": "mihomo-linux-arm64-v1.19.0.gz", "browser_download_url": "u3"},
        ]
        self.assertEqual(pick_asset(assets, "linux", "amd64")["browser_download_url"], "u2")

    def test_pick_asset_falls_back_to_plain_amd64(self):
        assets = [{"name": "mihomo-linux-amd64-v1.19.0.gz", "browser_download_url": "u1"}]
        self.assertEqual(pick_asset(assets, "linux", "amd64")["browser_download_url"], "u1")

    def test_pick_asset_arm64_has_no_compatible(self):
        assets = [
            {"name": "mihomo-linux-amd64-compatible-v1.19.0.gz", "browser_download_url": "u1"},
            {"name": "mihomo-linux-arm64-v1.19.0.gz", "browser_download_url": "u2"},
        ]
        self.assertEqual(pick_asset(assets, "linux", "arm64")["browser_download_url"], "u2")

    def test_pick_asset_darwin(self):
        assets = [
            {"name": "mihomo-linux-amd64-compatible-v1.19.0.gz", "browser_download_url": "u1"},
            {"name": "mihomo-darwin-arm64-v1.19.0.gz", "browser_download_url": "u2"},
        ]
        self.assertEqual(pick_asset(assets, "darwin", "arm64")["browser_download_url"], "u2")

    def test_pick_asset_windows_zip(self):
        assets = [
            {"name": "mihomo-windows-amd64-v1.19.0.zip", "browser_download_url": "u1"},
            {"name": "mihomo-windows-amd64-compatible-v1.19.0.zip", "browser_download_url": "u2"},
            {"name": "mihomo-linux-amd64-compatible-v1.19.0.gz", "browser_download_url": "u3"},
        ]
        self.assertEqual(pick_asset(assets, "windows", "amd64")["browser_download_url"], "u2")

    def test_pick_asset_raises_when_no_match(self):
        with self.assertRaises(RuntimeError):
            pick_asset([{"name": "mihomo-freebsd-amd64-v1.0.gz", "browser_download_url": "u"}],
                       "linux", "amd64")

    def test_binary_name(self):
        self.assertEqual(binary_name("windows"), "mihomo.exe")
        self.assertEqual(binary_name("linux"), "mihomo")
        self.assertEqual(binary_name("darwin"), "mihomo")

    def test_extract_binary_gz(self):
        raw = gzip.compress(b"FAKE-ELF-BINARY")
        with tempfile.TemporaryDirectory() as d:
            dest = os.path.join(d, "mihomo")
            _extract_binary(raw, "linux", dest)
            with open(dest, "rb") as f:
                self.assertEqual(f.read(), b"FAKE-ELF-BINARY")

    def test_extract_binary_windows_zip(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("mihomo-windows-amd64-v1.0.exe", b"FAKE-PE-EXE")
        with tempfile.TemporaryDirectory() as d:
            dest = os.path.join(d, "mihomo.exe")
            _extract_binary(buf.getvalue(), "windows", dest)
            with open(dest, "rb") as f:
                self.assertEqual(f.read(), b"FAKE-PE-EXE")

    def test_extract_binary_windows_zip_without_exe_raises(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("readme.txt", b"no exe here")
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError):
                _extract_binary(buf.getvalue(), "windows", os.path.join(d, "mihomo.exe"))

    def test_detect_platform_current_is_supported_or_raises(self):
        try:
            os_tag, arch = detect_platform()
        except RuntimeError:
            return
        self.assertIn(os_tag, ("linux", "darwin", "windows"))
        self.assertIn(arch, ("amd64", "arm64"))

    def test_sha256_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x")
            with open(p, "wb") as f:
                f.write(b"hello")
            self.assertEqual(
                sha256_file(p),
                "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
            )

    def test_ensure_mihomo_short_circuits_when_pinned(self):
        os_tag, _ = detect_platform()
        name = binary_name(os_tag)
        with tempfile.TemporaryDirectory() as d:
            bin_path = os.path.join(d, name)
            with open(bin_path, "wb") as f:
                f.write(b"fake-binary")
            if os.name != "nt":
                os.chmod(bin_path, os.stat(bin_path).st_mode | stat.S_IEXEC)
            with open(bin_path + ".sha256", "w") as f:
                f.write(sha256_file(bin_path))
            self.assertEqual(ensure_mihomo(d), bin_path)


if __name__ == "__main__":
    unittest.main()
