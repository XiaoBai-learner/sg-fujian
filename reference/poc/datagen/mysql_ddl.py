"""把源系统与中台表结构渲染成 MySQL DDL，用于在本地 MySQL 建一份“只有 schema”的库。

客户真实环境：营销/采集是 Oracle，中台是 MaxCompute。本地统一落到 MySQL，作为 information_schema
元数据的替身。刻意不建外键约束（真实业务库普遍没有），关系要靠流水线自己推断。
"""
from common import mysql_type, sql_str

PLATFORM_DB = "sgfj_dataplatform"

# 业务唯一键（真实系统通常有唯一索引）
UNIQUE_KEYS = {
    ("yx186", "C_CONS"): ["CONS_NO"],
    ("yx186", "C_MP"): ["MP_NO"],
    ("yx186", "D_METER"): ["ASSET_NO"],
    ("cjxt", "R_TMNL_RUN"): ["TMNL_ASSET_NO"],
}


def _table(name, comment, cols, pk=None, uniques=()):
    pk_cols = [k.strip() for k in pk.split(",")] if pk else []
    lines = []
    for c in cols:
        null = " NOT NULL" if c["name"] in pk_cols or c["name"] in uniques else ""
        cm = f" COMMENT {sql_str(c['comment'])}" if c.get("comment") else ""
        lines.append(f"  `{c['name']}` {mysql_type(c['t'])}{null}{cm}")
    if pk_cols:
        lines.append("  PRIMARY KEY (" + ", ".join(f"`{k}`" for k in pk_cols) + ")")
    for u in uniques:
        lines.append(f"  UNIQUE KEY `UK_{name[:40]}_{u}` (`{u}`)")
    tc = f" COMMENT={sql_str(comment)}" if comment else ""
    return (f"DROP TABLE IF EXISTS `{name}`;\nCREATE TABLE `{name}` (\n" + ",\n".join(lines)
            + f"\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4{tc};")


def render(tables, ods, etls):
    """返回 {数据库名: DDL 文本}。"""
    out = {}
    for db in ("yx186", "cjxt", "kf95598"):
        parts = []
        for tb in [t for t in tables if t["schema"] == db]:
            comment = tb["comment"] if tb["tcmt"] else ""
            parts.append(_table(tb["name"], comment, tb["cols"], tb["key"],
                                UNIQUE_KEYS.get((db, tb["name"]), ())))
        out[db] = parts
    plat = [_table(o["name"], o["comment"], o["cols"]) for o in ods]
    plat += [_table(e["name"], e["comment"], e["cols"]) for e in etls]
    out[PLATFORM_DB] = plat
    return {db: (f"-- 本地 MySQL 替身库：{db}（只有表结构）\n"
                 f"CREATE DATABASE IF NOT EXISTS `{db}` DEFAULT CHARACTER SET utf8mb4;\nUSE `{db}`;\n\n"
                 + "\n\n".join(parts) + "\n") for db, parts in out.items()}
