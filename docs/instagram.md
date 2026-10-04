# Official Instagram integration

## Supported route

This adapter is read-only and uses **Instagram API with Instagram Login**, on
`https://graph.instagram.com/{version}`. It does not use Instagram passwords,
browser sessions, cookies, scraped pages or private mobile endpoints. Business
and Creator accounts are eligible; ordinary personal/consumer accounts are not.
The Instagram Login route does not require linking a Facebook Page.

Sources researched on 2026-10-04:

- [Meta Instagram API collection](https://www.postman.com/meta/workspace/instagram/documentation/23987686-9386f468-7714-490f-9bfc-9442db5c8f00)
- [Meta Conversations API](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/conversations-api)
- [Meta Instagram Login setup](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login)
- [Meta messaging setup](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/messaging-api)
- [Meta Conversations collection and access levels](https://www.postman.com/meta/messenger-platform-api/folder/22794852-255610cd-47f5-4f4d-b3fa-71aec360be9a)

**Verification limitation:** Meta's direct Conversations documentation returned HTTP
429 during implementation. Meta's official public collection confirmed professional
accounts, Instagram Login messaging scopes, and messaging restrictions. The adapter
implements the documented Conversations endpoint family with contract tests; it has
**not** been validated against a live account. Treat Instagram support as experimental
and check the current linked documentation before enabling it. No claim is made that
v25.0 is the newest release; it is a configurable integration version.

## Setup

1. Create/configure a Meta developer app for Instagram API with Instagram Login.
2. Use a Professional Business or Creator account you control. Enable connected
   tools' message access in Instagram where required.
3. Complete Meta's official OAuth flow or supported developer-dashboard token flow.
   Request `instagram_business_basic` and `instagram_business_manage_messages`.
   Tokens must belong to this Instagram Login flow, not the Facebook Login route.
4. Test accounts need the appropriate app/account roles. Access to other users'
   accounts and conversations can require Advanced Access, App Review, business
   verification and a live app. A professional account alone is insufficient.
5. Put the token and account ID in local `.env` (never source code):

   ```dotenv
   PRIOR_SOURCE=instagram
   PRIOR_META_ACCOUNT_TYPE=BUSINESS
   PRIOR_META_ACCOUNT_ID=your-professional-account-id
   PRIOR_META_TOKEN=your-instagram-login-token
   PRIOR_META_API_VERSION=v25.0
   PRIOR_FIXTURE=false
   ```

6. Start the API with `.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log`
   and the UI with `npm --prefix frontend run dev`. `make demo` deliberately uses mock ingestion.

OAuth authorization, token refresh, permissions and account provisioning are manual.
The adapter refuses missing credentials or an unsupported configured account type;
Meta validates actual permissions/account eligibility on API calls. The configuration
field is not proof of the real account type. Expired or rejected credentials surface
as ingestion errors without logging tokens. Rotate the environment token and restart.

## Retrieval and limitations

The adapter lists `/{ig-user-id}/conversations`, requests
`/{conversation-id}?fields=messages`, and obtains recent message details from
`/{message-id}?fields=id,created_time,from,to,message`. It follows cursor pagination
through fixed-host endpoints, filters the account's own outbound messages, orders
incoming records by timestamp and relies on durable source/message IDs for deduplication.
It handles transient errors and rate limits with bounded backoff.

Polling is not real-time and is not guaranteed complete. Meta limits access to recent
message details; this implementation caps detail retrieval at 20 per conversation.
High-volume conversations and long outages can produce gaps. Unsupported media is a
reviewable placeholder, never silently treated as an empty reaction. Media contents
are not downloaded or analyzed. Group messaging is unsupported; inactive Requests
conversations may be unavailable. No attempt is made to bypass these restrictions.

For real-time delivery, Meta requires webhook subscriptions and a reachable HTTPS
callback with verification/signature validation. This local project does **not** host
that public callback. A secure webhook receiver is roadmap work; do not expose the
local dashboard to satisfy Meta's callback requirement.
