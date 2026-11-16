-- DataWorks 节点：sql_dwd_cj_zd_xx（ODPS SQL）
-- 产出表：dwd_cj_zd_xx
INSERT OVERWRITE TABLE dwd_cj_zd_xx PARTITION (dt = '${bizdate}')
SELECT
  t.terminal_id AS zdbs,
  t.tmnl_asset_no AS zdzcbh,
  t.tmnl_type_code AS zdlx,
  t.terminal_addr AS zddz,
  o.org_name AS gddw_mc,
  t.run_status AS yxzt,
  t.inst_date AS tyrq
FROM ods_cjxt_r_tmnl_run t LEFT JOIN ods_yx186_o_org o ON o.org_no = t.org_no;
