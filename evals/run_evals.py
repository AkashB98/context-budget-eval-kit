"""Golden evals. Deterministic; run 3x, md5 must match."""
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from corpus import generate_corpus  # noqa
from measure import compare_all, measure_bundle  # noqa
from tokens import estimate_tokens  # noqa
RESULTS = []
def check(name, ok, detail=""):
    RESULTS.append({"eval": name, "pass": bool(ok), "detail": detail})

def main():
    bundles = generate_corpus()
    by = {(r["content_type"], r["strategy"]): r for r in compare_all(bundles)}
    check("E1_corpus_shape", len(bundles) == 3 and [b["content_type"] for b in bundles] == ["logs", "json", "rag"])
    check("E2_token_estimator", estimate_tokens(" ".join(["w"] * 10)) == 13 and estimate_tokens("") == 0)
    check("E3_logs_dedup_headline", by[("logs", "dedup")]["savings_pct"] == 95.38 and by[("logs", "dedup")]["recall"] == 1.0, f"{by[('logs','dedup')]}")
    check("E4_rag_dedup_headline", by[("rag", "dedup")]["savings_pct"] == 78.88 and by[("rag", "dedup")]["recall"] == 1.0)
    check("E5_json_prune_headline", by[("json", "json_prune")]["savings_pct"] == 64.02 and by[("json", "json_prune")]["recall"] == 0.75)
    check("E6_head_tail_loses_facts", by[("logs", "head_tail")]["recall"] == 0.3333 and by[("json", "head_tail")]["recall"] == 0.25)
    check("E7_tfidf_json_loses_facts", by[("json", "tfidf")]["recall"] == 0.5 and by[("json", "tfidf_query")]["recall"] == 0.75)
    check("E8_tfidf_logs_rag_recall", by[("logs", "tfidf")]["recall"] == 1.0 and by[("rag", "tfidf")]["recall"] == 1.0)
    check("E9_dedup_stale_absent", all(measure_bundle(b, "dedup")["stale_absent"] in (True, None) for b in bundles))
    check("E10_json_prune_noop_non_json", by[("logs", "json_prune")]["savings_pct"] == 0.0 and by[("rag", "json_prune")]["savings_pct"] == 0.0)
    check("E11_determinism", compare_all(generate_corpus()) == compare_all(generate_corpus()))
    with __import__("tempfile").TemporaryDirectory() as td:
        codes = []
        for strat, exp in (("dedup", 0), ("head_tail", 1)):
            r = subprocess.run([sys.executable, str(ROOT / "cli.py"), "check", "--bundle", "logs-001", "--strategy", strat, "--min-recall", "0.99"], capture_output=True, cwd=ROOT)
            codes.append(r.returncode)
        r = subprocess.run([sys.executable, str(ROOT / "cli.py"), "check", "--bundle", "nope", "--strategy", "dedup"], capture_output=True, cwd=ROOT)
        codes.append(r.returncode)
        check("E12_cli_check_exit_codes", tuple(codes) == (0, 1, 2), f"{codes}")
    passed = sum(1 for r in RESULTS if r["pass"])
    out = {"passed": passed, "total": len(RESULTS), "results": RESULTS}
    (ROOT / "evals" / "eval_report.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(f"evals: {passed}/{len(RESULTS)} passed")
    for r in RESULTS: print(("PASS " if r["pass"] else "FAIL ") + r["eval"] + f"  {r['detail']}")
    return 0 if passed == len(RESULTS) else 1

if __name__ == "__main__":
    sys.exit(main())
