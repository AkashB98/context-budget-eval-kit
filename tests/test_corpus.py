import unittest
import helpers  # noqa
from corpus import generate_corpus


class T(unittest.TestCase):
    def test_three_types(self):
        self.assertEqual([b["content_type"] for b in generate_corpus()], ["logs", "json", "rag"])
    def test_deterministic(self): self.assertEqual(generate_corpus(), generate_corpus())
    def test_adversarial_present(self):
        blob = " ".join(b["text"] for b in generate_corpus())
        for needle in ("8473", "KESTREL-19", "cache_ttl_seconds is 900", "cache_ttl_seconds is 300", "ZX-8842", "FALCON-33", "6127", "firmware version is 3.0.0"):
            self.assertIn(needle, blob)
    def test_logs_size(self):
        logs = generate_corpus()[0]
        self.assertEqual(len(logs["text"].splitlines()), 500)


if __name__ == "__main__": unittest.main()
