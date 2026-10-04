import json
from datetime import UTC, datetime

import httpx
import pytest
from pydantic import ValidationError

from backend.app.classifier.pipeline import ClassificationError, Pipeline
from backend.app.config import Config
from backend.app.models.schemas import IncomingMessage, Settings, Verdict


def message(text: str = "Can you call me?") -> IncomingMessage:
    return IncomingMessage(
        external_id="one",
        conversation_id="thread",
        sender_id="alex",
        sender_display_name="Alex",
        text=text,
        timestamp=datetime.now(UTC),
        source="mock",
    )


def verdict(score: float = 0.8) -> dict:
    return {
        "important": True,
        "importance_score": score,
        "category": "question",
        "reason": "Requires an answer",
        "requires_response": True,
    }


@pytest.mark.parametrize(
    "change",
    [
        {"importance_score": 1.1},
        {"importance_score": float("nan")},
        {"important": "yes"},
        {"category": "invented"},
        {"reason": ""},
        {"extra": "field"},
    ],
)
def test_schema(change):
    with pytest.raises(ValidationError):
        Verdict.model_validate({**verdict(), **change})


@pytest.mark.parametrize(
    "url",
    [
        "https://api.example.com",
        "http://example.com",
        "http://localhost@evil.com",
        "http://localhost/path",
        "http://localhost?token=secret",
    ],
)
def test_loopback_required(url):
    with pytest.raises(ValidationError):
        Config(ollama_url=url)


async def test_threshold_and_schema_payload():
    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": json.dumps(verdict(0.7))}})

    pipeline = Pipeline("http://localhost:11434", transport=httpx.MockTransport(handler))
    try:
        result = await pipeline.classify(message(), [], Settings(threshold=0.8))
        assert not result.important
        assert result.llm_calls == 1
        assert captured[0]["format"]["additionalProperties"] is False
        assert captured[0]["stream"] is False
    finally:
        await pipeline.close()


async def test_malformed_retry_then_success(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("backend.app.classifier.pipeline.asyncio.sleep", no_wait)
    replies = iter(["not json", json.dumps(verdict())])
    pipeline = Pipeline(
        "http://localhost",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"message": {"content": next(replies)}})
        ),
    )
    result = await pipeline.classify(message(), [], Settings())
    assert result.llm_calls == 2 and result.important
    await pipeline.close()


async def test_failure_is_not_casual(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("backend.app.classifier.pipeline.asyncio.sleep", no_wait)
    pipeline = Pipeline(
        "http://localhost",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"message": {"content": "{}"}})
        ),
    )
    with pytest.raises(ClassificationError) as error:
        await pipeline.classify(message(), [], Settings())
    assert error.value.calls == 3
    await pipeline.close()


@pytest.mark.parametrize("text", ["lol", "😂", "", "lmao"])
async def test_filter_skips_only_obvious(text):
    pipeline = Pipeline("http://localhost", fixture=True)
    result = await pipeline.classify(message(text), [], Settings())
    assert result.model == "heuristic" and not result.important
    contextual = await pipeline.classify(message(text), ["Are you safe?"], Settings())
    assert contextual.model != "heuristic"
    baseline = await pipeline.classify(message(text), [], Settings(pipeline="baseline_llm"))
    assert baseline.model != "heuristic"
    await pipeline.close()


@pytest.mark.parametrize(
    "text",
    [
        "yeah tomorrow works",
        "okay",
        "👍",
        "Help!",
        "lol can you send the file?",
        "Can you call me?",
        "Where should I send payment?",
        "🆘",
    ],
)
async def test_important_and_ambiguous_not_filtered(text):
    pipeline = Pipeline("http://localhost", fixture=True)
    assert (await pipeline.classify(message(text), [], Settings())).model != "heuristic"
    await pipeline.close()


async def test_context_window_and_cloud_alias():
    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"remote_host": "cloud.example", "model_info": {}})
        return httpx.Response(200, json={"message": {"content": json.dumps(verdict())}})

    pipeline = Pipeline("http://localhost", transport=httpx.MockTransport(handler))
    await pipeline.classify(message(), ["old", "recent", "new"], Settings(context_messages=2))
    assert json.loads(captured[0]["messages"][1]["content"])["context"] == ["recent", "new"]
    with pytest.raises(ValueError):
        await pipeline.check_model("alias")
    await pipeline.close()


async def test_network_timeout_is_retried_without_leaking_text(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("backend.app.classifier.pipeline.asyncio.sleep", no_wait)

    def handler(request):
        raise httpx.ReadTimeout("sensitive transport details", request=request)

    pipeline = Pipeline("http://localhost", transport=httpx.MockTransport(handler))
    with pytest.raises(ClassificationError) as error:
        await pipeline.classify(message("private text"), [], Settings())
    assert error.value.calls == 3
    assert "private text" not in str(error.value)
    assert "sensitive" not in str(error.value)
    await pipeline.close()
