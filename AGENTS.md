# AGENTS.md

福建电力"业务字段溯源"PoC。

## 一期范围

输入：业务人员的一封取数邮件，内容是截图 OCR 文本加上要问的中文字段名。
输出：每个字段对应的源系统原表和原表字段（`schema.TABLE.COLUMN`），附带置信度和证据。

- 不做 OCR，客户自己有 OCR 能力。输入直接就是 OCR 文本。
- 不做码值翻译，比如 `01` 对应"柜台"。
- 不做数据治理和合并。同义字段只作为可接受的等价答案。
- 只做一个业务领域：营销域，福州试点。电力系统按领域分别建本体再组合，不做全域本体。

技术路线：DDL + 热点 SQL + DataWorks 血缘 + 样例值 → 领域本体（OWL/SKOS，带中文标签和同义词）+ R2RML 映射。
查询时的链路：截图字段名 → 本体属性（标签/同义词检索 + 大模型重排）→ R2RML 定位物理表和字段。
如果截图来自中台报表页，还要沿血缘从 ADS 追到 DWS、DWD、ODS，最后到源表。

## 目录

```
datagen/            测试数据生成器（确定性，固定随机种子）
  sources.py        源系统表结构：yx186 营销(Oracle)、cjxt 采集(Oracle)、kf95598 客服(MySQL)
  gen.py            样例数据（福州 7 区 21 供电所，600 户，2025 全年）
  dataplatform.py   中台 ODS/DWD/DWS/ADS 表与 ETL（拼音缩写命名）
  pages.py          业务页面（截图来源）与 20 个需求
  hotsql.py         热点 SQL 日志
  lineage.py        字段级血缘推导与追溯
  ontology.py       真值本体与 R2RML 生成
  build.py          入口
data/
  inputs/           只放客户能提供的东西，PoC 流水线只能读这里
    ddl/source/<系统>/schema.sql   源系统 DDL（注释部分缺失：采集约 75% 缺，营销约 25% 缺）
    ddl/platform/schema.sql        中台 DDL（MaxCompute）
    samples/                       每表前 200 行样例 CSV
    hot_sql/query_log.csv          24 条热点 SQL（含执行次数）
    dataworks/lineage_export.csv   血缘导出（不完整：部分任务整体缺失，其余随机丢 20%）
    dataworks/tasks/*.sql          DataWorks 任务 SQL（完整，可自行解析补全血缘）
    requests/R*.json               需求邮件 + 截图 OCR 文本；_index.csv 为清单
  gold/             标准答案，流水线禁止读取，只用于评测
    answers.csv                    90 个待溯源字段的答案（source_columns + acceptable_equivalents）
    ontology_marketing.ttl         参考本体（15 个类）
    mapping_marketing.r2rml.ttl    参考 R2RML
    lineage_full.csv / pages.csv / table_catalog.csv / concept_map.csv
  sandbox/          SQLite 库（gitignore，可重建），用于值校验、执行 SQL、R2RML
tests/test_dataset.py   数据集自洽性测试
docs/review_checklist.md  mock 数据人工审阅清单（待用户确认的口径问题）
```

## 命令

```bash
python3 datagen/build.py          # 重新生成 data/（会先删除整个 data/）
python3 -m pytest tests -q        # 重新生成并校验
```

依赖：Python 3.12、rdflib、pytest。sandbox 中 `platform.db` 以 ATTACH 方式挂载 `yx186`、`cjxt`、`kf95598`，SQL 里用 `yx186."C_CONS"` 访问源表。

## 数据集里刻意设置的难点

- 页面标签和 DDL 注释不一致，比如"户号""客户编号""用户编号"指的是同一个字段。
- 中台用拼音缩写命名（`hh`、`ljqfje`），ADS 和 DWD 的命名也不统一（`yhbh` 对应 `hh`）。
- 有派生和聚合字段：欠费金额 = 应收 − 实收；负载率来自曲线和合同容量。答案是多个源字段。
- 同一概念分布在多个系统：工单 `CUST_NO`、采集 `CONS_NO`、营销 `CONS_NO`。
- 有噪声表：备份表、临时表、旧版本表。热点 SQL 很少访问它们，答案里也不会出现。
- 有 8 个低上下文需求：截图里没有页面标题和菜单路径。

## 评测口径

- 每个字段的严格命中：预测集合等于 `source_columns`。
- 宽松命中：预测落在 `source_columns` 或 `acceptable_equivalents` 中。
- 按 `derivation`（direct / derived / aggregated）和需求的 `context_level` 分组统计。

## 约定

- 修改 datagen 后必须重新跑 `pytest`。测试保证答案字段真实存在于 DDL，并且直接映射的字段能通过值校验。
- 新增业务领域时，单独建一套 `sources_<领域>.py` 和本体文件，不要并入营销域。
- 不要提交真实客户数据。所有姓名、电话、编号都是生成的。
