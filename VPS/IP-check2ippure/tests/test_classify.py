import unittest
from core.classify import NodeResult, is_datacenter, from_ippure_json


class TestClassify(unittest.TestCase):
    def test_is_datacenter_true_for_vultr(self):
        self.assertTrue(is_datacenter(False, "Vultr Holdings, LLC"))

    def test_is_datacenter_false_when_residential(self):
        self.assertFalse(is_datacenter(True, "Comcast Cable"))

    def test_is_datacenter_false_for_unknown_org(self):
        self.assertFalse(is_datacenter(False, "Some Local ISP"))

    def test_from_ippure_json_maps_fields(self):
        data = {
            "ip": "203.0.113.10", "asn": 20473, "asOrganization": "Vultr Holdings, LLC",
            "country": "United States", "countryCode": "US", "city": "Santa Clara",
            "fraudScore": 43, "isResidential": False,
        }
        r = from_ippure_json("HK-01", data, delay_ms=120)
        self.assertEqual(r.name, "HK-01")
        self.assertEqual(r.status, "ok")
        self.assertEqual(r.ip, "203.0.113.10")
        self.assertEqual(r.asn, 20473)
        self.assertEqual(r.org, "Vultr Holdings, LLC")
        self.assertEqual(r.country_code, "US")
        self.assertEqual(r.fraud_score, 43)
        self.assertFalse(r.is_residential)
        self.assertEqual(r.delay_ms, 120)

    def test_from_ippure_json_tolerates_missing_keys(self):
        r = from_ippure_json("X", {}, delay_ms=None)
        self.assertEqual(r.status, "ok")
        self.assertEqual(r.ip, "")
        self.assertIsNone(r.asn)
        self.assertIsNone(r.fraud_score)


if __name__ == "__main__":
    unittest.main()
