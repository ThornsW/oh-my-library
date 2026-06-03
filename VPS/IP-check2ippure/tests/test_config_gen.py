import json
import unittest
from core.config_gen import build_config, dump_config, GROUP_NAME, PROVIDER_NAME


class TestConfigGen(unittest.TestCase):
    def setUp(self):
        self.cfg = build_config(
            sub_url="https://example.com/sub?token=abc",
            mixed_port=17890, ctrl_port=19090, secret="s3cr3t",
            user_agent="clash.meta",
        )

    def test_ports_and_controller(self):
        self.assertEqual(self.cfg["mixed-port"], 17890)
        self.assertEqual(self.cfg["external-controller"], "127.0.0.1:19090")
        self.assertEqual(self.cfg["secret"], "s3cr3t")

    def test_provider_carries_url_and_ua_and_no_healthcheck(self):
        prov = self.cfg["proxy-providers"][PROVIDER_NAME]
        self.assertEqual(prov["type"], "http")
        self.assertEqual(prov["url"], "https://example.com/sub?token=abc")
        self.assertEqual(prov["header"]["User-Agent"], ["clash.meta"])
        self.assertFalse(prov["health-check"]["enable"])

    def test_select_group_uses_provider(self):
        grp = self.cfg["proxy-groups"][0]
        self.assertEqual(grp["name"], GROUP_NAME)
        self.assertEqual(grp["type"], "select")
        self.assertEqual(grp["use"], [PROVIDER_NAME])

    def test_rule_routes_everything_via_group(self):
        self.assertEqual(self.cfg["rules"], [f"MATCH,{GROUP_NAME}"])

    def test_no_geoip_rules(self):
        blob = json.dumps(self.cfg).upper()
        self.assertNotIn("GEOIP", blob)
        self.assertNotIn("GEOSITE", blob)

    def test_dump_config_is_valid_json_hence_valid_yaml(self):
        text = dump_config(self.cfg)
        self.assertEqual(json.loads(text), self.cfg)


if __name__ == "__main__":
    unittest.main()
