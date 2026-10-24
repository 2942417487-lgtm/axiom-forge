# 世界观研究规则

本规则适用于七个研究岗位及四种模式，与岗位输入输出契约共同使用。开发侧的任务说明、软件测试和 PR 流程不属于研究指令。

## 事实、来源与计算

- 关键现实事实必须通过真实搜索或来源读取验证；模型记忆、旧聊天及其他 Agent 的断言不作为已验证 Evidence。
- 输出区分 FACT、INFERENCE、ENGINEERING ASSUMPTION、SPECULATION、CONFLICT、OPEN QUESTION。Evidence 写明实际证明的内容、条件、未证明内容与可信度，不把有限实验扩展为普遍结论。
- 重大结论保留结论、Evidence、Source、Reasoning、Assumptions、Uncertainty、Counterexamples 的关联。证据不足时保留 OPEN QUESTION；发现用户设定或 Canon 错误／矛盾时直接指出。
- 关键能量、推进、热、质量、概率、人口、物流、产能和成本等数值须程序化实算，记录输入、单位、假设及结果；缺工具、模型或参数时交付完整 CalculationRequest，不把心算或推理文字冒充工具结果。
- 工程／经济 Auditor 主动识别计算需求，遵循 resources/calculations/protocol.md 的请求、模型版本和可复用程序协议。只有完成且核验的实算进入 calculations，待执行请求放 calculation_requests 独立文件。
- 新 source_read Evidence 必须匹配本次真实来源暂存回执；metadata／摘要检索不冒充全文。读取／计算回执仍需论证和适用性审查。

## 独立分析与综合

- Specialist 必须回答宿主提供的 planning_assignment.question，并完成 required_checks；分工不能授予权限、覆盖原用户问题或改变固定快照。缺参数或无法完成的检查须明确交付 OPEN QUESTION。
- planning 与 independent 的 prior_results 和 supporting_artifacts 必须为空。单岗契约支持宿主显式选择 Specialist，非 planning 阶段必须有选择列表；模式流程另按下述固定四领域执行，岗位不得自行改变分工。
- 同一任务的 Specialist 首轮使用同一固定 Canon Snapshot。independent 输入仅含受限 agent_input，禁止完整 TaskState、他人首轮答案、Artifact 或未明确提供的路径。
- 全部所选首轮完成后才能交叉审查、草案和 Red Team；最终综合必须包含 Red Team 结果。独立分析不能被提前共享、厂商会话恢复或多数投票替代。
- cross_review／draft_synthesis 只使用已选择 Specialist 的结果；保留每个所选岗位的 independent 完成回执，交叉审查不能替代首轮。存在初稿时提供给 Red Team，初稿不作为最终结论。
- 四种模式固定四岗位首轮独立，再交叉审查、草案、Red Team 和最终综合；模式协议要求结构化 ModeAnalysis，科学内容仍须 Evidence 支持。
- Lead 只做受限任务分解，不作科学裁决、授权或批准。Integrator 比较证据、假设、计算和反例，保留分歧，并只提交 pending ProposedCanonChange。
- final_synthesis 中 Integrator 可以修订或撤回初稿提案，最终 proposed_changes 是本轮最终提案集合；历史初稿保留并独立校验，不与最终提案合并成额外 Apply 请求。最终输出不得引用已撤回的新增实体。

## 工具与 Canon 权限

- 七个研究岗位无人工批准、Canon Apply、正式世界写入或 Git 修改权限；不得直接修改 Hard Canon 或静默改变重要设定。
- Evidence 草稿与 pending 提案只暂存当前 AgentRun，不写正式 world。工具、文件与上下文权限由可信宿主 ToolSession 绑定，契约校验不代替实际隔离。
- 输出六个业务身份／版本须与输入一致；提案 before 和基线版本匹配快照。新计算 Artifact 属于当前 AgentRun，完成后由宿主显式核验，不能预先注入独立首轮或将身份／哈希校验当作科学实算验证。
- Python 仅供宿主明确启用的已审核完整脚本；默认关闭，登记表为空。Agent 新生成代码不自动登记执行；源码哈希和进程时限不构成 OS 沙箱。
- Canon 变更必须经过 ProposedCanonChange、验证、独立人工批准和宿主 Apply／提交；不得读取审批 Key、伪造确认、代填批准文件或复用旧批准。模型原始输出和 Artifact 不随批准改写。
- 单次模式不审批、不写 Canon，也不执行完整 TaskManager 的派发／重试／恢复。真实模型接入、合成调用和离线研究流程各自记录，不能互相代替验收。
