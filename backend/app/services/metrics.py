import math
from statistics import mean
from typing import Any


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def quality(truth: list[bool], predicted: list[bool]) -> dict[str, Any]:
    if len(truth) != len(predicted):
        raise ValueError("Labels and predictions must align")
    tp = sum(t and p for t, p in zip(truth, predicted, strict=True))
    fp = sum(not t and p for t, p in zip(truth, predicted, strict=True))
    fn = sum(t and not p for t, p in zip(truth, predicted, strict=True))
    tn = len(truth) - tp - fp - fn
    return {
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
        "false_negative_rate": fn / (tp + fn) if tp + fn else None,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "labeled_messages": len(truth),
    }


def summarize(records: list[dict], elapsed: float) -> dict[str, Any]:
    done = [r for r in records if r.get("classification")]
    results = [r["classification"] for r in done]
    n = len(results)
    important = sum(r["important"] for r in results)
    latencies = [r["latency_ms"] for r in results]
    routed = sum(r.get("llm_calls", 0) > 0 for r in records)
    filtered = sum(r["model"] == "heuristic" for r in results)
    labeled = [r for r in done if r.get("label") is not None]
    return {
        "messages_processed": n,
        "messages_received": len(records),
        "pending_or_failed": len(records) - n,
        "important": important,
        "casual": n - important,
        "notifications_suppressed": n - important,
        "notifications_submitted": sum(r.get("notification_sent", False) for r in records),
        "notification_reduction_pct": 100 * (n - important) / n if n else None,
        "messages_sent_to_ollama": routed,
        "ollama_invocation_pct": 100 * routed / len(records) if records else None,
        "llm_calls": sum(r.get("llm_calls", 0) for r in records),
        "filtered_before_llm_pct": 100 * filtered / n if n else None,
        "total_inference_ms": sum(r.get("inference_ms", 0) for r in records),
        "average_latency_ms": mean(latencies) if n else None,
        "p50_latency_ms": percentile(latencies, 0.5),
        "p95_latency_ms": percentile(latencies, 0.95),
        "throughput_per_second": n / elapsed if elapsed > 0 else None,
        **quality(
            [r["label"]["important"] for r in labeled],
            [r["classification"]["important"] for r in labeled],
        ),
    }
