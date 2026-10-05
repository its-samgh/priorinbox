import asyncio
import time

from backend.app.classifier.pipeline import ClassificationError, Pipeline
from backend.app.config import Config
from backend.app.ingestion.sources import (
    FileMessageSource,
    InstagramMessageSource,
    MessageSource,
    MockMessageSource,
)
from backend.app.models.schemas import Settings
from backend.app.models.store import Store
from backend.app.notifications.desktop import Notifier


class Worker:
    def __init__(self, config: Config):
        self.config = config
        self.store = Store(config.database_path, config.persist_raw)
        self.settings = self.store.settings(Settings(model=config.model))
        self.pipeline = Pipeline(config.ollama_url, config.fixture)
        self.notifier = Notifier()
        self.source: MessageSource
        if config.source == "mock":
            self.source = MockMessageSource()
        elif config.source == "file":
            self.source = FileMessageSource(config.input_dir)
        elif config.source == "instagram":
            self.source = InstagramMessageSource(config)
        else:
            raise ValueError("Source must be mock, file or instagram")
        self.started = time.perf_counter()
        self.health: str = (
            "Fixture mode · simulated classifications" if config.fixture else "Starting"
        )
        self.source_error: str | None = None
        self.verified_model: str | None = None
        self.lock = asyncio.Lock()

    async def tick(self) -> None:
        async with self.lock:
            try:
                for message in await self.source.get_new_messages():
                    self.store.add(message)
                self.source_error = None
                if isinstance(self.source, FileMessageSource) and self.source.invalid_files:
                    self.source_error = (
                        "Some local files/records are invalid; check the import format"
                    )
            except Exception:
                self.source_error = "Ingestion failed; check source configuration. Will retry."
            if not self.config.fixture:
                try:
                    model = self.settings.model
                    if self.verified_model != model:
                        await self.pipeline.check_model(model)
                        self.verified_model = model
                    self.health = "Local Ollama ready"
                except Exception:
                    self.health = (
                        f"Ollama unavailable or local model missing. Run: "
                        f"ollama pull {self.settings.model}"
                    )
                    return
            for message in self.store.pending():
                settings = self.settings.model_copy()
                if not self.config.fixture and self.verified_model != settings.model:
                    try:
                        await self.pipeline.check_model(settings.model)
                        self.verified_model = settings.model
                    except Exception:
                        self.health = f"Local model unavailable. Run: ollama pull {settings.model}"
                        return
                try:
                    context = self.store.context(message, settings.context_messages)
                    result = await self.pipeline.classify(message, context, settings)
                    self.store.save_result(message.id, result)
                    if await self.notifier.send(message, result, self.settings):
                        self.store.notified(message.id)
                except ClassificationError as exc:
                    self.store.fail(message.id, exc.calls, exc.inference_ms)
                    self.health = "Some classifications failed; retained for retry"
                except Exception:
                    self.store.fail(message.id)
                    self.health = "Processing error; retained for retry"

    async def run(self) -> None:
        failures = 0
        while True:
            try:
                await self.tick()
                failures = min(failures + 1, 5) if self.source_error else 0
            except Exception:
                failures = min(failures + 1, 5)
                self.health = "Worker error; retrying with backoff"
            await asyncio.sleep(min(300, self.settings.polling_interval * 2**failures))

    async def close(self) -> None:
        await self.pipeline.close()
        if isinstance(self.source, InstagramMessageSource):
            await self.source.close()
        self.store.engine.dispose()
