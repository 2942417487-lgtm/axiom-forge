# Phase 10：Python Task Manager 与人工 Canon 审批

2026-10-06 用户授权合并 PR #6、继续 Phase 10，随后确认本地 CLI 人工批准、独立分支提交、本轮离线验收。PR #6 合并提交为 `620c8b29511b3cb93b2f750aa94c0271c4666e75`；开发分支为 `feat/phase-10-task-manager`，交付新 PR 供审查，不自动合并。

- 复用 Phase 6 Runtime 和 Phase 9 四种模式，接入问题、计划、固定 Canon 检索、研究、审计、Red Team、综合。
- 收集任务状态、最终 pending 提案；生成带前后差异、Evidence、风险和内容哈希的审查包。
- 宿主 CLI 单独批准或拒绝；只有批准的精确变更包允许创建 Canon 分支提交。研究 ToolSession 不新增写入、审批或 Git 权限。
- 保留原始模型 Artifact 和 pending 提案；人工控制回执独立记录，批准不把虚构设定变成现实 FACT。
- 在隔离测试仓库验收新增、更新、删除、证据发布、过期基线、篡改、失败和输入隔离；不改正式世界观，不产生 API 费用。
- 不引入 LangGraph，不实现 Phase 11 全量事件日志、崩溃恢复、重试或并发派发；通用计算/MATLAB 执行器继续延期。

现成能力核查（2026-10-06）：[官方 Git MCP README](https://github.com/modelcontextprotocol/servers/blob/main/src/git/README.md)、[依赖](https://github.com/modelcontextprotocol/servers/blob/main/src/git/pyproject.toml)提供通用 Git 工具，MIT 许可；尚不包含 Canon/Evidence 校验、固定快照或人工审批内容绑定。此次不安装新 MCP、不将 Git 写入工具绑定到研究模型，复用已安装的 Git CLI，仅补业务宿主控制层。[Git commit-tree](https://git-scm.com/docs/git-commit-tree)、[update-index](https://git-scm.com/docs/git-update-index)、[update-ref](https://git-scm.com/docs/git-update-ref)支持独立临时索引、提交对象和创建分支时的原子基线校验，避免修改当前工作区和索引。
