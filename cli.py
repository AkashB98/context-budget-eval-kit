"""CLI: generate/measure/compare/report/check/demo/serve.

check = FIDELITY gate only: exit 0 pass / 1 fidelity breach / 2 data error.
check emits a JSON summary eval-cost-budget-gate could read. Fields:
  bundle_id (str), content_type (str), strategy (str),
  original_tokens (int), compressed_tokens (int), savings_pct (float),
  recall (float, planted-fact recall 0..1), facts_total (int),
  facts_kept (int), min_recall (float), passed (bool), verdict ("pass"|"fail")
"""
import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

from compress import STRATEGY_NAMES
from corpus import generate_corpus, get_bundle
from measure import compare_all, full_report, measure_bundle

EXIT_OK, EXIT_BREACH, EXIT_ERROR = 0, 1, 2


def _bundle(args):
    if getattr(args, "bundle", None):
        return get_bundle(args.bundle)
    return generate_corpus()[0]


def cmd_generate(args):
    bundles = generate_corpus()
    out = [{"bundle_id": b["bundle_id"], "content_type": b["content_type"],
            "tokens_hint": len(b["text"].split()), "facts": b["facts"], "query": b["query"]} for b in bundles]
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


def cmd_measure(args):
    try:
        b = _bundle(args)
    except Exception as exc:
        print(f"measure: {exc}"); return EXIT_ERROR
    print(json.dumps(measure_bundle(b, args.strategy), indent=2, sort_keys=True))
    return 0


def cmd_compare(args):
    rows = compare_all(generate_corpus())
    print(f"{'content':<8}{'strategy':<14}{'savings%':>10}{'recall':>8}")
    for r in rows:
        print(f"{r['content_type']:<8}{r['strategy']:<14}{r['savings_pct']:>10}{r['recall']:>8}")
    return 0


def cmd_report(args):
    print(json.dumps(full_report(generate_corpus()), indent=2, sort_keys=True))
    return 0


def check_summary(bundle, strategy, min_recall):
    r = measure_bundle(bundle, strategy)
    passed = r["recall"] >= min_recall
    return {**r, "min_recall": min_recall, "passed": passed, "verdict": "pass" if passed else "fail"}


def cmd_check(args):
    try:
        b = _bundle(args)
        if args.strategy not in STRATEGY_NAMES:
            raise ValueError("unknown strategy")
    except Exception as exc:
        print(json.dumps({"error": str(exc), "verdict": "error"}, sort_keys=True))
        return EXIT_ERROR
    s = check_summary(b, args.strategy, args.min_recall)
    print(json.dumps(s, indent=2, sort_keys=True))
    return EXIT_OK if s["passed"] else EXIT_BREACH


def cmd_demo(args):
    import demo
    return demo.main()


def make_server(port):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _send(self, payload, code=200):
            body = json.dumps(payload, sort_keys=True).encode()
            self.send_response(code); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        def do_GET(self):
            if self.path == "/health": self._send({"status": "ok"})
            elif self.path == "/report": self._send(full_report(generate_corpus()))
            else: self._send({"error": "not found"}, 404)
        def do_POST(self):
            if self.path != "/measure": self._send({"error": "not found"}, 404); return
            length = int(self.headers.get("Content-Length", 0))
            try:
                req = json.loads(self.rfile.read(length) or b"{}")
                b = get_bundle(req["bundle_id"]) if "bundle_id" in req else generate_corpus()[0]
                if "text" in req:
                    b = {"bundle_id": req.get("bundle_id", "custom"), "content_type": req.get("content_type", "logs"),
                         "text": req["text"], "facts": req.get("facts", []), "query": req.get("query", "")}
                self._send(measure_bundle(b, req.get("strategy", "dedup")))
            except Exception as exc: self._send({"error": str(exc)}, 400)
    return HTTPServer(("127.0.0.1", port), H)


def cmd_serve(args):
    srv = make_server(args.port)
    print(f"serving on 127.0.0.1:{args.port}")
    srv.serve_forever(); return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="ctxbudget")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("generate").set_defaults(fn=cmd_generate)
    for name, fn in (("measure", cmd_measure), ("check", cmd_check)):
        sp = sub.add_parser(name); sp.add_argument("--bundle", default=None); sp.add_argument("--strategy", default="dedup")
        if name == "check": sp.add_argument("--min-recall", type=float, default=0.99)
        sp.set_defaults(fn=fn)
    sub.add_parser("compare").set_defaults(fn=cmd_compare)
    sub.add_parser("report").set_defaults(fn=cmd_report)
    sub.add_parser("demo").set_defaults(fn=cmd_demo)
    sp = sub.add_parser("serve"); sp.add_argument("--port", type=int, default=8765); sp.set_defaults(fn=cmd_serve)
    a = p.parse_args(argv); return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
