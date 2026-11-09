-- DataWorks 节点：sql_dwd_yx_jf_mx（ODPS SQL）
-- 产出表：dwd_yx_jf_mx
INSERT OVERWRITE TABLE dwd_yx_jf_mx PARTITION (dt = '${bizdate}')
SELECT
  p.charge_id AS jfbs,
  p.cons_no AS hh,
  p.rcvbl_id AS ysbs,
  p.charge_date AS jfsj,
  p.rcv_amt AS jfje,
  p.pay_mode AS jffs,
  o.org_name AS sfdw
FROM ods_yx186_a_pay_flow p LEFT JOIN ods_yx186_o_org o ON o.org_no = p.acct_org_no;
