# Claude Runtime 项目操作说明

先完整阅读根目录 `AGENTS.md`，遵守其中的用户确认、事实分层、Canon 审批、密钥安全和 Git 审查规则。本文件补充 Claude 的操作方式。

## 当前阶段

Phase 0–6 已合并。Phase 7–9 功能分支增加可信宿主路由、模型分工与四种有界模式入口；使用见 routing/README.md、modes/README.md、docs/phase-7-9.md。Claude Adapter 复用官方 SDK，关闭原生工具、共享会话、项目/用户设置与外部 MCP；`.claude/agents/` 手工岗位入口仍仅 Read。模式整轮通过离线验收，四款模型的真实合成接入校验单独记录；完整 TaskManager、审批和 Canon 更新尚未实现。

## 开始工作

1. 阅读 `README.md`、`docs/phase-5.md`、`tools/README.md`、`agents/README.md` 与相关 `docs/tasks/` 任务，确认已实现内容和当前授权范围。
2. 执行 `git status --short --branch`，确认分支及用户未提交修改；重要变更在工作分支进行。
3. 要求存在歧义时先询问用户；不得自行扩展到后续阶段。
4. 涉及软件实现时，先记录范围明确的 issue 或本地任务说明，再修改代码。
5. 接入或新增工具前，按 AGENTS.md 优先真实搜索现成 MCP Tools 或 skills，评估适用性并记录选型；满足要求时优先复用，存在明确缺口时再自研。

## 后续研究流程

按任务检索相关 Canon、Evidence 与时间线，使用 `python -m axiom_forge snapshot create` 固定自包含版本，记录 canon_version 与 snapshot_id；用 `snapshot verify <文件>` 验证。当前正式 world 为空，应由作者逐步建立；不得拿 examples/ 测试数据替代设定。调用方用受限 agent_input，禁止向首轮 Specialist 发送完整 TaskState、他人答案或 Artifact；选择的首轮全部完成后才交叉审查、Red Team 和综合。输入校验不替代未来 Runtime 的文件、工具和上下文隔离。

使用运行环境实际提供的搜索、来源读取和计算工具；记录来源与实算结果。工具不可用时报告缺口，不得用参数记忆冒充搜索、文献读取或计算。

工程/经济岗位还应阅读 calculations/README.md，按 CalculationRequest 交付计算需求。Read 手工岗位返回完整 JSON；受控 Runtime 自动保存通过身份/结构检查的独立请求文件。只有宿主授权并登记脚本时才可使用 Python 工具，默认关闭且登记表为空；没有通用计算执行器或 MATLAB Adapter。不得声称未执行的 Python/MATLAB 或文件写入；未来程序必须复用模型/版本与通用参数接口，禁止写死本次参数。

Canon 变更应提出受影响实体、变更理由、证据、依赖、冲突和不确定性，等待验证与人工批准，再通过独立的应用步骤更新。不得静默编辑 Hard Canon。

## 验证与交付

使用以下检查（先按 README 安装依赖，命令在项目根目录执行）：

```powershell
git diff --check
git check-ignore .env .env.local .venv/ignore-check node_modules/ignore-check tmp/ignore-check
git ls-files .env.example
.\.venv\Scripts\python.exe -m axiom_forge check-schemas
.\.venv\Scripts\python.exe -m axiom_forge validate-world
.\.venv\Scripts\python.exe -m axiom_forge check-contracts
.\.venv\Scripts\python.exe -m axiom_forge validate-agent-output examples/agent_input.json examples/lead_plan.json
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

测试覆盖本地数据工具与角色契约边界，不证明真实 Agent Runtime、Claude 岗位加载、人工审批或完整研究应用已经实现。后续代码阶段应根据项目实际配置运行测试；不得虚构测试通过记录。

检查待提交文件清单与差异，在工作分支提交。推送至私有仓库后交付 review；合并由用户最终控制。交付说明包含已完成内容、检查结果和仍未实现的功能。
