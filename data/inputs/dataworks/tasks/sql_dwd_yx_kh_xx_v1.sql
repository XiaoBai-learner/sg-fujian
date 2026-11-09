-- DataWorks 节点：sql_dwd_yx_kh_xx_v1（ODPS SQL）
-- 产出表：dwd_yx_kh_xx_v1
INSERT OVERWRITE TABLE dwd_yx_kh_xx_v1 PARTITION (dt = '${bizdate}')
SELECT
  c.cons_no AS cons_no,
  c.cons_name AS cons_name,
  c.elec_addr AS elec_addr,
  c.org_no AS org_no
FROM ods_yx186_c_cons c;
