"""End-to-end demo incl. serve round-trip. Stdlib only, offline."""
import json, os, sys, threading, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cli import check_summary, make_server
from corpus import generate_corpus
from measure import compare_all, measure_bundle


def _req(port, path, payload=None, method="GET"):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status, json.loads(r.read())


def main():
    bundles = generate_corpus()
    assert bundles == generate_corpus(), "deterministic"
    print(f"1. corpus: {len(bundles)} bundles {[b['content_type'] for b in bundles]}")
    rows = compare_all(bundles)
    for r in rows:
        print(f"   {r['content_type']:<6} {r['strategy']:<12} savings={r['savings_pct']}% recall={r['recall']}")
    logs = [b for b in bundles if b["content_type"] == "logs"][0]
    d = measure_bundle(logs, "dedup")
    assert d["recall"] == 1.0, d
    print(f"2. dedup on logs: recall={d['recall']} savings={d['savings_pct']}% stale_absent={d['stale_absent']}")
    s = check_summary(logs, "dedup", 0.99)
    assert s["passed"] and s["verdict"] == "pass"
    print("3. check gate (dedup/logs, min_recall=0.99): PASS exit 0")
    server = make_server(0); port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        st, health = _req(port, "/health"); assert health == {"status": "ok"}
        st, served = _req(port, "/measure", payload={"bundle_id": "logs-001", "strategy": "dedup"}, method="POST")
        assert served == json.loads(json.dumps(d, sort_keys=True)), (served, d)
        st, report = _req(port, "/report"); assert len(report["rows"]) == len(rows)
        print("4. serve round-trip: POST /measure matches local, GET /report + /health ok")
    finally:
        server.shutdown(); server.server_close()
    print("demo: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
