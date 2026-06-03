import os
import stat
import tempfile
import unittest
from core.binary import pick_asset, sha256_file, ensure_mihomo


class TestBinary(unittest.TestCase):
    def test_pick_asset_prefers_compatible(self):
        assets = [
            {"name": "mihomo-linux-amd64-v1.19.0.gz", "browser_download_url": "u1"},
            {"name": "mihomo-linux-amd64-compatible-v1.19.0.gz", "browser_download_url": "u2"},
            {"name": "mihomo-linux-arm64-v1.19.0.gz", "browser_download_url": "u3"},
        ]
        self.assertEqual(pick_asset(assets)["browser_download_url"], "u2")

    def test_pick_asset_falls_back_to_plain_amd64(self):
        assets = [{"name": "mihomo-linux-amd64-v1.19.0.gz", "browser_download_url": "u1"}]
        self.assertEqual(pick_asset(assets)["browser_download_url"], "u1")

    def test_pick_asset_raises_when_none(self):
        with self.assertRaises(RuntimeError):
            pick_asset([{"name": "mihomo-windows-amd64.zip", "browser_download_url": "u"}])

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
        with tempfile.TemporaryDirectory() as d:
            bin_path = os.path.join(d, "mihomo")
            with open(bin_path, "wb") as f:
                f.write(b"fake-binary")
            os.chmod(bin_path, os.stat(bin_path).st_mode | stat.S_IEXEC)
            with open(bin_path + ".sha256", "w") as f:
                f.write(sha256_file(bin_path))
            self.assertEqual(ensure_mihomo(d), bin_path)


if __name__ == "__main__":
    unittest.main()
