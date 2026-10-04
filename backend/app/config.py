from pathlib import Path
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PRIOR_", env_file=".env", extra="ignore")
    ollama_url: str = "http://localhost:11434"
    model: str = "qwen2.5:3b"
    source: str = "mock"
    fixture: bool = False
    persist_raw: bool = True
    database_path: Path = Path("data/priorinbox.sqlite3")
    input_dir: Path = Path("data/incoming")
    meta_token: str = ""
    meta_account_id: str = ""
    meta_account_type: str = ""
    meta_api_version: str = "v25.0"

    @field_validator("ollama_url")
    @classmethod
    def loopback_only(cls, value: str) -> str:
        url = urlparse(value)
        if (
            url.scheme != "http"
            or url.hostname not in {"localhost", "127.0.0.1", "::1"}
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.path not in {"", "/"}
        ):
            raise ValueError("Ollama must use a loopback HTTP endpoint without credentials")
        return value.rstrip("/")
