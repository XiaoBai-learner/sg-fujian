-- 本地 MySQL 替身库：kf95598（只有表结构）
CREATE DATABASE IF NOT EXISTS `kf95598` DEFAULT CHARACTER SET utf8mb4;
USE `kf95598`;

DROP TABLE IF EXISTS `t_kf_workorder`;
CREATE TABLE `t_kf_workorder` (
  `APP_NO` varchar(32) NOT NULL COMMENT '工单号',
  `ACCEPT_TIME` datetime COMMENT '受理时间',
  `BUSI_TYPE` varchar(4) COMMENT '业务类型 01故障报修 02咨询 03投诉 04意见建议',
  `CUST_NO` varchar(16) COMMENT '客户编号',
  `CUST_NAME` varchar(128) COMMENT '客户名称',
  `CONTACT_TEL` varchar(32) COMMENT '联系电话',
  `ACCEPT_CONTENT` varchar(1024) COMMENT '受理内容',
  `HANDLE_ORG` varchar(16) COMMENT '处理单位',
  `HANDLE_STATUS` varchar(2) COMMENT '状态',
  `FINISH_TIME` datetime COMMENT '办结时间',
  `SATISFY_CODE` varchar(2) COMMENT '满意度',
  PRIMARY KEY (`APP_NO`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='95598工单';

DROP TABLE IF EXISTS `t_kf_visit`;
CREATE TABLE `t_kf_visit` (
  `VISIT_ID` bigint NOT NULL,
  `APP_NO` varchar(32) COMMENT '工单号',
  `VISIT_TIME` datetime COMMENT '回访时间',
  `VISIT_RESULT` varchar(256) COMMENT '回访结果',
  `SATISFY_SCORE` decimal(4,1) COMMENT '评分',
  PRIMARY KEY (`VISIT_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单回访';
