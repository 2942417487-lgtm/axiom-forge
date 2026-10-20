# Engineering task：Phase 1–3 基础层

用户授权：继续推进到 Phase 3。范围为 Phase 1、2、3；Phase 0 为已实现的基础依赖。

交付要求：

1. 建立分域世界观目录、统一 Canon 状态与实体 ID 规范；实现自包含、可校验的 Canon Snapshot。
2. 定义 Evidence Ledger、事实分层、provenance 与真实来源读取记录；禁止模型记忆冒充 Evidence。
3. 提供 TaskState、六类分析结果、Evidence、CanonChange 以及支持它们的 JSON Schema；分离 Task、Run、Agent Run；提供项目自身的业务 ID 生成工具。
4. 提供本地验证和快照命令、独立测试与使用说明。初始 world 为空，不替用户创作设定或伪造证据。

本轮不实施 Phase 4 的 Agent Contract、Phase 5 外部工具接入、模型调用、自动 Canon 应用、审批 Runtime、任务工作流或 LangGraph。

开发分支：`feat/phase-1-3-foundations`，基于 `bootstrap/phase-0`。提交独立 PR，Phase 0 PR 合并前以该分支为 base；用户批准合并后再调整后续 PR 基线。

验收：schemas 自检与样例校验；非法字段、引用与 ID 被拒绝；FACT 的来源记录门槛；任务/执行/结果身份一致性；快照可复现、自包含与篡改检测；旧快照在 live world 修改后仍保持原数据；空初始 world 不含 Canon 与 Evidence。
