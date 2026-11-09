-- DataWorks 节点：sql_ads_yx_ydl_fx（ODPS SQL）
-- 产出表：ads_yx_ydl_fx
INSERT OVERWRITE TABLE ads_yx_ydl_fx PARTITION (dt = '${bizdate}')
SELECT
  y.hh AS hh,
  k.hm AS hm,
  k.gddw_mc AS gddw,
  k.ydlb AS ydlb,
  y.ny AS ny,
  y.ydl AS ydl,
  y.ysdf AS ysdf
FROM dws_yx_kh_ydl_y y JOIN dwd_yx_kh_jbxx k ON k.hh = y.hh;
