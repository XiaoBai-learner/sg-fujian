-- 取自既有合成热点日志 Q001–Q022，SQL 仅补全隔离测试库名。

-- Q001；模拟90天执行 18420 次；原始账号 rpt_service
SELECT
  yhbh,
  yhmc,
  ydsz,
  gddw,
  ydlb,
  hylb,
  dydj,
  htrl,
  yhzt,
  lhrq,
  lxr,
  lxdh
FROM `sgtrace_trial_platform`.ads_yx_khda_cx
WHERE
  yhbh = '3523000123456';

-- Q002；模拟90天执行 15233 次；原始账号 rpt_service
SELECT
  *
FROM `sgtrace_trial_platform`.ads_yx_khda_cx
WHERE
  gddw LIKE '%鼓楼%' AND yhzt = '1'
ORDER BY
  lhrq DESC
LIMIT 50;

-- Q003；模拟90天执行 12871 次；原始账号 rpt_service
SELECT
  hh,
  hm,
  gddw,
  dfny,
  ysdf,
  ssdf,
  qfje,
  wyj,
  fxrq
FROM `sgtrace_trial_platform`.ads_yx_qfmx_cx
WHERE
  gddw = '台江城区供电所'
ORDER BY
  qfje DESC;

-- Q004；模拟90天执行 9655 次；原始账号 rpt_service
SELECT
  *
FROM `sgtrace_trial_platform`.ads_yx_kh360
WHERE
  hh = '3561000088123';

-- Q005；模拟90天执行 8410 次；原始账号 rpt_service
SELECT
  hh,
  hm,
  gddw,
  ydlb,
  ny,
  ydl,
  ysdf
FROM `sgtrace_trial_platform`.ads_yx_ydl_fx
WHERE
  ny = '202508'
ORDER BY
  ydl DESC
LIMIT 100;

-- Q006；模拟90天执行 7302 次；原始账号 rpt_service
SELECT
  *
FROM `sgtrace_trial_platform`.ads_kf_gd_cx
WHERE
  ywlx = '03' AND slsj >= '2025-08-01'
ORDER BY
  slsj DESC;

-- Q007；模拟90天执行 6120 次；原始账号 rpt_service
SELECT
  cldw,
  tjyf,
  gdzs,
  tsgds,
  bxgds,
  tsl,
  pjmyd
FROM `sgtrace_trial_platform`.ads_kf_gd_kb
WHERE
  tjyf = '2025-08';

-- Q008；模拟90天执行 4980 次；原始账号 rpt_service
SELECT
  hh,
  hm,
  gddw,
  htrl,
  rq,
  zdfh,
  pjfh,
  fzl
FROM `sgtrace_trial_platform`.ads_cj_dkh_fh
WHERE
  rq = '2025-12-29' AND fzl > 0.8;

-- Q009；模拟90天执行 3204 次；原始账号 analyst_lin
SELECT
  k.gddw_mc,
  COUNT(DISTINCT q.hh) AS qf_hs,
  ROUND(SUM(q.qfje), 2) AS qf_je
FROM `sgtrace_trial_platform`.dwd_yx_df_ysmx AS q
JOIN `sgtrace_trial_platform`.dwd_yx_kh_jbxx AS k
  ON k.hh = q.hh
WHERE
  q.jqbz = '0'
GROUP BY
  k.gddw_mc
ORDER BY
  qf_je DESC;

-- Q010；模拟90天执行 2877 次；原始账号 analyst_lin
SELECT
  k.ydlb,
  q.dfny,
  ROUND(SUM(q.jsdl), 2) AS dl,
  ROUND(SUM(q.ysje), 2) AS je
FROM `sgtrace_trial_platform`.dwd_yx_df_ysmx AS q
JOIN `sgtrace_trial_platform`.dwd_yx_kh_jbxx AS k
  ON k.hh = q.hh
GROUP BY
  k.ydlb,
  q.dfny
ORDER BY
  q.dfny;

-- Q011；模拟90天执行 2150 次；原始账号 analyst_chen
SELECT
  j.jffs,
  COUNT(*) AS bs,
  ROUND(SUM(j.jfje), 2) AS je
FROM `sgtrace_trial_platform`.dwd_yx_jf_mx AS j
WHERE
  j.jfsj >= '2025-07-01'
GROUP BY
  j.jffs;

-- Q012；模拟90天执行 1990 次；原始账号 analyst_chen
SELECT
  c.hh,
  c.cbny,
  c.cjdl,
  y.jsdl,
  ROUND(c.cjdl - y.jsdl, 2) AS diff
FROM `sgtrace_trial_platform`.dwd_yx_cbsz AS c
JOIN `sgtrace_trial_platform`.dwd_yx_df_ysmx AS y
  ON y.hh = c.hh AND y.dfny = c.cbny
WHERE
  ABS(c.cjdl - y.jsdl) > 0.01;

-- Q013；模拟90天执行 1764 次；原始账号 analyst_wu
SELECT
  r.hh,
  ROUND(SUM(r.zxygdl), 2) AS cj_dl,
  y.jsdl AS yx_dl
FROM `sgtrace_trial_platform`.dwd_cj_rdl AS r
JOIN `sgtrace_trial_platform`.dwd_yx_df_ysmx AS y
  ON y.hh = r.hh AND y.dfny = '202512'
WHERE
  r.sjrq BETWEEN '2025-12-01' AND '2025-12-31'
GROUP BY
  r.hh,
  y.jsdl;

-- Q014；模拟90天执行 1530 次；原始账号 analyst_wu
SELECT
  j.jldbh,
  j.dnbzcbh,
  j.zhbl,
  r.sjrq,
  r.zxygsz,
  r.zxygdl
FROM `sgtrace_trial_platform`.dwd_yx_jld_xx AS j
JOIN `sgtrace_trial_platform`.dwd_cj_rdl AS r
  ON r.dnbzcbh = j.dnbzcbh
WHERE
  r.sjrq = '2025-12-15';

-- Q015；模拟90天执行 1288 次；原始账号 analyst_zheng
SELECT
  g.cldw,
  g.ywlx,
  COUNT(*) AS n,
  ROUND(AVG(g.hfpf), 2) AS score
FROM `sgtrace_trial_platform`.dwd_kf_gd_mx AS g
WHERE
  g.slsj LIKE '2025-0%'
GROUP BY
  g.cldw,
  g.ywlx;

-- Q016；模拟90天执行 1102 次；原始账号 analyst_zheng
SELECT
  g.hh,
  k.hm,
  k.ydsz,
  COUNT(*) AS bx_cs
FROM `sgtrace_trial_platform`.dwd_kf_gd_mx AS g
JOIN `sgtrace_trial_platform`.dwd_yx_kh_jbxx AS k
  ON k.hh = g.hh
WHERE
  g.ywlx = '01'
GROUP BY
  g.hh,
  k.hm,
  k.ydsz
HAVING
  COUNT(*) >= 3;

-- Q017；模拟90天执行 980 次；原始账号 analyst_lin
SELECT
  z.gddw_mc,
  z.zdlx,
  COUNT(*) AS n
FROM `sgtrace_trial_platform`.dwd_cj_zd_xx AS z
WHERE
  z.yxzt = '1'
GROUP BY
  z.gddw_mc,
  z.zdlx;

-- Q018；模拟90天执行 856 次；原始账号 analyst_chen
SELECT
  k.hh,
  k.hm,
  k.htrl,
  MAX(f.yggl) AS max_p
FROM `sgtrace_trial_platform`.dwd_cj_fhqx AS f
JOIN `sgtrace_trial_platform`.dwd_yx_kh_jbxx AS k
  ON k.hh = f.hh
GROUP BY
  k.hh,
  k.hm,
  k.htrl
HAVING
  MAX(f.yggl) > k.htrl * 0.9;

-- Q019；模拟90天执行 640 次；原始账号 analyst_wu
SELECT
  c.cons_no,
  c.cons_name,
  c.elec_addr,
  o.org_name
FROM `sgtrace_trial_platform`.ods_yx186_c_cons AS c
JOIN `sgtrace_trial_platform`.ods_yx186_o_org AS o
  ON o.org_no = c.org_no
WHERE
  c.status_code = '9';

-- Q020；模拟90天执行 512 次；原始账号 analyst_zheng
SELECT
  w.app_no,
  w.cust_no,
  c.cons_no,
  w.cust_name,
  c.cons_name
FROM `sgtrace_trial_platform`.ods_kf95598_t_kf_workorder AS w
LEFT JOIN `sgtrace_trial_platform`.ods_yx186_c_cons AS c
  ON c.cons_no = w.cust_no
WHERE
  c.cons_name IS NULL OR TRIM(w.cust_name) <> c.cons_name;

-- Q021；模拟90天执行 433 次；原始账号 analyst_lin
SELECT
  m.mp_no,
  d.asset_no,
  p.meter_asset_no,
  d.t_factor,
  p.t_factor
FROM `sgtrace_trial_platform`.ods_yx186_c_mp AS m
JOIN `sgtrace_trial_platform`.ods_yx186_c_meter_mp_rela AS r
  ON r.mp_id = m.mp_id
JOIN `sgtrace_trial_platform`.ods_yx186_d_meter AS d
  ON d.meter_id = r.meter_id
JOIN `sgtrace_trial_platform`.ods_cjxt_e_data_mp AS p
  ON p.mp_id = m.mp_id
WHERE
  d.t_factor <> p.t_factor OR d.asset_no <> p.meter_asset_no;

-- Q022；模拟90天执行 310 次；原始账号 analyst_chen
SELECT
  q.hh,
  q.qfys,
  q.ljqfje,
  j.zjjfsj
FROM `sgtrace_trial_platform`.dws_yx_kh_qf_hz AS q
LEFT JOIN `sgtrace_trial_platform`.dws_yx_kh_jf_hz AS j
  ON j.hh = q.hh
WHERE
  q.qfys >= 2;
