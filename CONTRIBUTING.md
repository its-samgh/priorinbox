# Contributing

Use Python 3.12+, Node 22+ and uv. Run `make install`, then
`make lint typecheck test build`. Tests must work with no Ollama service, Meta token
or private dataset. Keep PRs focused and explain observed behavior and validation.

Use synthetic messages in tests. Never commit local datasets, exports, results,
credentials or screenshots of real inboxes. Preserve loopback-only inference and
avoid introducing telemetry or hosted model fallbacks.

Please report security issues using SECURITY.md. Evaluate heuristic changes against
contextual counterexamples as well as simple reactions; prioritize important-message
recall over filtering rate. Regenerate the public dataset with
`.venv/bin/python -m scripts.synthetic` after editing its source.
