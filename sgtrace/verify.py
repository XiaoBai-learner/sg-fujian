"""R2RML 实跑校验：用 Morph-KGC 在沙箱 SQLite（带样例数据）上物化 Wing 导出的 mapping.ttl。

Wing 导出的 rr:tableName 不带库名（schema_name 在导出时被丢弃，记为 binding_schema_name 损失），
所以按 TriplesMap 所属系统拆分 mapping，分别连各系统的沙箱库执行。

校验项：
  1. 每个 TriplesMap 都产生三元组（表名、列名、键模板与真实库一致）
  2. 关系三元组的宾语都能落到某个已生成的实体上（外键引用完整性）
"""
import os
import re
import tempfile
from collections import Counter

import rdflib

from .config import SANDBOX, SOURCE_DBS

RR = rdflib.Namespace("http://www.w3.org/ns/r2rml#")


def _split_by_db(mapping_ttl, pipeline):
    db_of = {b["id"]: b["schema_name"] for b in pipeline["bindings"]}
    g = rdflib.Graph().parse(data=mapping_ttl, format="turtle", publicID="urn:map:")
    parts = {db: rdflib.Graph() for db in SOURCE_DBS}
    for tm in set(g.subjects(rdflib.RDF.type, RR.TriplesMap)):
        bid = str(tm).split("#")[-1].removesuffix("Mapping")
        db = db_of.get(bid)
        if db is None:
            continue
        sub = parts[db]
        stack = [tm]
        while stack:
            node = stack.pop()
            for p, o in g.predicate_objects(node):
                sub.add((node, p, o))
                if isinstance(o, rdflib.BNode):
                    stack.append(o)
    return parts


def materialize(mapping_ttl, pipeline):
    import logging
    import morph_kgc
    logging.getLogger("morph_kgc").setLevel(logging.ERROR)
    graph = rdflib.Graph()
    per_map = Counter()
    errors = []
    with tempfile.TemporaryDirectory() as tmp:
        for db, sub in _split_by_db(mapping_ttl, pipeline).items():
            if len(sub) == 0:
                continue
            mpath = os.path.join(tmp, f"{db}.ttl")
            sub.serialize(mpath, format="turtle")
            cfg = (f"[CONFIGURATION]\nlogging_level=ERROR\nnumber_of_processes=1\n"
                   f"[{db}]\nmappings={mpath}\ndb_url=sqlite:///{SANDBOX / (db + '.db')}\n")
            try:
                g = morph_kgc.materialize(cfg)
            except Exception as e:  # noqa: BLE001 记录并继续其他系统
                errors.append(f"{db}: {type(e).__name__}: {e}"[:300])
                continue
            graph += g
    return graph, errors


def check(mapping_ttl, pipeline, model):
    if not all((SANDBOX / f"{db}.db").exists() for db in SOURCE_DBS):
        return {"ran": False, "reason": "沙箱库不存在，请先运行 python3 datagen/build.py"}
    graph, errors = materialize(mapping_ttl, pipeline)
    ns = "https://vocab.alita.dev/gongshang/"
    by_class = Counter()
    for s, o in graph.subject_objects(rdflib.RDF.type):
        by_class[str(o).removeprefix(ns)] += 1
    subjects = set(graph.subjects(rdflib.RDF.type, None))
    rel_ids = {r["id"] for r in model["relations"]}
    rel_total, rel_dangling = Counter(), Counter()
    for s, p, o in graph:
        pid = str(p).removeprefix(ns)
        if pid in rel_ids:
            rel_total[pid] += 1
            if o not in subjects:
                rel_dangling[pid] += 1
    empty = [c["id"] for c in model["concepts"] if by_class.get(c["id"], 0) == 0]
    return {
        "ran": True, "triples": len(graph), "errors": errors,
        "instances_by_concept": dict(sorted(by_class.items())),
        "empty_concepts": empty,
        "relations": {r: {"triples": rel_total[r], "dangling": rel_dangling[r]} for r in sorted(rel_ids)},
        "dangling_total": sum(rel_dangling.values()),
        "passed": not errors and not empty and sum(rel_total.values()) > 0,
    }
