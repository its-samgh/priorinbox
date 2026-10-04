import asyncio
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote

import httpx

from backend.app.config import Config
from backend.app.models.schemas import IncomingMessage


class MessageSource(Protocol):
    async def get_new_messages(self) -> list[IncomingMessage]: ...


SAMPLES = [
    ("Alex Morgan", "Can you send me the final deck before 6? The client review is tomorrow."),
    ("Jamie Chen", "lol"),
    ("Studio North", "We would love to order 30 shirts. Could you send a quote?"),
    ("Riley Park", "😂"),
    ("Jordan Lee", "Are you available for an interview Thursday at 2?"),
    ("Sam Rivera", "bro that reel 💀"),
    ("Taylor Kim", "Can you call me when you get a chance? Something happened."),
    ("Avery Patel", "Where should I send the payment for the deposit?"),
    ("Casey Brooks", "lmao"),
    ("Morgan Ellis", "Please bring your notes to our study session before noon."),
    ("Drew Lane", "yeah tomorrow works"),
    ("Robin Quinn", "The train is delayed. Can you pick me up at the north entrance?"),
]


class MockMessageSource:
    def __init__(self) -> None:
        self.index = 0

    async def get_new_messages(self) -> list[IncomingMessage]:
        batch = []
        for _ in range(2):
            if self.index >= len(SAMPLES):
                break
            i = self.index
            name, text = SAMPLES[i]
            batch.append(
                IncomingMessage(
                    external_id=f"demo-v1-{i}",
                    conversation_id=f"demo-{i}",
                    sender_id=f"person-{i}",
                    sender_display_name=name,
                    text=text,
                    timestamp=datetime.now(UTC),
                    source="mock",
                )
            )
            self.index += 1
        return batch


class FileMessageSource:
    """Replay files; database idempotency handles repeats and failed classifications."""

    def __init__(self, directory: Path):
        self.directory = directory
        self.invalid_files = 0

    async def get_new_messages(self) -> list[IncomingMessage]:
        return await asyncio.to_thread(self.read)

    def read(self) -> list[IncomingMessage]:
        output = []
        self.invalid_files = 0
        for path in sorted(self.directory.glob("*.json*")):
            if path.suffix not in {".json", ".jsonl"} or path.is_symlink():
                continue
            try:
                if path.stat().st_size > 20_000_000:
                    raise ValueError("File exceeds 20MB limit")
                raw = path.read_text()
                if path.suffix == ".jsonl":
                    rows = []
                    for line in raw.splitlines():
                        if not line.strip():
                            continue
                        try:
                            rows.append(json.loads(line))
                        except ValueError:
                            self.invalid_files += 1
                else:
                    rows = json.loads(raw)
                if not isinstance(rows, list):
                    raise ValueError("Expected an array; normalize Instagram exports first")
                for row in rows:
                    try:
                        output.append(IncomingMessage.model_validate({**row, "source": "file"}))
                    except (ValueError, TypeError):
                        self.invalid_files += 1
            except (ValueError, OSError, TypeError):
                self.invalid_files += 1
        return sorted(output, key=lambda m: m.timestamp)


class InstagramMessageSource:
    """Official Instagram Login Conversations API; no private endpoints or cookies."""

    def __init__(self, config: Config, transport: httpx.AsyncBaseTransport | None = None):
        if not config.meta_token or not config.meta_account_id:
            raise ValueError("Instagram requires an account ID and environment access token")
        if config.meta_account_type not in {"BUSINESS", "CREATOR"}:
            raise ValueError("Instagram supports only Professional Business/Creator accounts")
        if not re.fullmatch(r"v\d+\.\d+", config.meta_api_version):
            raise ValueError("Invalid Meta API version")
        self.account = config.meta_account_id
        self.version = config.meta_api_version
        self.client = httpx.AsyncClient(
            base_url="https://graph.instagram.com",
            headers={"Authorization": f"Bearer {config.meta_token}"},
            timeout=30,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        for attempt in range(4):
            response = await self.client.get(path, params=params)
            body = response.json()
            error = body.get("error", {})
            retry = (
                response.status_code == 429
                or response.status_code >= 500
                or error.get("code") in {4, 17, 32, 613}
                or error.get("is_transient")
            )
            if retry and attempt < 3:
                try:
                    delay = min(
                        60.0, max(0, float(response.headers.get("Retry-After", 2**attempt)))
                    )
                except ValueError:
                    delay = 2**attempt
                await asyncio.sleep(delay)
                continue
            if response.is_error or error:
                # Never include token, URL, API body or private message in exceptions.
                raise RuntimeError("Meta request failed; check permissions, token and rate limits")
            return body  # type: ignore[no-any-return]
        raise RuntimeError("Meta retry budget exhausted")

    async def pages(
        self, path: str, params: dict[str, str], first: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        seen = set()
        body = first
        for _ in range(100):
            body = body if body is not None else await self.get(path, params)
            items.extend(body.get("data", []))
            paging = body.get("paging", {})
            cursor = paging.get("cursors", {}).get("after")
            if not paging.get("next") or not cursor or cursor in seen:
                return items
            # Never follow remote pagination URLs (may contain tokens or another host).
            seen.add(cursor)
            params = {**params, "after": cursor}
            body = None
        raise RuntimeError("Meta pagination safety limit reached")

    async def get_new_messages(self) -> list[IncomingMessage]:
        prefix = f"/{self.version}"
        conversations = await self.pages(
            f"{prefix}/{quote(self.account, safe='')}/conversations", {"platform": "instagram"}
        )
        output = []
        for conversation in conversations:
            cid = str(conversation["id"])
            path = f"{prefix}/{quote(cid, safe='')}"
            envelope = await self.get(path, {"fields": "messages"})
            refs = await self.pages(f"{path}/messages", {}, envelope.get("messages", {"data": []}))
            # Meta restricts retrievable details to recent messages; this is not an archive.
            for ref in refs[:20]:
                message = await self.get(
                    f"{prefix}/{quote(str(ref['id']), safe='')}",
                    {"fields": "id,created_time,from,to,message"},
                )
                sender = message.get("from", {})
                if str(sender.get("id")) == self.account:
                    continue
                output.append(
                    IncomingMessage(
                        external_id=str(message["id"]),
                        conversation_id=cid,
                        sender_id=str(sender["id"]),
                        sender_display_name=sender.get("username", "Instagram"),
                        text=message.get("message")
                        or "[Media or unsupported message; review Instagram]",
                        timestamp=message["created_time"],
                        source="instagram",
                    )
                )
        return sorted(output, key=lambda m: m.timestamp)


def stable_export_id(conversation: str, row: dict[str, Any]) -> str:
    return hashlib.sha256((conversation + json.dumps(row, sort_keys=True)).encode()).hexdigest()
