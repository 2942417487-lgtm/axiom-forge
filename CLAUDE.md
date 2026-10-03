# Claude Runtime 项目操作说明

先完整阅读根目录 `AGENTS.md`，遵守其中的用户确认、事实分层、Canon 审批、密钥安全和 Git 审查规则。本文件补充 Claude 的操作方式。

## 当前阶段

当前已实现 Phase 0–3 基础：Canon/Evidence Schema、分域数据目录、离线校验与自包含 Snapshot。Claude Agent SDK Adapter、MCP 配置、专项 Agent 文件和审批工作流尚未实现。不得假装调用这些尚不存在的能力。

## 开始工作

1. 阅读 `README.md`、`docs/phase-1-3.md` 与相关 `docs/tasks/` 任务，确认已实现内容和当前授权范围。
2. 执行 `git status --short --branch`，确认分支及用户未提交修改；重要变更在工作分支进行。
3. 要求存在歧义时先询问用户；不得自行扩展到后续阶段。
4. 涉及软件实现时，先记录范围明确的 issue 或本地任务说明，再修改代码。

## 后续研究流程

按任务检索相关 Canon、Evidence 与时间线，使用 `python -m axiom_forge snapshot create` 固定自包含版本，记录 canon_version 与 snapshot_id；用 `snapshot verify <文件>` 验证。当前正式 world 为空，应由作者逐步建立；不得拿 examples/ 测试数据替代设定。后续 Specialist 首轮独立分析，然后交叉审查、Red Team 和综合。

使用运行环境实际提供的搜索、来源读取和计算工具；记录来源与实算结果。工具不可用时报告缺口，不得用参数记忆冒充搜索、文献读取或计算。

Canon 变更应提出受影响实体、变更理由、证据、依赖、冲突和不确定性，等待验证与人工批准，再通过独立的应用步骤更新。不得静默编辑 Hard Canon。

## 验证与交付

使用以下检查（先按 README 安装依赖，命令在项目根目录执行）：

```powershell
git diff --check
git check-ignore .env .env.local .venv/ignore-check node_modules/ignore-check tmp/ignore-check
git ls-files .env.example
.\.venv\Scripts\python.exe -m axiom_forge check-schemas
.\.venv\Scripts\python.exe -m axiom_forge validate-world
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

测试仅覆盖已实现的基础数据工具，不证明 Agent Runtime、人工审批或完整研究应用已经实现。后续代码阶段应根据项目实际配置运行测试；不得虚构测试通过记录。

检查待提交文件清单与差异，在工作分支提交。推送至私有仓库后交付 review；合并由用户最终控制。交付说明包含已完成内容、检查结果和仍未实现的功能。
