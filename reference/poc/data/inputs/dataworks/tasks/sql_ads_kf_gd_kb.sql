-- DataWorks 节点：sql_ads_kf_gd_kb（ODPS SQL）
-- 产出表：ads_kf_gd_kb
INSERT OVERWRITE TABLE ads_kf_gd_kb PARTITION (dt = '${bizdate}')
SELECT
  t.cldw AS cldw,
  t.tjyf AS tjyf,
  t.gdzs AS gdzs,
  t.tsgds AS tsgds,
  t.bxgds AS bxgds,
  t.tsl AS tsl,
  t.pjmyd AS pjmyd
FROM dws_kf_gd_tj_y t;
