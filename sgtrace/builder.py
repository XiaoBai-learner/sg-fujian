"""营销域本体与数据管道映射构建：表结构 + 血缘 + 热点 SQL → OntoWing model/pipeline 编辑器 JSON。

规则（全部可解释，每个产出都记录依据）：
  范围      同步到中台的源表（有 DI 血缘）；未同步的备份/临时表视为噪声剔除
  概念      一张源表一个概念；列结构完全相同的表（如当前表与历史表）合并为同一概念的多个绑定
  概念命名  领域词表（表名核心词）> 表注释 > 表名拆词
  标识      主键/唯一键中被外部引用最多的键作为实体标识；其余被引用的键生成“备用键绑定”
  关系      外键推断：列名同名或以“_<键名>”结尾 + 类型一致（命名约定），
            以及任务 SQL / 热点 SQL 中 JOIN 等值条件追溯到源字段（关联证据）
  属性      非外键列一列一属性；名称取 DDL 注释 > 领域词表；别名取血缘下游中台列的注释
"""
from collections import Counter, defaultdict

from .config import SOURCE_DBS, SYSTEM_TITLES
from .evidence import Evidence, strip_code_desc
from .glossary import COLUMN_EXACT, COLUMN_TOKENS, SENSITIVE_HINTS, TABLE_TERMS
from .text import camel, strip

DATATYPES = {"varchar": "string", "char": "string", "text": "string", "bigint": "integer", "int": "integer",
             "decimal": "decimal", "double": "decimal", "date": "date", "datetime": "datetime",
             "timestamp": "datetime"}
GENERIC_KEYS = {"ID"}  # 通用键名只在同一系统内做命名推断


def wing_datatype(t):
    return DATATYPES.get(t, "string")


def fact_plane(db, table):
    return {"teiid_id": "local-mysql", "data_source_id": str(SOURCE_DBS.index(db) + 1), "schema_name": db,
            "table_name": table, "active_vdb_version": "1", "data_source_revision": "1", "model_name": db,
            "query_availability": "available", "columns_truncated": False}


def _core_tokens(table_name):
    toks = table_name.upper().split("_")
    if len(toks) > 1 and len(toks[0]) == 1:
        toks = toks[1:]
    if toks and toks[-1] in ("HIS", "BAK", "TMP"):
        toks = toks[:-1]
    return tuple(toks)


def column_name_guess(col):
    """注释缺失时由领域词表推断中文名，返回 (名称, 依据)。"""
    up = col.upper()
    if up in COLUMN_EXACT:
        return COLUMN_EXACT[up], "glossary_exact"
    parts = [COLUMN_TOKENS.get(t) for t in up.split("_")]
    if parts and all(parts):
        return "".join(parts), "glossary_tokens"
    return col, "column_name"


def _signature(t):
    return tuple((c.name, c.data_type) for c in t.columns), tuple(t.primary_key)


class OntologyBuild:
    def __init__(self, meta, evidence: Evidence, meta_source=""):
        self.meta, self.ev, self.meta_source = meta, evidence, meta_source
        self.log = []
        self.decisions = []   # 供页面展示的构建依据
        self._scope()
        self._concepts()
        self._relations()
        self._identity()
        self._attributes()
        self._editors()

    # ------------------------------------------------------------ 范围
    def _scope(self):
        synced = self.ev.synced_source_tables()
        self.tables, self.excluded = [], []
        for db in SOURCE_DBS:
            for t in self.meta.get(db, {}).values():
                (self.tables if t.qname in synced else self.excluded).append(t)
        self.log.append(f"源表 {len(self.tables) + len(self.excluded)} 张：纳入 {len(self.tables)}，"
                        f"剔除 {len(self.excluded)}（未同步到中台）")
        for t in self.excluded:
            self.decisions.append({"type": "exclude_table", "table": t.qname, "reason": "无中台同步血缘，判定为备份/临时表"})

    # ------------------------------------------------------------ 概念
    def _concepts(self):
        groups = defaultdict(list)
        for t in self.tables:
            groups[(t.db, _signature(t))].append(t)
        self.concepts = {}        # concept_id -> dict
        self.table_concept = {}   # qname -> concept_id
        used = Counter()
        for (db, _), tables in groups.items():
            tables.sort(key=lambda t: (len(t.name), -self.ev.table_hits.get(f"ods_{t.db}_{t.name.lower()}", 0)))
            main = tables[0]
            term = TABLE_TERMS.get(_core_tokens(main.name))
            if term:
                cid, zh, top, cim = term
                basis = "glossary"
            else:
                cid = "".join(p.capitalize() for p in _core_tokens(main.name)) or main.name
                zh, top, cim = strip(main.comment) or main.name, None, ""
                basis = "table_comment" if main.comment else "table_name"
            used[cid] += 1
            if used[cid] > 1:
                cid = f"{cid}{used[cid]}"
            self.concepts[cid] = {"id": cid, "name": zh, "top_category": top, "cim": cim, "basis": basis,
                                  "tables": [t.qname for t in tables], "main": main.qname, "db": db}
            for t in tables:
                self.table_concept[t.qname] = cid
            if len(tables) > 1:
                self.decisions.append({"type": "merge_tables", "concept": cid,
                                       "tables": [t.qname for t in tables], "reason": "列结构与主键完全一致"})
        self.log.append(f"概念 {len(self.concepts)} 个（{sum(len(c['tables']) for c in self.concepts.values())} 张表）")

    # ------------------------------------------------------------ 关系
    def _key_index(self):
        """可被引用的键：单列主键或单列唯一键 → 表（同概念多表时只取主表）。"""
        idx = defaultdict(list)
        for t in self.tables:
            if self.concepts[self.table_concept[t.qname]]["main"] != t.qname:
                continue
            keys = []
            if len(t.primary_key) == 1:
                keys.append(t.primary_key[0])
            keys += [u[0] for u in t.unique_keys if len(u) == 1]
            for k in keys:
                idx[k].append(t)
        return idx

    def _relations(self):
        key_idx = self._key_index()
        tbl = {t.qname: t for t in self.tables}
        found = {}   # (child_qname, child_col) -> rel dict

        def add(child_t, child_col, parent_t, parent_col, prov):
            if child_t.qname == parent_t.qname and child_col == parent_col:
                return
            c, p = child_t.col(child_col), parent_t.col(parent_col)
            if c is None or p is None or wing_datatype(c.data_type) != wing_datatype(p.data_type):
                return
            key = (child_t.qname, child_col)
            r = found.get(key)
            if r is None:
                r = found[key] = {"child": child_t.qname, "child_col": child_col, "parent": parent_t.qname,
                                  "parent_col": parent_col, "provenance": set()}
            if (r["parent"], r["parent_col"]) == (parent_t.qname, parent_col):
                r["provenance"].add(prov)

        # 1) 命名约定
        for t in self.tables:
            own_pk = t.primary_key if len(t.primary_key) == 1 else []
            for c in t.columns:
                if c.name in own_pk:
                    continue
                for key, parents in key_idx.items():
                    if not (c.name == key or c.name.endswith("_" + key)):
                        continue
                    prefix = c.name[:-len(key)].rstrip("_").split("_")[-1] if c.name != key else ""
                    for p in parents:
                        # 后缀匹配时要求键名或前缀能指向父表（METER_ASSET_NO→D_METER，TMNL_ASSET_NO 不行）
                        ptoks = set(_core_tokens(p.name))
                        if prefix and not (ptoks & set(key.split("_")) or prefix in ptoks):
                            continue
                        if p.qname == t.qname and c.name == key:
                            continue
                        if key in GENERIC_KEYS and p.db != t.db:
                            continue
                        add(t, c.name, p, key, "naming_convention")
        # 2) JOIN 等值证据（追溯到源字段后）
        keyset = {(p.qname, k) for k, ps in key_idx.items() for p in ps}
        for pair, prov in self.ev.source_join_pairs().items():
            a, b = tuple(pair)
            ta, ca = a.rsplit(".", 1)
            tb, cb = b.rsplit(".", 1)
            if ta not in tbl or tb not in tbl:
                continue
            for (ct, cc, pt, pc) in ((ta, ca, tb, cb), (tb, cb, ta, ca)):
                if (pt, pc) in keyset and (ct, cc) not in keyset:
                    for p_ in prov:
                        add(tbl[ct], cc, tbl[pt], pc, p_)
        self.relations = []
        used = Counter()
        for r in sorted(found.values(), key=lambda r: (r["child"], r["child_col"])):
            child_c = self.table_concept[r["child"]]
            parent_c = self.table_concept[r["parent"]]
            col = tbl[r["child"]].col(r["child_col"])
            label = strip_code_desc(col.comment) if col.comment else ""
            rid = f"{child_c}_{camel(r['child_col'])}"
            used[rid] += 1
            if used[rid] > 1:
                continue  # 同概念多表的同一外键，只建一次关系
            name = f"{self.concepts[child_c]['name']}→{label or self.concepts[parent_c]['name']}"
            self.relations.append({**r, "id": rid, "name": name, "source_id": child_c, "target_id": parent_c,
                                   "provenance": sorted(r["provenance"])})
        # 同概念的其他表也挂同样的外键（用于映射）
        self.fk_columns = {(r["child"], r["child_col"]) for r in found.values()}
        self.fk_all = list(found.values())
        prov = Counter(p for r in self.relations for p in r["provenance"])
        self.log.append(f"关系 {len(self.relations)} 条（命名约定 {prov['naming_convention']}，"
                        f"任务 SQL 关联 {prov['task_sql_join']}，热点 SQL 关联 {prov['hot_sql_join']}）")

    # ------------------------------------------------------------ 实体标识
    def _identity(self):
        refs = Counter((r["parent"], r["parent_col"]) for r in self.fk_all)
        self.identity = {}     # concept -> key columns
        self.alt_keys = defaultdict(list)  # concept -> [key col]
        for cid, c in self.concepts.items():
            t = next(t for t in self.tables if t.qname == c["main"])
            cands = []
            if t.primary_key:
                cands.append(list(t.primary_key))
            cands += [list(u) for u in t.unique_keys]
            best = max(cands, key=lambda k: (refs.get((t.qname, k[0]), 0) if len(k) == 1 else 0, k == t.primary_key))
            self.identity[cid] = best
            for k in cands:
                if k != best and len(k) == 1 and refs.get((t.qname, k[0])):
                    self.alt_keys[cid].append(k[0])
            if best != list(t.primary_key):
                self.decisions.append({"type": "identity_key", "concept": cid, "key": best,
                                       "reason": f"该键被 {refs.get((t.qname, best[0]), 0)} 个外键引用，多于主键"})

    # ------------------------------------------------------------ 属性
    def _aliases(self, qname, col, main_name):
        names = []
        for dst in self.ev.downstream_direct(f"{qname}.{col}"):
            t, c = dst.rsplit(".", 1)
            pt = self.meta.get("sgfj_dataplatform", {}).get(t)
            pc = pt.col(c) if pt else None
            if pc and pc.comment:
                n = strip_code_desc(pc.comment)
                if n and n != main_name and n not in names and len(n) <= 30:
                    names.append(n)
        return names

    def _attributes(self):
        self.attributes = []
        self.column_attr = {}   # (qname, col) -> attribute id
        tbl = {t.qname: t for t in self.tables}
        for cid, c in self.concepts.items():
            t = tbl[c["main"]]
            for col in t.columns:
                if (t.qname, col.name) in self.fk_columns:
                    continue
                if col.comment:
                    name, basis = strip_code_desc(col.comment), "ddl_comment"
                else:
                    name, basis = column_name_guess(col.name)
                aid = f"{cid}_{camel(col.name)}"
                hint = f"{name}{col.name}"
                sens = "confidential" if any(h in hint for h in SENSITIVE_HINTS) else "internal"
                aliases = self._aliases(t.qname, col.name, name)
                if basis != "ddl_comment":
                    guess, _ = column_name_guess(col.name)
                    if guess != name and guess not in aliases:
                        aliases.append(guess)
                self.attributes.append({"id": aid, "name": name, "concept_id": cid,
                                        "datatype": wing_datatype(col.data_type), "sensitivity": sens,
                                        "aliases": aliases, "english_name": camel(col.name),
                                        "column": col.name, "basis": basis})
                for q in c["tables"]:
                    self.column_attr[(q, col.name)] = aid
        basis = Counter(a["basis"] for a in self.attributes)
        self.log.append(f"属性 {len(self.attributes)} 个（DDL 注释命名 {basis['ddl_comment']}，"
                        f"领域词表推断 {basis['glossary_exact'] + basis['glossary_tokens']}，"
                        f"仅列名 {basis['column_name']}）；别名来自中台注释 "
                        f"{sum(len(a['aliases']) for a in self.attributes)} 个")

    # ------------------------------------------------------------ OntoWing 编辑器
    def _editors(self):
        tbl = {t.qname: t for t in self.tables}
        concepts = []
        for cid, c in self.concepts.items():
            desc = f"源表：{'、'.join(c['tables'])}（{SYSTEM_TITLES[c['db']]}）"
            if c["cim"]:
                desc += f"；CIM 参考：{c['cim']}（待专家确认）"
            concepts.append({"id": cid, "name": c["name"], "top_category": c["top_category"], "parents": [],
                             "disjoint_with": [], "description": desc, "english_name": cid})
        attrs = [{"id": a["id"], "name": a["name"], "concept_id": a["concept_id"], "datatype": a["datatype"],
                  "sensitivity": a["sensitivity"], "aliases": a["aliases"],
                  "description": f"命名依据：{a['basis']}"} for a in self.attributes]
        rels = [{"id": r["id"], "name": r["name"], "source_id": r["source_id"], "target_id": r["target_id"],
                 "symmetric": False, "transitive": False, "functional": True, "inverse_id": None,
                 "description": f"{r['child']}.{r['child_col']} → {r['parent']}.{r['parent_col']}；"
                                f"依据：{'、'.join(r['provenance'])}"} for r in self.relations]
        self.model = {"format_version": "wing-model-editor/1", "concepts": concepts, "attributes": attrs,
                      "relations": rels, "annotations": []}

        rel_by_child = {}
        for r in self.relations:
            for q in self.concepts[r["source_id"]]["tables"]:
                rel_by_child[(q, r["child_col"])] = r
        bindings, planes = [], []
        bid_of = {}   # (concept, key col tuple) -> binding id of main table
        for cid, c in self.concepts.items():
            for q in c["tables"]:
                t = tbl[q]
                planes.append(fact_plane(t.db, t.name))
                bid = q.replace(".", "__")
                key = self.identity[cid]
                attrs_b = [{"attribute_id": self.column_attr[(q, col.name)], "column": col.name}
                           for col in t.columns if (q, col.name) in self.column_attr]
                bindings.append({"id": bid, "concept_id": cid, **fact_plane(t.db, t.name),
                                 "identity_scope": cid, "key_columns": key, "attributes": attrs_b,
                                 "references": []})
                if q == c["main"]:
                    bid_of[(cid, tuple(key))] = bid
                    for alt in self.alt_keys.get(cid, []):
                        abid = f"{bid}__by_{alt}"
                        bindings.append({"id": abid, "concept_id": cid, **fact_plane(t.db, t.name),
                                         "identity_scope": f"{cid}_by_{alt}", "key_columns": [alt],
                                         "attributes": [], "references": []})
                        bid_of[(cid, (alt,))] = abid
        by_id = {b["id"]: b for b in bindings}
        for b in bindings:
            q = f"{b['schema_name']}.{b['table_name']}"
            if "__by_" in b["id"]:
                continue
            for col in tbl[q].columns:
                r = rel_by_child.get((q, col.name))
                if r is None:
                    continue
                parent = bid_of.get((r["target_id"], (r["parent_col"],)))
                if parent is None:
                    continue
                b["references"].append({"relation_id": r["id"], "parent_binding_id": parent,
                                        "joins": [{"child": col.name, "parent": r["parent_col"]}]})
        self.pipeline = {"format_version": "wing-pipeline-editor/2", "fact_planes": planes, "bindings": bindings}
        self.bindings = by_id

        items = []
        for c in self.concepts.values():
            for q in c["tables"]:
                t = tbl[q]
                pk = set(t.primary_key)
                items.append({"reference": fact_plane(t.db, t.name), "dictionary": {
                    "table_name": t.name,
                    "columns": [{"name": col.name, "data_type": col.data_type, "nullable": col.nullable,
                                 "primary_key": col.name in pk, "position": col.position} for col in t.columns]}})
        self.snapshots = {"profile": "current-fact-plane-definitions/2", "items": items}
        n_alt = sum(1 for b in bindings if "__by_" in b["id"])
        self.log.append(f"数据管道映射：{len(bindings)} 个绑定（含备用键绑定 {n_alt}），"
                        f"{sum(len(b['references']) for b in bindings)} 条关联")

    # ------------------------------------------------------------ 供问答使用的索引
    def column_names(self, qname, col):
        """源字段的全部业务叫法：属性名+别名；外键列继承被引用键的叫法。"""
        aid = self.column_attr.get((qname, col))
        names = []
        if aid:
            a = next(a for a in self.attributes if a["id"] == aid)
            names = [a["name"], *a["aliases"]]
        for r in self.fk_all:
            if (r["child"], r["child_col"]) == (qname, col):
                paid = self.column_attr.get((r["parent"], r["parent_col"]))
                if paid:
                    pa = next(a for a in self.attributes if a["id"] == paid)
                    names += [pa["name"], *pa["aliases"]]
                t = next(t for t in self.tables if t.qname == qname)
                cc = t.col(col)
                if cc and cc.comment:
                    names.insert(0, strip_code_desc(cc.comment))
        return list(dict.fromkeys(n for n in names if n))

    def summary(self):
        return {"concepts": len(self.concepts), "attributes": len(self.attributes),
                "relations": len(self.relations), "bindings": len(self.pipeline["bindings"]),
                "tables_in_scope": len(self.tables), "tables_excluded": [t.qname for t in self.excluded],
                "metadata_source": self.meta_source}
