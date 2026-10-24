# Phase 6 交付与验收记录

用户授权接入 Claude、OpenAI、Codex，并进行真实模型联调；不接 DeepSeek。模型选择 Claude Sonnet 5.5 和 GPT-6.1 Sol，允许复用本机 Codex 登录，API 联调总预算上限 1 美元。用户已在本地 `.env` 填写同一 ZenMux Key 并提供接入文档及两个模型页面；已核对原生协议、地址、完整模型 Slug 和价格，使用专用宿主配置。本阶段基于已合并 PR #4，在 `feat/phase-6-runtime-adapters` 上交付待审查变更，按用户要求等待 Claude/OpenAI 联调结束后一起推送。

## 已实现

- 统一 `AgentRuntime.run(role, task, state)` 与投影后 `run_input`；业务层无厂商 SDK import。
- 官方 Claude Agent SDK、OpenAI Agents SDK 和 Python Codex SDK Adapter，复用 SDK 执行循环。
- 每次新会话、受限 ToolSession、岗位/阶段/快照/身份与结果校验；工具回执作为独立 Artifact。
- Claude 关闭原生工具、项目/用户设置与外部 MCP，使用 SDK 内进程 MCP；OpenAI 只有本地 FunctionTool，无 handoff、hosted 付费工具和共享 Session。
- 本地追加保存输入、启动、成功/失败/超时/取消、已校验结果及 SHA256；失败不输出科学结果 Artifact，厂商 ID 仅 metadata。
- 新 source_read Evidence 需要匹配本次真实暂存回执；计算数值/单位/假设必须与引用的当前成功程序输出一致。
- Auditor 的规范 CalculationRequest 自动保存为独立可复用 JSON 文件，核对请求业务上下文；通用计算执行器仍未建设。
- 显式操作者 CLI、可选锁定依赖、密钥不打印、不传给工具；SDK 轮次/token/工具大小/次数限制和费用预检。
- 支持可信操作者提供 HTTPS `base_url`，保留官方直连默认值；供应商前缀模型必须提供 endpoint，AgentInput 无选择地址或凭据的权限。ZenMux 专用配置复用 Responses / Anthropic Messages 两个原生接口。
- Codex 仅接软件工程 issue 与显式 job 文件，默认 read_only、deny_all，不接受任何研究/审计角色。

接口、现成 MCP/SDK 选型来源、依赖许可证、权限与费用限制见 [Runtime](../../../../product/docs/runtimes.md)；授权范围见 [本地工程任务](../../tasks/phase-6.md)。

## 离线验证

2026-10-06 在本机 Python 3.14.7 / Windows x64 执行全套 134 项 unittest，全部通过（本次 sandbox 外可以创建实际 junction，无跳过）。测试包含实际官方 SDK 对象＋假模型、Claude SDK 的真实内存 MCP 传输、OpenAI Runner 的实际工具循环、Codex 参数与 metadata、gateway 端点与错误地址拒绝；这些不是 Claude/OpenAI 真实 API 验收。

最终 Claude 代理和缓存输入计量修正后，再执行受影响的 Runtime 核心＋SDK 24 项回归，全部通过；其余 110 项对应代码未修改。缓存写入/读取被纳入总输入并保留分项，闭合代理/认证配置与无重试环境参数均有覆盖。

验证 29 个 Schema / 本地引用、7 个岗位契约、Runtime CLI 的未授权拒绝、配置 JSON / Python AST / 空值 `.env.example`、忽略规则和 Git 差异。生产 world 仍只有 world.json，未导入测试设定或正式 Evidence。完整回归执行前，Windows sandbox 阻止 asyncio 初始化本地 socket；取得 sandbox 外测试授权后通过，不通过修改 SDK 或跳过测试掩盖限制。

本机 SDK：openai-agents 0.23.1、claude-agent-sdk 0.2.163、openai-codex / CLI 0.160.1。Claude 原生运行时 2.1.291 来自官方发布 manifest，SHA256：`70052a17e06561a4563597f79570e81ccc0772474c3c6ac522aa5ccc71773013`。实际下载回执在忽略的 `.cache/claude-runtime/receipt.json`，二进制不提交。

## 真实联调

Codex 已通过：AgentRun `ARN-3e82e0ac-b8b7-46a5-a8b1-2849bb581cf3`，GPT-6.1 Sol，本机登录、read_only。请求为软件工程 smoke test：针对显式 identity 函数给出一个 unittest 名称和检查内容，无世界观任务。SDK 报告 input_tokens 13544、output_tokens 27，完成状态 completed；实际结果与业务记录位于 `.cache/codex-runs/<ARN>/completion.json`。这是账号/SDK/模型请求成功的验收，不是代码修改、完整工程自动化或科学计算验收。

首次 Codex 启动失败源于窄化环境时将继承的 originator override 置空，导致 SDK 初始化缺少 metadata；已显式设为本应用标识并通过初始化与真实请求复验。失败回执保留，没有冒充成功记录。

Claude / OpenAI 使用独立业务 ID、合成固定快照、一次 canon.read 和闭合 ResearchResult 联调。首轮 Claude `ARN-0af5ed46-7bfc-4b62-b9ad-370e146e4c88` 超时，无工具调用/成功输出；首轮 OpenAI `ARN-8918399a-f5a7-4fbe-b6d5-65452e916a33` 真实完成 canon.read，但第二次模型请求被保守费用预检拒绝，无结果 Artifact。失败回执完整保留。用户在 ZenMux 控制台确认首轮累计费用为 $0.0189，剩余总预算 $0.9811；该金额是用户提供的服务商记录，不是 SDK 估价。

随后按 ZenMux Claude Code 文档改用子进程 auth token，并关闭 beta/attribution；本地 SDK/CLI 初始化已验证成功，检查中没有发送模型 query。保留 OpenAI 原有保守字节与协议余量预检，按较高 gateway 价格重新分配阈值为 Claude $0.3 / OpenAI $0.6、输出上限 2048，不抬高 1 美元总预算。

第二轮 OpenAI 已通过：`ARN-cff2d25e-c221-4411-bba0-fe1276b79523`，模型 `openai/gpt-6.1-sol`，真实完成一次 canon.read，返回 ResearchResult 通过岗位 Schema、身份、上下文和 Artifact 校验；input_tokens 15547 / output_tokens 324。按较高 $4/$15 未缓存文本价格估算 $0.067048，不当作实际账单。结果在对应本地缓存目录，SHA256 `367a263a7d6809a50b268a03f215e0be28ca85f70c4c7f6e95eed3771cd5323a`；这是合成 Runtime 测试，不是科学研究结果。

第二轮 Claude `ARN-acaf30a9-bf56-4c4b-b186-332efa9356fe` 仍超时，无工具调用/成功输出。两种协议的模型列表 GET 返回 200，并列出两款指定模型及价格；GET 检查不包含推理请求。用户确认两轮累计实际费用 $0.0331，剩余 $0.9669。按官方文档关闭 CLI API 重试和超时重发，并将仅 Claude 的等待时限改为 300 秒、保持 $0.3 阈值和同样输出/工具/轮次限制，第三、四次诊断均返回 server_error / 零 token；第四次脱敏终止错误明确为 ECONNREFUSED，不再将其解释为模型不可用。

直接 Messages 接口诊断返回 HTTP 200、Sonnet 5.5、input 26 / output 4，响应报告费用 $0.000092，证明 Key / 原生协议 / 模型可用；这一步没有冒充岗位 Runtime 验收。只读代理检查定位到 Python 自动使用 Windows 的系统代理，而 CLI 未继承该设置。新增可信宿主的 `claude_https_proxy`，仅在本地忽略配置显式使用当前系统代理，不修改系统或公开样例的默认代理。

Claude 修正代理后已通过：`ARN-4d8310a1-59ab-40e6-90b1-f5f6871a073d`，模型 `anthropic/claude-sonnet-5.5`，实际完成一次 canon.read，最终 ResearchResult 和 Artifact 通过全部校验；SHA256 `0c7164223d799f67fb323af167167129c882c001512919181508fe7bf103217f`。终止用量为普通 input 597、5 分钟 cache_creation_input 26130、output 518，SDK 估价 $0.071699。该次追加回执的 input_tokens 是当时的普通输入数；随后修正 Adapter 为总输入并保留缓存分项，离线测试验证，既有回执不覆写。旧 smoke 的“未缓存文本估价”漏计缓存写入，不能使用；以上包含缓存的 SDK 估价作为本次参考。

已确认的 $0.0331 加直接诊断报告 $0.000092 和成功 Claude SDK 估价 $0.071699，参考合计约 $0.104891；后续失败调用 SDK 报告零 token，不能因此宣称服务商绝对零收费，最终以 ZenMux 控制台账单为准。未自动扩大预算、请求额度或恢复失败会话。三个 Runtime 的真实连接与范围内 smoke 验收均完成；代理与缓存计量修正也通过离线回归。按用户授权一起推送 Phase 6 并交付草稿 PR，尚未获得合并授权。

## 留给后续

Phase 7 模型 Router、Roundtable/LangGraph 工作流、崩溃恢复与历史结果认证、人工审批、Canon Apply、通用计算执行器、MATLAB 与对外 MCP 服务均未实现。原生 SDK 子进程不构成研究数据的 OS 沙箱，Codex 工程 sandbox 也不承诺仅能读工程 job；不将工程 Runtime 用作研究岗位。私有仓库与文档权限不替代服务端强制审批。
