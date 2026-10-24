# Phase 7–9：模型登记、路由与世界观工作模式

用户于 2026-10-06 授权合并 PR #5，并继续至 Phase 9。PR #5 已合并，合并提交为 `ab881bdd7812f21d0ea34d89a38a599f40479d78`；本阶段从该 main 建立 `feat/phase-7-9-routing-modes`，交付待审查 PR，不自动合并。

## 已明确的阶段要求

- Phase 7：建立 Model Registry、Routing Policy 与 Escalation Policy；登记总纲模型与 legacy pool，角色与厂商、模型解耦。
- Phase 8：初始模型分工可配置，按项目评测调整；重要任务的主分析与 Red Team 使用不同模型家族。
- Phase 9：情景模拟、直接质疑、圆桌、法庭四种模式；共用固定 Canon Snapshot、Evidence 与岗位 Schema。
- 延续现有权限边界：研究岗位不得审批、应用 Canon 或修改 Git；工程 Runtime 不承担研究角色。
- 通用计算执行器、MATLAB 执行器仍留给后续；工程/经济 Auditor 保留规范 CalculationRequest 与已审核 Python 脚本调用能力。

## 用户确认的执行边界

用户已回答两项异步问题并确认费用记录。

1. 启用并联调 Sonnet 5.5、GPT-6.1 Sol、Opus 5.5、GPT-6 Luna；Fable 5.1、GPT-6 Astra、DeepSeek 暂不启用，legacy 只登记。
2. 四种模式实现基于现有 Runtime 的可运行入口，包含独立分析、交叉审查、Red Team、综合；模式整轮先做离线验收。
3. Claude/OpenAI 经现有 ZenMux 端点，累计费用上限 2 美元，包含 Phase 6；用户确认 Phase 6 最终累计实际费用 $0.1049。四款模型接入 smoke 与整轮模式的验收分开。

本轮联调按新授权执行，不将模式入口的可用性当作整轮付费调用授权。现有 ZenMux Key 不得发送至厂商直连地址。

## 接口核对结果

- TaskState 已有四种 `task_type`，可沿用业务标识与快照。
- 岗位契约已约束首轮无他人结果；全部所选 Specialist 完成后才能交叉审查、综合；最终综合须包含 Red Team。
- AgentRuntime 已负责单次会话、工具绑定、结果校验与追加保存；路由层应选用已配置 Runtime，不重写厂商 SDK 执行循环。
- 历史岗位已有 causal_chains；本阶段新增 ModeAnalysis，校验情景因果阶次、挑战前提、四岗位观点与四领域举证。
- Phase 10 的完整 TaskManager、人工审批、Canon 更新和 Phase 11 的恢复机制不在当前授权范围内。

## 现成能力检索与资料

2026-10-06 已真实检索并读取下列官方文档；模型公开规格不等于 Axiom Forge Runtime 联调或本项目任务评测通过。

- [LiteLLM Router](https://docs.litellm.ai/docs/routing)：已有成本、延迟、负载等路由与回退能力，可作为供应商网关层候选。其文档描述的能力不能直接替代本项目按 Canon 重要性、独立分析契约与跨家族审查进行的业务选择。是否引入须根据确定后的范围评估，当前没有安装或部署。
- [Claude 模型总览](https://platform.claude.com/docs/en/models/overview)、[Opus 5.5](https://platform.claude.com/docs/en/models/opus-5-5/overview)：确认当前模型 ID、上下文和输出上限；Opus/Fable 的强制工具调用与关闭 thinking 存在兼容性限制，不能仅改模型名便标为已验证。
- [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra)、[GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna)：确认模型 ID、Responses 与函数调用支持、上下文和输出上限；登记其原生工具支持不授予研究 Runtime 新工具权限。
- [DeepSeek 更新日志](https://api-docs.deepseek.com/updates/)：公开 API 的当前 Flash 名称为 `deepseek-flash`；第三方网关 Slug 与本项目 Adapter 兼容性仍需单独确认，不从原生名称推断。

初始岗位偏好来源于用户设计总纲，须标为待项目评测的策略。价格与模型规格必须记录核对日期和来源；厂商直连价格不能当作 ZenMux 实际计费，既有成功 smoke 也不能当作完整模式验收。

## 后续验收要求

离线检查覆盖禁用/未验证模型过滤、上下文/工具/预算约束、升级终止与 OPEN QUESTION、不同家族审查、四种模式的输入输出及首轮信息隔离。真实调用只按用户明确授权的模型、端点和预算执行。交付记录见 docs/development/history/phases/phase-7-9.md，最后交付可审查的分支差异与 PR。
