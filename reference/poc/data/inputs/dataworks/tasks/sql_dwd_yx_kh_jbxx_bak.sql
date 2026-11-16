-- DataWorks 节点：sql_dwd_yx_kh_jbxx_bak（ODPS SQL）
-- 产出表：dwd_yx_kh_jbxx_bak
INSERT OVERWRITE TABLE dwd_yx_kh_jbxx_bak PARTITION (dt = '${bizdate}')
SELECT
  k.hh AS hh,
  k.hm AS hm,
  k.ydsz AS ydsz,
  k.htrl AS htrl
FROM dwd_yx_kh_jbxx k;
