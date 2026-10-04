# Design decisions

PriorInbox is a single-user, loopback-only application. React uses a same-origin
Vite proxy; FastAPI owns one sequential ingestion worker, SQLite and a bounded
conversation context window. No hosted inference or background model downloads.

Sources return replayable messages. A source/external-id unique key provides
idempotency. Pending/error messages are retried; classification is committed before
notification. Notifications are best effort, at most once (a crash can lose one).
Ephemeral mode uses an in-memory database and loses deduplication at restart.

The two-stage pipeline bypasses inference only for a tiny exact allowlist with no
conversation context. Context, questions, acknowledgments, and unfamiliar emoji
always go to the model. Schema validation failures remain errors, never casual.
Thresholding is applied centrally to the model's score.

Metrics count HTTP attempts separately from messages routed to inference. Benchmark
runs use identical frozen labeled data and fresh pipelines, include retries in wall
latency, and refuse resume claims for fixture or incomplete runs. Confidence scores
are model estimates, not calibrated probabilities. Synthetic metrics cannot establish
real-world recall. Settings changes affect future messages only.

Instagram uses only Instagram Login / graph.instagram.com official conversations
endpoints. OAuth provisioning is manual; consumer accounts are unsupported. Polling
is best effort, not a complete message archive. No browser automation or cookies.
