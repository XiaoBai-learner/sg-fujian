-- DataWorks 节点：sql_tmp_qf_hh_20251201（ODPS SQL）
-- 产出表：tmp_qf_hh_20251201
INSERT OVERWRITE TABLE tmp_qf_hh_20251201 PARTITION (dt = '${bizdate}')
SELECT
  q.hh AS hh,
  ROUND(SUM(q.qfje), 2) AS qfje
FROM dwd_yx_df_ysmx q
WHERE q.jqbz = '0'
GROUP BY q.hh;
