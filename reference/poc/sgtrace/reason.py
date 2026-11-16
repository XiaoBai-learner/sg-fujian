"""规则执行：在 R2RML 物化出的实例图上执行 OntoWing 导出的 SWRL 规则（rules.ttl）。

只实现 OntoWing swrl-simple/1 的子集：类原子、属性/关系原子、swrlb 比较内置；
按规则依赖顺序前向链推理到不动点（规则可以使用其他规则推出的类）。
同时实现 rdfs:subClassOf 继承（派生类实例也是父类实例）和约束检查（OntoWing 约束不导出，由此处执行）。

独立性：推理结果再用 rules.py 里每条规则的 cross_check SQL 直接在沙箱库上计算一遍，二者计数一致才算通过。
"""
import re
import sqlite3
from collections import defaultdict

import rdflib
from rdflib.namespace import RDF, RDFS

from .config import SANDBOX, SOURCE_DBS
from .wing import ALITA_NS

RULE = rdflib.Namespace("urn:rule:")
_ATOM = re.compile(r"([A-Za-z]+):([A-Za-z0-9_.-]+)\(([^)]*)\)")
CMP = {"greaterThanOrEqual": lambda a, b: a >= b, "lessThanOrEqual": lambda a, b: a <= b,
       "greaterThan": lambda a, b: a > b, "lessThan": lambda a, b: a < b,
       "equal": lambda a, b: a == b, "notEqual": lambda a, b: a != b}


def _term(t):
    t = t.strip()
    if t.startswith("?"):
        return ("var", t[1:])
    if t.startswith('"'):
        return ("lit", t.strip('"'))
    if t.startswith("alita:"):
        return ("iri", rdflib.URIRef(ALITA_NS + t[6:]))
    try:
        return ("lit", float(t))
    except ValueError:
        return ("lit", t)


def parse_rules(rules_ttl):
    g = rdflib.Graph().parse(data=rules_ttl, format="turtle")
    out = []
    for s in g.subjects(RULE.source_code, None):
        src = str(g.value(s, RULE.source_code))
        body_s, head_s = src.split("->")
        body = [(p, n, [_term(a) for a in args.split(",")]) for p, n, args in _ATOM.findall(body_s)]
        hp, hn, ha = _ATOM.findall(head_s)[0]
        out.append({"id": str(g.value(s, RULE.id)), "source": src, "body": body,
                    "head": (hn, [_term(a) for a in ha.split(",")])})
    return out


def _value(o):
    if isinstance(o, rdflib.Literal):
        v = o.toPython()
        if hasattr(v, "is_finite") or isinstance(v, (int, float)):
            return float(v)
        return str(v)
    return o


class Reasoner:
    def __init__(self, graph, ontology_ttl):
        self.g = graph
        onto = rdflib.Graph().parse(data=ontology_ttl, format="turtle")
        self.parents = defaultdict(set)
        for c, p in onto.subject_objects(RDFS.subClassOf):
            self.parents[c].add(p)
        self.types = defaultdict(set)      # class -> instances（含推导、含继承）
        self.by_pred = defaultdict(list)   # predicate -> [(s, value)]
        self.by_subj = defaultdict(lambda: defaultdict(list))  # predicate -> s -> [value]
        for s, p, o in graph:
            if p == RDF.type:
                self._add_type(s, o)
            else:
                v = _value(o)
                self.by_pred[p].append((s, v))
                self.by_subj[p][s].append(v)
        self.inferred = defaultdict(set)   # 规则推出的 (class) -> instances

    def _add_type(self, s, c, seen=None):
        if s in self.types[c]:
            return False
        self.types[c].add(s)
        for p in self.parents.get(c, ()):
            self._add_type(s, p)
        return True

    def _match(self, body, binding=None, i=0):
        binding = binding or {}
        if i == len(body):
            yield dict(binding)
            return
        prefix, name, args = body[i]
        if prefix == "swrlb":
            vals = [binding.get(a[1]) if a[0] == "var" else a[1] for a in args]
            if None not in vals and all(isinstance(v, float) for v in vals) and CMP[name](*vals):
                yield from self._match(body, binding, i + 1)
            return
        pred = rdflib.URIRef(ALITA_NS + name)
        if len(args) == 1:
            kind, v = args[0]
            if kind == "var" and v in binding:
                if binding[v] in self.types[pred]:
                    yield from self._match(body, binding, i + 1)
            else:
                for inst in list(self.types[pred]):
                    yield from self._match(body, {**binding, v: inst}, i + 1)
            return
        (ks, vs), (ko, vo) = args
        if vs in binding:   # 主语已绑定：按主语索引查，避免全表扫描
            pairs = ((binding[vs], o) for o in self.by_subj[pred].get(binding[vs], ()))
        else:
            pairs = self.by_pred.get(pred, ())
        for s, o in pairs:
            nb = {**binding, vs: s}
            if ko == "var":
                if vo in nb and nb[vo] != o:
                    continue
                nb[vo] = o
            elif ko == "lit" and o != vo:
                continue
            elif ko == "iri" and o != vo:
                continue
            yield from self._match(body, nb, i + 1)

    def _plan(self, body):
        """连接顺序：常量过滤的属性原子优先（选择性高），再按已绑定变量贪心推进；比较内置放在变量绑定之后。"""
        todo, plan, bound = list(body), [], set()

        def score(a):
            prefix, name, args = a
            if prefix == "swrlb":
                return 0 if all(t[0] != "var" or t[1] in bound for t in args) else 99
            vars_ = [t[1] for t in args if t[0] == "var"]
            if len(args) == 2 and args[1][0] != "var":
                return 1 if args[0][1] in bound else 2
            if any(v in bound for v in vars_):
                return 3
            if len(args) == 1:
                return 6
            return 5
        while todo:
            a = min(todo, key=score)
            todo.remove(a)
            plan.append(a)
            bound |= {t[1] for t in a[2] if t[0] == "var"}
        return plan

    def run(self, rules, max_rounds=10):
        # 把类原子移到最后之外：先用属性原子绑定变量能大幅减少搜索；类原子在前时直接迭代该类实例
        log = []
        for rnd in range(max_rounds):
            changed = False
            for r in rules:
                hname, hargs = r["head"]
                hcls = rdflib.URIRef(ALITA_NS + hname)
                new = 0
                for b in self._match(self._plan(r["body"])):
                    inst = b.get(hargs[0][1])
                    if inst is not None and self._add_type(inst, hcls):
                        self.inferred[hname].add(inst)
                        new += 1
                if new:
                    changed = True
                log.append({"round": rnd + 1, "rule": r["id"], "new": new})
            if not changed:
                break
        return log


def _sandbox():
    conn = sqlite3.connect(f"file:{SANDBOX / 'platform.db'}?mode=ro", uri=True)
    for db in SOURCE_DBS:
        conn.execute(f"ATTACH DATABASE 'file:{SANDBOX / (db + '.db')}?mode=ro' AS {db}")
    return conn


def check_constraints(reasoner, constraints, model):
    """在实例上执行 OntoWing 约束（min/max_count、pattern、取值范围、关系目标类）。"""
    attrs = {a["id"] for a in model["attributes"]}
    out = []
    for c in constraints:
        cls = rdflib.URIRef(ALITA_NS + c["target_class"])
        pred = rdflib.URIRef(ALITA_NS + c["property"])
        values = defaultdict(list)
        for s, o in reasoner.by_pred.get(pred, ()):
            values[s].append(o)
        targets = reasoner.types.get(cls, set())
        bad = 0
        pat = re.compile(c["pattern"]) if "pattern" in c else None
        target_cls = rdflib.URIRef(ALITA_NS + c["class"]) if "class" in c else None
        for s in targets:
            vs = values.get(s, [])
            if len(vs) < c.get("min_count", 0) or len(vs) > c.get("max_count", 10 ** 9):
                bad += 1
                continue
            ok = True
            for v in vs:
                if pat and not pat.fullmatch(str(v)):
                    ok = False
                if "min_inclusive" in c and isinstance(v, float) and v < float(c["min_inclusive"]["value"]):
                    ok = False
                if "max_inclusive" in c and isinstance(v, float) and v > float(c["max_inclusive"]["value"]):
                    ok = False
                if target_cls is not None and c["property"] not in attrs and v not in reasoner.types[target_cls]:
                    ok = False
            bad += not ok
        out.append({"id": c["id"], "name": c["name"], "target": c["target_class"], "checked": len(targets),
                    "violations": bad})
    return out


def run(graph, ontology_ttl, rules_ttl, rules_editor, rule_meta, model):
    rules = parse_rules(rules_ttl)
    r = Reasoner(graph, ontology_ttl)
    log = r.run(rules)
    conn = _sandbox()
    results = []
    by_head = {m["head"]: m for m in rule_meta}
    exported = {x["id"].split(":")[0] for x in rules}
    for m in rule_meta:
        inferred = len(r.inferred.get(m["head"], ()))
        expected = conn.execute(m["cross_check"]).fetchone()[0]
        results.append({"rule": m["id"], "name": m["name"], "level": m["level"], "head": m["head"],
                        "exported": m["id"] in exported, "inferred": inferred if m["id"] in exported else None,
                        "sql_check": expected,
                        "match": (inferred == expected) if m["id"] in exported else None})
    conn.close()
    constraints = check_constraints(r, rules_editor["constraints"], model)
    del by_head
    return {"rules": results, "rounds": max((x["round"] for x in log), default=0),
            "constraints": constraints,
            "passed": all(x["match"] for x in results if x["match"] is not None)}
