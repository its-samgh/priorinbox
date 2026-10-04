"""Publish only measured, complete, synthetic benchmark aggregates into README."""

from pathlib import Path

from benchmarks.compare import compare_if_ready, load_pair


def main() -> None:
    directory = Path("benchmarks/results")
    try:
        baseline, _ = load_pair(directory)
    except (FileNotFoundError, ValueError, KeyError):
        raise SystemExit("A complete compatible benchmark pair is required") from None
    if baseline["fixture"] or baseline["dataset_kind"] != "synthetic":
        raise SystemExit("Only real Ollama results on public synthetic data can be published")
    compare_if_ready(directory)
    path = Path("README.md")
    start, end = "<!-- benchmark-results:start -->", "<!-- benchmark-results:end -->"
    content = path.read_text()
    before = content.split(start)[0]
    after = content.split(end)[1]
    path.write_text(before + start + "\n" + (directory / "comparison.md").read_text() + end + after)


if __name__ == "__main__":
    main()
