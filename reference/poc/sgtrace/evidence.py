"""证据采集：字段级血缘、关联关系、热度。全部只读 data/inputs/。

血缘来源（可叠加，记录出处）：
  dataworks_export   DataWorks 血缘导出（不完整）
  task_sql           解析 DataWorks 任务 SQL 自行推导（补全缺失）
  naming_convention  ODS 命名约定 ods_<系统>_<表> 同名列（导出也缺时兜底）
关联来源：
  task_sql_join / hot_sql_join   ETL 和热点 SQL 中 JOIN ON / WHERE 的列等值条件
"""
import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp

from .config import INPUTS, PLATFORM_DB, SOURCE_DBS

KIND_RANK = {"direct": 0, "derived": 1, "aggregated": 2}


@dataclass
class Edge:
    src: str   # 源表列 "yx186.C_CONS.CONS_NO"；中台列 "dwd_yx_kh_jbxx.hh"
    dst: str
    kind: str
    expr: str = ""
    task: str = ""
    provenance: set = field(default_factory=set)


def _read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _projection_kind(node):
    if node.find(exp.AggFunc):
        return "aggregated"
    return "direct" if isinstance(node, exp.Column) else "derived"


def _alias_map(select):
    return {t.alias_or_name: t.name for t in select.find_all(exp.Table)}


def _col_pairs(node, aliases):
    """返回条件中所有 列 = 列 的等值对（已解析成 表.列）。"""
    out = []
    for eq in node.find_all(exp.EQ):
        left, right = eq.left, eq.right
        if isinstance(left, exp.Column) and isinstance(right, exp.Column) and left.table and right.table:
            lt, rt = aliases.get(left.table), aliases.get(right.table)
            if lt and rt and lt != rt:
                out.append((f"{lt}.{left.name}", f"{rt}.{right.name}"))
    return out


def parse_task_sql(text):
    """解析一个 INSERT OVERWRITE ... SELECT 任务，返回 (目标表, [(目标列, [来源列], kind, expr)], 等值关联对)。"""
    body = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("--")).strip().rstrip(";")
    stmt = sqlglot.parse_one(body, read="hive")
    target = stmt.this.find(exp.Table).name
    select = stmt.expression
    aliases = _alias_map(select)
    cols = []
    for proj in select.expressions:
        inner = proj.this if isinstance(proj, exp.Alias) else proj
        refs = []
        for c in inner.find_all(exp.Column):
            t = aliases.get(c.table)
            if t:
                refs.append(f"{t}.{c.name}")
        cols.append((proj.alias_or_name, list(dict.fromkeys(refs)), _projection_kind(inner), inner.sql()))
    joins = []
    for j in select.args.get("joins") or []:
        if j.args.get("on"):
            joins += _col_pairs(j.args["on"], aliases)
    return target, cols, joins


class Evidence:
    def __init__(self, meta, parse_tasks=True):
        self.meta = meta
        self.parse_tasks = parse_tasks
        self.edges = {}             # (src, dst) -> Edge
        self.joins = defaultdict(set)   # frozenset{a,b} -> {provenance}
        self.table_hits = defaultdict(int)   # 平台表 -> 热点 SQL 执行次数
        self.service_tables = defaultdict(int)  # 报表服务账号访问的表（页面取数）
        self.column_hits = defaultdict(int)
        self.stats = {}
        self._load_lineage_export()
        self._load_task_sql()
        self._naming_convention()
        self._load_hot_sql()
        self._index()

    # ---------------- 血缘
    def _add(self, src, dst, kind, prov, expr="", task=""):
        key = (src, dst)
        e = self.edges.get(key)
        if e is None:
            e = self.edges[key] = Edge(src, dst, kind, expr, task)
        elif KIND_RANK[kind] > KIND_RANK[e.kind]:
            e.kind = kind
        e.provenance.add(prov)
        e.expr = e.expr or expr
        e.task = e.task or task

    def _load_lineage_export(self):
        rows = _read_csv(INPUTS / "dataworks" / "lineage_export.csv")
        for r in rows:
            src = f"{r['src_table']}.{r['src_column']}"
            dst = f"{r['dst_table']}.{r['dst_column']}"
            # 导出里不带派生类型，先记 direct，任务 SQL 解析后会上调
            self._add(src, dst, "direct", "dataworks_export", task=r["task_name"])
        self.stats["export_edges"] = len(rows)

    def _load_task_sql(self):
        n = 0
        tasks = sorted((INPUTS / "dataworks" / "tasks").glob("*.sql")) if self.parse_tasks else []
        for p in tasks:
            target, cols, joins = parse_task_sql(p.read_text(encoding="utf-8"))
            for name, refs, kind, expr in cols:
                for r in refs:
                    self._add(r, f"{target}.{name}", kind, "task_sql", expr, p.stem)
                    n += 1
            for a, b in joins:
                self.joins[frozenset((a, b))].add("task_sql_join")
        self.stats["task_sql_files"] = len(tasks)
        self.stats["task_sql_edges"] = n

    def _naming_convention(self):
        plat = self.meta.get(PLATFORM_DB, {})
        n = 0
        for db in SOURCE_DBS:
            for t in self.meta.get(db, {}).values():
                ods = plat.get(f"ods_{db}_{t.name.lower()}")
                if ods is None:
                    continue
                for c in t.columns:
                    oc = ods.col(c.name.lower())
                    if oc is not None:
                        key = (f"{db}.{t.name}.{c.name}", f"{ods.name}.{oc.name}")
                        if key not in self.edges:
                            n += 1
                        self._add(*key, "direct", "naming_convention", c.name, f"di_{db}_{t.name.lower()}")
        self.stats["convention_edges"] = n

    # ---------------- 热点 SQL
    def _load_hot_sql(self):
        rows = _read_csv(INPUTS / "hot_sql" / "query_log.csv")
        for r in rows:
            n = int(r["exec_count_90d"])
            try:
                stmt = sqlglot.parse_one(r["sql"], read="mysql")
            except sqlglot.errors.ParseError:
                continue
            aliases = _alias_map(stmt)
            for t in set(aliases.values()):
                self.table_hits[t] += n
                if r["submitter"].startswith("rpt_"):
                    self.service_tables[t] += n
            for c in stmt.find_all(exp.Column):
                t = aliases.get(c.table) if c.table else (next(iter(aliases.values())) if len(aliases) == 1 else None)
                if t:
                    self.column_hits[f"{t}.{c.name}"] += n
            for a, b in _col_pairs(stmt, aliases):
                self.joins[frozenset((a, b))].add("hot_sql_join")
        self.stats["hot_sql"] = len(rows)
        self.stats["join_pairs"] = len(self.joins)

    # ---------------- 追溯
    def _index(self):
        self.inbound = defaultdict(list)
        self.outbound = defaultdict(list)
        for e in self.edges.values():
            self.inbound[e.dst].append(e)
            self.outbound[e.src].append(e)
        prov = defaultdict(int)
        for e in self.edges.values():
            for p in e.provenance:
                prov[p] += 1
        self.stats["edges_total"] = len(self.edges)
        self.stats["edges_only_from_parsing"] = sum(1 for e in self.edges.values()
                                                    if "dataworks_export" not in e.provenance)

    @staticmethod
    def is_source(col):
        return col.count(".") == 2 and col.split(".")[0] in SOURCE_DBS

    def trace(self, col, _seen=None):
        """中台列 → (源字段集合, 最强派生类型, 路径边列表)。"""
        if self.is_source(col):
            return {col}, "direct", []
        seen = _seen or set()
        if col in seen:
            return set(), "direct", []
        seen.add(col)
        origins, kind, path = set(), "direct", []
        for e in self.inbound.get(col, []):
            o, k, p = self.trace(e.src, seen)
            origins |= o
            path += [e] + p
            for kk in (k, e.kind):
                if KIND_RANK[kk] > KIND_RANK[kind]:
                    kind = kk
        return origins, kind, path

    def downstream_direct(self, col, _depth=0):
        """源字段经“直接搬运”到达的所有中台列（用于收集业务叫法）。"""
        out = []
        if _depth > 6:
            return out
        for e in self.outbound.get(col, []):
            if e.kind == "direct":
                out.append(e.dst)
                out += self.downstream_direct(e.dst, _depth + 1)
        return out

    def source_join_pairs(self):
        """把所有关联对追溯到源字段层面：返回 {frozenset(源列a, 源列b): {出处}}。"""
        out = defaultdict(set)
        for pair, prov in self.joins.items():
            a, b = tuple(pair)
            oa, ka, _ = self.trace(a)
            ob, kb, _ = self.trace(b)
            if ka != "direct" or kb != "direct":
                continue
            for x in oa:
                for y in ob:
                    if x != y and x.rsplit(".", 1)[0] != y.rsplit(".", 1)[0]:
                        out[frozenset((x, y))] |= prov
        return out

    def synced_source_tables(self):
        """有同步到中台（存在 DI 血缘）的源表。"""
        return {e.src.rsplit(".", 1)[0] for e in self.edges.values() if self.is_source(e.src)}


def strip_code_desc(comment):
    """“单位类型 02市 03县” → “单位类型”。"""
    return re.split(r"\s+\d", comment.strip())[0].strip()
