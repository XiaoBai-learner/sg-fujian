import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from sgtrace_app.config import Settings
from sgtrace_app.infrastructure.db.models import Base, JobModel
from sgtrace_app.infrastructure.db.repositories import JobRepository
from sgtrace_app.infrastructure.db.session import create_session_factory


def test_database_schema_and_job_claim_are_isolated(tmp_path):
    asyncio.run(_test_database_schema_and_job_claim_are_isolated(tmp_path))


async def _test_database_schema_and_job_claim_are_isolated(tmp_path):
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'app.db'}",
        storage_root=tmp_path / "storage",
        app_secret="test",
        max_material_bytes=1024,
        job_poll_interval_seconds=1,
        allowed_origins=(),
    )
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = create_session_factory(engine)
    async with factory() as session:
        repository = JobRepository(session)
        job = await repository.enqueue("parse_material", {"material_id": "m-1"}, "idem-1")
        claimed = await repository.claim_next("worker-a")
        assert claimed.id == job.id
        assert await repository.claim_next("worker-b") is None
        await session.commit()
        saved = await session.scalar(select(JobModel).where(JobModel.id == job.id))
        assert saved is not None and saved.status == "running"
    await engine.dispose()
