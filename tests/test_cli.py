import json, subprocess, sys, unittest
from pathlib import Path
import helpers  # noqa
ROOT = Path(__file__).parent.parent


def run(*a):
    return subprocess.run([sys.executable, str(ROOT / "cli.py"), *a], capture_output=True, text=True, cwd=ROOT)


class T(unittest.TestCase):
    def test_check_pass(self):
        r = run("check", "--bundle", "logs-001", "--strategy", "dedup", "--min-recall", "0.99")
        self.assertEqual(r.returncode, 0, r.stdout); self.assertEqual(json.loads(r.stdout)["verdict"], "pass")
    def test_check_breach(self):
        r = run("check", "--bundle", "logs-001", "--strategy", "head_tail", "--min-recall", "0.99")
        self.assertEqual(r.returncode, 1, r.stdout)
    def test_check_error(self):
        r = run("check", "--bundle", "nope", "--strategy", "dedup")
        self.assertEqual(r.returncode, 2)
    def test_measure_and_compare(self):
        self.assertEqual(run("measure", "--bundle", "rag-001", "--strategy", "dedup").returncode, 0)
        self.assertEqual(run("compare").returncode, 0)
        self.assertEqual(run("report").returncode, 0)
        self.assertEqual(run("generate").returncode, 0)


if __name__ == "__main__": unittest.main()
