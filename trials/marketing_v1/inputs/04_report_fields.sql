-- 补充的页面展示查询：根据原 dataplatform.py 列注释生成中文投影，不含标准答案。

-- 客户基本信息；显示名来自既有中台列注释，并非真实客户日志。
SELECT `khbs` AS `客户标识`, `hh` AS `户号`, `hm` AS `户名`, `ydsz` AS `用电地址`, `gddw_bm` AS `供电单位编码`, `gddw_mc` AS `供电单位名称`, `hylb` AS `行业类别`, `ydlb` AS `用电类别`, `gddy` AS `供电电压`, `htrl` AS `合同容量`, `yhzt` AS `用户状态`, `lhrq` AS `立户日期`, `xhrq` AS `销户日期`, `lxr` AS `主联系人`, `lxdh` AS `联系电话` FROM `sgtrace_trial_platform`.`dwd_yx_kh_jbxx`;

-- 计量点信息；显示名来自既有中台列注释，并非真实客户日志。
SELECT `jldbs` AS `计量点标识`, `jldbh` AS `计量点编号`, `jldmc` AS `计量点名称`, `hh` AS `户号`, `dnbzcbh` AS `电能表资产编号`, `ccbh` AS `出厂编号`, `sccj` AS `生产厂家`, `zhbl` AS `综合倍率`, `zbrq` AS `装表日期`, `jldzt` AS `计量点状态` FROM `sgtrace_trial_platform`.`dwd_yx_jld_xx`;

-- 应收电费明细；显示名来自既有中台列注释，并非真实客户日志。
SELECT `ysbs` AS `应收标识`, `hh` AS `户号`, `dfny` AS `电费年月`, `jsdl` AS `结算电量`, `ysje` AS `应收金额`, `ssje` AS `实收金额`, `qfje` AS `欠费金额`, `wyj` AS `违约金`, `jqbz` AS `结清标志`, `fxrq` AS `发行日期` FROM `sgtrace_trial_platform`.`dwd_yx_df_ysmx`;

-- 缴费明细；显示名来自既有中台列注释，并非真实客户日志。
SELECT `jfbs` AS `缴费标识`, `hh` AS `户号`, `ysbs` AS `应收标识`, `jfsj` AS `缴费时间`, `jfje` AS `缴费金额`, `jffs` AS `缴费方式`, `sfdw` AS `收费单位` FROM `sgtrace_trial_platform`.`dwd_yx_jf_mx`;

-- 抄表示数明细；显示名来自既有中台列注释，并非真实客户日志。
SELECT `cbbs` AS `抄表标识`, `jldbh` AS `计量点编号`, `hh` AS `户号`, `cbny` AS `抄表年月`, `sccbsz` AS `上次示数`, `bccbsz` AS `本次示数`, `cjdl` AS `抄见电量`, `cbrq` AS `抄表日期` FROM `sgtrace_trial_platform`.`dwd_yx_cbsz`;

-- 测量点日电量；显示名来自既有中台列注释，并非真实客户日志。
SELECT `cldbs` AS `测量点标识`, `hh` AS `户号`, `dnbzcbh` AS `电能表资产编号`, `sjrq` AS `数据日期`, `zxygdl` AS `正向有功电量`, `zxwgdl` AS `正向无功电量`, `zxygsz` AS `正向有功示数` FROM `sgtrace_trial_platform`.`dwd_cj_rdl`;

-- 测量点负荷曲线；显示名来自既有中台列注释，并非真实客户日志。
SELECT `cldbs` AS `测量点标识`, `hh` AS `户号`, `dnbzcbh` AS `电能表资产编号`, `sjsj` AS `数据时间`, `yggl` AS `有功功率`, `wggl` AS `无功功率` FROM `sgtrace_trial_platform`.`dwd_cj_fhqx`;

-- 采集终端信息；显示名来自既有中台列注释，并非真实客户日志。
SELECT `zdbs` AS `终端标识`, `zdzcbh` AS `终端资产编号`, `zdlx` AS `终端类型`, `zddz` AS `终端地址`, `gddw_mc` AS `供电单位名称`, `yxzt` AS `运行状态`, `tyrq` AS `投运日期` FROM `sgtrace_trial_platform`.`dwd_cj_zd_xx`;

-- 95598工单明细；显示名来自既有中台列注释，并非真实客户日志。
SELECT `gdbh` AS `工单编号`, `slsj` AS `受理时间`, `ywlx` AS `业务类型`, `hh` AS `户号`, `khmc` AS `客户名称`, `lxdh` AS `联系电话`, `slnr` AS `受理内容`, `cldw` AS `处理单位`, `clzt` AS `处理状态`, `bjsj` AS `办结时间`, `hfpf` AS `回访评分`, `hfjg` AS `回访结果` FROM `sgtrace_trial_platform`.`dwd_kf_gd_mx`;

-- 客户欠费汇总；显示名来自既有中台列注释，并非真实客户日志。
SELECT `hh` AS `户号`, `qfys` AS `欠费月数`, `ljqfje` AS `累计欠费金额`, `ljwyj` AS `累计违约金`, `zzqfny` AS `最早欠费年月` FROM `sgtrace_trial_platform`.`dws_yx_kh_qf_hz`;

-- 客户缴费汇总；显示名来自既有中台列注释，并非真实客户日志。
SELECT `hh` AS `户号`, `zjjfsj` AS `最近缴费时间`, `ljjfje` AS `累计缴费金额`, `jfcs` AS `缴费次数` FROM `sgtrace_trial_platform`.`dws_yx_kh_jf_hz`;

-- 客户月用电汇总；显示名来自既有中台列注释，并非真实客户日志。
SELECT `hh` AS `户号`, `ny` AS `年月`, `ydl` AS `月用电量`, `ysdf` AS `月应收电费` FROM `sgtrace_trial_platform`.`dws_yx_kh_ydl_y`;

-- 工单月度统计；显示名来自既有中台列注释，并非真实客户日志。
SELECT `cldw` AS `处理单位`, `tjyf` AS `统计月份`, `gdzs` AS `工单总数`, `tsgds` AS `投诉工单数`, `bxgds` AS `报修工单数`, `tsl` AS `投诉占比`, `pjmyd` AS `平均回访评分` FROM `sgtrace_trial_platform`.`dws_kf_gd_tj_y`;

-- 客户日负荷统计；显示名来自既有中台列注释，并非真实客户日志。
SELECT `hh` AS `户号`, `rq` AS `日期`, `zdfh` AS `日最大负荷`, `pjfh` AS `日平均负荷` FROM `sgtrace_trial_platform`.`dws_cj_kh_fh_r`;

-- 客户档案查询；显示名来自既有中台列注释，并非真实客户日志。
SELECT `yhbh` AS `用户编号`, `yhmc` AS `用户名称`, `ydsz` AS `用电地址`, `gddw` AS `供电单位`, `ydlb` AS `用电类别`, `hylb` AS `行业类别`, `dydj` AS `电压等级`, `htrl` AS `合同容量`, `yhzt` AS `用户状态`, `lhrq` AS `立户日期`, `lxr` AS `联系人`, `lxdh` AS `联系电话` FROM `sgtrace_trial_platform`.`ads_yx_khda_cx`;

-- 电费欠费明细；显示名来自既有中台列注释，并非真实客户日志。
SELECT `hh` AS `户号`, `hm` AS `户名`, `gddw` AS `供电单位`, `dfny` AS `电费年月`, `ysdf` AS `应收电费`, `ssdf` AS `实收电费`, `qfje` AS `欠费金额`, `wyj` AS `违约金`, `fxrq` AS `发行日期` FROM `sgtrace_trial_platform`.`ads_yx_qfmx_cx`;

-- 客户360视图；显示名来自既有中台列注释，并非真实客户日志。
SELECT `hh` AS `户号`, `hm` AS `户名`, `ydsz` AS `用电地址`, `gddw` AS `供电单位`, `htrl` AS `合同容量`, `lxdh` AS `联系电话`, `qfys` AS `欠费月数`, `ljqf` AS `累计欠费`, `zjjfsj` AS `最近缴费时间`, `ljjf` AS `累计缴费` FROM `sgtrace_trial_platform`.`ads_yx_kh360`;

-- 月度用电分析；显示名来自既有中台列注释，并非真实客户日志。
SELECT `hh` AS `户号`, `hm` AS `户名`, `gddw` AS `供电单位`, `ydlb` AS `用电类别`, `ny` AS `年月`, `ydl` AS `月用电量`, `ysdf` AS `应收电费` FROM `sgtrace_trial_platform`.`ads_yx_ydl_fx`;

-- 95598工单查询；显示名来自既有中台列注释，并非真实客户日志。
SELECT `gdbh` AS `工单编号`, `slsj` AS `受理时间`, `ywlx` AS `业务类型`, `hh` AS `户号`, `khmc` AS `客户名称`, `lxdh` AS `联系电话`, `slnr` AS `受理内容`, `cldw` AS `处理单位`, `clzt` AS `处理状态`, `bjsj` AS `办结时间`, `hfpf` AS `回访评分` FROM `sgtrace_trial_platform`.`ads_kf_gd_cx`;

-- 工单统计看板；显示名来自既有中台列注释，并非真实客户日志。
SELECT `cldw` AS `处理单位`, `tjyf` AS `统计月份`, `gdzs` AS `工单总数`, `tsgds` AS `投诉工单数`, `bxgds` AS `报修工单数`, `tsl` AS `投诉占比`, `pjmyd` AS `平均满意度` FROM `sgtrace_trial_platform`.`ads_kf_gd_kb`;

-- 大客户负荷监测；显示名来自既有中台列注释，并非真实客户日志。
SELECT `hh` AS `户号`, `hm` AS `户名`, `gddw` AS `供电单位`, `htrl` AS `合同容量`, `rq` AS `日期`, `zdfh` AS `最大负荷`, `pjfh` AS `平均负荷`, `fzl` AS `负载率` FROM `sgtrace_trial_platform`.`ads_cj_dkh_fh`;
