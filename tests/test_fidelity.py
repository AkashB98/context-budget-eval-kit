import unittest
import helpers  # noqa
from fidelity import planted_fact_recall
from corpus import generate_corpus
from measure import measure_bundle


class T(unittest.TestCase):
    def test_recall_all(self):
        facts = [{"id": "a", "needle": "x"}]
        self.assertEqual(planted_fact_recall(facts, "x here")["recall"], 1.0)
    def test_recall_none(self):
        facts = [{"id": "a", "needle": "x"}]
        self.assertEqual(planted_fact_recall(facts, "no")["recall"], 0.0)
    def test_dedup_logs_full_recall_and_stale_absent(self):
        logs = generate_corpus()[0]
        r = measure_bundle(logs, "dedup")
        self.assertEqual(r["recall"], 1.0); self.assertTrue(r["stale_absent"])
    def test_head_tail_loses_facts(self):
        logs = generate_corpus()[0]
        self.assertLess(measure_bundle(logs, "head_tail")["recall"], 1.0)


if __name__ == "__main__": unittest.main()
