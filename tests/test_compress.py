import json, unittest
import helpers  # noqa
from compress import dedup, head_tail, json_prune, tfidf


class T(unittest.TestCase):
    def test_dedup_keeps_latest(self):
        text = "alpha beta gamma delta value is 1 today now\n" + "filler unique sentence here xyz\n" + "alpha beta gamma delta value is 2 today now"
        out = dedup(text, threshold=0.3)
        self.assertIn("value is 2", out); self.assertNotIn("value is 1", out)
    def test_dedup_removes_repeats(self):
        self.assertEqual(dedup("same line here\nsame line here\nsame line here"), "same line here")
    def test_head_tail_saves(self):
        text = "\n".join(f"line {i} unique{i}" for i in range(100))
        self.assertLess(len(head_tail(text).splitlines()), 100)
    def test_tfidf_reduces(self):
        text = "\n".join(f"sentence number {i} about topic {i % 3} words here" for i in range(20))
        self.assertLess(len(tfidf(text).splitlines()), 20)
    def test_tfidf_query_differs_or_equal(self):
        text = "\n".join([f"cats and dogs topic {i}" for i in range(10)] + ["quantum payment gateway timeout special"])
        out = tfidf(text, query="payment gateway")
        self.assertIsInstance(out, str)
    def test_json_prune(self):
        obj = {"keep": "yes", "debug_notes": "no", "nested": {"trace_id": "x", "v": 1}}
        out = json.loads(json_prune(json.dumps(obj)))
        self.assertNotIn("debug_notes", out); self.assertNotIn("trace_id", out["nested"]); self.assertEqual(out["keep"], "yes")
    def test_json_prune_non_json_noop(self):
        self.assertEqual(json_prune("plain text"), "plain text")


if __name__ == "__main__": unittest.main()
