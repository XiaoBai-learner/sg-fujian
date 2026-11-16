"""Environment-backed formal application settings."""
from dataclasses import dataclass
import os
from pathlib import Path
from sqlalchemy.engine import make_url


@dataclass(frozen=True, repr=False)
class Settings:
    database_url: str
    storage_root: Path
    app_secret: str
    max_material_bytes: int
    job_poll_interval_seconds: int
    allowed_origins: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Settings":
        database_url = os.environ.get("DATABASE_URL", "").strip()
        if not database_url:
            raise ValueError("DATABASE_URL is required")
        if not database_url.startswith(("sqlite+aiosqlite://", "mysql+asyncmy://")):
            raise ValueError("DATABASE_URL must use sqlite+aiosqlite or mysql+asyncmy")
        try:
            max_material_bytes = int(os.environ.get("MAX_MATERIAL_BYTES", str(20 * 1024 * 1024)))
        except ValueError as error:
            raise ValueError("MAX_MATERIAL_BYTES must be an integer") from error
        if max_material_bytes <= 0:
            raise ValueError("MAX_MATERIAL_BYTES must be greater than zero")
        try:
            poll = int(os.environ.get("JOB_POLL_INTERVAL_SECONDS", "2"))
        except ValueError as error:
            raise ValueError("JOB_POLL_INTERVAL_SECONDS must be an integer") from error
        if poll <= 0:
            raise ValueError("JOB_POLL_INTERVAL_SECONDS must be greater than zero")
        origins = tuple(item.strip() for item in os.environ.get("ALLOWED_ORIGINS", "").split(",") if item.strip())
        return cls(
            database_url=database_url,
            storage_root=Path(os.environ.get("STORAGE_ROOT", "./var/storage")).resolve(),
            app_secret=os.environ.get("APP_SECRET", ""),
            max_material_bytes=max_material_bytes,
            job_poll_interval_seconds=poll,
            allowed_origins=origins,
        )

    def __repr__(self) -> str:
        safe_database_url = make_url(self.database_url).render_as_string(hide_password=True)
        return (
            "Settings(database_url={!r}, storage_root={!r}, app_secret=<redacted>, "
            "max_material_bytes={!r}, job_poll_interval_seconds={!r}, allowed_origins={!r})"
        ).format(
            safe_database_url,
            self.storage_root,
            self.max_material_bytes,
            self.job_poll_interval_seconds,
            self.allowed_origins,
        )
