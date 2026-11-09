"""语义索引：只从 OntoWing 导出的 ontology.ttl + mapping.ttl 构建“业务叫法 → 本体属性 → 物理表.列”。

问答时，源系统字段的候选全部来自这里，保证回答走的是“本体 + R2RML”这条路，而不是直接查 DDL。
mapping.ttl 的 rr:tableName 不带库名（Wing 导出损失 binding_schema_name），用 pipeline 编辑器里的
binding.schema_name 补回。
"""
import re
from collections import defaultdict
from dataclasses import dataclass, field

import rdflib
from rdflib.namespace import RDF, RDFS, SKOS

from .wing import ALITA_NS

RR = rdflib.Namespace("http://www.w3.org/ns/r2rml#")
_BRACE = re.compile(r"\{([^}]+)\}")


@dataclass
class Predicate:
    id: str
    kind: str                 # attribute / relation
    label: str
    alt_labels: list
    domain: str
    range: str
    columns: list = field(default_factory=list)   # [(db.table, column)]


class SemanticIndex:
    def __init__(self, ontology_ttl, mapping_ttl, pipeline):
        self.onto = rdflib.Graph().parse(data=ontology_ttl, format="turtle")
        self.map = rdflib.Graph().parse(data=mapping_ttl, format="turtle", publicID="urn:map:")
        db_of = {b["id"]: b["schema_name"] for b in pipeline["bindings"]}
        self.concepts = {}
        for c in self.onto.subjects(RDF.type, RDFS.Class):
            cid = str(c).removeprefix(ALITA_NS)
            self.concepts[cid] = self._label(c)
        self.preds = {}
        for p in self.onto.subjects(RDF.type, RDF.Property):
            pid = str(p).removeprefix(ALITA_NS)
            rng = str(self.onto.value(p, RDFS.range) or "")
            kind = "relation" if rng.startswith(ALITA_NS) else "attribute"
            self.preds[pid] = Predicate(
                pid, kind, self._label(p), [str(o) for o in self.onto.objects(p, SKOS.altLabel)],
                str(self.onto.value(p, RDFS.domain) or "").removeprefix(ALITA_NS), rng.removeprefix(ALITA_NS))
        # 解析 R2RML
        self.subject_key = {}     # scope 前缀 -> (db.table, key column)
        self.column_pred = {}     # (db.table, col) -> predicate id
        rel_targets = []
        for tm in self.map.subjects(RDF.type, RR.TriplesMap):
            bid = str(tm).split("#")[-1].removesuffix("Mapping")
            lt = self.map.value(tm, RR.logicalTable)
            table = f"{db_of.get(bid, '')}.{self.map.value(lt, RR.tableName)}"
            sm = self.map.value(tm, RR.subjectMap)
            tpl = str(self.map.value(sm, RR.template))
            keys = _BRACE.findall(tpl)
            prefix = tpl.split("{")[0]
            if len(keys) == 1 and prefix not in self.subject_key:
                self.subject_key[prefix] = (table, keys[0])
            for pom in self.map.objects(tm, RR.predicateObjectMap):
                pid = str(self.map.value(pom, RR.predicate)).removeprefix(ALITA_NS)
                om = self.map.value(pom, RR.objectMap)
                col = self.map.value(om, RR.column)
                if col is not None:
                    self._bind(pid, table, str(col))
                else:
                    otpl = str(self.map.value(om, RR.template) or "")
                    cols = _BRACE.findall(otpl)
                    if len(cols) == 1:
                        self._bind(pid, table, cols[0])
                        rel_targets.append((pid, otpl.split("{")[0]))
        self.relation_target = {}   # relation id -> (父表, 父键列)
        for pid, prefix in rel_targets:
            if prefix in self.subject_key:
                self.relation_target[pid] = self.subject_key[prefix]

    def _label(self, node):
        for o in self.onto.objects(node, RDFS.label):
            if getattr(o, "language", None) == "zh":
                return str(o)
        return str(node).removeprefix(ALITA_NS)

    def _bind(self, pid, table, col):
        p = self.preds.get(pid)
        if p is None:
            return
        if (table, col) not in p.columns:
            p.columns.append((table, col))
        self.column_pred.setdefault((table, col), pid)

    def names_of(self, pid):
        """属性：label + altLabel；关系（外键列）：继承被引用键属性的叫法。"""
        p = self.preds[pid]
        if p.kind == "attribute":
            return [p.label, *p.alt_labels]
        tgt = self.relation_target.get(pid)
        if tgt and tgt in self.column_pred:
            parent = self.preds[self.column_pred[tgt]]
            if parent.kind == "attribute":
                return [parent.label, *parent.alt_labels]
        return [p.label.split("→")[-1]]

    def candidates(self):
        """[(db.table.col, 谓词 id, 叫法列表)]"""
        out = []
        for pid, p in self.preds.items():
            names = self.names_of(pid)
            for table, col in p.columns:
                out.append((f"{table}.{col}", pid, names))
        return out

    def describe(self, qcol):
        table, col = qcol.rsplit(".", 1)
        pid = self.column_pred.get((table, col))
        if pid is None:
            return None
        p = self.preds[pid]
        d = {"predicate": f"alita:{pid}", "kind": p.kind, "label": p.label, "concept": p.domain,
             "concept_label": self.concepts.get(p.domain, p.domain)}
        if p.kind == "relation" and pid in self.relation_target:
            d["references"] = ".".join(self.relation_target[pid])
        return d

    def equivalents(self, qcol):
        """同一实体标识的其他物理列：被引用键 ↔ 所有引用它的外键列。"""
        table, col = qcol.rsplit(".", 1)
        root = (table, col)
        pid = self.column_pred.get(root)
        if pid and pid in self.relation_target:
            root = self.relation_target[pid]
        out = set()
        if root != (table, col):
            out.add(".".join(root))
        for rid, tgt in self.relation_target.items():
            if tgt == root:
                for t, c in self.preds[rid].columns:
                    out.add(f"{t}.{c}")
        root_pid = self.column_pred.get(root)
        if root_pid:
            for t, c in self.preds[root_pid].columns:
                out.add(f"{t}.{c}")
        out.discard(qcol)
        return sorted(out)

    def graph(self):
        nodes = [{"id": cid, "label": lab} for cid, lab in self.concepts.items()]
        attrs = defaultdict(list)
        edges = []
        for pid, p in self.preds.items():
            item = {"id": pid, "label": p.label, "alt_labels": p.alt_labels,
                    "columns": [f"{t}.{c}" for t, c in p.columns]}
            if p.kind == "attribute":
                attrs[p.domain].append(item)
            else:
                edges.append({"id": pid, "source": p.domain, "target": p.range, "label": p.label, **item})
        for n in nodes:
            n["attributes"] = attrs.get(n["id"], [])
            n["tables"] = sorted({c.rsplit(".", 1)[0] for a in n["attributes"] for c in a["columns"]})
        return {"nodes": nodes, "edges": edges}
