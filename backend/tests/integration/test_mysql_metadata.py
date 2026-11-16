import asyncio
import os

import pytest

from sgtrace_app.modules.sources.metadata.mysql import MySQLMetadataReader, MySQLSettings


pytestmark = pytest.mark.skipif(
    os.environ.get("MYSQL_INTEGRATION") != "1",
    reason="set MYSQL_INTEGRATION=1 to run against the local MySQL configured in .env",
)


def test_local_mysql_metadata_is_read_only_and_contains_yx186():
    asyncio.run(_run())


async def _run():
    reader = MySQLMetadataReader(MySQLSettings.from_env("yx186"))
    try:
        await reader.ping()
        tables = await reader.read()
        cons = next(table for table in tables if table.name == "C_CONS")
        assert cons.schema == "yx186"
        assert "CONS_NO" in {column.name for column in cons.columns}
        assert "CONS_ID" in cons.primary_key
    finally:
        await reader.close()
