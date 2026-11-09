"""问答：截图字段 → 源系统原表.原字段。

两类输入：
  截图需求  OCR 文本 + 要问的字段（客户邮件形态）
  自由提问  “户号属于什么表”

截图需求的推理过程（每一步都写进证据）：
  1. 解析 OCR：找表头行，拆出每个字段在截图上的取值
  2. 对每个截图字段打分：名称相似度（本体标签/同义词、中台注释）+ 原始数据值校验
  3. 页面来源判定：页面通常由一张中台应用表支撑，选覆盖全部截图字段得分最高的中台表；
     某字段在该表找不到可信列时，退回到本体（R2RML）里的源系统字段
  4. 中台字段沿血缘追溯到源字段；源字段经本体给出概念与属性
  5. 置信度低于阈值时标记“待人工确认”，不硬给答案
"""
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass

from .config import PLATFORM_DB, SANDBOX, SOURCE_DBS, SYSTEM_TITLES
from .evidence import strip_code_desc
from .text import best_similarity, strip

ABSTAIN = 0.35        # 低于此置信度标记待确认
TABLE_FLOOR = 0.4     # 中台表内匹配低于此值，退回源字段候选
_NUM = re.compile(r"^-?\d+(\.\d+)?$")


@dataclass
class Options:
    synonyms: bool = True
    value_check: bool = True
    platform: bool = True


def parse_ocr(ocr, asked):
    """返回 (表头标签列表, {标签: [取值]}, 页面上下文文本)。"""
    lines = [l for l in ocr.splitlines() if l.strip()]
    rows = [re.split(r"\s{2,}", l.strip()) for l in lines]
    asked_s = {strip(a) for a in asked}
    best_i, best_n = -1, 0
    for i, r in enumerate(rows):
        n = sum(1 for t in r if strip(t) in asked_s)
        if n > best_n:
            best_i, best_n = i, n
    if best_i < 0:
        return list(asked), {a: [] for a in asked}, ""
    header = rows[best_i]
    values = {h: [] for h in header}
    for r in rows[best_i + 1:]:
        if len(r) != len(header):
            continue
        for h, v in zip(header, r):
            v = v.strip()
            if v and v != "-":
                values[h].append(v)
    context = " ".join(lines[:best_i])
    return header, values, context


def _distinctive(values):
    out = []
    for v in values:
        if _NUM.match(v):
            if len(v.replace(".", "").replace("-", "").lstrip("0")) >= 5:
                out.append(v)
        elif len(v) >= 2:
            out.append(v)
    return list(dict.fromkeys(out))


class ValueChecker:
    """在模拟客户库（沙箱）里做原始数据值校验：截图上的值是否出现在候选列中。"""

    def __init__(self):
        self.conn = None
        if (SANDBOX / "platform.db").exists():
            self.conn = sqlite3.connect(f"file:{SANDBOX / 'platform.db'}?mode=ro", uri=True,
                                        check_same_thread=False)
            for db in SOURCE_DBS:
                self.conn.execute(f"ATTACH DATABASE 'file:{SANDBOX / (db + '.db')}?mode=ro' AS {db}")
        self.cache = {}

    @property
    def available(self):
        return self.conn is not None

    def _ref(self, qcol):
        parts = qcol.split(".")
        if len(parts) == 3:
            return f'{parts[0]}."{parts[1]}"', f'"{parts[2]}"'
        return f'"{parts[0]}"', f'"{parts[1]}"'

    def ratio(self, qcol, values):
        if not self.conn or not values:
            return None
        key = (qcol, tuple(values))
        if key in self.cache:
            return self.cache[key]
        table, col = self._ref(qcol)
        hits = 0
        for v in values:
            params = [v]
            if _NUM.match(v):
                params.append(float(v))
            ph = " OR ".join([f"{col} = ?"] * len(params))
            try:
                if self.conn.execute(f"SELECT 1 FROM {table} WHERE {ph} LIMIT 1", params).fetchone():
                    hits += 1
            except sqlite3.Error:
                self.cache[key] = None
                return None
        self.cache[key] = hits / len(values)
        return self.cache[key]


class QAEngine:
    def __init__(self, build, semantic, evidence, values=None, options=None):
        self.b, self.sem, self.ev = build, semantic, evidence
        self.opt = options or Options()
        self.values = values if values is not None else ValueChecker()
        plat = build.meta.get(PLATFORM_DB, {})
        self.platform = {}
        for t in plat.values():
            cols = []
            for c in t.columns:
                names = [strip_code_desc(c.comment)] if c.comment else []
                cols.append((f"{t.name}.{c.name}", names))
            self.platform[t.name] = {"comment": t.comment, "cols": cols}
        self.source = self.sem.candidates()
        self.source_comment = {}
        for db in SOURCE_DBS:
            for t in build.meta.get(db, {}).values():
                for c in t.columns:
                    self.source_comment[f"{t.qname}.{c.name}"] = (t.comment, c.comment)

    # ------------------------------------------------------------ 打分
    def _score(self, label, names, qcol, vals):
        name, hit = best_similarity(label, names, self.opt.synonyms) if names else (0.0, "")
        vr = self.values.ratio(qcol, vals) if (self.opt.value_check and vals) else None
        score = name if vr is None else 0.55 * name + 0.45 * vr
        return score, {"name_score": round(name, 3), "matched_name": hit,
                       "value_ratio": None if vr is None else round(vr, 3), "value_samples": vals[:3]}

    def _source_candidates(self, label, vals, top=8):
        pre = []
        for qcol, pid, names in self.source:
            s, _ = best_similarity(label, names, self.opt.synonyms)
            pre.append((s, qcol, pid, names))
        pre.sort(key=lambda x: -x[0])
        out = []
        for _, qcol, pid, names in pre[:top]:
            s, ev = self._score(label, names, qcol, vals)
            out.append({"column": qcol, "predicate": pid, "score": s, "evidence": ev})
        out.sort(key=lambda x: -x["score"])
        return out

    def _prefer_key(self, cands):
        """同分时优先被引用的实体键（如 C_CONS.CONS_NO），其次是外键列。"""
        if len(cands) < 2:
            return cands
        top = cands[0]["score"]
        tied = [c for c in cands if top - c["score"] < 1e-6]
        targets = {".".join(self.sem.relation_target[c["predicate"]]) for c in tied
                   if c["predicate"] in self.sem.relation_target}
        for c in tied:
            if c["column"] in targets:
                cands.remove(c)
                cands.insert(0, c)
                break
        return cands

    def _coherent(self, per_label):
        """按多数系统、多数表给源字段候选加一致性分（同一页面的字段通常来自同一系统、少数几张表）。"""
        firsts = [c[0]["column"] for c in per_label.values() if c]
        dbs = Counter(x.split(".")[0] for x in firsts)
        tables = Counter(x.rsplit(".", 1)[0] for x in firsts)
        main_db = dbs.most_common(1)[0][0] if dbs else None
        n = max(len(firsts), 1)
        for cands in per_label.values():
            for c in cands:
                t = c["column"].rsplit(".", 1)[0]
                bonus = (0.08 if c["column"].split(".")[0] == main_db else 0) + 0.06 * tables[t] / n
                c["score"] += bonus
                c["evidence"]["coherence_bonus"] = round(bonus, 3)
            cands.sort(key=lambda x: -x["score"])
            self._prefer_key(cands)
        return per_label

    def _pick_platform_table(self, header, values):
        if not self.opt.platform:
            return None, 0.0, []
        scored = []
        for tname, t in self.platform.items():
            tot = 0.0
            for h in header:
                tot += max((best_similarity(h, names, self.opt.synonyms)[0] for _, names in t["cols"]), default=0)
            mean = tot / max(len(header), 1)
            prior = (0.08 if self.ev.service_tables.get(tname) else 0) + (0.03 if tname.startswith("ads_") else 0)
            scored.append((mean + prior, tname))
        scored.sort(reverse=True)
        best = []
        for _, tname in scored[:3]:
            t = self.platform[tname]
            tot = 0.0
            for h in header:
                vals = _distinctive(values.get(h, []))
                tot += max((self._score(h, names, q, vals)[0] for q, names in t["cols"]), default=0)
            mean = tot / max(len(header), 1)
            prior = (0.08 if self.ev.service_tables.get(tname) else 0) + (0.03 if tname.startswith("ads_") else 0)
            best.append((mean + prior, mean, tname))
        best.sort(reverse=True)
        top = best[0]
        return top[2], top[1], [{"table": n, "score": round(s, 3)} for s, _, n in best]

    # ------------------------------------------------------------ 结果组装
    def _source_info(self, qcol):
        db, table, col = qcol.split(".")
        tcmt, ccmt = self.source_comment.get(qcol, ("", ""))
        return {"column": qcol, "system": db, "system_name": SYSTEM_TITLES.get(db, db), "table": table,
                "table_comment": tcmt, "field": col, "field_comment": ccmt,
                "ontology": self.sem.describe(qcol)}

    def _trace(self, pcol):
        origins, kind, path = self.ev.trace(pcol)
        steps = []
        seen = set()
        for e in path:
            k = (e.src, e.dst)
            if k in seen:
                continue
            seen.add(k)
            steps.append({"from": e.src, "to": e.dst, "kind": e.kind, "expr": e.expr,
                          "task": e.task, "provenance": sorted(e.provenance)})
        return sorted(origins), kind, steps

    def answer_screenshot(self, ocr, asked, context=""):
        header, values, page_ctx = parse_ocr(ocr, asked)
        table, table_mean, table_rank = self._pick_platform_table(header, values)
        plat_cols = self.platform[table]["cols"] if table else []
        # 先对页面上全部字段算源字段候选，用于一致性判断
        src = {h: self._source_candidates(h, _distinctive(values.get(h, []))) for h in header}
        source_mean = sum(c[0]["score"] for c in src.values() if c) / max(len(header), 1)
        src = self._coherent(src)
        # 页面来源判定：中台候选表对整页字段的解释力不如源系统字段时，按源系统页面处理
        page_is_platform = table is not None and table_mean >= 0.5 and table_mean >= source_mean
        results = []
        for label in asked:
            h = next((x for x in header if strip(x) == strip(label)), label)
            vals = _distinctive(values.get(h, []))
            item = {"label": label, "screenshot_values": values.get(h, [])[:3]}
            pbest = None
            for q, names in plat_cols:
                s, ev = self._score(h, names, q, vals)
                if pbest is None or s > pbest[0]:
                    pbest = (s, q, ev, names)
            use_platform = page_is_platform and pbest is not None and pbest[0] >= TABLE_FLOOR
            if use_platform:
                s, pcol, ev, names = pbest
                origins, kind, steps = self._trace(pcol)
                conf = min(1.0, 0.5 * s + 0.5 * table_mean) if origins else 0.0
                item.update({
                    "route": "platform", "platform_column": pcol,
                    "platform_comment": names[0] if names else "", "derivation": kind,
                    "sources": [self._source_info(o) for o in origins], "lineage": steps,
                    "confidence": round(conf, 3), "evidence": ev,
                })
            else:
                cands = src.get(h) or self._source_candidates(h, vals)
                top = cands[0] if cands else None
                conf = min(1.0, top["score"]) if top else 0.0
                item.update({
                    "route": "source", "platform_column": "", "derivation": "direct",
                    "sources": [self._source_info(top["column"])] if top else [], "lineage": [],
                    "confidence": round(conf, 3), "evidence": top["evidence"] if top else {},
                    "alternatives": [{"column": c["column"], "score": round(c["score"], 3)} for c in cands[1:4]],
                })
            item["status"] = "ok" if item["confidence"] >= ABSTAIN and item["sources"] else "needs_review"
            item["equivalents"] = sorted({e for s in item["sources"] for e in self.sem.equivalents(s["column"])}
                                         - {s["column"] for s in item["sources"]})
            results.append(item)
        return {"page": {"context": page_ctx, "header": header,
                         "page_type": "中台报表页" if page_is_platform else "源系统页",
                         "platform_table": table if page_is_platform else None,
                         "platform_table_comment": self.platform[table]["comment"] if page_is_platform else "",
                         "platform_table_score": round(table_mean, 3), "source_route_score": round(source_mean, 3),
                         "table_ranking": table_rank},
                "fields": results}

    # ------------------------------------------------------------ 自由提问
    _Q = re.compile(r"(这个|字段|属于|来自|来源于|对应|在|是|哪个|哪张|什么|哪|的|表|里|中|吗|呢|[？?。，,\"“”'‘’：:])")

    def extract_label(self, question):
        q = question.strip()
        m = re.search(r"[“\"'‘「](.+?)[”\"'’」]", q)
        if m:
            return m.group(1)
        return self._Q.sub("", q).strip() or q

    def answer_question(self, question):
        label = self.extract_label(question)
        hits = []
        for qcol, pid, names in self.source:
            s, hit = best_similarity(label, names, self.opt.synonyms)
            if s >= 0.5:
                hits.append((s, qcol, pid, hit))
        hits.sort(key=lambda x: (-x[0], x[1]))
        best = hits[0][0] if hits else 0
        # 只有足够像才作为答案（“欠费金额”与“缴费金额”只共享“金额”，不能当答案）
        primary = [h for h in hits if best >= 0.75 and best - h[0] < 0.05]
        # 优先展示被引用的实体键，外键列作为“引用位置”
        keys = [h for h in primary if self.sem.preds[h[2]].kind == "attribute"]
        refs = [h for h in primary if self.sem.preds[h[2]].kind == "relation"]
        plat = []
        for tname, t in self.platform.items():
            for q, names in t["cols"]:
                s, _ = best_similarity(label, names, self.opt.synonyms)
                if s >= 0.95 and tname.startswith(("dws_", "ads_")):
                    origins, kind, _ = self._trace(q)
                    if kind != "direct":
                        plat.append({"platform_column": q, "comment": names[0], "derivation": kind,
                                     "sources": origins})
        return {
            "label": label,
            "status": "ok" if primary else ("derived_only" if plat else "not_found"),
            "answers": [{**self._source_info(q), "score": round(s, 3), "matched_name": hit} for s, q, _, hit in keys],
            "referenced_by": [{**self._source_info(q), "score": round(s, 3)} for s, q, _, _ in refs],
            "derived_metrics": plat[:5],
            "near_misses": [{"column": q, "score": round(s, 3), "matched_name": hit}
                            for s, q, _, hit in hits[len(primary):len(primary) + 5] if s >= 0.5],
        }
