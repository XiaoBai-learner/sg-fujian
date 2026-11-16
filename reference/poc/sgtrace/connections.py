"""数据连通：只支持库表形式的结构化数据源，只读 information_schema。

内置两个连接：
  local-mysql  .env 里配置的 MySQL（只展示四个演示库，不暴露同实例上的其他库）
  ddl-files    data/inputs/ddl/mysql/*.sql（没有 MySQL 时的元数据来源）
用户新增的 MySQL 连接只保存在服务端内存，重启即失效；密码任何接口都不返回。
公网模式禁止新增连接和测试连接，防止被当作内网探测跳板。
"""
import os
import re
import threading
import time
import uuid

import pymysql

from . import metadata
from .config import SYSTEM_TITLES, mysql_config

TYPES = [
    {"type": "mysql", "label": "MySQL", "available": True},
    {"type": "ddl", "label": "DDL 文件导入", "available": True},
    {"type": "oracle", "label": "Oracle", "available": False},
    {"type": "postgresql", "label": "PostgreSQL", "available": False},
    {"type": "sqlserver", "label": "SQL Server", "available": False},
    {"type": "dameng", "label": "达梦 DM", "available": False},
    {"type": "maxcompute", "label": "MaxCompute", "available": False},
]
_HOST = re.compile(r"^[A-Za-z0-9.\-]{1,253}$")
_NAME = re.compile(r"^[A-Za-z0-9_$\-]{1,64}$")

_lock = threading.Lock()
_custom = {}            # id -> {"id","name","type","host","port","user","password","databases","created_by",...}
_status = {}            # id -> {"state","message","checked_at","tables"}


def _connect(host, port, user, password, database=None):
    return pymysql.connect(host=host, port=int(port), user=user, password=password, database=database,
                           charset="utf8mb4", connect_timeout=5, read_timeout=15, write_timeout=15)


def _readable(exc):
    if isinstance(exc, pymysql.err.OperationalError):
        code = exc.args[0] if exc.args else 0
        if code == 1045:
            return "认证失败：账号或密码错误"
        if code == 1044 or code == 1049:
            return "没有权限访问该库，或库不存在"
        if code in (2003, 2005):
            return "无法连接到主机：请检查地址、端口和网络"
        if code == 2013:
            return "连接超时"
    return "连接失败"


def _builtin():
    out = []
    cfg = mysql_config()
    if cfg:
        out.append({"id": "local-mysql", "name": os.environ.get("SGTRACE_MYSQL_NAME", "本机 MySQL（演示库）"), "type": "mysql", "builtin": True,
                    "host": cfg.host, "port": cfg.port, "user": cfg.user, "databases": list(metadata.ALL_DBS)})
    out.append({"id": "ddl-files", "name": "DDL 文件（data/inputs/ddl/mysql）", "type": "ddl", "builtin": True,
                "host": "", "port": None, "user": "", "databases": list(metadata.ALL_DBS)})
    return out


def _public_view(c, public):
    v = {k: c[k] for k in ("id", "name", "type", "builtin", "databases")}
    v["address"] = "" if public or c["type"] == "ddl" else f"{c['host']}:{c['port']}"
    v["user"] = "" if public else c.get("user", "")
    v["created_by"] = c.get("created_by", "")
    v["status"] = _status.get(c["id"], {"state": "unknown", "message": "未测试", "checked_at": None, "tables": None})
    return v


def _get(cid):
    for c in _builtin():
        if c["id"] == cid:
            if c["type"] == "mysql":
                cfg = mysql_config()
                c = {**c, "password": cfg.password}
            return c
    with _lock:
        c = _custom.get(cid)
    if not c:
        raise KeyError(cid)
    return c


def list_connections(public):
    items = _builtin()
    with _lock:
        items += list(_custom.values())
    return [_public_view(c, public) for c in items]


def validate(body):
    host, user = str(body.get("host", "")).strip(), str(body.get("user", "")).strip()
    try:
        port = int(body.get("port") or 3306)
    except (TypeError, ValueError):
        raise ValueError("端口必须是数字") from None
    dbs = body.get("databases") or []
    if isinstance(dbs, str):
        dbs = [x.strip() for x in dbs.split(",") if x.strip()]
    if body.get("type", "mysql") != "mysql":
        raise ValueError("一期只支持 MySQL 连接，其他类型即将支持")
    if not _HOST.match(host):
        raise ValueError("主机地址格式不正确")
    if not 1 <= port <= 65535:
        raise ValueError("端口超出范围")
    if not user or len(user) > 64:
        raise ValueError("请填写账号")
    if not dbs or len(dbs) > 20 or not all(_NAME.match(d) for d in dbs):
        raise ValueError("请填写要采集的库名（逗号分隔，最多 20 个）")
    name = str(body.get("name") or f"{host}:{port}").strip()[:60]
    return {"type": "mysql", "name": name, "host": host, "port": port, "user": user,
            "password": str(body.get("password", ""))[:256], "databases": dbs}


def _count_tables(c):
    conn = _connect(c["host"], c["port"], c["user"], c["password"])
    try:
        with conn.cursor() as cur:
            ph = ",".join(["%s"] * len(c["databases"]))
            cur.execute(f"SELECT TABLE_SCHEMA, COUNT(*) FROM information_schema.TABLES "
                        f"WHERE TABLE_SCHEMA IN ({ph}) GROUP BY TABLE_SCHEMA", c["databases"])
            return dict(cur.fetchall())
    finally:
        conn.close()


def test(c):
    """测试连接：返回每个库能看到的表数量。只查 information_schema。"""
    if c["type"] == "ddl":
        meta = metadata.from_ddl_files()
        return {"ok": True, "message": "已解析 DDL 文件", "tables": {db: len(t) for db, t in meta.items()}}
    try:
        tables = _count_tables(c)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "message": _readable(e), "tables": {}}
    missing = [d for d in c["databases"] if d not in tables]
    msg = "连接成功" if not missing else f"连接成功，但看不到库：{', '.join(missing)}"
    return {"ok": True, "message": msg, "tables": tables}


def refresh(cid):
    c = _get(cid)
    r = test(c)
    _status[cid] = {"state": "ok" if r["ok"] else "error", "message": r["message"],
                    "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"), "tables": r["tables"]}
    return _status[cid]


def add(body, user):
    c = validate(body)
    r = test(c)
    if not r["ok"]:
        raise ValueError(r["message"])
    cid = "conn-" + uuid.uuid4().hex[:8]
    c.update({"id": cid, "builtin": False, "created_by": user})
    with _lock:
        if len(_custom) >= 20:
            raise ValueError("连接数量已达上限")
        _custom[cid] = c
    _status[cid] = {"state": "ok", "message": r["message"], "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "tables": r["tables"]}
    return cid


def remove(cid):
    with _lock:
        if cid not in _custom:
            raise KeyError(cid)
        del _custom[cid]
    _status.pop(cid, None)


def tables(cid, db):
    c = _get(cid)
    if db not in c["databases"]:
        raise KeyError(db)
    if c["type"] == "ddl":
        meta = metadata.from_ddl_files().get(db, {})
        return [{"name": t.name, "comment": t.comment, "columns": len(t.columns)} for t in meta.values()]
    conn = _connect(c["host"], c["port"], c["user"], c["password"])
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT t.TABLE_NAME, t.TABLE_COMMENT, COUNT(c.COLUMN_NAME) FROM information_schema.TABLES t "
                        "LEFT JOIN information_schema.COLUMNS c ON c.TABLE_SCHEMA=t.TABLE_SCHEMA AND "
                        "c.TABLE_NAME=t.TABLE_NAME WHERE t.TABLE_SCHEMA=%s GROUP BY t.TABLE_NAME, t.TABLE_COMMENT "
                        "ORDER BY t.TABLE_NAME", (db,))
            return [{"name": n, "comment": cm or "", "columns": k} for n, cm, k in cur.fetchall()]
    finally:
        conn.close()


def columns(cid, db, table):
    c = _get(cid)
    if db not in c["databases"]:
        raise KeyError(db)
    if c["type"] == "ddl":
        t = metadata.from_ddl_files().get(db, {}).get(table)
        if t is None:
            raise KeyError(table)
        return {"name": t.name, "comment": t.comment, "primary_key": t.primary_key, "unique_keys": t.unique_keys,
                "columns": [{"name": x.name, "type": x.data_type, "nullable": x.nullable, "comment": x.comment,
                             "primary_key": x.name in t.primary_key} for x in t.columns]}
    conn = _connect(c["host"], c["port"], c["user"], c["password"])
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT TABLE_COMMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
                        (db, table))
            row = cur.fetchone()
            if row is None:
                raise KeyError(table)
            cur.execute("SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_COMMENT, COLUMN_KEY "
                        "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s "
                        "ORDER BY ORDINAL_POSITION", (db, table))
            cols = [{"name": n, "type": t, "nullable": nl == "YES", "comment": cm or "", "primary_key": k == "PRI"}
                    for n, t, nl, cm, k in cur.fetchall()]
    finally:
        conn.close()
    return {"name": table, "comment": row[0] or "", "primary_key": [x["name"] for x in cols if x["primary_key"]],
            "unique_keys": [], "columns": cols}


def system_title(db):
    return SYSTEM_TITLES.get(db, "")


def clear():
    with _lock:
        _custom.clear()
    _status.clear()
