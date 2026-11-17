-- 原 DataWorks 任务转换为只读视图定义；供建模解析及隔离测试库核对。

CREATE VIEW `sgtrace_trial_platform`.`ods_yx186_o_org` AS
SELECT
  `ORG_NO` AS `org_no`,
  `ORG_NAME` AS `org_name`,
  `P_ORG_NO` AS `p_org_no`,
  `ORG_TYPE` AS `org_type`,
  `SORT_NO` AS `sort_no`
FROM `sgtrace_trial_yx186`.`O_ORG`;

CREATE VIEW `sgtrace_trial_platform`.`ods_yx186_c_cons` AS
SELECT
  `CONS_ID` AS `cons_id`,
  `CONS_NO` AS `cons_no`,
  `CONS_NAME` AS `cons_name`,
  `ELEC_ADDR` AS `elec_addr`,
  `ORG_NO` AS `org_no`,
  `TRADE_CODE` AS `trade_code`,
  `ELEC_TYPE_CODE` AS `elec_type_code`,
  `VOLT_CODE` AS `volt_code`,
  `CONTRACT_CAP` AS `contract_cap`,
  `RUN_CAP` AS `run_cap`,
  `STATUS_CODE` AS `status_code`,
  `BUILD_DATE` AS `build_date`,
  `CANCEL_DATE` AS `cancel_date`,
  `LODE_ATTR_CODE` AS `lode_attr_code`
FROM `sgtrace_trial_yx186`.`C_CONS`;

CREATE VIEW `sgtrace_trial_platform`.`ods_yx186_c_contact` AS
SELECT
  `CONTACT_ID` AS `contact_id`,
  `CONS_ID` AS `cons_id`,
  `CONTACT_NAME` AS `contact_name`,
  `MOBILE` AS `mobile`,
  `OFFICE_TEL` AS `office_tel`,
  `CONTACT_MODE` AS `contact_mode`
FROM `sgtrace_trial_yx186`.`C_CONTACT`;

CREATE VIEW `sgtrace_trial_platform`.`ods_yx186_c_mp` AS
SELECT
  `MP_ID` AS `mp_id`,
  `MP_NO` AS `mp_no`,
  `MP_NAME` AS `mp_name`,
  `CONS_ID` AS `cons_id`,
  `MP_ADDR` AS `mp_addr`,
  `VOLT_CODE` AS `volt_code`,
  `MP_ATTR_CODE` AS `mp_attr_code`,
  `STATUS_CODE` AS `status_code`
FROM `sgtrace_trial_yx186`.`C_MP`;

CREATE VIEW `sgtrace_trial_platform`.`ods_yx186_d_meter` AS
SELECT
  `METER_ID` AS `meter_id`,
  `ASSET_NO` AS `asset_no`,
  `MADE_NO` AS `made_no`,
  `MANUFACTURER` AS `manufacturer`,
  `TYPE_CODE` AS `type_code`,
  `WIRING_MODE` AS `wiring_mode`,
  `T_FACTOR` AS `t_factor`,
  `INST_DATE` AS `inst_date`
FROM `sgtrace_trial_yx186`.`D_METER`;

CREATE VIEW `sgtrace_trial_platform`.`ods_yx186_c_meter_mp_rela` AS
SELECT
  `RELA_ID` AS `rela_id`,
  `MP_ID` AS `mp_id`,
  `METER_ID` AS `meter_id`,
  `RELA_DATE` AS `rela_date`
FROM `sgtrace_trial_yx186`.`C_METER_MP_RELA`;

CREATE VIEW `sgtrace_trial_platform`.`ods_yx186_r_read` AS
SELECT
  `READ_ID` AS `read_id`,
  `MP_ID` AS `mp_id`,
  `YM` AS `ym`,
  `LAST_READ` AS `last_read`,
  `THIS_READ` AS `this_read`,
  `READ_DATE` AS `read_date`,
  `READ_TYPE_CODE` AS `read_type_code`
FROM `sgtrace_trial_yx186`.`R_READ`;

CREATE VIEW `sgtrace_trial_platform`.`ods_yx186_a_rcvbl_flow` AS
SELECT
  `RCVBL_ID` AS `rcvbl_id`,
  `CONS_NO` AS `cons_no`,
  `RCVBL_YM` AS `rcvbl_ym`,
  `T_SETTLE_PQ` AS `t_settle_pq`,
  `RCVBL_AMT` AS `rcvbl_amt`,
  `RCVED_AMT` AS `rcved_amt`,
  `PENALTY` AS `penalty`,
  `SETTLE_FLAG` AS `settle_flag`,
  `REL_DATE` AS `rel_date`
FROM `sgtrace_trial_yx186`.`A_RCVBL_FLOW`;

CREATE VIEW `sgtrace_trial_platform`.`ods_yx186_a_pay_flow` AS
SELECT
  `CHARGE_ID` AS `charge_id`,
  `CONS_NO` AS `cons_no`,
  `RCVBL_ID` AS `rcvbl_id`,
  `CHARGE_DATE` AS `charge_date`,
  `RCV_AMT` AS `rcv_amt`,
  `PAY_MODE` AS `pay_mode`,
  `ACCT_ORG_NO` AS `acct_org_no`
FROM `sgtrace_trial_yx186`.`A_PAY_FLOW`;

CREATE VIEW `sgtrace_trial_platform`.`ods_cjxt_r_tmnl_run` AS
SELECT
  `TERMINAL_ID` AS `terminal_id`,
  `TMNL_ASSET_NO` AS `tmnl_asset_no`,
  `TMNL_TYPE_CODE` AS `tmnl_type_code`,
  `TERMINAL_ADDR` AS `terminal_addr`,
  `ORG_NO` AS `org_no`,
  `RUN_STATUS` AS `run_status`,
  `INST_DATE` AS `inst_date`
FROM `sgtrace_trial_cjxt`.`R_TMNL_RUN`;

CREATE VIEW `sgtrace_trial_platform`.`ods_cjxt_e_data_mp` AS
SELECT
  `ID` AS `id`,
  `TERMINAL_ID` AS `terminal_id`,
  `MP_SN` AS `mp_sn`,
  `MP_ID` AS `mp_id`,
  `CONS_NO` AS `cons_no`,
  `METER_ASSET_NO` AS `meter_asset_no`,
  `T_FACTOR` AS `t_factor`
FROM `sgtrace_trial_cjxt`.`E_DATA_MP`;

CREATE VIEW `sgtrace_trial_platform`.`ods_cjxt_e_mp_day_read` AS
SELECT
  `ID` AS `id`,
  `DATA_DATE` AS `data_date`,
  `PAP_R` AS `pap_r`,
  `PRP_R` AS `prp_r`,
  `RAP_R` AS `rap_r`,
  `COL_TIME` AS `col_time`
FROM `sgtrace_trial_cjxt`.`E_MP_DAY_READ`;

CREATE VIEW `sgtrace_trial_platform`.`ods_cjxt_e_mp_day_energy` AS
SELECT
  `ID` AS `id`,
  `DATA_DATE` AS `data_date`,
  `PAP_E` AS `pap_e`,
  `PRP_E` AS `prp_e`,
  `RAP_E` AS `rap_e`
FROM `sgtrace_trial_cjxt`.`E_MP_DAY_ENERGY`;

CREATE VIEW `sgtrace_trial_platform`.`ods_cjxt_e_mp_power_curve` AS
SELECT
  `ID` AS `id`,
  `DATA_TIME` AS `data_time`,
  `P` AS `p`,
  `Q` AS `q`
FROM `sgtrace_trial_cjxt`.`E_MP_POWER_CURVE`;

CREATE VIEW `sgtrace_trial_platform`.`ods_kf95598_t_kf_workorder` AS
SELECT
  `APP_NO` AS `app_no`,
  `ACCEPT_TIME` AS `accept_time`,
  `BUSI_TYPE` AS `busi_type`,
  `CUST_NO` AS `cust_no`,
  `CUST_NAME` AS `cust_name`,
  `CONTACT_TEL` AS `contact_tel`,
  `ACCEPT_CONTENT` AS `accept_content`,
  `HANDLE_ORG` AS `handle_org`,
  `HANDLE_STATUS` AS `handle_status`,
  `FINISH_TIME` AS `finish_time`,
  `SATISFY_CODE` AS `satisfy_code`
FROM `sgtrace_trial_kf95598`.`t_kf_workorder`;

CREATE VIEW `sgtrace_trial_platform`.`ods_kf95598_t_kf_visit` AS
SELECT
  `VISIT_ID` AS `visit_id`,
  `APP_NO` AS `app_no`,
  `VISIT_TIME` AS `visit_time`,
  `VISIT_RESULT` AS `visit_result`,
  `SATISFY_SCORE` AS `satisfy_score`
FROM `sgtrace_trial_kf95598`.`t_kf_visit`;

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_dwd_yx_kh_jbxx.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`dwd_yx_kh_jbxx` AS
SELECT
  c.cons_id AS khbs,
  c.cons_no AS hh,
  c.cons_name AS hm,
  c.elec_addr AS ydsz,
  c.org_no AS gddw_bm,
  o.org_name AS gddw_mc,
  c.trade_code AS hylb,
  c.elec_type_code AS ydlb,
  c.volt_code AS gddy,
  c.contract_cap AS htrl,
  c.status_code AS yhzt,
  c.build_date AS lhrq,
  c.cancel_date AS xhrq,
  ct.contact_name AS lxr,
  ct.mobile AS lxdh
FROM `sgtrace_trial_platform`.ods_yx186_c_cons AS c
LEFT JOIN `sgtrace_trial_platform`.ods_yx186_o_org AS o
  ON o.org_no = c.org_no
LEFT JOIN `sgtrace_trial_platform`.ods_yx186_c_contact AS ct
  ON ct.cons_id = c.cons_id AND ct.contact_mode = '01';

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_dwd_yx_jld_xx.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`dwd_yx_jld_xx` AS
SELECT
  m.mp_id AS jldbs,
  m.mp_no AS jldbh,
  m.mp_name AS jldmc,
  c.cons_no AS hh,
  d.asset_no AS dnbzcbh,
  d.made_no AS ccbh,
  d.manufacturer AS sccj,
  d.t_factor AS zhbl,
  d.inst_date AS zbrq,
  m.status_code AS jldzt
FROM `sgtrace_trial_platform`.ods_yx186_c_mp AS m
JOIN `sgtrace_trial_platform`.ods_yx186_c_cons AS c
  ON c.cons_id = m.cons_id
LEFT JOIN `sgtrace_trial_platform`.ods_yx186_c_meter_mp_rela AS r
  ON r.mp_id = m.mp_id
LEFT JOIN `sgtrace_trial_platform`.ods_yx186_d_meter AS d
  ON d.meter_id = r.meter_id;

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_dwd_yx_df_ysmx.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`dwd_yx_df_ysmx` AS
SELECT
  a.rcvbl_id AS ysbs,
  a.cons_no AS hh,
  a.rcvbl_ym AS dfny,
  a.t_settle_pq AS jsdl,
  a.rcvbl_amt AS ysje,
  a.rcved_amt AS ssje,
  ROUND(a.rcvbl_amt - a.rcved_amt, 2) AS qfje,
  a.penalty AS wyj,
  a.settle_flag AS jqbz,
  a.rel_date AS fxrq
FROM `sgtrace_trial_platform`.ods_yx186_a_rcvbl_flow AS a;

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_dwd_yx_jf_mx.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`dwd_yx_jf_mx` AS
SELECT
  p.charge_id AS jfbs,
  p.cons_no AS hh,
  p.rcvbl_id AS ysbs,
  p.charge_date AS jfsj,
  p.rcv_amt AS jfje,
  p.pay_mode AS jffs,
  o.org_name AS sfdw
FROM `sgtrace_trial_platform`.ods_yx186_a_pay_flow AS p
LEFT JOIN `sgtrace_trial_platform`.ods_yx186_o_org AS o
  ON o.org_no = p.acct_org_no;

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_dwd_yx_cbsz.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`dwd_yx_cbsz` AS
SELECT
  r.read_id AS cbbs,
  m.mp_no AS jldbh,
  c.cons_no AS hh,
  r.ym AS cbny,
  r.last_read AS sccbsz,
  r.this_read AS bccbsz,
  ROUND((
    r.this_read - r.last_read
  ) * d.t_factor, 2) AS cjdl,
  r.read_date AS cbrq
FROM `sgtrace_trial_platform`.ods_yx186_r_read AS r
JOIN `sgtrace_trial_platform`.ods_yx186_c_mp AS m
  ON m.mp_id = r.mp_id
JOIN `sgtrace_trial_platform`.ods_yx186_c_cons AS c
  ON c.cons_id = m.cons_id
LEFT JOIN `sgtrace_trial_platform`.ods_yx186_c_meter_mp_rela AS rl
  ON rl.mp_id = r.mp_id
LEFT JOIN `sgtrace_trial_platform`.ods_yx186_d_meter AS d
  ON d.meter_id = rl.meter_id;

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_dwd_cj_rdl.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`dwd_cj_rdl` AS
SELECT
  e.id AS cldbs,
  p.cons_no AS hh,
  p.meter_asset_no AS dnbzcbh,
  e.data_date AS sjrq,
  e.pap_e AS zxygdl,
  e.prp_e AS zxwgdl,
  dr.pap_r AS zxygsz
FROM `sgtrace_trial_platform`.ods_cjxt_e_mp_day_energy AS e
JOIN `sgtrace_trial_platform`.ods_cjxt_e_data_mp AS p
  ON p.id = e.id
LEFT JOIN `sgtrace_trial_platform`.ods_cjxt_e_mp_day_read AS dr
  ON dr.id = e.id AND dr.data_date = e.data_date;

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_dwd_cj_fhqx.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`dwd_cj_fhqx` AS
SELECT
  q.id AS cldbs,
  p.cons_no AS hh,
  p.meter_asset_no AS dnbzcbh,
  q.data_time AS sjsj,
  q.p AS yggl,
  q.q AS wggl
FROM `sgtrace_trial_platform`.ods_cjxt_e_mp_power_curve AS q
JOIN `sgtrace_trial_platform`.ods_cjxt_e_data_mp AS p
  ON p.id = q.id;

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_dwd_cj_zd_xx.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`dwd_cj_zd_xx` AS
SELECT
  t.terminal_id AS zdbs,
  t.tmnl_asset_no AS zdzcbh,
  t.tmnl_type_code AS zdlx,
  t.terminal_addr AS zddz,
  o.org_name AS gddw_mc,
  t.run_status AS yxzt,
  t.inst_date AS tyrq
FROM `sgtrace_trial_platform`.ods_cjxt_r_tmnl_run AS t
LEFT JOIN `sgtrace_trial_platform`.ods_yx186_o_org AS o
  ON o.org_no = t.org_no;

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_dwd_kf_gd_mx.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`dwd_kf_gd_mx` AS
SELECT
  w.app_no AS gdbh,
  w.accept_time AS slsj,
  w.busi_type AS ywlx,
  w.cust_no AS hh,
  w.cust_name AS khmc,
  w.contact_tel AS lxdh,
  w.accept_content AS slnr,
  o.org_name AS cldw,
  w.handle_status AS clzt,
  w.finish_time AS bjsj,
  v.satisfy_score AS hfpf,
  v.visit_result AS hfjg
FROM `sgtrace_trial_platform`.ods_kf95598_t_kf_workorder AS w
LEFT JOIN `sgtrace_trial_platform`.ods_yx186_o_org AS o
  ON o.org_no = w.handle_org
LEFT JOIN `sgtrace_trial_platform`.ods_kf95598_t_kf_visit AS v
  ON v.app_no = w.app_no;

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_dws_yx_kh_qf_hz.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`dws_yx_kh_qf_hz` AS
SELECT
  q.hh AS hh,
  COUNT(q.dfny) AS qfys,
  ROUND(SUM(q.qfje), 2) AS ljqfje,
  ROUND(SUM(q.wyj), 2) AS ljwyj,
  MIN(q.dfny) AS zzqfny
FROM `sgtrace_trial_platform`.dwd_yx_df_ysmx AS q
WHERE
  q.jqbz = '0'
GROUP BY
  q.hh;

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_dws_yx_kh_jf_hz.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`dws_yx_kh_jf_hz` AS
SELECT
  j.hh AS hh,
  MAX(j.jfsj) AS zjjfsj,
  ROUND(SUM(j.jfje), 2) AS ljjfje,
  COUNT(j.jfbs) AS jfcs
FROM `sgtrace_trial_platform`.dwd_yx_jf_mx AS j
GROUP BY
  j.hh;

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_dws_yx_kh_ydl_y.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`dws_yx_kh_ydl_y` AS
SELECT
  q.hh AS hh,
  q.dfny AS ny,
  ROUND(SUM(q.jsdl), 2) AS ydl,
  ROUND(SUM(q.ysje), 2) AS ysdf
FROM `sgtrace_trial_platform`.dwd_yx_df_ysmx AS q
GROUP BY
  q.hh,
  q.dfny;

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_dws_kf_gd_tj_y.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`dws_kf_gd_tj_y` AS
SELECT
  g.cldw AS cldw,
  SUBSTRING(g.slsj, 1, 7) AS tjyf,
  COUNT(g.gdbh) AS gdzs,
  SUM(CASE WHEN g.ywlx = '03' THEN 1 ELSE 0 END) AS tsgds,
  SUM(CASE WHEN g.ywlx = '01' THEN 1 ELSE 0 END) AS bxgds,
  ROUND(SUM(CASE WHEN g.ywlx = '03' THEN 1 ELSE 0 END) * 1.0 / COUNT(g.gdbh), 4) AS tsl,
  ROUND(AVG(g.hfpf), 2) AS pjmyd
FROM `sgtrace_trial_platform`.dwd_kf_gd_mx AS g
GROUP BY
  g.cldw,
  SUBSTRING(g.slsj, 1, 7);

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_dws_cj_kh_fh_r.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`dws_cj_kh_fh_r` AS
SELECT
  f.hh AS hh,
  SUBSTRING(f.sjsj, 1, 10) AS rq,
  MAX(f.yggl) AS zdfh,
  ROUND(AVG(f.yggl), 4) AS pjfh
FROM `sgtrace_trial_platform`.dwd_cj_fhqx AS f
GROUP BY
  f.hh,
  SUBSTRING(f.sjsj, 1, 10);

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_ads_yx_khda_cx.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`ads_yx_khda_cx` AS
SELECT
  k.hh AS yhbh,
  k.hm AS yhmc,
  k.ydsz AS ydsz,
  k.gddw_mc AS gddw,
  k.ydlb AS ydlb,
  k.hylb AS hylb,
  k.gddy AS dydj,
  k.htrl AS htrl,
  k.yhzt AS yhzt,
  k.lhrq AS lhrq,
  k.lxr AS lxr,
  k.lxdh AS lxdh
FROM `sgtrace_trial_platform`.dwd_yx_kh_jbxx AS k;

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_ads_yx_qfmx_cx.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`ads_yx_qfmx_cx` AS
SELECT
  q.hh AS hh,
  k.hm AS hm,
  k.gddw_mc AS gddw,
  q.dfny AS dfny,
  q.ysje AS ysdf,
  q.ssje AS ssdf,
  q.qfje AS qfje,
  q.wyj AS wyj,
  q.fxrq AS fxrq
FROM `sgtrace_trial_platform`.dwd_yx_df_ysmx AS q
JOIN `sgtrace_trial_platform`.dwd_yx_kh_jbxx AS k
  ON k.hh = q.hh
WHERE
  q.jqbz = '0';

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_ads_yx_kh360.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`ads_yx_kh360` AS
SELECT
  k.hh AS hh,
  k.hm AS hm,
  k.ydsz AS ydsz,
  k.gddw_mc AS gddw,
  k.htrl AS htrl,
  k.lxdh AS lxdh,
  COALESCE(q.qfys, 0) AS qfys,
  COALESCE(q.ljqfje, 0) AS ljqf,
  j.zjjfsj AS zjjfsj,
  j.ljjfje AS ljjf
FROM `sgtrace_trial_platform`.dwd_yx_kh_jbxx AS k
LEFT JOIN `sgtrace_trial_platform`.dws_yx_kh_qf_hz AS q
  ON q.hh = k.hh
LEFT JOIN `sgtrace_trial_platform`.dws_yx_kh_jf_hz AS j
  ON j.hh = k.hh;

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_ads_yx_ydl_fx.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`ads_yx_ydl_fx` AS
SELECT
  y.hh AS hh,
  k.hm AS hm,
  k.gddw_mc AS gddw,
  k.ydlb AS ydlb,
  y.ny AS ny,
  y.ydl AS ydl,
  y.ysdf AS ysdf
FROM `sgtrace_trial_platform`.dws_yx_kh_ydl_y AS y
JOIN `sgtrace_trial_platform`.dwd_yx_kh_jbxx AS k
  ON k.hh = y.hh;

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_ads_kf_gd_cx.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`ads_kf_gd_cx` AS
SELECT
  g.gdbh AS gdbh,
  g.slsj AS slsj,
  g.ywlx AS ywlx,
  g.hh AS hh,
  g.khmc AS khmc,
  g.lxdh AS lxdh,
  g.slnr AS slnr,
  g.cldw AS cldw,
  g.clzt AS clzt,
  g.bjsj AS bjsj,
  g.hfpf AS hfpf
FROM `sgtrace_trial_platform`.dwd_kf_gd_mx AS g;

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_ads_kf_gd_kb.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`ads_kf_gd_kb` AS
SELECT
  t.cldw AS cldw,
  t.tjyf AS tjyf,
  t.gdzs AS gdzs,
  t.tsgds AS tsgds,
  t.bxgds AS bxgds,
  t.tsl AS tsl,
  t.pjmyd AS pjmyd
FROM `sgtrace_trial_platform`.dws_kf_gd_tj_y AS t;

-- 来源 reference/poc/data/inputs/dataworks/tasks/sql_ads_cj_dkh_fh.sql；去除分区写入，保留 SELECT/JOIN/WHERE/GROUP BY。
CREATE VIEW `sgtrace_trial_platform`.`ads_cj_dkh_fh` AS
SELECT
  f.hh AS hh,
  k.hm AS hm,
  k.gddw_mc AS gddw,
  k.htrl AS htrl,
  f.rq AS rq,
  f.zdfh AS zdfh,
  f.pjfh AS pjfh,
  ROUND(f.zdfh / k.htrl, 4) AS fzl
FROM `sgtrace_trial_platform`.dws_cj_kh_fh_r AS f
JOIN `sgtrace_trial_platform`.dwd_yx_kh_jbxx AS k
  ON k.hh = f.hh;
