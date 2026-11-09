"""数据中台（DataWorks/MaxCompute 风格）分层表与 ETL 定义。

ODS：源表一比一同步（数据集成任务，不出现在 SQL 日志里，但有血缘）。
DWD/DWS/ADS：SQL 任务，表名、字段名使用拼音缩写，这是映射难点之一。

每个 ETL：
  name    目标表
  layer   分层
  comment 表注释
  src     别名 -> 来源表（用于解析字段级血缘）
  frm     FROM 子句（可含 JOIN）
  cols    [(列名, 逻辑类型, 注释, 表达式)]
  where / group  可选
  noise   噪声表（备份、临时、废弃版本），页面不会用到
  lineage_exported  该任务的血缘是否出现在 DataWorks 导出里（缺失模拟）
"""
from common import stable_pct
from sources import TABLES, S, N, INT, DATE, DT


def ods_name(tb):
    return f"ods_{tb['schema']}_{tb['name'].lower()}"


def build_ods():
    """返回 ODS 表定义列表，每列带 src 指向源列。"""
    ods = []
    for tb in TABLES:
        if not tb["sync"]:
            continue
        cols = []
        for c in tb["cols"]:
            key = f"ods.{tb['schema']}.{tb['name']}.{c['name']}"
            # 中台同步时会补一部分注释（中台注释较全），但用的是数据开发自己的理解
            cmt = c["comment"] or (c["meaning"] if stable_pct(key) < 60 else "")
            cols.append({"name": c["name"].lower(), "t": c["t"], "comment": cmt,
                         "src": f"{tb['schema']}.{tb['name']}.{c['name']}"})
        ods.append({"name": ods_name(tb), "layer": "ods",
                    "comment": f"{tb['comment'] or tb['name']}（{tb['schema']}同步）",
                    "src_table": f"{tb['schema']}.{tb['name']}", "cols": cols,
                    "task": f"di_{tb['schema']}_{tb['name'].lower()}"})
    return ods


def E(name, layer, comment, src, frm, cols, where=None, group=None, noise=False, lineage_exported=True):
    return {"name": name, "layer": layer, "comment": comment, "src": src, "frm": frm,
            "cols": [{"name": n, "t": t, "comment": cm, "expr": ex} for n, t, cm, ex in cols],
            "where": where, "group": group, "noise": noise, "lineage_exported": lineage_exported,
            "task": f"sql_{name}"}


AMT = N(14, 2)

ETLS = [
    # ======================= DWD =======================
    E("dwd_yx_kh_jbxx", "dwd", "客户基本信息",
      {"c": "ods_yx186_c_cons", "o": "ods_yx186_o_org", "ct": "ods_yx186_c_contact"},
      "ods_yx186_c_cons c LEFT JOIN ods_yx186_o_org o ON o.org_no = c.org_no "
      "LEFT JOIN ods_yx186_c_contact ct ON ct.cons_id = c.cons_id AND ct.contact_mode = '01'",
      [("khbs", INT, "客户标识", "c.cons_id"),
       ("hh", S(16), "户号", "c.cons_no"),
       ("hm", S(128), "户名", "c.cons_name"),
       ("ydsz", S(256), "用电地址", "c.elec_addr"),
       ("gddw_bm", S(16), "供电单位编码", "c.org_no"),
       ("gddw_mc", S(64), "供电单位名称", "o.org_name"),
       ("hylb", S(8), "行业类别", "c.trade_code"),
       ("ydlb", S(4), "用电类别", "c.elec_type_code"),
       ("gddy", S(4), "供电电压", "c.volt_code"),
       ("htrl", N(12, 2), "合同容量", "c.contract_cap"),
       ("yhzt", S(2), "用户状态", "c.status_code"),
       ("lhrq", DATE, "立户日期", "c.build_date"),
       ("xhrq", DATE, "销户日期", "c.cancel_date"),
       ("lxr", S(64), "主联系人", "ct.contact_name"),
       ("lxdh", S(32), "联系电话", "ct.mobile")]),
    E("dwd_yx_jld_xx", "dwd", "计量点信息",
      {"m": "ods_yx186_c_mp", "c": "ods_yx186_c_cons", "r": "ods_yx186_c_meter_mp_rela", "d": "ods_yx186_d_meter"},
      "ods_yx186_c_mp m JOIN ods_yx186_c_cons c ON c.cons_id = m.cons_id "
      "LEFT JOIN ods_yx186_c_meter_mp_rela r ON r.mp_id = m.mp_id "
      "LEFT JOIN ods_yx186_d_meter d ON d.meter_id = r.meter_id",
      [("jldbs", INT, "计量点标识", "m.mp_id"),
       ("jldbh", S(20), "计量点编号", "m.mp_no"),
       ("jldmc", S(128), "计量点名称", "m.mp_name"),
       ("hh", S(16), "户号", "c.cons_no"),
       ("dnbzcbh", S(32), "电能表资产编号", "d.asset_no"),
       ("ccbh", S(32), "出厂编号", "d.made_no"),
       ("sccj", S(64), "生产厂家", "d.manufacturer"),
       ("zhbl", N(10, 2), "综合倍率", "d.t_factor"),
       ("zbrq", DATE, "装表日期", "d.inst_date"),
       ("jldzt", S(2), "计量点状态", "m.status_code")]),
    E("dwd_yx_df_ysmx", "dwd", "应收电费明细",
      {"a": "ods_yx186_a_rcvbl_flow"},
      "ods_yx186_a_rcvbl_flow a",
      [("ysbs", INT, "应收标识", "a.rcvbl_id"),
       ("hh", S(16), "户号", "a.cons_no"),
       ("dfny", S(6), "电费年月", "a.rcvbl_ym"),
       ("jsdl", AMT, "结算电量", "a.t_settle_pq"),
       ("ysje", AMT, "应收金额", "a.rcvbl_amt"),
       ("ssje", AMT, "实收金额", "a.rcved_amt"),
       ("qfje", AMT, "欠费金额", "ROUND(a.rcvbl_amt - a.rcved_amt, 2)"),
       ("wyj", AMT, "违约金", "a.penalty"),
       ("jqbz", S(2), "结清标志", "a.settle_flag"),
       ("fxrq", DATE, "发行日期", "a.rel_date")]),
    E("dwd_yx_jf_mx", "dwd", "缴费明细",
      {"p": "ods_yx186_a_pay_flow", "o": "ods_yx186_o_org"},
      "ods_yx186_a_pay_flow p LEFT JOIN ods_yx186_o_org o ON o.org_no = p.acct_org_no",
      [("jfbs", INT, "缴费标识", "p.charge_id"),
       ("hh", S(16), "户号", "p.cons_no"),
       ("ysbs", INT, "应收标识", "p.rcvbl_id"),
       ("jfsj", DT, "缴费时间", "p.charge_date"),
       ("jfje", AMT, "缴费金额", "p.rcv_amt"),
       ("jffs", S(4), "缴费方式", "p.pay_mode"),
       ("sfdw", S(64), "收费单位", "o.org_name")]),
    E("dwd_yx_cbsz", "dwd", "抄表示数明细",
      {"r": "ods_yx186_r_read", "m": "ods_yx186_c_mp", "c": "ods_yx186_c_cons",
       "rl": "ods_yx186_c_meter_mp_rela", "d": "ods_yx186_d_meter"},
      "ods_yx186_r_read r JOIN ods_yx186_c_mp m ON m.mp_id = r.mp_id "
      "JOIN ods_yx186_c_cons c ON c.cons_id = m.cons_id "
      "LEFT JOIN ods_yx186_c_meter_mp_rela rl ON rl.mp_id = r.mp_id "
      "LEFT JOIN ods_yx186_d_meter d ON d.meter_id = rl.meter_id",
      [("cbbs", INT, "抄表标识", "r.read_id"),
       ("jldbh", S(20), "计量点编号", "m.mp_no"),
       ("hh", S(16), "户号", "c.cons_no"),
       ("cbny", S(6), "抄表年月", "r.ym"),
       ("sccbsz", N(14, 2), "上次示数", "r.last_read"),
       ("bccbsz", N(14, 2), "本次示数", "r.this_read"),
       ("cjdl", AMT, "抄见电量", "ROUND((r.this_read - r.last_read) * d.t_factor, 2)"),
       ("cbrq", DATE, "抄表日期", "r.read_date")]),
    E("dwd_cj_rdl", "dwd", "测量点日电量",
      {"e": "ods_cjxt_e_mp_day_energy", "p": "ods_cjxt_e_data_mp", "dr": "ods_cjxt_e_mp_day_read"},
      "ods_cjxt_e_mp_day_energy e JOIN ods_cjxt_e_data_mp p ON p.id = e.id "
      "LEFT JOIN ods_cjxt_e_mp_day_read dr ON dr.id = e.id AND dr.data_date = e.data_date",
      [("cldbs", INT, "测量点标识", "e.id"),
       ("hh", S(16), "户号", "p.cons_no"),
       ("dnbzcbh", S(32), "电能表资产编号", "p.meter_asset_no"),
       ("sjrq", DATE, "数据日期", "e.data_date"),
       ("zxygdl", AMT, "正向有功电量", "e.pap_e"),
       ("zxwgdl", AMT, "正向无功电量", "e.prp_e"),
       ("zxygsz", N(14, 2), "正向有功示数", "dr.pap_r")]),
    E("dwd_cj_fhqx", "dwd", "测量点负荷曲线",
      {"q": "ods_cjxt_e_mp_power_curve", "p": "ods_cjxt_e_data_mp"},
      "ods_cjxt_e_mp_power_curve q JOIN ods_cjxt_e_data_mp p ON p.id = q.id",
      [("cldbs", INT, "测量点标识", "q.id"),
       ("hh", S(16), "户号", "p.cons_no"),
       ("dnbzcbh", S(32), "电能表资产编号", "p.meter_asset_no"),
       ("sjsj", DT, "数据时间", "q.data_time"),
       ("yggl", N(12, 4), "有功功率", "q.p"),
       ("wggl", N(12, 4), "无功功率", "q.q")]),
    E("dwd_cj_zd_xx", "dwd", "采集终端信息",
      {"t": "ods_cjxt_r_tmnl_run", "o": "ods_yx186_o_org"},
      "ods_cjxt_r_tmnl_run t LEFT JOIN ods_yx186_o_org o ON o.org_no = t.org_no",
      [("zdbs", INT, "终端标识", "t.terminal_id"),
       ("zdzcbh", S(32), "终端资产编号", "t.tmnl_asset_no"),
       ("zdlx", S(4), "终端类型", "t.tmnl_type_code"),
       ("zddz", S(32), "终端地址", "t.terminal_addr"),
       ("gddw_mc", S(64), "供电单位名称", "o.org_name"),
       ("yxzt", S(2), "运行状态", "t.run_status"),
       ("tyrq", DATE, "投运日期", "t.inst_date")]),
    E("dwd_kf_gd_mx", "dwd", "95598工单明细",
      {"w": "ods_kf95598_t_kf_workorder", "o": "ods_yx186_o_org", "v": "ods_kf95598_t_kf_visit"},
      "ods_kf95598_t_kf_workorder w LEFT JOIN ods_yx186_o_org o ON o.org_no = w.handle_org "
      "LEFT JOIN ods_kf95598_t_kf_visit v ON v.app_no = w.app_no",
      [("gdbh", S(32), "工单编号", "w.app_no"),
       ("slsj", DT, "受理时间", "w.accept_time"),
       ("ywlx", S(4), "业务类型", "w.busi_type"),
       ("hh", S(16), "户号", "w.cust_no"),
       ("khmc", S(128), "客户名称", "w.cust_name"),
       ("lxdh", S(32), "联系电话", "w.contact_tel"),
       ("slnr", S(1024), "受理内容", "w.accept_content"),
       ("cldw", S(64), "处理单位", "o.org_name"),
       ("clzt", S(2), "处理状态", "w.handle_status"),
       ("bjsj", DT, "办结时间", "w.finish_time"),
       ("hfpf", N(4, 1), "回访评分", "v.satisfy_score"),
       ("hfjg", S(256), "回访结果", "v.visit_result")]),
    # ======================= DWS =======================
    E("dws_yx_kh_qf_hz", "dws", "客户欠费汇总",
      {"q": "dwd_yx_df_ysmx"}, "dwd_yx_df_ysmx q",
      [("hh", S(16), "户号", "q.hh"),
       ("qfys", INT, "欠费月数", "COUNT(q.dfny)"),
       ("ljqfje", AMT, "累计欠费金额", "ROUND(SUM(q.qfje), 2)"),
       ("ljwyj", AMT, "累计违约金", "ROUND(SUM(q.wyj), 2)"),
       ("zzqfny", S(6), "最早欠费年月", "MIN(q.dfny)")],
      where="q.jqbz = '0'", group="q.hh"),
    E("dws_yx_kh_jf_hz", "dws", "客户缴费汇总",
      {"j": "dwd_yx_jf_mx"}, "dwd_yx_jf_mx j",
      [("hh", S(16), "户号", "j.hh"),
       ("zjjfsj", DT, "最近缴费时间", "MAX(j.jfsj)"),
       ("ljjfje", AMT, "累计缴费金额", "ROUND(SUM(j.jfje), 2)"),
       ("jfcs", INT, "缴费次数", "COUNT(j.jfbs)")],
      group="j.hh"),
    E("dws_yx_kh_ydl_y", "dws", "客户月用电汇总",
      {"q": "dwd_yx_df_ysmx"}, "dwd_yx_df_ysmx q",
      [("hh", S(16), "户号", "q.hh"),
       ("ny", S(6), "年月", "q.dfny"),
       ("ydl", AMT, "月用电量", "ROUND(SUM(q.jsdl), 2)"),
       ("ysdf", AMT, "月应收电费", "ROUND(SUM(q.ysje), 2)")],
      group="q.hh, q.dfny", lineage_exported=False),
    E("dws_kf_gd_tj_y", "dws", "工单月度统计",
      {"g": "dwd_kf_gd_mx"}, "dwd_kf_gd_mx g",
      [("cldw", S(64), "处理单位", "g.cldw"),
       ("tjyf", S(7), "统计月份", "SUBSTR(g.slsj, 1, 7)"),
       ("gdzs", INT, "工单总数", "COUNT(g.gdbh)"),
       ("tsgds", INT, "投诉工单数", "SUM(CASE WHEN g.ywlx = '03' THEN 1 ELSE 0 END)"),
       ("bxgds", INT, "报修工单数", "SUM(CASE WHEN g.ywlx = '01' THEN 1 ELSE 0 END)"),
       ("tsl", N(8, 4), "投诉占比", "ROUND(SUM(CASE WHEN g.ywlx = '03' THEN 1 ELSE 0 END) * 1.0 / COUNT(g.gdbh), 4)"),
       ("pjmyd", N(4, 2), "平均回访评分", "ROUND(AVG(g.hfpf), 2)")],
      group="g.cldw, SUBSTR(g.slsj, 1, 7)"),
    E("dws_cj_kh_fh_r", "dws", "客户日负荷统计",
      {"f": "dwd_cj_fhqx"}, "dwd_cj_fhqx f",
      [("hh", S(16), "户号", "f.hh"),
       ("rq", DATE, "日期", "SUBSTR(f.sjsj, 1, 10)"),
       ("zdfh", N(12, 4), "日最大负荷", "MAX(f.yggl)"),
       ("pjfh", N(12, 4), "日平均负荷", "ROUND(AVG(f.yggl), 4)")],
      group="f.hh, SUBSTR(f.sjsj, 1, 10)"),

    # ======================= ADS（页面直接查询的应用表） =======================
    # ADS 由报表团队开发，字段命名与 DWD 不一致
    E("ads_yx_khda_cx", "ads", "客户档案查询",
      {"k": "dwd_yx_kh_jbxx"}, "dwd_yx_kh_jbxx k",
      [("yhbh", S(16), "用户编号", "k.hh"),
       ("yhmc", S(128), "用户名称", "k.hm"),
       ("ydsz", S(256), "用电地址", "k.ydsz"),
       ("gddw", S(64), "供电单位", "k.gddw_mc"),
       ("ydlb", S(4), "用电类别", "k.ydlb"),
       ("hylb", S(8), "行业类别", "k.hylb"),
       ("dydj", S(4), "电压等级", "k.gddy"),
       ("htrl", N(12, 2), "合同容量", "k.htrl"),
       ("yhzt", S(2), "用户状态", "k.yhzt"),
       ("lhrq", DATE, "立户日期", "k.lhrq"),
       ("lxr", S(64), "联系人", "k.lxr"),
       ("lxdh", S(32), "联系电话", "k.lxdh")]),
    E("ads_yx_qfmx_cx", "ads", "电费欠费明细",
      {"q": "dwd_yx_df_ysmx", "k": "dwd_yx_kh_jbxx"},
      "dwd_yx_df_ysmx q JOIN dwd_yx_kh_jbxx k ON k.hh = q.hh",
      [("hh", S(16), "户号", "q.hh"),
       ("hm", S(128), "户名", "k.hm"),
       ("gddw", S(64), "供电单位", "k.gddw_mc"),
       ("dfny", S(6), "电费年月", "q.dfny"),
       ("ysdf", AMT, "应收电费", "q.ysje"),
       ("ssdf", AMT, "实收电费", "q.ssje"),
       ("qfje", AMT, "欠费金额", "q.qfje"),
       ("wyj", AMT, "违约金", "q.wyj"),
       ("fxrq", DATE, "发行日期", "q.fxrq")],
      where="q.jqbz = '0'"),
    E("ads_yx_kh360", "ads", "客户360视图",
      {"k": "dwd_yx_kh_jbxx", "q": "dws_yx_kh_qf_hz", "j": "dws_yx_kh_jf_hz"},
      "dwd_yx_kh_jbxx k LEFT JOIN dws_yx_kh_qf_hz q ON q.hh = k.hh LEFT JOIN dws_yx_kh_jf_hz j ON j.hh = k.hh",
      [("hh", S(16), "户号", "k.hh"),
       ("hm", S(128), "户名", "k.hm"),
       ("ydsz", S(256), "用电地址", "k.ydsz"),
       ("gddw", S(64), "供电单位", "k.gddw_mc"),
       ("htrl", N(12, 2), "合同容量", "k.htrl"),
       ("lxdh", S(32), "联系电话", "k.lxdh"),
       ("qfys", INT, "欠费月数", "COALESCE(q.qfys, 0)"),
       ("ljqf", AMT, "累计欠费", "COALESCE(q.ljqfje, 0)"),
       ("zjjfsj", DT, "最近缴费时间", "j.zjjfsj"),
       ("ljjf", AMT, "累计缴费", "j.ljjfje")],
      lineage_exported=False),
    E("ads_yx_ydl_fx", "ads", "月度用电分析",
      {"y": "dws_yx_kh_ydl_y", "k": "dwd_yx_kh_jbxx"},
      "dws_yx_kh_ydl_y y JOIN dwd_yx_kh_jbxx k ON k.hh = y.hh",
      [("hh", S(16), "户号", "y.hh"),
       ("hm", S(128), "户名", "k.hm"),
       ("gddw", S(64), "供电单位", "k.gddw_mc"),
       ("ydlb", S(4), "用电类别", "k.ydlb"),
       ("ny", S(6), "年月", "y.ny"),
       ("ydl", AMT, "月用电量", "y.ydl"),
       ("ysdf", AMT, "应收电费", "y.ysdf")]),
    E("ads_kf_gd_cx", "ads", "95598工单查询",
      {"g": "dwd_kf_gd_mx"}, "dwd_kf_gd_mx g",
      [("gdbh", S(32), "工单编号", "g.gdbh"),
       ("slsj", DT, "受理时间", "g.slsj"),
       ("ywlx", S(4), "业务类型", "g.ywlx"),
       ("hh", S(16), "户号", "g.hh"),
       ("khmc", S(128), "客户名称", "g.khmc"),
       ("lxdh", S(32), "联系电话", "g.lxdh"),
       ("slnr", S(1024), "受理内容", "g.slnr"),
       ("cldw", S(64), "处理单位", "g.cldw"),
       ("clzt", S(2), "处理状态", "g.clzt"),
       ("bjsj", DT, "办结时间", "g.bjsj"),
       ("hfpf", N(4, 1), "回访评分", "g.hfpf")]),
    E("ads_kf_gd_kb", "ads", "工单统计看板",
      {"t": "dws_kf_gd_tj_y"}, "dws_kf_gd_tj_y t",
      [("cldw", S(64), "处理单位", "t.cldw"),
       ("tjyf", S(7), "统计月份", "t.tjyf"),
       ("gdzs", INT, "工单总数", "t.gdzs"),
       ("tsgds", INT, "投诉工单数", "t.tsgds"),
       ("bxgds", INT, "报修工单数", "t.bxgds"),
       ("tsl", N(8, 4), "投诉占比", "t.tsl"),
       ("pjmyd", N(4, 2), "平均满意度", "t.pjmyd")]),
    E("ads_cj_dkh_fh", "ads", "大客户负荷监测",
      {"f": "dws_cj_kh_fh_r", "k": "dwd_yx_kh_jbxx"},
      "dws_cj_kh_fh_r f JOIN dwd_yx_kh_jbxx k ON k.hh = f.hh",
      [("hh", S(16), "户号", "f.hh"),
       ("hm", S(128), "户名", "k.hm"),
       ("gddw", S(64), "供电单位", "k.gddw_mc"),
       ("htrl", N(12, 2), "合同容量", "k.htrl"),
       ("rq", DATE, "日期", "f.rq"),
       ("zdfh", N(12, 4), "最大负荷", "f.zdfh"),
       ("pjfh", N(12, 4), "平均负荷", "f.pjfh"),
       ("fzl", N(8, 4), "负载率", "ROUND(f.zdfh / k.htrl, 4)")]),

    # ======================= 噪声表 =======================
    E("dwd_yx_kh_jbxx_bak", "dwd", "",
      {"k": "dwd_yx_kh_jbxx"}, "dwd_yx_kh_jbxx k",
      [("hh", S(16), "", "k.hh"), ("hm", S(128), "", "k.hm"),
       ("ydsz", S(256), "", "k.ydsz"), ("htrl", N(12, 2), "", "k.htrl")],
      noise=True, lineage_exported=False),
    E("dwd_yx_kh_xx_v1", "dwd", "客户信息（旧版，已停用）",
      {"c": "ods_yx186_c_cons"}, "ods_yx186_c_cons c",
      [("cons_no", S(16), "用户编号", "c.cons_no"), ("cons_name", S(128), "用户名称", "c.cons_name"),
       ("elec_addr", S(256), "用电地址", "c.elec_addr"), ("org_no", S(16), "供电单位", "c.org_no")],
      noise=True),
    E("tmp_qf_hh_20251201", "dws", "",
      {"q": "dwd_yx_df_ysmx"}, "dwd_yx_df_ysmx q",
      [("hh", S(16), "", "q.hh"), ("qfje", AMT, "", "ROUND(SUM(q.qfje), 2)")],
      where="q.jqbz = '0'", group="q.hh", noise=True, lineage_exported=False),
]


def select_sql(e):
    cols = ",\n  ".join(f"{c['expr']} AS {c['name']}" for c in e["cols"])
    sql = f"SELECT\n  {cols}\nFROM {e['frm']}"
    if e["where"]:
        sql += f"\nWHERE {e['where']}"
    if e["group"]:
        sql += f"\nGROUP BY {e['group']}"
    return sql


def odps_task_sql(e):
    """渲染成 DataWorks 调度任务里的样子（含分区）。"""
    return f"INSERT OVERWRITE TABLE {e['name']} PARTITION (dt = '${{bizdate}}')\n" + select_sql(e)
