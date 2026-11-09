"""业务规则与约束（OntoWing wing-rules-editor/2）。

规则把对象、属性、关系串起来推导出新的业务分类（派生类），并允许规则引用其他规则的结论：
  欠费客户 = 有未结清应收电费的客户                       （应收电费 —应收客户→ 用电客户）
  投诉工单 = 业务类型为投诉的工单
  投诉客户 = 投诉工单的诉求客户                          （引用“投诉工单”）
  不满意工单 = 回访评分 ≤ 2 的工单                        （工单回访 —回访工单→ 95598工单）
  两部制电价客户 = 合同容量 ≥ 315kVA 的客户
  重点关注客户 = 既欠费又投诉的客户                       （引用“欠费客户”“投诉客户”）
  建议优先催收（DR，建议性结论，OntoWing 不导出为事实） = 欠费的两部制电价客户

规则引用的字段用“源表.列”书写，构建时解析成本体里的属性或关系 id；字段不存在时整条规则跳过并记录。
码值（"0" 未结清、"03" 投诉）取自 DDL 注释，阈值（315kVA、评分 ≤ 2）是领域假设，标注“待业务确认”。

cross_check 是独立的 SQL 口径：直接在沙箱库上计算同一结论，用来核对“R2RML 物化 + 规则推理”的结果。
"""

DERIVED = [
    # id, 中文名, 上位概念, 说明
    ("ArrearsConsumer", "欠费客户", "Consumer", "存在未结清应收电费的用电客户（规则推导）"),
    ("TwoPartTariffConsumer", "两部制电价客户", "Consumer", "合同容量 ≥ 315kVA 的用电客户（规则推导）"),
    ("ComplaintWorkOrder", "投诉工单", "WorkOrder", "业务类型为投诉的 95598 工单（规则推导）"),
    ("ComplainingConsumer", "投诉客户", "Consumer", "发起过投诉工单的用电客户（规则推导）"),
    ("DissatisfiedWorkOrder", "不满意工单", "WorkOrder", "回访评分 ≤ 2 的工单（规则推导）"),
    ("KeyAttentionConsumer", "重点关注客户", "Consumer", "既欠费又投诉的用电客户（规则推导）"),
    ("CollectionPriorityConsumer", "建议优先催收客户", "Consumer", "欠费的两部制电价客户（建议性结论）"),
]

V = lambda n: {"var": n}
S = lambda v: {"literal": {"value": v, "datatype": "string"}}
D = lambda v: {"literal": {"value": v, "datatype": "decimal"}}

# 规则体里的谓词写法：("class", 概念) / ("attr", "源表.列", 主语, 宾语) / ("rel", "源表.列", 主语, 宾语) /
#                    ("cmp", 运算符, 左, 右)
RULES = [
    {"id": "arrearsConsumer", "name": "欠费客户认定", "level": "FR",
     "nl": "应收电费未结清，则该应收电费的客户是欠费客户",
     "source": "yx186.A_RCVBL_FLOW.SETTLE_FLAG 注释“结清标志 0未结清 1已结清”",
     "body": [("class", "Receivable", "r"), ("attr", "yx186.A_RCVBL_FLOW.SETTLE_FLAG", "r", S("0")),
              ("rel", "yx186.A_RCVBL_FLOW.CONS_NO", "r", "c")],
     "head": ("ArrearsConsumer", "c"),
     "cross_check": "SELECT COUNT(DISTINCT CONS_NO) FROM (SELECT CONS_NO, SETTLE_FLAG FROM yx186.A_RCVBL_FLOW "
                    "UNION ALL SELECT CONS_NO, SETTLE_FLAG FROM yx186.A_RCVBL_FLOW_HIS) WHERE SETTLE_FLAG = '0'"},
    {"id": "twoPartTariff", "name": "两部制电价客户认定", "level": "FR",
     "nl": "合同容量不小于 315kVA 的客户执行两部制电价",
     "source": "电价政策：受电变压器容量 315kVA 及以上执行两部制电价（领域假设，待业务确认）",
     "body": [("class", "Consumer", "c"), ("attr", "yx186.C_CONS.CONTRACT_CAP", "c", "k"),
              ("cmp", "gte", "k", D("315.0"))],
     "head": ("TwoPartTariffConsumer", "c"),
     "cross_check": "SELECT COUNT(*) FROM yx186.C_CONS WHERE CONTRACT_CAP >= 315"},
    {"id": "complaintWorkOrder", "name": "投诉工单认定", "level": "FR",
     "nl": "业务类型为 03（投诉）的工单是投诉工单",
     "source": "kf95598.t_kf_workorder.BUSI_TYPE 注释“业务类型 01故障报修 02咨询 03投诉 04意见建议”",
     "body": [("class", "WorkOrder", "w"), ("attr", "kf95598.t_kf_workorder.BUSI_TYPE", "w", S("03"))],
     "head": ("ComplaintWorkOrder", "w"),
     "cross_check": "SELECT COUNT(*) FROM kf95598.t_kf_workorder WHERE BUSI_TYPE = '03'"},
    {"id": "complainingConsumer", "name": "投诉客户认定", "level": "FR",
     "nl": "投诉工单的诉求客户是投诉客户（引用规则“投诉工单认定”）",
     "source": "规则链：投诉工单认定 → 投诉客户认定",
     "body": [("class", "ComplaintWorkOrder", "w"), ("rel", "kf95598.t_kf_workorder.CUST_NO", "w", "c")],
     "head": ("ComplainingConsumer", "c"),
     "cross_check": "SELECT COUNT(DISTINCT CUST_NO) FROM kf95598.t_kf_workorder WHERE BUSI_TYPE = '03'"},
    {"id": "dissatisfiedWorkOrder", "name": "不满意工单认定", "level": "FR",
     "nl": "回访评分不高于 2 分的工单是不满意工单",
     "source": "回访评分 1-5 分，≤2 视为不满意（领域假设，待业务确认）",
     "body": [("class", "ReturnVisit", "v"), ("attr", "kf95598.t_kf_visit.SATISFY_SCORE", "v", "s"),
              ("cmp", "lte", "s", D("2.0")), ("rel", "kf95598.t_kf_visit.APP_NO", "v", "w")],
     "head": ("DissatisfiedWorkOrder", "w"),
     "cross_check": "SELECT COUNT(DISTINCT APP_NO) FROM kf95598.t_kf_visit WHERE SATISFY_SCORE <= 2"},
    {"id": "keyAttentionConsumer", "name": "重点关注客户认定", "level": "FR",
     "nl": "既是欠费客户又是投诉客户的，列为重点关注客户（引用两条规则的结论）",
     "source": "规则链：欠费客户认定 + 投诉客户认定 → 重点关注客户认定",
     "body": [("class", "ArrearsConsumer", "c"), ("class", "ComplainingConsumer", "c")],
     "head": ("KeyAttentionConsumer", "c"),
     "cross_check": "SELECT COUNT(*) FROM (SELECT DISTINCT CONS_NO AS c FROM yx186.A_RCVBL_FLOW WHERE SETTLE_FLAG = '0' "
                    "INTERSECT SELECT DISTINCT CUST_NO FROM kf95598.t_kf_workorder WHERE BUSI_TYPE = '03')"},
    {"id": "collectionPriority", "name": "建议优先催收", "level": "DR",
     "nl": "欠费的两部制电价客户，建议优先催收（建议性规则，供人工参考，不作为事实导出）",
     "source": "规则链：欠费客户认定 + 两部制电价客户认定",
     "body": [("class", "ArrearsConsumer", "c"), ("class", "TwoPartTariffConsumer", "c")],
     "head": ("CollectionPriorityConsumer", "c"),
     "cross_check": "SELECT COUNT(*) FROM (SELECT DISTINCT CONS_NO AS c FROM yx186.A_RCVBL_FLOW WHERE SETTLE_FLAG = '0' "
                    "INTERSECT SELECT CONS_NO FROM yx186.C_CONS WHERE CONTRACT_CAP >= 315)"},
]

# 约束（OntoWing constraints，SHACL 风格；OntoWing 当前不导出到 TTL，记为 rule_constraints 损失，由本项目在实例上执行）
CONSTRAINTS = [
    {"id": "consNoRequired", "name": "每户有且只有一个用户编号", "target": "Consumer",
     "field": "yx186.C_CONS.CONS_NO", "min_count": 1, "max_count": 1, "pattern": "^35[0-9]{10}$"},
    {"id": "contractCapNonNegative", "name": "合同容量不能为负", "target": "Consumer",
     "field": "yx186.C_CONS.CONTRACT_CAP", "min_inclusive": D("0.0")["literal"]},
    {"id": "receivableHasConsumer", "name": "应收电费必须关联到用电客户", "target": "Receivable",
     "field": "yx186.A_RCVBL_FLOW.CONS_NO", "relation": True, "min_count": 1, "class": "Consumer"},
    {"id": "workOrderAcceptTime", "name": "工单必须有受理时间", "target": "WorkOrder",
     "field": "kf95598.t_kf_workorder.ACCEPT_TIME", "min_count": 1},
    {"id": "visitScoreRange", "name": "回访评分在 1-5 分之间", "target": "ReturnVisit",
     "field": "kf95598.t_kf_visit.SATISFY_SCORE",
     "min_inclusive": D("1.0")["literal"], "max_inclusive": D("5.0")["literal"]},
    {"id": "workOrderHasConsumer", "name": "工单客户编号必须是在册用电客户", "target": "WorkOrder",
     "field": "kf95598.t_kf_workorder.CUST_NO", "relation": True, "min_count": 1, "class": "Consumer"},
]


def _term(t):
    return V(t) if isinstance(t, str) else t


def derive(build):
    """返回 (派生概念列表, wing-rules-editor/2, 规则元数据, 跳过记录)。"""
    attr_of = build.column_attr
    rel_of = {}
    for r in build.relations:
        for q in build.concepts.get(r["source_id"], {}).get("tables", [r["child"]]):
            rel_of[f"{q}.{r['child_col']}"] = r["id"]
        rel_of[f"{r['child']}.{r['child_col']}"] = r["id"]
    known = set(build.concepts) | {d[0] for d in DERIVED}
    skipped, rules, meta = [], [], []

    def resolve(field, relation):
        table, col = field.rsplit(".", 1)
        return rel_of.get(field) if relation else attr_of.get((table, col))

    for spec in RULES:
        items, ok, concepts = [], True, set()
        for atom in spec["body"]:
            kind = atom[0]
            if kind == "class":
                if atom[1] not in known:
                    ok = False
                    break
                items.append({"kind": "class", "predicate": atom[1], "args": [V(atom[2])]})
                concepts.add(atom[1])
            elif kind in ("attr", "rel"):
                pid = resolve(atom[1], kind == "rel")
                if pid is None:
                    ok = False
                    break
                items.append({"kind": "attribute" if kind == "attr" else "relation", "predicate": pid,
                              "args": [V(atom[2]), _term(atom[3])]})
            else:
                items.append({"op": "compare", "operator": atom[1], "left": _term(atom[2]), "right": _term(atom[3])})
        if not ok:
            skipped.append({"rule": spec["id"], "reason": f"字段或概念不存在：{atom}"})
            continue
        head = {"kind": "class", "predicate": spec["head"][0], "args": [V(spec["head"][1])]}
        rules.append({"id": spec["id"], "name": spec["name"], "level": spec["level"], "calibration": "pending",
                      "nl": spec["nl"], "source": spec["source"], "enabled": True,
                      "body": {"op": "all", "items": items}, "head": head})
        meta.append({"id": spec["id"], "name": spec["name"], "level": spec["level"], "nl": spec["nl"],
                     "source": spec["source"], "head": spec["head"][0], "body": items,
                     "body_concepts": sorted(concepts | {_domain(build, it) for it in items if it.get("kind") in
                                                         ("attribute", "relation")} - {None}),
                     "cross_check": spec["cross_check"]})

    constraints = []
    for c in CONSTRAINTS:
        pid = resolve(c["field"], c.get("relation", False))
        if pid is None:
            skipped.append({"constraint": c["id"], "reason": f"字段不存在：{c['field']}"})
            continue
        item = {"id": c["id"], "name": c["name"], "target_class": c["target"], "property": pid}
        for k in ("min_count", "max_count", "pattern", "min_inclusive", "max_inclusive", "class"):
            if k in c:
                item[k] = c[k]
        constraints.append(item)

    tops = {c: build.concepts[c]["top_category"] for c in build.concepts}
    derived = [{"id": i, "name": n, "top_category": tops.get(p), "parents": [p], "disjoint_with": [],
                "description": d, "english_name": i} for i, n, p, d in DERIVED
               if any(r["head"]["predicate"] == i for r in rules)]
    editor = {"format_version": "wing-rules-editor/2", "rules": rules, "constraints": constraints}
    return derived, editor, meta, skipped


def _domain(build, item):
    pid = item["predicate"]
    for a in build.attributes:
        if a["id"] == pid:
            return a["concept_id"]
    for r in build.relations:
        if r["id"] == pid:
            return r["source_id"]
    return None
