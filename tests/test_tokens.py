import unittest
import helpers  # noqa
from tokens import estimate_tokens


class T(unittest.TestCase):
    def test_empty(self): self.assertEqual(estimate_tokens(""), 0)
    def test_one_word(self): self.assertEqual(estimate_tokens("hello"), 2)  # ceil(1.3)
    def test_ten_words(self): self.assertEqual(estimate_tokens(" ".join(["w"] * 10)), 13)
    def test_deterministic(self): self.assertEqual(estimate_tokens("a b c"), estimate_tokens("a b c"))


if __name__ == "__main__": unittest.main()
