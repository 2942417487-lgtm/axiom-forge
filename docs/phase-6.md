# Phase 6 交付与验收记录

用户授权接入 Claude、OpenAI、Codex，并进行真实模型联调；不接 DeepSeek。模型选择 Claude Sonnet 5.5 和 GPT-6.1 Sol，允许复用本机 Codex 登录，API 联调总预算上限 1 美元。用户将在本地 `.env` 自行填写两个 API Key 后通知；未通知前不发起这两个 API 的真实联调。本阶段基于已合并 PR #4，在 `feat/phase-6-runtime-adapters` 上交付待审查变更。

## 已实现

- 统一 `AgentRuntime.run(role, task, state)` 与投影后 `run_input`；业务层无厂商 SDK import。
- 官方 Claude Agent SDK、OpenAI Agents SDK 和 Python Codex SDK Adapter，复用 SDK 执行循环。
- 每次新会话、受限 ToolSession、岗位/阶段/快照/身份与结果校验；工具回执作为独立 Artifact。
- Claude 关闭原生工具、项目/用户设置与外部 MCP，使用 SDK 内进程 MCP；OpenAI 只有本地 FunctionTool，无 handoff、hosted 付费工具和共享 Session。
- 本地追加保存输入、启动、成功/失败/超时/取消、已校验结果及 SHA256；失败不输出科学结果 Artifact，厂商 ID 仅 metadata。
- 新 source_read Evidence 需要匹配本次真实暂存回执；计算数值/单位/假设必须与引用的当前成功程序输出一致。
- Auditor 的规范 CalculationRequest 自动保存为独立可复用 JSON 文件，核对请求业务上下文；通用计算执行器仍未建设。
- 显式操作者 CLI、可选锁定依赖、密钥不打印、不传给工具；SDK 轮次/token/工具大小/次数限制和费用预检。
- Codex 仅接软件工程 issue 与显式 job 文件，默认 read_only、deny_all，不接受任何研究/审计角色。

接口、现成 MCP/SDK 选型来源、依赖许可证、权限与费用限制见 [Runtime](../runtimes/README.md)；授权范围见 [本地工程任务](tasks/phase-6.md)。

## 离线验证

2026-10-06 在本机 Python 3.14.7 / Windows x64 执行全套 130 项 unittest，全部通过（本次 sandbox 外可以创建实际 junction，无跳过）。随后新增计算数值回执和凭据解析两项测试，Runtime 核心 16 项全部通过；当前合计 132 项已有验证。测试包含实际官方 SDK 对象＋假模型、Claude SDK 的真实内存 MCP 传输、OpenAI Runner 的实际工具循环、Codex 参数与 metadata；这些不是 Claude/OpenAI 真实 API 验收。

验证 29 个 Schema / 本地引用、7 个岗位契约、Runtime CLI 的未授权拒绝、配置 JSON / Python AST / 空值 `.env.example`、忽略规则和 Git 差异。生产 world 仍只有 world.json，未导入测试设定或正式 Evidence。完整回归执行前，Windows sandbox 阻止 asyncio 初始化本地 socket；取得 sandbox 外测试授权后通过，不通过修改 SDK 或跳过测试掩盖限制。

本机 SDK：openai-agents 0.23.1、claude-agent-sdk 0.2.163、openai-codex / CLI 0.160.1。Claude 原生运行时 2.1.291 来自官方发布 manifest，SHA256：`70052a17e06561a4563597f79570e81ccc0772474c3c6ac522aa5ccc71773013`。实际下载回执在忽略的 `.cache/claude-runtime/receipt.json`，二进制不提交。

## 真实联调

Codex 已通过：AgentRun `ARN-3e82e0ac-b8b7-46a5-a8b1-2849bb581cf3`，GPT-6.1 Sol，本机登录、read_only。请求为软件工程 smoke test：针对显式 identity 函数给出一个 unittest 名称和检查内容，无世界观任务。SDK 报告 input_tokens 13544、output_tokens 27，完成状态 completed；实际结果与业务记录位于 `.cache/codex-runs/<ARN>/completion.json`。这是账号/SDK/模型请求成功的验收，不是代码修改、完整工程自动化或科学计算验收。

首次 Codex 启动失败源于窄化环境时将继承的 originator override 置空，导致 SDK 初始化缺少 metadata；已显式设为本应用标识并通过初始化与真实请求复验。失败回执保留，没有冒充成功记录。

Claude / OpenAI 真实 API 和真实模型工具调用尚待用户完成 `.env` 并通知。已经准备独立业务 ID、合成固定快照、一次 canon.read、闭合 ResearchResult 的联调包；Claude 阈值 0.4 / OpenAI 保守预留 0.5 美元，不自动重试或扩大额度。未获取凭据的部分不能标为 Phase 6 全部验收完成。

## 留给后续

Phase 7 模型 Router、Roundtable/LangGraph 工作流、崩溃恢复与历史结果认证、人工审批、Canon Apply、通用计算执行器、MATLAB 与对外 MCP 服务均未实现。原生 SDK 子进程不构成研究数据的 OS 沙箱，Codex 工程 sandbox 也不承诺仅能读工程 job；不将工程 Runtime 用作研究岗位。私有仓库与文档权限不替代服务端强制审批。
