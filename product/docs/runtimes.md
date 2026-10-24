# Runtime 接口与配置

世界操作与路径约束见 [独立世界工作区](guides/world-workspaces.md)。显式指定外部 --world，配置与凭据来自外部宿主目录。

[Router](../resources/routing/README.md)、[模式](../resources/modes/README.md) 和 [TaskManager](guides/task-management.md) 复用单次 Runtime。人工审批与 Canon Apply 是独立宿主 CLI，不增加 Runtime／ToolSession 权限。

这是单次岗位调用接口；模型路由、四种模式、任务管理和人工审批由既有上层宿主实现，LangGraph 尚未实现。实现位于 `axiom_forge/runtimes/`，业务角色和 Schema 不导入厂商 SDK。

## 依赖与安装

OpenAI、Claude 和 Codex Adapter 分别复用官方 Agents SDK、Claude Agent SDK 与 Codex SDK；依赖版本以 dependencies/runtimes/requirements-lock.txt 为准。SDK 是可选依赖，基础离线操作使用根目录的锁定依赖。

```powershell
python -m pip install -r dependencies/runtimes/requirements-lock.txt
```

Claude SDK 需要可运行的原生 CLI；按 [官方安装说明](https://code.claude.com/docs/en/setup) 安装，必要时通过外部宿主配置提供绝对 claude_cli_path，不用 npm 的 .cmd shim 代替原生程序。某台机器的 CLI 下载、代理和接入记录保存在开发历史，不作为其他机器的默认配置。

## 统一研究接口

```python
from axiom_forge.runtimes import AgentRuntime, RuntimeLimits, as_prior_result
from axiom_forge.runtimes.openai_adapter import OpenAIAdapter
from axiom_forge.tools.host import session_from_config
from axiom_forge.workspaces import WorldWorkspace

world_workspace = WorldWorkspace(external_world_path, host_root=external_host_path)
runtime = AgentRuntime(world_workspace, OpenAIAdapter(model_id), limits=RuntimeLimits(),
    session_factory=lambda data: session_from_config(world_workspace, data, trusted_tool_config))
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

调用前验证岗位、阶段、固定快照和前序结果；持久化到 `.axiom/local/runtime-runs/<ARN>/` 的 input、started 与 completion。校验通过才发布 output 和 Artifact 内容哈希。重复/并行使用同一 ARN 被追加存储拒绝；失败、超时、取消没有可用科学结果。进程突然终止可能仅留下 started；TaskManager 的显式重启恢复与结果校验见 [恢复指南](guides/recovery.md)。本地存储不是防本机操作者篡改的可信数据库。

后续 `prior_results` 使用 `as_prior_result(packet)` 的四字段包；计算所需工具 Artifact 由宿主显式加入 `supporting_artifacts`。规划输出不能作为前序科学结论。宿主仍负责验证历史包来源，静态完成回执不能证明真实执行。

## 工具绑定和计算

权限只取可信宿主的 ToolSession。SDK 工具名把点变为双下划线，如 `canon.read` → `canon__read`；Claude 前缀为 `mcp__axiom__canon__read`。参数继续由工具层校验，回执保存实际开始/结束、上下文和哈希。模型只看到授权工具；有权限但未配服务的工具仍返回 unavailable。

Claude 设置 `tools=[]` 关闭原生工具、`setting_sources=[]`、`skills=[]`、`strict_mcp_config=True`，不加载项目或用户 MCP/插件；PreToolUse 钩子和拒绝权限回调防止新增工具绕过绑定。独立 cwd、无会话恢复；CLI 的权限控制不是 OS 沙箱。本机原生 Windows 不支持 Claude shell sandbox，因此研究岗位不获得原生 Shell 或任意文件 Read。现有 `.claude/agents/` 的 Read 岗位入口保留，不能把手工启动该入口等同于受控 Adapter。

OpenAI 仅使用本地 FunctionTool，无 hosted shell、Web search、file search、handoff 或 server continuation；endpoint 只由可信操作者配置，关闭自动重试、远端 tracing 和 Responses 存储请求。模型与工具请求仍需发送给配置的 API 服务商；这些设置不构成服务商数据保留承诺。

新 `source_read` Evidence 必须与本次成功 `evidence.stage` 暂存的记录逐字/哈希一致；继承快照和显式前序 Evidence 保留来源。检索 metadata 不冒充来源全文，回执也不证明科学主张。

通用计算执行器没有实现，脚本登记仍为空、默认关闭。Auditor 的 `calculation_requests` 通过身份检查后，Runtime 自动保存为单独的 `calculations/<request_id>.json`，返回 request Artifact；这是可供后续程序复用的请求文件，不是计算结果。

若宿主另外批准并登记已有脚本：模型调用 `python__run_reviewed`；本次 calculations 只能引用成功 Python ToolResult 的 `result_id`。为避免模型改写实算数值，脚本 JSON 需含 `calculation: {inputs, outputs, assumptions}`，三个字段与岗位旧 calculations 的数值/单位/假设完全一致；不匹配则拒绝结果。该兼容桥不运行通用模型、不验证任意 script JSON 为 CalculationResult，也不保证算法科学正确。脚本审核和 OS 权限仍由操作者负责。

## 操作者 CLI、凭据与预算

模型、base_url、工具授权与预算只来自可信宿主配置。源码仓库的开发样例位于 development/examples/runtimes/，另随开发资料提供；独立产品使用外部宿主准备的配置，按当前任务调整，不能把样例价格或额度当成实时服务商限制。真实规格、可用性和价格须在运行前重新核对。

凭据只通过显式 --credentials 路径或操作者已配置的环境变量提供；程序不扫描个人凭据目录，也不执行 .env 中的 shell 内容。用户自行在外部 .env／Secret Store 填写对应 Key，不上传或回显。base_url 必须为 HTTPS，不含账号、密码、查询或片段；第三方路由的模型 Slug 与 Key 必须匹配其服务地址。SDK 设置不构成服务商数据保留承诺。

```powershell
python run.py --world <外部世界目录> --host-root <外部宿主目录> runtime run --context <AgentInput.json> --config <外部宿主目录>/openai-host.json --credentials <外部.env> --allow-live
python run.py --world <外部世界目录> --host-root <外部宿主目录> runtime run --context <另一个AgentInput.json> --config <外部宿主目录>/claude-host.json --credentials <外部.env> --allow-live
```

没有 --allow-live 时不读取凭据、不执行 SDK。每次调用使用新的 ARN，输入须匹配外部世界；不要直接用 examples 中的身份启动正式任务。控制台只打印状态、Artifact 路径和安全错误，不打印原始 SDK 异常或思考内容。子运行时收敛无关凭据变量，宿主环境保持原状。

兼容网关的配置示例为 zenmux-openai-host.json／zenmux-claude-host.json。Claude 可通过 claude_auth_mode="auth_token" 在专用子进程映射认证变量；claude_disable_experimental_betas 控制兼容 header。如果机器需要代理，使用当前宿主显式选择的 claude_https_proxy；不复制历史机器的 localhost 端口，不修改全局代理。

限制包括输出 token、SDK 轮次、工具次数与可见结果大小及 asyncio 截止时间。同步 I/O 或 SDK 清理可能延迟退出，不是硬进程隔离。过大的工具结果保留回执，向模型返回 unavailable，不能截断后冒充完整结果。

OpenAI 使用宿主核对单价和输入估计做调用前预留；Claude 的 max_budget_usd 为请求后检查阈值，最后一次请求可能越过预算。第三方 Slug 的 SDK 估价不等于服务商账单；失败或没有 Artifact 也不能推断未收费。样例不能替代服务商侧额度控制。

项目关闭自动重试；Claude 子进程设置相应重试变量和 API_TIMEOUT_MS，仍不能保证网关内部不重试。修改调用方式须重新评估预算。失败后的再次联调使用新 ARN，并由操作者核对累计费用；过去某一轮的付费授权不延续到新任务。

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
