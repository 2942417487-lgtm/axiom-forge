# Phase 6：Runtime Adapter

用户授权继续 Phase 6，选择本轮接入 Claude、OpenAI、Codex 并做真实模型联调；不建立可选 DeepSeek Adapter。基于已合并 PR #4 的 main，在功能分支交付待审查 PR，不自动合并。

## 范围

- 统一 `AgentRuntime.run(role, task, state)`，复用 Phase 4 的显式输入投影与输出校验，SDK 只出现在厂商 Adapter 内。
- Claude 使用官方 Claude Agent SDK；OpenAI 使用官方 Agents SDK；Codex 使用官方 Codex SDK，仅接受软件工程任务。
- 用最小绑定复用 Phase 5 ToolSession。研究角色没有原生 Shell、任意文件读取、其他角色会话、审批、Canon Apply 或 Git mutation。
- 输入、已校验结果、执行状态与内容哈希本地追加保存；厂商 session/thread ID 只放 metadata；不保存密钥或原始 SDK 异常到业务日志。
- 模型、凭据和额度由可信操作者配置，不把参考文档里的模型名称固定进业务角色。
- 后续已明确的接入选择：用户提供 ZenMux 文档及两款模型页面，在本地 `.env` 填写 Key；宿主使用对应原生协议及完整 Slug，支持显式 HTTPS endpoint、Claude auth token/beta 和本地代理配置，不改动用户全局设置。
- 离线 SDK/契约/工具/错误测试和真实模型联调分开记录。真实联调使用 Sonnet 5.5 / GPT-6.1 Sol，获准复用 Codex 登录，总 API 上限 1 美元；Claude/OpenAI 完成后一起推送，不在聊天中接收密钥。实际验收与预算记录见交付文档。

## 留给后续

模型路由、完整 Roundtable/LangGraph 工作流、自动恢复、审批认证、Canon Apply、通用计算执行器与对外 MCP 服务不属于本阶段。Claude 所需的 SDK 内进程 MCP 工具绑定仅是 Adapter，并非部署通用 MCP server。Codex 的工程 sandbox 不授予研究岗位。

## 选型查证

已真实查阅官方 SDK 与 MCP 接入资料。OpenAI 官方现有 Python Codex SDK；旧 Codex MCP server 的官方示例已归档并建议新自动化采用 SDK。本轮复用官方 SDK 的执行循环，项目自行实现的部分仅为业务契约、权限绑定与持久化。

- [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents/sdk)
- [Codex Python SDK](https://learn.chatgpt.com/docs/codex-sdk)
- [已归档的 Codex MCP 示例](https://developers.openai.com/cookbook/examples/codex/codex_mcp_agents_sdk/building_consistent_workflows_codex_cli_agents_sdk)
- [Claude Agent SDK：官方源码、内进程 MCP 与权限说明](https://github.com/anthropics/claude-agent-sdk-python)

安装后进一步核对实际 SDK 类型和源码；依赖版本、许可证与联调限制记录在交付说明中。官方 SDK 无法替代 Axiom Forge 的固定快照与独立分析边界，因此保留薄 Adapter。
