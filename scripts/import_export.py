"""Normalize a local Meta messages JSON export. Does not contact Instagram."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from backend.app.ingestion.sources import stable_export_id
from backend.app.models.schemas import IncomingMessage


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--self-name", required=True, help="Exact exported sender name to exclude")
    parser.add_argument("--output", type=Path, default=Path("data/incoming/export.jsonl"))
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    conversation = str(data.get("thread_path", data.get("title", args.input.stem)))
    rows = []
    for row in data["messages"]:
        if row["sender_name"] == args.self_name:
            continue
        rows.append(
            IncomingMessage(
                external_id=stable_export_id(conversation, row),
                conversation_id=conversation,
                sender_id=row["sender_name"],
                sender_display_name=row["sender_name"],
                text=row.get("content", "[Media or unsupported message; review export]"),
                timestamp=datetime.fromtimestamp(row["timestamp_ms"] / 1000, UTC),
                source="file",
            )
        )
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with args.output.open("x") as output:
        args.output.chmod(0o600)
        for message in sorted(rows, key=lambda m: m.timestamp):
            output.write(message.model_dump_json() + "\n")
    print(f"Normalized {len(rows)} messages locally. Original export remains unchanged.")


if __name__ == "__main__":
    main()
