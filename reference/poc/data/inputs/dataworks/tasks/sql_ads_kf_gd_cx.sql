-- DataWorks 节点：sql_ads_kf_gd_cx（ODPS SQL）
-- 产出表：ads_kf_gd_cx
INSERT OVERWRITE TABLE ads_kf_gd_cx PARTITION (dt = '${bizdate}')
SELECT
  g.gdbh AS gdbh,
  g.slsj AS slsj,
  g.ywlx AS ywlx,
  g.hh AS hh,
  g.khmc AS khmc,
  g.lxdh AS lxdh,
  g.slnr AS slnr,
  g.cldw AS cldw,
  g.clzt AS clzt,
  g.bjsj AS bjsj,
  g.hfpf AS hfpf
FROM dwd_kf_gd_mx g;
