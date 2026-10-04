import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import (
    Boolean,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.pool import StaticPool

from backend.app.models.schemas import Classification, IncomingMessage, Label, Settings


class Base(DeclarativeBase):
    pass


class MessageRow(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("source", "external_id"),)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String)
    external_id: Mapped[str] = mapped_column(String)
    payload: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending")
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    llm_calls: Mapped[int] = mapped_column(Integer, default=0)
    inference_ms: Mapped[float] = mapped_column(Float, default=0)
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)


class SettingRow(Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[str] = mapped_column(Text)


class Store:
    def __init__(self, path: Path, persist: bool = True):
        if persist:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.engine = create_engine(
            f"sqlite:///{path}" if persist else "sqlite://",
            connect_args={"check_same_thread": False},
            **({} if persist else {"poolclass": StaticPool}),
        )
        Base.metadata.create_all(self.engine)
        if persist:
            path.chmod(0o600)

    def add(self, message: IncomingMessage) -> bool:
        with Session(self.engine) as session:
            exists = session.scalar(
                select(MessageRow.id).where(
                    MessageRow.source == message.source,
                    MessageRow.external_id == message.external_id,
                )
            )
            if exists:
                return False
            session.add(
                MessageRow(
                    id=message.id,
                    source=message.source,
                    external_id=message.external_id,
                    payload=message.model_dump_json(),
                )
            )
            session.commit()
        return True

    def pending(self, limit: int = 50) -> list[IncomingMessage]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(MessageRow)
                .where(MessageRow.status != "done")
                .order_by(MessageRow.attempts, MessageRow.id)
                .limit(limit)
            )
            return [IncomingMessage.model_validate_json(row.payload) for row in rows]

    def save_result(self, id: str, result: Classification) -> None:
        with Session(self.engine) as session:
            row = session.get(MessageRow, id)
            assert row
            row.result, row.status = result.model_dump_json(), "done"
            row.attempts += 1
            row.llm_calls += result.llm_calls
            row.inference_ms += result.inference_ms
            session.commit()

    def fail(self, id: str, calls: int = 0, inference_ms: float = 0) -> None:
        with Session(self.engine) as session:
            row = session.get(MessageRow, id)
            assert row
            row.status = "error"
            row.attempts += 1
            row.llm_calls += calls
            row.inference_ms += inference_ms
            session.commit()

    def notified(self, id: str) -> None:
        with Session(self.engine) as session:
            row = session.get(MessageRow, id)
            assert row
            row.notification_sent = True
            session.commit()

    def label(self, id: str, label: Label) -> bool:
        with Session(self.engine) as session:
            row = session.get(MessageRow, id)
            if not row:
                return False
            row.label = label.model_dump_json()
            session.commit()
            return True

    def records(self) -> list[dict]:
        with Session(self.engine) as session:
            rows = session.scalars(select(MessageRow))
            return [
                {
                    **json.loads(row.payload),
                    "status": row.status,
                    "classification": json.loads(row.result) if row.result else None,
                    "label": json.loads(row.label) if row.label else None,
                    "attempts": row.attempts,
                    "llm_calls": row.llm_calls,
                    "inference_ms": row.inference_ms,
                    "notification_sent": row.notification_sent,
                }
                for row in rows
            ]

    def context(self, message: IncomingMessage, count: int) -> list[str]:
        if not count:
            return []
        rows = [
            r
            for r in self.records()
            if r["source"] == message.source
            and r["conversation_id"] == message.conversation_id
            and r["id"] != message.id
            and datetime.fromisoformat(r["timestamp"]).astimezone(UTC) < message.timestamp
        ]
        return [r["text"] for r in sorted(rows, key=lambda r: r["timestamp"])[-count:]]

    def settings(self, default: Settings) -> Settings:
        with Session(self.engine) as session:
            row = session.get(SettingRow, 1)
            return Settings.model_validate_json(row.payload) if row else default

    def save_settings(self, settings: Settings) -> None:
        with Session(self.engine) as session:
            session.merge(SettingRow(id=1, payload=settings.model_dump_json()))
            session.commit()
