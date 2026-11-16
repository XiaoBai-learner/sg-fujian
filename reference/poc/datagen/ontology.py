"""营销域本体（真值）与 R2RML 映射生成。

本体是“标准答案”形态的参考：PoC 流水线应该自动产出类似的东西，再拿它和这里比。
命名：类 yx:Consumer；属性 yx:Consumer_consNo（按类限定，避免同名列冲突）。
"""
import re

from sources import TABLES

BASE = "http://sgcc.fj/ontology/marketing#"
DATA = "http://sgcc.fj/data/"

CLASS_LABEL = {
    "SupplyOrg": ("供电单位", "电力企业内部的供电管理单位，含市公司、县公司、供电所"),
    "Consumer": ("用电客户", "与供电企业建立供用电关系的客户"),
    "Contact": ("客户联系人", "用电客户的联系人"),
    "MeteringPoint": ("计量点", "用于电能计量结算或考核的点"),
    "Meter": ("电能表", "电能表资产"),
    "MeterReading": ("抄表示数", "按月抄见的电能表示数"),
    "Receivable": ("应收电费", "按电费年月发行的应收电费"),
    "Payment": ("缴费记录", "客户缴纳电费的实收记录"),
    "Terminal": ("采集终端", "集中器、专变终端等采集设备"),
    "CollectionPoint": ("采集测量点", "采集终端下挂的测量点，对应营销计量点"),
    "DailyFrozenReading": ("日冻结示数", "采集终端每日零点冻结的电能示数"),
    "DailyEnergy": ("日电量", "按测量点计算的日电量"),
    "LoadCurvePoint": ("负荷曲线点", "测量点按时间采集的功率"),
    "WorkOrder": ("95598工单", "95598 受理的客户诉求工单"),
    "ReturnVisit": ("工单回访", "工单办结后的客户回访"),
}

# 业务同义词：截图上常见的叫法（skos:altLabel）
ALT = {
    "用户编号": ["户号", "客户编号", "用户号", "客户号"],
    "用户名称": ["户名", "客户名称", "客户名"],
    "供电单位名称": ["供电单位", "所属单位", "管理单位", "所属供电单位", "单位"],
    "合同容量（kVA）": ["合同容量", "签约容量"],
    "联系人手机号码": ["联系电话", "手机号码", "手机", "联系方式"],
    "电能表资产编号": ["表号", "电能表资产号", "资产号", "电表编号"],
    "应收电费金额（元）": ["应收电费", "应收金额", "电费"],
    "实收电费金额（元）": ["实收电费", "实收金额", "已缴金额"],
    "电费违约金（元）": ["违约金", "滞纳金"],
    "电费年月": ["账期", "应收年月", "电费月份"],
    "结算电量（kWh）": ["结算电量", "月用电量", "电量"],
    "上次抄见示数": ["上月示数", "起码", "上次示数"],
    "本次抄见示数": ["本月示数", "止码", "本次示数"],
    "正向有功总示数": ["正向有功总", "正向有功示数"],
    "正向无功总示数": ["正向无功总", "正向无功示数"],
    "日正向有功电量（kWh）": ["日电量", "日用电量"],
    "有功功率（kW）": ["负荷", "有功负荷"],
    "受理内容": ["诉求内容", "工单内容", "来电内容"],
    "来电联系电话": ["来电号码", "联系电话", "主叫号码"],
    "回访满意度评分（1-5分）": ["回访评分", "满意度评分", "满意度"],
    "工单编号": ["工单号"],
    "工单登记客户名称": ["客户名称"],
    "测量点序号": ["测量点号"],
    "日冻结日期": ["冻结日期"],
}

LINK_PROPS = [
    # 关联表表达的对象属性
    {"table": "yx186.C_METER_MP_RELA", "pred": "MeteringPoint_installedMeter", "label": "安装电能表",
     "domain": "MeteringPoint", "range": "Meter", "s_col": "MP_ID", "o_col": "METER_ID"},
]

DERIVED_PROPS = [
    # 源表没有物理列、需要计算的业务属性，用 R2RML 视图表达
    {"pred": "Receivable_arrearsAmt", "label": "欠费金额", "alt": ["欠费", "欠费金额(元)"], "domain": "Receivable",
     "sql": "SELECT RCVBL_ID, ROUND(RCVBL_AMT - RCVED_AMT, 2) AS ARREARS_AMT FROM yx186.A_RCVBL_FLOW",
     "key": "RCVBL_ID", "col": "ARREARS_AMT", "xsd": "decimal",
     "origins": ["yx186.A_RCVBL_FLOW.RCVBL_AMT", "yx186.A_RCVBL_FLOW.RCVED_AMT"]},
    {"pred": "MeterReading_readEnergy", "label": "抄见电量", "alt": ["抄表电量"], "domain": "MeterReading",
     "sql": "SELECT r.READ_ID, ROUND((r.THIS_READ - r.LAST_READ) * d.T_FACTOR, 2) AS READ_PQ FROM yx186.R_READ r "
            "JOIN yx186.C_METER_MP_RELA rl ON rl.MP_ID = r.MP_ID JOIN yx186.D_METER d ON d.METER_ID = rl.METER_ID",
     "key": "READ_ID", "col": "READ_PQ", "xsd": "decimal",
     "origins": ["yx186.R_READ.THIS_READ", "yx186.R_READ.LAST_READ", "yx186.D_METER.T_FACTOR"]},
]


def camel(col):
    parts = col.lower().split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def prop_name(cls, col):
    return f"{cls}_{camel(col)}"


def xsd(t):
    return {"str": "string", "num": "decimal", "int": "integer", "date": "date", "dt": "dateTime"}[t[0]]


def ttl_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"@zh'


def class_tables():
    return [t for t in TABLES if t["cls"] and not t["noise"]]


def build_ontology_ttl():
    L = ["@prefix yx: <%s> ." % BASE,
         "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
         "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
         "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
         "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
         "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .", "",
         "<http://sgcc.fj/ontology/marketing> a owl:Ontology ;",
         '  rdfs:label "营销域本体（福州试点，PoC 真值）"@zh .', ""]
    for cls, (lab, desc) in CLASS_LABEL.items():
        L += [f"yx:{cls} a owl:Class ; rdfs:label {ttl_str(lab)} ; skos:definition {ttl_str(desc)} .", ""]
    seen = set()
    concept_rows = []  # 源字段 -> 本体属性，供 gold/concept_map.csv
    for t in class_tables():
        cls = t["cls"]
        for c in t["cols"]:
            p = prop_name(cls, c["name"])
            col_id = f"{t['schema']}.{t['name']}.{c['name']}"
            concept_rows.append((col_id, f"yx:{p}", c["meaning"]))
            if p in seen:
                continue
            seen.add(p)
            alts = ALT.get(c["meaning"], [])
            alt = "".join(f" ;\n  skos:altLabel {ttl_str(a)}" for a in alts)
            if c["fk"]:
                L.append(f"yx:{p} a owl:ObjectProperty ;\n  rdfs:label {ttl_str(c['meaning'])}{alt} ;\n"
                         f"  rdfs:domain yx:{cls} ;\n  rdfs:range yx:{c['fk']} .\n")
                # 外键列本身往往也是业务上直接展示的编号（如户号），再给一个数据属性
                lp = p + "Value"
                L.append(f"yx:{lp} a owl:DatatypeProperty ;\n  rdfs:label {ttl_str(c['meaning'])}{alt} ;\n"
                         f"  rdfs:domain yx:{cls} ;\n  rdfs:range xsd:{xsd(c['t'])} .\n")
            else:
                L.append(f"yx:{p} a owl:DatatypeProperty ;\n  rdfs:label {ttl_str(c['meaning'])}{alt} ;\n"
                         f"  rdfs:domain yx:{cls} ;\n  rdfs:range xsd:{xsd(c['t'])} .\n")
    for lp in LINK_PROPS:
        L.append(f"yx:{lp['pred']} a owl:ObjectProperty ;\n  rdfs:label {ttl_str(lp['label'])} ;\n"
                 f"  rdfs:domain yx:{lp['domain']} ;\n  rdfs:range yx:{lp['range']} .\n")
    for d in DERIVED_PROPS:
        alt = "".join(f" ;\n  skos:altLabel {ttl_str(a)}" for a in d["alt"])
        L.append(f"yx:{d['pred']} a owl:DatatypeProperty ;\n  rdfs:label {ttl_str(d['label'])}{alt} ;\n"
                 f"  rdfs:domain yx:{d['domain']} ;\n  rdfs:range xsd:{d['xsd']} ;\n"
                 f"  skos:note {ttl_str('派生属性：' + d['sql'])} .\n")
    return "\n".join(L), concept_rows


def _template(cls, key):
    keys = key.split(",")
    return f"{DATA}{cls}/" + "/".join("{%s}" % k for k in keys)


def _table_index():
    return {f"{t['schema']}.{t['name']}": t for t in TABLES}


def build_r2rml_ttl():
    tidx = _table_index()
    # 每个类的主 TriplesMap（同类多表时第一张为主，用于外键 parentTriplesMap）
    L = ["@prefix rr: <http://www.w3.org/ns/r2rml#> .",
         "@prefix yx: <%s> ." % BASE,
         "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
         "@prefix map: <http://sgcc.fj/mapping/marketing#> .", ""]

    def tm_name(t):
        return f"map:{t['schema']}_{t['name']}"

    for t in class_tables():
        cls = t["cls"]
        tid = f"{t['schema']}.{t['name']}"
        L.append(f"{tm_name(t)} a rr:TriplesMap ;")
        L.append(f'  rr:logicalTable [ rr:tableName "{tid}" ] ;')
        L.append(f'  rr:subjectMap [ rr:template "{_template(cls, t["key"])}" ; rr:class yx:{cls} ] ;')
        pom = []
        for c in t["cols"]:
            p = prop_name(cls, c["name"])
            if c["fk"]:
                ref_schema, ref_table, ref_col = c["ref"].rsplit(".", 2)
                parent = tidx[f"{ref_schema}.{ref_table}"]
                if parent["key"] == ref_col:
                    pom.append(f'  rr:predicateObjectMap [ rr:predicate yx:{p} ;\n'
                               f'    rr:objectMap [ rr:template "{DATA}{c["fk"]}/{{{c["name"]}}}" ] ]')
                else:
                    pom.append(f'  rr:predicateObjectMap [ rr:predicate yx:{p} ;\n'
                               f'    rr:objectMap [ rr:parentTriplesMap {tm_name(parent)} ;\n'
                               f'      rr:joinCondition [ rr:child "{c["name"]}" ; rr:parent "{ref_col}" ] ] ]')
                pom.append(f'  rr:predicateObjectMap [ rr:predicate yx:{p}Value ;\n'
                           f'    rr:objectMap [ rr:column "{c["name"]}" ; rr:datatype xsd:{xsd(c["t"])} ] ]')
            else:
                pom.append(f'  rr:predicateObjectMap [ rr:predicate yx:{p} ;\n'
                           f'    rr:objectMap [ rr:column "{c["name"]}" ; rr:datatype xsd:{xsd(c["t"])} ] ]')
        L.append(" ;\n".join(pom) + " .\n")

    for lp in LINK_PROPS:
        L.append(f"map:{lp['pred']} a rr:TriplesMap ;\n"
                 f'  rr:logicalTable [ rr:tableName "{lp["table"]}" ] ;\n'
                 f'  rr:subjectMap [ rr:template "{DATA}{lp["domain"]}/{{{lp["s_col"]}}}" ] ;\n'
                 f'  rr:predicateObjectMap [ rr:predicate yx:{lp["pred"]} ;\n'
                 f'    rr:objectMap [ rr:template "{DATA}{lp["range"]}/{{{lp["o_col"]}}}" ] ] .\n')
    for d in DERIVED_PROPS:
        sql = d["sql"].replace('"', '\\"')
        L.append(f"map:{d['pred']} a rr:TriplesMap ;\n"
                 f'  rr:logicalTable [ rr:sqlQuery "{sql}" ] ;\n'
                 f'  rr:subjectMap [ rr:template "{DATA}{d["domain"]}/{{{d["key"]}}}" ] ;\n'
                 f'  rr:predicateObjectMap [ rr:predicate yx:{d["pred"]} ;\n'
                 f'    rr:objectMap [ rr:column "{d["col"]}" ; rr:datatype xsd:{d["xsd"]} ] ] .\n')
    return "\n".join(L)


def strip_unit(label):
    return re.sub(r"[（(].*?[)）]", "", label).strip()
