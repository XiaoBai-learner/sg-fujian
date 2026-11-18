"""Read-only MySQL information_schema adapter."""
from dataclasses import dataclass
import os

from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from .reader import ColumnDefinition, TableDefinition


@dataclass(frozen=True)
class MySQLSettings:
    host: str
    port: int
    username: str
    password: str
    database: str | None = None

    @classmethod
    def from_env(cls, database: str | None = None) -> "MySQLSettings":
        username = os.environ.get("MYSQL_USER", "").strip()
        if not username:
            raise ValueError("MYSQL_USER is required for MySQL metadata access")
        return cls(
            host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
            port=int(os.environ.get("MYSQL_PORT", "3306")),
            username=username,
            password=os.environ.get("MYSQL_PASSWORD", ""),
            database=database,
        )


class MySQLMetadataReader:
    def __init__(self, settings: MySQLSettings):
        self.settings = settings
        self.engine: AsyncEngine = create_async_engine(URL.create(
            "mysql+asyncmy",
            username=settings.username,
            password=settings.password,
            host=settings.host,
            port=settings.port,
        ), pool_pre_ping=True, connect_args={"connect_timeout":5,"read_timeout":15})

    async def close(self) -> None:
        await self.engine.dispose()

    async def ping(self) -> None:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def read(self) -> list[TableDefinition]:
        if not self.settings.database:
            raise ValueError("database is required for MySQL metadata access")
        schema = self.settings.database
        async with self.engine.connect() as connection:
            table_query = """
                SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_COMMENT
                FROM information_schema.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
            """
            table_query += " AND TABLE_SCHEMA = :schema"
            table_rows = (await connection.execute(text(table_query), {"schema": schema})).mappings().all()
            if not table_rows:
                return []
            column_query = """
                SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_COMMENT,
                       IS_NULLABLE, ORDINAL_POSITION
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = :schema
                ORDER BY TABLE_NAME, ORDINAL_POSITION
            """
            key_query = """
                SELECT TABLE_SCHEMA, TABLE_NAME, INDEX_NAME, COLUMN_NAME, NON_UNIQUE, SEQ_IN_INDEX
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = :schema
                ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX
            """
            grouped: dict[tuple[str, str], list[ColumnDefinition]] = {}
            keys: dict[tuple[str, str], dict[str, list[str]]] = {}
            all_columns = (await connection.execute(text(column_query), {"schema": schema})).mappings().all()
            all_keys = (await connection.execute(text(key_query), {"schema": schema})).mappings().all()
            for row in all_columns:
                key = (row["TABLE_SCHEMA"], row["TABLE_NAME"])
                grouped.setdefault(key, []).append(ColumnDefinition(
                    name=row["COLUMN_NAME"],
                    data_type=str(row["DATA_TYPE"]).lower(),
                    comment=row["COLUMN_COMMENT"] or "",
                    nullable=row["IS_NULLABLE"] == "YES",
                    position=int(row["ORDINAL_POSITION"]) - 1,
                ))
            for row in all_keys:
                if row["NON_UNIQUE"] != 0:
                    continue
                key = (row["TABLE_SCHEMA"], row["TABLE_NAME"])
                keys.setdefault(key, {}).setdefault(row["INDEX_NAME"], []).append(row["COLUMN_NAME"])
            definitions = []
            for table in table_rows:
                key = (table["TABLE_SCHEMA"], table["TABLE_NAME"])
                indexes = keys.get(key, {})
                primary = tuple(indexes.get("PRIMARY", []))
                uniques = tuple(tuple(cols) for name, cols in indexes.items() if name != "PRIMARY")
                definitions.append(TableDefinition(
                    schema=table["TABLE_SCHEMA"],
                    name=table["TABLE_NAME"],
                    comment=table["TABLE_COMMENT"] or "",
                    columns=tuple(grouped.get(key, [])),
                    primary_key=primary,
                    unique_keys=uniques,
                ))
            return definitions

    async def databases(self) -> list[str]:
        async with self.engine.connect() as connection:
            rows=(await connection.execute(text('SHOW DATABASES'))).scalars().all()
        return sorted(name for name in rows if name.lower() not in {'information_schema','performance_schema','mysql','sys'})

    async def export_ddl(self, databases: list[str]) -> str:
        visible=set(await self.databases())
        if not databases or not set(databases)<=visible:
            raise ValueError('请选择当前连接可访问的数据库')
        def quote(value): return '`'+value.replace('`','``')+'`'
        output=[]
        async with self.engine.connect() as connection:
            for schema in databases:
                output.append('USE '+quote(schema)+';')
                rows=(await connection.execute(text("SELECT TABLE_NAME,TABLE_TYPE FROM information_schema.TABLES WHERE TABLE_SCHEMA=:schema ORDER BY TABLE_NAME"),{'schema':schema})).all()
                for name,kind in rows:
                    # Metadata only: never execute uploaded or business SQL.
                    row=(await connection.execute(text('SHOW CREATE '+('VIEW ' if kind=='VIEW' else 'TABLE ')+quote(schema)+'.'+quote(name)))).first()
                    if row:
                        ddl=str(row[1])
                        if kind=='VIEW':
                            import re
                            ddl=re.sub(r'^CREATE\s+.*?\bVIEW\b','CREATE VIEW',ddl,count=1,flags=re.I|re.S)
                        output.append(ddl+';')
        if len(output)==len(databases): raise ValueError('所选数据库没有可采集的表或视图')
        body='\n\n'.join(output)
        if len(body.encode())>2_000_000: raise ValueError('结构超过 2 MB，请减少所选数据库')
        return body
