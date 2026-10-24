# 四种世界观工作模式

世界操作与路径约束见 [独立世界工作区](../../docs/guides/world-workspaces.md)。显式指定外部 --world，配置与凭据来自外部宿主目录。

基于已建立的 AgentRuntime 和岗位契约执行一次有界研究会话。支持情景模拟、直接质疑、圆桌和法庭；模式由 TaskState.task_type 决定，不由模型选择。规则分别在同目录 Markdown 中，输出使用共同 SynthesisResult 与严格 ModeAnalysis。

当前次序为 Lead planning → 四个 Specialist independent → 四个 cross_review → Integrator draft_synthesis → Red Team → Integrator final_synthesis，共 12 次单岗调用。所有首轮在产生答案前完成输入投影，使用相同快照且不携带其他岗位答案；交叉审查使用同一首轮集合。LeadPlan 保存为建议，当前固定四个审计领域，不自动执行模型提出的分工或工具授权。

AgentInput 可选 `mode_protocol: "1.0"` 表示宿主启动了模式协议；此时 Runtime 加载同名模式规则，最终综合必须含 mode_analysis。旧单岗调用与既有输出保持兼容。模式检查因果节点/阶次与父节点、四个不同岗位或四个审计领域、Evidence 引用；结构校验不能证明因果、反例或科学结论本身为真。

上述独立 `modes run` 保留建议型 LeadPlan。TaskManager 的 [tasks run](../../docs/guides/task-management.md) 使用同一 ModeRunner 的可信宿主观察接口，要求计划覆盖四岗位，传入受限 planning_assignment，保存检索 Artifact 和 TaskState，并交付人工审查包；不会自动批准或 Apply。

## 离线演示

```powershell
# 合成离线演示随源码开发资料提供，不是产品运行依赖。
```

该入口使用明确标注 SYNTHETIC 的假 Adapter，只验证真实 Runtime、输入输出契约和本地存储，不读密钥、不调用 API、不执行科研或成本/推进计算。四种模式输出均为 OPEN QUESTION。记录在忽略的 `.axiom/local/mode-runs/<RUN>/` 与 `.axiom/local/runtime-runs/<ARN>/`。

## 真实模式入口

先创建固定快照和合法 TaskState，选择 task_type；准备可信宿主配置（源码仓库另附 `development/examples/mode-host.json`；独立产品由操作者在外部宿主准备配置）。profiles 必须匹配已登记 provider/model，明确每次额度、SDK 限制和工具授权；max_cost_usd 是本次会话的预留总额。确认来源与脚本可用性后显式启动：

```powershell
python run.py --world <外部世界目录> --host-root <外部宿主目录> modes run --task path/to/task.json --config <外部宿主配置.json> --credentials <外部.env> --allow-live
```

运行前由操作者为当前任务明确配置预算；示例不提供真实调用授权。完整模式包含多次模型调用，应按任务调整工具与输出限制。Claude 如需代理，仅在外部宿主 profile 显式配置；ZenMux Key 只能用于对应 base_url。

会话在调用前预留该 profile 的全部 max_cost_usd，不因失败或未知用量退款；不足以满足档次、家族、profile 工具或预算时返回 OPEN_QUESTION。单岗失败或取消会停止后续阶段，不生成最终模式结果；已完成岗位与工具回执保持追加保存。预留与 SDK 的本地额度不是服务商强制账单上限，尤其 Claude 阈值检查可能发生在请求之后；真实计费以控制台为准。

模式不修改传入 TaskState 或生产 world，不执行审批或 Canon Apply，不恢复旧厂商会话。完整任务与显式恢复、独立人工审批和 Canon 更新由任务宿主入口处理；科学内容仍须来源与计算验证。
