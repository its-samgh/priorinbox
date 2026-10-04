"""Local terminal labeling. Never prints data except in this interactive session."""

import argparse
import json
from pathlib import Path

from backend.app.models.schemas import Category, Label


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path("benchmarks/data/private/labeled.jsonl")
    )
    args = parser.parse_args()
    if args.output.resolve() == args.input.resolve():
        raise SystemExit("Use a separate output file")
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    existing = set()
    if args.output.exists():
        existing = {
            json.loads(line)["external_id"] for line in args.output.read_text().splitlines()
        }
    with args.output.open("a") as output:
        args.output.chmod(0o600)
        for line in args.input.read_text().splitlines():
            row = json.loads(line)
            if row["external_id"] in existing:
                continue
            print("\nContext:", row.get("context", []))
            print("Message:", row["text"])
            choice = input("Important? [y/n/s=skip/q=quit]: ").strip().lower()
            if choice == "q":
                break
            if choice not in {"y", "n"}:
                continue
            print("Categories:", ", ".join(c.value for c in Category))
            try:
                label = Label(
                    important=choice == "y", category=Category(input("Category: ").strip())
                )
            except ValueError:
                print("Invalid category; skipping")
                continue
            row["label"] = label.model_dump(mode="json")
            row["synthetic"] = False
            output.write(json.dumps(row) + "\n")
            output.flush()
            existing.add(row["external_id"])


if __name__ == "__main__":
    main()
