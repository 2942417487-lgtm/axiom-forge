# Model Registry 与 Routing

配置由可信操作者编辑，不能来自 AgentInput、来源文本或模型 metadata。真实请求仍需宿主 Runtime profile、凭据与 `--allow-live`；登记模型不代表授权付费调用。

- `model_registry.yaml`：模型 ID、供应商与原生家族、层级、成本类别、上下文/输出、Runtime 支持的工具能力、验证状态与回执。当前启用 Luna、Sol、Sonnet、Opus；Fable、Astra、DeepSeek 与 legacy pool 禁用。
- `routing_policy.yaml`：难度、重要性、任务类别、复杂工具需求的最低档次。
- `role_assignments.yaml`：七个稳定研究岗位的候选优先级，全部为初始策略；最低可用档次优先，同档次才使用岗位排序。修改配置即可改分工，不修改 SDK 或岗位规则。
- `escalation_policy.yaml`：0 → 1 → 2 → 3、最多四次，最高档仍无答案保留 OPEN QUESTION。

成本类别不是实时账单。`minimum_reservation_usd` 是本项目操作者选择的最低单次预留，不是模型价格或最低消费。模型公开规格来源、核对日期及初始偏好来源须保留；调用可用性只依据本项目真实接入回执。能力字段描述现有 ToolSession 可绑定的能力，实际工具还须由宿主启用；搜索服务、网络来源、Python 脚本等缺少配置时会返回 unavailable。

```powershell
python run.py routing check
python run.py routing select --request <外部输入目录>/routing-request.json
```

RoutingRequest 有 role、task_kind、difficulty/importance（0–3）、context_size/output_tokens、tool_complexity、latency_tolerance、budget_usd、need_independent_review、major_canon_change、required_tools。上下文大小由宿主计量；模式入口采用 UTF-8 字节加余量的保守估计。延迟类别是可调整的初始偏好，不是响应时间 SLA。

`ModelRouter.select` 过滤禁用/未验证/legacy、档次不足、容量、输出、工具、预算和延迟，返回选择或 `OPEN_QUESTION`，列出过滤原因与策略哈希。不会把不可用 Tier 3 静默降到 Tier 1。`pair` 对要求独立审查或重要任务约束不同原生模型家族，即使两者都通过 ZenMux。没有满足条件的组合就保留问题；不同家族不保证没有共同错误。

`escalate(request, current_model, attempted, signals)` 是可调用的有界升级接口，signals 明确提供 uncertain、disagreement、unresolved 三个布尔值。它只选择模型，不付费调用、不从模型的任意 metadata 读取授权。模式入口只使用 select，按当前宿主要求选择模型，失败即停；尚未接入自动结果评估、升级或重新派发。TaskManager 提供固定流程编排、预算预留记录和操作者显式恢复。改变 request 的最低要求后应重新核对预算和独立审查组合。

## 配置与选型边界

岗位候选、模型启用状态、验证回执和最低档次以实际 YAML 配置为准；登记项可能禁用。软件工程任务与研究岗位分开，Codex 工程 Runtime 只接收 software_engineer，不因模型相同而获得研究权限。联调回执仅证明对应合成调用与协议可运行，不证明科学能力评测通过。

YAML 使用 PyYAML SafeLoader，另拒绝别名、重复字段、非 JSON 值与超大文件。路由为业务策略，不部署新的模型网关，也不替代 SDK 调用和宿主预算控制。
