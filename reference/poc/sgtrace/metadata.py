"""读取表结构元数据。

两种来源，产出同一结构：
  mysql  直接读本地 MySQL 的 information_schema（推荐，模拟客户库的系统目录）
  ddl    解析 data/inputs/ddl/mysql/*.sql（MySQL 不可用时的回退）

结构：{db: {table: Table}}
"""
from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp

from .config import INPUTS, PLATFORM_DB, SOURCE_DBS, mysql_config

ALL_DBS = (*SOURCE_DBS, PLATFORM_DB)


@dataclass
class Column:
    name: str
    data_type: str          # 小写基础类型：varchar/bigint/decimal/date/datetime
    comment: str
    nullable: bool
    position: int


@dataclass
class Table:
    db: str
    name: str
    comment: str
    columns: list = field(default_factory=list)
    primary_key: list = field(default_factory=list)
    unique_keys: list = field(default_factory=list)

    @property
    def qname(self):
        return f"{self.db}.{self.name}"

    def col(self, name):
        for c in self.columns:
            if c.name == name:
                return c
        return None


# ------------------------------------------------------------------ MySQL
def connect(database=None):
    import pymysql
    cfg = mysql_config()
    if cfg is None:
        raise RuntimeError("未配置 MySQL：请在项目根目录 .env 中设置 MYSQL_USER / MYSQL_PASSWORD")
    return pymysql.connect(host=cfg.host, port=cfg.port, user=cfg.user, password=cfg.password,
                           database=database, charset="utf8mb4", autocommit=True, connect_timeout=5)


def load_ddl_into_mysql():
    """把 data/inputs/ddl/mysql/*.sql 执行到本地 MySQL（DROP + CREATE，只有表结构）。"""
    conn = connect()
    created = {}
    try:
        with conn.cursor() as cur:
            for db in ALL_DBS:
                text = (INPUTS / "ddl" / "mysql" / f"{db}.sql").read_text(encoding="utf-8")
                n = 0
                for stmt in _split(text):
                    cur.execute(stmt)
                    n += stmt.upper().startswith("CREATE TABLE")
                created[db] = n
    finally:
        conn.close()
    return created


def _split(text):
    """按分号切分 DDL（DDL 内的注释字符串不含分号）。"""
    body = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("--"))
    return [s.strip() for s in body.split(";") if s.strip()]


def from_mysql():
    conn = connect()
    out = {db: {} for db in ALL_DBS}
    try:
        with conn.cursor() as cur:
            ph = ", ".join(["%s"] * len(ALL_DBS))
            cur.execute(f"SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_COMMENT FROM information_schema.TABLES "
                        f"WHERE TABLE_SCHEMA IN ({ph}) AND TABLE_TYPE = 'BASE TABLE'", ALL_DBS)
            for db, name, comment in cur.fetchall():
                out[db][name] = Table(db, name, comment or "")
            cur.execute(f"SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_COMMENT, IS_NULLABLE, "
                        f"ORDINAL_POSITION FROM information_schema.COLUMNS WHERE TABLE_SCHEMA IN ({ph}) "
                        f"ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION", ALL_DBS)
            for db, tname, cname, dtype, comment, nullable, pos in cur.fetchall():
                if tname in out[db]:
                    out[db][tname].columns.append(
                        Column(cname, dtype.lower(), comment or "", nullable == "YES", int(pos) - 1))
            cur.execute(f"SELECT TABLE_SCHEMA, TABLE_NAME, INDEX_NAME, COLUMN_NAME FROM information_schema.STATISTICS "
                        f"WHERE TABLE_SCHEMA IN ({ph}) AND NON_UNIQUE = 0 ORDER BY TABLE_SCHEMA, TABLE_NAME, "
                        f"INDEX_NAME, SEQ_IN_INDEX", ALL_DBS)
            idx = {}
            for db, tname, iname, cname in cur.fetchall():
                idx.setdefault((db, tname, iname), []).append(cname)
            for (db, tname, iname), cols in idx.items():
                t = out[db].get(tname)
                if t is None:
                    continue
                if iname == "PRIMARY":
                    t.primary_key = cols
                else:
                    t.unique_keys.append(cols)
    finally:
        conn.close()
    if not any(out.values()):
        raise RuntimeError("MySQL 中没有找到目标库，请先执行“建库”")
    return out


# ------------------------------------------------------------------ DDL 文件
def _base_type(kind):
    return kind.this.value.lower() if hasattr(kind.this, "value") else str(kind.this).lower()


def from_ddl_files():
    out = {db: {} for db in ALL_DBS}
    for db in ALL_DBS:
        text = (INPUTS / "ddl" / "mysql" / f"{db}.sql").read_text(encoding="utf-8")
        for stmt in sqlglot.parse(text, read="mysql"):
            if not isinstance(stmt, exp.Create) or stmt.kind != "TABLE":
                continue
            schema = stmt.this
            name = schema.this.name
            comment = ""
            props = stmt.args.get("properties")
            if props:
                for p in props.expressions:
                    if isinstance(p, exp.SchemaCommentProperty):
                        comment = p.this.name
            t = Table(db, name, comment)
            pos = 0
            for e in schema.expressions:
                if isinstance(e, exp.ColumnDef):
                    cmt, nullable = "", True
                    for c in e.constraints:
                        if isinstance(c.kind, exp.CommentColumnConstraint):
                            cmt = c.kind.this.name
                        elif isinstance(c.kind, exp.NotNullColumnConstraint):
                            nullable = False
                    t.columns.append(Column(e.name, _type_name(e.args["kind"]), cmt, nullable, pos))
                    pos += 1
                elif isinstance(e, exp.PrimaryKey):
                    t.primary_key = [x.name for x in e.expressions]
                elif isinstance(e, exp.UniqueColumnConstraint):
                    t.unique_keys.append([x.name for x in e.this.expressions])
            out[db][name] = t
    return out


def _type_name(kind):
    sql = kind.sql("mysql").lower()
    return sql.split("(")[0].strip()


def load(source="auto"):
    """返回 (元数据, 实际来源)。"""
    if source in ("auto", "mysql") and mysql_config() is not None:
        try:
            return from_mysql(), "mysql"
        except Exception:
            if source == "mysql":
                raise
    return from_ddl_files(), "ddl"
