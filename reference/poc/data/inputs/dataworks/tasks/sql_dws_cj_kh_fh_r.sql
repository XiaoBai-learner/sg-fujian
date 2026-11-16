-- DataWorks 节点：sql_dws_cj_kh_fh_r（ODPS SQL）
-- 产出表：dws_cj_kh_fh_r
INSERT OVERWRITE TABLE dws_cj_kh_fh_r PARTITION (dt = '${bizdate}')
SELECT
  f.hh AS hh,
  SUBSTR(f.sjsj, 1, 10) AS rq,
  MAX(f.yggl) AS zdfh,
  ROUND(AVG(f.yggl), 4) AS pjfh
FROM dwd_cj_fhqx f
GROUP BY f.hh, SUBSTR(f.sjsj, 1, 10);
