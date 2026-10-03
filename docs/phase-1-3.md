# Phase 1–3 交付记录

历史交付记录；PR #2 已于后续会话经用户审查并授权合并。当前进度见 README.md 与 docs/phase-4.md，下文描述 Phase 1–3 交付时的状态。

## Phase 1：世界观数据层

- [x] world/ 与八个 Canon 知识域目录。
- [x] Timeline、Actors、Assumptions、Evidence、Audits、Decisions。
- [x] 七类 Canon 状态与唯一实体 ID、字段规范。
- [x] 初始 world_id 与空生产知识库。
- [x] 自包含、可复现的 Canon Snapshot；内容哈希、离线验证、原子发布、旧快照复用与篡改检测。

## Phase 2：Evidence 与事实可靠性

- [x] Evidence Ledger 文件与完整 Schema。
- [x] Source、Source Type、Date、Field、实证范围、适用条件、未证明内容、Confidence、Supported Claims。
- [x] 论文书目信息，包括 Title、Authors、Journal/Conference、Year、DOI/URL。
- [x] 六类输出与 provenance 规范。
- [x] FACT/INFERENCE 引用与来源读取记录检查；拒绝 synthetic/unverified 依据。
- [x] 关键现实事实必须工具读取、禁止模型记忆冒充 Evidence 的规则。

此阶段定义和验证读取记录；真实来源检索能力属于 Phase 5，验证器不能证明实际访问或科学事实真实性。

## Phase 3：统一业务接口

- [x] TaskState、ResearchResult、EngineeringResult、EconomicResult、HistoricalResult、RedTeamResult、SynthesisResult、Evidence、CanonChange。
- [x] Task、Run、Agent Run / Session 分离，Artifact 身份与哈希。
- [x] 系统自行生成 world_id、task_id、run_id、agent_run_id、artifact_id、canon_version。
- [x] 厂商 session/thread ID 仅放 metadata。
- [x] 22 个 JSON Schema、21 个标注测试性质的样例与跨记录完整性校验。

## 验证与交付边界

已运行 39 项 unittest，全部通过，覆盖正常合约、非法字段/状态/日期/置信度、伪来源、未知引用、ID 混用、时间与结果哈希、提案基线与内存中的提案引用检查、快照篡改/复用/并发发布和 CLI 退出码。

开发分支为 `feat/phase-1-3-foundations`，基于未合并的 Phase 0 分支 `bootstrap/phase-0`。本轮提交独立 PR，等待人工独立审查，不自动合并。

Phase 4 Agent Contract、Phase 5 外部工具接入、Phase 6 Runtime、模型注册表、正式任务执行与 Canon 应用、LangGraph 均未实施。当前 CLI 只处理本地基础数据；没有模型调用、费用或自动世界观修改。
