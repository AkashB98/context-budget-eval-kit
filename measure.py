"""Measure one bundle x strategy, and full comparison tables."""
from compress import STRATEGY_NAMES, compress
from fidelity import planted_fact_recall
from tokens import estimate_tokens


def measure_bundle(bundle, strategy):
    comp = compress(bundle["text"], strategy, query=bundle.get("query"))
    orig_t = estimate_tokens(bundle["text"])
    comp_t = estimate_tokens(comp)
    savings = round((1 - comp_t / orig_t) * 100, 2) if orig_t else 0.0
    fid = planted_fact_recall(bundle["facts"], comp)
    # dedup stale check: stale needle must be absent for dedup to be correct
    stale_absent = None
    for f in bundle["facts"]:
        if f.get("expect_absent_after_dedup"):
            stale_absent = f["needle"] not in comp
    return {
        "bundle_id": bundle["bundle_id"], "content_type": bundle["content_type"],
        "strategy": strategy, "original_tokens": orig_t, "compressed_tokens": comp_t,
        "savings_pct": savings, "recall": fid["recall"], "facts_total": fid["facts_total"],
        "facts_kept": fid["facts_kept"], "kept_ids": fid["kept_ids"], "missed_ids": fid["missed_ids"],
        "stale_absent": stale_absent,
    }


def compare_all(bundles):
    rows = []
    for b in bundles:
        for s in STRATEGY_NAMES:
            rows.append(measure_bundle(b, s))
    return rows


def full_report(bundles):
    rows = compare_all(bundles)
    return {"bundles": [b["bundle_id"] for b in bundles], "strategies": STRATEGY_NAMES, "rows": rows}
