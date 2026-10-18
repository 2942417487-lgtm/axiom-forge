# Phase 3–5 业务接口

所有 Schema 使用 [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)。`$id` 使用 `https://axiom-forge.invalid/schemas/` 作为命名空间，不是远端下载地址。Python 校验器仅使用本地 Registry，拒绝未登记的引用；实现依据 [jsonschema 官方引用说明](https://python-jsonschema.readthedocs.io/en/stable/referencing/)。

共 42 个 Schema：原有数据、计算、工具、路由与模式结构，Phase 10 增加 CanonReview/Approval/Commit，Phase 11 增加 TaskCheckpoint/EventRecord，项目元数据最小实现增加 ProjectMetadata。角色使用相同严格输入包，根据 role/stage 做语义限制；AgentInput 可选 mode_protocol=1.0，SynthesisResult 可选 mode_analysis，模式协议的最终综合强制后者存在。详见 [Agent Contract](../agents/README.md)、[Routing](../routing/README.md)、[模式](../modes/README.md)。

ToolResult 记录工具调用身份、状态、输出或错误、开始/结束时间与参数/payload 哈希。完成状态必须有 data 且无 error；失败、不可用或拒绝状态不得携带成功输出。静态样例不是实际调用；来源记录与权限边界见 [Tool Layer](../tools/README.md)。

工程/经济结果新增可选的 calculation_requests 字段，单独承载尚未执行的请求，保持既有 Phase 3 数据兼容。计算协议由 [可复用计算接口](../calculations/README.md) 定义，目前只有结构与基本状态校验，没有执行器或跨请求/结果语义关联验证；不得把新 Schema 当作已接入 Python/MATLAB。

## 业务 ID 与执行边界

| 对象 | 标识 | 意义 |
| --- | --- | --- |
| World | WLD-UUIDv4 | 项目知识世界 |
| Project | PRJ-UUIDv4 | 共享项目身份；仅已实现格式／生成，完整登记尚未实现 |
| Task | TSK-UUIDv4 | 用户的业务问题，重复执行保留 Task ID |
| Run | RUN-UUIDv4 | 一次流程执行；Phase 11 恢复延续原 Run，另起流程使用新 Run |
| Agent Run | ARN-UUIDv4 | 某角色的一次运行；同角色多次运行各有独立 ID |
| Artifact | ART-UUIDv4 | 一份有身份、位置与内容哈希的结果 |
| Snapshot | SNP-UUIDv4 | 快照创建身份 |
| Canon Version | CANON-SHA256 | 快照内容版本 |
| Claim | CLM-UUIDv4 | 可追溯主张 |
| Evidence | EVD-UUIDv4 | 来源依据记录 |
| Canon Change | CHG-UUIDv4 | 变更提案 |
| Checkpoint | CKP-UUIDv4 | 原子阶段记录 |
| Event | EVT-UUIDv4 | 关联 checkpoint 的业务事件 |

使用 `python -m axiom_forge new-id task` 等命令生成。厂商 Session/Thread ID 放在 metadata 中，不能替代这些业务 ID。角色只使用稳定业务名，当前没有模型绑定。

## TaskState

包含用户问题、讨论模式、生命周期、固定 Canon Snapshot、相关实体、六类分析输出、冲突、综合、提案、审批状态、最终结果，以及彼此分离的 runs、agent_runs、artifacts 列表。

所有输出包含 world_id、task_id、run_id、agent_run_id、artifact_id、canon_version。每个结果必须属于该 Task 的某个 Agent Run，角色与结果类型一致；结果规范化 JSON 的 SHA256 必须等于对应 Artifact 的 sha256。Run 的 Agent Run/Artifact 列表与实际记录一致。

时间、实体引用、结果来源链、计算 Artifact、历史因果链 Evidence、冲突和提案基线会做语义校验。研究结果可以引用固定快照中的实体或完整提案集里的新实体。预期数据状态在内存整体校验，拒绝悬空引用和同一实体多个不同提案。WAITING_APPROVAL 要求 pending。Phase 10 COMMITTED 状态的可选 canon_commit 绑定原 waiting TaskState 哈希、人工回执、提案哈希与提交 SHA，保留模型输出中的 pending 提案；旧格式仍兼容要求已批准提案的结构检查。通用验证器只验证结构/内容绑定，不验 Key、不证明 Git 发布。生命周期执行由宿主 TaskManager/CanonHost 控制；Phase 11 的 TaskCheckpoint 包含有效 TaskState、可信宿主游标、预留和关联事件，EventRecord 不向模型授予日志写入权。结构校验不能代替整条日志、文件、输入和签名恢复校验，见 [恢复说明](../docs/phase-11.md)。

## CanonChange

类型涵盖 add、update、delete：add 要求 before=null；update 要求 before/after 都存在；delete 要求 after=null。target_entity_id 必须与记录一致，before 必须等于任务快照中的原条目，base_canon_version 必须匹配。

approval 默认为显式 pending，不能携带伪装的批准回执。approved/rejected 要求 reviewer、reviewed_at 与 DEC 决策标识，但形状正确不等于已获批准。研究 Agent 只能产生 pending；Phase 10 CanonHost 只接受完整待审任务、单独的 canon_review、经交互确认的 canon_approval 与 HMAC 验证。canon_commit 记录批准后的独立分支提交，见 [人工控制入口](../docs/phase-10.md)。

## 验证层级

`validate project_metadata <文件>` 使用严格有界 UTF-8 JSON 读取，只验证四字段及其精确约束，安全诊断不回显来源值。`--world <外部目录> project check` 再检查 world/world.json 元数据和世界身份一致；不会创建本机绑定，不检查 Git／完整 Canon／秘密或授予登记／接受权。命令与局限见 [项目元数据只读检查](../docs/project-metadata-check.md)。CNV 对话标识与仓库操作回执 Schema 尚未登记；相关草案不等于可运行接口。

`check-schemas` 校验 Schema 与引用；`validate <schema> <file>` 校验单文件结构，对 TaskState、CanonSnapshot 与 AgentInput 额外校验语义；`validate-world` 校验整个 Ledger/实体引用网络。`check-contracts` 校验七个岗位登记与规则文件；`validate-agent-output <输入> <输出>` 绑定岗位、输入与输出身份，检查阶段、证据引用和 pending 提案。单条 Canon/Evidence 的结构验证不能替代 world/task 的跨记录检查。

日期时间限定大写 T/Z、秒字段与显式时区；不支持闰秒 60。URI 限定 HTTP(S)。额外字段被拒绝；扩展信息应放进明确的 metadata，不绕过必填业务字段。

原有非公共业务 Schema 使用 examples/ 样例；新路由规范以 routing/ 的实际配置及请求样例验证，ModeHost 使用 examples/mode-host.json，ModeAnalysis 由显式离线演示生成四种合成样例。样例不是研究结论，也不属于生产 world。
