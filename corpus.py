"""Seeded corpus generation (seed 42, deterministic).

Bundles: logs, tool-output JSON, RAG chunks. Each bundle carries
adversarial planted facts (needles) used ONLY for planted-fact recall.
"""
import json
import random

SEED = 42


def _logs_bundle():
    rng = random.Random(SEED)
    lines = []
    for i in range(500):
        lvl = rng.choice(["INFO", "INFO", "INFO", "DEBUG"])
        lines.append(f"{lvl} worker-3 heartbeat ok latency {10 + (i % 5)}ms queue depth 4 request req-{1000 + (i % 20)} completed in {20 + (i % 7)}ms status ok")
    # Adversarial: number appearing once inside ~500 repetitive lines (index 250)
    lines[250] = "ERROR payment gateway timeout after 8473 ms for txn TXN-991827 status failed"
    # Updated value: early then later (dedup must keep newest, lines near-duplicates)
    lines[100] = "INFO config cache_ttl_seconds is 300 status ok applied to all workers in the cluster today"
    lines[400] = "INFO config cache_ttl_seconds is 900 status ok applied to all workers in the cluster today"
    # Low TF-IDF sentence: all common words except needle
    lines[350] = "the system is on and the status is the same as the other one and the value is KESTREL-19 and it is on"
    text = "\n".join(lines)
    facts = [
        {"id": "log-unique-number", "needle": "8473", "kind": "unique-number-in-repetitive-logs"},
        {"id": "log-updated-value", "needle": "cache_ttl_seconds is 900", "kind": "updated-value-keep-newest"},
        {"id": "log-stale-value", "needle": "cache_ttl_seconds is 300", "kind": "stale-value-should-be-dropped-by-dedup", "expect_absent_after_dedup": True},
        {"id": "log-low-tfidf", "needle": "KESTREL-19", "kind": "low-tfidf-sentence"},
    ]
    return {"bundle_id": "logs-001", "content_type": "logs", "text": text, "facts": facts, "query": "payment gateway timeout cache_ttl_seconds"}


def _json_bundle():
    obj = {
        "tool": "get_order_status",
        "status": "ok",
        "result": {
            "order_id": "ORD-5521",
            "customer": {"name": "Helios Home", "tier": "gold"},
            "detail": {
                "level1": {"level2": {"level3": {"level4": {"secret_code": "ZX-8842"}}}}
            },
            "summary": "order shipped and delivered on time",
        },
        "debug_notes": "verbose debug trace placeholder DEBUGONLY-6611 repeated debug info",
        "trace_id": "trace-abcdef-123456",
        "verbose_log": " ".join(["verbose"] * 60),
        "timestamps": {"created": "2026-01-01T00:00:00Z", "updated": "2026-01-02T00:00:00Z"},
        "empty_field": None,
        "status_code": "STATUS-OK-200",
    }
    text = json.dumps(obj, indent=2, sort_keys=True)
    facts = [
        {"id": "json-deep-key", "needle": "ZX-8842", "kind": "deep-nested-key"},
        {"id": "json-debug-field", "needle": "DEBUGONLY-6611", "kind": "value-in-low-value-field"},
        {"id": "json-status", "needle": "STATUS-OK-200", "kind": "kept-field-value"},
        {"id": "json-order", "needle": "ORD-5521", "kind": "kept-field-value"},
    ]
    return {"bundle_id": "json-001", "content_type": "json", "text": text, "facts": facts, "query": "order status secret_code"}


def _rag_bundle():
    # Repetitive background sentences + distinct chunks
    bg = [
        "The Helios thermostat keeps rooms comfortable throughout the day.",
        "The Helios app shows energy usage for the home each week.",
        "Users can set schedules for heating and cooling in the app.",
        "The support team answers questions about devices and setup.",
    ]
    chunks = []
    for i in range(40):
        chunks.append(bg[i % len(bg)])
    # Low TF-IDF fact: common words only + needle
    chunks[10] = "the system is on and the status is the same as the other one and the code is FALCON-33 and it is on"
    # Unique number fact
    chunks[20] = "The firmware rollout paused after 6127 devices reported a reboot loop."
    # Updated value: two near-duplicate chunks, keep latest
    chunks[5] = "The router firmware version is 2.4.1 for all Helios hubs in the home network setup guide."
    chunks[35] = "The router firmware version is 3.0.0 for all Helios hubs in the home network setup guide."
    text = "\n\n".join(chunks)
    facts = [
        {"id": "rag-low-tfidf", "needle": "FALCON-33", "kind": "low-tfidf-sentence"},
        {"id": "rag-unique-number", "needle": "6127", "kind": "unique-number"},
        {"id": "rag-updated-value", "needle": "firmware version is 3.0.0", "kind": "updated-value-keep-newest"},
        {"id": "rag-stale-value", "needle": "firmware version is 2.4.1", "kind": "stale-value-should-be-dropped-by-dedup", "expect_absent_after_dedup": True},
    ]
    return {"bundle_id": "rag-001", "content_type": "rag", "text": text, "facts": facts, "query": "router firmware version reboot"}


def generate_corpus(seed=SEED):
    if seed != SEED:
        # Only seed 42 corpus is defined deterministically; other seeds reuse it for reproducibility contract
        pass
    return [_logs_bundle(), _json_bundle(), _rag_bundle()]


def get_bundle(bundle_id):
    for b in generate_corpus():
        if b["bundle_id"] == bundle_id:
            return b
    raise KeyError(bundle_id)
