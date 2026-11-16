"""字段级血缘：从 ODS 同步定义和 ETL 表达式推导边，并做闭包追溯到源表字段。

列标识约定：
  源表列   "yx186.C_CONS.CONS_NO"（schema.TABLE.COL）
  中台列   "dwd_yx_kh_jbxx.hh"（表.列，中台单项目，不带项目名）
"""
import re

from dataplatform import ETLS, build_ods
from sources import TABLES

KIND_RANK = {"direct": 0, "derived": 1, "aggregated": 2}
_AGG = re.compile(r"\b(SUM|COUNT|AVG|MAX|MIN)\s*\(", re.I)
_REF = re.compile(r"\b([a-z][a-z0-9]*)\.([a-z_][a-z0-9_]*)\b")
_STR = re.compile(r"'[^']*'")


def expr_refs(expr, aliases):
    clean = _STR.sub("''", expr)
    refs = []
    for a, c in _REF.findall(clean):
        if a in aliases:
            refs.append(f"{aliases[a]}.{c}")
    return list(dict.fromkeys(refs))


def expr_kind(expr):
    if _AGG.search(expr):
        return "aggregated"
    if re.fullmatch(r"[a-z][a-z0-9]*\.[a-z_][a-z0-9_]*", expr.strip()):
        return "direct"
    return "derived"


def build_edges():
    edges = []
    for o in build_ods():
        for c in o["cols"]:
            edges.append({"src": c["src"], "dst": f"{o['name']}.{c['name']}", "task": o["task"],
                          "task_type": "DI", "kind": "direct", "expr": c["src"].split(".")[-1],
                          "exported": True})
    for e in ETLS:
        for c in e["cols"]:
            for r in expr_refs(c["expr"], e["src"]):
                edges.append({"src": r, "dst": f"{e['name']}.{c['name']}", "task": e["task"],
                              "task_type": "ODPS_SQL", "kind": expr_kind(c["expr"]), "expr": c["expr"],
                              "exported": e["lineage_exported"]})
    return edges


def source_col_ids():
    return {f"{t['schema']}.{t['name']}.{c['name']}" for t in TABLES for c in t["cols"]}


class Lineage:
    def __init__(self):
        self.edges = build_edges()
        self.inbound = {}
        for ed in self.edges:
            self.inbound.setdefault(ed["dst"], []).append(ed)
        self.src_ids = source_col_ids()

    def trace(self, col):
        """返回 (源字段集合, 最强派生类型, 经过的边列表)。"""
        if col in self.src_ids:
            return {col}, "direct", []
        origins, kind, path = set(), "direct", []
        for ed in self.inbound.get(col, []):
            o, k, p = self.trace(ed["src"])
            origins |= o
            path += [ed] + p
            for kk in (k, ed["kind"]):
                if KIND_RANK[kk] > KIND_RANK[kind]:
                    kind = kk
        return origins, kind, path


# ---------------- 等价字段（宽松评测用） ----------------
def _col_index():
    idx = {}
    for t in TABLES:
        for c in t["cols"]:
            idx[f"{t['schema']}.{t['name']}.{c['name']}"] = (t, c)
    return idx


def canonical_root(col_id, idx=None):
    """沿外键 ref 追到被引用的根字段。"""
    idx = idx or _col_index()
    seen = set()
    while col_id in idx and idx[col_id][1]["ref"] and col_id not in seen:
        seen.add(col_id)
        col_id = idx[col_id][1]["ref"]
    return col_id


def equivalents(col_id):
    """同一根字段的其他非噪声源字段，例如工单的 CUST_NO 与营销 CONS_NO。"""
    idx = _col_index()
    root = canonical_root(col_id, idx)
    out = []
    for cid, (t, c) in idx.items():
        if cid != col_id and not t["noise"] and canonical_root(cid, idx) == root:
            out.append(cid)
    return sorted(out)
