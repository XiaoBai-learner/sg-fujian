-- DataWorks 节点：sql_dwd_cj_rdl（ODPS SQL）
-- 产出表：dwd_cj_rdl
INSERT OVERWRITE TABLE dwd_cj_rdl PARTITION (dt = '${bizdate}')
SELECT
  e.id AS cldbs,
  p.cons_no AS hh,
  p.meter_asset_no AS dnbzcbh,
  e.data_date AS sjrq,
  e.pap_e AS zxygdl,
  e.prp_e AS zxwgdl,
  dr.pap_r AS zxygsz
FROM ods_cjxt_e_mp_day_energy e JOIN ods_cjxt_e_data_mp p ON p.id = e.id LEFT JOIN ods_cjxt_e_mp_day_read dr ON dr.id = e.id AND dr.data_date = e.data_date;
