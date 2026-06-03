import unittest
from core.classify import NodeResult
from core.runner import run_checks


class FakeController:
    def __init__(self, members, delays):
        self._members = members
        self._delays = delays
        self.switched = []

    def list_group_members(self):
        return list(self._members)

    def switch(self, node):
        self.switched.append(node)

    def delay(self, node):
        return self._delays.get(node)


class TestRunChecks(unittest.TestCase):
    def test_runs_all_nodes_and_classifies(self):
        members = ["A", "B", "Bad"]
        delays = {"A": 80, "B": 200, "Bad": None}
        table = {
            "A": {"ip": "1.1.1.1", "asn": 4134, "asOrganization": "China Telecom",
                  "countryCode": "HK", "city": "HK", "fraudScore": 10, "isResidential": True},
            "B": {"ip": "2.2.2.2", "asn": 20473, "asOrganization": "Vultr Holdings, LLC",
                  "countryCode": "US", "city": "LA", "fraudScore": 70, "isResidential": False},
            "Bad": "TIMEOUT",
        }

        ctrl = FakeController(members, delays)

        def query(proxy_port, timeout=8):
            node = ctrl.switched[-1]
            if table[node] == "TIMEOUT":
                raise TimeoutError("proxy timeout")
            return table[node]

        results = run_checks(ctrl, query, proxy_port=1234, gap=0, timeout=1)

        self.assertEqual(ctrl.switched, ["A", "B", "Bad"])
        by_name = {r.name: r for r in results}
        self.assertEqual(by_name["A"].status, "ok")
        self.assertEqual(by_name["A"].fraud_score, 10)
        self.assertEqual(by_name["A"].delay_ms, 80)
        self.assertEqual(by_name["Bad"].status, "timeout")
        self.assertTrue(by_name["Bad"].error)


if __name__ == "__main__":
    unittest.main()
