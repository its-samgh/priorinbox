# Security policy

PriorInbox is a single-user local application, not a multi-tenant web service.
Do not expose the API or Vite server to your LAN or the internet. The API uses
loopback host validation, origin checks, a custom mutation header and no CORS
allowlist for external sites. These mitigate browser cross-origin attacks; they
are not authentication against another process or user on the same machine.

Report vulnerabilities privately through GitHub's private vulnerability reporting
when enabled by the repository owner. Otherwise ask the maintainer for a private
channel without posting exploit details or private messages in a public issue.

## Data boundaries

- Ollama HTTP clients bypass proxy environment variables and reject redirects.
  Configuration accepts only loopback HTTP URLs. Cloud-named models and remote
  aliases are rejected; model metadata must describe local weights. Also run the
  Ollama **server** with `OLLAMA_NO_CLOUD=1`. A malicious local service can defeat
  client-side protections; keep your machine and Ollama installation trusted.
- Message text is untrusted model input. Structured outputs are validated and no
  model output triggers commands, replies, purchases or other external actions.
- `.env`, `data/`, private datasets, exports, credentials, SQLite files, logs and
  local benchmark outputs are ignored. Only explicitly synthetic fixtures belong
  in Git. Gitignore is not an access-control or secret-scanning system.
- Raw messages, senders, reasons and labels are stored in local SQLite unless
  `PRIOR_PERSIST_RAW=false`. This mode uses an in-memory database for **all** data,
  including settings and deduplication. It cannot erase an older persistent DB.
- Database and local export/label files get mode 0600 on supported filesystems.
  SQLite is not encrypted. Disk encryption, backups, OS notifications, swap,
  browser extensions and terminal history are outside this application's control.
- Notifications hide sender, preview and reason by default. Enabling previews may
  put private text on your lock screen or in OS notification history.
- No raw message logging. Error paths use generic diagnostics; do not enable HTTP
  debug logging on live data. Benchmark JSON is aggregate-only and ignores private
  filenames, but results are still kept out of Git by default.
- Meta tokens are read from environment variables and sent only in authorization
  headers to `graph.instagram.com`; pagination URLs are never followed directly.
  App OAuth setup and token rotation remain the operator's responsibility.

## Support and deployment

Only the latest release is supported. Dependencies are locked; CI uses mock AI and
Meta responses. Live Meta access and OS notification behavior require separate
validation on the target account and desktop. This tool can misclassify messages;
it is not an emergency monitoring service.
