-- DataWorks 节点：sql_dwd_yx_df_ysmx（ODPS SQL）
-- 产出表：dwd_yx_df_ysmx
INSERT OVERWRITE TABLE dwd_yx_df_ysmx PARTITION (dt = '${bizdate}')
SELECT
  a.rcvbl_id AS ysbs,
  a.cons_no AS hh,
  a.rcvbl_ym AS dfny,
  a.t_settle_pq AS jsdl,
  a.rcvbl_amt AS ysje,
  a.rcved_amt AS ssje,
  ROUND(a.rcvbl_amt - a.rcved_amt, 2) AS qfje,
  a.penalty AS wyj,
  a.settle_flag AS jqbz,
  a.rel_date AS fxrq
FROM ods_yx186_a_rcvbl_flow a;
