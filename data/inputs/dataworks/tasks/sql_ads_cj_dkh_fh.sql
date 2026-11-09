-- DataWorks 节点：sql_ads_cj_dkh_fh（ODPS SQL）
-- 产出表：ads_cj_dkh_fh
INSERT OVERWRITE TABLE ads_cj_dkh_fh PARTITION (dt = '${bizdate}')
SELECT
  f.hh AS hh,
  k.hm AS hm,
  k.gddw_mc AS gddw,
  k.htrl AS htrl,
  f.rq AS rq,
  f.zdfh AS zdfh,
  f.pjfh AS pjfh,
  ROUND(f.zdfh / k.htrl, 4) AS fzl
FROM dws_cj_kh_fh_r f JOIN dwd_yx_kh_jbxx k ON k.hh = f.hh;
