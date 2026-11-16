-- 数据中台（MaxCompute 项目 sgfj_dataplatform）DDL 导出
-- 表数量：41

CREATE TABLE IF NOT EXISTS ods_yx186_o_org (
  org_no STRING COMMENT '单位编号',
  org_name STRING COMMENT '单位名称',
  p_org_no STRING COMMENT '上级单位',
  org_type STRING COMMENT '单位类型 02市 03县 04供电所',
  sort_no BIGINT
)
COMMENT '供电单位（yx186同步）'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ods_yx186_c_cons (
  cons_id BIGINT COMMENT '客户ID',
  cons_no STRING COMMENT '用户编号',
  cons_name STRING COMMENT '用户名称',
  elec_addr STRING COMMENT '用电地址',
  org_no STRING COMMENT '供电单位',
  trade_code STRING COMMENT '行业分类代码',
  elec_type_code STRING COMMENT '用电类别',
  volt_code STRING COMMENT '电压',
  contract_cap DECIMAL(12,2) COMMENT '合同容量（kVA）',
  run_cap DECIMAL(12,2) COMMENT '运行容量（kVA）',
  status_code STRING COMMENT '用户状态',
  build_date STRING COMMENT '建档日期',
  cancel_date STRING COMMENT '销户日期',
  lode_attr_code STRING COMMENT '负荷性质'
)
COMMENT '用电客户（yx186同步）'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ods_yx186_c_contact (
  contact_id BIGINT COMMENT '联系人标识',
  cons_id BIGINT COMMENT '客户ID',
  contact_name STRING COMMENT '联系人',
  mobile STRING COMMENT '手机',
  office_tel STRING,
  contact_mode STRING COMMENT '类型 01主要 02备用'
)
COMMENT '客户联系人（yx186同步）'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ods_yx186_c_mp (
  mp_id BIGINT COMMENT '计量点ID',
  mp_no STRING COMMENT '计量点编号',
  mp_name STRING COMMENT '计量点名称',
  cons_id BIGINT,
  mp_addr STRING COMMENT '计量点地址',
  volt_code STRING COMMENT '计量点电压等级',
  mp_attr_code STRING COMMENT '性质 01结算 02考核',
  status_code STRING
)
COMMENT '计量点（yx186同步）'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ods_yx186_d_meter (
  meter_id BIGINT,
  asset_no STRING COMMENT '资产编号',
  made_no STRING COMMENT '出厂编号',
  manufacturer STRING COMMENT '厂家',
  type_code STRING,
  wiring_mode STRING COMMENT '接线方式',
  t_factor DECIMAL(10,2) COMMENT '倍率',
  inst_date STRING COMMENT '装表日期'
)
COMMENT '电能表资产（yx186同步）'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ods_yx186_c_meter_mp_rela (
  rela_id BIGINT COMMENT '关系标识',
  mp_id BIGINT COMMENT '计量点标识',
  meter_id BIGINT,
  rela_date STRING COMMENT '建立关系日期'
)
COMMENT '计量点电能表关系（yx186同步）'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ods_yx186_r_read (
  read_id BIGINT,
  mp_id BIGINT COMMENT '计量点标识',
  ym STRING COMMENT '年月',
  last_read DECIMAL(14,2) COMMENT '上次示数',
  this_read DECIMAL(14,2) COMMENT '本次示数',
  read_date STRING COMMENT '抄表日期',
  read_type_code STRING COMMENT '抄表方式 01远抄 02手工'
)
COMMENT '抄表示数（yx186同步）'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ods_yx186_a_rcvbl_flow (
  rcvbl_id BIGINT,
  cons_no STRING COMMENT '户号',
  rcvbl_ym STRING COMMENT '应收年月',
  t_settle_pq DECIMAL(14,2) COMMENT '结算电量',
  rcvbl_amt DECIMAL(14,2) COMMENT '应收金额',
  rcved_amt DECIMAL(14,2) COMMENT '实收金额',
  penalty DECIMAL(12,2) COMMENT '电费违约金（元）',
  settle_flag STRING COMMENT '结清标志 0未结清 1已结清',
  rel_date STRING COMMENT '电费发行日期'
)
COMMENT '应收电费流水（yx186同步）'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ods_yx186_a_pay_flow (
  charge_id BIGINT COMMENT '缴费记录标识',
  cons_no STRING COMMENT '户号',
  rcvbl_id BIGINT COMMENT '对应应收标识',
  charge_date DATETIME COMMENT '收费日期',
  rcv_amt DECIMAL(14,2) COMMENT '金额',
  pay_mode STRING COMMENT '缴费方式 01柜台 02支付宝 03微信 04银行代扣',
  acct_org_no STRING COMMENT '收费单位'
)
COMMENT '实收电费流水（yx186同步）'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ods_yx186_a_rcvbl_flow_his (
  rcvbl_id BIGINT COMMENT '应收电费标识',
  cons_no STRING COMMENT '户号',
  rcvbl_ym STRING COMMENT '应收年月',
  t_settle_pq DECIMAL(14,2) COMMENT '结算电量',
  rcvbl_amt DECIMAL(14,2) COMMENT '应收金额',
  rcved_amt DECIMAL(14,2) COMMENT '实收金额',
  penalty DECIMAL(12,2),
  settle_flag STRING COMMENT '结清标志',
  rel_date STRING COMMENT '电费发行日期'
)
COMMENT '应收电费历史流水（2024）（yx186同步）'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ods_cjxt_r_tmnl_run (
  terminal_id BIGINT COMMENT '终端标识',
  tmnl_asset_no STRING,
  tmnl_type_code STRING COMMENT '终端类型 01集中器 02专变终端',
  terminal_addr STRING COMMENT '终端逻辑地址',
  org_no STRING,
  run_status STRING COMMENT '终端运行状态',
  inst_date STRING COMMENT '终端投运日期'
)
COMMENT '终端运行档案（cjxt同步）'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ods_cjxt_e_data_mp (
  id BIGINT,
  terminal_id BIGINT COMMENT '所属终端标识',
  mp_sn BIGINT COMMENT '测量点序号',
  mp_id BIGINT,
  cons_no STRING,
  meter_asset_no STRING COMMENT '电能表资产编号',
  t_factor DECIMAL(10,2)
)
COMMENT '采集测量点（cjxt同步）'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ods_cjxt_e_mp_day_read (
  id BIGINT COMMENT '测量点标识',
  data_date STRING COMMENT '日冻结日期',
  pap_r DECIMAL(14,2) COMMENT '正向有功总示数',
  prp_r DECIMAL(14,2),
  rap_r DECIMAL(14,2) COMMENT '反向有功总示数',
  col_time DATETIME COMMENT '采集时间'
)
COMMENT 'E_MP_DAY_READ（cjxt同步）'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ods_cjxt_e_mp_day_energy (
  id BIGINT COMMENT '测量点标识',
  data_date STRING COMMENT '数据日期',
  pap_e DECIMAL(14,2) COMMENT '日正向有功电量（kWh）',
  prp_e DECIMAL(14,2),
  rap_e DECIMAL(14,2)
)
COMMENT 'E_MP_DAY_ENERGY（cjxt同步）'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ods_cjxt_e_mp_power_curve (
  id BIGINT COMMENT '测量点标识',
  data_time DATETIME COMMENT '曲线数据时间',
  p DECIMAL(12,4),
  q DECIMAL(12,4) COMMENT '无功功率（kvar）'
)
COMMENT 'E_MP_POWER_CURVE（cjxt同步）'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ods_kf95598_t_kf_workorder (
  app_no STRING COMMENT '工单号',
  accept_time DATETIME COMMENT '受理时间',
  busi_type STRING COMMENT '业务类型 01故障报修 02咨询 03投诉 04意见建议',
  cust_no STRING COMMENT '客户编号',
  cust_name STRING COMMENT '客户名称',
  contact_tel STRING COMMENT '联系电话',
  accept_content STRING COMMENT '受理内容',
  handle_org STRING COMMENT '处理单位',
  handle_status STRING COMMENT '状态',
  finish_time DATETIME COMMENT '办结时间',
  satisfy_code STRING COMMENT '满意度'
)
COMMENT '95598工单（kf95598同步）'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ods_kf95598_t_kf_visit (
  visit_id BIGINT COMMENT '回访记录标识',
  app_no STRING COMMENT '工单号',
  visit_time DATETIME COMMENT '回访时间',
  visit_result STRING COMMENT '回访结果',
  satisfy_score DECIMAL(4,1) COMMENT '评分'
)
COMMENT '工单回访（kf95598同步）'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS dwd_yx_kh_jbxx (
  khbs BIGINT COMMENT '客户标识',
  hh STRING COMMENT '户号',
  hm STRING COMMENT '户名',
  ydsz STRING COMMENT '用电地址',
  gddw_bm STRING COMMENT '供电单位编码',
  gddw_mc STRING COMMENT '供电单位名称',
  hylb STRING COMMENT '行业类别',
  ydlb STRING COMMENT '用电类别',
  gddy STRING COMMENT '供电电压',
  htrl DECIMAL(12,2) COMMENT '合同容量',
  yhzt STRING COMMENT '用户状态',
  lhrq STRING COMMENT '立户日期',
  xhrq STRING COMMENT '销户日期',
  lxr STRING COMMENT '主联系人',
  lxdh STRING COMMENT '联系电话'
)
COMMENT '客户基本信息'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS dwd_yx_jld_xx (
  jldbs BIGINT COMMENT '计量点标识',
  jldbh STRING COMMENT '计量点编号',
  jldmc STRING COMMENT '计量点名称',
  hh STRING COMMENT '户号',
  dnbzcbh STRING COMMENT '电能表资产编号',
  ccbh STRING COMMENT '出厂编号',
  sccj STRING COMMENT '生产厂家',
  zhbl DECIMAL(10,2) COMMENT '综合倍率',
  zbrq STRING COMMENT '装表日期',
  jldzt STRING COMMENT '计量点状态'
)
COMMENT '计量点信息'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS dwd_yx_df_ysmx (
  ysbs BIGINT COMMENT '应收标识',
  hh STRING COMMENT '户号',
  dfny STRING COMMENT '电费年月',
  jsdl DECIMAL(14,2) COMMENT '结算电量',
  ysje DECIMAL(14,2) COMMENT '应收金额',
  ssje DECIMAL(14,2) COMMENT '实收金额',
  qfje DECIMAL(14,2) COMMENT '欠费金额',
  wyj DECIMAL(14,2) COMMENT '违约金',
  jqbz STRING COMMENT '结清标志',
  fxrq STRING COMMENT '发行日期'
)
COMMENT '应收电费明细'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS dwd_yx_jf_mx (
  jfbs BIGINT COMMENT '缴费标识',
  hh STRING COMMENT '户号',
  ysbs BIGINT COMMENT '应收标识',
  jfsj DATETIME COMMENT '缴费时间',
  jfje DECIMAL(14,2) COMMENT '缴费金额',
  jffs STRING COMMENT '缴费方式',
  sfdw STRING COMMENT '收费单位'
)
COMMENT '缴费明细'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS dwd_yx_cbsz (
  cbbs BIGINT COMMENT '抄表标识',
  jldbh STRING COMMENT '计量点编号',
  hh STRING COMMENT '户号',
  cbny STRING COMMENT '抄表年月',
  sccbsz DECIMAL(14,2) COMMENT '上次示数',
  bccbsz DECIMAL(14,2) COMMENT '本次示数',
  cjdl DECIMAL(14,2) COMMENT '抄见电量',
  cbrq STRING COMMENT '抄表日期'
)
COMMENT '抄表示数明细'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS dwd_cj_rdl (
  cldbs BIGINT COMMENT '测量点标识',
  hh STRING COMMENT '户号',
  dnbzcbh STRING COMMENT '电能表资产编号',
  sjrq STRING COMMENT '数据日期',
  zxygdl DECIMAL(14,2) COMMENT '正向有功电量',
  zxwgdl DECIMAL(14,2) COMMENT '正向无功电量',
  zxygsz DECIMAL(14,2) COMMENT '正向有功示数'
)
COMMENT '测量点日电量'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS dwd_cj_fhqx (
  cldbs BIGINT COMMENT '测量点标识',
  hh STRING COMMENT '户号',
  dnbzcbh STRING COMMENT '电能表资产编号',
  sjsj DATETIME COMMENT '数据时间',
  yggl DECIMAL(12,4) COMMENT '有功功率',
  wggl DECIMAL(12,4) COMMENT '无功功率'
)
COMMENT '测量点负荷曲线'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS dwd_cj_zd_xx (
  zdbs BIGINT COMMENT '终端标识',
  zdzcbh STRING COMMENT '终端资产编号',
  zdlx STRING COMMENT '终端类型',
  zddz STRING COMMENT '终端地址',
  gddw_mc STRING COMMENT '供电单位名称',
  yxzt STRING COMMENT '运行状态',
  tyrq STRING COMMENT '投运日期'
)
COMMENT '采集终端信息'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS dwd_kf_gd_mx (
  gdbh STRING COMMENT '工单编号',
  slsj DATETIME COMMENT '受理时间',
  ywlx STRING COMMENT '业务类型',
  hh STRING COMMENT '户号',
  khmc STRING COMMENT '客户名称',
  lxdh STRING COMMENT '联系电话',
  slnr STRING COMMENT '受理内容',
  cldw STRING COMMENT '处理单位',
  clzt STRING COMMENT '处理状态',
  bjsj DATETIME COMMENT '办结时间',
  hfpf DECIMAL(4,1) COMMENT '回访评分',
  hfjg STRING COMMENT '回访结果'
)
COMMENT '95598工单明细'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS dws_yx_kh_qf_hz (
  hh STRING COMMENT '户号',
  qfys BIGINT COMMENT '欠费月数',
  ljqfje DECIMAL(14,2) COMMENT '累计欠费金额',
  ljwyj DECIMAL(14,2) COMMENT '累计违约金',
  zzqfny STRING COMMENT '最早欠费年月'
)
COMMENT '客户欠费汇总'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS dws_yx_kh_jf_hz (
  hh STRING COMMENT '户号',
  zjjfsj DATETIME COMMENT '最近缴费时间',
  ljjfje DECIMAL(14,2) COMMENT '累计缴费金额',
  jfcs BIGINT COMMENT '缴费次数'
)
COMMENT '客户缴费汇总'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS dws_yx_kh_ydl_y (
  hh STRING COMMENT '户号',
  ny STRING COMMENT '年月',
  ydl DECIMAL(14,2) COMMENT '月用电量',
  ysdf DECIMAL(14,2) COMMENT '月应收电费'
)
COMMENT '客户月用电汇总'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS dws_kf_gd_tj_y (
  cldw STRING COMMENT '处理单位',
  tjyf STRING COMMENT '统计月份',
  gdzs BIGINT COMMENT '工单总数',
  tsgds BIGINT COMMENT '投诉工单数',
  bxgds BIGINT COMMENT '报修工单数',
  tsl DECIMAL(8,4) COMMENT '投诉占比',
  pjmyd DECIMAL(4,2) COMMENT '平均回访评分'
)
COMMENT '工单月度统计'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS dws_cj_kh_fh_r (
  hh STRING COMMENT '户号',
  rq STRING COMMENT '日期',
  zdfh DECIMAL(12,4) COMMENT '日最大负荷',
  pjfh DECIMAL(12,4) COMMENT '日平均负荷'
)
COMMENT '客户日负荷统计'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ads_yx_khda_cx (
  yhbh STRING COMMENT '用户编号',
  yhmc STRING COMMENT '用户名称',
  ydsz STRING COMMENT '用电地址',
  gddw STRING COMMENT '供电单位',
  ydlb STRING COMMENT '用电类别',
  hylb STRING COMMENT '行业类别',
  dydj STRING COMMENT '电压等级',
  htrl DECIMAL(12,2) COMMENT '合同容量',
  yhzt STRING COMMENT '用户状态',
  lhrq STRING COMMENT '立户日期',
  lxr STRING COMMENT '联系人',
  lxdh STRING COMMENT '联系电话'
)
COMMENT '客户档案查询'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ads_yx_qfmx_cx (
  hh STRING COMMENT '户号',
  hm STRING COMMENT '户名',
  gddw STRING COMMENT '供电单位',
  dfny STRING COMMENT '电费年月',
  ysdf DECIMAL(14,2) COMMENT '应收电费',
  ssdf DECIMAL(14,2) COMMENT '实收电费',
  qfje DECIMAL(14,2) COMMENT '欠费金额',
  wyj DECIMAL(14,2) COMMENT '违约金',
  fxrq STRING COMMENT '发行日期'
)
COMMENT '电费欠费明细'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ads_yx_kh360 (
  hh STRING COMMENT '户号',
  hm STRING COMMENT '户名',
  ydsz STRING COMMENT '用电地址',
  gddw STRING COMMENT '供电单位',
  htrl DECIMAL(12,2) COMMENT '合同容量',
  lxdh STRING COMMENT '联系电话',
  qfys BIGINT COMMENT '欠费月数',
  ljqf DECIMAL(14,2) COMMENT '累计欠费',
  zjjfsj DATETIME COMMENT '最近缴费时间',
  ljjf DECIMAL(14,2) COMMENT '累计缴费'
)
COMMENT '客户360视图'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ads_yx_ydl_fx (
  hh STRING COMMENT '户号',
  hm STRING COMMENT '户名',
  gddw STRING COMMENT '供电单位',
  ydlb STRING COMMENT '用电类别',
  ny STRING COMMENT '年月',
  ydl DECIMAL(14,2) COMMENT '月用电量',
  ysdf DECIMAL(14,2) COMMENT '应收电费'
)
COMMENT '月度用电分析'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ads_kf_gd_cx (
  gdbh STRING COMMENT '工单编号',
  slsj DATETIME COMMENT '受理时间',
  ywlx STRING COMMENT '业务类型',
  hh STRING COMMENT '户号',
  khmc STRING COMMENT '客户名称',
  lxdh STRING COMMENT '联系电话',
  slnr STRING COMMENT '受理内容',
  cldw STRING COMMENT '处理单位',
  clzt STRING COMMENT '处理状态',
  bjsj DATETIME COMMENT '办结时间',
  hfpf DECIMAL(4,1) COMMENT '回访评分'
)
COMMENT '95598工单查询'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ads_kf_gd_kb (
  cldw STRING COMMENT '处理单位',
  tjyf STRING COMMENT '统计月份',
  gdzs BIGINT COMMENT '工单总数',
  tsgds BIGINT COMMENT '投诉工单数',
  bxgds BIGINT COMMENT '报修工单数',
  tsl DECIMAL(8,4) COMMENT '投诉占比',
  pjmyd DECIMAL(4,2) COMMENT '平均满意度'
)
COMMENT '工单统计看板'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS ads_cj_dkh_fh (
  hh STRING COMMENT '户号',
  hm STRING COMMENT '户名',
  gddw STRING COMMENT '供电单位',
  htrl DECIMAL(12,2) COMMENT '合同容量',
  rq STRING COMMENT '日期',
  zdfh DECIMAL(12,4) COMMENT '最大负荷',
  pjfh DECIMAL(12,4) COMMENT '平均负荷',
  fzl DECIMAL(8,4) COMMENT '负载率'
)
COMMENT '大客户负荷监测'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS dwd_yx_kh_jbxx_bak (
  hh STRING,
  hm STRING,
  ydsz STRING,
  htrl DECIMAL(12,2)
)
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS dwd_yx_kh_xx_v1 (
  cons_no STRING COMMENT '用户编号',
  cons_name STRING COMMENT '用户名称',
  elec_addr STRING COMMENT '用电地址',
  org_no STRING COMMENT '供电单位'
)
COMMENT '客户信息（旧版，已停用）'
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;

CREATE TABLE IF NOT EXISTS tmp_qf_hh_20251201 (
  hh STRING,
  qfje DECIMAL(14,2)
)
PARTITIONED BY (dt STRING COMMENT '业务日期')
LIFECYCLE 3650;
