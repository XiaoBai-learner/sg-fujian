-- DataWorks 节点：sql_dwd_yx_jld_xx（ODPS SQL）
-- 产出表：dwd_yx_jld_xx
INSERT OVERWRITE TABLE dwd_yx_jld_xx PARTITION (dt = '${bizdate}')
SELECT
  m.mp_id AS jldbs,
  m.mp_no AS jldbh,
  m.mp_name AS jldmc,
  c.cons_no AS hh,
  d.asset_no AS dnbzcbh,
  d.made_no AS ccbh,
  d.manufacturer AS sccj,
  d.t_factor AS zhbl,
  d.inst_date AS zbrq,
  m.status_code AS jldzt
FROM ods_yx186_c_mp m JOIN ods_yx186_c_cons c ON c.cons_id = m.cons_id LEFT JOIN ods_yx186_c_meter_mp_rela r ON r.mp_id = m.mp_id LEFT JOIN ods_yx186_d_meter d ON d.meter_id = r.meter_id;
