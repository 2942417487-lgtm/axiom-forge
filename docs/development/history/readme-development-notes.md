# 从 README 迁出的开发说明

迁移日期：2026-10-20。来源基线：`5958e41ffd64c0d3c69b266e0061203df2fe25ac`。以下是被替换／迁出的原文片段，保留当时语境；完整原件可用 `git show <基线>:<原路径>` 读取。它们不是现状、当前机器配置或新的执行授权；使用说明以现行 README／指南为准。

## README.md


> Phase 0–11 已合并，PR #8 完成持久化、审计与显式恢复。本轮基础分离改造将正式世界移到外部独立 Git 仓库，系统仓库只保留代码、规则、模板与合成测试资料。每个世界创建时就建立本地版本管理；GitHub 连接、标准导出/导入和前端另行实施。具体设计与命令见 [独立世界工作区](../../guides/world-workspaces.md)。
>
> 已有官方 SDK Runtime、受限工具、模型路由、四种模式、Task Manager 和人工 Canon 审批。四款模型的真实合成接入测试与研究流程的离线验收分别记录，不代表完整科学研究已通过真实模型验收。通用 Web 搜索与计算执行器尚未实现。
>
> 项目元数据现有四字段 Schema、PRJ 标识和只读格式／世界身份检查。使用 [项目元数据检查](../../guides/project-metadata-check.md)；它不会登记项目、创建本机绑定或更新世界，也不证明 Git／敏感检查通过。宿主回执、仓库接受／接续及完整产品功能仍待实施。

> 以下为设计规划，按后续阶段逐步创建：`workflows/`、`evals/`。Runtime 提供单次调用，模式入口组合有界研究会话；Claude 使用 SDK 内进程 MCP 绑定，尚未部署对外通用 MCP 服务。
>
> 业务角色与具体模型解耦；厂商模型名称、API 标识、价格和能力必须在接入时查证。先验证简单 Python V1，再评估引入 LangGraph。
>
> ## Git 与人工审查
>
> GitHub 仓库使用 Private 可见性。私有仓库仍需严格排除凭据。
>
> 仓库地址：[2942417487-lgtm/axiom-forge](https://github.com/2942417487-lgtm/axiom-forge)。`origin` 已连接该仓库，默认分支为 `main`。
>
> AI 的重要系统或世界观修改必须在功能分支上完成，经验证、人工审查后再合并至 `main`。Phase 0 的 [PR #1](https://github.com/2942417487-lgtm/axiom-forge/pull/1)、Phase 1–3 的 [PR #2](https://github.com/2942417487-lgtm/axiom-forge/pull/2)、Phase 4 的 [PR #3](https://github.com/2942417487-lgtm/axiom-forge/pull/3) 与 Phase 5 的 [PR #4](https://github.com/2942417487-lgtm/axiom-forge/pull/4) 已经用户审查并授权合并；main 包含 Phase 0–5。
>
> PR #5–#8 已按用户授权合并，main 包含 Phase 0–11。本轮在 `codex/separate-world-workspaces` 交付基础分离改造，等待人工审查。系统开发 PR 与世界 Canon 分支属于不同仓库；Canon Apply 只创建世界分支，发布与合并仍由操作者控制。
>
> 本机的 GitHub CLI 便携版与认证配置位于 `.cache/`，不会进入 Git。本仓库单独配置了 CLI credential helper；全局 Git 认证配置保持原状。更换电脑时需要自行配置 GitHub 认证，本地 `.cache/` 不可作为共享文件上传。
>
> ```powershell
> git switch -c codex/short-description
> # 完成修改并执行相关检查
> git diff --check
> git add -- <明确指定的文件>
> git commit -m "Describe the change"
> git push -u origin HEAD
> # 在 GitHub 发起 Pull Request，人工审查后合并。
> ```
>
> Hard Canon 修改还必须经过 `ProposedCanonChange → Validation → Human Approval → Apply → Git Commit`。仓库私有可见性与文档规则不等于服务端分支保护；后续若要配置强制规则，应单独实施并核验。

## tools/README.md


> 当前版本的路径与兼容性以 [独立世界工作区](../../guides/world-workspaces.md) 为准。世界操作显式指定外部 --world；配置与凭据来自外部宿主目录。以下历史验收保留原日期和当时结果。

> 本轮已经实现本地工具，不包含 MCP server/传输、厂商 SDK、模型调用或自动任务调度。Claude 岗位文件仍只有 Read，不会因创建这些代码而获得新的执行权限。

> 用户后续选型要求：接入或新增工具前，先真实搜索网上现成的 MCP Tools 或 skills，核查功能、维护、兼容性、许可证、权限、依赖与费用；可满足要求时优先复用，仅在明确缺口处自行实现。现有本地工具可在后续包装成 MCP，当前尚未实施包装。

> Phase 5 的真实联调与离线测试记录见 `docs/development/history/phases/phase-5.md`。Phase 6 通过受控 SDK Adapter 绑定宿主明确授权的 ToolSession，说明见 [Runtime](../../../runtimes/README.md)；工具存在仍不表示未配置的搜索服务或脚本已经可用。

## runtimes/README.md


> 当前版本的路径与兼容性以 [独立世界工作区](../../guides/world-workspaces.md) 为准。世界操作显式指定外部 --world；配置与凭据来自外部宿主目录。以下历史验收保留原日期和当时结果。

> ## 已复用的官方组件
>
> | Adapter | 实际执行循环 | 本机核对版本 / 代码许可证 |
> | --- | --- | --- |
> | OpenAI | 官方 Agents SDK `Agent` / `Runner`，Responses API | openai-agents 0.23.1 / MIT |
> | Claude | 官方 Claude Agent SDK `ClaudeSDKClient`；SDK 内进程 MCP 工具绑定 | claude-agent-sdk 0.2.163 / MIT；CLI 使用条款另见官方说明 |
> | Codex | 官方 Python SDK `AsyncCodex`，本地 app-server | openai-codex 0.160.1 / Apache-2.0 |
>
> 已真实检索并查阅 [Agents SDK](https://developers.openai.com/api/docs/guides/agents/sdk)、[Claude SDK 与自定义工具](https://github.com/anthropics/claude-agent-sdk-python)、[Codex SDK](https://learn.chatgpt.com/docs/codex-sdk) 和 [旧 MCP 示例](https://developers.openai.com/cookbook/examples/codex/codex_mcp_agents_sdk/building_consistent_workflows_codex_cli_agents_sdk)。旧 Codex MCP server 已弃用，新自动化选择官方 SDK。Claude 的内进程 SDK MCP 可复用已有 ToolSession，不需要再实现通用 MCP 传输或工具执行循环。项目新增代码只处理本项目的输入投影、权限、输出校验和本地记录。
>
> ZenMux 接入前也检索了其 [官方 Skills](https://zenmux.ai/docs/zh/guide/zenmux-skills.html)：已有接入配置和账户用量助手，适用于操作者交互，不提供本项目的岗位契约和受限研究调用。因此本轮复用已有官方 SDK 的 gateway 配置，不安装全局 Skill，也不自建通用模型执行器。
>
> 依赖安装：
>
> ```powershell
> python -m pip --python .venv install -r runtimes/requirements-lock.txt
> ```
>
> 锁定文件是本机 Python 3.14.7 / Windows x64 的已解析环境，不宣称已在其他平台验收。基础离线依赖仍在根目录；SDK 未安装时相应集成测试跳过。Codex 包附带固定版本 CLI。本次 Claude Windows 包从源码发行版安装，没有附带原生 CLI；使用官方 `downloads.claude.ai` 的 `manifest.json` 核对 SHA256，下载到忽略的 `.cache/claude-runtime/claude.exe`。本机为 2.1.291，二进制、下载脚本与凭据不进入 Git。其他电脑须按 [官方安装说明](https://code.claude.com/docs/en/setup) 补齐原生 CLI，或显式配置位于世界目录外的绝对 `claude_cli_path`；不得把 npm 的 `.cmd` shim 当作 SDK 可运行的原生文件。

> ## 操作者 CLI、密钥与额度
>
> 本机用户选择的模型 ID 已按官方页面查证：[claude-sonnet-5-5](https://platform.claude.com/docs/en/models/sonnet-5-5/overview)、[gpt-6.1-sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol)。模型只出现在显式宿主配置，不固定到岗位。样例的普通文本 token 单价于 2026-10-06 核对，后续运行前须重新查证，不能当作永久价格。
>
> 用户在本地 `.env` 填写 ANTHROPIC_API_KEY、OPENAI_API_KEY；不要上传、打印或在聊天中发送密钥。程序仅按显式 `--credentials` 路径读取，也可使用操作者已配置的环境变量；不自动扫描个人凭据目录或执行 `.env` 中的 shell 内容。
>
> API Key 用于认证；宿主配置的 `model` 选择模型，`base_url` 选择接入地址。省略 `base_url` 时使用对应官方直连地址；带供应商前缀的模型 ID 必须显式指定接入地址，避免把中转商 Key 意外发送给官方。地址必须为 HTTPS，不能包含账号、密码、查询或片段；不从 AgentInput、工具回包或任意环境变量中选择 API endpoint。这个校验不证明任意第三方可信，操作者仍需选择服务商。SDK 内部网络行为与服务商转发不能仅靠 URL 字符串校验保证。
>
> 本轮用户选择 [ZenMux](https://zenmux.ai/docs/zh/guide/quickstart.html)，该服务支持 Responses 和 Anthropic Messages 原生协议，继续复用官方 SDK，未新增模型执行循环。对应配置如下，模型名称应使用 ZenMux 的完整 Slug：
>
> | 配置 | `base_url` | `model` |
> | --- | --- | --- |
> | `examples/runtimes/zenmux-openai-host.json` | `https://zenmux.ai/api/v1` | `openai/gpt-6.1-sol` |
> | `examples/runtimes/zenmux-claude-host.json` | `https://zenmux.ai/api/anthropic` | `anthropic/claude-sonnet-5.5` |
>
> ZenMux 两个协议可以使用同一个 Key；仍分别放在本地两个变量中，工具不会收到它们。官方直连样例保留，不能将 ZenMux Key 与它们混用。2026-10-06 的 [GPT 页面](https://zenmux.ai/openai/gpt-6.1-sol) 列出输入 $2–4 / 输出 $10–15 每百万 token；ZenMux OpenAI 样例用上限 $4 / $15 做本地预留。[Claude 页面](https://zenmux.ai/anthropic/claude-sonnet-5.5) 列出输入 $2 / 输出 $10、缓存写入 $2.5–4 每百万 token；Claude CLI 的 `total_cost_usd` 是 SDK 自身估算，不作为中转商账单。模型价格与接入支持需在后续运行前重新核对。
>
> 按 [ZenMux Claude Code 接入说明](https://zenmux.ai/docs/zh/best-practices/claude-code.html)，Claude gateway 配置设置 `claude_auth_mode="auth_token"`：同一 `.env` 的 ANTHROPIC_API_KEY 值只在专用子进程内映射到 ANTHROPIC_AUTH_TOKEN，子进程 ANTHROPIC_API_KEY 置空；宿主变量不变。`claude_disable_experimental_betas=true` 关闭实验性 beta 与 attribution header，减少不兼容路由；这两个选项是闭合宿主配置，不允许传入任意环境变量或工具修改配置。
>
> 如果本机网络需要代理，可在本地宿主配置增加 `claude_https_proxy`，使用 `<本机显式代理地址>`；它只设置该 Claude 子进程的 HTTP(S)_PROXY，不修改系统、全局 Shell 或宿主环境，不接受代理账号/密码、路径、查询和片段。实际代理地址须由操作者核对；不得把某台机器的 localhost 端口当作通用默认值。本机 Python 使用 Windows 系统代理，而原生 Claude CLI 未自动继承，曾出现 ECONNREFUSED；联调用的本地覆盖配置位于忽略的 `.cache/phase6-zenmux-claude-host.json`。需要代理的本机用该覆盖配置替代公开样例路径；其余机器使用自己的显式配置。本机代理端点已在 2026-10-20 隐私复核中改为占位说明，原始记录仍可按来源基线追溯。
>
> ```powershell
> # 将所需 examples/runtimes/*-host.json 复制到外部宿主目录，再调整配置。
> # 先生成与外部世界匹配的新合法 AgentInput，不能跨调用复用 ARN。
> .\.venv\Scripts\python.exe -m axiom_forge --world <外部世界目录> --host-root <外部宿主目录> runtime run --context <AgentInput.json> --config <外部宿主目录>/openai-host.json --credentials <外部.env> --allow-live
> .\.venv\Scripts\python.exe -m axiom_forge --world <外部世界目录> --host-root <外部宿主目录> runtime run --context <另一个AgentInput.json> --config <外部宿主目录>/claude-host.json --credentials <外部.env> --allow-live
> # 本机 .env 为 ZenMux Key 时使用以下专用配置。
> .\.venv\Scripts\python.exe -m axiom_forge --world <外部世界目录> --host-root <外部宿主目录> runtime run --context <AgentInput.json> --config <外部宿主目录>/zenmux-openai-host.json --credentials <外部.env> --allow-live
> .\.venv\Scripts\python.exe -m axiom_forge --world <外部世界目录> --host-root <外部宿主目录> runtime run --context <另一个AgentInput.json> --config <外部宿主目录>/zenmux-claude-host.json --credentials <外部.env> --allow-live
> ```
>
> 没有 `--allow-live` 时不读取凭据、不执行 SDK。CLI 只打印状态、Artifact 路径和安全错误，原始 SDK 异常和思考内容不写业务日志。不同供应商的密钥不会通过 SDK 工具参数或工程 subprocess 传递；子运行时环境把无关变量值置空，宿主环境不受修改。
>
> 限制包括输出 token、SDK 最大轮次、工具次数、工具可见结果大小和 asyncio 截止时间；同步工具 I/O 与 SDK 清理可延迟截止，不是硬进程杀死时限。超大的工具结果保存回执，但向模型返回 unavailable，不能截断后冒充完整结果。
>
> Claude `max_budget_usd` 是 SDK 在请求后检查的停止阈值，可能被最后一个请求越过；第三方模型 Slug 的 CLI 估价可能与服务商计费不一致。OpenAI 每个请求按宿主核对的 token 价格、UTF-8 字节与额外协议余量预留额度；预检不足时不调用模型。它是本地保守估算，不是官方账单限额或通用价格服务。样例禁 hosted 付费工具、图片与隐藏会话上下文；OpenAI 客户端关闭自动重试，Claude 子进程设置 `CLAUDE_CODE_MAX_RETRIES=0`、`CLAUDE_CODE_NONSTREAMING_TIMEOUT_RETRIES=0` 和与 Runtime 截止一致的 `API_TIMEOUT_MS`（参见 [官方变量说明](https://code.claude.com/docs/en/env-vars)）；gateway 内部重试不能由客户端设置保证。变更调用方式须重新评估。官方直连样例为 Claude 0.4 / OpenAI 0.5 美元；ZenMux 样例按上限价格分配 Claude 0.3 / OpenAI 0.6 美元，分别最多两轮、2048 输出 token、一次小型快照工具调用，Claude 等待上限 300 秒。失败不由本项目自动重试；修正后重新联调须使用新 ARN，并先核对累计费用。总 API 上限 1 美元的授权只适用于本轮联调；后续运行须由操作者设置额度，可另外使用 [ZenMux Key Credit Limit](https://zenmux.ai/docs/zh/guide/pay-as-you-go.html) 的服务端限额。Codex 本机账号联调使用订阅配额，API 单价不能推算其账号计费。

> 现有 [Router](../../../routing/README.md)、[模式入口](../../../modes/README.md) 和 [Phase 10 Task Manager](../../guides/task-management.md) 复用以下 SDK/单次 Runtime；四款模型接入与模式离线验收见 [记录](phases/phase-7-9.md)。人工审批与 Canon Apply 位于独立宿主 CLI，未增加 Runtime/ToolSession 权限。

## modes/README.md


> 当前版本的路径与兼容性以 [独立世界工作区](../../guides/world-workspaces.md) 为准。世界操作显式指定外部 --world；配置与凭据来自外部宿主目录。以下历史验收保留原日期和当时结果。

> 样例是结构说明，并非本轮 2 美元授权；真实完整模式会有多次模型调用，须由操作者另行决定预算。示例沿用小规模 smoke 的工具/输出限制，正式研究须按任务调整。当前 Windows Claude CLI 需要本地代理的情况下，只在忽略的宿主 profile 设置 claude_https_proxy；不得复制个人代理地址为所有用户默认值。ZenMux Key 只能用于对应 ZenMux base_url。

> 模式不修改传入 TaskState 或生产 world，不执行审批或 Canon Apply，不恢复旧会话。全流程 TaskManager、显式重试/恢复、独立人工审批与 Canon 更新由 Phase 10–11 的宿主入口处理。四款模型的真实合成接入测试与四种模式的离线流程验收分别记录，不把它们混称为真实科学研究验收。

## agents/README.md


> 将来 Runtime 还需限制可见文件、工具、会话记忆和模型上下文

> Phase 9 模式入口

> 本阶段没有自动计划派发或人工审批执行器。

> 后续 Runtime 必须创建可信记录并保存首轮输入和结果。

> 持久化与真实运行边界留到 Runtime / 工作流阶段。

> Phase 10 审批后的 Apply

> Phase 5 增加默认关闭的已审核脚本宿主接口

> LeadPlan 不包含事实裁决、Canon 变更或批准字段；当前作为独立 Artifact 契约，未加入 Phase 3 TaskState 的持久化字段。Runtime 阶段将实现保存和读取这些记录。

> 文件格式已按官方文档核对和本地检查；`.claude/agents/` 的手工岗位加载尚未单独联调。受控 SDK Runtime 的角色指令加载与模型接入验证另见 docs/development/history/phases/phase-6.md、docs/development/history/phases/phase-7-9.md；这些手工文件本身不配置服务端权限、不实现 Runtime 隔离。

## schemas/README.md


> 共 42 个 Schema：原有数据、计算、工具、路由与模式结构，Phase 10 增加 CanonReview/Approval/Commit，Phase 11 增加 TaskCheckpoint/EventRecord，项目元数据最小实现增加 ProjectMetadata。角色使用相同严格输入包，根据 role/stage 做语义限制；AgentInput 可选 mode_protocol=1.0，SynthesisResult 可选 mode_analysis，模式协议的最终综合强制后者存在。详见 [Agent Contract](../../../agents/README.md)、[Routing](../../../routing/README.md)、[模式](../../../modes/README.md)。

## routing/README.md


> ## 初始分工
>
> | 模型 | 初始用途 | 当前状态 |
> | --- | --- | --- |
> | GPT-6 Luna | 分类、metadata、抽取、低成本预处理 | 已联调；研究模式最低 Tier 1，不使用其代替审计 |
> | DeepSeek 4.1 Flash | 机械 Coding、脚本与样板任务 | 登记但禁用，Adapter 未接入 |
> | Sonnet 5.5 | 情景/创意讨论、历史整理、普通 Lead/综合 | 已联调 |
> | GPT-6.1 Sol | 科学/工程/Evidence、工具任务、Coding 主力 | 研究 Adapter 已联调；Codex 仍只接软件工程 |
> | Opus 5.5 | 高重要性 Lead、Integrator、Red Team | 已联调，Tier 2 |
> | Fable 5.1 / GPT-6 Astra | 极难问题、全局一致性与最终独立复核 | 登记但禁用；需要 Tier 3 时返回 OPEN QUESTION |
>
> 软件工程分工是初始策略，不授予研究 Runtime 软件工程工具。所有强弱项均待项目自己的评测；联调通过只证明合成工具与 JSON 协议可运行。
>
> 现成方案检索：[LiteLLM Router](https://docs.litellm.ai/docs/routing) 已提供网关负载/延迟/成本路由；本阶段保留 Phase 6 官方 SDK，新增薄业务策略以执行固定快照、Canon 重要性、已验证状态与跨家族审查条件，没有部署新网关或重复实现供应商执行循环。YAML 复用 [PyYAML](https://pyyaml.org/wiki/PyYAMLDocumentation) SafeLoader，另拒绝别名、重复字段、非 JSON 值与超大文件；本机版本 6.0.3，许可证 MIT。

## calculations/README.md


> 本目录定义协议。本轮没有创建计算执行器、模型程序、MATLAB Adapter 或工具授权；样例都是待执行请求。两岗位已有真实工具计算规则，本补充使“需要计算”能够交付为规范文件，而不只是一段文字。

> 后续 Phase 5 已建立 [已审核 Python 脚本宿主接口](../../../tools/README.md)，默认关闭且登记表为空；它不会自动解析 CalculationRequest、分发模型、核验单位或生成 CalculationResult。通用计算执行器仍按用户要求后续再建，研究岗位尚未接入新权限。

> 当前 Claude 入口只有 Read；两岗位将完整请求 JSON 放入结果的 `calculation_requests` 数组，或返回独立 JSON 代码块供作者保存。磁盘导出、自动分发和工具调用由未来 Runtime 实现；当前岗位不声称文件已写出。

## CLAUDE.md


> ## 当前阶段
>
> Phase 0–11 已合并；系统与外部世界的边界见 docs/guides/world-workspaces.md。Phase 10 提供 Python Task Manager 与独立宿主 CLI 人工审批、Canon 分支提交，使用见 docs/guides/task-management.md。Claude Adapter 复用官方 SDK，关闭原生工具、共享会话、项目/用户设置与外部 MCP；`.claude/agents/` 手工岗位入口仍仅 Read。研究岗位不得调用审批/Git 写入宿主 API、读取 `.env.approval`、自行批准或把批准当成科学证据。任务流程本轮离线验收，未进行整轮付费研究。

> 测试覆盖本地数据工具与角色契约边界，不证明真实 Agent Runtime、Claude 岗位加载、人工审批或完整研究应用已经实现。后续代码阶段应根据项目实际配置运行测试；不得虚构测试通过记录。

## docs/phase-10.md


> 本阶段复用现有 Runtime、Router 和四种模式，实现简单 Python Task Manager。没有引入 LangGraph。新增 CLI 是宿主控制入口，研究岗位的工具集合没有增加审批、Canon Apply 或 Git 写入能力。

## docs/phase-11.md


> Phase 10 已合并。Task Manager 2.0 在既有 Workspace 和 Runtime 上加入 checkpoint、业务事件和恢复入口；没有新增依赖、数据库或研究工具权限。现成 MCP 的实际检索与缺口见 [任务说明](../tasks/phase-11.md)。本阶段采用离线模型和临时 Git 仓库验收。
