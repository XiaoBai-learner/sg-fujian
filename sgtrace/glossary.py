"""营销域领域词表（人工整理的领域知识，不来自标准答案）。

用途：
  1. 缩写词 → 中文/英文：DDL 注释缺失时（采集系统约 75% 缺失）给字段、表起名
  2. 同义词组：截图上的叫法和库里注释不一致时做归一（户号 / 用户编号 / 客户编号）
  3. CIM 对齐：概念对应的 IEC 61968/61970 CIM 类，作为 skos:closeMatch 输出，待专家确认

评测时会跑“去掉同义词组”的消融，单独报告这份人工知识的贡献。
"""

# 列名缩写 → 中文（按 token 拼接）
COLUMN_TOKENS = {
    "CONS": "用户", "CUST": "客户", "ORG": "单位", "MP": "计量点", "METER": "电能表", "TMNL": "终端",
    "TERMINAL": "终端", "RCVBL": "应收", "RCVED": "实收", "RCV": "收费", "PAY": "缴费", "CHARGE": "收费",
    "READ": "示数", "SETTLE": "结算", "PQ": "电量", "AMT": "金额", "PENALTY": "违约金", "FLAG": "标志",
    "REL": "发行", "YM": "年月", "NO": "编号", "ID": "标识", "NAME": "名称", "ADDR": "地址",
    "DATE": "日期", "TIME": "时间", "TYPE": "类型", "CODE": "代码", "STATUS": "状态", "MODE": "方式",
    "ASSET": "资产", "MADE": "出厂", "INST": "安装", "SN": "序号", "CAP": "容量", "CONTRACT": "合同",
    "RUN": "运行", "VOLT": "电压", "TRADE": "行业", "ELEC": "用电", "BUILD": "立户", "CANCEL": "销户",
    "CONTACT": "联系人", "MOBILE": "手机", "TEL": "电话", "OFFICE": "办公", "APP": "工单",
    "ACCEPT": "受理", "CONTENT": "内容", "BUSI": "业务", "HANDLE": "处理", "FINISH": "办结",
    "SATISFY": "满意度", "SCORE": "评分", "VISIT": "回访", "RESULT": "结果", "COL": "采集",
    "DATA": "数据", "MANUFACTURER": "生产厂家", "WIRING": "接线", "FACTOR": "倍率", "T": "综合",
    "LAST": "上次", "THIS": "本次", "SORT": "排序", "P": "上级", "ACCT": "收费", "LODE": "负荷",
    "ATTR": "性质", "RELA": "关系",
}

# 整列名直译（多 token 合成后意义不对的专有缩写）
COLUMN_EXACT = {
    "PAP_R": "正向有功总示数", "PRP_R": "正向无功总示数", "RAP_R": "反向有功总示数",
    "PAP_E": "日正向有功电量", "PRP_E": "日正向无功电量", "RAP_E": "日反向有功电量",
    "P": "有功功率", "Q": "无功功率", "MP_SN": "测量点序号", "T_FACTOR": "综合倍率",
    "ID": "测量点标识", "DATA_DATE": "数据日期", "DATA_TIME": "数据时间", "COL_TIME": "采集时间",
    "TERMINAL_ADDR": "终端地址", "P_ORG_NO": "上级单位编号",
}

# 表名 → (英文概念名, 中文概念名, OntoWing top_category, CIM 对应类)
# 按“表名去掉系统前缀后的核心 token”查；查不到时用表注释和 token 拼接兜底。
TABLE_TERMS = {
    ("ORG",): ("SupplyOrg", "供电单位", "participant", "cim:Organisation"),
    ("CONS",): ("Consumer", "用电客户", "participant", "cim:Customer"),
    ("CONTACT",): ("Contact", "客户联系人", "participant", "cim:Person"),
    ("MP",): ("MeteringPoint", "计量点", "resource", "cim:UsagePoint"),
    ("METER",): ("Meter", "电能表", "resource", "cim:Meter"),
    ("READ",): ("MeterReading", "抄表示数", "event", "cim:MeterReading"),
    ("RCVBL", "FLOW"): ("Receivable", "应收电费", "account", "cim:AccountMovement"),
    ("PAY", "FLOW"): ("Payment", "缴费记录", "account", "cim:Receipt"),
    ("TMNL", "RUN"): ("Terminal", "采集终端", "resource", "cim:EndDevice"),
    ("DATA", "MP"): ("CollectionPoint", "采集测量点", "resource", "cim:UsagePoint"),
    ("MP", "DAY", "READ"): ("DailyFrozenReading", "日冻结示数", "event", "cim:Reading"),
    ("MP", "DAY", "ENERGY"): ("DailyEnergy", "测量点日电量", "metric", "cim:IntervalReading"),
    ("MP", "POWER", "CURVE"): ("LoadCurvePoint", "负荷曲线点", "metric", "cim:IntervalReading"),
    ("KF", "WORKORDER"): ("WorkOrder", "95598工单", "event", "cim:ServiceRequest"),
    ("KF", "VISIT"): ("ReturnVisit", "工单回访", "event", "cim:Activity"),
}

# 上位类（抽象类，不直接对应物理表）：id → (中文名, OntoWing top_category, CIM 参考, 说明)
TOP_CLASSES = {
    "Party": ("参与方", "participant", "cim:OrganisationRole", "与供用电业务相关的单位与人员"),
    "Asset": ("计量与采集设备", "resource", "cim:Asset", "安装在现场的电能表、采集终端等设备资产"),
    "UsagePointBase": ("计量位置", "resource", "cim:UsagePoint", "电能计量或数据采集的逻辑位置"),
    "MeasurementData": ("计量数据", "metric", "cim:MeasurementValue", "示数、电量、负荷等计量与采集数据"),
    "BillingRecord": ("电费账务", "account", "cim:AccountMovement", "电费应收、实收等账务记录"),
    "ServiceEvent": ("客户服务事件", "event", "cim:ServiceRequest", "客户诉求、工单及其回访"),
}

# 具体概念 → 上位类
CONCEPT_PARENT = {
    "SupplyOrg": "Party", "Consumer": "Party", "Contact": "Party",
    "Meter": "Asset", "Terminal": "Asset",
    "MeteringPoint": "UsagePointBase", "CollectionPoint": "UsagePointBase",
    "MeterReading": "MeasurementData", "DailyFrozenReading": "MeasurementData",
    "DailyEnergy": "MeasurementData", "LoadCurvePoint": "MeasurementData",
    "Receivable": "BillingRecord", "Payment": "BillingRecord",
    "WorkOrder": "ServiceEvent", "ReturnVisit": "ServiceEvent",
}

# 关系的业务名称：(源概念, 目标概念) → 名称。同一对概念之间有多条外键或自引用时，改用外键列的业务名。
RELATION_VERBS = {
    ("Consumer", "SupplyOrg"): "归属供电单位",
    ("Contact", "Consumer"): "所属客户",
    ("MeteringPoint", "Consumer"): "所属客户",
    ("MeteringPoint", "Meter"): "安装电能表",
    ("MeterReading", "MeteringPoint"): "抄表计量点",
    ("Receivable", "Consumer"): "应收客户",
    ("Payment", "Consumer"): "缴费客户",
    ("Payment", "Receivable"): "冲抵应收",
    ("Terminal", "SupplyOrg"): "运维单位",
    ("CollectionPoint", "Terminal"): "所属终端",
    ("CollectionPoint", "MeteringPoint"): "对应计量点",
    ("CollectionPoint", "Consumer"): "所属客户",
    ("CollectionPoint", "Meter"): "采集电能表",
    ("DailyFrozenReading", "CollectionPoint"): "所属测量点",
    ("DailyEnergy", "CollectionPoint"): "所属测量点",
    ("LoadCurvePoint", "CollectionPoint"): "所属测量点",
    ("WorkOrder", "Consumer"): "诉求客户",
    ("ReturnVisit", "WorkOrder"): "回访工单",
}

# 同义词组：组内任一词在比较前替换为组内第一个词（长词优先匹配）
SYNONYM_GROUPS = [
    ["用户编号", "户号", "客户编号", "用户号", "客户号"],
    ["用户名称", "户名", "客户名称", "客户名"],
    ["联系电话", "手机号码", "手机", "联系方式", "来电号码", "联系人手机号码"],
    ["电能表资产编号", "电能表资产号", "表号", "资产编号"],
    ["受理内容", "诉求内容", "工单内容", "来电内容"],
    ["工单编号", "工单号"],
    ["供电单位", "所属供电单位", "管理单位", "所属单位", "单位"],
    ["上次示数", "上月示数", "上次抄见示数", "起码"],
    ["本次示数", "本月示数", "本次抄见示数", "止码"],
    ["回访评分", "满意度评分", "评分"],
    ["计量点", "测量点"],
    ["应收电费", "应收金额"],
    ["实收电费", "实收金额"],
    ["正向有功总示数", "正向有功总", "正向有功示数"],
    ["正向无功总示数", "正向无功总", "正向无功示数"],
    ["日电量", "日正向有功电量", "日用电量"],
    ["冻结日期", "日冻结日期", "数据日期"],
    ["占比", "率"],
    ["数", "量"],
]

# 包含这些词的字段按个人信息处理（OntoWing sensitivity=confidential）
SENSITIVE_HINTS = ("手机", "电话", "联系人", "姓名", "地址", "MOBILE", "TEL", "ADDR", "CONTACT_NAME")
