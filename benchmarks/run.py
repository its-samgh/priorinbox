"""Sequential paired benchmark; no network other than loopback Ollama."""

import argparse
import asyncio
import hashlib
import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path

from backend.app.classifier.pipeline import ClassificationError, Pipeline
from backend.app.config import Config
from backend.app.models.schemas import IncomingMessage, Label, Settings
from backend.app.services.metrics import summarize


async def run(args: argparse.Namespace) -> dict:
    raw = args.dataset.read_bytes()
    rows = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    if not rows:
        raise ValueError("Dataset is empty")
    for row in rows:
        Label.model_validate(row["label"])
        if not isinstance(row.get("context", []), list) or not all(
            isinstance(text, str) for text in row.get("context", [])
        ):
            raise ValueError("Context must be a list of strings")
    ids = [row["external_id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("Dataset contains duplicate external IDs")
    config = Config()
    settings = Settings(
        model=args.model or config.model,
        pipeline=args.pipeline,
        threshold=args.threshold,
        context_messages=args.context_messages,
    )
    pipeline = Pipeline(config.ollama_url, args.fixture)
    results = []
    try:
        if not args.fixture:
            await pipeline.check_model(settings.model)
        start = time.perf_counter()
        for row in rows:
            message = IncomingMessage.model_validate(row)
            record = {
                "label": row["label"],
                "classification": None,
                "llm_calls": 0,
                "inference_ms": 0.0,
            }
            try:
                result = await pipeline.classify(message, row.get("context", []), settings)
                record.update(
                    classification=result.model_dump(mode="json"),
                    llm_calls=result.llm_calls,
                    inference_ms=result.inference_ms,
                )
            except ClassificationError as exc:
                record.update(llm_calls=exc.calls, inference_ms=exc.inference_ms)
            results.append(record)
        elapsed = time.perf_counter() - start
    finally:
        await pipeline.close()
    metrics = summarize(results, elapsed)
    report = {
        "schema_version": 1,
        "pipeline": args.pipeline,
        "fixture": args.fixture,
        "model": settings.model,
        "threshold": settings.threshold,
        "context_messages": settings.context_messages,
        "dataset_sha256": hashlib.sha256(raw).hexdigest(),
        "dataset_kind": "synthetic"
        if all(r.get("synthetic") is True for r in rows)
        else "locally labeled",
        "dataset_size": len(rows),
        "elapsed_seconds": elapsed,
        "created_at": datetime.now(UTC).isoformat(),
        "machine": {
            "system": platform.system(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
        },
        "methodology": "sequential; cold/warm state uncontrolled; retries included; no warmup",
        "complete": metrics["pending_or_failed"] == 0,
        "metrics": metrics,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--pipeline", choices=["baseline_llm", "two_stage"], required=True)
    parser.add_argument("--model")
    parser.add_argument("--threshold", type=float, default=0.65)
    parser.add_argument("--context-messages", type=int, default=4)
    parser.add_argument(
        "--fixture", action="store_true", help="Test mechanics only; no resume claims"
    )
    parser.add_argument("--output-dir", type=Path, default=Path("benchmarks/results"))
    args = parser.parse_args()
    try:
        result = asyncio.run(run(args))
    except Exception:
        raise SystemExit(
            "Benchmark stopped. Check dataset schema and local Ollama/model availability."
        ) from None
    args.output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    name = "baseline" if args.pipeline == "baseline_llm" else "two_stage"
    path = args.output_dir / f"{name}.json"
    (args.output_dir / "resume-bullets.txt").unlink(missing_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    path.chmod(0o600)
    print(f"{name}: {result['metrics']['messages_processed']}/{result['dataset_size']} processed")
    from benchmarks.compare import compare_if_ready

    compare_if_ready(args.output_dir)
    if not result["complete"]:
        raise SystemExit(
            "Incomplete benchmark: failures retained in aggregate counts; no resume claims"
        )


if __name__ == "__main__":
    main()
