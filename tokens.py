"""Token estimator: ceil(words * 1.3), copied exactly from llm-cost-sidecar / agent-session-memory-kit."""
import math


def estimate_tokens(text: str) -> int:
    words = len(text.split())
    return math.ceil(words * 1.3) if words else 0
