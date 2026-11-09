"""源业务系统表结构定义（营销域，福州试点）。

三个源系统：
  yx186   营销业务应用系统（Oracle，SG186 风格命名）
  cjxt    用电信息采集系统（Oracle，注释缺失严重）
  kf95598 95598 客服系统（MySQL，与营销系统同一概念命名不同）

每列字段：
  name     物理列名
  t        逻辑类型（见 common.py）
  meaning  真实业务含义（真值，用于本体标签，不一定出现在 DDL 注释里）
  cmt      DDL 注释：None=按系统缺失率随机决定；""=强制缺失；其他=使用该文本
  fk       外键指向的本体类（同时用于判定等价字段）
  ref      外键指向的物理列 "schema.TABLE.COL"
"""
from common import stable_pct

S = lambda n: ("str", n)
N = lambda p, s: ("num", p, s)
INT = ("int",)
DATE = ("date",)
DT = ("dt",)

# 各系统列注释保留率（%）
COMMENT_KEEP = {"yx186": 75, "cjxt": 25, "kf95598": 90}


def C(name, t, meaning, cmt=None, fk=None, ref=None):
    return {"name": name, "t": t, "meaning": meaning, "cmt": cmt, "fk": fk, "ref": ref}


def T(schema, name, comment, cls, key, cols, noise=False, sync=True, tcmt=True):
    """cls: 对应本体类（None 表示关联表/噪声表）；sync: 是否同步进中台 ODS。"""
    return {"schema": schema, "name": name, "comment": comment, "cls": cls, "key": key,
            "cols": cols, "noise": noise, "sync": sync, "tcmt": tcmt}


def resolve_comments(tables):
    """确定每列最终 DDL 注释（写回 col['comment']）。"""
    for tb in tables:
        keep = COMMENT_KEEP[tb["schema"]]
        for c in tb["cols"]:
            if c["cmt"] is not None:
                c["comment"] = c["cmt"]
            else:
                key = f"{tb['schema']}.{tb['name']}.{c['name']}"
                c["comment"] = c["meaning"] if stable_pct(key) < keep else ""


YX = "yx186"
TABLES = [
    # ---------------- 营销业务应用系统 yx186 ----------------
    T(YX, "O_ORG", "供电单位", "SupplyOrg", "ORG_NO", [
        C("ORG_NO", S(16), "供电单位编码", "单位编号"),
        C("ORG_NAME", S(64), "供电单位名称", "单位名称"),
        C("P_ORG_NO", S(16), "上级供电单位编码", "上级单位", fk="SupplyOrg", ref="yx186.O_ORG.ORG_NO"),
        C("ORG_TYPE", S(2), "单位类别", "单位类型 02市 03县 04供电所"),
        C("SORT_NO", INT, "排序号", ""),
    ]),
    T(YX, "C_CONS", "用电客户", "Consumer", "CONS_ID", [
        C("CONS_ID", INT, "客户标识", "客户ID"),
        C("CONS_NO", S(16), "用户编号", "用户编号"),
        C("CONS_NAME", S(128), "用户名称", "用户名称"),
        C("ELEC_ADDR", S(256), "用电地址"),
        C("ORG_NO", S(16), "管理单位", "供电单位", fk="SupplyOrg", ref="yx186.O_ORG.ORG_NO"),
        C("TRADE_CODE", S(8), "行业分类代码"),
        C("ELEC_TYPE_CODE", S(4), "用电类别"),
        C("VOLT_CODE", S(4), "供电电压等级", "电压"),
        C("CONTRACT_CAP", N(12, 2), "合同容量（kVA）"),
        C("RUN_CAP", N(12, 2), "运行容量（kVA）", ""),
        C("STATUS_CODE", S(2), "用户状态"),
        C("BUILD_DATE", DATE, "立户日期", "建档日期"),
        C("CANCEL_DATE", DATE, "销户日期"),
        C("LODE_ATTR_CODE", S(2), "负荷性质", ""),
    ]),
    T(YX, "C_CONTACT", "客户联系人", "Contact", "CONTACT_ID", [
        C("CONTACT_ID", INT, "联系人标识", ""),
        C("CONS_ID", INT, "所属客户标识", "客户ID", fk="Consumer", ref="yx186.C_CONS.CONS_ID"),
        C("CONTACT_NAME", S(64), "联系人姓名", "联系人"),
        C("MOBILE", S(32), "联系人手机号码", "手机"),
        C("OFFICE_TEL", S(32), "办公电话"),
        C("CONTACT_MODE", S(2), "联系人类别", "类型 01主要 02备用"),
    ]),
    T(YX, "C_MP", "计量点", "MeteringPoint", "MP_ID", [
        C("MP_ID", INT, "计量点标识", "计量点ID"),
        C("MP_NO", S(20), "计量点编号"),
        C("MP_NAME", S(128), "计量点名称"),
        C("CONS_ID", INT, "所属客户标识", fk="Consumer", ref="yx186.C_CONS.CONS_ID"),
        C("MP_ADDR", S(256), "计量点地址", ""),
        C("VOLT_CODE", S(4), "计量点电压等级"),
        C("MP_ATTR_CODE", S(2), "计量点性质", "性质 01结算 02考核"),
        C("STATUS_CODE", S(2), "计量点状态"),
    ]),
    T(YX, "D_METER", "电能表资产", "Meter", "METER_ID", [
        C("METER_ID", INT, "电能表标识", ""),
        C("ASSET_NO", S(32), "电能表资产编号", "资产编号"),
        C("MADE_NO", S(32), "出厂编号"),
        C("MANUFACTURER", S(64), "生产厂家", "厂家"),
        C("TYPE_CODE", S(8), "电能表类型", ""),
        C("WIRING_MODE", S(2), "接线方式"),
        C("T_FACTOR", N(10, 2), "综合倍率", "倍率"),
        C("INST_DATE", DATE, "装表日期"),
    ]),
    T(YX, "C_METER_MP_RELA", "计量点电能表关系", None, "RELA_ID", [
        C("RELA_ID", INT, "关系标识", ""),
        C("MP_ID", INT, "计量点标识", fk="MeteringPoint", ref="yx186.C_MP.MP_ID"),
        C("METER_ID", INT, "电能表标识", fk="Meter", ref="yx186.D_METER.METER_ID"),
        C("RELA_DATE", DATE, "建立关系日期", ""),
    ], tcmt=False),
    T(YX, "R_READ", "抄表示数", "MeterReading", "READ_ID", [
        C("READ_ID", INT, "抄表记录标识", ""),
        C("MP_ID", INT, "计量点标识", fk="MeteringPoint", ref="yx186.C_MP.MP_ID"),
        C("YM", S(6), "抄表年月", "年月"),
        C("LAST_READ", N(14, 2), "上次抄见示数", "上次示数"),
        C("THIS_READ", N(14, 2), "本次抄见示数", "本次示数"),
        C("READ_DATE", DATE, "抄表日期"),
        C("READ_TYPE_CODE", S(2), "抄表方式", "抄表方式 01远抄 02手工"),
    ]),
    T(YX, "A_RCVBL_FLOW", "应收电费流水", "Receivable", "RCVBL_ID", [
        C("RCVBL_ID", INT, "应收电费标识", ""),
        C("CONS_NO", S(16), "用户编号", "户号", fk="Consumer", ref="yx186.C_CONS.CONS_NO"),
        C("RCVBL_YM", S(6), "电费年月", "应收年月"),
        C("T_SETTLE_PQ", N(14, 2), "结算电量（kWh）", "结算电量"),
        C("RCVBL_AMT", N(14, 2), "应收电费金额（元）", "应收金额"),
        C("RCVED_AMT", N(14, 2), "实收电费金额（元）", "实收金额"),
        C("PENALTY", N(12, 2), "电费违约金（元）", ""),
        C("SETTLE_FLAG", S(2), "结清标志", "结清标志 0未结清 1已结清"),
        C("REL_DATE", DATE, "电费发行日期"),
    ]),
    T(YX, "A_PAY_FLOW", "实收电费流水", "Payment", "CHARGE_ID", [
        C("CHARGE_ID", INT, "缴费记录标识", ""),
        C("CONS_NO", S(16), "用户编号", "户号", fk="Consumer", ref="yx186.C_CONS.CONS_NO"),
        C("RCVBL_ID", INT, "对应应收标识", fk="Receivable", ref="yx186.A_RCVBL_FLOW.RCVBL_ID"),
        C("CHARGE_DATE", DT, "缴费时间", "收费日期"),
        C("RCV_AMT", N(14, 2), "缴费金额（元）", "金额"),
        C("PAY_MODE", S(4), "缴费方式", "缴费方式 01柜台 02支付宝 03微信 04银行代扣"),
        C("ACCT_ORG_NO", S(16), "收费单位", "", fk="SupplyOrg", ref="yx186.O_ORG.ORG_NO"),
    ]),
    T(YX, "A_RCVBL_FLOW_HIS", "应收电费历史流水（2024）", "Receivable", "RCVBL_ID", [
        C("RCVBL_ID", INT, "应收电费标识", ""),
        C("CONS_NO", S(16), "用户编号", "户号", fk="Consumer", ref="yx186.C_CONS.CONS_NO"),
        C("RCVBL_YM", S(6), "电费年月", "应收年月"),
        C("T_SETTLE_PQ", N(14, 2), "结算电量（kWh）", "结算电量"),
        C("RCVBL_AMT", N(14, 2), "应收电费金额（元）", "应收金额"),
        C("RCVED_AMT", N(14, 2), "实收电费金额（元）", "实收金额"),
        C("PENALTY", N(12, 2), "电费违约金（元）", ""),
        C("SETTLE_FLAG", S(2), "结清标志", "结清标志"),
        C("REL_DATE", DATE, "电费发行日期"),
    ]),
    T(YX, "C_CONS_BAK_20230601", "", None, "CONS_ID", [
        C("CONS_ID", INT, "客户标识", ""),
        C("CONS_NO", S(16), "用户编号", ""),
        C("CONS_NAME", S(128), "用户名称", ""),
        C("ELEC_ADDR", S(256), "用电地址", ""),
        C("ORG_NO", S(16), "管理单位", ""),
        C("CONTRACT_CAP", N(12, 2), "合同容量", ""),
    ], noise=True, sync=False, tcmt=False),
    T(YX, "TMP_CONS_CHK", "", None, "CONS_NO", [
        C("CONS_NO", S(16), "用户编号", ""),
        C("CONS_NAME", S(128), "用户名称", ""),
        C("CHK_FLAG", S(2), "核查标志", ""),
    ], noise=True, sync=False, tcmt=False),

    # ---------------- 用电信息采集系统 cjxt ----------------
    T("cjxt", "R_TMNL_RUN", "终端运行档案", "Terminal", "TERMINAL_ID", [
        C("TERMINAL_ID", INT, "终端标识"),
        C("TMNL_ASSET_NO", S(32), "终端资产编号"),
        C("TMNL_TYPE_CODE", S(4), "终端类型", "终端类型 01集中器 02专变终端"),
        C("TERMINAL_ADDR", S(32), "终端逻辑地址"),
        C("ORG_NO", S(16), "终端所属供电单位", fk="SupplyOrg", ref="yx186.O_ORG.ORG_NO"),
        C("RUN_STATUS", S(2), "终端运行状态"),
        C("INST_DATE", DATE, "终端投运日期"),
    ]),
    T("cjxt", "E_DATA_MP", "采集测量点", "CollectionPoint", "ID", [
        C("ID", INT, "测量点标识"),
        C("TERMINAL_ID", INT, "所属终端标识", fk="Terminal", ref="cjxt.R_TMNL_RUN.TERMINAL_ID"),
        C("MP_SN", INT, "测量点序号"),
        C("MP_ID", INT, "营销计量点标识", fk="MeteringPoint", ref="yx186.C_MP.MP_ID"),
        C("CONS_NO", S(16), "用户编号", fk="Consumer", ref="yx186.C_CONS.CONS_NO"),
        C("METER_ASSET_NO", S(32), "电能表资产编号", fk="Meter", ref="yx186.D_METER.ASSET_NO"),
        C("T_FACTOR", N(10, 2), "综合倍率（采集侧）"),
    ], tcmt=False),
    T("cjxt", "E_MP_DAY_READ", "", "DailyFrozenReading", "ID,DATA_DATE", [
        C("ID", INT, "测量点标识", fk="CollectionPoint", ref="cjxt.E_DATA_MP.ID"),
        C("DATA_DATE", DATE, "日冻结日期"),
        C("PAP_R", N(14, 2), "正向有功总示数"),
        C("PRP_R", N(14, 2), "正向无功总示数"),
        C("RAP_R", N(14, 2), "反向有功总示数"),
        C("COL_TIME", DT, "采集时间"),
    ], tcmt=False),
    T("cjxt", "E_MP_DAY_ENERGY", "", "DailyEnergy", "ID,DATA_DATE", [
        C("ID", INT, "测量点标识", fk="CollectionPoint", ref="cjxt.E_DATA_MP.ID"),
        C("DATA_DATE", DATE, "数据日期"),
        C("PAP_E", N(14, 2), "日正向有功电量（kWh）"),
        C("PRP_E", N(14, 2), "日正向无功电量（kvarh）"),
        C("RAP_E", N(14, 2), "日反向有功电量（kWh）"),
    ], tcmt=False),
    T("cjxt", "E_MP_POWER_CURVE", "", "LoadCurvePoint", "ID,DATA_TIME", [
        C("ID", INT, "测量点标识", fk="CollectionPoint", ref="cjxt.E_DATA_MP.ID"),
        C("DATA_TIME", DT, "曲线数据时间"),
        C("P", N(12, 4), "有功功率（kW）"),
        C("Q", N(12, 4), "无功功率（kvar）"),
    ], tcmt=False),

    # ---------------- 95598 客服系统 kf95598（MySQL） ----------------
    T("kf95598", "t_kf_workorder", "95598工单", "WorkOrder", "APP_NO", [
        C("APP_NO", S(32), "工单编号", "工单号"),
        C("ACCEPT_TIME", DT, "受理时间"),
        C("BUSI_TYPE", S(4), "业务类型", "业务类型 01故障报修 02咨询 03投诉 04意见建议"),
        C("CUST_NO", S(16), "用户编号", "客户编号", fk="Consumer", ref="yx186.C_CONS.CONS_NO"),
        C("CUST_NAME", S(128), "工单登记客户名称", "客户名称"),
        C("CONTACT_TEL", S(32), "来电联系电话", "联系电话"),
        C("ACCEPT_CONTENT", S(1024), "受理内容"),
        C("HANDLE_ORG", S(16), "处理单位", "处理单位", fk="SupplyOrg", ref="yx186.O_ORG.ORG_NO"),
        C("HANDLE_STATUS", S(2), "工单处理状态", "状态"),
        C("FINISH_TIME", DT, "办结时间"),
        C("SATISFY_CODE", S(2), "客户满意度评价", "满意度"),
    ]),
    T("kf95598", "t_kf_visit", "工单回访", "ReturnVisit", "VISIT_ID", [
        C("VISIT_ID", INT, "回访记录标识", ""),
        C("APP_NO", S(32), "工单编号", "工单号", fk="WorkOrder", ref="kf95598.t_kf_workorder.APP_NO"),
        C("VISIT_TIME", DT, "回访时间"),
        C("VISIT_RESULT", S(256), "回访结果说明", "回访结果"),
        C("SATISFY_SCORE", N(4, 1), "回访满意度评分（1-5分）", "评分"),
    ]),
]
