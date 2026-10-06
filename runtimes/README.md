# Phase 6 Runtime

Phase 6 已合并。Phase 7–9 的 [Router](../routing/README.md) 与 [模式入口](../modes/README.md) 复用以下 SDK/单次 Runtime；四款模型接入与模式离线验收见 [交付记录](../docs/phase-7-9.md)。完整 TaskManager、审批与 Canon Apply 仍留给后续。

这是单次岗位调用接口；模型路由、Roundtable/LangGraph 调度、审批与 Canon Apply 留给后续阶段。实现位于 `axiom_forge/runtimes/`，业务角色和 Schema 不导入厂商 SDK。

## 已复用的官方组件

| Adapter | 实际执行循环 | 本机核对版本 / 代码许可证 |
| --- | --- | --- |
| OpenAI | 官方 Agents SDK `Agent` / `Runner`，Responses API | openai-agents 0.23.1 / MIT |
| Claude | 官方 Claude Agent SDK `ClaudeSDKClient`；SDK 内进程 MCP 工具绑定 | claude-agent-sdk 0.2.163 / MIT；CLI 使用条款另见官方说明 |
| Codex | 官方 Python SDK `AsyncCodex`，本地 app-server | openai-codex 0.160.1 / Apache-2.0 |

已真实检索并查阅 [Agents SDK](https://developers.openai.com/api/docs/guides/agents/sdk)、[Claude SDK 与自定义工具](https://github.com/anthropics/claude-agent-sdk-python)、[Codex SDK](https://learn.chatgpt.com/docs/codex-sdk) 和 [旧 MCP 示例](https://developers.openai.com/cookbook/examples/codex/codex_mcp_agents_sdk/building_consistent_workflows_codex_cli_agents_sdk)。旧 Codex MCP server 已弃用，新自动化选择官方 SDK。Claude 的内进程 SDK MCP 可复用已有 ToolSession，不需要再实现通用 MCP 传输或工具执行循环。项目新增代码只处理本项目的输入投影、权限、输出校验和本地记录。

ZenMux 接入前也检索了其 [官方 Skills](https://zenmux.ai/docs/zh/guide/zenmux-skills.html)：已有接入配置和账户用量助手，适用于操作者交互，不提供本项目的岗位契约和受限研究调用。因此本轮复用已有官方 SDK 的 gateway 配置，不安装全局 Skill，也不自建通用模型执行器。

依赖安装：

```powershell
python -m pip --python .venv install -r runtimes/requirements-lock.txt
```

锁定文件是本机 Python 3.14.7 / Windows x64 的已解析环境，不宣称已在其他平台验收。基础离线依赖仍在根目录；SDK 未安装时相应集成测试跳过。Codex 包附带固定版本 CLI。本次 Claude Windows 包从源码发行版安装，没有附带原生 CLI；使用官方 `downloads.claude.ai` 的 `manifest.json` 核对 SHA256，下载到忽略的 `.cache/claude-runtime/claude.exe`。本机为 2.1.291，二进制、下载脚本与凭据不进入 Git。其他电脑须按 [官方安装说明](https://code.claude.com/docs/en/setup) 补齐原生 CLI，或显式配置绝对/仓库相对 `claude_cli_path`；不得把 npm 的 `.cmd` shim 当作 SDK 可运行的原生文件。

## 统一研究接口

```python
from axiom_forge.runtimes import AgentRuntime, RuntimeLimits, as_prior_result
from axiom_forge.runtimes.openai_adapter import OpenAIAdapter
from axiom_forge.tools.host import session_from_config

runtime = AgentRuntime(repo, OpenAIAdapter(model_id), limits=RuntimeLimits(),
    session_factory=lambda data: session_from_config(repo, data, trusted_tool_config))
packet = await runtime.run(role, task_state, {
    "execution": {"run_id": run_id, "agent_run_id": agent_run_id, "artifact_id": artifact_id},
    "stage": "independent",
    "selected_specialists": [role],
    "prior_results": [],
    "supporting_artifacts": [],
})
# 后续审查显式选取；不要把整个 packet 塞入 AgentInput。
prior = as_prior_result(packet)
```

`run_input(validated_agent_input)` 是同一接口的投影后入口。TaskState 的 metadata、final_result、其他答案、配置与凭据不会自动转发。六个业务身份/版本字段必须由宿主提供，输出逐一匹配；厂商 session/thread ID 仅为 metadata，不用于业务标识。SDK 每次使用新会话，不共享/恢复其他角色记忆，不做 handoff 或自动启动子 Agent。

Claude 的 input_tokens 统一为普通输入＋缓存写入＋缓存读取，并在 metadata 单独保留两种缓存 token 数，避免忽略缓存计费；OpenAI SDK 已报告总输入。`reported_cost_usd` 保留 SDK 报告值，不能替代服务商账单。失败调用也可能产生费用，不能仅从没有成功 Artifact 推断未收费。

调用前验证岗位、阶段、固定快照和前序结果；持久化到 `.cache/runtime-runs/<ARN>/` 的 input、started 与 completion。校验通过才发布 output 和 Artifact 内容哈希。重复/并行使用同一 ARN 被追加存储拒绝；失败、超时、取消没有可用科学结果。进程突然终止可能仅留下 started；重启恢复与结果认证属于后续工作流。本地存储不是防本机操作者篡改的可信数据库。

后续 `prior_results` 使用 `as_prior_result(packet)` 的四字段包；计算所需工具 Artifact 由宿主显式加入 `supporting_artifacts`。规划输出不能作为前序科学结论。宿主仍负责验证历史包来源，静态完成回执不能证明真实执行。

## 工具绑定和计算

权限只取可信宿主的 ToolSession。SDK 工具名把点变为双下划线，如 `canon.read` → `canon__read`；Claude 前缀为 `mcp__axiom__canon__read`。参数继续由 Phase 5 校验，回执保存实际开始/结束、上下文和哈希。模型只看到授权工具；有权限但未配服务的工具仍返回 unavailable。

Claude 设置 `tools=[]` 关闭原生工具、`setting_sources=[]`、`skills=[]`、`strict_mcp_config=True`，不加载项目或用户 MCP/插件；PreToolUse 钩子和拒绝权限回调防止新增工具绕过绑定。独立 cwd、无会话恢复；CLI 的权限控制不是 OS 沙箱。本机原生 Windows 不支持 Claude shell sandbox，因此研究岗位不获得原生 Shell 或任意文件 Read。现有 `.claude/agents/` 的 Read 岗位入口保留，不能把手工启动该入口等同于受控 Adapter。

OpenAI 仅使用本地 FunctionTool，无 hosted shell、Web search、file search、handoff 或 server continuation；endpoint 只由可信操作者配置，关闭自动重试、远端 tracing 和 Responses 存储请求。模型与工具请求仍需发送给配置的 API 服务商；这些设置不构成服务商数据保留承诺。

新 `source_read` Evidence 必须与本次成功 `evidence.stage` 暂存的记录逐字/哈希一致；继承快照和显式前序 Evidence 保留来源。检索 metadata 不冒充来源全文，回执也不证明科学主张。

通用计算执行器没有实现，脚本登记仍为空、默认关闭。Auditor 的 `calculation_requests` 通过身份检查后，Runtime 自动保存为单独的 `calculations/<request_id>.json`，返回 request Artifact；这是可供后续程序复用的请求文件，不是计算结果。

若宿主另外批准并登记已有脚本：模型调用 `python__run_reviewed`；本次 calculations 只能引用成功 Python ToolResult 的 `result_id`。为避免模型改写实算数值，脚本 JSON 需含 `calculation: {inputs, outputs, assumptions}`，三个字段与岗位旧 calculations 的数值/单位/假设完全一致；不匹配则拒绝结果。该兼容桥不运行通用模型、不验证任意 script JSON 为 CalculationResult，也不保证算法科学正确。脚本审核和 OS 权限仍由操作者负责。

## 操作者 CLI、密钥与额度

本机用户选择的模型 ID 已按官方页面查证：[claude-sonnet-5-5](https://platform.claude.com/docs/en/models/sonnet-5-5/overview)、[gpt-6.1-sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol)。模型只出现在显式宿主配置，不固定到岗位。样例的普通文本 token 单价于 2026-10-06 核对，后续运行前须重新查证，不能当作永久价格。

用户在本地 `.env` 填写 ANTHROPIC_API_KEY、OPENAI_API_KEY；不要上传、打印或在聊天中发送密钥。程序仅按显式 `--credentials` 路径读取，也可使用操作者已配置的环境变量；不自动扫描个人凭据目录或执行 `.env` 中的 shell 内容。

API Key 用于认证；宿主配置的 `model` 选择模型，`base_url` 选择接入地址。省略 `base_url` 时使用对应官方直连地址；带供应商前缀的模型 ID 必须显式指定接入地址，避免把中转商 Key 意外发送给官方。地址必须为 HTTPS，不能包含账号、密码、查询或片段；不从 AgentInput、工具回包或任意环境变量中选择 API endpoint。这个校验不证明任意第三方可信，操作者仍需选择服务商。SDK 内部网络行为与服务商转发不能仅靠 URL 字符串校验保证。

本轮用户选择 [ZenMux](https://zenmux.ai/docs/zh/guide/quickstart.html)，该服务支持 Responses 和 Anthropic Messages 原生协议，继续复用官方 SDK，未新增模型执行循环。对应配置如下，模型名称应使用 ZenMux 的完整 Slug：

| 配置 | `base_url` | `model` |
| --- | --- | --- |
| `examples/runtimes/zenmux-openai-host.json` | `https://zenmux.ai/api/v1` | `openai/gpt-6.1-sol` |
| `examples/runtimes/zenmux-claude-host.json` | `https://zenmux.ai/api/anthropic` | `anthropic/claude-sonnet-5.5` |

ZenMux 两个协议可以使用同一个 Key；仍分别放在本地两个变量中，工具不会收到它们。官方直连样例保留，不能将 ZenMux Key 与它们混用。2026-10-06 的 [GPT 页面](https://zenmux.ai/openai/gpt-6.1-sol) 列出输入 $2–4 / 输出 $10–15 每百万 token；ZenMux OpenAI 样例用上限 $4 / $15 做本地预留。[Claude 页面](https://zenmux.ai/anthropic/claude-sonnet-5.5) 列出输入 $2 / 输出 $10、缓存写入 $2.5–4 每百万 token；Claude CLI 的 `total_cost_usd` 是 SDK 自身估算，不作为中转商账单。模型价格与接入支持需在后续运行前重新核对。

按 [ZenMux Claude Code 接入说明](https://zenmux.ai/docs/zh/best-practices/claude-code.html)，Claude gateway 配置设置 `claude_auth_mode="auth_token"`：同一 `.env` 的 ANTHROPIC_API_KEY 值只在专用子进程内映射到 ANTHROPIC_AUTH_TOKEN，子进程 ANTHROPIC_API_KEY 置空；宿主变量不变。`claude_disable_experimental_betas=true` 关闭实验性 beta 与 attribution header，减少不兼容路由；这两个选项是闭合宿主配置，不允许传入任意环境变量或工具修改配置。

如果本机网络需要代理，可在本地宿主配置增加 `claude_https_proxy`，例如 `http://127.0.0.1:10081`；它只设置该 Claude 子进程的 HTTP(S)_PROXY，不修改系统、全局 Shell 或宿主环境，不接受代理账号/密码、路径、查询和片段。实际代理地址须由操作者核对；不得把某台机器的 localhost 端口当作通用默认值。本机 Python 使用 Windows 系统代理，而原生 Claude CLI 未自动继承，曾出现 ECONNREFUSED；联调用的本地覆盖配置位于忽略的 `.cache/phase6-zenmux-claude-host.json`。需要代理的本机用该覆盖配置替代公开样例路径；其余机器使用自己的显式配置。

```powershell
# 先生成一个新的合法 AgentInput，不能跨调用复用 ARN。
.\.venv\Scripts\python.exe -m axiom_forge runtime run --context <AgentInput.json> --config examples/runtimes/openai-host.json --credentials .env --allow-live
.\.venv\Scripts\python.exe -m axiom_forge runtime run --context <另一个AgentInput.json> --config examples/runtimes/claude-host.json --credentials .env --allow-live
# 本机 .env 为 ZenMux Key 时使用以下专用配置。
.\.venv\Scripts\python.exe -m axiom_forge runtime run --context <AgentInput.json> --config examples/runtimes/zenmux-openai-host.json --credentials .env --allow-live
.\.venv\Scripts\python.exe -m axiom_forge runtime run --context <另一个AgentInput.json> --config examples/runtimes/zenmux-claude-host.json --credentials .env --allow-live
```

没有 `--allow-live` 时不读取凭据、不执行 SDK。CLI 只打印状态、Artifact 路径和安全错误，原始 SDK 异常和思考内容不写业务日志。不同供应商的密钥不会通过 SDK 工具参数或工程 subprocess 传递；子运行时环境把无关变量值置空，宿主环境不受修改。

限制包括输出 token、SDK 最大轮次、工具次数、工具可见结果大小和 asyncio 截止时间；同步工具 I/O 与 SDK 清理可延迟截止，不是硬进程杀死时限。超大的工具结果保存回执，但向模型返回 unavailable，不能截断后冒充完整结果。

Claude `max_budget_usd` 是 SDK 在请求后检查的停止阈值，可能被最后一个请求越过；第三方模型 Slug 的 CLI 估价可能与服务商计费不一致。OpenAI 每个请求按宿主核对的 token 价格、UTF-8 字节与额外协议余量预留额度；预检不足时不调用模型。它是本地保守估算，不是官方账单限额或通用价格服务。样例禁 hosted 付费工具、图片与隐藏会话上下文；OpenAI 客户端关闭自动重试，Claude 子进程设置 `CLAUDE_CODE_MAX_RETRIES=0`、`CLAUDE_CODE_NONSTREAMING_TIMEOUT_RETRIES=0` 和与 Runtime 截止一致的 `API_TIMEOUT_MS`（参见 [官方变量说明](https://code.claude.com/docs/en/env-vars)）；gateway 内部重试不能由客户端设置保证。变更调用方式须重新评估。官方直连样例为 Claude 0.4 / OpenAI 0.5 美元；ZenMux 样例按上限价格分配 Claude 0.3 / OpenAI 0.6 美元，分别最多两轮、2048 输出 token、一次小型快照工具调用，Claude 等待上限 300 秒。失败不由本项目自动重试；修正后重新联调须使用新 ARN，并先核对累计费用。总 API 上限 1 美元的授权只适用于本轮联调；后续运行须由操作者设置额度，可另外使用 [ZenMux Key Credit Limit](https://zenmux.ai/docs/zh/guide/pay-as-you-go.html) 的服务端限额。Codex 本机账号联调使用订阅配额，API 单价不能推算其账号计费。

## Codex 工程接口

```python
from axiom_forge.runtimes.codex_adapter import CodexRuntime
runtime = CodexRuntime(repo, model=model_id, allow_login_reuse=True)
receipt = await runtime.run("software_engineer", {
    "task_id": task_id,
    "issue": "范围明确的软件工程需求",
    "files": {"fixture.py": "# 宿主显式提供的工程文件\n"},
}, {"run_id": run_id, "agent_run_id": agent_run_id, "artifact_id": artifact_id})
```

它不接收任何研究岗位，包括 engineering_auditor，不产生 ResearchResult/Canon 提案。操作者必须授权复用登录；默认 read_only、deny_all 审批，工程文件放在独立 `.cache/codex-runs/<ARN>/job/`，SDK thread 为 ephemeral。只有可信操作者为明确工程任务设置 `allow_job_writes=True` 时选择 workspace_write；原仓库文件不自动复制、提交或合并。后续工程输出应由作者审查后手工采纳。

Codex 原生文件/命令能力由其 OS sandbox 和本机配置控制，不走研究 ToolSession；read_only 不承诺只允许读 job 或隔离所有个人文件，workspace_write 也需核对本机配置的额外 writable roots。不能将其用于需要上述研究岗位隔离的调用。目录中的原始 job 文件和 completion 均为本地缓存，无 Canon/审批写入口。
