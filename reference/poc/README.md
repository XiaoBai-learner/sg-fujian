# 既有溯源引擎参考

这里只保存可复用的 PoC 引擎、生成数据和回归测试，不是正式应用入口。旧页面、角色登录接口和部署脚本已从活动项目移出。

- `sgtrace/`：结构采集、SQL 血缘、领域词表、本体构建、OntoWing 校验与导出、SemanticIndex、映射实跑、规则推理和受控智能体工具。
- `datagen/`：确定性测试数据生成器；只会重建本目录的 `data/`。
- `data/inputs`：流水线输入；`data/gold` 仅供评测；`data/sandbox` 为生成的 SQLite。
- `tests/`：引擎与数据自洽性回归，包含 R2RML 与规则 SQL 核对。

在仓库根目录运行：

```bash
.venv/bin/python -m pytest reference/poc/tests -q
.venv/bin/python reference/poc/datagen/build.py
```

OntoWing 默认从仓库旁边的 `../ontowing/backend` 读取，可用 `ONTOWING_BACKEND` 覆盖。兼容旧数据路径的环境配置只用于参考引擎。

迁移时把不依赖演示数据和全局状态的能力提取到正式模块或 `backend/src/sgtrace_app/integrations/`，带上对应测试。正式应用不得导入此目录的全局运行状态，也不能将合成数据、固定库名和营销词表当作通用运行配置。
