-- DataWorks 节点：sql_dwd_cj_fhqx（ODPS SQL）
-- 产出表：dwd_cj_fhqx
INSERT OVERWRITE TABLE dwd_cj_fhqx PARTITION (dt = '${bizdate}')
SELECT
  q.id AS cldbs,
  p.cons_no AS hh,
  p.meter_asset_no AS dnbzcbh,
  q.data_time AS sjsj,
  q.p AS yggl,
  q.q AS wggl
FROM ods_cjxt_e_mp_power_curve q JOIN ods_cjxt_e_data_mp p ON p.id = q.id;
