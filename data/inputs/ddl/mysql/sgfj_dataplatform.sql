-- 本地 MySQL 替身库：sgfj_dataplatform（只有表结构）
CREATE DATABASE IF NOT EXISTS `sgfj_dataplatform` DEFAULT CHARACTER SET utf8mb4;
USE `sgfj_dataplatform`;

DROP TABLE IF EXISTS `ods_yx186_o_org`;
CREATE TABLE `ods_yx186_o_org` (
  `org_no` varchar(16) COMMENT '单位编号',
  `org_name` varchar(64) COMMENT '单位名称',
  `p_org_no` varchar(16) COMMENT '上级单位',
  `org_type` varchar(2) COMMENT '单位类型 02市 03县 04供电所',
  `sort_no` bigint
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='供电单位（yx186同步）';

DROP TABLE IF EXISTS `ods_yx186_c_cons`;
CREATE TABLE `ods_yx186_c_cons` (
  `cons_id` bigint COMMENT '客户ID',
  `cons_no` varchar(16) COMMENT '用户编号',
  `cons_name` varchar(128) COMMENT '用户名称',
  `elec_addr` varchar(256) COMMENT '用电地址',
  `org_no` varchar(16) COMMENT '供电单位',
  `trade_code` varchar(8) COMMENT '行业分类代码',
  `elec_type_code` varchar(4) COMMENT '用电类别',
  `volt_code` varchar(4) COMMENT '电压',
  `contract_cap` decimal(12,2) COMMENT '合同容量（kVA）',
  `run_cap` decimal(12,2) COMMENT '运行容量（kVA）',
  `status_code` varchar(2) COMMENT '用户状态',
  `build_date` date COMMENT '建档日期',
  `cancel_date` date COMMENT '销户日期',
  `lode_attr_code` varchar(2) COMMENT '负荷性质'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用电客户（yx186同步）';

DROP TABLE IF EXISTS `ods_yx186_c_contact`;
CREATE TABLE `ods_yx186_c_contact` (
  `contact_id` bigint COMMENT '联系人标识',
  `cons_id` bigint COMMENT '客户ID',
  `contact_name` varchar(64) COMMENT '联系人',
  `mobile` varchar(32) COMMENT '手机',
  `office_tel` varchar(32),
  `contact_mode` varchar(2) COMMENT '类型 01主要 02备用'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户联系人（yx186同步）';

DROP TABLE IF EXISTS `ods_yx186_c_mp`;
CREATE TABLE `ods_yx186_c_mp` (
  `mp_id` bigint COMMENT '计量点ID',
  `mp_no` varchar(20) COMMENT '计量点编号',
  `mp_name` varchar(128) COMMENT '计量点名称',
  `cons_id` bigint,
  `mp_addr` varchar(256) COMMENT '计量点地址',
  `volt_code` varchar(4) COMMENT '计量点电压等级',
  `mp_attr_code` varchar(2) COMMENT '性质 01结算 02考核',
  `status_code` varchar(2)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='计量点（yx186同步）';

DROP TABLE IF EXISTS `ods_yx186_d_meter`;
CREATE TABLE `ods_yx186_d_meter` (
  `meter_id` bigint,
  `asset_no` varchar(32) COMMENT '资产编号',
  `made_no` varchar(32) COMMENT '出厂编号',
  `manufacturer` varchar(64) COMMENT '厂家',
  `type_code` varchar(8),
  `wiring_mode` varchar(2) COMMENT '接线方式',
  `t_factor` decimal(10,2) COMMENT '倍率',
  `inst_date` date COMMENT '装表日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='电能表资产（yx186同步）';

DROP TABLE IF EXISTS `ods_yx186_c_meter_mp_rela`;
CREATE TABLE `ods_yx186_c_meter_mp_rela` (
  `rela_id` bigint COMMENT '关系标识',
  `mp_id` bigint COMMENT '计量点标识',
  `meter_id` bigint,
  `rela_date` date COMMENT '建立关系日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='计量点电能表关系（yx186同步）';

DROP TABLE IF EXISTS `ods_yx186_r_read`;
CREATE TABLE `ods_yx186_r_read` (
  `read_id` bigint,
  `mp_id` bigint COMMENT '计量点标识',
  `ym` varchar(6) COMMENT '年月',
  `last_read` decimal(14,2) COMMENT '上次示数',
  `this_read` decimal(14,2) COMMENT '本次示数',
  `read_date` date COMMENT '抄表日期',
  `read_type_code` varchar(2) COMMENT '抄表方式 01远抄 02手工'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='抄表示数（yx186同步）';

DROP TABLE IF EXISTS `ods_yx186_a_rcvbl_flow`;
CREATE TABLE `ods_yx186_a_rcvbl_flow` (
  `rcvbl_id` bigint,
  `cons_no` varchar(16) COMMENT '户号',
  `rcvbl_ym` varchar(6) COMMENT '应收年月',
  `t_settle_pq` decimal(14,2) COMMENT '结算电量',
  `rcvbl_amt` decimal(14,2) COMMENT '应收金额',
  `rcved_amt` decimal(14,2) COMMENT '实收金额',
  `penalty` decimal(12,2) COMMENT '电费违约金（元）',
  `settle_flag` varchar(2) COMMENT '结清标志 0未结清 1已结清',
  `rel_date` date COMMENT '电费发行日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='应收电费流水（yx186同步）';

DROP TABLE IF EXISTS `ods_yx186_a_pay_flow`;
CREATE TABLE `ods_yx186_a_pay_flow` (
  `charge_id` bigint COMMENT '缴费记录标识',
  `cons_no` varchar(16) COMMENT '户号',
  `rcvbl_id` bigint COMMENT '对应应收标识',
  `charge_date` datetime COMMENT '收费日期',
  `rcv_amt` decimal(14,2) COMMENT '金额',
  `pay_mode` varchar(4) COMMENT '缴费方式 01柜台 02支付宝 03微信 04银行代扣',
  `acct_org_no` varchar(16) COMMENT '收费单位'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实收电费流水（yx186同步）';

DROP TABLE IF EXISTS `ods_yx186_a_rcvbl_flow_his`;
CREATE TABLE `ods_yx186_a_rcvbl_flow_his` (
  `rcvbl_id` bigint COMMENT '应收电费标识',
  `cons_no` varchar(16) COMMENT '户号',
  `rcvbl_ym` varchar(6) COMMENT '应收年月',
  `t_settle_pq` decimal(14,2) COMMENT '结算电量',
  `rcvbl_amt` decimal(14,2) COMMENT '应收金额',
  `rcved_amt` decimal(14,2) COMMENT '实收金额',
  `penalty` decimal(12,2),
  `settle_flag` varchar(2) COMMENT '结清标志',
  `rel_date` date COMMENT '电费发行日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='应收电费历史流水（2024）（yx186同步）';

DROP TABLE IF EXISTS `ods_cjxt_r_tmnl_run`;
CREATE TABLE `ods_cjxt_r_tmnl_run` (
  `terminal_id` bigint COMMENT '终端标识',
  `tmnl_asset_no` varchar(32),
  `tmnl_type_code` varchar(4) COMMENT '终端类型 01集中器 02专变终端',
  `terminal_addr` varchar(32) COMMENT '终端逻辑地址',
  `org_no` varchar(16),
  `run_status` varchar(2) COMMENT '终端运行状态',
  `inst_date` date COMMENT '终端投运日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='终端运行档案（cjxt同步）';

DROP TABLE IF EXISTS `ods_cjxt_e_data_mp`;
CREATE TABLE `ods_cjxt_e_data_mp` (
  `id` bigint,
  `terminal_id` bigint COMMENT '所属终端标识',
  `mp_sn` bigint COMMENT '测量点序号',
  `mp_id` bigint,
  `cons_no` varchar(16),
  `meter_asset_no` varchar(32) COMMENT '电能表资产编号',
  `t_factor` decimal(10,2)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='采集测量点（cjxt同步）';

DROP TABLE IF EXISTS `ods_cjxt_e_mp_day_read`;
CREATE TABLE `ods_cjxt_e_mp_day_read` (
  `id` bigint COMMENT '测量点标识',
  `data_date` date COMMENT '日冻结日期',
  `pap_r` decimal(14,2) COMMENT '正向有功总示数',
  `prp_r` decimal(14,2),
  `rap_r` decimal(14,2) COMMENT '反向有功总示数',
  `col_time` datetime COMMENT '采集时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='E_MP_DAY_READ（cjxt同步）';

DROP TABLE IF EXISTS `ods_cjxt_e_mp_day_energy`;
CREATE TABLE `ods_cjxt_e_mp_day_energy` (
  `id` bigint COMMENT '测量点标识',
  `data_date` date COMMENT '数据日期',
  `pap_e` decimal(14,2) COMMENT '日正向有功电量（kWh）',
  `prp_e` decimal(14,2),
  `rap_e` decimal(14,2)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='E_MP_DAY_ENERGY（cjxt同步）';

DROP TABLE IF EXISTS `ods_cjxt_e_mp_power_curve`;
CREATE TABLE `ods_cjxt_e_mp_power_curve` (
  `id` bigint COMMENT '测量点标识',
  `data_time` datetime COMMENT '曲线数据时间',
  `p` decimal(12,4),
  `q` decimal(12,4) COMMENT '无功功率（kvar）'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='E_MP_POWER_CURVE（cjxt同步）';

DROP TABLE IF EXISTS `ods_kf95598_t_kf_workorder`;
CREATE TABLE `ods_kf95598_t_kf_workorder` (
  `app_no` varchar(32) COMMENT '工单号',
  `accept_time` datetime COMMENT '受理时间',
  `busi_type` varchar(4) COMMENT '业务类型 01故障报修 02咨询 03投诉 04意见建议',
  `cust_no` varchar(16) COMMENT '客户编号',
  `cust_name` varchar(128) COMMENT '客户名称',
  `contact_tel` varchar(32) COMMENT '联系电话',
  `accept_content` varchar(1024) COMMENT '受理内容',
  `handle_org` varchar(16) COMMENT '处理单位',
  `handle_status` varchar(2) COMMENT '状态',
  `finish_time` datetime COMMENT '办结时间',
  `satisfy_code` varchar(2) COMMENT '满意度'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='95598工单（kf95598同步）';

DROP TABLE IF EXISTS `ods_kf95598_t_kf_visit`;
CREATE TABLE `ods_kf95598_t_kf_visit` (
  `visit_id` bigint COMMENT '回访记录标识',
  `app_no` varchar(32) COMMENT '工单号',
  `visit_time` datetime COMMENT '回访时间',
  `visit_result` varchar(256) COMMENT '回访结果',
  `satisfy_score` decimal(4,1) COMMENT '评分'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单回访（kf95598同步）';

DROP TABLE IF EXISTS `dwd_yx_kh_jbxx`;
CREATE TABLE `dwd_yx_kh_jbxx` (
  `khbs` bigint COMMENT '客户标识',
  `hh` varchar(16) COMMENT '户号',
  `hm` varchar(128) COMMENT '户名',
  `ydsz` varchar(256) COMMENT '用电地址',
  `gddw_bm` varchar(16) COMMENT '供电单位编码',
  `gddw_mc` varchar(64) COMMENT '供电单位名称',
  `hylb` varchar(8) COMMENT '行业类别',
  `ydlb` varchar(4) COMMENT '用电类别',
  `gddy` varchar(4) COMMENT '供电电压',
  `htrl` decimal(12,2) COMMENT '合同容量',
  `yhzt` varchar(2) COMMENT '用户状态',
  `lhrq` date COMMENT '立户日期',
  `xhrq` date COMMENT '销户日期',
  `lxr` varchar(64) COMMENT '主联系人',
  `lxdh` varchar(32) COMMENT '联系电话'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户基本信息';

DROP TABLE IF EXISTS `dwd_yx_jld_xx`;
CREATE TABLE `dwd_yx_jld_xx` (
  `jldbs` bigint COMMENT '计量点标识',
  `jldbh` varchar(20) COMMENT '计量点编号',
  `jldmc` varchar(128) COMMENT '计量点名称',
  `hh` varchar(16) COMMENT '户号',
  `dnbzcbh` varchar(32) COMMENT '电能表资产编号',
  `ccbh` varchar(32) COMMENT '出厂编号',
  `sccj` varchar(64) COMMENT '生产厂家',
  `zhbl` decimal(10,2) COMMENT '综合倍率',
  `zbrq` date COMMENT '装表日期',
  `jldzt` varchar(2) COMMENT '计量点状态'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='计量点信息';

DROP TABLE IF EXISTS `dwd_yx_df_ysmx`;
CREATE TABLE `dwd_yx_df_ysmx` (
  `ysbs` bigint COMMENT '应收标识',
  `hh` varchar(16) COMMENT '户号',
  `dfny` varchar(6) COMMENT '电费年月',
  `jsdl` decimal(14,2) COMMENT '结算电量',
  `ysje` decimal(14,2) COMMENT '应收金额',
  `ssje` decimal(14,2) COMMENT '实收金额',
  `qfje` decimal(14,2) COMMENT '欠费金额',
  `wyj` decimal(14,2) COMMENT '违约金',
  `jqbz` varchar(2) COMMENT '结清标志',
  `fxrq` date COMMENT '发行日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='应收电费明细';

DROP TABLE IF EXISTS `dwd_yx_jf_mx`;
CREATE TABLE `dwd_yx_jf_mx` (
  `jfbs` bigint COMMENT '缴费标识',
  `hh` varchar(16) COMMENT '户号',
  `ysbs` bigint COMMENT '应收标识',
  `jfsj` datetime COMMENT '缴费时间',
  `jfje` decimal(14,2) COMMENT '缴费金额',
  `jffs` varchar(4) COMMENT '缴费方式',
  `sfdw` varchar(64) COMMENT '收费单位'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='缴费明细';

DROP TABLE IF EXISTS `dwd_yx_cbsz`;
CREATE TABLE `dwd_yx_cbsz` (
  `cbbs` bigint COMMENT '抄表标识',
  `jldbh` varchar(20) COMMENT '计量点编号',
  `hh` varchar(16) COMMENT '户号',
  `cbny` varchar(6) COMMENT '抄表年月',
  `sccbsz` decimal(14,2) COMMENT '上次示数',
  `bccbsz` decimal(14,2) COMMENT '本次示数',
  `cjdl` decimal(14,2) COMMENT '抄见电量',
  `cbrq` date COMMENT '抄表日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='抄表示数明细';

DROP TABLE IF EXISTS `dwd_cj_rdl`;
CREATE TABLE `dwd_cj_rdl` (
  `cldbs` bigint COMMENT '测量点标识',
  `hh` varchar(16) COMMENT '户号',
  `dnbzcbh` varchar(32) COMMENT '电能表资产编号',
  `sjrq` date COMMENT '数据日期',
  `zxygdl` decimal(14,2) COMMENT '正向有功电量',
  `zxwgdl` decimal(14,2) COMMENT '正向无功电量',
  `zxygsz` decimal(14,2) COMMENT '正向有功示数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测量点日电量';

DROP TABLE IF EXISTS `dwd_cj_fhqx`;
CREATE TABLE `dwd_cj_fhqx` (
  `cldbs` bigint COMMENT '测量点标识',
  `hh` varchar(16) COMMENT '户号',
  `dnbzcbh` varchar(32) COMMENT '电能表资产编号',
  `sjsj` datetime COMMENT '数据时间',
  `yggl` decimal(12,4) COMMENT '有功功率',
  `wggl` decimal(12,4) COMMENT '无功功率'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测量点负荷曲线';

DROP TABLE IF EXISTS `dwd_cj_zd_xx`;
CREATE TABLE `dwd_cj_zd_xx` (
  `zdbs` bigint COMMENT '终端标识',
  `zdzcbh` varchar(32) COMMENT '终端资产编号',
  `zdlx` varchar(4) COMMENT '终端类型',
  `zddz` varchar(32) COMMENT '终端地址',
  `gddw_mc` varchar(64) COMMENT '供电单位名称',
  `yxzt` varchar(2) COMMENT '运行状态',
  `tyrq` date COMMENT '投运日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='采集终端信息';

DROP TABLE IF EXISTS `dwd_kf_gd_mx`;
CREATE TABLE `dwd_kf_gd_mx` (
  `gdbh` varchar(32) COMMENT '工单编号',
  `slsj` datetime COMMENT '受理时间',
  `ywlx` varchar(4) COMMENT '业务类型',
  `hh` varchar(16) COMMENT '户号',
  `khmc` varchar(128) COMMENT '客户名称',
  `lxdh` varchar(32) COMMENT '联系电话',
  `slnr` varchar(1024) COMMENT '受理内容',
  `cldw` varchar(64) COMMENT '处理单位',
  `clzt` varchar(2) COMMENT '处理状态',
  `bjsj` datetime COMMENT '办结时间',
  `hfpf` decimal(4,1) COMMENT '回访评分',
  `hfjg` varchar(256) COMMENT '回访结果'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='95598工单明细';

DROP TABLE IF EXISTS `dws_yx_kh_qf_hz`;
CREATE TABLE `dws_yx_kh_qf_hz` (
  `hh` varchar(16) COMMENT '户号',
  `qfys` bigint COMMENT '欠费月数',
  `ljqfje` decimal(14,2) COMMENT '累计欠费金额',
  `ljwyj` decimal(14,2) COMMENT '累计违约金',
  `zzqfny` varchar(6) COMMENT '最早欠费年月'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户欠费汇总';

DROP TABLE IF EXISTS `dws_yx_kh_jf_hz`;
CREATE TABLE `dws_yx_kh_jf_hz` (
  `hh` varchar(16) COMMENT '户号',
  `zjjfsj` datetime COMMENT '最近缴费时间',
  `ljjfje` decimal(14,2) COMMENT '累计缴费金额',
  `jfcs` bigint COMMENT '缴费次数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户缴费汇总';

DROP TABLE IF EXISTS `dws_yx_kh_ydl_y`;
CREATE TABLE `dws_yx_kh_ydl_y` (
  `hh` varchar(16) COMMENT '户号',
  `ny` varchar(6) COMMENT '年月',
  `ydl` decimal(14,2) COMMENT '月用电量',
  `ysdf` decimal(14,2) COMMENT '月应收电费'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户月用电汇总';

DROP TABLE IF EXISTS `dws_kf_gd_tj_y`;
CREATE TABLE `dws_kf_gd_tj_y` (
  `cldw` varchar(64) COMMENT '处理单位',
  `tjyf` varchar(7) COMMENT '统计月份',
  `gdzs` bigint COMMENT '工单总数',
  `tsgds` bigint COMMENT '投诉工单数',
  `bxgds` bigint COMMENT '报修工单数',
  `tsl` decimal(8,4) COMMENT '投诉占比',
  `pjmyd` decimal(4,2) COMMENT '平均回访评分'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单月度统计';

DROP TABLE IF EXISTS `dws_cj_kh_fh_r`;
CREATE TABLE `dws_cj_kh_fh_r` (
  `hh` varchar(16) COMMENT '户号',
  `rq` date COMMENT '日期',
  `zdfh` decimal(12,4) COMMENT '日最大负荷',
  `pjfh` decimal(12,4) COMMENT '日平均负荷'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户日负荷统计';

DROP TABLE IF EXISTS `ads_yx_khda_cx`;
CREATE TABLE `ads_yx_khda_cx` (
  `yhbh` varchar(16) COMMENT '用户编号',
  `yhmc` varchar(128) COMMENT '用户名称',
  `ydsz` varchar(256) COMMENT '用电地址',
  `gddw` varchar(64) COMMENT '供电单位',
  `ydlb` varchar(4) COMMENT '用电类别',
  `hylb` varchar(8) COMMENT '行业类别',
  `dydj` varchar(4) COMMENT '电压等级',
  `htrl` decimal(12,2) COMMENT '合同容量',
  `yhzt` varchar(2) COMMENT '用户状态',
  `lhrq` date COMMENT '立户日期',
  `lxr` varchar(64) COMMENT '联系人',
  `lxdh` varchar(32) COMMENT '联系电话'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户档案查询';

DROP TABLE IF EXISTS `ads_yx_qfmx_cx`;
CREATE TABLE `ads_yx_qfmx_cx` (
  `hh` varchar(16) COMMENT '户号',
  `hm` varchar(128) COMMENT '户名',
  `gddw` varchar(64) COMMENT '供电单位',
  `dfny` varchar(6) COMMENT '电费年月',
  `ysdf` decimal(14,2) COMMENT '应收电费',
  `ssdf` decimal(14,2) COMMENT '实收电费',
  `qfje` decimal(14,2) COMMENT '欠费金额',
  `wyj` decimal(14,2) COMMENT '违约金',
  `fxrq` date COMMENT '发行日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='电费欠费明细';

DROP TABLE IF EXISTS `ads_yx_kh360`;
CREATE TABLE `ads_yx_kh360` (
  `hh` varchar(16) COMMENT '户号',
  `hm` varchar(128) COMMENT '户名',
  `ydsz` varchar(256) COMMENT '用电地址',
  `gddw` varchar(64) COMMENT '供电单位',
  `htrl` decimal(12,2) COMMENT '合同容量',
  `lxdh` varchar(32) COMMENT '联系电话',
  `qfys` bigint COMMENT '欠费月数',
  `ljqf` decimal(14,2) COMMENT '累计欠费',
  `zjjfsj` datetime COMMENT '最近缴费时间',
  `ljjf` decimal(14,2) COMMENT '累计缴费'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户360视图';

DROP TABLE IF EXISTS `ads_yx_ydl_fx`;
CREATE TABLE `ads_yx_ydl_fx` (
  `hh` varchar(16) COMMENT '户号',
  `hm` varchar(128) COMMENT '户名',
  `gddw` varchar(64) COMMENT '供电单位',
  `ydlb` varchar(4) COMMENT '用电类别',
  `ny` varchar(6) COMMENT '年月',
  `ydl` decimal(14,2) COMMENT '月用电量',
  `ysdf` decimal(14,2) COMMENT '应收电费'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='月度用电分析';

DROP TABLE IF EXISTS `ads_kf_gd_cx`;
CREATE TABLE `ads_kf_gd_cx` (
  `gdbh` varchar(32) COMMENT '工单编号',
  `slsj` datetime COMMENT '受理时间',
  `ywlx` varchar(4) COMMENT '业务类型',
  `hh` varchar(16) COMMENT '户号',
  `khmc` varchar(128) COMMENT '客户名称',
  `lxdh` varchar(32) COMMENT '联系电话',
  `slnr` varchar(1024) COMMENT '受理内容',
  `cldw` varchar(64) COMMENT '处理单位',
  `clzt` varchar(2) COMMENT '处理状态',
  `bjsj` datetime COMMENT '办结时间',
  `hfpf` decimal(4,1) COMMENT '回访评分'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='95598工单查询';

DROP TABLE IF EXISTS `ads_kf_gd_kb`;
CREATE TABLE `ads_kf_gd_kb` (
  `cldw` varchar(64) COMMENT '处理单位',
  `tjyf` varchar(7) COMMENT '统计月份',
  `gdzs` bigint COMMENT '工单总数',
  `tsgds` bigint COMMENT '投诉工单数',
  `bxgds` bigint COMMENT '报修工单数',
  `tsl` decimal(8,4) COMMENT '投诉占比',
  `pjmyd` decimal(4,2) COMMENT '平均满意度'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单统计看板';

DROP TABLE IF EXISTS `ads_cj_dkh_fh`;
CREATE TABLE `ads_cj_dkh_fh` (
  `hh` varchar(16) COMMENT '户号',
  `hm` varchar(128) COMMENT '户名',
  `gddw` varchar(64) COMMENT '供电单位',
  `htrl` decimal(12,2) COMMENT '合同容量',
  `rq` date COMMENT '日期',
  `zdfh` decimal(12,4) COMMENT '最大负荷',
  `pjfh` decimal(12,4) COMMENT '平均负荷',
  `fzl` decimal(8,4) COMMENT '负载率'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='大客户负荷监测';

DROP TABLE IF EXISTS `dwd_yx_kh_jbxx_bak`;
CREATE TABLE `dwd_yx_kh_jbxx_bak` (
  `hh` varchar(16),
  `hm` varchar(128),
  `ydsz` varchar(256),
  `htrl` decimal(12,2)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS `dwd_yx_kh_xx_v1`;
CREATE TABLE `dwd_yx_kh_xx_v1` (
  `cons_no` varchar(16) COMMENT '用户编号',
  `cons_name` varchar(128) COMMENT '用户名称',
  `elec_addr` varchar(256) COMMENT '用电地址',
  `org_no` varchar(16) COMMENT '供电单位'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户信息（旧版，已停用）';

DROP TABLE IF EXISTS `tmp_qf_hh_20251201`;
CREATE TABLE `tmp_qf_hh_20251201` (
  `hh` varchar(16),
  `qfje` decimal(14,2)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
