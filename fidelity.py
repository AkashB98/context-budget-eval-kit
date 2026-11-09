"""Fidelity metric = planted-fact recall ONLY."""


def planted_fact_recall(original_facts, compressed_text):
    """Recall = fraction of planted facts whose needle appears in compressed text.

    Facts flagged expect_absent_after_dedup are excluded from recall denominator
    when evaluating dedup specifically; for the generic metric they count like
    others unless caller filters. The headline metric excludes stale-value facts
    (they are superseded, keeping them is not fidelity) — see measure.py.
    """
    scored = [f for f in original_facts if not f.get("expect_absent_after_dedup")]
    if not scored:
        return {"recall": 1.0, "facts_total": 0, "facts_kept": 0, "kept_ids": [], "missed_ids": []}
    kept = [f["id"] for f in scored if f["needle"] in compressed_text]
    missed = [f["id"] for f in scored if f["needle"] not in compressed_text]
    return {"recall": round(len(kept) / len(scored), 4), "facts_total": len(scored),
            "facts_kept": len(kept), "kept_ids": kept, "missed_ids": missed}
