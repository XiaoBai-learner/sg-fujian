-- DataWorks 节点：sql_ads_yx_kh360（ODPS SQL）
-- 产出表：ads_yx_kh360
INSERT OVERWRITE TABLE ads_yx_kh360 PARTITION (dt = '${bizdate}')
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
FROM dwd_yx_kh_jbxx k LEFT JOIN dws_yx_kh_qf_hz q ON q.hh = k.hh LEFT JOIN dws_yx_kh_jf_hz j ON j.hh = k.hh;
