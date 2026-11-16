from hashlib import sha256
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....infrastructure.db.models import (
    MetadataColumnModel,
    MetadataSnapshotModel,
    MetadataTableModel,
    SourceConnectionModel,
)
from ..metadata.reader import parse_mysql_ddl
from ..metadata.mysql import MySQLMetadataReader, MySQLSettings


class SourceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_connection(self, workspace_id: str, name: str, kind: str, database: str | None):
        if kind not in {"ddl", "mysql"}:
            raise ValueError("unsupported source kind")
        source = SourceConnectionModel(
            workspace_id=workspace_id,
            name=name,
            kind=kind,
            database_name=database,
            last_status="unknown",
        )
        self.session.add(source)
        await self.session.flush()
        return source

    async def test_mysql(self, source_id: str):
        source = await self.session.get(SourceConnectionModel, source_id)
        if source is None:
            raise KeyError("source not found")
        if source.kind != "mysql":
            raise ValueError("source is not mysql")
        reader = MySQLMetadataReader(MySQLSettings.from_env(source.database_name))
        try:
            await reader.ping()
        finally:
            await reader.close()
        source.last_status = "ok"
        await self.session.flush()
        return {"source_id": source_id, "status": "ok"}

    async def refresh_mysql(self, source_id: str):
        source = await self.session.get(SourceConnectionModel, source_id)
        if source is None:
            raise KeyError("source not found")
        reader = MySQLMetadataReader(MySQLSettings.from_env(source.database_name))
        try:
            tables = await reader.read()
        finally:
            await reader.close()
        return await self._persist_snapshot(source, tables)

    async def list_connections(self, workspace_id: str):
        return (await self.session.scalars(select(SourceConnectionModel).where(
            SourceConnectionModel.workspace_id == workspace_id,
        ).order_by(SourceConnectionModel.created_at.desc()))).all()

    async def refresh_ddl(self, source_id: str, ddl: str):
        source = await self.session.get(SourceConnectionModel, source_id)
        if source is None:
            raise KeyError("source not found")
        tables = parse_mysql_ddl(ddl)
        return await self._persist_snapshot(source, tables, ddl.encode("utf-8"))

    async def _persist_snapshot(self, source, tables, source_bytes: bytes | None = None):
        previous = await self.session.scalar(select(func.max(MetadataSnapshotModel.revision)).where(
            MetadataSnapshotModel.source_id == source.id,
        ))
        revision = int(previous or 0) + 1
        snapshot = MetadataSnapshotModel(
            source_id=source.id,
            revision=revision,
            status="ready",
            source_sha256=sha256(source_bytes).hexdigest() if source_bytes is not None else None,
        )
        self.session.add(snapshot)
        await self.session.flush()
        for table in tables:
            row = MetadataTableModel(
                snapshot_id=snapshot.id,
                schema_name=table.schema,
                table_name=table.name,
                comment=table.comment,
                primary_key_json=list(table.primary_key),
            )
            self.session.add(row)
            await self.session.flush()
            for column in table.columns:
                self.session.add(MetadataColumnModel(
                    table_id=row.id,
                    name=column.name,
                    data_type=column.data_type,
                    comment=column.comment,
                    nullable=column.nullable,
                    position=column.position,
                ))
        source.last_status = "ok"
        await self.session.flush()
        return snapshot

    async def list_tables(self, source_id: str, revision: int):
        snapshot = await self.session.scalar(select(MetadataSnapshotModel).where(
            MetadataSnapshotModel.source_id == source_id,
            MetadataSnapshotModel.revision == revision,
        ))
        if snapshot is None:
            raise KeyError("snapshot not found")
        tables = (await self.session.scalars(select(MetadataTableModel).where(
            MetadataTableModel.snapshot_id == snapshot.id,
        ).order_by(MetadataTableModel.schema_name, MetadataTableModel.table_name))).all()
        return snapshot, tables

    async def list_columns(self, source_id: str, revision: int, table_name: str):
        snapshot, _ = await self.list_tables(source_id, revision)
        table = await self.session.scalar(select(MetadataTableModel).where(
            MetadataTableModel.snapshot_id == snapshot.id,
            MetadataTableModel.table_name == table_name,
        ))
        if table is None:
            raise KeyError("table not found")
        columns = (await self.session.scalars(select(MetadataColumnModel).where(
            MetadataColumnModel.table_id == table.id,
        ).order_by(MetadataColumnModel.position))).all()
        return table, columns
