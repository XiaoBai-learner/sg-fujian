-- DataWorks 节点：sql_dwd_yx_kh_jbxx（ODPS SQL）
-- 产出表：dwd_yx_kh_jbxx
INSERT OVERWRITE TABLE dwd_yx_kh_jbxx PARTITION (dt = '${bizdate}')
SELECT
  c.cons_id AS khbs,
  c.cons_no AS hh,
  c.cons_name AS hm,
  c.elec_addr AS ydsz,
  c.org_no AS gddw_bm,
  o.org_name AS gddw_mc,
  c.trade_code AS hylb,
  c.elec_type_code AS ydlb,
  c.volt_code AS gddy,
  c.contract_cap AS htrl,
  c.status_code AS yhzt,
  c.build_date AS lhrq,
  c.cancel_date AS xhrq,
  ct.contact_name AS lxr,
  ct.mobile AS lxdh
FROM ods_yx186_c_cons c LEFT JOIN ods_yx186_o_org o ON o.org_no = c.org_no LEFT JOIN ods_yx186_c_contact ct ON ct.cons_id = c.cons_id AND ct.contact_mode = '01';
