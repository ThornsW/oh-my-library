import csv
import os
import tempfile
import unittest
from core.classify import NodeResult
from core.report import sort_results, render_table, write_csv, write_markdown


def _sample():
    return [
        NodeResult(name="B", status="ok", ip="2.2.2.2", asn=20473, org="Vultr Holdings, LLC",
                   country_code="US", city="LA", fraud_score=70, is_residential=False, delay_ms=200),
        NodeResult(name="A", status="ok", ip="1.1.1.1", asn=4134, org="China Telecom",
                   country_code="HK", city="HK", fraud_score=10, is_residential=True, delay_ms=80),
        NodeResult(name="Dead", status="timeout", error="proxy timeout"),
    ]


class TestReport(unittest.TestCase):
    def test_sort_ok_by_fraud_then_failures_last(self):
        out = sort_results(_sample())
        self.assertEqual([r.name for r in out], ["A", "B", "Dead"])

    def test_render_table_contains_headers_and_rows(self):
        text = render_table(sort_results(_sample()))
        self.assertIn("风险分", text)
        self.assertIn("A", text)
        self.assertIn("Dead", text)
        self.assertIn("timeout", text)

    def test_write_csv_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.csv")
            write_csv(sort_results(_sample()), p)
            with open(p, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(rows[0]["name"], "A")
            self.assertEqual(rows[0]["is_datacenter"], "False")
            self.assertEqual(rows[1]["is_datacenter"], "True")
            self.assertEqual(rows[2]["status"], "timeout")

    def test_write_markdown_has_table(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.md")
            write_markdown(sort_results(_sample()), p, title="测试机场")
            text = open(p, encoding="utf-8").read()
            self.assertIn("测试机场", text)
            self.assertIn("| 风险分 |", text)
            self.assertIn("| A |", text)


if __name__ == "__main__":
    unittest.main()
