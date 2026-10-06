# Model Registry 与 Routing

配置由可信操作者编辑，不能来自 AgentInput、来源文本或模型 metadata。真实请求仍需宿主 Runtime profile、凭据与 `--allow-live`；登记模型不代表授权付费调用。

- `model_registry.yaml`：模型 ID、供应商与原生家族、层级、成本类别、上下文/输出、Runtime 支持的工具能力、验证状态与回执。当前启用 Luna、Sol、Sonnet、Opus；Fable、Astra、DeepSeek 与 legacy pool 禁用。
- `routing_policy.yaml`：难度、重要性、任务类别、复杂工具需求的最低档次。
- `role_assignments.yaml`：七个稳定研究岗位的候选优先级，全部为初始策略；最低可用档次优先，同档次才使用岗位排序。修改配置即可改分工，不修改 SDK 或岗位规则。
- `escalation_policy.yaml`：0 → 1 → 2 → 3、最多四次，最高档仍无答案保留 OPEN QUESTION。

成本类别不是实时账单。`minimum_reservation_usd` 是本项目操作者选择的最低单次预留，不是模型价格或最低消费。模型公开规格来源、核对日期及初始偏好来源须保留；调用可用性只依据本项目真实接入回执。能力字段描述现有 ToolSession 可绑定的能力，实际工具还须由宿主启用；搜索服务、网络来源、Python 脚本等缺少配置时会返回 unavailable。

```powershell
.\.venv\Scripts\python.exe -m axiom_forge routing check
.\.venv\Scripts\python.exe -m axiom_forge routing select --request examples/routing-request.json
```

RoutingRequest 有 role、task_kind、difficulty/importance（0–3）、context_size/output_tokens、tool_complexity、latency_tolerance、budget_usd、need_independent_review、major_canon_change、required_tools。上下文大小由宿主计量；模式入口采用 UTF-8 字节加余量的保守估计。延迟类别是可调整的初始偏好，不是响应时间 SLA。

`ModelRouter.select` 过滤禁用/未验证/legacy、档次不足、容量、输出、工具、预算和延迟，返回选择或 `OPEN_QUESTION`，列出过滤原因与策略哈希。不会把不可用 Tier 3 静默降到 Tier 1。`pair` 对要求独立审查或重要任务约束不同原生模型家族，即使两者都通过 ZenMux。没有满足条件的组合就保留问题；不同家族不保证没有共同错误。

`escalate(request, current_model, attempted, signals)` 是可调用的有界升级接口，signals 明确提供 uncertain、disagreement、unresolved 三个布尔值。它只选择模型，不付费调用、不从模型的任意 metadata 读取授权。模式入口使用当前宿主难度/重要性与一次调用次序，失败即停；自动评估结果并重新派发、恢复和预算账本的完整 TaskManager 留给 Phase 10–11。改变 request 的最低要求后应重新核对预算和独立审查组合。

## 初始分工

| 模型 | 初始用途 | 当前状态 |
| --- | --- | --- |
| GPT-6 Luna | 分类、metadata、抽取、低成本预处理 | 已联调；研究模式最低 Tier 1，不使用其代替审计 |
| DeepSeek 4.1 Flash | 机械 Coding、脚本与样板任务 | 登记但禁用，Adapter 未接入 |
| Sonnet 5.5 | 情景/创意讨论、历史整理、普通 Lead/综合 | 已联调 |
| GPT-6.1 Sol | 科学/工程/Evidence、工具任务、Coding 主力 | 研究 Adapter 已联调；Codex 仍只接软件工程 |
| Opus 5.5 | 高重要性 Lead、Integrator、Red Team | 已联调，Tier 2 |
| Fable 5.1 / GPT-6 Astra | 极难问题、全局一致性与最终独立复核 | 登记但禁用；需要 Tier 3 时返回 OPEN QUESTION |

软件工程分工是初始策略，不授予研究 Runtime 软件工程工具。所有强弱项均待项目自己的评测；联调通过只证明合成工具与 JSON 协议可运行。

现成方案检索：[LiteLLM Router](https://docs.litellm.ai/docs/routing) 已提供网关负载/延迟/成本路由；本阶段保留 Phase 6 官方 SDK，新增薄业务策略以执行固定快照、Canon 重要性、已验证状态与跨家族审查条件，没有部署新网关或重复实现供应商执行循环。YAML 复用 [PyYAML](https://pyyaml.org/wiki/PyYAMLDocumentation) SafeLoader，另拒绝别名、重复字段、非 JSON 值与超大文件；本机版本 6.0.3，许可证 MIT。
