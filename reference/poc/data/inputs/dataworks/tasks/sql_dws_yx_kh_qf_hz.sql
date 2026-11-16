-- DataWorks 节点：sql_dws_yx_kh_qf_hz（ODPS SQL）
-- 产出表：dws_yx_kh_qf_hz
INSERT OVERWRITE TABLE dws_yx_kh_qf_hz PARTITION (dt = '${bizdate}')
SELECT
  q.hh AS hh,
  COUNT(q.dfny) AS qfys,
  ROUND(SUM(q.qfje), 2) AS ljqfje,
  ROUND(SUM(q.wyj), 2) AS ljwyj,
  MIN(q.dfny) AS zzqfny
FROM dwd_yx_df_ysmx q
WHERE q.jqbz = '0'
GROUP BY q.hh;
