import argparse
import json
from pathlib import Path

import pytest

from benchmarks.compare import compare_if_ready, load_pair, resume
from benchmarks.run import run


async def test_fixture_benchmark_and_resume_rejection(tmp_path):
    for pipeline in ["baseline_llm", "two_stage"]:
        report = await run(
            argparse.Namespace(
                dataset=Path("benchmarks/data/synthetic.jsonl"),
                pipeline=pipeline,
                model=None,
                threshold=0.65,
                context_messages=4,
                fixture=True,
            )
        )
        assert report["complete"] and report["dataset_size"] == 210
        assert report["metrics"]["llm_calls"] == 0
        name = "baseline" if pipeline == "baseline_llm" else pipeline
        (tmp_path / f"{name}.json").write_text(json.dumps(report))
    compare_if_ready(tmp_path)
    assert "FIXTURE ONLY" in (tmp_path / "comparison.md").read_text()
    with pytest.raises(ValueError, match="Fixture"):
        resume(tmp_path)
    report["model_digest"] = "different-model-weights"
    (tmp_path / "two_stage.json").write_text(json.dumps(report))
    with pytest.raises(ValueError, match="different"):
        load_pair(tmp_path)
    report["model_digest"] = None
    report["dataset_sha256"] = "different"
    (tmp_path / "two_stage.json").write_text(json.dumps(report))
    with pytest.raises(ValueError, match="different"):
        load_pair(tmp_path)
    compare_if_ready(tmp_path)
    assert not (tmp_path / "comparison.md").exists()
