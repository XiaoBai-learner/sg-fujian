import asyncio
from io import BytesIO

from sqlalchemy.ext.asyncio import create_async_engine

from sgtrace_app.infrastructure.db.models import Base
from sgtrace_app.infrastructure.storage.local import LocalStorage
from sgtrace_app.modules.sources.materials.service import MaterialService


def test_material_revision_is_immutable_and_parse_status_is_explicit(tmp_path):
    asyncio.run(_run(tmp_path))


async def _run(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'app.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    from sgtrace_app.infrastructure.db.session import create_session_factory
    factory = create_session_factory(engine)
    storage = LocalStorage(tmp_path / "storage")
    async with factory() as session:
        service = MaterialService(session, storage, max_material_bytes=1024)
        revision = await service.create_material(
            workspace_id="w1",
            actor_id="u1",
            name="业务说明.md",
            category="document",
            content=BytesIO("户号来自客户表".encode()),
        )
        assert revision.parse_status == "pending"
        await service.mark_parsed(revision.id, "parsed/material-1.json")
        saved = await service.get_revision(revision.material_id, revision.revision)
        assert saved.parse_status == "succeeded"
        assert saved.parsed_uri == "parsed/material-1.json"
        assert saved.content_uri.startswith("file://")
    await engine.dispose()
