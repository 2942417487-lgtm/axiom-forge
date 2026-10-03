# Phase 3–4 业务接口

所有 Schema 使用 [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)。`$id` 使用 `https://axiom-forge.invalid/schemas/` 作为命名空间，不是远端下载地址。Python 校验器仅使用本地 Registry，拒绝未登记的引用；实现依据 [jsonschema 官方引用说明](https://python-jsonschema.readthedocs.io/en/stable/referencing/)。

共 25 个 Schema：Phase 3 的 22 个基础结构，加 Phase 4 的 AgentContract、AgentInput、LeadPlan。角色使用相同严格输入包，根据 role/stage 做本地语义限制；详见 [Agent Contract](../agents/README.md)。

## 业务 ID 与执行边界

| 对象 | 标识 | 意义 |
| --- | --- | --- |
| World | WLD-UUIDv4 | 项目知识世界 |
| Task | TSK-UUIDv4 | 用户的业务问题，重复执行保留 Task ID |
| Run | RUN-UUIDv4 | 一次流程执行；重试整次流程应新建 Run |
| Agent Run | ARN-UUIDv4 | 某角色的一次运行；同角色多次运行各有独立 ID |
| Artifact | ART-UUIDv4 | 一份有身份、位置与内容哈希的结果 |
| Snapshot | SNP-UUIDv4 | 快照创建身份 |
| Canon Version | CANON-SHA256 | 快照内容版本 |
| Claim | CLM-UUIDv4 | 可追溯主张 |
| Evidence | EVD-UUIDv4 | 来源依据记录 |
| Canon Change | CHG-UUIDv4 | 变更提案 |

使用 `python -m axiom_forge new-id task` 等命令生成。厂商 Session/Thread ID 放在 metadata 中，不能替代这些业务 ID。角色只使用稳定业务名，当前没有模型绑定。

## TaskState

包含用户问题、讨论模式、生命周期、固定 Canon Snapshot、相关实体、六类分析输出、冲突、综合、提案、审批状态、最终结果，以及彼此分离的 runs、agent_runs、artifacts 列表。

所有输出包含 world_id、task_id、run_id、agent_run_id、artifact_id、canon_version。每个结果必须属于该 Task 的某个 Agent Run，角色与结果类型一致；结果规范化 JSON 的 SHA256 必须等于对应 Artifact 的 sha256。Run 的 Agent Run/Artifact 列表与实际记录一致。

时间、实体引用、结果来源链、计算 Artifact、历史因果链 Evidence、冲突和提案基线会做语义校验。研究结果可以引用固定快照中的实体或完整提案集里的新实体。提案的预期数据状态会在内存中整体校验，检查悬空引用与相互依赖；不会执行写入。同一实体的多个不同提案被拒绝，需先人工消除歧义。生命周期为 WAITING_APPROVAL 时审批状态必须 pending；COMMITTED 要求 approved、final_result 与已批准提案。当前只校验这些条件，尚无生命周期执行器或状态迁移管理。

## CanonChange

类型涵盖 add、update、delete：add 要求 before=null；update 要求 before/after 都存在；delete 要求 after=null。target_entity_id 必须与记录一致，before 必须等于任务快照中的原条目，base_canon_version 必须匹配。

approval 默认为显式 pending，不能携带伪装的批准回执。approved/rejected 要求 reviewer、reviewed_at 与 DEC 决策标识。该结构不是安全审批实现；当前工具不认证 reviewer、不执行 Canon 更新。Human Approval 与 Apply Runtime 留到 Phase 10。

## 验证层级

`check-schemas` 校验 Schema 与引用；`validate <schema> <file>` 校验单文件结构，对 TaskState、CanonSnapshot 与 AgentInput 额外校验语义；`validate-world` 校验整个 Ledger/实体引用网络。`check-contracts` 校验七个岗位登记与规则文件；`validate-agent-output <输入> <输出>` 绑定岗位、输入与输出身份，检查阶段、证据引用和 pending 提案。单条 Canon/Evidence 的结构验证不能替代 world/task 的跨记录检查。

日期时间限定大写 T/Z、秒字段与显式时区；不支持闰秒 60。URI 限定 HTTP(S)。额外字段被拒绝；扩展信息应放进明确的 metadata，不绕过必填业务字段。

每个非公共 Schema 都有 `examples/` 样例。样例只演示结构，不是研究结论，也不属于生产 world。
