# Local validation record

Executed 2026-10-04 on macOS, Python 3.14.7, Node 22.23.2.
CI is configured for Linux, Python 3.12 and Node 22; a hosted CI run has not occurred.

| Check | Observed result |
|---|---|
| `make lint` | Ruff and Prettier passed |
| `make typecheck` | mypy (24 source files) and TypeScript passed |
| `make test` | 41 backend tests and 4 frontend tests passed |
| `make build` | Vite production bundle built successfully |
| npm dependency audit | Zero known vulnerabilities after updating Vitest |
| `make fixture` | Both loopback services started; all 12 synthetic demo messages processed |
| Browser workflows | Inbox, activity, settings save/reload, message details, labeling, analytics verified |
| Keyboard interaction | Escape closes message details; focus returns to message |
| Responsive check | Narrow layout inspected; document width and scroll width both 375 px |
| Screenshot | Actual synthetic dashboard saved in `docs/screenshots/fixture-inbox.jpg` |
| `make doctor` | Python, Node, configuration, DB integrity and Ollama service checked; no local models installed |
| Baseline fixture benchmark | 210/210 processed |
| Two-stage fixture benchmark | 210/210 processed |
| `make resume-metrics` on fixtures | Refused as intended; no fabricated resume claims |
| `scripts.publish_metrics` on fixtures | Refused as intended; README benchmark section stays unclaimed |
| Private-data gitignore checks | `.env`, SQLite DB, private dataset, exports and results ignored |
| `gh auth status` | Could not execute: installed CLI returned `bad CPU type in executable` |

## Unverified or constrained

- No real Ollama classification/benchmark was run: service available, no model weights.
  No download was started. Fixture timings and quality scores are not AI results.
- Instagram requests use mocked responses in tests. No live credentials or eligible
  account were supplied. Direct Meta Conversations docs returned HTTP 429 during
  research; see `instagram.md` for sources and precise limits.
- macOS denied notification authorization for the development Python application.
  Classification continued. The implementation checks authorization and bounds waits;
  actual desktop delivery is not claimed. `desktop-notifier` requires a supported
  desktop session, and macOS may require a signed app bundle. Packaging is roadmap work.
- Two upstream deprecation warnings remain under Python 3.14: Starlette's HTTPX test
  client integration and desktop-notifier's event-loop policy. Tests still pass.
- Browser automation used the built-in browser because the agent-browser executable
  was unavailable. A saved screenshot is evidence of the running fixture app only.

## Honest resume evidence currently available

“Built a local message-triage application with two configurable classification
pipelines, 210 synthetic evaluation examples, and 45 passing automated tests.”

There is currently no evidence for a model recall, inference savings or throughput
improvement claim. Run real paired benchmarks and review their provenance and
limitations before using `make resume-metrics` output.
