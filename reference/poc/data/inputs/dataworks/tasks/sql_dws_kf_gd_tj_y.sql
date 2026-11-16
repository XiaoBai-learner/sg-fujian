-- DataWorks 节点：sql_dws_kf_gd_tj_y（ODPS SQL）
-- 产出表：dws_kf_gd_tj_y
INSERT OVERWRITE TABLE dws_kf_gd_tj_y PARTITION (dt = '${bizdate}')
SELECT
  g.cldw AS cldw,
  SUBSTR(g.slsj, 1, 7) AS tjyf,
  COUNT(g.gdbh) AS gdzs,
  SUM(CASE WHEN g.ywlx = '03' THEN 1 ELSE 0 END) AS tsgds,
  SUM(CASE WHEN g.ywlx = '01' THEN 1 ELSE 0 END) AS bxgds,
  ROUND(SUM(CASE WHEN g.ywlx = '03' THEN 1 ELSE 0 END) * 1.0 / COUNT(g.gdbh), 4) AS tsl,
  ROUND(AVG(g.hfpf), 2) AS pjmyd
FROM dwd_kf_gd_mx g
GROUP BY g.cldw, SUBSTR(g.slsj, 1, 7);
