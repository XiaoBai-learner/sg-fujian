"""营销域本体与数据管道映射构建：表结构 + 血缘 + 热点 SQL → OntoWing model/pipeline 编辑器 JSON。

规则（全部可解释，每个产出都记录依据）：
  范围      同步到中台的源表（有 DI 血缘）；未同步的备份/临时表视为噪声剔除
  概念      一张源表一个概念；列结构完全相同的表（如当前表与历史表）合并为同一概念的多个绑定
  概念命名  领域词表（表名核心词）> 表注释 > 表名拆词
  标识      主键/唯一键中被外部引用最多的键作为实体标识；其余被引用的键生成“备用键绑定”
  关系      外键推断：列名同名或以“_<键名>”结尾 + 类型一致（命名约定），
            以及任务 SQL / 热点 SQL 中 JOIN 等值条件追溯到源字段（关联证据）
  属性      非外键列一列一属性；名称取 DDL 注释 > 领域词表；别名取血缘下游中台列的注释
  关联表    只有自身主键 + 两个外键（+ 日期）的表不建概念，转成两个概念之间的多对多关系（R2RML 由关联表产出三元组）
  层次      具体概念挂到领域上位类（参与方 / 设备 / 计量位置 / 计量数据 / 电费账务 / 客户服务事件），
            规则推导出的派生类（欠费客户、投诉工单…）是具体概念的子类
  关系命名  领域动词（归属供电单位、冲抵应收…）> 外键列注释；每条关系有反向关系
  规则      见 rules.py：派生类、规则链、约束，OntoWing wing-rules-editor/2 校验并导出 SWRL
"""
from collections import Counter, defaultdict

from .config import SOURCE_DBS, SYSTEM_TITLES
from .evidence import Evidence, strip_code_desc
from .glossary import (COLUMN_EXACT, COLUMN_TOKENS, CONCEPT_PARENT, RELATION_VERBS, SENSITIVE_HINTS,
                       TABLE_TERMS, TOP_CLASSES)
from . import rules as rulebook
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
        self._link_tables()
        self._name_relations()
        self._identity()
        self._attributes()
        self._editors()
        self._rules()

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

    # ------------------------------------------------------------ 关联表 → 多对多关系
    def _link_tables(self):
        tbl = {t.qname: t for t in self.tables}
        out_fk = defaultdict(list)
        for r in self.fk_all:
            out_fk[r["child"]].append(r)
        self.links = []
        for cid, c in list(self.concepts.items()):
            if len(c["tables"]) != 1:
                continue
            t = tbl[c["main"]]
            fks = out_fk.get(t.qname, [])
            others = [col for col in t.columns if col.name not in t.primary_key
                      and col.name not in {r["child_col"] for r in fks}]
            if len(fks) != 2 or any(wing_datatype(col.data_type) not in ("date", "datetime") for col in others):
                continue
            if any(r["parent"] == t.qname for r in self.fk_all):
                continue  # 被别人引用的不是纯关联表
            a, b = sorted(fks, key=lambda r: r["child_col"])
            ca, cb = self.table_concept[a["parent"]], self.table_concept[b["parent"]]
            if (cb, ca) in RELATION_VERBS and (ca, cb) not in RELATION_VERBS:
                a, b, ca, cb = b, a, cb, ca   # 方向以领域动词为准（计量点 安装电能表）
            self.links.append({"table": t.qname, "concept": cid, "from_fk": a, "to_fk": b,
                               "source_id": ca, "target_id": cb})
            del self.concepts[cid]
            self.decisions.append({"type": "link_table", "table": t.qname,
                                   "reason": f"只有主键和两个外键（{a['child_col']}、{b['child_col']}），"
                                             f"转为 {self.concepts[ca]['name']} 与 {self.concepts[cb]['name']} 之间的关系"})
        link_tables = {l["table"] for l in self.links}
        self.relations = [r for r in self.relations if r["child"] not in link_tables]
        if self.links:
            self.log.append(f"关联表 {len(self.links)} 张转为多对多关系：{'、'.join(l['table'] for l in self.links)}")

    def _name_relations(self):
        tbl = {t.qname: t for t in self.tables}
        pair_count = Counter((r["source_id"], r["target_id"]) for r in self.relations)
        for r in self.relations:
            col = tbl[r["child"]].col(r["child_col"])
            col_name = strip_code_desc(col.comment) if col and col.comment else column_name_guess(r["child_col"])[0]
            verb = RELATION_VERBS.get((r["source_id"], r["target_id"]))
            if r["source_id"] == r["target_id"] or pair_count[(r["source_id"], r["target_id"])] > 1 or not verb:
                verb, basis = col_name, "column_comment"
            else:
                basis = "glossary_verb"
            r["name"], r["name_basis"] = verb, basis
            child_name = self.concepts[r["source_id"]]["name"]
            r["inverse_name"] = f"下属{child_name}" if r["source_id"] == r["target_id"] else f"拥有{child_name}"
        for l in self.links:
            verb = RELATION_VERBS.get((l["source_id"], l["target_id"]))
            l["id"] = f"{l['source_id']}_via{l['concept']}"
            l["name"] = verb or self.concepts[l["target_id"]]["name"]
        self.log.append(f"关系命名：领域动词 {sum(r['name_basis'] == 'glossary_verb' for r in self.relations)} 条，"
                        f"外键注释 {sum(r['name_basis'] == 'column_comment' for r in self.relations)} 条")

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
        used_tops = {CONCEPT_PARENT[c] for c in self.concepts if c in CONCEPT_PARENT}
        for tid, (zh, top, cim, desc) in TOP_CLASSES.items():
            if tid in used_tops:
                concepts.append({"id": tid, "name": zh, "top_category": top, "parents": [], "disjoint_with": [],
                                 "description": f"领域上位类：{desc}；CIM 参考：{cim}（待专家确认）",
                                 "english_name": tid})
        self.abstract = sorted(used_tops)
        for cid, c in self.concepts.items():
            desc = f"源表：{'、'.join(c['tables'])}（{SYSTEM_TITLES[c['db']]}）"
            if c["cim"]:
                desc += f"；CIM 参考：{c['cim']}（待专家确认）"
            parent = CONCEPT_PARENT.get(cid)
            concepts.append({"id": cid, "name": c["name"], "top_category": c["top_category"],
                             "parents": [parent] if parent else [], "disjoint_with": [], "description": desc,
                             "english_name": cid})
        attrs = [{"id": a["id"], "name": a["name"], "concept_id": a["concept_id"], "datatype": a["datatype"],
                  "sensitivity": a["sensitivity"], "aliases": a["aliases"],
                  "description": f"命名依据：{a['basis']}"} for a in self.attributes]
        rels = []
        for r in self.relations:
            inv = f"{r['id']}_inverse"
            rels.append({"id": r["id"], "name": r["name"], "source_id": r["source_id"], "target_id": r["target_id"],
                         "symmetric": False, "transitive": False, "functional": True, "inverse_id": inv,
                         "description": f"{r['child']}.{r['child_col']} → {r['parent']}.{r['parent_col']}；"
                                        f"依据：{'、'.join(r['provenance'])}"})
            rels.append({"id": inv, "name": r["inverse_name"], "source_id": r["target_id"],
                         "target_id": r["source_id"], "symmetric": False, "transitive": False, "functional": False,
                         "inverse_id": r["id"], "description": f"{r['name']} 的反向关系"})
        for cid in sorted(self.alt_keys):
            if self.alt_keys[cid]:
                rels.append({"id": f"{cid}_sameAs", "name": f"同一{self.concepts[cid]['name']}（标识对齐）",
                             "source_id": cid, "target_id": cid, "symmetric": True, "transitive": True,
                             "functional": False, "inverse_id": None,
                             "description": f"{self.concepts[cid]['name']} 同时被 {'、'.join(self.alt_keys[cid])} 和 "
                                            f"{'、'.join(self.identity[cid])} 引用，按 owl:sameAs 语义合并"})
        for l in self.links:
            rels.append({"id": l["id"], "name": l["name"], "source_id": l["source_id"], "target_id": l["target_id"],
                         "symmetric": False, "transitive": False, "functional": False, "inverse_id": None,
                         "description": f"多对多，经关联表 {l['table']}（{l['from_fk']['child_col']} → "
                                        f"{l['to_fk']['child_col']}）"})
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
                        # 备用键实体与主标识实体是同一对象：用“标识对齐”关系连到主绑定，物化后合并
                        bindings.append({"id": abid, "concept_id": cid, **fact_plane(t.db, t.name),
                                         "identity_scope": f"{cid}_by_{alt}", "key_columns": [alt],
                                         "attributes": [], "references": [{
                                             "relation_id": f"{cid}_sameAs", "parent_binding_id": bid,
                                             "joins": [{"child": k, "parent": k} for k in key]}]})
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
        # 关联表：主语用“源概念”的标识模板，产出 源概念 —关系→ 目标概念
        for l in self.links:
            t = tbl[l["table"]]
            fa, fb = l["from_fk"], l["to_fk"]
            tgt_bid = bid_of.get((l["target_id"], (fb["parent_col"],)))
            # 主语必须与源概念某个绑定的标识一致：主标识或备用键标识
            if self.identity[l["source_id"]] == [fa["parent_col"]]:
                scope = l["source_id"]
            elif fa["parent_col"] in self.alt_keys.get(l["source_id"], []):
                scope = f"{l['source_id']}_by_{fa['parent_col']}"
            else:
                scope = None
            if scope is None or tgt_bid is None:
                self.decisions.append({"type": "link_table_unmapped", "table": l["table"],
                                       "reason": "两端实体标识与关联列不一致，未生成映射"})
                continue
            planes.append(fact_plane(t.db, t.name))
            bindings.append({"id": l["table"].replace(".", "__"), "concept_id": l["source_id"],
                             **fact_plane(t.db, t.name), "identity_scope": scope,
                             "key_columns": [fa["child_col"]], "attributes": [],
                             # 关联表外键列可空：空值行不产生三元组（显式声明，OntoWing 给出警告）
                             **({"null_key_policy": "skip"} if t.col(fa["child_col"]).nullable else {}),
                             "references": [{"relation_id": l["id"], "parent_binding_id": tgt_bid,
                                             "joins": [{"child": fb["child_col"], "parent": fb["parent_col"]}]}]})
        self.pipeline = {"format_version": "wing-pipeline-editor/2", "fact_planes": planes, "bindings": bindings}
        self.bindings = by_id

        items = []
        snap_tables = [q for c in self.concepts.values() for q in c["tables"]] + [l["table"] for l in self.links]
        for q in snap_tables:
            t = tbl[q]
            pk = set(t.primary_key)
            items.append({"reference": fact_plane(t.db, t.name), "dictionary": {
                "table_name": t.name,
                "columns": [{"name": col.name, "data_type": col.data_type, "nullable": col.nullable,
                             "primary_key": col.name in pk, "position": col.position} for col in t.columns]}})
        self.snapshots = {"profile": "current-fact-plane-definitions/2", "items": items}
        n_alt = sum(1 for b in bindings if "__by_" in b["id"])
        self.log.append(f"层次：上位类 {len(self.abstract)} 个，具体概念 {len(self.concepts)} 个均已挂接上位类；"
                        f"关系 {len(rels)} 条（含反向 {len(self.relations)}，多对多 {len(self.links)}）")
        self.log.append(f"数据管道映射：{len(bindings)} 个绑定（含备用键绑定 {n_alt}），"
                        f"{sum(len(b['references']) for b in bindings)} 条关联")

    # ------------------------------------------------------------ 规则
    def _rules(self):
        derived, editor, meta, skipped = rulebook.derive(self)
        self.model["concepts"].extend(derived)
        self.derived = derived
        self.rules = editor
        self.rule_meta = meta
        for sk in skipped:
            self.decisions.append({"type": "rule_skipped", **sk})
        chains = sum(1 for m in meta if any(it.get("kind") == "class" and it["predicate"] in {d["id"] for d in derived}
                                            for it in m["body"]))
        self.log.append(f"规则 {len(editor['rules'])} 条（事实规则 {sum(r['level'] == 'FR' for r in editor['rules'])}，"
                        f"建议规则 {sum(r['level'] == 'DR' for r in editor['rules'])}，引用其他规则结论的 {chains} 条），"
                        f"派生类 {len(derived)} 个，约束 {len(editor['constraints'])} 条")

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
        return {"concepts": len(self.concepts), "abstract_classes": len(self.abstract),
                "derived_classes": len(self.derived), "attributes": len(self.attributes),
                "relations": len(self.model["relations"]), "rules": len(self.rules["rules"]),
                "constraints": len(self.rules["constraints"]), "bindings": len(self.pipeline["bindings"]),
                "tables_in_scope": len(self.tables), "tables_excluded": [t.qname for t in self.excluded],
                "metadata_source": self.meta_source}
