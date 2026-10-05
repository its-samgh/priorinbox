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
| Clean browser load | No console errors after separating React bootstrap from the app component |
| Built single-server mode | FastAPI served the built dashboard and API successfully |
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

## Initial-session limitations (updated below)

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

## Initial-session resume evidence

“Built a local message-triage application with two configurable classification
pipelines, 210 synthetic evaluation examples, and 45 passing automated tests.”

At that point there was no evidence for a model recall, inference savings or throughput
improvement claim. Run real paired benchmarks and review their provenance and
limitations before using `make resume-metrics` output.

## Continuation on 2026-10-05

- Fixed settings updates waiting behind active inference; the API remains responsive
  and model changes are revalidated before subsequent messages are sent.
- Added regression coverage for an in-flight model change and settings responsiveness.
  The backend suite now passes 43 tests; existing frontend coverage adds 4 tests.
- Benchmark metadata now includes the installed model digest, Ollama version and
  classifier hash; mismatches cannot generate comparison/resume claims.
- Downloaded qwen2.5:3b with explicit user approval and verified local model availability.
- Verified the checksum of an official GitHub CLI v2.102.0 ARM64 temporary download.
  Its `gh auth status` confirms valid GitHub authentication for its-samgh. The system
  Intel-only CLI was left unchanged.
- The earlier no-model/no-publication entries describe the initial session; updated
  benchmark and publication evidence follows below.

### First real pair and score diagnosis

Both initial runs completed all 210 synthetic messages without classification failures.
The baseline made 210 Ollama calls; two-stage made 201 (4.29% fewer). Both had 60%
recall and 98.97% precision. Two-stage throughput was 1.04× baseline, but p95 latency
was 2.78% higher; no latency improvement is claimed for that pair.

Targeted public synthetic diagnostics showed information questions receiving low
scores/casual decisions despite needing a reply. Updated guidance explicitly separates
actionability from urgency and anchors score ranges. The initial result files remain
in the ignored `benchmarks/results/initial-prompt/` directory. The revised prompt is
evaluated again on the same development set; this is not an independent holdout.

### Revised real paired benchmark

Apple M1 Pro MacBook Pro, 16 GB RAM, macOS arm64, Python 3.14.7, Ollama 0.34.4,
qwen2.5:3b, threshold 0.65 and four context messages. Both completed 210/210 synthetic
messages with no failures. Model digest and classifier hash are in the generated
README table; output files contain aggregates only and remain ignored.

- Both: precision 95.14%, recall 85.62%, F1 90.13%, false-negative rate 14.38%.
  Of 160 positive examples, 137 were surfaced and 23 were missed; 7 false positives.
- Baseline: 210 calls; p50 1520.42 ms; p95 2487.37 ms; 0.594 messages/s.
- Two-stage: 201 calls; p50 1529.20 ms; p95 2435.86 ms; 0.615 messages/s.
- Calls fell 4.29%; single-run throughput ratio 1.03x; p95 fell 2.07%.
  These small timing differences do not establish a repeatable general speedup.
- Potential notifications suppressed: 31.43%, a decision count rather than delivery.
- `make resume-metrics` and `scripts.publish_metrics` succeeded with the real pair.
  The same public set informed prompt debugging; no held-out accuracy claim is made.

The current evidence supports a synthetic development-set recall claim, not a claim
of very high real-world recall. Use the private labeler and a separate holdout to
choose a model/threshold for an actual inbox.

### Real demo and final local checks

- `make lint typecheck test build`: all passed; 43 backend and 4 frontend tests.
- `make doctor`: Ollama reachable, qwen2.5:3b local weights available, configuration
  valid and SQLite integrity OK.
- `make demo`: 12 synthetic messages completed, 8 important, 4 suppressed, 9 local
  Ollama calls and 3 conservative heuristic decisions; zero pending/failed.
- Browser: important inbox, real model activity and analytics rendered; no browser
  warning/error logs. Unlabeled precision/recall/F1 remained unavailable as intended.
- Notification authorization was denied by macOS; no delivery success is claimed.
- Actual screenshot saved at `docs/screenshots/local-ai-inbox.jpg`, with the mock
  ingestion badge, real inference state and OS authorization warning visible.
- Public repository: https://github.com/its-samgh/priorinbox.

### Hosted CI

[GitHub Actions run 37355207339](https://github.com/its-samgh/priorinbox/actions/runs/37355207339)
passed on 2026-10-05 for implementation commit `d6a6ae7`. Locked installation,
lint, Python/TypeScript checks, all 47 tests, production build and both fixture
benchmark mechanics passed on Ubuntu with Python 3.12 and Node 22. Hosted CI does
not run real inference; the actual local model measurements above are separate.
