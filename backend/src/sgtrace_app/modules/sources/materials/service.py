"""Material validation and persistence service."""
from dataclasses import dataclass
from pathlib import PurePath
from typing import BinaryIO
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....infrastructure.storage.base import Storage
from .models import MaterialModel, MaterialRevisionModel

ALLOWED_EXTENSIONS = {".txt", ".md", ".sql", ".pdf", ".csv", ".json"}


@dataclass(frozen=True)
class UploadMetadata:
    name: str
    category: str
    content_type: str
    size_bytes: int


@dataclass(frozen=True)
class MaterialRevision:
    id: str
    material_id: str
    revision: int
    parse_status: str
    content_uri: str
    parsed_uri: str | None


def validate_upload(name: str, content_type: str, content: BinaryIO, max_bytes: int) -> UploadMetadata:
    normalized = PurePath(name).name
    suffix = PurePath(normalized).suffix.lower()
    if not normalized or suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("unsupported material type")
    data = content.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("material exceeds maximum size")
    if suffix in {".txt", ".md", ".sql", ".csv", ".json"}:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("text material must be UTF-8") from error
    content.seek(0)
    category = "ddl" if suffix == ".sql" else "document"
    return UploadMetadata(normalized, category, content_type or "application/octet-stream", len(data))


class MaterialService:
    def __init__(self, session: AsyncSession, storage: Storage, max_material_bytes: int):
        self.session = session
        self.storage = storage
        self.max_material_bytes = max_material_bytes

    async def create_material(
        self,
        workspace_id: str,
        actor_id: str,
        name: str,
        category: str,
        content: BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> MaterialRevision:
        metadata = validate_upload(name, content_type, content, self.max_material_bytes)
        stored = self.storage.put(content, f"{workspace_id}/{uuid4()}", metadata.content_type, self.max_material_bytes)
        material = MaterialModel(
            workspace_id=workspace_id,
            name=metadata.name,
            category=category or metadata.category,
            created_by=actor_id,
        )
        self.session.add(material)
        await self.session.flush()
        revision = MaterialRevisionModel(
            material_id=material.id,
            revision=1,
            source_sha256=stored.sha256,
            size_bytes=stored.size_bytes,
            content_uri=stored.uri,
            parse_status="pending",
        )
        self.session.add(revision)
        await self.session.flush()
        return self._view(revision)

    async def get_revision(self, material_id: str, revision: int) -> MaterialRevision:
        item = await self.session.scalar(select(MaterialRevisionModel).where(
            MaterialRevisionModel.material_id == material_id,
            MaterialRevisionModel.revision == revision,
        ))
        if item is None:
            raise KeyError("material revision not found")
        return self._view(item)

    async def mark_parsed(self, revision_id: str, parsed_uri: str) -> None:
        item = await self.session.get(MaterialRevisionModel, revision_id)
        if item is None:
            raise KeyError("material revision not found")
        item.parse_status = "succeeded"
        item.parsed_uri = parsed_uri
        item.parse_error = None
        await self.session.flush()

    @staticmethod
    def _view(item: MaterialRevisionModel) -> MaterialRevision:
        return MaterialRevision(item.id, item.material_id, item.revision, item.parse_status, item.content_uri, item.parsed_uri)
