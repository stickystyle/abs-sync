from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os

from dotenv import load_dotenv


@dataclass
class Config:
    """Configuration loaded from environment variables."""

    source_url: str
    source_api_key: str
    dest_url: str
    dest_api_key: str
    dest_library_id: str
    download_path: Path
    source_collection_name: str = "Download"
    synced_collection_name: str = "Synced"
    log_path: Path = field(default_factory=lambda: Path("./logs"))

    @classmethod
    def from_env(cls, env_file: Optional[Path] = None) -> "Config":
        """Load configuration from environment variables."""
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        def require_env(name: str) -> str:
            value = os.getenv(name)
            if not value:
                raise ValueError(f"Missing required environment variable: {name}")
            return value

        return cls(
            source_url=require_env("SOURCE_URL").rstrip("/"),
            source_api_key=require_env("SOURCE_API_KEY"),
            dest_url=require_env("DEST_URL").rstrip("/"),
            dest_api_key=require_env("DEST_API_KEY"),
            dest_library_id=require_env("DEST_LIBRARY_ID"),
            download_path=Path(require_env("DOWNLOAD_PATH")),
            source_collection_name=os.getenv("SOURCE_COLLECTION_NAME", "Download"),
            synced_collection_name=os.getenv("SYNCED_COLLECTION_NAME", "Synced"),
            log_path=Path(os.getenv("LOG_PATH", "./logs")),
        )
