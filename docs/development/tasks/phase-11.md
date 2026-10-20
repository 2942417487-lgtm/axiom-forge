# Phase 11：持久化、事件审计与中断恢复

2026-10-06 用户授权合并 PR #7 并继续 Phase 11。PR #7 合并提交为 `557f98f1dd1fba229edc15ad6d44546208089550`，工作分支为 `feat/phase-11-persistence-audit`。仅推进 Phase 11；交付待审查 PR，不自动合并。

- 每个重要阶段保存 Artifact/checkpoint，保留研究、工程、经济、历史、Red Team、草案/最终综合及提案。
- 建立可验证的任务生命周期与 Event Log，包括 TaskCreated、EvidenceAdded、RedTeamRaisedConflict、CanonChangeProposed、HumanApproved、CanonCommitted。
- 显式 CLI 恢复，从已验证的完成 Artifact 继续，不恢复厂商会话，不重复执行已完成岗位；保留失败/未知调用的预算预留。
- 用户已确认：由用户显式运行 CLI 恢复，自动重试未完成/失败调用，不重跑已完成岗位。每次恢复只尝试一次未完成调用，失败再次停止；新调用生成新 ARN/ART，旧预留不退回。审批入口沿用本地人工 CLI。离线验收不产生 API 费用，不修改正式世界观。
- 验收真实进程中断、结果落盘/日志落盘间隙、损坏数据、并发恢复、审批与 Git 提交中断的恢复；不绕过人工批准。
- 不引入 Phase 12 LangGraph 或自动并发/循环，通用计算执行器仍延期。

2026-10-06 已实际检索并读取 [官方归档 SQLite MCP](https://github.com/modelcontextprotocol/servers-archived/blob/main/src/sqlite/README.md)、[Filesystem MCP](https://github.com/modelcontextprotocol/servers/blob/main/src/filesystem/README.md) 与 [SQLite 原子提交](https://www.sqlite.org/atomiccommit.html)。现成 MCP 提供通用数据库/文件工具，但没有本项目的固定快照、预算预留、输入隔离、批准绑定或恢复校验。此次复用已存在的 Workspace 原子追加接口，以单一文件发布一次 checkpoint 和关联事件；不安装新数据库/MCP，也不向研究模型授予事件日志修改权限。进程锁复用 Python 标准库 [Windows msvcrt](https://docs.python.org/3/library/msvcrt.html) 和 [POSIX fcntl](https://docs.python.org/3/library/fcntl.html)。
