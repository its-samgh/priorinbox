import asyncio
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.config import Config
from backend.app.ingestion.sources import (
    FileMessageSource,
    InstagramMessageSource,
    MockMessageSource,
)
from backend.app.main import create_app
from backend.app.models.schemas import Settings
from backend.app.models.store import Store
from backend.app.services.metrics import percentile, quality, summarize
from backend.app.services.worker import Worker
from backend.tests.test_pipeline import message


def test_store_idempotency_restart_ephemeral(tmp_path):
    path = tmp_path / "messages.db"
    store = Store(path)
    one = message()
    assert store.add(one)
    assert not store.add(one.model_copy(update={"id": "another"}))
    store.engine.dispose()
    restarted = Store(path)
    assert len(restarted.pending()) == 1
    assert not restarted.add(one)
    restarted.engine.dispose()
    memory = Store(tmp_path / "no.db", persist=False)
    memory.add(one)
    assert not (tmp_path / "no.db").exists()
    memory.engine.dispose()


async def test_file_invalid_record_does_not_block_valid(tmp_path):
    (tmp_path / "messages.jsonl").write_text(message().model_dump_json() + "\n{}\n")
    (tmp_path / "broken.json").write_text("{broken")
    source = FileMessageSource(tmp_path)
    assert len(await source.get_new_messages()) == 1
    assert len(await source.get_new_messages()) == 1
    assert source.invalid_files == 2


async def test_mock_and_worker_restart(tmp_path):
    source = MockMessageSource()
    assert len(await source.get_new_messages()) == 2
    assert len(await source.get_new_messages()) == 2
    config = Config(database_path=tmp_path / "demo.db", fixture=True)
    worker = Worker(config)
    worker.settings.notifications = False
    await worker.tick()
    assert len(worker.store.records()) == 2
    assert all(r["status"] == "done" for r in worker.store.records())
    await worker.close()
    worker = Worker(config)
    worker.settings.notifications = False
    await worker.tick()
    assert len(worker.store.records()) == 2
    await worker.close()


def test_api_local_guard_settings_labels(tmp_path):
    app = create_app(Config(database_path=tmp_path / "app.db", fixture=True), run_worker=False)
    with TestClient(app, base_url="http://localhost") as client:
        assert client.get("/api/status").json()["fixture"]
        assert client.get("/api/messages").json()["items"] == []
        assert client.get("/api/analytics").json()["recall"] is None
        settings = Settings(notifications=False).model_dump()
        assert client.put("/api/settings", json=settings).status_code == 403
        headers = {"X-PriorInbox": "local"}
        assert client.put("/api/settings", json=settings, headers=headers).status_code == 200
        assert client.get("/api/settings").json()["notifications"] is False
        assert (
            client.put(
                "/api/settings", json={**settings, "threshold": 2}, headers=headers
            ).status_code
            == 422
        )
        assert (
            client.get("/api/status", headers={"Origin": "https://evil.example"}).status_code == 403
        )
        assert client.get("/api/status", headers={"Host": "evil.example"}).status_code == 400
        assert client.get("/api/messages?view=invalid").status_code == 422
        one = message()
        app.state.worker.store.add(one)
        assert (
            client.put(
                f"/api/messages/{one.id}/label",
                json={"important": True, "category": "question"},
                headers=headers,
            ).status_code
            == 200
        )
        assert (
            client.put(
                "/api/messages/missing/label",
                json={"important": True, "category": "question"},
                headers=headers,
            ).status_code
            == 404
        )


def test_metrics_exact():
    assert percentile([1, 2, 3, 4], 0.5) == 2.5
    assert percentile([1, 2, 3, 4], 0.95) == pytest.approx(3.85)
    result = quality([True, True, False, False], [True, False, True, False])
    assert result["precision"] == result["recall"] == result["f1"] == 0.5
    assert result["false_negative_rate"] == 0.5
    assert quality([], [])["recall"] is None
    assert summarize([], 0)["p95_latency_ms"] is None


async def test_instagram_pagination_bearer_and_outbound_exclusion():
    requests = []

    def handler(request):
        requests.append(request)
        path = request.url.path
        if path.endswith("/conversations"):
            if request.url.params.get("after"):
                return httpx.Response(200, json={"data": []})
            return httpx.Response(
                200,
                json={
                    "data": [{"id": "thread"}],
                    "paging": {
                        "next": "https://evil.example/?access_token=secret",
                        "cursors": {"after": "cursor"},
                    },
                },
            )
        if path.endswith("/thread"):
            return httpx.Response(200, json={"messages": {"data": [{"id": "m1"}, {"id": "m2"}]}})
        return httpx.Response(
            200,
            json={
                "id": path.rsplit("/", 1)[1],
                "created_time": "2026-01-01T12:00:00+0000",
                "from": {"id": "me" if path.endswith("m2") else "other", "username": "Alex"},
                "message": "Can you help?",
            },
        )

    source = InstagramMessageSource(
        Config(meta_token="test-only", meta_account_id="me", meta_account_type="BUSINESS"),
        transport=httpx.MockTransport(handler),
    )
    results = await source.get_new_messages()
    assert len(results) == 1 and results[0].external_id == "m1"
    assert all(r.url.host == "graph.instagram.com" for r in requests)
    assert all("access_token" not in r.url.params for r in requests)
    assert all(r.headers["Authorization"] == "Bearer test-only" for r in requests)
    await source.close()


async def test_instagram_retry_rate_limit(monkeypatch):
    waits = []

    async def sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr("backend.app.ingestion.sources.asyncio.sleep", sleep)
    responses = iter(
        [
            httpx.Response(429, headers={"Retry-After": "2"}, json={"error": {"code": 4}}),
            httpx.Response(200, json={"data": []}),
        ]
    )
    source = InstagramMessageSource(
        Config(meta_token="test-only", meta_account_id="me", meta_account_type="CREATOR"),
        transport=httpx.MockTransport(lambda _: next(responses)),
    )
    assert await source.get_new_messages() == []
    assert waits == [2]
    await source.close()


def test_professional_required():
    with pytest.raises(ValueError):
        InstagramMessageSource(Config(meta_token="test-only", meta_account_id="me"))


def test_synthetic_dataset():
    rows = [json.loads(s) for s in Path("benchmarks/data/synthetic.jsonl").read_text().splitlines()]
    assert len(rows) >= 200 and all(r["synthetic"] for r in rows)
    assert len({r["external_id"] for r in rows}) == len(rows)
    assert any(r["context"] for r in rows)


async def test_notification_error_does_not_stop_worker(tmp_path, monkeypatch):
    config = Config(database_path=tmp_path / "notify.db", fixture=True)
    worker = Worker(config)

    async def unavailable(**kwargs):
        raise RuntimeError("OS permission denied")

    async def authorized():
        return True

    monkeypatch.setattr(worker.notifier.notifier, "request_authorisation", authorized)
    monkeypatch.setattr(worker.notifier.notifier, "send", unavailable)
    await worker.tick()
    assert worker.notifier.last_error is not None
    assert all(row["status"] == "done" for row in worker.store.records())
    await worker.close()


async def test_invalid_jsonl_line_does_not_hide_valid_messages(tmp_path):
    (tmp_path / "input.jsonl").write_text("not json\n" + message().model_dump_json() + "\n")
    source = FileMessageSource(tmp_path)
    assert len(await source.get_new_messages()) == 1
    assert source.invalid_files == 1


def test_failed_inference_is_counted():
    metrics = summarize([{"classification": None, "llm_calls": 3, "inference_ms": 25}], 1)
    assert metrics["messages_sent_to_ollama"] == 1
    assert metrics["llm_calls"] == 3
    assert metrics["ollama_invocation_pct"] == 100
    assert metrics["messages_processed"] == 0


async def test_settings_save_does_not_wait_for_inference_batch(tmp_path):
    app = create_app(
        Config(database_path=tmp_path / "responsive.db", fixture=True), run_worker=False
    )
    async with app.router.lifespan_context(app):
        async with app.state.worker.lock:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://localhost"
            ) as client:
                response = await asyncio.wait_for(
                    client.put(
                        "/api/settings",
                        json=Settings(threshold=0.8, notifications=False).model_dump(),
                        headers={"X-PriorInbox": "local"},
                    ),
                    timeout=0.5,
                )
                assert response.status_code == 200
                assert app.state.worker.settings.threshold == 0.8


async def test_model_changed_during_validation_is_checked_before_inference(monkeypatch):
    worker = Worker(Config(fixture=False, persist_raw=False))
    checked = []
    original_model = worker.settings.model

    async def check_model(model):
        checked.append(model)
        if len(checked) == 1:
            worker.settings = Settings(model="another-local-model", notifications=False)
        else:
            raise ValueError("Replacement model does not have local weights")

    monkeypatch.setattr(worker.pipeline, "check_model", check_model)
    await worker.tick()
    assert checked == [original_model, "another-local-model"]
    assert worker.verified_model == original_model
    assert all(row["status"] == "pending" for row in worker.store.records())
    assert "unavailable" in worker.health
    await worker.close()
