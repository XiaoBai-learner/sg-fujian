"""确定性生成源系统样例数据。返回 {(schema, table): [row_dict, ...]}。"""
import random
from datetime import date, datetime, timedelta

from common import SEED

DISTRICTS = [("01", "鼓楼"), ("02", "台江"), ("03", "仓山"), ("04", "晋安"),
             ("05", "马尾"), ("06", "闽侯"), ("07", "长乐")]
STATION_SUFFIX = ["城区", "东郊", "西郊"]
ROADS = ["五四路", "八一七路", "工业路", "福飞路", "华林路", "杨桥路", "六一路", "江滨大道",
         "金山大道", "首山路", "湖东路", "福新路", "连江路", "则徐大道", "上下杭路", "南江滨路"]
SURNAMES = "陈林黄张吴王郑李刘杨何许谢罗余高蔡江游魏".replace("", " ").split()
GIVEN = "建明华丽芳伟强敏静秀英志勇国荣海燕玉兰俊杰文斌晓红春梅宏辉"
CO_PREFIX = ["闽江", "榕城", "鼓山", "海峡", "三坊", "左海", "乌山", "福盛", "东南", "新榕"]
CO_INDUSTRY = [("机械制造", "C34"), ("食品加工", "C14"), ("纺织", "C17"), ("物流", "G59"),
               ("商贸", "F51"), ("酒店管理", "H61"), ("电子科技", "C39"), ("建材", "C30")]
MANUFACTURERS = ["威胜集团", "林洋能源", "华立科技", "科陆电子", "炬华科技", "宁波三星"]
PAY_MODES = ["01", "02", "03", "04"]


def _name(rnd):
    return rnd.choice(SURNAMES) + "".join(rnd.choice(GIVEN) for _ in range(rnd.choice([1, 2])))


def _mobile(rnd):
    return "1" + rnd.choice(["35", "37", "38", "39", "50", "52", "58", "59", "77", "86", "88"]) + \
        "".join(str(rnd.randint(0, 9)) for _ in range(8))


def _rand_date(rnd, start: date, end: date):
    return start + timedelta(days=rnd.randint(0, (end - start).days))


def _ym_iter(y, m_from, m_to):
    return [f"{y}{m:02d}" for m in range(m_from, m_to + 1)]


def build():
    rnd = random.Random(SEED)
    out = {}

    # ---------- 供电单位 ----------
    orgs = [{"ORG_NO": "35101", "ORG_NAME": "国网福州供电公司", "P_ORG_NO": "351",
             "ORG_TYPE": "02", "SORT_NO": 1}]
    stations = []  # (station_org_no, district_name)
    for i, (dc, dn) in enumerate(DISTRICTS):
        county = f"35101{dc}"
        orgs.append({"ORG_NO": county, "ORG_NAME": f"国网福州{dn}供电服务中心",
                     "P_ORG_NO": "35101", "ORG_TYPE": "03", "SORT_NO": i + 2})
        for j, suf in enumerate(STATION_SUFFIX):
            st = f"{county}{j + 1:02d}"
            orgs.append({"ORG_NO": st, "ORG_NAME": f"{dn}{suf}供电所", "P_ORG_NO": county,
                         "ORG_TYPE": "04", "SORT_NO": j + 1})
            stations.append((st, dn))
    out[("yx186", "O_ORG")] = orgs

    # ---------- 用电客户 ----------
    cons = []
    for i in range(600):
        st, dn = rnd.choice(stations)
        kind = "res" if i < 480 else ("biz" if i < 560 else "ind")
        if kind == "res":
            name = _name(rnd)
            trade, etype, volt = "R01", "401", "AC02"  # 城乡居民 / 220V
            cap = rnd.choice([4, 6, 8, 10, 12])
            lode = "03"
        else:
            ind, trade = rnd.choice(CO_INDUSTRY)
            name = f"福州{rnd.choice(CO_PREFIX)}{ind}有限公司"
            if rnd.random() < 0.3:
                name = name.replace("有限公司", "股份有限公司")
            etype = "201" if kind == "biz" else "100"
            volt = "AC03" if kind == "biz" else rnd.choice(["AC10", "AC10", "AC35"])
            cap = rnd.choice([50, 80, 100, 160, 200]) if kind == "biz" else rnd.choice([315, 400, 630, 800, 1250, 2000])
            lode = rnd.choice(["01", "02"])
        build_d = _rand_date(rnd, date(2008, 1, 1), date(2024, 6, 30))
        status = "1"
        cancel = None
        if rnd.random() < 0.05:
            status = "9"
            cancel = _rand_date(rnd, date(2025, 3, 1), date(2025, 10, 31))
        cons.append({
            "CONS_ID": 10_000_000 + i * 7 + rnd.randint(0, 6),
            "CONS_NO": f"35{rnd.randint(10, 99)}{i:06d}{rnd.randint(10, 99)}",
            "CONS_NAME": name,
            "ELEC_ADDR": f"福建省福州市{dn}区{rnd.choice(ROADS)}{rnd.randint(1, 399)}号"
                         + (f"{rnd.randint(1, 30)}栋{rnd.randint(1, 3)}单元{rnd.randint(1, 33)}{rnd.randint(1, 4):02d}室"
                            if kind == "res" else ""),
            "ORG_NO": st,
            "TRADE_CODE": trade,
            "ELEC_TYPE_CODE": etype,
            "VOLT_CODE": volt,
            "CONTRACT_CAP": float(cap),
            "RUN_CAP": float(cap),
            "STATUS_CODE": status,
            "BUILD_DATE": build_d.isoformat(),
            "CANCEL_DATE": cancel.isoformat() if cancel else None,
            "LODE_ATTR_CODE": lode,
            "_kind": kind,
            "_cancel": cancel,
        })
    out[("yx186", "C_CONS")] = cons

    # ---------- 联系人 ----------
    contacts = []
    cid = 50_000_000
    for c in cons:
        n = 2 if rnd.random() < 0.3 else 1
        for k in range(n):
            cid += 1
            contacts.append({
                "CONTACT_ID": cid, "CONS_ID": c["CONS_ID"],
                "CONTACT_NAME": c["CONS_NAME"] if (c["_kind"] == "res" and k == 0) else _name(rnd),
                "MOBILE": _mobile(rnd),
                "OFFICE_TEL": None if c["_kind"] == "res" else f"0591-{rnd.randint(22000000, 88999999)}",
                "CONTACT_MODE": "01" if k == 0 else "02",
            })
    out[("yx186", "C_CONTACT")] = contacts

    # ---------- 计量点 / 电能表 / 关系 ----------
    mps, meters, relas = [], [], []
    mp_id, meter_id = 30_000_000, 70_000_000
    for c in cons:
        n = 1 if c["_kind"] == "res" else (1 if c["_kind"] == "biz" else 2)
        for k in range(n):
            mp_id += rnd.randint(1, 3)
            meter_id += rnd.randint(1, 3)
            mps.append({
                "MP_ID": mp_id, "MP_NO": f"{c['CONS_NO']}{k + 1:02d}",
                "MP_NAME": f"{c['CONS_NAME']}{'' if n == 1 else f'#{k + 1}'}计量点",
                "CONS_ID": c["CONS_ID"], "MP_ADDR": c["ELEC_ADDR"],
                "VOLT_CODE": c["VOLT_CODE"], "MP_ATTR_CODE": "01",
                "STATUS_CODE": "1" if c["STATUS_CODE"] == "1" else "9",
                "_cons": c, "_kind": c["_kind"],
            })
            if c["_kind"] == "res":
                tf = 1.0
            elif c["_kind"] == "biz":
                tf = float(rnd.choice([1, 20, 30]))
            else:
                tf = float(rnd.choice([200, 400, 600, 1000]))
            inst = _rand_date(rnd, date(2016, 1, 1), date(2024, 6, 30))
            meters.append({
                "METER_ID": meter_id,
                "ASSET_NO": f"3410001{rnd.randint(100000000, 999999999)}",
                "MADE_NO": f"{rnd.randint(2015, 2023)}{rnd.randint(1000000, 9999999)}",
                "MANUFACTURER": rnd.choice(MANUFACTURERS),
                "TYPE_CODE": "DDZY" if c["_kind"] == "res" else "DTZY",
                "WIRING_MODE": "11" if c["_kind"] == "res" else "33",
                "T_FACTOR": tf,
                "INST_DATE": inst.isoformat(),
            })
            relas.append({"RELA_ID": 90_000_000 + len(relas), "MP_ID": mp_id,
                          "METER_ID": meter_id, "RELA_DATE": inst.isoformat()})
    out[("yx186", "C_MP")] = mps
    out[("yx186", "D_METER")] = meters
    out[("yx186", "C_METER_MP_RELA")] = relas
    meter_of_mp = {r["MP_ID"]: m for r, m in zip(relas, meters)}

    # ---------- 抄表示数（2025 年 1-12 月） ----------
    reads = []
    read_id = 1
    mp_month_pq = {}  # (mp_id, ym) -> 电量
    mp_dec_start = {}  # mp_id -> 12 月起始示数（采集侧日示数用）
    for mp in mps:
        cancel = mp["_cons"]["_cancel"]
        base = {"res": (150, 450), "biz": (4, 25), "ind": (20, 180)}[mp["_kind"]]
        cur = round(rnd.uniform(1000, 30000), 2)
        tf = meter_of_mp[mp["MP_ID"]]["T_FACTOR"]
        for m in range(1, 13):
            if cancel and m > cancel.month:
                break
            ym = f"2025{m:02d}"
            season = 1.35 if m in (7, 8, 9) else (1.1 if m in (6, 10) else 1.0)
            inc = round(rnd.uniform(*base) * season, 2)  # 表码增量，电量 = 增量 × 倍率
            if m == 12:
                mp_dec_start[mp["MP_ID"]] = cur
            reads.append({
                "READ_ID": read_id, "MP_ID": mp["MP_ID"], "YM": ym,
                "LAST_READ": cur, "THIS_READ": round(cur + inc, 2),
                "READ_DATE": f"2025-{m:02d}-{rnd.randint(1, 5):02d}",
                "READ_TYPE_CODE": "01" if rnd.random() < 0.96 else "02",
            })
            mp_month_pq[(mp["MP_ID"], ym)] = round(inc * tf, 2)
            cur = round(cur + inc, 2)
            read_id += 1
    out[("yx186", "R_READ")] = reads

    # ---------- 应收 / 实收 ----------
    price = {"res": 0.4983, "biz": 0.7015, "ind": 0.6290}
    mps_of_cons = {}
    for mp in mps:
        mps_of_cons.setdefault(mp["CONS_ID"], []).append(mp["MP_ID"])
    arrears_cons = {c["CONS_NO"] for c in rnd.sample(cons, 48)}

    def rcvbl_rows(year, months, id_base, with_pay):
        rows, pays = [], []
        rid = id_base
        for c in cons:
            for ym in months:
                if year == 2025:
                    pq = sum(mp_month_pq.get((m, ym), 0) for m in mps_of_cons[c["CONS_ID"]])
                    if pq == 0:
                        continue
                else:
                    pq = round(rnd.uniform(150, 450) if c["_kind"] == "res" else rnd.uniform(2000, 90000), 2)
                pq = round(pq, 2)
                amt = round(pq * price[c["_kind"]], 2)
                rid += 1
                m = int(ym[4:])
                is_arrear = year == 2025 and c["CONS_NO"] in arrears_cons and m >= rnd.choice([8, 9, 10, 11])
                if is_arrear:
                    rcved = round(amt * rnd.choice([0, 0, 0.3, 0.5]), 2)
                    penalty = round((amt - rcved) * 0.001 * (12 - m + 1) * 30, 2)
                    flag = "0"
                else:
                    rcved, penalty, flag = amt, 0.0, "1"
                rel = date(year, m, 10)
                rows.append({"RCVBL_ID": rid, "CONS_NO": c["CONS_NO"], "RCVBL_YM": ym,
                             "T_SETTLE_PQ": pq, "RCVBL_AMT": amt, "RCVED_AMT": rcved,
                             "PENALTY": penalty, "SETTLE_FLAG": flag, "REL_DATE": rel.isoformat()})
                if with_pay and rcved > 0:
                    pay_t = datetime(year, m, 10) + timedelta(days=rnd.randint(1, 25),
                                                              hours=rnd.randint(8, 21), minutes=rnd.randint(0, 59))
                    pays.append({"CHARGE_ID": None, "CONS_NO": c["CONS_NO"], "RCVBL_ID": rid,
                                 "CHARGE_DATE": pay_t.strftime("%Y-%m-%d %H:%M:%S"), "RCV_AMT": rcved,
                                 "PAY_MODE": rnd.choice(PAY_MODES), "ACCT_ORG_NO": c["ORG_NO"]})
        return rows, pays

    rcvbl, pays = rcvbl_rows(2025, _ym_iter(2025, 1, 12), 600_000_000, True)
    pays.sort(key=lambda p: p["CHARGE_DATE"])
    for i, p in enumerate(pays):
        p["CHARGE_ID"] = 800_000_000 + i
    his, _ = rcvbl_rows(2024, _ym_iter(2024, 1, 12), 500_000_000, False)
    out[("yx186", "A_RCVBL_FLOW")] = rcvbl
    out[("yx186", "A_PAY_FLOW")] = pays
    out[("yx186", "A_RCVBL_FLOW_HIS")] = his

    # ---------- 噪声表 ----------
    bak = []
    for c in cons[:420]:  # 2023 年的旧快照：部分地址、容量后来变更
        bak.append({"CONS_ID": c["CONS_ID"], "CONS_NO": c["CONS_NO"], "CONS_NAME": c["CONS_NAME"],
                    "ELEC_ADDR": c["ELEC_ADDR"] if rnd.random() < 0.85 else c["ELEC_ADDR"][:-4],
                    "ORG_NO": c["ORG_NO"],
                    "CONTRACT_CAP": c["CONTRACT_CAP"] if rnd.random() < 0.9 else c["CONTRACT_CAP"] / 2})
    out[("yx186", "C_CONS_BAK_20230601")] = bak
    out[("yx186", "TMP_CONS_CHK")] = [{"CONS_NO": c["CONS_NO"], "CONS_NAME": c["CONS_NAME"],
                                       "CHK_FLAG": rnd.choice(["0", "1"])} for c in rnd.sample(cons, 60)]

    # ---------- 采集系统 ----------
    tmnls, tmnl_of_station = [], {}
    tid = 4_000_000
    for st, dn in stations:  # 每个供电所 2 台集中器
        for k in range(2):
            tid += 1
            tmnls.append({"TERMINAL_ID": tid, "TMNL_ASSET_NO": f"3420001{rnd.randint(100000000, 999999999)}",
                          "TMNL_TYPE_CODE": "01", "TERMINAL_ADDR": f"{rnd.randint(0x1000, 0xFFFF):04X}{rnd.randint(0x1000, 0xFFFF):04X}",
                          "ORG_NO": st, "RUN_STATUS": "1",
                          "INST_DATE": _rand_date(rnd, date(2015, 1, 1), date(2020, 12, 31)).isoformat()})
            tmnl_of_station.setdefault(st, []).append(tid)
    emps = []
    eid = 1_000_000
    sn_count = {}
    for mp in mps:
        c = mp["_cons"]
        if c["_kind"] == "res":
            t = rnd.choice(tmnl_of_station[c["ORG_NO"]])
        else:  # 专变终端，一户一台
            tid += 1
            tmnls.append({"TERMINAL_ID": tid, "TMNL_ASSET_NO": f"3420002{rnd.randint(100000000, 999999999)}",
                          "TMNL_TYPE_CODE": "02", "TERMINAL_ADDR": f"{rnd.randint(0x1000, 0xFFFF):04X}{rnd.randint(0x1000, 0xFFFF):04X}",
                          "ORG_NO": c["ORG_NO"], "RUN_STATUS": "1" if c["STATUS_CODE"] == "1" else "3",
                          "INST_DATE": _rand_date(rnd, date(2016, 1, 1), date(2023, 12, 31)).isoformat()})
            t = tid
        sn_count[t] = sn_count.get(t, 0) + 1
        eid += 1
        mtr = meter_of_mp[mp["MP_ID"]]
        emps.append({"ID": eid, "TERMINAL_ID": t, "MP_SN": sn_count[t], "MP_ID": mp["MP_ID"],
                     "CONS_NO": c["CONS_NO"], "METER_ASSET_NO": mtr["ASSET_NO"],
                     "T_FACTOR": mtr["T_FACTOR"], "_mp": mp})
    out[("cjxt", "R_TMNL_RUN")] = tmnls
    out[("cjxt", "E_DATA_MP")] = emps

    # 2025 年 12 月日冻结示数与日电量，和营销侧 12 月抄表增量保持一致
    dreads, denergy, curve = [], [], []
    dec_read = {r["MP_ID"]: r for r in reads if r["YM"] == "202512"}
    for e in emps:
        r = dec_read.get(e["MP_ID"])
        if r is None:
            continue
        total_inc = r["THIS_READ"] - r["LAST_READ"]
        weights = [rnd.uniform(0.7, 1.3) for _ in range(31)]
        s = sum(weights)
        cur = r["LAST_READ"]
        prp = round(cur * rnd.uniform(0.2, 0.4), 2)
        for d in range(31):
            inc = round(total_inc * weights[d] / s, 2)
            day = date(2025, 12, d + 1)
            q_inc = round(inc * rnd.uniform(0.2, 0.45), 2)
            dreads.append({"ID": e["ID"], "DATA_DATE": day.isoformat(), "PAP_R": round(cur, 2),
                           "PRP_R": prp, "RAP_R": 0.0,
                           "COL_TIME": f"{day.isoformat()} 00:{rnd.randint(5, 59):02d}:{rnd.randint(0, 59):02d}"})
            denergy.append({"ID": e["ID"], "DATA_DATE": day.isoformat(),
                            "PAP_E": round(inc * e["T_FACTOR"], 2),
                            "PRP_E": round(q_inc * e["T_FACTOR"], 2), "RAP_E": 0.0})
            cur += inc
            prp = round(prp + q_inc, 2)
            # 非居民 12-25 至 12-31 的整点负荷曲线
            if e["_mp"]["_kind"] != "res" and d >= 24:
                avg_kw = inc * e["T_FACTOR"] / 24
                for h in range(24):
                    shape = 0.45 if h < 7 else (1.35 if 9 <= h <= 17 else 0.9)
                    p = round(avg_kw * shape * rnd.uniform(0.9, 1.1), 4)
                    curve.append({"ID": e["ID"], "DATA_TIME": f"{day.isoformat()} {h:02d}:00:00",
                                  "P": p, "Q": round(p * rnd.uniform(0.25, 0.4), 4)})
    out[("cjxt", "E_MP_DAY_READ")] = dreads
    out[("cjxt", "E_MP_DAY_ENERGY")] = denergy
    out[("cjxt", "E_MP_POWER_CURVE")] = curve

    # ---------- 95598 ----------
    contact_main = {}
    for ct in contacts:
        if ct["CONTACT_MODE"] == "01":
            contact_main[ct["CONS_ID"]] = ct["MOBILE"]
    contents = {
        "01": ["家中突然停电，邻居家有电，请尽快派人处理", "表箱冒烟，有焦糊味", "小区整栋楼停电", "线路被树枝挂断"],
        "02": ["咨询阶梯电价计算方式", "咨询电费发票如何开具", "咨询如何办理增容", "咨询峰谷电价政策"],
        "03": ["抢修人员到达不及时", "电费突然增加，怀疑电表不准", "频繁停电影响生产", "营业厅工作人员态度差"],
        "04": ["建议增加线上缴费渠道", "建议提前通知计划停电"],
    }
    wos, visits = [], []
    vid = 1
    for i in range(900):
        c = rnd.choice(cons)
        bt = rnd.choices(["01", "02", "03", "04"], weights=[45, 35, 15, 5])[0]
        acc = datetime(2025, 1, 1) + timedelta(minutes=rnd.randint(0, 364 * 24 * 60))
        status = "05" if rnd.random() < 0.94 else rnd.choice(["02", "03"])
        fin = acc + timedelta(hours=rnd.uniform(0.5, 6) if bt == "01" else rnd.uniform(2, 120)) if status == "05" else None
        tel = contact_main.get(c["CONS_ID"]) if rnd.random() < 0.6 else _mobile(rnd)
        app_no = f"{acc:%y%m%d}{rnd.randint(10000000, 99999999)}"
        score = None
        if status == "05" and rnd.random() < 0.8:
            score = float(rnd.choices([5, 4, 3, 2, 1], weights=[60, 22, 10, 5, 3])[0])
            visits.append({"VISIT_ID": vid, "APP_NO": app_no,
                           "VISIT_TIME": (fin + timedelta(hours=rnd.randint(2, 48))).strftime("%Y-%m-%d %H:%M:%S"),
                           "VISIT_RESULT": "客户表示满意" if score >= 4 else ("客户表示基本满意" if score == 3 else "客户不满意，已反馈处理单位"),
                           "SATISFY_SCORE": score})
            vid += 1
        wos.append({
            "APP_NO": app_no, "ACCEPT_TIME": acc.strftime("%Y-%m-%d %H:%M:%S"), "BUSI_TYPE": bt,
            "CUST_NO": c["CONS_NO"],
            # 客服登记的客户名称存在空格、简称等不一致
            "CUST_NAME": c["CONS_NAME"] if rnd.random() < 0.85 else c["CONS_NAME"].replace("有限公司", "").replace("股份", "") + " ",
            "CONTACT_TEL": tel, "ACCEPT_CONTENT": rnd.choice(contents[bt]),
            "HANDLE_ORG": c["ORG_NO"], "HANDLE_STATUS": status,
            "FINISH_TIME": fin.strftime("%Y-%m-%d %H:%M:%S") if fin else None,
            "SATISFY_CODE": None if score is None else {5: "01", 4: "02", 3: "03"}.get(int(score), "04"),
        })
    wos.sort(key=lambda w: w["ACCEPT_TIME"])
    out[("kf95598", "t_kf_workorder")] = wos
    out[("kf95598", "t_kf_visit")] = visits

    # 去掉内部辅助字段
    for rows in out.values():
        for r in rows:
            for k in [k for k in r if k.startswith("_")]:
                del r[k]
    return out
