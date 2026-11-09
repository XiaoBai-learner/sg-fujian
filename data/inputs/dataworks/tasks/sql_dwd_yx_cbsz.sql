-- DataWorks 节点：sql_dwd_yx_cbsz（ODPS SQL）
-- 产出表：dwd_yx_cbsz
INSERT OVERWRITE TABLE dwd_yx_cbsz PARTITION (dt = '${bizdate}')
SELECT
  r.read_id AS cbbs,
  m.mp_no AS jldbh,
  c.cons_no AS hh,
  r.ym AS cbny,
  r.last_read AS sccbsz,
  r.this_read AS bccbsz,
  ROUND((r.this_read - r.last_read) * d.t_factor, 2) AS cjdl,
  r.read_date AS cbrq
FROM ods_yx186_r_read r JOIN ods_yx186_c_mp m ON m.mp_id = r.mp_id JOIN ods_yx186_c_cons c ON c.cons_id = m.cons_id LEFT JOIN ods_yx186_c_meter_mp_rela rl ON rl.mp_id = r.mp_id LEFT JOIN ods_yx186_d_meter d ON d.meter_id = rl.meter_id;
