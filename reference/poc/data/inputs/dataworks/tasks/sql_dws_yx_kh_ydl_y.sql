-- DataWorks 节点：sql_dws_yx_kh_ydl_y（ODPS SQL）
-- 产出表：dws_yx_kh_ydl_y
INSERT OVERWRITE TABLE dws_yx_kh_ydl_y PARTITION (dt = '${bizdate}')
SELECT
  q.hh AS hh,
  q.dfny AS ny,
  ROUND(SUM(q.jsdl), 2) AS ydl,
  ROUND(SUM(q.ysje), 2) AS ysdf
FROM dwd_yx_df_ysmx q
GROUP BY q.hh, q.dfny;
