-- DataWorks 节点：sql_ads_yx_khda_cx（ODPS SQL）
-- 产出表：ads_yx_khda_cx
INSERT OVERWRITE TABLE ads_yx_khda_cx PARTITION (dt = '${bizdate}')
SELECT
  k.hh AS yhbh,
  k.hm AS yhmc,
  k.ydsz AS ydsz,
  k.gddw_mc AS gddw,
  k.ydlb AS ydlb,
  k.hylb AS hylb,
  k.gddy AS dydj,
  k.htrl AS htrl,
  k.yhzt AS yhzt,
  k.lhrq AS lhrq,
  k.lxr AS lxr,
  k.lxdh AS lxdh
FROM dwd_yx_kh_jbxx k;
