-- DataWorks 节点：sql_dwd_kf_gd_mx（ODPS SQL）
-- 产出表：dwd_kf_gd_mx
INSERT OVERWRITE TABLE dwd_kf_gd_mx PARTITION (dt = '${bizdate}')
SELECT
  w.app_no AS gdbh,
  w.accept_time AS slsj,
  w.busi_type AS ywlx,
  w.cust_no AS hh,
  w.cust_name AS khmc,
  w.contact_tel AS lxdh,
  w.accept_content AS slnr,
  o.org_name AS cldw,
  w.handle_status AS clzt,
  w.finish_time AS bjsj,
  v.satisfy_score AS hfpf,
  v.visit_result AS hfjg
FROM ods_kf95598_t_kf_workorder w LEFT JOIN ods_yx186_o_org o ON o.org_no = w.handle_org LEFT JOIN ods_kf95598_t_kf_visit v ON v.app_no = w.app_no;
