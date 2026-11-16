"""公共工具：逻辑类型、各方言 DDL 渲染、确定性哈希。

逻辑类型（ltype）用元组表示：
  ("str", n)      字符串
  ("num", p, s)   定点数
  ("int",)        整数
  ("date",)       日期，统一存 'YYYY-MM-DD'
  ("dt",)         日期时间，统一存 'YYYY-MM-DD HH:MM:SS'
"""
import hashlib

SEED = 20251109


def stable_pct(key: str) -> int:
    """对字符串做稳定哈希，返回 0-99，用于确定性地决定“注释是否缺失”等。"""
    return int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16) % 100


def oracle_type(t):
    k = t[0]
    if k == "str":
        return f"VARCHAR2({t[1]})"
    if k == "num":
        return f"NUMBER({t[1]},{t[2]})"
    if k == "int":
        return "NUMBER(16)"
    return "DATE"


def mysql_type(t):
    k = t[0]
    if k == "str":
        return f"varchar({t[1]})"
    if k == "num":
        return f"decimal({t[1]},{t[2]})"
    if k == "int":
        return "bigint"
    if k == "date":
        return "date"
    return "datetime"


def odps_type(t):
    k = t[0]
    if k == "num":
        return f"DECIMAL({t[1]},{t[2]})"
    if k == "int":
        return "BIGINT"
    if k == "dt":
        return "DATETIME"
    return "STRING"


def sqlite_type(t):
    return {"str": "TEXT", "num": "REAL", "int": "INTEGER"}.get(t[0], "TEXT")


def sql_str(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"
