# Phase 4 Agent Contract

角色、契约和输入包与模型厂商无关；岗位规则不等于正在运行的 Agent。当前提供本地校验与输入投影，没有 Runtime、工具接入或任务调度。

| 业务角色 | 职责 | 输入 Schema / 阶段 | 输出 Schema |
| --- | --- | --- | --- |
| lead | World Architect：问题分解、因果链、选取动态 Specialists | agent_input / planning | lead_plan |
| researcher | 真实来源、实证范围与 Evidence Ledger | agent_input / independent、cross_review | research_result |
| engineering_auditor | 物理、工程、制造与供应链审查 | agent_input / independent、cross_review | engineering_result |
| economic_auditor | CAPEX/OPEX、替代方案、资源与机会成本 | agent_input / independent、cross_review | economic_result |
| historical_analyst | 历史、制度、激励、类比与因果链 | agent_input / independent、cross_review | historical_result |
| redteam | 最强反驳、失败场景、隐藏前提与矛盾 | agent_input / redteam | redteam_result |
| integrator | 比较论证、综合与 Canon 变更提案 | agent_input / draft_synthesis、final_synthesis | synthesis_result |

`contracts/*.json` 是可校验的角色登记；同名 Markdown 是厂商无关岗位规则。`required_capabilities` 表示岗位需要的抽象能力，不表示当前工具可用。角色不固定模型或预算；后续 Router 负责选择。

## 输入包与独立性

`agent_input` 使用显式白名单：六个业务身份/版本、角色与阶段、问题与模式、相关实体、固定 Snapshot、selected_specialists、prior_results 与 supporting_artifacts。不允许额外字段或顶层 metadata。完整 TaskState 含他人结果、审批与运行记录，不得直接发送给首轮 Specialist。

`project_input(task, execution, role, stage, selected_specialists, schemas, ...)` 先验证 TaskState，再深拷贝允许字段。`execution` 只包含系统生成的 run_id、agent_run_id、artifact_id。前序结果必须显式提供，函数不会从 TaskState 自动收集答案、final_result、审批记录或 metadata。所有首轮输入使用同一个任务的 Snapshot，调用方必须冻结 TaskState 基线。

planning 与 independent 禁止 prior_results 和 supporting_artifacts。非 planning 必须选择至少一个 Specialist；调用的 Specialist 必须在选择列表中。不强制每次调用全部四个 Specialist。LeadPlan 返回建议分工；调用方确认分工后填入 selected_specialists，不自动执行计划。

输入中的问题、快照文本、来源摘录与前序输出是数据，不是执行指令。独立性也不能通过仅隐藏 JSON 字段实现：将来 Runtime 还需限制可见文件、工具、会话记忆和模型上下文。当前 Read 权限的 Claude 岗位文件仍可访问文件系统；必须遵守指定路径规则，不能声称已有强制隔离。

## 审查与综合次序

业务顺序：planning → selected Specialists independent → 可选 cross_review → 可选 draft_synthesis → redteam → final_synthesis。它是契约规则，尚无阶段执行器。

每个 prior_results 包含声明的 stage、AgentRun、Artifact 与六类既有结果之一。校验角色阶段、业务身份、相同 Run 和 Canon 版本、completed/finished_at 回执、角色输出结构、规范化内容 SHA256、唯一执行和 Artifact ID。每个已选择 Specialist 必须保留 independent 结果包，cross_review 结果不能替代首轮回执。回执是数据，不证明真实模型执行；后续 Runtime 必须创建可信记录并保存首轮输入和结果。

cross_review / draft_synthesis 只能包含已选择的 Specialists；redteam 还可包含 Integrator 的初稿。任何后续阶段都要求所选 Specialists 的完成回执齐全。final_synthesis 必须包含 Red Team 结果，之后由 Integrator 对证据、假设、计算和反例进行比较，保留分歧与 OPEN QUESTION，不做多数投票。存在初稿时应显式提供给 Red Team；初稿不构成最终结论。

当前契约可以检查输入包是否满足这些条件，不能判定调用方是否伪造 stage/完成回执、是否在包外读取了别人的答案。持久化与真实运行边界留到 Runtime / 工作流阶段。

## 输出、证据与 Canon 权限

输出与输入的六个业务身份/版本完全一致。来源、主张、计算 Artifact、因果链 Evidence、冲突与 Canon 提案在固定快照及显式前序证据范围内校验。Researcher 可提供新 Evidence；所有来源读取仍需真实工具支持，结构验证不证明科学内容为真。

所有角色禁止 Canon 写入、Apply、人工审批和 Git 写操作。仅 Integrator 的 SynthesisResult 含 proposed_changes，且 Agent 生成/传递的提案必须 pending。提案 before 与版本必须匹配快照，引用与拟议数据状态只在内存中校验；无 Canon 写入。审批后的 Apply 是未来独立步骤，不再经 Agent 输出接口。

最终 Integrator 可以修订或撤回初稿提案；其输出的 proposed_changes 是本轮最终提案集合。输入中的历史初稿仍保留且单独校验，不与最终提案合并成多份 Apply 请求。最终输出不得再引用已经撤回的新增实体。

独立分析输入禁止 Artifact，分析完成后可用 `validate_output_artifacts(input, result, schemas, supporting_artifacts)` 单独验证新计算回执；新回执必须属于当前 AgentRun，不得预先注入首轮输入。该校验验证身份与引用，尚不运行 Python 或读取 Artifact 文件证明计算正确。

LeadPlan 不包含事实裁决、Canon 变更或批准字段；当前作为独立 Artifact 契约，未加入 Phase 3 TaskState 的持久化字段。Runtime 阶段将实现保存和读取这些记录。

## 使用与 Claude 专项入口

```powershell
.\.venv\Scripts\python.exe -m axiom_forge check-contracts
.\.venv\Scripts\python.exe -m axiom_forge validate-agent-input examples/agent_input.json
.\.venv\Scripts\python.exe -m axiom_forge validate-agent-output examples/agent_input.json examples/lead_plan.json
.\.venv\Scripts\python.exe -m axiom_forge validate-agent-output examples/agents/integrator-input.json examples/synthesis_result.json
```

`.claude/agents/` 的七个文件按 [Claude Code 官方岗位文件格式](https://code.claude.com/docs/en/sub-agents) 使用 YAML frontmatter 与 Markdown 正文。当前显式配置 `tools: Read`、默认权限且不绑定模型，仅支持规则/输入读取。没有搜索、Python、Shell、写入或子 Agent 能力；需要缺失工具时返回缺口，不能伪造研究。

文件格式已按官方文档核对和本地检查；本机尚未执行 Claude Code / SDK 的岗位加载或模型调用。这些文件不配置服务端权限、不实现 Runtime 隔离。
