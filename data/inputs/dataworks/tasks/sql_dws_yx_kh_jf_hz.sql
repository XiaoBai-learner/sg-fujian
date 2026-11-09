-- DataWorks 节点：sql_dws_yx_kh_jf_hz（ODPS SQL）
-- 产出表：dws_yx_kh_jf_hz
INSERT OVERWRITE TABLE dws_yx_kh_jf_hz PARTITION (dt = '${bizdate}')
SELECT
  j.hh AS hh,
  MAX(j.jfsj) AS zjjfsj,
  ROUND(SUM(j.jfje), 2) AS ljjfje,
  COUNT(j.jfbs) AS jfcs
FROM dwd_yx_jf_mx j
GROUP BY j.hh;
