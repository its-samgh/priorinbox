import argparse
import json
from pathlib import Path

PAIRED = (
    "dataset_sha256",
    "dataset_kind",
    "dataset_size",
    "model",
    "threshold",
    "context_messages",
    "fixture",
    "machine",
    "methodology",
    "schema_version",
)


def load_pair(directory: Path) -> tuple[dict, dict]:
    a = json.loads((directory / "baseline.json").read_text())
    b = json.loads((directory / "two_stage.json").read_text())
    if any(a[key] != b[key] for key in PAIRED):
        raise ValueError("Cannot compare different datasets, models, configurations or machines")
    if a["pipeline"] != "baseline_llm" or b["pipeline"] != "two_stage":
        raise ValueError("Unexpected pipeline pair")
    if not a["complete"] or not b["complete"]:
        raise ValueError("Cannot compare incomplete runs")
    return a, b


def reduction(old: float | None, new: float | None) -> float | None:
    return 100 * (old - new) / old if old and new is not None else None


def fmt(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"


def compare_if_ready(directory: Path) -> None:
    if not all((directory / f"{name}.json").exists() for name in ("baseline", "two_stage")):
        return
    try:
        a, b = load_pair(directory)
    except ValueError as exc:
        # Remove stale report so it cannot be mistaken for the newly mismatched pair.
        (directory / "comparison.md").unlink(missing_ok=True)
        print(str(exc))
        return
    am, bm = a["metrics"], b["metrics"]
    rows = [
        "# Measured pipeline comparison",
        "",
        f"Dataset: {a['dataset_kind']}; N={a['dataset_size']}; model: {a['model']}.",
        "FIXTURE ONLY — not evidence of AI performance."
        if a["fixture"]
        else "Single sequential runs; model warm state uncontrolled. Repeat in alternating order.",
        "",
        "| Metric | Baseline | Two-stage |",
        "|---|---:|---:|",
    ]
    for key in (
        "messages_processed",
        "llm_calls",
        "filtered_before_llm_pct",
        "total_inference_ms",
        "p50_latency_ms",
        "p95_latency_ms",
        "throughput_per_second",
        "precision",
        "recall",
        "f1",
        "false_negative_rate",
        "notification_reduction_pct",
    ):
        rows.append(f"| {key} | {fmt(am[key])} | {fmt(bm[key])} |")
    rows += [
        "",
        f"Ollama call reduction: {fmt(reduction(am['llm_calls'], bm['llm_calls']))}%.",
        f"p95 latency reduction: {fmt(reduction(am['p95_latency_ms'], bm['p95_latency_ms']))}%.",
        f"Throughput ratio: {fmt(bm['throughput_per_second'] / am['throughput_per_second'])}×.",
        "Notification reduction is versus notifying on every message, not versus baseline.",
        "Precision, recall, F1 and false-negative rate are fractions. N/A is undefined.",
    ]
    (directory / "comparison.md").write_text("\n".join(rows) + "\n")


def resume(directory: Path) -> str:
    a, b = load_pair(directory)
    if a["fixture"]:
        raise ValueError("Fixture runs cannot generate resume metrics; run real local Ollama")
    am, bm = a["metrics"], b["metrics"]
    if bm["recall"] is None:
        raise ValueError("Need labeled positive messages to claim recall")
    calls = reduction(am["llm_calls"], bm["llm_calls"])
    ratio = bm["throughput_per_second"] / am["throughput_per_second"]
    latency = reduction(am["p95_latency_ms"], bm["p95_latency_ms"])
    dataset = f"{b['dataset_kind']} dataset of {b['dataset_size']} messages"
    bullets = [
        f"Built a local AI triage engine using {b['model']}; measured "
        f"{100 * bm['recall']:.2f}% important-message recall on a {dataset}."
    ]
    if calls is not None and calls > 0:
        bullets.append(
            f"Reduced Ollama calls by {calls:.2f}% versus an all-LLM baseline on the "
            f"same {dataset}, with {100 * bm['recall']:.2f}% optimized recall "
            f"(baseline: {100 * am['recall']:.2f}%)."
        )
    if ratio > 1 and latency is not None and latency > 0:
        bullets.append(
            f"Measured {ratio:.2f}× throughput and {latency:.2f}% lower p95 latency "
            f"with two-stage triage on a {dataset}."
        )
    bullets.append(
        f"Suppressed {bm['notification_reduction_pct']:.2f}% of potential notifications "
        f"while preserving {100 * bm['recall']:.2f}% important-message recall on a {dataset}."
    )
    return (
        "\n".join(bullets) + "\nSingle-run measurements; repeat before claiming general speedups.\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("benchmarks/results"))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.resume:
        try:
            text = resume(args.results)
        except (ValueError, FileNotFoundError, KeyError) as exc:
            (args.results / "resume-bullets.txt").unlink(missing_ok=True)
            raise SystemExit(f"No resume claims produced: {exc}") from None
        (args.results / "resume-bullets.txt").write_text(text)
        print(text)
    else:
        compare_if_ready(args.results)


if __name__ == "__main__":
    main()
