-- DataWorks 节点：sql_ads_yx_qfmx_cx（ODPS SQL）
-- 产出表：ads_yx_qfmx_cx
INSERT OVERWRITE TABLE ads_yx_qfmx_cx PARTITION (dt = '${bizdate}')
SELECT
  q.hh AS hh,
  k.hm AS hm,
  k.gddw_mc AS gddw,
  q.dfny AS dfny,
  q.ysje AS ysdf,
  q.ssje AS ssdf,
  q.qfje AS qfje,
  q.wyj AS wyj,
  q.fxrq AS fxrq
FROM dwd_yx_df_ysmx q JOIN dwd_yx_kh_jbxx k ON k.hh = q.hh
WHERE q.jqbz = '0';
