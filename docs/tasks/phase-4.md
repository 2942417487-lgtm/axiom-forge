# Phase 4 工程任务

用户授权：先合并 PR #1、#2，再推进 Phase 4。两项 PR 已合并至 main；本阶段基于 main 的 `feat/phase-4-agent-contracts` 开发，交付新的 PR 待审查。

范围来自实施执行清单 Phase 4 与最新设计总纲第 6、11、16 节：

- 定义 Lead、Researcher、Physics / Engineering Auditor、Economic Auditor、Historical / Institutional Analyst、Red Team、Integrator / Canon Manager 七个厂商无关的角色。
- 明确每个角色的 Input / Output Schema，补充 Lead 规划结果与受限输入包。
- 实现输入投影和本地契约校验：同一 Snapshot、首轮无他人结果、首轮全部完成后才交叉审查、Red Team 和综合。
- 复用 Phase 3 的六种结果结构；所有 Canon 变更只生成 pending ProposedCanonChange。
- 提供 `.claude/agents/` 专项岗位文件，不固定模型、不创建 SDK Adapter。
- 用正向与负向测试验证独立性、阶段门槛、身份、证据关系与提案边界。

交付不包含真实 Agent 执行、Tool Layer、Runtime、路由、任务持久化、人工批准认证或 Canon Apply。文件与输入投影不能替代运行时权限隔离；不得声称已完成真实多 Agent 研究。
