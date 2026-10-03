# Phase 4 交付记录

用户已授权合并 Phase 0 的 PR #1 与 Phase 1–3 的 PR #2，再推进 Phase 4。两项 PR 已合并，本阶段在 `feat/phase-4-agent-contracts` 上实现，交付新的 PR 待审查。

## 清单验收

- [x] World Architect / Lead。
- [x] Researcher。
- [x] Physics / Engineering Auditor。
- [x] Economic Auditor。
- [x] Historical / Institutional Analyst。
- [x] Red Team。
- [x] Integrator / Canon Manager。
- [x] 七个角色明确输入/输出 Schema；新增 AgentContract、AgentInput、LeadPlan，复用六类结果。
- [x] 角色禁止直接修改 Hard Canon 和其他 Canon；提案必须 pending，只做内存验证。
- [x] 受限输入投影：首轮无他人结果、Artifact 或 TaskState metadata，基于同一固定 Snapshot。
- [x] 所有已选择首轮完成后才允许交叉审查、Red Team、初稿与最终综合；最终综合必须有 Red Team。
- [x] `.claude/agents/` 七个专项岗位文件，不固定模型，仅 Read，缺失来源/计算工具时报告缺口。

范围与验收细则见 [工程任务](tasks/phase-4.md)、[Agent 契约](../agents/README.md)。

## 已执行验证

74 项 unittest 全部通过：原有 39、角色契约 29、后续计算协议补充 6。覆盖七角色输入/输出、同快照深拷贝、首轮答案和 Artifact 泄露拒绝、动态角色选择、首轮完成门槛、Red Team 门槛、角色/身份/阶段/时间/哈希、伪来源、未知引用、Lead 权限、pending 提案、初稿提案修订/撤回、后置计算回执与无 world 写入；补充覆盖待执行请求、类型/角色错配、未执行回执和未实现模型伪装。

28 个 Schema 与本地引用自检通过；七个角色登记及规则文件检查通过；生产 world 校验仍仅含 world.json；完整综合输入/输出样例通过。原有 39 项数据、快照和 CLI 测试继续通过。

Claude 岗位的 frontmatter 按官方格式核对，测试检查七个唯一岗位名、必需字段、Read 与 default 权限；尚未安装或执行 Claude Code / SDK 加载验收。单纯文本、结构与契约测试不等于模型调用成功。

## 当前边界

用户追加了工程/经济角色的程序化 cost 计算与请求交付要求，明确本轮只补指导规则、通用格式与接口规范。已补四份指导文件、CalculationRequest/Model/Result、两岗位 calculation_protocol 及可选 calculation_requests 输出字段；Python/MATLAB 执行程序留待后续。详见 [计算协议](../calculations/README.md) 与 [补充任务](tasks/reusable-calculations.md)。

Phase 5 的 Web/Search、论文/PDF 与计算工具接入，Phase 6 的 Runtime，后续 Router、调度、阶段持久化、真实多 Agent 上下文隔离、人工审批认证、Canon Apply 与 LangGraph 均未实施。当前没有模型 API 调用或真实研究结论；正式 world 保持为空。

stage、完成回执、来源读取记录与 Artifact 校验可拒绝不一致数据，不能认证其实际执行。将来 Runtime 必须控制可见文件/工具/上下文，冻结基线并保存可信首轮记录；Claude 的 Read 岗位规则不能替代这些强制措施。

当前阶段 PR 等待人工审查。此前 PR #1、#2 的合并授权不适用于该 PR。
