-- 本地 MySQL 替身库：yx186（只有表结构）
CREATE DATABASE IF NOT EXISTS `yx186` DEFAULT CHARACTER SET utf8mb4;
USE `yx186`;

DROP TABLE IF EXISTS `O_ORG`;
CREATE TABLE `O_ORG` (
  `ORG_NO` varchar(16) NOT NULL COMMENT '单位编号',
  `ORG_NAME` varchar(64) COMMENT '单位名称',
  `P_ORG_NO` varchar(16) COMMENT '上级单位',
  `ORG_TYPE` varchar(2) COMMENT '单位类型 02市 03县 04供电所',
  `SORT_NO` bigint,
  PRIMARY KEY (`ORG_NO`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='供电单位';

DROP TABLE IF EXISTS `C_CONS`;
CREATE TABLE `C_CONS` (
  `CONS_ID` bigint NOT NULL COMMENT '客户ID',
  `CONS_NO` varchar(16) NOT NULL COMMENT '用户编号',
  `CONS_NAME` varchar(128) COMMENT '用户名称',
  `ELEC_ADDR` varchar(256) COMMENT '用电地址',
  `ORG_NO` varchar(16) COMMENT '供电单位',
  `TRADE_CODE` varchar(8) COMMENT '行业分类代码',
  `ELEC_TYPE_CODE` varchar(4),
  `VOLT_CODE` varchar(4) COMMENT '电压',
  `CONTRACT_CAP` decimal(12,2),
  `RUN_CAP` decimal(12,2),
  `STATUS_CODE` varchar(2) COMMENT '用户状态',
  `BUILD_DATE` date COMMENT '建档日期',
  `CANCEL_DATE` date,
  `LODE_ATTR_CODE` varchar(2),
  PRIMARY KEY (`CONS_ID`),
  UNIQUE KEY `UK_C_CONS_CONS_NO` (`CONS_NO`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用电客户';

DROP TABLE IF EXISTS `C_CONTACT`;
CREATE TABLE `C_CONTACT` (
  `CONTACT_ID` bigint NOT NULL,
  `CONS_ID` bigint COMMENT '客户ID',
  `CONTACT_NAME` varchar(64) COMMENT '联系人',
  `MOBILE` varchar(32) COMMENT '手机',
  `OFFICE_TEL` varchar(32),
  `CONTACT_MODE` varchar(2) COMMENT '类型 01主要 02备用',
  PRIMARY KEY (`CONTACT_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户联系人';

DROP TABLE IF EXISTS `C_MP`;
CREATE TABLE `C_MP` (
  `MP_ID` bigint NOT NULL COMMENT '计量点ID',
  `MP_NO` varchar(20) NOT NULL COMMENT '计量点编号',
  `MP_NAME` varchar(128),
  `CONS_ID` bigint,
  `MP_ADDR` varchar(256),
  `VOLT_CODE` varchar(4) COMMENT '计量点电压等级',
  `MP_ATTR_CODE` varchar(2) COMMENT '性质 01结算 02考核',
  `STATUS_CODE` varchar(2),
  PRIMARY KEY (`MP_ID`),
  UNIQUE KEY `UK_C_MP_MP_NO` (`MP_NO`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='计量点';

DROP TABLE IF EXISTS `D_METER`;
CREATE TABLE `D_METER` (
  `METER_ID` bigint NOT NULL,
  `ASSET_NO` varchar(32) NOT NULL COMMENT '资产编号',
  `MADE_NO` varchar(32) COMMENT '出厂编号',
  `MANUFACTURER` varchar(64) COMMENT '厂家',
  `TYPE_CODE` varchar(8),
  `WIRING_MODE` varchar(2) COMMENT '接线方式',
  `T_FACTOR` decimal(10,2) COMMENT '倍率',
  `INST_DATE` date COMMENT '装表日期',
  PRIMARY KEY (`METER_ID`),
  UNIQUE KEY `UK_D_METER_ASSET_NO` (`ASSET_NO`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='电能表资产';

DROP TABLE IF EXISTS `C_METER_MP_RELA`;
CREATE TABLE `C_METER_MP_RELA` (
  `RELA_ID` bigint NOT NULL,
  `MP_ID` bigint,
  `METER_ID` bigint,
  `RELA_DATE` date,
  PRIMARY KEY (`RELA_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS `R_READ`;
CREATE TABLE `R_READ` (
  `READ_ID` bigint NOT NULL,
  `MP_ID` bigint COMMENT '计量点标识',
  `YM` varchar(6) COMMENT '年月',
  `LAST_READ` decimal(14,2) COMMENT '上次示数',
  `THIS_READ` decimal(14,2) COMMENT '本次示数',
  `READ_DATE` date COMMENT '抄表日期',
  `READ_TYPE_CODE` varchar(2) COMMENT '抄表方式 01远抄 02手工',
  PRIMARY KEY (`READ_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='抄表示数';

DROP TABLE IF EXISTS `A_RCVBL_FLOW`;
CREATE TABLE `A_RCVBL_FLOW` (
  `RCVBL_ID` bigint NOT NULL,
  `CONS_NO` varchar(16) COMMENT '户号',
  `RCVBL_YM` varchar(6) COMMENT '应收年月',
  `T_SETTLE_PQ` decimal(14,2) COMMENT '结算电量',
  `RCVBL_AMT` decimal(14,2) COMMENT '应收金额',
  `RCVED_AMT` decimal(14,2) COMMENT '实收金额',
  `PENALTY` decimal(12,2),
  `SETTLE_FLAG` varchar(2) COMMENT '结清标志 0未结清 1已结清',
  `REL_DATE` date,
  PRIMARY KEY (`RCVBL_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='应收电费流水';

DROP TABLE IF EXISTS `A_PAY_FLOW`;
CREATE TABLE `A_PAY_FLOW` (
  `CHARGE_ID` bigint NOT NULL,
  `CONS_NO` varchar(16) COMMENT '户号',
  `RCVBL_ID` bigint COMMENT '对应应收标识',
  `CHARGE_DATE` datetime COMMENT '收费日期',
  `RCV_AMT` decimal(14,2) COMMENT '金额',
  `PAY_MODE` varchar(4) COMMENT '缴费方式 01柜台 02支付宝 03微信 04银行代扣',
  `ACCT_ORG_NO` varchar(16),
  PRIMARY KEY (`CHARGE_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实收电费流水';

DROP TABLE IF EXISTS `A_RCVBL_FLOW_HIS`;
CREATE TABLE `A_RCVBL_FLOW_HIS` (
  `RCVBL_ID` bigint NOT NULL,
  `CONS_NO` varchar(16) COMMENT '户号',
  `RCVBL_YM` varchar(6) COMMENT '应收年月',
  `T_SETTLE_PQ` decimal(14,2) COMMENT '结算电量',
  `RCVBL_AMT` decimal(14,2) COMMENT '应收金额',
  `RCVED_AMT` decimal(14,2) COMMENT '实收金额',
  `PENALTY` decimal(12,2),
  `SETTLE_FLAG` varchar(2) COMMENT '结清标志',
  `REL_DATE` date,
  PRIMARY KEY (`RCVBL_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='应收电费历史流水（2024）';

DROP TABLE IF EXISTS `C_CONS_BAK_20230601`;
CREATE TABLE `C_CONS_BAK_20230601` (
  `CONS_ID` bigint NOT NULL,
  `CONS_NO` varchar(16),
  `CONS_NAME` varchar(128),
  `ELEC_ADDR` varchar(256),
  `ORG_NO` varchar(16),
  `CONTRACT_CAP` decimal(12,2),
  PRIMARY KEY (`CONS_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS `TMP_CONS_CHK`;
CREATE TABLE `TMP_CONS_CHK` (
  `CONS_NO` varchar(16) NOT NULL,
  `CONS_NAME` varchar(128),
  `CHK_FLAG` varchar(2),
  PRIMARY KEY (`CONS_NO`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
