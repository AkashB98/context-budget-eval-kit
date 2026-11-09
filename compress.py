"""Exactly 4 compression strategies (TF-IDF has 2 variants = 5 strategy names).

1. dedup        near-duplicate removal, shingle Jaccard, keep LATEST
2. head_tail    head/tail truncation
3. tfidf        extractive summarization, query-agnostic
   tfidf_query  extractive summarization, query-aware
4. json_prune   JSON field pruning for tool outputs
"""
import json
import math
import re
from collections import Counter

STOPWORDS = {"a", "an", "the", "is", "are", "was", "were", "to", "of", "for", "on", "in", "at", "with", "and", "or", "it", "its", "this", "that"}

LOW_VALUE_KEYS = {"debug_notes", "trace_id", "verbose_log", "timestamps", "empty_field", "debug", "trace", "verbose"}


def _units(text):
    # Unit = line if multi-line log/json, else blank-line chunks / sentences fallback
    if "\n\n" in text:
        return text.split("\n\n"), "\n\n"
    if "\n" in text:
        return text.split("\n"), "\n"
    return re.split(r"(?<=[.!?])\s+", text), " "


def _words(s):
    return re.findall(r"[a-z0-9]+", s.lower())


def _shingles(words, n=3):
    if len(words) < n:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def _jaccard(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def dedup(text, threshold=0.5):
    units, sep = _units(text)
    kept = []  # list of (unit, shingles)
    for u in units:
        sh = _shingles(_words(u))
        # remove any earlier unit similar to this one -> keep LATEST
        kept = [(k, s) for (k, s) in kept if _jaccard(s, sh) < threshold]
        kept.append((u, sh))
    return sep.join(k for k, _ in kept)


def head_tail(text, fraction=0.5):
    units, sep = _units(text)
    n = len(units)
    keep = max(1, int(n * fraction)) if n else 0
    head = keep // 2
    tail = keep - head
    selected = units[:head] + (units[n - tail:] if tail else [])
    return sep.join(selected)


def _tfidf_scores(units, query=None):
    docs = [_words(u) for u in units]
    docs = [[w for w in d if w not in STOPWORDS] or d for d in docs]
    n = len(docs)
    df = Counter()
    for d in docs:
        for w in set(d):
            df[w] += 1

    def idf(w):
        return math.log((1 + n) / (1 + df.get(w, 0))) + 1.0
    qterms = set(_words(query)) if query else set()
    scores = []
    for d in docs:
        tf = Counter(d)
        s = sum(tf[w] * idf(w) for w in tf)
        s = s / max(1, len(d))  # length-normalised so long repetitive lines don't dominate purely by length
        if query:
            overlap = sum(1 for w in qterms if w in tf)
            s += overlap * 5.0  # query-aware boost
        scores.append(s)
    return scores


def tfidf(text, fraction=0.5, query=None):
    units, sep = _units(text)
    if not units:
        return text
    keep = max(1, int(len(units) * fraction))
    scores = _tfidf_scores(units, query=query)
    ranked = sorted(range(len(units)), key=lambda i: (-scores[i], i))
    chosen = set(ranked[:keep])
    return sep.join(u for i, u in enumerate(units) if i in chosen)


def _prune(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in LOW_VALUE_KEYS:
                continue
            if v is None:
                continue
            out[k] = _prune(v)
        return out
    if isinstance(obj, list):
        return [_prune(v) for v in obj]
    return obj


def json_prune(text):
    try:
        obj = json.loads(text)
    except Exception:
        return text  # not JSON: pruning is a no-op (honest 0% saving on logs/RAG)
    return json.dumps(_prune(obj), indent=2, sort_keys=True)


STRATEGIES = {
    "dedup": lambda text, query=None: dedup(text),
    "head_tail": lambda text, query=None: head_tail(text),
    "tfidf": lambda text, query=None: tfidf(text, query=None),
    "tfidf_query": lambda text, query=None: tfidf(text, query=query),
    "json_prune": lambda text, query=None: json_prune(text),
}
STRATEGY_NAMES = list(STRATEGIES.keys())


def compress(text, strategy, query=None):
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy {strategy}")
    return STRATEGIES[strategy](text, query=query)
