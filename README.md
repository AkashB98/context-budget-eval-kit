# context-budget-eval-kit

**Measure what context compression actually costs you in facts: on seeded bundles, near-duplicate removal saves 95.38% of log tokens at 1.0 planted-fact recall, while head/tail truncation saves ~50% and drops recall to 0.33 — compression is not free, and this kit proves which strategy loses what, per content type.**

Long agent contexts (logs, tool outputs, retrieved chunks) get compressed to fit a **context budget** — the token limit for what a model can read at once. Vendors claim large savings with "no accuracy loss" (context-compression tools in the headroom lineage; knowledge-compilation research reporting ~38% token saving with no accuracy change). This kit is the small, inspectable check on that claim: 4 compression strategies × 3 content types, scored only by **planted-fact recall** — did the facts planted in the original survive compression? Original build, not a clone.

> **Synthetic data only.** Every bundle is generated deterministically (seed 42) for a fictional setting. No real logs, tool outputs, or documents.

Stdlib-only Python. No network, no API keys, no LLM calls. Token estimator, copied exactly from the sibling kits: `ceil(words * 1.3)` where words are whitespace-separated tokens.

How this differs, in one line each:
- vs `eval-cost-budget-gate` — that gates an eval run's *cost/latency* against a budget; this gates a *compressed context's fidelity* (planted-fact recall) against a threshold.
- vs `llm-cost-sidecar` — that records and prices live LLM usage; this measures offline compression trade-offs before any model is called.
- vs `llm-semantic-cache` — that reuses prior answers via semantic matching; this shrinks the context itself and measures what the shrinking destroyed.

## Quickstart

```bash
python3 cli.py generate                      # seeded corpus summary (seed 42)
python3 cli.py measure --bundle logs-001 --strategy dedup
python3 cli.py compare                       # full strategy x content-type table
python3 cli.py report                        # same table as JSON
python3 cli.py check --bundle logs-001 --strategy dedup --min-recall 0.99; echo $?  # 0 pass
python3 cli.py check --bundle logs-001 --strategy head_tail --min-recall 0.99; echo $?  # 1 breach
python3 demo.py                              # end-to-end incl. serve round-trip
python3 cli.py serve --port 8765             # POST /measure, GET /report, GET /health
curl -s localhost:8765/health
curl -s -X POST localhost:8765/measure -d '{"bundle_id":"logs-001","strategy":"dedup"}'
```

## Headline results (actual run, pinned in evals)

Token savings % / planted-fact recall, per strategy × content type:

| Content | dedup | head_tail | tfidf | tfidf_query | json_prune |
|---|---|---|---|---|---|
| logs | 95.38% / 1.0 | 50.03% / 0.3333 | 49.99% / 1.0 | 49.99% / 1.0 | 0.0% / 1.0 |
| json | 6.71% / 1.0 | 24.39% / 0.25 | 64.02% / 0.5 | 69.51% / 0.75 | 64.02% / 0.75 |
| rag | 78.88% / 1.0 | 50.18% / 0.3333 | 47.29% / 1.0 | 47.29% / 1.0 | 0.0% / 1.0 |

**Honest finding:** dedup is essentially free on repetitive logs (95.38% saved, recall 1.0) and strong on repetitive RAG (78.88%, 1.0), because the corpus really is repetitive. Head/tail truncation is the worst trade — it blindly deletes the middle, where the planted facts live. TF-IDF kept every planted fact on logs/RAG in this corpus (rare needles score high on IDF) but lost half the facts on JSON (recall 0.5; query-aware 0.75) — sentence ranking is the wrong tool for structured data (below). JSON pruning saved 64.02% on tool JSON at 0.75 recall: it correctly kept the deep-nested and status values but deleted the fact planted inside the low-value `debug_notes` field — pruning is only as safe as your field list.

## The 4 strategies

1. **Near-duplicate removal (`dedup`)** — word 3-shingle **Jaccard similarity** (overlap of shingle sets ÷ union), threshold 0.5; when two units are near-duplicates the earlier one is dropped, so the **latest version wins** (the updated `cache_ttl_seconds is 900` survives, `300` does not).
2. **Head/tail truncation (`head_tail`)** — keep the first half and last half of the retained 50%; delete the middle.
3. **TF-IDF extractive summarization (`tfidf` / `tfidf_query`)** — score each unit (line/sentence) by length-normalised TF-IDF, keep the top 50% in original order. Run **both** query-agnostic and query-aware (query-term overlap boost) variants.
4. **JSON field pruning (`json_prune`)** — parse tool-output JSON and recursively drop low-value fields (`debug_notes`, `trace_id`, `verbose_log`, `timestamps`, nulls). No-op (0% saving) on non-JSON — honestly reported, not hidden.

**Why sentence-ranking JSON is wrong:** JSON's meaning lives in key paths and nesting, not in sentence-like lines. Splitting pretty-printed JSON into lines and ranking them by TF-IDF can keep a key line and drop its value line (or a closing level), produces output that is no longer valid JSON, and scores a deep-nested value by the rarity of its formatting tokens rather than its importance. Prune by structure (fields), never by sentence score.

## Corpus and adversarial planted facts

Seeded bundles (`fixtures/corpus.json`, seed 42): `logs-001` (500 repetitive log lines), `json-001` (tool-output JSON), `rag-001` (40 RAG chunks). Planted adversarial cases, all required and all present:

- a number appearing **once** inside ~500 repetitive log lines (`8473`)
- a fact in a **low-TF-IDF sentence** (all common words except the needle: `KESTREL-19`, `FALCON-33`)
- a value **updated later** (`cache_ttl_seconds 300 → 900`; firmware `2.4.1 → 3.0.0`) — dedup must keep the newest, and evals assert the stale value is absent after dedup
- a key **nested deep** in tool JSON (`ZX-8842`, four levels down)

Fidelity metric = **planted-fact recall only** (kept needles ÷ planted needles, stale-value facts excluded from the denominator). There is deliberately no second retention metric.

## The `check` gate (for `eval-cost-budget-gate` to read)

`check` is a **fidelity gate only**: exit `0` = recall ≥ `--min-recall`, `1` = fidelity breach, `2` = data error. It prints a JSON summary with fields: `bundle_id`, `content_type`, `strategy`, `original_tokens`, `compressed_tokens`, `savings_pct`, `recall`, `facts_total`, `facts_kept`, `kept_ids`, `missed_ids`, `stale_absent`, `min_recall`, `passed` (bool), `verdict` (`"pass"`/`"fail"`). A downstream cost gate can read `recall`/`passed`/`verdict` exactly as it reads any other run summary.

## Architecture

| Module | Job |
|---|---|
| `tokens.py` | The one estimator: `ceil(words * 1.3)` |
| `corpus.py` | Seeded (42) generation of the 3 bundles + adversarial planted facts |
| `compress.py` | The 4 strategies (5 names: TF-IDF has both variants) |
| `fidelity.py` | Planted-fact recall — the only fidelity metric |
| `measure.py` | One measurement / full comparison table |
| `cli.py` | `generate`/`measure`/`compare`/`report`/`check`/`demo`/`serve` (stdlib `http.server`, 127.0.0.1) |
| `demo.py` | End-to-end asserts incl. live serve round-trip matching local results |

## Evals

`python3 evals/run_evals.py` → **12/12 golden evals**, report at `evals/eval_report.json` (md5 `cd043a776b48f751d7e2eee14356aedc`, byte-identical across 3 verified runs): corpus shape, estimator pin, headline numbers per strategy × type (E3–E8), stale-value absence after dedup, JSON-prune no-op on non-JSON, determinism, and CLI `check` exit codes 0/1/2.

Unit tests: `python3 -m unittest discover -s tests` → **25 hermetic tests**, including a no-network enforcement test.

## Development loop — what the checks actually caught

1. **Dedup threshold vs the updated-value pair.** The first `cache_ttl` pair shared too few shingles (Jaccard 0.45 < 0.5 threshold), so dedup kept *both* 300 and 900 — the stale value survived. The eval's stale-absence assertion caught it; the planted pair now carries its full log context, similarity clears the threshold, and the newest wins.
2. **TF-IDF on JSON looked good on savings alone.** 64% saved reads like a win until recall (0.5) is printed next to it — which is the entire point of pairing every savings number with recall in one table, never alone.

## Scope and honest limits

- **Planted-fact recall stands in for answer accuracy — and cannot confirm "same answers" claims without LLM calls.** A needle surviving compression means the *text* is still present; it does not prove a model would answer the same way, attend to the fact in its new position, or not be misled by what was removed around it. Claims like "~38% saving, no accuracy change" need a downstream question-answering eval with real model calls; this kit deliberately makes none.
- **`words * 1.3` undercounts JSON/log tokens.** Real tokenizers split punctuation, numbers, keys, and indentation into many more tokens than whitespace words; absolute token counts here are underestimates, especially for JSON and logs. Savings *percentages* and recall comparisons are the reliable output, not the absolute counts.
- **One seeded corpus, repetitive by design.** Dedup's headline numbers are high because logs/RAG here are genuinely repetitive; a diverse corpus would save far less. The corpus is a measurement fixture, not a benchmark.
- **Future work only (not built): claim-evidence compilation** — compiling context into claim→evidence structures before compression. Named here as the next step; deliberately cut from this build to keep the 4-strategy scope testable.

## License

MIT — see LICENSE.
