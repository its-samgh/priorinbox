import asyncio
import platform
import shutil
import sqlite3
import subprocess

from backend.app.classifier.pipeline import Pipeline
from backend.app.config import Config
from backend.app.models.schemas import Settings


async def main() -> None:
    print(f"Python: {platform.python_version()} (requires 3.12+)")
    if shutil.which("node"):
        print("Node:", subprocess.check_output(["node", "--version"], text=True).strip())
    else:
        print("Node: MISSING (install Node 22+)")
    print("Ollama CLI:", "installed" if shutil.which("ollama") else "missing")
    try:
        config = Config()
        settings = Settings(model=config.model)
        print("Configuration: valid; loopback inference enforced")
    except Exception:
        print("Configuration: invalid; check .env against .env.example")
        return
    print("Storage:", "persistent" if config.persist_raw else "ephemeral")
    try:
        if config.persist_raw:
            config.database_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        connection = sqlite3.connect(
            str(config.database_path) if config.persist_raw else ":memory:"
        )
        print("Database integrity:", connection.execute("PRAGMA quick_check").fetchone()[0])
        connection.close()
        if config.persist_raw:
            config.database_path.chmod(0o600)
    except Exception:
        print("Database: unavailable; check path permissions")
    pipeline = Pipeline(config.ollama_url)
    try:
        models = await pipeline.models()
        print("Ollama service: reachable")
        print("Installed local models:", ", ".join(models) or "(none)")
        await pipeline.check_model(settings.model)
        print("Configured model: local weights available")
    except Exception:
        print(f"Model unavailable. Start ollama serve; then run ollama pull {settings.model}")
    finally:
        await pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())
